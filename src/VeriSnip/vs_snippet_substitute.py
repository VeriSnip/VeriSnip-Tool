"""Inlining of `.vs` snippet includes and cleanup of the module headers they leave behind."""

import os
import re
from typing import Optional

from .vs_colours import WARNING, vs_print


def locate_file_in_list(filename, files_list):
    found_files = ""
    for file in files_list:
        # TO DO: is this hack acceptable
        basename = os.path.basename(file)
        if basename == filename or basename == filename+".v" or basename == filename+".sv":
            if found_files != "":
                vs_print(
                    WARNING,
                    f"Found more than one directory with file {filename}.\n  {file}",
                )
            found_files = file
    return found_files


# Strip trailing commas left in module #(...) and (...) lists after .vs substitution.
#
# Approach: blank out comments/strings once into a same-length "masked" copy of the
# content, then do all paren/comma matching with plain index arithmetic against that
# copy (edits are applied to the original). This avoids re-deriving "am I inside a
# comment/string" at every step.
_RE_MODULE_NAME = re.compile(r"\bmodule\b\s+[A-Za-z_][A-Za-z0-9_$]*")
_RE_COMMENT_OR_STRING = re.compile(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"", re.DOTALL)


def _mask_comments_and_strings(content: str) -> str:
    """Same length as content, with comment/string bodies blanked out (newlines kept)."""
    return _RE_COMMENT_OR_STRING.sub(
        lambda m: "".join(c if c == "\n" else " " for c in m.group()), content
    )


def _match_parens(masked: str, index: int) -> Optional[tuple[int, int]]:
    """If the next non-whitespace char at/after index is '(', return the (inner_start, inner_end) of its balanced '(...)'."""
    while index < len(masked) and masked[index].isspace():
        index += 1
    if index >= len(masked) or masked[index] != "(":
        return None
    depth = 1
    for i in range(index + 1, len(masked)):
        if masked[i] == "(":
            depth += 1
        elif masked[i] == ")":
            depth -= 1
            if depth == 0:
                return (index + 1, i)
    return None


def _module_header_list_spans(masked: str) -> list[tuple[int, int]]:
    """Return (inner_start, inner_end) spans of module #(...) and (...) lists."""
    spans: list[tuple[int, int]] = []
    for match in _RE_MODULE_NAME.finditer(masked):
        index = match.end()

        probe = index
        while probe < len(masked) and masked[probe].isspace():
            probe += 1
        if probe < len(masked) and masked[probe] == "#":
            params = _match_parens(masked, probe + 1)
            if params is not None:
                spans.append(params)
                index = params[1] + 1

        ports = _match_parens(masked, index)
        if ports is not None:
            spans.append(ports)
    return spans


def _trailing_comma_index(masked: str, start: int, end: int) -> Optional[int]:
    """Index of a depth-0 trailing comma in masked[start:end], or None if there isn't one."""
    depth = 0
    last_comma = None
    for i in range(start, end):
        char = masked[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            last_comma = i
    if last_comma is None or masked[last_comma + 1 : end].strip():
        return None
    return last_comma


def strip_trailing_commas_in_module_headers(content: str) -> str:
    """
    Remove trailing commas in module parameter-port lists and ANSI port lists.
    Instantiations, tasks, functions, and concatenations are left unchanged.
    Comments and strings are never mistaken for list structure; a comment
    following the trailing comma is preserved.
    """
    masked = _mask_comments_and_strings(content)
    remove = {
        i
        for start, end in _module_header_list_spans(masked)
        if (i := _trailing_comma_index(masked, start, end)) is not None
    }
    if not remove:
        return content
    return "".join(char for i, char in enumerate(content) if i not in remove)


def _substitute_vs_includes(source_file: str, sources_list: list[str]) -> str:
    """Recursively substitute included .vs files without rewriting module headers."""
    new_content = ""
    on_comment = False

    with open(source_file, "r") as file:
        for line in file:
            if not on_comment:
                filename_match = re.findall(r'^\s*?`include\s+?"(.+?)\.vs"', line)
                if filename_match:
                    vs_file = filename_match[0] + ".vs"
                    vs_file_path = locate_file_in_list(vs_file, sources_list)

                    if vs_file_path:
                        new_content += _substitute_vs_includes(vs_file_path, sources_list)
                    else:
                        warning_text = f"File {vs_file} does not exist to substitute."
                        vs_print(WARNING, warning_text)
                        new_content += f"  // {warning_text}\n"
                    if "/*" in line:
                        on_comment = True
                else:
                    new_content += line
            else:
                if "*/" in line:
                    on_comment = False

    return new_content


def substitute_vs_file(source_file: str, sources_list: list[str]) -> str:
    """
    Recursively substitutes included .vs files in the source file content,
    then strips trailing commas in module parameter and port lists.
    """
    new_content = _substitute_vs_includes(source_file, sources_list)
    return strip_trailing_commas_in_module_headers(new_content)

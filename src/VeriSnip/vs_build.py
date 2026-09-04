#!/usr/bin/env python3
"""VeriSnip (VS) is a project designed to bring the power of Verilog scripting to the open-source hardware community. This tool simplifies the generation of Verilog modules or snippets by seamlessly integrating with other programs. The generated files can be easily included in any Verilog project."""

import os
import re
import shutil
import subprocess
import sys
import argparse
from typing import Any, Optional

from .vs_colours import INFO, OK, WARNING, NOTE, ERROR, DEBUG, CRITICAL, vs_print

class VsBuilder:
    _RE_MOD_INST = re.compile(r"\n\s*?(\w+?)\s+?(?:#\((?:[\s\S]*?)\))?\s*?(?:\w+?)\s*?\(\s*?(?:\.\w+?\s*?\([\s\S]*?)\);")
    _VERILOG_KEYWORDS = frozenset[str]({
        "module", "endmodule", "initial", "always", "assign", "if", "else",
        "for", "while", "case", "endcase", "begin", "end", "function",
        "endfunction", "task", "endtask", "generate", "endgenerate",
        "wire", "reg", "logic", "input", "output", "inout", "parameter",
        "localparam", "posedge", "negedge",
    })
    _RE_INC = re.compile(r'\n\s*?`include\s+?"(.*?)"(?!\s*?/\*)(.*)')
    _RE_INC_BLOCK = re.compile(r'\n\s*?`include\s+?"(.*?)"\s*?/\*([\s\S]*?)\*/')

    class VsSource:
        def __init__(self, name):
            self.name = name
            self.directory = ""
            self.comment = ""

        def locate_src(self, src_list):
            # TO DO: is there a better way of doing this?
            self.directory = locate_file_in_list(self.name, src_list)

        # TO DO: revise function
        def generate(self, script_files):
            script_directory, file_suffix = self._find_script(script_files)

            if script_directory != "":
                try:
                    script_arguments = [
                        script_directory,
                        file_suffix,
                        self.comment,
                    ] + sys.argv[1:]
                    subprocess.run(script_arguments, check=True)
                except subprocess.CalledProcessError as err:
                    vs_print(ERROR, f"{script_directory} failed!")
                    vs_print(NOTE, f"{err}")
                    sys.exit(1)
                except OSError as err:
                    vs_print(ERROR, f"Failed to execute {script_directory}: \n{err}")
                    sys.exit(1)
            else:
                vs_print(CRITICAL, f"Failed to generate '{self.name}': no script found.")
                return []
                
            generated_files = move_generated_files()
            for file in generated_files:
                basename = os.path.basename(file)
                if basename == self.name or basename == self.name+".v" or basename == self.name+".sv":
                    self.directory = file

            if generated_files == []:
                vs_print(WARNING, f"'{self.name}': generated no Verilog or VeriSnip files.")
            else:
                vs_print(DEBUG, f"'{os.path.basename(script_directory)}': generated files: {[os.path.basename(file) for file in generated_files]}")

            return generated_files

        # TO DO: revise function
        def _find_script(self, script_files):
            stem = self.name.removesuffix(".vs")
            input_words = stem.split("_") if stem else []
            similar_word_counter = 0
            most_similar_file = ""
            file_suffix = ""
            for file_path in script_files:
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                tmp_counter = 0
                tmp_string = ""
                for word in input_words:
                    tmp_string = tmp_string + word
                    tmp_counter = tmp_counter + 1
                    if file_name == tmp_string:
                        if tmp_counter > similar_word_counter:
                            similar_word_counter = tmp_counter
                            most_similar_file = file_path
                            file_suffix = "_".join(input_words[tmp_counter:])
                    tmp_string = tmp_string + "_"
            return most_similar_file, file_suffix

    def __init__(self, main_module, testbench, board_modules, include_directories):
        self.cwd = os.getcwd()
        self.main_module = main_module
        self.testbench = testbench
        self.board_modules = board_modules or []
        self.include_directories = include_directories or []
        self.source_configs = {}

        # discover files (implement or call your existing finder)
        self.script_files = []
        self.snippet_files = []
        self.verilog_files = []
        self._find_all_files()

        # resolved lists
        self.rtl_sources = []
        self.testbench_sources = []
        self.board_sources = {}

    def _find_all_files(self):
        vs_print(INFO, "Discovering HDL, snippet and script files...")
        excluded_files = {"LICENSE", ".gitignore", ".gitmodules", "Makefile", ".git"}
        verilog_extensions = {".v", ".vh", ".sv", ".svh"}
        script_extensions = {".py", ".sh", ".lua", ".scala", ".rb", ".pl", ".tcl", ""}

        script_files = []
        snippet_files = []
        verilog_files = []

        for search_dir in [self.cwd] + self.include_directories:
            for root, dirnames, filenames in os.walk(search_dir, topdown=True):
                # Prune irrelevant directories
                dirnames[:] = [d for d in dirnames if d not in {".git", "build", "generated", "__pycache__", ".venv"}]
                for fname in filenames:
                    name, ext = os.path.splitext(fname)
                    if name in excluded_files:
                        continue
                    fpath = os.path.join(root, fname)
                    if ext in script_extensions:
                        script_files.append(fpath)
                    if ext in verilog_extensions:
                        verilog_files.append(fpath)
                    if ext == ".vs":
                        snippet_files.append(fpath)

        # Deduplicate and sort for stable output
        self.script_files = sorted(set(script_files))
        self.verilog_files = sorted(set(verilog_files))
        self.snippet_files = sorted(set(snippet_files))

        vs_print(DEBUG, f"Found ({len(self.verilog_files)}) verilog files:")
        for file_path in self.verilog_files:
            vs_print(DEBUG, f"\t{relative_path(file_path)}")
        vs_print(DEBUG, f"Found ({len(self.snippet_files)}) snippet files:")
        for file_path in self.snippet_files:
            vs_print(DEBUG, f"\t{relative_path(file_path)}")
        vs_print(DEBUG, f"Found ({len(self.script_files)}) script files:")
        for file_path in self.script_files:
            vs_print(DEBUG, f"\t{relative_path(file_path)}")

    def resolve_sources(self) -> None:
        """
        This function builds the source lists needed for the RTL top module, testbench, and board wrappers.
        Each list contains the [System]Verilog and VeriSnip files reachable from its top module. Sources may already exist in the project or be generated from scripts when first referenced.
        """
        vs_print(INFO, f"Resolving sources for {self.main_module}...")
        generated_dir = os.path.join(self.cwd, "generated")
        create_directory(generated_dir)

        # Build RTL
        self.rtl_sources = self._collect_dependency_tree(self.main_module)

        # Build TestBench (excluding RTL duplicates)
        # TO DO: is this hack acceptable?
        if locate_file_in_list(self.testbench, self.verilog_files) != "":
            tb = self._collect_dependency_tree(self.testbench)
            self.testbench_sources = [f for f in tb if f not in self.rtl_sources]

        # Build Boards (each excluding RTL duplicates)
        self.board_sources = {}
        for board in self.board_modules:
            srcs = self._collect_dependency_tree(board)
            self.board_sources[board] = [f for f in srcs if f not in self.rtl_sources]

        # Debug print to verify resolved sources
        vs_print(DEBUG, f"RTL sources ({len(self.rtl_sources)}):")
        for src in self.rtl_sources:
            vs_print(DEBUG, f"\t{relative_path(src)}")

        if self.testbench:
            vs_print(DEBUG, f"TestBench sources ({len(self.testbench_sources)}):")
            for src in self.testbench_sources:
                vs_print(DEBUG, f"\t{relative_path(src)}")

        for board in self.board_modules:
            vs_print(DEBUG, f"Board '{board}' sources ({len(self.board_sources[board])}):")
            for src in self.board_sources[board]:
                vs_print(DEBUG, f"\t{relative_path(src)}")

    # ---------- source resolution helpers ----------

    # TO DO: revise passing only directories
    def _collect_dependency_tree(self, top_module: str) -> list[str]:
        """
        This function starts from a top module name, walks all discovered dependencies and returns the unique source file paths required to build the top module.
        Each referenced source is first located or generated, then scanned for further includes and module instantiations.
        """
        pending = [self.VsSource(top_module)]
        deferred = {}
        scanned = set()
        sources_directories = set()

        while pending:
            source = pending.pop(0)

            cfg = source.comment
            if source.name in self.source_configs:
                if self.source_configs[source.name] != cfg:
                    vs_print(ERROR, f"Source '{source.name}' referenced with conflicting configurations:\n"
                                    f"  Previous: {self.source_configs[source.name]}\n"
                                    f"  New:      {cfg}\n"
                                    f"VeriSnip currently supports only one configuration per generated file.")
                    sys.exit(1)
            else:
                self.source_configs[source.name] = cfg

            status = self._locate_or_generate_source(source)
            if status:
                if source.name in scanned:
                    continue
                scanned.add(source.name)
                sources_directories.add(source.directory)
                pending.extend(self._scan_source_dependencies(source))
                if not pending:
                    vs_print(DEBUG, f"Retrying deferred sources: {list(deferred.keys())}")
                    pending.extend(self._retry_deferred_sources(deferred))
            else:
                deferred[source.name] = source
        
        if deferred:
            vs_print(WARNING, f"The following sources could not be located or generated: {list(deferred.keys())}")
        
        return sorted(sources_directories)
    
    def _retry_deferred_sources(self, deferred: dict[str, VsSource]) -> list[VsSource]:
        """
        This function retries to locate the sources that were deferred.
        """
        resolved = []
        file_list = self.snippet_files + self.verilog_files
        for name, source in list(deferred.items()):
            source.locate_src(file_list)
            if source.directory:
                del deferred[name]
                resolved.append(source)
        return resolved
    
    def _locate_or_generate_source(self, source_file: VsSource) -> bool:
        """
        This function locates a given source in the known project files, or generates it from a matching script if it is missing. If the generation is successful, the generated files are added to the snippet_files and verilog_files source lists. If the generation is not successful, the function returns False.
        """
        file_list = self.snippet_files + self.verilog_files
        source_file.locate_src(file_list)
        
        if source_file.directory == "":
            vs_print(DEBUG, f"'{source_file.name}': missing from project sources. Trying to generate it...")
            if "VS_NO_GENERATE" in source_file.comment:
                vs_print(DEBUG, f"'{source_file.name}': VS_NO_GENERATE found in comment. Skipping generation.")
                return False
            else:
                generated_files = source_file.generate(self.script_files)
                if generated_files == []:
                    return False
                for file in generated_files:
                    if file.endswith(".vs"):
                        self.snippet_files.append(file)
                    else:
                        self.verilog_files.append(file)
        else:
            vs_print(DEBUG, f"'{source_file.name}': found in project sources.")
        return True

    def _scan_source_dependencies(self, source_file: VsSource) -> list[VsSource]:
        """
        This function scans a resolved source file and returns the sources it depends on. These dependencies can be either [System]Verilog or VeriSnip files. They can be found from `include` directives and module instantiations.
        """
        if not source_file.directory:
            vs_print(
                ERROR,
                f"Cannot resolve '{source_file.name}': missing from project sources and no "
                f"generator produced it. Check include paths, module names, and generator scripts.",
            )
            sys.exit(1)
        with open(source_file.directory, "r") as f:
            content = f.read()

        filename = os.path.basename(source_file.directory)
        file_dependencies = []
        for item in self._RE_INC.finditer(content):
            new_file = self.VsSource(item.group(1))
            new_file.comment = item.group(2).strip()
            file_dependencies.append(new_file)

        for item in self._RE_INC_BLOCK.finditer(content):
            new_file = self.VsSource(item.group(1))
            new_file.comment = item.group(2).strip()
            file_dependencies.append(new_file)

        for match in self._RE_MOD_INST.finditer(content):
            module_name = match.group(1)

            if module_name in self._VERILOG_KEYWORDS:
                vs_print(
                    NOTE,
                    f"Skipped '{module_name}' in {filename}: looks like a Verilog keyword, not a module instantiation.",
                )
                continue

            file_dependencies.append(self.VsSource(module_name))

        return file_dependencies
    
    # -----------------------------------------------

    def build_sources(self) -> None:
        """
        Create build directories, copy files and substitute snippets.
        Reuse existing helper functions where possible.
        """
        vs_print(INFO, "Populating build!")
        build_dir = f"{self.cwd}/build"
        create_directory(build_dir)
        build_verilog_sources(self.rtl_sources, build_dir+"/RTL")
        build_verilog_sources(self.testbench_sources, build_dir+"/TestBench")
        for board in self.board_modules:
            build_verilog_sources(self.board_sources[board], build_dir+"/"+board)
        pass


def clean_build(current_directory: str) -> None:
    """
    Cleans the build and generated directories by removing them and their contents.
    """
    remove_directory(f"{current_directory}/build")
    remove_directory(f"{current_directory}/generated")


def remove_directory(directory_to_remove: str) -> None:
    """
    Removes a directory and its contents.
    """
    if not os.path.isdir(directory_to_remove):
        vs_print(DEBUG, f"Directory '{directory_to_remove}' does not exist; nothing to remove.")
        return
    try:
        shutil.rmtree(directory_to_remove)
        vs_print(
            OK, f"Removed directory '{directory_to_remove}' and its contents."
        )
    except OSError as e:
        vs_print(WARNING, f"Could not remove directory. {e}")


def create_directory(path: str) -> None:
    """
    Creates a directory at the specified path.
    """
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        vs_print(WARNING, f"Did not create directory: {e}")


def relative_path(path: str) -> str:
    """
    Convert an absolute path to a relative path based on the current working directory.
    """
    return os.path.relpath(path, start=os.getcwd())


def move_generated_files():
    supported_extensions = [".v", ".vh", ".sv", ".svh", ".vs"]
    new_files = []
    cwd = os.getcwd()
    generated_dir = os.path.join(cwd, "generated")

    for filename in os.listdir(cwd):
        _, extension = os.path.splitext(filename)
        file_dst_path = os.path.join(generated_dir, filename)
        file_src_path = os.path.join(cwd, filename)
        if extension in supported_extensions:
            shutil.move(file_src_path, file_dst_path)
            new_files.append(file_dst_path)

    return new_files


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


def build_verilog_sources(sources: list[str], build_dir: str) -> None:
    """
    Builds Verilog sources from a list of source files and a build directory.
    """
    create_directory(build_dir)
    verilog_files = [file for file in sources if not file.endswith(".vs")]
    verisnip_files = [file for file in sources if file.endswith(".vs")]
    for verilog_file in verilog_files:
        verilog_content = ""
        verilog_content = substitute_vs_file(verilog_file, verisnip_files)
        file_name = os.path.basename(verilog_file)
        destination_path = f"{build_dir}/{file_name}"

        # Check if file exists and compare contents
        if os.path.exists(destination_path):
            with open(destination_path, "r") as existing_file:
                existing_content = existing_file.read()
            if existing_content == verilog_content:
                vs_print(DEBUG, f"File '{file_name}' unchanged, skipping write.")
                continue
        with open(f"{build_dir}/{file_name}", "w") as file:
            file.write(verilog_content)


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


def build_parser():
    description = (
        "VeriSnip (VS) version 0.0.4\n"
        "Create a build directory containing all the compiled hardware."
    )
    epilog = (
        "Examples:\n"
        "  vs_build top\n"
        "  vs_build top --TestBench top_tb --Boards \"Board1 Board2\"\n"
        "  vs_build top --inc_dir \"./rtl ../shared\"\n"
        "  vs_build top --pre-build scripts/setup.sh --post-build scripts/cleanup.sh\n"
        "  vs_build top EXTRA_FLAG=1\n"
        "  vs_build --clean\n\n"
        "Notes:\n"
        "  1. --TestBench defaults to <main_module>_tb.\n"
        "  2. --Boards accepts a space-separated string.\n"
        "  3. --inc_dir accepts a space-separated string.\n"
        "  4. Extra positional arguments (for example EXTRA_FLAG=1) are forwarded\n"
        "     to generator scripts together with the rest of vs_build's argv.\n"
    )
    parser = argparse.ArgumentParser(
        prog="vs_build",
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("module_name", nargs="?", help="Name of the main RTL top module.")
    parser.add_argument("--TestBench", dest="testbench_name", help="Testbench module name.")
    parser.add_argument("--Boards", dest="boards", default="", help="Space-separated list of board top modules.")
    parser.add_argument("--inc_dir", dest="include_dirs", default="", help="Space-separated list of include directories.")
    parser.add_argument("--pre-build", dest="pre_build", help="Path to script executed before build.")
    parser.add_argument("--post-build", dest="post_build", help="Path to script executed after a successful build.")
    parser.add_argument("--clean", action="store_true", dest="clean", help="Remove build and generated directories.")
    parser.add_argument("--quiet", action="store_true", help="Suppresses INFO, WARNING, NOTE, and DEBUG prints.")
    parser.add_argument("--debug", action="store_true", help="Enables DEBUG prints.")
    return parser


def parse_arguments():
    """
    Parses arguments with which vs_build is called.

    Returns:
        tuple: A tuple containing the module_name (string), testbench_name (string),
        board_modules (list), and include_directories (list).

    This function parses command-line arguments provided when calling vs_build. It extracts information such as the
    module name, testbench name, supported board modules, and include directories.
    """
    parser = build_parser()

    parsed_args, unknown_args = parser.parse_known_args()

    module_name = parsed_args.module_name
    testbench_name = parsed_args.testbench_name
    board_modules = []
    include_directories = []

    if testbench_name and re.match(r"^\s*$", testbench_name):
        vs_print(ERROR, "Empty value after --TestBench=")
        parser.print_help()
        exit(1)

    if module_name and testbench_name is None:
        testbench_name = f"{module_name}_tb"

    if parsed_args.boards:
        Boards = parsed_args.boards.split()
        Board_pattern = r"^[\w]+$"
        for Board in Boards:
            if re.match(Board_pattern, Board):
                board_modules.append(Board)  # Prefix will be applied after parsing if needed
            else:
                vs_print(ERROR, f"Invalid Board name {Board}")
                parser.print_help()
                exit(1)

    if parsed_args.include_dirs:
        directories = parsed_args.include_dirs.split()
        directory_pattern = r"^[\w/.-]+$"
        for directory in directories:
            if re.match(directory_pattern, directory):
                include_directories.append(directory)
            else:
                vs_print(ERROR, f"Invalid directory name {directory}")
                parser.print_help()
                exit(1)

    for arg in unknown_args:
        if arg.startswith("--"):
            vs_print(ERROR, f"Unknown argument {arg}")
            parser.print_help()
            exit(1)
        # Extra positionals are intentionally left in sys.argv so generator
        # scripts receive them when invoked from VsSource.generate().
        vs_print(DEBUG, f"Extra argument will be forwarded to generator scripts: {arg}")
    
    # Post-processing: apply "_" prefix expansion now that module_name is known
    if testbench_name and testbench_name.startswith("_") and module_name:
        testbench_name = f"{module_name}{testbench_name}"
    if module_name:
        board_modules = [
            (f"{module_name}{b}" if b.startswith("_") else b)
            for b in board_modules
        ]
          
    return (
        module_name,
        testbench_name,
        board_modules,
        include_directories,
        parsed_args.clean,
        parsed_args.pre_build,
        parsed_args.post_build,
    )


def run_script(path: str, stage: str) -> None:
    vs_print(INFO, f"Running {stage} script...")

    # 1. Check if the path is relative or absolute
    if os.path.isabs(path):
        script_path = path
    else:
        script_path = os.path.join(os.getcwd(), path)

    # 2. Check if the script exists
    if not os.path.exists(script_path):
        vs_print(ERROR, f"{stage} script not found at {script_path}")
        sys.exit(1) 

    # 3. Run the script and catch errors
    try:
        subprocess.run([script_path], check=True)
    except subprocess.CalledProcessError as err:
        vs_print(ERROR, f"{stage} script failed with exit code {err.returncode}.")
        sys.exit(1)
    except OSError as err:
        vs_print(ERROR, f"Failed to execute {stage} script: {err}")
        sys.exit(1)

    return


def main():
    """
    Main function to handle the vs_build script execution.
    It processes command-line arguments, cleans the build directory if requested,
    and builds the RTL, TestBench, and board modules as specified.
    """
    current_directory = os.getcwd()
    if len(sys.argv) < 2:
        build_parser().print_help()
        return

    (
        main_module,
        testbench,
        board_modules,
        include_directories,
        clean,
        pre_build_script,
        post_build_script,
    ) = parse_arguments()

    if clean:
        clean_build(current_directory)

    if pre_build_script and not os.path.isfile(pre_build_script):
        vs_print(ERROR, f"Pre-build script does not exist: {pre_build_script}")
        sys.exit(1)
    if post_build_script and not os.path.isfile(post_build_script):
        vs_print(ERROR, f"Post-build script does not exist: {post_build_script}")
        sys.exit(1)

    current_stage = "build"
    try:
        if pre_build_script:
            current_stage = "pre-build"
            run_script(pre_build_script, current_stage)

        if main_module is not None:
            current_stage = "build"
            builder = VsBuilder(main_module, testbench, board_modules, include_directories)
            builder.resolve_sources()  # Resolve and generate any missing HDL/snippet files; populate source lists.
            builder.build_sources()    # Copy sources into build/, performing snippet substitutions.
            vs_print(OK, f"Created {main_module} project build directory.")
        else:
            if not clean:
                vs_print(ERROR, f"Undefined main module!")
            sys.exit(1)

        if post_build_script:
            current_stage = "post-build"
            run_script(post_build_script, current_stage)
    except subprocess.CalledProcessError as err:
        vs_print(ERROR, f"{current_stage} step failed with exit code {err.returncode}.")
        sys.exit(1)


# Check if this script is called directly
if __name__ == "__main__":
    main()

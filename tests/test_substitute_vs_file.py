"""Tests for snippet inlining and trailing-comma cleanup in module headers."""

from pathlib import Path

from VeriSnip.vs_substitute import (
    locate_file_in_list,
    strip_trailing_commas_in_module_headers,
    substitute_vs_file,
)


def _write_and_substitute(tmp_path: Path, sv_text: str, snippets: dict[str, str]) -> str:
    sv_path = tmp_path / "top.sv"
    sv_path.write_text(sv_text, encoding="utf-8")
    snippet_paths = []
    for name, body in snippets.items():
        path = tmp_path / name
        path.write_text(body, encoding="utf-8")
        snippet_paths.append(str(path))
    return substitute_vs_file(str(sv_path), snippet_paths)


def test_snippet_only_parameter_strips_trailing_comma(tmp_path: Path):
    result = _write_and_substitute(
        tmp_path,
        """\
module top #(
    `include "params.vs"
) (
    input clk
);
endmodule
""",
        {"params.vs": "    parameter integer A = 1,\n    parameter integer B = 2,\n"},
    )
    assert "parameter integer B = 2\n) (" in result
    assert "parameter integer B = 2,\n) (" not in result
    assert "parameter integer A = 1," in result


def test_snippet_parameters_followed_by_more_keep_comma(tmp_path: Path):
    result = _write_and_substitute(
        tmp_path,
        """\
module top #(
    `include "params.vs"
    parameter integer EXTRA = 0
) (
    input clk
);
endmodule
""",
        {"params.vs": "    parameter integer A = 1,\n"},
    )
    assert "parameter integer A = 1," in result
    assert "parameter integer EXTRA = 0\n) (" in result


def test_snippet_only_ports_strips_trailing_comma(tmp_path: Path):
    result = _write_and_substitute(
        tmp_path,
        """\
module top (
    `include "ios.vs"
);
endmodule
""",
        {"ios.vs": "    input logic clk,\n    input logic rst,\n"},
    )
    assert "input logic rst\n);" in result
    assert "input logic rst,\n);" not in result
    assert "input logic clk," in result


def test_snippet_ports_followed_by_more_keep_comma(tmp_path: Path):
    result = _write_and_substitute(
        tmp_path,
        """\
module top (
    `include "ios.vs"

    input logic extra
);
endmodule
""",
        {"ios.vs": "    input logic clk,\n"},
    )
    assert "input logic clk," in result
    assert "input logic extra\n);" in result


def test_nested_paren_default_strips_only_list_comma():
    content = """\
module top #(
    parameter integer W = (8),
) (
    input clk
);
endmodule
"""
    result = strip_trailing_commas_in_module_headers(content)
    assert "parameter integer W = (8)\n) (" in result
    assert "parameter integer W = (8),\n) (" not in result


def test_line_comment_after_trailing_comma_is_preserved():
    content = """\
module top #(
    parameter integer A = 1,  // last param
) (
    input clk
);
endmodule
"""
    result = strip_trailing_commas_in_module_headers(content)
    assert "parameter integer A = 1  // last param" in result
    assert "parameter integer A = 1,  // last param" not in result


def test_block_comment_after_trailing_comma_is_preserved():
    content = """\
module top #(
    parameter integer A = 1,
    /* trailing */
) (
    input clk
);
endmodule
"""
    result = strip_trailing_commas_in_module_headers(content)
    assert "parameter integer A = 1\n    /* trailing */" in result
    assert "parameter integer A = 1,\n    /* trailing */" not in result


def test_instantiation_trailing_comma_is_left_unchanged():
    content = """\
module top (
    input clk
);
  foo inst (
    .a(a),
  );
endmodule
"""
    result = strip_trailing_commas_in_module_headers(content)
    assert result == content


def test_include_body_is_inlined(tmp_path: Path):
    result = _write_and_substitute(
        tmp_path,
        """\
module top;
  `include "body.vs"
endmodule
""",
        {"body.vs": "  wire generated_ok;\n"},
    )
    assert "wire generated_ok;" in result
    assert '`include "body.vs"' not in result


def test_missing_snippet_leaves_warning_comment_in_output(tmp_path: Path):
    result = _write_and_substitute(
        tmp_path,
        """\
module top;
  `include "missing.vs"
endmodule
""",
        {},
    )
    assert "does not exist to substitute" in result
    assert '`include "missing.vs"' not in result


def test_block_comment_config_after_include_is_stripped_from_output(tmp_path: Path):
    result = _write_and_substitute(
        tmp_path,
        """\
module top;
  `include "body.vs" /*
    WIDTH=8
  */
endmodule
""",
        {"body.vs": "  wire generated_ok;\n"},
    )
    assert "wire generated_ok;" in result
    assert "WIDTH=8" not in result
    assert "*/" not in result


def test_nested_vs_include_is_recursively_inlined(tmp_path: Path):
    result = _write_and_substitute(
        tmp_path,
        """\
module top;
  `include "outer.vs"
endmodule
""",
        {
            "outer.vs": '  `include "inner.vs"\n',
            "inner.vs": "  wire inner_ok;\n",
        },
    )
    assert "wire inner_ok;" in result
    assert '`include "inner.vs"' not in result
    assert '`include "outer.vs"' not in result


# ---------------------------------------------------------------------------
# locate_file_in_list
# ---------------------------------------------------------------------------

def test_locate_file_in_list_exact_match():
    files = ["/a/widget.vs", "/a/other.vs"]
    assert locate_file_in_list("widget.vs", files) == "/a/widget.vs"


def test_locate_file_in_list_matches_v_suffix():
    assert locate_file_in_list("top", ["/a/top.v"]) == "/a/top.v"


def test_locate_file_in_list_matches_sv_suffix():
    assert locate_file_in_list("top", ["/a/top.sv"]) == "/a/top.sv"


def test_locate_file_in_list_no_match_returns_empty_string():
    assert locate_file_in_list("missing.vs", ["/a/widget.vs"]) == ""


def test_locate_file_in_list_warns_on_duplicate_and_returns_last_match(capsys):
    result = locate_file_in_list("top.vs", ["/a/top.vs", "/b/top.vs"])

    assert result == "/b/top.vs"
    assert "more than one directory" in capsys.readouterr().out

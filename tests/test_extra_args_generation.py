"""Tests that extra vs_build CLI args are forwarded to generator scripts
and can produce distinct VeriSnip (.vs) content.
"""

import os
import sys
import textwrap
from pathlib import Path

import pytest

from VeriSnip.vs_build import VsBuilder


# Include name "snippet_body.vs" matches script "snippet.py" with suffix "body.vs".
GENERATOR_SCRIPT = textwrap.dedent(
    '''\
    #!/usr/bin/env python3
    """Minimal generator: writes snippet_body.vs from TAG=... in argv."""
    import sys

    tag = "default"
    for arg in sys.argv[1:]:
        if arg.startswith("TAG="):
            tag = arg.split("=", 1)[1]
            break

    # vs_build argv layout: [suffix, comment, *vs_build_argv[1:]]
    suffix = sys.argv[1] if len(sys.argv) > 1 else "body.vs"
    comment = sys.argv[2] if len(sys.argv) > 2 else ""
    out_name = f"snippet_{suffix}"

    with open(out_name, "w", encoding="utf-8") as f:
        f.write(f"// generated tag={tag} comment={comment}\\n")
        f.write(f"assign snippet_tag = \\"{tag}\\";\\n")
    '''
)


def _write_project(tmp: Path) -> None:
    (tmp / "top.v").write_text(
        textwrap.dedent(
            """\
            module top;
              `include "snippet_body.vs" // MODE=gen
            endmodule
            """
        ),
        encoding="utf-8",
    )
    script = tmp / "snippet.py"
    script.write_text(GENERATOR_SCRIPT, encoding="utf-8")
    script.chmod(0o755)


def _run_build(tmp: Path, extra_args: list[str]) -> Path:
    """Resolve sources under tmp with the given extra CLI args; return generated .vs path."""
    previous_cwd = os.getcwd()
    previous_argv = sys.argv[:]
    try:
        os.chdir(tmp)
        sys.argv = ["vs_build", "top", *extra_args]
        # Empty testbench skips TB resolution (None would crash locate_file_in_list).
        builder = VsBuilder("top", "", [], [])
        builder.resolve_sources()
    finally:
        os.chdir(previous_cwd)
        sys.argv = previous_argv

    generated = tmp / "generated" / "snippet_body.vs"
    assert generated.is_file(), f"expected generated snippet at {generated}"
    return generated


@pytest.mark.parametrize(
    "extra_args, expected_tag",
    [
        (["TAG=alpha"], "alpha"),
        (["TAG=beta"], "beta"),
        (["TAG=16", "OTHER=ignored"], "16"),
    ],
)
def test_extra_cli_args_shape_generated_verisnip(tmp_path: Path, extra_args, expected_tag):
    _write_project(tmp_path)
    generated = _run_build(tmp_path, extra_args)
    content = generated.read_text(encoding="utf-8")
    assert f"tag={expected_tag}" in content
    assert f'assign snippet_tag = "{expected_tag}";' in content


def test_distinct_extra_args_produce_distinct_verisnip_content(tmp_path: Path):
    project_a = tmp_path / "proj_a"
    project_b = tmp_path / "proj_b"
    project_a.mkdir()
    project_b.mkdir()
    _write_project(project_a)
    _write_project(project_b)

    vs_a = _run_build(project_a, ["TAG=alpha"])
    vs_b = _run_build(project_b, ["TAG=beta"])

    content_a = vs_a.read_text(encoding="utf-8")
    content_b = vs_b.read_text(encoding="utf-8")

    assert content_a != content_b
    assert "tag=alpha" in content_a
    assert "tag=beta" in content_b


def test_include_comment_is_passed_alongside_extra_args(tmp_path: Path):
    _write_project(tmp_path)
    generated = _run_build(tmp_path, ["TAG=gamma"])
    content = generated.read_text(encoding="utf-8")
    assert "MODE=gen" in content
    assert "tag=gamma" in content

import tempfile
from pathlib import Path

import pytest

from VeriSnip.vs_build import VsBuilder


def _builder_with_file(monkeypatch, content: str, name: str = "top.v") -> tuple[VsBuilder, Path]:
    tmp = tempfile.TemporaryDirectory()
    path = Path(tmp.name) / name
    path.write_text(content)
    # VsBuilder.__init__ walks os.getcwd() to discover project files; without
    # chdir'ing here it would scan the real repo instead of this fixture.
    monkeypatch.chdir(tmp.name)
    builder = VsBuilder("top", None, [], [])
    builder._temp_dir = tmp
    return builder, path


def test_include_directive_detected(monkeypatch):
    content = """
module top;
  `include "foo_ios.vs" // VS_NO_GENERATE
endmodule
"""
    builder, path = _builder_with_file(monkeypatch, content)
    source = builder.VsSource("top")
    source.directory = str(path)
    deps = builder._scan_source_dependencies(source)
    assert [d.name for d in deps] == ["foo_ios.vs"]


def test_include_block_comment_detected(monkeypatch):
    content = """
module top;
  `include "bar_logic.vs" /*
    WIDTH=8
  */
endmodule
"""
    builder, path = _builder_with_file(monkeypatch, content)
    source = builder.VsSource("top")
    source.directory = str(path)
    deps = builder._scan_source_dependencies(source)
    assert len(deps) == 1
    assert deps[0].name == "bar_logic.vs"
    assert "WIDTH=8" in deps[0].comment


def test_conflicting_configurations_throw_error(monkeypatch):
    content = """
module top;
  `include "my_snippet.vs" /* CONFIG=1 */
  `include "my_snippet.vs" /* CONFIG=2 */
endmodule
"""
    builder, path = _builder_with_file(monkeypatch, content, name="top.sv")

    # We must mock snippet file existence so it doesn't fail on missing source
    snippet_path = path.parent / "my_snippet.vs"
    snippet_path.write_text("// dummy")
    builder.snippet_files = [str(snippet_path)]
    builder.verilog_files = [str(path)]

    with pytest.raises(SystemExit):
        builder._collect_dependency_tree("top")

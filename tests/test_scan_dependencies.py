import tempfile
from pathlib import Path

from VeriSnip.vs_build import VsBuilder


def _builder_with_file(content: str, name: str = "top.v") -> tuple[VsBuilder, Path]:
    tmp = tempfile.TemporaryDirectory()
    path = Path(tmp.name) / name
    path.write_text(content)
    builder = VsBuilder("top", None, [], [])
    builder._temp_dir = tmp
    return builder, path


def test_include_directive_detected():
    content = """
module top;
  `include "foo_ios.vs" // VS_NO_GENERATE
endmodule
"""
    builder, path = _builder_with_file(content)
    source = builder.VsSource("top")
    source.directory = str(path)
    deps = builder._scan_source_dependencies(source)
    assert [d.name for d in deps] == ["foo_ios.vs"]


def test_include_block_comment_detected():
    content = """
module top;
  `include "bar_logic.vs" /*
    WIDTH=8
  */
endmodule
"""
    builder, path = _builder_with_file(content)
    source = builder.VsSource("top")
    source.directory = str(path)
    deps = builder._scan_source_dependencies(source)
    assert len(deps) == 1
    assert deps[0].name == "bar_logic.vs"
    assert "WIDTH=8" in deps[0].comment


def test_conflicting_configurations_throw_error():
    import pytest
    content = """
module top;
  `include "my_snippet.vs" /* CONFIG=1 */
  `include "my_snippet.vs" /* CONFIG=2 */
endmodule
"""
    builder, path = _builder_with_file(content, name="top.sv")
    
    # We must mock snippet file existence so it doesn't fail on missing source
    snippet_path = path.parent / "my_snippet.vs"
    snippet_path.write_text("// dummy")
    builder.snippet_files = [str(snippet_path)]
    builder.verilog_files = [str(path)]
    
    with pytest.raises(SystemExit):
        builder._collect_dependency_tree("top")

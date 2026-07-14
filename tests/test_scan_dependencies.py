import tempfile
from pathlib import Path

from VeriSnip.vs_build import VsBuilder


def _builder_with_file(content: str, name: str = "top.v") -> tuple[VsBuilder, Path]:
    tmp = tempfile.TemporaryDirectory()
    path = Path(tmp.name) / name
    path.write_text(content)
    builder = VsBuilder("top", None, [], {}, [])
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


def test_parameter_definition_scanned():
    content = """
module top #(
  parameter WIDTH = 8
) ();
endmodule
"""
    builder, path = _builder_with_file(content)
    source = builder.VsSource("top")
    source.directory = str(path)
    builder._scan_source_dependencies(source)
    assert builder.parameters["WIDTH"] == ["8"]


def test_parameter_instantiation_resolves_reference():
    content = """
module top #(
  parameter WIDTH = 8
) ();
  child #(
    .DATA_WIDTH(WIDTH)
  ) u_child (
    .clk(clk)
  );
endmodule
"""
    builder, path = _builder_with_file(content)
    source = builder.VsSource("top")
    source.directory = str(path)
    builder._scan_source_dependencies(source)
    assert "8" in builder.parameters["DATA_WIDTH"]


def test_localparam_definition_scanned():
    content = """
module tb ();
  localparam integer RAM_ADDR_WIDTH = 16;
endmodule
"""
    builder, path = _builder_with_file(content, name="tb.sv")
    source = builder.VsSource("tb")
    source.directory = str(path)
    builder._scan_source_dependencies(source)
    assert builder.parameters["RAM_ADDR_WIDTH"] == ["16"]


def test_localparam_instantiation_resolves_reference():
    content = """
module tb ();
  localparam integer RAM_ADDR_WIDTH = 16;
  axi_ram #(
    .ADDR_WIDTH(RAM_ADDR_WIDTH)
  ) u_ram ();
endmodule
"""
    builder, path = _builder_with_file(content, name="tb.sv")
    source = builder.VsSource("tb")
    source.directory = str(path)
    builder._scan_source_dependencies(source)
    assert "16" in builder.parameters["ADDR_WIDTH"]

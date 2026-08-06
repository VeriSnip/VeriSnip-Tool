import re

from VeriSnip.vs_build import VsBuilder

_RE_MOD_INST = VsBuilder._RE_MOD_INST
_KEYWORDS = VsBuilder._VERILOG_KEYWORDS


def _scan_modules(content: str) -> list[str]:
    modules = []
    for match in _RE_MOD_INST.finditer(content):
        name = match.group(1)
        if name in _KEYWORDS:
            continue
        modules.append(name)
    return modules


def test_axi_ram_detected_with_literal_port():
    snippet = """
  axi_ram #(
      .DATA_WIDTH(32)
  ) axi_ram_inst (
      .clk(clk),
      .s_axi_awlock(1'b0),
      .s_axi_awcache(axi_awcache)
  );
"""
    assert _scan_modules(snippet) == ["axi_ram"]


def test_module_declaration_not_detected():
    snippet = """
module foo (
  input clk
);
  initial begin
    $display("hi");
  end
endmodule
"""
    assert _scan_modules(snippet) == []


def test_named_port_instantiation_detected():
    snippet = """
  bitSANN #(
      .WIDTH(8)
  ) dut (
      .clk_i(clk)
  );
"""
    assert _scan_modules(snippet) == ["bitSANN"]

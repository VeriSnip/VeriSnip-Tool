#!/usr/bin/env python3

# axil_interface.py script creates required AXIL IOs and logic.
# To call this script in a Verilog file it should follow one of the following patterns:
#   `include "axil_interface_[slave/master]_[io/logic].vs"[,]
# If there is a comma (",") after the include and before the comment than this are not the last inputs/outputs (IOs) of the module.

import subprocess
from VTbuild import (
    find_verilog_and_scripts,
    find_filename_in_list,
)
from VTcolors import *

vs_name_suffix = sys.argv[1].removesuffix(".vs")
vs_name = f"axil_interface_{vs_name_suffix}.vs"

last_ios = False


def get_slave_ios():
    slave_ios = f"""
    input  wire AXIL_awvalid_i,
    output wire AXIL_awready_o,
    input  wire [ADDR_WIDTH-1:0] AXIL_awaddr_i,
    input  wire [2:0] AXIL_awprot_i,
    input  wire AXIL_wvalid_i,
    output wire AXIL_wready_o,
    input  wire [DATA_WIDTH-1:0] AXIL_wdata_i,
    input  wire [DATA_WIDTH/8-1:0] AXIL_wstrb_i,
    output  reg AXIL_bvalid_o,
    input  wire AXIL_bready_i,
    output wire [1:0] AXIL_bresp_o,
    input  wire AXIL_arvalid_i,
    output wire AXIL_arready_o,
    input  wire [ADDR_WIDTH-1:0] AXIL_araddr_i,
    input  wire [2:0] AXIL_arprot_i,
    output  reg AXIL_rvalid_o,
    input  wire AXIL_rready_i,
    output  reg [DATA_WIDTH-1:0] AXIL_rdata_o,
    output wire [1:0] AXIL_rresp_o{',' if last_ios else ''}
"""

    return slave_ios


def get_slave_logic():
    slave_logic = """
  // Automatically generated AXIL slave logic.
  assign AXIL_awready_o = 1'b1;
  assign AXIL_wready_o = 1'b1;
  assign AXIL_arready_o = 1'b1;
  assign AXIL_bresp_o = 2'b00;
  assign AXIL_rresp_o = 2'b00;

  assign w_address = AXIL_awvalid_i ? AXIL_awaddr_i : AXIL_awaddr_q;
  assign w_data = AXIL_wvalid_i ? AXIL_wdata_i : AXIL_wdata_q;
  assign w_enable = (AXIL_awvalid_i & AXIL_wvalid_i) | (AXIL_awvalid_i & AXIL_wvalid_q) | (AXIL_awvalid_q & AXIL_wvalid_i);
  assign r_address = AXIL_arvalid_i ? AXIL_araddr_i : AXIL_araddr_q;
  assign r_enable = AXIL_arvalid_i;
  assign AXIL_rvalid_e = AXIL_arvalid_i | AXIL_rready_i;

  `include "reg_axil_interface_slave.vs"  /*
    AXIL_awvalid_q, 1, 0, w_enable, AXIL_awvalid_i, AXIL_awvalid_i
    AXIL_awaddr_q, ADDR_WIDTH, 0, , AXIL_awvalid_i, AXIL_awaddr_i
    AXIL_wvalid_q, 1, 0, w_enable, AXIL_wvalid_i, AXIL_wvalid_i
    AXIL_wdata_q, DATA_WIDTH, 0, , AXIL_wvalid_i, AXIL_wdata_i
    AXIL_araddr_q, ADDR_WIDTH, 0, , AXIL_arvalid_i, AXIL_araddr_i
    AXIL_bvalid_o, 1, 0, , , w_enable
    AXIL_rvalid_o, 1, 0, , _e, r_enable
    AXIL_rdata_o, DATA_WIDTH, 0, , , r_data
    */
"""
    axil_slave_additional_signals()
    return slave_logic


def axil_slave_additional_signals():
    regs = "AXIL_awvalid_q, 1\n"
    regs += "AXIL_awaddr_q, ADDR_WIDTH\n"
    regs += "AXIL_wvalid_q, 1\n"
    regs += "AXIL_wdata_q, DATA_WIDTH\n"
    regs += "AXIL_araddr_q, ADDR_WIDTH\n"
    wire = "AXIL_rvalid_e, 1\n"

    current_directory = os.getcwd()
    module = sys.argv[3].split(".")[0]

    scripts, _ = find_verilog_and_scripts(current_directory)
    script_path = find_filename_in_list("generated_wires.py", scripts)
    script_arguments = ["python", script_path, module, wire]
    subprocess.run(script_arguments)
    script_arguments = ["python", script_path, module, regs, "variable"]
    subprocess.run(script_arguments)


def get_master_ios():
    master_ios = f"""
    output wire AXIL_awvalid_o,
    input  wire AXIL_awready_i,
    output wire [ADDR_WIDTH-1:0] AXIL_awaddr_o,
    output wire [2:0] AXIL_awprot_o,
    output wire AXIL_wvalid_o,
    input  wire AXIL_wready_i,
    output wire [DATA_WIDTH-1:0] AXIL_wdata_o,
    output wire [DATA_WIDTH/8-1:0] AXIL_wstrb_o,
    input  wire AXIL_bvalid_i,
    output wire AXIL_bready_o,
    input  wire [1:0] AXIL_bresp_i,
    output wire AXIL_arvalid_o,
    input  wire AXIL_arready_i,
    output wire [ADDR_WIDTH-1:0] AXIL_araddr_o,
    output wire [2:0] AXIL_arprot_o,
    input  wire AXIL_rvalid_i,
    output wire AXIL_rready_o,
    input  wire [DATA_WIDTH-1:0] AXIL_rdata_i,
    input  wire [1:0] AXIL_rresp_i{',' if last_ios else ''}
"""

    return master_ios


def get_master_logic():
    print_coloured(ERROR, "Master logic generation is not implemented yet.")
    exit(1)


def create_vs(node_type, component_type):
    vs_content = ""
    if node_type == "master":
        if component_type == "io":
            vs_content = get_master_ios()
        elif component_type == "logic":
            vs_content = get_master_logic()
        else:
            print_coloured(
                ERROR,
                f'AXIL generated file should be either "io" or "logic". {component_type} is not acceptable.',
            )
    elif node_type == "slave":
        if component_type == "io":
            vs_content = get_slave_ios()
        elif component_type == "logic":
            vs_content = get_slave_logic()
        else:
            print_coloured(
                ERROR,
                f'AXIL generated file should be either "io" or "logic". {component_type} is not acceptable.',
            )
    else:
        print_coloured(
            ERROR,
            f'AXIL interface should be either "master" or "slave". {node_type} is not acceptable.',
        )
    if vs_content == "":
        exit(1)
    write_vs(vs_content, vs_name)


def write_vs(string, file_name):
    with open(file_name, "w") as file:
        file.write(string)


def parse_arguments():
    global last_ios
    node_type = ""
    component_type = ""

    if len(sys.argv) < 3:
        print_coloured(ERROR, "Not enough arguments.")
        exit(1)

    node_type, component_type = vs_name_suffix.split("_")[:2]

    if "," in sys.argv[2]:
        last_ios = True

    return node_type, component_type


# Check if this script is called directly
if __name__ == "__main__":
    node_type, component_type = parse_arguments()
    create_vs(node_type, component_type)

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

last_ios = False


def get_slave_ios():
    slave_ios = f"""
    input  wire awvalid_i,
    output wire awready_o,
    input  wire [ADDR_WIDTH-1:0] awaddr_i,
    input  wire [2:0] awprot_i,
    input  wire wvalid_i,
    output wire wready_o,
    input  wire [DATA_WIDTH-1:0] wdata_i,
    input  wire [DATA_WIDTH/8-1:0] wstrb_i,
    output  reg bvalid_o,
    input  wire bready_i,
    output wire [1:0] bresp_o,
    input  wire arvalid_i,
    output wire arready_o,
    input  wire [ADDR_WIDTH-1:0] araddr_i,
    input  wire [2:0] arprot_i,
    output wire rvalid_o,
    input  wire rready_i,
    output  reg [DATA_WIDTH-1:0] rdata_o,
    output wire [1:0] rresp_o{',' if last_ios else ''}
"""

    return slave_ios


def get_slave_logic():
    slave_logic = """
  // Automatically generated AXIL slave logic.
  assign awready_o = 1'b1;
  assign wready_o = 1'b1;
  assign arready_o = 1'b1;
  assign bresp_o = 2'b00;
  assign rvalid_o = rvalid_q;
  assign rresp_o = 2'b00;

  assign w_address = awvalid_i ? awaddr_i : awaddr_q;
  assign w_data = wvalid_i ? wdata_i : wdata_q;
  assign w_enable = (awvalid_i & wvalid_i) | (awvalid_i & wvalid_q) | (awvalid_q & wvalid_i);
  assign r_address = arvalid_i ? araddr_i : araddr_q;
  assign r_enable = arvalid_i;
  assign rvalid_e = arvalid_i | rready_i;

  `include "reg_axil_interface_slave.vs"  /*
    awvalid_q, 1, 0, w_enable, awvalid_i, awvalid_i
    awaddr_q, ADDR_WIDTH, 0, , awvalid_i, awaddr_i
    wvalid_q, 1, 0, w_enable, wvalid_i, wvalid_i
    wdata_q, DATA_WIDTH, 0, , wvalid_i, wdata_i
    araddr_q, ADDR_WIDTH, 0, , arvalid_i, araddr_i
    bvalid_o, 1, 0, , , w_enable
    rvalid_q, 1, 0, , _e, r_enable
    rdata_o, DATA_WIDTH, 0, , , r_data
    */
"""
    axil_slave_aditional_signals()
    return slave_logic


def axil_slave_aditional_signals():
    regs = "awvalid_q, 1\n"
    regs += "awaddr_q, ADDR_WIDTH\n"
    regs += "wvalid_q, 1\n"
    regs += "wdata_q, DATA_WIDTH\n"
    regs += "araddr_q, ADDR_WIDTH\n"
    regs += "rvalid_q, 1\n"
    wire = "rvalid_e, 1\n"

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
    output wire awvalid_o,
    input  wire awready_i,
    output wire [ADDR_WIDTH-1:0] awaddr_o,
    output wire [2:0] awprot_o,
    output wire wvalid_o,
    input  wire wready_i,
    output wire [DATA_WIDTH-1:0] wdata_o,
    output wire [DATA_WIDTH/8-1:0] wstrb_o,
    input  wire bvalid_i,
    output wire bready_o,
    input  wire [1:0] bresp_i,
    output wire arvalid_o,
    input  wire arready_i,
    output wire [ADDR_WIDTH-1:0] araddr_o,
    output wire [2:0] arprot_o,
    input  wire rvalid_i,
    output wire rready_o,
    input  wire [DATA_WIDTH-1:0] rdata_i,
    input  wire [1:0] rresp_i{',' if last_ios else ''}
"""

    return master_ios


def get_master_logic():
    print_coloured(ERROR, "Master logic generation is not implemented yet.")
    exit(1)


def create_vs(node_type, component_type):
    vs_name = f"axil_interface_{sys.argv[1]}.vs"
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

    node_type, component_type = sys.argv[1].split("_")[:2]

    if "," in sys.argv[2]:
        last_ios = True

    return node_type, component_type


# Check if this script is called directly
if __name__ == "__main__":
    node_type, component_type = parse_arguments()
    create_vs(node_type, component_type)

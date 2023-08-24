#!/usr/bin/env python3

# reg.py script creates a register
# it should be called as "`include "reg_string.vs" // en rst rst_val=0 data_q=string_q ...""

import sys

reg_name = ""
en = False
rst = False
data_q = None
data_d = None
data_r = None
data_e = None
rst_val = None


def write_vs(string="", file_name="reg.vs"):
    with open(file_name, "w") as file:
        file.write(string)


def create_vs():
    vs_content = f"  // {reg_name} register\n"
    vs_content += "  always @(posedge clk_i, posedge arst_i) begin\n"
    vs_content += "    if (arst_i) begin\n"
    vs_content += f"      {data_q} <= 'd{rst_val};\n"
    if rst:
        vs_content += f"    end else if ({data_r}) begin\n"
        vs_content += f"      {data_q} <= 'd{rst_val};\n"
    if en:
        vs_content += f"    end else if ({data_e}) begin\n"
    else:
        vs_content += "    end else begin\n"
    vs_content += f"      {data_q} <= {data_d};\n"
    vs_content += "    end\n"
    vs_content += "  end\n"

    write_vs(vs_content, f"reg_{reg_name}.vs")


def parse_arguments():
    global reg_name, en, rst, data_q, data_d, data_r, data_e, rst_val

    if len(sys.argv) < 2:
        exit(1)
    reg_name = sys.argv[1]

    en = "en" in sys.argv
    rst = "rst" in sys.argv

    for arg in sys.argv[2:]:
        if arg.startswith("data_q="):
            data_q = arg.split("=")[1]
        elif arg.startswith("data_d="):
            data_d = arg.split("=")[1]
        elif arg.startswith("data_r="):
            data_r = arg.split("=")[1]
        elif arg.startswith("data_e="):
            data_e = arg.split("=")[1]
        elif arg.startswith("rst_val="):
            rst_val = int(arg.split("=")[1])

    if data_q is None:
        data_q = f"{reg_name}_q"
    if data_d is None:
        data_d = f"{reg_name}_d"
    if data_r is None:
        data_r = f"{reg_name}_r"
    if data_e is None:
        data_e = f"{reg_name}_e"
    if rst_val is None:
        rst_val = 0


# Check if this script is called directly
if __name__ == "__main__":
    parse_arguments()
    create_vs()

#!/usr/bin/env python3

import sys

def write_vs(string="", file_name="reg.vs"):
    file = open(file_name, "w")
    file.write(string)
    file.close()

def create_vs(reg_name):
    rst_val = 0
    rst = False
    en = False

    data_r = f"{reg_name}_r"
    data_e = f"{reg_name}_e"
    data_q = f"{reg_name}_q"
    data_d = f"{reg_name}_d"

    vs_content =      f"  // {reg_name} register\n"
    vs_content +=      "  always @(posedge clk_i, posedge arst_i) begin\n"
    vs_content +=      "    if (arst_i) begin\n"
    vs_content +=     f"      {data_q} <= 'd{rst_val};\n"
    if (rst):
        vs_content += f"    end else if ({data_r}) begin\n"
        vs_content += f"      {data_q} <= 'd{rst_val};\n"
    if (en):
        vs_content += f"    end else if ({data_e}) begin\n"
    else:
        vs_content +=  "    end else begin\n"
    vs_content +=     f"      {data_q} <= {data_d};\n"
    vs_content +=      "    end\n"
    vs_content +=      "  end\n"

    write_vs(vs_content, f"reg_{reg_name}.vs")

# Check if this script is called directly
if __name__ == "__main__":
    create_vs(sys.argv[1])
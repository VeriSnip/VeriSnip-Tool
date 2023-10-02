#!/usr/bin/env python3

# reg.py script creates a register
# it should be called as "`include "reg_string.vs" // en rst rst_val=0 data_q=string_q ...""
# TO DO: alternative to call:
## `include "reg_{Reg_name}.vs" // Size, Reset Value, Reg_reset, Reg_enable, Reg_next"
## and
## `include "reg_{list_name}.vs" /*
##           Reg_name0, Size, Reset Value, Reg_reset, Reg_enable, Reg_next
##           Reg_name1, Size, Reset Value, Reg_reset, Reg_enable, Reg_next
##           Reg_name2, Size, Reset Value, Reg_reset, Reg_enable, Reg_next
##           ...
##           */
## Default values are: Size = 1 bit; Reset Value = 0; Reg_reset = None; Reg_enable = None; Reg_next = {Reg_name}_n.

import sys

from VTcolors import *


class register:
    def __init__(self, reg_properties):
        self.name = ""
        self.signal = ""
        self.size = ""
        self.rst_val = ""
        self.rst = ""
        self.en = ""
        self.next = ""

        # TO DO: function that parses reg_properties and is able to organize its values in a list
        self.set_reg_name(reg_properties[0].strip())
        self.set_reg_size(reg_properties[1].strip())
        self.set_reg_rst_val(reg_properties[2].strip())
        self.set_reg_rst(reg_properties[3].strip())
        self.set_reg_en(reg_properties[4].strip())
        self.set_reg_next(reg_properties[5].strip())

    def set_reg_name(self, reg_name):
        known_suffixes = ["_q", "_r", "_reg"]
        if "name=" in reg_name:
            self.name = reg_name.split("name=")[1]
        if reg_name == "":
            print_coloured(ERROR, "You should give a name to the register.")
            exit(1)
        else:
            self.name = reg_name
        self.signal = self.name
        for suffix in known_suffixes:
            self.name = self.name.rsplit(suffix)[0]


    def set_reg_size(self, reg_size):
        if "size=" in reg_size:
            self.size = reg_size.split("=")[1]
        if reg_size == "":
            self.size = "1"
        else:
            self.size = reg_size

    def set_reg_rst_val(self, reg_rst_val):
        if "rst_val=" in reg_rst_val:
            self.rst_val = reg_rst_val.split("=")[1]
        if reg_rst_val == "":
            self.rst_val = f"{self.size}'d0"
        elif reg_rst_val.isdigit():
            self.rst_val = f"{self.size}'d{reg_rst_val}"
        else:
            self.rst_val = reg_rst_val

    def set_reg_rst(self, reg_rst):
        if "rst=" in reg_rst:
            self.rst = reg_rst.split("=")[1]
        if reg_rst == "":
            self.rst = None
        elif reg_rst.startswith("_"):
            self.rst = f"{self.name}{reg_rst}"
        else:
            self.rst = reg_rst

    def set_reg_en(self, reg_en):
        if "en=" in reg_en:
            self.en = reg_en.split("=")[1]
        if reg_en == "":
            self.en = None
        elif reg_en.startswith("_"):
            self.en = f"{self.name}{reg_en}"
        else:
            self.en = reg_en

    def set_reg_next(self, reg_next):
        if "next=" in reg_next:
            self.next = reg_next.split("=")[1]
        if reg_next == "":
            self.next = f"{self.name}_n"
        elif reg_next.startswith("_"):
            self.next = f"{self.name}{reg_next}"
        else:
            self.next = reg_next


def create_vs(vs_content):
    vs_name = f"reg_{sys.argv[1]}.vs"
    write_vs(vs_content, vs_name)


def write_vs(string="", file_name="reg.vs"):
    with open(file_name, "w") as file:
        file.write(string)


def reg_description(reg_list):
    verilog_code = f"  // {sys.argv[1]} register file\n"
    verilog_code += "  always @(posedge clk_i, posedge arst_i) begin\n"
    verilog_code += "    if (arst_i) begin\n"
    for reg in reg_list:
        verilog_code += f"      {reg.signal} <= {reg.rst_val};\n"
    verilog_code += f"    end else begin\n"
    for reg in reg_list:
        if reg.rst is not None:
            verilog_code += f"      if ({reg.rst}) begin\n"
            verilog_code += f"        {reg.signal} <= {reg.rst_val};\n"
        if reg.en is not None:
            verilog_code += f"      end else if ({reg.en}) begin\n"
        else:
            verilog_code += "      end else begin\n"
        verilog_code += f"        {reg.signal} <= {reg.next};\n"
        verilog_code += "      end\n"
    verilog_code += "    end\n"
    verilog_code += "  end\n"

    return verilog_code


def parse_arguments():
    if len(sys.argv) < 2:
        print_coloured(ERROR, "Not enough arguments.")
        exit(1)

    if "//" in sys.argv:
        args_after_comment = "".join(sys.argv[sys.argv.index("//") + 1 :])
        reg_properties = [sys.argv[1]] + args_after_comment.split(",")
        register_list = [register(reg_properties)]
        return register_list
    else:
        print_coloured(ERROR, "Not supported yet.")


# Check if this script is called directly
if __name__ == "__main__":
    reg_list = parse_arguments()
    vs_content = reg_description(reg_list)
    create_vs(vs_content)

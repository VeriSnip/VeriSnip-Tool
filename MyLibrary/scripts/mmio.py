#!/usr/bin/env python3

from VTcolors import *

# Should be called as "`include "mmio_{module}.vs" /*
#                       Reg_name0, Address, Size, Reset Value, Access Type, Reg_reset, Reg_enable, Reg_next
#                       Reg_name1, Address, Size, Reset Value, Access Type, Reg_reset, Reg_enable, Reg_next
#                       Reg_name2, Address, Size, Reset Value, Access Type, Reg_reset, Reg_enable, Reg_next
#                       ...
#                       */

module = sys.argv[1]

assigns = ""
read_always = ""
write_always = ""
registers = '`include "reg_mmio.vs"'

def parse_arguments():
    if len(sys.argv) < 2:
        print_coloured(ERROR, "Not enough arguments")
        exit(1)
    arguments = "".join(sys.argv[2:])
    list_of_regs = arguments.split("\n")
    print_coloured(DEBUG, list_of_regs)

def create_vs():
    vs_content = ""
    write_vs(vs_content, f"mmio_{module}.vs")

def write_vs(string="", file_name="reg.vs"):
    with open(file_name, "w") as file:
        file.write(string)

# Check if this script is called directly
if __name__ == "__main__":
    parse_arguments()
    create_vs()

    print_coloured(WARNING ,"\"mmio.py\" script still does nothing.")
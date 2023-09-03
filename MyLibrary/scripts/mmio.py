#!/usr/bin/env python3

from VTcolors import *

# Should be called as "`include "mmio_{module}.vs" /*
#                        Reg_name0, Address, Size, Reset Value, Access Type, Reg_reset, Reg_enable
#                        Reg_name1, Address, Size, Reset Value, Access Type, Reg_reset, Reg_enable
#                        Reg_name2, Address, Size, Reset Value, Access Type, Reg_reset, Reg_enable
#                        ...
#                        */


# Check if this script is called directly
if __name__ == "__main__":
    print_coloured(WARNING ,"\"mmio.py\" script still does nothing.")
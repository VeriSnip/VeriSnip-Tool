# MyScripts
This files gives a little information about the scripts under the current directory. This scripts are intended to generate automatic Verilog snippets code.

## instantiate.py

## mmio.py
This script

### How to call

> Should be called as "`include "mmio_{module}.vs" /*  
                        Reg_name0, Address, Size, Reset Value, Access Type, Reg_reset, Reg_enable, Reg_next_value  
                        Reg_name1, Address, Size, Reset Value, Access Type, Reg_reset, Reg_enable, Reg_next_value  
                        Reg_name2, Address, Size, Reset Value, Access Type, Reg_reset, Reg_enable, Reg_next_value  
                        ...  
                        */

### Dependencies
- reg.py

## reg.py
This script creates a snippet which instantiates one register or a list of registers. Every register should have a asynchronous reset and a clock signal. The registers can also have a synchronous reset signal and an enable signal. No more logic should be included when describing registers.

### How to call
The `reg.py` script can be called in two different ways. It could be called to describe only one register or it can receive a list of registers to describe. The ways to call it are respectively:

> `include "reg_{Reg_name}.vs" // Size, Reset Value, Reg_reset, Reg_enable, Reg_next_value"

and

> `include "reg_{list_name}.vs" /*  
            Reg_name0, Size, Reset Value, Reg_reset, Reg_enable, Reg_next_value  
            Reg_name1, Size, Reset Value, Reg_reset, Reg_enable, Reg_next_value  
            Reg_name2, Size, Reset Value, Reg_reset, Reg_enable, Reg_next_value  
            ...  
            */  

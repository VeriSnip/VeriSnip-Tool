# Random notes/ideas
- generate_io: if "," is in script call arguments than do not add a "," to the last generated IO.
- axil_interface_slave_logic: does not work if "awvalid_i" and "wvalid_i" are not set at the same time. Does not work if "rready_i" is not always set.
- reg.py: add comments above registers on register list.
- generate_wire: make arithmetic operation so that instead of "8-1" appears "7".
- reg.py: remove "_o" for reg.name when reg.signal has it.
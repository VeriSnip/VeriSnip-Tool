#!/usr/bin/env python3

def update_module_text(module_text, prefix):
    updated_lines = []

    for line in module_text.split('\n'):
        if line.strip().startswith('parameter'):
            parts = line.strip().split()
            parameter_value = parts[-1].rstrip(',')
            parameter_name = parts[-3]
            updated_line = f"    .{parameter_name}({parameter_value}),"
            updated_lines.append(updated_line)
        elif line.strip().startswith('input') or line.strip().startswith('output'):
            parts = line.strip().split()
            port_name = parts[-1].rstrip(',')
            updated_line = f"    .{port_name}({prefix}_{port_name}),"
            updated_lines.append(updated_line)
        else:
            updated_lines.append(line)

    updated_module_text = '\n'.join(updated_lines)
    return updated_module_text

original_text = """
module myuart #(
    parameter integer ADDR_W = 16,
    parameter integer DATA_W = 32,
    parameter integer TX_FIFO_DEPTH = 16,  // in bytes
    parameter integer RX_FIFO_DEPTH = 16  // in bytes
) (
    // ... ports ...

    input  wire rx_i,  // Receiver input
    output wire tx_o,  // Transmitter output

    output wire interrupt_o  // interrupt/event output
);
"""

prefix = "rcv"
updated_text = update_module_text(original_text, prefix)

uut_instantiation = f"""
  // Instantiate the Unit Under Test (UUT)
  myuart #(
    .ADDR_W(16),
    .DATA_W(32),
    .TX_FIFO_DEPTH(16),  // in bytes
    .RX_FIFO_DEPTH(16)  // in bytes
  ) {prefix} (
{updated_text}
  );
"""

print(uut_instantiation)

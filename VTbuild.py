#!/usr/bin/env python3

import sys
import re
import subprocess

def search(verilog_file):
    print("Find or generate '.vs' and modules used by the system.")
    with open(verilog_file, 'r') as file:
        for line in file:
            match = re.search(r'`include "reg_(.*?)\.vs" // (.*)', line)
            if match:
                reg_name = match.group(1)
                arguments = match.group(2)
                arguments_list = arguments.split()
                script_arguments = ['python', 'library/scripts/reg.py', reg_name] + arguments_list
                subprocess.run(script_arguments)
                break

def organize():
    print("Create build directory, substitute '.vs' and copy modules used by the system.")

def substitute_vs_file(verilog_file):
    with open(verilog_file, 'r') as file:
        content = file.read()

    def include_sub(match):
        include_line = match.group(0)
        reg_name = match.group(1)
        with open(f"reg_{reg_name}.vs", 'r') as reg_file:
            reg_content = reg_file.read()
        return reg_content

    new_content = re.sub(r'`include "reg_(.*?)\.vs" // (.*)', include_sub, content)

    with open("new.v", 'w') as file:
        file.write(new_content)


# Check if this script is called directly
if __name__ == "__main__":
    verilog_file = sys.argv[1]  # Replace with your Verilog file name
    search(verilog_file)
    substitute_vs_file(verilog_file)
    organize()
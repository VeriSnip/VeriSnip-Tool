#!/usr/bin/env python3

# instantiate.py script creates the instantiation of a module
# To call this script in a Verilog file it should follow one of the following patterns:
#   `include "instantiate_{module}_{module_name}.vs" // prefix="prefix" suffix="suffix" {port_name}="connected signal"
# Default values are: prefix = "{module_name}_"; suffix = ""; {port_name} = "{prefix}{port_name}{suffix}".
# It depends on: generated_wires.py.

import sys, os, re
import subprocess
from VTbuild import (
    find_verilog_and_scripts,
    find_or_generate,
    find_filename_in_list,
    substitute_vs_file,
)
from VTcolors import *

callee_module = ""
module = ""
module_name = ""
parameters = ""
ports_text = ""
prefix = None
suffix = None
custom_ports = {}

PROGRAM = "instantiate.py"


def update_module_text(module_text, prefix):
    global parameters, ports_text
    module_parameters = []
    module_ports = []
    module_new_ports = {}
    for line in module_text.split("\n"):
        if line.strip().startswith("parameter"):
            parameter_part, comment_part = extract_comment(line)
            parts = parameter_part.split("=")
            parameter_name = parts[0].strip().split()[-1]
            if parameter_name in custom_ports:
                parameter_value = custom_ports[parameter_name]
            else:
                parameter_value = parts[1].strip().rstrip(",")
            updated_line = f"      .{parameter_name}({parameter_value}),{comment_part}"
            module_parameters.append(updated_line)
        elif line.strip().startswith("input") or line.strip().startswith("output"):
            io_part, comment_part = extract_comment(line)
            parts = io_part.split()
            port_name = parts[-1].rstrip(",")
            if port_name in custom_ports:
                port_value = custom_ports[port_name]
            else:
                if port_name.endswith("_o"):
                    port = port_name.replace("_o", "")
                elif port_name.endswith("_i"):
                    port = port_name.replace("_i", "")
                else:
                    port = port_name
                port_value = f"{prefix}{port}{suffix}"
                module_new_ports[port_value] = io_part
            updated_line = f"      .{port_name}({port_value}),{comment_part}"
            module_ports.append(updated_line)

    if module_parameters != []:
        module_parameters[-1] = module_parameters[-1].replace(",", "")
        parameters = "\n".join(module_parameters)
    if module_ports != []:
        module_ports[-1] = module_ports[-1].replace(",", "")
        ports_text = "\n".join(module_ports)

    generate_io_wires(module_new_ports)


def generate_io_wires(io_dictionary):
    generate_wires = ""
    for io_name in io_dictionary:
        match = re.search(r".*?\[(.*?):.*?].*?", io_dictionary[io_name])
        if match:
            io_size = get_io_size(match.group(1).strip())
        else:
            io_size = ""
        generate_wires += f"{io_name}, {io_size}\n"
    scripts, _ = find_verilog_and_scripts(current_directory)
    script_path = find_filename_in_list("generated_wires.py", scripts)
    script_arguments = ["python", script_path, callee_module, generate_wires]
    subprocess.run(script_arguments)


def get_io_size(io_length):
    # Split the input string on arithmetic operators (+, -, *, /) while preserving the operators
    parts = re.split(r'([-+])', io_length)
    parts = [part.strip() for part in parts]
    if len(parts)%2 != 1:
        print("Port does not have a valid lenght: {io_length}")
        exit(1)

    arithmetic_str = f"+1"
    arithmetic = 1
    index = 0
    while index < len(parts):
        arithmetic_str = f"{parts[-(index+1)]}" + arithmetic_str
        try:
            arithmetic = eval(arithmetic_str)
            io_size = str(arithmetic)
        except (NameError, SyntaxError):
            # If it's not a valid arithmetic expression, add it to the result as is
            if arithmetic > 0:
                io_size = "".join(parts[0:len(parts)-index])+f"+{arithmetic}"
            elif arithmetic < 0:
                io_size = "".join(parts[0:len(parts)-index])+str(arithmetic)
            else:
                io_size = "".join(parts[0:len(parts)-index])
            break
        index = index + 1
    
    return io_size


def extract_comment(line):
    match = re.match(r"(.*?)\s*//\s*(.*)", line)
    if match:
        variable_part = match.group(1).strip()
        comment_part = match.group(2).strip()
        comment_part = f" // {comment_part}"
        return variable_part, comment_part
    else:
        return line.strip(), ""


def write_vs(string="", file_name="reg.vs"):
    with open(file_name, "w") as file:
        file.write(string)


def create_vs(content):
    update_module_text(content, prefix)
    if parameters != "":
        parameters_text = f"#(\n{parameters}\n  ) "
    else:
        parameters_text = ""
    instantiation = f"""
  // Instantiation of {module}, autogenerated by {PROGRAM}
  {module} {parameters_text}{module_name} (
{ports_text}
  );
"""
    write_vs(instantiation, f"instantiate_{module}_{module_name}.vs")


def parse_arguments():
    global module, module_name, prefix, suffix, callee_module

    if len(sys.argv) < 2:
        exit(1)
    module = sys.argv[1].split("_")[0]
    module_name = sys.argv[1][len(module) + 1 :]

    # print_coloured(DEBUG, ' '.join(sys.argv))
    arguments = re.split(r" (?![^\"\"]*[\"])", sys.argv[2])
    for arg in arguments:
        # Split the argument into variable name and value
        name_value = arg.split("=")
        if len(name_value) == 2:
            name, value = name_value
            custom_ports[name] = value

    if "prefix" in custom_ports:
        prefix = custom_ports["prefix"]
    if "suffix" in custom_ports:
        suffix = custom_ports["suffix"]

    if prefix is None:
        prefix = f"{module_name}_"
    if suffix is None:
        suffix = ""

    if len(sys.argv) > 3:
        callee_module, _ = os.path.splitext(sys.argv[3])


def module_definition_content(current_directory):
    sources_list = []

    script_files, verilog_files = find_verilog_and_scripts(current_directory)
    sources_list, verilog_files = find_or_generate(
        "", [module], script_files, verilog_files, sources_list
    )

    if sources_list == []:
        print_coloured(ERROR, f"Module {module} not found")
        exit(1)

    with open(sources_list[0], "r") as file:
        content = file.read()
    filename = os.path.basename(sources_list[0])

    module_text = ""
    module_pattern = r"module(.*?)\n?\s*#?\(\n([\s\S]*?)\);\n"
    module_matches = re.findall(module_pattern, content)

    if module_matches[0][0].strip() != module:
        print_coloured(
            ERROR, f"Module {module} not equivalent to {module_matches[0][0].strip()}."
        )
        exit(1)

    module_text = module_matches[0][1]
    include_pattern = r'`include "(.*?)"([^\n]*)'
    include_matches = re.findall(include_pattern, module_text)
    for include in include_matches:
        sources_list, verilog_files = find_or_generate(
            filename, include, script_files, verilog_files, sources_list
        )

    new_content = ""
    for line in module_text.split("\n"):
        include = re.search(r'`include "(.*?)\.vs"(.*)', line)
        if include:
            vs_file = include.group(1) + ".vs"
            vs_file_path = find_filename_in_list(vs_file, sources_list)
            if vs_file_path != None:
                new_content += substitute_vs_file(vs_file_path, sources_list)
            else:
                warning_text = f"File {vs_file} does not exist to substitute."
                print_coloured(WARNING, warning_text)
                new_content += f"  // {warning_text}"
        else:
            new_content += line + "\n"

    return new_content


# Check if this script is called directly
if __name__ == "__main__":
    current_directory = os.getcwd()
    parse_arguments()
    content = module_definition_content(current_directory)
    create_vs(content)

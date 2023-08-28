#!/usr/bin/env python3

# Should be called as "`include "instantiate_{module}_{module_name}.vs" // prefix="prefix" suffix="suffix""

import sys, os, re
from VTbuild import (
    find_verilog_and_scripts,
    find_or_generate,
    find_filename_in_list,
    substitute_vs_file,
)
from VTcolors import *

module = ""
module_name = ""
parameters_text = ""
ports_text = ""
prefix = None
suffix = None
custom_ports = {}

PROGRAM = "instantiate.py"


def update_module_text(module_text, prefix):
    global parameters_text, ports_text
    module_parameters = []
    module_ports = []
    for line in module_text.split("\n"):
        if line.strip().startswith("parameter"):
            variable_part, comment_part = extract_comment(line)
            parts = variable_part.split()
            parameter_name = parts[-3]
            if parameter_name in custom_ports:
                parameter_value = custom_ports[parameter_name]
            else:
                parameter_value = parts[-1].rstrip(",")
            updated_line = f"    .{parameter_name}({parameter_value}),{comment_part}"
            module_parameters.append(updated_line)
        elif line.strip().startswith("input") or line.strip().startswith("output"):
            variable_part, comment_part = extract_comment(line)
            parts = variable_part.split()
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
            updated_line = f"    .{port_name}({port_value}),{comment_part}"
            module_ports.append(updated_line)

    if module_parameters != []:
        print(module_parameters)
        module_parameters[-1] = module_parameters[-1].replace(",", "")
        parameters_text = "\n".join(module_parameters)
    if module_ports != []:
        module_ports[-1] = module_ports[-1].replace(",", "")
        ports_text = "\n".join(module_ports)


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
    instantiation = f"""
  // Instantiation of {module} the Unit Under Test (UUT)
  {module} #(
{parameters_text}
  ) {module_name} (
{ports_text}
  );
"""
    write_vs(instantiation, f"instantiate_{module}_{module_name}.vs")


def parse_arguments():
    global module, module_name, prefix, suffix

    if len(sys.argv) < 2:
        exit(1)
    module = sys.argv[1].split("_")[0]
    module_name = sys.argv[1][len(module) + 1 :]

    for arg in sys.argv[2:]:
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


def module_definition_content(current_directory):
    sources_list = []

    script_files, verilog_files = find_verilog_and_scripts(current_directory)
    sources_list, verilog_files = find_or_generate(
        [module], script_files, verilog_files, sources_list
    )

    if sources_list == []:
        print_coloured(ERROR, f"Module {module} not found")
        exit(1)

    with open(sources_list[0], "r") as file:
        content = file.read()

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
            include, script_files, verilog_files, sources_list
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

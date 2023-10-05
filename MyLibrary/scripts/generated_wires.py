#!/usr/bin/env python3

from VTcolors import *

vs_name = f"generated_wires_{sys.argv[1]}.vs"


class wire:
    def __init__(self, wire_properties) -> None:
        wire_properties = [wire_property.strip() for wire_property in wire_properties]
        self.set_wire_name(wire_properties[0])
        self.set_wire_size(wire_properties[1])

    def set_wire_name(self, wire_name):
        if "name=" in wire_name:
            wire_name = wire_name.split("name=")[1]
        if wire_name == "":
            print_coloured(ERROR, "You should give a name to the wire.")
            exit(1)
        else:
            self.name = wire_name

    def set_wire_size(self, wire_size):
        if "size=" in wire_size:
            wire_size = wire_size.split("=")[1]
        if wire_size == "":
            self.size = "1"
        else:
            self.size = wire_size


def create_vs(wires):
    vs_content = ""
    for wire in wires:
        if (wire.size != "1"):
            vs_content += f"  wire [{wire.size}-1:0] {wire.name};\n"
        else:
            vs_content += f"  wire {wire.name};\n"
    write_vs(vs_content, vs_name)


def find_file_recursive(directory, search_filename):
    # Walk through the directory tree recursively
    for _, _, files in os.walk(directory):
        for filename in files:
            # Check if the filename matches the search pattern
            if filename == search_filename:
                return True

    return False


def write_vs(string, file_name):
    current_directory = os.getcwd()
    generated_file = f"{current_directory}/hardware/generated/{file_name}"
    content = f"  // Automatically generated wires for {sys.argv[1]}\n"
    if os.path.isfile(generated_file):
        with open(generated_file, "r") as file:
            content = file.read()
    content += string
    with open(file_name, "w") as file:
        file.write(content)


def parse_arguments():
    wires = []
    if len(sys.argv) > 2:
        wires_properties = sys.argv[2].split("\n")
        for wire_properties in wires_properties:
            wire_properties = wire_properties.split(",")
            wires.append(wire(wire_properties))
    return wires


if __name__ == "__main__":
    wires = parse_arguments()
    create_vs(wires)

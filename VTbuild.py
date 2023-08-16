#!/usr/bin/env python3

import sys, re, os
import subprocess
import shutil


# Generic functions
def find_filename_in_list(filename, files_list):
    found_files = [file for file in files_list if os.path.basename(file) == filename]

    if found_files:
        return found_files[0]  # Return the first matching file
    else:
        return None


def create_directory(path):
    try:
        os.makedirs(path)
        print(f"Directory '{path}' created successfully.")
    except OSError as e:
        print(f"Error creating directory '{path}': {e}")


# VTbuild functional functions
def find_vs_scripts_and_verilog(directory):
    vs_files = []
    script_files = []
    verilog_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".vs"):
                vs_files.append(os.path.join(root, file))
            elif file.endswith(".py"):
                script_files.append(os.path.join(root, file))
            elif file.endswith(".v") or file.endswith(".vh"):
                verilog_files.append(os.path.join(root, file))

    print("Found snippet files:")
    for vs_file in vs_files:
        print(vs_file)
    print("Found script files:")
    for script_file in script_files:
        print(script_file)
    print("Found verilog files:")
    for verilog_file in verilog_files:
        print(verilog_file)
    print()

    return vs_files, script_files, verilog_files


def find_or_generate_vs(verilog_file):
    with open(verilog_file, 'r') as file:
        for line in file:
            match = re.search(r'`include "(.*?)\.vs"(.*)', line)
            if match:
                file_name = match.group(1)
                arguments = match.group(2)
                arguments_list = arguments.split()
                vs_path = find_filename_in_list(f"{file_name}.vs", vs_files)
                if vs_path is None:
                    script_path, script_arg = search_script(file_name)
                    if script_path is not None:
                        script_arguments = ['python', script_path, script_arg] + arguments_list
                        subprocess.run(script_arguments)
                        vs_files.append(f"{file_name}.vs")


def search_script(string_name):
    script_arg = ""
    script_path = find_filename_in_list(f"{string_name}.py", script_files)
    if script_path is None:
        string_parts = string_name.split('_')
        first_string = string_parts[0]
        script_arg = '_'.join(string_parts[1:])
        script_path = find_filename_in_list(f"{first_string}.py", script_files)
        if script_path is None:
            print(f"Unable to find or generate '{string_name}.vs'.")
    return script_path, script_arg


def substitute_vs_file(verilog_file):
    new_content = ""
    with open(verilog_file, 'r') as file:
        for line in file:
            match = re.search(r'`include "(.*?)\.vs"(.*)', line)
            if match:
                vs_file = match.group(1) + ".vs"
                vs_file_path = find_filename_in_list(vs_file, vs_files)
                with open(vs_file_path, 'r') as vs_file:
                    vs_content = vs_file.read()
                new_content += vs_content
            else:
                new_content += line

    build_dir = f"{current_directory}/build/rtl"
    create_directory(build_dir)
    with open(f"{build_dir}/{sys.argv[1]}.v", 'w') as file:
        file.write(new_content)


def clean_build():
    directory_to_remove = f"{current_directory}/build"
    try:
        shutil.rmtree(directory_to_remove)
        print(f"Directory '{directory_to_remove}' and its contents removed successfully.")
    except OSError as e:
        print(f"Error removing directory '{directory_to_remove}' and its contents: {e}")


# Check if this script is called directly
if __name__ == "__main__":
    current_directory = os.getcwd()
    if sys.argv[1] == "--clean":
        clean_build()
    else:
        vs_files, script_files, verilog_files = find_vs_scripts_and_verilog(current_directory)
        verilog_top_file = find_filename_in_list(f"{sys.argv[1]}.v", verilog_files)  # Replace with your Verilog file name
        find_or_generate_vs(verilog_top_file)
        substitute_vs_file(verilog_top_file)

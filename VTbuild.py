#!/usr/bin/env python3

import sys, re, os
import subprocess
import shutil

from VTcolors import *

program = "VTbuild"


# Displays help information about how to use the program.
def help_build():
    text = f'''
{program} must receive at least one argument.
The first argument can be: 
    --help -> shows this text
    --clean -> removes the build directory
    top_module -> creates the build directory with top_module as the main RTL design.
'''
    print_color(INFO, text)


# Cleans the build directory by removing it and its contents.
def clean_build():
    directory_to_remove = f"{current_directory}/build"
    try:
        shutil.rmtree(directory_to_remove)
        print_color(OK, f"Directory '{directory_to_remove}' and its contents removed successfully.")
    except OSError as e:
        print_color(ERROR, f"removing directory '{directory_to_remove}' and its contents: {e}")


# Finds all verilog snippets, modules, and scripts under the given directory.
# Args:
#   directory: The directory to search.
# Returns:
#   A lists of all verilog snippets, modules, and scripts found in the directory.
def find_vs_scripts_and_verilog(directory):
    vs_files = []
    script_files = []
    verilog_files = []
    excluded_files = ['LICENSE', '.gitignore', '.gitmodules']

    for root, dirs, files in os.walk(directory, topdown=True):
        dirs[:] = [d for d in dirs if '.git' not in d]
        for file in files:
            filename, extension = os.path.splitext(file)
            if filename not in excluded_files:
                if extension == ".vs":
                    vs_files.append(os.path.join(root, file))
                elif extension == ".py" or extension == "":
                    script_files.append(os.path.join(root, file))
                elif extension == ".v" or extension == ".vh":
                    verilog_files.append(os.path.join(root, file))

    print("Found snippet files:")
    print(vs_files)
    print("Found script files:")
    print(script_files)
    print("Found verilog files:")
    print(verilog_files)
    print()

    return vs_files, script_files, verilog_files


# Finds the verilog file or generates it from a snippet file.
# Args:
#   verilog_file: The verilog file to find.
# Returns:
#   A list of all verilog files.
# This function first checks if the verilog file exists. If it does not exist,
# the function checks if a snippet file with the same name exists. If a snippet
# file exists, the function generates the verilog file from the snippet file.
def verilog_fetch(verilog_file):
    module_list = [verilog_file]
    with open(verilog_file, 'r') as file:
        for line in file:
            match = re.search(r'`include "(.*?)\.vs"(.*)', line)
            if match:
                file_name = match.group(1)
                arguments = match.group(2)
                arguments_list = arguments.split()
                vs_path = find_filename_in_list(f"{file_name}.vs", vs_files)
                if vs_path is None:
                    script_path, script_arg = find_most_common_prefix(file_name, script_files)
                    if script_path is not None:
                        script_arguments = ['python', script_path, script_arg] + arguments_list
                        subprocess.run(script_arguments)
                        vs_files.append(f"{file_name}.vs")
    return module_list


# Searches for the file with the most common prefix in a file list.
# Args:
#   file_name (str): A string equivalent to the file name to search for.
#   file_list (list): A list of script file names. 
# Returns:
#    tuple: A tuple containing the file path and the remaining string words.
def find_most_common_prefix(file_name, file_list):
    input_words = file_name.split("_")
    max_common_words = 0
    most_common_file = ""
    uncommon_words = ""

    for file_path in file_list:
        filename = os.path.basename(file_path)
        filename_without_extension = os.path.splitext(filename)[0]
        common_words = 0
        string_words = filename_without_extension.split("_")

        if len(input_words) > len(string_words):
            for i in range(len(string_words)):
                if input_words[i] == string_words[i]:
                    common_words += 1
                else:
                    break

        if common_words > max_common_words:
            max_common_words = common_words
            uncommon_words = '_'.join(input_words[common_words:])
            most_common_file = file_path

    return most_common_file, uncommon_words


# Builds the Verilog file by substituting included .vs files and writing to build directory.
# Args:
#   verilog_file: The Verilog file to build.
def verilog_build(verilog_file):
    verilog_content = ""
    verilog_content = substitute_vs_file(verilog_file)
    build_dir = f"{current_directory}/build/rtl"
    file_name = os.path.basename(verilog_file)
    create_directory(build_dir)
    with open(f"{build_dir}/{file_name}", 'w') as file:
        file.write(verilog_content)


# Recursively substitutes included .vs files in the source file content.
# Args:
#   source_file: The source file containing potential `include directives.
# Returns:
#   The new content with included .vs files substituted.
def substitute_vs_file(source_file):
    new_content = ""
    with open(source_file, 'r') as file:
        for line in file:
            match = re.search(r'`include "(.*?)\.vs"(.*)', line)
            if match:
                vs_file = match.group(1) + ".vs"
                vs_file_path = find_filename_in_list(vs_file, vs_files)
                new_content += substitute_vs_file(vs_file_path)
            else:
                new_content += line
    return new_content


# Finds the filename in the list of files.
# Args:
#   filename: The filename to find.
#   files_list: The list of files to search.
# Returns:
#   The first matching file, or None if the file is not found.
def find_filename_in_list(filename, files_list):
    found_files = [file for file in files_list if os.path.basename(file) == filename]

    if found_files:
        return found_files[0]  # Return the first matching file
    else:
        return None


# Creates a directory at the specified path.
# Args:
#   path: The path of the directory to be created.
def create_directory(path):
    try:
        os.makedirs(path)
        print_color(OK, f"Directory '{path}' created successfully.")
    except OSError as e:
        print_color(WARNING, f"Failed to create directory: {e}")


# Check if this script is called directly
if __name__ == "__main__":
    current_directory = os.getcwd()
    if len(sys.argv)<2 or sys.argv[1] == "--help":
        help_build()
    elif sys.argv[1] == "--clean":
        clean_build()
    else:
        vs_files, script_files, verilog_files = find_vs_scripts_and_verilog(current_directory)
        top_module = find_filename_in_list(f"{sys.argv[1]}.v", verilog_files)  # Replace with your Verilog file name
        module_list = verilog_fetch(top_module)
        for file in module_list:
            verilog_build(file)

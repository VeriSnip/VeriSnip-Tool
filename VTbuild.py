#!/usr/bin/env python3

import os
import re
import shutil
import subprocess
import sys

from VTcolors import *

program = "VTbuild"
DEBUG_MODE = False  # Set to True for debugging
if "--debug" in sys.argv:
    debug_index = sys.argv.index("--debug")
    sys.argv.pop(debug_index)
    DEBUG_MODE = True
    print_coloured(DEBUG, "mode activated.")


# Displays help information about how to use the program.
def help_build():
    text = f"""
{program} must receive at least one argument.
The first argument can be: 
    --help -> shows this text
    --clean -> removes the build directory
    top_module -> creates the build directory with top_module as the main RTL design.
"""
    print_coloured(INFO, text)


# Cleans the build directory by removing it and its contents.
def clean_build():
    directory_to_remove = f"{current_directory}/build"
    remove_directory(directory_to_remove)
    if sys.argv[2] == "all":
        directory_to_remove = f"{current_directory}/hardware/generated"
        remove_directory(directory_to_remove)


# Removes a directory and its contents.
# Args:
#   directory_to_remove: The directory to remove.
def remove_directory(directory_to_remove):
    try:
        shutil.rmtree(directory_to_remove)
        print_coloured(
            OK,
            f"Directory '{directory_to_remove}' and its contents removed successfully.",
        )
    except OSError as e:
        print_coloured(
            WARNING, f"removing directory '{directory_to_remove}' and its contents: {e}"
        )


# Finds all verilog snippets, modules, and scripts under the given directory.
# Args:
#   directory: The directory to search.
# Returns:
#   A lists of all verilog snippets, modules, and scripts found in the directory.
def find_verilog_and_scripts(directory):
    script_files = []
    verilog_files = []
    excluded_files = ["LICENSE", ".gitignore", ".gitmodules"]
    verilog_extensions = [".v", ".vh", ".sv", ".svh", ".vs"]
    script_extensions = ["", ".py", ".sh"]

    for root, dirs, files in os.walk(directory, topdown=True):
        dirs[:] = [
            d
            for d in dirs
            if (".git" not in d) and (d != "build") and (d != "hardware/generated")
        ]
        for file in files:
            filename, extension = os.path.splitext(file)
            if filename not in excluded_files:
                if extension in script_extensions:
                    script_files.append(os.path.join(root, file))
                elif extension in verilog_extensions:
                    verilog_files.append(os.path.join(root, file))

    if DEBUG_MODE:
        print_coloured(DEBUG, f"Found verilog files:")
        for verilog_file in verilog_files:
            print_coloured(DEBUG, verilog_file)
        print_coloured(DEBUG, f"Found script files:")
        for script_file in script_files:
            print_coloured(DEBUG, script_file)

    return script_files, verilog_files


# Fetch verilog files, generating them if necessary.
# Args:
#   verilog_files (list): List of existing verilog file paths.
#   script_files (list): List of script file paths.
# Returns:
#   A list of all verilog files used by the core.
def verilog_fetch(verilog_files, script_files):
    sources_list = []
    sources_list, verilog_files = find_or_generate(
        [sys.argv[1]], script_files, verilog_files, sources_list
    )
    generated_path = f"{current_directory}/hardware/generated"
    create_directory(generated_path)
    i = 0

    while i < len(sources_list):
        verilog_file = sources_list[i]
        sources_list, verilog_files = analyse_file(
            verilog_file, script_files, verilog_files, sources_list
        )
        i = i + 1

    return sources_list


# Analyze a verilog file for module instantiations or includes.
# Args:
#   file_path (str): Path to the verilog file.
#   script_files (list): List of script file paths.
#   verilog_files (list): List of verilog file paths.
# Returns:
#   list: List of additional source file paths.
def analyse_file(file_path, script_files, verilog_files, sources_list):
    with open(file_path, "r") as file:
        content = file.read()

    module_pattern = r"(.*?)\n?\s*#?\(\n([\s\S]*?)\);\n"
    include_pattern = r'`include "(.*?)"([^\n]*)'
    include_pattern_alternative = r'`include "(.*?)" \\\*([\s\S]*?)\*/'
    for pattern in [module_pattern, include_pattern]:
        matches = re.findall(pattern, content)
        for item in matches:
            if not item[0].startswith("module "):
                sources_list, verilog_files = find_or_generate(
                    item, script_files, verilog_files, sources_list
                )

    return sources_list, verilog_files


# Find or generate a file based on given conditions.
# Args:
#   str_list (list): Name of the file to find or generate.
#   script_files (list): List of script file paths.
#   verilog_files (list): List of verilog file paths.
#   match: Matched object from module pattern.
# Returns:
#   str: Path to the found or generated file.
def find_or_generate(str_list, script_files, verilog_files, sources_list):
    file_path = None
    file_name = str_list[0].split()[0]
    _, extension = os.path.splitext(file_name)
    if extension == "":
        file_path = find_filename_in_list(f"{file_name}.v", verilog_files)
        if file_path is None:
            file_path = find_filename_in_list(f"{file_name}.sv", verilog_files)
    else:
        file_path = find_filename_in_list(file_name, verilog_files)

    if file_path is None:
        arguments_list = []
        if file_name.endswith(".vs"):
            arguments_list = str_list[1].split()
        script_path, script_arg = find_most_common_prefix(file_name, script_files)
        if script_path != "":
            script_arguments = ["python", script_path, script_arg] + arguments_list
            subprocess.run(script_arguments)
            sources_list, verilog_files = move_to_generated_dir(
                script_path, file_name, current_directory, sources_list, verilog_files
            )
    else:
        sources_list.append(file_path)
        print_coloured(
            INFO, f"File {file_name} already exists under the current directory."
        )

    return sources_list, verilog_files


# Moves Verilog files generated by a script under the current directory to the generated directory.
# Args:
#   script_path (str): A string equivalent to the script path executed.
#   current_directory (str): A string equivalent to the current directory.
# Returns:
#   generated_dir (str): Directory of the generated files.
def move_to_generated_dir(
    script_path, file_name, current_directory, sources_list, verilog_files
):
    verilog_extensions = [".v", ".vh", ".sv", ".svh", ".vs"]
    verilog_files_found = []
    generated_dir = os.path.join(current_directory, "hardware/generated/")
    file_path = os.path.join(current_directory, f"hardware/generated/{file_name}")

    for filename in os.listdir(current_directory):
        filename_no_ext, extension = os.path.splitext(filename)
        file_dir = os.path.join(generated_dir, filename)
        if extension in verilog_extensions:
            verilog_files.append(file_dir)
            file_path = os.path.join(current_directory, filename)
            shutil.move(file_path, file_dir)
        if filename == file_name or filename_no_ext == file_name:
            sources_list.append(file_path)

    if verilog_files_found == []:
        print_coloured(WARNING, f"{script_path} generated no Verilog files.")
    else:
        print_coloured(
            INFO, f"{script_path} generated {', '.join(verilog_files_found)}."
        )

    return sources_list, verilog_files


# Searches for the file with the most common prefix in a file list.
# Args:
#   file_name (str): A string equivalent to the file name to search for.
#   file_list (list): A list of script file names.
# Returns:
#    tuple: A tuple containing the file path and the remaining string words.
def find_most_common_prefix(file_name, file_list):
    filename_without_extension = os.path.splitext(file_name)[0]
    input_words = filename_without_extension.split("_")
    max_common_words = 0
    most_common_file = ""
    uncommon_words = ""

    for file_path in file_list:
        file_name = os.path.basename(file_path)
        filename_without_extension = os.path.splitext(file_name)[0]
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
            uncommon_words = "_".join(input_words[common_words:])
            most_common_file = file_path

    return most_common_file, uncommon_words


# Builds the Verilog files by substituting included .vs files and writes them to the build directory.
# Args:
#   sources_list (list): List of Verilog files to build.
def verilog_build(sources_list):
    build_dir = f"{current_directory}/build/rtl"
    create_directory(build_dir)
    for verilog_file in sources_list:
        if not verilog_file.endswith(".vs"):
            verilog_content = ""
            verilog_content = substitute_vs_file(verilog_file, sources_list)
            file_name = os.path.basename(verilog_file)
            with open(f"{build_dir}/{file_name}", "w") as file:
                file.write(verilog_content)


# Recursively substitutes included .vs files in the source file content.
# Args:
#   source_file: The source file containing potential `include directives.
# Returns:
#   The new content with included .vs files substituted.
def substitute_vs_file(source_file, sources_list):
    new_content = ""
    with open(source_file, "r") as file:
        for line in file:
            match = re.search(r'`include "(.*?)\.vs"(.*)', line)
            if match:
                vs_file = match.group(1) + ".vs"
                vs_file_path = find_filename_in_list(vs_file, sources_list)
                if vs_file_path != None:
                    new_content += substitute_vs_file(vs_file_path, sources_list)
                else:
                    warning_text = f"File {vs_file} does not exist to substitute."
                    print_coloured(WARNING, warning_text)
                    new_content += f"  // {warning_text}"
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
    found_files = None
    for file in files_list:
        if os.path.basename(file) == filename:
            if found_files != None:
                print_coloured(
                    WARNING, f"Found more than one directory with file {filename}."
                )
            found_files = file

    if found_files:
        return found_files
    else:
        return None


# Creates a directory at the specified path.
# Args:
#   path: The path of the directory to be created.
def create_directory(path):
    try:
        os.makedirs(path)
        print_coloured(OK, f"Created directory '{path}'.")
    except OSError as e:
        if DEBUG_MODE:
            print_coloured(DEBUG, f"Did not create directory: {e}")


# Check if this script is called directly
if __name__ == "__main__":
    current_directory = os.getcwd()
    if len(sys.argv) < 2 or sys.argv[1] == "--help":
        help_build()
    elif sys.argv[1] == "--clean":
        clean_build()
    else:
        script_files, verilog_files = find_verilog_and_scripts(current_directory)
        sources_list = verilog_fetch(verilog_files, script_files)
        verilog_build(sources_list)

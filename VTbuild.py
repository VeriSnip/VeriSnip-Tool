#!/usr/bin/env python3

import sys, re, os
import subprocess
import shutil

from VTcolors import *

program = "VTbuild"
DEBUG_MODE = True  # Set to True for debugging

# Displays help information about how to use the program.
def help_build():
    text = f'''
{program} must receive at least one argument.
The first argument can be: 
    --help -> shows this text
    --clean -> removes the build directory
    top_module -> creates the build directory with top_module as the main RTL design.
'''
    print_coloured(INFO, text)


# Cleans the build directory by removing it and its contents.
def clean_build():
    directory_to_remove = f"{current_directory}/build"
    try:
        shutil.rmtree(directory_to_remove)
        print_coloured(OK, f"Directory '{directory_to_remove}' and its contents removed successfully.")
    except OSError as e:
        print_coloured(ERROR, f"removing directory '{directory_to_remove}' and its contents: {e}")


# Finds all verilog snippets, modules, and scripts under the given directory.
# Args:
#   directory: The directory to search.
# Returns:
#   A lists of all verilog snippets, modules, and scripts found in the directory.
def find_verilog_and_scripts(directory):
    script_files = []
    verilog_files = []
    excluded_files = ['LICENSE', '.gitignore', '.gitmodules']
    verilog_extensions = [".v", ".vh", ".vs"]
    script_extensions  = ["", ".py", ".sh"]

    for root, dirs, files in os.walk(directory, topdown=True):
        dirs[:] = [d for d in dirs if '.git' not in d]
        for file in files:
            filename, extension = os.path.splitext(file)
            if filename not in excluded_files:
                if extension in script_extensions:
                    script_files.append(os.path.join(root, file))
                elif extension in verilog_extensions:
                    verilog_files.append(os.path.join(root, file))

    if DEBUG_MODE:
        print_coloured(DEBUG, f"Found verilog files: {', '.join(verilog_files)}. \n")
        print_coloured(DEBUG, f"Found script files: {', '.join(script_files)}. \n")

    return script_files, verilog_files


# Fetch verilog files, generating them if necessary.
# Args:
#   verilog_files (list): List of existing verilog file paths.
#   script_files (list): List of script file paths.
# Returns:
#   A list of all verilog files.
def verilog_fetch(verilog_files, script_files):
    top_module = find_filename_in_list(f"{sys.argv[1]}.v", verilog_files)
    sources_list = [top_module]
    generated_path = f"{current_directory}/hardware/generated"
    create_directory(generated_path)
    i = 0

    while(i<len(sources_list)):
        verilog_file = sources_list[i]
        additional_sources = analyse_file(verilog_file, script_files, verilog_files)
        sources_list += additional_sources
        verilog_files += additional_sources
        i = i + 1

    return sources_list


# Analyze a verilog file for module, header, and snippet references.
# Args:
#   file_path (str): Path to the verilog file.
#   script_files (list): List of script file paths.
#   verilog_files (list): List of verilog file paths.
# Returns:
#   list: List of additional source file paths.
def analyse_file(file_path, script_files, verilog_files):
    additional_sources = []

    with open(file_path, 'r') as file:
        content = file.read()
    
    module_pattern = r'(.*?)\(([\s\S]*?)\);'
    module_matches = re.findall(module_pattern, content)
    for module in module_matches:
        module_name = module[0].split()[0]
        if module_name is not "module":
            module_path = find_or_generate(f"{module_name}.v", script_files, verilog_files, module)
            additional_sources.append(module_path)

    header_pattern = r'`include "(.*?)\.vh"(.*)'
    header_matches = re.findall(header_pattern, content)
    for header in header_matches:
        header_name = header[0].split()[0]
        header_path = find_filename_in_list(f"{header_name}.vh", script_files, verilog_files, header)
        additional_sources.append(header_path)

    snippet_pattern = r'`include "(.*?)\.vs"(.*)'
    snippet_matches = re.findall(snippet_pattern, content)
    for snippet in snippet_matches:
        snippet_name = snippet[0].split()[0]
        snippet_path = find_filename_in_list(f"{snippet_name}.vs", script_files, verilog_files, snippet)
        additional_sources.append(snippet_path)

    return additional_sources


# Find or generate a file based on given conditions.
# Args:
#   file_name (str): Name of the file to find or generate.
#   script_files (list): List of script file paths.
#   verilog_files (list): List of verilog file paths.
#   match: Matched object from module pattern.
# Returns:
#   str: Path to the found or generated file.
def find_or_generate(file_name, script_files, verilog_files, match):
    file_path = find_filename_in_list(file_name, verilog_files)
    
    if file_path is None:
        arguments_list = []
        if file_name.endswith(".vs"):
            arguments_list = match[1].split()
        script_path, script_arg = find_most_common_prefix(file_name, script_files)
        if script_path is None:
            print_coloured(WARNING, f"Could not find or generate {file_name} under the current directory.")
        else:
            script_arguments = ['python', script_path, script_arg] + arguments_list
            subprocess.run(script_arguments)
        file_path = f"{current_directory}/hardware/generated/{file_name}"
        shutil.move(file_name, file_path)
    else:
        print_coloured(INFO, f"File {file_name} was not generated since it already exists under the current directory..")

    return file_path


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


# Builds the Verilog files by substituting included .vs files and writes them to the build directory.
# Args:
#   sources_list (list): List of Verilog files to build.
def verilog_build(sources_list):
    for verilog_file in sources_list:
        if not verilog_file.endswith(".vs"):
            verilog_content = ""
            verilog_content = substitute_vs_file(verilog_file, sources_list)
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
def substitute_vs_file(source_file, sources_list):
    new_content = ""
    with open(source_file, 'r') as file:
        for line in file:
            match = re.search(r'`include "(.*?)\.vs"(.*)', line)
            if match:
                vs_file = match.group(1) + ".vs"
                vs_file_path = find_filename_in_list(vs_file, sources_list)
                new_content += substitute_vs_file(vs_file_path, sources_list)
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
        print_coloured(OK, f"Directory '{path}' created successfully.")
    except OSError as e:
        print_coloured(WARNING, f"Failed to create directory: {e}")


# Check if this script is called directly
if __name__ == "__main__":
    current_directory = os.getcwd()
    if len(sys.argv)<2 or sys.argv[1] == "--help":
        help_build()
    elif sys.argv[1] == "--clean":
        clean_build()
    else:
        script_files, verilog_files = find_verilog_and_scripts(current_directory)
        sources_list = verilog_fetch(verilog_files, script_files)
        verilog_build(sources_list)

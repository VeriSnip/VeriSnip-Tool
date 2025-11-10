#!/usr/bin/env python3
"""VeriSnip (VS) is a project designed to bring the power of Verilog scripting to the open-source hardware community. This tool simplifies the generation of Verilog modules or snippets by seamlessly integrating with other programs. The generated files can be easily included in any Verilog project."""

import os
import re
import shutil
import subprocess
import sys

from .vs_colours import INFO, OK, WARNING, ERROR, DEBUG, vs_print

class VsBuilder:
    def __init__(self, main_module, testbench, board_modules, parameters, include_directories):
        self.cwd = os.getcwd()
        self.main_module = main_module
        self.testbench = testbench
        self.board_modules = board_modules or []
        self.parameters = parameters or {}
        self.include_directories = include_directories or []

        # discover files (implement or call your existing finder)
        self.script_files = []
        self.snippet_files = []
        self.verilog_files = []
        self._find_all_files()

        # resolved lists
        self.rtl_sources = []
        self.testbench_sources = []
        self.board_sources = {}


    def _find_all_files(self):
        vs_print(INFO, "Discovering HDL, snippet and script files...")
        excluded_files = {"LICENSE", ".gitignore", ".gitmodules", "Makefile", ".git"}
        verilog_extensions = {".v", ".vh", ".sv", ".svh"}
        script_extensions = {".py", ".sh", ".lua", ".scala", ".rb", ".pl", ".tcl", ""}

        script_files = []
        snippet_files = []
        verilog_files = []

        for search_dir in [self.cwd] + self.include_directories:
            for root, dirnames, filenames in os.walk(search_dir, topdown=True):
                # Prune irrelevant directories
                dirnames[:] = [d for d in dirnames if d not in {".git", "build", "generated", "__pycache__"}]
                for fname in filenames:
                    name, ext = os.path.splitext(fname)
                    if name in excluded_files:
                        continue
                    fpath = os.path.join(root, fname)
                    if ext in script_extensions:
                        script_files.append(fpath)
                    if ext in verilog_extensions:
                        verilog_files.append(fpath)
                    if ext == ".vs":
                        snippet_files.append(fpath)

        # Deduplicate and sort for stable output
        self.script_files = sorted(set(script_files))
        self.verilog_files = sorted(set(verilog_files))
        self.snippet_files = sorted(set(snippet_files))

        vs_print(DEBUG, f"Found ({len(self.verilog_files)}) verilog files:")
        for file_path in self.verilog_files:
            vs_print(DEBUG, f"\t{relative_path(file_path)}")
        vs_print(DEBUG, f"Found ({len(self.snippet_files)}) snippet files:")
        for file_path in self.snippet_files:
            vs_print(DEBUG, f"\t{relative_path(file_path)}")
        vs_print(DEBUG, f"Found ({len(self.script_files)}) script files:")
        for file_path in self.script_files:
            vs_print(DEBUG, f"\t{relative_path(file_path)}")

    def resolve_dependencies(self):
        """
        Resolve dependencies for main_module, testbench and boards.
        Should populate self.rtl_sources, self.testbench_sources and self.board_sources.
        """
        vs_print(INFO, f"Resolving dependencies for {self.main_module}...")
        # Example:
        # self.rtl_sources = build_dependency_tree(self.cwd, self.verilog_files, self.script_files, self.main_module, self.parameters)
        # if self.testbench: ...
        pass

    def build_sources(self):
        """
        Create build directories, copy files and substitute snippets.
        Reuse existing helper functions where possible.
        """
        vs_print(INFO, "Building sources into build/ and generated/ ...")
        # create_directory(f"{self.cwd}/build")
        # build_verilog_sources(self.rtl_sources, ..., build_dir=...)
        pass


def help_build():
    text = """
VeriSnip (VS) version 0.0.3
To show this help page: 
    Usage: vs_build --help

Create a build directory containing all the compiled hardware:
    Usage: vs_build <main_module> --TestBench <testbench_name> --Boards <board_modules> --quiet --debug
    <main_module> -> This is the name of the main RTL design.
    --TestBench=<testbench_name> (optional) -> by default vs_build looks for a TestBench file with the name <main_module>_tb.
    --Boards=<board_modules> (optional) -> by default vs_build looks for NO board RTL design top module. Multiple boards can be passed in a single argument (example, "Board1 Board2 Board3").
    --quiet (optional) -> suppresses INFO prints.
    --debug (optional) -> enables DEBUG prints.
    --inc_dir=<directory> (optional) -> define aditional directories where vs_build will look for Verilog files and scripts.
    <PARAMETER_NAME>=<verilog_value> (optional) -> user defined parameters to use in the Verilog HDL code generation.

Clean the contents generated by vs_build:
    Usage: vs_build --clean
    "--clean" removes the "build" and "generated" directories.

"""
    vs_print(INFO, text)


def clean_build(current_directory):
    """
    Cleans the build directory by removing it and its contents.

    Args:
        current_directory (str): The current directory of the build.
    """
    remove_directory(f"{current_directory}/build")
    remove_directory(f"{current_directory}/generated")


def remove_directory(directory_to_remove):
    """
    Removes a directory and its contents.

    Args:
        directory_to_remove (str): The directory to remove.
    """
    if not os.path.isdir(directory_to_remove):
        vs_print(DEBUG, f"Directory '{directory_to_remove}' does not exist; nothing to remove.")
        return
    try:
        shutil.rmtree(directory_to_remove)
        vs_print(
            OK, f"Removed directory '{directory_to_remove}' and its contents."
        )
    except OSError as e:
        vs_print(WARNING, f"Could not remove directory. {e}")


def create_directory(path):
    """
    Creates a directory at the specified path.

    Args:
        path (str): The path of the directory to be created.
    """
    try:
        os.makedirs(path, exist_ok=True)
        vs_print(INFO, f"Created directory '{path}'.")
    except OSError as e:
        vs_print(WARNING, f"Did not create directory: {e}")


def relative_path(path):
    """
    Convert an absolute path to a relative path based on the current working directory.

    Args:
        path (str): The absolute path to be converted.

    Returns:
        str: The relative path derived from the given absolute path.
    """
    path = os.path.relpath(path, os.getcwd())
    return path


def parse_arguments():
    """
    Parses arguments with which vs_build is called.

    Returns:
        tuple: A tuple containing the module_name (string), testbench_name (string), board_modules (list) and parameters (dict).

    This function parses command-line arguments provided when calling vs_build. It extracts information such as the
    module name, testbench name, supported board modules, and any parameters passed on the command line.
    """
    module_name = None
    testbench_name = None
    board_modules = []
    parameters = {}
    include_directories = []

    for i in range(1, len(sys.argv)):
        parameter = re.match(r'^(\w+)="?([^"]+)"?$', sys.argv[i])
        testbench = re.match(r'^--TestBench="?([^"]+)"?$', sys.argv[i])
        boards = re.match(r'^--Boards="?(.+?)"?$', sys.argv[i])
        include_directory = re.match(r'^--inc_dir="?(.+?)"?$', sys.argv[i])
        if testbench:
            testbench_name = testbench.group(1)
            # Reject empty/whitespace-only values and optionally prefix later if it starts with "_"
            if re.match(r"^\s*$", testbench_name):
                vs_print(ERROR, "Empty value after --TestBench=")
                help_build()
                exit(1)
        elif boards:
            Boards = boards.group(1).split()
            Board_pattern = r"^[\w]+$"
            for Board in Boards:
                if re.match(Board_pattern, Board):
                    board_modules.append(Board)  # Prefix will be applied after parsing if needed
                else:
                    vs_print(ERROR, f"Invalid Board name {Board}")
                    help_build()
                    exit(1)
        elif include_directory:
            directories = include_directory.group(1).split()
            directory_pattern = r"^[\w/.-]+$"
            for directory in directories:
                if re.match(directory_pattern, directory):
                    include_directories.append(directory)
                else:
                    vs_print(ERROR, f"Invalid directory name {directory}")
                    help_build()
                    exit(1)
        elif parameter:
            name = parameter.group(1)
            value = parameter.group(2)
            
            # Validate if it's a valid Verilog number format or integer
            verilog_pattern = r"^\d+('[bBdDhH][0-9a-fA-F_]+)$"
            integer_pattern = r"^\d+$"
            
            if re.match(verilog_pattern, value) or re.match(integer_pattern, value):
                parameters[name] = value
                vs_print(DEBUG, f"Parsed parameter {name} = {value}")
            else:
                vs_print(WARNING, f"Invalid parameter value format: {sys.argv[i]}")
            continue
        elif not sys.argv[i].startswith("--"):
            module_name = sys.argv[i]
            testbench_name = f"{sys.argv[i]}_tb"
    
    # Post-processing: apply "_" prefix expansion now that module_name is known
    if testbench_name and testbench_name.startswith("_") and module_name:
        testbench_name = f"{module_name}{testbench_name}"
    if module_name:
        board_modules = [
            (f"{module_name}{b}" if b.startswith("_") else b)
            for b in board_modules
        ]
          
    return module_name, testbench_name, board_modules, parameters, include_directories


def main():
    """
    Main function to handle the vs_build script execution.
    It processes command-line arguments, cleans the build directory if requested,
    and builds the RTL, TestBench, and board modules as specified.
    """
    current_directory = os.getcwd()
    if len(sys.argv) < 2 or sys.argv[1] == "--help":
        help_build()        
    else:
        if "--clean" in sys.argv:
            clean_build(current_directory)
        main_module, testbench, board_modules, parameters, include_directories = parse_arguments()
        if main_module != None:
            builder = VsBuilder(main_module, testbench, board_modules, parameters, include_directories)
            builder.resolve_dependencies()  # Resolve and generate any missing HDL/snippet files; populate source lists.
            builder.build_sources()         # Copy sources into build/, performing snippet substitutions.
            vs_print(OK, f"Created {main_module} project build directory.")
        else:
            vs_print(ERROR, f"Undefined main module!")
            exit(1)


# Check if this script is called directly
if __name__ == "__main__":
    main()

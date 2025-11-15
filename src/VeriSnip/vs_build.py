#!/usr/bin/env python3
"""VeriSnip (VS) is a project designed to bring the power of Verilog scripting to the open-source hardware community. This tool simplifies the generation of Verilog modules or snippets by seamlessly integrating with other programs. The generated files can be easily included in any Verilog project."""

import os
import re
import shutil
import subprocess
import sys

from .vs_colours import INFO, OK, WARNING, ERROR, DEBUG, vs_print

class VsBuilder:
    # TO DO: use these in the code
    _RE_MOD_INST = re.compile(r"\n\s*?(\w+?)\s+?(?:#\([\s\S]*?\))?\s*?(\w+?)\s*?\(\s*?(\.\w+?\s*?\([\s\S]*?)\);")
    _RE_INC = re.compile(r'\n\s*?`include\s+?"(.*?)"(?!\s*?/\*)(.*)')
    _RE_INC_BLOCK = re.compile(r'\n\s*?`include\s+?"(.*?)"\s*?/\*([\s\S]*?)\*/')
    _RE_PARAM_DEF = re.compile(r'^\s*parameter\s+(?:\w+\s+)?(\w+)\s*=\s*([^,;\n)]+)', re.MULTILINE)
    _RE_PARAM_PAIR = re.compile(r'\.(\w+)\s*\(\s*([^)]+?)\s*\)')
    _RE_PARAM_BLOCK_IN_INST = re.compile(r'\n\s*?\w+?\s+?#\(([\s\S]*?)\)\s*?\w+?\s*?\(')

    class VsSource:
        def __init__(self, name):
            self.name = name
            self.directory = ""
            self.comment = ""

        def locate_src(self, src_list):
            # TO DO: is there a better way of doing this?
            self.directory = locate_file_in_list(self.name, src_list)

        # TO DO: revise function
        def generate(self, parameters, script_files):
            script_directory, file_suffix = self._find_script(script_files)
            comment_arg = self.comment
            # Look for parameters name in comment_arg and replace by their value
            if parameters and self.comment:
# TO DO: Run subprocess with different comment_arg curresponding to the different parameter pairs.
#        If there is any parameters to replace, each generated file should be copied to the generated directry
#        and renamed to f"{self.name}_{i}". We should generate a vs file with f"{self.name}".
#        In this file we would write `generate begin if(<verify parameter pairs>) `include "{self.name}_{i}"
#        else $display("Unsuported parameters").
                for name, value in parameters.items():
                    comment_arg = re.sub("{"+name+"}", value[0], comment_arg)

            if script_directory:
                script_arguments = [
                    script_directory,
                    file_suffix,
                    comment_arg,
                ] + sys.argv[1:]
                subprocess.run(script_arguments)
                
            generated_files = move_generated_files()
            for file in generated_files:
                basename = os.path.basename(file)
                if basename == self.name or basename == self.name+".v" or basename == self.name+"sv":
                    self.directory = file
            if generated_files == []:
                vs_print(WARNING, f"{self.name} generated no Verilog or VeriSnip files.")

            return generated_files

        # TO DO: revise function
        def _find_script(self, script_files):
            input_words = self.name.split("_")
            similar_word_counter = 0
            most_similar_file = ""
            file_suffix = ""
            for file_path in script_files:
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                tmp_counter = 0
                tmp_string = ""
                for word in input_words:
                    tmp_string = tmp_string + word
                    tmp_counter = tmp_counter + 1
                    if file_name == tmp_string:
                        if tmp_counter > similar_word_counter:
                            similar_word_counter = tmp_counter
                            most_similar_file = file_path
                            file_suffix = "_".join(input_words[tmp_counter:])
                    tmp_string = tmp_string + "_"
            if most_similar_file == "":
                vs_print(WARNING, f'Could not locate any matching script to generate "{self.name}".')
            return most_similar_file, file_suffix

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

    def resolve_sources(self):
        """
        Build source trees for RTL, TestBench and Boards.
        - Generates missing HDL via scripts into generated/
        - Populates: self.rtl_sources, self.testbench_sources, self.board_sources
        """
        vs_print(INFO, f"Resolving sources for {self.main_module}...")
        generated_dir = os.path.join(self.cwd, "generated")
        create_directory(generated_dir)

        # Build RTL
        self.rtl_sources = self._resolve_sources_tree(self.main_module)

        # Build TestBench (excluding RTL duplicates)
        # TO DO: is this hack acceptable?
        if locate_file_in_list(self.testbench, self.verilog_files) != "":
            tb = self._resolve_sources_tree(self.testbench)
            self.testbench_sources = [f for f in tb if f not in self.rtl_sources]

        # Build Boards (each excluding RTL duplicates)
        self.board_sources = {}
        for board in self.board_modules:
            srcs = self._resolve_sources_tree(board)
            self.board_sources[board] = [f for f in srcs if f not in self.rtl_sources]

        # Debug print to verify resolved sources
        vs_print(DEBUG, f"RTL sources ({len(self.rtl_sources)}):")
        for src in self.rtl_sources:
            vs_print(DEBUG, f"\t{relative_path(src)}")

        if self.testbench:
            vs_print(DEBUG, f"TestBench sources ({len(self.testbench_sources)}):")
            for src in self.testbench_sources:
                vs_print(DEBUG, f"\t{relative_path(src)}")

        for board in self.board_modules:
            vs_print(DEBUG, f"Board '{board}' sources ({len(self.board_sources[board])}):")
            for src in self.board_sources[board]:
                vs_print(DEBUG, f"\t{relative_path(src)}")

    # ---------- source resolution helpers ----------

    # TO DO: revise passing only directories
    def _resolve_sources_tree(self, top_module):
        """
        Resolve all transitive sources for a given top module.
        """
        sources = [self.VsSource(top_module)]
        i = 0
        while i < len(sources):
            self._resolve_source(sources[i])
            sources += self._analyse_file(sources[i])
            i+=1
        
        source_directories = []
        for source in sources:
            source_directories.append(source.directory)

        return sorted(set(source_directories))
    
    def _resolve_source(self, source_file):
        file_list = self.snippet_files + self.verilog_files
        source_file.locate_src(file_list)
        if source_file.directory is "":
            generated_files = source_file.generate(self.parameters, self.script_files)
            for file in generated_files:
                if file.endswith(".vs"):
                    self.snippet_files.append(file)
                else:
                    self.verilog_files.append(file)
        return

    # TO DO: revise function and use re.compile defined above
    def _analyse_file(self, source_file):
        if not source_file.directory:
            vs_print(ERROR, f"{source_file.name} does not exist to analyse!")
            exit(1)
        with open(source_file.directory, "r") as f:
            content = f.read()

        filename = os.path.basename(source_file.directory)
        # TO DO: look for aditional parameter definitions
        param_def_pattern = r'^\s*parameter\s+(?:\w+\s+)?(\w+)\s*=\s*(.[^\s,\n)]+)'
        for match in re.finditer(param_def_pattern, content, re.MULTILINE):
            name = match.group(1)
            value = match.group(2).strip()
            if name in self.parameters:
                if value not in self.parameters[name]:
                    self.parameters[name].append(value)
            else:
                self.parameters[name] = [value]
        
        # Find parameter instantiations in module instances
        param_inst_pattern = r'\.(\w+)\s*\(\s*([^)]+?)\s*\)'
        module_inst_with_params = r'\n\s*?\w+?\s+?#\(([\s\S]*?)\)\s*?\w+?\s*?\('
        for inst_match in re.finditer(module_inst_with_params, content):
            param_block = inst_match.group(1)
            # Extract individual parameter assignments
            for param_match in re.finditer(param_inst_pattern, param_block):
                name = param_match.group(1)
                value = param_match.group(2).strip()
                # Check if value references another parameter
                if value in self.parameters:
                    # Replace with the actual parameter value
                    if name in self.parameters:
                        if value not in self.parameters[name]:
                            self.parameters[name] = list(set(self.parameters[value]+self.parameters[name]))
                    else:
                        self.parameters[name] = self.parameters[value]
                elif re.match(r'^[A-Z_][A-Z0-9_]*$', value) and value not in self.parameters:
                    # If it looks like a parameter name but isn't defined, throw an error
                    vs_print(ERROR, f"Parameter {value} used in instantiation in {filename} is not defined in parameters dictionary")
                    exit(1)
                    # Add to parameters if not already present
                    if name in self.parameters:
                        if value not in self.parameters[name]:
                            self.parameters[name].append(value)
                    else:
                        self.parameters[name] = [value]


        # TO DO: look for VeriSnip depedencies
        file_dependencies = []
        non_generated_file_dependencies = []
        includePattern = r'\n\s*?`include\s+?"(.*?)"(?!\s*?/\*)(.*)'
        multiCommentIncludePattern = r'\n\s*?`include\s+?"(.*?)"\s*?/\*([\s\S]*?)\*/'
        
        for pattern in [
            includePattern,
            multiCommentIncludePattern,
        ]:
            matches = re.finditer(pattern, content)
            for item in matches:
                new_file = self.VsSource(item.group(1))
                comment_arg = item.group(2).strip()
                if "VS_NO_GENERATE" in comment_arg:
                    non_generated_file_dependencies.append(new_file)
                else:
                    new_file.comment = comment_arg
                    file_dependencies.append(new_file)

        # TO DO: look for instantiated Verilog files and passed parameters
        # TO DO: verify regex expression
        moduleInstantiationPattern = r"\n\s*(\w+)\s+(?:#\([.\w\s,()]*?\))?\s*\w+?\s*?[(]+[.\w\s,()]+?[)]+;"
        matches = re.finditer(moduleInstantiationPattern, content)
        for item in matches:
            new_file = self.VsSource(item.group(1))
            file_dependencies.append(new_file)

        return file_dependencies + non_generated_file_dependencies
    
    # -----------------------------------------------

    def build_sources(self):
        """
        Create build directories, copy files and substitute snippets.
        Reuse existing helper functions where possible.
        """
        vs_print(INFO, "Populating build/!")
        build_dir = f"{self.cwd}/build"
        create_directory(build_dir)
        build_verilog_sources(self.rtl_sources, build_dir+"/RTL")
        build_verilog_sources(self.testbench_sources, build_dir+"/TestBench")
        for board in self.board_modules:
            build_verilog_sources(self.board_sources[board], build_dir+"/"+board)
        pass


def help_build():
    text = """
VeriSnip (VS) version 0.0.4
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


def move_generated_files():
    supported_extensions = [".v", ".vh", ".sv", ".svh", ".vs"]
    new_files = []
    cwd = os.getcwd()
    generated_dir = os.path.join(cwd, "generated")

    for filename in os.listdir(cwd):
        _, extension = os.path.splitext(filename)
        file_dst_path = os.path.join(generated_dir, filename)
        file_src_path = os.path.join(cwd, filename)
        if extension in supported_extensions:
            shutil.move(file_src_path, file_dst_path)
            new_files.append(file_dst_path)

    return new_files


def locate_file_in_list(filename, files_list):
    found_files = ""
    for file in files_list:
        # TO DO: is this hack acceptable
        basename = os.path.basename(file)
        if basename == filename or basename == filename+".v" or basename == filename+".sv":
            if found_files != "":
                vs_print(
                    WARNING,
                    f"Found more than one directory with file {filename}.\n  {file}",
                )
            found_files = file
    return found_files


def build_verilog_sources(sources, build_dir):
    create_directory(build_dir)
    for verilog_file in sources:
        if not verilog_file.endswith(".vs"):
            verilog_content = ""
            verilog_content = substitute_vs_file(verilog_file, sources)
            file_name = os.path.basename(verilog_file)
            destination_path = f"{build_dir}/{file_name}"

            # Check if file exists and compare contents
            if os.path.exists(destination_path):
                with open(destination_path, "r") as existing_file:
                    existing_content = existing_file.read()
                if existing_content == verilog_content:
                    vs_print(DEBUG, f"File '{file_name}' unchanged, skipping write.")
                    continue
            with open(f"{build_dir}/{file_name}", "w") as file:
                file.write(verilog_content)


def substitute_vs_file(source_file, sources_list):
    """
    Recursively substitutes included .vs files in the source file content.

    Args:
        source_file (str): The source file containing potential `include directives.
        sources_list (list): List of source file paths.

    Returns:
        str: The new content with included .vs files substituted.
    """
    new_content = ""
    on_comment = False

    with open(source_file, "r") as file:
        for line in file:
            if not on_comment:
                filename_match = re.findall(r'^\s*?`include\s+?"(.+?)\.vs"', line)
                if filename_match:
                    vs_file = filename_match[0] + ".vs"
                    vs_file_path = locate_file_in_list(vs_file, sources_list)

                    if vs_file_path:
                        new_content += substitute_vs_file(vs_file_path, sources_list)
                    else:
                        warning_text = f"File {vs_file} does not exist to substitute."
                        vs_print(WARNING, warning_text)
                        new_content += f"  // {warning_text}\n"
                    if "/*" in line:
                        on_comment = True
                else:
                    new_content += line
            else:
                if "*/" in line:
                    on_comment = False

    return new_content


# TO DO: use arg_parse
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
                if name in parameters:
                    parameters[name].append(value)
                else:
                    parameters[name] = [value]
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
            builder.resolve_sources()  # Resolve and generate any missing HDL/snippet files; populate source lists.
            builder.build_sources()    # Copy sources into build/, performing snippet substitutions.
            vs_print(OK, f"Created {main_module} project build directory.")
        else:
            vs_print(ERROR, f"Undefined main module!")
            exit(1)


# Check if this script is called directly
if __name__ == "__main__":
    main()

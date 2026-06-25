#!/usr/bin/env python3
"""VeriSnip (VS) is a project designed to bring the power of Verilog scripting to the open-source hardware community. This tool simplifies the generation of Verilog modules or snippets by seamlessly integrating with other programs. The generated files can be easily included in any Verilog project."""

import os
import re
import shutil
import subprocess
import sys
import argparse
from typing import Any

from .vs_colours import INFO, OK, WARNING, ERROR, DEBUG, CRITICAL, vs_print

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

            if script_directory != "":
                try:
                    script_arguments = [
                        script_directory,
                        file_suffix,
                        comment_arg,
                    ] + sys.argv[1:]
                    subprocess.run(script_arguments, check=True)
                except subprocess.CalledProcessError as err:
                    vs_print(ERROR, f"{script_directory} failed: \n{err}")
                    sys.exit(1)
                except OSError as err:
                    vs_print(ERROR, f"Failed to execute {script_directory}: \n{err}")
                    sys.exit(1)
            else:
                vs_print(CRITICAL, f"Failed to generate '{self.name}': no script found.")
                return []
                
            generated_files = move_generated_files()
            for file in generated_files:
                basename = os.path.basename(file)
                if basename == self.name or basename == self.name+".v" or basename == self.name+"sv":
                    self.directory = file

            if generated_files == []:
                vs_print(WARNING, f"'{self.name}': generated no Verilog or VeriSnip files.")
            else:
                vs_print(DEBUG, f"'{os.path.basename(script_directory)}': generated files: {[os.path.basename(file) for file in generated_files]}")

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
                dirnames[:] = [d for d in dirnames if d not in {".git", "build", "generated", "__pycache__", ".venv"}]
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
        self.script_files = sorted(set[Any](script_files))
        self.verilog_files = sorted(set[Any](verilog_files))
        self.snippet_files = sorted(set[Any](snippet_files))

        vs_print(DEBUG, f"Found ({len(self.verilog_files)}) verilog files:")
        for file_path in self.verilog_files:
            vs_print(DEBUG, f"\t{relative_path(file_path)}")
        vs_print(DEBUG, f"Found ({len(self.snippet_files)}) snippet files:")
        for file_path in self.snippet_files:
            vs_print(DEBUG, f"\t{relative_path(file_path)}")
        vs_print(DEBUG, f"Found ({len(self.script_files)}) script files:")
        for file_path in self.script_files:
            vs_print(DEBUG, f"\t{relative_path(file_path)}")

    def resolve_sources(self) -> None:
        """
        This function builds the source lists needed for the RTL top module, testbench, and board wrappers.
        Each list contains the [System]Verilog and VeriSnip files reachable from its top module. Sources may already exist in the project or be generated from scripts when first referenced.
        """
        vs_print(INFO, f"Resolving sources for {self.main_module}...")
        generated_dir = os.path.join(self.cwd, "generated")
        create_directory(generated_dir)

        # Build RTL
        self.rtl_sources = self._collect_dependency_tree(self.main_module)

        # Build TestBench (excluding RTL duplicates)
        # TO DO: is this hack acceptable?
        if locate_file_in_list(self.testbench, self.verilog_files) != "":
            tb = self._collect_dependency_tree(self.testbench)
            self.testbench_sources = [f for f in tb if f not in self.rtl_sources]

        # Build Boards (each excluding RTL duplicates)
        self.board_sources = {}
        for board in self.board_modules:
            srcs = self._collect_dependency_tree(board)
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
    def _collect_dependency_tree(self, top_module: str) -> list[str]:
        """
        This function starts from a top module name, walks all discovered dependencies and returns the unique source file paths required to build the top module.
        Each referenced source is first located or generated, then scanned for further includes, module instantiations, and parameter references.
        """
        pending = [self.VsSource(top_module)]
        deferred = {}
        scanned = set[Any]()
        sources_directories = set[Any]()

        while pending:
            source = pending.pop(0)
            status = self._locate_or_generate_source(source)
            if status:
                if source.name in scanned:
                    continue
                scanned.add(source.name)
                sources_directories.add(source.directory)
                pending.extend(self._scan_source_dependencies(source))
                if not pending:
                    vs_print(DEBUG, f"Retrying deferred sources: {list[Any](deferred.keys())}")
                    pending.extend(self._retry_deferred_sources(deferred))
            else:
                deferred[source.name] = source
        
        if deferred:
            vs_print(WARNING, f"The following sources could not be located or generated: {list[Any](deferred.keys())}")
        
        return sorted(sources_directories)
    
    def _retry_deferred_sources(self, deferred: dict[str, VsSource]) -> list[VsSource]:
        """
        This function retries to locate the sources that were deferred.
        """
        resolved = list[self.VsSource]()
        file_list = self.snippet_files + self.verilog_files
        for name, source in list[Any](deferred.items()):
            source.locate_src(file_list)
            if source.directory:
                del deferred[name]
                resolved.append(source)
        return resolved
    
    def _locate_or_generate_source(self, source_file: VsSource) -> bool:
        """
        This function locates a given source in the known project files, or generates it from a matching script if it is missing. If the generation is successful, the generated files are added to the snippet_files and verilog_files source lists. If the generation is not successful, the function returns False.
        """
        file_list = self.snippet_files + self.verilog_files
        source_file.locate_src(file_list)
        
        if source_file.directory == "":
            vs_print(DEBUG, f"'{source_file.name}': missing from project sources. Trying to generate it...")
            if "VS_NO_GENERATE" in source_file.comment:
                vs_print(DEBUG, f"'{source_file.name}': VS_NO_GENERATE found in comment. Skipping generation.")
                return False
            else:
                generated_files = source_file.generate(self.parameters, self.script_files)
                if generated_files == []:
                    return False
                for file in generated_files:
                    if file.endswith(".vs"):
                        self.snippet_files.append(file)
                    else:
                        self.verilog_files.append(file)
        else:
            vs_print(DEBUG, f"'{source_file.name}': found in project sources.")
        return True

    # TO DO: revise function and use re.compile defined above
    def _scan_source_dependencies(self, source_file: VsSource) -> list[VsSource]:
        """
        This function scans a resolved source file and returns the sources it depends on. These dependencies can be either [System]Verilog or VeriSnip files. They can be found from `include` directives and module instantiations.
        The function also updates known parameter values from parameter declarations and parameterized module instantiations.
        """
        if not source_file.directory:
            vs_print(
                ERROR,
                f"Cannot resolve '{source_file.name}': missing from project sources and no "
                f"generator produced it. Check include paths, module names, and generator scripts.",
            )
            sys.exit(1)
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
                            self.parameters[name] = list[Any](set[Any](self.parameters[value]+self.parameters[name]))
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
        includePattern = r'\n\s*?`include\s+?"(.*?)"(?!\s*?/\*)(.*)'
        multiCommentIncludePattern = r'\n\s*?`include\s+?"(.*?)"\s*?/\*([\s\S]*?)\*/'
        
        for pattern in [
            includePattern,
            multiCommentIncludePattern,
        ]:
            matches = re.finditer(pattern, content)
            for item in matches:
                new_file = self.VsSource(item.group(1))
                new_file.comment = item.group(2).strip()
                file_dependencies.append(new_file)

        # TO DO: look for instantiated Verilog files and passed parameters
        # TO DO: verify regex expression
        moduleInstantiationPattern = r"\n\s*(\w+)\s+(?:#\([.\w\s,()]*?\))?\s*\w+?\s*?[(]+[.\w\s,()]+?[)]+;"
        matches = re.finditer(moduleInstantiationPattern, content)
        for item in matches:
            new_file = self.VsSource(item.group(1))
            file_dependencies.append(new_file)

        return file_dependencies
    
    # -----------------------------------------------

    def build_sources(self) -> None:
        """
        Create build directories, copy files and substitute snippets.
        Reuse existing helper functions where possible.
        """
        vs_print(INFO, "Populating build!")
        build_dir = f"{self.cwd}/build"
        create_directory(build_dir)
        build_verilog_sources(self.rtl_sources, build_dir+"/RTL")
        build_verilog_sources(self.testbench_sources, build_dir+"/TestBench")
        for board in self.board_modules:
            build_verilog_sources(self.board_sources[board], build_dir+"/"+board)
        pass


def clean_build(current_directory: str) -> None:
    """
    Cleans the build and generated directories by removing them and their contents.
    """
    remove_directory(f"{current_directory}/build")
    remove_directory(f"{current_directory}/generated")


def remove_directory(directory_to_remove: str) -> None:
    """
    Removes a directory and its contents.
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


def create_directory(path: str) -> None:
    """
    Creates a directory at the specified path.
    """
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        vs_print(WARNING, f"Did not create directory: {e}")


def relative_path(path: str) -> str:
    """
    Convert an absolute path to a relative path based on the current working directory.
    """
    return os.path.relpath(path, start=os.getcwd())


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


def build_verilog_sources(sources: list[str], build_dir: str) -> None:
    """
    Builds Verilog sources from a list of source files and a build directory.
    """
    create_directory(build_dir)
    verilog_files = [file for file in sources if not file.endswith(".vs")]
    verisnip_files = [file for file in sources if file.endswith(".vs")]
    for verilog_file in verilog_files:
        verilog_content = ""
        verilog_content = substitute_vs_file(verilog_file, verisnip_files)
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


def substitute_vs_file(source_file: str, sources_list: list[str]) -> str:
    """
    Recursively substitutes included .vs files in the source file content.
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


def build_parser():
    description = (
        "VeriSnip (VS) version 0.0.4\n"
        "Create a build directory containing all the compiled hardware."
    )
    epilog = (
        "Examples:\n"
        "  vs_build top\n"
        "  vs_build top --TestBench top_tb --Boards \"Board1 Board2\"\n"
        "  vs_build top --inc_dir \"./rtl ../shared\" WIDTH=8\n"
        "  vs_build top --pre-build scripts/setup.sh --post-build scripts/cleanup.sh\n"
        "  vs_build --clean\n\n"
        "Notes:\n"
        "  1. --TestBench defaults to <main_module>_tb.\n"
        "  2. --Boards accepts a space-separated string.\n"
        "  3. --inc_dir accepts a space-separated string.\n"
        "  4. Additional parameters use NAME=VALUE (for example WIDTH=8, DEPTH=16'h00FF)."
    )
    parser = argparse.ArgumentParser(
        prog="vs_build",
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("module_name", nargs="?", help="Name of the main RTL top module.")
    parser.add_argument("--TestBench", dest="testbench_name", help="Testbench module name.")
    parser.add_argument("--Boards", dest="boards", default="", help="Space-separated list of board top modules.")
    parser.add_argument("--inc_dir", dest="include_dirs", default="", help="Space-separated list of include directories.")
    parser.add_argument("--pre-build", dest="pre_build", help="Path to script executed before build.")
    parser.add_argument("--post-build", dest="post_build", help="Path to script executed after a successful build.")
    parser.add_argument("--clean", action="store_true", dest="clean", help="Remove build and generated directories.")
    parser.add_argument("--quiet", action="store_true", help="Suppresses INFO prints.")
    parser.add_argument("--debug", action="store_true", help="Enables DEBUG prints.")
    return parser


def parse_arguments():
    """
    Parses arguments with which vs_build is called.

    Returns:
        tuple: A tuple containing the module_name (string), testbench_name (string), board_modules (list) and parameters (dict).

    This function parses command-line arguments provided when calling vs_build. It extracts information such as the
    module name, testbench name, supported board modules, and any parameters passed on the command line.
    """
    parser = build_parser()

    parsed_args, unknown_args = parser.parse_known_args()

    module_name = parsed_args.module_name
    testbench_name = parsed_args.testbench_name
    board_modules = []
    parameters = {}
    include_directories = []

    if testbench_name and re.match(r"^\s*$", testbench_name):
        vs_print(ERROR, "Empty value after --TestBench=")
        parser.print_help()
        exit(1)

    if module_name and testbench_name is None:
        testbench_name = f"{module_name}_tb"

    if parsed_args.boards:
        Boards = parsed_args.boards.split()
        Board_pattern = r"^[\w]+$"
        for Board in Boards:
            if re.match(Board_pattern, Board):
                board_modules.append(Board)  # Prefix will be applied after parsing if needed
            else:
                vs_print(ERROR, f"Invalid Board name {Board}")
                parser.print_help()
                exit(1)

    if parsed_args.include_dirs:
        directories = parsed_args.include_dirs.split()
        directory_pattern = r"^[\w/.-]+$"
        for directory in directories:
            if re.match(directory_pattern, directory):
                include_directories.append(directory)
            else:
                vs_print(ERROR, f"Invalid directory name {directory}")
                parser.print_help()
                exit(1)

    for arg in unknown_args:
        parameter = re.match(r'^(\w+)="?([^"]+)"?$', arg)
        if arg.startswith("--"):
            vs_print(ERROR, f"Unknown argument {arg}")
            parser.print_help()
            exit(1)
        if parameter:
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
                vs_print(WARNING, f"Invalid parameter value format: {arg}")
        else:
            vs_print(WARNING, f"Ignoring unrecognized positional argument: {arg}")
    
    # Post-processing: apply "_" prefix expansion now that module_name is known
    if testbench_name and testbench_name.startswith("_") and module_name:
        testbench_name = f"{module_name}{testbench_name}"
    if module_name:
        board_modules = [
            (f"{module_name}{b}" if b.startswith("_") else b)
            for b in board_modules
        ]
          
    return (
        module_name,
        testbench_name,
        board_modules,
        parameters,
        include_directories,
        parsed_args.clean,
        parsed_args.pre_build,
        parsed_args.post_build,
    )


def run_script(path: str, stage: str) -> None:
    print(f"Running {stage} script...")
    subprocess.run([path], check=True)


def main():
    """
    Main function to handle the vs_build script execution.
    It processes command-line arguments, cleans the build directory if requested,
    and builds the RTL, TestBench, and board modules as specified.
    """
    current_directory = os.getcwd()
    if len(sys.argv) < 2:
        build_parser().print_help()
        return

    (
        main_module,
        testbench,
        board_modules,
        parameters,
        include_directories,
        clean,
        pre_build_script,
        post_build_script,
    ) = parse_arguments()

    if clean:
        clean_build(current_directory)

    if pre_build_script and not os.path.isfile(pre_build_script):
        vs_print(ERROR, f"Pre-build script does not exist: {pre_build_script}")
        sys.exit(1)
    if post_build_script and not os.path.isfile(post_build_script):
        vs_print(ERROR, f"Post-build script does not exist: {post_build_script}")
        sys.exit(1)

    current_stage = "build"
    try:
        if pre_build_script:
            current_stage = "pre-build"
            run_script(pre_build_script, current_stage)

        if main_module is not None:
            current_stage = "build"
            builder = VsBuilder(main_module, testbench, board_modules, parameters, include_directories)
            builder.resolve_sources()  # Resolve and generate any missing HDL/snippet files; populate source lists.
            builder.build_sources()    # Copy sources into build/, performing snippet substitutions.
            vs_print(OK, f"Created {main_module} project build directory.")
        else:
            if not clean:
                vs_print(ERROR, f"Undefined main module!")
            sys.exit(1)

        if post_build_script:
            current_stage = "post-build"
            run_script(post_build_script, current_stage)
    except subprocess.CalledProcessError as err:
        vs_print(ERROR, f"{current_stage} step failed with exit code {err.returncode}.")
        sys.exit(1)


# Check if this script is called directly
if __name__ == "__main__":
    main()

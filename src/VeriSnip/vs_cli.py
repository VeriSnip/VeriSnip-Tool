"""Command-line entry point for vs_build: argument parsing and top-level orchestration."""

import argparse
import glob
import os
import re
import subprocess
import sys

from .vs_build import VsBuilder, clean_build
from .vs_colours import INFO, OK, ERROR, DEBUG, vs_print


def build_parser():
    description = (
        "VeriSnip (VS) version 0.0.4\n"
        "Create a build directory containing all the compiled hardware."
    )
    epilog = (
        "Examples:\n"
        "  vs_build top\n"
        "  vs_build top --TestBench top_tb --Boards \"Board1 Board2\"\n"
        "  vs_build top --inc_dir \"./rtl ../shared\"\n"
        "  vs_build top --pre-build scripts/setup.sh --post-build scripts/cleanup.sh\n"
        "  vs_build top EXTRA_FLAG=1\n"
        "  vs_build --clean\n\n"
        "Notes:\n"
        "  1. --TestBench defaults to <main_module>_tb.\n"
        "  2. --Boards accepts a space-separated string.\n"
        "  3. --inc_dir accepts a space-separated string.\n"
        "  4. Extra positional arguments (for example EXTRA_FLAG=1) are forwarded\n"
        "     to generator scripts together with the rest of vs_build's argv.\n"
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
    parser.add_argument(
        "--pre-build",
        dest="pre_build",
        help="Path to script executed before build. Defaults to a pre_build.* file "
        "in the working directory, if one exists.",
    )
    parser.add_argument(
        "--post-build",
        dest="post_build",
        help="Path to script executed after a successful build. Defaults to a "
        "post_build.* file in the working directory, if one exists.",
    )
    parser.add_argument("--clean", action="store_true", dest="clean", help="Remove build and generated directories.")
    parser.add_argument("--quiet", action="store_true", help="Suppresses INFO, WARNING, NOTE, and DEBUG prints.")
    parser.add_argument("--debug", action="store_true", help="Enables DEBUG prints.")
    return parser


def parse_arguments():
    """
    Parses arguments with which vs_build is called.

    Returns:
        tuple: A tuple containing the module_name (string), testbench_name (string),
        board_modules (list), and include_directories (list).

    This function parses command-line arguments provided when calling vs_build. It extracts information such as the
    module name, testbench name, supported board modules, and include directories.
    """
    parser = build_parser()

    parsed_args, unknown_args = parser.parse_known_args()

    module_name = parsed_args.module_name
    testbench_name = parsed_args.testbench_name
    board_modules = []
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
        if arg.startswith("--"):
            vs_print(ERROR, f"Unknown argument {arg}")
            parser.print_help()
            exit(1)
        # Extra positionals are intentionally left in sys.argv so generator
        # scripts receive them when invoked from VsSource.generate().
        vs_print(DEBUG, f"Extra argument will be forwarded to generator scripts: {arg}")

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
        include_directories,
        parsed_args.clean,
        parsed_args.pre_build,
        parsed_args.post_build,
    )


def find_default_script(directory: str, stem: str) -> "str | None":
    """Return the path to a `<stem>.*` file in `directory`, if exactly one exists."""
    candidates = sorted(
        path for path in glob.glob(os.path.join(directory, f"{stem}.*"))
        if os.path.isfile(path)
    )
    if len(candidates) > 1:
        vs_print(ERROR, f"Multiple default {stem}.* scripts found: {', '.join(candidates)}")
        sys.exit(1)
    return candidates[0] if candidates else None


def run_script(path: str, stage: str) -> None:
    vs_print(INFO, f"Running {stage} script...")

    # 1. Check if the path is relative or absolute
    if os.path.isabs(path):
        script_path = path
    else:
        script_path = os.path.join(os.getcwd(), path)

    # 2. Check if the script exists
    if not os.path.exists(script_path):
        vs_print(ERROR, f"{stage} script not found at {script_path}")
        sys.exit(1)

    # 3. Run the script and catch errors
    try:
        subprocess.run([script_path], check=True)
    except subprocess.CalledProcessError as err:
        vs_print(ERROR, f"{stage} script failed with exit code {err.returncode}.")
        sys.exit(1)
    except OSError as err:
        vs_print(ERROR, f"Failed to execute {stage} script: {err}")
        sys.exit(1)

    return


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
        include_directories,
        clean,
        pre_build_script,
        post_build_script,
    ) = parse_arguments()

    if clean:
        clean_build(current_directory)

    if pre_build_script is None:
        pre_build_script = find_default_script(current_directory, "pre_build")
    if post_build_script is None:
        post_build_script = find_default_script(current_directory, "post_build")

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
            builder = VsBuilder(main_module, testbench, board_modules, include_directories)
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

"""This module provides color to the messages printed while using the VT-Tool."""

import sys
import os

# Based on ANSI escape code
OK_BLUE = "\033[94m"  # Blue
INFO = "\033[96mInfo"  # Cyan
OK = "\033[92mDone"  # Green
WARNING = "\033[93mWarning"  # Orange
ERROR = "\033[91mError"  # Red
DEBUG = "\033[95mDebug"  # Magenta
NORMAL = "\033[0m"  # White
BOLD = "\033[1m"
UNDERLINE = "\033[4m"

def vs_print(modifier, string):
    """This function prints the given string with the given text modifier.
    Args:
        modifier: The text modifier.
        string: The string to print."""
    script_name = os.path.basename(sys.argv[0])
    # Check conditions for printing based on arguments and modifier
    if modifier == DEBUG:
        if "--debug" in sys.argv:
            print(f"{modifier} ({script_name}): {string}{NORMAL}")
    elif modifier == INFO:
        if "--quiet" not in sys.argv:
            print(f"{modifier} ({script_name}): {string}{NORMAL}")
    else:
        print(f"{modifier} ({script_name}): {string}{NORMAL}")

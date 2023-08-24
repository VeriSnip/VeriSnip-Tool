import inspect
import os

# Based on ANSI escape code
OKBLUE = "\033[94m"  # Blue
INFO = f"\033[96mInfo"  # Cyan
OK = f"\033[92mDone"  # Green
WARNING = f"\033[93mWarning"  # Orange
ERROR = f"\033[91mError"  # Red
DEBUG = f"\033[95mDebug"  # Magenta
NORMAL = "\033[0m"  # White
BOLD = "\033[1m"
UNDERLINE = "\033[4m"


#  Prints the given string with the given text modifier.
#  Args:
#    modifier: The text modifier.
#    string: The string to print.
def print_coloured(modifier, string):
    frame = inspect.currentframe().f_back
    calling_script = inspect.getframeinfo(frame).filename
    script_name = os.path.basename(calling_script)
    print(f"{modifier} ({script_name}): {string}{NORMAL}")

HEADER = "\033[95m"
OKBLUE = "\033[94m"  # Blue
INFO = "\033[96mInfo: "  # Cyan
OK = "\033[92mDone: "  # Green
WARNING = "\033[93mWarning: "  # Orange
ERROR = "\033[91mError: "  # Red
NORMAL = "\033[0m"  # White
BOLD = "\033[1m"
UNDERLINE = "\033[4m"


#  Prints the given string with the given text modifier.
#  Args:
#    modifier: The text modifier.
#    string: The string to print.
def print_color(modifier, string):
    print(modifier+string+NORMAL)

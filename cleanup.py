#!/usr/bin/env python3
import argparse
import logging
import sys
import subprocess
import textwrap
from pathlib import Path

from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator, ValidationError


# Set default values
DEFAULT_DIRECTORY = Path.home()
TEMP_FILE = DEFAULT_DIRECTORY / f".{Path(sys.argv[0]).name}.log"

# Define color codes
RED = "\033[31m"
GREEN = "\033[32m"
WHITE = "\033[37m"
YELLOW = "\033[33m"
ORANGE = "\033[38;5;172m"
RESET = "\033[0m"

# Constants
TERM_WIDTH = 80
BOX_PADDING = 2


class YNValidator(Validator):
    def validate(self, document):
        text = document.text.lower()
        if text not in ["y", "n"]:
            raise ValidationError(message="Please enter y or n", cursor_position=len(document.text))


def prompt_yn(message):
    """
    Prompt the user for a yes/no answer.

    Args:
        message (str): The message to display to the user.

    Returns:
        bool: True if the user entered 'y', False if the user entered 'n'.
    """
    logger.debug("Prompting user for yes/no answer")
    while True:
        response = prompt(f"{message} (y/n): ", validator=YNValidator())
        if response.lower() == "y":
            return True
        elif response.lower() == "n":
            return False


def print_success(message):
    """
    Print a success message.

    Args:
        message (str): The success message to print.
    """
    logger.info(f"{GREEN}{message}{WHITE}")


def print_info(message):
    """
    Print an informational message.

    Args:
        message (str): The informational message to print.
    """
    message = message or "Error: No message passed"
    logger.info(f"{GREEN}{message}{WHITE}")


def print_warning(message):
    """
    Print a warning message.

    Args:
        message (str): The warning message to print.
    """
    message = message or "Error: No message passed"
    logger.warning(f"{RED}{message}{WHITE}")


def check_directory_arg(directory):
    """
    Check if the argument is a directory.

    Args:
        directory (Path): The directory to check.

    Returns:
        None
    """
    logger.debug(f"Checking if {directory} is a directory")
    global DEFAULT_DIRECTORY
    if not directory.is_dir():
        print_warning(f"{directory} is not a directory. Defaulting to {DEFAULT_DIRECTORY}")
        check_os_and_set_find()
    else:
        DEFAULT_DIRECTORY = directory
        check_os_and_set_find()


def draw_box(*message_lines):
    """
    Draw a box around a message.

    Args:
        *message_lines (str): The message lines to display in the box.

    Returns:
        None
    """
    logger.debug("Drawing message box")
    # Split message into multiple lines if it's longer than TERM_WIDTH - BOX_PADDING * 2
    new_message_lines = []
    for line in message_lines:
        if len(line) > TERM_WIDTH - BOX_PADDING * 2:
            new_message_lines.extend(textwrap.wrap(line, width=TERM_WIDTH - BOX_PADDING * 2))
        else:
            new_message_lines.append(line)

    # Draw the box
    logger.info(f"{ORANGE}┌{'─' * (TERM_WIDTH - 2)}┐\n{'│':<79}{'│'}")
    for i, line in enumerate(new_message_lines):
        # Calculate padding for each line
        line_length = len(line)
        left_padding = (TERM_WIDTH - BOX_PADDING * 2 - line_length) // 2
        right_padding = TERM_WIDTH - BOX_PADDING * 2 - left_padding - line_length

        # Draw the line
        logger.info(f"{'│':<}{YELLOW}{' ' * left_padding} {line} {' ' * right_padding}{ORANGE}{'│'}")
    logger.info(f"{'│':<79}{'│'}\n{'└'}{'─' * (TERM_WIDTH - 2)}{'┘'}{RESET}")


def check_os_and_set_find():
    """
    Check the operating system and set the find command accordingly.

    Returns:
        None
    """
    logger.debug("Performing sanity check")
    global agnostic_find
    if sys.platform.startswith("linux"):
        agnostic_find = ["find", str(DEFAULT_DIRECTORY), "-regextype", "posix-extended", "-regex"]
    elif sys.platform.startswith("freebsd") or sys.platform.startswith("darwin"):
        agnostic_find = ["find", "-E", str(DEFAULT_DIRECTORY), "-type", "f", "-regex"]

    if TEMP_FILE.is_file():
        try:
            TEMP_FILE.unlink()
            draw_box(f"removing {TEMP_FILE}")
        except Exception as e:
            logging.exception(f"Failed to remove {TEMP_FILE}: {e}")
            sys.exit(1)

def find_files():
    """
    Find files that match the regex and write to temporary file.

    Returns:
        None
    """
    logger.debug("Finding files")
    try:
        with TEMP_FILE.open("w") as f:
            agnostic_find.append(r".*\.(bak|swp|DS_Store|~)$")
            agnostic_find.append("-print")
            result = subprocess.run(agnostic_find, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            f.write(result.stdout)
    except Exception as e:
        logging.exception(f"Failed to find files: {e}")
        sys.exit(1)

def count_files():
    """
    Count the number of files to be removed.

    Returns:
        None
    """
    logger.debug("Counting files")
    try:
        with TEMP_FILE.open() as f:
            global num_files
            num_files = len(f.readlines())
    except Exception as e:
        logging.exception(f"Failed to count files: {e}")
        sys.exit(1)


def display_box():
    """
    Display message box with number of files to be removed.

    Returns:
        None
    """
    logger.debug("Displaying message box")
    try:
        with TEMP_FILE.open() as f:
            file_names = [line.strip() for line in f]
            if num_files > 0:
                message_lines = [f"{len(file_names)} files to be removed:"]
                for name in file_names:
                    message_lines.append(f"{name}")
                draw_box(*message_lines)
            else:
                print_info("No files found to remove.")
    except Exception as e:
        logging.exception(f"Failed to display message: {e}")
        sys.exit(1)


def remove_files():
    """
    Remove the files.

    Returns:
        None
    """
    logger.debug("Removing files")
    try:
        with TEMP_FILE.open() as f:
            for line in f:
                line = line.strip()
                print_warning(line)
                Path(line).unlink()
    except Exception as e:
        logging.exception(f"Failed to remove files: {e}")
        sys.exit(1)


def clean_up():
    """
    Clean up the temporary files.

    Returns:
        None
    """
    logger.debug("Cleaning up temporary files")
    if TEMP_FILE.is_file():
        try:
            TEMP_FILE.unlink()
        except Exception as e:
            logging.exception(f"Failed to remove {TEMP_FILE}: {e}")
            sys.exit(1)


# Parse command-line arguments
parser = argparse.ArgumentParser(description="Clean up backup files.")
parser.add_argument("directory", nargs="?", type=Path, default=DEFAULT_DIRECTORY, help="directory to clean up")
parser.add_argument("--debug", action="store_true", help="print debug information")
args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
else:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

check_directory_arg(args.directory)

find_files()
count_files()
display_box()

if num_files > 0:
    if prompt_yn("Are you sure you want to delete these files?"):
        remove_files()
        print_success("Cleanup complete.")
    else:
        print_info("Cleanup aborted.")

clean_up()

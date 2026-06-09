#!/usr/bin/env python3
"""Module for cleaning up temporary files and backup files."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit.validation import ValidationError, Validator

if TYPE_CHECKING:
    from prompt_toolkit.document import Document

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger: logging.Logger = logging.getLogger(__name__)

# Constants for UI
TERM_WIDTH: int = 80
BOX_PADDING: int = 2
TEMP_FILE: Path = Path("/tmp/cleanup_files.txt")  # noqa: S108
FIND_CMD: str = "/usr/bin/find"

# ANSI color codes
ORANGE: str = "\033[38;5;214m"
YELLOW: str = "\033[38;5;226m"
GREEN: str = "\033[38;5;46m"
RED: str = "\033[38;5;196m"
WHITE: str = "\033[38;5;231m"
RESET: str = "\033[0m"


class CleanupState:
    """Container for cleanup script global state."""

    def __init__(self) -> None:
        """Initialize state."""
        self.num_files: int = 0
        self.agnostic_find: list[str] = []


state = CleanupState()


class YNValidator(Validator):
    """Validator for yes/no input."""

    def validate(self, document: Document) -> None:
        """Validate that the input is 'y' or 'n'."""
        text = document.text.lower()
        if text not in ["y", "n"]:
            raise ValidationError(message="Please enter 'y' or 'n'")


def prompt_yn(message: str) -> bool:
    """Prompt the user for a yes/no answer.

    Args:
        message: The message to display to the user.

    Returns:
        True if the user entered 'y', False if the user entered 'n'.

    """
    logger.debug("Prompting user for yes/no answer")
    while True:
        choice = _get_user_choice(message)
        if choice is None:
            return False
        if choice == "y":
            return True
        if choice == "n":
            return False
    return False


def _get_user_choice(message: str) -> str | None:
    """Get choice from user with EOF handling."""
    try:
        return input(f"{message} (y/n): ").lower()
    except EOFError:
        return None


def print_success(message: str) -> None:
    """Print a success message in green.

    Args:
        message: The success message to print.

    """
    sys.stdout.write(f"{GREEN}{message}{WHITE}\n")


def print_info(message: str | None) -> None:
    """Print an informational message in green.

    Args:
        message: The informational message to print.

    """
    msg = message or "Error: No message passed"
    sys.stdout.write(f"{GREEN}{msg}{WHITE}\n")


def print_warning(message: str | None) -> None:
    """Print a warning message in red.

    Args:
        message: The warning message to print.

    """
    msg = message or "Error: No message passed"
    sys.stderr.write(f"{RED}{msg}{WHITE}\n")


def check_directory_arg(directory: Path) -> None:
    """Check if the argument is a valid directory.

    Args:
        directory: The directory path to check.

    """
    logger.debug("Checking if %s is a directory", directory)
    if not directory.is_dir():
        print_warning(f"Error: {directory} is not a directory")
        sys.exit(1)


def draw_box(*message_lines: str) -> None:
    """Draw a decorative box around a message.

    Args:
        *message_lines: The message lines to display in the box.

    """
    logger.debug("Drawing message box")
    new_message_lines: list[str] = []
    max_line_width = TERM_WIDTH - BOX_PADDING * 2 - 2

    for line in message_lines:
        if len(line) > max_line_width:
            _wrap_line(line, max_line_width, new_message_lines)
        else:
            new_message_lines.append(line)

    # Draw the box
    sys.stdout.write(f"{ORANGE}┌{'─' * (TERM_WIDTH - 2)}┐\n{'│':<79}{'│'}\n")
    for line in new_message_lines:
        line_length = len(line)
        left_padding = (TERM_WIDTH - BOX_PADDING * 2 - line_length) // 2
        right_padding = TERM_WIDTH - BOX_PADDING * 2 - left_padding - line_length
        sys.stdout.write(f"{'│':<}{YELLOW}{' ' * left_padding} {line} {' ' * right_padding}{ORANGE}{'│'}\n")
    sys.stdout.write(f"{'│':<79}{'│'}\n{'└'}{'─' * (TERM_WIDTH - 2)}{'┘'}{RESET}\n")


def _wrap_line(line: str, max_line_width: int, result_lines: list[str]) -> None:
    """Wrap a long line into multiple lines."""
    words = line.split()
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= max_line_width:
            current_line += word + " "
        else:
            result_lines.append(current_line.strip())
            current_line = word + " "
    result_lines.append(current_line.strip())


def check_os_and_set_find() -> None:
    """Check the operating system and set the find command accordingly."""
    logger.debug("Performing sanity check")
    if sys.platform == "darwin":
        state.agnostic_find = [FIND_CMD, "-E", ".", "-type", "f", "-regex"]
    else:
        state.agnostic_find = [FIND_CMD, ".", "-type", "f", "-regextype", "posix-egrep", "-regex"]


def find_files() -> None:
    """Find files matching the cleanup pattern and write to a temporary file."""
    logger.debug("Finding files")
    try:
        with TEMP_FILE.open("w") as f:
            cmd = [*state.agnostic_find, r".*\.(bak|swp|DS_Store|~)$", "-print"]
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            f.write(result.stdout)
    except OSError:
        logger.exception("Failed to find files")
        sys.exit(1)


def count_files() -> None:
    """Count the number of lines (files) in the temporary results file."""
    logger.debug("Counting files")
    try:
        with TEMP_FILE.open() as f:
            lines = f.readlines()
            state.num_files = len(lines)
    except OSError:
        logger.exception("Failed to count files")
        sys.exit(1)


def display_box() -> None:
    """Display the summary box with the count of files to be removed."""
    logger.debug("Displaying message box")
    draw_box(f"Found {state.num_files} files to be removed.")


def remove_files() -> None:
    """Iterate through the temporary file and remove each listed file."""
    logger.debug("Removing files")
    try:
        with TEMP_FILE.open() as f:
            for line in f:
                _remove_single_file(line.strip())
    except OSError:
        logger.exception("Failed to remove files")
        sys.exit(1)


def _remove_single_file(file_path_str: str) -> None:
    """Remove a single file if it exists."""
    file_path = Path(file_path_str)
    if file_path.is_file():
        file_path.unlink()


def clean_up() -> None:
    """Remove the temporary file used for storage."""
    logger.debug("Cleaning up temporary files")
    if TEMP_FILE.is_file():
        TEMP_FILE.unlink()


def main() -> None:
    """Execute the cleanup script logic."""
    check_os_and_set_find()
    find_files()
    count_files()
    display_box()

    if state.num_files > 0:
        if prompt_yn("Are you sure you want to delete these files?"):
            remove_files()
            print_success("Cleanup complete.")
        else:
            print_info("Cleanup aborted.")

    clean_up()


if __name__ == "__main__":
    main()

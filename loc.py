#!/usr/bin/env python
import os
import argparse
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich import box
from rich.style import Style
from typing import Optional, List, Tuple, Dict
import subprocess

console = Console()

# Supported file extensions for programming languages
SUPPORTED_EXTENSIONS: Dict[str, str] = {
    ".py": "Python",
    ".sh": "Shell",
    ".js": "JavaScript",
    ".html": "HTML",
    ".css": "CSS",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".ts": "TypeScript",
    ".kt": "Kotlin",
    ".sql": "SQL",
    ".xml": "XML",
    ".json": "JSON",
    ".yaml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".txt": "Text",
    ".conf": "Apache Config",
    ".vcl": "Varnish Config",
    ".tf": "Terraform",
    ".tfvars": "Terraform",
    ".yml": "Ansible",
}

# Shebang to language mapping
SHEBANG_MAPPING: Dict[str, str] = {
    "python": "Python",
    "bash": "Shell",
    "sh": "Shell",
    "ruby": "Ruby",
    "node": "JavaScript",
}

# File names to language mapping
FILENAME_MAPPING: Dict[str, str] = {
    "meson.build": "Meson Build",
    ".pylintrc": "Pylint Config",
    ".flake8": "Flake8 Config",
    ".eslintrc": "ESLint Config",
    ".prettierrc": "Prettier Config",
    "Makefile": "Makefile",
    "Dockerfile": "Dockerfile",
}

BINARY_EXTENSIONS = {
    ".gz",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".ico",
    ".tiff",
    ".webp",
    ".pdf",
    ".exe",
}

# Default directories to exclude
DEFAULT_EXCLUDED_DIRS = {
    "build",
    "__pycache__",
    "node_modules",
    "dist",
    ".git",
    ".svn",
    ".env",
    ".venv",
    ".so",
    "env",
    "venv",
}

# Create styles using the custom theme
header_style = Style.parse("bold #F6D365")
cell_styles = [
    Style.parse("#56949f"),
    Style.parse("#D190E8"),
    Style.parse("#f6c177"),
    Style.parse("#286983"),
]
border_style = Style.parse("#6e6a86")
footer_style = Style.parse("bold #eb6f92")
info_style = Style.parse("#A39E9B")
warning_style = Style.parse("bold #FFE58F")
error_style = Style.parse("bold #FA5D5D")


def detect_language(file_path: str) -> str:
    """Detect the programming language of a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            first_line = file.readline().strip()

            if first_line.startswith("<?xml"):
                return "XML"

            for line in file:
                for char in line:
                    if ord(char) < 32 and char not in ["\n", "\r", "\t"]:
                        return "Binary"

            return "Text"

    except FileNotFoundError:
        console.print(f"[{error_style}]File not found: {file_path}[/{error_style}]")
        return "Unknown"
    except UnicodeDecodeError:
        return "Binary"
    except Exception as e:
        console.print(
            f"[{error_style}]Error processing file {file_path}: {e}[/{error_style}]"
        )
        return "Unknown"


def is_binary_file(file_path: str) -> bool:
    """Check if a file is binary."""
    try:
        result = subprocess.run(
            ["file", "--mime", "-b", file_path], capture_output=True, text=True
        )
        return "binary" in result.stdout.lower()
    except Exception as e:
        console.print(
            f"[{error_style}]Error determining file type for {file_path}: {e}[/{error_style}]"
        )
        return False


def count_lines_and_size(
    start: str,
    exclude_filetypes: Optional[List[str]] = None,
    exclude_dirs: Optional[set] = None,
) -> Tuple[int, int, dict, dict]:
    """Count lines of code and size in a directory."""
    total_lines = 0
    total_size = 0
    file_counts = defaultdict(lambda: {"lines": 0, "size": 0, "language": "Unknown"})
    language_totals = defaultdict(lambda: {"lines": 0, "size": 0})

    exclude_dirs = exclude_dirs or DEFAULT_EXCLUDED_DIRS

    try:
        for root, dirs, files in os.walk(start):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                file_path = os.path.join(root, file)
                file_name = os.path.basename(file)
                file_ext = os.path.splitext(file)[1]

                if exclude_filetypes and file_ext in exclude_filetypes:
                    continue

                if is_binary_file(file_path):
                    continue

                try:
                    if not os.path.isfile(file_path) or not os.access(
                        file_path, os.R_OK
                    ):
                        continue

                    language = FILENAME_MAPPING.get(
                        file_name,
                        SUPPORTED_EXTENSIONS.get(file_ext, detect_language(file_path)),
                    )

                    with open(file_path, "r", encoding="utf-8") as f:
                        new_lines = sum(1 for _ in f)
                        file_size = os.path.getsize(file_path)
                        total_lines += new_lines
                        total_size += file_size
                        file_counts[file_path] = {
                            "lines": new_lines,
                            "size": file_size,
                            "language": language,
                        }
                        language_totals[language]["lines"] += new_lines
                        language_totals[language]["size"] += file_size
                except (UnicodeDecodeError, OSError) as e:
                    console.print(
                        f"[{error_style}]Error reading file {file_path}: {e}[/{error_style}]"
                    )

    except KeyboardInterrupt:
        console.print("[{error_style}]Operation cancelled by user.[/{error_style}]")

    return total_lines, total_size, file_counts, language_totals


def display_results(
    total_lines: int,
    total_size: int,
    file_counts: dict,
    language_totals: dict,
    start_directory: str,
) -> None:
    """Display results using Rich tables."""
    file_table = Table(
        title="[bold]Lines of Code, Size and File Type[/bold]", box=box.ROUNDED
    )
    file_table.pad_edge = False
    file_table.expand = False
    file_table.title_style = header_style
    file_table.border_style = border_style

    file_table.add_column("File", justify="left", style=cell_styles[0], no_wrap=True)
    file_table.add_column("Lines", justify="right", style=cell_styles[1])
    file_table.add_column("Size", justify="right", style=cell_styles[2])
    file_table.add_column("Language", justify="left", style=cell_styles[3])

    # Sort file_counts by file path alphabetically
    sorted_files = sorted(file_counts.items(), key=lambda item: item[0])

    for file, info in sorted_files:
        lines = info["lines"]
        size = info["size"]
        language = info["language"]

        if file.startswith(start_directory):
            file_display = "." + file[len(start_directory) :]
        else:
            file_display = file

        file_size_human_readable = _format_size(size)
        file_table.add_row(file_display, str(lines), file_size_human_readable, language)

    console.print(file_table)

    language_table = Table(
        title="[bold]Lines of Code Count and Size by Language[/bold]", box=box.ROUNDED
    )
    language_table.pad_edge = False
    language_table.expand = False
    language_table.title_style = header_style
    language_table.border_style = border_style

    language_table.add_column(
        "Language", justify="left", style=cell_styles[0], no_wrap=True
    )
    language_table.add_column("Total Lines", justify="right", style=cell_styles[1])
    language_table.add_column("Total Size", justify="right", style=cell_styles[2])

    for language, info in sorted(
        language_totals.items(), key=lambda item: item[1]["lines"], reverse=True
    ):
        lines = info["lines"]
        size = info["size"]

        size_human_readable = _format_size(size)
        language_table.add_row(language, str(lines), size_human_readable)

    console.print(language_table)
    console.print(
        f"\n[bold {warning_style}]Total Lines: {total_lines}, Total Size: {_format_size(total_size)}[/bold {warning_style}]"
    )

    # Additional Metrics
    total_files = len(file_counts)
    average_lines = total_lines / total_files if total_files > 0 else 0
    average_size = total_size / total_files if total_files > 0 else 0

    console.print(f"\n[bold {info_style}]Additional Metrics[/bold {info_style}]")
    console.print(f"Total Files: {total_files}")
    console.print(f"Average Lines per File: {average_lines:.2f}")

    # Calculate average size in human-readable format
    average_size_human_readable = _format_size(average_size)
    console.print(f"Average Size per File: {average_size_human_readable}")


def _format_size(size_in_bytes: float) -> str:
    """Format size in bytes into human-readable format."""
    if size_in_bytes == 0:
        return "0 bytes"

    # lets calculate the number of bytes into kilobytes, megabytes etc.
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0

    while size_in_bytes >= 1024 and unit_index < len(units) - 1:
        size_in_bytes /= 1024
        unit_index += 1

    return f"{size_in_bytes:.2f} {units[unit_index]}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count lines of code in a directory.")
    parser.add_argument(
        "directory",
        nargs="?",
        default=os.getcwd(),
        help="Directory path to count lines of code.",
    )
    parser.add_argument(
        "-e", "--exclude", nargs="*", help="File extensions to exclude."
    )
    parser.add_argument(
        "-d", "--exclude-dirs", nargs="*", help="Directories to exclude."
    )
    args = parser.parse_args()

    exclude_filetypes = args.exclude if args.exclude else []
    exclude_dirs = (
        set(args.exclude_dirs) if args.exclude_dirs else DEFAULT_EXCLUDED_DIRS
    )

    total_lines, total_size, file_counts, language_totals = count_lines_and_size(
        args.directory, exclude_filetypes, exclude_dirs
    )
    display_results(
        total_lines,
        total_size,
        file_counts,
        language_totals,
        os.path.abspath(args.directory),
    )

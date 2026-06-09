#!/usr/bin/env python3
"""Module for counting lines of code in a directory."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Global styles
ERROR_STYLE: str = "bold red"
SUCCESS_STYLE: str = "bold green"
INFO_STYLE: str = "bold cyan"
WARNING_STYLE: str = "bold yellow"

# Supported languages and their extensions/filenames
LANGUAGES: dict[str, dict[str, list[str]]] = {
    "Python": {"extensions": [".py"], "filenames": []},
    "JavaScript": {"extensions": [".js"], "filenames": []},
    "TypeScript": {"extensions": [".ts", ".tsx"], "filenames": []},
    "HTML": {"extensions": [".html", ".htm"], "filenames": []},
    "CSS": {"extensions": [".css", ".scss", ".sass", ".less"], "filenames": []},
    "C": {"extensions": [".c", ".h"], "filenames": []},
    "C++": {"extensions": [".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx"], "filenames": []},
    "Java": {"extensions": [".java"], "filenames": []},
    "Go": {"extensions": [".go"], "filenames": []},
    "Rust": {"extensions": [".rs"], "filenames": []},
    "Markdown": {"extensions": [".md"], "filenames": []},
    "JSON": {"extensions": [".json"], "filenames": []},
    "YAML": {"extensions": [".yaml", ".yml"], "filenames": []},
    "Shell": {"extensions": [".sh", ".bash", ".zsh"], "filenames": []},
    "Make": {"extensions": [], "filenames": ["Makefile", "makefile"]},
    "Docker": {"extensions": [], "filenames": ["Dockerfile", "dockerfile"]},
}

# Directories to ignore
IGNORE_DIRS: list[str] = [
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    "target",
    ".ruff_cache",
]

console: Console = Console()


def detect_language(file_path: Path) -> str:
    """Detect the programming language of a file based on its extension or name.

    Args:
        file_path: Path to the file.

    Returns:
        The detected language name, or 'Unknown' if not recognized.

    """
    file_name = file_path.name
    file_ext = file_path.suffix.lower()

    for lang, data in LANGUAGES.items():
        if file_ext in data["extensions"] or file_name in data["filenames"]:
            return lang

    return "Unknown"


def is_binary_file(file_path: Path) -> bool:
    """Check if a file is binary using the 'file' command.

    Args:
        file_path: Path to the file.

    Returns:
        True if the file is binary, False otherwise.

    """
    try:
        result = subprocess.run(  # noqa: S603
            ["/usr/bin/file", "--mime", "-b", str(file_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        return "binary" in result.stdout.lower()
    except (subprocess.SubprocessError, OSError) as e:
        console.print(f"[{ERROR_STYLE}]Error determining file type for {file_path}: {e}[/]")
        return False


def _process_file(
    file_path: Path,
    exclude_filetypes: list[str] | None,
    file_counts: dict[str, int],
    language_totals: dict[str, int],
) -> tuple[int, int]:
    """Process a single file and update totals."""
    if exclude_filetypes and file_path.suffix.lower() in exclude_filetypes:
        return 0, 0

    try:
        if not file_path.is_file() or not os.access(file_path, os.R_OK):
            return 0, 0

        if is_binary_file(file_path):
            return 0, 0

        language = detect_language(file_path)
        if language == "Unknown":
            return 0, 0

        with file_path.open(encoding="utf-8", errors="ignore") as f:
            new_lines = sum(1 for _ in f)
            file_size = file_path.stat().st_size

            file_counts[language] = file_counts.get(language, 0) + 1
            language_totals[language] = language_totals.get(language, 0) + new_lines
            return new_lines, file_size

    except OSError as e:
        console.print(f"[{ERROR_STYLE}]Error reading file {file_path}: {e}[/]")
        return 0, 0


def count_lines_in_directory(
    directory_path: Path,
    exclude_filetypes: list[str] | None = None,
) -> tuple[dict[str, int], dict[str, int], int, int]:
    """Recursively count lines of code and files per language in a directory.

    Args:
        directory_path: Root directory to start counting from.
        exclude_filetypes: List of file extensions to exclude.

    Returns:
        A tuple containing:
        - Dict mapping language to file count.
        - Dict mapping language to total lines.
        - Overall total lines.
        - Overall total size in bytes.

    """
    file_counts: dict[str, int] = {}
    language_totals: dict[str, int] = {}
    total_lines = 0
    total_size = 0

    for root, dirs, files in os.walk(directory_path):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            file_path = Path(root) / file
            lines, size = _process_file(file_path, exclude_filetypes, file_counts, language_totals)
            total_lines += lines
            total_size += size

    return file_counts, language_totals, total_lines, total_size


def _format_size(size_in_bytes: float) -> str:
    """Format bytes into human-readable string (KB, MB, etc.)."""
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size_threshold = 1024
    while size_in_bytes >= size_threshold and unit_index < len(units) - 1:
        size_in_bytes /= size_threshold
        unit_index += 1
    return f"{size_in_bytes:.2f} {units[unit_index]}"


def display_results(
    file_counts: dict[str, int],
    language_totals: dict[str, int],
    total_lines: int,
    total_size: int,
    directory: str,
) -> None:
    """Display the line count results in a formatted table.

    Args:
        file_counts: Dict mapping language to file count.
        language_totals: Dict mapping language to total lines.
        total_lines: Overall total lines.
        total_size: Overall total size in bytes.
        directory: The directory that was analyzed.

    """
    total_files = sum(file_counts.values())

    console.print(f"\n[{INFO_STYLE}]Lines of Code Statistics for [underline]{directory}[/][/]\n")

    if total_files == 0:
        console.print(f"[{WARNING_STYLE}]No supported code files found.[/]")
        return

    table = Table(show_header=True, header_style=INFO_STYLE)
    table.add_column("Language", style="dim", width=15)
    table.add_column("Files", justify="right")
    table.add_column("Lines", justify="right")
    table.add_column("Percentage", justify="right")

    # Sort by line count descending
    sorted_langs = sorted(
        language_totals.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    for lang, lines in sorted_langs:
        files = file_counts[lang]
        percentage = (lines / total_lines) * 100 if total_lines > 0 else 0
        table.add_row(
            lang,
            str(files),
            str(lines),
            f"{percentage:.1f}%",
        )

    console.print(table)
    console.print(
        f"\n[bold {INFO_STYLE}]Total Summary:[/]\n"
        f"  Files: {total_files}\n"
        f"  Lines: {total_lines}\n"
        f"  Size:  {_format_size(total_size)}\n",
    )


def main() -> None:
    """Parse arguments and execute the line counting logic."""
    parser = argparse.ArgumentParser(description="Count lines of code in a directory.")
    parser.add_argument(
        "directory",
        nargs="?",
        default=str(Path.cwd()),
        help="Directory path to count lines of code.",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        help="File extensions to exclude (e.g., .json .md).",
    )

    args = parser.parse_args()
    dir_path = Path(args.directory).resolve()

    if not dir_path.is_dir():
        console.print(f"[{ERROR_STYLE}]Error: {dir_path} is not a directory.[/]")
        return

    file_counts, language_totals, total_lines, total_size = count_lines_in_directory(
        dir_path,
        args.exclude,
    )

    display_results(
        file_counts,
        language_totals,
        total_lines,
        total_size,
        str(dir_path),
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python
import os
import argparse
from collections import defaultdict
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from typing import Optional, List, Tuple, Dict

console = Console()

# Supported file extensions for programming languages
SUPPORTED_EXTENSIONS: Dict[str, str] = {
    '.py': 'Python',
    '.sh': 'Shell',
    '.js': 'JavaScript',
    '.html': 'HTML',
    '.css': 'CSS',
    '.java': 'Java',
    '.c': 'C',
    '.cpp': 'C++',
    '.cs': 'C#',
    '.go': 'Go',
    '.rs': 'Rust',
    '.php': 'PHP',
    '.rb': 'Ruby',
    '.swift': 'Swift',
    '.ts': 'TypeScript',
    '.kt': 'Kotlin',
    '.sql': 'SQL',
    '.xml': 'XML',
    '.json': 'JSON',
    '.yaml': 'YAML',
    '.toml': 'TOML',
    '.md': 'Markdown',
    '.txt': 'Text',
    '.conf': 'Apache Config',
    '.vcl': 'Varnish Config',
    '.tf': 'Terraform',
    '.tfvars': 'Terraform',
    '.yml': 'Ansible',
}

# Shebang to language mapping
SHEBANG_MAPPING: Dict[str, str] = {
    'python': 'Python',
    'bash': 'Shell',
    'sh': 'Shell',
    'ruby': 'Ruby',
    'node': 'JavaScript',
}

# File names to language mapping
FILENAME_MAPPING: Dict[str, str] = {
    'meson.build': 'Meson Build',
    '.pylintrc': 'Pylint Config',
    '.flake8': 'Flake8 Config',
    '.eslintrc': 'ESLint Config',
    '.prettierrc': 'Prettier Config',
    'Makefile': 'Makefile',
    'Dockerfile': 'Dockerfile',
}


def detect_language(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            first_line = file.readline().strip()

            if first_line.startswith('<?xml'):
                return 'XML'

            for line in file:
                for char in line:
                    if ord(char) < 32 and char not in ['\n', '\r', '\t']:
                        return 'Binary'

            return 'Text'

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return 'Unknown'
    except UnicodeDecodeError:
        print(f"Unable to decode file: {file_path}")
        return 'Binary'
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return 'Unknown'


def is_binary_file(file_path: str) -> bool:
    binary_extensions = ['.gz', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.tiff', '.webp', '.pdf']
    file_ext = os.path.splitext(file_path)[1]
    return file_ext.lower() in binary_extensions


def count_lines_and_size(start: str, exclude_filetypes: Optional[List[str]] = None, show_progress: bool = True) -> Tuple[int, int, dict, dict]:
    total_lines = 0
    total_size = 0
    file_counts = defaultdict(lambda: {'lines': 0, 'size': 0, 'language': 'Unknown'})
    language_totals = defaultdict(lambda: {'lines': 0, 'size': 0})

    progress = Progress(console=console, auto_refresh=False)
    if show_progress:
        task = progress.add_task("[cyan]Analyzing files...", total=os.stat(start).st_size, start=False,
                                 complete_style="green", start_style="yellow", bar_template='{bar}{info}')
        progress.start()

    try:
        for root, dirs, files in os.walk(start):
            dirs[:] = [d for d in dirs if d != '.git']

            for file in files:
                file_path = os.path.join(root, file)
                file_name = os.path.basename(file)
                file_ext = os.path.splitext(file)[1]

                if exclude_filetypes and file_ext in exclude_filetypes:
                    continue

                if is_binary_file(file_path):
                    continue

                try:
                    if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK):
                        continue

                    language = FILENAME_MAPPING.get(file_name, SUPPORTED_EXTENSIONS.get(file_ext, detect_language(file_path)))

                    with open(file_path, 'r', encoding='utf-8') as f:
                        new_lines = sum(1 for _ in f)
                        file_size = os.path.getsize(file_path)
                        total_lines += new_lines
                        total_size += file_size
                        file_counts[file_path] = {'lines': new_lines, 'size': file_size, 'language': language}
                        language_totals[language]['lines'] += new_lines
                        language_totals[language]['size'] += file_size
                except (UnicodeDecodeError, OSError) as e:
                    print(f"Error reading file {file_path}: {e}")

                if show_progress:
                    progress.update(task, advance=os.path.getsize(file_path))

        if show_progress:
            progress.stop()
    except KeyboardInterrupt:
        console.print("[bold red]Operation cancelled by user.[/bold red]")
        if show_progress:
            progress.stop()

    return total_lines, total_size, file_counts, language_totals


def display_results(total_lines: int, total_size: int, file_counts: dict, language_totals: dict) -> None:
    file_table = Table(title="[bold cyan]Lines of Code Count and Size by File[/bold cyan]")

    file_table.add_column("File", justify="left", style="cyan", no_wrap=True)
    file_table.add_column("Lines", justify="right", style="magenta")
    file_table.add_column("Size (Bytes)", justify="right", style="yellow")
    file_table.add_column("Language", justify="left", style="yellow")
    file_table.add_column("Cumulative Total Lines", justify="right", style="green")
    file_table.add_column("Cumulative Total Size", justify="right", style="green")

    cumulative_total_lines = 0
    cumulative_total_size = 0

    for file, info in sorted(file_counts.items(), key=lambda item: item[1]['lines'], reverse=True):
        lines = info['lines']
        size = info['size']
        language = info['language']
        cumulative_total_lines += lines
        cumulative_total_size += size
        file_table.add_row(file, str(lines), str(size), language, str(cumulative_total_lines), str(cumulative_total_size))

    console.print(file_table)

    language_table = Table(title="[bold cyan]Lines of Code Count and Size by Language[/bold cyan]")

    language_table.add_column("Language", justify="left", style="cyan", no_wrap=True)
    language_table.add_column("Total Lines", justify="right", style="magenta")
    language_table.add_column("Total Size (Bytes)", justify="right", style="yellow")

    for language, info in sorted(language_totals.items(), key=lambda item: item[1]['lines'], reverse=True):
        lines = info['lines']
        size = info['size']
        language_table.add_row(language, str(lines), str(size))

    console.print(language_table)
    console.print(f"\n[bold red]Total Lines: {total_lines}, Total Size: {total_size} bytes[/bold red]")


def additional_metrics(file_counts: dict) -> None:
    average_lines_per_file = sum(info['lines'] for info in file_counts.values()) / len(file_counts)
    largest_files = sorted(file_counts.items(), key=lambda item: item[1]['size'], reverse=True)[:5]

    console.print(f"\n[bold cyan]Additional Metrics[/bold cyan]:")
    console.print(f"Average lines per file: {average_lines_per_file:.2f}")

    console.print("\n[bold cyan]Top 5 Largest Files[/bold cyan]:")
    for idx, (file, info) in enumerate(largest_files, start=1):
        console.print(f"{idx}. {file} - {info['size']} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count lines of code and calculate total size of files in a directory.")
    parser.add_argument("start_dir", nargs='?', default='.', help="Directory path to analyze (default is current directory)")
    parser.add_argument("-e", "--exclude", nargs='+', help="File extensions to exclude (space-separated list, e.g., .pyc .exe)")
    args = parser.parse_args()

    excluded_extensions = args.exclude or []
    excluded_extensions.extend(['.gz', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.tiff', '.webp', '.pdf'])

    total_lines, total_size, file_counts, language_totals = count_lines_and_size(args.start_dir, exclude_filetypes=excluded_extensions)
    display_results(total_lines, total_size, file_counts, language_totals)
    additional_metrics(file_counts)

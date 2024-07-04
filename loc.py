#!/usr/bin/env python3
"""
Count lines of code and categorize by language.
"""

import os
from collections import defaultdict
from rich.console import Console
from rich.table import Table

console = Console()

# Supported file extensions for programming languages
SUPPORTED_EXTENSIONS = {
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
}

# Shebang to language mapping
SHEBANG_MAPPING = {
    'python': 'Python',
    'bash': 'Shell',
    'sh': 'Shell',
    'ruby': 'Ruby',
    'node': 'JavaScript',
}

# File names to language mapping
FILENAME_MAPPING = {
    'meson.build': 'Meson Build',
    '.pylintrc': 'Pylint Config',
    '.flake8': 'Flake8 Config',
    '.eslintrc': 'ESLint Config',
    '.prettierrc': 'Prettier Config',
    'Makefile': 'Makefile',
    'Dockerfile': 'Dockerfile',
}

def detect_language(file_path):
    """
    Detect the programming language of a file based on its shebang or content.

    Returns:
        str: Detected language or 'Unknown' if undetermined.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            first_line = file.readline().strip()
            
            # Check for XML file
            if first_line.startswith('<?xml'):
                return 'XML'
            
            # Check for plain text
            for line in file:
                # Check if line contains non-printable characters
                for char in line:
                    if ord(char) < 32 and char not in ['\n', '\r', '\t']:
                        return 'Binary'  # Likely binary data
                
            # If no specific format detected, default to Text
            return 'Text'
    
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return 'Unknown'
    except UnicodeDecodeError:
        print(f"Unable to decode file: {file_path}")
        return 'Unknown'
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return 'Unknown'

def count_lines(start):
    """
    Count lines of code in files starting from the given directory.

    Returns:
        tuple: Total lines, file counts, language totals.
    """
    total_lines = 0
    file_counts = defaultdict(lambda: {'lines': 0, 'language': 'Unknown'})
    language_totals = defaultdict(int)

    for root, dirs, files in os.walk(start):
        dirs[:] = [d for d in dirs if d != '.git']  # Skip .git directory

        for file in files:
            file_path = os.path.join(root, file)
            file_name = os.path.basename(file)
            file_ext = os.path.splitext(file)[1]

            language = FILENAME_MAPPING.get(file_name, SUPPORTED_EXTENSIONS.get(file_ext, detect_language(file_path)))

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Count lines efficiently
                    new_lines = sum(1 for _ in f)
                    total_lines += new_lines
                    file_counts[file_path] = {'lines': new_lines, 'language': language}
                    language_totals[language] += new_lines
            except (UnicodeDecodeError, OSError) as e:
                print(f"Error reading file {file_path}: {e}")

    return total_lines, file_counts, language_totals

def display_results(total_lines, file_counts, language_totals):
    """
    Display the results using the rich library.
    """
    file_table = Table(title="[bold cyan]Lines of Code Count by File[/bold cyan]")

    file_table.add_column("File", justify="left", style="cyan", no_wrap=True)
    file_table.add_column("Lines", justify="right", style="magenta")
    file_table.add_column("Language", justify="left", style="yellow")
    file_table.add_column("Cumulative Total", justify="right", style="green")

    cumulative_total = 0

    for file, info in sorted(file_counts.items(), key=lambda item: item[1]['lines'], reverse=True):
        lines = info['lines']
        language = info['language']
        cumulative_total += lines
        file_table.add_row(file, str(lines), language, str(cumulative_total))

    console.print(file_table)

    language_table = Table(title="[bold cyan]Lines of Code Count by Language[/bold cyan]")

    language_table.add_column("Language", justify="left", style="cyan", no_wrap=True)
    language_table.add_column("Total Lines", justify="right", style="magenta")

    for language, lines in sorted(language_totals.items(), key=lambda item: item[1], reverse=True):
        language_table.add_row(language, str(lines))

    console.print(language_table)
    console.print(f"\n[bold red]Total Lines: {total_lines}[/bold red]")

if __name__ == "__main__":
    start_dir = '.'
    total_lines, file_counts, language_totals = count_lines(start_dir)
    display_results(total_lines, file_counts, language_totals)

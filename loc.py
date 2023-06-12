#!/usr/bin/env python3
import argparse
import codecs
import glob
import logging
import os
from beautifultable import BeautifulTable

EXTENSIONS = {
    "VCL": "*.vcl",
    "GO": "*.go",
    "XML": "*.xml",
    "HTML": "*.html",
    "JAVA": "*.java",
    "JS": "*.js",
    "CSS": "*.css",
    "JSON": "*.json",
    "SHELL": "*.sh",
    "C": "*.[ch]",
    "RUBY": "*.rb",
    "PHP": "*.php",
    "PYTHON": "*.py"
}

def main(args):
    logging.basicConfig(level=logging.INFO)
    search_path = os.path.abspath(args.path)
    table = BeautifulTable()
    table.set_style(BeautifulTable.STYLE_BOX_ROUNDED)
    table.columns.header = ["Filetype", "Lines of Code", "# of files", "Avg LOC per file"]
    total_loc, total_files = 0, 0
    for language, pattern in EXTENSIONS.items():
        files = glob.glob(os.path.join(search_path, "**", pattern), recursive=True)
        loc, num_files = 0, len(files)
        for file in files:
            try:
                if os.path.isfile(file):
                    with codecs.open(file, "r", "utf-8") as f:
                        loc += len(f.readlines())
            except UnicodeDecodeError:
                logging.warning(f"Could not read file {file}: invalid characters")
            except Exception:
                logging.exception(f"Could not read file {file}")
        if num_files == 0:
            avg_loc_file = 0
        else:
            avg_loc_file = loc // num_files
        table.rows.append([language, loc, num_files, avg_loc_file])
        total_loc += loc
        total_files += num_files
    if total_files == 0:
        total_avg_loc_file = 0
    else:
        total_avg_loc_file = total_loc // total_files
    table.rows.append(["TOTAL", total_loc, total_files, total_avg_loc_file])
    print(table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count lines of code in a directory.")
    parser.add_argument("path", nargs="?", default=".", help="the directory to search for files (default: current directory)")
    args = parser.parse_args()
    main(args)

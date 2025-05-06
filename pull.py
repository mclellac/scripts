#!/usr/bin/env python3

import os
import subprocess
import sys
import re


class Colors:
    RESET = "\033[0m"
    GREY = "\033[1;30m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    WHITE = "\033[0;37m"
    ORANGE = "\033[0;91m"
    BROWN = "\033[0;33m"


ICONS = {
    "github": "",     # GitHub icon
    "bitbucket": "",  # Bitbucket/Stash icon
    "gitlab": "",     # GitLab icon
    "default": "📦",   # Generic package icon
    "success": "",    # Success checkmark
    "uptodate": "",   # Up-to-date icon
    "error": "",      # Error warning sign
}


# Utility Function to Run Git Commands
def run_git_command(command, cwd=None):
    """Runs a git command in a specified directory and captures output/status."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,  # Don't raise an exception for non-zero exit code
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        print(
            f"{Colors.RED}Error: 'git' command not found. Is Git installed and in your PATH?{Colors.RESET}",
            file=sys.stderr,
        )
        return 1, "", "git command not found"
    except Exception as e:
        print(
            f"{Colors.RED}An unexpected error occurred: {e}{Colors.RESET}", file=sys.stderr
        )  
        return 1, "", str(e)


# Function to Pull Git Repositories
def pull_repositories(target_dir_arg):
    """
    Finds and pulls changes for Git repositories under a specified directory.
    If successful, prints the target search directory to stdout for shell integration.
    All other output goes to stderr.
    """
    base_src_dir = os.path.join(os.path.expanduser("~"), "Projects", "src")
    search_dir = os.path.join(base_src_dir, target_dir_arg) if target_dir_arg else base_src_dir

    if not os.path.isdir(search_dir):
        print(
            f"{Colors.RED}Error: Directory not found: {search_dir}{Colors.RESET}",
            file=sys.stderr,  
        )
        sys.exit(1)

    print(
        f"{Colors.CYAN}Searching for repositories under {search_dir}...{Colors.RESET}",
        file=sys.stderr,
    )  

    git_dirs = []
    for root, dirs, files in os.walk(search_dir):
        if ".git" in dirs:
            git_dirs.append(os.path.join(root, ".git"))
            dirs.remove(".git")

    if not git_dirs:
        print(
            f"{Colors.YELLOW}No Git repositories found under {search_dir}{Colors.RESET}",
            file=sys.stderr,
        )  
    else:
        print(
            f"{Colors.CYAN}Found {len(git_dirs)} repositories under {search_dir}. Pulling...{Colors.RESET}",
            file=sys.stderr,  
        )

    overall_status = 0

    for gitdir in git_dirs:
        repo_path = os.path.dirname(gitdir)

        if not repo_path.startswith(base_src_dir):
            print(
                f"{Colors.YELLOW}Warning: Skipping potentially unsafe path: {repo_path}{Colors.RESET}",
                file=sys.stderr,  
            )
            overall_status = 1
            continue

        relative_path = os.path.relpath(repo_path, base_src_dir)

        current_dir_before_repo_cd = os.getcwd()  # Store CWD
        try:
            os.chdir(repo_path)
        except OSError as e:
            print(
                f"{Colors.RED}Error: Could not change directory to {repo_path}: {e}{Colors.RESET}",
                file=sys.stderr,  
            )
            overall_status = 1
            # Attempt to change back directory
            if os.getcwd() != current_dir_before_repo_cd:
                os.chdir(current_dir_before_repo_cd)
            continue

        branch_code, branch_stdout, _ = run_git_command(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"]
        )
        branch = (
            branch_stdout.strip()
            if branch_code == 0 and branch_stdout.strip()
            else "(detached HEAD)"
        )

        origin_code, origin_stdout, _ = run_git_command(
            ["git", "config", "--get", "remote.origin.url"]
        )
        origin_url = origin_stdout.strip() if origin_code == 0 else ""

        icon = ICONS["default"]
        if origin_url:
            if "github.com" in origin_url:
                icon = ICONS["github"]
            elif "bitbucket.org" in origin_url or "stash.nm.cbc.ca" in origin_url:
                icon = ICONS["bitbucket"]
            elif "gitlab.nm.cbc.ca" in origin_url:
                icon = ICONS["gitlab"]

        pull_status, pull_stdout, pull_stderr = run_git_command(["git", "pull", "--ff-only"])
        pull_output = pull_stdout + pull_stderr

        if pull_status == 0:
            if "Already up to date" in pull_output or "Already up-to-date" in pull_output:
                status_icon = ICONS["uptodate"]
                status_message = "Already up to date."
                status_color = Colors.GREEN
                print(
                    f"{Colors.CYAN}{icon} {Colors.GREEN}{relative_path} ({branch}){Colors.RESET} {status_color}{status_icon} {status_message}{Colors.RESET}",
                    file=sys.stderr,  
                )
            else:
                status_icon = ICONS["success"]
                status_message = "Pulled successfully."
                status_color = Colors.GREEN
                print(
                    f"{Colors.CYAN}{icon} {Colors.GREEN}{relative_path} ({branch}){Colors.RESET} {status_color}{status_icon} {status_message}{Colors.RESET}",
                    file=sys.stderr,  
                )
                filtered_output = []
                notice_pattern = re.compile(
                    r"^\s*\*+\s*NOTICE\s*\*+|^s*Access to this computer system is restricted|^s*connections are logged and monitored|/usr/bin/gh auth git-credential"
                )
                for line in pull_output.splitlines():
                    if not notice_pattern.search(line):
                        filtered_output.append(f"  {line}")
                if filtered_output:
                    print("\n".join(filtered_output), file=sys.stderr)  
        else:  # pull_status != 0 (Pull failed)
            overall_status = 1
            status_icon = ICONS["error"]
            status_color = Colors.RED

            # Default error message
            git_error_summary = f"Pull failed (Status: {pull_status})."

            # Check for specific common errors related to local changes
            git_error_output_lower = pull_output.lower()
            if (
                "unstaged changes" in git_error_output_lower
                or "uncommitted changes" in git_error_output_lower
                or "commit or stash them" in git_error_output_lower
                or (
                    "overwritten by" in git_error_output_lower
                    and ("merge" in git_error_output_lower or "pull" in git_error_output_lower)
                )
            ):
                git_error_summary = (
                    "Pull aborted: Uncommitted local changes. Please commit or stash."
                )

            print(
                f"{Colors.CYAN}{icon} {Colors.GREEN}{relative_path} ({branch}){Colors.RESET} {status_color}{status_icon} {git_error_summary}{Colors.RESET}",
                file=sys.stderr,  
            )

            # Print the raw, detailed output from git
            if pull_output.strip():
                # Indent Git's own error messages for slight visual separation
                for line in pull_output.strip().splitlines():
                    print(
                        f"  {Colors.RED}{line}{Colors.RESET}", file=sys.stderr
                    )  , indented

        os.chdir(current_dir_before_repo_cd)  # Change back to the CWD before entering the repo_path

    print(
        f"{Colors.CYAN}Finished processing repositories under {search_dir}.{Colors.RESET}",
        file=sys.stderr,
    )  

    final_chdir_success = False
    try:
        os.chdir(search_dir)
        final_chdir_success = True
    except OSError as e:
        print(
            f"{Colors.RED}Error: Could not change script's internal CWD to {search_dir}: {e}{Colors.RESET}",
            file=sys.stderr,  
        )
        overall_status = 1

    if overall_status == 0 and final_chdir_success:
        print(search_dir, file=sys.stdout)

    sys.exit(overall_status)


# Main Execution
if __name__ == "__main__":
    target_directory_arg_main = sys.argv[1] if len(sys.argv) > 1 else ""
    pull_repositories(target_directory_arg_main)

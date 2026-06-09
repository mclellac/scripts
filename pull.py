#!/usr/bin/env python3
"""Module for finding and pulling changes for Git repositories."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""

    RESET: str = "\033[0m"
    GREY: str = "\033[1;30m"
    RED: str = "\033[0;31m"
    GREEN: str = "\033[0;32m"
    YELLOW: str = "\033[0;33m"
    BLUE: str = "\033[0;34m"
    PURPLE: str = "\033[0;35m"
    CYAN: str = "\033[0;36m"
    WHITE: str = "\033[0;37m"
    BOLD: str = "\033[1m"


ICONS: dict[str, str] = {
    "success": "✔",
    "failure": "✘",
    "warning": "⚠",
    "uptodate": "≡",
    "pulling": "↓",
    "branch": "",
}


def run_git_command(command: list[str], *, cwd: str | Path | None = None) -> tuple[int, str, str]:
    """Run a git command in a specified directory and capture output/status.

    Args:
        command: The git command to run as a list of strings.
        cwd: The directory to run the command in.

    Returns:
        A tuple of (return_code, stdout, stderr).

    """
    try:
        result = subprocess.run(  # noqa: S603
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        msg = f"{Colors.RED}Error: 'git' command not found. Is Git installed and in your PATH?{Colors.RESET}\n"
        sys.stderr.write(msg)
        return 1, "", "git command not found"
    except (subprocess.SubprocessError, OSError) as e:
        sys.stderr.write(f"{Colors.RED}An unexpected error occurred: {e}{Colors.RESET}\n")
        return 1, "", str(e)
    else:
        return result.returncode, result.stdout, result.stderr


def _get_repo_info(repo_path: Path) -> tuple[str, str, str]:
    """Get branch name and origin URL for a repository."""
    branch_code, branch_stdout, _ = run_git_command(
        ["/usr/bin/git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_path,
    )
    branch = branch_stdout.strip() if branch_code == 0 else "unknown"

    origin_code, origin_stdout, _ = run_git_command(
        ["/usr/bin/git", "config", "--get", "remote.origin.url"],
        cwd=repo_path,
    )
    origin_url = origin_stdout.strip() if origin_code == 0 else ""

    icon = ICONS["branch"]
    if "github.com" in origin_url:
        icon = ""
    elif "gitlab.com" in origin_url:
        icon = ""

    return branch, origin_url, icon


def _process_pull_output(pull_output: str, relative_path: Path, branch: str, icon: str) -> None:
    """Process and print the output of a git pull command."""
    if any(msg in pull_output for msg in ("Already up to date.", "Déjà à jour.", "Ya está al día.")):
        status_icon = ICONS["uptodate"]
        status_message = "Already up to date."
        status_color = Colors.GREEN
        sys.stderr.write(
            f"{Colors.CYAN}{icon} {Colors.GREEN}{relative_path} "
            f"({branch}){Colors.RESET} {status_color}{status_icon} "
            f"{status_message}{Colors.RESET}\n",
        )
    else:
        status_icon = ICONS["success"]
        status_message = "Pulled successfully."
        status_color = Colors.GREEN
        sys.stderr.write(
            f"{Colors.CYAN}{icon} {Colors.GREEN}{relative_path} "
            f"({branch}){Colors.RESET} {status_color}{status_icon} "
            f"{status_message}{Colors.RESET}\n",
        )

        notice_pattern = re.compile(
            r"^\s*\*+\s*NOTICE\s*\*+|"
            r"^\s*Access to this computer system is restricted|"
            r"^\s*connections are logged and monitored|"
            r"/usr/bin/gh auth git-credential",
        )
        filtered_output = [f"  {line}" for line in pull_output.splitlines() if not notice_pattern.search(line)]
        if filtered_output:
            sys.stderr.write("\n".join(filtered_output) + "\n")


def _handle_pull_failure(pull_output: str, relative_path: Path, branch: str, icon: str) -> None:
    """Handle and print information for a failed git pull."""
    status_icon = ICONS["failure"]
    status_color = Colors.RED
    git_error_summary = "Pull failed."

    if "local changes" in pull_output and "overwritten by merge" in pull_output:
        git_error_summary = "Pull aborted: Uncommitted local changes. Please commit or stash."

    sys.stderr.write(
        f"{Colors.CYAN}{icon} {Colors.GREEN}{relative_path} "
        f"({branch}){Colors.RESET} {status_color}{status_icon} "
        f"{git_error_summary}{Colors.RESET}\n",
    )

    if pull_output.strip():
        for line in pull_output.strip().splitlines():
            sys.stderr.write(f"  {Colors.RED}{line}{Colors.RESET}\n")


def _find_git_dirs(search_dir: Path) -> list[Path]:
    """Find all .git directories under search_dir."""
    git_dirs: list[Path] = []
    for root, dirs, _ in os.walk(search_dir):
        if ".git" in dirs:
            git_dirs.append(Path(root) / ".git")
            dirs.remove(".git")
    return git_dirs


def pull_repositories(target_dir_arg: str | None) -> None:
    """Find and pull changes for Git repositories under a specified directory.

    If successful, prints the target search directory to stdout for shell integration.
    All other output goes to stderr.

    Args:
        target_dir_arg: The sub-directory under ~/Projects/src to search.

    """
    base_src_dir = Path.home() / "Projects" / "src"
    search_dir = base_src_dir / target_dir_arg if target_dir_arg else base_src_dir

    if not search_dir.is_dir():
        sys.stderr.write(f"{Colors.RED}Error: Directory not found: {search_dir}{Colors.RESET}\n")
        sys.exit(1)

    sys.stderr.write(f"{Colors.CYAN}Searching for repositories under {search_dir}...{Colors.RESET}\n")

    git_dirs = _find_git_dirs(search_dir)

    if not git_dirs:
        sys.stderr.write(f"{Colors.YELLOW}No Git repositories found under {search_dir}{Colors.RESET}\n")
    else:
        msg = f"{Colors.CYAN}Found {len(git_dirs)} repositories under {search_dir}. Pulling...{Colors.RESET}\n"
        sys.stderr.write(msg)

    overall_status = 0
    for gitdir in git_dirs:
        repo_path = gitdir.parent
        if not str(repo_path).startswith(str(base_src_dir)):
            sys.stderr.write(f"{Colors.YELLOW}Warning: Skipping potentially unsafe path: {repo_path}{Colors.RESET}\n")
            continue

        relative_path = repo_path.relative_to(base_src_dir)
        branch, _, icon = _get_repo_info(repo_path)

        pull_status, pull_stdout, pull_stderr = run_git_command(["/usr/bin/git", "pull"], cwd=repo_path)
        pull_output = pull_stdout + pull_stderr

        if pull_status == 0:
            _process_pull_output(pull_output, relative_path, branch, icon)
        else:
            overall_status = 1
            _handle_pull_failure(pull_output, relative_path, branch, icon)

    sys.stderr.write(f"{Colors.CYAN}Finished processing repositories under {search_dir}.{Colors.RESET}\n")

    try:
        os.chdir(search_dir)
    except OSError as e:
        msg = f"{Colors.RED}Error: Could not change script's internal CWD to {search_dir}: {e}{Colors.RESET}\n"
        sys.stderr.write(msg)
        overall_status = 1
    else:
        if overall_status == 0:
            sys.stdout.write(f"{search_dir}\n")

    sys.exit(overall_status)


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else None
    pull_repositories(target_dir)

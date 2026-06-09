#!/usr/bin/env python3
"""Module for extracting domain names from a webpage."""

from __future__ import annotations

import re
import sys

import requests


def fetch_webpage(url: str) -> str | None:
    """Fetch the content of a webpage.

    Args:
        url: The URL of the webpage to fetch.

    Returns:
        The content of the webpage as a string, or None if the fetch fails.

    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        sys.stderr.write(f"Error fetching webpage: {e}\n")
        return None
    else:
        return response.text


def extract_matches(content: str, regex: str) -> list[str]:
    """Extract all matches of a regex from a string.

    Args:
        content: The string to search.
        regex: The regular expression pattern to use.

    Returns:
        A list of unique strings matching the regex, filtered for valid domains.

    """
    try:
        matches: list[str] = re.findall(regex, content)
        # Filter out empty and undesired 'http://' or 'https://' only objects.
        # Break long list comprehension for readability
        filtered_matches = [m for m in matches if m not in ("http://fast.", "http://", "https://", "")]
        return sorted(set(filtered_matches))
    except re.error as e:
        sys.stderr.write(f"Regex error: {e}\n")
        return []


def validate_url(url: str) -> bool:
    """Validate if a string is a properly formatted URL.

    Args:
        url: The string to validate.

    Returns:
        True if the URL is valid, False otherwise.

    """
    regex = r"^(https?://)?(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    return re.match(regex, url) is not None


def main() -> None:
    """Entry point for the domain extractor script."""
    arg_count_threshold = 2
    if len(sys.argv) < arg_count_threshold:
        sys.stderr.write(f"Usage: {sys.argv[0]} <URL>\n")
        sys.exit(1)

    url = sys.argv[1]
    if not validate_url(url):
        sys.stderr.write(f"Invalid URL: {url}\n")
        sys.exit(1)

    content = fetch_webpage(url)
    if content:
        # Regex for finding potential domain names/URLs
        domain_regex = r"https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z0-9-]+"
        domains = extract_matches(content, domain_regex)
        for domain in domains:
            sys.stdout.write(f"{domain}\n")


if __name__ == "__main__":
    main()

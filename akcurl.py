#!/usr/bin/env python3
"""Module for fetching and analyzing Akamai HTTP headers."""

from __future__ import annotations

import argparse
import re
import sys
from typing import TYPE_CHECKING, Callable

import requests

if TYPE_CHECKING:
    from collections.abc import Mapping

try:
    from rich.console import Console as _RichConsole
    from rich.text import Text as _RichText

    RichConsole: type[_RichConsole | _FallbackConsole] = _RichConsole
    RichText: type[_RichText | _FallbackText] = _RichText
    _rich_available = True
except ImportError:
    _rich_available = False

    class _FallbackConsole:
        """Fallback for rich.console.Console."""

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            """Initialize the fallback console."""

        def print(self, *_args: object, **_kwargs: object) -> None:
            """Print a message to the console."""

    class _FallbackText:
        """Fallback for rich.text.Text."""

        def __init__(self, text: str, style: str | None = None) -> None:
            """Initialize the fallback text."""
            self.text = text
            self.style = style

        @staticmethod
        def from_markup(markup: str) -> _FallbackText:
            """Create a RichText object from markup."""
            return _FallbackText(re.sub(r"\[.*?\]", "", markup))

        def __add__(self, other: _RichText | _FallbackText) -> _FallbackText:
            """Add two RichText objects together."""
            return _FallbackText(self.text + str(other))

        def __str__(self) -> str:
            """Return the string representation of the text."""
            return self.text

    RichConsole = _FallbackConsole
    RichText = _FallbackText


class Printers:
    """Container for console print functions."""

    console_print: Callable[..., object] = print

    @staticmethod
    def error_print(*args: object, **_kwargs: object) -> int:
        """Print an error message to stderr."""
        return sys.stderr.write(" ".join(map(str, args)) + "\n")

    @staticmethod
    def verbose_print(*args: object, **_kwargs: object) -> int:
        """Print a verbose message to stderr."""
        return sys.stderr.write(" ".join(map(str, args)) + "\n")


printers = Printers()


STYLE_AKAMAI_VALUE: str = "bold dim cyan"
STYLE_XCACHE_VALUE: str = "bold dim magenta"
STYLE_CACHE_VALUE: str = "bold dim green"
STYLE_COOKIE_VALUE: str = "bold dim purple"
STYLE_CONTENT_VALUE: str = "bold dim yellow"
STYLE_SECURITY_VALUE: str = "bold dim orange_red1"
STYLE_REDIRECT_VALUE: str = "bold dim blue"
STYLE_DEFAULT_VALUE: str = "bold dim"

STYLE_AKAMAI_KEY: str = "bright_cyan"
STYLE_XCACHE_KEY: str = "bright_magenta"
STYLE_CACHE_KEY: str = "bright_green"

DEFAULT_AKAMAI_PRAGMA_HEADERS: list[str] = [
    "akamai-x-cache-on",
    "akamai-x-cache-remote-on",
    "akamai-x-check-cacheable",
    "akamai-x-get-cache-key",
    "akamai-x-get-extracted-values",
    "akamai-x-get-ssl-client-session-id",
    "akamai-x-get-true-cache-key",
    "akamai-x-serial-no",
    "akamai-x-feo-trace",
    "akamai-x-get-request-id",
]

HEADERS_TO_SPLIT: list[str] = [
    "x-cache",
    "x-cache-remote",
    "x-akamai-staging",
    "x-cache-key",
    "x-true-cache-key",
]


def setup_printers(*, no_color: bool) -> None:
    """Initialize print functions based on the no_color flag.

    Args:
        no_color: Whether to disable colored output.

    """
    if no_color or not _rich_available:
        if not no_color and not _rich_available:
            printers.error_print("Warning: 'rich' library not found. Falling back to plain text output.")
            printers.error_print("Install it ('pip install rich') for colored output.")

        def _console_print_fallback(*args: object, **_kwargs: object) -> None:
            sys.stdout.write(" ".join(map(str, args)) + "\n")

        printers.console_print = _console_print_fallback
    else:
        _console = RichConsole()
        printers.console_print = _console.print


def get_styles(header_name: str) -> tuple[str, str]:
    """Determine the color style for a header based on its name.

    Args:
        header_name: The name of the HTTP header.

    Returns:
        A tuple of (key_style, value_style).

    """
    lower_key = header_name.lower()

    if lower_key == "x-cache":
        return STYLE_XCACHE_KEY, STYLE_XCACHE_VALUE
    if lower_key == "x-cache-remote":
        return STYLE_XCACHE_KEY, STYLE_XCACHE_VALUE
    if lower_key in ["x-cache-key", "x-true-cache-key"]:
        return STYLE_CACHE_KEY, STYLE_CACHE_VALUE

    return _get_complex_styles(lower_key, header_name)


def _get_complex_styles(lower_key: str, header_name: str) -> tuple[str, str]:
    """Handle complex style matching logic."""
    if lower_key.startswith(("x-akamai-", "x-feo", "x-serial", "x-check-cacheable")):
        return STYLE_AKAMAI_KEY, STYLE_AKAMAI_VALUE
    if lower_key == "server" and "akamai" in header_name.lower():
        return STYLE_AKAMAI_KEY, STYLE_AKAMAI_VALUE
    if lower_key in ["set-cookie", "cookie", "p3p"]:
        return STYLE_DEFAULT_VALUE, STYLE_COOKIE_VALUE
    if lower_key in ["content-type", "content-encoding", "transfer-encoding"]:
        return STYLE_DEFAULT_VALUE, STYLE_CONTENT_VALUE
    if lower_key in ["strict-transport-security", "content-security-policy"]:
        return STYLE_DEFAULT_VALUE, STYLE_SECURITY_VALUE

    style_map = {
        "location": (STYLE_DEFAULT_VALUE, STYLE_REDIRECT_VALUE),
        "refresh": (STYLE_DEFAULT_VALUE, STYLE_REDIRECT_VALUE),
    }
    return style_map.get(lower_key, (STYLE_DEFAULT_VALUE, STYLE_DEFAULT_VALUE))


def _handle_request_error(e: Exception, *, verbose: bool) -> tuple[int | None, Mapping[str, str] | None]:
    """Handle request exceptions and return status/headers if available.

    Args:
        e: The exception that occurred.
        verbose: Whether verbose output is enabled.

    Returns:
        A tuple of (status_code, response_headers).

    """
    if isinstance(e, requests.exceptions.SSLError):
        printers.error_print(f"Error: SSL certificate verification failed: {e}")
    elif isinstance(e, requests.exceptions.HTTPError):
        if e.response is not None:
            final_status = e.response.status_code
            if not verbose:
                url_str = e.request.url if e.request else "unknown"
                printers.error_print(f"Error: HTTP {final_status} for url {url_str}")
            return final_status, e.response.headers
        printers.error_print(f"Error: HTTP Error occurred: {e}")
    elif isinstance(e, requests.exceptions.ConnectionError):
        printers.error_print(f"Error: Connection failed: {e}")
    elif isinstance(e, requests.exceptions.Timeout):
        printers.error_print(f"Error: The request timed out: {e}")
    elif isinstance(e, requests.exceptions.RequestException):
        printers.error_print(f"Error: An error occurred during the request: {e}")
    else:
        printers.error_print(f"An unexpected error occurred: {e}")
    return None, None


def fetch_akamai_headers(
    url: str,
    pragma_directives: list[str] | None = None,
    timeout: int = 10,
    *,
    verbose: bool = False,
    no_color: bool = False,
) -> tuple[int | None, Mapping[str, str] | None]:
    """Fetch HTTP headers from a URL with Akamai pragma directives.

    Args:
        url: The URL to fetch headers from.
        pragma_directives: List of Akamai pragma headers to send.
        timeout: Request timeout in seconds.
        verbose: Whether to print verbose output.
        no_color: Whether to disable colored output.

    Returns:
        A tuple of (status_code, response_headers).

    """
    if pragma_directives is None:
        pragma_directives = DEFAULT_AKAMAI_PRAGMA_HEADERS

    pragma_value = ", ".join(pragma_directives)
    req_headers = {
        "Pragma": pragma_value,
        "User-Agent": "Mozilla/5.0 (AkCurl; Akamai Header Analyzer)",
    }

    if verbose:
        _print_request_details(url, timeout, req_headers, no_color=no_color)

    try:
        response = requests.get(url, headers=req_headers, timeout=timeout, allow_redirects=True)
    except Exception as e:  # noqa: BLE001
        return _handle_request_error(e, verbose=verbose)
    else:
        final_status = response.status_code

        if verbose:
            printers.verbose_print("--- Response Details ---")
            printers.verbose_print(f"Status: {final_status}")
            printers.verbose_print(f"Final URL: {response.url}")
            printers.verbose_print(f"Redirects: {len(response.history)}")
            printers.verbose_print("")

        return final_status, response.headers


def _print_request_details(url: str, timeout: int, req_headers: dict[str, str], *, no_color: bool) -> None:
    """Print request parameters for verbose mode.

    Args:
        url: The URL being requested.
        timeout: The request timeout.
        req_headers: The headers being sent.
        no_color: Whether to disable colored output.

    """
    printers.verbose_print(f"Requesting URL: {url}")
    printers.verbose_print("Method: GET")
    printers.verbose_print(f"Timeout: {timeout}s")
    printers.verbose_print("Headers Sent:")
    for k, v in req_headers.items():
        style_marker = "[dim]" if not no_color and _rich_available else ""
        end_marker = "[/]" if not no_color and _rich_available else ""
        printers.verbose_print(f"  {style_marker}{k}{end_marker}: {v}")
    printers.verbose_print("")


def _print_headers(headers: Mapping[str, str], *, no_color: bool) -> None:
    """Print headers with optional styling.

    Args:
        headers: The headers to print.
        no_color: Whether to disable colored output.

    """
    sorted_keys = sorted(headers.keys())

    for key in sorted_keys:
        value = headers[key]
        lower_key = key.lower()

        if _rich_available and not no_color:
            key_style, value_style = get_styles(key)
            key_text = RichText.from_markup(f"[{key_style}]{key}:[/]")
            indent = "  "

            if lower_key in HEADERS_TO_SPLIT and "," in value:
                printers.console_print(key_text)
                parts = re.split(r",\s*", value)
                for part in parts:
                    cleaned_part = part.strip()
                    if cleaned_part:
                        value_text = RichText.from_markup(f"[{value_style}]{indent}{cleaned_part}[/]")
                        printers.console_print(value_text)
            else:
                value_text = RichText.from_markup(f"[{value_style}] {value}[/]")
                printers.console_print(key_text + value_text)
        elif lower_key in HEADERS_TO_SPLIT and "," in value:
            printers.console_print(f"{key}:")
            parts = re.split(r",\s*", value)
            for part in parts:
                cleaned_part = part.strip()
                if cleaned_part:
                    printers.console_print(f"  {cleaned_part}")
        else:
            printers.console_print(f"{key}: {value}")


def main() -> None:
    """Entry point for the AkCurl script."""
    parser = argparse.ArgumentParser(
        description="Fetch and analyze Akamai HTTP headers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    pos_group = parser.add_argument_group("Required Argument")
    pragma_group = parser.add_argument_group("Pragma Header Options (choose one or none)")
    opt_group = parser.add_argument_group("Optional Arguments")

    pos_group.add_argument("url", help="The URL to analyze.")
    pragma_group.add_argument("-p", "--pragma", nargs="+", help="Specify one or more custom Akamai Pragma directives.")
    pragma_group.add_argument(
        "-d",
        "--default-pragma",
        action="store_true",
        help="Use the internal default list of Akamai Pragma directives.",
    )
    opt_group.add_argument("-v", "--verbose", action="store_true", help="print verbose debug information to stderr.")
    opt_group.add_argument("-t", "--timeout", type=int, default=10, help="request timeout in seconds.")
    opt_group.add_argument("--no-color", action="store_true", help="Disable rich colored output.")

    args = parser.parse_args()

    url = args.url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    setup_printers(no_color=args.no_color)

    if args.pragma:
        pragma_directives_to_use = args.pragma
        if args.verbose:
            printers.verbose_print(f"Using specified Pragma directives: {pragma_directives_to_use}\n")
    else:
        pragma_directives_to_use = DEFAULT_AKAMAI_PRAGMA_HEADERS
        if args.verbose:
            printers.verbose_print(f"Using default Akamai Pragma directives: {pragma_directives_to_use}\n")

    status, headers = fetch_akamai_headers(
        url,
        pragma_directives=pragma_directives_to_use,
        timeout=args.timeout,
        verbose=args.verbose,
        no_color=args.no_color,
    )

    if status is not None and headers is not None:
        printers.console_print(f"HTTP Status: {status}")
        printers.console_print("-" * 40)
        _print_headers(headers, no_color=args.no_color)
        sys.exit(0)

    printers.error_print("Failed to retrieve headers.")
    sys.exit(1)


if __name__ == "__main__":
    main()

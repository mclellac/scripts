#!/usr/bin/env python3

import argparse
import requests
import sys
from urllib.parse import urlparse
import re

try:
    from rich.console import Console
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

    class Console:
        pass

    class Text:
        def __init__(self, text, style=None):
            self.text = text

        @staticmethod
        def from_markup(markup):
            return Text(re.sub(r"\[.*?\]", "", markup))

        def __add__(self, other):
            return Text(self.text + other.text)

        def __str__(self):
            return self.text

    # Removed dummy Panel class

console_print = None
error_print = None
verbose_print = None

STYLE_AKAMAI_KEY = "bold dim cyan"
STYLE_XCACHE_KEY = "bold dim magenta"
STYLE_CACHE_KEY = "bold dim green"
STYLE_COOKIE_KEY = "bold dim purple"
STYLE_CONTENT_KEY = "bold dim yellow"
STYLE_SECURITY_KEY = "bold dim orange_red1"
STYLE_REDIRECT_KEY = "bold dim blue"
STYLE_DEFAULT_KEY = "bold dim"

STYLE_AKAMAI_VALUE = "bright_cyan"
STYLE_XCACHE_VALUE = "bright_magenta"
STYLE_CACHE_VALUE = "bright_green"
STYLE_COOKIE_VALUE = "bright_purple"
STYLE_CONTENT_VALUE = "bright_yellow"
STYLE_SECURITY_VALUE = "bright_red"
STYLE_REDIRECT_VALUE = "bright_blue"
STYLE_DEFAULT_VALUE = "white"


def setup_printers(no_color):
    """Initializes print functions based on the no_color flag."""
    global console_print, error_print, verbose_print

    if no_color or not RICH_AVAILABLE:
        if not no_color and not RICH_AVAILABLE:
            print(
                "Warning: 'rich' library not found. Falling back to plain text output.",
                file=sys.stderr,
            )
            print("Install it ('pip install rich') for colored output.", file=sys.stderr)

        def _print_std(*args, **kwargs):
            kwargs.pop("style", None)
            print(*args, **kwargs)

        def _print_err(*args, **kwargs):
            kwargs.pop("style", None)
            print(*args, file=sys.stderr, **kwargs)

        console_print = _print_std
        error_print = _print_err
        verbose_print = _print_err

    else:
        try:
            from rich.console import Console as RichConsole

            _console = RichConsole(highlight=False)
            _error_console = RichConsole(stderr=True, style="bold red")
            _verbose_console = RichConsole(stderr=True)

            console_print = _console.print
            error_print = _error_console.print
            verbose_print = _verbose_console.print
        except ImportError:
            print("Error: 'rich' library failed to import despite being expected.", file=sys.stderr)
            sys.exit(1)


def get_styles(header_name):
    """Determines the rich style pair (key_style, value_style) for a header."""
    lower_key = header_name.lower()

    if lower_key.startswith("x-cache"):
        return STYLE_XCACHE_KEY, STYLE_XCACHE_VALUE
    elif lower_key.startswith(("x-akamai-", "x-feo", "x-serial", "x-check-cacheable")):
        return STYLE_AKAMAI_KEY, STYLE_AKAMAI_VALUE
    elif lower_key == "server" and "akamai" in header_name.lower():
        return STYLE_AKAMAI_KEY, STYLE_AKAMAI_VALUE
    elif lower_key in [
        "cache-control",
        "pragma",
        "expires",
        "age",
        "vary",
        "etag",
        "last-modified",
    ]:
        return STYLE_CACHE_KEY, STYLE_CACHE_VALUE
    elif lower_key == "set-cookie":
        return STYLE_COOKIE_KEY, STYLE_COOKIE_VALUE
    elif lower_key.startswith("content-"):
        return STYLE_CONTENT_KEY, STYLE_CONTENT_VALUE
    elif lower_key in [
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
        "x-xss-protection",
        "referrer-policy",
        "permissions-policy",
    ]:
        return STYLE_SECURITY_KEY, STYLE_SECURITY_VALUE
    elif lower_key == "location":
        return STYLE_REDIRECT_KEY, STYLE_REDIRECT_VALUE
    else:
        return STYLE_DEFAULT_KEY, STYLE_DEFAULT_VALUE


DEFAULT_AKAMAI_PRAGMA_HEADERS = [
    "akamai-x-cache-on",
    "akamai-x-cache-remote-on",
    "akamai-x-check-cacheable",
    "akamai-x-get-cache-key",
    "akamai-x-get-extracted-values",
    "akamai-x-get-nonces",
    "akamai-x-get-request-id",
    "akamai-x-get-request-trace",
    "akamai-x-get-ssl-client-session-id",
    "akamai-x-get-true-cache-key",
    "akamai-x-serial-no",
    "akamai-x-feo-trace",
    "akamai-x-get-client-ip",
    "x-akamai-logging-mode: verbose",
]

HEADERS_TO_SPLIT = {
    "x-akamai-session-info",
    "x-akamai-a2-trace",
    "accept-ch",
}


def fetch_akamai_headers(url, pragma_directives, verbose=False, timeout=10, no_color=False):
    """
    Fetches headers from a URL with specified Akamai Pragma directives.
    Returns a tuple: (final_status_code, response_headers_dict or None)
    """
    final_status = None
    if not pragma_directives:
        req_headers = {}
    else:
        pragma_value = ",".join(pragma_directives)
        req_headers = {"Pragma": pragma_value}

    req_headers["User-Agent"] = "CBC/Akamai cURL/1.0"

    if verbose:
        verbose_print(
            "--- Request Details ---", style="blue" if not no_color and RICH_AVAILABLE else None
        )
        verbose_print(f"URL: {url}")
        verbose_print(f"Method: GET")
        verbose_print(f"Timeout: {timeout}s")
        verbose_print(f"Headers Sent:")
        for k, v in req_headers.items():
            if not no_color and RICH_AVAILABLE:
                verbose_print(f"  [dim]{k}[/]: {v}")
            else:
                verbose_print(f"  {k}: {v}")
        verbose_print(
            "---------------------", style="blue" if not no_color and RICH_AVAILABLE else None
        )

    try:
        response = requests.get(url, headers=req_headers, timeout=timeout, allow_redirects=True)
        final_status = response.status_code
        response.raise_for_status()

        if verbose:
            status_code_str = f"{response.status_code}"
            final_url_str = f"{response.url}"
            history_lines = []
            if response.history:
                history_lines.append("Redirect History:")
                for i, resp in enumerate(response.history):
                    history_lines.append(f"  {i + 1}: {resp.status_code} {resp.url}")

            verbose_print(
                "--- Response Details ---",
                style="green"
                if response.ok
                else "red"
                if not no_color and RICH_AVAILABLE
                else None,
            )
            if not no_color and RICH_AVAILABLE:
                status_color = get_status_color(response.status_code)
                verbose_print(f"[bold]Status Code:[/bold] [{status_color}]{status_code_str}[/]")
                if history_lines:
                    verbose_print("[bold]Redirect History:[/bold]")
                    for i, resp in enumerate(response.history):
                        verbose_print(
                            f"  {i + 1}: [{get_status_color(resp.status_code)}]{resp.status_code}[/] [dim]{resp.url}[/]"
                        )
                    verbose_print(f"[bold]Final URL:[/bold] [dim]{final_url_str}[/]")
                else:
                    verbose_print(f"[bold]Final URL:[/bold] [dim]{final_url_str}[/]")
            else:
                verbose_print(f"Status Code: {status_code_str}")
                for line in history_lines:
                    verbose_print(line)
                verbose_print(f"Final URL: {final_url_str}")
            verbose_print(
                "----------------------",
                style="green"
                if response.ok
                else "red"
                if not no_color and RICH_AVAILABLE
                else None,
            )

        return final_status, response.headers

    except requests.exceptions.Timeout:
        error_print(f"Error: Request timed out after {timeout} seconds.")
    except requests.exceptions.SSLError as e:
        error_print(f"Error: SSL certificate verification failed: {e}")
    except requests.exceptions.ConnectionError as e:
        error_print(f"Error: Could not connect to the server: {e}")
    except requests.exceptions.HTTPError as e:
        final_status = e.response.status_code
        if not verbose:
            error_print(f"Error: HTTP {final_status} for url {e.request.url}")
        # No need for elif verbose here, status/headers returned below if available
        return final_status, e.response.headers  # Return status/headers even on HTTP error
    except requests.exceptions.RequestException as e:
        error_print(f"Error: An error occurred during the request: {e}")
    except Exception as e:
        error_print(f"An unexpected error occurred: {e}")

    return final_status, None


def get_status_color(status_code):
    """Return a color style based on HTTP status code."""
    if not status_code:
        return "white"
    if 200 <= status_code < 300:
        return "green"
    elif 300 <= status_code < 400:
        return "blue"
    elif 400 <= status_code < 500:
        return "yellow"
    else:
        return "red"


def is_valid_url(url_string):
    """Basic check if the string looks like a valid HTTP/HTTPS URL."""
    if not isinstance(url_string, str):
        return False
    try:
        result = urlparse(url_string)
        return all([result.scheme in ["http", "https"], result.netloc])
    except ValueError:
        return False


def main():
    """Parses arguments and fetches/prints Akamai headers for a given URL."""
    default_pragma_str = ",".join(DEFAULT_AKAMAI_PRAGMA_HEADERS)
    all_help_text = f"request all default Akamai Pragma directives:\n({default_pragma_str})"

    parser = argparse.ArgumentParser(
        description="Fetch HTTP headers from a URL with specified Akamai Pragma directives.",
        epilog="Examples:\n"
        "  %(prog)s https://www.example.com\n"
        "  %(prog)s -p akamai-x-get-cache-key https://www.example.com\n"
        "  %(prog)s -v --no-color https://www.example.com",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    pos_group = parser.add_argument_group("Required Argument")
    pragma_group = parser.add_argument_group("Pragma Header Options (choose one or none)")
    opt_group = parser.add_argument_group("Other Options")

    pos_group.add_argument("url", metavar="URL", help="The URL to fetch headers from.")

    mx_group = pragma_group.add_mutually_exclusive_group()
    mx_group.add_argument(
        "-p",
        "--pragma",
        nargs="+",
        metavar="DIRECTIVE",
        help="request specific Akamai Pragma directive(s).",
    )
    mx_group.add_argument("-a", "--all", action="store_true", help=all_help_text)

    opt_group.add_argument(
        "-v", "--verbose", action="store_true", help="print verbose debug information to stderr."
    )
    opt_group.add_argument(
        "-t", "--timeout", type=int, default=10, metavar="SEC", help="request timeout in seconds."
    )
    opt_group.add_argument("--no-color", action="store_true", help="disable colored output.")

    if "-h" in sys.argv or "--help" in sys.argv:
        parser.print_help()
        sys.exit(0)

    try:
        args = parser.parse_args()
    except SystemExit as e:
        sys.exit(e.code)

    setup_printers(args.no_color)

    if not is_valid_url(args.url):
        error_print(f"Error: Invalid URL provided: '{args.url}'")
        sys.exit(1)

    if args.pragma:
        pragma_directives_to_use = args.pragma
        if args.verbose:
            verbose_print(f"Using specified Pragma directives: {pragma_directives_to_use}\n")
    else:
        pragma_directives_to_use = DEFAULT_AKAMAI_PRAGMA_HEADERS
        if args.verbose:
            verbose_print(
                f"Using default Pragma directives: {','.join(pragma_directives_to_use)}\n"
            )

    final_status, headers = fetch_akamai_headers(
        args.url, pragma_directives_to_use, args.verbose, args.timeout, args.no_color
    )

    if final_status is not None:
        status_style = get_status_color(final_status)
        status_prefix = "- Status Code:"
        if args.no_color or not RICH_AVAILABLE:
            console_print(f"{status_prefix} {final_status}")
        else:
            console_print(f"[{status_style}]{status_prefix} {final_status}[/]")

    if headers is not None:
        for key, value in sorted(headers.items(), key=lambda item: item[0].lower()):
            lower_key = key.lower()

            if args.no_color or not RICH_AVAILABLE:
                indent = "  "
                if lower_key in HEADERS_TO_SPLIT and "," in value:
                    parts = re.split(r",\s*", value)
                    console_print(f"{key}:")
                    for part in parts:
                        cleaned_part = part.strip()
                        if cleaned_part:
                            console_print(f"{indent}{cleaned_part}")
                else:
                    console_print(f"{key}: {value}")
            else:
                key_style, value_style = get_styles(key)
                if RICH_AVAILABLE:
                    from rich.text import Text as RichText
                else:
                    RichText = Text
                key_text = RichText.from_markup(f"[{key_style}]{key}:[/]")
                indent = "  "

                if lower_key in HEADERS_TO_SPLIT and "," in value:
                    console_print(key_text)
                    parts = re.split(r",\s*", value)
                    for part in parts:
                        cleaned_part = part.strip()
                        if cleaned_part:
                            value_text = RichText.from_markup(
                                f"[{value_style}]{indent}{cleaned_part}[/]"
                            )
                            console_print(value_text)
                else:
                    value_text = RichText.from_markup(f"[{value_style}] {value}[/]")
                    console_print(key_text + value_text)

        sys.exit(0)

    else:
        error_print("Failed to retrieve headers.")
        sys.exit(1)


if __name__ == "__main__":
    main()

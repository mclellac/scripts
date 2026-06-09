#!/usr/bin/env python3
"""Module for fetching and providing an 'ELI5' explanation of Akamai headers."""

from __future__ import annotations

import http.client
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Callable, cast

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

        def print(self, *_args: object, **kwargs: object) -> None:
            """Print a message to the console with minimal formatting."""
            kwargs.pop("style", None)
            kwargs.pop("highlight", None)
            file = sys.stderr if kwargs.pop("stderr", False) else sys.stdout
            file.write(" ".join(map(str, _args)) + "\n")

    class _FallbackText:
        """Fallback for rich.text.Text."""

        def __init__(self, text: object, style: str | None = None) -> None:
            """Initialize the fallback text."""
            self.text = str(text)
            self.style = style

        @staticmethod
        def from_markup(markup: str) -> _FallbackText:
            """Create a RichText object from markup."""
            return _FallbackText(re.sub(r"\[.*?\]", "", markup))

        def __add__(self, other: object) -> _FallbackText:
            """Add two RichText objects together."""
            return _FallbackText(self.text + str(other))

        def __radd__(self, other: object) -> _FallbackText:
            """Add a RichText object to a string."""
            return _FallbackText(str(other) + self.text)

        def __str__(self) -> str:
            """Return the string representation of the text."""
            return self.text

    RichConsole = _FallbackConsole
    RichText = _FallbackText


console_print: Callable[..., object] = print


def error_print(*args: object, **_kwargs: object) -> int:
    """Print an error message to stderr."""
    return sys.stderr.write(" ".join(map(str, args)) + "\n")


Console = RichConsole
Text = RichText


STYLE_ANALYSIS_HEADER: str = "bold underline"
STYLE_ANALYSIS_VALUE: str = "white"
STYLE_ANALYSIS_NA: str = "dim"
STYLE_ELI5_HIGHLIGHT: str = "bold magenta"

DEFAULT_AKAMAI_PRAGMA_HEADERS: list[str] = [
    "akamai-x-cache-on",
    "akamai-x-cache-remote-on",
    "akamai-x-check-cacheable",
    "akamai-x-get-cache-key",
    "akamai-x-get-true-cache-key",
    "akamai-x-get-extracted-values",
    "akamai-x-get-ssl-client-session-id",
    "akamai-x-serial-no",
    "akamai-x-feo-trace",
    "akamai-x-get-request-id",
]


def _format_ttl(ttl_seconds: int | None) -> str:
    """Format TTL seconds into a human-readable string.

    Args:
        ttl_seconds: The TTL in seconds.

    Returns:
        A formatted string like '2h 15m 30s'.

    """
    if ttl_seconds is None:
        return "N/A"
    if ttl_seconds < 0:
        return "Expired"

    hours, rem = divmod(ttl_seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    parts: list[str] = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def _parse_origin_ttl(headers: Mapping[str, str]) -> tuple[int, str]:
    """Calculate the remaining TTL based on Cache-Control or Expires headers.

    Args:
        headers: The response headers.

    Returns:
        A tuple of (ttl_seconds, source_description).

    """
    # 1. Check Cache-Control: max-age
    cache_control = headers.get("cache-control", "").lower()
    if "max-age=" in cache_control:
        return _parse_max_age(cache_control, headers)

    # 2. Check Expires header
    expires = headers.get("expires")
    if expires:
        return _parse_expires(expires)

    return 0, "N/A"


def _parse_max_age(cache_control: str, headers: Mapping[str, str]) -> tuple[int, str]:
    """Parse max-age from Cache-Control header.

    Args:
        cache_control: The Cache-Control header value.
        headers: The full response headers.

    Returns:
        A tuple of (ttl_seconds, source_description).

    """
    match = re.search(r"max-age=(\d+)", cache_control)
    if match:
        try:
            ttl_seconds = int(match.group(1))
            source = "Cache-Control: max-age"

            # If Age header exists, subtract it
            age = headers.get("age")
            if age:
                ttl_seconds -= int(age)
                source += " (adjusted by Age)"
            return max(0, ttl_seconds), source
        except (ValueError, IndexError):
            pass
    return 0, "N/A"


def _parse_expires(expires: str) -> tuple[int, str]:
    """Parse TTL from Expires header.

    Args:
        expires: The Expires header value.

    Returns:
        A tuple of (ttl_seconds, source_description).

    """
    try:
        expires_dt = parsedate_to_datetime(expires)
        now = datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return 0, "N/A"
    else:
        if expires_dt > now:
            ttl_seconds = int((expires_dt - now).total_seconds())
            source = "Expires header"
        else:
            ttl_seconds = 0
            source = "Expires header (past date)"
        return ttl_seconds, source


def print_cache_control_explanation(cache_control_val: str) -> None:
    """Print an ELI5 explanation for common Cache-Control directives.

    Args:
        cache_control_val: The value of the Cache-Control header.

    """
    val = cache_control_val.lower()
    explanations = _get_cache_control_explanations(val)

    if explanations:
        console_print(f"[{STYLE_ELI5_HIGHLIGHT}]ELI5:[/] Cache-Control says:")
        for exp in explanations:
            console_print(f"  • {exp}")


def _get_cache_control_explanations(val: str) -> list[str]:
    """Extract human-readable explanations from Cache-Control value.

    Args:
        val: The lowercased Cache-Control header value.

    Returns:
        A list of explanation strings.

    """
    explanations: list[str] = []
    if "public" in val:
        explanations.append("Allowed to be cached by everyone (browsers, CDNs).")
    if "private" in val:
        explanations.append("Only meant for the user's browser, not for CDNs.")
    if "no-cache" in val:
        explanations.append("Must check with the server before using a cached copy.")
    if "no-store" in val:
        explanations.append("Do not save this at all. Ever.")
    if "must-revalidate" in val:
        explanations.append("Once it expires, do not use it without re-checking.")

    _extract_max_age_explanation(val, explanations)
    return explanations


def _extract_max_age_explanation(val: str, explanations: list[str]) -> None:
    """Extract max-age and s-maxage explanations.

    Args:
        val: The lowercased Cache-Control header value.
        explanations: The list to append explanations to.

    """
    match = re.search(r"max-age=(\d+)", val)
    if match:
        try:
            sec = int(match.group(1))
            explanations.append(f"Tells caches to keep it for {_format_ttl(sec)}.")
        except ValueError:
            pass

    match_s = re.search(r"s-maxage=(\d+)", val)
    if match_s:
        try:
            sec_s = int(match_s.group(1))
            explanations.append(f"Tells CDNs (like Akamai) to keep it for {_format_ttl(sec_s)}.")
        except ValueError:
            pass


def parse_cache_key(key: str) -> dict[str, str]:
    """Parse an Akamai cache key into its components.

    Args:
        key: The raw cache key string.

    Returns:
        A dictionary containing parsed components like 'CP Code', 'TTL', etc.

    """
    info_dict: dict[str, str] = {}
    parts = key.split("/")
    for part in parts:
        if ":" in part:
            name_part, value_part = part.split(":", 1)
            info_dict[name_part] = value_part
    return info_dict


def extract_analysis_data(headers: Mapping[str, str]) -> dict[str, object]:
    """Extract and organize key data points from headers for analysis.

    Args:
        headers: The HTTP response headers.

    Returns:
        A dictionary of analysis results.

    """
    data: dict[str, object] = {}
    headers_lower = {k.lower(): v for k, v in headers.items()}

    data["cache_status_raw"] = headers_lower.get("x-cache", "N/A")
    data["cache_remote_status_raw"] = headers_lower.get("x-cache-remote", "N/A")

    # Determine simplified Cache Status
    if "TCP_HIT" in str(data["cache_status_raw"]):
        data["cache_status"] = "HIT (Akamai Edge)"
    elif "TCP_MISS" in str(data["cache_status_raw"]):
        data["cache_status"] = "MISS (Fetched from Origin)"
    elif "TCP_REFRESH_HIT" in str(data["cache_status_raw"]):
        data["cache_status"] = "REFRESH_HIT (Revalidated with Origin)"
    else:
        data["cache_status"] = "Unknown"

    cache_key_raw = headers_lower.get("x-cache-key", "N/A")
    data["cache_key_raw"] = cache_key_raw
    data["cache_key_parsed"] = parse_cache_key(cache_key_raw) if cache_key_raw != "N/A" else {}
    data["true_cache_key_raw"] = headers_lower.get("x-true-cache-key", "N/A")

    data["ttl_seconds"], data["ttl_source"] = _parse_origin_ttl(headers_lower)

    data["server"] = headers_lower.get("server", "N/A")
    data["request_id"] = headers_lower.get("x-akamai-request-id", "N/A")
    data["serial_no"] = headers_lower.get("x-serial", "N/A")

    return data


def print_analysis(analysis_data: dict[str, object]) -> None:
    """Print the formatted analysis to the console.

    Args:
        analysis_data: The dictionary of analysis results to display.

    """
    # Analysis Title
    console_print(Text("\n--- Akamai Header Analysis ---", style=STYLE_ANALYSIS_HEADER))

    # Cache Status
    status_text = Text("Cache Status: ", style=STYLE_ANALYSIS_VALUE)
    cache_status = str(analysis_data.get("cache_status", "Unknown"))
    status_style = "green" if "HIT" in cache_status else "yellow"
    status_text += Text(cache_status, style=status_style)
    console_print(status_text)

    # TTL
    ttl_text = Text("Estimated Origin TTL: ", style=STYLE_ANALYSIS_VALUE)
    ttl_seconds = analysis_data.get("ttl_seconds")
    ttl_val = _format_ttl(int(ttl_seconds)) if isinstance(ttl_seconds, int) else "N/A"
    ttl_text += Text(ttl_val, style="cyan")
    ttl_text += Text(f" (Source: {analysis_data.get('ttl_source', 'N/A')})", style="dim")
    console_print(ttl_text)

    # Server info
    console_print(Text(f"Edge Server: {analysis_data.get('server', 'N/A')}", style=STYLE_ANALYSIS_VALUE))
    console_print(Text(f"Request ID: {analysis_data.get('request_id', 'N/A')}", style=STYLE_ANALYSIS_VALUE))

    # Cache Key breakdown
    cache_key_parsed = analysis_data.get("cache_key_parsed")
    if isinstance(cache_key_parsed, dict):
        cache_key_dict = cast("dict[str, str]", cache_key_parsed)
        console_print(Text("\nCache Key Details:", style=STYLE_ANALYSIS_HEADER))
        for k, v in cache_key_dict.items():
            console_print(Text(f"  • {k}: ", style=STYLE_ANALYSIS_VALUE) + Text(str(v), style="dim"))

    console_print("")


def fetch_headers_for_analysis(url: str, timeout: int = 10) -> tuple[int | None, Mapping[str, str] | None]:
    """Fetch headers from a URL using default Akamai Pragma directives.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        A tuple of (status_code, response_headers).

    """
    pragma_value = ",".join(DEFAULT_AKAMAI_PRAGMA_HEADERS)
    req_headers = {"Pragma": pragma_value, "User-Agent": "CBC/Akamai Ananysis/1.0"}

    try:
        response = requests.get(url, headers=req_headers, timeout=timeout, allow_redirects=True)
    except requests.exceptions.HTTPError as e:
        if e.response is not None:
            error_print(f"Error: An error occurred during the request: {e} (Status: {e.response.status_code})")
            return e.response.status_code, e.response.headers
        error_print(f"Error: An error occurred during the request: {e}")
    except (requests.exceptions.RequestException, http.client.HTTPException) as e:
        error_print(f"Error: An error occurred during the request: {e}")
    else:
        return response.status_code, response.headers

    return None, None


def main() -> None:
    """Entry point for the AkEli5 script."""
    arg_count_threshold = 2
    if len(sys.argv) < arg_count_threshold:
        console_print("Usage: akeli5 <URL>")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    _, headers = fetch_headers_for_analysis(url)

    if headers:
        analysis = extract_analysis_data(headers)
        print_analysis(analysis)

        cc = headers.get("cache-control")
        if cc:
            print_cache_control_explanation(cc)

        sys.exit(0)
    else:
        error_print("Failed to fetch headers for analysis.")
        sys.exit(1)


if __name__ == "__main__":
    main()

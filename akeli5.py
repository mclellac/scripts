#!/usr/bin/env python3

import requests
import sys
from urllib.parse import urlparse, unquote
import re
from email.utils import parsedate_to_datetime
from typing import Optional, Tuple, Dict, Any, Callable
import http.client  # for HTTPException

try:
    from rich.console import Console
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

    class Console:
        def print(self, *args, **kwargs):
            print(*args)

    class Text:
        def __init__(self, text, style=None):
            self.text = str(text)

        @staticmethod
        def from_markup(markup):
            return Text(re.sub(r"\[.*?\]", "", markup))

        def __add__(self, other):
            other_text = str(other)
            return Text(self.text + other_text)

        def __radd__(self, other):
            other_text = str(other)
            return Text(other_text + self.text)

        def __str__(self):
            return self.text


console_print: Optional[Callable] = None
error_print: Optional[Callable] = None

STYLE_ANALYSIS_HEADER = "bold underline"
STYLE_ANALYSIS_VALUE = "white"
STYLE_ANALYSIS_NA = "dim"
STYLE_ELI5_HIGHLIGHT = "bold magenta"

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


def is_valid_url(url_string: Optional[str]) -> bool:
    """Basic check if the string looks like a valid HTTP/HTTPS URL."""
    if not isinstance(url_string, str):
        return False
    try:
        result = urlparse(url_string)
        return all([result.scheme in ["http", "https"], result.netloc])
    except ValueError:
        return False


def setup_printers():
    """Initializes print functions using rich."""
    global console_print, error_print
    try:
        _console = Console(highlight=False)
        _error_console = Console(stderr=True, style="bold red")
        console_print = _console.print
        error_print = _error_console.print
    except Exception as e:
        print(
            f"Error initializing rich: {e}. Falling back to plain text.",
            file=sys.stderr,
        )

        def _print_plain_std(*args, **kwargs):
            print(*args, **kwargs)

        def _print_plain_err(*args, **kwargs):
            print(*args, file=sys.stderr, **kwargs)

        console_print = _print_plain_std
        error_print = _print_plain_err


def parse_session_info(session_info_value: Optional[str]) -> Dict[str, str]:
    """Parses the X-Akamai-Session-Info header value into a dictionary."""
    info_dict = {}
    if not session_info_value or not isinstance(session_info_value, str):
        return info_dict
    pairs = session_info_value.split(",")
    for pair in pairs:
        if "name=" in pair and "; value=" in pair:
            parts = pair.split("; value=", 1)
            name_part = parts[0].replace("name=", "").strip()
            value_part = parts[1].strip()
            if "; full_location_id=" in value_part:
                value_part = value_part.split("; full_location_id=")[0]
            if name_part == "UA_IDENTIFIER":
                try:
                    value_part = unquote(value_part)
                except Exception:
                    pass
            info_dict[name_part] = value_part
    return info_dict


def extract_analysis_data(headers: Dict[str, str]) -> Dict[str, Any]:
    """Extracts and organizes key data points from headers for analysis."""
    data = {}
    headers_lower = {k.lower(): v for k, v in headers.items()}

    data["cache_status_raw"] = headers_lower.get("x-cache", "N/A")
    data["cache_status"] = (
        data["cache_status_raw"].split(" ")[0]
        if data["cache_status_raw"] != "N/A"
        else "N/A"
    )
    data["cache_server_hostname"] = (
        data["cache_status_raw"].split(" from ")[1].split(" ")[0]
        if " from " in data["cache_status_raw"]
        else "N/A"
    )
    data["cacheability"] = headers_lower.get("x-check-cacheable", "N/A")
    data["cache_key"] = headers_lower.get("x-cache-key", "N/A")
    data["true_cache_key"] = headers_lower.get("x-true-cache-key", "N/A")
    data["edge_server"] = headers_lower.get("x-cache-server", "N/A")
    data["serial"] = headers_lower.get("x-serial", "N/A")
    data["request_id"] = headers_lower.get("x-akamai-request-id", "N/A")
    data["client_ip"] = (
        headers_lower.get("x-akamai-pragma-client-ip", "N/A").split(",")[0].strip()
    )
    data["origin_server"] = headers_lower.get("x-origin-server", "N/A")
    data["midmile_rtt"] = headers_lower.get("x-edgeconnect-midmile-rtt", "N/A")
    data["origin_latency"] = headers_lower.get(
        "x-edgeconnect-origin-mex-latency", "N/A"
    )
    data["date"] = headers_lower.get("date", "N/A")
    data["content_type"] = headers_lower.get("content-type", "N/A")
    data["content_length"] = headers_lower.get("content-length", "N/A")
    data["last_modified"] = headers_lower.get("last-modified", "N/A")
    data["etag"] = headers_lower.get("etag", "N/A")
    data["expires"] = headers_lower.get("expires", "N/A")
    data["cache_control"] = headers_lower.get("cache-control", "N/A")
    data["vary"] = headers_lower.get("vary", "N/A")
    data["akamai_network"] = (
        "Akamai Staging"
        if headers_lower.get("x-akamai-staging", "").upper() == "ESSL"
        else "Akamai Production"
    )

    session_info_raw = headers_lower.get("x-akamai-session-info", "")
    session_info_dict = parse_session_info(session_info_raw)
    data["property_name"] = session_info_dict.get("AKA_PM_PROPERTY_NAME", "N/A")
    data["property_version"] = session_info_dict.get("AKA_PM_PROPERTY_VERSION", "N/A")
    data["fwd_url"] = session_info_dict.get("AKA_PM_FWD_URL", "N/A")
    data["sr_enabled"] = session_info_dict.get("AKA_PM_SR_ENABLED", "N/A")
    data["td_enabled"] = session_info_dict.get("AKA_PM_TD_ENABLED", "N/A")
    data["client_city"] = session_info_dict.get("PMUSER_CITY", "N/A")
    data["client_country"] = session_info_dict.get("PMUSER_COUNTRY", "N/A")

    return data


def get_status_color(status_code: Optional[int]) -> str:
    """Return a rich color style string based on HTTP status code."""
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


def _format_variable(text: Any) -> Text:
    """Applies bold magenta styling using rich."""
    text_str = str(text) if text is not None else ""
    escaped_text = text_str.replace("[", "\\[").replace("]", "\\]")
    style = STYLE_ANALYSIS_NA if text_str == "unknown" else STYLE_ELI5_HIGHLIGHT
    return Text.from_markup(f"[{style}]{escaped_text}[/]")


def _get_analysis_value(
    data: Dict[str, Any], key: str, default: str = "unknown"
) -> str:
    """Gets value from analysis data dict, handling N/A."""
    val = data.get(key, default)
    return str(val) if val and val != "N/A" else default


def _parse_cache_key_ttl(cache_key: str) -> Optional[str]:
    """Extracts TTL string (e.g., '30s', '1d') from Akamai cache key."""
    if not cache_key or cache_key == "unknown":
        return None
    match = re.search(r"/(?:S/)?L/[^/]+/[^/]+/([^/]+)/", cache_key)
    return match.group(1) if match else None


def _format_ttl_string(ttl_seconds: Optional[int]) -> str:
    """Formats seconds into human-readable TTL string."""
    if ttl_seconds is None:
        return "unknown"
    if ttl_seconds == 0:
        return "0 seconds (effectively not cached or must revalidate)"
    if ttl_seconds < 60:
        return f"{ttl_seconds} seconds"
    if ttl_seconds < 3600:
        return f"{ttl_seconds // 60} minutes"
    if ttl_seconds < 86400:
        return f"{ttl_seconds // 3600} hours"
    return f"{ttl_seconds // 86400} days"


def _parse_origin_ttl(
    cache_control: str, expires: str, date_header: str
) -> Tuple[Optional[int], str]:
    """Parses Cache-Control and Expires to determine origin TTL in seconds."""
    ttl_seconds = None
    source = "unknown"
    if cache_control != "unknown":
        s_maxage_match = re.search(r"s-maxage=(\d+)", cache_control, re.IGNORECASE)
        maxage_match = re.search(r"max-age=(\d+)", cache_control, re.IGNORECASE)
        no_cache_match = re.search(
            r"no-cache|no-store|private", cache_control, re.IGNORECASE
        )

        if s_maxage_match:
            ttl_seconds = int(s_maxage_match.group(1))
            source = "s-maxage"
        elif maxage_match:
            ttl_seconds = int(maxage_match.group(1))
            source = "max-age"

        if no_cache_match:
            source = (
                f"{source} (overridden by no-cache/private)"
                if ttl_seconds and ttl_seconds > 0
                else "no-cache/private"
            )
            ttl_seconds = 0

    if ttl_seconds is None and expires != "unknown" and date_header != "unknown":
        try:
            expires_dt = parsedate_to_datetime(expires).replace(tzinfo=timezone.utc)
            date_dt = parsedate_to_datetime(date_header).replace(tzinfo=timezone.utc)
            if expires_dt > date_dt:
                ttl_seconds = int((expires_dt - date_dt).total_seconds())
                source = "Expires header"
            else:
                ttl_seconds = 0
                source = "Expires header (past date)"
        except Exception:
            pass

    return ttl_seconds, source


def print_cache_control_explanation(cache_control_val: str):
    """Prints explanation of Cache-Control header."""
    output_prefix = Text("  Explanation: ")
    if cache_control_val == "unknown":
        console_print(output_prefix + _format_variable("Not provided by origin."))
        return

    directives = [d.strip().lower() for d in cache_control_val.split(",")]
    explanation_parts = []

    if "public" in directives:
        explanation_parts.append(Text("Public (can be stored by any cache)"))
    if "private" in directives:
        explanation_parts.append(
            Text("Private (intended for single user, not shared caches)")
        )
    if "no-cache" in directives:
        explanation_parts.append(
            Text("No-Cache (cache must revalidate with origin before using)")
        )
    if "no-store" in directives:
        explanation_parts.append(Text("No-Store (cannot be cached anywhere)"))
    if "must-revalidate" in directives:
        explanation_parts.append(
            Text("Must-Revalidate (cache must revalidate once stale)")
        )

    maxage_match = re.search(r"max-age=(\d+)", cache_control_val, re.IGNORECASE)
    if maxage_match:
        secs = int(maxage_match.group(1))
        explanation_parts.append(
            Text("Max-Age (browser TTL): ") + _format_variable(_format_ttl_string(secs))
        )

    s_maxage_match = re.search(r"s-maxage=(\d+)", cache_control_val, re.IGNORECASE)
    if s_maxage_match:
        secs = int(s_maxage_match.group(1))
        explanation_parts.append(
            Text("S-Maxage (shared cache TTL): ")
            + _format_variable(_format_ttl_string(secs))
        )

    if not explanation_parts:
        console_print(
            output_prefix
            + Text("Contains directives: ")
            + _format_variable(cache_control_val)
        )
    else:
        output = output_prefix
        for i, part in enumerate(explanation_parts):
            output += part
            if i < len(explanation_parts) - 1:
                output += Text("; ")
        console_print(output)


def print_analysis(analysis_data: Dict[str, Any]):
    """Prints the formatted analysis with accurate explanations."""

    cache_status = _get_analysis_value(analysis_data, "cache_status")
    cache_server = _get_analysis_value(analysis_data, "cache_server_hostname")
    cacheable = _get_analysis_value(analysis_data, "cacheability")
    edge_server_id = _get_analysis_value(analysis_data, "edge_server")
    cache_key = _get_analysis_value(analysis_data, "cache_key")
    true_cache_key = _get_analysis_value(analysis_data, "true_cache_key")
    cache_control_val = _get_analysis_value(analysis_data, "cache_control")
    expires_val = _get_analysis_value(analysis_data, "expires")
    date_val = _get_analysis_value(analysis_data, "date")
    akamai_network = _get_analysis_value(analysis_data, "akamai_network", "Production")

    cache_key_ttl_str = _parse_cache_key_ttl(cache_key) or _parse_cache_key_ttl(
        true_cache_key
    )
    origin_ttl_seconds, origin_ttl_source = _parse_origin_ttl(
        cache_control_val, expires_val, date_val
    )
    origin_ttl_str = _format_ttl_string(origin_ttl_seconds)

    console_print(f"\n{_format_variable('1. Caching Behavior')}")
    line1 = Text("  Cache Status: ")
    if cache_status == "TCP_HIT" or cache_status == "TCP_MEM_HIT":
        line1 += (
            _format_variable(cache_status)
            + Text(" (Served from Akamai Edge server ")
            + _format_variable(cache_server)
            + Text(" ID: ")
            + _format_variable(edge_server_id)
            + Text(")")
        )
    elif cache_status == "TCP_MISS":
        line1 += _format_variable(cache_status) + Text(
            " (Akamai fetched content from the origin server)"
        )
    elif cache_status == "TCP_REFRESH_HIT":
        line1 += (
            _format_variable(cache_status)
            + Text(
                " (Akamai revalidated its cached copy with the origin; origin confirmed it was still valid. Served cached copy from "
            )
            + _format_variable(cache_server)
            + Text(" ID: ")
            + _format_variable(edge_server_id)
            + Text(")")
        )
    elif cache_status == "TCP_REFRESH_MISS":
        line1 += _format_variable(cache_status) + Text(
            " (Akamai revalidated its cached copy with the origin; origin sent updated content, which was served)"
        )
    elif cache_status == "TCP_CLIENT_REFRESH_MISS":
        line1 += _format_variable(cache_status) + Text(
            " (Client requested fresh copy, Akamai fetched from origin)"
        )
    elif cache_status != "unknown":
        line1 += (
            _format_variable(cache_status)
            + Text(" (Served from ")
            + _format_variable(cache_server)
            + Text(" ID: ")
            + _format_variable(edge_server_id)
            + Text(")")
        )
    else:
        line1 += _format_variable("Unknown")
    console_print(line1)

    line2 = Text("  Cacheability: ")
    if cacheable == "YES":
        line2 += _format_variable("YES") + Text(
            " (Akamai determined this content could be cached)"
        )
    elif cacheable == "NO":
        line2 += _format_variable("NO") + Text(
            " (Akamai determined this content should not be cached)"
        )
    else:
        line2 += _format_variable("Unknown")
    console_print(line2)

    line3 = Text("  Cache TTL: ")
    if cache_key_ttl_str:
        line3 += _format_variable(cache_key_ttl_str) + Text(
            " (According to Akamai's Cache Key)"
        )
    elif origin_ttl_seconds is not None:
        line3 += (
            _format_variable(origin_ttl_str)
            + Text(" (According to origin's ")
            + _format_variable(origin_ttl_source)
            + Text(" header)")
        )
    else:
        line3 += _format_variable("Unknown")
    console_print(line3)

    display_cache_key = cache_key if cache_key != "unknown" else true_cache_key
    if display_cache_key != "unknown":
        line4 = Text("  Cache Key: ") + _format_variable(display_cache_key)
        console_print(line4)

    if cache_control_val != "unknown":
        line_cc_raw = Text("  Cache-Control Raw: ") + _format_variable(
            cache_control_val
        )
        console_print(line_cc_raw)
        print_cache_control_explanation(cache_control_val)

    req_id = _get_analysis_value(analysis_data, "request_id")
    prop_name = _get_analysis_value(analysis_data, "property_name")
    prop_ver = _get_analysis_value(analysis_data, "property_version")
    sr_enabled = _get_analysis_value(analysis_data, "sr_enabled")

    console_print(f"\n{_format_variable('2. Akamai Processing')}")
    line5 = Text("  Request ID: ") + _format_variable(req_id)
    console_print(line5)

    line_net = Text("  Network: ") + _format_variable(akamai_network)
    console_print(line_net)

    line6 = Text("  Configuration: ")
    if prop_name != "unknown":
        line6 += (
            Text("'")
            + _format_variable(prop_name)
            + Text("' version ")
            + _format_variable(prop_ver)
        )
    else:
        line6 += _format_variable("Unknown")
    console_print(line6)

    line7 = Text("  SureRoute: ")
    if sr_enabled == "true":
        line7 += _format_variable("Enabled") + Text(
            " (Akamai optimized the path to origin)"
        )
    elif sr_enabled == "false":
        line7 += _format_variable("Disabled")
    else:
        line7 += _format_variable("Unknown")
    console_print(line7)

    client_ip = _get_analysis_value(analysis_data, "client_ip")
    city = _get_analysis_value(analysis_data, "client_city")
    country = _get_analysis_value(analysis_data, "client_country")
    origin = _get_analysis_value(analysis_data, "origin_server")

    console_print(f"\n{_format_variable('3. Connection Details')}")
    line8 = (
        Text("  Client IP: ")
        + _format_variable(client_ip)
        + Text(" (Geo-located near: ")
        + _format_variable(city)
        + Text(", ")
        + _format_variable(country)
        + Text(")")
    )
    console_print(line8)

    line9 = Text("  Origin Server: ") + _format_variable(origin)
    console_print(line9)

    mid_rtt = _get_analysis_value(analysis_data, "midmile_rtt")
    origin_lat = _get_analysis_value(analysis_data, "origin_latency")

    console_print(f"\n{_format_variable('4. Network Timing')}")
    line10 = Text("  ")
    has_timing = False
    if mid_rtt != "unknown":
        line10 += Text("MidMile RTT: ") + _format_variable(mid_rtt) + Text(" ms")
        has_timing = True
    if origin_lat != "unknown":
        if has_timing:
            line10 += Text(" | ")
        line10 += Text("Origin Latency: ") + _format_variable(origin_lat) + Text(" ms")
        has_timing = True
    if not has_timing:
        line10 += _format_variable("Timing data not available")
    console_print(line10)

    ctype = _get_analysis_value(analysis_data, "content_type")
    clen = _get_analysis_value(analysis_data, "content_length")
    lmod = _get_analysis_value(analysis_data, "last_modified")

    console_print(f"\n{_format_variable('5. Delivered Content Info')}")
    line11 = Text("  ")
    has_meta = False
    if ctype != "unknown":
        line11 += Text("Type: '") + _format_variable(ctype.split(";")[0]) + Text("'")
        has_meta = True
    if clen != "unknown":
        if has_meta:
            line11 += Text(" | ")
        line11 += Text("Size: ") + _format_variable(clen) + Text(" bytes")
        has_meta = True
    if lmod != "unknown":
        if has_meta:
            line11 += Text(" | ")
        line11 += Text("Last Modified: ") + _format_variable(lmod)
        has_meta = True
    if not has_meta:
        line11 += _format_variable("Metadata not available")
    console_print(line11)


def fetch_headers_for_analysis(
    url: str, timeout: int = 10
) -> Tuple[Optional[int], Optional[Dict[str, str]]]:
    """
    Fetches headers from a URL using default Akamai Pragma directives.
    Returns a tuple: (final_status_code, response_headers_dict or None)
    """
    final_status = None
    pragma_value = ",".join(DEFAULT_AKAMAI_PRAGMA_HEADERS)
    req_headers = {"Pragma": pragma_value}
    req_headers["User-Agent"] = "CBC/Akamai Ananysis/1.0"

    try:
        response = requests.get(
            url, headers=req_headers, timeout=timeout, allow_redirects=True
        )
        final_status = response.status_code
        return final_status, response.headers

    except requests.exceptions.Timeout:
        error_print(f"Error: Request timed out after {timeout} seconds.")
    except requests.exceptions.SSLError as e:
        error_print(f"Error: SSL certificate verification failed: {e}")
    except requests.exceptions.ConnectionError as e:
        # Catch the specific HTTPException for too many headers
        if (
            isinstance(e.args[0], tuple)
            and len(e.args[0]) > 1
            and isinstance(e.args[0][1], http.client.HTTPException)
        ):
            error_print(
                f"Error: Connection aborted - {e.args[0][1]}. The server sent too many headers."
            )
        else:
            error_print(f"Error: Could not connect to the server: {e}")
    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None:
            final_status = e.response.status_code
            error_print(
                f"Error: An error occurred during the request: {e} (Status: {final_status})"
            )
            return final_status, e.response.headers
        else:
            error_print(f"Error: An error occurred during the request: {e}")
    except Exception as e:
        error_print(f"An unexpected error occurred: {e}")

    return final_status, None


def main():
    """Fetches Akamai headers for a URL and prints an ELI5 analysis."""
    if len(sys.argv) != 2 or sys.argv[1] in ["-h", "--help"]:
        prog_name = sys.argv[0]
        print(f"Usage: {prog_name} URL")
        print(
            "\nFetch default Akamai Pragma headers for a URL and print an ELI5 analysis."
        )
        print("\nExample:")
        print(f"  {prog_name} https://www.example.com")
        sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"] else 1)

    url = sys.argv[1]
    timeout = 10

    setup_printers()

    if not is_valid_url(url):
        error_print(f"Error: Invalid URL provided: '{url}'")
        sys.exit(1)

    final_status, headers = fetch_headers_for_analysis(url, timeout)

    if final_status is not None:
        status_style = get_status_color(final_status)
        status_prefix = "Website answered with code:"
        print_func = error_print if headers is None else console_print
        # Use rich Text object directly for printing status
        print_func(
            Text(status_prefix + " ") + Text(str(final_status), style=status_style)
        )

    if headers is not None:
        analysis_data = extract_analysis_data(headers)
        print_analysis(analysis_data)
        exit_code = 0 if final_status and 200 <= final_status < 400 else 1
        sys.exit(exit_code)
    else:
        status_info = f" (Last status code: {final_status})" if final_status else ""
        error_print(f"Could not get headers from the website.{status_info}")
        sys.exit(1)


if __name__ == "__main__":
    main()

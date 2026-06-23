#!/usr/bin/env python3
import requests
import argparse
from rich.table import Table
from rich.console import Console
from rich.syntax import Syntax
import sys

def main():
    console = Console()
    parser = argparse.ArgumentParser(description='Make a POST request to the specified URL.')
    parser.add_argument('url', help='The URL to send the POST request to.')
    parser.add_argument('--cookie', help='Cookie header value')
    parser.add_argument('--cookie-file', help='Path to a file containing cookie data')
    parser.add_argument('--host', help='Overwrite host header')
    args = parser.parse_args()

    headers = {
        'Accept': '*/*',
        'Cache-Control': 'no-cache',
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/92.0.4515.159 Safari/537.36'),
        'Content-Type': 'application/json',
    }

    # C is for cookie. That's good enough for me.
    if args.cookie_file:
        try:
            with open(args.cookie_file, 'r', encoding='utf-8') as f:
                headers['Cookie'] = f.read().strip()
        except FileNotFoundError:
            console.print(f"[bold red]Error:[/bold red] Cookie file '{args.cookie_file}' not found.")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]Error reading cookie file:[/bold red] {e}")
            sys.exit(1)
    elif args.cookie:
        headers['Cookie'] = args.cookie

    if args.host:
        headers['host'] = args.host

    # GQL payload
    query = """#graphql
    query ($sourceId: String!) {
        relatedItems(
            sourceId: $sourceId
            formats: "story"
            first: 5
        ) {
            nodes {
                sourceId
                title
                section {
                    path
                }
                href: url
                updatedAt
            }
        }
    }"""

    data = {
        "query": query,
        "variables": {"sourceId": "1.7143586"}
    }

    console.print(f"[bold green]Making a POST request to {args.url}[/bold green]")

    try:
        response = requests.post(args.url, headers=headers, json=data)
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Request Error:[/bold red] {e}")
        sys.exit(1)

    # Display status code
    console.print(f"\n[bold]Status Code:[/bold] {response.status_code}")

    # Display request headers
    console.print("\n[bold cyan]Request Headers:[/bold cyan]")
    request_headers_table = Table(show_header=True, header_style="bold magenta")
    request_headers_table.add_column("Header", style="dim", width=25)
    request_headers_table.add_column("Value", overflow="fold")

    for key, value in response.request.headers.items():
        request_headers_table.add_row(key, value)

    console.print(request_headers_table)

    request_headers_str = ''.join(f"{key}: {value}\r\n" for key, value in response.request.headers.items())
    request_headers_size_kb = len(request_headers_str.encode('utf-8')) / 1024
    console.print(f"[bold yellow]Total Request Headers Size:[/bold yellow] {request_headers_size_kb:.2f} KB")

    console.print("\n[bold cyan]Response Headers:[/bold cyan]")
    response_headers_table = Table(show_header=True, header_style="bold magenta")
    response_headers_table.add_column("Header", style="dim", width=25)
    response_headers_table.add_column("Value", overflow="fold")

    for key, value in response.headers.items():
        response_headers_table.add_row(key, value)

    console.print(response_headers_table)

    response_headers_str = ''.join(f"{key}: {value}\r\n" for key, value in response.headers.items())
    response_headers_size_kb = len(response_headers_str.encode('utf-8')) / 1024
    console.print(f"[bold yellow]Total Response Headers Size:[/bold yellow] {response_headers_size_kb:.2f} KB")

    console.print("\n[bold cyan]Response Body:[/bold cyan]")

    try:
        response_json = response.json()
        syntax = Syntax(response.text, "json", theme="monokai", line_numbers=True)
        console.print(syntax)
    except ValueError:
        console.print(response.text)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
import argparse
import json
import logging
import os
from urllib.parse import urlparse

import requests

# Constants
PURGER_API_URL = "https://webops03.nm.cbc.ca/purger/api/v1/purge/prod"
PURGER_TOKEN = os.getenv("PURGER_TOKEN")


class PurgeError(Exception):
    pass


class InvalidURLError(PurgeError):
    pass


class PurgeRequestError(PurgeError):
    pass


def is_valid_url(url):
    try:
        return url.startswith("http") and urlparse(url).scheme in ("http", "https")
    except Exception as e:
        raise InvalidURLError(f"Invalid URL: {url}. Error: {str(e)}")


def format_output(status):
    try:
        return (
            f"URL: {status.get('item', '')}\n"
            f"JIRA Issue: {status['status']['jira'].get('issue', '')}\n"
            f"Varnish Update Time: {status['status']['jira'].get('varnish_update', '')}\n"
            f"Akamai Update Time: {status['status']['jira'].get('akamai_update', '')}\n"
        )
    except Exception as e:
        raise PurgeError(f"Error while formatting output: {str(e)}")


def parse_response(response_text):
    try:
        response_data = json.loads(response_text)
        result = response_data.get("result", "")
        status_list = response_data.get("status", [])

        if result == "ok":
            return (
                "Purge request was successful.\n" +
                "".join(format_output(status) for status in status_list)
            )
        else:
            return f"Purge request failed with the following response:\n{response_text}"

    except json.JSONDecodeError as e:
        raise PurgeError(f"Failed to decode JSON response: {e}")


def purge_urls(url_list, auth_token):
    headers = {
        "Authorization": f"Basic {auth_token}",
        "Content-Type": "application/json",
        "User-Agent": "URLPurger/1.0",
    }
    payload = {"url": url_list}

    try:
        response = requests.post(PURGER_API_URL, headers=headers, json=payload, timeout=10, verify=False)
        response.raise_for_status()
        output = parse_response(response.text)
        print(output)

        # Log the JSON response
        with open("purger.log", "a") as log_file:
            print(response.text, file=log_file)

    except requests.exceptions.RequestException as e:
        raise PurgeRequestError(f"Purge request failed: {e}")
    except json.JSONDecodeError as e:
        raise PurgeRequestError(f"Purge request failed due to an invalid JSON response: {e}")


def main():
    parser = argparse.ArgumentParser(description="URL Purger")
    parser.add_argument("urls", nargs="+", help="List of URLs to purge", type=str)
    parser.add_argument("--auth-token", help="Authorization Basic Token")

    args = parser.parse_args()

    logging.basicConfig(filename="purger.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    auth_token = args.auth_token or PURGER_TOKEN

    if not auth_token:
        raise PurgeError("Authorization token not found. Please set the PURGER_TOKEN environment variable or use the --auth-token argument.")

    valid_urls = [url for url in args.urls if is_valid_url(url)]
    invalid_urls = [url for url in args.urls if not is_valid_url(url)]

    if invalid_urls:
        print("Invalid URLs:", *invalid_urls, sep="\n - ")

    if valid_urls:
        try:
            purge_urls(valid_urls, auth_token)
        except PurgeError as e:
            logging.error(str(e))


if __name__ == "__main__":
    main()

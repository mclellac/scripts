#!/usr/bin/env python3
import openai
import requests
import argparse
import sys
import os
from configparser import ConfigParser
from icecream import ic
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API key from config file or environment variable
config = ConfigParser()
config.read(
    "config.ini"
)  # Create a 'config.ini' file with [OpenAI] section and api_key entry
openai.api_key = config.get(
    "OpenAI", "api_key", fallback=os.getenv("OPENAI_API_KEY")
)


def ask_chatgpt(prompt, engine="gpt-4", max_tokens=500):
    try:
        response = openai.Completion.create(
            engine=engine, prompt=prompt, max_tokens=max_tokens
        )
        return response.choices[0].text.strip()
    except openai.error.OpenAIError as e:
        logger.error(f"Error from OpenAI: {e}")
        sys.exit(1)


def make_request(url, headers):
    try:
        with requests.get(url, headers=headers, timeout=5) as response:
            response.raise_for_status()
            return response.headers
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error making request to {url}: {e}")


def analyze_headers(url, include_pragma=False):
    try:
        if not url.startswith(("http://", "https://")):
            raise ValueError(
                "Invalid URL format. Please include 'http://' or 'https://'."
            )

        # Akamai debug headers.
        pragma_header = (
            "akamai-x-cache-on,akamai-x-cache-remote-on,"
            "akamai-x-get-cache-key,akamai-x-get-extracted-values,"
            "akamai-x-get-ssl-client-session-id,akamai-x-get-true-cache-key,"
            "akamai-x-serial-no,akamai-x-get-request-id,akamai-x-get-nonces,"
            "akamai-x-get-client-ip,akamai-x-feo-trace,akamai-x-check-cacheable"
        )
        headers = {"Pragma": pragma_header} if include_pragma else {}

        # Debugging: Displaying headers before making the request
        ic("Headers before making the request:")
        ic(headers)

        # Fire off the request
        response_headers = make_request(url, headers)

        # Debugging: Displaying response headers
        ic("Response Headers:")
        ic(response_headers)

        # Construct the prompt and send it to ChatGPT
        prompt = f"""Examine the HTTP headers {headers} retrieved from the URL
           {url} and furnish a thorough analysis for each header. Illuminate
            its purpose, significance, and potential implications on the web 
            browsing experience. Additionally, present concrete examples of 
            alternative options or configurations for each header, offering 
            insights into potential variations encountered in diverse 
            scenarios. Consider critical aspects such as caching mechanisms, 
            security policies, content type specifications, and any 
            distinctive features associated with the scrutinized headers. 
            Moreover, proffer recommendations for any absent security headers 
            that should be incorporated into the response for enhanced 
            security."""
        chatgpt_response = ask_chatgpt(prompt)

        # Debugging: Displaying ChatGPT response
        ic("Analysis of HTTP Headers:")
        print("-" * 25)
        ic(chatgpt_response)

    except (ValueError, RuntimeError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze HTTP headers and get explanations from ChatGPT."
    )
    parser.add_argument("url", help="The URL to inspect")
    parser.add_argument(
        "-p",
        "--pragma",
        action="store_true",
        help="Include Akamai pragma headers in the request",
    )

    args = parser.parse_args()

    # Debugging: Displaying command line arguments
    ic("Command Line Arguments:")
    ic(args)

    # Check if the OpenAI API key is set
    if not openai.api_key:
        logger.error(
            "Error: OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable or add it to the 'config.ini' file."
        )
        sys.exit(1)

    target_url = args.url
    include_pragma = args.pragma
    analyze_headers(target_url, include_pragma)

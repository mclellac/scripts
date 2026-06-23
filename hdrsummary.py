#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from configparser import ConfigParser

import openai
import requests
from icecream import ic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenAIError(Exception):
    """
    Exception raised for errors related to OpenAI.

    Attributes:
        message -- explanation of the error
    """

    pass


class RequestError(Exception):
    """
    Exception raised for errors related to requests.

    Attributes:
        message -- explanation of the error
    """

    pass


class URLFormatError(Exception):
    """
    Exception raised for errors in URL format.

    Attributes:
        None
    """

    pass


def load_api_key(config_path):
    """
    Load the API key from the specified config file.

    Args:
        config_path (str): The path to the config file.

    Returns:
        str: The API key.

    """
    config = ConfigParser()
    config.read(config_path)
    return config.get("OpenAI", "api_key", fallback=os.getenv("OPENAI_API_KEY"))


def validate_url(url):
    if not url.startswith(("http://", "https://")):
        raise URLFormatError(
            "Invalid URL format. Please include 'http://' or 'https://'."
        )


def construct_headers(include_pragma):
    """
    Constructs and returns a dictionary of headers.

    Parameters:
    include_pragma (bool): Whether to include the 'Pragma' header.

    Returns:
    dict: A dictionary of headers. If include_pragma is True, the dictionary will contain
          the 'Pragma' header with a value. Otherwise, an empty dictionary will be returned.
    """
    pragma_header = (
        "akamai-x-cache-on,akamai-x-cache-remote-on,"
        "akamai-x-get-cache-key,akamai-x-get-extracted-values,"
        "akamai-x-get-ssl-client-session-id,akamai-x-get-true-cache-key,"
        "akamai-x-serial-no,akamai-x-get-request-id,akamai-x-get-nonces,"
        "akamai-x-get-client-ip,akamai-x-feo-trace,akamai-x-check-cacheable"
    )
    return {"Pragma": pragma_header} if include_pragma else {}


def ask_chatgpt(prompt, engine="gpt-4", max_tokens=500):
    try:
        response = openai.Completion.create(
            engine=engine, prompt=prompt, max_tokens=max_tokens
        )
        return response.choices[0].text.strip()
    except openai.error.OpenAIError as e:
        logger.error(f"Error from OpenAI: {e}")
        raise OpenAIError(f"Error from OpenAI: {e}") from e


def make_request(url, headers):
    try:
        with requests.get(url, headers=headers, timeout=5) as response:
            response.raise_for_status()
            return response.headers
    except requests.exceptions.RequestException as e:
        raise RequestError(f"Error making request to {url}: {e}") from e


def analyze_headers(url, include_pragma=False):
    try:
        # Debugging: Displaying headers before making the request
        ic("Headers before making the request:")
        ic(headers)

        # Fire off the request
        response_headers = make_request(url, headers)

        # Debugging: Displaying response headers
        ic("Response Headers:")
        ic(response_headers)

        # Construct the prompt and send it to ChatGPT
        prompt = f"""Examine these HTTP headers: "{headers}" retrieved from the
            URL "{url}" and furnish a thorough analysis for each header. 
            Illuminate its purpose, significance, and potential implications on 
            the web browsing experience. Additionally, present concrete examples
            of alternative options or configurations for each header, offering 
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

    except (URLFormatError, RequestError, OpenAIError) as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    try:
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
        parser.add_argument(
            "-c",
            "--config",
            default="config.ini",
            help="Path to the configuration file",
        )

        args = parser.parse_args()

        openai.api_key = load_api_key(args.config)

        if not openai.api_key:
            logger.error(
                "Error: OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable or add it to the 'config.ini' file."
            )
            sys.exit(1)

        validate_url(args.url)
        headers = construct_headers(args.pragma)
        analyze_headers(args.url, headers)
    except (URLFormatError, RequestError, OpenAIError) as e:
        logger.error(f"An error occurred while processing URL {args.url}: {e}")
        sys.exit(1)
    except Exception:
        logger.exception("An unexpected error occurred:")
        sys.exit(1)

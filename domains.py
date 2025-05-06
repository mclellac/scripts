#!/usr/bin/env python3
import re
import requests
import sys

def fetch_webpage(url):
    try:
        response = requests.get(url)
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching webpage: {e}")
        sys.exit(1)

def extract_matches(content, regex):
    try:
        matches = re.findall(regex, content)
        # Filter out empty and undesired 'http://' or 'https://' only objects.
        matches = [match for match in matches if match not in ('http://fast.', 'http://', 'https://', '')]
        return matches
    except re.error as e:
        print(f"Error compiling regular expression: {e}")
        sys.exit(1)

def validate_url(url):
    regex = r'^(https?://)?(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    if not re.match(regex, url):
        print("Invalid URL")
        sys.exit(1)

if len(sys.argv) != 2:
    print("Usage: python3 script.py <url>")
    sys.exit(1)

url = sys.argv[1]
validate_url(url)

content = fetch_webpage(url)
regex = r'(https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+)|(\b(?:\d{1,3}\.){3}\d{1,3}\b)'
matches = extract_matches(content, regex)

# Sort matches and remove duplicates
matches = sorted(set(matches))

for match in matches:
    if match: 
        print(match[0]) 
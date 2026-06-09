#!/usr/bin/env python3
"""Module for simulating a Sean Connery accent in text."""

from __future__ import annotations

import re
import sys

# Dictionary of word-based transformations
WORD_REPLACEMENTS: dict[str, str] = {
    "is": "ish",
    "my": "me",
    "house": "housh",
    "mouse": "moush",
    "rouse": "roush",
    "police": "polishe",
    "city": "shity",
    "certainly": "sherhtainly",
    "something": "shomething",
    "this": "thish",
    "that": "thet",
    "you": "ye",
    "your": "yer",
    "for": "fer",
    "was": "wash",
    "seen": "sheen",
    "suit": "shuit",
    "soup": "shoup",
    "simple": "shimple",
    "section": "shection",
    "secret": "shecret",
    "seven": "sheven",
    "sit": "shit",
    "star": "shtar",
    "stone": "shtone",
    "stop": "shtop",
    "story": "shtory",
    "strong": "shtrong",
    "student": "shtudent",
    "stuff": "shtuff",
    "stupid": "shtupid",
    "style": "shtyle",
    "summer": "shummer",
    "sun": "shun",
    "support": "shupport",
    "system": "shystem",
}


def replace_word(match: re.Match[str]) -> str:
    """Replace a word based on WORD_REPLACEMENTS with case preservation.

    Args:
        match: The regex match object containing the word to replace.

    Returns:
        The replacement string with attempted case preservation.

    """
    original_word = match.group(0)
    lower_word = original_word.lower()
    replacement = WORD_REPLACEMENTS.get(lower_word, original_word)

    if original_word.islower():
        return replacement.lower()
    if original_word.isupper():
        return replacement.upper()
    if original_word.istitle():
        return replacement.capitalize()

    return replacement


def connerize(text: str) -> str:
    """Convert input text to simulate a Sean Connery accent.

    Args:
        text: The input string to transform.

    Returns:
        The transformed string with Connery-esque phonetics.

    """
    # 1. Word-based replacements
    # Using word boundaries to match exact words
    pattern = re.compile(r"\b(" + "|".join(re.escape(w) for w in WORD_REPLACEMENTS) + r")\b", re.IGNORECASE)
    text = pattern.sub(replace_word, text)

    # 2. Pattern-based transformations (The 's' to 'sh' sound)
    # Handle 's' at the end of words (excluding 'is', 'as', 'has', 'his' which are often handled differently)
    text = re.sub(r"([a-rt-uvw-z])s\b", r"\1sh", text, flags=re.IGNORECASE)

    # Handle 's' followed by 'i', 'u', 't', 'o'
    text = re.sub(r"s([iuo])", r"sh\1", text, flags=re.IGNORECASE)

    # Handle 'st' sounds
    text = re.sub(r"\bst", "sht", text, flags=re.IGNORECASE)
    text = re.sub(r"([aeiou])st", r"\1sht", text, flags=re.IGNORECASE)

    # Handle 'str' sounds
    text = re.sub(r"str", "shtr", text, flags=re.IGNORECASE)

    # 3. Specific Connery quirks
    # 'don't know' -> 'dinna ken' (more Scottish/Connery flavor)
    text = re.sub(r"\bdon't know\b", "dinna ken", text, flags=re.IGNORECASE)
    # 'yes' -> 'aye'
    return re.sub(r"\byes\b", "aye", text, flags=re.IGNORECASE)


def main() -> None:
    """Read from stdin or arguments and print the connerized text."""
    input_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()

    if not input_text.strip():
        sys.stderr.write("Error: No input text provided.\n")
        sys.exit(1)

    connerized_text = connerize(input_text)
    sys.stdout.write(connerized_text + "\n")


if __name__ == "__main__":
    main()

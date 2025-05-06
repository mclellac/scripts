#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Convert your text into Sean Connery speak.
"""

import sys
import re

# Dictionary of word-based transformations
WORD_REPLACEMENTS = {
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
    "these": "theshe",
    "those": "thoshe",
    "us": "ush",
    "yes": "yesh",
    "see": "shee",
    "sea": "shea",
    "sun": "shun",
    "soon": "shoon",
    "send": "shend",
    "sent": "shent",
    "say": "shay",
    "says": "shesh",
    "said": "shed",
    "miss": "mish",
    "kiss": "kish",
    "list": "lisht",
    "best": "besht",
    "test": "tesht",
    "just": "jusht",
    "must": "musht",
    "fast": "fasht",
    "last": "lasht",
    "past": "pasht",
    "coast": "coasht",
    "most": "mosht",
    "post": "posht",
    "ghost": "ghosht",
    "risk": "rishk",
    "desk": "deshk",
    "task": "tashk",
    "ask": "ashk",
    "mask": "mashk",
    "disk": "dishk",
    "crisp": "crishp",
    "wasp": "washp",
    "grasp": "grashp",
    "lisp": "lishp",
    "clasp": "clashp",
    "whisper": "whishper",
    "crispy": "crishpy",
    "wispy": "wishpy",
    "gasped": "gashped",
    "clasped": "clashped",
    "lisped": "lishped",
    "wasps": "washpsh",
    "grasps": "grashpsh",
    "lisps": "lishpsh",
    "clasps": "clashpsh",
    "whispers": "whishpersh",
    "crisps": "crishpsh",
    "wisps": "wishpsh",
    "gasps": "gashpsh",
    "has": "hash",
    "his": "hish",
    "hers": "hersh",
    "theirs": "theirsh",
    "ours": "oursh",
    "yours": "yoursh",
    "its": "itsh",
    "always": "alwayzh",
    "easy": "eazhy",
    "busy": "bizhy",
    "music": "muzic",
    "present": "prezent",
    "reason": "reazon",
    "season": "seazon",
    "visit": "vizit",
    "close": "closh",
    "lose": "losh",
    "choose": "choosh",
    "use": "ush",
    "abuse": "abush",
    "excuse": "excush",
    "analyse": "analyzh",
    "realise": "realizh",
    "realize": "realizh",
    "organise": "organizh",
    "organize": "organizh",
    "advertise": "advertizh",
    "surprise": "surprizh",
    "rise": "rizh",
    "wise": "wizh",
    "size": "sizh",
    "prize": "prizh",
    "noise": "noizh",
    "poise": "poizh",
    "cause": "cauzh",
    "because": "becauzh",
    "pause": "pauzh",
    "side": "shide",
    "slide": "shlide",
    "stride": "shtride",
    "inside": "inshide",
    "outside": "outshide",
    "beside": "beshide",
    "subside": "subshide",
    "preside": "preshide",
    "reside": "reshide",
    "business": "bizhness",
    "system": "shystem",
    "service": "sherhvice",
    "services": "sherhvicesh",
    "possible": "poshible",
    "possibly": "poshibly",
    "personal": "pershonal",
    "personally": "pershonally",
    "social": "shocial",
    "society": "shociety",
    "special": "speshial",
    "especially": "espheshially",
    "essential": "esshential",
    "issue": "ishoo",
    "issues": "ishoos",
    "increase": "increash",
    "decrease": "decreash",
    "access": "accessh",
    "process": "processh",
    "discuss": "discussh",
    "analysis": "analysish",
    "crisis": "crisish",
    "basis": "basish",
    "status": "statush",
    "series": "seriesh",
    "species": "speciesh",
    "success": "successh",
    "successful": "successful",
    "responsibility": "reshponshibility",
    "responsible": "reshponsible",
    "sense": "shense",
    "sensible": "shenshible",
    "sensitive": "shenshitive",
    "consistent": "consishtent",
    "consistency": "consishtency",
    "insist": "insisht",
    "assist": "assisht",
    "resist": "reshisht",
    "existence": "existensh",
    "persist": "pershisht",
    "consist": "consisht",
    "systematic": "shystematic",
    "session": "shession",
    "pressure": "presshure",
    "ensure": "enshure",
    "sure": "shure",
    "sugar": "shugar",
    "russia": "rushia",
    "asian": "ashian",
    "tension": "tenshion",
    "extension": "extenshion",
    "comprehension": "comprehenshion",
    "dimension": "dimenshion",
    "expression": "expresshion",
    "impression": "impresshion",
    "mission": "misshion",
    "passion": "passhion",
    "possession": "poshession",
    "profession": "professhion",
    "discussion": "discusshion",
    "permission": "permisshion",
    "admission": "admisshion",
    "submission": "submisshion",
    "omission": "omisshion",
    "succession": "successhion",
    "aggression": "aggresshion",
    "depression": "depresshion",
    "oppression": "oppresshion",
    "recession": "recesshion",
    "confession": "confesshion",
    "television": "televizhion",
    "vision": "vizhion",
    "explosion": "explozhion",
    "conclusion": "concluzhion",
    "illusion": "illuzhion",
    "decision": "decizhion",
    "precision": "precizhion",
    "occasion": "occazhion",
    "erosion": "erozhion",
    "collision": "collizhion",
    "division": "divizhion",
    "inclusion": "incluzhion",
    "exclusion": "excluzhion",
    "fusion": "fuzhion",
    "confusion": "confuzhion",
    "persuasion": "persuazhion",
    "invasion": "invazhion",
    "version": "verzhion",
    "diversion": "diverzhion",
    "conversion": "converzhion",
    "suspicion": "suspishion",
    "physician": "physhician",
    "musician": "muzishian",
    "politician": "politishian",
    "statistician": "statistishian",
    "beautician": "beautishian",
    "optician": "optishian",
    "technician": "technishian",
    "dietitian": "dietishian",
    "mortician": "mortishian",
    "patrician": "patrishian",
    "rhetorician": "rhetorishian",
    "physicist": "physhisist",
    "biologist": "biolozhist",
    "geologist": "geolozhist",
    "sociologist": "sociolozhist",
    "psychologist": "psycholozhist",
    "artist": "artisht",
    "dentist": "dentisht",
    "scientist": "scientisht",
    "tourist": "tourisht",
    "specialist": "speshialisht",
    "journalist": "jourhalisht",
    "novelist": "novelisht",
    "pianist": "pianisht",
    "violinist": "violinisht",
    "cellist": "cellisht",
    "flutist": "flutisht",
    "saxophonist": "saxophonisht",
    "guitarist": "guitarisht",
    "bassist": "basshisht",
    "vocalist": "vocalisht",
    "soloist": "soloish",
    "duetist": "duetisht",
    "ass": "assh",
    "asshole": "asshole",
    "bastard": "bashterd",
    "fuck": "fucksh",
    "jesus": "jesush",
    "motherfucker": "motherfucker",
    "piss": "pish",
    "shit": "shit",
    "slut": "shlut",
    "jizz": "jizsh",
    "whore": "whore",
    "arse": "arsh",
    "arsehole": "arshole",
    "tosser": "tosher",
    "was": "wash",
    "as": "ash",
    "louse": "loosh",
    "blouse": "bloosh",
    "spouse": "spoosh",
    "grouse": "groosh",
    "carouse": "caroosh",
    "espouse": "espoosh",
    "douse": "doosh",
    "souse": "shoosh",
    "touse": "toosh",
    "vouse": "voosh",
    "wouse": "woosh",
    "youse": "yoosh",
    "zouse": "zoosh",
    "loose": "loosh",
    "goose": "goosh",
    "moose": "moosh",
    "noose": "noosh",
    "patoose": "patoosh",
    "snoose": "shnoosh",
    "voose": "voosh",
    "zoose": "zoosh",
    "bruise": "broozh",
    "cruise": "croozh",
    "fuse": "fuzh",
    "muse": "muz",
    "peruse": "peruzh",
    "refuse": "refush",
    "suffuse": "suffuzh",
    "transfuse": "transfuzh",
    "amuse": "amuzh",
    "diffuse": "diffuzh",
    "infuse": "infuzh",
    "obtuse": "obtush",
    "recluse": "reclush",
    "seduse": "sedush",
    "profuse": "profush",
    "spruce": "sproosh",
    "juice": "joosh",
    "speak": "shpeak",
    "sport": "shport",
    "street": "shtreet",
    "strong": "shtrong",
    "slow": "shlow",
    "small": "shmall",
    "snow": "shnow",
    "swim": "shwim",
    "sweet": "shweet",
    "start": "shtart",
    "stop": "shtop",
    "student": "shtudent",
    "study": "shtudy",
    "school": "shchool",
    "skin": "shkin",
    "sky": "shky",
    "smile": "shmile",
    "smell": "shmell",
    "smoke": "shmoke",
    "snack": "shnack",
    "snake": "shnake",
    "spin": "shpin",
    "spit": "shpit",
    "spread": "shpread",
    "spring": "shpring",
    "square": "shquare",
    "squeeze": "shqueeze",
    "simple": "shimple",
    "single": "shingle",
    "sister": "shishter",
    "seven": "sheven",
    "several": "sheveral",
    "soup": "shoop",
    "south": "shouth",
    "super": "shuper",
    "listen": "lishen",
    "hasten": "hashen",
    "castle": "cashel",
    "whistle": "whishel",
    "moisture": "moishter",
    "pasture": "pashture",
    "first": "firsht",
    "measure": "measzhure",
    "pleasure": "pleazhure",
    "treasure": "treazhure",
    "visual": "vizhual",
    "site": "shite",
    "since": "shince",
    "silly": "shilly",
    "six": "shix",
    "sleep": "shleep",
    "slip": "shlip",
    "slice": "shlice",
    "smooth": "shmooth",
    "sniff": "shniff",
    "sneeze": "shneeze",
    "swing": "shwing",
    "switch": "shwitch",
    "spoon": "shpoon",
    "splooge": "shplooge",
    "space": "shpace",
    "skip": "shkip",
    "price": "prish",
    "rice": "rish",
    "face": "fash",
    "place": "plash",
    "nice": "nish",
    "ice": "ish",
}

REGEX_REPLACEMENTS = [
    # Handle 's' at word boundaries carefully
    (re.compile(r"(\b)s(\b)", re.IGNORECASE), r"\1sh\2"),
    (re.compile(r"(\w)s(\b)", re.IGNORECASE), r"\1sh\2"),
    # General 's' -> 'sh' (unless already 'sh'). Aggressive rule.
    (re.compile(r"s(?!h)", re.IGNORECASE), "sh"),
    # Specific common patterns ('ce', 'ci', 'cy')
    (re.compile(r"ce\b", re.IGNORECASE), "sh"),
    (re.compile(r"ci", re.IGNORECASE), "shi"),
    (re.compile(r"cy", re.IGNORECASE), "shy"),
]

# Sort keys by length (descending). Match longer words first
_SORTED_WORD_KEYS = sorted(WORD_REPLACEMENTS.keys(), key=len, reverse=True)
_WORD_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(word) for word in _SORTED_WORD_KEYS) + r")\b",
    re.IGNORECASE,
)


def _replace_word_match(match):
    """
    Callback function for re.sub to replace words using WORD_REPLACEMENTS.

    Attempts to preserve the original word's case (lower, UPPER, Title).

    Args:
        match (re.Match): The regex match object.

    Returns:
        str: The replacement string with attempted case preservation.
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
    if lower_word in WORD_REPLACEMENTS:
        return replacement.lower()

    return original_word


def connerize(text):
    """
    Converts input text to simulate a Sean Connery accent.

    Applies substitutions first from WORD_REPLACEMENTS, then uses broader
    phonetic patterns from REGEX_REPLACEMENTS.

    Args:
        text (str): The input text string.

    Returns:
        str: The text processed with simulated accent rules.
    """
    connerized_text = _WORD_PATTERN.sub(_replace_word_match, text)

    temp_text = connerized_text
    for pattern, replacement_str in REGEX_REPLACEMENTS:
        temp_text = pattern.sub(replacement_str, temp_text)
    connerized_text = temp_text

    return connerized_text


def main():
    """
    Handles command-line argument processing, calls the conversion function,
    and prints the output formatted within a box.
    """
    input_text = " ".join(sys.argv[1:])

    usage_template = "Usage: connerize <string>"

    if not input_text:
        connerized_usage = connerize(usage_template)
        print(connerized_usage)
        sys.exit(1)

    connerized_output = connerize(input_text)
    label = "Sean Connery:"

    full_output = f"{label} {connerized_output}"
    content_width = len(full_output)

    top_border = "╭─" + "─" * content_width + "─╮"
    text_line = "│ " + full_output + " │"
    bottom_border = "╰─" + "─" * content_width + "─╯"

    print(top_border)
    print(text_line)
    print(bottom_border)


if __name__ == "__main__":
    main()

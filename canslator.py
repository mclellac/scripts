#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Canadian slang translator
"""

import sys
import re

SLANG_TO_STANDARD = {
    "canadian tuxedo": "outfit consisting of denim jacket and denim jeans",
    "crosby": "Sidney Crosby (famous Canadian hockey player)",
    "timmies": "Tim Hortons (popular Canadian coffee shop chain)",
    "all hat and no cattle": "all talk and no action; boastful without substance",
    "apple": "assist (hockey statistic)",
    "apples": "assists (hockey statistic)",
    "backburner": "delay consideration; postpone",
    "backhander": "backhand shot (hockey)",
    "bail": "leave abruptly; depart quickly",
    "bar down": "goal scored when puck hits the bottom of the crossbar and goes in",
    "bar south": "goal scored hitting just under the crossbar",
    "barn": "ice hockey arena or rink",
    "bathroom": "washroom (common Canadian term)",
    "beanie": "toque (Canadian term for a winter hat)",
    "beater": "old, worn-out car (slang)",
    "beauty flow": "nice hairstyle (hockey slang for long hair)",
    "beauty": "excellent player, play, or thing; attractive person (hockey/Canadian slang)",
    "beavertail": "Canadian pastry (fried dough with toppings)",
    "bender": "bad skater (hockey slang, from weak ankles) / extended drinking session",
    "bevvy": "beverage (often alcoholic, informal)",
    "biff": "make a mistake; fall clumsily (informal)",
    "biscuit": "hockey puck (slang)",
    "bonk": "hit lightly; bump (informal)",
    "booze cruise": "boat trip where drinking alcohol is the main activity",
    "boxcar": "long sequence (figurative, like train cars); very fast (figurative)",
    "breakaway": "one-on-one situation against the goalie (hockey)",
    "broke": "having no money (informal)",
    "buck": "dollar (Canadian currency unit, often referring to 'loonie')",
    "bucket": "helmet (hockey slang)",
    "buckled": "very drunk; intoxicated (slang)",
    "buddy": "friend; pal (informal)",
    "bud": "friend; pal (often used sarcastically or condescendingly)",
    "okay bud": "okay pal (often dismissive or sarcastic)",
    "butter tart": "small pastry tart with a sweet, buttery filling (Canadian dessert)",
    "cellied": "celebrated (hockey slang, after scoring)",
    "celly": "celebration (hockey slang, after scoring)",
    "chesterfield": "sofa; couch (Canadian/older term)",
    "chill out": "relax; calm down (informal command)",
    "chill": "relax; calm down (informal)",
    "chilly": "cold (weather or mood)",
    "chirp": "insult; tease; taunt (especially in hockey)",
    "chirped": "insulted; teased; taunted",
    "chirping": "insulting; teasing; taunting",
    "clapper": "slap shot (hockey slang)",
    "clutch": "performing well under pressure; succeeding in a critical moment",
    "couch": "chesterfield (Canadian/older term for sofa)",
    "dangle": "perform a deke or skilled stickhandle move (hockey)",
    "dangled": "performed a deke (hockey)",
    "dangler": "player skilled at stickhandling (hockey slang)",
    "dangling": "performing dekes; stickhandling skillfully (hockey)",
    "dart": "cigarette",
    "darts": "cigarettes",
    "decent": "acceptable; satisfactory; quite good",
    "degens": "degenerates (Letterkenny insult)",
    "dialed in": "highly focused; well-prepared; performing optimally (slang)",
    "do the dishes": "wash the dishes",
    "dog's breakfast": "complete mess; poorly organized situation (idiom)",
    "doll": "term of endearment for a woman/girl (can be dated/condescending)",
    "donnybrook": "brawl; large fight; uproar",
    "double double": "coffee with two creams and two sugars (Tim Hortons order)",
    "double-parked": "parked across two parking spaces",
    "duck": "lower one's head to avoid being hit",
    "dude": "friend; pal; generic term for a person (usually male, informal)",
    "duster": "hockey player who sits on the bench often; benchwarmer",
    "eh buddy?": "hey friend; getting someone's attention (Canadian)",
    "eh?": "(Canadian tag question, seeking confirmation or softening statement, like 'right?')",
    "fancy pants": "someone perceived as pretentious or overly refined (informal)",
    "ferda": "for the boys; yes; okay (hockey/Letterkenny slang)",
    "figure it out": "understand; solve the problem; deal with it",
    "five-hole": "space between a goalie's legs (hockey term)",
    "flyin'": "moving quickly; succeeding; doing well (informal)",
    "for the boys": "acting for camaraderie or the benefit of the male friend group",
    "freezing rain": "rain that freezes upon contact with surfaces",
    "friend": "buddy (common substitute in target slang)",
    "friends": "buddies (common substitute in target slang)",
    "ftb": "acronym for 'For The Boys'",
    "fuckin'": "very; really; extremely (vulgar intensifier)",
    "garburator": "kitchen garbage disposal unit",
    "gassed": "exhausted; out of energy (slang)",
    "gimme a sec": "give me a second; wait a moment (informal)",
    "give yer balls a tug": "man up; stop complaining",
    "give your balls a tug": "man up; stop complaining",
    "giver": "put in maximum effort; go all out",
    "gnarly": "excellent; impressive; difficult (slang, often surf/skate culture)",
    "go for a rip": "go for a drive, ride, or outing, often spiritedly",
    "gotta go": "I have to leave (informal)",
    "gravy": "bonus; extra benefit; easy money or situation (slang)",
    "greasy": "unpleasant; sketchy; low-quality; unattractive (slang)",
    "green bin": "municipal bin for organic waste/compost (common in Canada)",
    "grocery stick": "player separating forwards/defense on bench; benchwarmer (hockey slang)",
    "grub": "food (informal)",
    "guilty pleasure": "something enjoyed despite feeling it's not generally held in high regard",
    "guy": "bud (common substitute in target slang)",
    "guys": "fellas (common substitute in target slang)",
    "hard no": "an emphatic and absolute refusal",
    "hat": "toque (common Canadian substitute for winter hat)",
    "hello": "how'r ya now? (common substitute in target slang)",
    "hey": "how'r ya now? (common substitute in target slang)",
    "hi": "how'r ya now? (common substitute in target slang)",
    "hicks": "(term for rural/farmer characters in Letterkenny, often self-applied)",
    "hockey game": "hockey game; match (sometimes 'tilt' in slang)",
    "hockey night in canada": "Saturday night NHL hockey broadcast tradition (CBC)",
    "hockey night": "Saturday night hockey broadcast",
    "hosed": "cheated; defeated badly; put in a bad situation (slang)",
    "hoser": "foolish, clumsy, or unskilled person (classic Canadian insult)",
    "housecoat": "bathrobe (Canadian/older term)",
    "hundo": "one hundred dollars (slang)",
    "jet": "extremely fast skater (hockey slang)",
    "jig": "lively folk dance",
    "keener": "overly eager person; try-hard",
    "kerfuffle": "commotion; fuss; minor disagreement",
    "knock on wood": "superstitious phrase to avert bad luck",
    "lamp lighter": "player who scores goals frequently (hockey slang)",
    "lay a beat down": "defeat someone decisively (in a fight or competition)",
    "lettuce": "long hair (hockey slang for 'flow')",
    "line up": "form a queue; wait in line",
    "linesy": "linesman (hockey official, slang)",
    "lip": "insolent talk; back talk (slang)",
    "loon": "Canadian one-dollar coin ('loonie') / aquatic bird",
    "loonie": "Canadian one-dollar coin",
    "toonie": "Canadian two-dollar coin",
    "lumber": "hockey stick (slang, often implies rough play)",
    "lumberjack": "person who fells trees (strong Canadian stereotype)",
    "lunchpail": "symbol of a hard-working, blue-collar attitude (figurative)",
    "man": "bud (common substitute in target slang)",
    "maritime": "relating to Canada's Maritime provinces (NB, NS, PEI)",
    "mickey": "small bottle of liquor (375ml - Canadian term)",
    "money": "cash; currency",
    "morning glory": "dawn; first light of day / type of flowering vine",
    "mountie": "RCMP officer (Royal Canadian Mounted Police)",
    "mucker": "gritty player who works hard in corners (hockey slang)",
    "mushy peas": "mashed peas side dish (British/Canadian food)",
    "nah": "no (informal)",
    "nana": "grandmother (informal term of endearment)",
    "napkin": "serviette (common Canadian substitute)",
    "negative": "no (formal)",
    "no": "no (standard refusal)",
    "nope": "no (informal)",
    "odr": "outdoor ice rink (hockey slang)",
    "off the wall": "unconventional; bizarre; crazy (idiom)",
    "ok": "ferda (common substitute in target slang)",
    "okay": "ferda (common substitute in target slang)",
    "ontario": "province in central Canada",
    "out to lunch": "not paying attention; clueless; crazy (idiom)",
    "outta here": "leaving now (informal contraction)",
    "pal": "bud (common substitute in target slang)",
    "parking garage": "parkade (common Canadian substitute)",
    "pencil crayon": "colored pencil",
    "pencil it in": "schedule tentatively; make a casual note (idiom)",
    "people": "fellas (common substitute in target slang)",
    "person": "fella (common substitute in target slang)",
    "pigeon": "player who benefits from teammates' work; less skilled player (hockey slang)",
    "plowed": "very drunk; intoxicated (slang)",
    "plug": "bad or useless player/person (hockey slang/insult)",
    "pop": "soda; carbonated soft drink (Canadian/Midwest US term)",
    "popcorn machine": "excessively talkative person (slang/idiom)",
    "popcorn": "react suddenly; jump up (like popcorn popping)",
    "pops": "beers (informal slang)",
    "poutine": "dish of french fries, cheese curds, and gravy (Quebecois/Canadian food)",
    "probably": "likely; presumably",
    "puck bunny": "fan (often female) more interested in players than the game",
    "puck off": "get lost; go away (hockey-themed twist on 'fuck off')",
    "pylon": "slow defenseman who is easily skated around (hockey slang)",
    "rack": "sleep; bed (informal slang)",
    "rackin'": "sleeping (informal slang)",
    "reel": "spool for fishing line / lively folk dance or music",
    "ref": "referee (sports official, informal)",
    "restroom": "washroom (common Canadian substitute)",
    "rick": "stack or pile of wood (regional term)",
    "rides the pine": "spends most of the game on the bench (sports idiom)",
    "right on": "expression of agreement or approval (informal)",
    "rink rat": "person who spends excessive time at an ice rink",
    "rip-roaring": "noisy, lively, and exciting",
    "ripple": "small wave / type of potato chip",
    "rocket": "very hard shot (hockey) / very attractive person (esp. Letterkenny/Shoresy)",
    "running shoes": "runners (common Canadian substitute)",
    "sauce": "lifted 'saucer' pass over sticks (hockey slang)",
    "sauced": "made a saucer pass (hockey slang)",
    "saucering": "making a saucer pass (hockey slang)",
    "scrap": "fight; brawl (informal)",
    "scrapper": "fighter; someone prone to fighting (informal)",
    "scrappin'": "fighting (informal)",
    "scree": "loose rock debris on a slope",
    "serviette": "napkin (Canadian/formal term)",
    "shield": "visor (on a hockey helmet)",
    "shinny": "informal pickup hockey game",
    "shoot the breeze": "chat casually; converse idly (idiom)",
    "sieve": "goalie who lets in many goals (hockey insult)",
    "sin bin": "penalty box (hockey slang)",
    "sixth gear": "maximum effort or speed (idiom)",
    "skids": "Dirty unkempt person. Street kids.",
    "skookum": "strong; excellent; impressive (BC Indigenous origin/slang)",
    "smoke": "cigarette (informal slang)",
    "snagged": "caught; obtained; grabbed quickly (informal)",
    "snappy": "quick; brisk; stylish (informal)",
    "snapshot": "quick wrist shot in hockey / informal photograph",
    "sneakers": "runners (common Canadian substitute)",
    "snipe": "goal, especially a well-placed shot (hockey slang)",
    "sniped": "scored (usually a good goal) (hockey slang)",
    "sniper": "player skilled at scoring goals, especially with accurate shots (hockey slang)",
    "snipes": "goals (hockey slang)",
    "snowbird": "Canadian who spends winter in warmer southern locations",
    "soda": "pop (common Canadian substitute)",
    "sofa": "chesterfield (common Canadian/older substitute)",
    "soft drink": "pop (common Canadian substitute)",
    "sore loser": "person who handles losing poorly",
    "sorry": "sorrey (representing Canadian pronunciation)",
    "squad": "team; group of friends (informal slang)",
    "stitch": "sharp, localized pain from exertion (like running)",
    "stoked": "very excited; enthusiastic (slang)",
    "sure": "ferda (common substitute in target slang)",
    "sweater": "hockey jersey",
    "sweet": "cool; awesome (informal slang)",
    "take a rain check": "politely decline an invitation, suggesting postponement (idiom)",
    "take care": "goodbye; be careful (common closing)",
    "take off": "leave; depart (informal command or statement)",
    "tallboy": "tall can of beer (typically 16oz or more)",
    "tendy": "goalie; goaltender (hockey slang)",
    "the 6ix": "Toronto (nickname based on area codes)",
    "the cup": "The Stanley Cup trophy or championship (hockey)",
    "the rock": "Newfoundland (Canadian province nickname)",
    "the show": "the NHL (National Hockey League - top professional league)",
    "threads": "clothes (slang)",
    "tilt": "hockey game / fight (hockey slang)",
    "tilted": "fought / played a game (hockey slang)",
    "timber": "warning shouted when a tree is falling",
    "toque weather": "weather cold enough to require a toque/winter hat",
    "toque": "close-fitting knitted winter hat",
    "trainers": "runners (common Canadian substitute for athletic shoes)",
    "trip to the bin": "penalty requiring time in the penalty box (hockey slang)",
    "trolley": "shopping cart (less common Canadian term, mostly UK/Aus)",
    "tuck in": "eat heartily (invitation)",
    "turn on a dime": "change direction very quickly (idiom)",
    "tweed": "rough woolen fabric",
    "twig": "hockey stick (slang)",
    "two-four": "case of 24 beers",
    "washroom": "bathroom; restroom (common Canadian term)",
    "whip": "car (slang)",
    "white knuckle": "tense situation causing one to grip tightly (idiom)",
    "wicked": "cool; awesome; very (slang, esp. New England/East Coast/older)",
    "wrister": "wrist shot (hockey term)",
    "zed": "the letter Z (Canadian/British pronunciation)",
    "zonked": "exhausted; extremely tired (slang)",
    "twat": "A vulgar insult for someone irritating, often used as a general insult.",
    "douchebag": "A term for an obnoxious, self-centered person, commonly used in Canada similar to the U.S.",
    "shit-disturber": "Someone who causes trouble or stirs up conflict without reason.",
    "friggin'": "A milder, substitute for the word 'fucking', used to emphasize something, though still vulgar.",
    "goof": "A derogatory term that, in certain Canadian contexts, can refer to a pedophile. It traditionally means a foolish or silly person.",
    "broke-ass": "A crude term to describe someone who has no money or is financially struggling.",
    "bum": "Someone who is lazy, or derogatorily, someone with poor hygiene or bad behavior.",
    "chin-wag": "While often innocent as 'chatter,' in a certain context can refer to trivial, annoying gossip.",
    "cock": "Used in various derogatory phrases, often an insult to someone's personality or behavior.",
    "fuckface": "A vulgar insult for someone who is perceived as extremely annoying or stupid.",
    "asshole": "A common and very vulgar term for a mean, rude, or unpleasant person.",
    "piss-off": "A phrase to tell someone to leave or stop bothering you in a very rude manner.",
}

# Regex replacements are not used for this translation direction.
SLANG_REGEX_REPLACEMENTS = []

# Precompile pattern: Sort keys by length (desc) to match longer phrases first.
_SORTED_SLANG_KEYS = sorted(SLANG_TO_STANDARD.keys(), key=len, reverse=True)
_SLANG_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(word) for word in _SORTED_SLANG_KEYS) + r")\b",
    re.IGNORECASE,
)


def _translate_slang_match(match):
    """
    Callback for re.sub to replace slang using SLANG_TO_STANDARD dictionary.
    Attempts to preserve the original slang's case in the output (if applicable).
    """
    original_slang = match.group(0)
    lower_slang = original_slang.lower()
    replacement = SLANG_TO_STANDARD.get(lower_slang, original_slang)

    if original_slang.islower():
        return replacement
    if original_slang.isupper():
        return replacement.upper()
    if original_slang.istitle():
        return replacement.capitalize()
    return replacement


def translate_slang(text):
    """
    Translates known Canadian/hockey slang in text to more standard English.
    Focuses on Letterkenny and Shoresy vocabulary.
    """
    translated_text = _SLANG_PATTERN.sub(_translate_slang_match, text)

    # Apply any regex replacements (currently none)
    temp_text = translated_text
    for pattern, replacement_str in SLANG_REGEX_REPLACEMENTS:
        temp_text = pattern.sub(replacement_str, temp_text)
    translated_text = temp_text

    return translated_text


def main():
    """
    Handles CLI arguments, calls translation, prints output in a box.
    """
    input_text = " ".join(sys.argv[1:])

    script_name = "translate_slang_script.py"
    usage_template = f"Usage: python3 {script_name} <text containing slang to translate>"

    if not input_text:
        translated_usage = translate_slang(usage_template)
        print(translated_usage)
        sys.exit(1)

    translated_output = translate_slang(input_text)
    label = "Canadian for:"

    full_output = f"{label} {translated_output}"
    content_width = len(full_output)

    top_border = "╭─" + "─" * content_width + "─╮"
    text_line = "│ " + full_output + " │"
    bottom_border = "╰─" + "─" * content_width + "─╯"

    print(top_border)
    print(text_line)
    print(bottom_border)


if __name__ == "__main__":
    main()


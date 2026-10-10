"""A small two-object command parser in the Infocom tradition.

Turns a line like "put the brass key in the locker" into a Command with a
canonical verb, a noun phrase, a preposition, and a second noun phrase.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

ARTICLES = {"the", "a", "an", "some", "my", "that", "this", "please"}

PREPOSITIONS = {
    "in", "into", "inside", "on", "onto", "to", "at", "with", "using", "from",
    "under", "beneath", "through", "for", "about", "behind", "off", "over",
    "toward", "towards", "against",
}

DIRECTIONS = {
    "north": "north", "n": "north",
    "south": "south", "s": "south",
    "east": "east", "e": "east",
    "west": "west", "w": "west",
    "up": "up", "u": "up", "upstairs": "up",
    "down": "down", "d": "down", "downstairs": "down",
    "in": "in", "inside": "in",
    "out": "out", "outside": "out", "exit": "out",
}

VERBS = {
    "look": {"look", "l", "gaze"},
    "examine": {"examine", "x", "inspect", "describe", "check", "study"},
    "take": {"take", "get", "grab", "pick", "carry", "lift", "remove"},
    "drop": {"drop", "discard", "release", "leave"},
    "put": {"put", "place", "insert", "deposit", "store", "stow"},
    "inventory": {"inventory", "i", "inv"},
    "open": {"open"},
    "close": {"close", "shut"},
    "read": {"read"},
    "light": {"light", "ignite", "kindle"},
    "extinguish": {"extinguish", "douse", "snuff", "unlight"},
    "turn": {"turn", "set", "rotate", "spin", "twist", "dial"},
    "unlock": {"unlock"},
    "lock": {"lock"},
    "pry": {"pry", "prise", "prize", "lever", "force", "wedge", "jimmy"},
    "attack": {"attack", "kill", "hit", "strike", "stab", "fight", "spear", "slay", "gaff", "whack"},
    "give": {"give", "feed", "offer", "hand"},
    "throw": {"throw", "toss", "hurl", "fling"},
    "tie": {"tie", "fasten", "attach", "knot", "lash", "secure"},
    "untie": {"untie", "unfasten", "detach", "unknot"},
    "climb": {"climb", "scale", "descend", "ascend"},
    "enter": {"enter", "board"},
    "search": {"search", "rummage", "investigate"},
    "wait": {"wait", "z", "rest"},
    "wind": {"wind", "play", "crank"},
    "fill": {"fill", "refill"},
    "ring": {"ring"},
    "go": {"go", "walk", "run", "head", "travel", "proceed"},
    "score": {"score", "points"},
    "save": {"save"},
    "restore": {"restore", "load"},
    "quit": {"quit", "q"},
    "restart": {"restart"},
    "help": {"help", "?", "commands", "hint", "hints"},
    "verbose": {"verbose"},
    "brief": {"brief", "superbrief"},
    "tide": {"tide", "tides"},
    "again": {"again", "g"},
    "listen": {"listen"},
    "smell": {"smell", "sniff"},
    "jump": {"jump", "leap"},
    "swim": {"swim", "dive", "wade"},
    "push": {"push", "press", "shove", "move"},
    "pull": {"pull", "drag", "tug", "yank"},
    "eat": {"eat", "taste", "bite"},
    "drink": {"drink"},
    "yell": {"yell", "shout", "scream", "sing", "hello", "hi", "hey", "call", "talk", "speak"},
    "pray": {"pray", "kneel"},
    "sleep": {"sleep", "nap"},
    "dig": {"dig"},
    "diagnose": {"diagnose", "health"},
    "xyzzy": {"xyzzy", "plugh", "plover", "frotz"},
    "use": {"use"},
    "break": {"break", "smash", "destroy"},
    "knock": {"knock"},
    "touch": {"touch", "feel", "rub"},
    "swing": {"swing", "wave", "brandish"},
    "burn": {"burn"},
    "cut": {"cut", "slice"},
    "look_through": set(),
}

VERB_LOOKUP = {}
for _canon, _syns in VERBS.items():
    for _s in _syns:
        VERB_LOOKUP[_s] = _canon

UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19,
}
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}


@dataclass
class Command:
    verb: Optional[str] = None
    noun: List[str] = field(default_factory=list)
    prep: Optional[str] = None
    noun2: List[str] = field(default_factory=list)
    number: Optional[int] = None
    direction: Optional[str] = None
    raw: str = ""
    error: Optional[str] = None
    words: List[str] = field(default_factory=list)


def _word_number(tok: str) -> Optional[int]:
    if tok.isdigit():
        return int(tok)
    parts = tok.split("-")
    total = 0
    for p in parts:
        if p in UNITS:
            total += UNITS[p]
        elif p in TENS:
            total += TENS[p]
        else:
            return None
    return total


def _extract_number(tokens: List[str]):
    """Pull a number (digits or words like 'twenty three') out of a token list."""
    out = []
    number = None
    i = 0
    while i < len(tokens):
        n = _word_number(tokens[i])
        if n is None:
            out.append(tokens[i])
            i += 1
            continue
        # combine "twenty" "three"
        if tokens[i] in TENS and i + 1 < len(tokens) and tokens[i + 1] in UNITS and UNITS[tokens[i + 1]] < 10:
            n += UNITS[tokens[i + 1]]
            i += 1
        if number is None:
            number = n
        i += 1
    return out, number


def parse(text: str) -> Command:
    raw = text.strip()
    cleaned = re.sub(r"[^\w\s'\-?]", " ", raw.lower())
    tokens = [t for t in cleaned.split() if t not in ARTICLES]
    cmd = Command(raw=raw, words=list(tokens))

    if not tokens:
        cmd.error = "I beg your pardon?"
        return cmd

    if len(tokens) == 1 and tokens[0] in DIRECTIONS:
        cmd.verb = "go"
        cmd.direction = DIRECTIONS[tokens[0]]
        return cmd

    verb_word = tokens[0]
    rest = tokens[1:]
    verb = VERB_LOOKUP.get(verb_word)
    if verb is None:
        cmd.error = "I don't know the word \"%s\"." % verb_word
        return cmd

    # Phrasal verbs and particles.
    if rest:
        p = rest[0]
        if verb == "take" and p == "up":
            rest = rest[1:]
        elif verb == "put" and p == "down":
            verb, rest = "drop", rest[1:]
        elif verb == "turn" and p in ("on", "off"):
            verb, rest = ("light" if p == "on" else "extinguish"), rest[1:]
        elif verb == "look":
            if p == "at":
                verb, rest = "examine", rest[1:]
            elif p in ("under", "behind", "beneath"):
                verb, rest = "search", rest[1:]
            elif p in ("in", "inside", "into"):
                verb, rest = "examine", rest[1:]
            elif p == "through":
                verb, rest = "look_through", rest[1:]
            elif p in DIRECTIONS and len(rest) == 1:
                rest = []
        elif verb == "climb" and p in ("up", "down"):
            cmd.direction = p
            rest = rest[1:]
        elif verb in ("go", "take", "enter") and p in DIRECTIONS and len(rest) == 1:
            cmd.verb = "go"
            cmd.direction = DIRECTIONS[p]
            return cmd
        elif verb == "wait" and p in ("for", "until", "till"):
            rest = rest[1:]

    if verb == "turn" and rest:
        if rest[-1] in ("on", "off"):
            verb = "light" if rest[-1] == "on" else "extinguish"
            rest = rest[:-1]

    if verb == "go" and not rest:
        cmd.error = "Go where?"
        return cmd

    # Split on the first preposition.
    prep_idx = None
    for i, t in enumerate(rest):
        if t in PREPOSITIONS:
            prep_idx = i
            break
    if prep_idx is not None:
        noun = rest[:prep_idx]
        prep = rest[prep_idx]
        noun2 = rest[prep_idx + 1:]
    else:
        noun, prep, noun2 = rest, None, []

    noun, n1 = _extract_number(noun)
    noun2, n2 = _extract_number(noun2)
    cmd.number = n2 if n2 is not None else n1

    cmd.verb = verb
    cmd.noun = noun
    cmd.prep = prep
    cmd.noun2 = noun2
    return cmd

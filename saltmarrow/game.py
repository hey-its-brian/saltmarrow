"""The SALTMARROW engine: turns, tides, light, puzzles, scoring, and death."""

import json
import os
import random
import sys
import textwrap
from typing import Callable, List, Optional

from .parser import parse, Command, DIRECTIONS
from .world import build_world, Item, Room

# Tide cycle: (phase name, length in turns). Forty turns all told.
CYCLE = [("low", 22), ("flooding", 6), ("high", 8), ("ebbing", 4)]
CYCLE_LEN = sum(n for _, n in CYCLE)
START_POS = 32          # the game opens at high tide, four turns before the ebb
LANTERN_FULL = 120
MAX_SCORE = 350
SAFE_COMBINATION = 23
TREASURES = ["medal", "music_box", "ring", "pearl", "astrolabe", "reliquary", "log"]
BONUSES = {
    "descended": 10, "safe": 15, "sarcophagus": 10, "cabin": 10,
    "gannets": 10, "eel": 10, "finished": 30,
}
RANKS = [
    (350, "Keeper of the Light"), (275, "Harbormaster"), (200, "Salvager"),
    (125, "Wrecker"), (50, "Mudlark"), (0, "Beachcomber"),
]
SAVE_VERSION = 1

BELL = {
    "ebbing": "Far off, the tide bell at Gannet Point rings once. The sea has begun to "
              "draw back from Saltmarrow.",
    "low": "The tide bell rings twice. The streets of the Low Town stand open to the air.",
    "flooding": "The tide bell rings three times, urgent. The sea is coming back.",
    "high": "The tide bell rings four times and falls silent. Saltmarrow is drowned again.",
}

INTRO = (
    "SALTMARROW\n"
    "An interactive salvage.\n\n"
    "Eighty years ago the sea took the fishing town of Saltmarrow in a single night, "
    "and the keeper of the Gannet Point light rang the tide bell until no one was left "
    "to hear it. Twice a day the sea gives the Low Town back for a little while, and "
    "twice a day it takes it again.\n\n"
    "You are a salvager. You have come for what the drowned left behind. The keeper's "
    "locker will hold whatever you find, if you can find it, and if you can carry it "
    "out before the bell rings four.\n\n"
    "Type HELP for a list of commands."
)

HELP = (
    "You talk to SALTMARROW in short imperative sentences: LOOK, TAKE LANTERN, PUT "
    "MEDAL IN LOCKER, UNLOCK DOOR WITH KEY, TURN DIAL TO 17, GIVE FISH TO BIRDS.\n\n"
    "Moving: NORTH, SOUTH, EAST, WEST, UP, DOWN, IN, OUT (or N, S, E, W, U, D). "
    "CLIMB, ENTER and BOARD also work where they make sense.\n\n"
    "Looking: LOOK (L), EXAMINE something (X), READ something, SEARCH something, "
    "INVENTORY (I).\n\n"
    "Doing: TAKE, DROP, PUT X IN Y, OPEN, CLOSE, LIGHT, EXTINGUISH, FILL, TIE, UNTIE, "
    "WIND, RING, PRY, ATTACK, GIVE, THROW, and others. If a sensible thing doesn't "
    "work, try saying it another way.\n\n"
    "Time: WAIT passes one turn. WAIT FOR TIDE waits until the bell next rings. TIDE "
    "tells you where the water is. Your lantern burns oil while it is lit.\n\n"
    "Housekeeping: SCORE, SAVE, RESTORE, RESTART, VERBOSE, BRIEF, AGAIN (G), QUIT.\n\n"
    "Treasures go in the keeper's salvage locker. The bell tells the tide. Do not be "
    "in the Low Town when it rings four, and do not walk in the dark."
)

ENDING = (
    "As the last of it settles into the locker, the brass lid closes itself with a "
    "sound like a held breath let go.\n\n"
    "Above you, the great lamp of Gannet Point kindles without oil or flame. A cold "
    "white light sweeps out across the water, once, twice, and steadies. Far below, "
    "in the drowned streets, the tide bell rings, and rings, and rings, and the voices "
    "you have heard all night at the edge of the dark rise together into a hymn with "
    "exactly the right number of parts, and are carried out past the harbor mouth, "
    "and are gone.\n\n"
    "Saltmarrow is quiet. For the first time in eighty years, it is only a town that "
    "drowned."
)


class Game:
    def __init__(self, seed: Optional[int] = None, out: Optional[Callable[[str], None]] = None):
        self.rooms, self.items = build_world()
        self.location = "base"
        self.turns = 0
        self.score = 0
        self.flags = set()
        self.verbose = False
        self.fuel = LANTERN_FULL
        self.refills = 2
        self.dead = False
        self.over = False
        self.won = False
        self.last_it: Optional[str] = None
        self.last_command: Optional[str] = None
        self.seed = seed
        self.rng = random.Random(seed)
        self._out = out or self._print
        self._prefix = ""
        self.rooms["base"].visited = True

    # ------------------------------------------------------------------ output

    @staticmethod
    def _print(text: str) -> None:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()

    def say(self, text: str) -> None:
        if self._prefix:
            text = self._prefix + text
            self._prefix = ""
        paragraphs = text.split("\n\n")
        wrapped = []
        for p in paragraphs:
            lines = p.split("\n")
            wrapped.append("\n".join(textwrap.fill(line, 76) if line else "" for line in lines))
        self._out("\n\n".join(wrapped))

    # ------------------------------------------------------------------ helpers

    @property
    def room(self) -> Room:
        return self.rooms[self.location]

    def item(self, key: str) -> Item:
        return self.items[key]

    def carrying(self, key: str) -> bool:
        return self.items[key].location == "player"

    def inventory_items(self) -> List[Item]:
        return [it for it in self.items.values() if it.location == "player"]

    def has_light(self) -> bool:
        if not self.room.dark:
            return True
        lantern = self.item("lantern")
        return lantern.lit and lantern.location in ("player", self.location)

    def tide_pos(self, turns: Optional[int] = None) -> int:
        t = self.turns if turns is None else turns
        return (START_POS + t) % CYCLE_LEN

    def tide_phase(self, turns: Optional[int] = None) -> str:
        pos = self.tide_pos(turns)
        for name, length in CYCLE:
            if pos < length:
                return name
            pos -= length
        return CYCLE[-1][0]

    def tide_remaining(self) -> int:
        pos = self.tide_pos()
        for name, length in CYCLE:
            if pos < length:
                return length - pos
            pos -= length
        return 0

    def low_town_open(self) -> bool:
        return self.tide_phase() in ("low", "flooding")

    def award(self, flag: str, points: int, message: Optional[str] = None) -> None:
        if flag in self.flags:
            return
        self.flags.add(flag)
        self.score += points
        if message:
            self.say(message)

    def rank(self) -> str:
        for threshold, title in RANKS:
            if self.score >= threshold:
                return title
        return RANKS[-1][1]

    def contents(self, container_key: str) -> List[Item]:
        return [it for it in self.items.values() if it.location == container_key]

    def list_names(self, items: List[Item]) -> str:
        names = [it.full_name() for it in items]
        if not names:
            return "nothing"
        if len(names) == 1:
            return names[0]
        return ", ".join(names[:-1]) + " and " + names[-1]

    # ------------------------------------------------------------------ scope

    def scope(self) -> List[Item]:
        lit = self.has_light()
        found = []
        for it in self.items.values():
            if it.location == "player":
                found.append(it)
            elif it.location == "*":
                found.append(it)
            elif lit and it.location == self.location:
                found.append(it)
        for c in list(found):
            if c.container and c.is_open:
                found.extend(self.contents(c.key))
        return found

    def resolve(self, phrase: List[str], quiet: bool = False) -> Optional[Item]:
        if not phrase:
            return None
        if phrase == ["it"] or phrase == ["them"]:
            if self.last_it and self.item(self.last_it) in self.scope():
                return self.item(self.last_it)
            if not quiet:
                self.say("I'm not sure what \"it\" refers to.")
            return None
        adjs, noun = phrase[:-1], phrase[-1]
        known = any(noun in it.words or noun in it.adjectives for it in self.items.values())
        if not known:
            if not quiet:
                self.say("I don't know the word \"%s\"." % noun)
            return None
        candidates = []
        for it in self.scope():
            if noun in it.words and all(a in it.adjectives or a in it.words for a in adjs):
                candidates.append(it)
        if len(candidates) == 1:
            self.last_it = candidates[0].key
            return candidates[0]
        if not candidates:
            if not quiet:
                if not self.has_light():
                    self.say("It's too dark to see any %s here." % noun)
                else:
                    self.say("You don't see any %s here." % " ".join(phrase))
            return None
        if not quiet:
            names = [c.full_name(definite=True) for c in candidates]
            self.say("Which do you mean, %s?" % (", ".join(names[:-1]) + " or " + names[-1]))
        return None

    # ------------------------------------------------------------------ descriptions

    def room_desc(self, room: Room) -> str:
        phase = self.tide_phase()
        key = room.key
        if key == "lamp_room":
            if phase == "low":
                view = ("Below, the Low Town lies bared to the sky, its streets glistening, "
                        "weed hanging from every window like washing.")
            elif phase == "flooding":
                view = ("Below, the sea is pouring back into the Low Town through every "
                        "street at once.")
            elif phase == "ebbing":
                view = ("Below, the water is sliding off the Low Town, and the roofs are "
                        "coming up out of it one by one.")
            else:
                view = ("Below, the Low Town lies under a sheet of grey water. Only the "
                        "chapel roof and a single mast show above it.")
            return room.desc + " " + view
        if key == "sea_wall":
            if phase == "low":
                view = ("Beyond and below, the Low Town stands exposed, its streets running "
                        "with water, its doorways black.")
            elif phase == "flooding":
                view = ("Beyond and below, the sea is sheeting back across the cobbles of "
                        "the Low Town, faster than a man can walk.")
            elif phase == "ebbing":
                view = ("Beyond and below, the water is draining off the Low Town, but the "
                        "streets are still deep.")
            else:
                view = ("Beyond and below, the Low Town is drowned. Grey water laps a few "
                        "feet beneath the parapet, and a chapel roof and a mast stand out "
                        "of it.")
            rope = ""
            if "rope_tied" in self.flags:
                rope = " Your rope is tied to the bollard and hangs down the face of the wall."
            return room.desc + " " + view + rope
        if key == "rookery":
            if "gannets" in self.flags:
                return (room.desc + " At the moment, though, every bird within fifty yards "
                        "is shrieking over the remains of a salt cod.")
            return room.desc
        if key == "harbor_square":
            if "rope_tied" in self.flags:
                return room.desc + " A rope hangs down the wall from the parapet above."
            return room.desc
        if key == "fish_market":
            if "eel" in self.flags:
                return room.desc + " The water in the pool has gone still."
            return (room.desc + " Something long and dark moves in the pool, slow as a "
                    "thought you don't want to finish.")
        if key == "crypt":
            if self.item("sarcophagus").is_open:
                return room.desc.replace("its lid carved", "its lid levered aside, carved")
            return room.desc
        if key == "wreck_deck":
            if phase in ("high", "ebbing"):
                return (room.desc.replace("The mud flats lie west.",
                        "Where the mud flats were, there is only black water, slapping at "
                        "the hull a foot below the rail."))
            return room.desc
        return room.desc

    def item_desc(self, it: Item) -> str:
        key = it.key
        phase = self.tide_phase()
        if key == "lantern":
            if it.lit:
                state = "It is lit, and burning steadily."
                if self.fuel <= 10:
                    state = "It is lit, but the flame is guttering. There is very little oil left."
                elif self.fuel <= 30:
                    state = "It is lit. The flame is lower than it was; the oil is running down."
            else:
                state = "It is not lit." if self.fuel > 0 else "It is not lit, and the reservoir is dry."
            return it.desc + " " + state
        if key == "locker":
            if it.is_open:
                inside = self.contents("locker")
                if inside:
                    return it.desc + " The lid is open. Inside: %s." % self.list_names(inside)
                return it.desc + " The lid is open. It is empty."
            return it.desc + " The lid is closed."
        if key == "safe":
            if it.is_open:
                inside = self.contents("safe")
                return it.desc + " The door stands open. Inside: %s." % self.list_names(inside)
            return it.desc
        if key == "sarcophagus":
            if it.is_open:
                inside = self.contents("sarcophagus")
                if inside:
                    return ("The lid has been levered aside. Inside, on a bed of rotted velvet: "
                            "%s." % self.list_names(inside))
                return "The lid has been levered aside. Inside is only rotted velvet and dust."
            return it.desc
        if key == "tin":
            if it.is_open:
                inside = self.contents("tin")
                if inside:
                    return it.desc + " Inside: %s." % self.list_names(inside)
                return it.desc + " It is empty."
            return it.desc + " It is closed."
        if key == "windows":
            return self.room_desc(self.rooms["lamp_room"]).split("Windows look out on every side. ")[-1]
        if key == "gannets":
            if "gannets" in self.flags:
                return ("The gannets are a shrieking white knot around the cod, stabbing at it "
                        "and each other. They have forgotten you entirely.")
            return ("Big white birds with black-tipped wings and eyes like chips of slate. "
                    "They are between you and the nests, and they are not moving.")
        if key == "eel":
            if "eel" in self.flags:
                return "The eel hangs dead in the water, as long as you are tall."
            return ("An eel as thick as your arm and as long as you are tall, lying along the "
                    "bottom of the pool with its jaw slightly open. It has not blinked. It "
                    "does not need to.")
        if key == "pool":
            parts = ["A pool of black water, deeper than it looks, fed by a drain that runs "
                     "under the market."]
            if "eel" not in self.flags:
                parts.append("The eel lies along the bottom of it.")
            if self.item("pearl").location == "fish_market":
                parts.append("Something pale gleams down there.")
            return " ".join(parts)
        if key == "rope":
            if "rope_tied" in self.flags:
                return "The rope is knotted fast to the bollard and hangs down over the wall."
            return it.desc
        if key == "cabin_door":
            if "cabin" in self.flags:
                return "A low iron-bound door, unlocked and standing open on a dark stair."
            return "A low iron-bound door, shut fast. There is a keyhole, and the lock is brass."
        if key == "wreck":
            return ("The Merrow's Grace, a forty-foot ketch, beached on her side with her "
                    "deck canted toward you. Her mast stands. Her name is still legible "
                    "on the stern, in gold.")
        if key == "sea":
            if self.room.key in ("lamp_room", "sea_wall"):
                return self.room_desc(self.room).split(". ")[-1]
            if phase == "low":
                return "The sea has drawn back to the harbor mouth, where it waits."
            if phase == "flooding":
                return "The sea is coming back. It is not hurrying, and it does not need to."
            if phase == "ebbing":
                return "The sea is sliding back off the town, grudgingly."
            return "Grey, cold, patient, and everywhere it ought not to be."
        return it.desc

    def describe_room(self, full: bool) -> None:
        room = self.room
        if not self.has_light():
            self.say("It is pitch dark. Somewhere close, many voices are singing, very "
                     "softly, a hymn with too many parts.")
            return
        self.say(room.name)
        if full:
            self.say(self.room_desc(room))
        self.list_contents(room)

    def list_contents(self, room: Room) -> None:
        plain = []
        for it in self.items.values():
            if it.location != room.key:
                continue
            if it.key == "rope" and "rope_tied" in self.flags:
                continue
            if it.scenery and not it.moved:
                if it.container and it.is_open and it.key in ("safe", "sarcophagus"):
                    inside = self.contents(it.key)
                    if inside:
                        self.say("%s stands open. Inside: %s." % (
                            it.full_name(definite=True).capitalize(), self.list_names(inside)))
                continue
            if it.initial and not it.moved:
                self.say(it.initial)
            else:
                plain.append(it)
            if it.container and it.is_open:
                inside = self.contents(it.key)
                if inside:
                    self.say("%s contains %s." % (
                        it.full_name(definite=True).capitalize(), self.list_names(inside)))
        if plain:
            if len(plain) == 1:
                self.say("There is %s here." % plain[0].full_name())
            else:
                self.say("There are %s here." % self.list_names(plain))

    # ------------------------------------------------------------------ main loop

    def intro(self) -> None:
        self.say(INTRO)
        self.say("")
        self.describe_room(full=True)

    def do(self, line: str) -> None:
        line = line.strip()
        if self.over:
            return
        if self.dead:
            self.handle_dead(line)
            return
        low = line.lower().strip()
        if low in ("again", "g"):
            if not self.last_command:
                self.say("You haven't done anything yet.")
                return
            line = self.last_command
        cmd = parse(line)
        if cmd.error:
            self.say(cmd.error)
            return
        meta = cmd.verb in ("score", "save", "restore", "quit", "restart", "help",
                            "verbose", "brief", "inventory", "tide", "look", "examine", "read", "diagnose")
        if not meta:
            self.last_command = line
        took_time = self.execute(cmd)
        if took_time and not self.dead and not self.over:
            self.tick()

    def handle_dead(self, line: str) -> None:
        word = line.lower().split()[:1]
        if word == ["restart"]:
            self.restart()
        elif word == ["restore"]:
            self.act_restore(Command(verb="restore", raw=line))
        elif word in (["quit"], ["q"]):
            self.over = True
            self.say("The sea keeps what it takes. Goodbye.")
        else:
            self.say("Please type RESTART, RESTORE, or QUIT.")

    def restart(self) -> None:
        out = self._out
        seed = self.seed
        self.__init__(seed=seed, out=out)
        self.intro()

    def execute(self, cmd: Command) -> bool:
        handler = getattr(self, "act_" + cmd.verb, None)
        if handler is None:
            self.say("That isn't something you can do here.")
            return False
        result = handler(cmd)
        return True if result is None else result

    # ------------------------------------------------------------------ time and tide

    def tick(self, quiet: bool = False) -> None:
        self.turns += 1
        lantern = self.item("lantern")
        if lantern.lit:
            self.fuel -= 1
            near = lantern.location in ("player", self.location)
            if self.fuel <= 0:
                lantern.lit = False
                self.fuel = 0
                if near:
                    self.say("Your lantern flickers, flares blue, and goes out.")
                    if not self.has_light():
                        self.describe_room(full=False)
            elif near and self.fuel in (30, 10, 5):
                self.say({
                    30: "The lantern flame dips. The oil is getting low.",
                    10: "The lantern is guttering. You have very little oil left.",
                    5: "The lantern flame is a blue bead. Minutes, at most.",
                }[self.fuel])
        old = self.tide_phase(self.turns - 1)
        new = self.tide_phase(self.turns)
        if new != old:
            self.say(BELL[new])
        if self.room.tidal:
            if new == "high":
                self.drown()
                return
            if new == "flooding":
                pos = self.tide_pos() - CYCLE[0][1]
                if pos <= 1:
                    self.say("Seawater is sheeting across the stones around your ankles.")
                elif pos <= 3:
                    self.say("The water is at your knees and rising fast.")
                else:
                    self.say("The water is at your waist and the current drags at you. GET OUT.")
        elif self.room.key in ("wreck_deck", "cabin") and new == "flooding" and old != "flooding":
            self.say("Water is climbing the hull below you. The wreck will stand above it, "
                     "as she always has, but the flats will not.")

    def drown(self) -> None:
        self.say("The sea comes back the way it left: all at once. The water lifts you off "
                 "your feet, turns you over, and carries you into the dark between the "
                 "houses, where a great many hands are waiting to welcome you.")
        self.die("You have drowned")

    def die(self, headline: str) -> None:
        self.dead = True
        self.say("\n    ****  %s  ****\n" % headline)
        self.say("Your score is %d of a possible %d, in %d moves. That gives you the rank "
                 "of %s." % (self.score, MAX_SCORE, self.turns, self.rank()))
        self.say("Would you like to RESTART, RESTORE, or QUIT?")

    def win(self) -> None:
        self.won = True
        self.award("finished", BONUSES["finished"])
        self.say(ENDING)
        self.say("\n    ****  You have won  ****\n")
        self.say("Your score is %d of a possible %d, in %d moves. That gives you the rank "
                 "of %s." % (self.score, MAX_SCORE, self.turns, self.rank()))
        self.over = True

    # ------------------------------------------------------------------ movement

    def act_go(self, cmd: Command) -> bool:
        direction = cmd.direction
        if direction is None and cmd.noun:
            direction = DIRECTIONS.get(cmd.noun[0])
        if direction is None:
            self.say("Go where?")
            return False
        return self.move(direction)

    def move(self, direction: str) -> bool:
        room = self.room
        if direction not in room.exits:
            if room.key == "sea_wall" and direction in ("down", "south"):
                pass
            elif direction == "in" or direction == "out":
                self.say("You'd have to say where.")
                return False
            else:
                self.say(self.blocked_message(room, direction))
                return False
        dest = room.exits[direction]

        if room.key == "sea_wall" and dest == "harbor_square":
            if not self.low_town_open():
                if self.tide_phase() == "ebbing":
                    self.say("The water is draining off the streets below, but it is still "
                             "deep enough to drown in. Wait for the bell.")
                else:
                    self.say("Below the wall there is only black water, lapping a few feet "
                             "under the parapet. You'll have to wait for the ebb.")
                return True
            if "rope_tied" not in self.flags:
                self.say("The lower steps are gone. It is a sheer twelve feet to the stones, "
                         "and the stones are not soft. You would need a rope.")
                return True
            if self.tide_phase() == "flooding":
                self.say("You go down the rope hand over hand and drop into water that is "
                         "already over the cobbles. Whatever you are here for, be quick.")
            else:
                self.say("You go down the rope hand over hand and drop onto the wet stones.")
        if room.key == "harbor_square" and dest == "sea_wall":
            self.say("You haul yourself up the rope and over the parapet.")
        if room.key == "wreck_deck" and dest == "mud_flats":
            if not self.low_town_open():
                self.say("There is nothing west of the rail but black water. You will have "
                         "to wait on the wreck for the sea to go out.")
                return True
            if self.tide_phase() == "flooding":
                self.say("You drop over the rail into rising water.")
        if room.key == "wreck_deck" and dest == "cabin" and "cabin" not in self.flags:
            self.say("The cabin door is locked.")
            return True

        if not self.has_light():
            if self.rng.random() < 0.5:
                self.say("You grope forward into the dark. The singing stops. Cold hands "
                         "take your arms, gently, the way you would take a child's, and "
                         "lead you down.")
                self.die("You have joined the choir")
                return False
            self.say("You feel your way forward, one hand on the wet stone, and the "
                     "singing stays where it was.")

        self.location = dest
        new_room = self.room
        first = not new_room.visited
        if new_room.key == "harbor_square":
            self.award("descended", BONUSES["descended"])
        if dest == "cabin":
            self.say("You climb down a steep companionway into the cabin.")
        self.describe_room(full=first or self.verbose)
        new_room.visited = True
        return True

    def blocked_message(self, room: Room, direction: str) -> str:
        if room.key == "rookery" and direction in ("north", "east", "west", "down"):
            return "The rock ends in a two-hundred-foot drop to the surf."
        if room.key == "cliff_path" and direction == "east":
            return "The headland falls away to the sea."
        if room.key == "mud_flats" and direction in ("north", "south"):
            return "The mud goes soft and then softer. You stop before it stops you."
        if room.key == "lamp_room" and direction == "up":
            return "Only the roof, and the gulls."
        if room.key == "wreck_deck" and direction in ("north", "south", "east", "up"):
            return "There is nothing that way but mud, or water, depending."
        return "You can't go that way."

    def act_climb(self, cmd: Command) -> bool:
        if cmd.direction:
            return self.move(cmd.direction)
        if cmd.noun:
            word = cmd.noun[-1]
            if word in ("rope", "wall") and self.room.key == "sea_wall":
                return self.move("down")
            if word in ("rope", "wall") and self.room.key == "harbor_square":
                return self.move("up")
            if word in ("stair", "stairs", "steps", "ladder", "companionway"):
                if "up" in self.room.exits:
                    return self.move("up")
                if "down" in self.room.exits:
                    return self.move("down")
            if word in ("mast",):
                self.say("The mast is slick as glass. You get six feet up it and slide back down.")
                return True
            if word in ("tree", "cliff", "rock", "tower", "lighthouse"):
                self.say("There's a perfectly good stair for that.")
                return False
        if "up" in self.room.exits:
            return self.move("up")
        if "down" in self.room.exits:
            return self.move("down")
        self.say("There's nothing here to climb.")
        return False

    ENTER_TARGETS = {
        "mud_flats": {"wreck": "east", "ketch": "east", "ship": "east", "boat": "east",
                      "grace": "east", "deck": "east"},
        "wreck_deck": {"cabin": "down", "door": "down", "hatch": "down"},
        "harbor_square": {"chapel": "south", "church": "south", "market": "east",
                          "office": "west"},
        "cliff_path": {"lighthouse": "west", "tower": "west", "light": "west"},
        "high_street": {"chandlery": "east", "chandler's": "east", "shop": "west",
                        "toymaker's": "west", "toymaker": "west"},
        "harbor_steps": {"smokehouse": "east", "shed": "east"},
        "base": {"door": "out"},
        "chapel": {"crypt": "down"},
    }

    def act_enter(self, cmd: Command) -> bool:
        if cmd.noun:
            targets = self.ENTER_TARGETS.get(self.room.key, {})
            d = targets.get(cmd.noun[-1])
            if d:
                return self.move(d)
            if cmd.noun[-1] in ("pool", "water", "sea"):
                return self.act_swim(cmd)
            self.say("You can't get into that.")
            return False
        if "in" in self.room.exits:
            return self.move("in")
        self.say("You'd have to say where.")
        return False

    # ------------------------------------------------------------------ looking

    def act_look(self, cmd: Command) -> bool:
        self.describe_room(full=True)
        return False

    def act_examine(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.describe_room(full=True)
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        self.say(self.item_desc(it))
        return False

    def act_read(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Read what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if not self.has_light() and it.location != "player":
            self.say("It's too dark to read.")
            return False
        if not self.has_light():
            self.say("It's too dark to read anything.")
            return False
        if it.readable:
            self.say(it.readable)
        elif it.key == "medal":
            self.say(it.desc)
        else:
            self.say("There's nothing written on %s." % it.full_name(definite=True))
        return False

    def act_search(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("You poke about and find nothing you hadn't already seen.")
            return True
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if it.key == "bunk":
            tin = self.item("tin")
            if tin.location is None:
                tin.location = "quarters"
                self.say("You pull back the stiff blankets. Beneath the straw mattress your "
                         "hand finds a small tin box, which you set on the floor.")
            else:
                self.say("Only straw, and the shape of someone who is not there any more.")
            return True
        if it.key == "nest":
            if self.item("ring").location == "rookery":
                self.say("Fish bones, weed, a bottle cap, and the gold thing you already noticed.")
            else:
                self.say("Fish bones and weed.")
            return True
        if it.container:
            if not it.is_open:
                self.say("%s is closed." % it.full_name(definite=True).capitalize())
            else:
                inside = self.contents(it.key)
                self.say("Inside: %s." % self.list_names(inside) if inside else "It's empty.")
            return True
        self.say("You find nothing of interest.")
        return True

    def act_look_through(self, cmd: Command) -> bool:
        it = self.resolve(cmd.noun) if cmd.noun else None
        if it is None:
            if cmd.noun:
                return False
            self.say("Look through what?")
            return False
        if it.key == "windows":
            self.say(self.item_desc(it))
            return True
        if it.key != "spyglass":
            self.say("You can't see through that.")
            return False
        if self.room.key in ("lamp_room", "sea_wall", "cliff_path", "rookery"):
            self.say("You put the glass to your eye. Beyond the harbor mouth, where the "
                     "water goes from grey to black, something long and pale is circling. "
                     "It has been circling, you think, for a long time. It is waiting for "
                     "the bell.")
        elif self.room.key == "cabin":
            self.say("Through the glass, the cabin is only larger and darker.")
        else:
            self.say("Everything is very large and very close and no more interesting for it.")
        return True

    def act_inventory(self, cmd: Command) -> bool:
        items = self.inventory_items()
        if not items:
            self.say("You are empty-handed.")
            return False
        lines = ["You are carrying:"]
        for it in items:
            label = it.full_name()
            if it.key == "lantern" and it.lit:
                label += " (lit)"
            lines.append("  " + label)
            if it.container and it.is_open:
                inside = self.contents(it.key)
                if inside:
                    lines.append("    containing " + self.list_names(inside))
        self._out("\n".join(lines))
        return False

    # ------------------------------------------------------------------ handling

    def act_take(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Take what?")
            return False
        if cmd.noun == ["all"] or cmd.noun == ["everything"]:
            if not self.has_light():
                self.say("You fumble about in the dark and find nothing but wet stone.")
                return True
            took = False
            for it in list(self.items.values()):
                if it.location == self.location and it.portable and not it.scenery:
                    self._prefix = "%s: " % it.full_name().capitalize()
                    self.take_item(it)
                    took = True
            if not took:
                self.say("There is nothing here worth taking.")
            return True
        if cmd.prep in ("from", "out") and cmd.noun2:
            container = self.resolve(cmd.noun2)
            if container is None:
                return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if cmd.verb == "take" and it.key == "sarcophagus":
            return self.act_pry(cmd)
        return self.take_item(it)

    def take_item(self, it: Item) -> bool:
        if it.location == "player":
            self.say("You already have that.")
            return False
        if it.key == "rope" and "rope_tied" in self.flags:
            self.say("It's tied fast to the bollard. You'd have to untie it first.")
            return True
        if not it.portable:
            self.say(it.fixed_msg or "You can't take that.")
            return True
        if it.key == "ring" and "gannets" not in self.flags:
            self.say("You take one step toward the nest and the gannets come off the rock "
                     "like a thrown sheet. Beaks and wings. You stagger back with your arms "
                     "over your face, and when you lower them the ring is where it was and "
                     "so are the birds.")
            return True
        if it.key == "pearl" and "eel" not in self.flags:
            self.say("You reach down into the cold water. The eel is faster than you are, "
                     "and only just misses, and you sit down hard on the wet stone with "
                     "all your fingers and a new respect for it.")
            return True
        if len(self.inventory_items()) >= 10:
            self.say("Your arms are full. You'll have to put something down.")
            return True
        it.location = "player"
        it.moved = True
        if it.treasure and ("took_" + it.key) not in self.flags:
            self.flags.add("took_" + it.key)
            self.score += it.treasure[0]
        self.say("Taken.")
        return True

    def act_drop(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Drop what?")
            return False
        if cmd.noun == ["all"] or cmd.noun == ["everything"]:
            items = self.inventory_items()
            if not items:
                self.say("You are empty-handed.")
                return False
            for it in items:
                self._prefix = "%s: " % it.full_name().capitalize()
                self.drop_item(it)
            return True
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        return self.drop_item(it)

    def drop_item(self, it: Item) -> bool:
        if it.location != "player":
            self.say("You aren't carrying that.")
            return False
        if it.key == "cod" and self.room.key == "rookery":
            return self.feed_gannets()
        it.location = self.location
        it.moved = True
        if self.room.key == "fish_market" and it.key == "cod":
            self.say("Dropped. The eel does not so much as glance at it.")
            return True
        self.say("Dropped.")
        return True

    def act_put(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Put what?")
            return False
        if not cmd.noun2:
            if cmd.prep == "down" or cmd.prep is None:
                return self.act_drop(cmd)
            self.say("Put it where?")
            return False
        container = self.resolve(cmd.noun2)
        if container is None:
            return False
        if cmd.noun == ["all"] or cmd.noun == ["everything"]:
            items = [it for it in self.inventory_items() if it.key != container.key]
            if not items:
                self.say("You are empty-handed.")
                return False
            for it in items:
                if self.over:
                    break
                self._prefix = "%s: " % it.full_name().capitalize()
                self.put_item(it, container, cmd.prep)
            return True
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        return self.put_item(it, container, cmd.prep)

    def put_item(self, it: Item, container: Item, prep: Optional[str]) -> bool:
        if it.location != "player":
            self.say("You aren't carrying %s." % it.full_name(definite=True))
            return False
        if it.key == container.key:
            self.say("That would be a neat trick.")
            return False
        if container.key == "pool":
            if it.key == "cod":
                self.say("The cod sinks. The eel watches it go down with no interest "
                         "whatsoever. It wants something warmer.")
                it.location = None
                return True
            self.say("You'd never get it back.")
            return False
        if container.key == "gannets":
            if it.key == "cod":
                return self.feed_gannets()
            self.say("The gannets want nothing from you but your absence.")
            return True
        if container.key == "eel":
            self.say("The eel ignores it. It wants something warmer.")
            return True
        if prep in ("on", "onto") and not container.container:
            return self.drop_item(it)
        if not container.container:
            self.say("You can't put anything in that.")
            return False
        if not container.is_open:
            self.say("%s is closed." % container.full_name(definite=True).capitalize())
            return True
        if container.key == "tin" and it.key not in ("medal", "brass_key", "pearl", "ring"):
            self.say("It won't fit.")
            return True
        it.location = container.key
        it.moved = True
        if container.key == "locker" and it.treasure and ("stored_" + it.key) not in self.flags:
            self.flags.add("stored_" + it.key)
            self.score += it.treasure[1]
            self.say("You lay %s in the locker. It settles there as if it had never been "
                     "anywhere else." % it.full_name(definite=True))
            if all(self.item(k).location == "locker" for k in TREASURES):
                self.win()
            return True
        self.say("Done.")
        return True

    def act_open(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Open what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if cmd.prep in ("with", "using") and cmd.noun2 and it.key == "sarcophagus":
            return self.act_pry(cmd)
        if it.key == "cabin_door":
            if "cabin" in self.flags:
                self.say("It's already open. A steep stair goes down into the dark.")
            else:
                self.say("It's locked. The lock is brass, and wants a brass key.")
            return True
        if not it.openable:
            self.say("You can't open that.")
            return False
        if it.is_open:
            self.say("It's already open.")
            return False
        if it.locked:
            if it.key == "safe":
                self.say("It's locked. There's no keyhole, only the numbered dial.")
            elif it.key == "sarcophagus":
                if self.carrying("crowbar"):
                    return self.act_pry(cmd)
                self.say("The lid weighs as much as you do and is sealed with eighty years "
                         "of salt. You would need to lever it.")
            else:
                self.say("It's locked.")
            return True
        it.is_open = True
        inside = self.contents(it.key)
        if inside:
            self.say("Opening %s reveals %s." % (it.full_name(definite=True), self.list_names(inside)))
        else:
            self.say("Opened.")
        return True

    def act_close(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Close what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if not it.openable:
            self.say("You can't close that.")
            return False
        if it.key == "sarcophagus":
            self.say("You could no more close it than open it bare-handed, and you have no "
                     "wish to try.")
            return True
        if not it.is_open:
            self.say("It's already closed.")
            return False
        it.is_open = False
        self.say("Closed.")
        return True

    # ------------------------------------------------------------------ light and oil

    def act_light(self, cmd: Command) -> bool:
        if not cmd.noun:
            if self.carrying("lantern"):
                it = self.item("lantern")
            else:
                self.say("Light what?")
                return False
        else:
            it = self.resolve(cmd.noun)
            if it is None:
                return False
        if it.key == "great_lamp":
            self.say("There is no oil in the great lamp and no wick to carry a flame. It "
                     "is cold brass and glass, and it is waiting for something else.")
            return True
        if it.key != "lantern":
            self.say("That won't burn, or shouldn't.")
            return False
        if it.lit:
            self.say("It's already lit.")
            return False
        if self.fuel <= 0:
            self.say("The lantern is dry. It would need oil.")
            return True
        was_dark = not self.has_light()
        it.lit = True
        self.say("The wick catches, and warm light pushes the dark back to the walls.")
        if was_dark:
            self.describe_room(full=True)
            self.room.visited = True
        return True

    def act_extinguish(self, cmd: Command) -> bool:
        it = self.resolve(cmd.noun) if cmd.noun else (self.item("lantern") if self.carrying("lantern") else None)
        if it is None:
            if not cmd.noun:
                self.say("Extinguish what?")
            return False
        if it.key != "lantern":
            self.say("It isn't burning.")
            return False
        if not it.lit:
            self.say("It isn't lit.")
            return False
        it.lit = False
        self.say("You turn down the wick and the lantern goes out.")
        if not self.has_light():
            self.describe_room(full=False)
        return True

    def act_fill(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Fill what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if it.key != "lantern":
            self.say("You can't fill that.")
            return False
        if self.item("cask").location != self.location:
            self.say("There's nothing here to fill it from.")
            return False
        if self.fuel >= LANTERN_FULL - 10:
            self.say("The lantern is already full, or near enough.")
            return False
        if self.refills <= 0:
            self.say("You open the tap. A last dribble of oil, and then nothing. The cask is dry.")
            return True
        self.refills -= 1
        self.fuel = LANTERN_FULL
        self.say("You open the tap and fill the lantern's reservoir to the brim with "
                 "whale oil. It smells like the inside of a church.")
        if self.refills == 0:
            self.say("The cask sounds hollow when you knock it. That was the last of it.")
        return True

    # ------------------------------------------------------------------ puzzles

    def act_turn(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Turn what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if it.key in ("dial", "safe"):
            if cmd.number is None:
                self.say("The dial turns with a dry click, and another. It wants a number.")
                return True
            if cmd.number == SAFE_COMBINATION:
                if self.item("safe").locked:
                    self.item("safe").locked = False
                    self.award("safe", BONUSES["safe"])
                    self.say("You turn the dial to %d. Deep in the door, something goes "
                             "clunk, like a heart remembering." % cmd.number)
                else:
                    self.say("The safe is already unlocked.")
                return True
            self.say("You turn the dial to %d. It clicks. Nothing else happens." % cmd.number)
            return True
        if it.key == "music_box":
            return self.act_wind(cmd)
        if it.key == "lantern":
            self.say("Up or down? Say LIGHT or EXTINGUISH.")
            return False
        self.say("It doesn't turn.")
        return False

    def act_unlock(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Unlock what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        key = None
        if cmd.noun2:
            key = self.resolve(cmd.noun2)
            if key is None:
                return False
        if it.key == "cabin_door":
            if "cabin" in self.flags:
                self.say("It's already unlocked.")
                return False
            if key is None:
                if self.carrying("brass_key"):
                    key = self.item("brass_key")
                else:
                    self.say("You have nothing to unlock it with.")
                    return True
            if key.key != "brass_key":
                self.say("That doesn't fit.")
                return True
            if key.location != "player":
                self.say("You aren't holding the key.")
                return True
            self.flags.add("cabin")
            self.award("cabin_bonus", BONUSES["cabin"])
            self.say("The brass key turns stiffly, and the door swings inward on a steep, "
                     "dark stair that smells of tar and eighty years.")
            return True
        if it.key == "safe":
            self.say("There's no keyhole, only the dial.")
            return True
        if it.key == "sarcophagus":
            self.say("It isn't locked, exactly. It's just very heavy and very sealed.")
            return True
        if it.key in ("locker", "tin"):
            self.say("It isn't locked.")
            return False
        self.say("That doesn't have a lock.")
        return False

    def act_lock(self, cmd: Command) -> bool:
        self.say("You have better things to do than lock things.")
        return False

    def act_pry(self, cmd: Command) -> bool:
        target = None
        if cmd.noun:
            target = self.resolve(cmd.noun)
            if target is None:
                return False
        tool = None
        if cmd.noun2:
            tool = self.resolve(cmd.noun2)
            if tool is None:
                return False
        if target is None:
            self.say("Pry what?")
            return False
        if tool is None:
            if self.carrying("crowbar"):
                tool = self.item("crowbar")
            else:
                self.say("You have nothing to pry with. Your fingers won't do it.")
                return True
        if tool.key != "crowbar":
            self.say("%s is not up to that." % tool.full_name(definite=True).capitalize())
            return True
        if target.key == "sarcophagus":
            if target.is_open:
                self.say("The lid is already off.")
                return False
            target.locked = False
            target.is_open = True
            self.award("sarcophagus", BONUSES["sarcophagus"])
            inside = self.contents("sarcophagus")
            self.say("You work the crowbar into the gap under the lid and lean on it with "
                     "everything you have. Salt cracks like ice. The lid grinds aside a "
                     "foot and stops, and in the lantern light you see, on a bed of rotted "
                     "velvet, %s." % self.list_names(inside))
            return True
        if target.key == "cabin_door":
            self.say("The crowbar skids off the iron banding. The door wants a key, and "
                     "the ship wants you to find it.")
            return True
        if target.key == "safe":
            self.say("The crowbar bends. The safe does not.")
            return True
        if target.key in ("locker", "tin"):
            self.say("It opens perfectly well by hand.")
            return False
        self.say("There's nothing to pry there.")
        return False

    def act_attack(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Attack what?")
            return False
        target = self.resolve(cmd.noun)
        if target is None:
            return False
        weapon = None
        if cmd.noun2:
            weapon = self.resolve(cmd.noun2)
            if weapon is None:
                return False
        if target.key == "eel":
            if "eel" in self.flags:
                self.say("It's quite dead.")
                return False
            if weapon is None:
                if self.carrying("gaff"):
                    weapon = self.item("gaff")
                else:
                    self.say("With your bare hands? The eel has more teeth than you have fingers.")
                    return True
            if weapon.key != "gaff":
                if weapon.key == "crowbar":
                    self.say("You swing the crowbar into the pool. The water takes the force "
                             "out of it and the eel takes a lazy interest in your wrist. You "
                             "stop.")
                else:
                    self.say("That would only annoy it.")
                return True
            self.flags.add("eel")
            self.award("eel_bonus", BONUSES["eel"])
            self.say("You wait until the eel turns, and drive the gaff down past its head "
                     "and heave. It comes out of the pool in a thrashing, muscular arc, "
                     "longer than you are tall, and goes still on the stones after a "
                     "while. The pool goes quiet.")
            return True
        if target.key == "gannets":
            self.say("They have numbers, beaks, and the high ground. You have a bad idea. "
                     "You keep it.")
            return True
        if target.key == "self":
            self.say("The sea will see to that if you let it.")
            return False
        if target.scenery:
            self.say("Violence won't help here.")
            return False
        self.say("You can't hurt %s. It's already had a worse day than you can give it." %
                 target.full_name(definite=True))
        return False

    def feed_gannets(self) -> bool:
        if "gannets" in self.flags:
            self.say("They're busy.")
            return True
        cod = self.item("cod")
        cod.location = None
        cod.moved = True
        self.flags.add("gannets")
        self.award("gannets_bonus", BONUSES["gannets"])
        self.say("You throw the cod as far along the rock as you can. For a moment nothing "
                 "happens. Then every gannet on the headland is in the air at once and "
                 "coming down on it, and the noise is like the end of the world. The nests "
                 "are unguarded.")
        return True

    def act_give(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Give what?")
            return False
        it = None
        target = None
        if cmd.noun2:
            it = self.resolve(cmd.noun)
            if it is None:
                return False
            target = self.resolve(cmd.noun2)
            if target is None:
                return False
        else:
            # "feed gannets" or "give gannets cod"
            if len(cmd.noun) >= 2:
                target = self.resolve(cmd.noun[:1], quiet=True)
                it = self.resolve(cmd.noun[1:], quiet=True)
            if target is None or it is None:
                single = self.resolve(cmd.noun)
                if single is None:
                    return False
                if single.key in ("gannets", "eel"):
                    target = single
                    if self.carrying("cod"):
                        it = self.item("cod")
                    else:
                        self.say("You have nothing it would want.")
                        return True
                else:
                    self.say("Give it to whom?")
                    return False
        if it.location != "player":
            self.say("You aren't carrying that.")
            return False
        if target.key == "gannets":
            if it.key == "cod":
                return self.feed_gannets()
            self.say("The gannets want nothing from you but your absence.")
            return True
        if target.key == "eel":
            if it.key == "cod":
                self.say("You dangle the cod over the water. The eel ignores it. It wants "
                         "something warmer.")
            else:
                self.say("The eel is not interested.")
            return True
        self.say("There's no one here to take it.")
        return False

    def act_throw(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Throw what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if it.location != "player":
            self.say("You aren't carrying that.")
            return False
        if it.key == "cod" and self.room.key == "rookery":
            return self.feed_gannets()
        if cmd.noun2:
            target = self.resolve(cmd.noun2)
            if target is None:
                return False
            if target.key == "eel" or target.key == "pool":
                return self.put_item(it, self.item("pool"), "in")
            if target.key == "gannets":
                return self.put_item(it, target, "at")
        if it.treasure:
            self.say("You think better of it. That's what you came for.")
            return False
        it.location = self.location
        it.moved = True
        self.say("Thrown. It lands with no great ceremony.")
        return True

    def act_tie(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Tie what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if it.key != "rope":
            self.say("You can't tie that.")
            return False
        if "rope_tied" in self.flags:
            self.say("It's already tied to the bollard.")
            return False
        if it.location != "player":
            self.say("You aren't carrying the rope.")
            return False
        target = None
        if cmd.noun2:
            target = self.resolve(cmd.noun2)
            if target is None:
                return False
        if self.room.key != "sea_wall":
            if target is not None:
                self.say("You can't tie it to that; it wouldn't hold your weight, or there's "
                         "no reason to.")
            else:
                self.say("There's nothing here worth tying it to.")
            return True
        if target is not None and target.key != "bollard":
            self.say("The bollard would be the obvious choice.")
            return True
        it.location = "sea_wall"
        it.moved = True
        self.flags.add("rope_tied")
        self.say("You make the rope fast to the bollard with a knot your father taught you "
                 "and drop the rest over the wall. It reaches the stones with a yard to "
                 "spare.")
        return True

    def act_untie(self, cmd: Command) -> bool:
        if "rope_tied" not in self.flags:
            self.say("Nothing here is tied.")
            return False
        if self.room.key != "sea_wall":
            self.say("You'd need to be at the knot.")
            return False
        rope = self.item("rope")
        rope.location = "player"
        self.flags.discard("rope_tied")
        self.say("You work the knot loose and coil the rope over your shoulder.")
        return True

    def act_wind(self, cmd: Command) -> bool:
        it = self.resolve(cmd.noun) if cmd.noun else None
        if it is None:
            if cmd.noun:
                return False
            self.say("Wind what?")
            return False
        if it.key != "music_box":
            self.say("That doesn't wind.")
            return False
        self.say("You turn the little brass key and let it go. The box plays a hymn tune, "
                 "slow and clear, in a room that has not heard a note in eighty years. "
                 "Eight bars, then a pause; then eight bars again. On the last note, the "
                 "ticking from the back of the shop stops, and waits, and starts again.")
        return True

    def act_ring(self, cmd: Command) -> bool:
        it = self.resolve(cmd.noun) if cmd.noun else None
        if cmd.noun and it is None:
            return False
        if it is not None and it.key != "bell":
            self.say("You can't ring that.")
            return False
        if it is None and self.item("bell").location != self.location:
            self.say("There's no bell here.")
            return False
        self.say("You swing the clapper by hand. The bell gives a single dull, waterlogged "
                 "note, and far below, from under the water, something answers it in kind.")
        return True

    # ------------------------------------------------------------------ time

    def act_wait(self, cmd: Command) -> bool:
        words = cmd.noun + cmd.noun2 + cmd.words
        if any(w in ("tide", "bell", "low", "ebb", "water", "sea", "high", "flood") for w in words):
            phase = self.tide_phase()
            lantern = self.item("lantern")
            if lantern.lit and lantern.location == "player":
                self.say("You wait, with the lantern burning.")
            else:
                self.say("You wait.")
            for _ in range(CYCLE_LEN):
                self.tick()
                if self.dead or self.tide_phase() != phase:
                    break
            return False
        self.say("Time passes. The sea doesn't mind.")
        return True

    def act_tide(self, cmd: Command) -> bool:
        phase = self.tide_phase()
        left = self.tide_remaining()
        word = {
            "low": "The tide is OUT. The Low Town stands open",
            "flooding": "The tide is COMING IN. The Low Town is flooding",
            "high": "The tide is IN. The Low Town is drowned",
            "ebbing": "The tide is GOING OUT. The Low Town is draining",
        }[phase]
        nxt = {"low": "the flood", "flooding": "high water", "high": "the ebb", "ebbing": "low water"}[phase]
        self.say("%s. By your reckoning the bell will ring for %s in %d turn%s." % (
            word, nxt, left, "" if left == 1 else "s"))
        return False

    # ------------------------------------------------------------------ meta

    def act_score(self, cmd: Command) -> bool:
        self.say("Your score is %d of a possible %d, in %d moves. That gives you the rank "
                 "of %s." % (self.score, MAX_SCORE, self.turns, self.rank()))
        return False

    def act_help(self, cmd: Command) -> bool:
        self.say(HELP)
        return False

    def act_verbose(self, cmd: Command) -> bool:
        self.verbose = True
        self.say("Maximum verbosity. Rooms will be described in full every time you enter them.")
        return False

    def act_brief(self, cmd: Command) -> bool:
        self.verbose = False
        self.say("Brief descriptions. Rooms are described in full only on your first visit.")
        return False

    def act_diagnose(self, cmd: Command) -> bool:
        self.say("You are cold, wet to the knee, and alive. The last of those is the one "
                 "that can change.")
        return False

    def act_quit(self, cmd: Command) -> bool:
        self.act_score(cmd)
        self.say("The sea keeps what it takes. Goodbye.")
        self.over = True
        return False

    def act_restart(self, cmd: Command) -> bool:
        self.restart()
        return False

    def act_again(self, cmd: Command) -> bool:
        self.say("You haven't done anything yet.")
        return False

    # ------------------------------------------------------------------ save and restore

    def save_filename(self, cmd: Command) -> str:
        parts = cmd.raw.split(None, 1)
        if len(parts) == 2 and parts[1].strip():
            name = parts[1].strip()
            return name if "." in os.path.basename(name) else name + ".sav"
        return "saltmarrow.sav"

    def act_save(self, cmd: Command) -> bool:
        state = {
            "version": SAVE_VERSION,
            "location": self.location,
            "turns": self.turns,
            "score": self.score,
            "flags": sorted(self.flags),
            "verbose": self.verbose,
            "fuel": self.fuel,
            "refills": self.refills,
            "last_it": self.last_it,
            "items": {k: {"location": it.location, "moved": it.moved, "is_open": it.is_open,
                          "locked": it.locked, "lit": it.lit}
                      for k, it in self.items.items()},
            "rooms": {k: r.visited for k, r in self.rooms.items()},
        }
        name = self.save_filename(cmd)
        try:
            with open(name, "w") as f:
                json.dump(state, f, indent=1)
        except OSError as e:
            self.say("Couldn't save: %s" % e)
            return False
        self.say("Saved to %s." % name)
        return False

    def act_restore(self, cmd: Command) -> bool:
        name = self.save_filename(cmd)
        try:
            with open(name) as f:
                state = json.load(f)
        except (OSError, ValueError) as e:
            self.say("Couldn't restore: %s" % e)
            return False
        if state.get("version") != SAVE_VERSION:
            self.say("That save file is from a different version of the game.")
            return False
        self.location = state["location"]
        self.turns = state["turns"]
        self.score = state["score"]
        self.flags = set(state["flags"])
        self.verbose = state["verbose"]
        self.fuel = state["fuel"]
        self.refills = state["refills"]
        self.last_it = state.get("last_it")
        for k, data in state["items"].items():
            if k in self.items:
                it = self.items[k]
                it.location = data["location"]
                it.moved = data["moved"]
                it.is_open = data["is_open"]
                it.locked = data["locked"]
                it.lit = data["lit"]
        for k, visited in state["rooms"].items():
            if k in self.rooms:
                self.rooms[k].visited = visited
        self.dead = False
        self.say("Restored.")
        self.describe_room(full=True)
        return False

    # ------------------------------------------------------------------ flavor

    def act_listen(self, cmd: Command) -> bool:
        if not self.has_light():
            self.say("Singing. Many voices, very soft, and not all of them finished with "
                     "the same line.")
        elif self.room.key in ("rookery", "cliff_path"):
            self.say("Gannets, wind, and surf, in that order.")
        elif self.room.tidal:
            self.say("Water running out of the houses. Under it, very faintly, something "
                     "that is almost a tune.")
        elif self.room.key == "toymaker":
            self.say("Something in the back of the shop ticks, slowly.")
        else:
            self.say("Wind, and the sea, which is always somewhere.")
        return True

    def act_smell(self, cmd: Command) -> bool:
        self.say("Salt, weed, and old oil. Underneath, like a note held too long, rot.")
        return True

    def act_jump(self, cmd: Command) -> bool:
        if self.room.key == "sea_wall":
            self.say("It's twelve feet onto wet stone, or into deep water, depending. Neither "
                     "ends with you walking away.")
            return True
        self.say("You jump. The ground is where you left it.")
        return True

    def act_swim(self, cmd: Command) -> bool:
        if self.room.key == "fish_market":
            self.say("Into the eel's pool? No.")
        elif self.room.key in ("sea_wall", "wreck_deck") and not self.low_town_open():
            self.say("The water is cold enough to stop your heart and there is something in "
                     "it that sings. You stay where you are.")
        else:
            self.say("There's no water here deep enough to swim in. Give it time.")
        return True

    def act_push(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Push what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if it.key == "sarcophagus":
            self.say("You set your shoulder to the lid and shove until your boots slip. "
                     "It doesn't move a hair. You would need to lever it.")
            return True
        if it.key == "safe":
            self.say("It's set into the wall, and it knows it.")
            return True
        self.say("Nothing happens.")
        return True

    def act_pull(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Pull what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if it.key == "rope" and "rope_tied" in self.flags:
            self.say("The knot holds. Good.")
            return True
        if it.key == "bell":
            return self.act_ring(cmd)
        if it.key == "sarcophagus":
            return self.act_push(cmd)
        self.say("Nothing happens.")
        return True

    def act_eat(self, cmd: Command) -> bool:
        it = self.resolve(cmd.noun) if cmd.noun else None
        if cmd.noun and it is None:
            return False
        if it is not None and it.key == "cod":
            self.say("You could sooner eat the shelf it hung on. Something with a beak "
                     "might manage it.")
            return True
        self.say("You're not that hungry. You may never be that hungry.")
        return False

    def act_drink(self, cmd: Command) -> bool:
        self.say("Everything here is salt.")
        return False

    def act_yell(self, cmd: Command) -> bool:
        if not self.has_light():
            self.say("You call out. The singing stops. Then, after a moment, it starts again, "
                     "one voice nearer than before.")
        elif self.room.key in ("chapel", "crypt"):
            self.say("Your voice goes up into the loft and comes back down with company.")
        else:
            self.say("Your voice goes out over the water and doesn't come back.")
        return True

    def act_pray(self, cmd: Command) -> bool:
        if self.room.key == "chapel":
            self.say("You kneel on the wet stone. Above you, in the empty loft, something "
                     "that might be a breeze turns the pages of a hymnal that is not there.")
        else:
            self.say("You say a few words. The sea doesn't answer. It never has.")
        return True

    def act_sleep(self, cmd: Command) -> bool:
        self.say("Not here. Not with the bell about to ring.")
        return False

    def act_dig(self, cmd: Command) -> bool:
        if self.room.key == "mud_flats":
            self.say("You dig into the mud with your hands and find more mud, a clay pipe, "
                     "and the suspicion that you should stop.")
            return True
        self.say("The ground here is stone, or near enough.")
        return False

    def act_xyzzy(self, cmd: Command) -> bool:
        self.say("A hollow voice says, \"Not here. Not that one.\"")
        return False

    def act_use(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Use what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        hints = {
            "lantern": "Try LIGHT LANTERN or EXTINGUISH LANTERN.",
            "rope": "Try TIE ROPE TO something.",
            "crowbar": "Try PRY something WITH CROWBAR.",
            "gaff": "Try ATTACK something WITH GAFF.",
            "brass_key": "Try UNLOCK something WITH KEY.",
            "cod": "Try GIVE COD TO someone, or THROW it.",
            "spyglass": "Try LOOK THROUGH SPYGLASS.",
            "music_box": "Try WIND BOX.",
            "dial": "Try TURN DIAL TO a number.",
        }
        self.say(hints.get(it.key, "You'll have to be more specific about how."))
        return False

    def act_break(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Break what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if it.key == "safe":
            self.say("You'd break yourself first.")
        elif it.treasure:
            self.say("You've come a long way for it. No.")
        else:
            self.say("Saltmarrow is broken enough.")
        return True

    def act_knock(self, cmd: Command) -> bool:
        if self.room.key in ("wreck_deck",) or (cmd.noun and cmd.noun[-1] == "door"):
            self.say("You knock. After a moment, from inside, something knocks back, once.")
        else:
            self.say("Nobody's home. Nobody has been for eighty years.")
        return True

    def act_touch(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Touch what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if it.key == "eel" and "eel" not in self.flags:
            self.say("You think about it. You think about your fingers. You don't.")
        elif it.key == "great_lamp":
            self.say("Cold. Colder than brass has any right to be, and faintly humming.")
        else:
            self.say("Wet, and cold.")
        return True

    def act_swing(self, cmd: Command) -> bool:
        if not cmd.noun:
            self.say("Swing what?")
            return False
        it = self.resolve(cmd.noun)
        if it is None:
            return False
        if it.key in ("gaff", "crowbar") and self.room.key == "rookery":
            self.say("You swing it over your head. The gannets lift, scream, and settle "
                     "again exactly where they were, which is between you and the nest.")
            return True
        if it.key == "lantern":
            self.say("Light swings around the walls and comes back to you.")
            return True
        self.say("You swing it about. Nothing is impressed.")
        return True

    def act_burn(self, cmd: Command) -> bool:
        self.say("Everything in Saltmarrow is too wet to burn, except the oil, and you need that.")
        return False

    def act_cut(self, cmd: Command) -> bool:
        self.say("You have nothing to cut with, and nothing here needs cutting.")
        return False

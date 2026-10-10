"""World data for SALTMARROW: rooms, items, and the text that describes them."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Room:
    key: str
    name: str
    desc: str
    exits: Dict[str, str] = field(default_factory=dict)
    dark: bool = False
    tidal: bool = False
    visited: bool = False


@dataclass
class Item:
    key: str
    name: str
    words: List[str]
    desc: str
    location: Optional[str]
    adjectives: List[str] = field(default_factory=list)
    article: str = "a"
    portable: bool = True
    scenery: bool = False
    initial: Optional[str] = None
    moved: bool = False
    container: bool = False
    openable: bool = False
    is_open: bool = False
    locked: bool = False
    readable: Optional[str] = None
    treasure: Optional[Tuple[int, int]] = None
    fixed_msg: Optional[str] = None
    lit: bool = False

    def full_name(self, definite: bool = False) -> str:
        if self.article == "":
            return self.name
        if definite:
            return "the " + self.name
        return self.article + " " + self.name


def build_rooms() -> Dict[str, Room]:
    rooms = [
        Room(
            "base", "Foot of the Lighthouse",
            "You stand inside the base of the Gannet Point light, a round room of "
            "whitewashed stone that smells of salt and old oil. An iron stair spirals "
            "upward. A heavy door stands open to the east, and wind comes through it "
            "carrying the sound of birds.",
            {"up": "quarters", "east": "cliff_path", "out": "cliff_path"},
        ),
        Room(
            "quarters", "Keeper's Quarters",
            "A cramped room curving with the tower wall. There is a narrow bunk, a cask "
            "of whale oil lashed to the wall, and a printed tide table pinned beside the "
            "door. Against the far wall squats a brass-bound salvage locker, the keeper's "
            "own, built to hold whatever the sea gives back. The stair continues up and "
            "down.",
            {"up": "lamp_room", "down": "base"},
        ),
        Room(
            "lamp_room", "Lamp Room",
            "The top of the tower. The great lamp sits in the center, cold, its lenses "
            "clouded with salt. A tide bell hangs from a bracket by the stair, its rope "
            "long rotted away. Windows look out on every side.",
            {"down": "quarters"},
        ),
        Room(
            "cliff_path", "Gannet Point",
            "A path of trodden turf on the headland. The lighthouse rises to the west. "
            "North, the path climbs toward a clamor of seabirds. South, a stair cut into "
            "the cliff face goes down toward the town.",
            {"west": "base", "in": "base", "north": "rookery", "south": "stair", "down": "stair"},
        ),
        Room(
            "rookery", "Gannet Rookery",
            "The headland ends in a shelf of guano-whitened rock crowded with nests. "
            "Hundreds of gannets wheel and scream overhead, and the ones on the ground "
            "watch you with flat, pale eyes.",
            {"south": "cliff_path"},
        ),
        Room(
            "stair", "Stair of Hooks",
            "A long stair cut into the cliff, worn to a dish in the middle of every step. "
            "Iron hooks are driven into the rock at intervals; the fishermen used to hang "
            "lanterns here to light the way home. There are no lanterns now. The stair "
            "climbs north to the point and descends south to the town.",
            {"north": "cliff_path", "up": "cliff_path", "south": "harbor_steps", "down": "harbor_steps"},
        ),
        Room(
            "harbor_steps", "Harbor Steps",
            "A broad landing of cracked flagstones at the top of the town, where the "
            "fishermen's wives once waited for the boats. A weathered signpost leans at "
            "the center. The cliff stair climbs north. A low stone building stands east, "
            "and a street runs south between shuttered houses.",
            {"north": "stair", "up": "stair", "east": "smokehouse", "south": "high_street"},
        ),
        Room(
            "smokehouse", "Smokehouse",
            "A windowless stone shed, black with eighty years of soot that still smells "
            "faintly of oak and fish. Rows of empty hooks hang from the rafters.",
            {"west": "harbor_steps", "out": "harbor_steps"},
        ),
        Room(
            "high_street", "High Street",
            "The main street of the High Town, cobbles slick with weed even up here. "
            "Shuttered shopfronts face each other: a chandler's to the east, a toymaker's "
            "to the west. The street runs north to the harbor steps and south to the sea "
            "wall.",
            {"north": "harbor_steps", "east": "chandlery", "west": "toymaker", "south": "sea_wall"},
        ),
        Room(
            "chandlery", "Mortlake's Chandlery",
            "Shelves of rotted canvas and rusted blocks line the walls of the ship's "
            "chandler's. Most of the stock is ruin, but iron lasts.",
            {"west": "high_street", "out": "high_street"},
        ),
        Room(
            "toymaker", "Toymaker's Shop",
            "Shelves climb to the ceiling, crowded with the dust-grey shapes of wooden "
            "boats, tin soldiers, and dolls with painted eyes. Something in the back "
            "ticks, very slowly, as it has been ticking for a long time.",
            {"east": "high_street", "out": "high_street"},
            dark=True,
        ),
        Room(
            "sea_wall", "The Sea Wall",
            "The High Street ends at a massive wall of fitted stone, built to hold back a "
            "sea that came over it anyway. An iron bollard is set into the parapet. A "
            "stone stair once led down from here, but the lower steps have fallen away, "
            "leaving a sheer drop of twelve feet to the stones below.",
            {"north": "high_street", "down": "harbor_square", "south": "harbor_square"},
        ),
        Room(
            "harbor_square", "Harbor Square",
            "The heart of the Low Town. Weed hangs from every lintel and the cobbles run "
            "with draining water. A fish market stands east, the harbormaster's office "
            "west, and the chapel's squat tower rises to the south. The sea wall looms to "
            "the north.",
            {"up": "sea_wall", "north": "sea_wall", "east": "fish_market",
             "west": "harbormaster", "south": "chapel"},
            tidal=True,
        ),
        Room(
            "fish_market", "Fish Market",
            "Stone tables where the catch was laid out, now furred with green. In the "
            "center is a deep tidal pool, fed by a drain, which never empties. East, the "
            "square gives way to open mud flats.",
            {"west": "harbor_square", "east": "mud_flats"},
            tidal=True,
        ),
        Room(
            "harbormaster", "Harbormaster's Office",
            "A small room with a water-stained desk and a chart of the harbor peeling "
            "from the wall. Set into the back wall is an iron safe with a numbered dial.",
            {"east": "harbor_square", "out": "harbor_square"},
            tidal=True,
        ),
        Room(
            "chapel", "Chapel of Saint Ormund",
            "The pews have floated and settled at odd angles. Light comes through a "
            "window of green glass that is now the exact color of the water. A choir "
            "loft overlooks the nave, empty. A memorial plaque is set into the wall by "
            "the altar, and a stair goes down behind it to the crypt.",
            {"north": "harbor_square", "out": "harbor_square", "down": "crypt"},
            tidal=True,
        ),
        Room(
            "crypt", "Crypt",
            "A low vault beneath the chapel, the ceiling furred with weed. Water drips. "
            "A single stone sarcophagus stands in the center, its lid carved with a man "
            "holding a lantern.",
            {"up": "chapel"},
            dark=True, tidal=True,
        ),
        Room(
            "mud_flats", "Mud Flats",
            "The harbor bottom, exposed: a glistening plain of mud and eelgrass that "
            "sucks at your boots. The wreck of a small ketch, the Merrow's Grace, lies "
            "canted on her side to the east, her deck almost level with the mud. West is "
            "the fish market.",
            {"west": "fish_market", "east": "wreck_deck"},
            tidal=True,
        ),
        Room(
            "wreck_deck", "Deck of the Merrow's Grace",
            "The deck tilts underfoot, slick with weed. The mast still stands, rigging "
            "long gone; it is the one thing in the Low Town that shows above the water "
            "at high tide. Aft, a low iron-bound door leads down into the captain's "
            "cabin. The mud flats lie west.",
            {"west": "mud_flats", "down": "cabin", "in": "cabin"},
        ),
        Room(
            "cabin", "Captain's Cabin",
            "A small cabin, dark and sloping, where the captain of the Merrow's Grace "
            "spent his last night above water. A chart table is bolted to the floor.",
            {"up": "wreck_deck", "out": "wreck_deck"},
            dark=True,
        ),
    ]
    return {r.key: r for r in rooms}


def build_items() -> Dict[str, Item]:
    items = [
        # Lighthouse
        Item("lantern", "brass lantern", ["lantern", "lamp"],
             "A squat brass whale-oil lantern with a wire handle and a glass chimney.",
             "base", adjectives=["brass", "whale-oil", "oil"],
             initial="A brass whale-oil lantern hangs from a hook by the door."),
        Item("rope", "coil of rope", ["rope", "coil", "line"],
             "Thirty feet of tarred hemp, stiff but sound.",
             "base", adjectives=["tarred", "hemp"],
             initial="A coil of tarred rope lies at the foot of the stair."),
        Item("locker", "salvage locker", ["locker", "chest", "trunk", "box"],
             "A brass-bound sea chest, heavy as an anchor, with the keeper's initials "
             "worn almost smooth on the lid.",
             "quarters", adjectives=["brass", "brass-bound", "salvage", "keeper's"],
             portable=False, scenery=True, container=True, openable=True,
             fixed_msg="It weighs as much as you do, and it belongs here."),
        Item("cask", "oil cask", ["cask", "barrel", "oil"],
             "A small cask of whale oil, lashed to the wall. A brass tap is set near the bottom.",
             "quarters", adjectives=["oil", "whale"],
             portable=False, scenery=True,
             fixed_msg="It's lashed to the wall, and it would take two men to lift anyway."),
        Item("bunk", "bunk", ["bunk", "bed", "cot", "mattress", "blankets"],
             "A narrow bunk with a straw mattress and blankets stiff with salt. The "
             "blankets are rumpled, as if someone slept badly here a long time ago.",
             "quarters", portable=False, scenery=True,
             fixed_msg="It's bolted to the wall."),
        Item("tide_table", "tide table", ["table", "card", "paper", "chart"],
             "A printed card, foxed with damp, pinned beside the door.",
             "quarters", adjectives=["tide", "printed"], scenery=True,
             readable="TIDE AT SALTMARROW.\n\nThe ebb runs four turns of the glass. The low "
                      "holds twenty-two. The flood runs six. The high holds eight.\n\nListen "
                      "for the bell: one for the ebb, two for the low, three for the flood, "
                      "four for the high.\n\nDo not be in the Low Town when it rings four."),
        Item("tin", "tin box", ["tin", "box"],
             "A small tin that once held tobacco. The lid is painted with a faded ship.",
             None, adjectives=["small", "tobacco"], container=True, openable=True,
             initial="A small tin box sits on the floor where you set it."),
        Item("medal", "keeper's medal", ["medal", "medallion"],
             "A silver medal on a faded ribbon, struck by the Lifeboat Society. The "
             "inscription reads: FOR THE NIGHT OF THE GREAT TIDE. HE RANG UNTIL THE END.",
             "tin", adjectives=["silver", "keeper's", "keepers"], treasure=(5, 15)),
        Item("great_lamp", "great lamp", ["lamp", "light", "beacon", "lenses", "lens"],
             "A lamp the size of a man, ringed with clouded lenses. There is no oil in "
             "its reservoir and no wick in its burner. It is waiting, you think, for "
             "something other than fire.",
             "lamp_room", adjectives=["great", "big", "huge"],
             portable=False, scenery=True, fixed_msg="It is the lighthouse."),
        Item("bell", "tide bell", ["bell", "clapper"],
             "A bronze bell green with verdigris, hung from an iron bracket. The rope "
             "rotted away long ago, but the clapper still swings freely.",
             "lamp_room", adjectives=["tide", "bronze"],
             portable=False, scenery=True, fixed_msg="It is bolted to the tower."),
        Item("windows", "windows", ["windows", "window", "view", "town", "saltmarrow"],
             "", "lamp_room", portable=False, scenery=True,
             fixed_msg="You can't take a view."),
        # Point and stair
        Item("gannets", "gannets", ["gannets", "gannet", "birds", "bird", "seabirds"],
             "", "rookery", article="the", portable=False, scenery=True,
             fixed_msg="They have beaks like marlinspikes and they know it."),
        Item("nest", "nest", ["nest", "nests"],
             "A heap of weed and fish bones. The gannets have been bringing things "
             "back to it for eighty years, and not all of them were fish.",
             "rookery", portable=False, scenery=True,
             fixed_msg="It falls apart in your hands."),
        Item("ring", "signet ring", ["ring", "signet"],
             "A heavy gold signet ring. The seal shows a lantern over three waves: the "
             "mark of the harbormasters of Saltmarrow.",
             "rookery", adjectives=["gold", "signet", "heavy"], treasure=(10, 25),
             initial="In the nearest nest, among the fish bones, something gold glints."),
        Item("hooks", "iron hooks", ["hooks", "hook"],
             "Rust-eaten hooks driven into the rock every ten steps, each one bearded "
             "with lichen.",
             "stair", article="the", portable=False, scenery=True,
             fixed_msg="They are driven deep into the rock."),
        # High Town
        Item("signpost", "signpost", ["signpost", "sign", "post"],
             "A weathered wooden signpost with three arms, and something scratched into the post below them.",
             "harbor_steps", portable=False, scenery=True,
             fixed_msg="It's set in the flagstones.",
             readable="GANNET POINT LIGHT: up the stair.\nSMOKEHOUSE: east.\nHIGH STREET and SEA "
                      "WALL: south.\n\nBelow the arms, scratched deep into the wood: THEY COME "
                      "BACK WITH THE WATER."),
        Item("cod", "salt cod", ["cod", "fish"],
             "A whole cod, split and salted and dried until it could be used as a roof "
             "slate. Eighty years have not improved it.",
             "smokehouse", adjectives=["salt", "dried", "stiff"],
             initial="A single salt cod, stiff as a plank, hangs from a hook."),
        Item("crowbar", "crowbar", ["crowbar", "bar", "lever"],
             "Three feet of iron, flattened and curved at one end. Rusted, but rust is "
             "only iron being patient.",
             "chandlery", adjectives=["iron"],
             initial="An iron crowbar leans in a corner."),
        Item("gaff", "gaff hook", ["gaff", "hook", "boathook", "pole"],
             "A long ash pole with a wicked iron hook at the end, for landing fish too "
             "big to argue with.",
             "chandlery", adjectives=["gaff", "long", "iron"],
             initial="A long-handled gaff hook lies across the counter."),
        Item("music_box", "music box", ["box", "musicbox"],
             "A small box of inlaid wood with a brass key in its side. The lid is "
             "painted with a lighthouse, its beam picked out in gold leaf.",
             "toymaker", adjectives=["music", "inlaid", "wooden", "small"], treasure=(10, 20),
             initial="On a low shelf, a small music box of inlaid wood sits in a circle of "
                     "clean, dustless shelf, as if someone has been keeping it for you."),
        Item("toys", "toys", ["toys", "toy", "boats", "soldiers", "dolls", "doll", "shelves"],
             "Wooden boats with their paint gone grey. Tin soldiers rusted at attention. "
             "Dolls whose painted eyes have run in the damp so that they seem to weep.",
             "toymaker", article="the", portable=False, scenery=True,
             fixed_msg="They come apart at a touch. Leave them."),
        Item("bollard", "iron bollard", ["bollard", "post", "ring", "parapet"],
             "A squat iron bollard, set deep in the stone of the parapet. Boats used to "
             "tie up here, when the water was this high on purpose.",
             "sea_wall", adjectives=["iron"], portable=False, scenery=True,
             fixed_msg="It's set in a ton of stone."),
        # Low Town
        Item("eel", "eel", ["eel", "creature", "monster", "thing"],
             "", "fish_market", article="the", portable=False, scenery=True,
             fixed_msg="You'd rather keep your fingers."),
        Item("pool", "tidal pool", ["pool", "water", "drain"],
             "", "fish_market", adjectives=["tidal", "deep"], portable=False, scenery=True,
             fixed_msg="It's a hole in the ground full of water."),
        Item("pearl", "black pearl", ["pearl"],
             "A pearl the size of a thumbnail, black as the water that made it, with a "
             "green light moving under its skin.",
             "fish_market", adjectives=["black", "large"], treasure=(10, 25),
             initial="At the bottom of the pool, something pale gleams."),
        Item("safe", "iron safe", ["safe", "strongbox"],
             "A squat iron safe, rusted at the seams but solid. A numbered dial is set "
             "in the door, marked 0 to 99.",
             "harbormaster", adjectives=["iron"], portable=False, scenery=True,
             container=True, openable=True, locked=True,
             fixed_msg="It is set into the wall."),
        Item("dial", "dial", ["dial", "combination", "knob"],
             "A brass dial marked 0 to 99. It turns with a dry click.",
             "harbormaster", adjectives=["numbered", "brass"], portable=False, scenery=True,
             fixed_msg="It's part of the safe."),
        Item("desk", "desk", ["desk", "chart"],
             "A desk of some dark wood, swollen and split. The chart on the wall above "
             "it shows the harbor as it was: soundings in fathoms, the channel marked in "
             "red, and the lighthouse drawn with a beam like a pointing finger.",
             "harbormaster", portable=False, scenery=True,
             fixed_msg="It's too swollen with water to move."),
        Item("logbook", "logbook", ["logbook", "ledger", "book", "journal", "entry"],
             "The harbormaster's logbook, its pages fused into a single wet brick, "
             "except for the last one.",
             "harbormaster", adjectives=["harbormaster's", "water-swollen", "wet"],
             initial="A water-swollen logbook lies open on the desk.",
             readable="Most of the pages have fused into pulp. Only the final entry can be "
                      "read, in a cramped and hurried hand:\n\n\"Changed the safe to the one "
                      "number none of us in Saltmarrow will ever forget. God help us if we "
                      "do. The water is at the door.\""),
        Item("astrolabe", "harbormaster's astrolabe", ["astrolabe", "instrument"],
             "A mariner's astrolabe of gilded bronze, engraved with the stars of the "
             "northern sky. It is as heavy as a conscience and far more beautiful.",
             "safe", adjectives=["gilded", "bronze", "harbormaster's"], treasure=(15, 30)),
        Item("brass_key", "brass key", ["key"],
             "A brass key, long and plain, on a loop of twine. A paper tag reads: GRACE, AFT.",
             "safe", adjectives=["brass", "long", "plain"]),
        Item("plaque", "memorial plaque", ["plaque", "memorial", "inscription"],
             "A plaque of green bronze, set into the wall by the altar, with raised lettering.",
             "chapel", adjectives=["memorial", "bronze"], portable=False, scenery=True,
             fixed_msg="It's fixed to the wall with bolts as thick as your thumb.",
             readable="HERE THE SEA TOOK TWENTY-THREE SOULS OF SALTMARROW\nAND THE TOWN WITH THEM.\n\n"
                      "THEY SING STILL."),
        Item("altar", "altar", ["altar", "pews", "pew", "loft", "window"],
             "A slab of plain stone. The pews lie heaped against it like driftwood, and "
             "above, the empty choir loft waits for a choir.",
             "chapel", portable=False, scenery=True,
             fixed_msg="It's a slab of stone the size of a boat."),
        Item("sarcophagus", "stone sarcophagus", ["sarcophagus", "coffin", "tomb", "lid"],
             "A sarcophagus of grey stone. The lid is carved with the effigy of a man "
             "holding a lantern aloft, and sealed with eighty years of salt. There is a "
             "narrow gap under the lid, just wide enough for a bar.",
             "crypt", adjectives=["stone", "grey", "carved"], portable=False, scenery=True,
             container=True, openable=True, locked=True,
             fixed_msg="It weighs more than the boat that brought you."),
        Item("reliquary", "silver reliquary", ["reliquary", "casket"],
             "A silver casket the size of a loaf, worked all over with waves and fish. "
             "Something inside shifts when you tilt it, with a sound like a small bell.",
             "sarcophagus", adjectives=["silver", "small"], treasure=(15, 30)),
        Item("wreck", "wreck", ["wreck", "ketch", "ship", "boat", "grace", "merrow's", "hull", "mast"],
             "", "mud_flats", article="the", portable=False, scenery=True,
             fixed_msg="She's forty tons of oak and iron."),
        Item("cabin_door", "iron-bound door", ["door", "hatch"],
             "", "wreck_deck", adjectives=["iron-bound", "cabin", "low", "iron"],
             portable=False, scenery=True, openable=True, locked=True,
             fixed_msg="It's hinged to the ship."),
        Item("log", "captain's log", ["log", "book", "journal"],
             "The log of the Merrow's Grace, bound in sharkskin that has kept the water "
             "out. The final page is the only one that matters.",
             "cabin", adjectives=["captain's", "captains", "sharkskin", "ship's"],
             article="the", treasure=(15, 30),
             initial="A book bound in sharkskin is wedged behind the chart table.",
             readable="The final page, in a steady hand:\n\n\"The light is out. The keeper "
                      "rings the bell and we steer for it, but we cannot find the harbor "
                      "mouth. Something in the water is singing. The men have stopped "
                      "rowing to listen. God forgive me, so have I.\""),
        Item("spyglass", "brass spyglass", ["spyglass", "telescope", "glass"],
             "A brass spyglass, three draws, the lenses miraculously whole.",
             "cabin", adjectives=["brass"],
             initial="A brass spyglass has rolled into the corner."),
        Item("chart_table", "chart table", ["table", "charts"],
             "A table bolted to the deck, its charts long since dissolved into a grey "
             "film. Someone has scratched a line into the wood with a knife, over and "
             "over, pointing aft.",
             "cabin", adjectives=["chart"], portable=False, scenery=True,
             fixed_msg="It's bolted down."),
        # Global scenery, present everywhere
        Item("sea", "sea", ["sea", "ocean", "water", "tide", "waves"],
             "", "*", article="the", portable=False, scenery=True,
             fixed_msg="The sea takes. It doesn't give itself to be taken."),
        Item("ground", "ground", ["ground", "floor", "cobbles", "stones", "flagstones", "mud", "weed", "seaweed"],
             "Wet. Everything in Saltmarrow is wet, or was, or will be.",
             "*", article="the", portable=False, scenery=True,
             fixed_msg="You can't take the ground. It's taken enough."),
        Item("self", "yourself", ["me", "myself", "self", "salvager", "hands"],
             "A salvager: cold, damp, and determined. Your hands are steady enough.",
             "*", article="", portable=False, scenery=True,
             fixed_msg="You already have yourself, more or less."),
    ]
    return {it.key: it for it in items}


def build_world():
    return build_rooms(), build_items()

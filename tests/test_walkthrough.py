"""End-to-end tests: a full winning walkthrough plus the ways to die."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from saltmarrow.game import Game, MAX_SCORE  # noqa: E402
from saltmarrow.parser import parse  # noqa: E402


class Transcript:
    def __init__(self):
        self.lines = []

    def __call__(self, text):
        self.lines.append(text)

    @property
    def text(self):
        return "\n".join(self.lines)


def run(commands, seed=1):
    out = Transcript()
    game = Game(seed=seed, out=out)
    game.intro()
    for c in commands:
        out.lines.append("> " + c)
        game.do(c)
    return game, out


WALKTHROUGH = [
    # Lighthouse
    "take lantern", "take rope", "up", "search bunk", "open tin", "take medal",
    "open locker", "put medal in locker", "read tide table", "down",
    # Headland and High Town
    "east", "south", "south", "east", "take cod", "west", "north", "north", "north",
    "give cod to gannets", "take ring", "south", "south", "south", "south",
    "east", "take crowbar", "take gaff", "west", "light lantern", "west",
    "take music box", "east", "south", "tie rope to bollard", "extinguish lantern",
    # Wait out the high tide
    "wait for tide", "wait for tide", "wait for tide",
    # Low Town in one trip
    "light lantern", "down", "south", "down", "pry sarcophagus with crowbar",
    "take reliquary", "up", "north", "west", "read logbook", "turn dial to 23",
    "open safe", "take astrolabe", "take key", "east", "east",
    "kill eel with gaff", "take pearl", "east", "board wreck",
    "unlock door with key", "down", "take log", "up", "west", "west", "west", "up",
    # Home
    "extinguish lantern", "north", "north", "north", "north", "west", "up",
    "put all in locker",
]


class WalkthroughTest(unittest.TestCase):
    def test_full_game_is_winnable(self):
        game, out = run(WALKTHROUGH)
        self.assertTrue(game.won, out.text)
        self.assertEqual(game.score, MAX_SCORE, out.text)
        self.assertFalse(game.dead)
        self.assertNotIn("You can't go that way", out.text)
        self.assertNotIn("I don't know the word", out.text)
        self.assertNotIn("You don't see any", out.text)

    def test_score_is_capped_by_treasure_math(self):
        game, _ = run([])
        from saltmarrow.game import TREASURES, BONUSES
        total = sum(game.item(k).treasure[0] + game.item(k).treasure[1] for k in TREASURES)
        total += sum(BONUSES.values())
        self.assertEqual(total, MAX_SCORE)


class TideTest(unittest.TestCase):
    def test_low_town_is_closed_at_high_tide(self):
        game, out = run(["take rope", "east", "south", "south", "south", "south",
                         "tie rope to bollard", "down"])
        self.assertEqual(game.location, "sea_wall")
        self.assertIn("wait", out.text.lower())

    def test_drowning_in_the_low_town(self):
        game, out = run(["take rope", "east", "south", "south", "south", "south",
                         "tie rope to bollard", "wait for tide", "wait for tide", "down",
                         "wait for tide", "wait for tide"])
        self.assertTrue(game.dead, out.text)
        self.assertIn("drowned", out.text)

    def test_wreck_is_a_refuge(self):
        game, out = run(["take rope", "east", "south", "south", "south", "south",
                         "tie rope to bollard", "wait for tide", "wait for tide", "down",
                         "east", "east", "east", "wait for tide", "wait for tide", "west"])
        self.assertFalse(game.dead, out.text)
        self.assertEqual(game.location, "wreck_deck")
        self.assertIn("nothing west of the rail but black water", out.text)


class DarknessTest(unittest.TestCase):
    def test_dark_room_hides_items(self):
        game, out = run(["east", "south", "south", "south", "west", "take box"])
        self.assertIn("pitch dark", out.text)
        self.assertEqual(game.item("music_box").location, "toymaker")

    def test_lantern_reveals_dark_room(self):
        game, out = run(["take lantern", "east", "south", "south", "south", "west",
                         "light lantern", "take box"])
        self.assertEqual(game.item("music_box").location, "player")

    def test_choir_eventually_takes_you(self):
        deaths = 0
        for seed in range(20):
            game, out = run(["east", "south", "south", "south", "west", "east", "west", "east",
                             "west", "east", "west", "east"], seed=seed)
            if game.dead:
                deaths += 1
                self.assertIn("joined the choir", out.text)
        self.assertGreater(deaths, 10)


class PuzzleTest(unittest.TestCase):
    def test_gannets_guard_ring(self):
        game, out = run(["east", "north", "take ring"])
        self.assertEqual(game.item("ring").location, "rookery")
        self.assertIn("gannets", out.text)

    def test_wrong_combination(self):
        game, out = run(["take rope", "east", "south", "south", "south", "south",
                         "tie rope to bollard", "wait for tide", "wait for tide", "down",
                         "west", "turn dial to 17", "open safe", "set dial to twenty three",
                         "open safe"])
        self.assertIn("Nothing else happens", out.text)
        self.assertTrue(game.item("safe").is_open, out.text)

    def test_eel_bites(self):
        game, out = run(["take rope", "east", "south", "south", "south", "south",
                         "tie rope to bollard", "wait for tide", "wait for tide", "down",
                         "east", "take pearl"])
        self.assertEqual(game.item("pearl").location, "fish_market")


class ParserTest(unittest.TestCase):
    def test_two_object_command(self):
        c = parse("put the brass key in the locker")
        self.assertEqual((c.verb, c.noun, c.prep, c.noun2), ("put", ["brass", "key"], "in", ["locker"]))

    def test_phrasal_verbs(self):
        self.assertEqual(parse("pick up lantern").noun, ["lantern"])
        self.assertEqual(parse("turn on lantern").verb, "light")
        self.assertEqual(parse("turn lantern off").verb, "extinguish")
        self.assertEqual(parse("look at bell").verb, "examine")
        self.assertEqual(parse("climb down rope").direction, "down")

    def test_numbers(self):
        self.assertEqual(parse("turn dial to 23").number, 23)
        self.assertEqual(parse("set dial to twenty-three").number, 23)
        self.assertEqual(parse("dial 7").number, 7)

    def test_direction_shortcuts(self):
        self.assertEqual(parse("n").direction, "north")
        self.assertEqual(parse("go west").direction, "west")


class SaveRestoreTest(unittest.TestCase):
    def test_round_trip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.sav")
            game, out = run(["take lantern", "light lantern", "up", "search bunk", "save " + path])
            self.assertIn("Saved", out.text)
            game2, out2 = run(["restore " + path])
            self.assertEqual(game2.location, "quarters")
            self.assertEqual(game2.turns, game.turns)
            self.assertTrue(game2.item("lantern").lit)
            self.assertEqual(game2.item("tin").location, "quarters")


if __name__ == "__main__":
    unittest.main()

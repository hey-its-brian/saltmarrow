# SALTMARROW

An interactive salvage. A text adventure in the Infocom tradition, written in
plain Python with no dependencies.

Eighty years ago the sea took the fishing town of Saltmarrow in a single
night. Twice a day the tide gives the Low Town back for a little while, and
twice a day it takes it again. You are a salvager with a whale-oil lantern, a
coil of rope, and a keeper's locker to fill before the bell rings four.

## Running it

```bash
python3 -m saltmarrow
```

Python 3.8 or newer. Nothing to install.

## Playing

Talk to the game in short imperative sentences:

```
> take lantern
> light it
> put medal in locker
> unlock door with key
> turn dial to 17
> give cod to gannets
```

Directions are `north`, `south`, `east`, `west`, `up`, `down`, `in`, `out`
(or `n`, `s`, `e`, `w`, `u`, `d`). `look`, `examine`, `read`, `search`,
`inventory`, `score`, `save`, `restore`, `wait`, `wait for tide`, `tide`,
`verbose`, `brief`, `again`, and `help` all work.

## What makes it tick

- **The tide.** A forty-turn cycle: low (22 turns), flooding (6), high (8),
  ebbing (4). The Low Town is only reachable at low tide and during the
  flood. The lighthouse bell rings at every turning: once for the ebb, twice
  for low, three times for the flood, four for high. If you are in a tidal
  street when it rings four, you drown. The wreck's deck stands above high
  water and can be used as a refuge.
- **The lantern.** Burns 120 turns of oil per fill. The cask in the keeper's
  quarters holds two refills. Three rooms are dark. Moving in the dark
  without light has a coin-flip chance of ending badly; the Hollow Choir is
  always listening.
- **Seven treasures.** Each scores points when taken and more when laid in
  the salvage locker. Puzzle bonuses on top. Maximum score 350, ranked from
  Beachcomber to Keeper of the Light.
- **Save and restore** write a small JSON file in the working directory.

## Map

```
                 Gannet Rookery
                       |
   Lamp Room           |
       |               |
   Keeper's Qtrs       |
       |               |
   Foot of Light --- Gannet Point
                       |
                  Stair of Hooks
                       |
                  Harbor Steps ---- Smokehouse
                       |
   Toymaker's ---- High Street ---- Chandlery
                       |
                   The Sea Wall
                       :  (rope, low tide only)
   Harbormaster --- Harbor Square --- Fish Market --- Mud Flats --- Wreck Deck
                       |                                                |
                     Chapel                                       Captain's Cabin
                       |
                     Crypt
```

Everything below the Sea Wall floods. The wreck deck and cabin do not.

## Project layout

```
saltmarrow/
  world.py     rooms, items, and all the descriptive text
  parser.py    the two-object command parser
  game.py      the engine: turns, tide, light, puzzles, scoring, save/restore
  __main__.py  the read-eval-print loop
tests/
  test_walkthrough.py   a full winning walkthrough plus tide, darkness,
                        puzzle, parser, and save/restore tests
```

Run the tests with:

```bash
python3 -m unittest discover -s tests
```

## Spoilers

A complete winning command list lives in `tests/test_walkthrough.py` as
`WALKTHROUGH`. Read it only if the choir has taken you one time too many.

"""Run SALTMARROW from the command line: python3 -m saltmarrow"""

import sys

from .game import Game


def main() -> int:
    game = Game()
    game.intro()
    while not game.over:
        try:
            line = input("\n> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        game.do(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

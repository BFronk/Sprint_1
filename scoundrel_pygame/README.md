# Scoundrel — Pygame Edition

A polished, from-scratch desktop implementation of the original 2011 solo card
game by Zach Gage and Kurt Bieg. It uses procedural artwork, so there are no
external art or font files to manage.

## Run it

```bash
cd scoundrel_pygame
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Python 3.10+ is recommended. The dependency is `pygame-ce`; importing it still
uses `import pygame`.

## Controls

- Mouse: hover and click cards or buttons
- `1`–`4`: choose a card
- `W`: use the equipped weapon in combat
- `B`: fight barehanded
- `R`: avoid the room (when legal)
- `H` or `?`: rules overlay
- `N`: begin a fresh shuffled run
- `Esc`: close an overlay, or return to the title screen

## Base rules included

- Correct 44-card dungeon (red aces and red face cards removed)
- 20 starting/max health
- Clubs and spades as monsters, with J/Q/K/A worth 11/12/13/14
- Diamonds as binding weapons
- Weapon damage reduction and descending kill restriction
- Hearts as potions, with only the first potion per room healing
- Four-card rooms; face three and carry the fourth forward
- Room avoidance, but never twice in succession
- Mandatory short final chamber
- Original win and loss scoring, including the full-health final-potion bonus

## Tests

The rules engine does not depend on Pygame:

```bash
python -m unittest discover -s tests -v
```

## Project layout

- `main.py` — Pygame presentation, input, animation, and screens
- `scoundrel/engine.py` — deterministic, testable card-game rules
- `tests/test_engine.py` — rules regression tests

This is an independent fan implementation. Scoundrel was designed by Zach Gage
and Kurt Bieg; no original game assets are included.

# Scoundrel V3 — Roguelike Prototype

A polished, from-scratch desktop implementation of the original 2011 solo card
game by Zach Gage and Kurt Bieg. It uses procedural artwork, so there are no
external art or font files to manage.

V3 preserves Classic and Marathon while adding a focused 40-room roguelike mode
where the dungeon evolves and the player chooses a counter-build.

## Run it

```bash
cd scoundrel_pygame_v3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Python 3.10+ is recommended. The dependency is `pygame-ce`; importing it still
uses `import pygame`.

## Controls

- Mouse: hover and click cards or buttons
- Title screen: Arrow keys or `A`/`D` select a mode; `Enter` or `Space` starts it
- Title screen shortcuts: `C` Classic, `R` Roguelike, `M` Marathon, or `1`–`3`
- `1`–`4`: choose a card
- `W`: use the equipped weapon in combat
- `B`: fight barehanded
- `R`: avoid the room (when legal)
- `H` or `?`: rules overlay
- `S`: settings overlay
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

## V2 modes

- **Classic ×1:** the original single 44-card dungeon.
- **Marathon ×2:** clear the complete first dungeon, including its short final
  chamber, then immediately enter a newly shuffled 44-card dungeon. Health,
  equipped weapon, and that weapon's kill history carry forward. Clear all 88
  cards to win.

Marathon loss scoring includes every monster you have not yet faced. If you
fall in dungeon one, the remaining first-dungeon monsters and the full 208
monster-value points of dungeon two are subtracted. The results screen records
the run as `0 / 2`, `1 / 2`, or `2 / 2` dungeons cleared.

The right-side equipment panel is intentionally text-free. The diamond weapon
sits at the bottom of a physical-style cascade of monsters it has killed. Each
new victim is placed on top; equipping a replacement weapon clears the old
weapon and its stack, exactly as the base rules require.

Every dungeon is exactly one unique 44-card deck. Matching ranks in Clubs and
Spades are different cards, and a room you avoid can appear again after cycling
through the dungeon, but no exact suit/rank card is duplicated.

Forced barehand fights resolve immediately by default when no equipped weapon
can legally attack. Enable **Confirm forced barehand fights** in Settings to see
the combat confirmation instead. The preference persists in `settings.json`.

**Allow equal-rank weapon kills** controls the weapon-chain comparison. On is
the official rule: the next monster may be less than or equal to the previous
victim. Off is the strict-descending solitaire-style variant: every subsequent
weapon kill must have a lower rank. This preference also persists and applies
to the next run. The selected weapon-chain rule is locked as soon as a run
starts and cannot be changed until that run ends or is abandoned at the title
screen.

Action feedback is rendered as unboxed floating text beneath the room. Healing
and damage values rise slightly and fade, with a fixed upper bound that keeps
them out of the cards.

## V3 Roguelike ×40

- Face 40 rooms to win; avoided rooms do not advance the counter.
- Start with the true base-game state: 20 health and no stat bonuses. Rooms 1–8
  use pure Scoundrel rules.
- After rooms 8, 16, 24, and 32, the dungeon gains one unique permanent threat:
  Spades gain Fury, Clubs gain weapon-resistant Armor, barehanded combat gains
  Bloodlust, or potions suffer Drought. All four appear by the final depth.
- At the same checkpoint, choose one of three free permanent boons. The choices
  improve weapon power, potion healing, damage guard, maximum health, or provide
  an immediate heal. There is no currency or shop bookkeeping.
- Each checkpoint forces a paired decision: see exactly how the dungeon changed,
  then choose one counter from a limited offer. A boon cannot be skipped.
- When one complete 44-card deck is exhausted, its short chamber must still be
  cleared before a newly shuffled deck begins. Health, equipment, boons, and
  upgrades carry through the full run.
- Red, blue, green, and pale-blue UI values consistently mean enemy damage,
  weapon power, potion healing, and damage guard. **Run Info** lists every active
  threat and boon, while combat confirmation displays the full calculation.
- Roguelike score rewards room progress first, then defeated monsters and
  surviving health.

## Tests

The rules engine does not depend on Pygame:

```bash
python -m unittest discover -s tests -v
```

## Project layout

- `main.py` — Pygame presentation, input, animation, and screens
- `scoundrel/engine.py` — deterministic, testable card-game rules
- `tests/test_engine.py` — rules regression tests
- `scoundrel/settings.py` — persistent JSON preference handling
- `settings.json` — saved player preferences

This is an independent fan implementation. Scoundrel was designed by Zach Gage
and Kurt Bieg; no original game assets are included.

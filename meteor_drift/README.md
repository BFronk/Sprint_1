# Meteor Drift: Voidling Invasion

A self-contained arcade shooter built with Pygame. Dodge meteors, battle Galaga-style Voidlings, collect power-ups, and skim past danger for valuable near-miss bonuses.

## Run it

From this folder:

```bash
python3 -m pip install -r requirements.txt
python3 game.py
```

Or, on macOS, double-click `run_game.command`. The launcher creates a private virtual environment and installs Pygame there if it is missing.

## Controls

- Move: WASD or arrow keys
- Fire: hold Space
- Pause/resume: P
- Start/restart: Enter
- Quit: Escape

## Challenge modes

Choose with **1**, **2**, or **3** on the title or game-over screen:

- **Cruise:** slower enemies, fewer shots, standard scoring
- **Arcade:** the intended balance with a 1.25× score multiplier
- **Onslaught:** much faster spawns, movement, and enemy fire with a 1.75× score multiplier

Waves now advance every 180 points and accelerate more quickly. Later waves contain a higher proportion of Voidlings, which enter formation, fire aimed plasma, and eventually dive toward you.

## Power-ups

- **R — Rapid Fire:** shoot faster for 8 seconds
- **3 — Triple Shot:** adds two angled shots for 9 seconds
- **S — Energy Shield:** absorbs one hit and lasts up to 12 seconds
- **+ — Repair:** restores one life, up to a maximum of five

Destroying Voidlings has a better power-up drop chance than destroying meteors. Timed effects can stack.

## Near misses

Let a meteor, diving Voidling, or enemy plasma bolt pass just outside your collision radius. A gold **NEAR MISS** graphic appears and awards roughly 45–80 base points—the closer the pass, the larger the bonus. Challenge-mode score multipliers also apply.

Only direct collisions and enemy plasma hits cost a life. Letting a hazard leave the screen does not hurt you.

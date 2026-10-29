# Meteor Drift V2

V2 preserves the complete arcade game from Meteor Drift V1 and adds a five-mission campaign. V1 remains separate and unchanged in `../meteor_drift/meteor_driftV1.py`.

## Start the game on macOS

Double-click `run_game.command`, or run:

```bash
cd "/Users/bridger/Documents/Codex/2026-08-01/build-me-a-working-gar-with/outputs/meteor_drift_v2"
./run_game.command
```

The launcher reuses the working Pygame environment from V1 when available. Otherwise, it creates a private environment for V2 and installs the dependency.

## Choose a game

- Press **A** for Arcade, choose Cruise/Arcade/Onslaught with **1**, **2**, or **3**, then press Enter.
- Press **C** for Campaign, then press Enter.

## Campaign

The adventure contains five missions with briefings and checkpoints:

1. **First Contact:** earn 500 points.
2. **The Shattered Belt:** survive 35 seconds in an asteroid-heavy sector.
3. **Hunter's Nest:** destroy 12 Voidlings.
4. **The Razor Run:** score four near misses.
5. **Last Stand at Orion:** survive a 50-second onslaught.

Your score, near misses, and remaining lives carry forward. Completing a mission awards an increasing score bonus, and each checkpoint restores one life up to the five-life maximum.

## Controls

- Move: WASD or arrow keys
- Fire: hold Space
- Pause: P
- Restart: press R twice within 0.75 seconds
- Confirm/start: Enter
- Quit: Escape

The first R press displays a red confirmation graphic. Press R again before it disappears to restart the current arcade run or the entire campaign. This prevents accidental restarts.

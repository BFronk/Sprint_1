# Meteor Drift V3

V3 is a separate game. V1 and V2 remain unchanged. It keeps the endless arcade modes and expands the adventure into a persistent 15-mission campaign.

## Start the game on macOS

Double-click `run_game.command`, or run:

```bash
cd "/Users/bridger/Documents/Codex/2026-08-01/build-me-a-working-gar-with/outputs/meteor_drift_v3"
./run_game.command
```

## Game selection

- Press **A** for endless Arcade, select difficulty with **1**, **2**, or **3**, then press Enter.
- Press **C** for Campaign, then press Enter to resume the latest autosave.
- With Campaign selected, press **N** to deliberately start a new campaign.

## Campaign structure

The campaign contains 15 missions across five sectors. Objectives include:

- Earn a target score
- Survive a timed assault
- Destroy a number of enemy craft
- Hunt fast Dartwings
- Break armored Bulwarks
- Perform dangerous near misses

A protected checkpoint is secured after missions 3, 6, 9, and 12. Checkpoints fully repair the ship. If the player is defeated or uses double-R restart, the campaign returns to the latest checkpoint rather than mission 1.

The final two sectors repeat the same speed profile as missions 7–9 instead of accelerating from cumulative score. Their objectives are longer—more targets, points, near misses, or survival time—so the challenge comes from consistent play rather than unavoidable reaction speed.

## Enemies

- **Voidling:** the original formation fighter; strafes, aims, fires, and dives.
- **Dartwing:** a fragile, fast interceptor with wide zigzags and an early dive.
- **Bulwark:** a slow armored enemy that always takes five hits, fires heavy plasma, and awards a larger score reward. Surviving Bulwarks loop back to the top for another attack pass without recovering health.
- **Asteroid:** the original rotating environmental hazard remains in every sector.

Arcade mode gradually introduces Dartwings and Bulwarks at higher waves. Campaign missions specify their own enemy mix.

## JSON saving

V3 creates `save_data.json` beside `game.py`. It stores:

- High score
- Latest completed mission
- Latest protected checkpoint
- Score, lives, near misses, and enemy-kill totals
- Campaign-completion status

The save is written atomically through a temporary file, reducing the chance of corruption if the program closes during a write. If a malformed save is encountered, the game safely falls back to a new save instead of crashing.

Closing and reopening resumes the mission after the most recently completed mission. Losing all lives falls back to the last three-mission checkpoint.

## Controls

- Move: WASD or arrow keys
- Fire: hold Space
- Pause: P
- Restart from the latest checkpoint: press R twice within 0.75 seconds
- Confirm/start: Enter
- Quit and save: Escape

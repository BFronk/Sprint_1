#!/bin/zsh
set -e
cd "${0:A:h}"

game_python=".venv/bin/python3"
if [[ ! -x "$game_python" ]] && [[ -x "../meteor_drift/.venv/bin/python3" ]]; then
  game_python="../meteor_drift/.venv/bin/python3"
fi
if [[ ! -x "$game_python" ]] && [[ -x "../meteor_drift_v2/.venv/bin/python3" ]]; then
  game_python="../meteor_drift_v2/.venv/bin/python3"
fi
if [[ ! -x "$game_python" ]]; then
  python3 -m venv .venv
  game_python=".venv/bin/python3"
fi
if ! "$game_python" -c 'import pygame' 2>/dev/null; then
  "$game_python" -m pip install -r requirements.txt
fi
exec "$game_python" game.py

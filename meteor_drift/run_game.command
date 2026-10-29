#!/bin/zsh
set -e
cd "${0:A:h}"
if [[ ! -x .venv/bin/python3 ]]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python3 -c 'import pygame' 2>/dev/null; then
  .venv/bin/python3 -m pip install -r requirements.txt
fi
exec .venv/bin/python3 game.py

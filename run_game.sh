#!/usr/bin/env bash
# Skulls & Stuff - start the game on Mac or Linux (run install.sh once first).
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
    echo "The game isn't set up yet: run install.sh (or install.command on a Mac) first."
    read -r -p "Press Enter to close." _
    exit 1
fi
if ! .venv/bin/python game/main.py "$@"; then
    echo
    echo "The game closed with an error. If it says \"No module named pygame\", run install.sh again."
    read -r -p "Press Enter to close." _
fi

#!/usr/bin/env bash
# Skulls & Stuff - start the game on a Raspberry Pi (run install_pi.sh once first).
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
    echo "The game isn't set up yet: run   bash install_pi.sh   first."
    read -r -p "Press Enter to close." _
    exit 1
fi
if ! .venv/bin/python game/main.py "$@" 2> last_error.txt; then
    # started from the desktop icon there's no window to show the error in, so keep it in a file
    if [ -t 1 ]; then
        cat last_error.txt
        echo
        echo "The game closed with an error (saved in last_error.txt)."
        read -r -p "Press Enter to close." _
    fi
fi

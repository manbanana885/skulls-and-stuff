#!/usr/bin/env bash
# Skulls & Stuff - one-time setup for Mac and Linux.
# Makes a private Python environment in this folder (.venv) and installs the game's libraries into it.
cd "$(dirname "$0")" || exit 1
echo
echo " Skulls & Stuff - one-time setup"
echo " ==============================="
echo

PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PY="$c"
        break
    fi
done

if [ -z "$PY" ]; then
    echo " Python 3.10 or newer was not found."
    if [ "$(uname)" = "Darwin" ]; then
        echo " Get it from https://www.python.org/downloads/ (the macOS installer), then run this again."
        open "https://www.python.org/downloads/" 2>/dev/null
    else
        echo " Install it with your package manager, for example:"
        echo "   Ubuntu / Debian / Mint:  sudo apt install python3 python3-venv"
        echo "   Fedora:                  sudo dnf install python3"
        echo "   Arch / SteamOS:          sudo pacman -S python"
        echo " then run this again."
    fi
    echo
    read -r -p " Press Enter to close." _
    exit 1
fi

echo " Found $("$PY" --version)"
if [ ! -x .venv/bin/python ]; then
    echo " Making the game's Python environment (.venv)..."
    if ! "$PY" -m venv .venv; then
        echo
        echo " Couldn't make it. On Ubuntu / Debian:  sudo apt install python3-venv   then run this again."
        read -r -p " Press Enter to close." _
        exit 1
    fi
fi
echo " Installing the game's libraries (pygame-ce, numpy)..."
echo
if ! .venv/bin/python -m pip install --upgrade pip pygame-ce numpy; then
    echo
    echo " Something went wrong installing the libraries - see the messages above."
    read -r -p " Press Enter to close." _
    exit 1
fi
echo
echo " All done! Start the game with run_game.sh (or run_game.command on a Mac)."
echo
read -r -p " Press Enter to close." _

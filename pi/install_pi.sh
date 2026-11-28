#!/usr/bin/env bash
# Skulls & Stuff - one-time setup for a Raspberry Pi 4 / 5 (Raspberry Pi OS, 64-bit recommended).
# Makes a private Python environment in this folder (.venv), installs the game's libraries into it,
# and puts a Skulls & Stuff shortcut on the desktop and in the applications menu.
cd "$(dirname "$0")" || exit 1
HERE="$(pwd)"
echo
echo " Skulls & Stuff - Raspberry Pi setup"
echo " ==================================="
echo

PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PY="$c"
        break
    fi
done
if [ -z "$PY" ]; then
    echo " This needs Python 3.10 or newer, and this Raspberry Pi OS is too old to have it."
    echo " Install the current Raspberry Pi OS (64-bit) with Raspberry Pi Imager, then run this again."
    echo
    read -r -p " Press Enter to close." _
    exit 1
fi
echo " Found $("$PY" --version) on $(uname -m)"

MEM_MB=$(awk '/MemTotal/ {print int($2 / 1024)}' /proc/meminfo 2>/dev/null)
if [ -n "$MEM_MB" ] && [ "$MEM_MB" -lt 1800 ]; then
    echo
    echo " Warning: this Pi has ${MEM_MB} MB of memory. The game needs about 1 GB on its own, so close"
    echo " everything else (especially the web browser) before playing."
fi

if [ ! -x .venv/bin/python ]; then
    echo " Making the game's Python environment (.venv)..."
    if ! "$PY" -m venv .venv; then
        echo
        echo " Couldn't make it. Run:   sudo apt install python3-venv   then run this again."
        read -r -p " Press Enter to close." _
        exit 1
    fi
fi

echo " Installing the game's libraries (pygame-ce, numpy). This can take a few minutes on a Pi..."
echo
if ! .venv/bin/python -m pip install --upgrade pip pygame-ce numpy; then
    echo
    echo " Installing the libraries failed. If the messages above mention SDL or a compiler, install"
    echo " the build tools and run this again:"
    echo "   sudo apt install python3-dev libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libfreetype6-dev"
    read -r -p " Press Enter to close." _
    exit 1
fi

chmod +x run_pi.sh 2>/dev/null
SHORTCUT="[Desktop Entry]
Type=Application
Name=Skulls & Stuff
Comment=Isometric twin-stick shooter
Exec=\"$HERE/run_pi.sh\"
Path=$HERE
Icon=$HERE/icon.png
Terminal=false
Categories=Game;"
mkdir -p "$HOME/.local/share/applications"
printf '%s\n' "$SHORTCUT" > "$HOME/.local/share/applications/skulls-and-stuff.desktop"
if [ -d "$HOME/Desktop" ]; then
    printf '%s\n' "$SHORTCUT" > "$HOME/Desktop/skulls-and-stuff.desktop"
    chmod +x "$HOME/Desktop/skulls-and-stuff.desktop"
    gio set "$HOME/Desktop/skulls-and-stuff.desktop" metadata::trusted true 2>/dev/null
fi

echo
echo " All done! Start the game from the Skulls & Stuff icon on the desktop, from the"
echo " applications menu (Games), or by running:   bash run_pi.sh"
echo
read -r -p " Press Enter to close." _

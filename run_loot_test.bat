@echo off
rem Test build: starts the game as usual, but Mythical / Demonic / Eldritch / Sacred gear drops all the time.
cd /d "%~dp0"
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
    echo Python was not found. Double-click install.bat first.
    pause
    exit /b 1
)
%PY% game\main.py --rare-loot

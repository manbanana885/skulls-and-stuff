@echo off
setlocal
cd /d "%~dp0"
title Skulls ^& Stuff - setup
echo.
echo  Skulls ^& Stuff - one-time setup
echo  ===============================
echo.

rem Find Python: the "py" launcher first, then "python".
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"

if not defined PY (
    echo  Python is not installed. Installing it now with winget...
    echo  ^(Windows may ask for permission - click Yes.^)
    echo.
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo  Automatic install did not work. Opening the Python download page...
        echo  Download Python, run the installer, and TICK "Add python.exe to PATH".
        echo  Then double-click install.bat again.
        start "" https://www.python.org/downloads/
        echo.
        pause
        exit /b 1
    )
    echo.
    echo  Python is installed. Close this window and double-click install.bat again
    echo  to finish setup.
    echo.
    pause
    exit /b 0
)

echo  Found Python:
%PY% --version
echo.
echo  Installing the game's libraries ^(pygame-ce, numpy^)...
echo.
%PY% -m pip install --upgrade pygame-ce numpy
if errorlevel 1 (
    echo.
    echo  Something went wrong installing the libraries - see the messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo  All done! Double-click run_game.bat to play.
echo.
pause

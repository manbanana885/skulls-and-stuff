@echo off
setlocal
cd /d "%~dp0"
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
    echo Python was not found. Double-click install.bat first.
    pause
    exit /b 1
)
%PY% game\main.py
if errorlevel 1 (
    echo.
    echo The game closed with an error. If it says "No module named pygame",
    echo double-click install.bat first.
    pause
)

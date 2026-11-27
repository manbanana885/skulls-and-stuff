@echo off
cd /d %~dp0
python tools\make_sfx.py
python tools\make_soundtrack.py


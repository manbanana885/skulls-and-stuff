@echo off
cd /d %~dp0
"D:\SteamLibrary\steamapps\common\Blender\blender.exe" -b -P blender\build_assets.py -- %*


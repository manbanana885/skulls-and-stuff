"""Split expansion assets into render batches -> blender/_batches.txt (one batch per line)."""
import re
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(ROOT, "blender", "expansion.py")
src = open(p, encoding="utf-8").read()
src = src.replace('(creature(_spec), 8, {"walk": 4}, (240, 240), 1.6)', '(creature(_spec), 8, {"walk": 4}, (256, 300), 1.9)')
open(p, "w", encoding="utf-8").write(src)

tiles = re.findall(r'^    "((?:floor|wall)_\w+)": style_', src, re.M)
props = re.findall(r'"(\w+)": \(p_', src)
en = re.search(r"ENEMY_SPECS = \{(.*?)\n\}", src, re.S).group(1)
enemies = re.findall(r'^    "(\w+)": dict', en, re.M)
bo = re.search(r"BOSS_SPECS = \{(.*?)\n\}", src, re.S).group(1)
bosses = ["boss_" + b for b in re.findall(r'^    "(\w+)": dict', bo, re.M)]
print(len(tiles), "tiles", len(props), "props", len(enemies), "enemies", len(bosses), "bosses")
batches = [tiles[:24], tiles[24:], props + enemies[:6], enemies[6:15], enemies[15:],
           bosses[:6], bosses[6:12], bosses[12:18], bosses[18:]]
open(os.path.join(ROOT, "blender", "_batches.txt"), "w").write("\n".join(" ".join(b) for b in batches))
for i, b in enumerate(batches):
    print(i, len(b), b[0], "...")

"""Make a contact sheet of rendered sprites:  python tools/contact_sheet.py out.png [asset ...]"""
import os
import sys
import glob
import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPR = os.path.join(ROOT, "assets", "sprites")

out = sys.argv[1]
names = sys.argv[2:] or sorted(d for d in os.listdir(SPR) if os.path.isdir(os.path.join(SPR, d)))
pygame.init()
rows = []
for n in names:
    files = sorted(glob.glob(os.path.join(SPR, n, "*.png")))[:24]
    rows.append([pygame.image.load(f) for f in files])
cell = max((im.get_width() for r in rows for im in r), default=64)
cols = max((len(r) for r in rows), default=1)
sheet = pygame.Surface((cols * cell, len(rows) * cell))
sheet.fill((40, 44, 52))
for y, r in enumerate(rows):
    for x, im in enumerate(r):
        sheet.blit(im, (x * cell + (cell - im.get_width()) // 2, y * cell + (cell - im.get_height()) // 2))
pygame.image.save(sheet, out)
print("saved", out, sheet.get_size())

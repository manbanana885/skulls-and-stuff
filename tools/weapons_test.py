"""Targeted test of the nuke / saw / chem / cryo weapons. python tools/weapons_test.py <outdir>"""
import os
import sys
import math
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SKULLS_SAVE"] = os.devnull        # never touch the player's save.json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import weapons as WP  # noqa: E402
from world import Proj, Enemy  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(3)
g = main.Game(windowed=True)


class Bot:
    move = (0.0, 0.0)
    aim = None
    fire = False
    pressed = set()
    device_name = None

    def poll(self, ps):
        pass


bot = Bot()
g.input = bot
main.biome_for = lambda d, s: "castle"


def fresh():
    g.new_world(3)
    g.state = "play"
    g.banner = ("", 0)
    w = g.world
    w.bosses = []
    w.enemies = []
    return w, w.player, w.level


# ---- nukes: terrain radius, self damage, radiation zone
for arch, want in (("tac_nuke", 3.0), ("nuke", 5.0)):
    w, p, L = fresh()
    wp = WP.generate(3, arch=arch, rarity=0)
    st = wp.st
    # detonate against a wall at a known spot
    cx, cy = None, None
    for x in range(2, L.W - 2):
        for y in range(2, L.H - 2):
            if L.solid[L.i(x, y)] == 0 and L.solid[L.i(x + 1, y)] == 1:
                cx, cy = x + 0.5, y + 0.5
                break
        if cx:
            break
    inside = [(x, y) for x in range(L.W) for y in range(L.H) if L.solid[L.i(x, y)] == 1 and 1 <= x < L.W - 1 and 1 <= y < L.H - 1
              and math.hypot(x + 0.5 - cx, y + 0.5 - cy) < want]
    p.x, p.y = cx - 1.5, cy
    e = Enemy("zombie", cx - 0.5, cy + 0.5, awake=True, depth=3)
    e.hp = 10 ** 6
    w.enemies.append(e)
    rad = (st["rad"][0], st["rad"][1], st["rad"][2], st["rad"][3])
    b = Proj("nuke", cx, cy, 1.2, 0, 0, st["dmg"], blast=st["blast"], rad=rad)
    hp0 = p.hp
    w.impact(b, cx, cy)
    left = sum(1 for (x, y) in inside if L.solid[L.i(x, y)] == 1)
    hp_after_blast = p.hp
    ehp = e.hp
    p.invuln = 0
    for f in range(120):
        p.hp = max(p.hp, 50)
        p.alive = True
        w.update(1 / 60, bot)
    print("%-8s walls within %.0f tiles: %d -> %d left  |  player %d -> %d from blast  |  radiation dmg to enemy over 2s: %.0f  |  zone r=%.0f %.0fs" % (
        arch, want, len(inside), left, hp0, hp_after_blast, ehp - e.hp, rad[0], rad[1]))
    g.draw()
    pygame.image.save(g.screen, os.path.join(out, arch + ".png"))

# ---- saw: bounces and self-hits
w, p, L = fresh()
wp = WP.generate(3, arch="saw", rarity=0)
p.weapons[0] = wp
bounces = []
for k in range(8):
    p.aim = (math.cos(k), math.sin(k))
    wp.cd = 0
    wp.ammo = 6
    w.fire_weapon(p, wp)
    bounces.append(w.projs[-1].bounce)
hits = 0
hp_track = p.hp
for f in range(60 * 5):
    p.invuln = 0
    before = p.hp
    w.update(1 / 60, bot)
    if p.hp < before:
        hits += 1
    p.hp = 100
    if f == 20:
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "saw.png"))
print("saw      bounce counts rolled: %s  |  times the saws hit the player in 5s: %d" % (bounces, hits))

# ---- chem: gas clouds damage monsters and the player
w, p, L = fresh()
wp = WP.generate(3, arch="chem", rarity=0)
p.weapons[0] = wp
targets = [Enemy("zombie", p.x + math.cos(a) * 3, p.y + math.sin(a) * 3, awake=False, depth=3) for a in (0, 1.5, 3, 4.5)]
for t_ in targets:
    t_.hp = 1000
w.enemies.extend(targets)
bot.fire = True
bot.aim = (40, 0)
for f in range(120):
    p.hp = 100
    g.update(1 / 60)
bot.fire = False
gas = [hz for hz in w.hazards if hz[4] == "gas"]
dmg0 = sum(1000 - t_.hp for t_ in targets)
if gas:
    p.x, p.y = gas[0][0], gas[0][1]
p.hp = 100
for f in range(60):
    w.update(1 / 60, bot)
g.draw()
pygame.image.save(g.screen, os.path.join(out, "chem.png"))
print("chem     gas clouds: %d  |  player hp after 1s standing in gas: %d  |  monster dmg: %.0f" % (len(gas), p.hp, sum(1000 - t_.hp for t_ in targets)))

# ---- cryo: chill -> freeze -> thaw
w, p, L = fresh()
wp = WP.generate(3, arch="cryo", rarity=0)
p.weapons[0] = wp
z = Enemy("zombie", p.x + 2.0, p.y, awake=True, depth=3)
z.hp = 1000
z.speed = 0
w.enemies.append(z)
bot.fire = True
froze_at = None
for f in range(60 * 4):
    dx, dy = z.x - p.x, z.y - p.y
    bot.aim = ((dy - dx) * 32, (dx + dy) * 16)
    p.hp = 100
    g.update(1 / 60)
    if z.frozen > 0 and froze_at is None:
        froze_at = f / 60
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "cryo.png"))
        break
bot.fire = False
thaw = 0
while z.frozen > 0 and thaw < 600:
    w.update(1 / 60, bot)
    thaw += 1
print("cryo     froze after %.1fs of spraying, thawed %.1fs later" % (froze_at or -1, thaw / 60))
print("DONE")

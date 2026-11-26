"""Exercise every boss attack in every phase, and tour all biomes with their enemies.
python tools/expansion_test.py <outdir>"""
import os
import sys
import math
import time
import random
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import weapons as WP  # noqa: E402
import bestiary as BE  # noqa: E402
from biomes import BIOMES  # noqa: E402
from world import Enemy  # noqa: E402
from bosses import Boss, ATTACKS  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(7)
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
errors = 0

# ---- 1) every boss, every phase, every attack
main.biome_for = lambda d, s: "facility"
g.new_world(3)
g.state = "play"
w = g.world
p = w.player
used = {}
for kind in BE.BOSSES:
    try:
        w.bosses = []
        w.projs = []
        w.enemies = []
        b = Boss(kind, p.x + 4, p.y, 3)
        b.awake = True
        w.bosses.append(b)
        for ph in range(3):
            b.hp = b.maxhp * (0.9 - ph * 0.33)
            b.phase = ph
            b.queue = []
            b.gen = None
            for name, kw in BE.BOSSES[kind]["phases"][ph]:
                gen = ATTACKS[name](b, w, **kw)
                for _ in range(400):
                    try:
                        next(gen)
                    except StopIteration:
                        break
                    w.update(1 / 60, bot)
                    p.hp = p.max_hp
                    p.alive = True
                used.setdefault(kind, set()).add(name)
    except Exception:
        errors += 1
        print("BOSS ERROR", kind)
        traceback.print_exc()
print("bosses exercised:", len(used), "min distinct attacks per boss:", min(len(v) for v in used.values()))

# ---- 2) biome tour
for biome in BIOMES:
    try:
        main.biome_for = lambda d, s, b=biome: b
        g.new_world(3)
        g.state = "play"
        g.banner = ("", 0)
        w = g.world
        p = w.player
        L = w.level
        p.weapons[0] = WP.generate(6, arch=random.choice(["assault", "plasma", "shotgun", "rocket"]), rarity=3)
        sig = BIOMES[biome]["signature"]
        for i, k in enumerate(sig * 3):
            a = random.random() * math.tau
            x, y = p.x + math.cos(a) * 3.5, p.y + math.sin(a) * 3.5
            if not L.is_solid(int(x), int(y)):
                w.enemies.append(Enemy(k, x, y, awake=True, depth=3))
        t0 = time.perf_counter()
        boss = w.bosses[0] if w.bosses else None
        for f in range(60 * 8):
            if f == 150 and boss:   # teleport next to the boss to start the fight
                for ox, oy in ((4, 0), (-4, 0), (0, 4), (0, -4), (3, 3), (-3, -3)):
                    x, y = boss.x + ox, boss.y + oy
                    if not L.is_solid(int(x), int(y)):
                        p.x, p.y = x + 0.5 - (x % 1), y + 0.5 - (y % 1)
                        break
            tgt = boss if (boss and boss.alive and boss.awake) else min(w.enemies, key=lambda e: math.hypot(e.x - p.x, e.y - p.y), default=None)
            if tgt:
                dx, dy = tgt.x - p.x, tgt.y - p.y
                bot.aim = ((dy - dx) * 32, (dx + dy) * 16)
                bot.fire = math.hypot(dx, dy) < 10
            bot.move = (math.cos(f / 40) * 0.5, math.sin(f / 33) * 0.5)
            p.hp = p.max_hp
            p.alive = True
            g.update(1 / 60)
            g.draw()
            if f in (200, 420):
                pygame.image.save(g.screen, os.path.join(out, "%s_%d.png" % (biome, f)))
        dt = time.perf_counter() - t0
        print("%-11s fps %3.0f  boss %-14s hp %5s  enemies %2d  hostile projs %3d" % (
            biome, 480 / dt, boss.kind if boss else "-", ("%d" % boss.hp) if boss else "-", len(w.enemies),
            sum(1 for q in w.projs if q.hostile)))
    except Exception:
        errors += 1
        print("BIOME ERROR", biome)
        traceback.print_exc()
print("ERRORS", errors)

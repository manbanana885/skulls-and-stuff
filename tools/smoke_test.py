"""Headless smoke test: every biome, new enemies, explosives breaching walls, flamethrower. Saves screenshots.
python tools/smoke_test.py <outdir>"""
import os
import sys
import math
import time
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import weapons as WP  # noqa: E402
from world import Enemy  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(4)
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
archs = ["rocket", "flamer", "grenade", "shotgun", "laser_rifle", "plasma", "sniper"]
kinds = ["hellspawn", "wretch", "stalker", "mimic", "zombie", "brute", "spitter"]
plan = [(2, "facility"), (4, "ossuary"), (4, "otherworld"), (4, "outpost"), (5, "hell")]
for depth, biome in plan:
    main.biome_for = lambda d, s, b=biome: b
    g.new_world(depth)
    g.state = "play"
    w = g.world
    L = w.level
    walls_before = sum(1 for v in L.solid if v == 1)
    t_upd = t_draw = 0.0
    frames = 0
    worst = 0.0
    self_hits = 0
    for f in range(60 * 14):
        t = f / 60
        p = w.player
        if f % 120 == 0:
            arch = archs[(f // 120) % len(archs)]
            p.weapons[p.cur] = WP.generate(depth, arch=arch, rarity=random.randint(0, 3))
            for i in range(3):
                k = kinds[(f // 120 * 3 + i) % len(kinds)]
                ang = random.random() * math.tau
                x, y = p.x + math.cos(ang) * 4, p.y + math.sin(ang) * 4
                if not L.is_solid(int(x), int(y)):
                    w.enemies.append(Enemy(k, x, y, awake=k != "mimic", depth=depth))
        bot.move = (math.cos(t * 0.5) * 0.3, math.sin(t * 0.37) * 0.3)
        near = min((e for e in w.enemies if e.state != "dormant"), key=lambda e: math.hypot(e.x - p.x, e.y - p.y), default=None)
        if p.weapon.arch in ("rocket", "grenade") and (f // 30) % 2:
            bot.aim = (math.cos(t), math.sin(t))          # sweep explosives into walls
            bot.fire = True
        elif near:
            dx, dy = near.x - p.x, near.y - p.y
            bot.aim = ((dy - dx) * 32, (dx + dy) * 16)
            bot.fire = math.hypot(dx, dy) < 9
        else:
            bot.fire = False
        hp0 = p.hp
        if p.hp < 30:
            p.hp = p.max_hp
        p.alive = True
        f0 = time.perf_counter()
        g.update(1 / 60)
        f1 = time.perf_counter()
        g.draw()
        f2 = time.perf_counter()
        t_upd += f1 - f0
        t_draw += f2 - f1
        worst = max(worst, f2 - f0)
        frames += 1
        if f % 120 == 100:
            pygame.image.save(g.screen, os.path.join(out, "%s_%s.png" % (biome, p.weapon.arch)))
    print("%-10s fps %.0f (update %.1fms draw %.1fms) worst %.0fms  walls destroyed %d  kills %d  alive %d  hazards %d" % (
        biome, frames / (t_upd + t_draw), t_upd / frames * 1000, t_draw / frames * 1000, worst * 1000,
        walls_before - sum(1 for v in L.solid if v == 1), w.kills, len(w.enemies), len(w.hazards)))
print("OK")

"""Headless trap test: every biome places its traps; every trap mechanic damages players and monsters; screenshots.
python tools/traps_test.py <outdir>"""
import os
import sys
import math
import random
import time
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import traps as TR  # noqa: E402
from world import Enemy  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(11)
g = main.Game(windowed=True)


class Bot:
    move = (0.0, 0.0)
    aim = (1.0, 0.0)
    fire = False
    pressed = set()
    pending = set()
    device_name = None
    keyboard = True
    mouse_mode = False
    dev = None

    def poll(self, ps):
        pass


bot = Bot()
g.inputs = [bot]
g.spare = {}
errors = 0
hurt_by = {}      # mech -> (player dmg seen, monster dmg seen)
for biome in TR.BIOME_TRAPS:
    main.biome_for = lambda d, s, b=biome: b
    try:
        g.new_world(5)
    except Exception:
        traceback.print_exc()
        errors += 1
        continue
    g.state = "play"
    w = g.world
    p = w.player
    mechs = sorted({(t.mech, t.style) for t in w.traps})
    counts = {}
    for t in w.traps:
        counts[t.mech] = counts.get(t.mech, 0) + 1
    fr = 0
    t0 = time.perf_counter()
    # visit one trap of each kind, park the player on it and drop a monster next to it
    seen = []
    for mech, style in mechs:
        tr = next(t for t in w.traps if t.mech == mech and t.style == style)
        if mech == "strike":
            spot = (p.x, p.y)
        elif mech == "pool":
            c = next(iter(tr.cells))
            spot = (c[0] + 0.5, c[1] + 0.5)
        elif mech == "wind":
            spot = (tr.x, tr.y)
        elif mech in ("reactor", "tesla"):
            spot = (tr.x + 1.0, tr.y)
        elif mech == "laser":
            spot = (tr.x, tr.y)
        elif mech == "tentacle":
            spot = (tr.x + 1.5, tr.y)
        else:
            spot = (tr.x, tr.y)
        p.x, p.y = spot
        p.hp = p.max_hp
        p.alive = True
        w.enemies = [e for e in w.enemies if math.hypot(e.x - p.x, e.y - p.y) > 8]
        pdmg = 0.0
        edmg = 0.0
        if mech == "reactor":
            tr.hit(w, 100)
        # phase A: player alone on the trap
        for f in range(60 * 5):
            hp0 = p.hp
            if mech not in ("strike", "wind", "turret"):
                p.x, p.y = spot
            p.invuln = min(p.invuln, 0.05)
            try:
                g.update(1 / 60)
                if f % 6 == 0:
                    g.draw()
            except Exception:
                traceback.print_exc()
                errors += 1
                break
            pdmg += max(0.0, hp0 - p.hp)
            if p.hp < 40 or not p.alive:
                p.alive = True
                p.hp = p.max_hp
            if f == 140:
                pygame.image.save(g.screen, os.path.join(out, "trap_%s_%s_%s.png" % (biome, mech, style)))
            fr += 1
        # phase B: a (harmless, immortal) monster on the trap, player 2.4 tiles away to keep triggers awake
        if mech == "reactor":
            tr = next((t for t in w.traps if t.mech == mech and t.alive), tr)
            tr.hit(w, 100)
        mpos = (tr.x - 1.0, tr.y) if mech in ("reactor", "tesla") else ((spot) if mech in ("pool", "strike") else (tr.x, tr.y))
        if mech == "tentacle":
            mpos = (tr.x + 1.5, tr.y)
        mon = Enemy("zombie", mpos[0], mpos[1], awake=True, depth=5)
        mon.hp = 100000
        w.enemies.append(mon)
        for f in range(60 * 5):
            ehp0 = mon.hp
            mon.x, mon.y = mpos
            mon.vx = mon.vy = 0
            mon.lunge = 0
            p.alive = True
            p.hp = p.max_hp
            if mech == "strike":
                p.x, p.y = mpos[0] + 2.4, mpos[1]
                tr.pending = [[mpos[0], mpos[1], s_[2]] for s_ in tr.pending]
            elif mech not in ("wind",):
                p.x, p.y = tr.x + 2.4, tr.y
                if w.level.is_solid(int(p.x), int(p.y)):
                    p.x, p.y = tr.x - 2.4, tr.y
            try:
                g.update(1 / 60)
            except Exception:
                traceback.print_exc()
                errors += 1
                break
            edmg += max(0.0, ehp0 - mon.hp)
        w.enemies = [e for e in w.enemies if e is not mon]
        key = "%s/%s" % (mech, style)
        a, b = hurt_by.get(key, (0, 0))
        hurt_by[key] = (a + pdmg, b + edmg)
        seen.append("%s/%s p%.0f m%.0f" % (mech, style, pdmg, edmg))
    dt = time.perf_counter() - t0
    print("%-10s traps %-58s fps %.0f" % (biome, " ".join("%s:%d" % kv for kv in sorted(counts.items())), fr / max(dt, 1e-6)))
    print("            " + "  |  ".join(seen))
print()
bad = [k for k, (a, b) in hurt_by.items() if a <= 0 and not k.startswith("wind")]
badm = [k for k, (a, b) in hurt_by.items() if b <= 0 and not k.startswith(("wind", "turret", "pool/mud"))]
print("no player damage:", bad)
print("no monster damage:", badm)
print("ERRORS", errors)

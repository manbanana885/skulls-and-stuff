"""Explosive barrels: each kind detonates with its own effect, hurting monsters and players.
python tools/barrels_test.py <outdir>"""
import os
import sys
import random
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
from world import Enemy, BARREL_WEIGHTS  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(2)
g = main.Game(windowed=True)
g.save_settings = lambda: None


class Bot:
    move = (0.0, 0.0)
    aim = None
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
fails = []


def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fails.append(what)


# placement: barrels become one of the four kinds, weighted by biome
counts = {}
for biome in ("facility", "nuclear", "chemical", "hell"):
    main.biome_for = lambda d, s, b=biome: b
    c = {}
    for d in range(1, 9):
        g.new_world(d)
        for k in g.world.barrel_kind.values():
            c[k] = c.get(k, 0) + 1
        assert all(g.world.level.props[p].startswith("barrel_") or g.world.level.props[p] in ("raddrum", "chemdrum") for p in g.world.barrel_kind)
    counts[biome] = c
    print("  %-9s barrels over 8 sectors: %s" % (biome, c))
check(all(set(c) <= {"fire", "chem", "rad", "shrap"} and c for c in counts.values()), "every barrel is one of the four kinds")
check(counts["nuclear"].get("rad", 0) >= max(counts["nuclear"].values()) and counts["hell"].get("fire", 0) >= max(counts["hell"].values()),
      "biomes favour their own barrel (rad in nuclear, fire in hell)")

main.biome_for = lambda d, s: "facility"
for kind in ("fire", "chem", "rad", "shrap"):
    try:
        g.new_world(2)
        g.state = "play"
        g.banner = ("", 0)
        w = g.world
        w.traps, w.enemies, w.spawners, w.bosses, w.loot, w.shootables = [], [], [], [], [], []
        L = w.level
        p = w.player
        cx, cy = int(L.start[0]), int(L.start[1])
        for x in range(cx - 7, cx + 8):
            for y in range(cy - 7, cy + 8):
                L.solid[L.i(x, y)] = 0
        L.props = {}
        w.barrels, w.barrel_kind = {}, {}
        L.exit = (-50.0, -50.0)
        g.floor_layer.chunks.clear()
        pos = (cx + 3, cy)
        L.props[pos] = "barrel_" + kind
        L.solid[L.i(*pos)] = 2
        w.barrels[pos] = 3
        w.barrel_kind[pos] = kind
        p.x, p.y = cx + 2.1, cy + 0.5
        p.hp = p.max_hp = 1000
        p.invuln = 0
        e = Enemy("zombie", cx + 4.6, cy + 0.5, awake=True, depth=1)
        e.hp = 1e6
        w.enemies = [e]
        g.update(1 / 60)
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "barrel_%s_before.png" % kind))
        w.damage_barrel(pos, 99)
        lost = 0.0
        for f in range(240):
            e.x, e.y, e.vx, e.vy = cx + 4.6, cy + 0.5, 0, 0
            p.x, p.y = cx + 2.1, cy + 0.5
            hp0 = p.hp
            p.invuln = 0
            g.update(1 / 60)
            lost += max(0.0, hp0 - p.hp)
            if f == 12:
                g.draw()
                pygame.image.save(g.screen, os.path.join(out, "barrel_%s_boom.png" % kind))
            if f == 120:
                g.draw()
                pygame.image.save(g.screen, os.path.join(out, "barrel_%s_after.png" % kind))
        lost = 1000 - p.hp
        lingering = sorted({hz[4] for hz in w.hazards})
        print("  %-6s barrel: monster took %.0f, player lost %.0f, still on the ground after 4s: %s" % (kind, 1e6 - e.hp, lost, lingering))
        check(1e6 - e.hp > 0 and lost > 0 and pos not in L.props and L.solid[L.i(*pos)] == 0,
              "%s barrel detonates, hurting monsters and players" % kind)
    except Exception:
        traceback.print_exc()
        fails.append(kind + " crashed")
# the nuclear / chemical sectors' own drums are explosive too
main.biome_for = lambda d, s: "nuclear"
g.new_world(3)
drums = [pos for pos, nm in g.world.level.props.items() if nm == "raddrum"]
check(drums and all(g.world.barrel_kind.get(pos) == "rad" for pos in drums), "rad drums in the nuclear sector are explosive (%d)" % len(drums))
if drums:
    w = g.world
    w.damage_barrel(drums[0], 99)
    check(drums[0] not in w.level.props and any(hz[4] == "rad" for hz in w.hazards), "and they go off with fallout when shot")

# reactors: a 12-tile blast that flattens terrain, warns for 4.5s
import traps as TR  # noqa: E402
main.biome_for = lambda d, s: "facility"
g.new_world(3)
g.state = "play"
g.banner = ("", 0)
w = g.world
w.traps, w.enemies, w.spawners, w.bosses, w.loot = [], [], [], [], []
L = w.level
p = w.player
cx, cy = int(L.start[0]), int(L.start[1])
L.exit = (-50.0, -50.0)
rx, ry = cx + 0.5, cy + 0.5
re = TR.Reactor("chem", rx, ry)
L.solid[L.i(cx, cy)] = 2
w.traps = [re]
walls_before = sum(1 for x in range(cx - 13, cx + 14) for y in range(cy - 13, cy + 14)
                   if 1 <= x < L.W - 1 and 1 <= y < L.H - 1 and L.solid[L.i(x, y)] == 1 and ((x + 0.5 - rx) ** 2 + (y + 0.5 - ry) ** 2) < 11.5 ** 2)
mons = []
for d in (3, 6, 9, 11, 14):
    e = Enemy("zombie", rx + d, ry, awake=True, depth=3)
    e.hp = 120
    e._d = d
    mons.append(e)
w.enemies = list(mons)
p.hp = p.max_hp = 1000
re.hit(w, 50)
check(abs(re.fuse - TR.REACTOR_FUSE) < 1e-6 and any(abs(wn[2] - TR.REACTOR_RADIUS) < 1e-6 for wn in w.warnings),
      "a critical reactor warns for %.1fs with a %d-tile ring" % (TR.REACTOR_FUSE, TR.REACTOR_RADIUS))
far = (rx - 6, ry)
for f in range(int(60 * (TR.REACTOR_FUSE + 0.5))):
    p.x, p.y = far
    for e in mons:
        if e.alive:
            e.x, e.y, e.vx, e.vy = rx + e._d, ry, 0, 0
    g.update(1 / 60)
    if f == int(60 * TR.REACTOR_FUSE) + 3:
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "reactor_boom.png"))
    if f == int(60 * 3):
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "reactor_warning.png"))
walls_after = sum(1 for x in range(cx - 13, cx + 14) for y in range(cy - 13, cy + 14)
                  if 1 <= x < L.W - 1 and 1 <= y < L.H - 1 and L.solid[L.i(x, y)] == 1 and ((x + 0.5 - rx) ** 2 + (y + 0.5 - ry) ** 2) < 11.5 ** 2)
dead = [e._d for e in mons if not e.alive]
print("  reactor: (inner) walls within 11.5 tiles %d -> %d, monsters killed at distances %s (of 3/6/9/11/14), player 6 tiles away lost %.0f"
      % (walls_before, walls_after, dead, 1000 - p.hp))
check(walls_after == 0 and dead == [3, 6, 9, 11] and 1000 - p.hp > 20, "reactors flatten a 12-tile radius and wreck everything in it")
g.draw()
pygame.image.save(g.screen, os.path.join(out, "reactor_crater.png"))
print()
print("FAILED:", fails if fails else "none")

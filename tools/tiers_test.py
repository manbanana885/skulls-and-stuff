"""Void and Chaos weapon tiers. python tools/tiers_test.py [outdir]"""
import os
import sys
import math
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SKULLS_SAVE"] = os.devnull        # never touch the player's save.json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
os.chdir(ROOT)
import pygame  # noqa: E402
import main  # noqa: E402
import world as W  # noqa: E402
import weapons as WP  # noqa: E402
import support as SU  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")
os.makedirs(out, exist_ok=True)
random.seed(4)
W.rnd.seed(4)
fails = []


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)


# ---- rolls
rr = random.Random(1)
n = 600000
tiers = [WP.roll_rarity(rr, 5) for _ in range(n)]
c = {t: tiers.count(t) for t in (WP.SACRED, WP.VOID, WP.CHAOS)}
print("  depth 5: sacred 1 in %d, void 1 in %d, chaos 1 in %d" % tuple(n // max(1, c[t]) for t in (WP.SACRED, WP.VOID, WP.CHAOS)))
check(0 < c[WP.VOID] < c[WP.SACRED] and 0 < c[WP.CHAOS] < c[WP.SACRED] and 0.6 < c[WP.CHAOS] / c[WP.VOID] < 1.8,
      "void is the rarest tier, chaos about as rare")
archs = {WP.generate(5, random.Random(i), rarity=WP.VOID).arch for i in range(300)}
check(archs == set(WP.VOID_ARCHS), "void guns are only revolvers, grenade launchers and tactical nukes (%s)" % sorted(archs))
check(WP.Weapon("smg", WP.VOID, 1, 2).rarity == WP.SACRED, "a fixed archetype that can't hold the void comes out sacred")
pulls = [WP.Weapon("revolver", WP.VOID, 1, i).st["void"] for i in range(200)]
check(4.0 <= min(pulls) and max(pulls) <= 6.0 and max(pulls) - min(pulls) > 1.5, "void pull radius rolls 4-6 tiles per gun")
ratios = []
for a in WP.VOID_ARCHS:
    for i in range(40):
        ratios.append(WP.Weapon(a, WP.VOID, 1, i).dps() / WP.Weapon(a, 0, 1, i).dps())
ratios.sort()
print("  void vs common damage: median x%.2f" % ratios[len(ratios) // 2])
check(2.5 < ratios[len(ratios) // 2] < 4.0, "void guns hit roughly 3x their ordinary counterparts")
WP.RARE_ONLY = True
loot = {WP.roll_rarity(random.Random(i), 2) for i in range(300)}
mods_ = {SU.generate(3, random.Random(i)).rarity for i in range(300)}
WP.RARE_ONLY = False
check({WP.VOID, WP.CHAOS} <= loot, "the loot test mode rolls void and chaos too")
check(max(mods_) <= WP.SACRED, "modules never come out void or chaos")
cw = WP.Weapon("smg", WP.CHAOS, 1, 9)
seq = [cw.next_chaos_type() for _ in range(200)]
check(all(a != b for a, b in zip(seq, seq[1:])) and len(set(seq)) == len(WP.CHAOS_TYPES),
      "chaos never repeats a damage type twice running, and uses all %d" % len(WP.CHAOS_TYPES))
import time  # noqa: E402
c0 = cw.color
time.sleep(0.15)
check(cw.color != c0, "chaos colour keeps changing (%s -> %s)" % (c0, cw.color))

# ---- in a live world
g = main.Game(windowed=True)


class Bot:
    move = (0.0, 0.0)
    aim = (10, 5)
    fire = False
    pressed = set()
    device_name = None

    def poll(self, ps):
        pass


g.input = Bot()


def setup(depth=4):
    main.biome_for = lambda d, s: "facility"
    g.new_world(depth)
    g.state = "play"
    g.banner = ("", 0)
    w = g.world
    w.enemies, w.bosses = [], []
    return w, w.player


def open_spot(w, p, dist):
    L = w.level
    for a in [i * 0.3 for i in range(21)]:
        x, y = p.x + math.cos(a) * dist, p.y + math.sin(a) * dist
        if all(not L.is_solid(int(x + ox), int(y + oy)) for ox in (-1.5, 0, 1.5) for oy in (-1.5, 0, 1.5)) \
                and L.line_of_sight(p.x, p.y, x, y):
            return x, y
    return None


for arch in WP.VOID_ARCHS:
    best = None
    for tries in range(12):
        w, p = setup()
        spot = open_spot(w, p, 6.0)
        if spot:
            break
    hx, hy = spot
    pack = []
    for k in range(6):
        a = k * math.tau / 6
        e = W.Enemy("zombie", hx + math.cos(a) * 3.0, hy + math.sin(a) * 3.0, awake=True, depth=4)
        e.hp = e.maxhp = 5000
        e.speed = 0.0
        pack.append(e)
    w.enemies = list(pack)
    wp = WP.Weapon(arch, WP.VOID, 4, 11)
    pr = W.Proj("bullet", hx, hy, 0.5, 0, 0, wp.st["dmg"], life=0.5)
    pr.void = max(wp.st["void"], 4.5)
    pr.kind = {"revolver": "bullet", "grenade": "grenade", "tac_nuke": "nuke"}[arch]
    pr.blast = wp.st["blast"]
    pr.rad = wp.st["rad"]
    w.open_void(pr, hx, hy)
    d0 = sum(math.hypot(e.x - hx, e.y - hy) for e in pack) / len(pack)
    shot = None
    for f in range(int(60 * 1.2)):
        g.update(1 / 60)
        p.hp, p.alive = p.max_hp, True
        if f == 45 and shot is None:
            g.draw()
            shot = os.path.join(out, "void_%s.png" % arch)
            pygame.image.save(g.screen, shot)
    d1 = sum(math.hypot(e.x - hx, e.y - hy) for e in pack) / len(pack)
    alive_void = bool(w.voids)
    for f in range(60 * 2):
        g.update(1 / 60)
        p.hp, p.alive = p.max_hp, True
    dmg = sum(5000 - max(e.hp, 0) for e in pack)
    check(d1 < d0 * 0.6 and alive_void and not w.voids and dmg > 0,
          "void %s: hole pulled the pack from %.1f to %.1f tiles, then collapsed and exploded (%.0f damage)" % (arch, d0, d1, dmg))

# void rounds fired for real open holes where they land
w, p = setup()
spot = open_spot(w, p, 5.0)
e = W.Enemy("zombie", spot[0], spot[1], awake=True, depth=4)
e.hp = e.maxhp = 5000
e.speed = 0
w.enemies = [e]
wp = WP.Weapon("revolver", WP.VOID, 4, 3)
dx, dy = e.x - p.x, e.y - p.y
p.aim = (dx / math.hypot(dx, dy), dy / math.hypot(dx, dy))
w.fire_weapon(p, wp)
opened = False
for f in range(60):
    g.update(1 / 60)
    p.hp = p.max_hp
    opened = opened or bool(w.voids)
check(opened, "a fired void revolver round opens a black hole where it hits")

# chaos: consecutive shots carry different damage types
w, p = setup()
wp = WP.Weapon("assault", WP.CHAOS, 4, 5)
types = []
for i in range(12):
    n0 = len(w.projs)
    w.fire_weapon(p, wp)
    new = w.projs[n0:]
    types.append(new[0].dtype if new else None)
base = wp.st["dtype"]
check(all(t and a != b for t, a, b in zip(types, types, types[1:])) and wp.st["dtype"] == base,
      "chaos shots: %s (gun's own stats untouched)" % ", ".join(types[:7]))

# cards and auras draw for both tiers
for rar in (WP.VOID, WP.CHAOS):
    w, p = setup()
    gun = WP.generate(4, random.Random(rar), rarity=rar)
    p.weapons[p.cur] = gun
    w.loot.append(W.Loot("weapon", p.x + 1, p.y, WP.generate(4, random.Random(rar + 1), rarity=rar)))
    for f in range(20):
        g.update(1 / 60)
    g.draw()
    g.weapon_card(g.screen, gun, 40, 40)
    pygame.image.save(g.screen, os.path.join(out, "tier_%s.png" % WP.RARITY[rar][0].replace(" ", "_")))
check(True, "void and chaos cards, auras and pickups draw")

print()
print("ALL PASSED" if not fails else "%d FAILED" % len(fails))
sys.exit(1 if fails else 0)

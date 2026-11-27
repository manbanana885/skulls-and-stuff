"""Damage types vs enemy categories, measured in the running game.
python tools/damage_test.py <outdir>"""
import os
import sys
import math
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import weapons as WP  # noqa: E402
import damage as DM  # noqa: E402
from world import Enemy, Loot  # noqa: E402
from bosses import Boss  # noqa: E402
from assets import to_screen  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(4)
g = main.Game(windowed=True)


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
main.biome_for = lambda d, s: "facility"
fails = []


def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fails.append(what)


def fresh():
    g.new_world(2)
    g.state = "play"
    g.banner = ("", 0)
    w = g.world
    w.traps, w.enemies, w.spawners, w.bosses, w.loot, w.shootables = [], [], [], [], [], []
    L = w.level
    p = w.player
    cx, cy = int(L.start[0]), int(L.start[1])
    for x in range(max(1, cx - 8), min(L.W - 1, cx + 9)):
        for y in range(max(1, cy - 8), min(L.H - 1, cy + 9)):
            i = L.i(x, y)
            L.solid[i] = 0
            L.floor[i] = L.floor[i] or L.floor[L.i(cx, cy)]
    L.props = {}
    w.barrels, w.crates = {}, {}
    L.exit = (-50.0, -50.0)
    g.floor_layer.chunks.clear()
    p.x, p.y = cx + 0.5, cy + 0.5
    p.hp = p.max_hp = 1e6
    g.cam = list(g.cam_target())
    return w, p


REP = {"undead": "zombie", "robot": "drone", "demon": "hellspawn", "construct": "goldgolem", "mutant": "leech"}

# ---- the table, measured through World.hit_enemy for every category x type
print("== multiplier table (damage taken from a 10-point hit)")
w, p = fresh()
print("  %-10s" % "" + "".join("%11s" % t for t in DM.TYPES))
ok_all = True
for cat, kind in REP.items():
    row = []
    for t in DM.TYPES:
        e = Enemy(kind, p.x + 3, p.y, awake=True, depth=1)
        e.hp = 1e6
        w.enemies.append(e)
        w._shooter = p
        w.hit_enemy(e, 10, 1, 0, {"dtype": t})
        got = 1e6 - e.hp
        row.append(got)
        ok_all &= abs(got - 10 * DM.MULT[cat][t]) < 1e-6
        w.enemies.remove(e)
    print("  %-10s" % cat + "".join("%11.1f" % v for v in row))
check(ok_all, "every category takes exactly its table multiplier from every type")
b = Boss("blackknight", p.x + 3, p.y, 2)
b.hp = 1e6
w.hit_enemy(b, 10, 1, 0, {"dtype": "fire"})
check(abs((1e6 - b.hp) - 14) < 1e-6, "bosses use their category too (Black Knight, undead, takes 1.4x fire)")


# ---- real weapons
def shoot(arch, kind, frames=40, mods=()):
    w, p = fresh()
    wp = WP.generate(2, random.Random(1), arch=arch, rarity=0)
    for k in mods:
        WP.MOD_BY_KEY[k]["fn"](wp.st)
    wp.st["spread"] = 0
    p.weapons[p.cur] = wp
    e = Enemy(kind, p.x + 3, p.y, awake=True, depth=1)
    e.hp = 1e6
    e._p = (e.x, e.y)
    w.enemies.append(e)
    a, b_ = to_screen(1, 0)
    c, d = to_screen(0, 0)
    bot.aim = ((a - c) * 10, (b_ - d) * 10)
    g.update(1 / 60)
    bot.fire = True
    for _ in range(frames):
        e.x, e.y = e._p
        e.vx = e.vy = 0
        g.update(1 / 60)
    bot.fire = False
    for _ in range(90):
        e.x, e.y = e._p
        g.update(1 / 60)
    return 1e6 - e.hp, w, e


print("== real weapons")
for arch, good, bad in (("laser_pistol", "zombie", "hellspawn"), ("coil_rifle", "drone", "zombie"),
                        ("carbine", "leech", "goldgolem"), ("plasma", "hellspawn", "leech"), ("flamer", "zombie", "hellspawn")):
    dg, _, _ = shoot(arch, good)
    db, _, _ = shoot(arch, bad)
    t = DM.WEAPON_TYPE[arch]
    want = DM.MULT[DM.category(good)][t] / DM.MULT[DM.category(bad)][t]
    print("  %-12s (%s)  vs %-9s %6.1f   vs %-9s %6.1f   ratio %.2f (table %.2f)" % (arch, t, good, dg, bad, db, dg / max(db, 1e-6), want))
    check(dg > db * 1.3, "%s hits %s much harder than %s" % (arch, good, bad))

# cryo: demons freeze fast, undead barely
def freeze_time(kind):
    w, p = fresh()
    wp = WP.generate(2, random.Random(1), arch="cryo", rarity=0)
    wp.st["spread"] = 0
    p.weapons[p.cur] = wp
    e = Enemy(kind, p.x + 1.8, p.y, awake=True, depth=1)
    e.hp = 1e6
    w.enemies.append(e)
    a, b_ = to_screen(1, 0)
    c, d = to_screen(0, 0)
    bot.aim = ((a - c) * 10, (b_ - d) * 10)
    bot.fire = True
    for f in range(600):
        e.x, e.y = p.x + 1.8, p.y
        g.update(1 / 60)
        if e.frozen > 0:
            bot.fire = False
            return f / 60
    bot.fire = False
    return 99


fd, fu = freeze_time("hellspawn"), freeze_time("zombie")
print("  cryo: hellspawn frozen after %.1fs, zombie after %.1fs" % (fd, fu))
check(fd < fu, "cryo freezes demons faster than undead")

# ---- acid-augmented mod
print("== acid-augmented projectiles")
dmg, w, e = shoot("revolver", "goldgolem", frames=60, mods=("acid",))
n_pud = sum(1 for hz in w.hazards if hz[4] == "acidp")
print("  revolver + acid vs gold golem: %.1f damage, %d puddles" % (dmg, n_pud))
check(n_pud >= 1, "acid rounds leave puddles")
w, p = fresh()
e = Enemy("goldgolem", p.x + 3, p.y, awake=True, depth=1)
e.hp = 1e6
w.enemies.append(e)
w.acid_puddle(e.x, e.y, 10)
w.acid_puddle(p.x, p.y, 10)
hp0 = p.hp
for _ in range(120):
    e.x, e.y = p.x + 3, p.y
    g.update(1 / 60)
taken = 1e6 - e.hp
print("  2s in a puddle: gold golem (construct, chemical x1.4) took %.1f; player lost %.0f" % (taken, hp0 - p.hp))
check(taken > 20 and hp0 - p.hp < 1e-6, "puddles eat monsters (chemical) and spare players")

# ---- kinetic ammo mods + explosive
print("== kinetic ammo + explosive")
for mod, lo_kind, hi_kind in (("penetrating", "zombie", "drone"), ("expanding", "drone", "zombie")):
    rows = []
    for kind in ("zombie", "leech", "drone", "goldgolem", "hellspawn"):
        dmg, _, _ = shoot("revolver", kind, frames=1, mods=(mod,))
        rows.append((kind, dmg))
    base = {k: shoot("revolver", k, frames=1)[0] for k in ("zombie", "drone")}
    print("  %-11s " % mod + "  ".join("%s %.1f" % r for r in rows) + "   (plain: zombie %.1f drone %.1f)" % (base["zombie"], base["drone"]))
    d = dict(rows)
    check(d[hi_kind] / base[hi_kind] > 1.3 and d[lo_kind] / base[lo_kind] < 0.85, "%s rounds shift damage as designed" % mod)
wpn = WP.generate(1, random.Random(3), arch="carbine")
WP.MOD_BY_KEY["penetrating"]["fn"](wpn.st)
check(wpn.st["pierce"] >= 2, "penetrating core adds pierce (%d)" % wpn.st["pierce"])
both = sum(1 for i in range(4000) if {"penetrating", "expanding"} <= {m["key"] for m in WP.generate(3, random.Random(i), arch="smg", rarity=3).mods})
check(both == 0, "penetrating and expanding never roll together")
w, p = fresh()
vals = []
for kind in REP.values():
    e = Enemy(kind, p.x + 4, p.y, awake=True, depth=1)
    e.hp = 1e6
    w.enemies = [e]
    w.explode(e.x, e.y, 1.0, 10, hurt_player=False)
    vals.append(round(1e6 - e.hp, 2))
print("  explosion (10) vs undead/robot/demon/construct/mutant:", vals)
check(len(set(vals)) == 1 and vals[0] == 10, "explosive damage is uniform across categories")

# ---- damage numbers option
w, p = fresh()
g.damage_numbers = False
g.toggle_numbers()
check(w.show_numbers and g.damage_numbers, "toggling damage numbers turns them on in the world")
e = Enemy("drone", p.x + 2, p.y, awake=True, depth=1)
e.hp = 1e6
w.enemies = [e]
w.popups = []
w.hit_enemy(e, 5, 1, 0, {"dtype": "electrical"})
nums = [pu for pu in w.popups if pu[3][0].isdigit()]
check(nums and nums[0][3] == "8" and nums[0][4] == DM.COLOR["electrical"], "a hit shows its number in its type colour %s" % [n_[3] for n_ in nums])
w.popups = []
for _ in range(60):
    w.dot(e, 0.2, "chemical")
    w.time += 1 / 60
dots = [pu for pu in w.popups if pu[3][0].isdigit()]
check(1 <= len(dots) <= 3, "damage over time is pooled into a few numbers (%d)" % len(dots))
g.toggle_numbers()
check(not w.show_numbers, "and toggles back off")

# ---- feedback + cards
w, p = fresh()
e = Enemy("drone", p.x + 2, p.y, awake=True, depth=1)
e.hp = 1e6
w.enemies.append(e)
w.hit_enemy(e, 5, 1, 0, {"dtype": "electrical"})
e2 = Enemy("goldgolem", p.x + 2, p.y + 1.5, awake=True, depth=1)
e2.hp = 1e6
w.enemies.append(e2)
w.hit_enemy(e2, 5, 1, 0, {"dtype": "kinetic"})
texts = [pu[3] for pu in w.popups]
check("WEAK" in texts and "RESIST" in texts, "weak and resisted hits pop up feedback %s" % texts)
for _ in range(10):
    g.update(1 / 60)
wp = WP.generate(3, random.Random(2), arch="carbine", rarity=2)
for k in ("acid", "incendiary"):
    if k not in [m["key"] for m in wp.mods]:
        WP.MOD_BY_KEY[k]["fn"](wp.st)
w.loot = [Loot("weapon", p.x + 0.4, p.y, wp)]
g.update(1 / 60)
g.draw()
pygame.image.save(g.screen, os.path.join(out, "damage_feedback_and_card.png"))
print()
print("FAILED:", fails if fails else "none")

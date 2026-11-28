"""Tier projectile looks, smiting, black holes pulling players, and DOOM, DOOOOM?. python tools/tierfx_test.py [outdir]"""
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

out = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")
os.makedirs(out, exist_ok=True)
random.seed(7)
W.rnd.seed(7)
fails = []


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)


# ---- rolls
def share(rar, arch="pistol", n=400):
    guns = [WP.Weapon(arch, rar, 1, i) for i in range(n)]
    return guns, sum(1 for g in guns if g.st["smite"]) / n


sac, s_sac = share(WP.SACRED)
dem, s_dem = share(WP.DEMONIC)
_, s_eld = share(WP.ELDRITCH)
_, s_leg = share(WP.LEGENDARY)
check(0.45 < s_sac < 0.75 and 0.35 < s_dem < 0.65 and s_eld == 0 and s_leg == 0,
      "smiting rolls on sacred (%.0f%%) and demonic (%.0f%%) guns only" % (s_sac * 100, s_dem * 100))
check({g.st["smite_kind"] for g in sac if g.st["smite"]} == {"pillar", "lightning"}
      and {g.st["smite_kind"] for g in dem if g.st["smite"]} == {"hellfire"},
      "sacred smites with light or lightning, demonic with hellfire")
smg = WP.Weapon("smg", WP.SACRED, 1, next(i for i in range(400) if WP.Weapon("smg", WP.SACRED, 1, i).st["smite"]))
rev = WP.Weapon("revolver", WP.SACRED, 1, next(i for i in range(400) if WP.Weapon("revolver", WP.SACRED, 1, i).st["smite"]))
check(smg.st["smite"] < rev.st["smite"] <= 0.36, "fast guns smite less often per hit (smg %.0f%%, revolver %.0f%%)"
      % (smg.st["smite"] * 100, rev.st["smite"] * 100))
check(WP.Weapon("revolver", WP.SACRED, 1, 5).name == WP.Weapon("revolver", WP.SACRED, 1, 5).name
      and WP.Weapon("revolver", WP.SACRED, 1, 5).st["smite"] == WP.Weapon("revolver", WP.SACRED, 1, 5).st["smite"],
      "smiting is fixed by the gun's seed")
nukes = [WP.Weapon("tac_nuke", WP.VOID, 1, i) for i in range(500)]
dooms = [g for g in nukes if g.doom]
check(0.1 < len(dooms) / len(nukes) < 0.3 and all(g.name == '"%s"' % WP.DOOM_NAME and g.st["void"] == WP.DOOM_PULL for g in dooms),
      "%d of %d void tactical nukes are %s" % (len(dooms), len(nukes), WP.DOOM_NAME))
check(not any(WP.Weapon(a, WP.VOID, 1, i).doom for a in ("revolver", "grenade") for i in range(200)),
      "only the tactical nuke can be DOOM")

# ---- in a live world
g = main.Game(windowed=True)


class Bot:
    move = (0.0, 0.0)
    aim = (1.0, 0.0)
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


def open_spot(w, p, dist, clear=1.5):
    L = w.level
    for a in [i * 0.3 for i in range(21)]:
        x, y = p.x + math.cos(a) * dist, p.y + math.sin(a) * dist
        if all(not L.is_solid(int(x + ox), int(y + oy)) for ox in (-clear, 0, clear) for oy in (-clear, 0, clear)) \
                and L.line_of_sight(p.x, p.y, x, y):
            return x, y
    return None


def tick(n):
    for _ in range(n):
        g.update(1 / 60)
        for p in g.world.players:
            p.hp, p.alive = p.max_hp, True


# tier rounds are tagged and draw in their own style
w, p = setup()
shots = []
for i, rar in enumerate((WP.DEMONIC, WP.ELDRITCH, WP.SACRED, WP.VOID, WP.MYTHICAL)):
    arch = "revolver" if rar == WP.VOID else "assault"
    wp = WP.Weapon(arch, rar, 4, 3)
    p.aim = (math.cos(i * 0.5 - 1), math.sin(i * 0.5 - 1))
    n0 = len(w.projs)
    w.fire_weapon(p, wp)
    shots += w.projs[n0:]
check(sorted({b.tier for b in shots}) == sorted((WP.DEMONIC, WP.ELDRITCH, WP.SACRED, WP.VOID, WP.MYTHICAL)),
      "player rounds carry their gun's tier")
for b in shots:
    b.vx *= 0.15
    b.vy *= 0.15
    b.life = 5
n_tw = sum(1 for q in w.particles if q.kind == "twinkle")
n_em = sum(1 for q in w.particles if q.kind == "ember")
tick(8)
g.draw()
pygame.image.save(g.screen, os.path.join(out, "tier_rounds.png"))
tw = sum(1 for q in w.particles if q.kind == "twinkle") - n_tw
em = sum(1 for q in w.particles if q.kind == "ember") - n_em
check(tw > 0 and em > 0, "sacred rounds shed white sparkles (%d), demonic rounds red embers (%d)" % (tw, em))
for kind in ("bullet", "pellet", "slug", "bolt", "rail", "plasma", "grenade", "rocket", "missile", "nuke", "mortar", "acid"):
    for rar in main.TIER_PAL:
        b = W.Proj(kind, p.x + 1, p.y, 0.6, 3, 0, 5)
        b.tier = rar
        g.draw_proj(b, 0, 0)
check(True, "every tier draws every projectile kind")

# smiting
for kind in ("pillar", "lightning", "hellfire"):
    spot = None
    while spot is None:
        w, p = setup()
        spot = open_spot(w, p, 5.0)
    e = W.Enemy("zombie", spot[0], spot[1], awake=True, depth=4)
    e.hp = e.maxhp = 5000
    e.speed = 0
    e2 = W.Enemy("zombie", spot[0] + 0.6, spot[1], awake=True, depth=4)
    e2.hp = e2.maxhp = 5000
    e2.speed = 0
    w.enemies = [e, e2]
    b = W.Proj("bullet", e.x, e.y, 0.6, 1, 0, 10)
    b.smite, b.smite_kind = 1.0, kind
    w.hit_enemy(e, 10, 1, 0, b)
    made = [sm for sm in w.smites if sm[2] == kind]
    lost = 5000 - e.hp
    burning = kind != "hellfire" or e.burn > 0
    tick(6)
    g.draw()
    pygame.image.save(g.screen, os.path.join(out, "smite_%s.png" % kind))
    check(made and lost > 10 and (5000 - e2.hp) > 0 and burning, "%s: struck for %.0f, splashed its neighbour" % (kind, lost))
    tick(60)
    check(not w.smites, "%s fades out" % kind)
w.smite_cd = 0
n = len(w.smites)
b = W.Proj("bullet", 0, 0, 0, 1, 0, 10)
b.smite, b.smite_kind, b.hostile = 1.0, "pillar", True
e.hp = 5000
w.hit_enemy(e, 10, 1, 0, b)
check(len(w.smites) == n, "hostile rounds never smite")

# black holes drag at the player, harder near the heart
pulls = []
for dist in (4.5, 1.8):
    spot = None
    while spot is None:
        w, p = setup()
        spot = open_spot(w, p, dist, clear=2.5)
    pr = W.Proj("bullet", spot[0], spot[1], 0.5, 0, 0, 20)
    pr.void = 6.0
    w.open_void(pr, *spot)
    v = w.voids[0]
    v["t"] = v["grow"] * 0.7
    d0 = math.hypot(p.x - spot[0], p.y - spot[1])
    tick(6)
    pulls.append(d0 - math.hypot(p.x - spot[0], p.y - spot[1]))
check(pulls[0] > 0.01 and pulls[1] > pulls[0] * 1.5, "a black hole pulls the player, harder up close (%.2f vs %.2f tiles in 0.1 s)"
      % (pulls[0], pulls[1]))

# DOOM, DOOOOM?
w, p = setup()
L = w.level
spot = None
for dist in (14.0, 13.0, 15.0, 12.5, 16.0):
    spot = open_spot(w, p, dist, clear=1.0)
    if spot:
        break
if spot is None:
    spot = (p.x + 14, p.y)
hx, hy = spot
pack = []
for k in range(8):
    a = k * math.tau / 8
    for rr in (2.0, 6.0):
        x, y = hx + math.cos(a) * rr, hy + math.sin(a) * rr
        if not L.is_solid(int(x), int(y)):
            e = W.Enemy("zombie", x, y, awake=True, depth=4)
            e.hp = e.maxhp = 3000
            e.speed = 0
            pack.append(e)
w.enemies = list(pack)
far = W.Enemy("zombie", hx + 30, hy, awake=True, depth=4)
w.enemies.append(far)
walls0 = sum(1 for yy in range(L.H) for xx in range(L.W) if L.solid[L.i(xx, yy)] == 1
             and math.hypot(xx + 0.5 - hx, yy + 0.5 - hy) < WP.DOOM_RADIUS)
hz0 = len(w.hazards)
gas0 = len(getattr(w, "gas", []) or [])
doom = next(gn for gn in nukes if gn.doom)
pr = W.Proj("nuke", hx, hy, 0.5, 0, 0, doom.st["dmg"])
pr.void, pr.effect, pr.kind = doom.st["void"], "doom", "nuke"
pr.rad, pr.blast = doom.st["rad"], doom.st["blast"]
w.open_void(pr, hx, hy)
v = w.voids[0]
check(v["doom"] and v["R"] == WP.DOOM_PULL and v["grow"] > 3, "DOOM opens a vast hole (pulls %.0f tiles, grows %.1f s)" % (v["R"], v["grow"]))
tick(int(60 * 2.5))
g.draw()
pygame.image.save(g.screen, os.path.join(out, "doom_hole.png"))
tick(int(60 * 1.5))
g.draw()
pygame.image.save(g.screen, os.path.join(out, "doom_blast.png"))
walls1 = sum(1 for yy in range(L.H) for xx in range(L.W) if L.solid[L.i(xx, yy)] == 1
             and math.hypot(xx + 0.5 - hx, yy + 0.5 - hy) < WP.DOOM_RADIUS)
dead = sum(1 for e in pack if not e.alive)
check(dead == len(pack) and far.alive, "DOOM destroyed all %d monsters in the blast, spared the one 30 tiles off" % len(pack))
check(walls0 == 0 or walls1 < walls0 * 0.5, "DOOM flattened the walls (%d -> %d)" % (walls0, walls1))
new_hz = [hz for hz in w.hazards[hz0:] if hz[4] in ("rad", "acidp", "gas", "chem")]
check(not new_hz and len(getattr(w, "gas", []) or []) <= gas0, "DOOM leaves no fallout or chemical spill")
gw = WP.Weapon("tac_nuke", WP.VOID, 4, nukes.index(doom))
g.weapon_card(g.screen, gw, 40, 40)
pygame.image.save(g.screen, os.path.join(out, "doom_card.png"))
check(True, "DOOM card draws")

print()
print("ALL PASSED" if not fails else "%d FAILED" % len(fails))
sys.exit(1 if fails else 0)

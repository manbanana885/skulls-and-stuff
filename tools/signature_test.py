"""Check each signature enemy's unique mechanic. python tools/signature_test.py <outdir>"""
import os
import sys
import math
import random
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import weapons as WP  # noqa: E402
from world import Enemy, Proj  # noqa: E402
from bestiary import SIGNATURE  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(5)
g = main.Game(windowed=True)


class Bot:
    move = (0.0, 0.0)
    aim = (10, 5)
    fire = False
    pressed = set()
    device_name = None

    def poll(self, ps):
        pass


bot = Bot()
g.input = bot
results = {}


def setup(biome, kind, dist=3.0, awake=True):
    main.biome_for = lambda d, s: biome
    g.new_world(3)
    g.state = "play"
    g.banner = ("", 0)
    w = g.world
    w.bosses, w.enemies = [], []
    p = w.player
    L = w.level
    for a in [i * 0.4 for i in range(16)]:
        x, y = p.x + math.cos(a) * dist, p.y + math.sin(a) * dist
        if not L.is_solid(int(x), int(y)) and L.line_of_sight(p.x, p.y, x, y):
            break
    e = Enemy(kind, x, y, awake=awake, depth=3)
    w.enemies.append(e)
    return w, p, e


def run(w, p, frames, keep_alive=True, cb=None):
    for f in range(frames):
        if keep_alive:
            p.hp = p.max_hp
            p.alive = True
        g.update(1 / 60)
        if cb:
            cb(f)


def check(name, fn):
    try:
        results[name] = fn()
    except Exception:
        traceback.print_exc()
        results[name] = "ERROR"


def t_pink():
    w, p, e = setup("facility", "pinkmelt", 4)
    run(w, p, 180)
    g.draw()
    pygame.image.save(g.screen, os.path.join(out, "pinkmelt.png"))
    shots = sum(1 for q in w.projs if q.hostile)
    return "wields %s (%s), hostile shots in flight %d" % (e.weapon.name, e.weapon.arch, shots) if e.weapon else "NO WEAPON"


def t_statue():
    w, p, e = setup("limbo", "mourner", 5)
    p.status = {}
    dx, dy = e.x - p.x, e.y - p.y
    bot.aim = ((dy - dx) * 32, (dx + dy) * 16)       # look at it
    x0 = (e.x, e.y)
    run(w, p, 60)
    moved_watched = math.hypot(e.x - x0[0], e.y - x0[1])
    bot.aim = (-(dy - dx) * 32, -(dx + dy) * 16)     # look away
    x1 = (e.x, e.y)
    run(w, p, 40)
    moved_away = math.hypot(e.x - x1[0], e.y - x1[1])
    bot.aim = (10, 5)
    return "moved %.2f while watched, %.2f while unwatched" % (moved_watched, moved_away)


def t_vacuum():
    w, p, e = setup("gluttony", "devourer", 5)
    d0 = math.hypot(e.x - p.x, e.y - p.y)
    run(w, p, 150)
    return "player pulled from %.1f to %.1f tiles" % (d0, math.hypot(e.x - p.x, e.y - p.y))


def t_lurker():
    w, p, e = setup("sewer", "lurker", 6)
    hp0 = e.hp
    w.projs.append(Proj("bullet", e.x - 1, e.y, 0.5, 20, 0, 5))
    run(w, p, 10)
    sub_dmg = hp0 - e.hp
    run(w, p, 300)
    return "damage taken while submerged: %.0f, has surfaced at some point: %s" % (sub_dmg, e.state_t != 0)


def t_shield():
    w, p, e = setup("castle", "shieldbearer", 3)
    e.speed = 0
    run(w, p, 5)
    hp0 = e.hp
    dx, dy = e.x - p.x, e.y - p.y
    d = math.hypot(dx, dy)
    for k in range(5):
        w.projs.append(Proj("bullet", p.x + dx / d * 0.5, p.y + dy / d * 0.5, 1.0, dx / d * 20, dy / d * 20, 5))
    run(w, p, 30)
    front = hp0 - e.hp
    hp1 = e.hp
    for k in range(5):   # from behind
        w.projs.append(Proj("bullet", e.x + dx / d * 1.5, e.y + dy / d * 1.5, 1.0, -dx / d * 20, -dy / d * 20, 5))
    run(w, p, 20)
    return "damage from front %.0f, from behind %.0f" % (front, hp1 - e.hp)


def t_split():
    w, p, e = setup("biotech", "clone", 3)
    e.hit(w, e.maxhp * 0.6, 1, 0)
    run(w, p, 5)
    return "clones alive after one heavy hit: %d" % sum(1 for x in w.enemies if x.kind == "clone")


def t_chest():
    w, p, e = setup("greed", "chestmimic", 5, awake=False)
    g.draw()
    st0 = e.state
    p.x, p.y = e.x - 1.5, e.y
    run(w, p, 30)
    return "state %s -> %s when approached" % (st0, e.state)


def t_status(kind, biome, eff):
    w, p, e = setup(biome, kind, 3)
    seen = set()
    run(w, p, 400, cb=lambda f: seen.update(p.status))
    return "player effects inflicted: %s" % (sorted(seen) or "none")


def t_generic(kind, biome):
    w, p, e = setup(biome, kind, 4)
    hp0 = p.hp
    dmg = [0]

    def cb(f):
        dmg[0] += max(0, p.max_hp - p.hp)
    run(w, p, 300, keep_alive=False, cb=lambda f: (dmg.__setitem__(0, dmg[0] + max(0, p.max_hp - p.hp)), setattr(p, "hp", p.max_hp),
                                                   setattr(p, "alive", True)))
    extra = ""
    if kind == "bonepriest":
        extra = ", minions raised %d" % sum(1 for x in w.enemies if x.kind == "crawler")
    if kind == "raddrone":
        extra = ", rad puddles %d" % sum(1 for h in w.hazards if h[4] == "rad")
    if kind == "hazmatsprayer":
        extra = ", gas clouds %d" % sum(1 for h in w.hazards if h[4] == "gas")
    if kind == "flagellant":
        extra = ", self-inflicted hp %d/%d" % (e.hp, e.maxhp)
    return "damage dealt to player in 5s: %d%s" % (dmg[0], extra)


check("pinkmelt", t_pink)
check("mourner", t_statue)
check("devourer", t_vacuum)
check("lurker", t_lurker)
check("shieldbearer", t_shield)
check("clone", t_split)
check("chestmimic", t_chest)
check("wendigo", lambda: t_status("wendigo", "outpost", "chill"))
check("enthraller", lambda: t_status("enthraller", "lust", "confuse"))
check("rustbound", lambda: t_status("rustbound", "otherworld", "pull"))
for kind, biome in (("bonepriest", "ossuary"), ("cinderfiend", "hell"), ("boghag", "wrath"), ("flagellant", "heresy"),
                    ("hookman", "violence"), ("raddrone", "nuclear"), ("hazmatsprayer", "chemical"), ("rustbound", "otherworld")):
    check(kind + " (combat)", lambda k=kind, b=biome: t_generic(k, b))
for k, v in results.items():
    print("%-22s %s" % (k, v))
print("signature enemies defined:", len(SIGNATURE))

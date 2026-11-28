"""Heavy gunners, vermin, fire demons, the Ocularch and the top-tier drop rates. python tools/monsters_test.py"""
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
import level as LV  # noqa: E402
import weapons as WP  # noqa: E402
import damage as DM  # noqa: E402
from bosses import Boss  # noqa: E402

random.seed(7)
W.rnd.seed(7)
fails = []
NEW = ["pinkheavy", "viper", "cobra", "scorpion", "roach", "imp", "pitdemon", "devil"]


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)


# ---- drop rates
odds = {}
for lv in (1, 5, 9):
    rr = random.Random(lv)
    n = 200000
    c = sum(1 for _ in range(n) if WP.roll_rarity(rr, lv) >= WP.DEMONIC)
    odds[lv] = n / max(1, c)
print("demonic / eldritch / sacred: 1 in %.0f (depth 1), 1 in %.0f (depth 5), 1 in %.0f (depth 9)" % (odds[1], odds[5], odds[9]))
check(300 < odds[1] < 900 and 40 < odds[5] < 120, "top tiers are rare but findable")
rr = random.Random(3)
tiers = [WP.roll_rarity(rr, 5) for _ in range(200000)]
check(tiers.count(WP.MYTHICAL) > tiers.count(WP.DEMONIC) > tiers.count(WP.ELDRITCH) > tiers.count(WP.SACRED) > 0,
      "rarer tiers still roll less often (mythical > demonic > eldritch > sacred)")

# ---- eldritch gifts: multi-shot, homing, radioactive / corrosive spatter
gifts = {"twin": 0, "triple": 0, "seeking": 0, "acid": 0, "irradiated": 0}
none_ = 0
for i in range(400):
    wp = WP.Weapon(random.choice(list(WP.ARCH)), WP.ELDRITCH, 5, i)
    keys = {m["key"] for m in wp.mods}
    for k in gifts:
        gifts[k] += k in keys
    none_ += not (keys & set(gifts))
    if "triple" in keys:
        check(wp.st["twin"] == 2 and "twin" not in keys, "triple-linked replaces twin-linked") if gifts["triple"] == 1 else None
print("  400 eldritch guns:", gifts, "with no gift:", none_)
check(gifts["triple"] > 40 and gifts["twin"] > 40 and gifts["seeking"] > 80 and gifts["irradiated"] > 40 and gifts["acid"] > 40,
      "eldritch guns often double / triple, home and spatter")
check(none_ < 40, "almost every eldritch gun carries a gift (%d without, all arch-limited)" % none_)
plain = sum(1 for i in range(400) if any(m["key"] in ("triple", "irradiated") for m in WP.Weapon("assault", WP.LEGENDARY, 5, i).mods))
check(plain == 0, "triple-linked and irradiated never roll outside eldritch")

# ---- spawning: the Pink Heavy ramps up with depth; packs come in packs
for d in (2, 3, 5, 7):
    print("  pink heavy weight at depth %d: %.2f" % (d, LV.ramp("pinkheavy", d)))
check(LV.ramp("pinkheavy", 2) < 0.1 and LV.ramp("pinkheavy", 5) >= 1.0, "pink heavy: rare at depth 2, full weight by depth 5")
counts = {}
for seed in range(30):
    L = LV.Level(6, seed=seed, biome="facility")
    for k, _, _ in L.enemies:
        counts[k] = counts.get(k, 0) + 1
print("  30 depth-6 facility levels:", {k: counts.get(k, 0) for k in NEW})
check(all(counts.get(k, 0) > 0 for k in NEW), "every new monster shows up in generated levels")
early = sum(1 for s in range(30) for k, _, _ in LV.Level(2, seed=s, biome="facility").enemies if k == "pinkheavy")
check(early < counts.get("pinkheavy", 0) / 2, "pink heavies are much scarcer at depth 2 (%d) than depth 6 (%d)" % (early, counts.get("pinkheavy", 0)))

# ---- behaviour in a live world
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


def setup(kind, dist=4.0, depth=5, boss=False):
    main.biome_for = lambda d, s: "facility"
    g.new_world(depth)
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
    if boss:
        e = Boss(kind, x, y, depth)
        w.bosses.append(e)
    else:
        e = W.Enemy(kind, x, y, awake=True, depth=depth)
        w.enemies.append(e)
    return w, p, e


def run(w, p, frames, cb=None):
    taken = 0.0
    for f in range(frames):
        hp0 = p.hp
        g.update(1 / 60)
        taken += max(0.0, hp0 - p.hp)
        p.hp, p.alive = p.max_hp, True
        if cb:
            cb(f)
    return taken


for kind, eff in (("viper", "poison"), ("cobra", "poison"), ("scorpion", "venom"), ("imp", "burn"), ("pitdemon", "burn"),
                  ("devil", "burn")):
    w, p, e = setup(kind)
    seen = set()
    taken = run(w, p, 60 * 10, cb=lambda f: seen.update(p.status))
    check(eff in seen and taken > 20, "%s hurts (%d in 10 s) and inflicts %s" % (kind, taken, eff))
    g.draw()

# triple-linked guns fire three lanes; irradiated hits leave radioactive puddles
w, p, e = setup("zombie", 5)
wp = WP.Weapon("assault", WP.ELDRITCH, 5, 1)
wp.mods = [WP.MOD_BY_KEY["triple"], WP.MOD_BY_KEY["irradiated"]]
for m in wp.mods:
    m["fn"](wp.st)
check(wp.projectiles_per_shot() == 3, "triple-linked: 3 projectiles per shot")
n0 = len(w.projs)
w.fire_weapon(p, wp) if hasattr(w, "fire_weapon") else None
check(len(w.projs) - n0 == 3, "triple-linked fires three shots at once (%d)" % (len(w.projs) - n0))
w.acid_puddle(p.x + 1, p.y, 10, "radiation")
check(w.hazards[-1][7] == "radiation", "irradiated spatter makes a radiation puddle")
g.draw()

# deeper sectors: meaner monsters
z1, z9 = W.Enemy("zombie", 0, 0, depth=1), W.Enemy("zombie", 0, 0, depth=9)
check(z1.aggro == 1.0 and z9.aggro > 1.5, "aggression climbs with depth (x%.2f at sector 9)" % z9.aggro)
n3 = sum(len(LV.Level(3, seed=s, biome="facility").enemies) for s in range(10))
n8 = sum(len(LV.Level(8, seed=s, biome="facility").enemies) for s in range(10))
check(n8 > n3 * 2, "sector 8 holds far more monsters than sector 3 (%d vs %d per level)" % (n8 / 10, n3 / 10))

# the deployed mortar lobs toward its target (not behind itself)
import support as SU  # noqa: E402
w, p, e = setup("zombie", 6)
e.speed = 0
mod = SU.generate(5, random.Random(2), kind="mortar")
t = SU.Turret(mod, p.x, p.y, (1.0, 0.0))
w.turrets.append(t)
fired = None
for f in range(240):
    n0 = len(w.projs)
    t.update(w, 1 / 60, p)
    new = [q for q in w.projs[n0:] if q.kind == "mortar"]
    if new:
        fired = new[0]
        break
if fired:
    to_e = ((e.x - t.x) * fired.vx + (e.y - t.y) * fired.vy) > 0
    face = (t.aim[0] * (e.x - t.x) + t.aim[1] * (e.y - t.y)) > 0
    check(to_e and face, "mortar faces and fires toward its target")
else:
    check(False, "mortar fired")

# poison / burn tick down on their own
w, p, e = setup("viper", 30)
w.enemies = []
w.player_effect("burn", who=p)
w.player_effect("poison", who=p)
hp0 = p.hp
for _ in range(60):
    g.update(1 / 60)
check(hp0 - p.hp > 4 and "burn" in p.status, "burning and poison eat %.1f integrity in a second" % (hp0 - p.hp))
for _ in range(60 * 5):
    g.update(1 / 60)
check("burn" not in p.status and "poison" not in p.status, "...and wear off")

# scorpion pincers soak shots from the front, not from behind
w, p, e = setup("scorpion", 4)
e.speed = 0
e.cd2 = 99
run(w, p, 3)
dx, dy = e.x - p.x, e.y - p.y
d = math.hypot(dx, dy)
e.hp = e.maxhp = 1000
w.hit_enemy(e, 10, -dx / d * 20, -dy / d * 20, W.Proj("bullet", e.x, e.y, 1, -dx / d * 20, -dy / d * 20, 10))     # bullet travelling toward the player = from behind
back = 1000 - e.hp
e.hp = 1000
w.hit_enemy(e, 10, dx / d * 20, dy / d * 20, W.Proj("bullet", e.x, e.y, 1, dx / d * 20, dy / d * 20, 10))       # travelling away from the player = into its face
front = 1000 - e.hp
check(front < back * 0.5, "scorpion: %.1f from the front vs %.1f from behind" % (front, back))

# roaches shrug off radiation and blasts
r = W.Enemy("roach", 0, 0)
z = W.Enemy("zombie", 0, 0)
check(DM.mult(r, "radiation") < 0.2 and DM.mult(r, "explosive") <= 0.5, "roach: radiation x%.2f, explosive x%.2f" %
      (DM.mult(r, "radiation"), DM.mult(r, "explosive")))
check(DM.mult(W.Enemy("pitdemon", 0, 0), "fire") == 0.0, "pit demon is immune to fire")

# roaches jink away from your aim
w, p, e = setup("roach", 5)
dx, dy = e.x - p.x, e.y - p.y
p.aim = (dx / math.hypot(dx, dy), dy / math.hypot(dx, dy))
d0 = math.hypot(e.x - p.x, e.y - p.y)
side = 0.0
for f in range(30):
    g.update(1 / 60)
    p.hp = p.max_hp
    # how far off the aim line it has slid
    qx, qy = e.x - p.x, e.y - p.y
    side = max(side, abs(qx * -p.aim[1] + qy * p.aim[0]))
check(side > 0.5, "roach slides %.2f tiles off your aim line" % side)

# the Pink Heavy with each weapon
for arch in ("chaingun", "railgun", "barrage", "tac_nuke"):
    w, p, e = setup("pinkheavy", 6)
    e.weapon = WP.generate(5, arch=arch, rarity=1)
    e.wshot = W.weapon_to_shot(e.weapon)
    kinds = set()
    taken = run(w, p, 60 * 12, cb=lambda f: kinds.update(q.kind for q in w.projs if q.hostile))
    check(taken > (30 if arch == "tac_nuke" else 25), "pink heavy with %s deals %d in 12 s (shots: %s)" % (arch, taken, sorted(kinds)))
    if arch == "tac_nuke":
        check(any(h[4] == "rad" for h in w.hazards) or "nuke" in kinds, "its warhead leaves fallout")
    g.draw()
drops = 0
for i in range(40):
    w, p, e = setup("pinkheavy", 6)
    run(w, p, 2)
    e.hp = 1
    n0 = sum(1 for l in w.loot if l.kind == "weapon")
    e.hit(w, 50, 1, 0)
    drops += any(l.kind == "weapon" and l.item.arch in ("chaingun", "railgun", "barrage", "tac_nuke") for l in w.loot[n0:])
check(4 <= drops <= 22, "pink heavy dropped its heavy weapon %d / 40 times" % drops)

# the Ocularch: eyestalk rays of several kinds, plasma from the stalks
w, p, e = setup("ocularch", 5, boss=True)
e.awake = True
seen, rays, plasma = set(), set(), 0
cnt = [0]


def cb(f):
    seen.update(p.status)
    for L in e.eyebeams:
        rays.add(L["ray"])
    cnt[0] += sum(1 for q in w.projs if q.hostile and q.kind == "plasma" and q.age == 0)


taken = run(w, p, 60 * 40, cb=cb)
check(len(rays) >= 3 and taken > 100, "ocularch fired rays %s, dealt %d in 40 s, effects %s" % (sorted(rays), taken, sorted(seen)))
e.hp = e.maxhp * 0.2
run(w, p, 60 * 20)
check(e.phase == 2, "ocularch reaches its last phase")
g.draw()
pygame.image.save(g.screen, os.path.join(os.environ.get("TEMP", "."), "ocularch_test.png"))

print()
print("ALL PASSED" if not fails else "%d FAILED" % len(fails))
sys.exit(1 if fails else 0)

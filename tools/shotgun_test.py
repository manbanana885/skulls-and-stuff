"""Shotgun family: auto shotgun, double / triple / quad break-actions, buckshot vs dum-dum vs sabot slugs.
python tools/shotgun_test.py <outdir>"""
import os
import sys
import math
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SKULLS_SAVE"] = os.devnull
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import weapons as WP  # noqa: E402
from world import Enemy  # noqa: E402
from assets import to_screen  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_shotgun_test")
os.makedirs(out, exist_ok=True)
SHOTGUNS = ("shotgun", "auto_shotgun", "shotgun_2", "shotgun_3", "shotgun_4")
fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


# ---------------------------------------------------------------- rolls
print("rolls")
for a in SHOTGUNS:
    shells = {None: 0, "dumdum": 0, "sabot": 0}
    bad_mag = bad_slugs = 0
    for i in range(1500):
        wp = WP.generate(random.Random(i).randint(1, 9), random.Random(i), arch=a, rarity=i % 9)
        shells[wp.shell] += 1
        n = max(1, WP.ARCH[a].get("barrels", 0))
        if WP.ARCH[a].get("barrels") and wp.st["mag"] != 1:
            bad_mag += 1
        if wp.shell and (wp.st["pellets"] != n or wp.st["proj"] != "slug"
                         or wp.projectiles_per_shot() != n * (2 if wp.st["twin"] else 1)):
            bad_slugs += 1
        if wp.shell and wp.ammo_type != WP.SHELLS[wp.shell]["ammo"]:
            bad_slugs += 1
    check(bad_mag == 0, "%-12s break-action always holds one load (%d bad)" % (a, bad_mag))
    check(bad_slugs == 0, "%-12s slug guns fire one slug per barrel with the shell's ammo (%d bad)" % (a, bad_slugs))
    check(abs(shells[None] / 1500 - 0.7) < 0.04 and abs(shells["dumdum"] / 1500 - 0.2) < 0.03
          and abs(shells["sabot"] / 1500 - 0.1) < 0.025, "%-12s shells rolled 70/20/10: %s" % (a, shells))
sample = [WP.generate(3, random.Random(s), arch=a, rarity=1).name for s in range(40) for a in ("shotgun_2", "auto_shotgun")]
print("  names:", ", ".join(sorted(set(n for n in sample if "Dum" in n or "Sabot" in n))[:6]))

# ---------------------------------------------------------------- live fire
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
lane = None
for attempt in range(20):                # levels are random: build until one has a long open lane
    g.new_world(1)
    L = g.world.level
    for y in range(2, L.H - 2):
        for x in range(2, L.W - 16):
            if all(not L.is_solid(x + k, y + d) for k in range(14) for d in (-1, 0, 1)):
                lane = (x, y)
                break
        if lane:
            break
    if lane:
        break
g.state = "play"
w = g.world
p = w.player
w.traps, w.enemies, w.spawners, w.bosses = [], [], [], []
x0, y0 = lane
sx, sy = to_screen(1, 0)
s0x, s0y = to_screen(0, 0)
AIM = ((sx - s0x) * 10, (sy - s0y) * 10)       # straight down +x


def make(arch, shell):
    for s in range(4000):
        wp = WP.generate(1, random.Random(s), arch=arch, rarity=0)
        if wp.shell == shell and not wp.mods:
            return wp
    raise RuntimeError("no %s %s" % (arch, shell))


def volley(arch, shell, shot_png=None):
    """One trigger pull at a line of 6 tough zombies 2..7 tiles away."""
    wp = make(arch, shell)
    p.weapons[p.cur] = wp
    p.x, p.y = x0 + 0.5, y0 + 0.5
    p.buffs = {}
    w.projs = []
    w.enemies = []
    mons = []
    for k in range(6):
        e = Enemy("zombie", x0 + 2.5 + k, y0 + 0.5, awake=True, depth=1)
        e.hp = 1e6
        e.speed = 0
        mons.append(e)
        w.enemies.append(e)
    wp.cd = 0
    bot.aim, bot.fire = AIM, True
    g.update(1 / 60)
    bot.fire = False
    fired = len([b for b in w.projs if not b.hostile])
    reload_now = wp.reload_t > 0
    pushed = 0.0
    for f in range(50):
        g.update(1 / 60)
        if f == 3 and shot_png:
            g.draw()
            pygame.image.save(g.screen, os.path.join(out, shot_png))
        pushed = max(pushed, max(abs(e.vx) for e in mons))
    dealt = [1e6 - e.hp for e in mons]
    return wp, fired, dealt, reload_now, pushed


print("live fire (one trigger pull into a line of 6 zombies)")
for a in SHOTGUNS:
    for shell in (None, "dumdum", "sabot"):
        wp, fired, dealt, reload_now, pushed = volley(a, shell, "%s_%s.png" % (a, shell or "buck"))
        hit = sum(1 for d in dealt if d > 0)
        n = max(1, WP.ARCH[a].get("barrels", 0))
        want = n if shell else wp.st["pellets"]
        print("    %-12s %-6s fired %2d  monsters hit %d  total dmg %5.1f  first %5.1f  shove %.1f  %s" % (
            a, shell or "buck", fired, hit, sum(dealt), dealt[0], pushed, wp.name))
        check(fired == want, "%s %s fires %d projectiles (want %d)" % (a, shell or "buck", fired, want))
        if WP.ARCH[a].get("barrels"):
            check(reload_now, "%s %s cracks open to reload right after the shot" % (a, shell or "buck"))
        if shell == "sabot":
            check(hit >= 5, "%s sabot punches through the line (%d of 6)" % (a, hit))
        if shell == "dumdum":
            check(hit <= 2 + n and dealt[0] > 0, "%s dum-dum stops in the first monsters (%d hit)" % (a, hit))

# auto shotgun holds the trigger
wp = make("auto_shotgun", None)
p.weapons[p.cur] = wp
w.enemies, w.projs = [], []
bot.aim, bot.fire = AIM, True
a0 = wp.ammo
for _ in range(60):
    g.update(1 / 60)
bot.fire = False
check(a0 - wp.ammo >= 3, "auto shotgun fires %d shells in a held second (rate %.1f, drum %d)" % (a0 - wp.ammo, wp.st["rate"], wp.st["mag"]))

# break-action reloads back to one load
wp = make("shotgun_4", None)
p.weapons[p.cur] = wp
wp.cd = 0
bot.fire = True
g.update(1 / 60)
bot.fire = False
for _ in range(int(wp.st["reload"] * 60) + 5):
    g.update(1 / 60)
check(wp.ammo == 1 and wp.reload_t <= 0, "quad barrel reloads to 1 (%.1fs)" % wp.st["reload"])

# spent casings
def casings():
    return [q for q in w.particles if q.kind == "shell" and q.size >= 2.0]


def fire_once(wp, frames_after):
    p.weapons[p.cur] = wp
    wp.cd, wp.reload_t = 0, 0
    w.particles, w.ejects, w.enemies, w.projs = [], [], [], []
    bot.aim, bot.fire = AIM, True
    g.update(1 / 60)
    bot.fire = False
    now = [(q.size, q.color) for q in casings()]
    for _ in range(frames_after):
        g.update(1 / 60)
    return now, [(q.size, q.color) for q in casings()]


now, later = fire_once(make("shotgun", None), 30)
check(not now and len(later) == 1, "pump shotgun ejects its hull after the shot, on the pump (%d then %d)" % (len(now), len(later)))
now, later = fire_once(make("shotgun_3", "dumdum"), 30)
check(not now and len(later) == 3, "triple barrel drops 3 hulls as it cracks open (%d then %d)" % (len(now), len(later)))
now, later = fire_once(make("auto_shotgun", None), 1)
check(len(now) == 1, "auto shotgun kicks a hull straight out (%d)" % len(now))
now, later = fire_once(WP.generate(1, random.Random(1), arch="assault", rarity=0), 1)
check(len(now) == 1 and now[0][1] == (230, 180, 60), "assault rifle throws brass with every shot")
rv = WP.generate(1, random.Random(1), arch="revolver", rarity=0)
now, later = fire_once(rv, 1)
check(not now, "revolver keeps its brass while firing")
rv.ammo = 0
now, later = fire_once(rv, 20)
check(len(later) == rv.st["mag"], "revolver dumps %d cases when the reload starts (%d)" % (rv.st["mag"], len(later)))
for la in ("laser_pistol", "laser_rifle"):
    lw = WP.generate(1, random.Random(2), arch=la, rarity=0)
    lw.ammo = 1
    now, later = fire_once(lw, 10)
    check(sum(1 for sz, _ in later if sz >= 4) == 1, "%s drops a spent battery when the reload begins" % la)
w.particles = []
p.weapons[p.cur] = make("shotgun_4", None)
p.x, p.y = x0 + 0.5, y0 + 0.5
for k in range(3):
    p.weapons[p.cur].cd = p.weapons[p.cur].reload_t = 0
    p.weapons[p.cur].ammo = 1
    bot.fire = True
    g.update(1 / 60)
    bot.fire = False
    for _ in range(25):
        g.update(1 / 60)
g.draw()
pygame.image.save(g.screen, os.path.join(out, "casings.png"))

# card DPS / RATE match what actually happens when you hold the trigger for 36 seconds
print("held trigger vs card")
for a in ("shotgun", "auto_shotgun", "shotgun_2", "shotgun_4", "assault", "revolver"):
    wp = WP.generate(1, random.Random(7), arch=a, rarity=0)
    p.weapons[p.cur] = wp
    wp.cd = wp.reload_t = 0
    wp.ammo = wp.st["mag"]
    w.enemies, w.projs, w.particles = [], [], []
    shots = 0
    bot.aim, bot.fire = AIM, True
    for _ in range(36 * 60):
        cd0 = wp.cd
        g.update(1 / 60)
        if wp.cd > cd0:                   # the cooldown restarts on every shot (a break-action refills and fires in one frame)
            shots += 1
    bot.fire = False
    measured = shots / 36.0
    card = dict(wp.card_lines())
    print("    %-12s %5.2f shots/s measured, card RATE %s DPS %s  (model %.2f shots/s)" % (a, measured, card["RATE"], card["DPS"],
                                                                                         wp.shots_per_sec()))
    check(abs(measured - wp.shots_per_sec()) / wp.shots_per_sec() < 0.12, "%s card fire rate matches the gun (%.2f vs %.2f)"
          % (a, measured, wp.shots_per_sec()))

# tower shields stop buckshot and dum-dums, but not penetrating cores or sabots
print("shieldbearer, shot from the front")
for arch, shell, force_pen in (("shotgun", None, False), ("shotgun", "dumdum", False), ("shotgun", "sabot", False),
                               ("carbine", None, True), ("carbine", None, False)):
    wp = make(arch, shell) if arch == "shotgun" else WP.generate(1, random.Random(3), arch=arch, rarity=0)
    if arch == "shotgun" and not shell:
        wp.st["ammo"] = None              # plain buckshot (a Penetrating roll would rightly go through)
    if arch == "carbine":
        wp.st["ammo"] = "pen" if force_pen else None
    p.weapons[p.cur] = wp
    p.x, p.y = x0 + 0.5, y0 + 0.5
    w.projs, w.particles = [], []
    e = Enemy("shieldbearer", x0 + 4.5, y0 + 0.5, awake=True, depth=1)
    e.hp = 1e6
    e.speed = 0
    e.target = p
    w.enemies = [e]
    wp.cd = wp.reload_t = 0
    wp.ammo = wp.st["mag"]
    bot.aim, bot.fire = AIM, True
    g.update(1 / 60)
    bot.fire = False
    for _ in range(40):
        g.update(1 / 60)
    dealt = 1e6 - e.hp
    label = "%s %s" % (arch, shell or ("penetrating" if force_pen else "standard"))
    through = shell == "sabot" or force_pen
    print("    %-22s damage behind the shield %.1f" % (label, dealt))
    check((dealt > 0) == through, "%s %s the shield" % (label, "goes through" if through else "is stopped by"))

# chemical jets splash off the shield into a puddle at the knight's feet
print("jets vs shieldbearer, from the front")
for arch in ("jet_napalm", "jet_cryo", "jet_rad"):
    wp = WP.generate(1, random.Random(4), arch=arch, rarity=0)
    p.weapons[p.cur] = wp
    p.x, p.y = x0 + 0.5, y0 + 0.5
    w.projs, w.particles, w.hazards = [], [], []
    e = Enemy("shieldbearer", x0 + 4.5, y0 + 0.5, awake=True, depth=1)
    e.hp = 1e6
    e.speed = 0
    e.target = p
    w.enemies = [e]
    wp.cd = wp.reload_t = 0
    bot.aim, bot.fire = AIM, True
    for _ in range(60):
        g.update(1 / 60)
        e.x, e.y = x0 + 4.5, y0 + 0.5
    bot.fire = False
    pools = [h for h in w.hazards if h[4] == "jet"]
    near = [h for h in pools if math.hypot(h[0] - e.x, h[1] - e.y) < h[2] + e.r]
    for _ in range(60):
        g.update(1 / 60)
        e.x, e.y = x0 + 4.5, y0 + 0.5
    dealt = 1e6 - e.hp
    print("    %-10s puddles %d (%d under the knight), damage %.1f, burning %s, frozen %s" % (
        arch, len(pools), len(near), dealt, getattr(e, "burn", 0) > 0, getattr(e, "frozen", 0) > 0 or getattr(e, "chill", 0) > 0))
    check(near and dealt > 0, "%s splashes off the shield into a puddle that hurts the knight" % arch)

# weapon cards
for a, shell in (("shotgun_3", "sabot"), ("auto_shotgun", "dumdum")):
    p.weapons[p.cur] = make(a, shell)
    p.card_t = 3.0
    g.update(1 / 60)
    g.draw()
    pygame.image.save(g.screen, os.path.join(out, "card_%s_%s.png" % (a, shell)))

print("FAILED: %d" % len(fails) if fails else "all shotgun checks passed")
sys.exit(1 if fails else 0)

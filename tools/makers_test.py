"""Module manufacturers + forward / rear shields.
python tools/makers_test.py <outdir>"""
import os
import sys
import math
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SKULLS_SAVE"] = os.devnull        # never touch the player's save.json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import weapons as WP  # noqa: E402
import support as SU  # noqa: E402
from world import Enemy, Proj, Loot  # noqa: E402
from assets import to_screen  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(5)
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


def fresh(depth=2):
    g.new_world(depth)
    g.state = "play"
    g.banner = ("", 0)
    w = g.world
    w.traps, w.enemies, w.spawners, w.bosses, w.loot = [], [], [], [], []
    w.shootables = []
    L = w.level
    best = None
    for rad in (5, 4, 3, 2):
        for y in range(6, L.H - 6):
            for x in range(6, L.W - 6):
                if all(not L.is_solid(x + i, y + j) for i in range(-rad, rad + 1) for j in range(-rad, rad + 1)):
                    best = (x + 0.5, y + 0.5)
                    break
            if best:
                break
        if best:
            break
    p = w.player
    p.x, p.y = best
    # carve a clean 17x17 arena so line-of-sight checks don't depend on the random map
    cx, cy = int(best[0]), int(best[1])
    ftile = L.floor[L.i(cx, cy)]
    for x in range(max(1, cx - 8), min(L.W - 1, cx + 9)):
        for y in range(max(1, cy - 8), min(L.H - 1, cy + 9)):
            i = L.i(x, y)
            L.solid[i] = 0
            L.floor[i] = L.floor[i] or ftile
    L.props = {k: v for k, v in L.props.items() if abs(k[0] - cx) > 8 or abs(k[1] - cy) > 8}
    w.barrels, w.crates = {}, {}
    g.floor_layer.chunks.clear()
    L.exit = (-50.0, -50.0)       # no accidental sector change mid-test
    p.invuln = 0
    g.cam = list(g.cam_target())
    return w, p, L


def mon(w, x, y, hp=1e6):
    e = Enemy("zombie", x, y, awake=True, depth=1)
    e.hp = hp
    w.enemies.append(e)
    return e



def aim_at(dx, dy):
    a, b = to_screen(dx, dy)
    a0, b0 = to_screen(0, 0)
    bot.aim = ((a - a0) * 10, (b - b0) * 10)


# ---------------------------------------------------------------- makers
print("makers")
counts, bad_line, bad_tier, no_maker = {}, 0, 0, 0
for i in range(6000):
    rng = random.Random(i)
    m = SU.generate(rng.randint(1, 9), rng)
    if m.kind == "barrel":
        check_ = m.maker is None
        if not check_:
            bad_line += 1
        continue
    if m.maker is None:
        no_maker += 1
        continue
    M_ = SU.MAKERS[m.maker]
    counts[m.maker] = counts.get(m.maker, 0) + 1
    if M_["lines"] != "all" and not (M_["lines"] & SU.LINES[m.kind]):
        bad_line += 1
    if M_["tier"] > m.rarity:
        bad_tier += 1
check(no_maker == 0, "every module except barrels has a maker (%d without)" % no_maker)
check(bad_line == 0, "makers only build modules in their lines (%d wrong)" % bad_line)
check(bad_tier == 0, "top-tier houses only on top-tier modules (%d wrong)" % bad_tier)
print("    " + ", ".join("%s %d" % kv for kv in sorted(counts.items(), key=lambda kv: -kv[1])))
check(len(counts) >= 13, "most makers turn up (%d of %d)" % (len(counts), len(SU.MAKERS)))

# the lean moves each number the right way: compare the same seed built with and without its maker
real = SU.makers_for
wrong = 0
for kind in [k for k in SU.KINDS if k != "barrel"]:
    for s in range(30):
        m = SU.Support(kind, 1, 3, s)
        SU.makers_for = lambda k, r: []
        base = SU.Support(kind, 1, 3, s)
        SU.makers_for = real
        for name, (lo, hi, _, _) in SU.KINDS[kind]["params"].items():
            q = SU.QUALITY.get(name) or ("reach" if name == "size" and kind in SU.SHIELDS | {"sawbot"} else None)
            f = m.lean.get(q, 1.0) if q else 1.0
            if f == 1.0 or name in SU.INT or name == "arc":
                continue
            better = (m.p[name] > base.p[name]) == (hi >= lo)
            if better != (f > 1):
                wrong += 1
check(wrong == 0, "maker leans push every stat the right way (%d wrong)" % wrong)
useless = 0
for kind in [k for k in SU.KINDS if k != "barrel"]:
    for name, _ in SU.makers_for(kind, 2):
        M_ = SU.MAKERS[name]
        if not M_["wild"] and not any(v > 1 and q in SU.qualities_of(kind) for q, v in M_["lean"].items()):
            useless += 1
check(useless == 0, "no maker builds a module its strengths don't apply to")

# ---------------------------------------------------------------- forward / rear shields
print("forward / rear shields")


def shots_from(kind, frames=60 * 6):
    """Shoot at the player from 16 directions while they aim +x; count what the shield stops, per side."""
    w, p, L = fresh()
    sh = SU.generate(2, random.Random(4), kind=kind, rarity=1)
    p.give(sh)
    sh.p["capacity"] = sh.charge = 999
    p.hp = p.max_hp = 1e6
    aim_at(1, 0)
    stats = {"front": [0, 0], "back": [0, 0]}
    live = []                         # (shot, side): holding the shots keeps their ids from being reused
    home = (p.x, p.y)
    for f in range(frames):
        p.x, p.y = home                   # pinned: knockback would let later shots slip past the side
        p.kbx = p.kby = 0.0
        if f % 8 == 0:
            a = (f // 8) * math.tau / 16
            pr = Proj("orb", p.x + math.cos(a) * 4, p.y + math.sin(a) * 4, 1.0, -math.cos(a) * 9, -math.sin(a) * 9, 5,
                      hostile=True, life=3, color=(255, 80, 60), r=0.13)
            pr.effect = None
            w.projs.append(pr)
            side = "front" if math.cos(a) > 0.6 else ("back" if math.cos(a) < -0.6 else None)
            if side:
                stats[side][1] += 1
                live.append((pr, side))
        g.update(1 / 60)
        for pr, side in list(live):
            if id(pr) in w.blocked:
                stats[side][0] += 1
            if pr not in w.projs:
                live.remove((pr, side))
        p.invuln = 0
        if f == 100:
            g.draw()
            pygame.image.save(g.screen, os.path.join(out, "%s.png" % kind))
    return sh, stats


for kind, good in (("shield_front", "front"), ("shield_rear", "back")):
    sh, st = shots_from(kind)
    other = "back" if good == "front" else "front"
    print("    %-12s arc %d deg: stopped %d/%d shots from the %s, %d/%d from the %s" % (
        kind, math.degrees(sh.p["arc"]), st[good][0], st[good][1], good, st[other][0], st[other][1], other))
    check(st[good][0] >= 0.8 * st[good][1] and st[other][0] == 0, "%s stops shots from the %s only" % (kind, good))


def claw(kind, from_dx):
    w, p, L = fresh()
    sh = SU.generate(2, random.Random(4), kind=kind, rarity=1)
    p.give(sh)
    aim_at(1, 0)
    g.update(1 / 60)
    p.hp = p.max_hp = 100
    p.invuln = 0
    c0 = sh.charge
    w.hurt_player(16, p.x + from_dx, p.y, who=p)
    return 100 - p.hp, c0 - sh.charge


for kind, blocked_side in (("shield_front", 1), ("shield_rear", -1)):
    lost_b, used_b = claw(kind, blocked_side * 0.8)
    lost_o, used_o = claw(kind, -blocked_side * 0.8)
    print("    %-12s claw from its side: player lost %.0f (shield spent %d); from the other side lost %.0f" % (kind, lost_b, used_b, lost_o))
    check(lost_b == 0 and used_b >= 1 and lost_o > 0, "%s takes claws on its side and only there" % kind)

# overload: a few hits drop it, it reboots after its timer
w, p, L = fresh()
sh = SU.generate(2, random.Random(4), kind="shield_front", rarity=1)
p.give(sh)
aim_at(1, 0)
g.update(1 / 60)
sh.charge = 2
for k in range(3):
    p.invuln = 0
    w.hurt_player(10, p.x + 0.8, p.y, who=p)
check(sh.down > 0, "forward shield overloads when its blocks run out")
for _ in range(int(sh.p["recharge"] * 60) + 10):
    g.update(1 / 60)
check(sh.down <= 0 and sh.charge == sh.p["capacity"], "and comes back after its reboot (%.1fs)" % sh.p["recharge"])

# explosions are not stopped
w, p, L = fresh()
sh = SU.generate(2, random.Random(4), kind="shield_front", rarity=1)
p.give(sh)
aim_at(1, 0)
g.update(1 / 60)
p.hp = p.max_hp = 100
p.invuln = 0
w.hurt_player(20, p.x + 0.8, p.y, who=p, dtype="explosive")
check(p.hp < 100, "blasts still get through a forward shield")

# cards
for kind in ("shield_front", "shield_rear", "gunbot"):
    w, p, L = fresh()
    m = SU.generate(4, random.Random(11), kind=kind, rarity=2)
    g.draw()
    g.support_card(g.screen, m, 40, 40)
    pygame.image.save(g.screen, os.path.join(out, "card_%s.png" % kind))
    print("    card %-12s %s by %s: %s" % (kind, m.name, m.maker, SU.maker_summary(m.lean, m.kind)))

print("FAILED: %s" % (fails or "none"))
sys.exit(1 if fails else 0)

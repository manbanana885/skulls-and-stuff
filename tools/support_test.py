"""Support gadgets + barrage / coil / microwave guns, exercised headless with numbers and screenshots.
python tools/support_test.py <outdir>"""
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
    c, d = to_screen(0, 0)
    bot.aim = ((a - c) * 10, (b - d) * 10)


def run(sec, pin=(), shot=None, at=None):
    frames = int(sec * 60)
    for f in range(frames):
        for e, (x, y) in pin:
            e.x, e.y, e.vx, e.vy = x, y, 0, 0
            e.lunge = 0
        g.update(1 / 60)
        if shot and f == (at if at is not None else frames // 2):
            g.draw()
            pygame.image.save(g.screen, os.path.join(out, shot + ".png"))


def frozen_monsters(w, spots):
    ms = [mon(w, x, y) for x, y in spots]
    return ms, [(m, (m.x, m.y)) for m in ms]


# ================================================================ support gadgets
print("== support gadgets")
for kind in SU.KINDS:
    for rar in (0, 4):
        s = SU.generate(3, random.Random(rar * 7 + len(kind)), kind=kind, rarity=rar)
        print("  %-28s %s" % (s.name, "  ".join("%s %s" % kv for kv in s.card_lines())))

# sawbot
w, p, L = fresh()
sb = SU.generate(2, random.Random(1), kind="sawbot", rarity=2)
p.give(sb)
r = sb.radius()
ms, pin = frozen_monsters(w, [(p.x + math.cos(a) * r, p.y + math.sin(a) * r) for a in (0.3, 2.4, 4.4)])
p.hp = p.max_hp = 1e6
run(4, pin, "sup_sawbot")
dmg = [round(1e6 - m.hp) for m in ms]
print("  sawbot  orbit %.2f spin %.1f dmg/hit %.1f -> 3 monsters on the ring took %s in 4s" % (r, sb.p["spin"], sb.p["dmg"], dmg))
check(all(d > 0 for d in dmg), "sawbot hits every monster on its orbit")

# shield: enemy shots from every direction
w, p, L = fresh()
sh = SU.generate(2, random.Random(2), kind="shield", rarity=4)
p.give(sh)
sh.p["capacity"] = sh.charge = 999
p.hp = p.max_hp = 1e6
blocked = hits = fired = 0
rng = random.Random(3)
for f in range(60 * 8):
    if f % 6 == 0:
        a = rng.random() * math.tau
        pr = Proj("orb", p.x + math.cos(a) * 4, p.y + math.sin(a) * 4, 1.0, -math.cos(a) * 9, -math.sin(a) * 9, 5, hostile=True,
                  life=3, color=(255, 80, 60), r=0.13)
        w.projs.append(pr)
        fired += 1
    hp0 = p.hp
    p.invuln = 0
    g.update(1 / 60)
    blocked += len(w.blocked)
    hits += hp0 > p.hp
    if f == 200:
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "sup_shield.png"))
expect = sh.p["arc"] / math.tau
print("  shield  arc %d deg: blocked %d / %d shots (%.0f%%, arc covers %.0f%% of the circle), %d reached the player"
      % (math.degrees(sh.p["arc"]), blocked, fired, 100 * blocked / fired, 100 * expect, hits))
check(blocked > 0.6 * expect * fired, "shield intercepts shots in proportion to its arc")
# overload + recharge
w.projs = []
run(sh.p["recharge"] + 0.5)
sh.p["capacity"] = 3
sh.charge = 3
sh.p["spin"] = 0
eaten = 0
for k in range(3):
    a = sh.ang
    w.projs.append(Proj("orb", p.x + math.cos(a) * 2.5, p.y + math.sin(a) * 2.5, 1.0, -math.cos(a) * 9, -math.sin(a) * 9, 5,
                        hostile=True, life=3, r=0.13))
    for f in range(40):
        g.update(1 / 60)
        eaten += len(w.blocked)
        if w.blocked:
            break
check(eaten == 3 and sh.down > 0, "shield overloads after its capacity is spent (ate %d, down for %.1fs)" % (eaten, sh.down))
run(sh.p["recharge"] + 0.2)
check(sh.down <= 0 and sh.charge == 3, "shield comes back fully charged after recharge")

# medbot
w, p, L = fresh()
md = SU.generate(2, random.Random(4), kind="medbot", rarity=1)
p.give(md)
p.hp = 40
bot.move = (0.6, 0.2)
run(5, shot="sup_medbot", at=200)
bot.move = (0.0, 0.0)
run(5)
gain = p.hp - 40
print("  medbot  heal %.2f/s -> +%.1f integrity in 10s while walking, bot %.1f tiles from player"
      % (md.p["heal"], gain, math.hypot(md.x - p.x, md.y - p.y)))
check(gain > md.p["heal"] * 10 * 0.7, "medbot heals slowly while following")
check(math.hypot(md.x - p.x, md.y - p.y) < md.p["reach"], "medbot keeps up with the player")

# gun drone
w, p, L = fresh()
gb = SU.generate(2, random.Random(5), kind="gunbot", rarity=2)
p.give(gb)
ms, pin = frozen_monsters(w, [(p.x + 3.5, p.y + 0.5), (p.x - 1, p.y + 3.2)])
run(4, pin, "sup_gunbot")
dmg = [round(1e6 - m.hp, 1) for m in ms]
print("  gunbot  dmg %.1f rate %.1f/s -> monsters took %s in 4s" % (gb.p["dmg"], gb.p["rate"], dmg))
check(sum(dmg) > gb.p["dmg"] * gb.p["rate"] * 4 * 0.5, "gun drone shoots monsters")

# pickup / swap through the loot system
w, p, L = fresh()
a = SU.generate(2, random.Random(6), kind="medbot")
b_ = SU.generate(2, random.Random(7), kind="sawbot")
w.loot = [Loot("support", p.x + 0.3, p.y, a)]
bot.pressed = {"interact"}
g.update(1 / 60)
bot.pressed = set()
check(p.gear[0] is a and not w.loot, "picking up a module with a free slot equips it")
w.loot = [Loot("support", p.x + 0.3, p.y, b_)]
bot.pressed = {"interact"}
g.update(1 / 60)
bot.pressed = set()
check(p.gear[1] is b_ and not w.loot, "a second module goes into the next free slot")
# fill all module slots + the backpack, then one more swaps with slot 1
import world as WD  # noqa: E402
for k in range(WD.GEAR_SLOTS - 2 + WD.PACK_SIZE):
    w.loot = [Loot("support", p.x + 0.3, p.y, SU.generate(2, random.Random(100 + k)))]
    bot.pressed = {"interact"}
    g.update(1 / 60)
    bot.pressed = set()
check(all(p.gear) and len(p.pack) == WD.PACK_SIZE, "slots fill first, then the backpack (gear %d, pack %d)" % (len(p.equipped()), len(p.pack)))
extra = SU.generate(2, random.Random(200))
first = p.gear[0]
w.loot = [Loot("support", p.x + 0.3, p.y, extra)]
bot.pressed = {"interact"}
g.update(1 / 60)
bot.pressed = set()
check(p.gear[0] is extra and len(w.loot) == 1 and w.loot[0].item is first, "with everything full, a pickup swaps with slot 1")
# pause-menu inventory: unequip, equip from pack (swap by column), drop
g.state = "pause"
p.pack.pop()                      # make room to unequip
p.inv_cur = (1, 1)
geared = p.gear[1]
bot.pressed = {"confirm"}
g.update(1 / 60)
bot.pressed = set()
check(p.gear[1] is None and p.pack[-1] is geared, "confirm on a gear slot unequips into the backpack")
p.inv_cur = (0, 2)
want = p.pack[0]
bot.pressed = {"confirm"}
g.update(1 / 60)
bot.pressed = set()
check(p.gear[1] is want, "confirm on a backpack item equips it into the free slot")
p.inv_cur = (2, 2)
victim = g.inv_item(p, 2, 2)
n_loot = len(w.loot)
bot.pressed = {"reload"}
g.update(1 / 60)
bot.pressed = set()
check(victim not in p.pack and len(w.loot) == n_loot + 1, "drop puts the module on the floor")
for name in ("nav_right", "nav_down"):
    bot.pressed = {name}
    g.update(1 / 60)
bot.pressed = set()
check(p.inv_cur == (3, 3), "cursor moves with the navigation keys (at %s)" % (p.inv_cur,))
# guns row: highlight the stowed gun and take it in hand
p.inv_cur = (0, 0)
held = p.cur
bot.pressed = {"nav_right"}
g.update(1 / 60)
bot.pressed = {"confirm"}
g.update(1 / 60)
bot.pressed = set()
check(p.cur != held and p.inv_cur == (1, 0), "pause menu: the guns row shows both guns and confirm swaps which is in hand")
g.draw()
pygame.image.save(g.screen, os.path.join(out, "inventory.png"))
g.state = "play"
g.draw()
pygame.image.save(g.screen, os.path.join(out, "sup_pickup_card.png"))
n_sup = 0
for d in range(1, 6):
    g.new_world(d)
    n_sup += sum(1 for lt in g.world.loot if lt.kind == "support")
print("  sectors 1-5 placed %d support pickups" % n_sup)
check(n_sup >= 5, "every sector has at least one support pickup")

# ================================================================ weapons
print("== new weapons")
for arch in ("barrage", "coil_pistol", "coil_rifle", "coil_heavy", "microwave", "carbine", "rocket", "chaingun"):
    ws = [WP.generate(1, random.Random(i), arch=arch, rarity=0) for i in range(30)]
    print("  %-12s dps %5.1f  (heavy x%.2f)" % (arch, sum(x.dps() for x in ws) / len(ws), ws[0].st["heavy"]))
salvos = sorted({WP.generate(1, random.Random(i), arch="barrage").st["salvo"] for i in range(200)})
check(salvos[0] == 4 and salvos[-1] == 16, "barrage salvos roll 4-16 missiles (saw %d-%d)" % (salvos[0], salvos[-1]))

# barrage
w, p, L = fresh()
wp = p.weapons[p.cur] = WP.generate(2, random.Random(9), arch="barrage", rarity=0)
ms, pin = frozen_monsters(w, [(p.x + 4.5 + (i % 3) * 0.6, p.y + (i // 3) * 0.8 - 0.4) for i in range(6)])
aim_at(1, 0)
p.hp = p.max_hp = 1e6
wp.cd = 0
bot.fire = True
g.update(1 / 60)
bot.fire = False
peak = 0
for f in range(150):
    for e, (x, y) in pin:
        e.x, e.y = x, y
    g.update(1 / 60)
    peak = max(peak, sum(1 for b in w.projs if b.kind == "missile"))
    if f == 16:
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "wpn_barrage.png"))
launched = p.salvo_n
dmg = round(sum(1e6 - m.hp for m in ms))
print("  barrage salvo %d -> launched %d missiles, %d in the air at once, %d total damage to the pack, player hp lost %d"
      % (wp.st["salvo"], launched, peak, dmg, 1e6 - p.hp))
check(launched == wp.st["salvo"], "one trigger pull launches the whole salvo")
check(dmg > 0, "missiles hit the pack")
# like rockets: point-blank into a wall tears it open and the blast hurts the shooter
w, p, L = fresh()
wp = p.weapons[p.cur] = WP.generate(2, random.Random(9), arch="barrage", rarity=0)
x0, y0 = int(p.x), int(p.y)
while not L.is_solid(x0 + 1, y0):
    x0 += 1
p.x = x0 + 1 - 0.3          # hugging the wall
walls0 = sum(L.solid)
p.hp = p.max_hp = 1000
aim_at(1, 0)
wp.cd = 0
bot.fire = True
g.update(1 / 60)
bot.fire = False
lost = 0
for f in range(150):
    hp0 = p.hp
    p.invuln = 0
    g.update(1 / 60)
    lost += max(0, hp0 - p.hp)
broke = walls0 - sum(L.solid)
print("  barrage point-blank into a wall: %d wall blocks destroyed, shooter lost %d integrity" % (broke, lost))
check(broke > 0, "barrage missiles destroy walls like rockets")
check(lost > 0, "barrage blasts hurt the shooter like rockets")

# coil: chains through a line of monsters, ricochets off a wall when nothing is in front
for arch in ("coil_pistol", "coil_rifle", "coil_heavy"):
    w, p, L = fresh()
    wp = p.weapons[p.cur] = WP.generate(2, random.Random(10), arch=arch, rarity=0)
    wp.st["spread"] = 0
    ms, pin = frozen_monsters(w, [(p.x + 2.5 + (i // 2) * 1.5, p.y + (0.8 if i % 2 else -0.6)) for i in range(8)])
    aim_at(1, -0.6 / 2.5)
    run(0.05, pin)          # let the monsters register in the spatial grid
    wp.cd = 0
    bot.fire = True
    g.update(1 / 60)
    bot.fire = False
    g.draw()
    pygame.image.save(g.screen, os.path.join(out, "wpn_%s.png" % arch))
    n_hit = sum(1 for m in ms if m.hp < 1e6)
    print("  %-11s chain %d: one bolt hit %d monsters" % (arch, wp.st["chain"], n_hit))
    check(n_hit == min(8, 1 + wp.st["chain"]), "%s chains through %d targets" % (arch, 1 + wp.st["chain"]))
# ricochet: stand next to a wall, shoot into it
w, p, L = fresh()
wp = p.weapons[p.cur] = WP.generate(2, random.Random(11), arch="coil_heavy", rarity=0)
wp.st["spread"] = 0
x0, y0 = int(p.x), int(p.y)
while not L.is_solid(x0 + 1, y0):
    x0 += 1
p.x = x0 + 0.5
aim_at(1, 0.35)
w.arcs = []
wp.cd = 0
bot.fire = True
g.update(1 / 60)
bot.fire = False
g.draw()
pygame.image.save(g.screen, os.path.join(out, "wpn_coil_ricochet.png"))
pts = w.arcs[0][0] if w.arcs else []
print("  coil ricochet: bolt path has %d points (bounce limit %d)" % (len(pts), wp.st["bounce"]))
check(len(pts) >= 3, "coil lightning bounces off walls")

# microwave: hits everything inside the cone, nothing outside it or behind a wall
w, p, L = fresh()
wp = p.weapons[p.cur] = WP.generate(2, random.Random(12), arch="microwave", rarity=0)
cone = wp.st["cone"]
mf = WP.MUZZLE["microwave"][0]
inside = [(2.0, 0.0), (3.5, 0.3), (4.5, -0.35), (3.0, cone * 0.9)]
outside = [(3.0, cone + 0.6), (2.5 + mf, math.pi)]
mf = WP.MUZZLE["microwave"][0]      # the rings grow from the muzzle
spots = [(p.x + mf + d * math.cos(a), p.y + d * math.sin(a)) for d, a in inside + outside]
ms, pin = frozen_monsters(w, spots)
aim_at(1, 0)
wp.cd = 0
bot.fire = True
g.update(1 / 60)
bot.fire = False
run(0.9, pin, "wpn_microwave", at=20)
hit_in = sum(1 for m in ms[:len(inside)] if m.hp < 1e6)
hit_out = sum(1 for m in ms[len(inside):] if m.hp < 1e6)
print("  microwave cone %d deg: %d/%d inside hit, %d/%d outside hit" % (math.degrees(cone * 2), hit_in, len(inside), hit_out, len(outside)))
check(hit_in == len(inside) and hit_out == 0, "microwave rings hit the whole cone and only the cone")

# whole-game soak with every new toy: random sectors, bot firing everything
print("== soak")
errs = 0
import traceback  # noqa: E402
for d, arch, kind in ((1, "barrage", "sawbot"), (3, "coil_heavy", "shield"), (5, "microwave", "medbot"), (7, "coil_rifle", "gunbot")):
    main.biome_for = lambda d_, s_, b=("facility", "castle", "hell", "sewer")[d % 4]: b
    try:
        g.new_world(d)
        g.state = "play"
        w = g.world
        p = w.player
        p.hp = p.max_hp = 1e6
        p.weapons[p.cur] = WP.generate(d, arch=arch, rarity=3)
        for k_ in range(3):
            p.give(SU.generate(d, kind=kind if k_ == 0 else None, rarity=3))
        bot.fire = True
        for f in range(60 * 12):
            bot.move = (math.cos(f / 50), math.sin(f / 70))
            bot.aim = (math.cos(f / 30) * 300, math.sin(f / 30) * 300)
            g.update(1 / 60)
            if f % 5 == 0:
                g.draw()
        pygame.image.save(g.screen, os.path.join(out, "soak_%s_%s.png" % (arch, kind)))
        print("  sector %d %s + %s: kills %d" % (d, arch, kind, w.kills))
    except Exception:
        traceback.print_exc()
        errs += 1
bot.fire = False
check(errs == 0, "soak runs without errors")
print()
print("FAILED:", fails if fails else "none")

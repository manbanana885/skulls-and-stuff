"""Playable characters, falling-hazard warnings and deployable turrets.
python tools/characters_test.py <outdir>"""
import os
import sys
import json
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
import characters as CH  # noqa: E402
import traps as TR  # noqa: E402
from world import Enemy  # noqa: E402
from assets import to_screen  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(6)
g = main.Game(windowed=True)
g.save_settings = lambda: None            # never touch the real save.json from a test


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


def press(*names, frames=1):
    bot.pressed = set(names)
    g.update(1 / 60)
    bot.pressed = set()
    for _ in range(frames - 1):
        g.update(1 / 60)


def fresh(char="skelebot", depth=2):
    g.chars = [char, "canbot"]
    g.inputs = [bot]
    g.new_world(depth)
    g.state = "play"
    g.banner = ("", 0)
    w = g.world
    w.traps, w.enemies, w.spawners, w.bosses, w.loot, w.shootables = [], [], [], [], [], []
    L = w.level
    p = w.player
    cx, cy = int(L.start[0]), int(L.start[1])
    for x in range(max(1, cx - 9), min(L.W - 1, cx + 10)):
        for y in range(max(1, cy - 9), min(L.H - 1, cy + 10)):
            i = L.i(x, y)
            L.solid[i] = 0
            L.floor[i] = L.floor[i] or L.floor[L.i(cx, cy)]
    L.props = {}
    w.barrels, w.crates = {}, {}
    L.exit = (-50.0, -50.0)
    g.floor_layer.chunks.clear()
    p.x, p.y = cx + 0.5, cy + 0.5
    p.invuln = 0
    g.cam = list(g.cam_target())
    bot.move, bot.aim, bot.fire = (0.0, 0.0), None, False
    return w, p, L


# ---------------------------------------------------------------- characters
print("== characters")
for ch in CH.ORDER:
    C = CH.CHARS[ch]
    missing = [a for a in WP.ARCH if (C["torso"] + a) not in g.spr]
    check(C["legs"] in g.spr and not missing, "%s has legs and a torso for every gun (missing %s)" % (ch, missing))
speeds = {}
for ch in CH.ORDER:
    w, p, L = fresh(ch)
    x0 = p.x
    bot.move = (1.0, 0.0)
    for _ in range(30):
        g.update(1 / 60)
    bot.move = (0.0, 0.0)
    speeds[ch] = math.hypot(p.x - x0, p.y - (L.start[1] + 0.5)) * 2
    print("  %-9s integrity %3d  speed %.2f tiles/s  category %s" % (ch, p.max_hp, speeds[ch], p.cat))
    g.draw()
    pygame.image.save(g.screen, os.path.join(out, "char_%s.png" % ch))
check(abs(speeds["canbot"] / speeds["skelebot"] - 0.8) < 0.05 and abs(speeds["mutant"] / speeds["skelebot"] - 1.2) < 0.05,
      "CanBot moves 20% slower, Super Mutant 20% faster")
check([CH.CHARS[c]["hp"] for c in CH.ORDER] == [1.0, 1.2, 0.8], "integrity: Skelebot 100, CanBot 120, Super Mutant 80")


def taken(ch, dtype):
    w, p, L = fresh(ch)
    p.hp = p.max_hp = 1000
    w.hurt_player(10, p.x + 1, p.y, who=p, dtype=dtype)
    return 1000 - p.hp


tbl = {ch: {t: taken(ch, t) for t in ("kinetic", "electrical", "fire", "chemical")} for ch in CH.ORDER}
for ch in CH.ORDER:
    print("  %-9s takes from a 10-point hit: %s" % (ch, "  ".join("%s %.1f" % kv for kv in tbl[ch].items())))
check(tbl["canbot"]["electrical"] > tbl["canbot"]["kinetic"] and tbl["mutant"]["chemical"] < tbl["mutant"]["kinetic"]
      and tbl["skelebot"]["fire"] > tbl["skelebot"]["kinetic"], "players feel their category's weaknesses (softened)")

# per-body hit / death / movement feedback
import sfx as SFX  # noqa: E402
played = []
loops = {}
_play, _loop = SFX.play, SFX.loop
SFX.play = lambda name, vol=1.0: played.append(name)
SFX.loop = lambda name, on, vol=1.0: loops.__setitem__(name, on)
for ch in CH.ORDER:
    w, p, L = fresh(ch)
    played.clear()
    g0 = len(w.gibs)
    p.hp = p.max_hp = 1000
    for k in range(6):
        p.invuln = 0
        w.hurt_player(5, p.x + 1, p.y)
    chips = {gb.sprite for gb in w.gibs[g0:]}
    bot.move = (1.0, 0.0)
    for _ in range(40):
        g.update(1 / 60)
    tread_on = loops.get("tread_loop", False)
    bot.move = (0.0, 0.0)
    for _ in range(5):
        g.update(1 / 60)
    tread_after = loops.get("tread_loop", False)
    steps = [n_ for n_ in played if n_.startswith("step")]
    p.hp = 0
    p.alive = True
    w.check_player_death(p.x + 1, p.y, p)
    C = CH.CHARS[ch]
    print("  %-9s hit sound %s, chips %s, steps %s, tread loop moving/stopped %s/%s, death %s" % (
        ch, C["hurt"] in played, sorted(chips), sorted(set(steps)), tread_on, tread_after, C["death"] in played))
    ok = C["hurt"] in played and chips and chips <= set(C["chips"]) and C["death"] in played
    if ch == "canbot":
        ok = ok and tread_on and not tread_after and not steps
    else:
        ok = ok and steps and set(steps) == {C["step"]} and not tread_on
    check(bool(ok), "%s has its own hit sound, debris, movement sound and death" % ch)
SFX.play, SFX.loop = _play, _loop

# title screen: pick characters
g.state = "title"
g.chars = ["skelebot", "canbot"]
g.inputs = [bot]
press("nav_right")
check(g.chars[0] == "canbot", "LEFT / RIGHT on the title screen picks a body (now %s)" % g.chars[0])
g.draw()
pygame.image.save(g.screen, os.path.join(out, "title_select.png"))
press("nav_right")
press("start")
check(g.state == "play" and g.world.player.char == "mutant", "starting a run uses the picked body (%s)" % g.world.player.char)
p2 = g.world.add_player()
check(p2.char != g.world.player.char, "a joining P2 gets a different body by default (%s)" % p2.char)

# ---------------------------------------------------------------- falling hazards
print("== falling hazards")
w, p, L = fresh()
st = TR.Strikes("icicle", 3)
w.traps = [st]
st.next = 0.0
g.update(1 / 60)
check(st.pending and abs(st.pending[0][2] - TR.STRIKE_WARN) < 0.05, "strikes give %.1fs warning (was 1.2s)" % TR.STRIKE_WARN)
seen = 0.0
for f in range(150):
    if st.falling():
        seen += 1 / 60
    if f == 100:
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "strike_warning.png"))
    g.update(1 / 60)
    st.next = 99
check(0.6 < seen < 1.0, "the falling object is visible for the last %.2fs" % seen)

# ---------------------------------------------------------------- turrets
print("== turrets")
w, p, L = fresh()
mg = SU.generate(2, random.Random(3), kind="mgturret", rarity=2)
p.give(mg)
p.aim = (1.0, 0.0)
press("deploy")
check(mg.deployed is not None and w.turrets, "F / B deploys the MG turret")
tr = mg.deployed
e = Enemy("zombie", tr.x + 5, tr.y + 0.5, awake=True, depth=1)
e.hp = 1e6
w.enemies = [e]
for f in range(120):
    e.x, e.y, e.vx, e.vy = tr.x + 5, tr.y + 0.5, 0, 0
    g.update(1 / 60)
    if f == 60:
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "turret_mg.png"))
check(1e6 - e.hp > 0, "MG turret shoots monsters (dealt %.1f)" % (1e6 - e.hp))
p.x, p.y = tr.x + 8, tr.y
e.x, e.y = tr.x - 1.5, tr.y
g.update(1 / 60)
check(e.target is tr, "a monster closer to the turret than to you goes after the turret")
hp0 = tr.hp
w.hurt_player(10, tr.x - 0.8, tr.y)
check(tr.hp < hp0, "monster hits land on the turret (%d -> %d)" % (hp0, tr.hp))
w.enemies = []
p.x, p.y = tr.x + 1, tr.y
press("deploy")
check(mg.deployed is None and not w.turrets, "pressing again next to it packs it up")
press("deploy")
check(mg.deployed is not None, "and it deploys again")

# destruction: nuke-like, walls broken, nearby player hurt, rebuild timer
tr = mg.deployed
p.x, p.y = tr.x + 1.5, tr.y
p.hp = p.max_hp = 1000
p.invuln = 0
for dx in (-3, -2):                         # a little wall block next to it
    L.solid[L.i(int(tr.x) + dx, int(tr.y))] = 1
walls0 = sum(1 for dx in range(-4, 5) for dy in range(-4, 5) if L.solid[L.i(int(tr.x) + dx, int(tr.y) + dy)])
tr.hit(w, 1e6)
walls1 = sum(1 for dx in range(-4, 5) for dy in range(-4, 5) if L.solid[L.i(int(tr.x) + dx, int(tr.y) + dy)])
for _ in range(3):
    g.update(1 / 60)
g.draw()
pygame.image.save(g.screen, os.path.join(out, "turret_boom.png"))
print("  destroyed turret: walls nearby %d -> %d, player lost %.0f, rebuild %.0fs" % (walls0, walls1, 1000 - p.hp, mg.rebuild_t))
check(walls1 < walls0 and p.hp < 1000 and mg.rebuild_t > 0 and mg.deployed is None,
      "a destroyed turret blows like a tac-nuke: breaks walls, hurts you, then needs rebuilding")
press("deploy")
check(mg.deployed is None, "can't redeploy while rebuilding")

# mortar: lobs over walls
w, p, L = fresh()
mo = SU.generate(2, random.Random(4), kind="mortar", rarity=2)
p.give(mo)
p.aim = (1.0, 0.0)
press("deploy")
tr = mo.deployed
for dy in range(-3, 4):
    L.solid[L.i(int(tr.x) + 3, int(tr.y) + dy)] = 1
g.floor_layer.chunks.clear()
e = Enemy("zombie", tr.x + 6, tr.y, awake=True, depth=1)
e.hp = 1e6
w.enemies = [e]
for f in range(300):
    e.x, e.y, e.vx, e.vy = tr.x + 6, tr.y, 0, 0
    g.update(1 / 60)
    if f == 75:
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "turret_mortar.png"))
check(1e6 - e.hp > 0, "mortar lobs shells over a wall onto a monster (dealt %.1f)" % (1e6 - e.hp))

# soak: each body with turrets, random fights
errs = 0
import traceback  # noqa: E402
for ch, biome in (("canbot", "castle"), ("mutant", "hell")):
    main.biome_for = lambda d_, s_, b=biome: b
    g.chars = [ch, "skelebot"]
    g.new_world(4)
    g.state = "play"
    w = g.world
    p = w.player
    p.hp = p.max_hp = 1e6
    p.give(SU.generate(4, kind="mgturret", rarity=3))
    p.give(SU.generate(4, kind="mortar", rarity=3))
    bot.fire = True
    try:
        for f in range(60 * 10):
            bot.move = (math.cos(f / 50), math.sin(f / 70))
            bot.aim = (math.cos(f / 30) * 300, math.sin(f / 30) * 300)
            bot.pressed = {"deploy"} if f % 150 == 10 else set()
            g.update(1 / 60)
            p.hp = max(p.hp, 1e5)
            if f % 5 == 0:
                g.draw()
        pygame.image.save(g.screen, os.path.join(out, "soak_%s.png" % ch))
        print("  soak %s in %s: kills %d" % (ch, biome, w.kills))
    except Exception:
        traceback.print_exc()
        errs += 1
bot.fire = False
check(errs == 0, "soak with each body and turrets runs without errors")
print()
print("FAILED:", fails if fails else "none")

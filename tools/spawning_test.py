"""Room populations, spawning stations and off-screen restocking. python tools/spawning_test.py [outdir]"""
import os
import sys
import math
import random
from collections import Counter

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
import spawning as SP  # noqa: E402
from biomes import BIOMES  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")
os.makedirs(out, exist_ok=True)
random.seed(3)
W.rnd.seed(3)
fails = []


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        fails.append(msg)


# ---- levels
avg = {}
for d in (1, 5, 10):
    n = [len(LV.Level(d, s, random.Random(s).choice(list(BIOMES))).enemies) for s in range(12)]
    avg[d] = sum(n) / len(n)
check(avg[1] < avg[5] < avg[10], "rooms fill up as you go deeper (avg %.0f / %.0f / %.0f monsters at sectors 1 / 5 / 10)"
      % (avg[1], avg[5], avg[10]))

native_share = {}
for b in ("biotech", "gluttony", "heresy", "castle", "nuclear", "lust"):
    sig = set(BIOMES[b]["signature"])
    ks = [k for s in range(6) for k, _, _ in LV.Level(5, s, b).enemies]
    native_share[b] = sum(1 for k in ks if k in sig) / max(1, len(ks))
check(all(v > 0.3 for v in native_share.values()), "biomes are mostly their own monsters (%s)"
      % ", ".join("%s %.0f%%" % (b, v * 100) for b, v in native_share.items()))
check(any(k == "specimen" for s in range(4) for k, _, _ in LV.Level(4, s, "biotech").enemies),
      "biome natives that weren't in the shared table now turn up (specimens in the biotech labs)")

# arrangement: shooters stand further from the doorways than brawlers
ranged_d, melee_d = [], []
for s in range(10):
    L = LV.Level(6, s, "castle")
    for (k, x, y), ri in zip(L.enemies, L.enemy_rooms):
        r = L.rooms[ri]
        ents = [(cx, cy) for cx in range(r.x - 1, r.x + r.w + 1) for cy in (r.y - 1, r.y + r.h)] + \
               [(cx, cy) for cy in range(r.y, r.y + r.h) for cx in (r.x - 1, r.x + r.w)]
        ents = [c for c in ents if 0 <= c[0] < L.W and 0 <= c[1] < L.H and L.solid[L.i(*c)] == 0]
        if not ents:
            continue
        dd = min(abs(int(x) - c[0]) + abs(int(y) - c[1]) for c in ents)
        (ranged_d if SP.role(k) == "ranged" else melee_d if SP.role(k) == "melee" else []).append(dd)
check(ranged_d and melee_d and sum(ranged_d) / len(ranged_d) > sum(melee_d) / len(melee_d),
      "shooters hang back from the doorways (%.1f tiles) behind the brawlers (%.1f)"
      % (sum(ranged_d) / max(1, len(ranged_d)), sum(melee_d) / max(1, len(melee_d))))

# rooms hold one coherent group: a single damage category dominates most rooms
import damage as DM  # noqa: E402
coh = []
for s in range(8):
    L = LV.Level(5, s, "facility")
    rooms = {}
    for (k, _, _), ri in zip(L.enemies, L.enemy_rooms):
        rooms.setdefault(ri, []).append(DM.category(k))
    for cats in rooms.values():
        if len(cats) >= 3:
            coh.append(Counter(cats).most_common(1)[0][1] / len(cats))
check(sum(coh) / len(coh) > 0.6, "rooms hold a group of one kind of thing (top category %.0f%% of a room on average)"
      % (sum(coh) / len(coh) * 100))

# stations
sts = Counter()
fam_ok = True
for s in range(60):
    d = 2 + s % 10
    L = LV.Level(d, s, random.Random(s).choice(list(BIOMES)))
    check_n = len(L.spawners) <= SP.max_stations(d)
    fam_ok = fam_ok and check_n
    for st, x, y, kinds in L.spawners:
        sts[st] += 1
        fam_ok = fam_ok and kinds and all(k in SP.STATIONS[st] for k, _ in kinds)
check(fam_ok and len(sts) >= 5, "stations breed only their own family, a few per sector at most (%s)" % dict(sts))
check(all(os.path.isdir(os.path.join(ROOT, "assets", "sprites", "st_" + st)) for st in SP.STATIONS), "every station has a sprite")

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


def new(depth, biome, seed=None):
    main.biome_for = lambda d, s_: biome
    g.new_world(depth)
    g.state = "play"
    g.banner = ("", 0)
    return g.world, g.world.player


def tick(n):
    for _ in range(n):
        g.update(1 / 60)
        for p in g.world.players:
            p.hp, p.alive = p.max_hp, True


# a station breeds its family while you're close
found = None
for tries in range(40):
    w, p = new(4 + tries % 6, random.Random(tries).choice(["gluttony", "ossuary", "biotech", "hell", "nuclear", "facility"]))
    if w.spawners:
        found = w.spawners[0]
        break
check(found is not None, "sectors get spawning stations")
s = found
w.enemies = []
w.bosses = []
w.traps = []
p.x, p.y = W.resolve(w.level, s.x + 3, s.y, p.R)
if w.level.is_solid(int(p.x), int(p.y)):
    p.x, p.y = s.x + 1.2, s.y
s.cd = 0
tick(60 * 25)
brood = [e for e in w.enemies if e.owner is s]
check(brood and all(e.kind in SP.STATIONS[s.station] for e in brood) and s.children <= 3,
      "the %s bred %d of its family (%s)" % (s.station, len(brood), ", ".join(sorted({e.kind for e in brood}))))
g.draw()
pygame.image.save(g.screen, os.path.join(out, "station_%s.png" % s.station))
s.hit(w, 1e4)
check(not s.alive and not w.level.solid[w.level.i(int(s.x), int(s.y))], "shooting the %s shuts it down" % s.station)
tick(30)

# every station draws
w, p = new(5, "facility")
w.enemies, w.bosses, w.traps = [], [], []
w.spawners = []
for k, st in enumerate(SP.STATIONS):
    sx, sy = p.x + 1.5 * (k - 2.5), p.y - 2.5
    w.spawners.append(W.Spawner(st, sx, sy, 5, [(SP.STATIONS[st][0], 1.0)]))
tick(2)
g.draw()
pygame.image.save(g.screen, os.path.join(out, "stations_lineup.png"))
check(True, "all six stations draw")

# off-screen restocking
w, p = new(6, "castle")
w.spawners = []
w.bosses = []
w.traps, w.hazards = [], []          # hazards would wake (and hurt) whatever they restock
start_counts = Counter(e.room for e in w.enemies)
for e in w.enemies:                 # wipe the sector
    e.alive = False
w.enemies = []
far = [r for r in w.rooms if math.hypot(r["rect"][0] + r["rect"][2] / 2 - p.x, r["rect"][1] + r["rect"][3] / 2 - p.y)
       > W.TRICKLE_RANGE + max(r["rect"][2], r["rect"][3]) / 2]
near = [r for r in w.rooms if r not in far]
cleared = far[0] if far else None
if cleared:
    cleared["seen"] = cleared["cleared"] = True
n0 = len(w.enemies)
for _ in range(400):
    w.trickle_t = 0
    tick(1)
counts = Counter(e.room for e in w.enemies if e.alive)
check(len(w.enemies) > n0, "uncleared rooms out of range restock (%d monsters crept back)" % (len(w.enemies) - n0))
check(all(counts[r["idx"]] <= r["quota"] for r in w.rooms), "no room restocks past the headcount it started with")
check(cleared is None or counts[cleared["idx"]] == 0, "a cleared room stays clear")
check(all(counts[r["idx"]] == 0 for r in near), "nothing appears in rooms near the player")
check(all(not e.awake for e in w.enemies), "restocked monsters lie in wait rather than charging in")
mind = min(math.hypot(e.x - p.x, e.y - p.y) for e in w.enemies) if w.enemies else 99
check(mind > 12, "restocking happens out of sight (nearest %.0f tiles away)" % mind)

# rooms become cleared once you've been in and killed everything
w, p = new(3, "facility")
r = next(r for r in w.rooms if r["quota"] > 0)
rx, ry, rw, rh = r["rect"]
for e in w.enemies:
    if e.room == r["idx"]:
        e.alive = False
for s_ in w.spawners:
    if s_.room == r["idx"]:
        s_.alive = False
w.enemies = [e for e in w.enemies if e.alive]
for cx in range(rx, rx + rw):
    for cy in range(ry, ry + rh):
        if not w.level.is_solid(cx, cy):
            p.x, p.y = cx + 0.5, cy + 0.5
            break
    else:
        continue
    break
w._room_tick = 0
tick(3)
check(r["seen"] and r["cleared"], "a room you've stood in with nothing left alive counts as cleared")

# a populated sector at depth, for a look
w, p = new(7, "heresy")
tick(30)
g.draw()
pygame.image.save(g.screen, os.path.join(out, "heresy_start.png"))

print()
print("ALL PASSED" if not fails else "%d FAILED" % len(fails))
sys.exit(1 if fails else 0)

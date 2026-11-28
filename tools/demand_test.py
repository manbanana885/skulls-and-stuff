"""Demand modes (HIGH / MID / LOW): fewer monsters on lower modes, each tougher and angrier; the red crosshair.
python tools/demand_test.py [outdir]"""
import os
import sys
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SKULLS_SAVE"] = os.devnull
os.environ.pop("SKULLS_DEMAND", None)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import perf  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_demand_test")
os.makedirs(out, exist_ok=True)
fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


g = main.Game(windowed=True)
main.biome_for = lambda d, s: "facility"

# ---- monsters per mode, same level seeds
print("monsters per sector (depth 3, 6 seeds each)")
stats = {}
for mode in ("high", "mid", "low"):
    perf.local = mode
    n = hp = 0.0
    agg = spd = 0.0
    for seed in range(6):
        random.seed(seed)
        g.new_world(3)
        es = g.world.enemies
        n += len(es)
        hp += sum(e.hp for e in es)
        agg += sum(e.aggro for e in es) / max(1, len(es))
        spd += sum(e.speed for e in es) / max(1, len(es))
    stats[mode] = (n / 6, hp / 6, agg / 6, spd / 6)
    print("    %-4s  %5.1f monsters   total health %6.0f   avg aggro %.2f   avg speed %.2f   (sim=%s)"
          % (mode, n / 6, hp / 6, agg / 6, spd / 6, perf.sim))
hi, mi, lo = stats["high"], stats["mid"], stats["low"]
check(0.4 < lo[0] / hi[0] < 0.65, "LOW has about half the monsters (%.0f%%)" % (100 * lo[0] / hi[0]))
check(0.65 < mi[0] / hi[0] < 0.85, "MID has about three quarters (%.0f%%)" % (100 * mi[0] / hi[0]))
from world import Enemy  # noqa: E402
per = {}
for mode in ("high", "mid", "low"):
    perf.sim = mode
    per[mode] = Enemy("zombie", 5, 5, depth=3).hp
check(abs(per["low"] / per["high"] - 2.0) < 0.01 and abs(per["mid"] / per["high"] - 1.4) < 0.01,
      "each monster's health: MID x%.2f, LOW x%.2f" % (per["mid"] / per["high"], per["low"] / per["high"]))
print("    sector total health: MID %.0f%%, LOW %.0f%% of HIGH" % (100 * mi[1] / hi[1], 100 * lo[1] / hi[1]))
check(lo[2] > mi[2] > hi[2] and lo[3] > hi[3], "lower modes are angrier and quicker")

# ---- net: the session runs at the lowest mode anyone has
import netplay as NP  # noqa: E402


class FakeGuest:
    def __init__(self, dm, hello=True):
        self.demand, self.hello = dm, hello


class FakeHost:
    session_mode = NP.HostSession.session_mode

    def __init__(self, guests):
        self.guests = guests


perf.local = "high"
check(FakeHost([FakeGuest("high"), FakeGuest("low")]).session_mode() == "low", "a LOW guest pulls a HIGH host's session to LOW")
check(FakeHost([FakeGuest("mid")]).session_mode() == "mid", "a MID guest -> MID")
check(FakeHost([FakeGuest("low", hello=False)]).session_mode() == "high", "someone still connecting doesn't count yet")

# ---- title toggle cycles and saves
perf.local = "high"
g.state, g.world = "title", None
g.inputs[0].pressed = {"reload"}
g.update(1 / 60)
check(perf.local == "mid", "R / X on the title screen steps HIGH -> MID")
g.inputs[0].pressed = set()

# ---- crosshair
perf.local = "high"
g.new_world(1)
g.state = "play"
inp = g.inputs[0]
inp.mouse_mode = True
pos = (g.W // 2 + 140, g.H // 2 - 60)
pygame.mouse.get_pos = lambda: pos
g._mouse_t = g.time
g.draw()
g.draw_pointer(g.screen)
px = g.screen.get_at(pos)
check(g._cursor_vis is False, "the system arrow hides while mouse-aiming in play")
red = [g.screen.get_at((pos[0] + dx, pos[1])) for dx in range(-14, 15)]
check(any(c.r > 200 and c.g < 90 and c.b < 90 for c in red), "a red crosshair sits under the mouse")
pygame.image.save(g.screen.subsurface(pygame.Rect(pos[0] - 60, pos[1] - 60, 120, 120)), os.path.join(out, "crosshair.png"))
g.time += 5.5
g.draw()
g.draw_pointer(g.screen)
red = [g.screen.get_at((pos[0] + dx, pos[1])) for dx in range(-14, 15)]
check(not any(c.r > 230 and c.g < 60 and c.b < 60 for c in red) and g._cursor_vis is False,
      "after 5 s of a still mouse the crosshair is gone")
g._mouse_t = g.time
g.state = "title"
g.world = None
g.draw()
g.draw_pointer(g.screen)
check(g._cursor_vis is True, "on menus the normal arrow is back")
g.time += 5.5
g.draw_pointer(g.screen)
check(g._cursor_vis is False, "...and it hides after 5 s still too")

print("FAILED: %d" % len(fails) if fails else "all demand checks passed")
sys.exit(1 if fails else 0)

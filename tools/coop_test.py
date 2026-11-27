"""Headless local co-op test: drop-in join, enemy targeting, down/revive, sector transition, game over.
python tools/coop_test.py <outdir>"""
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
from world import Enemy  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(7)
g = main.Game(windowed=True)


class Bot:
    def __init__(self, dev):
        self.move = (0.0, 0.0)
        self.aim = None
        self.fire = False
        self.pressed = set()
        self.pending = set()
        self.device_name = None
        self.keyboard = False
        self.mouse_mode = False
        self.dev = dev

    def poll(self, ps):
        pass

    def set_device(self, d):
        self.dev = d


p1 = Bot(None)
p1.keyboard = True
g.inputs = [p1]
g.spare = {}
g.new_world(2)
g.state = "play"
w = g.world
ok = True


def check(cond, msg):
    global ok
    print(("PASS " if cond else "FAIL ") + msg)
    ok &= bool(cond)


# --- join: a spare pad presses BACK
pad = Bot(("joy", object()))
g.spare = {1: pad}
pad.pressed = {"back"}
g.try_join()
pad.pressed = set()
check(g.state == "join" and len(g.inputs) == 2 and len(w.players) == 1, "BACK on a spare pad opens P2's body pick (game waits)")
p2b = g.inputs[1]
# backing out gives up the slot
p2b.pressed = {"back"}
g.update(1 / 60)
p2b.pressed = set()
check(g.state == "play" and len(g.inputs) == 1 and len(w.players) == 1, "B / BACK on the pick screen cancels the join")
# join again, pick a body, confirm
g.spare = {1: pad}
pad.pressed = {"back"}
g.try_join()
pad.pressed = set()
p2b = g.inputs[1]
g.chars[1] = "skelebot"
p2b.pressed = {"nav_right"}
g.update(1 / 60)
want = g.chars[1]
g.draw()
pygame.image.save(g.screen, os.path.join(out, "coop_pick.png"))
p2b.pressed = {"a"}
g.update(1 / 60)
p2b.pressed = set()
check(want != "skelebot" and g.state == "play" and len(w.players) == 2 and w.players[1].char == want,
      "P2 chose %s with LEFT / RIGHT and joined as it" % want)
check(len(g.inputs) == 2 and len(w.players) == 2, "P2 joined (inputs %d, players %d)" % (len(g.inputs), len(w.players)))
p2b = g.inputs[1]
P1, P2 = w.players
check(P2.idx == 1 and math.hypot(P1.x - P2.x, P1.y - P2.y) < 3, "P2 spawned next to P1")

# --- both move/shoot independently for a few seconds
p1.move = (1, 0)
p2b.move = (0, 1)
for f in range(120):
    g.update(1 / 60)
    g.draw()
pygame.image.save(g.screen, os.path.join(out, "coop_play.png"))
check(P1.x != P2.x or P1.y != P2.y, "players moved separately")
p1.move = p2b.move = (0, 0)

# --- targeting: an enemy next to P2 goes for P2
L = w.level
w.enemies = []
P1.x, P1.y = P2.x + 9, P2.y + 9          # far apart (tether permitting)
spot = next(((P2.x + dx, P2.y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1))
             if not L.is_solid(int(P2.x + dx), int(P2.y + dy))), (P2.x, P2.y))
e = Enemy("zombie", spot[0], spot[1], awake=True, depth=2)
w.enemies.append(e)
for f in range(10):
    g.update(1 / 60)
check(e.target is P2, "enemy near P2 targets P2")

# --- down + revive
w.enemies = []
P2.hp = 1
w.hurt_player(50, P2.x, P2.y, 0, who=P2)
check(not P2.alive, "P2 downed")
check(g.state == "play", "game continues while P1 lives")
P1.x, P1.y = P2.x, P2.y
for f in range(60 * 3):
    g.update(1 / 60)
    if f == 60:
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "coop_revive.png"))
check(P2.alive and P2.hp > 0, "P2 revived by standing on bones (hp %.0f)" % P2.hp)

# --- transition carries both players
P2.alive = False
P2.hp = 0
g.transition = 0
d0 = w.depth
g.new_world(w.depth + 1, w.players, w.score)
w = g.world
check(len(w.players) == 2 and all(p.alive for p in w.players) and w.depth == d0 + 1, "next sector: both players present, downed one revived")

# --- HUD with two players draws
g.draw()
pygame.image.save(g.screen, os.path.join(out, "coop_hud.png"))

# --- game over only when both are down
for p in w.players:
    p.hp = 1
    p.invuln = 0
    w.hurt_player(50, p.x, p.y, 0, who=p)
g.update(1 / 60)
check(g.state == "dead", "game over when all players down")
print("OK" if ok else "FAILURES")

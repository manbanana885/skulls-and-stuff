"""Net play test: a host and up to four guests in one process, talking over real localhost sockets.
python tools/net_test.py <outdir>"""
import os
import sys
import math
import time
import random

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import net  # noqa: E402
import netplay as NP  # noqa: E402
import weapons as WP  # noqa: E402
from world import Enemy, Loot  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(7)
PORT = 47877
FAILED = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILED.append(msg)


class Bot:
    def __init__(self):
        self.move = (0.0, 0.0)
        self.aim = None
        self.fire = False
        self.pressed = set()
        self.pending = set()
        self.device_name = None
        self.keyboard = False
        self.mouse_mode = False
        self.dev = None

    def poll(self, ps):
        pass

    def set_device(self, d):
        pass


def make_game():
    g = main.Game(windowed=True)
    b = Bot()
    g.inputs = [b]
    g.spare = {}
    return g, b


games = []


def frames(n=1, press=None):
    """Run every game one frame at a time (host first), optionally pressing a key on one bot for the first frame."""
    for f in range(n):
        if press and f == 0:
            press[0].pressed = set(press[1])
        for g_, b_ in games:
            g_.update(1 / 60)
        for g_, b_ in games:
            b_.pressed = set()
        time.sleep(0.001)


def until(cond, limit=300):
    for _ in range(limit):
        if cond():
            return True
        frames(1)
    return cond()


print("== lobby")
host, hb = make_game()
games.append((host, hb))
host.chars[0] = "skelebot"
host.net = NP.HostSession(host, PORT)
check(host.state == "lobby" and host.net.addresses, "hosting: lobby open, address %s" % host.net.addresses)
host.draw()
pygame.image.save(host.screen, os.path.join(out, "net_host_lobby.png"))

guest, gb = make_game()
games.append((guest, gb))
guest.chars[0] = "canbot"
guest.net = NP.JoinScreen(guest)
guest.net.text = "127.0.0.1:%d" % PORT
guest.draw()
pygame.image.save(guest.screen, os.path.join(out, "net_join_screen.png"))
guest.net.connect(guest, guest.net.text)
check(until(lambda: isinstance(guest.net, NP.GuestSession) and guest.net.slot is not None),
      "guest connects and gets a slot (%s)" % getattr(guest.net, "slot", None))
check(until(lambda: guest.net.lobby is not None and len(guest.net.lobby["players"]) == 2), "both appear in the lobby")
frames(1, (gb, {"nav_right"}))
frames(5, (gb, {"a"}))
check(until(lambda: any(gu.ready and gu.char == "mutant" for gu in host.net.guests)),
      "guest picked a body (mutant) and readied up")
guest.draw()
pygame.image.save(guest.screen, os.path.join(out, "net_guest_lobby.png"))

print("== start")
frames(1, (hb, {"start"}))
check(host.state == "play" and len(host.world.players) == 2, "host starts: 2 players in the world")
check(until(lambda: guest.state == "play" and guest.world is not None), "guest receives the world")
hw, gw = host.world, guest.world
check(gw.depth == hw.depth and gw.level.W == hw.level.W and bytes(gw.level.solid) == bytes(hw.level.solid),
      "guest's level matches the host's")
frames(10)
gw = guest.world
check(sorted(p.idx for p in gw.players) == [0, 1] and next(p for p in gw.players if p.idx == 1).char == "mutant",
      "guest sees both players, itself as the mutant")
check(guest.local_players()[0].idx == 1 and host.local_players()[0].idx == 0, "each machine knows which player is theirs")

print("== guest controls drive its player on the host")
hp1 = next(p for p in host.world.players if p.idx == 1)
L = host.world.level
cx, cy = int(hp1.x), int(hp1.y)
for x in range(cx - 8, cx + 9):
    for y in range(cy - 8, cy + 9):
        if 0 < x < L.W - 1 and 0 < y < L.H - 1:
            L.solid[L.i(x, y)] = 0
            L.changed.append((x, y))
host.world.enemies = [e for e in host.world.enemies if math.hypot(e.x - hp1.x, e.y - hp1.y) > 14]
host.world.flow_tile = None
x0, y0 = hp1.x, hp1.y
gb.move = (1.0, 0.0)
frames(40)
gb.move = (0.0, 0.0)
frames(10)
hp1 = next(p for p in host.world.players if p.idx == 1)
gp1 = guest.local_players()[0]
check(math.hypot(hp1.x - x0, hp1.y - y0) > 1.0, "guest's stick moved its player on the host (%.1f tiles)" % math.hypot(hp1.x - x0, hp1.y - y0))
check(math.hypot(gp1.x - hp1.x, gp1.y - hp1.y) < 0.3, "and the guest sees itself where the host has it")
check(bytes(guest.world.level.solid) == bytes(host.world.level.solid), "cleared floor (level edits) reached the guest")

print("== prediction: the guest moves at once, even when the host is slow to answer")
hp1 = next(p for p in host.world.players if p.idx == 1)
hx0, hy0 = hp1.x, hp1.y
gx0, gy0 = guest.local_players()[0].x, guest.local_players()[0].y
gb.move = (0.0, 1.0)
for _ in range(12):                      # host frozen: only the guest runs
    guest.update(1 / 60)
gp1 = guest.local_players()[0]
moved = math.hypot(gp1.x - gx0, gp1.y - gy0)
check(moved > 0.5 and math.hypot(hp1.x - hx0, hp1.y - hy0) < 1e-6,
      "with the host frozen the guest still walks right away (%.2f tiles)" % moved)
gb.move = (0.0, 0.0)
frames(30)
hp1 = next(p for p in host.world.players if p.idx == 1)
gp1 = guest.local_players()[0]
check(math.hypot(gp1.x - hp1.x, gp1.y - hp1.y) < 0.35, "once the host catches up they agree again (off by %.2f)"
      % math.hypot(gp1.x - hp1.x, gp1.y - hp1.y))

print("== guest shoots a monster")
e = Enemy("zombie", hp1.x + 3, hp1.y, awake=True, depth=1)
e.hp = 1e6
host.world.enemies.append(e)
from assets import to_screen  # noqa: E402
ax_, ay_ = to_screen(1, 0)
bx_, by_ = to_screen(0, 0)
gb.aim = (ax_ - bx_, ay_ - by_)         # screen direction of world +x, where the monster stands
gb.fire = True
for _ in range(60):
    e.x, e.y, e.vx, e.vy = hp1.x + 3, hp1.y, 0, 0
    frames(1)
gb.fire = False
check(1e6 - e.hp > 0, "the guest's bullets hurt a monster on the host (%.0f)" % (1e6 - e.hp))
gp1 = guest.local_players()[0]
check(len(guest.world.particles) > 0 or len(guest.world.gibs) > 0, "the guest sees effects (%d particles)" % len(guest.world.particles))
check(any(math.hypot(q.x - e.x, q.y - e.y) < 0.5 for q in guest.world.enemies), "the guest sees the monster")
guest.draw()
pygame.image.save(guest.screen, os.path.join(out, "net_guest_view.png"))
host.draw()
pygame.image.save(host.screen, os.path.join(out, "net_host_view.png"))
e.hp = 0
e.alive = False

print("== guest picks up a gun")
hp1 = next(p for p in host.world.players if p.idx == 1)
gun = WP.generate(3, random.Random(5), arch="shotgun", rarity=2)
host.world.loot.append(Loot("weapon", hp1.x + 0.3, hp1.y, gun))
frames(3)
frames(4, (gb, {"interact"}))
hp1 = next(p for p in host.world.players if p.idx == 1)
check(gun in hp1.weapons, "E / A on the guest picks the gun up (on the host)")
frames(4)
check(any(w_.arch == "shotgun" for w_ in guest.local_players()[0].weapons), "and the guest's view shows it in hand")

print("== guest menu: world keeps running, cursor moves on the host")
frames(2, (gb, {"start"}))
check(guest.state == "pause", "START opens the guest's menu")
t0 = host.world.time
cur0 = next(p for p in host.world.players if p.idx == 1).inv_cur
frames(4, (gb, {"nav_down"}))
cur1 = next(p for p in host.world.players if p.idx == 1).inv_cur
check(cur1 != cur0, "menu navigation reaches the host (%s -> %s)" % (cur0, cur1))
check(host.world.time > t0 and host.state == "play", "the host's game kept running")
guest.draw()
pygame.image.save(guest.screen, os.path.join(out, "net_guest_menu.png"))
frames(2, (gb, {"start"}))
check(guest.state == "play", "START closes it")

print("== bandwidth")
s0 = host.net.guests[0].conn.sent_bytes
t0 = time.perf_counter()
hp0 = next(p for p in host.world.players if p.idx == 0)
for k in range(8):
    host.world.enemies.append(Enemy("zombie", hp0.x + 4 + k % 3, hp0.y - 2 + k // 3, awake=True, depth=2))
hb.fire = True
hb.aim = (1.0, 0.0)
for _ in range(120):
    host.world.player.hp = host.world.player.max_hp
    for p in host.world.players:
        p.hp = p.max_hp
    frames(1)
hb.fire = False
sent = host.net.guests[0].conn.sent_bytes - s0
print("  %d bytes to the guest over 2 s of fighting (%.1f KB/s)" % (sent, sent / 2 / 1024))
check(sent / 2 < 120 * 1024, "under 120 KB/s per guest")

print("== breach seen by the guest")
hp1 = next(p for p in host.world.players if p.idx == 1)
L = host.world.level
wx, wy = int(hp1.x) + 4, int(hp1.y)
L.solid[L.i(wx, wy)] = 1
frames(4)
check(guest.world.level.solid[L.i(wx, wy)] == 1, "a new wall shows up for the guest")
host.world.breach(wx + 0.5, wy + 0.5, 2.0)
frames(4)
check(guest.world.level.solid[L.i(wx, wy)] == host.world.level.solid[L.i(wx, wy)] != 1, "and its breach too")

print("== more guests drop in mid-game; a fifth is turned away")
extra = []
for k, ch in enumerate(("skelebot", "mutant")):
    g3, b3 = make_game()
    games.append((g3, b3))
    g3.chars[0] = ch
    g3.net = NP.JoinScreen(g3)
    g3.net.connect(g3, "127.0.0.1:%d" % PORT)
    ok = until(lambda: isinstance(g3.net, NP.GuestSession) and g3.net.slot is not None)
    frames(3, (b3, {"a"}))
    ok = ok and until(lambda: g3.state == "play")
    extra.append((g3, b3))
    check(ok, "guest %d dropped into the running game" % (k + 2))
frames(10)
check(len(host.world.players) == 4 and sorted(p.idx for p in host.world.players) == [0, 1, 2, 3], "4 players on the host")
check(all(len(g_.world.players) == 4 for g_, _ in games), "every machine sees 4 players")
g5, b5 = make_game()
games.append((g5, b5))
g5.net = NP.JoinScreen(g5)
g5.net.connect(g5, "127.0.0.1:%d" % PORT)
until(lambda: g5.net is None or (isinstance(g5.net, NP.GuestSession) and g5.net.error))
check(g5.net is None and "full" in g5.title_msg[0], "a fifth player is told the game is full (%r)" % g5.title_msg[0])
games.remove((g5, b5))
g3 = extra[0][0]
g3.draw()
pygame.image.save(g3.screen, os.path.join(out, "net_p3_view.png"))

print("== version mismatch")
bad = net.Connector("127.0.0.1:%d" % PORT)
conn = None
for _ in range(200):
    conn = bad.poll()
    if conn:
        break
    frames(1)
conn.send_json("h", {"v": "nope"})
msg = None
for _ in range(200):
    frames(1)
    for kind, payload in conn.poll():
        if kind == "x":
            msg = net.read_json(payload).get("msg")
    if msg:
        break
check(msg and "version" in msg, "a different game version is refused: %r" % msg)

print("== next sector carries everyone along")
d0 = host.world.depth
host.world.exit_reached = True
until(lambda: host.world.depth == d0 + 1, 200)
check(until(lambda: all(g_.world is not None and g_.world.depth == d0 + 1 for g_, _ in games), 300),
      "all guests moved to sector %d" % (d0 + 1))
check(all(len(g_.world.players) == 4 for g_, _ in games), "with all 4 players")

print("== a guest leaves; the host leaves")
g4, b4 = extra[1]
g4.leave_net()
games.remove((g4, b4))
check(until(lambda: len(host.world.players) == 3), "the host drops the player who left")
host.leave_net()
games.remove((host, hb))
check(until(lambda: guest.net is None) and guest.state == "title" and guest.title_msg[1] > 0,
      "guests go back to the title with a message: %r" % guest.title_msg[0])

print()
print("FAILED:", FAILED or "none")

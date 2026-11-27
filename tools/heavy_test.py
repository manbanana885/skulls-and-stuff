"""Heavy weapons: chaingun spin-up + slowdown, railgun pierces every monster and up to 5 wall blocks.
python tools/heavy_test.py <outdir>"""
import os
import sys
import math

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SKULLS_SAVE"] = os.devnull        # never touch the player's save.json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import weapons as WP  # noqa: E402
from world import Enemy  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
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
g.new_world(1)
g.state = "play"
w = g.world
p = w.player
w.traps = []
w.enemies = []
w.spawners = []
w.bosses = []
L = w.level


def walk_speed(arch):
    p.weapons[p.cur] = WP.generate(1, arch=arch, rarity=0)
    x0, y0 = p.x, p.y
    bot.move = (1.0, 0.0)
    bot.fire = False
    d = 0.0
    for _ in range(30):
        ox, oy = p.x, p.y
        g.update(1 / 60)
        d += math.hypot(p.x - ox, p.y - oy)
    bot.move = (0.0, 0.0)
    p.x, p.y = x0, y0
    return d / 0.5


base = walk_speed("pistol")
for a in ("chaingun", "railgun"):
    print("%-9s move speed %.2f tiles/s vs pistol %.2f  (x%.2f)" % (a, walk_speed(a), base, walk_speed(a) / base))

# chaingun spin-up: shots in each 0.25 s window while holding the trigger
p.weapons[p.cur] = WP.generate(1, arch="chaingun", rarity=0)
p.weapon.st["mag"] = p.weapon.ammo = 9999
bot.fire = True
bot.aim = (300, 0)
counts = []
for win in range(8):
    a0 = p.weapon.ammo
    for f in range(15):
        g.update(1 / 60)
    counts.append(a0 - p.weapon.ammo)
print("chaingun shots per 0.25s while held:", counts, "(spins up to %.1f/s)" % (p.weapon.st["rate"]))
bot.fire = False
for _ in range(60):
    g.update(1 / 60)

# railgun: find a straight line with monsters in the open and several wall blocks behind them
p.weapons[p.cur] = WP.generate(1, arch="railgun", rarity=0)
best = None
for y in range(2, L.H - 2):
    for x in range(2, L.W - 12):
        if all(not L.is_solid(x + k, y) for k in range(4)):
            walls = sum(1 for k in range(4, 30) if x + k < L.W and L.is_solid(x + k, y))
            if walls >= 7:
                best = (x, y)
                break
    if best:
        break
x, y = best
walls_before = [(x + k, y) for k in range(4, 30) if x + k < L.W and L.is_solid(x + k, y)]
p.x, p.y = x + 0.5, y + 0.5
w.enemies = []
mons = []
for k in (1.5, 2.3, 3.1):
    e = Enemy("zombie", x + k + 0.5, y + 0.5, awake=True, depth=1)
    e.hp = 1e6
    mons.append(e)
    w.enemies.append(e)
hp0 = [e.hp for e in mons]
w.projs = []
# aim straight down +x in world space
from assets import to_screen  # noqa: E402
sx, sy = to_screen(1, 0)
s0x, s0y = to_screen(0, 0)
bot.aim = ((sx - s0x) * 10, (sy - s0y) * 10)
p.weapon.cd = 0
bot.fire = True
g.update(1 / 60)
bot.fire = False
rail = [b for b in w.projs if b.kind == "rail"]
walls_hit = 0
frames = 0
shot = None
for f in range(60):
    if rail and rail[0] in w.projs:
        shot = rail[0]
    g.update(1 / 60)
    if f == 2:
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "railgun.png"))
    frames += 1
cells = [c for c in shot.hit if isinstance(c, tuple)] if shot else []
print("railgun: wall blocks on the line destroyed %d of %d (first %s)" % (
    sum(1 for c in walls_before if not L.is_solid(*c)), len(walls_before), [int(not L.is_solid(*c)) for c in walls_before]))
print("railgun: monsters hit %d/3 (dmg %s), wall blocks entered %d (punches through 5, stops in the next), slug end x=%.1f" % (
    sum(1 for e, h in zip(mons, hp0) if e.hp < h), [round(h - e.hp) for e, h in zip(mons, hp0)], len(cells), shot.x if shot else -1))

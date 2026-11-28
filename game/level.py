"""Procedural level generation: rooms + wide corridors, biome themes, props, spawners."""
import random
from collections import deque
from biomes import BIOMES
from bestiary import ENEMIES as _BEST

# enemy types unlocked by depth: (min_depth, type, weight)
ENEMY_TABLE = [
    (1, "zombie", 6), (1, "leech", 4), (1, "crawler", 4),
    (2, "drone", 3), (2, "spitter", 3), (2, "bloater", 2), (2, "stalker", 2), (2, "wretch", 2), (2, "mimic", 1.5),
    (3, "spider", 2), (3, "turret", 2), (3, "skull", 3), (3, "hellspawn", 2.5),
    (4, "brute", 1.5), (4, "walker", 1.5),
]
NOT_FROM_HIVES = {"turret", "walker", "brute", "mimic", "chestmimic", "mourner", "bonepriest", "lurker", "cinderfiend", "devourer"}
# signature enemies roam outside their home biome too, just rarely (home biomes boost them x4)
ENEMY_TABLE += [(1, "pinkmelt", 1.0)] + [(2, k, 0.35) for k in (
    "bonepriest", "rustbound", "wendigo", "cinderfiend", "mourner", "enthraller", "devourer", "chestmimic", "boghag",
    "flagellant", "hookman", "raddrone", "clone", "lurker", "hazmatsprayer", "shieldbearer")]
# vermin, fire demons and the Pink Heavy roam everywhere
ENEMY_TABLE += [(1, "viper", 1.6), (1, "roach", 0.45), (2, "scorpion", 1.4), (3, "cobra", 1.2),
                (2, "imp", 0.7), (3, "pitdemon", 1.0), (4, "devil", 0.9), (2, "pinkheavy", 1.0)]
# (first depth, depth it reaches full strength): weight climbs (quadratically) in between - rare early, common later
RAMP = {"pinkheavy": (2, 5), "pitdemon": (3, 5), "devil": (4, 6)}
# where the new monsters like to live (on top of the biome's own bias)
HOMES = {"pinkheavy": {"facility": 2.0, "nuclear": 1.5},
         "viper": {"wrath": 3.0, "otherworld": 2.0, "ossuary": 1.5}, "cobra": {"wrath": 3.0, "otherworld": 2.0, "greed": 1.5},
         "scorpion": {"hell": 2.5, "ossuary": 2.0, "violence": 2.0},
         "roach": {"sewer": 4.0, "gluttony": 3.0, "nuclear": 2.5, "facility": 1.5, "biotech": 1.5},
         "imp": {"hell": 4.0, "heresy": 3.0, "lust": 2.0, "wrath": 2.0, "violence": 2.0},
         "pitdemon": {"hell": 3.0, "violence": 3.0, "heresy": 2.0}, "devil": {"hell": 3.0, "heresy": 3.0, "greed": 2.0}}


def ramp(kind, depth):
    r = RAMP.get(kind)
    if not r:
        return 1.0
    a, b = r
    return max(0.06, min(1.0, ((depth - a + 1) / (b - a + 1)) ** 2))


def weighted(rng, items):
    tot = sum(w for _, w in items)
    r = rng.uniform(0, tot)
    for v, w in items:
        r -= w
        if r <= 0:
            return v
    return items[-1][0]


class Room:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def center(self):
        return self.x + self.w // 2, self.y + self.h // 2

    def overlaps(self, o, pad=2):
        return (self.x - pad < o.x + o.w and o.x - pad < self.x + self.w and
                self.y - pad < o.y + o.h and o.y - pad < self.y + self.h)

    def cells(self):
        for x in range(self.x, self.x + self.w):
            for y in range(self.y, self.y + self.h):
                yield x, y


class Level:
    def __init__(self, depth, seed=None, biome="facility"):
        self.depth = depth
        self.biome_name = biome
        B = self.biome = BIOMES[biome]
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        rng = self.rng = random.Random(self.seed)
        W = H = 46 + min(depth * 4, 30)
        self.W, self.H = W, H
        self.solid = bytearray([1]) * (W * H)    # 1 = wall, 2 = solid prop, 0 = floor
        self.floor = [None] * (W * H)
        self.wallkind = [None] * (W * H)
        self.props = {}                          # (x,y) -> sprite name (decor or solid)
        self.enemies, self.spawners, self.pickups = [], [], []
        self.corridor_floor = B["floors"][0][0]
        decor = B["decor"]

        # --- rooms
        rooms = []
        target = 8 + min(depth, 8)
        for _ in range(400):
            if len(rooms) >= target:
                break
            w, h = rng.randint(6, 12), rng.randint(6, 12)
            r = Room(rng.randint(2, W - w - 2), rng.randint(2, H - h - 2), w, h)
            if not any(r.overlaps(o) for o in rooms):
                rooms.append(r)
        self.rooms = rooms
        themes = B["floors"] + [("floor_flesh", min(4.0, (0.4 + depth * 0.5) * B["infest"]))]
        for idx_r, r in enumerate(rooms):
            theme = weighted(rng, themes) if idx_r else B["floors"][0][0]
            r.theme = theme
            for x, y in r.cells():
                self.carve(x, y, theme)
            if r.w >= 9 and r.h >= 9 and rng.random() < 0.6:
                for px, py in ((r.x + 2, r.y + 2), (r.x + r.w - 4, r.y + 2), (r.x + 2, r.y + r.h - 4), (r.x + r.w - 4, r.y + r.h - 4)):
                    for dx in range(2):
                        for dy in range(2):
                            self.solid[self.i(px + dx, py + dy)] = 1
            for _ in range(r.w + r.h):
                side = rng.randint(0, 3)
                if side == 0:
                    x, y = rng.randint(r.x, r.x + r.w - 1), r.y - 1
                elif side == 1:
                    x, y = rng.randint(r.x, r.x + r.w - 1), r.y + r.h
                elif side == 2:
                    x, y = r.x - 1, rng.randint(r.y, r.y + r.h - 1)
                else:
                    x, y = r.x + r.w, rng.randint(r.y, r.y + r.h - 1)
                if 1 < x < W - 2 and 1 < y < H - 2:
                    self.carve(x, y, theme)

        for i in range(1, len(rooms)):
            a = rooms[i]
            b = min(rooms[:i], key=lambda o: abs(o.center[0] - a.center[0]) + abs(o.center[1] - a.center[1]))
            self.corridor(a.center, b.center)
        for _ in range(max(1, len(rooms) // 4)):
            a, b = rng.sample(rooms, 2)
            self.corridor(a.center, b.center)

        # floor variety
        for idx in range(W * H):
            if self.solid[idx] != 0:
                continue
            f, roll = self.floor[idx], rng.random()
            acc = 0.0
            for src, dst, p in B["extras"]:
                if f == src:
                    acc += p
                    if roll < acc:
                        self.floor[idx] = dst
                        break

        region = {}
        for y in range(H):
            for x in range(W):
                key = (x // 7, y // 7)
                if key not in region:
                    region[key] = rng.choice(B["walls"])
                self.wallkind[self.i(x, y)] = region[key]
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                if self.solid[self.i(x, y)] == 1 and any(self.floor[self.i(x + dx, y + dy)] == "floor_flesh"
                                                          for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    self.wallkind[self.i(x, y)] = "wall_flesh"

        # --- start + exit
        start = rooms[0]
        self.start = (start.center[0] + 0.5, start.center[1] + 0.5)
        dist = self.bfs(start.center)
        far = max(rooms[1:], key=lambda r: dist[self.i(*r.center)] if dist[self.i(*r.center)] >= 0 else -1)
        self.exit = (far.center[0] + 0.5, far.center[1] + 0.5)
        ex, ey = far.center
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if self.solid[self.i(ex + dx, ey + dy)] == 0:
                    self.floor[self.i(ex + dx, ey + dy)] = "floor_hazard"
        # boss guards the portal from a few tiles away
        self.boss_spot = None
        spots = [(ex + dx, ey + dy) for dx in range(-5, 6) for dy in range(-5, 6)
                 if 2.5 <= abs(dx) + abs(dy) <= 6 and 1 < ex + dx < W - 2 and 1 < ey + dy < H - 2 and self.open_around(ex + dx, ey + dy)]
        if spots:
            bx, by = rng.choice(spots)
            self.boss_spot = (bx + 0.5, by + 0.5)

        # --- populate rooms
        bias = B["bias"]
        sig = set(B["signature"])
        kinds = [(k, w * bias.get(k, 1.0) * HOMES.get(k, {}).get(biome, 1.0) * ramp(k, depth))
                 for d, k, w in ENEMY_TABLE if depth >= d or k in sig]
        hive_kinds = [(k, w) for k, w in kinds if k not in NOT_FROM_HIVES]
        for r in rooms[1:]:
            free = [(x, y) for x, y in r.cells() if self.solid[self.i(x, y)] == 0 and (x, y) != (ex, ey)
                    and abs(x - ex) + abs(y - ey) > 2]
            rng.shuffle(free)
            for _ in range(rng.randint(0, 3)):
                if not free:
                    break
                x, y = free.pop()
                if self.open_around(x, y):
                    self.props[(x, y)] = rng.choice(B["solids"])
                    self.solid[self.i(x, y)] = 2
            for _ in range(rng.randint(1, 4)):
                if free:
                    self.props[free.pop()] = rng.choice(decor)
            if r is not far and rng.random() < 0.45 + depth * 0.06:
                for _ in range(1 + (rng.random() < depth * 0.1)):
                    if free:
                        x, y = free.pop()
                        self.spawners.append((weighted(rng, hive_kinds), x + 0.5, y + 0.5))
            for _ in range(rng.randint(1 + depth // 3, 3 + depth + depth // 3)):     # rooms fill up as you go deeper
                if free:
                    x, y = free.pop()
                    kind = weighted(rng, kinds)
                    self.enemies.append((kind, x + 0.5, y + 0.5))
                    pack = (_BEST.get(kind) or {}).get("pack")
                    for _ in range(rng.randint(*pack) - 1 if pack else 0):     # roaches and imps come in packs
                        if free:
                            x, y = free.pop()
                            self.enemies.append((kind, x + 0.5, y + 0.5))
            if free and rng.random() < 0.3:
                x, y = free.pop()
                self.pickups.append(("health", x + 0.5, y + 0.5))
            if free and rng.random() < 0.15:
                x, y = free.pop()
                self.pickups.append(("power", x + 0.5, y + 0.5))
            if free and rng.random() < 0.22:
                x, y = free.pop()
                self.pickups.append(("weapon", x + 0.5, y + 0.5))
        sx, sy = start.center
        for ox, oy in ((2, 0), (0, 2), (-2, 0), (0, -2), (1, 1)):
            if self.solid[self.i(sx + ox, sy + oy)] == 0:
                self.pickups.append(("weapon", sx + ox + 0.5, sy + oy + 0.5))
                break
        self.props = {k: v for k, v in self.props.items() if v not in decor or self.solid[self.i(*k)] == 0}

        self.edge = bytearray(W * H)
        for y in range(H):
            for x in range(W):
                self.refresh_edge(x, y)
        self.changed = []     # cells whose floor changed (renderer invalidates its cache)

    # -------------------------------------------------------------- helpers
    def i(self, x, y):
        return y * self.W + x

    def refresh_edge(self, x, y):
        """A wall is drawn only if it borders open space."""
        idx = self.i(x, y)
        if self.solid[idx] != 1:
            self.edge[idx] = 0
            return
        W, H = self.W, self.H
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and self.solid[self.i(nx, ny)] != 1:
                    self.edge[idx] = 1
                    return
        self.edge[idx] = 0

    def destroy_wall(self, x, y):
        """Blast a wall cell into rubble. Returns True if something was destroyed."""
        if not (1 <= x < self.W - 1 and 1 <= y < self.H - 1):
            return False
        idx = self.i(x, y)
        if self.solid[idx] != 1:
            return False
        self.solid[idx] = 0
        self.floor[idx] = "floor_rubble"
        self.changed.append((x, y))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                self.refresh_edge(x + dx, y + dy)
        return True

    def carve(self, x, y, theme):
        idx = self.i(x, y)
        self.solid[idx] = 0
        if self.floor[idx] is None:
            self.floor[idx] = theme

    def corridor(self, a, b):
        (x1, y1), (x2, y2) = a, b
        theme = self.corridor_floor
        if self.rng.random() < 0.5:
            self.hline(x1, x2, y1, theme)
            self.vline(y1, y2, x2, theme)
        else:
            self.vline(y1, y2, x1, theme)
            self.hline(x1, x2, y2, theme)

    def hline(self, x1, x2, y, theme):
        for x in range(min(x1, x2), max(x1, x2) + 2):
            for dy in (0, 1):
                self.carve(x, y + dy, theme)

    def vline(self, y1, y2, x, theme):
        for y in range(min(y1, y2), max(y1, y2) + 2):
            for dx in (0, 1):
                self.carve(x + dx, y, theme)

    def open_around(self, x, y):
        return all(self.solid[self.i(x + dx, y + dy)] == 0 for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    def is_solid(self, x, y):
        if x < 0 or y < 0 or x >= self.W or y >= self.H:
            return True
        return self.solid[y * self.W + x] != 0

    def bfs(self, start, max_dist=10 ** 9):
        """Distance field over walkable cells (8-neighbour, no corner cutting)."""
        W, H = self.W, self.H
        dist = [-1] * (W * H)
        starts = start if isinstance(start, list) else [start]     # multi-source: distance to the nearest player
        q = deque()
        for sx, sy in starts:
            if not self.is_solid(sx, sy) and dist[self.i(sx, sy)] < 0:
                dist[self.i(sx, sy)] = 0
                q.append((sx, sy))
        if not q:
            return dist
        solid = self.solid
        while q:
            x, y = q.popleft()
            d = dist[y * W + x]
            if d >= max_dist:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= W or ny >= H:
                    continue
                ni = ny * W + nx
                if solid[ni] or dist[ni] >= 0:
                    continue
                if dx and dy and (solid[y * W + nx] or solid[ny * W + x]):
                    continue
                dist[ni] = d + 1
                q.append((nx, ny))
        return dist

    def line_of_sight(self, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        n = int(max(abs(dx), abs(dy)) * 4) + 1
        for k in range(1, n):
            t = k / n
            if self.solid[int(y1 + dy * t) * self.W + int(x1 + dx * t)] == 1:
                return False
        return True

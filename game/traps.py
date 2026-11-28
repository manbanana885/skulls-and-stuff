"""Environmental traps: 2-3 per biome, placed at level start.

Every trap hurts everything that walks into it (players AND monsters), so luring enemies into
them is a valid tactic. Mechanics are generic; a style picks sprite, colours and side-effects.
"""
import math
import random

import sfx

rnd = random.Random()

# biome -> [(mechanic, style, weight)]
BIOME_TRAPS = {
    "facility": [("turret", "tech", 1.0), ("vent", "steam", 1.0), ("saw", "steel", 1.0)],
    "ossuary": [("spikes", "bone", 1.2), ("hands", "bone", 1.0), ("pendulum", "rust", 0.6)],
    "otherworld": [("tentacle", "flesh", 1.0), ("saw", "rust", 1.0), ("spikes", "rust", 0.8)],
    "outpost": [("strike", "icicle", 1.0), ("turret", "frost", 1.0), ("vent", "steam", 1.0)],
    "hell": [("pool", "lava", 1.0), ("vent", "fire", 1.0), ("strike", "meteor", 1.0)],
    "limbo": [("hands", "bone", 1.0), ("spikes", "bone", 1.0), ("wind", "ash", 0.6)],
    "lust": [("wind", "storm", 1.0), ("thorns", "rose", 1.2), ("tentacle", "pink", 0.8)],
    "gluttony": [("maw", "flesh", 1.2), ("pool", "bile", 1.0), ("vent", "geyser", 1.0)],
    "greed": [("saw", "gold", 1.0), ("spikes", "gold", 1.0), ("turret", "gold", 0.8)],
    "wrath": [("strike", "lightning", 1.0), ("pool", "mud", 1.0), ("tentacle", "bog", 1.0)],
    "heresy": [("vent", "fire", 1.2), ("pool", "lava", 1.0), ("strike", "meteor", 0.6)],
    "violence": [("pool", "blood", 1.0), ("thorns", "bramble", 1.0), ("pendulum", "iron", 1.0)],
    "nuclear": [("reactor", "rad", 1.0), ("tesla", "tesla", 1.0), ("vent", "steam", 0.8)],
    "biotech": [("laser", "red", 1.2), ("tentacle", "lab", 1.0), ("pool", "acid", 0.8)],
    "sewer": [("pool", "sludge", 1.0), ("vent", "geyser", 1.0), ("tentacle", "sewer", 1.0)],
    "chemical": [("reactor", "chem", 1.0), ("vent", "gas", 1.0), ("pool", "acid", 1.0)],
    "castle": [("pendulum", "iron", 1.0), ("spikes", "iron", 1.0), ("vent", "fire", 0.8)],
}
NAMES = {
    "turret": "POP-UP TURRETS", "vent": {"steam": "STEAM VENTS", "fire": "FIRE VENTS", "gas": "GAS VENTS", "geyser": "SLUDGE GEYSERS"},
    "saw": "BUZZSAWS", "spikes": "SPIKE TRAPS", "hands": "GRASPING HANDS", "pendulum": "PENDULUM BLADES", "tentacle": "TENTACLES",
    "strike": {"icicle": "FALLING ICICLES", "lightning": "LIGHTNING", "meteor": "FIRE RAIN"},
    "pool": {"lava": "LAVA", "bile": "BILE", "mud": "SUCKING MUD", "blood": "BOILING BLOOD", "acid": "ACID", "sludge": "SLUDGE"},
    "wind": "GALES", "thorns": "THORNS", "maw": "FLOOR MAWS", "reactor": "UNSTABLE REACTORS", "tesla": "TESLA COILS", "laser": "LASER GRIDS",
}

POOL = {   # colour, highlight, player dps, monster dps, effect
    "lava": ((150, 40, 8), (255, 150, 40), 26, 30, "burn"),
    "acid": ((40, 110, 20), (150, 255, 70), 16, 22, None),
    "bile": ((110, 100, 20), (220, 210, 70), 13, 18, None),
    "blood": ((90, 6, 8), (200, 40, 30), 12, 16, None),
    "sludge": ((52, 50, 24), (110, 115, 50), 5, 6, "mire"),
    "mud": ((44, 32, 20), (85, 65, 40), 0, 0, "mire"),
}
TENTACLE = {   # body colour, tip colour, hole tint
    "flesh": ((150, 60, 60), (230, 120, 110), None), "pink": ((200, 90, 150), (255, 170, 220), (255, 170, 210)),
    "bog": ((60, 80, 40), (140, 160, 80), (140, 170, 110)), "sewer": ((95, 100, 70), (170, 170, 120), (170, 180, 140)),
    "lab": ((215, 190, 175), (255, 120, 120), (230, 230, 240)),
}
TINT = {"gold": (255, 205, 90), "rust": (215, 140, 95), "frost": (190, 225, 255), "iron": None, "steel": None, "tech": None, "bone": None}


def _flyers():
    from world import FLYERS
    return FLYERS


def los(L, x0, y0, x1, y1):
    d = math.hypot(x1 - x0, y1 - y0)
    n = max(1, int(d / 0.3))
    c0, c1 = (int(x0), int(y0)), (int(x1), int(y1))
    for i in range(1, n):
        t = i / n
        c = (int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t))
        if c != c0 and c != c1 and L.is_solid(*c):
            return False
    return True


def players_in(w, x, y, r):
    return [p for p in w.players if p.alive and (p.x - x) ** 2 + (p.y - y) ** 2 < (r + p.R) ** 2]


def enemies_in(w, x, y, r, ground=True):
    fl = _flyers() if ground else ()
    out = []
    for e in w.enemies:
        if e.alive and e.state != "dormant" and not getattr(e, "submerged", False) and e.kind not in fl:
            if (e.x - x) ** 2 + (e.y - y) ** 2 < (r + e.r) ** 2:
                out.append(e)
    return out


def dist_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy or 1e-6
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(px - ax - vx * t, py - ay - vy * t)


class Trap:
    shootable = False
    solid = False
    sprite = None
    r = 0.45

    def __init__(self, mech, style, x, y):
        self.mech, self.style = mech, style
        self.x, self.y = x, y
        self.t = rnd.random() * 10
        self.alive = True
        self.cool = {}            # id(victim) -> cooldown, so each trap hits each monster at a sane rate
        self.flash = 0.0
        # enemy-like fields so weapon side effects can be applied harmlessly
        self.burn = self.burn_dps = self.slow = 0.0
        self.last_hit_by = None

    # --- shared damage helper
    def harm(self, w, x, y, r, pdmg, edmg, knock=8.0, cd=0.5, ground=True, kx=None, ky=None):
        hit = False
        for p in players_in(w, x, y, r):
            if pdmg:
                w.hurt_player(pdmg, x if kx is None else p.x - kx, y if ky is None else p.y - ky, knock, who=p)
                hit = True
        for e in enemies_in(w, x, y, r, ground):
            k = id(e)
            if self.cool.get(k, 0) <= 0 and edmg:
                self.cool[k] = cd
                vx, vy = e.x - x, e.y - y
                d = math.hypot(vx, vy) or 1
                e.hit(w, edmg, vx / d * 30, vy / d * 30)
                hit = True
        return hit

    def tick_cool(self, dt):
        if self.cool:
            for k in list(self.cool):
                self.cool[k] -= dt
                if self.cool[k] <= -2:
                    del self.cool[k]

    def near_player(self, w, r):
        return any(p.alive and (p.x - self.x) ** 2 + (p.y - self.y) ** 2 < r * r for p in w.players)

    def update(self, w, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.tick_cool(dt)

    def hit(self, w, dmg, vx=0.0, vy=0.0):
        pass


# ---------------------------------------------------------------- spikes
class Spikes(Trap):
    def __init__(self, style, x, y, offset=0.0, period=3.2):
        super().__init__("spikes", style, x, y)
        self.sprite = "trap_bonespikes" if style == "bone" else "trap_spikes"
        self.period = period
        self.t = offset
        self.cycle = -1
        self.hits = set()

    def phase(self):
        c = self.t % self.period
        up0 = self.period - 1.4
        if c < up0 - 0.6:
            return "down", 0
        if c < up0:
            return "warn", 0
        if c < up0 + 0.1:
            return "rise", 2
        if c < up0 + 1.0:
            return "up", 3
        if c < up0 + 1.2:
            return "fall", 2
        return "fall", 1

    def frame(self, time):
        ph, f = self.phase()
        if ph == "warn" and int(time * 20) % 2:
            return 1
        return f

    def update(self, w, dt):
        super().update(w, dt)
        ph, f = self.phase()
        cyc = int(self.t / self.period)
        if ph == "rise" and cyc != self.cycle:
            self.cycle = cyc
            self.hits = set()
            if self.near_player(w, 8):
                w.snd("trap_spikes", self.x, self.y, 0.8)
        if ph in ("rise", "up"):
            for p in players_in(w, self.x, self.y, 0.45):
                if id(p) not in self.hits:
                    self.hits.add(id(p))
                    w.hurt_player(20, self.x, self.y, 5, who=p)
                    w.spray(p.x, p.y, 0.5, (20, 18, 22), 6, 2.5)
            for e in enemies_in(w, self.x, self.y, 0.45):
                if id(e) not in self.hits:
                    self.hits.add(id(e))
                    e.hit(w, 40, 0, 0)
                    w.spray(e.x, e.y, 0.6, e.blood, 14, 3.5)
        elif ph == "warn" and rnd.random() < dt * 8:
            from world import Particle
            w.add(Particle("chunk", self.x + rnd.uniform(-0.4, 0.4), self.y + rnd.uniform(-0.4, 0.4), 0.05, 0, 0, 1.2, 0.4, (60, 55, 50), 2))


# ---------------------------------------------------------------- buzzsaw on a track
class Saw(Trap):
    sprite = "trap_saw"

    def __init__(self, style, x0, y0, x1, y1):
        super().__init__("saw", style, x0, y0)
        self.a, self.b = (x0, y0), (x1, y1)
        self.axis = 0 if abs(x1 - x0) > abs(y1 - y0) else 1
        self.len = max(0.5, math.hypot(x1 - x0, y1 - y0))
        self.u = rnd.random()
        self.dir = 1
        self.speed = rnd.uniform(2.0, 2.8)

    def update(self, w, dt):
        super().update(w, dt)
        self.u += self.dir * self.speed * dt / self.len
        if self.u > 1 or self.u < 0:
            self.u = min(1.0, max(0.0, self.u))
            self.dir = -self.dir
        self.x = self.a[0] + (self.b[0] - self.a[0]) * self.u
        self.y = self.a[1] + (self.b[1] - self.a[1]) * self.u
        from world import Particle
        if rnd.random() < dt * 14:
            dx, dy = (1, 0) if self.axis == 0 else (0, 1)
            w.add(Particle("spark", self.x - dx * self.dir * 0.3, self.y - dy * self.dir * 0.3, 0.1, -dx * self.dir * rnd.uniform(2, 5) + rnd.uniform(-1, 1),
                           -dy * self.dir * rnd.uniform(2, 5) + rnd.uniform(-1, 1), rnd.uniform(1, 3), 0.3, (255, 220, 140), 2))
        if self.near_player(w, 6) and rnd.random() < dt * 2.5:
            w.snd("trap_saw", self.x, self.y, 0.5)
        for e in enemies_in(w, self.x, self.y, 0.42):
            if self.cool.get(id(e), 0) <= 0:
                w.spray(e.x, e.y, 0.5, e.blood, 20, 4)
                w.splat(e.x, e.y, e.blood, 0.25)
        if self.harm(w, self.x, self.y, 0.42, 18, 45, knock=10, cd=0.35):
            w.shake = max(w.shake, 3)


# ---------------------------------------------------------------- liquid pools
class Pool(Trap):
    def __init__(self, style, cells):
        cx = sum(c[0] for c in cells) / len(cells) + 0.5
        cy = sum(c[1] for c in cells) / len(cells) + 0.5
        super().__init__("pool", style, cx, cy)
        self.cells = set(cells)
        self.col, self.hi, self.pdps, self.edps, self.fx = POOL[style]
        self.snd_t = 0.0

    def inside(self, x, y):
        return (int(x), int(y)) in self.cells

    def update(self, w, dt):
        super().update(w, dt)
        from world import Particle
        self.snd_t -= dt
        cells = list(self.cells)
        for _ in range(2):
            if rnd.random() < dt * len(cells) * 0.4:
                cx, cy = rnd.choice(cells)
                x, y = cx + rnd.random(), cy + rnd.random()
                if self.style == "lava":
                    w.add(Particle("fire", x, y, 0.05, 0, 0, rnd.uniform(0.5, 1.5), 0.5, (255, 120, 30), rnd.uniform(6, 12)))
                elif self.style != "mud":
                    w.add(Particle("glow", x, y, 0.03, 0, 0, rnd.uniform(0.3, 0.8), 0.6, self.hi, 2))
        for p in w.players:
            if p.alive and self.inside(p.x, p.y):
                if self.fx == "mire":
                    p.status["mire"] = 0.25
                if self.pdps:
                    p.hp -= self.pdps * dt * p.mult("aegis")
                    w.hurt_flash = max(w.hurt_flash, 0.06)
                    if self.snd_t <= 0:
                        self.snd_t = 0.5
                        w.snd("sizzle" if self.style in ("lava", "acid", "bile") else "bubble", p.x, p.y, 0.6)
                    w.check_player_death(p.x, p.y, p)
        fl = _flyers()
        for e in w.enemies:
            if e.alive and e.kind not in fl and e.state != "dormant" and self.inside(e.x, e.y):
                if self.edps:
                    w.dot(e, self.edps * dt)
                if self.fx == "burn":
                    e.burn = max(e.burn, 1.0)
                    e.burn_dps = max(e.burn_dps, 4)
                elif self.fx == "mire":
                    e.slow = max(e.slow, 0.3)


# ---------------------------------------------------------------- vents / geysers
class Vent(Trap):
    def __init__(self, style, x, y):
        super().__init__("vent", style, x, y)
        self.sprite = "trap_hole" if style == "geyser" else "trap_vent"
        self.period = rnd.uniform(3.4, 4.8)
        self.gas_t = 0.0
        self.cyc = -1

    def state(self):
        c = self.t % self.period
        if c < self.period - 2.1:
            return "idle"
        if c < self.period - 1.3:
            return "warn"
        return "blast"

    def update(self, w, dt):
        super().update(w, dt)
        from world import Particle
        st = self.state()
        x, y = self.x, self.y
        if st == "warn" and rnd.random() < dt * 10:
            c = {"steam": (200, 200, 210), "fire": (255, 140, 40), "gas": (150, 175, 40), "geyser": (90, 85, 40)}[self.style]
            w.add(Particle("smoke", x + rnd.uniform(-0.3, 0.3), y + rnd.uniform(-0.3, 0.3), 0.1, 0, 0, 0.8, 0.6, c, 0.15))
        if st != "blast":
            return
        cyc = int(self.t / self.period)
        if cyc != self.cyc:
            self.cyc = cyc
            if self.near_player(w, 9):
                w.snd("trap_vent" if self.style != "geyser" else "bubble", x, y, 0.9)
        if self.style == "steam":
            for _ in range(3):
                if rnd.random() < dt * 30:
                    w.add(Particle("smoke", x + rnd.uniform(-0.2, 0.2), y + rnd.uniform(-0.2, 0.2), 0.2, rnd.uniform(-0.3, 0.3),
                                   rnd.uniform(-0.3, 0.3), rnd.uniform(3, 5), rnd.uniform(0.6, 1.0), (215, 215, 225), rnd.uniform(0.2, 0.35)))
            self.harm(w, x, y, 0.6, 10, 20, knock=11, cd=0.5)
        elif self.style == "fire":
            for _ in range(3):
                if rnd.random() < dt * 30:
                    w.add(Particle("fire", x + rnd.uniform(-0.2, 0.2), y + rnd.uniform(-0.2, 0.2), 0.2, rnd.uniform(-0.4, 0.4),
                                   rnd.uniform(-0.4, 0.4), rnd.uniform(3, 6), rnd.uniform(0.4, 0.7), (255, 130, 30), rnd.uniform(12, 22)))
            self.harm(w, x, y, 0.6, 14, 22, knock=6, cd=0.4)
            for e in enemies_in(w, x, y, 0.6):
                e.burn = max(e.burn, 2.5)
                e.burn_dps = max(e.burn_dps, 6)
            if rnd.random() < dt * 2:
                w.hazards.append([x + rnd.uniform(-0.5, 0.5), y + rnd.uniform(-0.5, 0.5), 0.45, 1.6, "fire", 6])
        elif self.style == "gas":
            self.gas_t -= dt
            if self.gas_t <= 0:
                self.gas_t = 0.22
                a = rnd.random() * math.tau
                w.add_gas(x + math.cos(a) * 0.3, y + math.sin(a) * 0.3, 9, math.cos(a) * 6, math.sin(a) * 6)
            if rnd.random() < dt * 20:
                w.add(Particle("smoke", x, y, 0.2, rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(1, 2), 1.0, (150, 175, 40), 0.3))
        else:   # geyser
            for _ in range(3):
                if rnd.random() < dt * 30:
                    a = rnd.random() * math.tau
                    s = rnd.uniform(0.5, 2)
                    w.add(Particle("blood", x, y, 0.3, math.cos(a) * s, math.sin(a) * s, rnd.uniform(5, 8), 1.2, (85, 80, 35), rnd.uniform(3, 6)))
            if self.harm(w, x, y, 0.65, 9, 18, knock=15, cd=0.5):
                pass
            if rnd.random() < dt * 3:
                w.splat(x + rnd.uniform(-0.8, 0.8), y + rnd.uniform(-0.8, 0.8), (60, 58, 28), 0.25)


# ---------------------------------------------------------------- reactor (shoot it!)
REACTOR_RADIUS = 12.0     # tiles flattened when a reactor goes up
REACTOR_FUSE = 4.5        # seconds of warning (chain reactions: REACTOR_CHAIN)
REACTOR_CHAIN = 1.5


class Reactor(Trap):
    shootable = True
    solid = True

    def __init__(self, style, x, y):
        super().__init__("reactor", style, x, y)
        self.sprite = "trap_radreactor" if style == "rad" else "trap_chemreactor"
        self.hp = 45
        self.fuse = -1.0
        self.r = 0.42
        self.klaxon_t = 0.0

    def hit(self, w, dmg, vx=0.0, vy=0.0):
        if not self.alive:
            return
        self.hp -= dmg
        self.flash = 0.06
        from world import Particle
        for _ in range(3):
            a = rnd.random() * math.tau
            w.add(Particle("spark", self.x, self.y, 0.6, math.cos(a) * 3, math.sin(a) * 3, rnd.uniform(1, 3), 0.3, (255, 230, 150), 2))
        if self.hp <= 0 and self.fuse < 0:
            self.fuse = REACTOR_FUSE if dmg < 100 else REACTOR_CHAIN       # another reactor's blast sets it off sooner
            self.klaxon_t = 0.0
            col = (255, 210, 60) if self.style == "chem" else (140, 255, 90)
            w.warnings.append([self.x, self.y, REACTOR_RADIUS, self.fuse, self.fuse, col])
            w.message("REACTOR CRITICAL - GET CLEAR!", col)
        else:
            w.snd("hit_metal", self.x, self.y, 0.5)

    def update(self, w, dt):
        super().update(w, dt)
        from world import Particle
        col = (180, 255, 60) if self.style == "chem" else (90, 255, 120)
        if self.fuse >= 0:
            self.fuse -= dt
            self.klaxon_t -= dt
            if self.klaxon_t <= 0:
                self.klaxon_t = 1.0
                w.snd("klaxon", self.x, self.y, 1.0)
            w.shake = max(w.shake, 1.5 + 3.0 * max(0.0, 1.0 - self.fuse / REACTOR_FUSE))
            if rnd.random() < dt * 25:
                w.add(Particle("smoke", self.x, self.y, 1.0, rnd.uniform(-1, 1), rnd.uniform(-1, 1), 1.5, 0.8, col, 0.25))
            if self.fuse < 0:
                self.detonate(w, col)
        elif rnd.random() < dt * 1.5:
            w.add(Particle("glow", self.x + rnd.uniform(-0.3, 0.3), self.y + rnd.uniform(-0.3, 0.3), 1.05, 0, 0, 0.8, 0.8, col, 2))

    def detonate(self, w, col):
        self.alive = False
        L = w.level
        cx, cy = int(self.x), int(self.y)
        if L.solid[L.i(cx, cy)] == 2:
            L.solid[L.i(cx, cy)] = 0
            w.flow_tile = None
        w.gibs_from("barrel", self.x, self.y, 0.8, force=2.0)
        x, y = self.x, self.y
        w.cataclysm(x, y, REACTOR_RADIUS, col)
        # the contamination it leaves behind
        if self.style == "rad":
            w.hazards.append([x, y, 5.0, 16.0, "rad", 9, 16.0])
        else:
            for k in range(18):
                a = k / 18 * math.tau
                d = rnd.uniform(1.0, 5.0)
                w.add_gas(x + math.cos(a) * d, y + math.sin(a) * d, 9, math.cos(a) * 2, math.sin(a) * 2)
        w.splat(x, y, (30, 60, 10) if self.style == "chem" else (20, 70, 30), 3.0)


# ---------------------------------------------------------------- pop-up turret
class Turret(Trap):
    sprite = "trap_turret"

    def __init__(self, style, x, y):
        super().__init__("turret", style, x, y)
        self.state = "hidden"
        self.k = 0.0          # rise 0..1
        self.timer = 0.0
        self.aim = (1.0, 0.0)
        self.burst = 0
        self.shot_t = 0.0
        self.hp = 40
        self.r = 0.35

    @property
    def shootable(self):
        return self.state in ("rising", "active", "sinking") and self.k > 0.4

    def hit(self, w, dmg, vx=0.0, vy=0.0):
        if not self.shootable or not self.alive:
            return
        self.hp -= dmg
        self.flash = 0.06
        w.snd("hit_metal", self.x, self.y, 0.5)
        if self.hp <= 0:
            self.alive = False
            w.gibs_from("turret", self.x, self.y, 0.4, force=1.5)
            w.explode(self.x, self.y, 1.0, 10, (255, 160, 60), hurt_player=False, small=True, quiet=True)
            w.score += 150

    def update(self, w, dt):
        super().update(w, dt)
        self.timer -= dt
        tgt = None
        best = 7.0
        for p in w.players:
            if p.alive:
                d = math.hypot(p.x - self.x, p.y - self.y)
                if d < best and los(w.level, self.x, self.y, p.x, p.y):
                    tgt, best = p, d
        if self.state == "hidden":
            if tgt is not None and self.timer <= 0:
                self.state = "rising"
                w.snd("servo", self.x, self.y)
        elif self.state == "rising":
            self.k = min(1.0, self.k + dt * 2.2)
            if self.k >= 1:
                self.state, self.timer = "active", 5.0
                w.snd("turret_beep", self.x, self.y, 0.6)
        elif self.state == "active":
            if tgt is not None:
                ax, ay = tgt.x - self.x, tgt.y - self.y
                d = math.hypot(ax, ay) or 1
                cur = math.atan2(self.aim[1], self.aim[0])
                want = math.atan2(ay, ax)
                diff = (want - cur + math.pi) % math.tau - math.pi
                cur += max(-dt * 3.5, min(dt * 3.5, diff))
                self.aim = (math.cos(cur), math.sin(cur))
                self.shot_t -= dt
                if self.shot_t <= 0 and abs(diff) < 0.35:
                    self.fire(w)
                    self.burst += 1
                    self.shot_t = 0.11 if self.burst % 4 else 0.9
            if self.timer <= 0:
                self.state = "sinking"
                w.snd("servo", self.x, self.y, 0.7)
        elif self.state == "sinking":
            self.k = max(0.0, self.k - dt * 2.2)
            if self.k <= 0:
                self.state, self.timer = "hidden", 2.5

    def fire(self, w):
        from world import Proj, Particle
        ax, ay = self.aim
        sx, sy = self.x + ax * 0.5, self.y + ay * 0.5
        a = math.atan2(ay, ax) + rnd.uniform(-0.06, 0.06)
        pr = Proj("bolt", sx, sy, 0.45, math.cos(a) * 10, math.sin(a) * 10, 7, hostile=True, life=1.4, color=(255, 190, 80), r=0.12)
        w.projs.append(pr)
        w.add(Particle("glow", sx, sy, 0.45, 0, 0, 0, 0.06, (255, 200, 100), 3))
        w.snd("turret_shot", self.x, self.y, 0.6)

    def frame(self):
        return min(3, int(self.k * 3.99))


# ---------------------------------------------------------------- tentacle
class Tentacle(Trap):
    sprite = "trap_hole"

    def __init__(self, style, x, y):
        super().__init__("tentacle", style, x, y)
        self.col, self.tip, self.hole_tint = TENTACLE[style]
        self.state = "lurk"
        self.k = 0.0             # how far emerged 0..1
        self.timer = 0.0
        self.attacks = 0
        self.hp = self.max_hp = 70
        self.tx, self.ty = x + 1, y
        self.lean = 0.0          # -1 reared back .. 1 slammed down
        self.r = 0.4
        self.target = None

    @property
    def shootable(self):
        return self.k > 0.5 and self.state != "dead"

    def hit(self, w, dmg, vx=0.0, vy=0.0):
        if not self.shootable:
            return
        self.hp -= dmg
        self.flash = 0.06
        w.spray(self.x, self.y, 1.0, self.col, 5, 3)
        w.snd("hit_flesh", self.x, self.y, 0.6)
        if self.hp <= 0:
            self.state, self.timer = "dead", 9.0
            w.spray(self.x, self.y, 1.2, self.col, 40, 5)
            w.gibs_from("leech", self.x, self.y, 1.0, force=1.3)
            w.snd("death_leech", self.x, self.y)
            w.score += 200

    def update(self, w, dt):
        super().update(w, dt)
        self.timer -= dt
        alive = [p for p in w.players if p.alive]
        near = min(alive, key=lambda p: math.hypot(p.x - self.x, p.y - self.y), default=None)
        dn = math.hypot(near.x - self.x, near.y - self.y) if near else 99
        st = self.state
        if st == "dead":
            self.k = max(0.0, self.k - dt * 3)
            if self.timer <= 0:
                self.state, self.hp = "lurk", self.max_hp
            return
        if st == "lurk":
            self.k = max(0.0, self.k - dt * 2)
            if dn < 3.4 and self.timer <= 0:
                self.state = "emerge"
                w.snd("tentacle", self.x, self.y)
                w.spray(self.x, self.y, 0.3, self.col, 16, 4)
        elif st == "emerge":
            self.k = min(1.0, self.k + dt * 2.5)
            self.lean = 0.0
            if self.k >= 1:
                self.state, self.timer = "idle", 0.5
        elif st == "idle":
            self.lean += (0 - self.lean) * min(1, dt * 6)
            if dn > 5.5:
                self.state, self.timer = "lurk", 1.5
            elif self.timer <= 0 and near is not None:
                self.target = near
                self.tx, self.ty = near.x, near.y
                self.state, self.timer = "windup", 0.6
        elif st == "windup":
            self.lean = max(-1.0, self.lean - dt * 3)
            if self.target is not None:      # tracks you while rearing back
                self.tx += (self.target.x - self.tx) * min(1, dt * 4)
                self.ty += (self.target.y - self.ty) * min(1, dt * 4)
            if self.timer <= 0:
                self.attacks += 1
                self.state, self.timer = ("grab" if self.attacks % 3 == 0 else "slam"), 0.15
        elif st in ("slam", "grab"):
            self.lean = min(1.0, self.lean + dt * 14)
            if self.timer <= 0 and self.lean >= 1:
                self.strike(w, st == "grab")
                self.state, self.timer = "recover", 0.7
        elif st == "recover":
            self.lean += (0 - self.lean) * min(1, dt * 3)
            if self.timer <= 0:
                self.state, self.timer = "idle", rnd.uniform(0.3, 0.9)

    def reach(self):
        dx, dy = self.tx - self.x, self.ty - self.y
        d = math.hypot(dx, dy) or 1
        n = min(3.2, d)
        return self.x + dx / d * n, self.y + dy / d * n

    def strike(self, w, grab):
        ex, ey = self.reach()
        w.shake = max(w.shake, 5)
        w.snd("stomp", ex, ey, 0.7)
        w.splat(ex, ey, self.col, 0.4)
        for p in w.players:
            if p.alive and dist_seg(p.x, p.y, self.x, self.y, ex, ey) < 0.45 + p.R:
                if grab:
                    w.player_effect("pull", self, who=p)
                    w.hurt_player(6, ex, ey, 0, who=p)
                else:
                    w.hurt_player(22, self.x, self.y, 10, who=p)
        for e in list(w.enemies):
            if e.alive and e.state != "dormant" and dist_seg(e.x, e.y, self.x, self.y, ex, ey) < 0.45 + e.r:
                e.hit(w, 40, (e.x - self.x) * 20, (e.y - self.y) * 20)
        from world import Particle
        for _ in range(10):
            a = rnd.random() * math.tau
            w.add(Particle("chunk", ex, ey, 0.1, math.cos(a) * 3, math.sin(a) * 3, rnd.uniform(2, 4), 0.8, (70, 60, 50), 3))

    def points(self, time, n=14):
        """3D spine (x, y, z) from the hole to the tip."""
        if self.k <= 0.01:
            return []
        ex, ey = self.reach()
        dx, dy = ex - self.x, ey - self.y
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        H = 1.7 * self.k
        pts = []
        lean = self.lean
        for i in range(n + 1):
            s = i / n
            sway = math.sin(time * 2.2 + s * 3.5) * 0.25 * s
            # upright pose: rises straight, curling slightly; reared back pose leans away; slam lies along the ground
            if lean >= 0:
                up_x = self.x + (-uy * sway) + ux * s * 0.3
                up_y = self.y + (ux * sway) + uy * s * 0.3
                up_z = H * s
                sl_x, sl_y = self.x + dx * s, self.y + dy * s
                sl_z = 0.15 + math.sin(s * math.pi) * 0.4 * (1 - lean)
                t_ = lean
            else:
                up_x = self.x + (-uy * sway) + ux * s * 0.3
                up_y = self.y + (ux * sway) + uy * s * 0.3
                up_z = H * s
                sl_x = self.x - ux * s * s * 0.9
                sl_y = self.y - uy * s * s * 0.9
                sl_z = H * s * 1.05
                t_ = -lean
            pts.append((up_x + (sl_x - up_x) * t_, up_y + (sl_y - up_y) * t_, up_z + (sl_z - up_z) * t_ * (self.k)))
        return pts


# ---------------------------------------------------------------- floor maw
class Maw(Trap):
    sprite = "trap_maw"

    def __init__(self, style, x, y):
        super().__init__("maw", style, x, y)
        self.state = "open"
        self.timer = 0.0

    def frame(self):
        if self.state == "snap":
            return min(3, 1 + int((0.12 - max(0, self.timer)) / 0.04))
        if self.state == "shut":
            return 3
        if self.state == "reopen":
            return 2 if self.timer > 0.15 else 1
        return 0

    def update(self, w, dt):
        super().update(w, dt)
        self.timer -= dt
        if self.state == "open":
            if players_in(w, self.x, self.y, 0.35) or enemies_in(w, self.x, self.y, 0.3):
                self.state, self.timer = "trig", 0.22
        elif self.state == "trig":
            if self.timer <= 0:
                self.state, self.timer = "snap", 0.12
                w.snd("chomp", self.x, self.y)
                for p in players_in(w, self.x, self.y, 0.55):
                    w.hurt_player(24, self.x, self.y, 7, who=p)
                for e in enemies_in(w, self.x, self.y, 0.55):
                    e.hit(w, 60, 0, 0)
                    w.spray(e.x, e.y, 0.4, e.blood, 24, 4)
                w.spray(self.x, self.y, 0.3, (120, 10, 10), 10, 3)
        elif self.state == "snap":
            if self.timer <= 0:
                self.state, self.timer = "shut", 0.7
        elif self.state == "shut":
            if self.timer <= 0:
                self.state, self.timer = "reopen", 0.3
        elif self.state == "reopen":
            if self.timer <= 0:
                self.state, self.timer = "cool", 1.0
        elif self.state == "cool":
            if self.timer <= 0:
                self.state = "open"


# ---------------------------------------------------------------- grasping hands
class Hands(Trap):
    sprite = "trap_hands"

    def __init__(self, style, x, y):
        super().__init__("hands", style, x, y)
        self.state = "under"
        self.k = 0.0
        self.timer = 0.0

    def frame(self):
        return min(3, int(self.k * 3.99))

    def update(self, w, dt):
        super().update(w, dt)
        self.timer -= dt
        if self.state == "under":
            self.k = max(0.0, self.k - dt * 3)
            if self.timer <= 0 and (players_in(w, self.x, self.y, 0.55) or enemies_in(w, self.x, self.y, 0.5)):
                self.state, self.timer = "grip", 2.2
                w.snd("bones", self.x, self.y)
                w.spray(self.x, self.y, 0.2, (60, 45, 30), 12, 3)
        elif self.state == "grip":
            self.k = min(1.0, self.k + dt * 5)
            for p in players_in(w, self.x, self.y, 0.7):
                if "mire" not in p.status:
                    w.message("GRABBED!", (200, 190, 160))
                p.status["mire"] = 0.25
                p.kbx += (self.x - p.x) * dt * 20       # dragged toward the middle
                p.kby += (self.y - p.y) * dt * 20
                p.hp -= 6 * dt * p.mult("aegis")
                w.check_player_death(self.x, self.y, p)
            for e in enemies_in(w, self.x, self.y, 0.7):
                e.slow = max(e.slow, 0.5)
                w.dot(e, 10 * dt)
            if self.timer <= 0:
                self.state, self.timer = "under", 2.5


# ---------------------------------------------------------------- thorns
class Thorns(Trap):
    sprite = "trap_thorns"

    def __init__(self, style, x, y):
        super().__init__("thorns", style, x, y)

    def update(self, w, dt):
        super().update(w, dt)
        for p in players_in(w, self.x, self.y, 0.4):
            if p.invuln <= 0:
                w.hurt_player(8, self.x, self.y, 6, who=p)
                w.spray(p.x, p.y, 0.4, (20, 18, 22), 4, 2)
        for e in enemies_in(w, self.x, self.y, 0.4):
            w.dot(e, 14 * dt)
            e.slow = max(e.slow, 0.3)
            if rnd.random() < dt * 4:
                w.spray(e.x, e.y, 0.4, e.blood, 3, 2)


# ---------------------------------------------------------------- tesla coil
class Tesla(Trap):
    sprite = "trap_tesla"
    solid = True

    def __init__(self, style, x, y):
        super().__init__("tesla", style, x, y)
        self.period = rnd.uniform(2.8, 3.6)
        self.arcs = []           # [x2, y2, life]
        self.cyc = -1

    def charge(self):
        c = self.t % self.period
        return max(0.0, (c - (self.period - 1.1)) / 1.1)

    def update(self, w, dt):
        super().update(w, dt)
        from world import Particle
        for a in self.arcs:
            a[2] -= dt
        self.arcs = [a for a in self.arcs if a[2] > 0]
        ch = self.charge()
        if ch > 0 and rnd.random() < dt * 20 * ch:
            a = rnd.random() * math.tau
            w.add(Particle("spark", self.x, self.y, 1.05, math.cos(a) * 2, math.sin(a) * 2, rnd.uniform(0, 2), 0.2, (170, 220, 255), 2))
        cyc = int(self.t / self.period)
        if cyc != self.cyc:
            self.cyc = cyc
            if self.t < self.period:
                return
            victims = []
            for p in w.players:
                if p.alive and math.hypot(p.x - self.x, p.y - self.y) < 3.8 and los(w.level, self.x, self.y, p.x, p.y):
                    victims.append((math.hypot(p.x - self.x, p.y - self.y), p))
            for e in w.enemies:
                if e.alive and e.state != "dormant" and math.hypot(e.x - self.x, e.y - self.y) < 3.8 and los(w.level, self.x, self.y, e.x, e.y):
                    victims.append((math.hypot(e.x - self.x, e.y - self.y), e))
            victims.sort(key=lambda v: v[0])
            if not victims:
                a = rnd.random() * math.tau
                self.arcs.append([self.x + math.cos(a) * 1.5, self.y + math.sin(a) * 1.5, 0.15])
                if self.near_player(w, 8):
                    w.snd("zap", self.x, self.y, 0.5)
                return
            w.snd("zap", self.x, self.y)
            for _, v in victims[:3]:
                self.arcs.append([v.x, v.y, 0.22])
                if v in w.players:
                    w.hurt_player(14, self.x, self.y, 6, who=v)
                else:
                    v.hit(w, 30, (v.x - self.x) * 10, (v.y - self.y) * 10)
                    v.slow = max(getattr(v, "slow", 0), 1.0)
                for _ in range(8):
                    a = rnd.random() * math.tau
                    w.add(Particle("spark", v.x, v.y, 0.6, math.cos(a) * 4, math.sin(a) * 4, rnd.uniform(1, 3), 0.3, (170, 220, 255), 2))


# ---------------------------------------------------------------- pendulum blade
class Pendulum(Trap):
    sprite = "trap_pendulum"

    def __init__(self, style, x, y, axis):
        super().__init__("pendulum", style, x, y)
        self.axis = axis
        self.period = rnd.uniform(2.0, 2.6)
        self.whoosh = 0

    def phase(self):
        return (self.t / self.period) * math.tau

    def frame(self):
        return int((self.t / self.period) * 12) % 12

    def blade(self):
        th = 1.0 * math.sin(self.phase())
        d = 1.4 * math.sin(th)
        dx, dy = (1, 0) if self.axis == 0 else (0, 1)
        return self.x + dx * d, self.y + dy * d, math.cos(th)

    def update(self, w, dt):
        super().update(w, dt)
        bx, by, c = self.blade()
        if c > 0.78:
            ph = int(self.phase() / math.pi)
            if ph != self.whoosh:
                self.whoosh = ph
                if self.near_player(w, 7):
                    w.snd("lunge", bx, by, 0.6)
            dx, dy = (1, 0) if self.axis == 0 else (0, 1)
            sgn = 1 if math.cos(self.phase()) > 0 else -1
            for e in enemies_in(w, bx, by, 0.45):
                if self.cool.get(id(e), 0) <= 0:
                    w.spray(e.x, e.y, 0.7, e.blood, 26, 5)
            self.harm(w, bx, by, 0.45, 28, 70, knock=13, cd=0.5, kx=dx * sgn, ky=dy * sgn)


# ---------------------------------------------------------------- laser grid
class Laser(Trap):
    def __init__(self, style, x0, y0, x1, y1):
        super().__init__("laser", style, (x0 + x1) / 2, (y0 + y1) / 2)
        self.a, self.b = (x0, y0), (x1, y1)
        self.period = rnd.uniform(3.6, 4.4)
        self.cyc = -1

    def state(self):
        c = self.t % self.period
        if c < self.period - 2.4:
            return "off"
        if c < self.period - 1.8:
            return "warn"
        return "on"

    def update(self, w, dt):
        super().update(w, dt)
        if self.state() != "on":
            return
        cyc = int(self.t / self.period)
        if cyc != self.cyc:
            self.cyc = cyc
            if self.near_player(w, 8):
                w.snd("shot_beam", self.x, self.y, 0.5)
        (ax, ay), (bx, by) = self.a, self.b
        for p in w.players:
            if p.alive and dist_seg(p.x, p.y, ax, ay, bx, by) < 0.18 + p.R:
                if p.invuln <= 0:
                    w.hurt_player(18, p.x - (by - ay) * 0.1, p.y + (bx - ax) * 0.1, 4, who=p)
                    w.snd("sizzle", p.x, p.y, 0.5)
        for e in w.enemies:
            if e.alive and e.state != "dormant" and dist_seg(e.x, e.y, ax, ay, bx, by) < 0.18 + e.r:
                if self.cool.get(id(e), 0) <= 0:
                    self.cool[id(e)] = 0.3
                    e.hit(w, 25, 0, 0)
                    e.burn = max(e.burn, 1.5)
                    e.burn_dps = max(e.burn_dps, 5)


# ---------------------------------------------------------------- gusts of wind
class Wind(Trap):
    def __init__(self, style, room):
        super().__init__("wind", style, room.x + room.w / 2, room.y + room.h / 2)
        self.rx, self.ry, self.rw, self.rh = room.x, room.y, room.w, room.h
        self.period = rnd.uniform(5.0, 6.5)
        self.d = (1, 0)
        self.cyc = -1
        self.col = (255, 190, 230) if style == "storm" else (190, 185, 180)

    def inside(self, x, y):
        return self.rx <= x < self.rx + self.rw and self.ry <= y < self.ry + self.rh

    def state(self):
        c = self.t % self.period
        if c < self.period - 2.8:
            return "calm"
        if c < self.period - 2.2:
            return "warn"
        return "gust"

    def update(self, w, dt):
        super().update(w, dt)
        from world import Particle
        st = self.state()
        cyc = int(self.t / self.period)
        if st == "warn" and cyc != self.cyc:
            self.cyc = cyc
            self.d = rnd.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
            if any(p.alive and self.inside(p.x, p.y) for p in w.players):
                w.snd("trap_vent", self.x, self.y, 0.6)
        if st == "calm":
            return
        dx, dy = self.d
        n = 1 if st == "warn" else 5
        for _ in range(n):
            if rnd.random() < dt * 20:
                x = self.rx + rnd.random() * self.rw
                y = self.ry + rnd.random() * self.rh
                w.add(Particle("smoke" if st == "gust" else "glow", x, y, rnd.uniform(0.2, 1.2), dx * rnd.uniform(6, 10), dy * rnd.uniform(6, 10),
                               0, 0.5, self.col, 0.12 if st == "gust" else 2))
        if st != "gust":
            return
        L = w.level
        for p in w.players:
            if p.alive and self.inside(p.x, p.y):
                p.kbx += dx * dt * 40
                p.kby += dy * dt * 40
                p.kbx = max(-6, min(6, p.kbx))
                p.kby = max(-6, min(6, p.kby))
        fl = _flyers()
        for e in w.enemies:
            if e.alive and self.inside(e.x, e.y):
                k = 4.5 if e.kind in fl else 2.5
                nx, ny = e.x + dx * k * dt, e.y + dy * k * dt
                if not L.is_solid(int(nx), int(ny)):
                    e.x, e.y = nx, ny


# ---------------------------------------------------------------- strikes from above (level-wide)
STRIKE_WARN = 2.2        # seconds between the target marker appearing and impact
STRIKE_FALL = 0.8        # the falling object is visible for the last this-many seconds


class Strikes(Trap):
    def __init__(self, style, depth):
        super().__init__("strike", style, 0, 0)
        self.pending = []        # [x, y, t_left]
        self.bolts = []          # lightning flashes [x, y, life]
        self.next = 5.0
        self.depth = depth
        self.col = {"icicle": (170, 220, 255), "lightning": (220, 210, 255), "meteor": (255, 120, 40)}[style]

    def update(self, w, dt):
        super().update(w, dt)
        self.next -= dt
        for b in self.bolts:
            b[2] -= dt
        self.bolts = [b for b in self.bolts if b[2] > 0]
        L = w.level
        alive = [p for p in w.players if p.alive]
        if self.next <= 0 and alive:
            self.next = rnd.uniform(2.5, 5.0) / (1 + 0.06 * self.depth)
            p = rnd.choice(alive)
            for _ in range(8):
                a, d = rnd.random() * math.tau, rnd.uniform(0.0, 2.5)
                x, y = p.x + math.cos(a) * d, p.y + math.sin(a) * d
                if not L.is_solid(int(x), int(y)):
                    T = STRIKE_WARN
                    self.pending.append([x, y, T])
                    w.warnings.append([x, y, 0.95, T, T, self.col])
                    w.snd({"icicle": "crumble", "lightning": "zap", "meteor": "fireball"}[self.style], x, y, 0.35)
                    break
        keep = []
        for s in self.pending:
            s[2] -= dt
            if s[2] > 0:
                keep.append(s)
            else:
                self.impact(w, s[0], s[1])
        self.pending = keep

    def impact(self, w, x, y):
        from world import Particle
        st = self.style
        if st == "icicle":
            w.snd("shatter", x, y)
            for _ in range(16):
                a = rnd.random() * math.tau
                s = rnd.uniform(2, 5)
                w.add(Particle("chunk", x, y, 0.4, math.cos(a) * s, math.sin(a) * s, rnd.uniform(2, 4), 0.9, (200, 230, 255), 3))
            w.splat(x, y, (175, 210, 235), 0.4)
            for p in players_in(w, x, y, 0.85):
                w.hurt_player(18, x, y, 6, who=p)
                w.player_effect("chill", None, who=p)
            for e in enemies_in(w, x, y, 0.85, ground=False):
                e.hit(w, 40, 0, 0)
                if hasattr(e, "chill"):
                    e.chill += 0.6
        elif st == "lightning":
            w.snd("thunder", x, y)
            w.shake = max(w.shake, 7)
            self.bolts.append([x, y, 0.25])
            w.add(Particle("ring", x, y, 0.05, 3.0, 0, 0, 0.3, self.col, 0.1))
            for _ in range(14):
                a = rnd.random() * math.tau
                w.add(Particle("spark", x, y, 0.2, math.cos(a) * 6, math.sin(a) * 6, rnd.uniform(2, 5), 0.4, self.col, 2))
            w.splat(x, y, (20, 18, 25), 0.5)
            for p in players_in(w, x, y, 0.95):
                w.hurt_player(22, x, y, 8, who=p)
            for e in enemies_in(w, x, y, 0.95, ground=False):
                e.hit(w, 55, 0, 0)
                e.burn = max(e.burn, 2.0)
                e.burn_dps = max(e.burn_dps, 5)
        else:
            w.explode(x, y, 1.1, 35, (255, 120, 40), hurt_player=True, player_dmg=18, small=True)
            for _ in range(3):
                w.hazards.append([x + rnd.uniform(-0.5, 0.5), y + rnd.uniform(-0.5, 0.5), 0.45, 2.5, "fire", 6])
            w.splat(x, y, (22, 16, 12), 0.5)

    def falling(self):
        """Things currently falling: (x, y, height 0..1) for the renderer."""
        return [(s[0], s[1], s[2] / STRIKE_FALL) for s in self.pending if s[2] < STRIKE_FALL]


# ================================================================ placement
def place(L, biome, depth, rng):
    """Pick and place this level's traps. Never in the start room, on the exit pad or on props."""
    kinds = BIOME_TRAPS.get(biome)
    if not kinds:
        return []
    start = L.rooms[0]
    ex, ey = int(L.exit[0]), int(L.exit[1])
    taken = set()
    spawn_cells = {(int(s[1]), int(s[2])) for s in L.spawners} | {(int(p[1]), int(p[2])) for p in L.pickups}
    boss = (int(L.boss_spot[0]), int(L.boss_spot[1])) if L.boss_spot else None

    def ok(x, y, margin=0):
        if not (1 <= x < L.W - 1 and 1 <= y < L.H - 1):
            return False
        if L.solid[L.i(x, y)] != 0 or (x, y) in L.props or (x, y) in taken or (x, y) in spawn_cells:
            return False
        if start.x - 2 - margin <= x < start.x + start.w + 2 + margin and start.y - 2 - margin <= y < start.y + start.h + 2 + margin:
            return False
        if abs(x - ex) + abs(y - ey) <= 3:
            return False
        if boss and abs(x - boss[0]) + abs(y - boss[1]) <= 1:
            return False
        return True

    rooms = [r for r in L.rooms[1:]]
    floor_cells = [(x, y) for x in range(L.W) for y in range(L.H) if ok(x, y)]
    if not floor_cells:
        return []
    traps = []
    total = min(10, 4 + depth)
    bag = []
    for mech, style, wgt in kinds:
        if mech == "strike":
            traps.append(Strikes(style, depth))
            continue
        bag.append((mech, style, wgt))

    def run(x, y, axis, wall_ends=False):
        dx, dy = (1, 0) if axis == 0 else (0, 1)
        a = b = 0
        while ok(x - dx * (a + 1), y - dy * (a + 1)) and a < 4:
            a += 1
        while ok(x + dx * (b + 1), y + dy * (b + 1)) and b < 4:
            b += 1
        if wall_ends:
            if not (L.is_solid(x - dx * (a + 1), y - dy * (a + 1)) and L.is_solid(x + dx * (b + 1), y + dy * (b + 1))):
                return None
        return (x - dx * a, y - dy * a), (x + dx * b, y + dy * b), a + b + 1

    def claim(cells):
        for c in cells:
            taken.add(c)

    def weighted_pick():
        tot = sum(wt for _, _, wt in bag)
        r = rng.random() * tot
        for m, s, wt in bag:
            r -= wt
            if r <= 0:
                return m, s
        return bag[-1][:2]

    tries = 0
    placed = 0
    while placed < total and tries < total * 30 and bag:
        tries += 1
        mech, style = weighted_pick()
        x, y = rng.choice(floor_cells)
        if not ok(x, y):
            continue
        if mech == "spikes":
            axis = rng.randint(0, 1)
            pattern = rng.choice(("line", "line", "checker"))
            cells = []
            if pattern == "line":
                rr = run(x, y, axis)
                if rr and rr[2] >= 3:
                    (ax, ay), (bx, by), n = rr
                    cells = [(ax + i * (axis == 0), ay + i * (axis == 1)) for i in range(min(n, 5))]
            else:
                for dx in range(3):
                    for dy in range(3):
                        if ok(x + dx, y + dy) and (pattern == "block" or (dx + dy) % 2 == 0):
                            cells.append((x + dx, y + dy))
            if len(cells) < 3:
                continue
            per = rng.uniform(2.8, 3.6)
            for i, (cx, cy) in enumerate(cells):
                off = (i * 0.25) if pattern == "line" else ((cx + cy) % 2) * per / 2
                traps.append(Spikes(style, cx + 0.5, cy + 0.5, off, per))
            claim(cells)
        elif mech in ("saw",):
            rr = run(x, y, rng.randint(0, 1))
            if not rr or rr[2] < 3:
                continue
            (ax, ay), (bx, by), n = rr
            traps.append(Saw(style, ax + 0.5, ay + 0.5, bx + 0.5, by + 0.5))
            claim([(ax + i * (bx != ax), ay + i * (by != ay)) for i in range(n)])
        elif mech == "laser":
            axis = rng.randint(0, 1)
            rr = run(x, y, axis, wall_ends=True)
            if not rr or not 2 <= rr[2] <= 9:
                continue
            (ax, ay), (bx, by), n = rr
            dx, dy = (0.5, 0) if axis == 0 else (0, 0.5)
            traps.append(Laser(style, ax + 0.5 - dx, ay + 0.5 - dy, bx + 0.5 + dx, by + 0.5 + dy))
            claim([(ax + i * (axis == 0), ay + i * (axis == 1)) for i in range(n)])
        elif mech == "pendulum":
            axis = rng.randint(0, 1)
            dx, dy = (1, 0) if axis == 0 else (0, 1)
            if not all(ok(x + dx * k, y + dy * k) for k in (-1, 1)):
                continue
            traps.append(Pendulum(style, x + 0.5, y + 0.5, axis))
            claim([(x, y), (x + dx, y + dy), (x - dx, y - dy)])
        elif mech == "pool":
            cells = [(x, y)]
            target = rng.randint(5, 13)
            for _ in range(target * 6):
                if len(cells) >= target:
                    break
                cx, cy = rng.choice(cells)
                nx, ny = cx + rng.choice((-1, 0, 1)), cy + rng.choice((-1, 0, 1))
                if (nx, ny) not in cells and ok(nx, ny, 1):
                    cells.append((nx, ny))
            if len(cells) < 4:
                continue
            traps.append(Pool(style, cells))
            claim(cells)
        elif mech == "wind":
            rms = [r for r in rooms if not any(isinstance(t, Wind) and t.rx == r.x and t.ry == r.y for t in traps)]
            if not rms:
                continue
            traps.append(Wind(style, rng.choice(rms)))
        elif mech in ("reactor", "tesla"):
            if not L.open_around(x, y):
                continue
            t = Reactor(style, x + 0.5, y + 0.5) if mech == "reactor" else Tesla(style, x + 0.5, y + 0.5)
            L.solid[L.i(x, y)] = 2
            traps.append(t)
            claim([(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)])
        else:
            cls = {"vent": Vent, "turret": Turret, "tentacle": Tentacle, "maw": Maw, "hands": Hands, "thorns": Thorns}[mech]
            n = 1
            if mech in ("thorns", "maw", "hands") and rng.random() < 0.6:
                n = rng.randint(2, 3)
            elif mech == "vent" and rng.random() < 0.4:
                n = 2
            cells = [(x, y)]
            for _ in range(n * 6):
                if len(cells) >= n:
                    break
                cx, cy = rng.choice(cells)
                nx, ny = cx + rng.choice((-2, -1, 1, 2)), cy + rng.choice((-2, -1, 1, 2))
                if (nx, ny) not in cells and ok(nx, ny):
                    cells.append((nx, ny))
            for cx, cy in cells:
                traps.append(cls(style, cx + 0.5, cy + 0.5))
            claim(cells)
        placed += 1
    return traps


def intro(biome):
    """'BEWARE: LAVA - FALLING ICICLES' line for the sector banner."""
    out = []
    for mech, style, _ in BIOME_TRAPS.get(biome, ()):
        n = NAMES[mech]
        out.append(n[style] if isinstance(n, dict) else n)
    return "  -  ".join(out)

"""Support items: one companion gadget per player.

  sawbot  - Buzzsaw Orbiter: circles you and shreds whatever it passes through
  shield  - Arc Shield: a partial ring that orbits you and swallows enemy projectiles
  medbot  - Medbot: trails behind you and slowly patches you up
  gunbot  - Gun Drone: hovers beside you and shoots at monsters

Every item rolls its own parameters (speed, strength, size, reach...) from a seed; rarity biases the rolls upward.
"""
import math
import random

import weapons as WP

# kind -> label, colour, params: name -> (lo, hi, card label, format). Rolls lerp lo..hi; lo > hi means "low is good".
KINDS = {
    "sawbot": dict(label="Buzzsaw Orbiter", color=(255, 190, 70), weight=10, params={
        "dmg":    (2.6, 6.5, "DMG", "%.1f"),
        "spin":   (2.0, 4.6, "SPIN", "%.1f rad/s"),
        "orbit":  (1.0, 1.9, "ORBIT", "%.1f m"),
        "size":   (0.85, 1.35, "SIZE", "x%.2f"),
    }),
    "shield": dict(label="Arc Shield", color=(110, 200, 255), weight=9, params={
        "arc":      (0.75, 1.6, "ARC", "%d deg"),
        "spin":     (0.9, 2.6, "SPIN", "%.1f rad/s"),
        "capacity": (5, 16, "BLOCKS", "%d"),
        "recharge": (6.0, 2.5, "REBOOT", "%.1fs"),
        "size":     (0.85, 1.3, "RADIUS", "x%.2f"),
    }),
    "medbot": dict(label="Medbot", color=(120, 255, 150), weight=8, params={
        "heal":   (0.35, 1.1, "HEAL", "%.2f/s"),
        "reach":  (1.6, 3.0, "RANGE", "%.1f m"),
        "speed":  (2.4, 5.5, "SPEED", "%.1f"),
        "size":   (0.8, 1.3, "SIZE", "x%.2f"),
    }),
    "gunbot": dict(label="Gun Drone", color=(255, 120, 90), weight=9, params={
        "dmg":    (0.9, 2.2, "DMG", "%.1f"),
        "rate":   (1.6, 4.2, "RATE", "%.1f/s"),
        "range":  (5.0, 9.0, "RANGE", "%.1f m"),
        "speed":  (3.0, 6.0, "SPEED", "%.1f"),
        "spread": (0.14, 0.03, "SPREAD", "%.2f"),
        "size":   (0.8, 1.3, "SIZE", "x%.2f"),
    }),
}
# the adjective an item gets from its best roll
ADJ = {
    "sawbot": {"dmg": "Serrated", "spin": "Whirling", "orbit": "Wide-Orbit", "size": "Hulking"},
    "shield": {"arc": "Broad", "spin": "Spinning", "capacity": "Fortified", "recharge": "Rapid-Cycle", "size": "Wide"},
    "medbot": {"heal": "Surgical", "reach": "Long-Range", "speed": "Nimble", "size": "Field"},
    "gunbot": {"dmg": "Heavy", "rate": "Rapid", "range": "Long-Range", "speed": "Agile", "spread": "Precise", "size": "Armored"},
}
UNIQUE = {"sawbot": ["Mr. Whirly", "The Lawnmower", "Grinder Prime"], "shield": ["The Umbrella", "Halo of Saint Rivet", "Bulwark-9"],
          "medbot": ["Nurse Ratchet", "Dr. Bolts", "Saint Gauze"], "gunbot": ["Little Buddy", "The Wingman", "Peacekeeper Mk.0"]}
SCALED = {"dmg", "heal", "capacity"}     # grows with item level


def targets(w, x, y, rng):
    """Live, visible monsters within rng of (x, y), nearest first."""
    out = []
    r2 = rng * rng
    for e in w.enemies:
        if e.alive and e.state != "dormant" and not getattr(e, "submerged", False):
            d2 = (e.x - x) ** 2 + (e.y - y) ** 2
            if d2 < r2:
                out.append((d2, e))
    for b in w.bosses:
        if b.alive and b.awake:
            d2 = (b.x - x) ** 2 + (b.y - y) ** 2
            if d2 < r2:
                out.append((d2, b))
    out.sort(key=lambda t: t[0])
    return [e for _, e in out]


class Support:
    def __init__(self, kind, rarity=0, level=1, seed=None):
        rng = random.Random(seed)
        self.kind, self.rarity, self.level, self.seed = kind, rarity, level, seed
        K = KINDS[kind]
        self.p = {}
        rolls = {}
        lv = 1 + 0.15 * (level - 1)
        for name, (lo, hi, _, _) in K["params"].items():
            u = 1 - (1 - rng.random()) ** (1 + 0.45 * rarity)       # rarity pushes rolls toward the good end
            rolls[name] = u
            v = lo + (hi - lo) * u
            if name in SCALED:
                v *= lv
            self.p[name] = v
        self.p["capacity"] = int(round(self.p.get("capacity", 0)))
        if rarity == 4:
            self.name = '"%s"' % rng.choice(UNIQUE[kind])
        else:
            best = max((n for n in rolls if n != "size" or len(rolls) < 2), key=lambda n: rolls[n])
            self.name = "%s %s" % (ADJ[kind][best], K["label"]) if rarity else K["label"]
        self.label = K["label"]
        self.tint = K["color"]
        # runtime state
        self.x = self.y = 0.0
        self.z = 1.0
        self.ang = rng.random() * math.tau
        self.t = 0.0
        self.hit_cd = {}
        self.charge = self.p.get("capacity", 0)
        self.down = 0.0          # shield: seconds until it comes back online
        self.regen = 0.0
        self.cd = 0.0
        self.aim = (1.0, 0.0)
        self.target = None
        self.healing = False
        self.flash = 0.0
        self.muzzle = 0.0
        self.snd_t = 0.0

    # ---- info
    @property
    def color(self):
        return WP.RARITY[self.rarity][1]

    @property
    def rarity_name(self):
        return WP.RARITY[self.rarity][0]

    @property
    def size(self):
        return self.p["size"]

    def card_lines(self):
        out = []
        for name, (lo, hi, lbl, fmt) in KINDS[self.kind]["params"].items():
            v = self.p[name]
            if name == "arc":
                v = math.degrees(v)
            out.append((lbl, fmt % v))
        return out

    def blurb(self):
        return {"sawbot": "Orbits you, shredding monsters it touches",
                "shield": "Orbiting barrier that blocks enemy shots",
                "medbot": "Follows you and slowly repairs integrity",
                "gunbot": "Hovers beside you and fires at monsters"}[self.kind]

    # ---- behaviour
    def attach(self, pl):
        self.x, self.y = pl.x, pl.y
        self.hit_cd.clear()
        self.target = None

    def radius(self):
        """sawbot orbit / shield ring radius in tiles"""
        return self.p["orbit"] if self.kind == "sawbot" else 1.0 * self.p["size"]

    def update(self, w, dt, pl):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.muzzle = max(0.0, self.muzzle - dt)
        self.snd_t = max(0.0, self.snd_t - dt)
        getattr(self, "update_" + self.kind)(w, dt, pl)

    def follow(self, w, dt, pl, tx, ty, speed):
        from world import resolve
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d > 7:                         # left behind (teleport, revive): snap back
            self.x, self.y = tx, ty
            return
        step = min(d, speed * dt * (1 + d))
        if d > 1e-6:
            self.x, self.y = resolve(w.level, self.x + dx / d * step, self.y + dy / d * step, 0.15)

    def update_sawbot(self, w, dt, pl):
        self.ang += self.p["spin"] * dt
        r = self.radius()
        self.x = pl.x + math.cos(self.ang) * r
        self.y = pl.y + math.sin(self.ang) * r
        self.z = 0.55 + math.sin(self.t * 5) * 0.04
        for k in list(self.hit_cd):
            self.hit_cd[k] -= dt
            if self.hit_cd[k] <= 0:
                del self.hit_cd[k]
        hr = 0.42 * self.p["size"]          # matches the drawn blade
        tvx, tvy = -math.sin(self.ang) * 8, math.cos(self.ang) * 8
        for e in targets(w, self.x, self.y, hr + 1.2):
            if id(e) in self.hit_cd or math.hypot(e.x - self.x, e.y - self.y) > hr + e.r:
                continue
            self.hit_cd[id(e)] = 0.28
            w._shooter = pl
            w.hit_enemy(e, self.p["dmg"] * pl.dmg_mult(), tvx, tvy, {})
            self.flash = 0.06
            from world import Particle
            for _ in range(5):
                a = self.ang + math.pi / 2 + random.uniform(-0.7, 0.7)
                s = random.uniform(3, 6)
                w.add(Particle("spark", self.x, self.y, self.z, math.cos(a) * s, math.sin(a) * s, random.uniform(1, 3), 0.25,
                               (255, 220, 140), 2))
            if self.snd_t <= 0:
                self.snd_t = 0.12
                w.snd("saw_bounce", self.x, self.y, 0.45)

    def update_shield(self, w, dt, pl):
        self.ang += self.p["spin"] * dt
        self.x, self.y = pl.x, pl.y
        cap = self.p["capacity"]
        if self.down > 0:
            self.down -= dt
            if self.down <= 0:
                self.charge = cap
                w.snd("shield_up", pl.x, pl.y, 0.6)
            return
        if self.charge < cap:                # trickle back between hits
            self.regen += dt
            if self.regen >= self.p["recharge"] * 0.5:
                self.regen = 0.0
                self.charge += 1
        r = self.radius()
        half = self.p["arc"] / 2
        band = 0.28
        for b in w.projs:
            if not b.hostile or id(b) in w.blocked or b.z > 1.9:
                continue
            hit = False
            for k in (0.0, 0.5, 1.0):        # sample along this frame's travel so fast shots can't tunnel
                px, py = b.x + b.vx * dt * k - pl.x, b.y + b.vy * dt * k - pl.y
                d = math.hypot(px, py)
                if abs(d - r) < band + b.r:
                    da = (math.atan2(py, px) - self.ang + math.pi) % math.tau - math.pi
                    if abs(da) < half + b.r / max(r, 0.3):
                        hit = True
                        break
            if not hit:
                continue
            w.blocked.add(id(b))
            self.charge -= 1
            self.regen = 0.0
            self.flash = 0.12
            from world import Particle
            for _ in range(8):
                a = random.random() * math.tau
                s = random.uniform(1.5, 4)
                w.add(Particle("glow", b.x, b.y, max(0.5, b.z), math.cos(a) * s, math.sin(a) * s, random.uniform(0, 2), 0.35,
                               (150, 220, 255), 2))
            if b.blast:
                w.explode(b.x, b.y, b.blast * 0.6, 0, (130, 200, 255), hurt_player=False, quiet=True, small=True)
            w.snd("shield_block", b.x, b.y, 0.7)
            if self.charge <= 0:
                self.down = self.p["recharge"]
                w.snd("shield_down", pl.x, pl.y, 0.8)
                w.message("ARC SHIELD OVERLOADED", (110, 200, 255))
                break

    def update_medbot(self, w, dt, pl):
        ax, ay = pl.aim
        side = math.sin(self.t * 0.7) * 0.5
        tx, ty = pl.x - ax * 0.85 - ay * side, pl.y - ay * 0.85 + ax * side
        ox, oy = self.x, self.y
        self.follow(w, dt, pl, tx, ty, self.p["speed"])
        mvx, mvy = self.x - ox, self.y - oy
        if math.hypot(mvx, mvy) > 0.002:
            self.aim = (mvx, mvy)
        self.z = 1.25 + math.sin(self.t * 3) * 0.08
        d = math.hypot(pl.x - self.x, pl.y - self.y)
        self.healing = pl.alive and pl.hp < pl.max_hp and d < self.p["reach"]
        if self.healing:
            pl.hp = min(pl.max_hp, pl.hp + self.p["heal"] * dt)
            if random.random() < dt * 4:
                from world import Particle
                w.add(Particle("glow", pl.x + random.uniform(-0.25, 0.25), pl.y + random.uniform(-0.25, 0.25), 0.9, 0, 0,
                               random.uniform(0.8, 1.6), 0.7, (120, 255, 150), 2))

    def update_gunbot(self, w, dt, pl):
        from world import Proj, Particle
        from traps import los
        ax, ay = pl.aim
        wob = math.sin(self.t * 1.3) * 0.3
        tx, ty = pl.x + ay * (0.95 + wob) - ax * 0.25, pl.y - ax * (0.95 + wob) - ay * 0.25
        self.follow(w, dt, pl, tx, ty, self.p["speed"])
        self.z = 1.55 + math.sin(self.t * 2.4) * 0.07
        self.cd = max(0.0, self.cd - dt)
        tg = self.target
        if tg is None or not tg.alive or math.hypot(tg.x - self.x, tg.y - self.y) > self.p["range"] + 1 \
                or not los(w.level, self.x, self.y, tg.x, tg.y):
            self.target = tg = next((e for e in targets(w, self.x, self.y, self.p["range"])
                                     if los(w.level, self.x, self.y, e.x, e.y)), None)
        if tg is None:
            self.aim = pl.aim
            return
        dx, dy = tg.x - self.x, tg.y - self.y
        d = math.hypot(dx, dy) or 1
        self.aim = (dx / d, dy / d)
        if self.cd <= 0:
            self.cd = 1.0 / self.p["rate"]
            a = random.uniform(-self.p["spread"], self.p["spread"])
            c, s = math.cos(a), math.sin(a)
            vx, vy = dx / d * c - dy / d * s, dx / d * s + dy / d * c
            spd = 20.0
            pr = Proj("bullet", self.x + vx * 0.25, self.y + vy * 0.25, self.z - 0.1, vx * spd, vy * spd,
                      self.p["dmg"] * pl.dmg_mult(), life=self.p["range"] / spd + 0.1, color=(255, 150, 110))
            pr.owner = pl
            w.projs.append(pr)
            self.muzzle = 0.05
            w.add(Particle("spark", self.x + vx * 0.3, self.y + vy * 0.3, self.z - 0.1, vx * 4, vy * 4, 0.5, 0.1, (255, 190, 140), 2))
            w.snd("shot_smg", self.x, self.y, 0.35)


def generate(level, rng=None, bonus=0, kind=None, rarity=None):
    rng = rng or random.Random()
    if kind is None:
        ks = list(KINDS)
        kind = rng.choices(ks, weights=[KINDS[k]["weight"] for k in ks])[0]
    if rarity is None:
        rarity = WP.roll_rarity(rng, level, bonus)
    return Support(kind, rarity, level, rng.randrange(1 << 30))

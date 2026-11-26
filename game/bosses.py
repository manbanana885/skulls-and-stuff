"""Boss engine: every attack is a generator that spawns projectiles and yields wait times.
Bosses escalate through 3 phases (100-66-33% HP) from simple patterns to bullet hell."""
import math
import random
from assets import dir_index
from world import Proj, Particle, Enemy, resolve, rot, Loot
import bestiary as BE
import weapons as WP
import sfx

rnd = random.Random()

# projectile style per attack 'kind': (proj kind, colour or None=boss colour, radius, blast)
STYLE = {
    "orb": ("orb", None, 0.18, 0.0), "bile": ("orb", (180, 160, 60), 0.2, 0.0), "fireball": ("fireball", (255, 120, 30), 0.22, 0.8),
    "coin": ("orb", (255, 215, 70), 0.14, 0.0), "thorn": ("orb", (190, 120, 80), 0.15, 0.0), "spore": ("orb", (90, 255, 210), 0.2, 0.0),
    "acid_orb": ("orb", (130, 240, 60), 0.2, 0.0), "rocket": ("rocket", (255, 90, 40), 0.18, 1.2), "bolt": ("bolt", None, 0.14, 0.0),
}


def eel_points(e, k, t, n=12):
    """Points (x, y, z) along eel arm k of entity e (enemy or boss)."""
    arms = e.eels
    base = k * math.tau / arms + e.eel_spin
    bx, by, hz = e.x, e.y, e.hz
    s = math.sin(math.pi * e.eel_t) if 0 <= e.eel_t < 1 and (k % 2 == 0 or e.eel_all) else 0.0
    ia = base + math.sin(t * 1.3 + k) * 0.4
    idx, idy = math.cos(ia), math.sin(ia)
    tx, ty = e.eel_tx - bx, e.eel_ty - by
    tl = math.hypot(tx, ty) or 1
    tx, ty = tx / tl, ty / tl
    dx, dy = idx * (1 - s) + tx * s, idy * (1 - s) + ty * s
    dl = math.hypot(dx, dy) or 1
    dx, dy = dx / dl, dy / dl
    length = (0.9 + 0.3 * e.r) + (min(e.reach, tl) - 0.9) * s
    pts = []
    for i in range(n + 1):
        u = i / n
        wig = math.sin(t * 7 + u * 6 + k * 1.7) * 0.3 * u * (1 - 0.6 * s)
        x = bx + dx * length * u - dy * wig
        y = by + dy * length * u + dx * wig
        z = hz * (1 - 0.6 * u) + math.sin(u * math.pi) * 0.35
        pts.append((x, y, z))
    return pts, s


def update_eels(e, w, dt, dmg):
    """Advance strike, emit particles, deal damage at the tips."""
    e.eel_spin += dt * 0.4
    if 0 <= e.eel_t < 1:
        e.eel_t += dt / 0.6
        if e.eel_t >= 1:
            e.eel_t = -1
    for k in range(e.eels):
        pts, s = eel_points(e, k, w.time)
        if rnd.random() < dt * 5:
            x, y, z = pts[rnd.randrange(len(pts))]
            w.add(Particle("glow", x, y, z, rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), rnd.uniform(0, 1), 0.5, e.eel_color, 2))
        if s > 0.6:
            x, y, _ = pts[-1]
            for p in w.players:
                if p.alive and math.hypot(p.x - x, p.y - y) < 0.55:
                    w.hurt_player(dmg, e.x, e.y, knock=9, who=p)


# ---------------------------------------------------------------- attacks
def aim(b, w):
    t = getattr(b, "target", None) or w.player
    return math.atan2(t.y - b.y, t.x - b.x)


def shoot(b, w, a, speed, kind="orb", homing=0.0, z=None):
    pk, col, r, blast = STYLE.get(kind, STYLE["orb"])
    c, s = math.cos(a), math.sin(a)
    w.projs.append(Proj(pk, b.x + c * b.r * 0.8, b.y + s * b.r * 0.8, z if z is not None else b.hz, c * speed, s * speed, b.dmg,
                        hostile=True, life=7.0, color=col or b.color, r=r, blast=blast, homing=homing, maxspeed=9.0))


def a_aimed(b, w, n=5, interval=0.15, speed=8.5, kind="bolt"):
    for _ in range(n):
        shoot(b, w, aim(b, w) + rnd.uniform(-0.05, 0.05), speed, kind)
        sfx.play("turret_shot", 0.5)
        yield interval


def a_fan(b, w, count=7, arc=1.1, waves=1, speed=6.5, kind="orb"):
    for wv in range(waves):
        base = aim(b, w) + (0.08 if wv % 2 else 0)
        for i in range(count):
            shoot(b, w, base + arc * (i / max(1, count - 1) - 0.5), speed, kind)
        sfx.play("enemy_shot", 0.7)
        yield 0.45


def a_ring(b, w, count=16, waves=1, speed=5.0, kind="orb"):
    off = rnd.random() * math.tau
    for wv in range(waves):
        for i in range(count):
            shoot(b, w, off + math.tau * i / count + wv * math.pi / count, speed, kind)
        sfx.play("enemy_shot", 0.8)
        yield 0.5


def a_spiral(b, w, arms=3, duration=4.0, spin=1.0, rate=10.0, speed=5.5, kind="orb"):
    t, a0, sgn = 0.0, rnd.random() * math.tau, rnd.choice((1, -1))
    while t < duration:
        for k in range(arms):
            shoot(b, w, a0 + sgn * t * spin * 2.2 + math.tau * k / arms, speed, kind)
        if int(t * rate) % 3 == 0:
            sfx.play("shot_laser", 0.35)
        yield 1.0 / rate
        t += 1.0 / rate


def a_wave(b, w, duration=3.0, amp=0.9, rate=14.0, speed=7.0, kind="orb"):
    t = 0.0
    base = aim(b, w)
    while t < duration:
        off = amp * math.sin(t * 5)
        shoot(b, w, base + off, speed, kind)
        shoot(b, w, base - off, speed, kind)
        if int(t * rate) % 4 == 0:
            sfx.play("shot_laser", 0.3)
        yield 1.0 / rate
        t += 1.0 / rate
        base += (aim(b, w) - base) * 0.05


def a_homing(b, w, n=6, kind="orb"):
    for i in range(n):
        shoot(b, w, aim(b, w) + (i - n / 2) * 0.35, 4.5, kind, homing=1.4)
        sfx.play("enemy_shot" if kind != "rocket" else "walker_rocket", 0.6)
        yield 0.18


def a_mortar(b, w, n=8, kind="orb"):
    p = b.target or w.nearest_player(b.x, b.y)
    pk, col, r, blast = STYLE.get(kind, STYLE["orb"])
    for i in range(n):
        if i == 0:
            x, y = p.x, p.y
        else:
            a, d = rnd.random() * math.tau, rnd.uniform(0.6, 3.5)
            x, y = p.x + math.cos(a) * d, p.y + math.sin(a) * d
        w.warnings.append([x, y, 1.1, 1.1, 1.1, col or b.color])
        m = Proj("mortar", x, y, 9.0, 0, 0, b.dmg * 1.2, hostile=True, life=4, color=col or b.color, r=0.3, blast=1.1, vz=-8.0)
        w.projs.append(m)
        yield 0.12
    sfx.play("shot_grenade", 0.7)
    yield 0.6


def a_charge(b, w, n=1):
    for _ in range(n):
        b.telegraph = 0.55
        sfx.play("brute_roar", 0.7)
        yield 0.55
        a = aim(b, w)
        b.cvx, b.cvy = math.cos(a) * 9.5, math.sin(a) * 9.5
        b.charging = 0.75
        yield 0.95


def a_slam(b, w, rings=1, kind="orb"):
    for k in range(rings):
        b.telegraph = 0.35
        yield 0.35
        w.shake = max(w.shake, 10)
        w.add(Particle("ring", b.x, b.y, 0.05, 6.0, 0, 0, 0.6, b.color, 0.2))
        w.breach(b.x, b.y, b.r + 1.4)
        sfx.play("stomp", 1.0)
        count = 30
        gap = rnd.randrange(count)
        off = rnd.random() * math.tau
        for i in range(count):
            if (i - gap) % count < 4:
                continue      # a gap to slip through
            shoot(b, w, off + math.tau * i / count, 4.2, kind, z=0.35)
        yield 0.5


def a_laser(b, w, sweep=1.5, duration=2.2):
    a0 = aim(b, w)
    sgn = rnd.choice((1, -1))
    b.laser = dict(a0=a0 - sgn * sweep / 2, sweep=sgn * sweep, t=0.0, tele=0.8, dur=duration)
    sfx.play("turret_beep", 1.0)
    yield 0.8 + duration + 0.2


def a_summon(b, w, kind="shade", n=3):
    for i in range(n):
        a = rnd.random() * math.tau
        x, y = b.x + math.cos(a) * (b.r + 0.8), b.y + math.sin(a) * (b.r + 0.8)
        if not w.level.is_solid(int(x), int(y)) and len(w.enemies) < 70:
            w.enemies.append(Enemy(kind, x, y, awake=True, depth=w.depth))
            w.spray(x, y, 0.5, b.color, 12, 3.0)
            sfx.play("spawn", 0.8)
        yield 0.25


def a_flower(b, w, rings=6, count=14, kind="orb"):
    off = rnd.random() * math.tau
    for i in range(rings):
        for j in range(count):
            a = math.tau * j / count + off + i * 0.27
            shoot(b, w, a, 3.8 + (i % 2) * 1.6, kind)
            shoot(b, w, -a, 3.2 + (i % 3) * 0.8, kind)
        sfx.play("enemy_shot", 0.6)
        yield 0.3


def a_blink(b, w):
    p = b.target or w.nearest_player(b.x, b.y)
    for _ in range(20):
        a, d = rnd.random() * math.tau, rnd.uniform(4.0, 6.5)
        x, y = p.x + math.cos(a) * d, p.y + math.sin(a) * d
        if not any(w.level.is_solid(int(x + ox), int(y + oy)) for ox in (-0.8, 0, 0.8) for oy in (-0.8, 0, 0.8)):
            for _ in range(24):
                w.add(Particle("glow", b.x + rnd.uniform(-0.6, 0.6), b.y + rnd.uniform(-0.6, 0.6), rnd.uniform(0, 2), 0, 0, 1, 0.5,
                               b.color, 3))
            b.x, b.y = x, y
            sfx.play("wretch_blink", 0.9)
            break
    yield 0.3
    off = rnd.random()
    for i in range(14):
        shoot(b, w, off + math.tau * i / 14, 5.0, "orb")
    yield 0.6


def a_eel(b, w):
    for k in range(3 + b.phase):
        p = b.target or w.nearest_player(b.x, b.y)
        b.eel_tx, b.eel_ty = p.x, p.y
        b.eel_t = 0.0
        b.eel_all = k % 2 == 1
        sfx.play("tongue", 0.9)
        yield 0.75


ATTACKS = {"aimed": a_aimed, "fan": a_fan, "ring": a_ring, "spiral": a_spiral, "wave": a_wave, "homing": a_homing,
           "mortar": a_mortar, "charge": a_charge, "slam": a_slam, "laser": a_laser, "summon": a_summon, "flower": a_flower,
           "blink": a_blink, "eel": a_eel}


# ---------------------------------------------------------------- boss
class Boss:
    def __init__(self, kind, x, y, depth):
        sp = BE.BOSSES[kind]
        self.kind, self.sp, self.title = kind, sp, sp["title"]
        self.maxhp = self.hp = 450 + 170 * depth
        self.x, self.y = x, y
        self.r = sp["r"]
        self.speed = sp["speed"]
        self.color = sp["color"]
        self.fly = sp.get("fly", False)
        self.hz = 1.6
        self.st = dict(hz=self.hz, score=5000)
        self.dmg = 9 + 1.5 * depth
        self.blood = (125, 8, 6)
        self.dir, self.frame = 1, 0.0
        self.flash = self.telegraph = 0.0
        self.awake = False
        self.alive = True
        self.gen = None
        self.wait = 1.2
        self.phase = 0
        self.queue = []
        self.vx = self.vy = 0.0
        self.charging = 0.0
        self.cvx = self.cvy = 0.0
        self.laser = None
        self.burn = self.burn_dps = self.slow = 0.0
        self.eels = sp.get("eels", 0)
        self.eel_color = sp.get("eel_color", self.color)
        self.eel_t = -1.0
        self.eel_tx = self.eel_ty = 0.0
        self.eel_spin = 0.0
        self.eel_all = False
        self.reach = 4.0
        self.hitvx = self.hitvy = 0.0
        self.state = "boss"
        self.target = None
        self.stuck = 0.0

    def phase_now(self):
        f = self.hp / self.maxhp
        return 0 if f > 0.66 else (1 if f > 0.33 else 2)

    def next_attack(self, w):
        if not self.queue:
            self.queue = list(self.sp["phases"][self.phase])
            rnd.shuffle(self.queue)
        name, kw = self.queue.pop()
        return ATTACKS[name](self, w, **kw)

    def update(self, w, dt):
        p = w.nearest_player(self.x, self.y)
        self.target = p
        dx, dy = p.x - self.x, p.y - self.y
        d = math.hypot(dx, dy) or 1e-6
        self.flash = max(0.0, self.flash - dt)
        self.telegraph = max(0.0, self.telegraph - dt)
        if self.burn > 0:
            self.burn -= dt
            self.hp -= self.burn_dps * dt
            if rnd.random() < dt * 20:
                w.add(Particle("fire", self.x + rnd.uniform(-0.5, 0.5), self.y + rnd.uniform(-0.5, 0.5), rnd.uniform(0.5, 2), 0, 0, 1.5, 0.4,
                               (255, 120, 30), 14))
            if self.hp <= 0 and self.alive:
                self.alive = False
                w.kill_boss(self)
                return
        self.slow = max(0.0, self.slow - dt)
        if not self.awake:
            if (d < 9 and w.level.line_of_sight(self.x, self.y, p.x, p.y)) or self.flash > 0:
                self.awake = True
                w.boss_awake(self)
            else:
                self.frame += dt * 3
                return
        ph = self.phase_now()
        if ph > self.phase:
            self.phase = ph
            self.queue = []
            w.message("%s ENRAGES" % self.title, self.color)
            w.shake = max(w.shake, 12)
            w.add(Particle("ring", self.x, self.y, 0.1, 8, 0, 0, 0.6, self.color, 0.2))
            sfx.play("brute_roar", 1.0)
        # movement
        ox, oy = self.x, self.y
        if self.charging > 0:
            self.charging -= dt
            # rushes plough straight through terrain
            sp_ = math.hypot(self.cvx, self.cvy) or 1
            if w.breach(self.x + self.cvx / sp_ * (self.r + 0.4), self.y + self.cvy / sp_ * (self.r + 0.4), self.r + 0.5):
                w.shake = max(w.shake, 8)
            nx, ny = resolve(w.level, self.x + self.cvx * dt, self.y + self.cvy * dt, self.r)
            if math.hypot(nx - self.x, ny - self.y) < 9.5 * dt * 0.3:   # only the indestructible map edge stops it
                self.charging = 0
                w.shake = max(w.shake, 10)
                sfx.play("stomp", 1.0)
            self.x, self.y = nx, ny
            if rnd.random() < dt * 25:
                w.add(Particle("smoke", self.x, self.y, 0.1, rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0.3, 0.8, (80, 70, 60), 0.3))
        elif self.telegraph <= 0 and p.alive:
            want = 4.5 if self.fly else 3.5
            sgn = 1 if d > want else -1
            tx, ty = dx / d * sgn, dy / d * sgn
            sx_, sy_ = -dy / d * 0.4, dx / d * 0.4
            spd = self.speed * (0.5 if self.slow > 0 else 1.0)
            if abs(d - want) < 0.8:
                tx, ty = sx_, sy_
            self.vx += (tx * spd - self.vx) * min(1, dt * 3)
            self.vy += (ty * spd - self.vy) * min(1, dt * 3)
            px_, py_ = self.x, self.y
            self.x, self.y = resolve(w.level, self.x + self.vx * dt, self.y + self.vy * dt, self.r)
            # stuck while pursuing? smash a way through toward the player
            if d > want + 1.0 and math.hypot(self.x - px_, self.y - py_) < spd * dt * 0.25:
                self.stuck += dt
                if self.stuck > 0.8:
                    self.stuck = 0.0
                    self.telegraph = 0.3
                    if w.breach(self.x + dx / d * (self.r + 0.6), self.y + dy / d * (self.r + 0.6), self.r + 0.8):
                        w.shake = max(w.shake, 9)
                        sfx.play("stomp", 1.0)
            else:
                self.stuck = max(0.0, self.stuck - dt)
        self.frame += math.hypot(self.x - ox, self.y - oy) * 3 + dt * 3
        self.dir = dir_index(dx, dy, 8)
        # attacks
        if p.alive:
            self.wait -= dt
            guard = 0
            while self.wait <= 0 and guard < 8:
                guard += 1
                if self.gen is None:
                    self.gen = self.next_attack(w)
                try:
                    self.wait += next(self.gen)
                except StopIteration:
                    self.gen = None
                    self.wait += 0.9 - 0.25 * self.phase
        # laser sweep
        if self.laser:
            L = self.laser
            L["t"] += dt
            if L["t"] < L["tele"]:
                a = L["a0"]
                w.beams.append([self.x, self.y, self.x + math.cos(a) * 14, self.y + math.sin(a) * 14, 1.0, 0.03, 0.03, (255, 60, 60), 0.25])
            elif L["t"] < L["tele"] + L["dur"]:
                k = (L["t"] - L["tele"]) / L["dur"]
                a = L["a0"] + L["sweep"] * k
                ex, ey = math.cos(a), math.sin(a)
                w.beams.append([self.x, self.y, self.x + ex * 14, self.y + ey * 14, 1.0, 0.03, 0.03, self.color, 2.2])
                px, py = p.x - self.x, p.y - self.y
                along = px * ex + py * ey
                for pl in w.players:
                    qx, qy = pl.x - self.x, pl.y - self.y
                    al = qx * ex + qy * ey
                    if pl.alive and 0 < al < 14 and abs(qx * -ey + qy * ex) < 0.45:
                        w.hurt_player(16, self.x, self.y, knock=6, who=pl)
                if rnd.random() < dt * 30:
                    t = rnd.uniform(0.5, 12)
                    w.add(Particle("spark", self.x + ex * t, self.y + ey * t, 1.0, rnd.uniform(-2, 2), rnd.uniform(-2, 2), 2, 0.3, self.color, 2))
            else:
                self.laser = None
        if self.eels:
            update_eels(self, w, dt, 16)
        if p.alive and d < self.r + 0.35:
            w.hurt_player(22 if self.charging > 0 else 14, self.x, self.y, knock=14)

    def hit(self, w, dmg, vx, vy):
        if not self.alive:
            return
        self.hp -= dmg
        self.flash = 0.06
        self.hitvx, self.hitvy = vx, vy
        sp = math.hypot(vx, vy) or 1
        for _ in range(4):
            a = rnd.uniform(-0.6, 0.6)
            ex, ey = rot(vx / sp, vy / sp, a)
            w.add(Particle("blood", self.x + ex * 0.3, self.y + ey * 0.3, self.hz, ex * 3, ey * 3, rnd.uniform(0.5, 3), 1.5, self.blood, 4))
        w.snd("hit_flesh", self.x, self.y, 0.6)
        if self.hp <= 0:
            self.alive = False
            w.kill_boss(self)


def drop_boss_loot(w, b):
    for k in range(2):
        w.loot.append(Loot("weapon", b.x + rnd.uniform(-0.5, 0.5), b.y + rnd.uniform(-0.5, 0.5), WP.generate(w.depth, bonus=2.5), pop=True))
    w.loot.append(Loot("buff", b.x, b.y, WP.roll_buff(level=w.depth + 2), pop=True))
    w.loot.append(Loot("health", b.x, b.y, pop=True))

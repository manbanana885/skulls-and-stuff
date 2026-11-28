"""Game simulation: player + weapons, enemies, projectiles, loot, gibs, particles, hazards."""
import math
import random
from assets import screen_to_world_dir, dir_index, to_screen, S as _S
from level import Level
import weapons as WP
import support as SU
import damage as DM
import characters as CH
import bestiary as BE
import sfx

rnd = random.Random()

RED = (125, 8, 6)
DARKRED = (80, 4, 4)
ICHOR = (70, 150, 25)
OIL = (28, 24, 32)
BRAIN = (150, 60, 70)
ASH = (45, 35, 30)

# what each thing is made of: (gib sprites, blood colour)
GIB_SETS = {
    "zombie": (["gib_bone", "gib_rib", "gib_skull", "gib_jaw", "gib_meat_green", "gib_meat", "gib_gut", "gib_eye",
                "gib_bone", "gib_meat", "gib_rib"], RED),
    "leech": (["gib_leech", "gib_leech", "gib_meat", "gib_gut", "gib_leech", "gib_meat", "gib_gut"], DARKRED),
    "spider": (["gib_chitin", "gib_spiderleg", "gib_spiderleg", "gib_chitin", "gib_eye", "gib_spiderleg", "gib_meat_green",
                "gib_chitin", "gib_spiderleg", "gib_gut", "gib_eye", "gib_spiderleg"], ICHOR),
    "drone": (["gib_metal", "gib_gear", "gib_wire", "gib_metal", "gib_gear", "gib_meat", "gib_wire", "gib_eye"], OIL),
    "crawler": (["gib_skull", "gib_jaw", "gib_chrome", "gib_chrome", "gib_eye"], RED),
    "spitter": (["gib_meat_green", "gib_gut", "gib_bone", "gib_jaw", "gib_eye", "gib_leech", "gib_meat_green", "gib_rib"], ICHOR),
    "bloater": (["gib_meat", "gib_gut", "gib_gut", "gib_gut", "gib_meat_green", "gib_bone", "gib_eye", "gib_meat", "gib_pod",
                 "gib_meat_green", "gib_gut"], ICHOR),
    "brute": (["gib_meat", "gib_gut", "gib_bone", "gib_rib", "gib_skull", "gib_meat", "gib_eye", "gib_chrome", "gib_metal",
               "gib_bone", "gib_meat", "gib_gut", "gib_rib", "gib_jaw"], RED),
    "turret": (["gib_metal", "gib_gear", "gib_wire", "gib_chrome", "gib_metal", "gib_gear"], OIL),
    "walker": (["gib_metal", "gib_gear", "gib_wire", "gib_chrome", "gib_metal", "gib_gear", "gib_wire", "gib_metal"], OIL),
    "skull": (["gib_skull", "gib_jaw", "gib_chrome", "gib_gear"], ASH),
    "player": (["gib_chrome", "gib_armor", "gib_bone", "gib_skull", "gib_wire", "gib_gear", "gib_rib", "gib_armor",
                "gib_bone", "gib_chrome", "gib_jaw", "gib_rib"], OIL),
    "spawner": (["gib_pod", "gib_meat", "gib_gut", "gib_pod", "gib_meat", "gib_eye", "gib_gut", "gib_pod", "gib_leech",
                 "gib_meat", "gib_skull"], ICHOR),
    "barrel": (["gib_barrel", "gib_barrel", "gib_metal", "gib_barrel", "gib_metal"], ICHOR),
    "crate": (["gib_plank", "gib_plank", "gib_plank", "gib_plank", "gib_metal"], None),
    "rubble": (["gib_rubble", "gib_rubble", "gib_rubble", "gib_metal"], None),
    "hellspawn": (["gib_meat", "gib_bone", "gib_rib", "gib_skull", "gib_jaw", "gib_meat", "gib_gut", "gib_eye"], (90, 12, 5)),
    "wretch": (["gib_bone", "gib_gut", "gib_meat", "gib_jaw", "gib_rib", "gib_meat", "gib_gut"], RED),
    "stalker": (["gib_meat", "gib_meat", "gib_gut", "gib_bone", "gib_eye", "gib_rib", "gib_meat", "gib_gut"], RED),
    "mimic": (["gib_meat", "gib_gut", "gib_gut", "gib_gut", "gib_eye", "gib_skull", "gib_jaw", "gib_meat", "gib_leech",
               "gib_bone", "gib_gut", "gib_eye"], RED),
}
MAX_GIBS = 320
HARD_GIBS = {"gib_bone", "gib_rib", "gib_skull", "gib_jaw", "gib_metal", "gib_gear", "gib_chrome", "gib_armor",
             "gib_barrel", "gib_wire", "gib_plank"}
MAX_PARTICLES = 1800


def resolve(level, x, y, r):
    """Push a circle out of solid tiles (smooth sliding along walls)."""
    for _ in range(2):
        for tx in range(int(x - r) - 1, int(x + r) + 1):
            for ty in range(int(y - r) - 1, int(y + r) + 1):
                if not level.is_solid(tx, ty):
                    continue
                cx = min(max(x, tx), tx + 1)
                cy = min(max(y, ty), ty + 1)
                ddx, ddy = x - cx, y - cy
                d2 = ddx * ddx + ddy * ddy
                if d2 < r * r:
                    if d2 > 1e-10:
                        d = math.sqrt(d2)
                        push = r - d
                        x += ddx / d * push
                        y += ddy / d * push
                    else:
                        opts = ((x - tx + r, -1, 0), (tx + 1 - x + r, 1, 0), (y - ty + r, 0, -1), (ty + 1 - y + r, 0, 1))
                        dist, sx, sy = min(opts)
                        x += sx * dist
                        y += sy * dist
    return x, y


def rot(vx, vy, a):
    c, s = math.cos(a), math.sin(a)
    return vx * c - vy * s, vx * s + vy * c


# ---------------------------------------------------------------- particles
class Particle:
    """kind: blood | chunk | spark | smoke | fire | shell | ring | glow"""
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "life", "max", "color", "size", "kind", "rest")

    def __init__(self, kind, x, y, z, vx, vy, vz, life, color, size=2.0):
        self.kind = kind
        self.x, self.y, self.z = x, y, z
        self.vx, self.vy, self.vz = vx, vy, vz
        self.life = self.max = life
        self.color, self.size = color, size
        self.rest = False

    def update(self, w, dt):
        k = self.kind
        self.life -= dt
        if self.life <= 0:
            return False
        if k == "smoke":
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.z += self.vz * dt
            self.vx *= 0.96
            self.vy *= 0.96
            self.size += dt * 1.4
            return True
        if k == "ring":
            self.size += dt * self.vx
            return True
        if k in ("fire", "glow"):
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.z += self.vz * dt
            self.vx *= 0.92
            self.vy *= 0.92
            self.vz += dt * (2 if k == "fire" else -4)
            if self.z < 0:
                self.z = 0
            return True
        if self.rest:
            return True
        self.vz -= (16.0 if k != "spark" else 6.0) * dt
        nx, ny = self.x + self.vx * dt, self.y + self.vy * dt
        L = w.level
        if not (0 <= nx < L.W and 0 <= ny < L.H):
            return False
        if L.solid[int(ny) * L.W + int(nx)] == 1 and self.z < 1.0:
            self.vx *= -0.3
            self.vy *= -0.3
            nx, ny = self.x, self.y
            if k == "blood" and rnd.random() < 0.3:
                w.splat(nx, ny, self.color, 0.07)
        self.x, self.y = nx, ny
        self.z += self.vz * dt
        if self.z <= 0:
            self.z = 0
            if k == "blood":
                if rnd.random() < 0.45:
                    w.splat(self.x, self.y, self.color, self.size * 0.035)
                return False
            if k == "spark":
                return False
            self.vz *= -0.35
            self.vx *= 0.5
            self.vy *= 0.5
            if abs(self.vz) < 0.8:
                self.rest = True
        return True


class Gib:
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "frame", "spin", "sprite", "rest", "bleed", "blood", "bounces", "trail")

    def __init__(self, sprite, x, y, z, vx, vy, vz, blood, bleed):
        self.sprite = sprite
        self.x, self.y, self.z = x, y, z
        self.vx, self.vy, self.vz = vx, vy, vz
        self.frame = rnd.random() * 8
        self.spin = rnd.uniform(10, 24) * rnd.choice((1, -1))
        self.rest = False
        self.blood, self.bleed = blood, bleed
        self.bounces = 0
        self.trail = 0.0

    def update(self, w, dt):
        if self.rest:
            return
        L = w.level
        self.vz -= 18 * dt
        nx, ny = self.x + self.vx * dt, self.y + self.vy * dt
        if L.solid[int(self.y) * L.W + int(nx)] == 1:
            self.vx *= -0.45
            nx = self.x
            if self.blood and self.z > 0.2 and rnd.random() < 0.5:
                w.splat(nx, ny, self.blood, 0.12)
        if L.solid[int(ny) * L.W + int(nx)] == 1:
            self.vy *= -0.45
            ny = self.y
        self.x, self.y = nx, ny
        self.z += self.vz * dt
        self.frame += self.spin * dt
        if self.bleed > 0 and self.blood:
            self.bleed -= dt
            self.trail -= dt
            if self.trail <= 0:
                self.trail = 0.03
                w.add(Particle("blood", self.x, self.y, self.z, self.vx * 0.2 + rnd.uniform(-0.5, 0.5),
                               self.vy * 0.2 + rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 1), 1.0, self.blood, rnd.uniform(2, 3.5)))
        if self.z <= 0:
            self.z = 0
            if self.bounces == 0:
                if self.blood:
                    w.splat(self.x, self.y, self.blood, rnd.uniform(0.1, 0.18))
                w.snd("clatter" if self.sprite in HARD_GIBS else "splat", self.x, self.y, 0.7)
            self.bounces += 1
            self.vz = -self.vz * 0.38
            self.vx *= 0.55
            self.vy *= 0.55
            self.spin *= 0.55
            if self.vz < 1.3 or self.bounces > 3:
                self.rest = True
                self.vz = 0
                self.frame = int(self.frame)


# ---------------------------------------------------------------- projectiles
class Proj:
    """kind: bullet | pellet | slug | bolt | plasma | flame | grenade | rocket | acid"""
    __slots__ = ("kind", "x", "y", "z", "vx", "vy", "vz", "life", "dmg", "hostile", "color", "r", "pierce", "bounce",
                 "blast", "burn", "shock", "homing", "slow", "grav", "hit", "trail", "age", "maxspeed", "rad", "gas", "chill", "spin",
                 "hurt_cd", "effect", "owner", "ox", "oy", "cone", "reach", "dtype", "acid", "ammo", "tier_leech")

    def __init__(self, kind, x, y, z, vx, vy, dmg, hostile=False, life=0.9, color=(255, 220, 140), r=0.1,
                 pierce=0, bounce=0, blast=0.0, burn=0.0, shock=0, homing=0, slow=0, vz=0.0, grav=0.0, maxspeed=22.0,
                 rad=None, gas=0.0, chill=0.0):
        self.kind = kind
        self.x, self.y, self.z = x, y, z
        self.vx, self.vy, self.vz = vx, vy, vz
        self.life, self.dmg, self.hostile, self.color, self.r = life, dmg, hostile, color, r
        self.pierce, self.bounce, self.blast, self.burn = pierce, bounce, blast, burn
        self.shock, self.homing, self.slow, self.grav = shock, homing, slow, grav
        self.hit = set()
        self.trail = 0.0
        self.age = 0.0
        self.maxspeed = maxspeed
        self.rad, self.gas, self.chill = rad, gas, chill
        self.spin = 0.0
        self.hurt_cd = 0.0
        self.effect = None
        self.owner = None
        self.ox = self.oy = 0.0
        self.cone = 0.0
        self.reach = None
        self.dtype = "kinetic"
        self.acid = 0.0
        self.ammo = None
        self.tier_leech = 0.0


class Loot:
    """kind: weapon | support | buff | health"""

    def __init__(self, kind, x, y, item=None, pop=False):
        self.kind, self.x, self.y, self.item = kind, x, y, item
        self.t = rnd.random() * 5
        self.z = 0.0
        self.vz = rnd.uniform(4, 6) if pop else 0.0
        self.vx, self.vy = (rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5)) if pop else (0.0, 0.0)


# ---------------------------------------------------------------- player
TETHER_X, TETHER_Y = (960 - 180) * _S, (540 - 150) * _S   # max on-screen separation between co-op players


GEAR_SLOTS = 4          # one per D-pad direction: up / right / down / left (keys 1-4)
PACK_SIZE = 8
SLOT_DIRS = ("UP", "RIGHT", "DOWN", "LEFT")


BARREL_WEIGHTS = {
    "default": {"fire": 1, "chem": 1, "rad": 1, "shrap": 1},
    "nuclear": {"fire": 1, "chem": 1, "rad": 4, "shrap": 1},
    "chemical": {"fire": 1, "chem": 4, "rad": 1, "shrap": 1},
    "hell": {"fire": 4, "chem": 1, "rad": 1, "shrap": 1},
    "heresy": {"fire": 3, "chem": 1, "rad": 1, "shrap": 1},
    "facility": {"fire": 1, "chem": 1, "rad": 1, "shrap": 2},
    "outpost": {"fire": 2, "chem": 1, "rad": 1, "shrap": 2},
    "sewer": {"fire": 1, "chem": 3, "rad": 1, "shrap": 1},
}


class Player:
    R = 0.28
    SPEED = 4.4

    def __init__(self, x, y, idx=0, char="skelebot", name=""):
        self.idx = idx
        self.name = name             # shown over your head / in the lobby (net play); '' -> "P1".."P4"
        self.char = char if char in CH.CHARS else "skelebot"
        self.cat = CH.CHARS[self.char]["cat"]
        self.spraying = None
        self.revive_t = 0.0
        self.spin = 0.0
        self.x, self.y = x, y
        self.max_hp = int(round(100 * CH.CHARS[self.char]["hp"]))
        self.hp = self.max_hp
        self.legs_dir = 1
        self.aim = (math.sqrt(0.5), math.sqrt(0.5))
        self.walk = 0.0
        self.moving = False
        self.invuln = 0.0
        self.flash = 0.0
        self.muzzle = 0.0
        self.muzzle_color = (180, 240, 255)
        self.kbx = self.kby = 0.0
        self.alive = True
        start = None if WP.RARE_ONLY else 0          # loot-test mode: you start with top-tier guns too
        self.weapons = [WP.generate(1, arch="carbine", rarity=start), WP.generate(1, arch="pistol", rarity=start)]
        self.cur = 0
        self.buffs = {}            # kind -> [magnitude, seconds left]
        self.status = {}           # chill / confuse -> seconds left
        self.perm_dmg = 1.0
        self.gear = [None] * GEAR_SLOTS    # equipped accessories (support.Support)
        self.pack = []                      # spare accessories, up to PACK_SIZE
        self.inv_cur = (0, 0)               # pause-menu cursor (column, row)
        self.sel = 0                        # selected module slot (D-pad / 1-4); F / B uses it
        self.dpad_t = 0.0                   # seconds left to show the D-pad HUD (it fades out when unused)
        self.last_move = (0.0, 0.0)
        self.card_t = 0.0                   # seconds left to show the weapon card (after a swap / pickup)
        self.salvo_q = 0           # barrage missiles still to ripple out
        self.salvo_t = 0.0
        self.salvo_n = 0
        self.salvo_wp = None

    @property
    def weapon(self):
        return self.weapons[self.cur]

    def equipped(self):
        return [g for g in self.gear if g is not None]

    def give(self, item):
        """New accessory: first free gear slot, else the backpack. Returns where it went, or None if full."""
        for i, g in enumerate(self.gear):
            if g is None:
                self.gear[i] = item
                item.attach(self, i)
                return "slot %d" % (i + 1)
        if len(self.pack) < PACK_SIZE:
            self.pack.append(item)
            return "backpack"
        return None

    def equip_from_pack(self, k, col):
        """Backpack item k -> first free gear slot, or swap with the item in gear slot col."""
        item = self.pack.pop(k)
        free = next((i for i, g in enumerate(self.gear) if g is None), None)
        i = free if free is not None else col
        old = self.gear[i]
        self.gear[i] = item
        item.attach(self, i)
        if old is not None:
            self.pack.insert(k, old)

    DPAD_SHOW = 3.5

    def use_button(self, w):
        """F / B / RB: use the module in the selected slot (it never picks anything up)."""
        g = self.gear[self.sel]
        if g is None:
            w.message("Slot %d (%s) is empty" % (self.sel + 1, SLOT_DIRS[self.sel]), (160, 165, 180))
        else:
            g.activate(w, self)

    def pickup_target(self, w):
        """What E / A would take: the nearest (and faced) of floor loot, a barrel, or your own deployed turret.
        Returns ("loot", Loot) / ("barrel", (x, y)) / ("turret", Turret) or None."""
        ax, ay = self.aim
        al = math.hypot(ax, ay) or 1.0
        best = None

        def consider(kind, obj, x, y, reach):
            nonlocal best
            d = math.hypot(x - self.x, y - self.y)
            if d < reach:
                facing = ((x - self.x) * ax + (y - self.y) * ay) / (max(d, 1e-6) * al)
                score = d - facing * 0.3
                if best is None or score < best[0]:
                    best = (score, kind, obj)
        for lt in w.loot:
            if lt.kind in ("weapon", "support"):
                consider("loot", lt, lt.x, lt.y, 0.9)
        for pos in w.barrels:
            consider("barrel", pos, pos[0] + 0.5, pos[1] + 0.5, 1.3)
        for t in w.turrets:
            if t.alive and getattr(t, "owner", None) is self:
                consider("turret", t, t.x, t.y, 1.4)
        return best[1:] if best else None

    def pick_up_barrel(self, w, pos):
        """A barrel on the floor becomes a barrel module of the same kind."""
        if all(g is not None for g in self.gear) and len(self.pack) >= PACK_SIZE:
            w.message("No room to carry the barrel", (255, 140, 120))
            return True
        mod = SU.barrel_module(w.barrel_kind.get(pos, "chem"), w.depth, w.barrels[pos])
        del w.barrels[pos]
        w.barrel_kind.pop(pos, None)
        L = w.level
        L.props.pop(pos, None)
        L.solid[L.i(*pos)] = 0
        w.flow_tile = None
        where = self.give(mod)
        w.snd("tink", pos[0] + 0.5, pos[1] + 0.5)
        w.message("Picked up %s (%s)" % (mod.label, where), mod.tint)
        return True

    def unequip(self, i):
        if self.gear[i] is None or len(self.pack) >= PACK_SIZE:
            return False

        self.pack.append(self.gear[i])
        self.gear[i] = None
        return True

    def mult(self, kind, default=1.0):
        b = self.buffs.get(kind)
        return b[0] if b else default

    def dmg_mult(self):
        return self.perm_dmg * self.mult("berserk")

    def update(self, w, dt, inp):
        mx, my = inp.move
        self.last_move = inp.move
        for k_ in list(self.status):
            self.status[k_] -= dt
            if self.status[k_] <= 0:
                del self.status[k_]
        if self.alive and ("poison" in self.status or "burn" in self.status):
            for k_, dps_, typ_, col_ in (("poison", 2.5, "chemical", (140, 220, 60)), ("burn", 4.0, "fire", (255, 130, 40))):
                if k_ in self.status:
                    if k_ == "poison" and "venom" in self.status:
                        dps_ = 4.5
                    self.hp -= dps_ * dt * self.mult("aegis") * CH.player_mult(self, typ_)
                    if rnd.random() < dt * 10:
                        w.add(Particle("fire" if k_ == "burn" else "glow", self.x + rnd.uniform(-0.2, 0.2), self.y + rnd.uniform(-0.2, 0.2),
                                       rnd.uniform(0.4, 1.2), 0, 0, rnd.uniform(0.6, 1.4), 0.5, col_, 9 if k_ == "burn" else 2))
            w.check_player_death(self.x, self.y, self)
        if "confuse" in self.status:
            mx, my = -mx, -my
        mag = min(1.0, math.hypot(mx, my)) * (0.5 if "chill" in self.status else 1.0) * (0.55 if "mire" in self.status else 1.0)
        self.moving = mag > 0.15
        dx = dy = 0.0
        if self.moving:
            wx, wy = screen_to_world_dir(mx, my)
            spd = self.SPEED * CH.CHARS[self.char]["speed"] * mag * self.mult("haste") * self.weapon.st.get("heavy", 1.0)
            dx, dy = wx * spd * dt, wy * spd * dt
            self.legs_dir = dir_index(wx, wy, 8)
            if inp.aim is None:
                self.aim = (wx, wy)
        if inp.aim is not None:
            self.aim = screen_to_world_dir(*inp.aim)
        ox, oy = self.x, self.y
        self.x, self.y = resolve(w.level, self.x + dx + self.kbx * dt, self.y + dy + self.kby * dt, self.R)
        for o in (() if w.free_roam else w.players):      # elastic co-op tether: you can't walk off your partner's screen
            if o is not self and o.alive:
                a1, b1 = to_screen(self.x, self.y)
                a2, b2 = to_screen(o.x, o.y)
                if abs(a1 - a2) > TETHER_X or abs(b1 - b2) > TETHER_Y:
                    a0, b0 = to_screen(ox, oy)
                    if abs(a1 - a2) + abs(b1 - b2) > abs(a0 - a2) + abs(b0 - b2):
                        self.x, self.y = ox, oy
        decay = math.exp(-10 * dt)
        self.kbx *= decay
        self.kby *= decay
        before = self.walk
        self.walk += math.hypot(self.x - ox, self.y - oy)
        stepname = CH.CHARS[self.char]["step"]
        if stepname and int(self.walk / 0.55) != int(before / 0.55):
            sfx.play(stepname)
        for t in ("invuln", "flash", "muzzle"):
            setattr(self, t, max(0.0, getattr(self, t) - dt))
        for k in list(self.buffs):
            self.buffs[k][1] -= dt
            if self.buffs[k][1] <= 0:
                del self.buffs[k]
                w.message("%s faded" % WP.BUFFS[k][0], (150, 150, 160))
        self.weapon.update(dt)
        fx_ = WP.TIER_FX.get(self.weapon.rarity)
        if fx_ and fx_.get("regen"):        # sacred heals, demonic / eldritch eat at you (never below 10%)
            if fx_["regen"] > 0:
                self.hp = min(self.max_hp, self.hp + fx_["regen"] * dt)
            elif self.hp > self.max_hp * 0.1:
                self.hp = max(self.max_hp * 0.1, self.hp + fx_["regen"] * dt)
        if self.salvo_q > 0:
            self.salvo_t -= dt
            while self.salvo_q > 0 and self.salvo_t <= 0:
                self.salvo_t += 0.05
                w.fire_missile(self, self.salvo_wp, self.salvo_n)
                self.salvo_q -= 1
                self.salvo_n += 1
        pressed = getattr(inp, "pressed", ())
        self.card_t = max(0.0, self.card_t - dt)
        self.dpad_t = max(0.0, self.dpad_t - dt)
        if "swap" in pressed:
            self.weapon.reload_t = 0.0
            self.cur = 1 - self.cur
            self.card_t = 3.0
            sfx.play("swap")
        if "reload" in pressed and self.weapon.start_reload():
            w.on_reload(self, self.weapon)
            sfx.play("reload")
        for k_ in range(GEAR_SLOTS):         # D-pad / 1-4: only selects that slot
            if "slot%d" % (k_ + 1) in pressed:
                self.dpad_t = self.DPAD_SHOW
                if self.sel != k_:
                    self.sel = k_
                    sfx.play("tink", 0.5)
        if "deploy" in pressed:
            self.use_button(w)
        if "dash" in pressed:
            jet = next((g for g in self.equipped() if g.ready()), None)
            if jet is not None:
                jet.dash(w, self, *inp.move)
        wp = self.weapon
        su = wp.st.get("spinup", 0.0)
        if su:
            if inp.fire and wp.reload_t <= 0:
                if self.spin <= 0:
                    sfx.play("servo", 0.7)
                self.spin = min(1.0, self.spin + dt / su)
            else:
                self.spin = max(0.0, self.spin - dt * 1.2)
        else:
            self.spin = 0.0
        spraying = bool(inp.fire) and wp.reload_t <= 0 and (wp.ammo > 0 or "infinite" in self.buffs)
        self.spraying = wp.arch if spraying else None
        if inp.fire:
            self.try_fire(w)

    def try_fire(self, w):
        wp = self.weapon
        if wp.reload_t > 0 or wp.cd > 0:
            return
        infinite = "infinite" in self.buffs
        if wp.ammo <= 0 and not infinite:
            if wp.start_reload():
                w.on_reload(self, wp)
                sfx.play("reload")
            return
        su = wp.st.get("spinup", 0.0)
        if su and self.spin < 0.2:
            return                        # barrels still spinning up
        wp.cd = 1.0 / (wp.st["rate"] * self.mult("overdrive") * ((0.3 + 0.7 * self.spin) if su else 1.0))
        if not infinite:
            wp.ammo -= 1
        w._shooter = self
        w.fire_weapon(self, wp)
        if wp.ammo <= 0 and not infinite and wp.start_reload():
            w.on_reload(self, wp)
            sfx.play("reload")


# ---------------------------------------------------------------- enemies
STATS = {
    "zombie":  dict(hp=5, speed=1.35, r=0.3, dmg=12, score=100, stride=0.9, hz=1.0),
    "leech":   dict(hp=3, speed=1.05, r=0.34, dmg=8, score=75, stride=0.6, hz=0.35),
    "spider":  dict(hp=16, speed=2.0, r=0.62, dmg=20, score=400, stride=1.5, hz=0.7),
    "drone":   dict(hp=6, speed=1.9, r=0.36, dmg=12, score=200, stride=1.0, hz=1.2),
    "crawler": dict(hp=2, speed=3.1, r=0.24, dmg=6, score=50, stride=0.5, hz=0.3),
    "spitter": dict(hp=5, speed=1.25, r=0.3, dmg=8, score=150, stride=0.8, hz=1.0),
    "bloater": dict(hp=9, speed=1.0, r=0.45, dmg=0, score=175, stride=0.6, hz=0.7),
    "brute":   dict(hp=45, speed=1.15, r=0.62, dmg=25, score=700, stride=1.3, hz=1.2),
    "turret":  dict(hp=16, speed=0.0, r=0.42, dmg=0, score=250, stride=1.0, hz=0.7),
    "walker":  dict(hp=24, speed=1.4, r=0.5, dmg=15, score=500, stride=1.4, hz=1.1),
    "skull":   dict(hp=4, speed=2.4, r=0.3, dmg=10, score=120, stride=1.0, hz=1.0),
    "hellspawn": dict(hp=10, speed=1.7, r=0.32, dmg=12, score=300, stride=1.0, hz=1.1),
    "wretch":  dict(hp=12, speed=1.0, r=0.3, dmg=15, score=350, stride=0.8, hz=1.2),
    "stalker": dict(hp=9, speed=2.6, r=0.38, dmg=12, score=300, stride=0.9, hz=0.5),
    "mimic":   dict(hp=20, speed=1.6, r=0.5, dmg=14, score=600, stride=1.0, hz=0.6),
}
WEAPON_DROP = {"brute": 0.35, "walker": 0.3, "turret": 0.12, "spider": 0.08, "mimic": 0.3, "hellspawn": 0.06}
FLYERS = {"drone", "skull"}
for _k, _d in BE.ENEMIES.items():
    STATS[_k] = dict(hp=_d["hp"], speed=_d["speed"], r=_d["r"], dmg=_d["dmg"], score=_d["score"], stride=_d.get("stride", 0.9), hz=_d["hz"])
    GIB_SETS[_k] = (_d["gibs"], _d["blood"])
    if _d.get("fly"):
        FLYERS.add(_k)
    if _d["ai"] == "charger":
        WEAPON_DROP[_k] = 0.2
DM.KIND_MULT.update(BE.KIND_RESIST)


def weapon_to_shot(wp):
    st = wp.st
    pk = st["proj"]
    sh = dict(kind="bolt", speed=11.0, dmg=7, color=st["color"], r=0.13, count=1, spread=0.0, burst=1, gap=0.1, cd=(1.4, 2.2), rng=8.0,
              blast=0.0, homing=0.0, hazard=None)
    if pk == "pellet":
        sh.update(count=5, spread=0.5, dmg=4, speed=10.0)
    elif pk in ("bullet", "bolt", "slug", "beam"):
        sh.update(burst=4 if st["rate"] > 7 else (2 if st["rate"] > 3 else 1), dmg=8 if st["rate"] > 3 else 13)
    elif pk == "grenade":
        sh.update(kind="fireball", speed=7.0, blast=0.9, dmg=12, color=(255, 150, 60), r=0.2)
    elif pk in ("rocket", "missile"):
        sh.update(kind="rocket", speed=5.0, blast=1.2, dmg=14, cd=(2.4, 3.2))
    elif pk == "plasma":
        sh.update(kind="orb", speed=7.0, dmg=11, r=0.2)
    elif pk == "saw":
        sh.update(kind="cleaver", speed=9.0, dmg=10, r=0.24, rng=7.0)
    elif pk in WP.SPRAYS:
        sh.update(kind="orb", speed=8.0, dmg=3, count=4, spread=0.35, burst=4, gap=0.08, rng=4.5, r=0.16)
    # heavy weapons (the Pink Heavy's arsenal): each keeps its character, with a tell you can react to
    a = wp.arch
    if a == "chaingun":       # spins up, then hoses a long stream
        sh.update(kind="bolt", speed=13.0, dmg=9, burst=16, gap=0.065, jitter=0.13, windup=0.6, cd=(2.8, 3.8), rng=9.0, r=0.1)
    elif a == "railgun":      # laser sight for a second, then a slug that goes through everything
        sh.update(kind="slug", speed=34.0, dmg=30, burst=1, aimed=1.0, cd=(3.4, 4.4), rng=13.0, r=0.11, color=(140, 230, 255))
    elif a == "barrage":      # a rippling salvo of slow homing rockets
        sh.update(kind="rocket", speed=5.5, dmg=12, blast=1.0, homing=0.45, burst=6, gap=0.14, jitter=0.55, cd=(4.2, 5.6), rng=9.5)
    elif a == "tac_nuke":     # a slow, glowing warhead: get out of its way
        sh.update(kind="nuke", speed=4.0, dmg=55, blast=1.8, rad=(1.6, 6.0, 5.0, 2.0), burst=1, cd=(6.5, 8.5), rng=10.0, minr=4.0,
                  r=0.24, color=(170, 255, 70))
    return sh


class Enemy:
    def __init__(self, kind, x, y, awake=False, depth=1):
        self.kind = kind
        self.cat = DM.category(kind)
        st = STATS[kind]
        self.st = st
        self.hp = st["hp"] * (1 + 0.15 * (depth - 1))
        self.speed = st["speed"] * rnd.uniform(0.9, 1.15)
        self.r = st["r"]
        self.blood = GIB_SETS[kind][1]
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.dir = rnd.randrange(8)
        self.angle = self.dir * math.tau / 8
        self.frame = rnd.random() * 6
        self.flash = 0.0
        self.awake = awake
        self.los = False
        self.los_t = rnd.random() * 0.3
        self.cd = rnd.uniform(1.0, 2.5)
        self.lunge = 0.0
        self.ldx = self.ldy = 0.0
        self.owner = None
        self.alive = True
        self.hitvx = self.hitvy = 0.0
        self.burn = 0.0
        self.burn_dps = 0.0
        self.slow = 0.0
        self.state = "walk"
        self.state_t = 0.0
        self.burst = 0
        self.burst_t = 0.0
        self.phase = rnd.random() * 10
        if kind == "mimic" and not awake:
            self.state = "dormant"
        self.bdef = BE.ENEMIES.get(kind)
        self.hz = st["hz"]
        self.eels = self.bdef.get("eels", 0) if self.bdef else 0
        self.eel_color = self.bdef.get("eel_color", (120, 255, 170)) if self.bdef else (0, 0, 0)
        self.reach = self.bdef.get("reach", 2.5) if self.bdef else 0
        self.eel_t, self.eel_tx, self.eel_ty, self.eel_spin, self.eel_all = -1.0, 0.0, 0.0, 0.0, False
        self.aim_t = 0.0
        self.bang = 0.0               # pit demon: where its fire breath is pointing
        self.stx = self.sty = 0.0     # scorpion: where the tail is coming down
        self.chill = 0.0
        self.frozen = 0.0
        self.maxhp = self.hp
        self.weapon = None
        self.wshot = None
        self.cd2 = rnd.uniform(2.0, 4.0)
        self.children = 0
        self.state2 = None
        self.gen = 0
        self.split_done = False
        self.erupt_t = 0.0
        self.submerged = bool(self.bdef) and self.bdef["ai"] in ("lurker", "burrower")
        if self.bdef and self.bdef["ai"] == "riser" and not awake:
            self.state = "dormant"

    def wake_mimic(self, w):
        self.state = "walk"
        self.awake = True
        w.spray(self.x, self.y, 0.5, self.blood or RED, 40, 5)
        w.splat(self.x, self.y, self.blood or RED, 0.7)
        w.gibs_from(self.kind, self.x, self.y, 0.4, count=4, force=0.8)
        w.shake = max(w.shake, 10 if self.kind == "mimic" else 5)
        w.hitstop = max(w.hitstop, 0.06)
        w.snd("mimic_scream" if self.kind == "mimic" else "spawn", self.x, self.y)

    def update(self, w, dt):
        p = w.target_for(self.x, self.y)
        self.target = p
        dx, dy = p.x - self.x, p.y - self.y
        d = math.hypot(dx, dy) or 1e-6
        k = self.kind
        self.flash = max(0.0, self.flash - dt)
        self.slow = max(0.0, self.slow - dt)
        if self.burn > 0:
            self.burn -= dt
            self.hp -= self.burn_dps * dt
            if w.show_numbers:
                w.damage_number(self, self.burn_dps * dt, "fire", True)
            if rnd.random() < dt * 25:
                w.add(Particle("fire", self.x + rnd.uniform(-0.2, 0.2), self.y + rnd.uniform(-0.2, 0.2),
                               self.st["hz"] * rnd.uniform(0.4, 1.1), 0, 0, rnd.uniform(1, 2), 0.4, (255, 120, 30), rnd.uniform(6, 12)))
            if self.hp <= 0 and self.alive:
                self.alive = False
                w.kill_enemy(self)
                return
        if self.chill > 0:
            self.chill = max(0.0, self.chill - dt * 0.2)        # slowly warms back up
        if self.frozen > 0:
            self.frozen -= dt
            if rnd.random() < dt * 6:
                w.add(Particle("glow", self.x + rnd.uniform(-0.3, 0.3), self.y + rnd.uniform(-0.3, 0.3), self.st["hz"] * rnd.random(),
                               0, 0, 0.4, 0.6, (200, 235, 255), 2))
            if self.frozen <= 0:      # thawed out
                for _ in range(10):
                    a = rnd.random() * math.tau
                    w.add(Particle("chunk", self.x, self.y, self.st["hz"] * 0.6, math.cos(a) * 2, math.sin(a) * 2, 2, 0.8, (190, 225, 255), 3))
                w.snd("tink", self.x, self.y, 0.8)
            return
        if self.slow > 0 and rnd.random() < dt * 10:
            w.add(Particle("glow", self.x, self.y, self.st["hz"], rnd.uniform(-1, 1), rnd.uniform(-1, 1), 1, 0.5,
                           (150, 210, 255), 2))
        if k == "skull" and rnd.random() < dt * 30:
            w.add(Particle("fire", self.x - self.vx * 0.05, self.y - self.vy * 0.05, 1.1 + rnd.uniform(0, 0.2),
                           -self.vx * 0.3, -self.vy * 0.3, rnd.uniform(0.5, 1.5), 0.35, (255, 110, 20), rnd.uniform(6, 11)))
        self.los_t -= dt
        if self.los_t <= 0:
            self.los_t = 0.3
            self.los = d < 13 and w.level.line_of_sight(self.x, self.y, p.x, p.y)
        if self.state == "dormant":
            if self.bdef and not self.bdef.get("disguise") and rnd.random() < dt * 2:
                w.add(Particle("glow", self.x + rnd.uniform(-0.3, 0.3), self.y + rnd.uniform(-0.3, 0.3), 0.02, 0, 0, 0.6, 0.6,
                               self.blood or (90, 120, 60), 2))
            if d < (2.3 if self.kind == "mimic" else (self.bdef or {}).get("wake", 3.5)) or self.flash > 0:
                self.wake_mimic(w)
            return
        if not self.awake:
            rng_wake = 10 if k == "turret" else 9
            if (d < rng_wake and self.los) or d < 3:
                self.awake = True
                if k == "turret":
                    w.snd("turret_beep", self.x, self.y)
                elif k == "brute":
                    w.snd("brute_roar", self.x, self.y)
            else:
                return
        if not p.alive:
            tx, ty = 0.0, 0.0
        elif d < 1.5 or (self.los and d < 7):
            tx, ty = dx / d, dy / d
        else:
            tx, ty = self.follow_flow(w, dx / d, dy / d)
        speed = self.speed * (0.45 if self.slow > 0 else 1.0)
        face = None
        if self.bdef:
            res = self.generic_ai(w, dt, dx, dy, d, tx, ty, speed)
            if res is None:
                return
            tx, ty, speed, face = res
        elif k == "turret":
            self.update_turret(w, dt, dx, dy, d)
            return
        elif k == "spider":
            if self.lunge > 0:
                self.lunge -= dt
                tx, ty, speed = self.ldx, self.ldy, 7.5
            else:
                self.cd -= dt
                if self.cd <= 0 and d < 4.5 and self.los:
                    self.lunge = 0.38
                    self.ldx, self.ldy = dx / d, dy / d
                    self.cd = rnd.uniform(1.3, 2.2)
                    w.snd("lunge", self.x, self.y)
        elif k == "skull":
            wob = math.sin(w.time * 5 + self.phase) * 0.7
            tx, ty = tx - ty * wob, ty + tx * wob
            if self.lunge > 0:
                self.lunge -= dt
                tx, ty, speed = self.ldx, self.ldy, 7.0
            else:
                self.cd -= dt
                if self.cd <= 0 and d < 5 and self.los:
                    self.lunge = 0.45
                    self.ldx, self.ldy = dx / d, dy / d
                    self.cd = rnd.uniform(1.8, 3.0)
                    w.snd("skull_screech", self.x, self.y)
        elif k == "crawler":
            wob = math.sin(w.time * 9 + self.phase) * 0.8
            tx, ty = tx - ty * wob, ty + tx * wob
        elif k == "drone" and p.alive:
            self.cd -= dt
            if self.los and d < 3.2:
                tx, ty = -dx / d, -dy / d
            elif self.los and d < 6.5:
                s = 1 if (int(w.time * 0.5 + self.phase) % 2) else -1
                tx, ty = -dy / d * s * 0.7, dx / d * s * 0.7
            if self.cd <= 0 and self.los and d < 8:
                self.cd = rnd.uniform(1.4, 2.2)
                w.projs.append(Proj("bolt", self.x + dx / d * 0.5, self.y + dy / d * 0.5, 1.0, dx / d * 6.5, dy / d * 6.5,
                                    12, hostile=True, life=2.0, color=(255, 70, 40), r=0.2))
                w.snd("enemy_shot", self.x, self.y)
            face = (dx, dy) if self.los else None
        elif k == "spitter" and p.alive:
            self.cd -= dt
            if self.los and d < 3.5:
                tx, ty = -dx / d, -dy / d
            elif self.los and d < 8:
                s = 1 if (int(w.time * 0.4 + self.phase) % 2) else -1
                tx, ty = -dy / d * s * 0.4, dx / d * s * 0.4
            if self.cd <= 0 and self.los and 2 < d < 9:
                self.cd = rnd.uniform(2.2, 3.2)
                T = max(0.45, min(1.2, d / 7))
                g = 14.0
                vz = (0.5 * g * T * T - 1.1) / T
                w.projs.append(Proj("acid", self.x, self.y, 1.1, dx / T, dy / T, 10, hostile=True, life=3, color=(120, 255, 60),
                                    r=0.22, vz=vz, grav=g))
                w.snd("acid_spit", self.x, self.y)
            face = (dx, dy) if self.los else None
        elif k == "bloater":
            if d < 4:
                speed *= 2.3
            if p.alive and d < self.r + Player.R + 0.15:
                self.hp = 0
                self.alive = False
                w.kill_enemy(self)
                return
        elif k == "walker" and p.alive:
            self.cd -= dt
            if self.los and d < 4:
                tx, ty = -dx / d, -dy / d
            elif self.los and d < 7.5:
                s = 1 if (int(w.time * 0.3 + self.phase) % 2) else -1
                tx, ty = -dy / d * s * 0.5, dx / d * s * 0.5
            if self.cd <= 0 and self.los and d < 10:
                self.cd = rnd.uniform(3.0, 4.2)
                self.burst = 2
                self.burst_t = 0
            if self.burst > 0:
                self.burst_t -= dt
                if self.burst_t <= 0:
                    self.burst -= 1
                    self.burst_t = 0.3
                    side = 0.33 if self.burst % 2 else -0.33
                    ux, uy = dx / d, dy / d
                    sx, sy = self.x + uy * side, self.y - ux * side
                    vx, vy = rot(ux, uy, rnd.uniform(-0.1, 0.1))
                    w.projs.append(Proj("rocket", sx, sy, 1.1, vx * 4, vy * 4, 16, hostile=True, life=3.5, color=(255, 90, 40),
                                        r=0.18, blast=1.3, maxspeed=9))
                    w.snd("walker_rocket", self.x, self.y)
            face = (dx, dy) if self.los else None
        elif k == "brute":
            tx, ty, speed = self.update_brute(w, dt, dx, dy, d, tx, ty, speed)
        elif k == "hellspawn" and p.alive:
            self.cd -= dt
            if self.los and d < 2.5 and d > 1.2:
                tx, ty = -dx / d, -dy / d
            elif self.los and d < 7:
                s_ = 1 if (int(w.time * 0.6 + self.phase) % 2) else -1
                tx, ty = -dy / d * s_ * 0.8 + dx / d * 0.2, dx / d * s_ * 0.8 + dy / d * 0.2
            if self.cd <= 0 and self.los and 2 < d < 10:
                self.cd = rnd.uniform(1.8, 2.8)
                ux, uy = dx / d, dy / d
                w.projs.append(Proj("fireball", self.x + ux * 0.5, self.y + uy * 0.5, 1.1, ux * 7, uy * 7, 14, hostile=True,
                                    life=2.5, color=(255, 120, 30), r=0.22, blast=0.9))
                w.snd("fireball", self.x, self.y)
            face = (dx, dy) if self.los else None
        elif k == "wretch" and p.alive:
            self.cd -= dt
            if self.cd <= 0 and self.los and 2.5 < d < 9:
                self.cd = rnd.uniform(2.5, 4.5)
                jump = min(d - 1.2, rnd.uniform(2.0, 3.2))
                nx, ny = self.x + dx / d * jump, self.y + dy / d * jump
                if not w.level.is_solid(int(nx), int(ny)):
                    for _ in range(16):
                        w.add(Particle("glow", self.x + rnd.uniform(-0.3, 0.3), self.y + rnd.uniform(-0.3, 0.3),
                                       rnd.uniform(0, 1.6), 0, 0, 0, 0.25, (200, 200, 200), 2))
                    self.x, self.y = nx, ny
                    w.snd("wretch_blink", self.x, self.y)
                    w.static_kick = 0.6
        elif k == "stalker" and p.alive:
            self.cd -= dt
            if self.lunge > 0:
                self.lunge -= dt
                tx, ty, speed = self.ldx, self.ldy, 9.0
            elif self.cd <= 0 and self.los and d < 2.2:
                self.cd = rnd.uniform(1.4, 2.0)
                w.beams.append([self.x, self.y, p.x, p.y, 0.5, 0.15, 0.15, (200, 60, 80), 0.9])
                w.hurt_player(10, self.x, self.y)
                w.snd("tongue", self.x, self.y)
            elif self.cd <= 0 and self.los and 2.2 <= d < 5:
                self.lunge = 0.35
                self.ldx, self.ldy = dx / d, dy / d
                self.cd = rnd.uniform(1.5, 2.4)
                w.snd("stalker_screech", self.x, self.y)
        elif k == "mimic" and p.alive:
            self.cd -= dt
            if self.cd <= 0 and d < 1.9:
                self.cd = rnd.uniform(0.9, 1.4)
                for _ in range(2):
                    a = rnd.uniform(-0.3, 0.3)
                    ex_, ey_ = rot(dx / d, dy / d, a)
                    w.beams.append([self.x, self.y, self.x + ex_ * d, self.y + ey_ * d, 0.6, 0.18, 0.18, (170, 40, 50), 1.2])
                w.hurt_player(14, self.x, self.y)
                w.snd("tongue", self.x, self.y)
        sx, sy = w.separation(self)
        dvx, dvy = tx * speed + sx, ty * speed + sy
        a = min(1.0, dt * (14 if (self.lunge > 0 or self.state == "charge") else 6))
        self.vx += (dvx - self.vx) * a
        self.vy += (dvy - self.vy) * a
        ox, oy = self.x, self.y
        self.x, self.y = resolve(w.level, self.x + self.vx * dt, self.y + self.vy * dt, self.r)
        moved = math.hypot(self.x - ox, self.y - oy)
        if self.state == "charge" and moved < 7 * dt * 0.3 and self.state_t < 0.85:
            self.state, self.state_t = "stun", 1.1
            w.shake = max(w.shake, 9)
            w.snd("stomp", self.x, self.y)
        if face:
            self.dir = dir_index(face[0], face[1], 8)
        elif math.hypot(self.vx, self.vy) > 0.25:
            self.dir = dir_index(self.vx, self.vy, 8)
        before = self.frame
        self.frame += moved / self.st["stride"] * 6 + (dt * 6 if k in FLYERS else 0)
        if k in ("brute", "walker") and int(before / 3) != int(self.frame / 3):
            w.snd("stomp", self.x, self.y, 0.6)
        if k == "leech" and moved > 0 and rnd.random() < dt * 3:
            w.splat(self.x, self.y, (50, 90, 20), 0.06)
        dmg = self.st["dmg"]
        if p.alive and dmg and d < self.r + Player.R + 0.08 and not self.submerged:
            if self.bdef and self.bdef.get("on_hit"):
                w.player_effect(self.bdef["on_hit"], self)
            if self.state == "charge":
                w.hurt_player(32, self.x, self.y, knock=16)
                self.state, self.state_t = "walk", 0
                self.cd = rnd.uniform(3, 4.5)
            else:
                w.hurt_player(dmg, self.x, self.y)
            if self.lunge > 0:
                self.lunge = 0

    def generic_ai(self, w, dt, dx, dy, d, tx, ty, speed):
        """Data-driven behaviours for the expansion bestiary. Returns (tx, ty, speed, face) or None if the enemy died."""
        bd = self.bdef
        ai = bd.get("then", bd["ai"]) if bd["ai"] == "riser" else bd["ai"]
        sh = bd.get("shot")
        p = self.target
        face = None
        ux, uy = dx / d, dy / d
        shooter = None
        if bd.get("melty") and rnd.random() < dt * 2:
            w.splat(self.x + rnd.uniform(-0.2, 0.2), self.y + rnd.uniform(-0.2, 0.2), bd.get("puddle", self.blood), 0.08)
        if ai == "swarm":
            wob = math.sin(w.time * 9 + self.phase) * 0.8
            tx, ty = tx - ty * wob, ty + tx * wob
        elif ai in ("flyer", "pouncer"):
            if ai == "flyer":
                wob = math.sin(w.time * 5 + self.phase) * 0.7
                tx, ty = tx - ty * wob, ty + tx * wob
            if self.lunge > 0:
                self.lunge -= dt
                tx, ty, speed = self.ldx, self.ldy, 8.0
            else:
                self.cd -= dt
                if self.cd <= 0 and self.los and d < 5:
                    self.lunge = 0.4
                    self.ldx, self.ldy = ux, uy
                    self.cd = rnd.uniform(1.4, 2.4)
                    w.snd("stalker_screech" if ai == "pouncer" else "skull_screech", self.x, self.y, 0.8)
        elif ai == "charger":
            tx, ty, speed = self.update_brute(w, dt, dx, dy, d, tx, ty, speed)
        elif ai == "exploder":
            if d < 4:
                speed *= 2.0
            if p.alive and d < self.r + 0.45:
                self.hp = 0
                self.alive = False
                w.kill_enemy(self)
                return None
        elif ai == "eel":
            if d < 1.6:
                tx, ty = -ux * 0.3, -uy * 0.3
            self.cd -= dt
            if self.cd <= 0 and d < self.reach and self.los:
                self.cd = rnd.uniform(1.2, 1.8)
                self.eel_tx, self.eel_ty = p.x, p.y
                self.eel_t = 0.0
                self.eel_all = rnd.random() < 0.5
                w.snd("tongue", self.x, self.y)
            from bosses import update_eels
            update_eels(self, w, dt, self.st["dmg"])
            face = (dx, dy)
        # ---------------- signature mechanics
        elif ai == "pinkgunner":      # rolls a real player weapon and fights with it
            if self.weapon is None:
                light = ["pistol", "revolver", "smg", "shotgun", "carbine", "assault", "laser_pistol", "shotgun_2"]
                heavy = ["plasma", "grenade", "flamer", "saw", "rocket", "auto_shotgun", "shotgun_3", "shotgun_4"]
                arch = rnd.choice(light if w.depth <= 2 else light + heavy)   # no launchers in the first sectors
                if bd.get("arsenal"):
                    ars = [(a_, wt) for a_, wt in bd["arsenal"] if a_ != "tac_nuke" or w.depth >= 3]
                    arch = rnd.choices([a_ for a_, _ in ars], weights=[wt for _, wt in ars])[0]
                self.weapon = WP.generate(w.depth, arch=arch, rarity=WP.roll_rarity(rnd, w.depth))
                self.wshot = weapon_to_shot(self.weapon)
            sh = self.wshot
            shooter = "spewer" if sh["rng"] < 5 else "gunner"
            if bd.get("arsenal"):
                shooter = "sniper" if sh.get("aimed") else "heavy"
                if self.burst > 0 or self.aim_t > 0:
                    speed *= 0.35          # plants its feet while it fires
                if self.burst > 0 and sh.get("windup") and self.burst_t > sh["gap"] and rnd.random() < dt * 30:
                    a_ = math.atan2(dy, dx)    # barrels spinning up: sparks at the muzzle
                    w.add(Particle("spark", self.x + math.cos(a_) * 0.6, self.y + math.sin(a_) * 0.6, 1.0, rnd.uniform(-2, 2),
                                   rnd.uniform(-2, 2), rnd.uniform(0, 2), 0.2, (255, 220, 140), 2))
        elif ai == "summoner":
            self.cd2 -= dt
            if self.cd2 <= 0 and self.los and d < 11 and self.children < bd["summon"][2]:
                self.cd2 = rnd.uniform(5.0, 7.0)
                kind, n, _ = bd["summon"]
                for _ in range(n):
                    a_ = rnd.random() * math.tau
                    x_, y_ = self.x + math.cos(a_) * 0.9, self.y + math.sin(a_) * 0.9
                    if not w.level.is_solid(int(x_), int(y_)):
                        c = Enemy(kind, x_, y_, awake=True, depth=w.depth)
                        c.owner = self
                        self.children += 1
                        w.enemies.append(c)
                        for _ in range(10):
                            w.add(Particle("glow", x_, y_, 0.1, rnd.uniform(-1, 1), rnd.uniform(-1, 1), 1.5, 0.6, (170, 220, 255), 2))
                w.snd("spawn", self.x, self.y)
            shooter = "summoner"
        elif ai in ("grappler", "boomerang", "charmer"):
            shooter = "gunner" if ai != "charmer" else "caster"
        elif ai == "statue":          # only moves while you are not aiming at it
            ax, ay = p.aim
            watched = (-dx * ax - dy * ay) / d > 0.3
            if watched:
                speed = 0.0
                self.frame -= dt * 0      # frozen pose
            else:
                speed = bd["speed"]
                if rnd.random() < dt * 4:
                    w.add(Particle("chunk", self.x, self.y, 0.1, rnd.uniform(-1, 1), rnd.uniform(-1, 1), 1, 0.8, (150, 148, 140), 2))
        elif ai == "vacuum":          # inhales, dragging the player toward its maw
            self.cd -= dt
            if self.state2 == "inhale":
                self.state_t -= dt
                speed = 0.0
                if p.alive and d < 7 and self.los:
                    pull = 2.8 * (1.2 - d / 7)
                    p.x, p.y = resolve(w.level, p.x - ux * pull * dt, p.y - uy * pull * dt, p.R)
                    if rnd.random() < dt * 30:
                        t_ = rnd.uniform(0.3, 1.0)
                        w.add(Particle("glow", self.x + dx * t_, self.y + dy * t_, 0.8, -ux * 6, -uy * 6, 0, 0.3, (200, 190, 120), 2))
                if self.state_t <= 0:
                    self.state2 = None
                    self.cd = rnd.uniform(3.0, 4.5)
            elif self.cd <= 0 and self.los and d < 6.5:
                self.state2 = "inhale"
                self.state_t = 2.4
                w.snd("lunge", self.x, self.y)
            face = (dx, dy)
        elif ai == "geomancer":       # calls bog geysers onto marked spots
            if self.los and d < 4:
                tx, ty = -ux, -uy
            elif self.los and d < 9:
                tx, ty = -uy * 0.5, ux * 0.5
            self.cd -= dt
            if self.cd <= 0 and self.los and d < 10:
                self.cd = rnd.uniform(3.0, 4.0)
                for i in range(3):
                    a_, r_ = rnd.random() * math.tau, (0 if i == 0 else rnd.uniform(1.0, 2.2))
                    x_, y_ = p.x + math.cos(a_) * r_, p.y + math.sin(a_) * r_
                    w.warnings.append([x_, y_, 0.9, 1.0, 1.0, (80, 160, 60)])
                    w.projs.append(Proj("mortar", x_, y_, 6.0, 0, 0, 12, hostile=True, life=4, color=(90, 150, 60), r=0.3, blast=0.9, vz=-6.0))
                w.snd("acid_spit", self.x, self.y)
            face = (dx, dy) if self.los else None
        elif ai == "zealot":          # hurts itself into a frenzy; whips at close range
            frac = max(0.05, self.hp / self.maxhp)
            speed *= 1 + 1.6 * (1 - frac)
            self.cd -= dt
            if self.cd <= 0:
                self.cd = rnd.uniform(3.0, 4.0)
                self.hp = max(1.0, self.hp - self.maxhp * 0.07)
                w.spray(self.x, self.y, 1.0, self.blood, 10, 2.5)
                w.snd("hit_flesh", self.x, self.y)
            self.cd2 -= dt
            if self.cd2 <= 0 and p.alive and d < 2.4 and self.los:
                self.cd2 = 1.2 * frac + 0.4
                w.beams.append([self.x, self.y, p.x, p.y, 1.0, 0.15, 0.15, (220, 50, 30), 0.7])
                w.hurt_player(self.st["dmg"] * (1 + (1 - frac)), self.x, self.y)
                w.snd("tongue", self.x, self.y)
        elif ai == "bomber":          # hovers over you dropping radioactive puddles
            a_ = w.time * 0.9 + self.phase
            hx_, hy_ = p.x + math.cos(a_) * 0.6 - self.x, p.y + math.sin(a_) * 0.6 - self.y
            hl = math.hypot(hx_, hy_) or 1
            tx, ty = hx_ / hl, hy_ / hl
            self.cd -= dt
            if self.cd <= 0 and d < 3:
                self.cd = rnd.uniform(2.0, 2.6)
                w.hazards.append([self.x, self.y, 0.9, 5.0, "rad", 6.0, 5.0])
                w.snd("sizzle", self.x, self.y)
        elif ai == "splitter":        # divides when badly hurt
            if not self.split_done and self.gen < 2 and self.hp < self.maxhp * 0.5:
                self.split_done = True
                c = Enemy(self.kind, self.x + rnd.uniform(-0.3, 0.3), self.y + rnd.uniform(-0.3, 0.3), awake=True, depth=w.depth)
                c.hp = c.maxhp = self.hp
                c.gen = self.gen + 1
                self.maxhp = self.hp
                self.gen += 1
                self.split_done = False
                w.enemies.append(c)
                w.spray(self.x, self.y, 0.8, self.blood, 16, 3)
                w.snd("splat", self.x, self.y)
        elif ai in ("lurker", "burrower"):   # hides underground / underwater, untouchable until it surfaces
            self.state_t -= dt
            if self.submerged:
                speed = bd["speed"] * 1.2
                if rnd.random() < dt * 14:
                    col = (110, 95, 40) if ai == "lurker" else (60, 40, 30)
                    w.add(Particle("chunk" if ai == "burrower" else "glow", self.x + rnd.uniform(-0.3, 0.3), self.y + rnd.uniform(-0.3, 0.3), 0.05,
                                   rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(1, 2), 0.6, col, 3))
                if ai == "lurker" and self.state_t <= 0 and d < 4.5 and self.los:
                    self.submerged = False
                    self.state_t = 2.8
                    w.spray(self.x, self.y, 0.3, self.blood, 16, 3)
                    w.snd("splat", self.x, self.y)
                elif ai == "burrower" and self.state_t <= 0:
                    if self.erupt_t > 0:
                        self.erupt_t -= dt
                        speed = 0.0
                        if self.erupt_t <= 0:
                            self.submerged = False
                            self.state_t = 2.5
                            w.explode(self.x, self.y, 1.3, 4, (255, 120, 30), hurt_player=True, quiet=False, player_dmg=16)
                    elif d < 0.9:
                        self.erupt_t = 0.7
                        w.warnings.append([self.x, self.y, 1.3, 0.7, 0.7, (255, 110, 30)])
            else:
                if self.state_t <= 0:
                    self.submerged = True
                    self.state_t = 2.5 if ai == "lurker" else 1.5
                    w.spray(self.x, self.y, 0.2, self.blood, 8, 2)
                elif ai == "lurker":
                    speed = 0.0
                    shooter = "lobber"
        elif ai == "sprayer":
            shooter = "spewer"
        elif ai == "shield":          # advances behind a tower shield, bashes at close range
            face = (dx, dy)
            if self.lunge > 0:
                self.lunge -= dt
                tx, ty, speed = self.ldx, self.ldy, 6.0
            else:
                self.cd -= dt
                if self.cd <= 0 and self.los and d < 1.9:
                    self.lunge = 0.3
                    self.ldx, self.ldy = ux, uy
                    self.cd = rnd.uniform(1.6, 2.4)
                    w.snd("stomp", self.x, self.y, 0.6)
        elif ai == "snake":           # weaves in, coils (a tell), then strikes; cobras also spit venom
            if self.lunge > 0:
                self.lunge -= dt
                tx, ty, speed = self.ldx, self.ldy, 9.5
            elif self.state2 == "coil":
                self.state_t -= dt
                speed = 0.0
                face = (dx, dy)
                if int(self.state_t * 16) % 2 == 0:
                    self.flash = 0.03
                if self.state_t <= 0:
                    self.state2 = None
                    self.lunge = 0.26
                    self.ldx, self.ldy = ux, uy
                    w.snd("lunge", self.x, self.y, 0.7)
            else:
                wob = math.sin(w.time * 6 + self.phase) * 0.9
                tx, ty = tx - ty * wob, ty + tx * wob
                self.cd2 -= dt
                if self.cd2 <= 0 and self.los and p.alive and d < 2.8:
                    self.state2, self.state_t = "coil", 0.42
                    self.cd2 = rnd.uniform(1.6, 2.4)
                    w.snd("tongue", self.x, self.y, 0.6)
            if sh and self.state2 is None and self.lunge <= 0 and d > 3.2:
                shooter = "snake"
        elif ai == "scorpion":        # front armour; a telegraphed tail sting at the spot you stood on
            face = (dx, dy)
            if self.state2 == "sting":
                self.state_t -= dt
                speed = 0.0
                if int(self.state_t * 14) % 2 == 0:
                    self.flash = 0.03
                if self.state_t <= 0:
                    self.state2 = None
                    sx_, sy_ = self.stx, self.sty
                    w.beams.append([self.x, self.y, sx_, sy_, 0.6, 0.18, 0.18, (170, 230, 60), 1.4])
                    w.snd("tongue", self.x, self.y)
                    for pl in w.players:
                        if pl.alive and math.hypot(pl.x - sx_, pl.y - sy_) < 0.65:
                            w.hurt_player(self.st["dmg"] * 1.8, self.x, self.y, who=pl, dtype="chemical")
                            w.player_effect("venom", self, who=pl)
                    for _ in range(8):
                        a_ = rnd.random() * math.tau
                        w.add(Particle("glow", sx_, sy_, 0.2, math.cos(a_) * 2, math.sin(a_) * 2, 1.5, 0.4, (170, 230, 60), 2))
            else:
                if self.los and d < 4.5:   # sidles round you, pincers first
                    sgn = 1 if (int(w.time * 0.4 + self.phase) % 2) else -1
                    tx, ty = tx * 0.6 - uy * sgn * 0.6, ty * 0.6 + ux * sgn * 0.6
                self.cd2 -= dt
                if self.cd2 <= 0 and self.los and p.alive and d < 2.6:
                    self.state2, self.state_t = "sting", 0.55
                    self.stx, self.sty = p.x, p.y
                    self.cd2 = rnd.uniform(1.8, 2.6)
                    w.warnings.append([p.x, p.y, 0.65, 0.55, 0.55, (170, 230, 60)])
                    w.snd("stalker_screech", self.x, self.y, 0.5)
        elif ai == "roach":           # skitters in jinks; dodges sideways when you aim at it
            ax, ay = getattr(p, "aim", (1.0, 0.0))
            watched = self.los and (-dx * ax - dy * ay) / d > 0.9
            if watched:
                sgn = 1 if (int(w.time * 2.5 + self.phase) % 2) else -1
                tx, ty = -uy * sgn * 0.9 + ux * 0.25, ux * sgn * 0.9 + uy * 0.25
                speed *= 1.25
            else:
                wob = math.sin(w.time * 13 + self.phase * 3) * 0.7
                tx, ty = tx - ty * wob, ty + tx * wob
        elif ai == "imp":             # flits about throwing fireballs, hopping away in a puff of flame
            wob = math.sin(w.time * 5 + self.phase) * 0.8
            tx, ty = tx - ty * wob, ty + tx * wob
            self.cd2 -= dt
            if self.cd2 <= 0 and self.los and d < 7:
                self.cd2 = rnd.uniform(3.0, 5.0)
                w.fire_puff(self.x, self.y, 10)
                for _ in range(8):
                    a_ = rnd.random() * math.tau
                    x_, y_ = self.x + math.cos(a_) * rnd.uniform(1.2, 2.4), self.y + math.sin(a_) * rnd.uniform(1.2, 2.4)
                    if not w.level.is_solid(int(x_), int(y_)) and w.level.line_of_sight(self.x, self.y, x_, y_):
                        self.x, self.y = x_, y_
                        break
                w.fire_puff(self.x, self.y, 10)
                w.snd("wretch_blink", self.x, self.y, 0.6)
            shooter = "caster"
        elif ai == "breather":        # pit demon: plods in and breathes a sweeping cone of fire
            if self.state2 == "breath":
                self.state_t -= dt
                speed *= 0.25
                diff = (math.atan2(dy, dx) - self.bang + math.pi) % math.tau - math.pi
                self.bang += max(-1.1 * dt, min(1.1 * dt, diff))      # tracks you, but slowly: circle it
                face = (math.cos(self.bang), math.sin(self.bang))
                self.burst_t -= dt
                if self.burst_t <= 0:
                    self.burst_t = 0.04
                    a_ = self.bang + rnd.uniform(-0.17, 0.17)
                    c_, s_ = math.cos(a_), math.sin(a_)
                    sp_ = rnd.uniform(6.5, 8.0)
                    pr = Proj("flame", self.x + c_ * 0.55, self.y + s_ * 0.55, 1.2, c_ * sp_, s_ * sp_, 7, hostile=True, life=0.6,
                              color=(255, 140, 40), r=0.2)
                    pr.effect = "burn"
                    pr.owner = self
                    w.projs.append(pr)
                if self.state_t <= 0:
                    self.state2 = None
                    self.cd2 = rnd.uniform(2.6, 3.6)
            else:
                self.cd2 -= dt
                if self.cd2 <= 0 and self.los and p.alive and d < 4.4:
                    self.state2, self.state_t = "breath", 1.7
                    self.bang = math.atan2(dy, dx)
                    self.burst_t = 0.35       # a beat of smoke and glow before the fire comes
                    w.fire_puff(self.x + ux * 0.5, self.y + uy * 0.5, 6)
                    w.snd("brute_roar", self.x, self.y, 0.8)
                    w.snd("shot_flame", self.x, self.y, 0.8)
        elif ai == "devil":           # hurls fans of hellfire; when you get close it vanishes, leaving the floor burning
            self.cd2 -= dt
            if self.cd2 <= 0 and p.alive and d < 2.6:
                self.cd2 = rnd.uniform(3.5, 5.0)
                w.fire_puff(self.x, self.y, 18)
                w.hazards.append([self.x, self.y, 0.9, 3.5, "blaze", 10.0])
                for _ in range(16):
                    a_ = rnd.random() * math.tau
                    r_ = rnd.uniform(4.0, 6.5)
                    x_, y_ = p.x + math.cos(a_) * r_, p.y + math.sin(a_) * r_
                    if (0 < x_ < w.level.W and 0 < y_ < w.level.H and not w.level.is_solid(int(x_), int(y_))
                            and w.level.line_of_sight(p.x, p.y, x_, y_)):
                        self.x, self.y = x_, y_
                        break
                w.fire_puff(self.x, self.y, 18)
                w.snd("wretch_blink", self.x, self.y)
                self.cd = min(self.cd, 0.5)       # and opens fire straight away
            shooter = "caster"
        elif sh:
            shooter = ai
        # ---------------- shared ranged behaviour
        if shooter and sh and p.alive:
            rng_ = sh["rng"]
            keep = {"gunner": (3.0, 7.5), "sniper": (6.0, 11.0), "caster": (3.0, 8.0), "lobber": (2.5, 8.0), "spewer": (0.0, 3.2),
                    "summoner": (5.0, 9.0), "heavy": (4.0, 9.0), "snake": (0.0, 0.0)}.get(shooter, (3, 8))
            if speed > 0:
                if self.los and d < keep[0]:
                    tx, ty = -ux, -uy
                elif self.los and d < keep[1]:
                    sgn = 1 if (int(w.time * 0.5 + self.phase) % 2) else -1
                    tx, ty = -uy * sgn * 0.6, ux * sgn * 0.6
            self.cd -= dt
            if self.aim_t > 0:   # sniper telegraph
                self.aim_t -= dt
                w.beams.append([self.x, self.y, p.x, p.y, self.hz, 0.03, 0.03, (255, 40, 40), 0.25])
                tx = ty = 0.0
                if self.aim_t <= 0:
                    w.enemy_shoot(self, sh, math.atan2(dy, dx))
            elif self.cd <= 0 and self.los and sh.get("minr", 0) < d < rng_:
                self.cd = rnd.uniform(*sh["cd"])
                if shooter == "sniper":
                    self.aim_t = sh.get("aimed", 0.8)
                    w.snd("turret_beep", self.x, self.y, 0.7)
                else:
                    self.burst = sh["burst"]
                    self.burst_t = sh.get("windup", 0.0)
                    if sh.get("windup"):
                        w.snd("servo", self.x, self.y, 0.8)
            if self.burst > 0:
                self.burst_t -= dt
                if self.burst_t <= 0:
                    self.burst -= 1
                    self.burst_t = sh["gap"]
                    base = math.atan2(dy, dx)
                    n = sh["count"]
                    for i in range(n):
                        if sh["spread"] >= 3.0:      # full ring: one orb always points straight at you
                            off = math.tau * i / n
                        else:
                            off = sh["spread"] * (i / (n - 1) - 0.5) if n > 1 else rnd.uniform(-0.04, 0.04)
                        if sh.get("jitter"):
                            off += rnd.uniform(-sh["jitter"], sh["jitter"])
                        w.enemy_shoot(self, sh, base + off)
            face = (dx, dy) if self.los else None
        return tx, ty, speed, face

    def update_brute(self, w, dt, dx, dy, d, tx, ty, speed):
        self.cd -= dt
        if self.state == "walk":
            if self.cd <= 0 and self.los and 2.5 < d < 8:
                self.state, self.state_t = "windup", 0.65
                w.snd("brute_roar", self.x, self.y)
            return tx, ty, speed
        self.state_t -= dt
        if self.state == "windup":
            if int(self.state_t * 8) % 2 == 0:
                self.flash = 0.04
            self.dir = dir_index(dx, dy, 8)
            if self.state_t <= 0:
                self.state, self.state_t = "charge", 1.0
                self.ldx, self.ldy = dx / d, dy / d
            return 0.0, 0.0, 0.0
        if self.state == "charge":
            if self.state_t <= 0:
                self.state = "walk"
                self.cd = rnd.uniform(3, 4.5)
            if rnd.random() < dt * 20:
                w.add(Particle("smoke", self.x, self.y, 0.1, rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0.3, 0.8, (70, 60, 55), 0.2))
            return self.ldx, self.ldy, 7.0
        if self.state == "stun":
            if self.state_t <= 0:
                self.state = "walk"
                self.cd = rnd.uniform(2, 3.5)
            return 0.0, 0.0, 0.0
        return tx, ty, speed

    def update_turret(self, w, dt, dx, dy, d):
        target = math.atan2(dy, dx)
        diff = (target - self.angle + math.pi) % math.tau - math.pi
        turn = 2.4 * dt * (0.5 if self.slow > 0 else 1.0)
        self.angle += max(-turn, min(turn, diff))
        self.dir = dir_index(math.cos(self.angle), math.sin(self.angle), 8)
        self.frame += dt * 6
        self.cd -= dt
        if self.cd <= 0 and self.los and d < 10 and abs(diff) < 0.35 and self.target.alive:
            self.cd = rnd.uniform(1.8, 2.6)
            self.burst = 3
            self.burst_t = 0
        if self.burst > 0:
            self.burst_t -= dt
            if self.burst_t <= 0:
                self.burst -= 1
                self.burst_t = 0.13
                ux, uy = math.cos(self.angle), math.sin(self.angle)
                vx, vy = rot(ux, uy, rnd.uniform(-0.05, 0.05))
                w.projs.append(Proj("bolt", self.x + ux * 0.55, self.y + uy * 0.55, 0.75, vx * 10, vy * 10, 7, hostile=True,
                                    life=1.6, color=(255, 90, 40), r=0.15))
                w.snd("turret_shot", self.x, self.y)

    def follow_flow(self, w, fx, fy):
        f = w.flow
        if f is None:
            return fx, fy
        L = w.level
        cx, cy = int(self.x), int(self.y)
        here = f[L.i(cx, cy)]
        if here < 0:
            return fx, fy
        best, bx, by = here, None, None
        for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = cx + ddx, cy + ddy
            if L.is_solid(nx, ny):
                continue
            v = f[L.i(nx, ny)]
            if 0 <= v < best:
                best, bx, by = v, nx + 0.5, ny + 0.5
        if bx is None:
            return fx, fy
        tx, ty = bx - self.x, by - self.y
        l = math.hypot(tx, ty) or 1
        return tx / l, ty / l

    def hit(self, w, dmg, vx, vy):
        self.hp -= dmg
        self.flash = 0.08
        self.hitvx, self.hitvy = vx, vy
        if self.kind not in ("spider", "brute", "turret", "walker"):
            self.vx += vx * 0.08
            self.vy += vy * 0.08
        self.awake = True
        sp = math.hypot(vx, vy) or 1
        ux, uy = vx / sp, vy / sp
        hz = self.st["hz"]
        if self.blood in (OIL, ASH):
            for _ in range(6):
                a = rnd.uniform(-1.2, 1.2)
                v = rnd.uniform(3, 7)
                ex, ey = rot(ux, uy, a)
                w.add(Particle("spark", self.x, self.y, hz, ex * v, ey * v, rnd.uniform(1, 4), 0.3, (255, 220, 120), 2))
        for _ in range(7):
            a = rnd.uniform(-0.6, 0.6)
            v = rnd.uniform(1.5, 4.5)
            ex, ey = rot(ux, uy, a)
            w.add(Particle("blood", self.x + ux * 0.2, self.y + uy * 0.2, hz, ex * v, ey * v, rnd.uniform(0.5, 3), 1.5,
                           self.blood, rnd.uniform(2.5, 5)))
        if self.hp <= 0 and self.alive:
            self.alive = False
            w.kill_enemy(self)
        else:
            w.snd("hit_metal" if self.blood in (OIL, ASH) else "hit_flesh", self.x, self.y)


class Spawner:
    def __init__(self, kind, x, y, depth=1):
        self.kind, self.x, self.y, self.depth = kind, x, y, depth
        self.hp = 30 * (1 + 0.12 * (depth - 1))
        self.cd = rnd.uniform(1.5, 4.0)
        self.flash = 0.0
        self.t = rnd.random() * 4
        self.children = 0
        self.alive = True
        self.r = 0.45

    def update(self, w, dt):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        p = w.nearest_player(self.x, self.y)
        if math.hypot(p.x - self.x, p.y - self.y) > 11 or not p.alive:
            return
        self.cd -= dt
        if self.cd <= 0:
            self.cd = rnd.uniform(3.0, 5.5) / (1 + w.depth * 0.12)
            if self.children < 5 and len(w.enemies) < 70:
                a = rnd.random() * math.tau
                ex, ey = self.x + math.cos(a) * 0.8, self.y + math.sin(a) * 0.8
                if not w.level.is_solid(int(ex), int(ey)):
                    e = Enemy(self.kind, ex, ey, awake=True, depth=self.depth)
                    e.owner = self
                    self.children += 1
                    w.enemies.append(e)
                    w.spray(ex, ey, 0.5, ICHOR, 14, 3.0)
                    w.splat(ex, ey, ICHOR, 0.2)
                    w.snd("spawn", ex, ey)

    def hit(self, w, dmg):
        self.hp -= dmg
        self.flash = 0.06
        w.spray(self.x, self.y, 0.5, ICHOR, 4, 2.5)
        if self.hp <= 0 and self.alive:
            self.alive = False
            w.kill_spawner(self)
        else:
            w.snd("hit_flesh", self.x, self.y)


# ---------------------------------------------------------------- world
class World:
    def __init__(self, depth=1, players=None, score=0, seed=None, biome="facility"):
        self.depth = depth
        self.biome = biome
        self.level = L = Level(depth, seed, biome)
        if players is None:
            players = [Player(*L.start)]
        elif isinstance(players, Player):
            players = [players]
        for i, pl in enumerate(players):
            pl.x, pl.y = resolve(L, L.start[0] + (0.7 if i else 0.0), L.start[1] + (0.7 if i else 0.0), pl.R)
            pl.kbx = pl.kby = 0.0
            if not pl.alive:      # downed players come back at the next sector
                pl.alive = True
                pl.hp = pl.max_hp * 0.5
            pl.idx = i
        self.players = players
        for pl in players:
            for i, g in enumerate(pl.gear):
                if g is not None:
                    g.attach(pl, i)
            pl.salvo_q = 0
        self._shooter = players[0]
        self.arcs = []             # lightning: [[(x, y, z), ...], life, max, colour, width]
        self.decoys = []           # decoy projector holograms monsters chase instead of players
        self.turrets = []          # deployed MG / mortar turrets
        self.popups = []           # floating "WEAK" / "RESIST" ticks and damage numbers [x, y, z, text, colour, life]
        self.show_numbers = False  # coloured damage numbers (option on the title / pause screens)
        self.dot_targets = []      # monsters with pooled (spray / damage-over-time) numbers waiting to show
        self.blocked = set()       # ids of enemy projectiles eaten by an arc shield this frame
        self.near_loot_by = {}
        self.net_events = None     # net play host: sounds / music for the guests ([("s", name, x, y, vol), ...])
        self.actor = None          # the player whose action is running (so a guest's reload click only plays for them)
        self.local_idx = None      # net play: which players sit at this machine (None = all of them)
        self.free_roam = False     # net play: everyone has their own screen, so no co-op leash
        self.score = score
        self.time = 0.0
        self.enemies = [Enemy(k, x, y, depth=depth) for k, x, y in L.enemies]
        self.spawners = [Spawner(k, x, y, depth) for k, x, y in L.spawners]
        for s in self.spawners:
            L.solid[L.i(int(s.x), int(s.y))] = 2
        self.loot = []
        suprng = random.Random(L.seed ^ 0x5099)
        wspots = [i for i, pk in enumerate(L.pickups) if pk[0] == "weapon"]
        sup_at = {i for i in wspots if suprng.random() < 0.2}
        if wspots and not sup_at:          # at least one support item per sector
            sup_at.add(suprng.choice(wspots))
        for i_, (kind, x, y) in enumerate(L.pickups):
            if i_ in sup_at:
                self.loot.append(Loot("support", x, y, SU.generate(depth, suprng, bonus=0.3)))
            elif kind == "weapon":
                self.loot.append(Loot("weapon", x, y, WP.generate(depth, bonus=0.3)))
            elif kind == "power":
                self.loot.append(Loot("buff", x, y, WP.roll_buff(level=depth)))
            else:
                self.loot.append(Loot("health", x, y))
        # explosive barrels: each rolls a kind (biome-weighted) and shows it by colour
        brng = random.Random(L.seed ^ 0xBA22E1)
        bw = BARREL_WEIGHTS.get(biome, BARREL_WEIGHTS["default"])
        self.barrels = {}
        self.barrel_kind = {}
        for pos, name in list(L.props.items()):
            if name == "barrel":
                kind = brng.choices(list(bw), weights=list(bw.values()))[0]
                L.props[pos] = "barrel_" + kind
                self.barrels[pos] = 3
                self.barrel_kind[pos] = kind
            elif name in ("raddrum", "chemdrum"):       # the sectors' own drums go off too, keeping their look
                self.barrels[pos] = 3
                self.barrel_kind[pos] = "rad" if name == "raddrum" else "chem"
        self.crates = {pos: 4 for pos, name in L.props.items() if name == "crate"}
        self.projs = []
        self.beams = []            # [x1, y1, x2, y2, z, life, max, colour, width]
        self.hazards = []          # acid pools [x, y, r, life]
        self.particles = []
        self.ejects = []               # [seconds left, shooter, casing kind] - spent casings still to fly out
        self.gibs = []
        self.decals = []
        self.messages = []         # [text, colour, life]
        self.flow = None
        self.flow_tile = None
        self.shake = 0.0
        self.hitstop = 0.0
        self.exit_reached = False
        self.explored = bytearray(L.W * L.H)
        self.explore_dirty = []
        self.explore_t = 0.0
        self.hurt_flash = 0.0
        self.kills = 0
        self.grid = {}
        self.near_loot = None
        self.acid_t = 0.0
        self.static = 0.0
        self.static_kick = 0.0
        self.warnings = []    # mortar target circles [x, y, r, life, max, colour]
        self.flash_white = 0.0
        self.bosses = []
        from biomes import BIOMES
        self.biome_music = BIOMES[biome]["music"]
        if depth >= 2 and BIOMES[biome].get("bosses") and L.boss_spot:
            from bosses import Boss
            brng = random.Random(L.seed ^ 0xB055)
            self.bosses.append(Boss(brng.choice(BIOMES[biome]["bosses"]), L.boss_spot[0], L.boss_spot[1], depth))
        # environmental traps (2-3 kinds per biome)
        import traps as TR
        self.traps = TR.place(L, biome, depth, random.Random(L.seed ^ 0x7A95))
        self.shootables = []
        if self.traps:
            self.message("HAZARDS:  " + TR.intro(biome), (255, 170, 90))
        # biome stains (oil, rust, scorch, slush...) break up the floor at a larger scale than single tiles
        from biomes import STAINS
        srng = random.Random(L.seed ^ 0xA11)
        for idx in range(L.W * L.H):
            if L.solid[idx] == 0 and L.floor[idx] not in ("floor_hazard",):
                for col, (r0, r1), p in STAINS.get(biome, ()):
                    if srng.random() < p:
                        x, y = idx % L.W + srng.random(), idx // L.W + srng.random()
                        self.decals.append((x, y, col, srng.uniform(r0, r1), srng.randrange(12)))

    # ---- players
    @property
    def player(self):
        """Primary player (first one alive) - kept for single-player code paths."""
        for pl in self.players:
            if pl.alive:
                return pl
        return self.players[0]

    def nearest_player(self, x, y):
        best, bd = None, 1e9
        for pl in self.players:
            if pl.alive:
                d = (pl.x - x) ** 2 + (pl.y - y) ** 2
                if d < bd:
                    best, bd = pl, d
        return best or self.players[0]

    def target_for(self, x, y):
        """Who a monster at (x, y) goes after: any decoy hologram within 10 tiles wins, else the nearest player."""
        if self.decoys:
            d = min(self.decoys, key=lambda q: (q.x - x) ** 2 + (q.y - y) ** 2)
            if (d.x - x) ** 2 + (d.y - y) ** 2 < 100:
                return d
        p = self.nearest_player(x, y)
        if self.turrets:                  # a deployed turret closer than any player gets mobbed instead
            t = min(self.turrets, key=lambda q: (q.x - x) ** 2 + (q.y - y) ** 2)
            if (t.x - x) ** 2 + (t.y - y) ** 2 < ((p.x - x) ** 2 + (p.y - y) ** 2 if p.alive else 1e9):
                return t
        return p

    def add_player(self, char=None, idx=None, limit=2, name=""):
        """Drop-in co-op: a new player appears next to the first living one."""
        if len(self.players) >= limit:
            return None
        host = self.player
        if char is None:            # default to a different body than the host
            char = CH.ORDER[(CH.ORDER.index(host.char) + 1) % len(CH.ORDER)]
        if idx is None:
            idx = next(i for i in range(limit + 1) if all(p.idx != i for p in self.players))
        pl = Player(host.x, host.y, idx=idx, char=char, name=name)
        pl.x, pl.y = resolve(self.level, host.x + 0.6, host.y + 0.6, pl.R)
        pl.max_hp = int(round(pl.max_hp * host.max_hp / (100 * CH.CHARS[host.char]["hp"])))   # match grafts so far
        pl.hp = pl.max_hp
        self.players.append(pl)
        self.players.sort(key=lambda p_: p_.idx)
        self.message("%s JOINED" % (name or "PLAYER %d" % (idx + 1)), (90, 230, 230))
        sfx.play("weapon_pickup")
        return pl

    def remove_player(self, idx):
        """Net play: a guest left. Their body goes, with whatever they carried."""
        gone = [p for p in self.players if p.idx == idx]
        if not gone or len(self.players) <= 1:
            return
        self.players = [p for p in self.players if p.idx != idx]
        for t in self.turrets:
            if getattr(t, "owner", None) is gone[0]:
                t.owner = self.player
        if self._shooter is gone[0]:
            self._shooter = self.player
        self.message("%s LEFT" % (getattr(gone[0], "name", "") or "PLAYER %d" % (idx + 1)), (150, 160, 180))

    def listeners(self):
        """Players whose ears are at this machine."""
        if self.local_idx is None:
            return self.players
        return [p for p in self.players if p.idx in self.local_idx] or self.players[:1]

    def sound_loops(self):
        """Continuous sounds that follow the players' state (also run by net guests from the replicated players)."""
        sfx.loop("tread_loop", any(pl.alive and pl.moving and pl.char == "canbot" for pl in self.players))
        for arch_, loop_ in (("flamer", "flame_loop"), ("chem", "chem_loop"), ("cryo", "cryo_loop")):
            sfx.loop(loop_, any(pl.alive and pl.spraying == arch_ for pl in self.players))
        sfx.loop("static_loop", self.static > 0.02, self.static)

    # ---- fx helpers
    def snd(self, name, x, y, vol=1.0):
        """Positional-ish sound: fades with distance from the nearest player (at this machine)."""
        if self.net_events is not None:
            self.net_events.append(("s", name, round(x, 2), round(y, 2), vol))
        ears = self.listeners()
        d = min(math.hypot(x - p_.x, y - p_.y) for p_ in ears)
        r, sfx.router = sfx.router, None          # already recorded for the guests above
        try:
            sfx.play(name, vol * max(0.15, min(1.0, 1.25 - d / 12)))
        finally:
            sfx.router = r

    def message(self, text, color=(230, 230, 230)):
        self.messages.append([text, color, 3.0])
        if len(self.messages) > 5:
            self.messages.pop(0)

    def add(self, p):
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(p)

    def enemy_shoot(self, e, sh, a):
        k = sh["kind"]
        c, s_ = math.cos(a), math.sin(a)
        if k in ("acid", "bile") and sh.get("hazard"):
            tg = getattr(e, "target", None) or self.player
            d = min(sh["rng"], max(1.0, math.hypot(tg.x - e.x, tg.y - e.y))) * rnd.uniform(0.8, 1.1)
            T = max(0.4, min(1.2, d / 7))
            g = 14.0
            self.projs.append(Proj("acid", e.x, e.y, 1.0, c * d / T, s_ * d / T, sh["dmg"], hostile=True, life=3, color=sh["color"],
                                   r=sh["r"], vz=(0.5 * g * T * T - 1.0) / T, grav=g))
            self.snd("acid_spit", e.x, e.y, 0.7)
            return
        pk = {"coin": "orb", "spore": "orb", "bile": "orb", "orb": "orb"}.get(k, k)
        pr = Proj(pk, e.x + c * 0.4, e.y + s_ * 0.4, e.hz, c * sh["speed"], s_ * sh["speed"], sh["dmg"], hostile=True,
                  life=3.0 if pk not in ("chem",) else 0.6, color=sh["color"], r=sh["r"], blast=sh["blast"], homing=sh["homing"],
                  maxspeed=sh["speed"], gas=sh.get("gas", 0.0))
        pr.effect = sh.get("effect")
        pr.owner = e
        pr.dtype = sh.get("dtype") or "kinetic"
        if sh.get("rad"):
            pr.rad = sh["rad"]
        self.projs.append(pr)
        snd = {"bolt": "turret_shot", "fireball": "fireball", "coin": "clatter"}.get(k, "enemy_shot")
        if getattr(e, "weapon", None) is not None and e.weapon.st.get("sound"):
            snd = e.weapon.st["sound"]          # a real gun sounds like itself
        self.snd(snd, e.x, e.y, 0.7)

    def fire_puff(self, x, y, n=10):
        for _ in range(n):
            a = rnd.random() * math.tau
            s_ = rnd.uniform(0.8, 2.5)
            self.add(Particle("fire", x, y, rnd.uniform(0.2, 1.0), math.cos(a) * s_, math.sin(a) * s_, rnd.uniform(0.5, 2), 0.5,
                              rnd.choice(((255, 200, 90), (255, 120, 30), (220, 60, 20))), rnd.uniform(8, 14)))
        for _ in range(n // 2):
            self.add(Particle("smoke", x + rnd.uniform(-0.2, 0.2), y + rnd.uniform(-0.2, 0.2), 0.6, rnd.uniform(-0.3, 0.3),
                              rnd.uniform(-0.3, 0.3), rnd.uniform(0.6, 1.4), 1.2, (60, 50, 45), 0.35))

    def player_effect(self, kind, src=None, who=None):
        p = who or (self.nearest_player(src.x, src.y) if src is not None else self.player)
        if not p.alive:
            return
        if kind == "pull" and src is not None:
            dx, dy = src.x - p.x, src.y - p.y
            d = math.hypot(dx, dy) or 1
            p.kbx, p.kby = dx / d * 15, dy / d * 15
            self.message("HOOKED!", (200, 190, 170))
        elif kind in ("chill", "confuse"):
            if kind not in p.status:
                self.message("CHILLED - slowed" if kind == "chill" else "ENTHRALLED - controls reversed",
                             (150, 210, 255) if kind == "chill" else (255, 120, 200))
            p.status[kind] = 2.6
        elif kind in ("poison", "venom"):       # snake bites and cobra spit: 4 s; a scorpion sting: 7 s and stronger
            if "poison" not in p.status:
                self.message("POISONED", (150, 230, 60))
            p.status["poison"] = max(p.status.get("poison", 0), 7.0 if kind == "venom" else 4.0)
            if kind == "venom":
                p.status["venom"] = 7.0
        elif kind == "burn":
            if "burn" not in p.status:
                self.message("ON FIRE", (255, 140, 40))
            p.status["burn"] = max(p.status.get("burn", 0), 2.5)

    def boss_awake(self, b):
        self.message("%s AWAKENS" % b.title, b.color)
        self.boss_music = True
        self.shake = max(self.shake, 8)
        sfx.music("hunter", 800)

    def kill_boss(self, b):
        from bosses import drop_boss_loot
        self.score += 5000
        self.kills += 1
        for k in range(4):
            a = k * math.pi / 2
            self.explode(b.x + math.cos(a) * 0.6, b.y + math.sin(a) * 0.6, 1.6, 0, b.color, hurt_player=False, quiet=k > 0)
        for name in ("brute", "mimic", "zombie"):
            self.gibs_from(name, b.x, b.y, 1.2, force=1.6)
        self.spray(b.x, b.y, 1.2, b.blood, 60, 6)
        self.splat(b.x, b.y, b.blood, 1.2)
        self.hitstop = 0.3
        self.shake = 18
        self.message("%s DEFEATED  -  the portal is open" % b.title, (255, 230, 120))
        sfx.play("death_brute")
        sfx.music(self.biome_music, 2500)
        drop_boss_loot(self, b)
        for pr in self.projs:
            if pr.hostile:
                pr.life = min(pr.life, 0.05)

    def typed(self, e, dmg, dtype, ammo=None, tick=False):
        """Scale damage by the target's category vs the damage type (and kinetic ammo mods); weak / resisted hits get
        a little feedback, and with the option on, a damage number in the type's colour."""
        m = DM.mult(e, dtype, ammo)
        if self.show_numbers and dmg * m > 0:
            self.damage_number(e, dmg * m, dtype or "kinetic", tick)
        if (m >= 1.25 or m <= 0.7) and self.time - getattr(e, "_pop_t", -9) > 0.7:
            e._pop_t = self.time
            weak = m > 1
            hz = (getattr(e, "st", None) or {}).get("hz", 0.8)
            col = DM.COLOR.get(dtype, (255, 255, 255)) if weak else (140, 140, 150)
            self.popups.append([e.x, e.y, hz + 0.5, "WEAK" if weak else "RESIST", col, 0.8])
            for _ in range(10 if weak else 5):
                a = rnd.random() * math.tau
                s_ = rnd.uniform(2, 6) if weak else rnd.uniform(1, 2.5)
                self.add(Particle("spark", e.x, e.y, hz * 0.7, math.cos(a) * s_, math.sin(a) * s_, rnd.uniform(1, 3), 0.35,
                                  col, 3 if weak else 2))
        return dmg * m

    def damage_number(self, e, amount, dtype, tick):
        """Direct hits of 1+ pop their own number at once. Spray puffs and damage over time (burning, gas, auras,
        puddles) pool per target and type; World.update shows each pool every 0.4s and flushes what's left."""
        if not tick and amount >= 1.0:
            self.number_popup(e, amount, dtype)
            return
        acc = getattr(e, "_dot_acc", None)
        if acc is None:
            acc = e._dot_acc = {}
            self.dot_targets.append(e)
        a = acc.get(dtype)
        if a is None:
            a = acc[dtype] = [0.0, self.time]
        a[0] += amount

    def number_popup(self, e, amount, dtype):
        hz = (getattr(e, "st", None) or {}).get("hz", 0.8)
        k = getattr(e, "_num_k", 0)
        e._num_k = k + 1
        side = ((k % 5) - 2) * 0.22                  # fan consecutive numbers out so they don't stack
        txt = "%d" % round(amount) if amount >= 1 else "%.1f" % amount
        self.popups.append([e.x + side, e.y - side, hz + 0.25 + (k % 2) * 0.15, txt, DM.COLOR[dtype], 1.0])

    def flush_numbers(self):
        keep = []
        for e in self.dot_targets:
            acc = e._dot_acc
            for dtype, a in acc.items():
                due = self.time - a[1] >= 0.4 or not e.alive
                if due and a[0] >= 0.5:
                    self.number_popup(e, a[0], dtype)
                    a[0], a[1] = 0.0, self.time
                elif due:
                    a[1] = self.time
            if e.alive:
                keep.append(e)
            else:
                e._dot_acc = None
        self.dot_targets = keep

    def acid_puddle(self, x, y, dps):
        L = self.level
        if L.is_solid(int(x), int(y)):
            return
        self.hazards.append([x, y, 0.55, 3.5, "acidp", dps, 3.5])
        self.snd("sizzle", x, y, 0.35)

    def dot(self, e, amount, dtype=None):
        """Damage over time (radiation, gas, acid, auras) without per-tick blood sprays."""
        if dtype:
            amount = self.typed(e, amount, dtype, tick=True)
        e.hp -= amount
        e.awake = True
        if e.hp <= 0 and e.alive:
            e.alive = False
            if hasattr(e, "title"):
                self.kill_boss(e)
            else:
                self.kill_enemy(e)

    def add_gas(self, x, y, dps, vx=0.0, vy=0.0):
        for hz in self.hazards:
            if hz[4] == "gas" and abs(hz[0] - x) < 0.5 and abs(hz[1] - y) < 0.5:
                hz[3] = hz[6] = max(hz[3], 5.0)
                hz[2] = min(1.15, hz[2] + 0.06)
                hz[5] = max(hz[5], dps)
                return
        if sum(1 for hz in self.hazards if hz[4] == "gas") < 90:
            self.hazards.append([x, y, 0.55, 5.0, "gas", dps, 5.0, vx * 0.15, vy * 0.15])

    def splat(self, x, y, color, r):
        if color:
            self.decals.append((x, y, color, r, rnd.randrange(12)))   # baked & cleared by the renderer

    def spray(self, x, y, z, color, n, speed=3.0, size=(2.5, 5.5)):
        if not color:
            return
        for _ in range(n):
            a = rnd.random() * math.tau
            s = rnd.uniform(0.3, 1.0) * speed
            self.add(Particle("blood", x, y, z, math.cos(a) * s, math.sin(a) * s, rnd.uniform(1.5, 5), 2.0, color,
                              rnd.uniform(*size)))

    def gibs_from(self, what, x, y, z, ivx=0.0, ivy=0.0, count=None, force=1.0):
        names, blood = GIB_SETS[what]
        sp = math.hypot(ivx, ivy)
        ux, uy = (ivx / sp, ivy / sp) if sp > 0 else (0.0, 0.0)
        picks = names if count is None else [rnd.choice(names) for _ in range(count)]
        for name in picks:
            a = rnd.random() * math.tau
            s = rnd.uniform(1.2, 4.0) * force
            self.gibs.append(Gib(name, x + rnd.uniform(-0.15, 0.15), y + rnd.uniform(-0.15, 0.15), z * rnd.uniform(0.6, 1.1),
                                 math.cos(a) * s + ux * 2.5 * force, math.sin(a) * s + uy * 2.5 * force,
                                 rnd.uniform(3.5, 7.5) * (0.7 + 0.3 * force), blood, rnd.uniform(0.3, 0.9)))
        if len(self.gibs) > MAX_GIBS:
            extra = len(self.gibs) - MAX_GIBS
            keep = []
            for g in self.gibs:
                if extra > 0 and g.rest:
                    extra -= 1
                    continue
                keep.append(g)
            self.gibs = keep

    def blast_kick(self, x, y, radius, power):
        for g in self.gibs:
            dx, dy = g.x - x, g.y - y
            d = math.hypot(dx, dy)
            if d < radius:
                f = (1 - d / radius) * power
                g.rest = False
                g.bounces = 0
                g.vx += dx / (d or 1) * f * 2
                g.vy += dy / (d or 1) * f * 2
                g.vz = max(g.vz, f * rnd.uniform(0.8, 1.3))
                g.spin = rnd.uniform(10, 24) * rnd.choice((1, -1))

    # ---- loot
    def drop_weapon(self, x, y, bonus=0.0):
        self.loot.append(Loot("weapon", x, y, WP.generate(self.depth, bonus=bonus), pop=True))

    def drop_support(self, x, y, bonus=0.0):
        self.loot.append(Loot("support", x, y, SU.generate(self.depth, bonus=bonus), pop=True))

    def take_support(self, lt, p=None):
        """Pick up an accessory: free gear slot, else backpack; with both full it swaps with gear slot 1."""
        p = p or self.player
        new = lt.item
        where = p.give(new)
        if where is None:
            old = p.gear[0]
            p.gear[0] = new
            new.attach(p, 0)
            lt.item = old
            lt.vz, lt.z = 3.0, 0.0
            where = "slot 1 (swapped out %s)" % old.name
        elif lt in self.loot:
            self.loot.remove(lt)
        self.message("%s  ->  %s" % (new.name, where), new.color)
        sfx.play("power")

    def drop_item(self, p, item):
        self.loot.append(Loot("support", p.x, p.y, item, pop=True))

    def drop_buff(self, x, y):
        self.loot.append(Loot("buff", x, y, WP.roll_buff(level=self.depth), pop=True))

    def apply_buff(self, b, p=None):
        p = p or self.player
        if b.kind == "graft":
            p.max_hp += int(b.mag)
            p.hp = min(p.max_hp, p.hp + int(b.mag))
        elif b.kind == "calibrate":
            p.perm_dmg *= 1 + b.mag / 100
        else:
            cur = p.buffs.get(b.kind)
            if not cur or b.mag >= cur[0] or b.dur > cur[1]:
                p.buffs[b.kind] = [max(b.mag, cur[0]) if cur else b.mag, max(b.dur, cur[1] if cur else 0)]
        dur = "" if b.permanent else "  (%.0fs)" % b.dur
        self.message("%s  -  %s%s" % (b.title, b.desc, dur), b.color)
        sfx.play("power")

    def take_weapon(self, lt, p=None):
        p = p or self.player
        old = p.weapons[p.cur]
        new = lt.item
        new.reload_t, new.cd = 0.0, 0.2
        p.weapons[p.cur] = new
        p.card_t = 3.0
        old.reload_t = 0.0
        lt.item = old
        lt.vz, lt.z = 3.0, 0.0
        self.message("Took %s  [%s %s, lvl %d]" % (new.name, new.rarity_name, new.brand, new.level), new.color)
        sfx.play("weapon_pickup")

    # ---- combat
    def fire_weapon(self, p, wp):
        st = wp.st
        ax, ay = p.aim
        mf, mz = WP.MUZZLE[wp.arch]
        side = WP.SHOULDER.get(WP.sprite_arch(wp.arch), 0.0)
        mx, my = p.x + ax * mf + ay * side, p.y + ay * mf - ax * side
        lvl = 1 + 0.2 * (wp.level - 1)
        dmg = st["dmg"] * p.dmg_mult()
        burn = st["burn"] * 1.4 * lvl * p.dmg_mult()
        rad = (st["rad"][0], st["rad"][1], st["rad"][2] * lvl * p.dmg_mult(), st["rad"][3]) if st["rad"] else None
        gas = st["gas"] * lvl * p.dmg_mult()
        kind = st["proj"]
        extra = int(p.mult("multishot", 0))
        count = st["pellets"] + extra
        spread = st["spread"]
        lanes = (-0.09, 0.09) if st["twin"] else (0.0,)
        p.muzzle = 0.05
        p.muzzle_color = st["color"]
        if st["salvo"]:                   # missiles ripple out of the pod over the next few frames
            p.salvo_q += st["salvo"] + extra * 2
            p.salvo_wp, p.salvo_t, p.salvo_n = wp, 0.0, 0
            sfx.play("servo", 0.4)
            return
        nbar = max(1, st["barrels"])
        for i in range(count):
            bar_off = 0.0
            if st["shell"]:                   # slugs: one per barrel, side by side; multishot extras fan out
                a = rnd.uniform(-spread, spread)
                if nbar > 1:
                    bar_off = ((i % nbar) - (nbar - 1) / 2) * 0.055
                if i >= st["pellets"]:
                    j = i - st["pellets"] + 1
                    a += ((j + 1) // 2) * 0.11 * (1 if j % 2 else -1)
            elif st["pellets"] > 1 or kind in WP.SPRAYS:
                a = rnd.uniform(-spread, spread)
            elif i == 0:
                a = rnd.uniform(-spread, spread)
            else:
                a = ((i + 1) // 2) * 0.13 * (1 if i % 2 else -1)
            dx, dy = rot(ax, ay, a)
            for lane in lanes:
                ox, oy = mx + dy * (lane + bar_off), my - dx * (lane + bar_off)
                if kind == "beam":
                    self.fire_beam(ox, oy, mz, dx, dy, dmg, st, wp)
                    continue
                if kind == "arc":
                    self.fire_arc(ox, oy, mz, dx, dy, dmg, st, p)
                    continue
                spray = kind in WP.SPRAYS
                spd = st["speed"] * (rnd.uniform(0.85, 1.15) if (kind == "pellet" or spray) else 1.0)
                bounce = st["bounce"] + (rnd.randint(*st["saw_bounces"]) if st["saw_bounces"] else 0)
                pr = Proj(kind, ox, oy, mz, dx * spd, dy * spd, dmg, life=st["life"] * (rnd.uniform(0.8, 1.1) if spray else 1),
                          color=st["color"], r={"plasma": 0.22, "flame": 0.22, "chem": 0.22, "cryo": 0.22, "grenade": 0.15, "rocket": 0.16,
                                                "slug": 0.12, "nuke": 0.2, "saw": 0.24}.get(kind, 0.1),
                          pierce=st["pierce"], bounce=bounce, blast=st["blast"], burn=burn, shock=st["shock"],
                          homing=st["homing"], slow=st["slow"], rad=rad, gas=gas, chill=st["chill"])
                pr.dtype = st["dtype"]
                pr.ammo = st["ammo"]
                if kind == "jet":
                    pr.effect = "jet:" + st["jet"]
                    pr.r = 0.11
                if st["shell"]:
                    pr.effect = st["shell"]
                    pr.r = 0.17 if st["shell"] == "dumdum" else 0.08
                pr.tier_leech = st["tier_leech"]
                if st["acid"]:
                    pr.acid = min(1.0, 1.6 / max(0.1, st["rate"] * st["pellets"]))
                if kind == "grenade":
                    pr.vz, pr.grav = 3.0, 14.0
                if st["cluster"]:               # the mother shell: bigger, carries its bomblet count
                    pr.effect = "cluster"
                    pr.cone = st["cluster"]
                    pr.r = 0.2
                    pr.vz = 3.6
                if kind == "rail":
                    pr.bounce = st["wallpierce"]
                    pr.r = 0.16
                    pr.owner = p
                if kind == "wave":
                    self.setup_wave(pr, ox, oy, dx, dy, st)
                    pr.owner = p
                self.projs.append(pr)
        if kind == "rail":
            for _ in range(10):
                a = rnd.uniform(-0.4, 0.4)
                ex, ey = rot(ax, ay, a)
                v = rnd.uniform(3, 9)
                self.add(Particle("glow", mx, my, mz, ex * v, ey * v, rnd.uniform(-0.5, 1.5), 0.3, st["color"], 2))
        if WP.is_shotgun(wp.arch):
            if st["barrels"]:                 # break-action: every spent hull pops out as it cracks open
                for i in range(nbar):
                    self.eject(p, "hull_drop", 0.28 + i * 0.03)
            elif wp.arch == "auto_shotgun":
                self.eject(p, "hull")
            else:                             # pump: the hull flies out on the pump stroke
                self.eject(p, "hull", 0.34)
        elif kind in ("bullet", "slug") and wp.arch != "revolver":     # revolvers keep their brass until reload
            self.eject(p, "brass")
        if st["shell"] == "sabot":            # the plastic petals peel off the steel core just past the muzzle
            for i in range(min(8, count * 2)):
                side = 1 if i % 2 else -1
                v = rnd.uniform(2.5, 4.5)
                self.add(Particle("shell", mx + ax * 0.15, my + ay * 0.15, mz, ax * v * 0.8 - ay * side * v * 0.6,
                                  ay * v * 0.8 + ax * side * v * 0.6, rnd.uniform(1.0, 2.5), 0.8, (225, 225, 215), 2))
        elif st["shell"] == "dumdum":
            for _ in range(5 * nbar):
                a = rnd.uniform(-0.25, 0.25)
                ex, ey = rot(ax, ay, a)
                v = rnd.uniform(1.5, 4)
                self.add(Particle("smoke", mx, my, mz, ex * v, ey * v, 0.6, 0.7, (70, 64, 58), 0.3))
        for _ in range(3 if kind not in WP.SPRAYS else 1):
            a = rnd.uniform(-0.5, 0.5)
            ex, ey = rot(ax, ay, a)
            v = rnd.uniform(4, 8)
            self.add(Particle("spark", mx, my, mz, ex * v, ey * v, rnd.uniform(0, 1.5), 0.12, st["color"], 2))
        kick = st["kick"]
        self.shake = max(self.shake, kick)
        if kick >= 4:
            p.kbx -= ax * kick * 0.6
            p.kby -= ay * kick * 0.6
        if st["sound"]:
            sfx.play(st["sound"])

    # ---- spent casings
    def eject(self, who, kind, delay=0.0):
        if delay <= 0:
            self.spawn_casing(who, kind)
        else:
            self.ejects.append([delay, who, kind])

    def spawn_casing(self, who, kind):
        """brass (rifle / pistol case), hull (shotgun shell), hull_drop (falls out of a broken-open action), battery (laser cell)."""
        ax, ay = who.aim
        x, y = who.x + ax * 0.3, who.y + ay * 0.3
        if kind == "battery":            # the spent cell drops out of the grip
            self.add(Particle("shell", x, y, 1.0, -ay * 0.8 + rnd.uniform(-0.3, 0.3), ax * 0.8 + rnd.uniform(-0.3, 0.3),
                              rnd.uniform(0.5, 1.5), 4.0, (70, 78, 92), 4.2))
            for _ in range(4):
                self.add(Particle("spark", x, y, 1.0, rnd.uniform(-2, 2), rnd.uniform(-2, 2), rnd.uniform(0.5, 2), 0.25, (255, 90, 90), 2))
            return
        if kind == "hull_drop":
            s = rnd.uniform(0.6, 1.6)
            self.add(Particle("shell", x, y, 1.15, -ay * s - ax * 1.0 + rnd.uniform(-0.4, 0.4), ax * s - ay * 1.0 + rnd.uniform(-0.4, 0.4),
                              rnd.uniform(2.0, 3.2), 3.0, (200, 50, 40), 2.7))
            return
        s = rnd.uniform(2.0, 3.0)
        hull = kind == "hull"
        self.add(Particle("shell", x, y, 1.1, -ay * s + rnd.uniform(-0.4, 0.4), ax * s + rnd.uniform(-0.4, 0.4), rnd.uniform(2.5, 4),
                          3.0 if hull else 2.5, (200, 50, 40) if hull else (230, 180, 60), 2.7 if hull else 2.0))

    def on_reload(self, who, wp):
        """A reload just started: revolvers dump their brass, laser guns drop their spent battery."""
        if wp.arch == "revolver":
            for i in range(max(1, wp.st["mag"] - wp.ammo)):
                self.eject(who, "brass", 0.05 + i * 0.02)
        elif wp.arch in ("laser_pistol", "laser_rifle"):
            self.eject(who, "battery", 0.05)

    def dumdum_hit(self, e, b):
        """An expanding slug mushrooms inside its target: a big shove and a spray out the back."""
        sp = math.hypot(b.vx, b.vy) or 1
        ux, uy = b.vx / sp, b.vy / sp
        if isinstance(e, Enemy) and e.kind not in ("spider", "brute", "turret", "walker"):
            e.vx += ux * 5.0
            e.vy += uy * 5.0
        col = getattr(e, "blood", None)
        if not (isinstance(col, tuple) and len(col) == 3):
            col = RED
        hz = e.st["hz"] if isinstance(e, Enemy) else 0.9
        for _ in range(10):
            a = rnd.uniform(-0.45, 0.45)
            v = rnd.uniform(3, 7)
            ex, ey = rot(ux, uy, a)
            self.add(Particle("blood", e.x + ux * 0.3, e.y + uy * 0.3, hz, ex * v, ey * v, rnd.uniform(0.5, 3), 1.5, col, rnd.uniform(3, 6)))

    def fire_missile(self, p, wp, i):
        """One missile of a barrage salvo, from barrel i of the 4x2 pod; fans out, then homes in."""
        st = wp.st
        ax, ay = p.aim
        mf, mz = WP.MUZZLE[wp.arch]
        lat = ((i % 4) - 1.5) * 0.055
        z = mz + (((i // 4) % 2) - 0.5) * 0.07
        mx, my = p.x + ax * mf + ay * lat, p.y + ay * mf - ax * lat
        lvl = 1 + 0.2 * (wp.level - 1)
        a = rnd.uniform(-1, 1) * (0.3 + st["spread"])
        dx, dy = rot(ax, ay, a)
        spd = st["speed"] * rnd.uniform(0.85, 1.1)
        pr = Proj("missile", mx, my, z, dx * spd, dy * spd, st["dmg"] * p.dmg_mult(), life=st["life"] * rnd.uniform(0.9, 1.1),
                  color=st["color"], r=0.12, blast=st["blast"], burn=st["burn"] * 1.4 * lvl * p.dmg_mult(), shock=st["shock"],
                  homing=st["homing"], slow=st["slow"], chill=st["chill"], maxspeed=st["speed"] * 2.4)
        pr.cone = math.atan2(ay, ax)      # where the salvo was aimed: missiles with nothing to chase drift back to it
        pr.dtype = st["dtype"]
        pr.tier_leech = st["tier_leech"]
        if st["acid"]:
            pr.acid = min(1.0, 1.6 / max(0.1, st["rate"] * (st["salvo"] or 1)))
        pr.owner = p
        self.projs.append(pr)
        for _ in range(2):
            self.add(Particle("smoke", mx, my, z, -dx * rnd.uniform(1, 2.5), -dy * rnd.uniform(1, 2.5), 0.4, 0.6, (110, 104, 96), 0.15))
        p.muzzle = 0.04
        p.muzzle_color = st["color"]
        self.shake = max(self.shake, st["kick"])
        sfx.play(st["sound"], 0.55)

    def setup_wave(self, pr, x, y, dx, dy, st):
        """Microwave ring: an arc of a circle centred on the muzzle that grows as it flies. Walls cast shadows in it."""
        pr.ox, pr.oy = x, y
        pr.cone = st["cone"]
        pr.r = 0.3
        base = math.atan2(dy, dx)
        far = st["speed"] * st["life"] + 0.5
        L = self.level
        reach = []
        for k in range(11):
            a = base - pr.cone + 2 * pr.cone * k / 10
            c, s = math.cos(a), math.sin(a)
            d = 0.0
            while d < far and not L.is_solid(int(x + c * d), int(y + s * d)):
                d += 0.2
            reach.append(d)
        pr.reach = reach

    def fire_arc(self, x, y, z, dx, dy, dmg, st, p):
        """Coil lightning: instant bolt that ricochets off walls until it finds a monster, then chains through the pack."""
        from traps import los
        L = self.level
        pts = [(x, y, z)]
        bounces, left = st["bounce"], st["arc_range"]
        cx, cy = x, y
        step = 0.15
        first = None
        while left > 0 and first is None:
            nx, ny = cx + dx * step, cy + dy * step
            left -= step
            tx, ty = int(nx), int(ny)
            if L.is_solid(tx, ty):
                self.hit_solid((tx, ty), dmg, nx, ny, z, None)
                pts.append((cx, cy, z))
                for _ in range(5):
                    a = rnd.random() * math.tau
                    self.add(Particle("spark", cx, cy, z, math.cos(a) * 4, math.sin(a) * 4, rnd.uniform(0, 2), 0.2, st["color"], 2))
                if bounces <= 0:
                    break
                bounces -= 1
                sx_, sy_ = L.is_solid(tx, int(cy)), L.is_solid(int(cx), ty)
                if sx_:
                    dx = -dx
                if sy_:
                    dy = -dy
                if not sx_ and not sy_:
                    dx, dy = -dx, -dy
                continue
            cx, cy = nx, ny
            for e in list(self.nearby(cx, cy)) + self.bosses + self.shootables:
                if e.alive and getattr(e, "state", "") != "dormant" and not getattr(e, "submerged", False) \
                        and math.hypot(e.x - cx, e.y - cy) < e.r + 0.18:
                    first = e
                    break
        if first is None:
            pts.append((cx, cy, z))
        else:
            def hz(e):
                return (getattr(e, "st", None) or {}).get("hz", 0.8) * 0.6
            pts.append((first.x, first.y, hz(first)))
            self.hit_enemy(first, dmg, dx * 10, dy * 10, st)
            hit = {id(first)}
            cur, k = first, dmg
            for _ in range(st["chain"]):
                nxt = next((o for o in SU.targets(self, cur.x, cur.y, 3.6) if id(o) not in hit and los(L, cur.x, cur.y, o.x, o.y)), None)
                if nxt is None:
                    break
                k *= 0.85
                hit.add(id(nxt))
                pts.append((nxt.x, nxt.y, hz(nxt)))
                self.hit_enemy(nxt, k, (nxt.x - cur.x) * 8, (nxt.y - cur.y) * 8, st)
                cur = nxt
            if len(hit) > 1:
                self.snd("shock", cur.x, cur.y, 0.5)
        self.arcs.append([pts, 0.13, 0.13, st["color"], 0.8 + st["chain"] * 0.12])
        ex, ey, ez = pts[-1]
        for _ in range(4):
            a = rnd.random() * math.tau
            self.add(Particle("glow", ex, ey, ez, math.cos(a) * 2, math.sin(a) * 2, rnd.uniform(0, 1.5), 0.25, st["color"], 2))

    def step_wave(self, b, dt):
        b.age += dt
        b.x += b.vx * dt
        b.y += b.vy * dt
        b.life -= dt
        if b.life <= 0:
            return False
        rad = math.hypot(b.x - b.ox, b.y - b.oy)
        base = math.atan2(b.vy, b.vx)
        n = len(b.reach)
        for e in SU.targets(self, b.ox, b.oy, rad + 1.5) + [t for t in self.shootables if t.alive]:
            if id(e) in b.hit:
                continue
            ex, ey = e.x - b.ox, e.y - b.oy
            d = math.hypot(ex, ey) or 1e-6
            if abs(d - rad) > 0.3 + e.r:
                continue
            da = (math.atan2(ey, ex) - base + math.pi) % math.tau - math.pi
            if abs(da) > b.cone + e.r / max(d, 0.3):
                continue
            i = min(n - 1, max(0, int((da + b.cone) / (2 * b.cone) * (n - 1) + 0.5)))
            if d > b.reach[i] + e.r:
                continue                  # behind a wall
            b.hit.add(id(e))
            self.hit_enemy(e, b.dmg, ex / d * 4, ey / d * 4, b)
            for _ in range(3):
                self.add(Particle("glow", e.x, e.y, 0.6, rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(1, 2), 0.4, b.color, 2))
        return True

    def fire_beam(self, x, y, z, dx, dy, dmg, st, wp):
        L = self.level
        hit = set()
        step = 0.12
        cx, cy = x, y
        for _ in range(int(15 / step)):
            nx, ny = cx + dx * step, cy + dy * step
            tx, ty = int(nx), int(ny)
            if L.is_solid(tx, ty):
                self.hit_solid((tx, ty), dmg, nx, ny, 1.0, None)
                break
            cx, cy = nx, ny
            for e in list(self.nearby(cx, cy)) + self.bosses + self.shootables:
                if e.alive and id(e) not in hit and not getattr(e, "submerged", False) and math.hypot(e.x - cx, e.y - cy) < e.r + 0.1:
                    hit.add(id(e))
                    self.hit_enemy(e, dmg, dx * 20, dy * 20, st)
        self.beams.append([x, y, cx, cy, z, 0.08, 0.08, st["color"], 1.0])
        for _ in range(4):
            a = rnd.random() * math.tau
            self.add(Particle("spark", cx, cy, z, math.cos(a) * 3, math.sin(a) * 3, rnd.uniform(0, 2), 0.2, st["color"], 2))

    def hit_enemy(self, e, dmg, vx, vy, fx):
        """Apply damage plus weapon side-effects (fx: Proj or stats dict)."""
        get = (lambda k: fx.get(k, 0)) if isinstance(fx, dict) else (lambda k: getattr(fx, k, 0))
        burn, slow, shock, blast = get("burn"), get("slow"), get("shock"), get("blast")
        chill = get("chill")
        dtype = get("dtype") or "kinetic"
        ammo = get("ammo") or None
        raw = dmg
        if isinstance(fx, dict):   # beam stats come unscaled
            burn = burn * 1.4 * self._shooter.dmg_mult()
        e.last_hit_by = getattr(fx, "owner", None) if not isinstance(fx, dict) else self._shooter
        armor = (getattr(e, "bdef", None) or {}).get("armor")
        if armor and getattr(fx, "kind", None) != "rail" and ammo != "pen" and getattr(fx, "effect", None) != "sabot":
            tg = getattr(e, "target", None) or self.player
            fx_, fy_ = tg.x - e.x, tg.y - e.y
            vl = math.hypot(vx, vy) or 1
            if (vx * fx_ + vy * fy_) / ((math.hypot(fx_, fy_) or 1) * vl) < -0.35:     # hit from the front: the pincers take it
                dmg *= armor
                if rnd.random() < 0.5:
                    self.add(Particle("spark", e.x, e.y, 0.5, -vx * 0.1, -vy * 0.1, rnd.uniform(1, 3), 0.25, (255, 230, 160), 2))
                    self.snd("tink", e.x, e.y, 0.4)
        dealt = self.typed(e, dmg, dtype, ammo)
        e.hit(self, dealt, vx, vy)
        tl = get("tier_leech")
        if tl:                              # eldritch weapons feed their wielder
            who = getattr(fx, "owner", None) if not isinstance(fx, dict) else self._shooter
            who = getattr(who, "owner_player", who)
            if isinstance(who, Player) and who.alive:
                who.hp = min(who.max_hp, who.hp + dealt * tl)
        acid = get("acid")
        if acid:
            p_ = acid if not isinstance(fx, dict) else min(1.0, 1.6 / max(0.1, fx.get("rate", 1.0)))
            if rnd.random() < p_:
                self.acid_puddle(e.x, e.y, raw * 0.9)
        if burn and hasattr(e, "burn_dps"):
            e.burn = max(e.burn, 2.5)
            e.burn_dps = max(e.burn_dps, burn * DM.mult(e, "fire"))
        if slow:
            e.slow = 2.2
        if chill and e.alive and hasattr(e, "frozen"):
            e.chill += chill * DM.mult(e, "cryo")
            if e.chill >= 1.0 and e.frozen <= 0:
                e.frozen = 3.5
                e.chill = 0.0
                e.vx = e.vy = 0.0
                e.lunge = 0.0
                e.burn = 0.0
                for _ in range(14):
                    a = rnd.random() * math.tau
                    self.add(Particle("glow", e.x, e.y, e.st["hz"] * rnd.random(), math.cos(a) * 1.5, math.sin(a) * 1.5, 1, 0.6, (210, 240, 255), 2))
                self.snd("freeze", e.x, e.y)
        if shock:
            others = sorted((o for o in self.enemies if o.alive and o is not e and math.hypot(o.x - e.x, o.y - e.y) < 3.2),
                            key=lambda o: math.hypot(o.x - e.x, o.y - e.y))[:2]
            for o in others:
                self.beams.append([e.x, e.y, o.x, o.y, e.st["hz"] if hasattr(e, "st") else 0.6, 0.12, 0.12, (140, 200, 255), 0.6])
                o.hit(self, self.typed(o, raw * 0.5, "electrical"), o.x - e.x, o.y - e.y)
            if others:
                self.snd("shock", e.x, e.y, 0.6)
        if blast and (isinstance(fx, dict) or fx.kind not in ("grenade", "rocket", "plasma")):
            self.explode(e.x, e.y, blast, raw * 0.6, (255, 170, 60), hurt_player=False, quiet=True, small=True)

    def hit_solid(self, cell, dmg, x, y, z, b):
        """Something hit a solid cell: barrels / crates / hives take damage. Returns True if it was destructible."""
        hostile = b is not None and b.hostile
        if not hostile:
            for t in self.traps:
                if t.solid and t.shootable and t.alive and (int(t.x), int(t.y)) == cell:
                    t.hit(self, dmg, 0, 0)
                    return True
            if cell in self.barrels:
                self.damage_barrel(cell, dmg)
                self.spray(x, y, z * 0.5, ICHOR, 4, 2)
                return True
            if cell in self.crates:
                self.damage_crate(cell, dmg)
                return True
            for s in self.spawners:
                if int(s.x) == cell[0] and int(s.y) == cell[1]:
                    s.hit(self, dmg)
                    return True
        return False

    def hurt_player(self, dmg, sx, sy, knock=7.0, who=None, dtype="kinetic"):
        if getattr(who, "decoy", False):
            who.flash = 0.15
            return
        if getattr(who, "is_turret", False):
            who.hit(self, dmg)
            return
        if who is None and self.turrets:          # a monster swinging at a turret hits the turret
            t = min(self.turrets, key=lambda q: (q.x - sx) ** 2 + (q.y - sy) ** 2)
            p0 = self.nearest_player(sx, sy)
            if math.hypot(t.x - sx, t.y - sy) < min(1.3, math.hypot(p0.x - sx, p0.y - sy)):
                t.hit(self, dmg)
                return
        if who is None and self.decoys:          # a monster swinging at a hologram hits nothing
            d = min(self.decoys, key=lambda q: (q.x - sx) ** 2 + (q.y - sy) ** 2)
            if math.hypot(d.x - sx, d.y - sy) < 1.4:
                d.flash = 0.15
                return
        p = who or self.nearest_player(sx, sy)
        if p.invuln > 0 or not p.alive:
            return
        if dtype != "explosive" and (sx - p.x) ** 2 + (sy - p.y) ** 2 > 1e-4:
            for su in p.equipped():           # forward / rear shields catch blows from their side: claws, bites, shots
                if su.kind in SU.FIXED_SHIELDS and su.covers(p, sx, sy):
                    su.absorb(self, p, p.x + (sx - p.x) * 0.5, p.y + (sy - p.y) * 0.5, cost=max(1, int(round(dmg / 12))))
                    p.invuln = 0.25
                    d = math.hypot(p.x - sx, p.y - sy) or 1
                    p.kbx, p.kby = (p.x - sx) / d * knock * 0.4, (p.y - sy) / d * knock * 0.4
                    return
        p.hp -= dmg * p.mult("aegis") * CH.player_mult(p, dtype)
        p.invuln = 0.6
        p.flash = 0.15
        d = math.hypot(p.x - sx, p.y - sy) or 1
        p.kbx, p.kby = (p.x - sx) / d * knock, (p.y - sy) / d * knock
        self.shake = 7
        self.hurt_flash = 0.25
        C = CH.CHARS[p.char]                  # each body bleeds / sparks / sheds its own bits
        if C["sparks"]:
            for _ in range(8):
                a = rnd.random() * math.tau
                self.add(Particle("spark", p.x, p.y, 1.0, math.cos(a) * 4, math.sin(a) * 4, rnd.uniform(1, 3), 0.3, (255, 220, 120), 2))
        self.spray(p.x, p.y, 1.0, C["fluid"], 6 if C["sparks"] else 14, 2.5 if C["sparks"] else 3.5)
        if rnd.random() < 0.6:
            g_ = Gib(rnd.choice(C["chips"]), p.x, p.y, 1.0, rnd.uniform(-2, 2) + (p.x - sx) * 2, rnd.uniform(-2, 2) + (p.y - sy) * 2,
                     rnd.uniform(2, 4), C["fluid"], not C["sparks"])
            self.gibs.append(g_)
        sfx.play(C["hurt"])
        self.check_player_death(sx, sy, p)

    def check_player_death(self, sx, sy, p=None):
        p = p or self.player
        if p.hp <= 0 and p.alive:
            for g in p.equipped():
                if g.kind == "battery" and g.elem == "revive" and g.charge >= g.p["capacity"]:
                    g.charge = 0
                    p.hp = p.max_hp * g.p["heal"]
                    p.invuln = 2.0
                    self.explode(p.x, p.y, 2.5, 20, (230, 220, 190), hurt_player=False)
                    self.message("BONE BATTERY DISCHARGED - REBOOTED", (230, 220, 190))
                    sfx.play("power")
                    return
            p.hp = 0
            p.alive = False
            self.gibs_from(CH.CHARS[p.char]["gibs"], p.x, p.y, 1.0, p.x - sx, p.y - sy, force=1.3)
            self.explode(p.x, p.y, 1.5, 0, (120, 230, 255), hurt_player=False, quiet=True)
            sfx.play(CH.CHARS[p.char]["death"])
            self.spray(p.x, p.y, 1.0, CH.CHARS[p.char]["fluid"], 30, 4.5)
            self.shake = 16
            self.hitstop = 0.12
            p.revive_t = 0.0
            if any(o.alive for o in self.players):
                self.message("PLAYER %d IS DOWN - stand on the bones to revive" % (p.idx + 1), (255, 120, 90))

    def kill_enemy(self, e):
        st = e.st
        k = e.kind
        if getattr(e, "frozen", 0) > 0:     # frozen solid: shatter into ice
            for _ in range(26):
                a = rnd.random() * math.tau
                s_ = rnd.uniform(2, 6)
                self.add(Particle("chunk", e.x, e.y, st["hz"] * 0.7, math.cos(a) * s_, math.sin(a) * s_, rnd.uniform(2, 6), 2.5,
                                  rnd.choice(((200, 230, 255), (150, 200, 245), (255, 255, 255))), rnd.uniform(3, 6)))
            self.splat(e.x, e.y, (150, 190, 220), 0.35)
            self.snd("shatter", e.x, e.y)
        p = getattr(e, "last_hit_by", None)
        p = getattr(p, "owner_player", p)
        if not isinstance(p, Player):
            p = self.player
        for g in p.equipped():
            g.on_kill(self) if g.kind == "battery" else None
        self.score += st["score"]
        self.kills += 1
        hz = st["hz"]
        force = 1.3 if k in ("spider", "brute", "walker") else 1.0
        self.gibs_from(k, e.x, e.y, hz, e.hitvx, e.hitvy, force=force)
        if e.blood not in (OIL, ASH):
            self.spray(e.x, e.y, hz, e.blood, 34, 4.5)
        else:
            self.spray(e.x, e.y, hz, OIL, 12, 3.5)
        if k == "drone":
            self.spray(e.x, e.y, hz, BRAIN, 12, 3.5)
        if k in ("drone", "turret", "walker"):
            self.explode(e.x, e.y, 1.2 if k != "walker" else 1.8, 3, (255, 160, 60), hurt_player=False, quiet=True)
            self.snd("death_drone", e.x, e.y)
        elif k == "skull":
            self.explode(e.x, e.y, 0.9, 2, (255, 120, 30), hurt_player=False, quiet=True, small=True)
            self.snd("death_skull", e.x, e.y)
        elif k == "bloater":
            self.explode(e.x, e.y, 1.9, 9, (140, 255, 70), hurt_player=True, quiet=True, player_dmg=22)
            self.splat(e.x, e.y, ICHOR, 0.8)
            self.snd("bloater_pop", e.x, e.y)
        elif k == "brute":
            self.snd("death_brute", e.x, e.y)
        elif k == "crawler":
            self.snd("bones", e.x, e.y)
        elif k == "spitter":
            self.snd("death_leech", e.x, e.y)
        elif k == "hellspawn":
            self.explode(e.x, e.y, 0.8, 2, (255, 120, 30), hurt_player=False, quiet=True, small=True)
            self.snd("death_zombie", e.x, e.y)
        elif k == "wretch":
            self.snd("wretch_blink", e.x, e.y)
            self.snd("death_zombie", e.x, e.y)
        elif k == "stalker":
            self.snd("stalker_screech", e.x, e.y)
        elif e.bdef:
            bd = e.bdef
            if e.weapon is not None and rnd.random() < bd.get("drop", 0.35):     # gun-toting monsters drop what they carried
                e.weapon.ammo = e.weapon.st["mag"]
                self.loot.append(Loot("weapon", e.x, e.y, e.weapon, pop=True))
                e.weapon = None
            if k == "chestmimic":
                if rnd.random() < 0.6:
                    self.drop_weapon(e.x, e.y, 1.0)
                for _ in range(12):
                    a = rnd.random() * math.tau
                    self.add(Particle("chunk", e.x, e.y, 0.5, math.cos(a) * 3, math.sin(a) * 3, 4, 2.5, (255, 210, 60), 3))
            if bd.get("boom"):
                rad, dmg_, col = bd["boom"]
                self.explode(e.x, e.y, rad, 6, col, hurt_player=True, quiet=False, player_dmg=dmg_)
            if bd.get("puddle"):
                self.splat(e.x, e.y, bd["puddle"], 0.6)
            self.snd("bones" if e.blood == BE.ASH else ("death_drone" if e.blood == BE.GOLD else "death_zombie"), e.x, e.y)
        elif k == "mimic":
            self.snd("mimic_scream", e.x, e.y)
            for _ in range(3):
                a = rnd.random() * math.tau
                cx, cy = e.x + math.cos(a) * 0.4, e.y + math.sin(a) * 0.4
                if not self.level.is_solid(int(cx), int(cy)):
                    c = Enemy("crawler", cx, cy, awake=True, depth=self.depth)
                    c.vx, c.vy = math.cos(a) * 4, math.sin(a) * 4
                    self.enemies.append(c)
        else:
            self.snd("death_" + k, e.x, e.y)
        if k in ("zombie", "spider", "brute"):
            self.snd("bones", e.x, e.y)
        if e.blood not in (OIL, ASH):
            self.snd("splat", e.x, e.y)
            self.splat(e.x, e.y, e.blood, e.r * 0.9 + 0.15)
        for _ in range(8):
            a = rnd.random() * math.tau
            s = rnd.uniform(1, 4)
            col = tuple(min(255, int(c * 1.3) + 20) for c in (e.blood or ASH))
            self.add(Particle("chunk", e.x, e.y, hz, math.cos(a) * s, math.sin(a) * s, rnd.uniform(2, 5), 3.0, col, rnd.uniform(3, 5)))
        big = k in ("spider", "brute", "walker")
        self.shake = max(self.shake, 9 if big else 4)
        self.hitstop = max(self.hitstop, 0.08 if big else 0.035)
        if e.owner:
            e.owner.children -= 1
        # lifesteal
        heal = p.weapon.st["lifesteal"] + p.mult("leech", 0)
        if heal and p.alive:
            p.hp = min(p.max_hp, p.hp + heal)
        # loot
        if rnd.random() < WEAPON_DROP.get(k, 0.025):
            self.drop_weapon(e.x, e.y, 0.6 if big else 0.0)
        elif rnd.random() < (0.2 if big else 0.045):
            self.drop_buff(e.x, e.y)
        elif rnd.random() < (0.08 if big else 0.005):
            self.drop_support(e.x, e.y, 0.5 if big else 0.0)
        elif rnd.random() < 0.04:
            self.loot.append(Loot("health", e.x, e.y, pop=True))

    def kill_spawner(self, s):
        self.score += 500
        L = self.level
        L.solid[L.i(int(s.x), int(s.y))] = 0
        self.gibs_from("spawner", s.x, s.y, 0.5, force=1.4)
        self.gibs_from("spawner", s.x, s.y, 0.5, count=6, force=1.1)
        self.spray(s.x, s.y, 0.5, ICHOR, 40, 5)
        self.spray(s.x, s.y, 0.5, RED, 25, 4)
        self.splat(s.x, s.y, ICHOR, 0.7)
        self.splat(s.x + 0.3, s.y - 0.2, RED, 0.4)
        self.explode(s.x, s.y, 2.0, 6, (130, 255, 80), quiet=True)
        self.snd("hive_death", s.x, s.y)
        self.hitstop = 0.1
        self.drop_weapon(s.x, s.y, 1.0)
        if rnd.random() < 0.5:
            self.drop_buff(s.x, s.y)
        if rnd.random() < 0.25:
            self.drop_support(s.x, s.y, 0.8)

    def breach(self, x, y, radius):
        """Explosions chew through walls, opening rooms up."""
        L = self.level
        broke = 0
        thin = radius > 4                 # huge craters: keep debris per wall low
        for cx in range(int(x - radius) - 1, int(x + radius) + 2):
            for cy in range(int(y - radius) - 1, int(y + radius) + 2):
                if math.hypot(cx + 0.5 - x, cy + 0.5 - y) < radius and L.destroy_wall(cx, cy):
                    broke += 1
                    if not thin or rnd.random() < 0.25:
                        self.gibs_from("rubble", cx + 0.5, cy + 0.5, 0.8, cx + 0.5 - x, cy + 0.5 - y, count=4 if not thin else 2, force=1.2)
                    for _ in range(6 if not thin else (1 if rnd.random() < 0.5 else 0)):
                        a = rnd.random() * math.tau
                        self.add(Particle("smoke", cx + 0.5, cy + 0.5, rnd.uniform(0.2, 1.0), math.cos(a), math.sin(a),
                                          rnd.uniform(0.2, 0.8), rnd.uniform(1.0, 2.0), (95, 88, 80), rnd.uniform(0.25, 0.45)))
                    for ddx in (-1, 0, 1):
                        for ddy in (-1, 0, 1):
                            nx, ny = cx + ddx, cy + ddy
                            if 0 <= nx < L.W and 0 <= ny < L.H:
                                self.explored[L.i(nx, ny)] = 1
                                self.explore_dirty.append((nx, ny))
        if broke:
            self.flow_tile = None
            self.snd("crumble", x, y)
        return broke

    def explode(self, x, y, radius, dmg, color=(255, 170, 60), hurt_player=True, quiet=False, small=False, player_dmg=15,
                breach=0.0, dtype="explosive"):
        self.add(Particle("ring", x, y, 0.05, radius * 3.2, 0, 0, 0.35, color, 0.1))
        n = 8 if small else 26
        for _ in range(n):
            a = rnd.random() * math.tau
            s = rnd.uniform(0.5, 1.0) * 3.5 * radius
            self.add(Particle("fire", x, y, rnd.uniform(0.1, 0.6), math.cos(a) * s, math.sin(a) * s, rnd.uniform(0.5, 2.5),
                              rnd.uniform(0.3, 0.7), color, rnd.uniform(10, 22)))
        for _ in range(n // 2):
            a = rnd.random() * math.tau
            s = rnd.uniform(0.3, 1.0) * 1.6
            self.add(Particle("smoke", x, y, rnd.uniform(0.2, 0.8), math.cos(a) * s, math.sin(a) * s, rnd.uniform(0.4, 1.2),
                              rnd.uniform(1.0, 2.2), (60, 56, 52), rnd.uniform(0.2, 0.4)))
        for _ in range(n):
            a = rnd.random() * math.tau
            s = rnd.uniform(4, 10)
            self.add(Particle("spark", x, y, 0.5, math.cos(a) * s, math.sin(a) * s, rnd.uniform(2, 7), 0.5, (255, 230, 150), 2))
        self.shake = max(self.shake, 4 if small else (11 if not quiet else 6))
        self.blast_kick(x, y, radius * 1.8, 7)
        if not quiet:
            self.snd("explosion", x, y)
        elif small:
            self.snd("explosion_small", x, y, 0.6)
        if dmg:
            for e in list(self.enemies) + self.bosses + [t for t in self.traps if t.shootable or t.mech == "reactor"]:
                if e.alive and not getattr(e, "submerged", False) and math.hypot(e.x - x, e.y - y) < radius + e.r:
                    e.hit(self, self.typed(e, dmg, dtype), (e.x - x) * 30, (e.y - y) * 30)
            for s in self.spawners:
                if s.alive and math.hypot(s.x - x, s.y - y) < radius:
                    s.hit(self, dmg * 2)
            for pos in list(self.barrels):
                if math.hypot(pos[0] + 0.5 - x, pos[1] + 0.5 - y) < radius:
                    self.damage_barrel(pos, 5)
            for pos in list(self.crates):
                if math.hypot(pos[0] + 0.5 - x, pos[1] + 0.5 - y) < radius:
                    self.damage_crate(pos, 5)
        if hurt_player:
            for t in list(self.turrets):
                if t.alive and math.hypot(t.x - x, t.y - y) < radius * 0.85:
                    t.hit(self, player_dmg)
            for p in self.players:
                if p.alive and math.hypot(p.x - x, p.y - y) < radius * 0.85:
                    self.hurt_player(player_dmg, x, y, knock=12, who=p, dtype="explosive")
        if breach:
            self.breach(x, y, breach)

    def damage_barrel(self, pos, dmg):
        if pos not in self.barrels:
            return
        self.barrels[pos] -= dmg
        if self.barrels[pos] <= 0:
            del self.barrels[pos]
            kind = self.barrel_kind.pop(pos, "chem")
            L = self.level
            L.props.pop(pos, None)
            L.solid[L.i(*pos)] = 0
            cx, cy = pos[0] + 0.5, pos[1] + 0.5
            self.gibs_from("barrel", cx, cy, 0.5, force=1.6)
            getattr(self, "barrel_" + kind)(cx, cy)

    # each barrel kind's detonation: all of them can hurt players too
    def barrel_fire(self, x, y):
        """Red: a fireball, then burning ground ('blaze') that scorches monsters and players for a while."""
        self.explode(x, y, 2.0, 10, (255, 120, 30), player_dmg=14, breach=1.0, dtype="fire")
        for k in range(7):
            a = k * math.tau / 7 + rnd.uniform(-0.3, 0.3)
            d = rnd.uniform(0.3, 1.6)
            self.hazards.append([x + math.cos(a) * d, y + math.sin(a) * d, 0.55, rnd.uniform(4, 6), "blaze", 8.0])
        for _ in range(30):
            a = rnd.random() * math.tau
            s_ = rnd.uniform(2, 6)
            self.add(Particle("fire", x, y, rnd.uniform(0.2, 0.8), math.cos(a) * s_, math.sin(a) * s_, rnd.uniform(1, 3), 0.8,
                              (255, 140, 40), rnd.uniform(14, 24)))
        self.splat(x, y, (22, 16, 12), 0.7)

    def barrel_chem(self, x, y):
        """Green: a burst of toxic gas clouds drifting outward, plus an acid splash."""
        self.explode(x, y, 2.0, 6, (150, 255, 70), player_dmg=10, breach=0.8, dtype="chemical")
        for k in range(7):
            a = k * math.tau / 7 + rnd.uniform(-0.3, 0.3)
            d = rnd.uniform(0.4, 1.4)
            self.add_gas(x + math.cos(a) * d, y + math.sin(a) * d, 7.0, math.cos(a) * 0.8, math.sin(a) * 0.8)
        for k in range(3):
            a = rnd.random() * math.tau
            self.hazards.append([x + math.cos(a) * 0.9, y + math.sin(a) * 0.9, 0.7, 5.0, "acid"])
        self.splat(x, y, ICHOR, 0.8)
        self.spray(x, y, 0.6, ICHOR, 30, 5)
        self.snd("sizzle", x, y)

    def barrel_rad(self, x, y):
        """Yellow: a blast that leaves a glowing fallout zone (hurts everything standing in it)."""
        self.explode(x, y, 1.8, 10, (210, 255, 90), player_dmg=12, breach=1.0)
        self.hazards.append([x, y, 2.2, 10.0, "rad", 7.0, 10.0])
        self.add(Particle("ring", x, y, 0.05, 6, 0, 0, 0.5, (200, 255, 90), 0.2))
        for _ in range(20):
            a = rnd.random() * math.tau
            s_ = rnd.uniform(1, 4)
            self.add(Particle("glow", x, y, 0.4, math.cos(a) * s_, math.sin(a) * s_, rnd.uniform(1, 3), 1.0, (170, 255, 70), 3))
        self.splat(x, y, (90, 120, 20), 0.6)

    def barrel_shrap(self, x, y):
        """Orange: a hard blast and a ring of metal fragments that tear into monsters and players alike."""
        self.explode(x, y, 2.4, 16, (255, 170, 60), player_dmg=20, breach=1.4)
        n = 24
        for k in range(n):
            a = k * math.tau / n + rnd.uniform(-0.08, 0.08)
            s_ = rnd.uniform(12, 17)
            hostile = k % 2 == 1                  # half the shards can hit players, half hit monsters
            pr = Proj("slug", x + math.cos(a) * 0.4, y + math.sin(a) * 0.4, 0.6, math.cos(a) * s_, math.sin(a) * s_,
                      8 if hostile else 7, hostile=hostile, life=0.45, color=(255, 190, 120), r=0.08, pierce=1)
            pr.dtype = "kinetic"
            self.projs.append(pr)
        self.snd("clatter", x, y, 0.9)

    def damage_crate(self, pos, dmg):
        if pos not in self.crates:
            return
        self.crates[pos] -= dmg
        cx, cy = pos[0] + 0.5, pos[1] + 0.5
        self.snd("clatter", cx, cy, 0.8)
        if self.crates[pos] <= 0:
            del self.crates[pos]
            L = self.level
            L.props.pop(pos, None)
            L.solid[L.i(*pos)] = 0
            self.gibs_from("crate", cx, cy, 0.4, force=1.2)
            self.snd("bones", cx, cy)
            for _ in range(10):
                a = rnd.random() * math.tau
                self.add(Particle("smoke", cx, cy, 0.3, math.cos(a), math.sin(a), 0.4, 0.8, (90, 80, 60), 0.2))
            r = rnd.random()
            if r < 0.45:
                self.drop_weapon(cx, cy, 0.5)
            elif r < 0.57:
                self.drop_support(cx, cy, 0.5)
            elif r < 0.8:
                self.drop_buff(cx, cy)
            else:
                self.loot.append(Loot("health", cx, cy, pop=True))

    def separation(self, me):
        sx = sy = 0.0
        for o in self.nearby(me.x, me.y):
            if o is me:
                continue
            dx, dy = me.x - o.x, me.y - o.y
            d2 = dx * dx + dy * dy
            rr = me.r + o.r
            if 1e-8 < d2 < rr * rr:
                d = math.sqrt(d2)
                f = (rr - d) / rr * 4.0
                if o.kind == "turret":
                    f *= 2
                sx += dx / d * f
                sy += dy / d * f
        return sx, sy

    def nearby(self, x, y):
        cx, cy = int(x) >> 1, int(y) >> 1
        g = self.grid
        for ix in (cx - 1, cx, cx + 1):
            for iy in (cy - 1, cy, cy + 1):
                lst = g.get((ix, iy))
                if lst:
                    yield from lst

    # ---- tick
    def update(self, dt, inp):
        inputs = inp if isinstance(inp, (list, tuple)) else [inp]
        self.shake = max(0.0, self.shake - dt * 30)
        for m in self.messages:
            m[2] -= dt
        self.messages = [m for m in self.messages if m[2] > 0]
        if self.hitstop > 0:
            self.hitstop -= dt
            return
        self.time += dt
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.flash_white = max(0.0, self.flash_white - dt)
        L = self.level
        for i, pl in enumerate(self.players):
            if pl.alive and i < len(inputs) and inputs[i] is not None:
                self.actor = pl
                pl.update(self, dt, inputs[i])
                self.actor = None
        alive = [pl for pl in self.players if pl.alive]
        p = self.player
        pts = tuple(sorted((int(pl.x), int(pl.y)) for pl in (alive or self.players)))
        pt = pts[0]
        if pts != self.flow_tile:
            self.flow_tile = pts
            self.flow = L.bfs(list(pts), 45)
        # reviving: stand on a downed partner's bones
        for pl in self.players:
            if not pl.alive and alive:
                if any(math.hypot(o.x - pl.x, o.y - pl.y) < 0.9 for o in alive):
                    pl.revive_t += dt
                    if rnd.random() < dt * 20:
                        self.add(Particle("glow", pl.x + rnd.uniform(-0.4, 0.4), pl.y + rnd.uniform(-0.4, 0.4), 0.1, 0, 0, 2, 0.6,
                                          (120, 230, 255), 2))
                    if pl.revive_t >= 2.5:
                        pl.alive = True
                        pl.hp = pl.max_hp * 0.4
                        pl.invuln = 2.0
                        pl.revive_t = 0.0
                        self.message("%s REVIVED" % (getattr(pl, "name", "") or "PLAYER %d" % (pl.idx + 1)), (120, 230, 255))
                        sfx.play("power")
                else:
                    pl.revive_t = max(0.0, pl.revive_t - dt)

        self.grid = {}
        for e in self.enemies:
            self.grid.setdefault((int(e.x) >> 1, int(e.y) >> 1), []).append(e)
        for e in self.enemies[:]:
            if e.alive:
                e.update(self, dt)
        for s in self.spawners:
            s.update(self, dt)
        for b in self.bosses:
            b.update(self, dt)
        self.bosses = [b for b in self.bosses if b.alive]
        for wn in self.warnings:
            wn[3] -= dt
        self.warnings = [wn for wn in self.warnings if wn[3] > 0]

        self.blocked = set()
        for pl in self.players:
            if pl.alive:
                self.actor = pl
                for g in pl.equipped():
                    g.update(self, dt, pl)
        self.actor = None
        for t in self.turrets:            # deployed turrets run on their own (their module left the inventory)
            if t.alive:
                t.update(self, dt, getattr(t, "owner", None) or self.player)
        self.turrets = [t for t in self.turrets if t.alive]
        self.projs = [b for b in self.projs if id(b) not in self.blocked and self.step_proj(b, dt)]
        self.enemies = [e for e in self.enemies if e.alive]
        self.spawners = [s for s in self.spawners if s.alive]
        for g in self.gibs:
            g.update(self, dt)
        if self.ejects:
            keep = []
            for ej in self.ejects:
                ej[0] -= dt
                if ej[0] <= 0:
                    self.spawn_casing(ej[1], ej[2])
                else:
                    keep.append(ej)
            self.ejects = keep
        self.particles = [q for q in self.particles if q.update(self, dt)]
        for bm in self.beams:
            bm[5] -= dt
        self.beams = [bm for bm in self.beams if bm[5] > 0]
        if self.dot_targets:
            self.flush_numbers()
        for pu in self.popups:
            pu[5] -= dt
            pu[2] += dt * 1.0
        self.popups = [pu for pu in self.popups if pu[5] > 0]
        for a_ in self.arcs:
            a_[1] -= dt
        self.arcs = [a_ for a_ in self.arcs if a_[1] > 0]

        # wretch radio static
        near = min((math.hypot(e.x - pl.x, e.y - pl.y) for e in self.enemies if e.kind == "wretch" for pl in alive), default=99)
        self.static_kick = max(0.0, self.static_kick - dt)
        self.static = max(self.static_kick, max(0.0, 1 - near / 8.0) * 0.8)
        self.sound_loops()
        # hazards: acid pools hurt you, burning ground hurts them
        self.acid_t -= dt
        for hz in self.hazards:
            hz[3] -= dt
            if hz[4] in ("rad", "gas"):
                x_, y_, r_, dps = hz[0], hz[1], hz[2], hz[5]
                if hz[4] == "gas":
                    hz[0] += hz[7] * dt
                    hz[1] += hz[8] * dt
                    hz[7] *= 0.98
                    hz[8] *= 0.98
                    dps *= min(1.0, hz[3] / hz[6] * 1.6)
                    if rnd.random() < dt * 1.5:
                        self.add(Particle("smoke", x_ + rnd.uniform(-r_, r_) * 0.5, y_ + rnd.uniform(-r_, r_) * 0.5, 0.3, rnd.uniform(-0.2, 0.2),
                                          rnd.uniform(-0.2, 0.2), 0.15, 1.5, (150, 175, 40), 0.35))
                elif rnd.random() < dt * 10 * r_:
                    a, d_ = rnd.random() * math.tau, rnd.random() * r_
                    self.add(Particle("glow", x_ + math.cos(a) * d_, y_ + math.sin(a) * d_, 0.05, 0, 0, rnd.uniform(0.6, 1.4), 1.2,
                                      (140, 255, 70), 2))
                for e in list(self.enemies) + self.bosses:
                    if e.alive and e.state != "dormant" and not getattr(e, "submerged", False) and (e.x - x_) ** 2 + (e.y - y_) ** 2 < (r_ + e.r) ** 2:
                        self.dot(e, dps * dt, "radiation" if hz[4] == "rad" else "chemical")
                for pl in alive:
                    if (pl.x - x_) ** 2 + (pl.y - y_) ** 2 < r_ * r_:
                        pl.hp -= dps * dt * pl.mult("aegis") * CH.player_mult(pl, "radiation" if hz[4] == "rad" else "chemical")
                        self.hurt_flash = max(self.hurt_flash, 0.06)
                        if self.acid_t <= 0:
                            self.acid_t = 0.45
                            sfx.play("sizzle", 0.5)
                        self.check_player_death(x_, y_, pl)
                continue
            if hz[4] == "jet":             # chemical-jet puddles: napalm burns, cryo chills, rad-waste irradiates - everyone
                kind = hz[7]
                k_ = min(1.0, hz[3] / hz[6] * 2)
                dps = hz[5] * k_
                J = self.JET[kind]
                for e in self.nearby(hz[0], hz[1]):
                    if e.alive and e.kind not in FLYERS and (e.x - hz[0]) ** 2 + (e.y - hz[1]) ** 2 < (hz[2] + e.r) ** 2:
                        if kind == "napalm" and hasattr(e, "burn_dps"):
                            e.burn = max(e.burn, 1.2)
                            e.burn_dps = max(e.burn_dps, dps * DM.mult(e, "fire"))
                        else:
                            self.dot(e, dps * dt, J["dtype"])
                            if kind == "cryo" and hasattr(e, "frozen") and e.frozen <= 0:
                                e.chill += dt * 0.25 * DM.mult(e, "cryo")
                                if e.chill >= 1.0:
                                    e.frozen, e.chill, e.vx, e.vy = 3.0, 0.0, 0.0, 0.0
                for pl in alive:
                    if (pl.x - hz[0]) ** 2 + (pl.y - hz[1]) ** 2 < hz[2] ** 2:
                        pl.hp -= dps * 0.6 * dt * pl.mult("aegis") * CH.player_mult(pl, J["dtype"])
                        if kind == "cryo":
                            pl.status["chill"] = max(pl.status.get("chill", 0), 0.5)
                        self.hurt_flash = max(self.hurt_flash, 0.05)
                        self.check_player_death(hz[0], hz[1], pl)
                if rnd.random() < dt * 6 * hz[2]:
                    a, d_ = rnd.random() * math.tau, rnd.random() * hz[2]
                    self.add(Particle("fire" if kind == "napalm" else "glow", hz[0] + math.cos(a) * d_, hz[1] + math.sin(a) * d_, 0.05,
                                      0, 0, rnd.uniform(0.6, 1.4), 0.5, J["col"], 10 if kind == "napalm" else 2))
                continue
            if hz[4] == "blaze":           # burning barrel fuel: scorches monsters and players
                if rnd.random() < dt * 14:
                    self.add(Particle("fire", hz[0] + rnd.uniform(-0.3, 0.3), hz[1] + rnd.uniform(-0.3, 0.3), 0.05,
                                      0, 0, rnd.uniform(0.9, 1.8), 0.5, (255, 120, 30), rnd.uniform(10, 16)))
                for e in self.nearby(hz[0], hz[1]):
                    if e.alive and e.kind not in FLYERS and math.hypot(e.x - hz[0], e.y - hz[1]) < hz[2] + e.r:
                        e.burn = max(e.burn, 1.5)
                        e.burn_dps = max(e.burn_dps, hz[5] * DM.mult(e, "fire"))
                for pl in alive:
                    if math.hypot(pl.x - hz[0], pl.y - hz[1]) < hz[2]:
                        pl.hp -= hz[5] * dt * pl.mult("aegis") * CH.player_mult(pl, "fire")
                        self.hurt_flash = max(self.hurt_flash, 0.06)
                        if self.acid_t <= 0:
                            self.acid_t = 0.4
                            sfx.play("sizzle", 0.5)
                        self.check_player_death(hz[0], hz[1], pl)
                continue
            if hz[4] == "acidp":           # Acid-Augmented puddles: eat monsters, leave players alone
                k_ = min(1.0, hz[3] / hz[6] * 2)
                for e in self.nearby(hz[0], hz[1]):
                    if e.alive and e.kind not in FLYERS and (e.x - hz[0]) ** 2 + (e.y - hz[1]) ** 2 < (hz[2] + e.r) ** 2:
                        self.dot(e, hz[5] * k_ * dt, "chemical")
                if rnd.random() < dt * 5:
                    self.add(Particle("glow", hz[0] + rnd.uniform(-0.3, 0.3), hz[1] + rnd.uniform(-0.3, 0.3), 0.02, 0, 0, 0.8, 0.5,
                                      (140, 255, 70), 2))
                continue
            if hz[4] == "fire":
                if rnd.random() < dt * 12:
                    self.add(Particle("fire", hz[0] + rnd.uniform(-0.3, 0.3), hz[1] + rnd.uniform(-0.3, 0.3), 0.05,
                                      0, 0, rnd.uniform(0.8, 1.6), 0.45, (255, 120, 30), rnd.uniform(8, 14)))
                for e in self.nearby(hz[0], hz[1]):
                    if e.alive and e.kind not in FLYERS and math.hypot(e.x - hz[0], e.y - hz[1]) < hz[2] + e.r:
                        e.burn = max(e.burn, 1.5)
                        e.burn_dps = max(e.burn_dps, (hz[5] or 1.0) * DM.mult(e, "fire"))
                continue
            if rnd.random() < dt * 6:
                self.add(Particle("glow", hz[0] + rnd.uniform(-hz[2], hz[2]) * 0.6, hz[1] + rnd.uniform(-hz[2], hz[2]) * 0.6, 0.02,
                                  0, 0, 1.2, 0.6, (120, 255, 60), 2))
            for pl in alive:
                if math.hypot(pl.x - hz[0], pl.y - hz[1]) < hz[2]:
                    pl.hp -= 14 * dt * pl.mult("aegis") * CH.player_mult(pl, "chemical")
                    self.hurt_flash = max(self.hurt_flash, 0.08)
                    if self.acid_t <= 0:
                        self.acid_t = 0.4
                        sfx.play("sizzle", 0.6)
                    self.check_player_death(hz[0], hz[1], pl)
        self.hazards = [hz for hz in self.hazards if hz[3] > 0]

        # environmental traps
        for t in self.traps:
            t.update(self, dt)
        self.traps = [t for t in self.traps if t.alive]
        self.shootables = [t for t in self.traps if t.shootable]

        # loot (per player)
        for lt in self.loot[:]:
            lt.t += dt
            if lt.vz or lt.z > 0:
                lt.vz -= 18 * dt
                lt.z += lt.vz * dt
                nx, ny = resolve(L, lt.x + lt.vx * dt, lt.y + lt.vy * dt, 0.2)
                lt.x, lt.y = nx, ny
                if lt.z <= 0:
                    lt.z, lt.vx, lt.vy = 0.0, lt.vx * 0.4, lt.vy * 0.4
                    lt.vz = -lt.vz * 0.35 if lt.vz < -2 else 0.0
            for pl in alive:
                d = math.hypot(lt.x - pl.x, lt.y - pl.y)
                if lt.kind in ("weapon", "support"):
                    continue                  # taken with E / A (see pickup_target below)
                if d >= 0.6 or lt not in self.loot:
                    continue
                self.loot.remove(lt)
                if lt.kind == "health":
                    pl.hp = min(pl.max_hp, pl.hp + 35)
                    sfx.play("pickup")
                    self.message("+35 integrity" + (" (P%d)" % (pl.idx + 1) if len(self.players) > 1 else ""), (255, 120, 120))
                else:
                    self.apply_buff(lt.item, pl)
                for _ in range(14):
                    a = rnd.random() * math.tau
                    self.add(Particle("glow", lt.x, lt.y, 0.4, math.cos(a) * 2.5, math.sin(a) * 2.5, rnd.uniform(1, 3), 0.6,
                                      (255, 255, 255), 2))
        # E / A picks up whatever's nearest / faced: floor loot, a barrel, or your own turret
        self.near_loot_by = {}
        self.pickup_by = {}
        for pl in alive:
            tg = pl.pickup_target(self)
            if tg is None:
                continue
            self.pickup_by[pl.idx] = tg
            if tg[0] == "loot":
                self.near_loot_by[pl.idx] = tg[1]
        self.near_loot = self.near_loot_by.get(0)
        for i, pl in enumerate(self.players):
            tg = self.pickup_by.get(i)
            if tg is None or not pl.alive or i >= len(inputs) or "interact" not in getattr(inputs[i], "pressed", ()):
                continue
            kind, obj = tg
            self.actor = pl
            if kind == "loot" and obj in self.loot:
                if obj.kind == "support":
                    self.take_support(obj, pl)
                else:
                    self.take_weapon(obj, pl)
            elif kind == "barrel" and obj in self.barrels:
                pl.pick_up_barrel(self, obj)
            elif kind == "turret" and obj.alive:
                obj.mod.pack_up(self, pl, pl.sel)
            self.actor = None

        ex, ey = L.exit
        if not self.bosses and any(math.hypot(ex - pl.x, ey - pl.y) < 0.6 for pl in alive):
            self.exit_reached = True

        self.explore_t -= dt
        if self.explore_t <= 0:
            self.explore_t = 0.15
            r = 9
            for pt in pts:
                for x in range(max(0, pt[0] - r), min(L.W, pt[0] + r + 1)):
                    for y in range(max(0, pt[1] - r), min(L.H, pt[1] + r + 1)):
                        i = L.i(x, y)
                        if not self.explored[i] and (x - pt[0]) ** 2 + (y - pt[1]) ** 2 <= r * r:
                            self.explored[i] = 1
                            self.explore_dirty.append((x, y))

    def impact(self, b, x, y):
        """Projectile ended at (x, y)."""
        if getattr(b, "acid", 0) and not b.hostile and rnd.random() < b.acid:
            self.acid_puddle(x, y, b.dmg * 0.9)
        if b.kind == "nuke":
            rr, dur, dps, breach_r = b.rad     # terrain destruction: 3 tiles (tactical) / 5 tiles (nuke)
            big = rr >= 3
            self.explode(x, y, b.blast, b.dmg, (200, 255, 90), hurt_player=True, player_dmg=min(b.dmg * 0.6, 60), breach=breach_r)
            for _ in range(70 if big else 35):
                a = rnd.random() * math.tau
                s_ = rnd.uniform(0.3, 1.0) * b.blast * 3
                self.add(Particle("fire", x, y, rnd.uniform(0.1, 0.8), math.cos(a) * s_, math.sin(a) * s_, rnd.uniform(0.5, 3), rnd.uniform(0.5, 1.1),
                                  rnd.choice(((255, 240, 150), (220, 255, 90), (255, 150, 40))), rnd.uniform(18, 34)))
            for _ in range(40 if big else 20):    # rising mushroom column
                self.add(Particle("smoke", x + rnd.uniform(-0.4, 0.4), y + rnd.uniform(-0.4, 0.4), rnd.uniform(0.5, 2.5), rnd.uniform(-0.3, 0.3),
                                  rnd.uniform(-0.3, 0.3), rnd.uniform(1.5, 3.5), rnd.uniform(2, 4), (90, 100, 70), rnd.uniform(0.4, 0.8)))
            self.add(Particle("ring", x, y, 0.05, b.blast * 4, 0, 0, 0.6, (220, 255, 120), 0.2))
            self.hazards.append([x, y, rr, dur, "rad", dps, dur])
            self.flash_white = 0.6 if big else 0.35
            self.shake = 24 if big else 15
            self.hitstop = max(self.hitstop, 0.12)
            sfx.play("nuke_blast")
            return
        if b.effect and b.effect.startswith("gmod:"):
            self.grenade_burst(b, x, y, b.effect[5:])
            return
        if b.effect and b.effect.startswith("jet:"):
            self.jet_spatter(b, x, y, b.effect[4:])
            return
        if b.effect == "cluster" and not b.hostile:
            self.cluster_burst(b, x, y)
        if b.blast:
            col = (120, 255, 90) if b.kind == "plasma" else ((255, 90, 40) if b.hostile else (255, 170, 60))
            if b.kind == "fireball":
                col = (255, 120, 30)
            small = b.kind in ("plasma", "fireball", "missile") or b.blast < 1.0
            heavy = b.kind in ("rocket", "grenade", "missile") and not b.hostile
            # your own rockets and grenades hurt you too (reduced), and they chew through walls
            pdmg = b.dmg if b.hostile else min(b.dmg * (1.5 if b.kind == "missile" or b.effect == "bomblet" else 0.6), 40)
            self.explode(x, y, b.blast, b.dmg if not b.hostile else b.dmg * 0.5, col,
                         hurt_player=b.hostile or heavy, quiet=small, small=small, player_dmg=pdmg,
                         breach=(max(1.0, b.blast * 0.7) if b.effect in ("bomblet", "cluster") else b.blast * 0.7)
                         if (heavy or b.kind == "mortar") else 0.0,
                         dtype=getattr(b, "dtype", "explosive") if b.kind == "plasma" else "explosive")
            return
        if b.kind == "acid":
            self.hazards.append([x, y, 0.8, 4.0, "acid"])
            self.splat(x, y, (60, 170, 30), 0.45)
            self.spray(x, y, 0.2, (90, 200, 40), 10, 2.5)
            self.snd("sizzle", x, y)
            return
        if b.kind == "flame" or b.kind == "cryo":
            return
        if b.kind == "chem":         # spray splashing on a wall still leaves gas
            self.add_gas(b.x, b.y, b.gas)
            return
        for _ in range(6):
            a = rnd.random() * math.tau
            s = rnd.uniform(2, 5)
            self.add(Particle("spark", x, y, b.z, -b.vx * 0.15 + math.cos(a) * s, -b.vy * 0.15 + math.sin(a) * s,
                              rnd.uniform(0, 3), 0.25, b.color, 2))
        self.add(Particle("chunk", x, y, b.z, -b.vx * 0.1, -b.vy * 0.1, 2, 1.0, (70, 70, 80), 3))
        if not b.hostile:
            self.snd("ricochet", x, y)

    JET = {"napalm": dict(col=(255, 120, 30), dtype="fire", life=4.0),
           "cryo": dict(col=(150, 215, 255), dtype="cryo", life=4.0),
           "rad": dict(col=(170, 255, 60), dtype="radiation", life=6.0)}

    def jet_spatter(self, b, x, y, kind):
        """A chemical-jet droplet landed: splash, then feed (or start) a puddle that hurts monsters and players."""
        J = self.JET[kind]
        L = self.level
        x, y = x - b.vx * 0.01, y - b.vy * 0.01
        if L.is_solid(int(x), int(y)):
            return
        for _ in range(4):
            a = rnd.random() * math.tau
            s_ = rnd.uniform(1.5, 4)
            self.add(Particle("glow", x, y, 0.3, math.cos(a) * s_ - b.vx * 0.08, math.sin(a) * s_ - b.vy * 0.08, rnd.uniform(1, 2.5),
                              0.35, J["col"], 2))
        dps = max(1.5, b.dmg * 1.6)
        for hz in self.hazards:          # keep feeding the same puddle rather than carpeting the floor
            if hz[4] == "jet" and hz[7] == kind and (hz[0] - x) ** 2 + (hz[1] - y) ** 2 < 0.5 ** 2:
                hz[3] = hz[6] = J["life"]
                hz[2] = min(1.3, hz[2] + 0.04)
                hz[5] = max(hz[5], dps)
                return
        self.hazards.append([x, y, 0.45, J["life"], "jet", dps, J["life"], kind])

    def grenade_burst(self, b, x, y, kind):
        """Grenade modules: each kind goes off its own way; all of them hurt players close by and chew walls."""
        R, dmg = b.blast, b.dmg
        if kind == "hex":
            self.explode(x, y, R, dmg, (255, 200, 90), player_dmg=dmg * 0.5, breach=R * 0.8)
        elif kind == "shrapnel":
            self.explode(x, y, R * 0.8, dmg * 0.6, (255, 170, 60), player_dmg=dmg * 0.35, breach=R * 0.5)
            for k in range(20):
                a = k * math.tau / 20 + rnd.uniform(-0.1, 0.1)
                hostile = k % 2 == 1
                pr = Proj("slug", x + math.cos(a) * 0.3, y + math.sin(a) * 0.3, 0.6, math.cos(a) * 15, math.sin(a) * 15,
                          dmg * 0.25, hostile=hostile, life=0.45, color=(255, 190, 120), r=0.08, pierce=1)
                self.projs.append(pr)
        elif kind == "nuke":
            self.explode(x, y, R * 1.2, dmg, (200, 255, 90), player_dmg=min(dmg * 0.6, 60), breach=3.0)
            self.hazards.append([x, y, 2.5, 10.0, "rad", max(4.0, dmg * 0.08), 10.0])
            self.add(Particle("ring", x, y, 0.05, R * 4, 0, 0, 0.6, (220, 255, 120), 0.2))
            self.flash_white = 0.35
            self.shake = 15
            sfx.play("nuke_blast")
        elif kind == "incendiary":
            self.explode(x, y, R * 0.8, dmg * 0.4, (255, 120, 30), player_dmg=dmg * 0.3, breach=R * 0.4, dtype="fire")
            for k in range(9):
                a = k * math.tau / 9 + rnd.uniform(-0.3, 0.3)
                d = rnd.uniform(0.3, R)
                self.hazards.append([x + math.cos(a) * d, y + math.sin(a) * d, 0.55, rnd.uniform(5, 8), "blaze", max(5.0, dmg * 0.1)])
        elif kind == "cryo":
            self.explode(x, y, R, dmg * 0.4, (150, 215, 255), player_dmg=dmg * 0.25, breach=R * 0.4, dtype="cryo")
            for e in list(self.enemies):
                if e.alive and math.hypot(e.x - x, e.y - y) < R + e.r and hasattr(e, "frozen"):
                    e.frozen = 3.5 * DM.mult(e, "cryo")
                    e.vx = e.vy = 0.0
            for pl in self.players:
                if pl.alive and math.hypot(pl.x - x, pl.y - y) < R:
                    pl.status["chill"] = 3.0
            self.splat(x, y, (175, 210, 235), R * 0.5)
            self.snd("freeze", x, y)
        else:   # corrosive
            self.explode(x, y, R * 0.8, dmg * 0.4, (140, 230, 50), player_dmg=dmg * 0.3, breach=R * 0.4, dtype="chemical")
            for k in range(4):
                a = k * math.tau / 4 + rnd.uniform(-0.4, 0.4)
                self.hazards.append([x + math.cos(a) * R * 0.5, y + math.sin(a) * R * 0.5, 0.7, 6.0, "acid"])
                self.hazards.append([x + math.cos(a) * R * 0.5, y + math.sin(a) * R * 0.5, 0.6, 6.0, "acidp", max(4.0, dmg * 0.1), 6.0])
            self.add_gas(x, y, max(5.0, dmg * 0.08))
            self.splat(x, y, (90, 200, 40), R * 0.5)

    def cluster_burst(self, b, x, y):
        """Cluster shell bursting: throw a ring of small grenades that bounce about and pop a moment later."""
        n = int(b.cone) or 6
        for i in range(n):
            a = i * math.tau / n + rnd.uniform(-0.3, 0.3)
            s_ = rnd.uniform(2.5, 5.0)
            bl = Proj("grenade", x, y, 0.4, math.cos(a) * s_, math.sin(a) * s_, b.dmg * 0.45, life=rnd.uniform(0.45, 0.9),
                      color=b.color, r=0.1, blast=0.9, burn=b.burn, shock=b.shock, slow=b.slow, chill=b.chill)
            bl.vz, bl.grav = rnd.uniform(3.0, 5.0), 14.0
            bl.dtype = "explosive"
            bl.effect = "bomblet"
            bl.owner = b.owner
            self.projs.append(bl)
        self.snd("clatter", x, y, 0.6)

    def nearest_enemy(self, x, y, vx, vy, rng=7.0):
        sp = math.hypot(vx, vy) or 1
        best, bd = None, rng
        for e in self.enemies:
            dx, dy = e.x - x, e.y - y
            d = math.hypot(dx, dy)
            if d < bd and (dx * vx + dy * vy) / (sp * (d or 1)) > 0.2:
                best, bd = e, d
        return best

    def step_rail(self, b, dt):
        """Hyper-velocity slug: sub-stepped so it never skips a target, tears through every monster
        and punches through up to b.bounce wall blocks before it is spent."""
        L = self.level
        dist = math.hypot(b.vx, b.vy) * dt
        n = max(1, int(dist / 0.15))
        ux, uy = b.vx * dt / n, b.vy * dt / n
        x0, y0 = b.x, b.y
        alive = True
        for _ in range(n):
            nx, ny = b.x + ux, b.y + uy
            cx, cy = int(nx), int(ny)
            if not (0 <= cx < L.W and 0 <= cy < L.H):
                alive = False
                break
            if L.is_solid(cx, cy):
                cell = (cx, cy)
                if cell not in b.hit:
                    b.hit.add(cell)
                    self.hit_solid(cell, b.dmg, nx, ny, b.z, b)
                    self.breach(cx + 0.5, cy + 0.5, 0.5)       # the slug blows the block it tunnels through to rubble
                    b.bounce -= 1
                    self.snd("hit_metal", nx, ny, 0.6)
                    for _ in range(8):
                        a = rnd.random() * math.tau
                        s = rnd.uniform(2, 6)
                        self.add(Particle("spark", nx, ny, b.z, math.cos(a) * s - ux * 20, math.sin(a) * s - uy * 20,
                                          rnd.uniform(1, 4), 0.35, b.color, 2))
                    self.add(Particle("chunk", nx, ny, b.z, rnd.uniform(-2, 2), rnd.uniform(-2, 2), 2, 1.0, (80, 76, 72), 3))
                    if b.bounce < 0:
                        alive = False
                        break
            b.x, b.y = nx, ny
            for e in list(self.nearby(b.x, b.y)) + self.bosses + self.shootables:
                if e.alive and id(e) not in b.hit and not getattr(e, "submerged", False) and math.hypot(e.x - b.x, e.y - b.y) < e.r + b.r:
                    b.hit.add(id(e))
                    self.hit_enemy(e, b.dmg, b.vx, b.vy, b)
                    if getattr(e, "blood", None):
                        self.spray(e.x, e.y, 0.8, e.blood, 16, 7)
        self.beams.append([x0, y0, b.x, b.y, b.z, 0.35, 0.35, b.color, 0.7])
        b.life -= dt
        if not alive or b.life <= 0:
            self.add(Particle("ring", b.x, b.y, b.z, 1.2, 0, 0, 0.2, b.color, 0.1))
            return False
        return True

    def step_proj(self, b, dt):
        L = self.level
        k = b.kind
        if k == "rail":
            return self.step_rail(b, dt)
        if k == "wave":
            return self.step_wave(b, dt)
        b.age += dt
        if k == "mortar":
            b.x += b.vx * dt               # enemy shells drop straight down (vx = vy = 0); turret shells arc
            b.y += b.vy * dt
            b.z += b.vz * dt
            b.vz -= 6 * dt
            if b.z <= 0.1:
                self.impact(b, b.x, b.y)
                return False
            return True
        tgp = self.nearest_player(b.x, b.y) if b.hostile else None
        if b.homing and b.hostile and tgp.alive and b.age < 2.5:
            want = math.atan2(tgp.y - b.y, tgp.x - b.x)
            cur = math.atan2(b.vy, b.vx)
            diff = (want - cur + math.pi) % math.tau - math.pi
            turn = max(-2.2 * dt * b.homing, min(2.2 * dt * b.homing, diff))
            b.vx, b.vy = rot(b.vx, b.vy, turn)
        if b.homing and not b.hostile:
            tgt = self.nearest_enemy(b.x, b.y, b.vx, b.vy)
            if tgt:
                want = math.atan2(tgt.y - b.y, tgt.x - b.x)
                cur = math.atan2(b.vy, b.vx)
                diff = (want - cur + math.pi) % math.tau - math.pi
                turn = max(-5 * dt * b.homing, min(5 * dt * b.homing, diff))
                b.vx, b.vy = rot(b.vx, b.vy, turn)
        if k == "rocket":
            sp = math.hypot(b.vx, b.vy) or 1
            ns = min(b.maxspeed, sp + dt * 28)
            b.vx, b.vy = b.vx / sp * ns, b.vy / sp * ns
            b.trail -= dt
            if b.trail <= 0:
                b.trail = 0.02
                self.add(Particle("smoke", b.x - b.vx * 0.03, b.y - b.vy * 0.03, b.z, rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3),
                                  0.3, 0.7, (90, 85, 80), 0.12))
                self.add(Particle("fire", b.x - b.vx * 0.02, b.y - b.vy * 0.02, b.z, 0, 0, 0, 0.12, (255, 150, 50), 9))
        elif k == "missile":
            sp = math.hypot(b.vx, b.vy) or 1
            ns = min(b.maxspeed, sp + dt * 22)
            b.vx, b.vy = b.vx / sp * ns, b.vy / sp * ns
            if b.age > 0.12 and (not b.homing or self.nearest_enemy(b.x, b.y, b.vx, b.vy) is None):
                cur = math.atan2(b.vy, b.vx)
                diff = (b.cone - cur + math.pi) % math.tau - math.pi
                b.vx, b.vy = rot(b.vx, b.vy, max(-2.5 * dt, min(2.5 * dt, diff)))
            b.trail -= dt
            if b.trail <= 0:
                b.trail = 0.03
                self.add(Particle("smoke", b.x - b.vx * 0.02, b.y - b.vy * 0.02, b.z, rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2),
                                  0.2, 0.45, (100, 95, 90), 0.08))
                self.add(Particle("fire", b.x - b.vx * 0.015, b.y - b.vy * 0.015, b.z, 0, 0, 0, 0.08, (255, 160, 60), 6))
        elif k in ("chem", "cryo"):
            f = math.exp(-1.7 * dt)
            b.vx *= f
            b.vy *= f
            b.r += dt * 1.5
            b.z += dt * 0.3
        elif k == "nuke":
            sp = math.hypot(b.vx, b.vy) or 1
            ns = min(14.0, sp + dt * 10)
            b.vx, b.vy = b.vx / sp * ns, b.vy / sp * ns
            b.trail -= dt
            if b.trail <= 0:
                b.trail = 0.02
                self.add(Particle("smoke", b.x - b.vx * 0.03, b.y - b.vy * 0.03, b.z, rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3),
                                  0.3, 0.9, (80, 95, 70), 0.15))
                self.add(Particle("fire", b.x - b.vx * 0.02, b.y - b.vy * 0.02, b.z, 0, 0, 0, 0.15, (170, 255, 70), 11))
        elif k == "cleaver":
            b.spin += dt * 25
            b.hurt_cd = max(0.0, b.hurt_cd - dt)
            o = b.owner
            if b.age > 0.6 and o is not None and o.alive:
                ox_, oy_ = o.x - b.x, o.y - b.y
                ol = math.hypot(ox_, oy_) or 1
                b.vx, b.vy = ox_ / ol * 9, oy_ / ol * 9
                if ol < 0.5:
                    return False
            for pl in self.players:
                if b.hurt_cd <= 0 and pl.alive and math.hypot(pl.x - b.x, pl.y - b.y) < pl.R + b.r:
                    b.hurt_cd = 0.5
                    self.hurt_player(b.dmg, b.x - b.vx, b.y - b.vy, who=pl)
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.life -= dt
            return b.life > 0
        elif k == "saw":
            b.spin += dt * 30
            b.hurt_cd = max(0.0, b.hurt_cd - dt)
            for pl in self.players:
                if b.age > 0.3 and b.hurt_cd <= 0 and pl.alive and math.hypot(pl.x - b.x, pl.y - b.y) < pl.R + b.r:
                    b.hurt_cd = 0.6
                    self.hurt_player(min(b.dmg * 0.7, 15), b.x - b.vx, b.y - b.vy, knock=6, who=pl)
        elif k == "flame":
            f = math.exp(-1.6 * dt)
            b.vx *= f
            b.vy *= f
            b.r += dt * 1.6
            b.z += dt * 0.5
            if rnd.random() < dt * 5:
                self.add(Particle("fire", b.x, b.y, b.z, b.vx * 0.15, b.vy * 0.15, rnd.uniform(0.8, 1.6), 0.4,
                                  (255, 110, 25), rnd.uniform(10, 18)))
            if rnd.random() < dt * 6:
                self.add(Particle("spark", b.x, b.y, b.z, b.vx * 0.3 + rnd.uniform(-1, 1), b.vy * 0.3 + rnd.uniform(-1, 1),
                                  rnd.uniform(1, 3), 0.5, (255, 170, 60), 2))
        elif k == "fireball":
            if rnd.random() < dt * 40:
                self.add(Particle("fire", b.x, b.y, b.z, rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 0.5, 0.35,
                                  (255, 110, 20), rnd.uniform(8, 14)))
        elif k == "plasma" and rnd.random() < dt * 30:
            self.add(Particle("glow", b.x, b.y, b.z, rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0, 0.3, b.color, 2))
        if b.grav:
            b.vz -= b.grav * dt
            b.z += b.vz * dt
            floor = 0.12 if k == "grenade" else 0.0
            if b.z <= floor:
                if k == "acid":
                    self.impact(b, b.x, b.y)
                    return False
                b.z = floor
                if b.vz < -1.5:
                    self.snd("tink", b.x, b.y, 0.5)
                b.vz = abs(b.vz) * 0.45
                b.vx *= 0.7
                b.vy *= 0.7
        sp = math.hypot(b.vx, b.vy)
        steps = max(1, int(sp * dt / 0.22) + 1)
        for _ in range(steps):
            nx, ny = b.x + b.vx * dt / steps, b.y + b.vy * dt / steps
            cx, cy = int(nx), int(ny)
            if L.is_solid(cx, cy):
                destructible = self.hit_solid((cx, cy), b.dmg, nx, ny, b.z, b)
                if not destructible and ((k == "grenade" and b.effect != "cluster") or b.bounce > 0):
                    if L.is_solid(cx, int(b.y)):
                        b.vx = -b.vx * 0.7
                    if L.is_solid(int(b.x), cy):
                        b.vy = -b.vy * 0.7
                    if k != "grenade":
                        b.bounce -= 1
                        b.hit.clear()
                        if k == "saw":
                            self.snd("saw_bounce", b.x, b.y, 0.7)
                            for _ in range(6):
                                a = rnd.random() * math.tau
                                self.add(Particle("spark", b.x, b.y, b.z, math.cos(a) * 4, math.sin(a) * 4, rnd.uniform(1, 3), 0.3,
                                                  (255, 230, 160), 2))
                    else:
                        self.snd("tink", b.x, b.y, 0.5)
                    return True
                self.impact(b, b.x, b.y)
                return False
            b.x, b.y = nx, ny
            if b.hostile:
                tur = next((t for t in self.turrets if t.alive and (k not in ("acid", "mortar") or b.z < 1.3)
                            and math.hypot(t.x - b.x, t.y - b.y) < t.R + b.r), None)
                if tur is not None:
                    if b.blast or k == "acid":
                        self.impact(b, b.x, b.y)
                    else:
                        tur.hit(self, b.dmg)
                    return False
                for pl in self.players:
                    if pl.alive and (k != "acid" or b.z < 1.3) and math.hypot(pl.x - b.x, pl.y - b.y) < pl.R + b.r:
                        if b.blast or k == "acid":
                            self.impact(b, b.x, b.y)
                        else:
                            self.hurt_player(b.dmg, b.x - b.vx, b.y - b.vy, who=pl,
                                             dtype=b.dtype if b.dtype not in (None, "kinetic") else CH.HOSTILE_TYPE.get(k, "kinetic"))
                        if b.effect:
                            self.player_effect(b.effect, b.owner, who=pl)
                        if k == "chem" and b.gas:
                            self.add_gas(b.x, b.y, b.gas)
                        return False
                continue
            if b.effect == "bomblet" and b.age < 0.3:
                continue                   # freshly scattered bomblets arm before they can go off on contact
            for e in list(self.nearby(b.x, b.y)) + self.bosses + self.shootables:
                if e.alive and id(e) not in b.hit and not getattr(e, "submerged", False) and math.hypot(e.x - b.x, e.y - b.y) < e.r + b.r:
                    if e.bdef and e.bdef["ai"] == "shield" if hasattr(e, "bdef") else False:
                        tg = getattr(e, "target", None) or self.player
                        fx, fy = tg.x - e.x, tg.y - e.y
                        fl = math.hypot(fx, fy) or 1
                        bl = math.hypot(b.vx, b.vy) or 1
                        if (b.vx * fx + b.vy * fy) / (fl * bl) < -0.35 and k not in ("grenade", "rocket", "nuke", "plasma") and k not in WP.SPRAYS:
                            for _ in range(5):
                                a = rnd.random() * math.tau
                                self.add(Particle("spark", b.x, b.y, b.z, math.cos(a) * 4, math.sin(a) * 4, rnd.uniform(1, 3), 0.25, (255, 230, 160), 2))
                            self.snd("hit_metal", b.x, b.y, 0.6)
                            if k == "jet" and b.effect and b.effect.startswith("jet:"):
                                # the stream splashes off the shield and runs down it into a puddle round the knight's feet
                                self.jet_spatter(b, (b.x + e.x) / 2, (b.y + e.y) / 2, b.effect[4:])
                                return False
                            if not (b.ammo == "pen" or b.effect == "sabot" or k == "rail"):
                                return False      # deflected by the tower shield
                            # penetrating cores, sabots and rails punch straight through the shield into whoever holds it
                    if k in ("grenade", "rocket", "nuke", "missile"):
                        self.impact(b, b.x, b.y)
                        return False
                    b.hit.add(id(e))
                    self.hit_enemy(e, b.dmg, b.vx, b.vy, b)
                    if b.effect == "dumdum":
                        self.dumdum_hit(e, b)
                    if k == "plasma":
                        self.explode(b.x, b.y, b.blast, b.dmg * 0.4, (120, 255, 90), hurt_player=False, quiet=True, small=True, dtype=b.dtype)
                    if b.pierce <= 0:
                        if k not in WP.SPRAYS:
                            self.impact(b, b.x, b.y)
                        return False
                    b.pierce -= 1
        b.life -= dt
        if b.life <= 0:
            if k in ("grenade", "rocket", "plasma", "fireball", "nuke", "missile", "jet"):
                self.impact(b, b.x, b.y)
            elif k == "chem":
                if rnd.random() < 0.55:
                    self.add_gas(b.x, b.y, b.gas, b.vx, b.vy)
            elif k == "cryo":
                if rnd.random() < 0.12:
                    self.splat(b.x, b.y, (175, 210, 235), 0.1)
            elif k == "flame":
                if rnd.random() < 0.22:
                    self.hazards.append([b.x, b.y, 0.45, rnd.uniform(1.2, 2.0), "fire", b.burn])
                if rnd.random() < 0.12:
                    self.splat(b.x, b.y, (22, 16, 12), 0.12)
                self.add(Particle("smoke", b.x, b.y, b.z, b.vx * 0.2, b.vy * 0.2, 0.8, 0.9, (40, 34, 30), 0.25))
            return False
        return True

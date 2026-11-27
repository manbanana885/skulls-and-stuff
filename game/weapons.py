"""Procedural weapons and power-ups.

A weapon = archetype (base stats + projectile behaviour) + brand (stat leanings) + rarity
(number of modifiers) + random rolls + item level. Everything is derived from a seed.
"""
import random

import damage as DM

# ---------------------------------------------------------------- archetypes
DEFAULTS = dict(pellets=1, life=0.9, pierce=0, blast=0.0, burn=0.0, bounce=0, shock=0, homing=0, slow=0,
                lifesteal=0, twin=False, kick=1.5, spread=0.03, speed=19.0, rad=None, gas=0.0, chill=0.0, saw_bounces=None,
                heavy=1.0, spinup=0.0, wallpierce=0, salvo=None, chain=0, arc_range=0.0, cone=0.0, acid=0, ammo=None)

ARCH = {
    "pistol":       dict(label="Pistol", dmg=1.7, rate=5.0, spread=0.03, mag=12, reload=0.9, proj="bullet",
                         kick=1.2, sound="shot_pistol", color=(255, 215, 130), weight=10),
    "revolver":     dict(label="Revolver", dmg=4.6, rate=2.2, spread=0.015, speed=24, mag=6, reload=1.4, proj="bullet",
                         pierce=1, kick=4, sound="shot_revolver", color=(255, 205, 110), weight=7),
    "smg":          dict(label="SMG", dmg=0.85, rate=13, spread=0.09, speed=18, mag=36, reload=1.3, proj="bullet",
                         kick=1.0, sound="shot_smg", color=(255, 225, 150), weight=9),
    "shotgun":      dict(label="Shotgun", dmg=0.95, rate=1.6, spread=0.32, pellets=8, speed=16, life=0.42, mag=6,
                         reload=1.6, proj="pellet", kick=6, sound="shot_shotgun", color=(255, 195, 95), weight=9),
    "carbine":      dict(label="Carbine", dmg=1.25, rate=8, spread=0.035, speed=20, mag=25, reload=1.2, proj="bullet",
                         kick=1.5, sound="shot", color=(120, 230, 255), weight=8),
    "assault":      dict(label="Assault Rifle", dmg=1.35, rate=10, spread=0.06, speed=21, mag=32, reload=1.5,
                         proj="bullet", kick=1.8, sound="shot_assault", color=(255, 215, 130), weight=8),
    "sniper":       dict(label="High-Power Rifle", dmg=9.5, rate=1.0, spread=0.0, speed=42, life=0.8, mag=5, reload=2.0,
                         proj="slug", pierce=4, kick=7, sound="shot_sniper", color=(255, 245, 210), weight=5),
    "grenade":      dict(label="Grenade Launcher", dmg=8, rate=1.4, spread=0.04, speed=9, life=1.5, mag=6, reload=2.2,
                         proj="grenade", blast=1.8, kick=4, sound="shot_grenade", color=(255, 170, 60), weight=4),
    "rocket":       dict(label="Rocket Launcher", dmg=13, rate=0.9, spread=0.0, speed=6, life=2.5, mag=3, reload=2.4,
                         proj="rocket", blast=2.2, kick=6, sound="shot_rocket", color=(255, 150, 50), weight=3),
    "laser_pistol": dict(label="Laser Pistol", dmg=1.6, rate=6, spread=0.01, speed=32, mag=16, reload=1.0, proj="bolt",
                         kick=0.8, sound="shot_laser", color=(255, 60, 60), weight=6),
    "laser_rifle":  dict(label="Laser Rifle", dmg=1.25, rate=9, spread=0.0, speed=0, mag=30, reload=1.6, proj="beam",
                         pierce=99, kick=0.8, sound="shot_beam", color=(255, 50, 80), weight=5),
    "plasma":       dict(label="Plasma Gun", dmg=3.6, rate=3, spread=0.03, speed=9, life=1.5, mag=14, reload=1.6,
                         proj="plasma", blast=0.9, pierce=2, kick=2.5, sound="shot_plasma", color=(120, 255, 90), weight=5),
    "tac_nuke":     dict(label="Tactical Nuke", dmg=32, rate=0.5, spread=0.0, speed=7, life=3.0, mag=1, reload=3.0, proj="nuke",
                         blast=2.0, rad=(2.0, 8.0, 7.0, 3.0), kick=10, sound="shot_nuke", color=(170, 255, 70), weight=2),
    "nuke":         dict(label="Nuke", dmg=70, rate=0.3, spread=0.0, speed=5.5, life=3.5, mag=1, reload=4.5, proj="nuke",
                         blast=4.0, rad=(4.0, 14.0, 10.0, 5.0), kick=16, sound="shot_nuke", color=(200, 255, 60), weight=1),
    "saw":          dict(label="Saw Launcher", dmg=4.0, rate=2.2, spread=0.02, speed=13, life=4.0, mag=6, reload=1.8, proj="saw",
                         pierce=99, saw_bounces=(3, 6), kick=2, sound="shot_saw", color=(215, 215, 225), weight=5),
    "chem":         dict(label="Chem Sprayer", dmg=0.25, rate=22, spread=0.18, speed=10, life=0.6, mag=90, reload=2.0, proj="chem",
                         pierce=99, gas=5.0, kick=0.3, sound=None, color=(190, 235, 40), weight=4),
    "cryo":         dict(label="Cryo Thrower", dmg=0.22, rate=24, spread=0.15, speed=12, life=0.65, mag=90, reload=2.0, proj="cryo",
                         pierce=99, slow=1, chill=0.05, kick=0.3, sound=None, color=(140, 210, 255), weight=4),
    # heavy weapons: slow you down while equipped, hit much harder
    "chaingun":     dict(label="Chaingun", dmg=2.1, rate=17, spread=0.085, speed=22, mag=150, reload=3.2, proj="bullet",
                         kick=1.3, heavy=0.62, spinup=0.7, sound="shot_chaingun", color=(255, 200, 110), weight=3),
    "railgun":      dict(label="Railgun", dmg=34, rate=0.55, spread=0.0, speed=60, life=0.6, mag=4, reload=2.6, proj="rail",
                         pierce=99, wallpierce=5, kick=10, heavy=0.6, sound="shot_railgun", color=(110, 220, 255), weight=3),
    # barrage launcher: one trigger pull = a rippling salvo of 4-16 small homing missiles
    "barrage":      dict(label="Barrage Launcher", dmg=4.0, rate=0.6, spread=0.2, speed=7, life=2.2, mag=3, reload=3.0, proj="missile",
                         blast=1.4, homing=0.7, salvo=(4, 16), kick=2.5, heavy=0.6, sound="shot_barrage", color=(255, 165, 70), weight=3),
    # coil guns: instant lightning that ricochets off walls and chains between monsters
    "coil_pistol":  dict(label="Coil Pistol", dmg=2.4, rate=3.6, spread=0.04, speed=0, mag=12, reload=1.1, proj="arc",
                         chain=2, bounce=1, arc_range=8.0, kick=1.0, sound="shot_coil", color=(150, 190, 255), weight=6),
    "coil_rifle":   dict(label="Coil Rifle", dmg=1.5, rate=7, spread=0.05, speed=0, mag=28, reload=1.5, proj="arc",
                         chain=3, bounce=2, arc_range=11.0, kick=1.2, sound="shot_coil", color=(140, 175, 255), weight=5),
    "coil_heavy":   dict(label="Storm Coil", dmg=3.2, rate=5.5, spread=0.06, speed=0, mag=60, reload=2.8, proj="arc",
                         chain=6, bounce=3, arc_range=13.0, kick=2.0, heavy=0.62, sound="shot_coil", color=(170, 150, 255), weight=3),
    # microwave emitter: expanding rings that sweep a cone and cook everything in it
    "microwave":    dict(label="Microwave Emitter", dmg=2.6, rate=3.2, spread=0.0, speed=8.5, life=0.75, mag=18, reload=1.7,
                         proj="wave", pierce=99, cone=0.5, burn=0.5, kick=1.0, sound="shot_microwave", color=(235, 130, 255), weight=5),
    "flamer":       dict(label="Flamethrower", dmg=0.42, rate=24, spread=0.15, speed=12, life=0.65, mag=90, reload=2.0,
                         proj="flame", pierce=99, burn=1.2, kick=0.4, sound=None, color=(255, 140, 40), weight=4),
}

# muzzle (forward distance, height) in the torso model - must match blender/build_assets.py GUNS
MUZZLE = {
    "pistol": (0.67, 1.18), "revolver": (0.79, 1.185), "smg": (0.8, 1.14), "shotgun": (0.99, 1.17),
    "carbine": (1.01, 1.14), "assault": (1.09, 1.15), "sniper": (1.35, 1.16), "grenade": (0.87, 1.17),
    "rocket": (0.88, 1.33), "laser_pistol": (0.73, 1.18), "laser_rifle": (1.1, 1.14), "plasma": (0.98, 1.13),
    "flamer": (1.0, 1.14), "tac_nuke": (0.76, 1.33), "nuke": (1.07, 1.36), "saw": (0.86, 1.23), "chem": (0.98, 1.14),
    "cryo": (0.98, 1.14), "chaingun": (1.2, 1.09), "railgun": (1.47, 1.15),
    "barrage": (0.98, 1.2), "coil_pistol": (0.74, 1.18), "coil_rifle": (1.12, 1.14), "coil_heavy": (1.22, 1.1),
    "microwave": (0.98, 1.13),
}
SHOULDER = {"rocket": 0.14, "tac_nuke": 0.14, "nuke": 0.15}   # sideways offset to the right shoulder

RARITY = [("Common", (205, 205, 205)), ("Uncommon", (80, 225, 95)), ("Rare", (70, 145, 255)),
          ("Epic", (195, 85, 255)), ("Legendary", (255, 155, 30))]

BRANDS = {
    "Ossuary Arms": dict(dmg=1.15, rate=0.92),
    "Necrotek": dict(rate=1.15, spread=1.2),
    "Hexforge": dict(speed=1.25, reload=0.9),
    "Marrow & Sons": dict(mag=1.35, dmg=0.95),
    "Cadaver Dynamics": dict(reload=0.75),
    "Graveline": dict(spread=0.6, dmg=1.05),
}

NO_PROJ_SPEED = {"beam", "arc"}
EXPLOSIVE = {"grenade", "rocket", "tac_nuke", "nuke", "barrage"}
SPRAYS = {"flame", "chem", "cryo"}


def _m(key, adj, desc, fn, ok=lambda a: True):
    return dict(key=key, adj=adj, desc=desc, fn=fn, ok=ok)


def _mul(**kw):
    def f(st):
        for k, v in kw.items():
            st[k] *= v
    return f


def _add(**kw):
    def f(st):
        for k, v in kw.items():
            st[k] += v
    return f


def _set_twin(st):
    st["twin"] = True


def _penetrating(st):
    st["pierce"] += 2
    st["ammo"] = "pen"


def _expanding(st):
    st["ammo"] = "exp"


BULLETS = ("bullet", "pellet", "slug")
AMMO_MODS = {"penetrating", "expanding"}


def _explosive(st):
    st["blast"] = max(st["blast"], 0.75)
    st["dmg"] *= 0.9


MODS = [
    _m("incendiary", "Incendiary", "Sets targets ablaze", _add(burn=1.2)),
    _m("explosive", "Explosive", "Rounds explode on impact", _explosive, lambda a: ARCH[a]["proj"] not in SPRAYS | {"beam", "wave"} and a not in EXPLOSIVE),
    _m("piercing", "Piercing", "Punches through 2 more targets", _add(pierce=2),
       lambda a: a not in EXPLOSIVE and ARCH[a]["proj"] not in SPRAYS | {"beam", "saw", "rail", "arc", "wave"} | set(BULLETS)),
    _m("penetrating", "Penetrating Core", "Pierces 2 more; x1.35 vs robots & constructs, x0.8 vs undead & mutants",
       _penetrating, lambda a: ARCH[a]["proj"] in BULLETS),
    _m("expanding", "Expanding", "x1.35 vs undead & mutants, x0.75 vs robots & constructs",
       _expanding, lambda a: ARCH[a]["proj"] in BULLETS),
    _m("ricochet", "Ricochet", "Bounces off walls", _add(bounce=1), lambda a: ARCH[a]["proj"] in ("bullet", "pellet", "bolt", "slug", "plasma", "saw", "arc")),
    _m("twin", "Twin-Linked", "Fires a second parallel shot", _set_twin, lambda a: ARCH[a]["proj"] not in SPRAYS | {"nuke", "missile"}),
    _m("rapid", "Rapid", "+35% fire rate", _mul(rate=1.35, dmg=0.88)),
    _m("heavy", "Heavy", "+45% damage, slower", _mul(dmg=1.45, rate=0.85, kick=1.5)),
    _m("precise", "Precise", "Halved spread", _mul(spread=0.5), lambda a: ARCH[a]["spread"] > 0.02),
    _m("drum", "Drum-Fed", "+75% magazine", _mul(mag=1.75)),
    _m("quick", "Quickload", "40% faster reloads", _mul(reload=0.6)),
    _m("vampiric", "Vampiric", "Heals 3 integrity per kill", _add(lifesteal=3)),
    _m("shock", "Shocking", "Arcs to nearby enemies", _add(shock=1), lambda a: ARCH[a]["proj"] != "arc"),
    _m("seeking", "Seeking", "Projectiles home in", _add(homing=1), lambda a: ARCH[a]["proj"] not in SPRAYS | {"beam", "saw", "rail", "arc", "wave"}),
    _m("velocity", "High-Velocity", "+50% projectile speed", _mul(speed=1.5), lambda a: ARCH[a]["proj"] not in SPRAYS | {"beam", "arc"}),
    _m("cryo", "Cryo", "Chills and slows targets", _add(slow=1)),
    _m("acid", "Acid-Augmented", "Acid-augmented projectiles: hits leave corrosive puddles", _add(acid=1),
       lambda a: ARCH[a]["proj"] in ("bullet", "pellet", "slug", "bolt", "rocket", "grenade", "missile", "saw", "plasma", "rail")),
]
MOD_BY_KEY = {m["key"]: m for m in MODS}

UNIQUE_NAMES = ["Bonesaw", "Marrowmaker", "Gravewhisper", "Last Rites", "The Ossifier", "Hellmouth", "Cadaver Kiss",
                "Widowmaker", "Coffin Nail", "Requiem", "Ribcracker", "Dead Man's Hand", "Ashen Choir",
                "Neon Reaper", "Skullsplitter", "Black Sabbath Engine", "Night Drive", "The Undertaker"]


class Weapon:
    def __init__(self, arch, rarity=0, level=1, seed=None):
        rng = random.Random(seed)
        self.seed = seed
        self.arch = arch
        self.rarity = rarity
        self.level = level
        st = dict(DEFAULTS)
        st.update(ARCH[arch])
        st["dtype"] = DM.WEAPON_TYPE.get(arch, "kinetic")
        for k in ("dmg", "rate", "mag", "reload", "speed"):
            st[k] *= rng.uniform(0.88, 1.12)
        st["spread"] *= rng.uniform(0.8, 1.2)
        if st["salvo"]:
            st["salvo"] = rng.randint(*st["salvo"])
            st["dmg"] *= (10.0 / st["salvo"]) ** 0.35     # small salvos hit a little harder per missile
        self.brand = rng.choice(list(BRANDS))
        for k, v in BRANDS[self.brand].items():
            st[k] *= v
        pool = [m for m in MODS if m["ok"](arch)]
        rng.shuffle(pool)
        n_mods = min(rarity, 3)
        self.mods = []
        for m in pool:                       # Penetrating Core and Expanding rounds are mutually exclusive
            if len(self.mods) >= n_mods:
                break
            if m["key"] in AMMO_MODS and any(o["key"] in AMMO_MODS for o in self.mods):
                continue
            self.mods.append(m)
        for m in self.mods:
            m["fn"](st)
        st["dmg"] *= (1 + 0.07 * rarity) * (1.35 if rarity == 4 else 1.0) * (1 + 0.2 * (level - 1))
        st["mag"] = max(1, int(round(st["mag"])))
        self.st = st
        if rarity == 4:
            self.name = '"%s"' % rng.choice(UNIQUE_NAMES)
        else:
            adj = self.mods[0]["adj"] + " " if self.mods else ""
            self.name = "%s%s" % (adj, st["label"])
        self.ammo = st["mag"]
        self.reload_t = 0.0
        self.cd = 0.0

    # ---- derived info
    @property
    def color(self):
        return RARITY[self.rarity][1]

    @property
    def rarity_name(self):
        return RARITY[self.rarity][0]

    def projectiles_per_shot(self):
        return self.st["pellets"] * (2 if self.st["twin"] else 1) * (self.st["salvo"] or 1)

    def dps(self):
        st = self.st
        per_shot = st["dmg"] * self.projectiles_per_shot() * (1 + st["blast"] * 0.6) * (1 + st["burn"] * 0.3)
        if st["rad"]:
            per_shot += st["rad"][1] * st["rad"][2] * 0.5
        if st["saw_bounces"]:
            per_shot *= 2.5
        if st["chain"]:
            per_shot *= 1 + st["chain"] * 0.55
        if st["proj"] == "wave":
            per_shot *= 2.0
        cycle = st["mag"] / st["rate"] + st["reload"]
        return per_shot * st["mag"] / cycle

    def card_lines(self):
        st = self.st
        dmg = "%.1f" % st["dmg"] + (" x%d" % self.projectiles_per_shot() if self.projectiles_per_shot() > 1 else "")
        lines = [("DMG", dmg), ("RATE", "%.1f/s" % st["rate"]), ("MAG", "%d" % st["mag"]),
                 ("RELOAD", "%.1fs" % st["reload"]), ("DPS", "%.0f" % self.dps())]
        return lines

    def update(self, dt, infinite=False):
        self.cd = max(0.0, self.cd - dt)
        if self.reload_t > 0:
            self.reload_t -= dt
            if self.reload_t <= 0:
                self.ammo = self.st["mag"]
                return "reloaded"
        return None

    def start_reload(self):
        if self.reload_t <= 0 and self.ammo < self.st["mag"]:
            self.reload_t = self.st["reload"]
            return True
        return False


def roll_rarity(rng, level, bonus=0):
    w = [60, 26, 10, 3.5, 0.8]
    shift = min(level - 1, 8) * 0.35 + bonus
    for i in range(len(w)):
        w[i] *= (1 + shift) ** (i * 0.8)
    r = rng.uniform(0, sum(w))
    for i, wi in enumerate(w):
        r -= wi
        if r <= 0:
            return min(4, i)
    return 0


def generate(level, rng=None, bonus=0, arch=None, rarity=None):
    rng = rng or random.Random()
    if arch is None:
        archs = list(ARCH)
        arch = rng.choices(archs, weights=[ARCH[a]["weight"] for a in archs])[0]
    if rarity is None:
        rarity = roll_rarity(rng, level, bonus)
    return Weapon(arch, rarity, level, rng.randrange(1 << 30))


# ---------------------------------------------------------------- power-ups
BUFFS = {
    # kind: (title, colour, description template, magnitude range, duration range or None=permanent, weight)
    "overdrive": ("OVERDRIVE", (255, 200, 60), "fire rate x{m:.1f}", (1.5, 2.2), (12, 20), 10),
    "berserk":   ("BERSERK", (255, 60, 60), "damage x{m:.1f}", (1.5, 2.5), (10, 18), 9),
    "haste":     ("HASTE", (80, 255, 200), "move speed x{m:.1f}", (1.3, 1.6), (12, 20), 9),
    "aegis":     ("AEGIS", (120, 160, 255), "damage taken x{m:.1f}", (0.3, 0.55), (10, 18), 8),
    "leech":     ("BLOOD PACT", (220, 30, 70), "+{m:.0f} integrity per kill", (2, 5), (15, 25), 7),
    "multishot": ("MULTISHOT", (255, 120, 255), "+{m:.0f} projectiles", (1, 2.99), (10, 16), 6),
    "infinite":  ("BOTTOMLESS", (240, 240, 255), "no reloads", (1, 1), (10, 15), 6),
    "graft":     ("BONE GRAFT", (230, 220, 190), "+{m:.0f} max integrity", (10, 20), None, 4),
    "calibrate": ("CALIBRATION", (255, 180, 80), "+{m:.0f}% damage, permanently", (5, 10), None, 4),
}


class Buff:
    def __init__(self, kind, mag, dur):
        self.kind, self.mag, self.dur = kind, mag, dur
        title, self.color, tmpl, _, _, _ = BUFFS[kind]
        self.title = title
        self.desc = tmpl.format(m=int(mag) if kind == "multishot" else mag)
        if kind == "multishot":
            self.mag = int(mag)

    @property
    def permanent(self):
        return self.dur is None


def roll_buff(rng=None, level=1):
    rng = rng or random.Random()
    kinds = list(BUFFS)
    kind = rng.choices(kinds, weights=[BUFFS[k][5] for k in kinds])[0]
    _, _, _, (a, b), dur, _ = BUFFS[kind]
    lv = min(1.0, (level - 1) * 0.12)
    mag = a + (b - a) * min(1.0, rng.random() * 0.8 + lv * 0.4)
    d = None if dur is None else rng.uniform(*dur)
    return Buff(kind, mag, d)

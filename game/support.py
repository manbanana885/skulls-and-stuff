"""Modules: gadgets a player equips (3 slots + a backpack, managed from the pause menu).

  sawbot    - Buzzsaw Orbiter: circles you and shreds whatever it passes through
  shield    - Arc Shield: a partial ring that orbits you and swallows enemy projectiles
  medbot    - Medbot: trails behind you and slowly patches you up
  gunbot    - Gun Drone: hovers beside you and shoots at monsters
  gunarm    - Gun Arm: a pipe arm on your back that fires your stowed gun at its own targets
  leech     - Bile Leech: shoulder pod whose tongues latch onto monsters and drain them into you
  core      - Retaliation Core: when you're hit it answers with a blast / magnetic pulse / lightning storm
  skull     - Skull Familiar: a soul-fire skull that dive-bombs monsters, explodes, and reforms
  decoy     - Decoy Projector: when you're swarmed it throws out a hologram of you that monsters chase
  mines     - Mine Spine: sows proximity mines behind you as you move
  aura      - Aura Emitter: a ring that burns / chills / irradiates everything near you
  battery   - Bone Battery: kills charge it; full, it either revives you once or detonates a nova
  autoloader- Autoloader: faster reloads, and reloads your stowed gun in the background
  jets      - Jump Jets: dash (SHIFT / LB) with a cooldown, optionally leaving a burning trail
  tether    - Tether Beam: a damaging beam to your partner (healing you both) or to its own satellite
  magnet    - Loot Magnet: pulls health and power-ups to you
  mgturret  - MG Turret: deploy (F / B) a machine-gun tripod; undeploy by pressing again next to it
  mortar    - Mortar Turret: deploy a mortar that lobs shells over walls
  Deployed turrets draw monsters, take damage, and go up like a tactical nuke when destroyed.

Every item rolls its own parameters (speed, strength, size, reach...) from a seed; rarity biases the rolls upward.
"""
import math
import random

import weapons as WP

# kind -> label, colour, params: name -> (lo, hi, card label, format). Rolls lerp lo..hi; lo > hi means "low is good".
KINDS = {
    "sawbot": dict(label="Buzzsaw Orbiter", color=(255, 190, 70), weight=10, params={
        "dmg":    (2.6, 6.5, "DMG", "%.1f"),
        "spin":   (2.0, 4.6, "SPIN", "%.1f/s"),
        "orbit":  (1.0, 1.9, "ORBIT", "%.1f m"),
        "size":   (0.85, 1.35, "SIZE", "x%.2f"),
    }),
    "shield": dict(label="Arc Shield", color=(110, 200, 255), weight=9, params={
        "arc":      (0.75, 1.6, "ARC", "%d deg"),
        "spin":     (0.9, 2.6, "SPIN", "%.1f/s"),
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
    "gunarm": dict(label="Gun Arm", color=(200, 200, 210), weight=7, params={
        "rate":   (0.45, 0.8, "FIRE RATE", "x%.2f"),
        "track":  (3.0, 8.0, "TRACKING", "%.1f/s"),
        "range":  (6.0, 10.0, "RANGE", "%.1f m"),
        "size":   (0.85, 1.2, "REACH", "x%.2f"),
    }),
    "leech": dict(label="Bile Leech", color=(180, 230, 60), weight=8, params={
        "drain":   (1.5, 4.0, "DRAIN", "%.1f/s"),
        "heal":    (0.3, 0.8, "HEALS", "%.0f%%"),
        "range":   (2.5, 4.5, "RANGE", "%.1f m"),
        "latches": (1, 3.49, "TONGUES", "%d"),
    }),
    "core": dict(label="Retaliation Core", color=(255, 150, 80), weight=8, params={
        "dmg":      (8, 20, "DMG", "%.0f"),
        "radius":   (2.5, 4.5, "RADIUS", "%.1f m"),
        "cooldown": (9.0, 3.0, "COOLDOWN", "%.1fs"),
    }),
    "skull": dict(label="Skull Familiar", color=(110, 220, 255), weight=7, params={
        "dmg":      (6, 14, "DMG", "%.0f"),
        "radius":   (1.0, 1.7, "BLAST", "%.1f m"),
        "cooldown": (5.0, 2.0, "REFORM", "%.1fs"),
        "speed":    (8.0, 15.0, "SPEED", "%.0f"),
        "range":    (6.0, 9.0, "RANGE", "%.1f m"),
    }),
    "decoy": dict(label="Decoy Projector", color=(90, 230, 255), weight=6, params={
        "duration": (3.0, 6.0, "DURATION", "%.1fs"),
        "cooldown": (14.0, 6.0, "COOLDOWN", "%.1fs"),
        "trigger":  (5.49, 2.0, "TRIGGERS AT", "%d near"),
    }),
    "mines": dict(label="Mine Spine", color=(255, 90, 60), weight=7, params={
        "dmg":     (8, 18, "DMG", "%.0f"),
        "radius":  (1.2, 2.0, "BLAST", "%.1f m"),
        "spacing": (3.0, 1.4, "SPACING", "%.1f m"),
        "max":     (3, 6.49, "MINES", "%d"),
    }),
    "aura": dict(label="Aura Emitter", color=(255, 120, 60), weight=7, params={
        "dps":    (2.0, 5.0, "DPS", "%.1f"),
        "radius": (1.5, 2.6, "RADIUS", "%.1f m"),
    }),
    "battery": dict(label="Bone Battery", color=(230, 220, 190), weight=6, params={
        "capacity": (35, 15, "CHARGE", "%d kills"),
        "dmg":      (20, 45, "NOVA DMG", "%.0f"),
        "heal":     (0.3, 0.6, "REVIVE HP", "%.0f%%"),
    }),
    "autoloader": dict(label="Autoloader", color=(240, 200, 90), weight=7, params={
        "reload": (0.85, 0.55, "RELOAD TIME", "x%.2f"),
        "stow":   (1.6, 0.8, "STOWED RELOAD", "x%.2f"),
    }),
    "jets": dict(label="Jump Jets", color=(255, 160, 60), weight=7, params={
        "dist":     (2.5, 4.5, "DASH", "%.1f m"),
        "cooldown": (4.0, 1.5, "COOLDOWN", "%.1fs"),
        "burn":     (0.0, 8.0, "TRAIL DMG", "%.0f"),
    }),
    "tether": dict(label="Tether Beam", color=(80, 255, 220), weight=6, params={
        "dps":    (3.0, 7.0, "BEAM DPS", "%.1f"),
        "length": (2.0, 3.5, "LENGTH", "%.1f m"),
        "spin":   (0.8, 2.0, "SPIN", "%.1f/s"),
        "heal":   (0.0, 0.6, "CO-OP HEAL", "%.1f/s"),
    }),
    "magnet": dict(label="Loot Magnet", color=(200, 80, 80), weight=6, params={
        "radius": (3.0, 7.0, "RADIUS", "%.1f m"),
        "pull":   (3.0, 8.0, "PULL", "%.1f"),
    }),
    "mgturret": dict(label="MG Turret", color=(170, 180, 110), weight=7, params={
        "dmg":     (1.2, 2.6, "DMG", "%.1f"),
        "rate":    (5.0, 10.0, "RATE", "%.1f/s"),
        "range":   (6.0, 10.0, "RANGE", "%.1f m"),
        "hp":      (60, 140, "ARMOR", "%d"),
        "rebuild": (25.0, 10.0, "REBUILD", "%.0fs"),
    }),
    "mortar": dict(label="Mortar Turret", color=(170, 180, 110), weight=6, params={
        "dmg":     (12, 26, "DMG", "%.0f"),
        "blast":   (1.4, 2.2, "BLAST", "%.1f m"),
        "rate":    (0.4, 0.9, "RATE", "%.2f/s"),
        "range":   (9.0, 14.0, "RANGE", "%.1f m"),
        "hp":      (50, 120, "ARMOR", "%d"),
        "rebuild": (30.0, 12.0, "REBUILD", "%.0fs"),
    }),
}
TURRETS = {"mgturret", "mortar"}
# modules whose flavour is rolled, not just their numbers
ELEMENTS = {"core": ("blast", "magnet", "storm"), "aura": ("burn", "chill", "rad"), "battery": ("revive", "nova")}
ELEMENT_LABEL = {"blast": "Blast Core", "magnet": "Magnet Core", "storm": "Storm Core",
                 "burn": "Inferno Aura", "chill": "Frost Aura", "rad": "Rad Aura",
                 "revive": "Bone Battery", "nova": "Nova Battery"}
ELEMENT_COLOR = {"blast": (255, 150, 60), "magnet": (130, 170, 255), "storm": (170, 150, 255),
                 "burn": (255, 110, 40), "chill": (140, 210, 255), "rad": (150, 255, 70)}
PCT = {"heal"}                 # shown as percentages for these kinds
INT = {"capacity", "latches", "trigger", "max", "hp"}
# the adjective an item gets from its best roll
ADJ = {
    "sawbot": {"dmg": "Serrated", "spin": "Whirling", "orbit": "Wide-Orbit", "size": "Hulking"},
    "shield": {"arc": "Broad", "spin": "Spinning", "capacity": "Fortified", "recharge": "Rapid-Cycle", "size": "Wide"},
    "medbot": {"heal": "Surgical", "reach": "Long-Range", "speed": "Nimble", "size": "Field"},
    "gunbot": {"dmg": "Heavy", "rate": "Rapid", "range": "Long-Range", "speed": "Agile", "spread": "Precise", "size": "Armored"},
    "gunarm": {"rate": "Rapid", "track": "Hunting", "range": "Long-Range", "size": "Extended"},
    "leech": {"drain": "Ravenous", "heal": "Bloated", "range": "Long-Tongued", "latches": "Hydra"},
    "core": {"dmg": "Volatile", "radius": "Wide", "cooldown": "Hair-Trigger"},
    "skull": {"dmg": "Wrathful", "radius": "Bursting", "cooldown": "Restless", "speed": "Screaming", "range": "Hunting"},
    "decoy": {"duration": "Lingering", "cooldown": "Quick", "trigger": "Paranoid"},
    "mines": {"dmg": "Heavy", "radius": "Wide", "spacing": "Prolific", "max": "Stocked"},
    "aura": {"dps": "Searing", "radius": "Wide"},
    "battery": {"capacity": "Hungry", "dmg": "Overcharged", "heal": "Merciful"},
    "autoloader": {"reload": "Rapid", "stow": "Diligent"},
    "jets": {"dist": "Long", "cooldown": "Twitchy", "burn": "Scorching"},
    "tether": {"dps": "Searing", "length": "Long", "spin": "Spinning", "heal": "Kindred"},
    "magnet": {"radius": "Strong", "pull": "Greedy"},
    "mgturret": {"dmg": "Heavy", "rate": "Rapid", "range": "Long-Range", "hp": "Armored", "rebuild": "Quick-Build"},
    "mortar": {"dmg": "Heavy", "blast": "High-Yield", "rate": "Rapid", "range": "Long-Range", "hp": "Armored", "rebuild": "Quick-Build"},
}
UNIQUE = {"sawbot": ["Mr. Whirly", "The Lawnmower", "Grinder Prime"], "shield": ["The Umbrella", "Halo of Saint Rivet", "Bulwark-9"],
          "medbot": ["Nurse Ratchet", "Dr. Bolts", "Saint Gauze"], "gunbot": ["Little Buddy", "The Wingman", "Peacekeeper Mk.0"],
          "gunarm": ["Third Hand", "The Octopus", "Second Opinion"], "leech": ["Mother Tick", "The Sommelier", "Thirsty Boy"],
          "core": ["Spite", "Grudge Engine", "Payback"], "skull": ["Yorick", "Old Smokey", "Ghost Rider"],
          "decoy": ["Doppelganger", "Mirror Man", "Fetch"], "mines": ["Breadcrumbs", "Party Favors", "The Gardener"],
          "aura": ["Halo of Ruin", "Personal Space", "Hotbox"], "battery": ["Lazarus Cell", "Second Wind", "Phylactery"],
          "autoloader": ["Busy Hands", "The Butler", "Quartermaster"], "jets": ["Rocket Boots", "Heel Burners", "Quickfoot"],
          "tether": ["Umbilical", "Red String", "Leash"], "magnet": ["Sticky Fingers", "Gravity Well", "The Collector"],
          "mgturret": ["Sentry Gun", "The Doorman", "Tripod Tim"], "mortar": ["Big Bertha", "Rainmaker", "Thunder Pot"]}
SCALED = {"dmg", "heal", "capacity", "drain", "dps", "burn", "hp"}     # grows with item level
NOT_SCALED = {("battery", "capacity"), ("battery", "heal"), ("leech", "heal"), ("tether", "heal")}


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
            if name in SCALED and (kind, name) not in NOT_SCALED:
                v *= lv
            if name in INT:
                v = int(round(v)) if name != "trigger" else int(v)
            self.p[name] = v
        self.p.setdefault("size", 1.0)
        self.p["capacity"] = int(round(self.p.get("capacity", 0)))
        self.elem = rng.choice(ELEMENTS[kind]) if kind in ELEMENTS else None
        if rarity >= 4:
            self.name = '"%s"' % rng.choice(UNIQUE[kind])
        else:
            best = max((n for n in rolls if n != "size" or len(rolls) < 2), key=lambda n: rolls[n])
            self.name = "%s %s" % (ADJ[kind][best], K["label"]) if rarity else K["label"]
        self.label = ELEMENT_LABEL.get(self.elem, K["label"])
        if self.elem and rarity < 4:
            self.name = self.name.replace(K["label"], self.label)
        self.tint = ELEMENT_COLOR.get(self.elem, K["color"])
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
        self.charge = self.p.get("capacity", 0) if kind == "shield" else 0
        self.last_hp = None
        self.state = "idle"
        self.latched = []          # leech: [enemy, grow 0..1]
        self.mines = []            # mine spine: [x, y, armed_in]
        self.walked = 0.0
        self.decoy = None
        self.trail_t = 0.0
        self.trail_hit = set()
        self.proxy = None
        self.sat = (0.0, 0.0)      # tether satellite
        self.beam = None
        self.stow_t = 0.0
        self.tx = self.ty = 0.0
        self.deployed = None       # turret modules: the Turret in the world, or None while packed
        self.armor = self.p.get("hp", 0)
        self.rebuild_t = 0.0

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
            if self.kind == "battery" and name == ("dmg" if self.elem == "revive" else "heal"):
                continue
            v = self.p[name]
            if name == "arc":
                v = math.degrees(v)
            if name in PCT and self.kind in ("leech", "battery"):
                v *= 100
            out.append((lbl, fmt % v))
        return out

    def dtype(self):
        """Damage type this module deals (None for pure utility)."""
        if self.kind == "core":
            return "explosive" if self.elem == "blast" else "electrical"
        if self.kind == "aura":
            return {"burn": "fire", "chill": "cryo", "rad": "radiation"}[self.elem]
        if self.kind == "battery":
            return "explosive" if self.elem == "nova" else None
        return {"sawbot": "kinetic", "gunbot": "kinetic", "leech": "chemical", "skull": "explosive", "mines": "explosive",
                "mgturret": "kinetic", "mortar": "explosive",
                "jets": "fire", "tether": "electrical"}.get(self.kind)

    def blurb(self):
        return {"sawbot": "Orbits you, shredding monsters it touches",
                "shield": "Orbiting barrier that blocks enemy shots",
                "medbot": "Follows you and slowly repairs integrity",
                "gunbot": "Hovers beside you and fires at monsters",
                "gunarm": "Back-mounted arm that fires your stowed gun",
                "leech": "Tongues latch onto monsters and drain them into you",
                "core": {"blast": "When you're hit: an explosion around you",
                         "magnet": "When you're hit: shoves monsters away, reflects bullets",
                         "storm": "When you're hit: lightning chains through everything near"}.get(self.elem, ""),
                "skull": "Soul-fire skull dive-bombs monsters, then reforms",
                "decoy": "When swarmed, projects a hologram monsters chase",
                "mines": "Sows proximity mines behind you as you move",
                "aura": {"burn": "Sets everything near you on fire", "chill": "Chills and slows everything near you",
                         "rad": "Irradiates everything near you"}.get(self.elem, ""),
                "battery": {"revive": "Kills charge it; when full it saves you from death once",
                            "nova": "Kills charge it; when full it detonates a nova"}.get(self.elem, ""),
                "autoloader": "Faster reloads; reloads your stowed gun",
                "jets": "Dash with SHIFT / LB, leaving a burning trail",
                "tether": "Beam to your partner (or a satellite) that burns monsters",
                "magnet": "Pulls health and power-ups to you",
                "mgturret": "Deploy / pack up with F / B: auto-firing machine gun",
                "mortar": "Deploy / pack up with F / B: lobs shells over walls"}[self.kind]

    # ---- behaviour
    def attach(self, pl, slot=0):
        """Equip on a player. The slot spreads duplicates apart: orbiters start a third of a turn apart and the
        followers take different stations (right shoulder / left shoulder / behind)."""
        self.slot = slot
        self.ang = slot * math.tau / 3
        self.x, self.y = pl.x, pl.y
        self.hit_cd.clear()
        self.target = None
        self.latched = []
        self.mines = []
        self.decoy = None
        self.last_hp = pl.hp
        self.state = "idle"
        self.z = 1.4
        self.sat = (pl.x, pl.y)
        self.deployed = None       # a new sector: the turret comes along packed

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
            w.hit_enemy(e, self.p["dmg"] * pl.dmg_mult(), tvx, tvy, {"dtype": "kinetic"})
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
        side += (0.0, 0.9, -0.9)[getattr(self, "slot", 0) % 3]
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
        lat, back = ((0.95, 0.25), (-0.95, 0.25), (0.0, 1.0))[getattr(self, "slot", 0) % 3]
        lat = lat + wob * (1 if lat >= 0 else -1)
        tx, ty = pl.x + ay * lat - ax * back, pl.y - ax * lat - ay * back
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


    # ================================================================ worn modules hover at a station on your back
    def station(self, w, dt, pl, z=1.55):
        ax, ay = pl.aim
        lat = (0.45, -0.45, 0.0)[getattr(self, "slot", 0) % 3]
        back = 0.45 if getattr(self, "slot", 0) % 3 < 2 else 0.75
        tx, ty = pl.x - ax * back + ay * lat, pl.y - ay * back - ax * lat
        d = math.hypot(tx - self.x, ty - self.y)
        if d > 3:
            self.x, self.y = tx, ty
        else:
            k = min(1.0, dt * 14)
            self.x += (tx - self.x) * k
            self.y += (ty - self.y) * k
        self.z = z + math.sin(self.t * 2.6 + getattr(self, "slot", 0)) * 0.05

    def was_hit(self, pl):
        hit = self.last_hp is not None and pl.hp < self.last_hp - 0.5
        self.last_hp = pl.hp
        return hit

    # ---- gun arm
    def update_gunarm(self, w, dt, pl):
        from traps import los
        # bolted to the top corner of the backpack (right shoulder; a second arm takes the left, a third the middle)
        ax, ay = pl.aim
        side = (-1, 1, 0)[getattr(self, "slot", 0) % 3]
        self.x = pl.x - ax * 0.2 - ay * 0.13 * side
        self.y = pl.y - ay * 0.2 + ax * 0.13 * side
        self.z = 1.32 if side else 1.42
        self.side = side
        wp = pl.weapons[1 - pl.cur]
        if getattr(wp, "_arm_t", None) != w.time:         # the stowed gun cools down / reloads here (once per frame)
            wp._arm_t = w.time
            wp.update(dt)
        reach = 0.55 * self.p["size"]
        tg = self.target
        if tg is None or not tg.alive or math.hypot(tg.x - self.x, tg.y - self.y) > self.p["range"] + 1 \
                or not los(w.level, self.x, self.y, tg.x, tg.y):
            self.target = tg = next((e for e in targets(w, self.x, self.y, self.p["range"])
                                     if los(w.level, self.x, self.y, e.x, e.y)), None)
        want = math.atan2(tg.y - self.y, tg.x - self.x) if tg else math.atan2(pl.aim[1], pl.aim[0])
        cur = math.atan2(self.aim[1], self.aim[0])
        diff = (want - cur + math.pi) % math.tau - math.pi
        cur += max(-self.p["track"] * dt, min(self.p["track"] * dt, diff))
        self.aim = (math.cos(cur), math.sin(cur))
        out = 0.22 * (self.side if self.side else 0)          # reach out past the shoulder so the gun clears the body
        lx, ly = -ay, ax
        self.tx = self.x + lx * out + self.aim[0] * reach
        self.ty = self.y + ly * out + self.aim[1] * reach
        px = self.proxy
        if px is None or px.pl is not pl:
            px = self.proxy = ArmProxy(pl)
        mf = WP.MUZZLE[wp.arch][0]
        px.x, px.y = self.tx - self.aim[0] * mf, self.ty - self.aim[1] * mf
        px.aim = self.aim
        if px.salvo_q > 0:                               # barrage salvos ripple out of the arm too
            px.salvo_t -= dt
            while px.salvo_q > 0 and px.salvo_t <= 0:
                px.salvo_t += 0.05
                w.fire_missile(px, px.salvo_wp, px.salvo_n)
                px.salvo_q -= 1
                px.salvo_n += 1
        px.muzzle = max(0.0, px.muzzle - dt)
        if tg is None or abs(diff) > 0.2 or wp.reload_t > 0 or wp.cd > 0:
            return
        if wp.ammo <= 0:
            wp.start_reload()
            return
        wp.cd = 1.0 / (wp.st["rate"] * pl.mult("overdrive") * self.p["rate"])
        wp.ammo -= 1
        shooter = w._shooter
        w._shooter = px
        w.fire_weapon(px, wp)
        w._shooter = shooter
        self.muzzle = 0.06

    # ---- bile leech
    def update_leech(self, w, dt, pl):
        from traps import los
        self.station(w, dt, pl, 1.6)
        rng = self.p["range"]
        keep = []
        for e, grow in self.latched:
            if e.alive and math.hypot(e.x - pl.x, e.y - pl.y) < rng + 1.0:
                keep.append([e, min(1.0, grow + dt / 0.35)])
        self.latched = keep
        if len(self.latched) < self.p["latches"]:
            have = {id(e) for e, _ in self.latched}
            for e in targets(w, pl.x, pl.y, rng):
                if id(e) not in have and los(w.level, pl.x, pl.y, e.x, e.y):
                    self.latched.append([e, 0.0])
                    w.snd("tongue", e.x, e.y, 0.4)
                    break
        for e, grow in self.latched:
            if grow >= 1.0:
                amt = self.p["drain"] * pl.dmg_mult() * dt
                w.dot(e, amt, "chemical")
                if pl.alive:
                    pl.hp = min(pl.max_hp, pl.hp + amt * self.p["heal"])
                if random.random() < dt * 6:
                    from world import Particle
                    w.add(Particle("blood", e.x, e.y, 0.8, (pl.x - e.x) * 0.8, (pl.y - e.y) * 0.8, 1.0, 0.6,
                                   getattr(e, "blood", None) or (140, 20, 20), 3))

    # ---- retaliation core
    def update_core(self, w, dt, pl):
        from world import Particle
        self.station(w, dt, pl, 1.75)
        self.cd = max(0.0, self.cd - dt)
        if not self.was_hit(pl) or self.cd > 0:
            return
        self.cd = self.p["cooldown"]
        self.flash = 0.3
        R = self.p["radius"]
        dmg = self.p["dmg"] * pl.dmg_mult()
        col = ELEMENT_COLOR[self.elem]
        w.add(Particle("ring", pl.x, pl.y, 0.6, R * 1.1, 0, 0, 0.45, col, 0.15))
        if self.elem == "blast":
            w.explode(pl.x, pl.y, R * 0.75, dmg, col, hurt_player=False)
        elif self.elem == "magnet":
            for e in targets(w, pl.x, pl.y, R):
                d = math.hypot(e.x - pl.x, e.y - pl.y) or 1
                if hasattr(e, "vx") and not hasattr(e, "title"):
                    e.vx += (e.x - pl.x) / d * 14
                    e.vy += (e.y - pl.y) / d * 14
                w._shooter = pl
                w.hit_enemy(e, dmg * 0.4, (e.x - pl.x) * 10, (e.y - pl.y) * 10, {"dtype": "electrical"})
            for b in w.projs:                     # enemy shots get flung back at their owners
                if b.hostile and math.hypot(b.x - pl.x, b.y - pl.y) < R:
                    b.hostile = False
                    b.vx, b.vy = -b.vx * 1.3, -b.vy * 1.3
                    b.dmg = max(b.dmg, 4) * 2
                    b.owner = pl
                    b.hit = set()
                    b.color = col
            w.snd("magnet_pulse", pl.x, pl.y)
        else:
            from traps import los
            prev = (pl.x, pl.y, 1.0)
            pts = [prev]
            for e in targets(w, pl.x, pl.y, R)[:8]:
                if los(w.level, pl.x, pl.y, e.x, e.y):
                    w._shooter = pl
                    w.hit_enemy(e, dmg, e.x - pl.x, e.y - pl.y, {"dtype": "electrical"})
                    pts.append((e.x, e.y, 0.7))
            if len(pts) > 1:
                w.arcs.append([pts, 0.25, 0.25, col, 1.4])
            w.snd("zap", pl.x, pl.y, 0.9)

    # ---- skull familiar
    def update_skull(self, w, dt, pl):
        from world import Particle
        if self.state == "idle":
            self.station(w, dt, pl, 1.9)
            self.cd = max(0.0, self.cd - dt)
            if self.cd <= 0:
                tg = next(iter(targets(w, pl.x, pl.y, self.p["range"])), None)
                if tg is not None:
                    self.target = tg
                    self.state = "dive"
                    w.snd("skull_screech", self.x, self.y, 0.5)
        elif self.state == "dive":
            tg = self.target
            if tg is None or not tg.alive:
                tg = self.target = next(iter(targets(w, self.x, self.y, self.p["range"])), None)
            if tg is None:
                self.state = "idle"
                return
            dx, dy, dz = tg.x - self.x, tg.y - self.y, 0.6 - self.z
            d = math.sqrt(dx * dx + dy * dy + dz * dz) or 1
            step = self.p["speed"] * dt
            self.aim = (dx / d, dy / d)
            if d <= step + tg.r:
                w.explode(self.x, self.y, self.p["radius"], self.p["dmg"] * pl.dmg_mult(), (110, 220, 255), hurt_player=False,
                          quiet=True, small=True)
                self.state = "reform"
                self.cd = self.p["cooldown"]
                return
            self.x += dx / d * step
            self.y += dy / d * step
            self.z += dz / d * step
        else:
            self.cd -= dt
            if self.cd <= 0:
                self.state = "idle"
                self.x, self.y, self.z = pl.x, pl.y, 2.2
                for _ in range(12):
                    a = random.random() * math.tau
                    w.add(Particle("glow", pl.x, pl.y, 2.0, math.cos(a) * 2, math.sin(a) * 2, 0.5, 0.5, (110, 220, 255), 2))
                self.cd = 0.6
            return
        if random.random() < dt * 30:
            w.add(Particle("fire", self.x, self.y, self.z + 0.15, random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3),
                           random.uniform(0.6, 1.4), 0.3, (90, 200, 255), random.uniform(6, 11)))

    # ---- decoy projector
    def update_decoy(self, w, dt, pl):
        self.station(w, dt, pl, 1.6)
        self.cd = max(0.0, self.cd - dt)
        hit = self.was_hit(pl)
        if self.decoy is not None:
            self.decoy.t -= dt
            if self.decoy.t <= 0:
                if self.decoy in w.decoys:
                    w.decoys.remove(self.decoy)
                self.decoy = None
            return
        if self.cd > 0:
            return
        near = sum(1 for e in targets(w, pl.x, pl.y, 4.5))
        if near >= self.p["trigger"] or (hit and near):
            from world import resolve
            ax, ay = pl.aim
            x, y = resolve(w.level, pl.x - ax * 0.8, pl.y - ay * 0.8, 0.28)
            self.decoy = Decoy(x, y, pl, self.p["duration"])
            w.decoys.append(self.decoy)
            self.cd = self.p["cooldown"] + self.p["duration"]
            w.snd("decoy_on", x, y)

    # ---- mine spine
    def update_mines(self, w, dt, pl):
        self.station(w, dt, pl, 1.5)
        if self.last_hp is None:
            self.last_hp = 0
        mv = math.hypot(pl.x - getattr(self, "_px", pl.x), pl.y - getattr(self, "_py", pl.y))
        self._px, self._py = pl.x, pl.y
        self.walked += mv
        if self.walked >= self.p["spacing"]:
            self.walked = 0.0
            if len(self.mines) >= self.p["max"]:
                self.mines.pop(0)
            self.mines.append([pl.x, pl.y, 0.7])
            w.snd("tink", pl.x, pl.y, 0.4)
        keep = []
        for mn in self.mines:
            mn[2] -= dt
            boom = False
            if mn[2] <= 0:
                for e in targets(w, mn[0], mn[1], 1.3):
                    if math.hypot(e.x - mn[0], e.y - mn[1]) < 0.7 + e.r:
                        boom = True
                        break
            if boom:
                w.explode(mn[0], mn[1], self.p["radius"], self.p["dmg"] * pl.dmg_mult(), (255, 140, 60), hurt_player=False, small=True)
            else:
                keep.append(mn)
        self.mines = keep

    # ---- aura emitter
    def update_aura(self, w, dt, pl):
        from world import Particle
        self.station(w, dt, pl, 1.6)
        R = self.p["radius"]
        dps = self.p["dps"] * pl.dmg_mult()
        for e in targets(w, pl.x, pl.y, R + 0.5):
            if math.hypot(e.x - pl.x, e.y - pl.y) > R + e.r:
                continue
            if self.elem == "burn":
                if hasattr(e, "burn_dps"):
                    import damage as DM
                    e.burn = max(e.burn, 0.6)
                    e.burn_dps = max(e.burn_dps, dps * DM.mult(e, "fire"))
            elif self.elem == "chill":
                import damage as DM
                e.slow = max(getattr(e, "slow", 0.0), 0.3)
                w.dot(e, dps * 0.6 * dt, "cryo")
                if hasattr(e, "frozen"):
                    e.chill += dt * 0.15 * DM.mult(e, "cryo")
            else:
                w.dot(e, dps * dt, "radiation")
        if random.random() < dt * 14:
            a = random.random() * math.tau
            r = R * random.uniform(0.3, 1.0)
            kind = "fire" if self.elem == "burn" else "glow"
            w.add(Particle(kind, pl.x + math.cos(a) * r, pl.y + math.sin(a) * r, 0.05, 0, 0, random.uniform(0.6, 1.5), 0.5,
                           ELEMENT_COLOR[self.elem], random.uniform(6, 10) if kind == "fire" else 2))

    # ---- bone battery (charged from World.kill_enemy, revive handled in World.check_player_death)
    def update_battery(self, w, dt, pl):
        self.station(w, dt, pl, 1.7)
        cap = self.p["capacity"]
        if self.elem == "nova" and self.charge >= cap:
            self.charge = 0
            self.flash = 0.4
            w.explode(pl.x, pl.y, 3.2, self.p["dmg"] * pl.dmg_mult(), (230, 220, 190), hurt_player=False)
            w.message("BONE NOVA", (230, 220, 190))

    def on_kill(self, w):
        if self.kind == "battery" and self.charge < self.p["capacity"]:
            self.charge += 1
            if self.charge == self.p["capacity"] and self.elem == "revive":
                w.message("BONE BATTERY CHARGED - you will get back up once", (230, 220, 190))
                w.snd("power", self.x, self.y, 0.6)

    # ---- autoloader
    def update_autoloader(self, w, dt, pl):
        self.station(w, dt, pl, 1.45)
        wp = pl.weapon
        if wp.reload_t > 0:
            wp.reload_t -= dt * (1.0 / self.p["reload"] - 1.0)
        off = pl.weapons[1 - pl.cur]
        if off.ammo < off.st["mag"] and off.reload_t <= 0:
            self.stow_t += dt
            if self.stow_t >= off.st["reload"] * self.p["stow"]:
                self.stow_t = 0.0
                off.ammo = off.st["mag"]
                self.flash = 0.15
        else:
            self.stow_t = 0.0

    # ---- jump jets (dash triggered from Player.update)
    def ready(self):
        return self.kind == "jets" and self.cd <= 0

    def dash(self, w, pl, mx, my):
        from assets import screen_to_world_dir
        if abs(mx) + abs(my) > 0.1:
            dx, dy = screen_to_world_dir(mx, my)
        else:
            dx, dy = pl.aim
        v = self.p["dist"] * 10.0                  # knockback decays at 10/s, so this travels ~dist tiles
        pl.kbx, pl.kby = dx * v, dy * v
        pl.invuln = max(pl.invuln, 0.3)
        self.cd = self.p["cooldown"]
        self.trail_t = 0.3
        self.trail_hit = set()
        self.flash = 0.3
        w.snd("dash", pl.x, pl.y)

    def update_jets(self, w, dt, pl):
        from world import Particle
        self.station(w, dt, pl, 1.4)
        self.cd = max(0.0, self.cd - dt)
        if self.trail_t > 0:
            self.trail_t -= dt
            for _ in range(3):
                w.add(Particle("fire", pl.x + random.uniform(-0.2, 0.2), pl.y + random.uniform(-0.2, 0.2), 0.4, -pl.kbx * 0.05,
                               -pl.kby * 0.05, 0.5, 0.35, (255, 150, 50), random.uniform(8, 14)))
            if self.p["burn"] >= 1:
                for e in targets(w, pl.x, pl.y, 1.5):
                    if id(e) not in self.trail_hit and math.hypot(e.x - pl.x, e.y - pl.y) < 0.6 + e.r:
                        self.trail_hit.add(id(e))
                        w._shooter = pl
                        w.hit_enemy(e, self.p["burn"] * pl.dmg_mult(), pl.kbx, pl.kby, {"burn": 1.0, "dtype": "fire"})

    # ---- tether beam
    def update_tether(self, w, dt, pl):
        self.station(w, dt, pl, 1.3)
        partner = next((o for o in w.players if o is not pl and o.alive and math.hypot(o.x - pl.x, o.y - pl.y) < 9), None)
        if partner is not None:
            end = (partner.x, partner.y)
            if self.p["heal"] > 0:
                for q in (pl, partner):
                    q.hp = min(q.max_hp, q.hp + self.p["heal"] * dt)
        else:
            self.ang += self.p["spin"] * dt
            L = self.p["length"]
            end = (pl.x + math.cos(self.ang) * L, pl.y + math.sin(self.ang) * L)
        self.sat = end
        self.beam = (pl.x, pl.y, end[0], end[1], partner is not None)
        ax, ay = pl.x, pl.y
        bx, by = end
        sx, sy = bx - ax, by - ay
        ll = sx * sx + sy * sy or 1e-6
        for e in targets(w, (ax + bx) / 2, (ay + by) / 2, math.sqrt(ll) / 2 + 1.0):
            u = max(0.0, min(1.0, ((e.x - ax) * sx + (e.y - ay) * sy) / ll))
            if math.hypot(ax + sx * u - e.x, ay + sy * u - e.y) < e.r + 0.15:
                w.dot(e, self.p["dps"] * pl.dmg_mult() * dt, "electrical")
                if random.random() < dt * 10:
                    from world import Particle
                    w.add(Particle("spark", e.x, e.y, 0.8, random.uniform(-3, 3), random.uniform(-3, 3), 1, 0.25, (80, 255, 220), 2))

    # ---- loot magnet
    def update_magnet(self, w, dt, pl):
        self.station(w, dt, pl, 1.55)
        R = self.p["radius"]
        self.beam = []
        for lt in w.loot:
            if lt.kind not in ("health", "buff") or lt.z > 0.05:
                continue
            dx, dy = pl.x - lt.x, pl.y - lt.y
            d = math.hypot(dx, dy)
            if 0.2 < d < R:
                step = min(d, self.p["pull"] * dt)
                lt.x += dx / d * step
                lt.y += dy / d * step
                self.beam.append((lt.x, lt.y))


    # ---- deployable turrets (deploy / pack up from Player.update via toggle_turret)
    def update_mgturret(self, w, dt, pl):
        self.update_turret_module(w, dt, pl)

    def update_mortar(self, w, dt, pl):
        self.update_turret_module(w, dt, pl)

    def update_turret_module(self, w, dt, pl):
        self.station(w, dt, pl, 1.5)
        if self.rebuild_t > 0:
            self.rebuild_t -= dt
            if self.rebuild_t <= 0:
                self.armor = self.p["hp"]
                w.message("%s rebuilt" % self.label, (170, 180, 110))
        tr = self.deployed
        if tr is None:
            self.armor = min(self.p["hp"], self.armor + self.p["hp"] * 0.05 * dt)    # field repairs while packed
            return
        if not tr.alive:
            self.deployed = None
            self.rebuild_t = self.p["rebuild"]
            return
        tr.update(w, dt, pl)

    def can_deploy(self):
        return self.kind in TURRETS and self.deployed is None and self.rebuild_t <= 0

    def deploy(self, w, pl):
        from world import resolve
        ax, ay = pl.aim
        x, y = resolve(w.level, pl.x + ax * 0.9, pl.y + ay * 0.9, 0.35)
        self.deployed = Turret(self, x, y, pl.aim)
        w.turrets.append(self.deployed)
        w.snd("servo", x, y, 0.8)
        w.message("%s deployed" % self.label, (170, 180, 110))

    def pack_up(self, w):
        tr = self.deployed
        self.armor = tr.hp
        tr.alive = False
        if tr in w.turrets:
            w.turrets.remove(tr)
        self.deployed = None
        w.snd("reload", tr.x, tr.y, 0.8)


class Turret:
    """A deployed MG / mortar: picks targets, shoots, draws monsters, takes hits, and goes up like a tactical nuke."""

    R = 0.35
    is_turret = True

    def __init__(self, mod, x, y, aim):
        self.mod = mod
        self.kind = mod.kind
        self.x, self.y = x, y
        self.r = self.R
        self.aim = aim
        self.hp = mod.armor
        self.max_hp = mod.p["hp"]
        self.alive = True
        self.cd = 0.5
        self.flash = 0.0
        self.muzzle = 0.0
        self.target = None
        self.burst = 0

    def update(self, w, dt, pl):
        from traps import los
        from world import Proj, Particle
        self.flash = max(0.0, self.flash - dt)
        self.muzzle = max(0.0, self.muzzle - dt)
        self.cd -= dt
        p = self.mod.p
        mortar = self.kind == "mortar"
        tg = self.target
        ok = lambda e: (mortar and math.hypot(e.x - self.x, e.y - self.y) > 2.0) or (not mortar and los(w.level, self.x, self.y, e.x, e.y))
        if tg is None or not tg.alive or math.hypot(tg.x - self.x, tg.y - self.y) > p["range"] + 1 or not ok(tg):
            self.target = tg = next((e for e in targets(w, self.x, self.y, p["range"]) if ok(e)), None)
        if tg is None:
            return
        dx, dy = tg.x - self.x, tg.y - self.y
        d = math.hypot(dx, dy) or 1
        want = math.atan2(dy, dx)
        cur = math.atan2(self.aim[1], self.aim[0])
        diff = (want - cur + math.pi) % math.tau - math.pi
        cur += max(-6 * dt, min(6 * dt, diff))
        self.aim = (math.cos(cur), math.sin(cur))
        if self.cd > 0 or abs(diff) > 0.25:
            return
        dmg = p["dmg"] * pl.dmg_mult()
        if mortar:
            self.cd = 1.0 / p["rate"]
            T = max(0.7, min(1.8, d / 6.0))
            z0 = 0.7
            vz = (0.1 - z0 + 3.0 * T * T) / T          # step_proj's mortar arc: z += vz dt, vz -= 6 dt
            pr = Proj("mortar", self.x + self.aim[0] * 0.3, self.y + self.aim[1] * 0.3, z0, dx / T, dy / T, dmg, life=T + 1,
                      color=(255, 170, 60), r=0.15, blast=p["blast"], vz=vz)
            pr.owner = pl
            pr.dtype = "explosive"
            w.projs.append(pr)
            w.warnings.append([tg.x, tg.y, p["blast"] * 0.6, T, T, (255, 170, 60)])
            w.snd("shot_grenade", self.x, self.y, 0.7)
            for _ in range(6):
                w.add(Particle("smoke", self.x + self.aim[0] * 0.3, self.y + self.aim[1] * 0.3, 0.8, random.uniform(-0.5, 0.5),
                               random.uniform(-0.5, 0.5), 1.0, 0.8, (110, 105, 95), 0.2))
        else:
            self.cd = 1.0 / p["rate"]
            a = random.uniform(-0.06, 0.06)
            c, s_ = math.cos(a), math.sin(a)
            vx, vy = self.aim[0] * c - self.aim[1] * s_, self.aim[0] * s_ + self.aim[1] * c
            side = 0.05 if self.burst % 2 else -0.05
            self.burst += 1
            pr = Proj("bullet", self.x + vx * 0.5 - vy * side, self.y + vy * 0.5 + vx * side, 0.55, vx * 22, vy * 22, dmg,
                      life=p["range"] / 22 + 0.1, color=(255, 210, 130))
            pr.owner = pl
            w.projs.append(pr)
            w.snd("shot_smg", self.x, self.y, 0.4)
        self.muzzle = 0.06

    def hit(self, w, dmg):
        if not self.alive:
            return
        self.hp -= dmg
        self.flash = 0.1
        w.snd("hit_metal", self.x, self.y, 0.5)
        if self.hp <= 0:
            self.destroy(w)

    def destroy(self, w):
        """Goes up like a tactical nuke (no fallout): flattens walls, hurts everything nearby, you included."""
        from world import Particle
        self.alive = False
        if self in w.turrets:
            w.turrets.remove(self)
        x, y = self.x, self.y
        w.explode(x, y, 3.0, 45 * (1 + 0.15 * (self.mod.level - 1)), (255, 200, 120), hurt_player=True, player_dmg=45, breach=3.0)
        for _ in range(40):
            a = random.random() * math.tau
            s_ = random.uniform(0.3, 1.0) * 6
            w.add(Particle("fire", x, y, random.uniform(0.1, 0.8), math.cos(a) * s_, math.sin(a) * s_, random.uniform(0.5, 3),
                           random.uniform(0.5, 1.1), random.choice(((255, 240, 150), (255, 170, 60), (255, 120, 40))), random.uniform(18, 30)))
        for _ in range(24):
            w.add(Particle("smoke", x + random.uniform(-0.4, 0.4), y + random.uniform(-0.4, 0.4), random.uniform(0.5, 2.5),
                           random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), random.uniform(1.5, 3.5), random.uniform(2, 4),
                           (90, 85, 75), random.uniform(0.4, 0.8)))
        w.add(Particle("ring", x, y, 0.05, 9, 0, 0, 0.6, (255, 220, 150), 0.2))
        w.flash_white = 0.35
        w.shake = 15
        w.hitstop = max(w.hitstop, 0.1)
        w.snd("nuke_blast", x, y)
        w.message("%s DESTROYED" % self.mod.label.upper(), (255, 140, 90))
        self.mod.deployed = None
        self.mod.rebuild_t = self.mod.p["rebuild"]
        self.mod.armor = 0


class ArmProxy:
    """Stands in for the player when the gun arm fires: same buffs and damage, but its own position and aim."""

    def __init__(self, pl):
        self.pl = pl
        self.owner_player = pl
        self.x = self.y = 0.0
        self.aim = (1.0, 0.0)
        self.muzzle = 0.0
        self.muzzle_color = (255, 255, 255)
        self.kbx = self.kby = 0.0
        self.salvo_q = 0
        self.salvo_t = 0.0
        self.salvo_n = 0
        self.salvo_wp = None
        self.buffs = pl.buffs
        self.idx = pl.idx

    def dmg_mult(self):
        return self.pl.dmg_mult()

    def mult(self, kind, default=1.0):
        return self.pl.mult(kind, default)


class Decoy:
    """A hologram of a player: monsters target it; it can't be hurt."""

    R = 0.28

    def __init__(self, x, y, pl, t):
        self.x, self.y = x, y
        self.pl = pl
        self.t = self.max_t = t
        self.alive = True
        self.decoy = True
        self.aim = pl.aim
        self.idx = pl.idx
        self.flash = 0.0


def generate(level, rng=None, bonus=0, kind=None, rarity=None):
    rng = rng or random.Random()
    if kind is None:
        ks = list(KINDS)
        kind = rng.choices(ks, weights=[KINDS[k]["weight"] for k in ks])[0]
    if rarity is None:
        rarity = WP.roll_rarity(rng, level, bonus)
    return Support(kind, rarity, level, rng.randrange(1 << 30))

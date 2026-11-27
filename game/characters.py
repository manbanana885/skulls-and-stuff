"""Playable characters. Each is a lower-half sprite set (legs / treads, 8 move directions) and an upper-half set per
weapon (16 aim directions), so the top always turns independently of the bottom.

cat is the character's damage category: players feel a softened version of their category's weaknesses and
resistances to enemy attacks (PLAYER_SCALE of the way from 1.0 to the enemy-table multiplier).
"""
import damage as DM

CHARS = {
    "skelebot": dict(name="SKELEBOT", cat="undead", speed=1.0, hp=1.0, legs="player_legs", torso="torso_", gibs="player",
                     stride=1.1, desc="Cyborg skeleton. Balanced.",
                     hurt="hurt", death="player_death", step="step", fluid=(28, 24, 32), chips=("gib_bone", "gib_rib", "gib_wire"),
                     sparks=True),
    "canbot":   dict(name="CANBOT", cat="robot", speed=0.8, hp=1.2, legs="canbot_legs", torso="cbtorso_", gibs="walker",
                     stride=0.9, desc="Armoured drum on tank treads. Slow and tough.",
                     hurt="hurt_can", death="death_can", step=None, fluid=(28, 24, 32), chips=("gib_gear", "gib_metal", "gib_wire"),
                     sparks=True),
    "mutant":   dict(name="SUPER MUTANT", cat="mutant", speed=1.2, hp=0.8, legs="mutant_legs", torso="mttorso_", gibs="pinkmelt",
                     stride=1.1, desc="Melting, blistered brute. Fast and fragile.",
                     hurt="hurt_mutant", death="death_mutant", step="step_mutant", fluid=(190, 60, 110), chips=("gib_meat",),
                     sparks=False),
}
ORDER = ["skelebot", "canbot", "mutant"]
PLAYER_SCALE = 0.5

# what kind of damage enemy projectiles deal to players
HOSTILE_TYPE = {"acid": "chemical", "bile": "chemical", "chem": "chemical", "fireball": "fire", "flame": "fire",
                "cryo": "cryo", "bolt": "electrical", "orb": "radiation", "rocket": "explosive", "mortar": "explosive",
                "nuke": "explosive"}


def player_mult(p, dtype):
    cat = CHARS[getattr(p, "char", "skelebot")]["cat"]
    m = DM.MULT[cat].get(dtype or "kinetic", 1.0)
    return 1.0 + (m - 1.0) * PLAYER_SCALE


def stat_lines(char):
    c = CHARS[char]
    out = []
    for key, label in (("hp", "INTEGRITY"), ("speed", "SPEED")):
        d = round((c[key] - 1) * 100)
        out.append(("%s %+d%%" % (label, d)) if d else "%s --" % label)
    return out

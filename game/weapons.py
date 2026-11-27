"""Procedural weapons and power-ups.

A weapon = archetype (base stats + projectile behaviour) + brand (stat leanings) + rarity
(number of modifiers) + random rolls + item level. Everything is derived from a seed.
"""
import random

import damage as DM

# ---------------------------------------------------------------- archetypes
DEFAULTS = dict(pellets=1, life=0.9, pierce=0, blast=0.0, burn=0.0, bounce=0, shock=0, homing=0, slow=0,
                lifesteal=0, twin=False, kick=1.5, spread=0.03, speed=19.0, rad=None, gas=0.0, chill=0.0, saw_bounces=None,
                heavy=1.0, spinup=0.0, wallpierce=0, salvo=None, chain=0, arc_range=0.0, cone=0.0, acid=0, ammo=None, cluster=None,
                tier_leech=0.0, demonic_bonus=0.0, jet=None, barrels=0, shell=None)

ARCH = {
    "pistol":       dict(label="Pistol", dmg=1.7, rate=5.0, spread=0.03, mag=12, reload=0.9, proj="bullet",
                         kick=1.2, sound="shot_pistol", color=(255, 215, 130), heavy=1.2, weight=10),
    "revolver":     dict(label="Revolver", dmg=4.6, rate=2.2, spread=0.015, speed=24, mag=6, reload=1.4, proj="bullet",
                         pierce=1, kick=4, sound="shot_revolver", color=(255, 205, 110), heavy=1.2, weight=7),
    "smg":          dict(label="SMG", dmg=0.85, rate=13, spread=0.09, speed=18, mag=36, reload=1.3, proj="bullet",
                         kick=1.0, sound="shot_smg", color=(255, 225, 150), weight=9),
    "shotgun":      dict(label="Shotgun", dmg=0.95, rate=1.6, spread=0.32, pellets=8, speed=16, life=0.42, mag=6,
                         reload=1.6, proj="pellet", kick=6, sound="shot_shotgun", color=(255, 195, 95), weight=9),
    # drum-fed automatic shotgun: holds the trigger like an assault rifle, long reload when the drum runs dry
    "auto_shotgun": dict(label="Auto Shotgun", dmg=0.7, rate=4.2, spread=0.36, pellets=7, speed=16, life=0.42, mag=20,
                         reload=2.6, proj="pellet", kick=3.5, sound="shot_autoshotgun", color=(255, 185, 90), weight=4),
    # break-action guns: every barrel goes off at once, then you crack it open and reload
    "shotgun_2":    dict(label="Double-Barrel Shotgun", dmg=0.95, rate=3.0, spread=0.4, pellets=16, speed=16, life=0.42, mag=1,
                         reload=1.5, proj="pellet", kick=9, sound="shot_boomstick", color=(255, 195, 95), weight=6, barrels=2),
    "shotgun_3":    dict(label="Triple-Barrel Shotgun", dmg=0.95, rate=3.0, spread=0.44, pellets=24, speed=16, life=0.42, mag=1,
                         reload=1.9, proj="pellet", kick=11, sound="shot_boomstick", color=(255, 190, 90), weight=4, barrels=3,
                         heavy=0.94),
    "shotgun_4":    dict(label="Quad-Barrel Shotgun", dmg=0.95, rate=3.0, spread=0.48, pellets=32, speed=16, life=0.42, mag=1,
                         reload=2.3, proj="pellet", kick=13, sound="shot_boomstick", color=(255, 185, 85), weight=3, barrels=4,
                         heavy=0.86),
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
                         kick=0.8, sound="shot_laser", color=(255, 60, 60), heavy=1.2, weight=6),
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
    # cluster bomb launcher: a fat lobbed shell that bursts into a spray of bouncing bomblets
    "cluster":      dict(label="Cluster Launcher", dmg=9, rate=0.8, spread=0.03, speed=8, life=1.3, mag=4, reload=2.6, proj="grenade",
                         blast=1.6, cluster=(5, 9), kick=5, sound="shot_grenade", color=(255, 160, 60), weight=3),
    # coil guns: instant lightning that ricochets off walls and chains between monsters
    "coil_pistol":  dict(label="Coil Pistol", dmg=2.4, rate=3.6, spread=0.04, speed=0, mag=12, reload=1.1, proj="arc",
                         chain=2, bounce=1, arc_range=8.0, kick=1.0, sound="shot_coil", color=(150, 190, 255), heavy=1.2, weight=6),
    "coil_rifle":   dict(label="Coil Rifle", dmg=1.5, rate=7, spread=0.05, speed=0, mag=28, reload=1.5, proj="arc",
                         chain=3, bounce=2, arc_range=11.0, kick=1.2, sound="shot_coil", color=(140, 175, 255), weight=5),
    "coil_heavy":   dict(label="Storm Coil", dmg=3.2, rate=5.5, spread=0.06, speed=0, mag=60, reload=2.8, proj="arc",
                         chain=6, bounce=3, arc_range=13.0, kick=2.0, heavy=0.62, sound="shot_coil", color=(170, 150, 255), weight=3),
    # microwave emitter: expanding rings that sweep a cone and cook everything in it
    "microwave":    dict(label="Microwave Emitter", dmg=2.6, rate=3.2, spread=0.0, speed=8.5, life=0.75, mag=18, reload=1.7,
                         proj="wave", pierce=99, cone=0.5, burn=0.5, kick=1.0, sound="shot_microwave", color=(235, 130, 255), weight=5),
    # chemical jets: a fast, narrow stream that spatters where it lands and leaves a hazardous puddle
    "jet_napalm":   dict(label="Napalm Jet", dmg=2.4, rate=9, spread=0.02, speed=17, life=0.55, mag=60, reload=2.0, proj="jet",
                         burn=1.0, kick=0.6, sound="shot_chem_jet", color=(255, 120, 30), weight=3, jet="napalm"),
    "jet_cryo":     dict(label="Cryo Jet", dmg=2.0, rate=9, spread=0.02, speed=17, life=0.55, mag=60, reload=2.0, proj="jet",
                         chill=0.06, kick=0.6, sound="shot_chem_jet", color=(140, 210, 255), weight=3, jet="cryo"),
    "jet_rad":      dict(label="Rad-Waste Jet", dmg=2.2, rate=9, spread=0.02, speed=17, life=0.55, mag=60, reload=2.0, proj="jet",
                         kick=0.6, sound="shot_chem_jet", color=(170, 255, 60), weight=3, jet="rad"),
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
    "auto_shotgun": (1.04, 1.16), "shotgun_2": (1.0, 1.16), "shotgun_3": (1.0, 1.17), "shotgun_4": (0.99, 1.18),
    "microwave": (0.98, 1.13), "cluster": (1.0, 1.17), "jet_napalm": (1.0, 1.14), "jet_cryo": (0.98, 1.14), "jet_rad": (0.98, 1.14),
}
SHOULDER = {"rocket": 0.14, "tac_nuke": 0.14, "nuke": 0.15}   # sideways offset to the right shoulder

# archetypes that borrow another gun's models (torso / floor pickup sprites)
SPRITE_ARCH = {"jet_napalm": "flamer", "jet_cryo": "cryo", "jet_rad": "chem"}


def sprite_arch(arch):
    return SPRITE_ARCH.get(arch, arch)


RARITY = [("Common", (205, 205, 205)), ("Uncommon", (80, 225, 95)), ("Rare", (70, 145, 255)),
          ("Epic", (195, 85, 255)), ("Legendary", (255, 155, 30)), ("Mythical", (40, 230, 255)), ("Demonic", (255, 50, 40)),
          ("Eldritch", (90, 255, 90)), ("Sacred", (255, 255, 255))]
LEGENDARY, MYTHICAL, DEMONIC, ELDRITCH, SACRED = 4, 5, 6, 7, 8
# how a tier's name is lettered: (text colour, outline colour or None)
TIER_TEXT = {DEMONIC: ((12, 8, 8), (255, 50, 40)), ELDRITCH: ((8, 12, 8), (90, 255, 90)), SACRED: ((255, 255, 255), None)}
# while it's the gun in your hands: integrity per second (+ heals, - hurts) and the share of damage dealt that heals you
TIER_FX = {SACRED: dict(regen=1.0), ELDRITCH: dict(regen=-1.0, leech=0.08), DEMONIC: dict(regen=-1.5)}

# ---------------------------------------------------------------- manufacturers
# Which weapon groups each archetype belongs to; a manufacturer only builds guns in its groups ("all" = anything).
GROUPS = {
    "pistol": {"sidearm"}, "revolver": {"sidearm"}, "laser_pistol": {"sidearm", "energy"}, "coil_pistol": {"sidearm", "energy"},
    "smg": {"auto"}, "carbine": {"auto"}, "assault": {"auto"}, "coil_rifle": {"auto", "energy"}, "chaingun": {"auto", "heavy"},
    "shotgun": {"shotgun"}, "auto_shotgun": {"shotgun", "auto"}, "shotgun_2": {"shotgun"}, "shotgun_3": {"shotgun"},
    "shotgun_4": {"shotgun"},
    "sniper": {"precision"}, "railgun": {"precision", "heavy"}, "laser_rifle": {"precision", "energy"},
    "plasma": {"energy"}, "microwave": {"energy"}, "coil_heavy": {"energy", "heavy"},
    "flamer": {"sprayer"}, "chem": {"sprayer"}, "cryo": {"sprayer"},
    "jet_napalm": {"sprayer"}, "jet_cryo": {"sprayer"}, "jet_rad": {"sprayer"},
    "grenade": {"explosive"}, "rocket": {"explosive"}, "barrage": {"explosive", "heavy"}, "cluster": {"explosive"},
    "tac_nuke": {"explosive"}, "nuke": {"explosive"},
    "saw": {"exotic"},
}
GROUP_LABEL = {"sidearm": "sidearms", "auto": "automatics", "shotgun": "shotguns", "precision": "precision rifles",
               "energy": "energy weapons", "sprayer": "sprayers", "explosive": "explosives", "heavy": "heavy weapons",
               "exotic": "exotic launchers"}


def _brand(groups, color, blurb, mul=None, add=None, extra_mods=0, bias=None, tier=0, weight=1.0, special=None):
    return dict(groups=groups, color=color, blurb=blurb, mul=mul or {}, add=add or {}, extra_mods=extra_mods, bias=bias or {},
                tier=tier, weight=weight, special=special)


# mul: stat multipliers; add: additive stat bonuses; extra_mods: +/- bonus mod slots; bias: mod key -> roll weight;
# tier: minimum rarity that can carry the brand (LEGENDARY / MYTHICAL / ELDRITCH / SACRED brands are exclusive to those tiers)
BRANDS = {
    # --- the original six, now with real personalities
    "Ossuary Arms": _brand("all", (215, 205, 180), "old reliable bone-and-steel", {"dmg": 1.35, "rate": 0.78}),
    "Necrotek": _brand({"energy"}, (90, 230, 255), "corporate death-tech", {"rate": 1.55, "spread": 1.8, "dmg": 0.88},
                       bias={"rapid": 4, "shock": 4}),
    "Hexforge": _brand({"sidearm", "precision"}, (200, 120, 255), "witch-forged precision",
                       {"speed": 1.7, "spread": 0.35, "dmg": 1.15, "reload": 0.8}, bias={"precise": 4, "velocity": 4}),
    "Marrow & Sons": _brand("all", (190, 150, 110), "family workshop, bottomless drums", {"mag": 2.0, "dmg": 0.82, "reload": 1.3},
                            bias={"drum": 3}),
    "Cadaver Dynamics": _brand({"explosive", "heavy"}, (150, 170, 120), "military ordnance",
                               {"reload": 0.55, "mag": 1.5, "dmg": 0.92}, bias={"quick": 4, "drum": 2}),
    "Graveline": _brand({"precision"}, (170, 180, 200), "one shot, one grave", {"dmg": 1.6, "mag": 0.55, "rate": 0.85},
                        bias={"heavy": 3}),
    # --- new houses
    "Rattlebone Surplus": _brand("all", (160, 140, 90), "junkyard guns, jury-rigged extras", {"dmg": 0.72, "mag": 1.4, "spread": 1.3},
                                 extra_mods=1, weight=0.8),
    "Pyre & Ash Industrial": _brand({"sprayer", "explosive"}, (255, 120, 40), "arsonist chemists", {"dmg": 1.1},
                                    add={"burn": 2.5}, bias={"incendiary": 8}),
    "Halcyon Biomech": _brand({"sprayer", "energy"}, (130, 230, 170), "clean-room bio-weapons", {"rate": 1.15},
                              add={"chill": 0.04, "gas": 3.0}, bias={"acid": 6, "cryo": 6}),
    "Gorewright Foundry": _brand({"heavy"}, (170, 60, 50), "crude, brutal, hits like a truck", {"dmg": 1.9, "rate": 0.7, "spread": 1.2},
                                 extra_mods=-1),
    "Kettleblack Pneumatics": _brand({"shotgun"}, (120, 110, 100), "choked barrels, packed shells", {"spread": 0.55, "dmg": 0.9},
                                     add={"pellets": 4}, bias={"heavy": 2}),
    "Blackreef Munitions": _brand({"auto"}, (80, 120, 150), "spray and pray", {"rate": 1.45, "mag": 1.5, "dmg": 0.78, "spread": 1.5},
                                  bias={"drum": 3, "rapid": 2}),
    "Voltaic Mortuary": _brand({"energy", "auto"}, (150, 140, 255), "electrified undertakers", {"dmg": 1.05},
                               add={"shock": 1, "chain": 1}, bias={"shock": 5}),
    "Thornwall Defense": _brand({"heavy", "precision"}, (120, 140, 110), "frame-mounted, easy to carry",
                                {"mag": 1.5, "reload": 0.8}, special="light"),
    "Saint Wormwood Armory": _brand({"sidearm", "shotgun"}, (240, 230, 190), "blessed arms for demon hunters",
                                    {"dmg": 1.3, "mag": 0.8, "reload": 1.2}, bias={"explosive": 3, "incendiary": 3}),
    "Sawtooth & Cleaver Co.": _brand({"exotic", "shotgun"}, (210, 210, 220), "butcher's engineering", {"dmg": 1.25},
                                     add={"pierce": 2, "bounce": 1}, bias={"ricochet": 5}),
    # --- legendary-only houses
    "The Ninefold Choir": _brand("all", (255, 210, 120), "nine voices, one hymn of ruin", {"dmg": 1.4}, extra_mods=1, tier=LEGENDARY),
    "Asphodel Atelier": _brand({"sidearm", "precision"}, (255, 170, 200), "bespoke killing instruments",
                               {"dmg": 1.6, "speed": 1.5, "spread": 0.3, "reload": 0.8}, tier=LEGENDARY),
    "House Mourningstar": _brand({"explosive", "heavy"}, (255, 140, 60), "dynastic artillery", {"blast": 1.5, "mag": 1.6, "dmg": 1.2},
                                 tier=LEGENDARY),
    # --- mythical-only, eldritch-only and sacred-only
    "The Gilded Pantheon": _brand("all", (40, 230, 255), "forged by the smiths of dead gods", {"dmg": 1.45, "speed": 1.3, "reload": 0.8},
                                  extra_mods=1, tier=MYTHICAL),
    "Brimstone Covenant": _brand("all", (255, 50, 40), "forged in the ninth pit", {"dmg": 1.4, "rate": 1.15},
                                 add={"burn": 2.0}, bias={"incendiary": 10, "explosive": 3}, tier=DEMONIC),
    "The Unspeakable Works": _brand("all", (90, 255, 90), "built by something that should not build", {"dmg": 1.5, "rate": 1.25},
                                    extra_mods=1, tier=ELDRITCH),
    "The Reliquary": _brand("all", (255, 245, 200), "relics of a dead god", {"dmg": 1.6, "rate": 1.2, "mag": 1.4, "reload": 0.7},
                            extra_mods=1, tier=SACRED),
}


def brands_for(arch, rarity):
    groups = GROUPS.get(arch, set())
    out = []
    for name, b in BRANDS.items():
        if b["tier"] > rarity:
            continue
        if rarity >= MYTHICAL and b["tier"] < LEGENDARY:
            continue                     # mythical / sacred guns only come out of the top houses
        if b["groups"] != "all" and not (b["groups"] & groups):
            continue
        w = b["weight"]
        if b["tier"] and b["tier"] == rarity:
            w *= 14.0                    # each top tier mostly comes from its own house
        elif b["tier"]:
            w *= 3.0
        out.append((name, w))
    return out


def brand_summary(name):
    """'+60% DMG  -45% MAG' style line from a brand's multipliers and additions."""
    b = BRANDS[name]
    lab = {"dmg": "DMG", "rate": "RATE", "mag": "MAG", "reload": "RELOAD", "speed": "VELOCITY", "spread": "SPREAD", "blast": "BLAST"}
    parts = []
    for k, v in b["mul"].items():
        parts.append("%+d%% %s" % (round((v - 1) * 100), lab.get(k, k.upper())))
    for k, v in b["add"].items():
        parts.append({"burn": "+BURN", "chill": "+CHILL", "gas": "+GAS", "pellets": "+%d PELLETS" % v, "shock": "+SHOCK",
                      "chain": "+1 CHAIN (coil guns)", "pierce": "+%d PIERCE" % v, "bounce": "+BOUNCE"}.get(k, "+" + k.upper()))
    if b["extra_mods"]:
        parts.append("%+d MOD" % b["extra_mods"])
    if b["special"] == "light":
        parts.append("HALF WEIGHT")
    return "  ".join(parts)

NO_PROJ_SPEED = {"beam", "arc"}
EXPLOSIVE = {"grenade", "rocket", "tac_nuke", "nuke", "barrage", "cluster"}
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

# ---------------------------------------------------------------- shotgun shells
# Every shotgun rolls its shell: buckshot (a cloud of pellets) or a slug - one big projectile per barrel.
#   dumdum: a fat, slow-ish expanding slug that hits like a truck and shoves what it hits (Expanding ammo)
#   sabot:  a fast steel dart that punches through a whole line of monsters (Penetrating Core ammo)
SHELLS = {
    "dumdum": dict(word="Dum-Dum", label="Dum-Dum slugs", ammo="exp", share=1.0, speed=17.0, life=0.95, spread=0.035,
                   pierce=0, kick=1.3),
    "sabot":  dict(word="Sabot", label="Discarding-sabot steel cores", ammo="pen", share=0.8, speed=44.0, life=0.5,
                   spread=0.012, pierce=4, kick=1.1),
}
SHELL_ODDS = (("dumdum", 0.2), ("sabot", 0.2))       # the rest is buckshot


def is_shotgun(arch):
    return "shotgun" in GROUPS.get(arch, ())


def _load_slugs(st, shell):
    """Turn buckshot stats into slug stats: one projectile per barrel carrying a share of the whole load."""
    sh = SHELLS[shell]
    n = max(1, st["barrels"])
    st["dmg"] *= st["pellets"] / n * sh["share"]
    st["pellets"] = n
    st["proj"] = "slug"
    st["speed"], st["life"], st["spread"] = sh["speed"], sh["life"], sh["spread"]
    st["pierce"] += sh["pierce"]
    st["kick"] *= sh["kick"]
    st["shell"] = shell
    if st["sound"] == "shot_shotgun":
        st["sound"] = "shot_slug"


def _explosive(st):
    st["blast"] = max(st["blast"], 0.75)
    st["dmg"] *= 0.9


MODS = [
    _m("incendiary", "Incendiary", "Sets targets ablaze", _add(burn=1.2)),
    _m("explosive", "Explosive", "Rounds explode on impact", _explosive, lambda a: ARCH[a]["proj"] not in SPRAYS | {"beam", "wave"} and a not in EXPLOSIVE),
    _m("piercing", "Piercing", "Punches through 2 more targets", _add(pierce=2),
       lambda a: a not in EXPLOSIVE and ARCH[a]["proj"] not in SPRAYS | {"beam", "saw", "rail", "arc", "wave"} | set(BULLETS)),
    # ammo types are rolled separately (every bullet gun gets one), never as bonus mods
    _m("penetrating", "Penetrating Core", "Pierces 2 more; x1.35 vs robots & constructs, x0.8 vs undead & mutants",
       _penetrating, lambda a: False),
    _m("expanding", "Expanding", "x1.35 vs undead & mutants, x0.75 vs robots & constructs",
       _expanding, lambda a: False),
    _m("ricochet", "Ricochet", "Bounces off walls", _add(bounce=1), lambda a: ARCH[a]["proj"] in ("bullet", "pellet", "bolt", "slug", "plasma", "saw", "arc")),
    _m("twin", "Twin-Linked", "Fires a second parallel shot", _set_twin,
       lambda a: ARCH[a]["proj"] not in SPRAYS | {"nuke", "missile"} and not ARCH[a].get("barrels")),
    _m("rapid", "Rapid", "+35% fire rate", _mul(rate=1.35, dmg=0.88)),
    _m("heavy", "Heavy", "+45% damage, slower", _mul(dmg=1.45, rate=0.85, kick=1.5)),
    _m("precise", "Precise", "Halved spread", _mul(spread=0.5), lambda a: ARCH[a]["spread"] > 0.02),
    _m("drum", "Drum-Fed", "+75% magazine", _mul(mag=1.75), lambda a: not ARCH[a].get("barrels")),   # break-actions hold one load
    _m("quick", "Quickload", "40% faster reloads", _mul(reload=0.6)),
    _m("vampiric", "Vampiric", "Heals 3 integrity per kill", _add(lifesteal=3)),
    _m("shock", "Shocking", "Arcs to nearby enemies", _add(shock=1), lambda a: ARCH[a]["proj"] != "arc"),
    _m("seeking", "Seeking", "Projectiles home in", _add(homing=1), lambda a: ARCH[a]["proj"] not in SPRAYS | {"beam", "saw", "rail", "arc", "wave"}),
    _m("velocity", "High-Velocity", "+50% projectile speed", _mul(speed=1.5), lambda a: ARCH[a]["proj"] not in SPRAYS | {"beam", "arc"}),
    _m("cryo", "Cryo", "Chills and slows targets", _add(slow=1)),
    _m("acid", "Acid-Augmented", "Hits leave corrosive puddles", _add(acid=1),
       lambda a: ARCH[a]["proj"] in ("bullet", "pellet", "slug", "bolt", "rocket", "grenade", "missile", "saw", "plasma", "rail")),
]
MOD_BY_KEY = {m["key"]: m for m in MODS}

MYTHICAL_NAMES = ["Starfall", "The Worldspine", "Titan's Mercy", "Aegis of Ash", "Hydra's Last Head", "Ironsong",
                  "The Ninth Labour", "Dawnbreaker", "Oathkeeper's Wrath"]
DEMONIC_NAMES = ["Hellmaw Howitzer", "The Ninth Circle", "Brimstone Sermon", "Pitfire", "Cinder Saint", "The Goat's Bargain",
                 "Infernal Writ", "Ashen Tongue", "Sulphur Kiss"]
ELDRITCH_NAMES = ["The Hollow Psalm", "Mouth of the Deep", "Nine Black Stars", "The Unborn Choir", "Grief Engine",
                  "Whisper of Yth", "The Thing in the Barrel", "Sorrowmaw", "Last Light Eater"]
SACRED_NAMES = ["The Last Benediction", "Saint Ossein's Mercy", "Halo Breaker", "Requiem Aeterna", "Gospel of Teeth",
                "The Marrow Relic", "Choirfall", "Lux Ultima"]
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
        if st["cluster"]:
            st["cluster"] = rng.randint(*st["cluster"])
        if st["salvo"]:
            st["salvo"] = rng.randint(*st["salvo"])
            st["dmg"] *= (10.0 / st["salvo"]) ** 0.35     # small salvos hit a little harder per missile
        self.shell = None
        if is_shotgun(arch):
            r_ = rng.random()
            for shell, odds in SHELL_ODDS:
                if r_ < odds:
                    self.shell = shell
                    _load_slugs(st, shell)
                    break
                r_ -= odds
        options = brands_for(arch, rarity)
        self.brand = rng.choices([n for n, _ in options], weights=[w for _, w in options])[0]
        B = BRANDS[self.brand]
        for k, v in B["mul"].items():
            st[k] *= v
        for k, v in B["add"].items():
            if k == "pellets" and (st["pellets"] <= 1 or st["shell"]):
                continue
            if k == "pellets":
                v *= max(1, st["barrels"])        # choked barrels: every barrel gets the extra shot
            if k == "chain" and not st["chain"]:
                continue
            if k == "bounce" and st["proj"] not in ("bullet", "pellet", "bolt", "slug", "plasma", "saw", "arc"):
                continue
            st[k] += v
        if B["special"] == "light" and st["heavy"] < 1.0:
            st["heavy"] = 1.0 - (1.0 - st["heavy"]) * 0.5
        # bullet guns always roll an ammo type: standard 50%, Penetrating Core 25%, Expanding 25%
        self.ammo_type = None
        if self.shell:                               # a slug's ammo type comes with the shell
            self.ammo_type = SHELLS[self.shell]["ammo"]
            MOD_BY_KEY["penetrating" if self.ammo_type == "pen" else "expanding"]["fn"](st)
        elif ARCH[arch]["proj"] in BULLETS:
            r_ = rng.random()
            pen_w = 0.25 * (2.0 if self.brand == "Graveline" else 1.0)
            self.ammo_type = "pen" if r_ < pen_w else ("exp" if r_ < pen_w + 0.25 else None)
            if self.ammo_type:
                MOD_BY_KEY["penetrating" if self.ammo_type == "pen" else "expanding"]["fn"](st)
        pool = [m for m in MODS if m["ok"](arch)]
        n_mods = max(0, {LEGENDARY: 3, MYTHICAL: 4, DEMONIC: 4, ELDRITCH: 5, SACRED: 5}.get(rarity, rarity) + B["extra_mods"])
        n_mods = min(n_mods, 6)
        self.mods = []
        while pool and len(self.mods) < n_mods:        # weighted draw without replacement; brands lean toward their favourites
            weights = [B["bias"].get(m["key"], 1.0) for m in pool]
            m = rng.choices(pool, weights=weights)[0]
            pool.remove(m)
            self.mods.append(m)
        if rarity == DEMONIC and rng.random() < 0.9 and not any(m["key"] == "incendiary" for m in self.mods):
            inc = MOD_BY_KEY["incendiary"]                      # demonic guns almost always burn
            if self.mods:
                self.mods[-1] = inc
            else:
                self.mods.append(inc)
        for m in self.mods:
            m["fn"](st)
        if rarity == DEMONIC:
            st["demonic_bonus"] = rng.uniform(0.10, 0.30)
            st["dmg"] *= 1 + st["demonic_bonus"]
        st["tier_leech"] = TIER_FX.get(rarity, {}).get("leech", 0.0)
        st["dmg"] *= (1 + 0.07 * rarity) * {LEGENDARY: 1.35, MYTHICAL: 1.7, DEMONIC: 1.85, ELDRITCH: 2.0, SACRED: 2.4}.get(rarity, 1.0) * (1 + 0.2 * (level - 1))
        st["mag"] = 1 if st["barrels"] else max(1, int(round(st["mag"])))
        st["pellets"] = int(round(st["pellets"]))
        self.st = st
        if rarity == SACRED:
            self.name = '"%s"' % rng.choice(SACRED_NAMES)
        elif rarity == ELDRITCH:
            self.name = '"%s"' % rng.choice(ELDRITCH_NAMES)
        elif rarity == DEMONIC:
            self.name = '"%s"' % rng.choice(DEMONIC_NAMES)
        elif rarity == MYTHICAL:
            self.name = '"%s"' % rng.choice(MYTHICAL_NAMES)
        elif rarity == LEGENDARY:
            self.name = '"%s"' % rng.choice(UNIQUE_NAMES)
        else:
            adj = self.mods[0]["adj"] + " " if self.mods else ""
            ammo_word = (SHELLS[self.shell]["word"] + " ") if self.shell else {"pen": "Penetrating ", "exp": "Expanding "}.get(self.ammo_type, "")
            self.name = "%s%s%s" % (adj, ammo_word, st["label"])
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
        if st["cluster"]:
            per_shot *= 1 + st["cluster"] * 0.45
        if st["proj"] == "wave":
            per_shot *= 2.0
        return per_shot * st["mag"] / self.cycle()

    def cycle(self):
        """Seconds to empty the magazine and be ready again. The reload starts the moment the last shot goes,
        so it overlaps that shot's cooldown (a break-action is ready after its reload, not cooldown + reload)."""
        st = self.st
        return (st["mag"] - 1) / st["rate"] + max(1.0 / st["rate"], st["reload"])

    def shots_per_sec(self):
        return self.st["mag"] / self.cycle()

    def card_lines(self):
        st = self.st
        dmg = "%.1f" % st["dmg"] + (" x%d" % self.projectiles_per_shot() if self.projectiles_per_shot() > 1 else "")
        rate = self.shots_per_sec() if st["barrels"] else st["rate"]      # break-actions: one shot per reload
        lines = [("DMG", dmg), ("RATE", "%.2f/s" % rate if rate < 1 else "%.1f/s" % rate), ("MAG", "%d" % st["mag"]),
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


RARE_ONLY = False      # run_loot_test.bat: every roll is Mythical / Demonic / Eldritch / Sacred


def roll_rarity(rng, level, bonus=0):
    if RARE_ONLY:
        return rng.choice((MYTHICAL, DEMONIC, ELDRITCH, SACRED))
    w = [60, 26, 10, 3.5, 0.8, 0.012, 0.005, 0.003, 0.0008]
    shift = min(level - 1, 8) * 0.35 + bonus
    for i in range(len(w)):
        w[i] *= (1 + shift) ** (min(i, LEGENDARY) * 0.8)     # tiers above legendary keep a fixed ratio to it
    r = rng.uniform(0, sum(w))
    for i, wi in enumerate(w):
        r -= wi
        if r <= 0:
            return min(SACRED, i)
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

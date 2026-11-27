"""Damage types and enemy categories.

Every source of damage to a monster has one of six types; every monster and boss belongs to one of five
categories; MULT says how hard each type hits each category. Gun mods add secondary types (Incendiary burns =
Fire, Cryo chill = Cryo, Shocking arcs = Electrical, Acid-Augmented puddles = Chemical).
"""

TYPES = ("kinetic", "explosive", "fire", "chemical", "cryo", "radiation", "electrical")
COLOR = {"kinetic": (230, 230, 235), "explosive": (255, 205, 90), "fire": (255, 120, 40), "chemical": (130, 230, 60),
         "cryo": (150, 215, 255), "radiation": (210, 255, 90), "electrical": (160, 150, 255)}

#               kinetic fire  chem  cryo  rad   elec
MULT = {
    "undead":    dict(kinetic=1.0, fire=1.4, chemical=1.0, cryo=0.6, radiation=0.6, electrical=0.8),
    "robot":     dict(kinetic=0.8, fire=0.8, chemical=1.0, cryo=1.1, radiation=1.0, electrical=1.6),
    "demon":     dict(kinetic=1.0, fire=0.4, chemical=0.8, cryo=1.4, radiation=1.3, electrical=1.0),
    "construct": dict(kinetic=0.6, fire=0.8, chemical=1.4, cryo=1.2, radiation=0.8, electrical=1.0),
    "mutant":    dict(kinetic=1.25, fire=1.2, chemical=0.7, cryo=1.0, radiation=0.6, electrical=1.0),
}
for _row in MULT.values():
    _row["explosive"] = 1.0          # explosions hit everything the same

# kinetic ammo mods: an extra multiplier on top of the kinetic column
AMMO = {
    "pen": {"robot": 1.35, "construct": 1.35, "undead": 0.8, "mutant": 0.8},     # Penetrating Core
    "exp": {"undead": 1.35, "mutant": 1.35, "robot": 0.75, "construct": 0.75},   # Expanding
}
AMMO_LABEL = {"pen": "PENETRATING CORE", "exp": "EXPANDING"}

CATEGORY = {}
for _cat, _names in {
    "undead": "zombie crawler skull wretch shade hollow drowned revenant bowman bonepriest flayed hookman shieldbearer "
              "pyrewraith boghag",
    "robot": "drone turret walker raddrone",
    "demon": "hellspawn brute cinderfiend berserker heretic flagellant siren enthraller thornling harpy hoarder",
    "construct": "goldgolem mourner chestmimic mimic rustbound",
    "mutant": "leech spider spitter bloater stalker specimen sporewalker clone radhound meltgunner meltman acidcrab eelmaw "
              "lurker sludgegunner hazmatsprayer glutton maggot devourer wendigo pinkmelt",
}.items():
    for _n in _names.split():
        CATEGORY[_n] = _cat

BOSS_CATEGORY = {
    "gatekeeper": "undead", "necroking": "undead", "blackknight": "undead", "leviathan": "undead",
    "ashcolossus": "construct", "tombtitan": "construct", "goldenmaw": "construct",
    "midasengine": "robot", "liquidator": "robot", "distiller": "robot",
    "wrathful": "demon", "archheretic": "demon", "butcherking": "demon", "thornmother": "demon", "tempestqueen": "demon",
    "entwined": "demon", "triplemaw": "demon",
    "gorged": "mutant", "subjectzero": "mutant", "hivemind": "mutant", "coreabom": "mutant", "sewerking": "mutant",
    "gatorbeast": "mutant", "melttitan": "mutant",
}

WEAPON_TYPE = {
    "pistol": "kinetic", "revolver": "kinetic", "smg": "kinetic", "shotgun": "kinetic", "carbine": "kinetic",
    "assault": "kinetic", "sniper": "kinetic", "grenade": "explosive", "rocket": "explosive", "tac_nuke": "explosive",
    "nuke": "explosive", "saw": "kinetic", "chaingun": "kinetic", "railgun": "kinetic", "barrage": "explosive", "cluster": "explosive",
    "flamer": "fire", "laser_pistol": "fire", "laser_rifle": "fire",
    "chem": "chemical", "cryo": "cryo",
    "plasma": "radiation", "microwave": "radiation",
    "coil_pistol": "electrical", "coil_rifle": "electrical", "coil_heavy": "electrical",
}


def category(kind):
    return CATEGORY.get(kind, "mutant")


def mult(e, dtype, ammo=None):
    cat = getattr(e, "cat", None)
    m = MULT.get(cat, {}).get(dtype or "kinetic", 1.0)
    if ammo and (dtype or "kinetic") == "kinetic":
        m *= AMMO[ammo].get(cat, 1.0)
    return m


def secondary(st):
    """Extra damage types a weapon's mods add."""
    out = []
    if st.get("burn") and st.get("dtype") != "fire":
        out.append("fire")
    if (st.get("slow") or st.get("chill")) and st.get("dtype") != "cryo":
        out.append("cryo")
    if st.get("shock") and st.get("dtype") != "electrical":
        out.append("electrical")
    if (st.get("acid") or st.get("gas")) and st.get("dtype") != "chemical":
        out.append("chemical")
    if st.get("rad") and st.get("dtype") != "radiation":
        out.append("radiation")
    if st.get("blast") and st.get("dtype") not in ("explosive", "radiation"):
        out.append("explosive")
    return out

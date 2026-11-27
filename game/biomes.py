"""Biomes: each sector picks one. Controls tiles, props, enemy mix, lighting tint, ambient particles and music."""
import random

BIOMES = {
    "facility": dict(
        title="THE FACILITY",
        floors=[("floor_metal", 5), ("floor_concrete", 4), ("floor_grate", 2)],
        walls=["wall_tech", "wall_pipe", "wall_skull"],
        decor=["skullpile", "gorepile", "corpse", "cables"],
        solids=["barrel", "barrel", "crate", "crate", "crate", "tank"],
        extras=[("floor_concrete", "floor_bones", 0.05), ("floor_concrete", "floor_gore", 0.07),
                ("floor_metal", "floor_gore", 0.05), ("floor_metal", "floor_cables", 0.13)],
        infest=1.0, tint=(255, 255, 255), ambient="dust", music="combat",
        bias={}, signature=[]),
    "ossuary": dict(
        title="THE OSSUARY",
        floors=[("floor_flagstone", 6), ("floor_concrete", 2)],
        walls=["wall_crypt", "wall_crypt", "wall_skull"],
        decor=["candles", "candles", "skullpile", "gorepile", "corpse"],
        solids=["sarcophagus", "sarcophagus", "crate", "crate", "barrel"],
        extras=[("floor_flagstone", "floor_bones", 0.12), ("floor_concrete", "floor_bones", 0.2)],
        infest=0.4, tint=(255, 222, 185), ambient="dust", music="deep",
        bias={"zombie": 2.0, "crawler": 2.0, "skull": 2.5, "wretch": 0.7}, signature=["skull"]),
    "otherworld": dict(
        title="THE RUST",
        floors=[("floor_rust", 5), ("floor_rustgrate", 3)],
        walls=["wall_rust", "wall_rust", "wall_fence"],
        decor=["bodybag", "bodybag", "gorepile", "cables"],
        solids=["gurney", "gurney", "crate", "barrel"],
        extras=[("floor_rust", "floor_gore", 0.06)],
        infest=0.7, tint=(235, 175, 160), ambient="ash", music="dread",
        bias={"wretch": 3.5, "stalker": 2.5, "bloater": 1.5, "leech": 1.5}, signature=["wretch", "stalker"]),
    "outpost": dict(
        title="THE OUTPOST",
        floors=[("floor_snow", 5), ("floor_lab", 4)],
        walls=["wall_ice", "wall_ice", "wall_lab"],
        decor=["thingcorpse", "corpse", "cables", "thingcorpse"],
        solids=["generator", "crate", "crate", "crate", "barrel"],
        extras=[("floor_lab", "floor_gore", 0.06), ("floor_snow", "floor_snowblood", 0.12)],
        infest=0.6, tint=(195, 222, 255), ambient="snow", music="frost",
        bias={"mimic": 4.0, "crawler": 3.0, "drone": 1.5, "turret": 1.5}, signature=["mimic"]),
    "hell": dict(
        title="THE PIT",
        floors=[("floor_brimstone", 6), ("floor_rune", 0.6)],
        walls=["wall_hellrock", "wall_hellrock", "wall_spine"],
        decor=["skullpile", "gorepile", "corpse", "candles"],
        solids=["brazier", "brazier", "impaler", "barrel"],
        extras=[("floor_brimstone", "floor_bones", 0.04)],
        infest=0.5, tint=(255, 185, 150), ambient="embers", music="inferno",
        bias={"hellspawn": 4.0, "skull": 3.0, "brute": 2.0, "spider": 1.5}, signature=["hellspawn"]),
}
# large multi-tile stains scattered at level start: (colour, radius range in tiles, chance per floor cell)
STAINS = {
    "facility": [((22, 20, 24), (0.25, 0.6), 0.025), ((70, 35, 15), (0.2, 0.4), 0.015)],
    "ossuary": [((30, 24, 18), (0.3, 0.7), 0.03), ((60, 8, 6), (0.2, 0.4), 0.012)],
    "otherworld": [((65, 6, 6), (0.3, 0.8), 0.035), ((55, 28, 12), (0.3, 0.6), 0.03)],
    "outpost": [((120, 132, 148), (0.3, 0.7), 0.03), ((95, 8, 8), (0.2, 0.5), 0.012)],
    "hell": [((18, 8, 5), (0.3, 0.8), 0.04), ((120, 30, 5), (0.15, 0.3), 0.01)],
}
def _b(title, floors, walls, decor, solids, tint, ambient, music, enemies, bosses, extras=(), infest=0.3, stains=()):
    return dict(title=title, floors=floors, walls=walls, decor=decor, solids=solids, extras=list(extras), infest=infest, tint=tint,
                ambient=ambient, music=music, bias={e: 5.0 for e in enemies}, signature=list(enemies), bosses=bosses, stains=list(stains))


BIOMES.update({
    # ---- the seven circles
    "limbo": _b("CIRCLE I  -  LIMBO", [("floor_ash", 5), ("floor_marble", 4)], ["wall_marble", "wall_ruin"],
                ["ashpile", "skullpile", "corpse"], ["column_broken", "column_broken", "crate"], (205, 210, 225), "ash", "dread",
                ["shade", "hollow"], ["gatekeeper", "ashcolossus"], stains=[((70, 70, 72), (0.3, 0.8), 0.04)]),
    "lust": _b("CIRCLE II  -  LUST", [("floor_velvet", 4), ("floor_storm", 5)], ["wall_thorn", "wall_silk"],
               ["rosebush", "rosebush", "corpse"], ["lustbed", "crate", "barrel"], (255, 185, 225), "petals", "dread",
               ["siren", "thornling"], ["tempestqueen", "entwined"], stains=[((90, 10, 40), (0.3, 0.6), 0.03)]),
    "gluttony": _b("CIRCLE III  -  GLUTTONY", [("floor_mud", 5), ("floor_rot", 4)], ["wall_mudbrick", "wall_gorge"],
                   ["feast", "feast", "gorepile"], ["cauldron", "barrel", "crate"], (225, 215, 170), "rain", "deep",
                   ["glutton", "maggot"], ["gorged", "triplemaw"], infest=0.8, stains=[((60, 50, 18), (0.3, 0.8), 0.05)]),
    "greed": _b("CIRCLE IV  -  GREED", [("floor_gold", 4), ("floor_vault", 5)], ["wall_vault", "wall_hoard"],
                ["coinpile", "coinpile", "skullpile"], ["chest", "chest", "crate"], (255, 230, 175), "dust", "combat",
                ["hoarder", "goldgolem"], ["goldenmaw", "midasengine"], stains=[((140, 100, 20), (0.2, 0.5), 0.02)]),
    "wrath": _b("CIRCLE V  -  WRATH", [("floor_bog", 4), ("floor_peat", 5)], ["wall_bogrock", "wall_deadtree"],
                ["swampcorpse", "swampcorpse", "corpse"], ["deadtree", "deadtree", "barrel"], (175, 200, 175), "dust", "deep",
                ["berserker", "drowned"], ["wrathful", "leviathan"], stains=[((10, 16, 10), (0.4, 0.9), 0.05)]),
    "heresy": _b("CIRCLE VI  -  HERESY", [("floor_tomb", 5), ("floor_cinder", 4)], ["wall_tomb", "wall_pyre"],
                 ["candelabra", "candles", "skullpile"], ["burningtomb", "burningtomb", "sarcophagus"], (255, 195, 150), "embers", "inferno",
                 ["heretic", "pyrewraith"], ["archheretic", "tombtitan"], stains=[((18, 10, 6), (0.3, 0.8), 0.04)]),
    "violence": _b("CIRCLE VII  -  VIOLENCE", [("floor_bloodriver", 4), ("floor_thornwood", 5)], ["wall_thorntree", "wall_bloodrock"],
                   ["bloodpool", "gorepile", "skullpile"], ["spikerack", "impaler", "deadtree"], (255, 175, 165), "embers", "inferno",
                   ["flayed", "harpy"], ["butcherking", "thornmother"], infest=0.6, stains=[((110, 5, 5), (0.3, 0.8), 0.05)]),
    # ---- the industrial / gothic sites
    "nuclear": _b("REACTOR SITE", [("floor_reactor", 5), ("floor_radtile", 4)], ["wall_reactor", "wall_coolant"],
                  ["fuelrods", "cables", "corpse"], ["raddrum", "raddrum", "crate"], (200, 245, 185), "radglow", "combat",
                  ["meltgunner", "radhound"], ["coreabom", "liquidator"], stains=[((60, 150, 30), (0.2, 0.5), 0.02), ((20, 20, 22), (0.3, 0.6), 0.02)]),
    "biotech": _b("BIOTECH LABS", [("floor_cleanroom", 5), ("floor_biogrowth", 3)], ["wall_cleanroom", "wall_vat"],
                  ["spectable", "cables", "thingcorpse"], ["biovat", "biovat", "crate"], (200, 245, 245), "spores", "frost",
                  ["specimen", "sporewalker"], ["subjectzero", "hivemind"], stains=[((40, 120, 110), (0.2, 0.5), 0.02)]),
    "sewer": _b("THE TREATMENT PLANT", [("floor_sewer", 5), ("floor_sludge", 4)], ["wall_sewerbrick", "wall_outflow"],
                ["trashpile", "trashpile", "bodybag"], ["outflow", "barrel", "crate"], (215, 210, 170), "rain", "dread",
                ["eelmaw", "sludgegunner"], ["sewerking", "gatorbeast"], infest=0.6, stains=[((55, 45, 15), (0.3, 0.8), 0.05)]),
    "chemical": _b("CHEMICAL WORKS", [("floor_catwalk", 4), ("floor_corroded", 5)], ["wall_chemtank", "wall_corroded"],
                   ["valvestation", "cables", "corpse"], ["chemdrum", "chemdrum", "crate"], (230, 205, 245), "fumes", "combat",
                   ["meltman", "acidcrab"], ["distiller", "melttitan"], stains=[((120, 40, 150), (0.2, 0.5), 0.025), ((170, 160, 30), (0.2, 0.4), 0.02)]),
    "castle": _b("THE BLACK KEEP", [("floor_cobble", 5), ("floor_hall", 3)], ["wall_castle", "wall_keep"],
                 ["torchstand", "skullpile", "candles"], ["armorstand", "armorstand", "crate"], (255, 225, 195), "dust", "deep",
                 ["revenant", "bowman"], ["blackknight", "necroking"], stains=[((40, 30, 24), (0.3, 0.7), 0.03)]),
})
# bosses for the original environments too
for _name, _bosses in (("facility", ["liquidator", "subjectzero"]), ("ossuary", ["necroking", "gatekeeper"]),
                       ("otherworld", ["butcherking", "entwined"]), ("outpost", ["subjectzero", "hivemind"]), ("hell", ["wrathful", "archheretic"])):
    BIOMES[_name]["bosses"] = _bosses
for _name, _b_ in BIOMES.items():
    if _b_.get("stains"):
        STAINS[_name] = _b_["stains"]

ORDER = [n for n in BIOMES if n != "facility"]


def biome_for(depth, run_seed):
    """Sector 1 is always the facility; afterwards cycle a per-run shuffle of the others (facility mixed back in)."""
    if depth <= 1:
        return "facility"
    rng = random.Random(run_seed)
    order = ORDER[:]
    rng.shuffle(order)
    cycle = order + ["facility"]
    return cycle[(depth - 2) % len(cycle)]


# each biome's signature enemy spawns mostly at home (other biomes get it rarely via level.ENEMY_TABLE)
from bestiary import SIGNATURE as _SIG  # noqa: E402
for _b, _k in _SIG.items():
    BIOMES[_b]["bias"][_k] = 4.0
    BIOMES[_b]["signature"].append(_k)

# explosive barrels (fire / chemical / radiation / shrapnel kinds are rolled per barrel in World)
for _b in ("nuclear", "chemical", "biotech", "heresy", "violence"):
    BIOMES[_b]["solids"].append("barrel")

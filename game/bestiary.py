"""Data for the expansion bestiary: 24 enemies (behaviour + stats + weapon) and 24 bosses (phased attack lists).

Enemy ai kinds:  chaser | swarm | flyer | gunner | sniper | caster | lobber | spewer | charger | pouncer | exploder | riser | eel
Boss attacks:    aimed | fan | ring | spiral | wave | homing | mortar | charge | slam | laser | summon | flower | blink | eel
"""

RED = (125, 8, 6)
ICHOR = (70, 150, 25)
OIL = (28, 24, 32)
ASH = (60, 58, 56)
SOUL = (120, 160, 190)
GOLD = (200, 150, 30)
SLUDGE = (70, 55, 20)
RAD = (90, 200, 40)
CHEM = (130, 40, 160)

FLESHY = ["gib_meat", "gib_gut", "gib_bone", "gib_rib", "gib_eye", "gib_meat", "gib_jaw", "gib_skull"]
BONY = ["gib_bone", "gib_rib", "gib_skull", "gib_jaw", "gib_bone", "gib_rib"]
METAL = ["gib_metal", "gib_gear", "gib_wire", "gib_chrome", "gib_metal"]


def shot(kind="orb", speed=7.0, dmg=10, color=(255, 120, 60), r=0.16, count=1, spread=0.0, burst=1, gap=0.12, cd=(1.6, 2.4),
         rng=8.0, blast=0.0, homing=0.0, hazard=None):
    return dict(kind=kind, speed=speed, dmg=dmg, color=color, r=r, count=count, spread=spread, burst=burst, gap=gap, cd=cd,
                rng=rng, blast=blast, homing=homing, hazard=hazard)


ENEMIES = {
    # ---- Limbo
    "shade": dict(ai="flyer", hp=7, speed=2.3, r=0.3, dmg=12, score=220, hz=1.0, blood=SOUL, gibs=["gib_jaw", "gib_rib"], fly=True),
    "hollow": dict(ai="caster", hp=8, speed=1.2, r=0.3, dmg=10, score=200, hz=1.1, blood=ASH, gibs=BONY,
                   shot=shot("orb", 5.5, 10, (170, 210, 255), 0.2, cd=(2.0, 3.0), homing=0.6)),
    # ---- Lust
    "siren": dict(ai="caster", hp=8, speed=2.0, r=0.3, dmg=10, score=260, hz=1.2, blood=RED, gibs=FLESHY, fly=True,
                  shot=shot("orb", 6.0, 9, (255, 80, 170), 0.17, count=3, spread=0.35, cd=(1.6, 2.4), homing=1.2)),
    "thornling": dict(ai="swarm", hp=3, speed=3.0, r=0.25, dmg=7, score=60, hz=0.3, blood=RED, gibs=["gib_chitin", "gib_spiderleg"]),
    # ---- Gluttony
    "glutton": dict(ai="spewer", hp=22, speed=0.9, r=0.55, dmg=16, score=420, hz=1.0, blood=SLUDGE, gibs=FLESHY + ["gib_gut", "gib_gut"],
                    shot=shot("bile", 5.0, 6, (150, 130, 40), 0.18, count=7, spread=0.5, cd=(2.2, 3.0), rng=4.0, hazard="acid")),
    "maggot": dict(ai="swarm", hp=2, speed=1.5, r=0.22, dmg=5, score=40, hz=0.25, blood=(200, 190, 140), gibs=["gib_meat", "gib_leech"]),
    # ---- Greed
    "hoarder": dict(ai="gunner", hp=9, speed=1.5, r=0.3, dmg=10, score=280, hz=1.0, blood=RED, gibs=FLESHY,
                    shot=shot("coin", 9.0, 7, (255, 210, 60), 0.12, count=5, spread=0.5, cd=(1.6, 2.4))),
    "goldgolem": dict(ai="charger", hp=40, speed=1.0, r=0.6, dmg=24, score=650, hz=1.2, blood=GOLD, gibs=["gib_metal", "gib_metal", "gib_gear"]),
    # ---- Wrath
    "berserker": dict(ai="charger", hp=24, speed=1.8, r=0.5, dmg=20, score=480, hz=1.1, blood=RED, gibs=FLESHY + ["gib_bone"]),
    "drowned": dict(ai="riser", hp=10, speed=1.1, r=0.32, dmg=12, score=260, hz=1.0, blood=(50, 70, 30), gibs=FLESHY, then="lobber",
                    shot=shot("acid", 7.0, 10, (90, 160, 50), 0.22, cd=(2.4, 3.2), hazard="acid")),
    # ---- Heresy
    "heretic": dict(ai="caster", hp=10, speed=1.4, r=0.3, dmg=10, score=300, hz=1.1, blood=RED, gibs=FLESHY,
                    shot=shot("fireball", 7.0, 13, (255, 120, 30), 0.22, cd=(1.8, 2.6), blast=0.9)),
    "pyrewraith": dict(ai="exploder", hp=6, speed=2.4, r=0.3, dmg=0, score=200, hz=1.0, blood=ASH, gibs=BONY, boom=(1.6, 18, (255, 120, 30))),
    # ---- Violence
    "flayed": dict(ai="gunner", hp=10, speed=1.6, r=0.3, dmg=10, score=320, hz=1.0, blood=RED, gibs=FLESHY, melty=True,
                   shot=shot("bolt", 11.0, 7, (255, 70, 40), 0.13, burst=3, gap=0.12, cd=(1.6, 2.2))),
    "harpy": dict(ai="flyer", hp=8, speed=2.6, r=0.32, dmg=12, score=260, hz=1.3, blood=RED, gibs=FLESHY, fly=True),
    # ---- Nuclear
    "meltgunner": dict(ai="gunner", hp=11, speed=1.4, r=0.32, dmg=10, score=340, hz=1.0, blood=RAD, gibs=FLESHY, melty=True,
                       shot=shot("bolt", 10.0, 7, (140, 255, 60), 0.14, burst=4, gap=0.1, cd=(1.8, 2.4)), puddle=(80, 190, 40)),
    "radhound": dict(ai="pouncer", hp=8, speed=2.8, r=0.38, dmg=12, score=240, hz=0.6, blood=RAD, gibs=FLESHY),
    # ---- Biotech
    "specimen": dict(ai="pouncer", hp=10, speed=2.4, r=0.32, dmg=14, score=280, hz=1.0, blood=RED, gibs=FLESHY),
    "sporewalker": dict(ai="caster", hp=11, speed=1.2, r=0.32, dmg=10, score=300, hz=1.2, blood=ICHOR, gibs=FLESHY + ["gib_pod"],
                        shot=shot("spore", 4.5, 9, (90, 255, 210), 0.2, count=3, spread=0.6, cd=(2.2, 3.0), homing=1.0)),
    # ---- Sewage
    "eelmaw": dict(ai="eel", hp=16, speed=1.3, r=0.38, dmg=14, score=420, hz=1.0, blood=SLUDGE, gibs=FLESHY + ["gib_leech", "gib_leech"],
                   eels=2, eel_color=(120, 255, 170), reach=2.6),
    "sludgegunner": dict(ai="gunner", hp=11, speed=1.4, r=0.32, dmg=10, score=330, hz=1.0, blood=SLUDGE, gibs=FLESHY, melty=True,
                         shot=shot("bile", 9.0, 8, (190, 160, 60), 0.15, count=3, spread=0.25, cd=(1.6, 2.2)), puddle=(90, 70, 25)),
    # ---- Chemical
    "meltman": dict(ai="gunner", hp=12, speed=1.3, r=0.32, dmg=10, score=360, hz=1.0, blood=CHEM, gibs=FLESHY, melty=True,
                    shot=shot("bolt", 10.0, 8, (200, 90, 255), 0.14, burst=3, gap=0.1, cd=(1.5, 2.1)), puddle=(150, 60, 190)),
    "acidcrab": dict(ai="lobber", hp=7, speed=2.0, r=0.32, dmg=8, score=200, hz=0.4, blood=(200, 190, 40), gibs=["gib_chitin", "gib_spiderleg", "gib_chitin"],
                     shot=shot("acid", 7.0, 9, (230, 220, 40), 0.2, cd=(2.0, 3.0), hazard="acid")),
    # ---- Castle
    "revenant": dict(ai="charger", hp=26, speed=1.3, r=0.36, dmg=18, score=450, hz=1.1, blood=ASH, gibs=BONY + ["gib_metal", "gib_armor"]),
    "bowman": dict(ai="sniper", hp=7, speed=1.4, r=0.3, dmg=8, score=260, hz=1.1, blood=ASH, gibs=BONY,
                   shot=shot("bolt", 20.0, 16, (255, 230, 180), 0.12, cd=(2.4, 3.4), rng=12)),
}


def A(name, **kw):
    return (name, kw)


# Each boss: 3 phases (100-66%, 66-33%, 33-0%) of attack lists, escalating from simple to bullet hell.
BOSSES = {
    # a floating eye ringed with eyestalks: every stalk has its own ray (scorch / frost / venom / charm / death) and spits plasma
    "ocularch": dict(title="THE OCULARCH", r=1.0, speed=0.85, fly=True, color=(205, 120, 255), stalks=8, phases=[
        [A("eyebeams", n=2, sweep=0.4), A("eyeorbs", n=6), A("aimed", n=6, kind="bolt"), A("eyebeams", n=3, sweep=0.3)],
        [A("eyebeams", n=4, sweep=0.8), A("eyeorbs", n=10, homing=0.6), A("laser", sweep=1.8), A("ring", count=18, kind="plasma")],
        [A("eyebeams", n=6, sweep=1.3, duration=2.0), A("eyeorbs", n=16, homing=0.8, speed=6.5), A("laser", sweep=3.2),
         A("spiral", arms=5, duration=5, kind="plasma"), A("blink")]]),
    # Limbo
    "gatekeeper": dict(title="THE GATEKEEPER", r=1.0, speed=1.0, fly=True, color=(160, 210, 255), phases=[
        [A("aimed", n=5), A("ring", count=14), A("summon", kind="shade", n=3)],
        [A("spiral", arms=3, duration=4), A("homing", n=6), A("laser", sweep=1.4)],
        [A("flower", rings=6), A("spiral", arms=5, duration=5, spin=1.6), A("ring", count=30, waves=3), A("blink")]]),
    "ashcolossus": dict(title="ASHEN COLOSSUS", r=1.3, speed=0.8, color=(200, 190, 170), phases=[
        [A("slam", rings=1), A("fan", count=7), A("charge", n=1)],
        [A("mortar", n=6), A("slam", rings=2), A("charge", n=2), A("fan", count=11, waves=2)],
        [A("mortar", n=12), A("ring", count=36, waves=3), A("slam", rings=4), A("wave", duration=4)]]),
    # Lust
    "tempestqueen": dict(title="THE TEMPEST QUEEN", r=1.0, speed=1.6, fly=True, color=(255, 90, 190), phases=[
        [A("homing", n=4), A("fan", count=7), A("blink")],
        [A("spiral", arms=4, duration=4), A("wave", duration=3), A("homing", n=8)],
        [A("flower", rings=8), A("spiral", arms=6, duration=6, spin=2.2), A("wave", duration=5, amp=1.2), A("blink")]]),
    "entwined": dict(title="THE ENTWINED", r=1.2, speed=1.0, color=(255, 60, 120), eels=4, eel_color=(255, 80, 140), phases=[
        [A("eel"), A("aimed", n=6), A("charge", n=1)],
        [A("eel"), A("ring", count=20, waves=2), A("fan", count=9, waves=2)],
        [A("eel"), A("flower", rings=6), A("spiral", arms=4, duration=5), A("ring", count=40, waves=2)]]),
    # Gluttony
    "gorged": dict(title="THE GORGED", r=1.4, speed=0.6, color=(170, 150, 50), phases=[
        [A("fan", count=9, kind="bile"), A("summon", kind="maggot", n=5), A("slam", rings=1)],
        [A("mortar", n=8, kind="bile"), A("fan", count=13, waves=2, kind="bile"), A("summon", kind="maggot", n=8)],
        [A("ring", count=40, waves=3, kind="bile"), A("mortar", n=14, kind="bile"), A("spiral", arms=3, duration=5, kind="bile")]]),
    "triplemaw": dict(title="THE TRIPLE MAW", r=1.1, speed=1.8, color=(255, 120, 30), phases=[
        [A("fan", count=3, waves=3, kind="fireball"), A("charge", n=1), A("aimed", n=6)],
        [A("charge", n=3), A("ring", count=18, kind="fireball"), A("fan", count=9, waves=3)],
        [A("spiral", arms=3, duration=5), A("charge", n=4), A("flower", rings=5), A("mortar", n=10, kind="fireball")]]),
    # Greed
    "goldenmaw": dict(title="THE GOLDEN MAW", r=1.2, speed=1.2, color=(255, 210, 60), phases=[
        [A("fan", count=9, kind="coin"), A("charge", n=1), A("summon", kind="goldgolem", n=1)],
        [A("mortar", n=8, kind="coin"), A("fan", count=15, waves=2, kind="coin"), A("charge", n=2)],
        [A("flower", rings=7, kind="coin"), A("spiral", arms=6, duration=5, kind="coin"), A("mortar", n=16, kind="coin")]]),
    "midasengine": dict(title="THE MIDAS ENGINE", r=1.1, speed=0.9, color=(255, 200, 80), phases=[
        [A("aimed", n=10, interval=0.1), A("ring", count=16), A("homing", n=4)],
        [A("wave", duration=4), A("laser", sweep=1.6), A("ring", count=24, waves=3)],
        [A("spiral", arms=8, duration=6, spin=1.2), A("laser", sweep=3.0), A("flower", rings=8), A("wave", duration=5, amp=1.4)]]),
    # Wrath
    "wrathful": dict(title="THE WRATHFUL", r=1.3, speed=1.4, color=(255, 70, 30), phases=[
        [A("charge", n=2), A("slam", rings=1), A("fan", count=7)],
        [A("charge", n=3), A("slam", rings=3), A("ring", count=24, kind="fireball")],
        [A("charge", n=5), A("spiral", arms=4, duration=5, kind="fireball"), A("slam", rings=5), A("flower", rings=6)]]),
    "leviathan": dict(title="STYX LEVIATHAN", r=1.3, speed=0.9, color=(110, 230, 140), eels=4, eel_color=(90, 255, 160), phases=[
        [A("eel"), A("wave", duration=3, kind="acid_orb"), A("summon", kind="drowned", n=2)],
        [A("eel"), A("ring", count=24, waves=2), A("homing", n=6), A("mortar", n=8, kind="bile")],
        [A("eel"), A("spiral", arms=5, duration=5), A("flower", rings=7), A("wave", duration=5, amp=1.3)]]),
    # Heresy
    "archheretic": dict(title="THE ARCH-HERETIC", r=1.0, speed=1.2, fly=True, color=(255, 130, 40), phases=[
        [A("aimed", n=5, kind="fireball"), A("summon", kind="heretic", n=2), A("ring", count=12, kind="fireball")],
        [A("spiral", arms=3, duration=4, kind="fireball"), A("laser", sweep=1.5), A("blink"), A("homing", n=6)],
        [A("flower", rings=8, kind="fireball"), A("laser", sweep=3.2), A("spiral", arms=6, duration=6, spin=1.8), A("blink")]]),
    "tombtitan": dict(title="THE TOMB TITAN", r=1.4, speed=0.8, color=(255, 140, 40), phases=[
        [A("slam", rings=2), A("fan", count=9, kind="fireball"), A("charge", n=1)],
        [A("mortar", n=10, kind="fireball"), A("slam", rings=3), A("ring", count=24)],
        [A("mortar", n=16, kind="fireball"), A("spiral", arms=4, duration=5), A("slam", rings=5), A("ring", count=40, waves=3)]]),
    # Violence
    "butcherking": dict(title="THE BUTCHER KING", r=1.3, speed=1.3, color=(220, 40, 30), phases=[
        [A("charge", n=2), A("fan", count=5, waves=3), A("slam", rings=1)],
        [A("charge", n=3), A("mortar", n=8), A("fan", count=11, waves=3)],
        [A("charge", n=4), A("spiral", arms=4, duration=5), A("ring", count=36, waves=3), A("slam", rings=4)]]),
    "thornmother": dict(title="THE THORNMOTHER", r=1.3, speed=0.4, color=(200, 60, 60), eels=6, eel_color=(160, 90, 60), phases=[
        [A("eel"), A("ring", count=16, kind="thorn"), A("homing", n=4)],
        [A("eel"), A("summon", kind="thornling", n=5), A("wave", duration=4, kind="thorn"), A("ring", count=24, waves=2, kind="thorn")],
        [A("eel"), A("flower", rings=8, kind="thorn"), A("spiral", arms=6, duration=6, kind="thorn"), A("homing", n=10)]]),
    # Nuclear
    "coreabom": dict(title="CORE ABOMINATION", r=1.4, speed=0.6, color=(140, 255, 60), phases=[
        [A("ring", count=16), A("laser", sweep=1.2), A("summon", kind="meltgunner", n=2)],
        [A("spiral", arms=4, duration=4), A("mortar", n=10, kind="acid_orb"), A("laser", sweep=2.2)],
        [A("flower", rings=8), A("laser", sweep=3.4), A("spiral", arms=8, duration=6, spin=1.4), A("ring", count=48, waves=3)]]),
    "liquidator": dict(title="THE LIQUIDATOR", r=1.1, speed=1.1, color=(255, 210, 40), phases=[
        [A("aimed", n=14, interval=0.07), A("homing", n=4, kind="rocket"), A("charge", n=1)],
        [A("wave", duration=4), A("fan", count=11, waves=3), A("homing", n=6, kind="rocket")],
        [A("wave", duration=6, amp=1.4), A("spiral", arms=6, duration=5), A("homing", n=10, kind="rocket"), A("ring", count=40, waves=2)]]),
    # Biotech
    "subjectzero": dict(title="SUBJECT ZERO", r=1.3, speed=1.2, color=(90, 255, 220), eels=4, eel_color=(120, 255, 230), phases=[
        [A("eel"), A("charge", n=1), A("fan", count=7, kind="spore")],
        [A("eel"), A("homing", n=8, kind="spore"), A("summon", kind="specimen", n=2), A("charge", n=2)],
        [A("eel"), A("flower", rings=7, kind="spore"), A("spiral", arms=5, duration=5), A("charge", n=3)]]),
    "hivemind": dict(title="THE HIVE MIND", r=1.2, speed=0.8, fly=True, color=(120, 255, 230), phases=[
        [A("homing", n=6, kind="spore"), A("ring", count=18), A("summon", kind="sporewalker", n=2)],
        [A("laser", sweep=1.8), A("spiral", arms=4, duration=4), A("blink"), A("wave", duration=4)],
        [A("flower", rings=9), A("laser", sweep=3.4), A("spiral", arms=7, duration=6, spin=2.0), A("blink")]]),
    # Sewage
    "sewerking": dict(title="THE SEWER KING", r=1.4, speed=0.8, color=(160, 200, 80), eels=6, eel_color=(140, 255, 120), phases=[
        [A("eel"), A("fan", count=9, kind="bile"), A("summon", kind="eelmaw", n=1)],
        [A("eel"), A("mortar", n=10, kind="bile"), A("wave", duration=4, kind="bile"), A("summon", kind="sludgegunner", n=2)],
        [A("eel"), A("ring", count=40, waves=3, kind="bile"), A("spiral", arms=5, duration=6, kind="bile"), A("mortar", n=16, kind="bile")]]),
    "gatorbeast": dict(title="GATORBEAST", r=1.3, speed=1.6, color=(190, 210, 80), phases=[
        [A("charge", n=2), A("fan", count=7), A("slam", rings=1)],
        [A("charge", n=3), A("ring", count=20, waves=2), A("wave", duration=3)],
        [A("charge", n=5), A("spiral", arms=4, duration=5), A("flower", rings=6), A("slam", rings=4)]]),
    # Chemical
    "distiller": dict(title="THE DISTILLER", r=1.2, speed=0.9, color=(200, 90, 255), phases=[
        [A("mortar", n=6, kind="acid_orb"), A("aimed", n=10, interval=0.08), A("ring", count=14)],
        [A("wave", duration=4), A("mortar", n=12, kind="acid_orb"), A("homing", n=6)],
        [A("spiral", arms=6, duration=6), A("flower", rings=8), A("mortar", n=18, kind="acid_orb"), A("wave", duration=5, amp=1.3)]]),
    "melttitan": dict(title="THE MELTED TITAN", r=1.4, speed=0.9, color=(255, 220, 60), phases=[
        [A("aimed", n=12, interval=0.08), A("fan", count=7, waves=2), A("slam", rings=1)],
        [A("wave", duration=4), A("charge", n=2), A("ring", count=24, waves=2), A("mortar", n=8, kind="acid_orb")],
        [A("spiral", arms=4, duration=6), A("wave", duration=6, amp=1.5), A("flower", rings=7), A("slam", rings=4)]]),
    # Castle
    "blackknight": dict(title="THE BLACK KNIGHT", r=1.1, speed=1.5, color=(255, 60, 60), phases=[
        [A("charge", n=2), A("fan", count=5, waves=2), A("slam", rings=1)],
        [A("charge", n=3), A("summon", kind="revenant", n=2), A("fan", count=11, waves=3), A("blink")],
        [A("charge", n=5), A("ring", count=36, waves=3), A("spiral", arms=4, duration=5), A("slam", rings=4)]]),
    "necroking": dict(title="THE NECROMANCER KING", r=1.0, speed=1.1, fly=True, color=(150, 220, 255), phases=[
        [A("homing", n=5), A("summon", kind="bowman", n=2), A("ring", count=14)],
        [A("spiral", arms=4, duration=4), A("summon", kind="revenant", n=2), A("laser", sweep=1.6), A("blink")],
        [A("flower", rings=9), A("spiral", arms=7, duration=6, spin=1.6), A("homing", n=12), A("laser", sweep=3.0)]]),
}


# ---------------------------------------------------------------- signature enemies: one per biome, each with a unique mechanic
PINK = (190, 60, 110)
ENEMIES.update({
    "pinkmelt": dict(ai="pinkgunner", hp=12, speed=1.3, r=0.32, dmg=10, score=380, hz=1.0, blood=PINK, gibs=FLESHY, melty=True,
                     puddle=(200, 80, 140)),
    "bonepriest": dict(ai="summoner", hp=12, speed=1.2, r=0.3, dmg=8, score=420, hz=1.1, blood=ASH, gibs=BONY, summon=("crawler", 2, 6),
                       shot=shot("orb", 5.0, 9, (170, 220, 255), 0.18, cd=(2.4, 3.2), homing=0.8)),
    "rustbound": dict(ai="grappler", hp=26, speed=1.1, r=0.5, dmg=16, score=480, hz=1.2, blood=RED, gibs=FLESHY + METAL,
                      shot=dict(shot("chain", 12.0, 8, (150, 140, 130), 0.18, cd=(3.0, 4.0), rng=7.0), effect="pull")),
    "wendigo": dict(ai="pouncer", hp=14, speed=2.8, r=0.45, dmg=14, score=400, hz=0.8, blood=RED, gibs=FLESHY + BONY, on_hit="chill"),
    "cinderfiend": dict(ai="burrower", hp=14, speed=3.0, r=0.4, dmg=12, score=420, hz=0.5, blood=ASH, gibs=["gib_chitin", "gib_chitin", "gib_spiderleg"]),
    "mourner": dict(ai="statue", hp=20, speed=4.4, r=0.32, dmg=20, score=450, hz=1.2, blood=ASH, gibs=["gib_rubble", "gib_rubble", "gib_skull"]),
    "enthraller": dict(ai="charmer", hp=10, speed=1.8, r=0.32, dmg=10, score=420, hz=1.3, blood=RED, gibs=FLESHY, fly=True,
                       shot=dict(shot("orb", 4.0, 6, (255, 110, 200), 0.2, count=14, spread=6.0, cd=(3.0, 4.0), rng=8.0), effect="confuse")),
    "devourer": dict(ai="vacuum", hp=30, speed=0.8, r=0.6, dmg=22, score=500, hz=0.8, blood=SLUDGE, gibs=FLESHY + ["gib_gut", "gib_gut"]),
    "chestmimic": dict(ai="riser", then="caster", disguise="chest", wake=2.6, hp=18, speed=2.4, r=0.45, dmg=16, score=500, hz=0.6, blood=RED,
                       gibs=["gib_plank", "gib_plank", "gib_gut", "gib_meat", "gib_jaw"],
                       shot=shot("coin", 8.0, 7, (255, 210, 60), 0.13, count=7, spread=0.8, cd=(1.6, 2.4))),
    "boghag": dict(ai="geomancer", hp=12, speed=1.1, r=0.3, dmg=10, score=420, hz=1.1, blood=(50, 70, 30), gibs=FLESHY),
    "flagellant": dict(ai="zealot", hp=18, speed=1.4, r=0.32, dmg=14, score=420, hz=1.1, blood=RED, gibs=FLESHY),
    "hookman": dict(ai="boomerang", hp=16, speed=1.5, r=0.36, dmg=12, score=440, hz=1.1, blood=RED, gibs=FLESHY,
                    shot=shot("cleaver", 9.0, 14, (220, 80, 70), 0.24, cd=(2.0, 3.0), rng=7.0)),
    "raddrone": dict(ai="bomber", hp=10, speed=2.0, r=0.35, dmg=0, score=420, hz=1.6, blood=OIL, gibs=METAL, fly=True),
    "clone": dict(ai="splitter", hp=16, speed=1.9, r=0.32, dmg=12, score=260, hz=1.0, blood=(60, 150, 140), gibs=FLESHY),
    "lurker": dict(ai="lurker", hp=14, speed=2.2, r=0.4, dmg=14, score=440, hz=0.4, blood=SLUDGE, gibs=FLESHY + ["gib_leech"],
                   shot=shot("acid", 7.0, 10, (160, 140, 50), 0.22, cd=(1.0, 1.4), hazard="acid")),
    "hazmatsprayer": dict(ai="sprayer", hp=14, speed=1.3, r=0.33, dmg=8, score=420, hz=1.0, blood=RED, gibs=FLESHY + METAL,
                          shot=dict(shot("chem", 9.0, 3, (190, 235, 40), 0.22, count=3, spread=0.4, burst=8, gap=0.07, cd=(2.4, 3.2), rng=4.5), gas=5.0)),
    "shieldbearer": dict(ai="shield", hp=28, speed=1.1, r=0.4, dmg=16, score=480, hz=1.1, blood=ASH, gibs=BONY + METAL),
})
# ---------------------------------------------------------------- heavy gunners, vermin and fire demons
VENOM = (110, 190, 40)
ROACH = (150, 125, 60)
CHITIN = ["gib_chitin", "gib_chitin", "gib_spiderleg", "gib_gut", "gib_spiderleg"]
SCALY = ["gib_meat", "gib_gut", "gib_bone", "gib_rib", "gib_meat"]
DEVILISH = FLESHY + ["gib_bone", "gib_jaw"]
ENEMIES.update({
    # the Pink Melter's big brother: lugs a real heavy weapon (chaingun / railgun / barrage / tactical nuke) and may drop it
    "pinkheavy": dict(ai="pinkgunner", hp=42, speed=0.95, r=0.5, dmg=18, score=950, hz=1.5, blood=PINK, gibs=FLESHY + ["gib_gut", "gib_meat"],
                      melty=True, puddle=(200, 80, 140), stride=1.3, grip=(0.55, 1.05), drop=0.3,
                      arsenal=[("chaingun", 3.0), ("railgun", 3.0), ("barrage", 2.0), ("tac_nuke", 1.6)]),
    # snakes: weave in, coil, then strike; the bite poisons. The cobra also spits venom from range.
    "viper": dict(ai="snake", hp=6, speed=2.4, r=0.3, dmg=10, score=180, hz=0.3, blood=RED, gibs=SCALY, on_hit="poison", stride=0.8),
    "cobra": dict(ai="snake", hp=10, speed=2.0, r=0.33, dmg=11, score=280, hz=0.75, blood=RED, gibs=SCALY, on_hit="poison", stride=0.8,
                  shot=dict(shot("orb", 8.0, 6, (150, 235, 50), 0.13, count=2, spread=0.16, cd=(2.6, 3.4), rng=6.5), effect="poison",
                            dtype="chemical")),
    # armoured pincers soak most of what hits it from the front; the tail sting is telegraphed, hits hard and poisons badly
    "scorpion": dict(ai="scorpion", hp=18, speed=1.7, r=0.45, dmg=12, score=420, hz=0.5, blood=VENOM, gibs=CHITIN, armor=0.35, stride=1.0),
    # giant cockroaches come in packs, jink sideways when you aim at them and shrug off radiation and blasts
    "roach": dict(ai="roach", hp=4, speed=3.3, r=0.28, dmg=6, score=70, hz=0.25, blood=ROACH, gibs=CHITIN, pack=(3, 5), stride=0.6),
    # fire demons: flitting imps throw fireballs, pit demons breathe fire, devils hurl volleys of hellfire and blink away
    "imp": dict(ai="imp", hp=6, speed=2.6, r=0.26, dmg=8, score=170, hz=1.35, blood=RED, gibs=DEVILISH, fly=True, pack=(2, 3),
                shot=dict(shot("fireball", 7.5, 7, (255, 130, 40), 0.15, cd=(1.5, 2.3), rng=8.0, blast=0.6), effect="burn")),
    "pitdemon": dict(ai="breather", hp=34, speed=1.15, r=0.52, dmg=18, score=650, hz=1.45, blood=RED, gibs=DEVILISH + ["gib_gut"], stride=1.3),
    "devil": dict(ai="devil", hp=24, speed=1.6, r=0.36, dmg=14, score=750, hz=1.25, blood=RED, gibs=DEVILISH,
                  shot=dict(shot("fireball", 6.5, 12, (255, 100, 30), 0.24, count=3, spread=0.55, cd=(2.4, 3.2), rng=9.0, blast=1.0),
                            effect="burn")),
})
# extra damage resistances for single monsters, on top of their category (damage.KIND_MULT)
KIND_RESIST = {"roach": {"radiation": 0.15, "explosive": 0.5, "chemical": 0.5},
               "imp": {"fire": 0.1}, "pitdemon": {"fire": 0.0}, "devil": {"fire": 0.1}}

SIGNATURE = {"facility": "pinkmelt", "ossuary": "bonepriest", "otherworld": "rustbound", "outpost": "wendigo", "hell": "cinderfiend",
             "limbo": "mourner", "lust": "enthraller", "gluttony": "devourer", "greed": "chestmimic", "wrath": "boghag",
             "heresy": "flagellant", "violence": "hookman", "nuclear": "raddrone", "biotech": "clone", "sewer": "lurker",
             "chemical": "hazmatsprayer", "castle": "shieldbearer"}

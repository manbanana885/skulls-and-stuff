"""Who lives where. Every room is populated when the sector is built, with a group that fits the biome: one anchor
monster (picked from the biome's own roster) plus a few of its kin, laid out by role - shooters hang back from the
doorways, brawlers hold the middle, swarms bunch up, ambushers hug the walls. Now and then a room is built around a
spawning station (a carcass, a grave, a tank, a fabricator, a hell-gate or a nest) that keeps breeding its family.
World.update_trickle restocks rooms you haven't cleared yet, slowly and out of sight."""
import math
from bestiary import ENEMIES as BEST
from damage import CATEGORY

# the original monsters (not in the bestiary): (role, score)
BASE = {"zombie": ("melee", 100), "leech": ("swarm", 75), "crawler": ("swarm", 50), "drone": ("ranged", 200),
        "spitter": ("ranged", 150), "bloater": ("melee", 175), "stalker": ("melee", 300), "wretch": ("melee", 350),
        "mimic": ("ambush", 600), "spider": ("melee", 400), "turret": ("ambush", 250), "skull": ("swarm", 120),
        "hellspawn": ("melee", 300), "brute": ("melee", 700), "walker": ("ranged", 500)}
RANGED_AI = {"caster", "spewer", "gunner", "lobber", "sniper", "pinkgunner", "summoner", "geomancer", "charmer", "sprayer",
             "bomber", "breather", "devil", "boomerang"}
SWARM_AI = {"swarm", "roach", "imp"}
AMBUSH_AI = {"statue", "lurker", "eel", "riser"}

# spawning stations and the families they breed
STATIONS = {
    "carcass": ("maggot", "leech", "roach", "bloater"),
    "grave": ("zombie", "crawler", "skull", "wretch", "shade", "hollow", "drowned", "revenant", "bowman", "pyrewraith"),
    "vat": ("pinkmelt", "meltman", "meltgunner", "sludgegunner", "flayed", "specimen", "sporewalker", "clone", "stalker", "spitter",
            "pinkheavy"),
    "fabricator": ("drone", "raddrone", "walker"),
    "hellgate": ("imp", "hellspawn", "thornling", "harpy", "heretic", "siren", "berserker", "cinderfiend", "brute", "pitdemon", "devil"),
    "nest": ("spider", "viper", "cobra", "scorpion", "acidcrab", "radhound"),
}
STATION_OF = {k: st for st, ks in STATIONS.items() for k in ks}
STATION_RARE = {"pinkheavy": 0.15, "pitdemon": 0.3, "devil": 0.25, "brute": 0.4, "walker": 0.5}   # big ones hatch seldom
STATION_TITLE = {"carcass": "CARCASS", "grave": "GRAVE", "vat": "VAT", "fabricator": "FABRICATOR", "hellgate": "HELL-GATE",
                 "nest": "NEST"}


def role(kind):
    if kind in BASE:
        return BASE[kind][0]
    bd = BEST.get(kind, {})
    if bd.get("disguise"):
        return "ambush"
    ai = bd.get("ai")
    if ai in SWARM_AI or bd.get("pack"):
        return "swarm"
    if ai in AMBUSH_AI:
        return "ambush"
    if ai in RANGED_AI:
        return "ranged"
    return "melee"


def cost(kind):
    """How much of a room's budget one of these eats (roughly its threat)."""
    sc = BASE[kind][1] if kind in BASE else BEST.get(kind, {}).get("score", 200)
    return max(0.55, min(3.5, (sc / 140.0) ** 0.6))    # compressed: big brutes cost more, but not so much rooms empty out


def budget(depth, w, h):
    """A room's threat budget: rooms fill up as you go deeper, and big rooms hold more."""
    size = max(0.75, min(1.35, math.sqrt(w * h / 72.0)))
    return min(34.0, (4.0 + 2.3 * depth) * size)


def station_odds(depth):
    return min(0.3, 0.1 + 0.025 * depth)


def max_stations(depth):
    return min(4, 1 + depth // 3)


def weighted(rng, items):
    tot = sum(w for _, w in items)
    r = rng.uniform(0, tot)
    for v, w in items:
        r -= w
        if r <= 0:
            return v
    return items[-1][0]


def station_kinds(station, roster):
    """What a station breeds on this level: its family, as the biome weights them."""
    fam = set(STATIONS[station])
    return [(k, w * STATION_RARE.get(k, 1.0)) for k, w in roster if k in fam]


def compose(rng, L, room, free, roster, depth, allow_station=True, avoid=()):
    """Populate one room. free: the room's open cells (consumed as they're used).
    Returns (enemies [(kind, x, y)], station (name, x, y, kinds) or None, kinds the room restocks from)."""
    if not free or not roster:
        return [], None, []
    cells = [c for c in free if c not in avoid]
    if not cells:
        return [], None, []
    rx, ry, rw, rh = room.x, room.y, room.w, room.h
    ents = [(x, y) for x in range(rx - 1, rx + rw + 1) for y in (ry - 1, ry + rh)] + \
           [(x, y) for y in range(ry, ry + rh) for x in (rx - 1, rx + rw)]
    ents = [c for c in ents if 0 <= c[0] < L.W and 0 <= c[1] < L.H and L.solid[L.i(*c)] == 0] or [room.center]
    dist = {c: min(abs(c[0] - e[0]) + abs(c[1] - e[1]) for e in ents) for c in cells}
    maxd = max(dist.values()) or 1

    # ---- what lives here
    r = rng.random()
    typ = "quiet" if r < 0.12 else ("horde" if r < 0.42 else "squad")
    anchor = weighted(rng, roster)
    cat = CATEGORY.get(anchor)
    kin = [(k, w * (3.0 if CATEGORY.get(k) == cat else 0.3) * (2.0 if role(k) != role(anchor) else 1.0))
           for k, w in roster if k != anchor]
    B = budget(depth, rw, rh) * (0.45 if typ == "quiet" else 1.0)
    station = None
    if allow_station and anchor in STATION_OF and rng.random() < station_odds(depth):
        st = STATION_OF[anchor]
        sk = station_kinds(st, roster)
        if sk:
            station = st
            B *= 0.6                                        # it breeds more later
    escorts = []
    if kin:
        for _ in range(1 if typ == "horde" else rng.randint(1, 2)):
            k = weighted(rng, kin)
            if k not in escorts:
                escorts.append(k)
    picks, spent = [], 0.0
    for _ in range(90):
        if (spent >= B and picks) or len(picks) >= 30:
            break
        if not picks:
            k = anchor
        elif typ == "horde":
            k = anchor if (rng.random() < 0.8 or not escorts) else rng.choice(escorts)
        else:
            k = anchor if (rng.random() < 0.5 or not escorts) else rng.choice(escorts)
        pack = BEST.get(k, {}).get("pack")
        n = rng.randint(*pack) if pack else 1
        if picks and spent + cost(k) * n > B * 1.25:
            if spent >= B * 0.7:
                break
            continue
        picks += [k] * n
        spent += cost(k) * n

    # ---- where they stand
    used = set()
    out = []
    taken = set()

    def ok(c, spacing):
        return c not in taken and all((c[0] - u[0]) ** 2 + (c[1] - u[1]) ** 2 >= spacing * spacing for u in used)

    def place(c):
        taken.add(c)
        used.add(c)
        if c in free:
            free.remove(c)
        return c[0] + 0.5 + rng.uniform(-0.2, 0.2), c[1] + 0.5 + rng.uniform(-0.2, 0.2)

    def near(centre, spacing):
        best = sorted((c for c in cells if c not in taken), key=lambda c: (c[0] - centre[0]) ** 2 + (c[1] - centre[1]) ** 2)
        for c in best:
            if ok(c, spacing):
                return c
        return best[0] if best else None

    st_out = None
    centres = {}
    if station:
        back = sorted((c for c in cells if L.open_around(*c)), key=lambda c: -dist[c])
        if back:
            c = rng.choice(back[:max(1, len(back) // 4)])
            taken.add(c)
            if c in free:
                free.remove(c)
            st_out = (station, c[0] + 0.5, c[1] + 0.5, station_kinds(station, roster))
            for k in STATIONS[station]:
                centres[k] = c                              # its brood gathers round it
    mid = sorted(cells, key=lambda c: abs(dist[c] - maxd * 0.5))
    melee_c = rng.choice(mid[:max(1, len(mid) // 3)])
    back_cells = sorted(cells, key=lambda c: -dist[c])
    back_cells = back_cells[:max(3, len(back_cells) // 3)]
    walled = [c for c in cells if any(L.solid[L.i(c[0] + dx, c[1] + dy)] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for k in sorted(picks, key=lambda k: ("ambush", "ranged", "swarm", "melee").index(role(k))):
        rl = role(k)
        c = None
        if k in centres:
            c = near(centres[k], 0.9)
        elif rl == "ranged":
            opts = [c_ for c_ in back_cells if ok(c_, 1.6)] or [c_ for c_ in back_cells if c_ not in taken]
            c = rng.choice(opts) if opts else None
        elif rl == "ambush":
            opts = [c_ for c_ in walled if ok(c_, 2.0)]
            c = rng.choice(opts) if opts else None
        elif rl == "swarm":
            if k not in centres:
                centres[k] = rng.choice(back_cells + mid[:max(1, len(mid) // 3)])
            c = near(centres[k], 0.7)
        else:
            c = near(melee_c, 1.1)
        if c is None:
            c = near(melee_c, 0.6)
        if c is None:
            break
        x, y = place(c)
        out.append((k, x, y))
    kinds = [(anchor, 3.0)] + [(k, 1.0) for k in escorts]
    return out, st_out, kinds

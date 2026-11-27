# Expansion assets: 12 environments (tile style kit), 24 enemies and 24 bosses (parametric creature generator).
# Exec'd from build_assets.py so it shares its helpers (box, cyl, sphere, bone, M, RNG, ASSETS, ...).

# ---------------------------------------------------------------- materials
for _n, _c, _m, _r in (
    ("ash", (0.32, 0.31, 0.3), 0.0, 0.95), ("marble", (0.62, 0.6, 0.56), 0.1, 0.35), ("marble2", (0.45, 0.43, 0.4), 0.1, 0.4),
    ("velvet", (0.28, 0.03, 0.12), 0.0, 0.8), ("silk", (0.5, 0.05, 0.1), 0.0, 0.5), ("darkwood", (0.07, 0.04, 0.03), 0.0, 0.8),
    ("rose", (0.5, 0.01, 0.03), 0.0, 0.5), ("mud", (0.14, 0.09, 0.05), 0.0, 0.6), ("mud2", (0.09, 0.06, 0.03), 0.0, 0.3),
    ("rot", (0.2, 0.18, 0.06), 0.0, 0.5), ("gold", (0.8, 0.55, 0.12), 1.0, 0.25), ("gilded", (0.45, 0.3, 0.06), 0.8, 0.35),
    ("bog", (0.01, 0.02, 0.015), 0.0, 0.04), ("peat", (0.06, 0.05, 0.03), 0.0, 0.9), ("deadwood", (0.12, 0.09, 0.07), 0.0, 0.85),
    ("tombstone", (0.2, 0.19, 0.18), 0.0, 0.85), ("cinder", (0.05, 0.04, 0.035), 0.0, 0.95), ("bloodwater", (0.3, 0.0, 0.0), 0.0, 0.05),
    ("wood", (0.25, 0.14, 0.06), 0.0, 0.7), ("iron", (0.1, 0.1, 0.11), 0.8, 0.5), ("banner", (0.4, 0.02, 0.02), 0.0, 0.8),
    ("cobble", (0.22, 0.21, 0.2), 0.0, 0.9), ("carpet", (0.35, 0.02, 0.03), 0.0, 0.9), ("sewerbrick", (0.22, 0.12, 0.07), 0.0, 0.85),
    ("sludge", (0.12, 0.1, 0.03), 0.0, 0.08), ("lead", (0.2, 0.21, 0.22), 0.6, 0.6), ("corroded", (0.2, 0.22, 0.15), 0.5, 0.7),
    ("plague", (0.4, 0.42, 0.25), 0.0, 0.55), ("melt", (0.55, 0.3, 0.28), 0.0, 0.08), ("meltgreen", (0.3, 0.45, 0.12), 0.0, 0.08),
    ("bull", (0.2, 0.1, 0.07), 0.0, 0.7), ("hazmat", (0.75, 0.6, 0.08), 0.1, 0.5), ("whitecoat", (0.75, 0.76, 0.75), 0.0, 0.8),
    ("robe", (0.1, 0.05, 0.06), 0.0, 0.9), ("robe2", (0.25, 0.04, 0.02), 0.0, 0.9), ("teal", (0.1, 0.4, 0.42), 0.2, 0.4),
):
    mat(_n, _c, _m, _r)
mat("ghost", (0.6, 0.8, 0.85), 0.0, 0.2, (0.3, 0.55, 0.6), 1.2, alpha=0.45)
mat("radglow", (0.4, 1.0, 0.2), 0, 0.3, (0.35, 1.0, 0.1), 7.0)
mat("tealglow", (0.1, 0.9, 0.8), 0, 0.3, (0.1, 0.9, 0.8), 5.0)
mat("purpleglow", (0.7, 0.1, 1.0), 0, 0.3, (0.6, 0.05, 1.0), 5.0)
mat("pinkglow", (1.0, 0.2, 0.6), 0, 0.3, (1.0, 0.15, 0.55), 5.0)
mat("chemyellow", (0.9, 0.8, 0.05), 0, 0.2, (0.9, 0.75, 0.05), 2.5)
mat("chempurple", (0.5, 0.05, 0.6), 0, 0.1, (0.5, 0.05, 0.7), 2.0)
mat("soul", (0.7, 0.9, 1.0), 0, 0.3, (0.6, 0.85, 1.0), 4.0)
mat("torchflame", (1.0, 0.55, 0.1), 0, 0.3, (1.0, 0.5, 0.08), 8.0)


# ---------------------------------------------------------------- tile style kit
def f_layer(r, kind, a, b):
    """Top surface patterns for floors. a/b are material names."""
    if kind == "flag":
        layout = RNG.choice(["2x2", "3x3", "long"])
        if layout == "2x2":
            rects = [(x, y, 0.46, 0.46) for x in (-0.25, 0.25) for y in (-0.25, 0.25)]
        elif layout == "3x3":
            rects = [(x, y, 0.3, 0.3) for x in (-0.33, 0, 0.33) for y in (-0.33, 0, 0.33)]
        else:
            rects = [(-0.25, 0, 0.46, 0.95), (0.25, -0.25, 0.46, 0.46), (0.25, 0.25, 0.46, 0.46)]
        for k, (x, y, w, h) in enumerate(rects):
            if not chance(0.05):
                box("fl%d" % k, (w, h, 0.03), (x, y, 0.004 + RNG.uniform(0, 0.012)), M[a if chance(0.8) else b], r,
                    (RNG.uniform(-0.02, 0.02), RNG.uniform(-0.02, 0.02), RNG.uniform(-0.04, 0.04)))
    elif kind == "plates":
        plates("pl", r, a, RNG.choice(["one", "twox", "twoy", "four", "three"]))
    elif kind == "tiles":
        n = RNG.choice([2, 3, 4])
        st = 1.0 / n
        for i in range(n):
            for j in range(n):
                if chance(0.04):
                    continue
                box("t%d%d" % (i, j), (st - 0.025, st - 0.025, 0.02), (-0.5 + st * (i + 0.5), -0.5 + st * (j + 0.5), 0.0),
                    M[a if (i + j) % 2 == 0 or chance(0.5) else b], r)
    elif kind == "planks":
        along = chance(0.5)
        for k in range(6):
            u = -0.42 + k * 0.168
            L = 1.0 if chance(0.7) else RNG.uniform(0.4, 0.7)
            off = 0 if L == 1.0 else RNG.uniform(-0.25, 0.25)
            size = (L, 0.15, 0.03) if along else (0.15, L, 0.03)
            box("pk%d" % k, size, ((off, u, 0.005) if along else (u, off, 0.005)), M[a if chance(0.85) else b], r,
                (0, 0, RNG.uniform(-0.02, 0.02)))
    elif kind == "cobble":
        for k in range(RNG.randint(14, 20)):
            s = RNG.uniform(0.12, 0.2)
            sphere("cb%d" % k, s, (RNG.uniform(-0.42, 0.42), RNG.uniform(-0.42, 0.42), -0.035), M[a if chance(0.8) else b], r,
                   (1, RNG.uniform(0.8, 1.2), 0.25), 7, 4)
    elif kind == "liquid":
        box("liq", (1.0, 1.0, 0.02), (0, 0, -0.03), M[a], r)
        for k in range(RNG.randint(0, 4)):
            s = RNG.uniform(0.08, 0.2)
            sphere("isl%d" % k, s, (RNG.uniform(-0.38, 0.38), RNG.uniform(-0.38, 0.38), -0.04), M[b], r, (1, 1, 0.35), 7, 4)
    elif kind == "grate":
        box("liq", (0.95, 0.95, 0.01), (0, 0, -0.06), M[b], r)
        n = RNG.randint(5, 7)
        along = chance(0.5)
        for k in range(n):
            u = -0.42 + k * 0.84 / (n - 1)
            size = (0.98, 0.04, 0.04) if along else (0.04, 0.98, 0.04)
            box("gb%d" % k, size, ((0, u, -0.02) if along else (u, 0, -0.02)), M[a], r)
    elif kind == "carpet":
        f_layer(r, "flag", "cobble", "stone")
        along = chance(0.5)
        size = (1.0, 0.6, 0.012) if along else (0.6, 1.0, 0.012)
        box("carpet", size, (0, 0, 0.022), M[a], r)
        trim = (1.0, 0.04, 0.014) if along else (0.04, 1.0, 0.014)
        for s_ in (-1, 1):
            box("trim%d" % s_, trim, ((0, s_ * 0.3, 0.024) if along else (s_ * 0.3, 0, 0.024)), M[b], r)
    elif kind == "earth":
        for k in range(RNG.randint(6, 10)):
            s = RNG.uniform(0.12, 0.28)
            sphere("e%d" % k, s, (RNG.uniform(-0.4, 0.4), RNG.uniform(-0.4, 0.4), -0.05), M[a if chance(0.7) else b], r,
                   (1.2, 1, 0.3), 8, 5, True)


def f_feature(r, name, p):
    if not chance(p[0] if isinstance(p, tuple) else p):
        return
    arg = p[1] if isinstance(p, tuple) and len(p) > 1 else None
    z = 0.03
    if name == "cracks":
        rnd_cracks("ck", r, z, RNG.randint(1, 3), arg or "black")
    elif name == "debris":
        rnd_debris("db", r, arg or ["concrete2", "stone"], RNG.randint(1, 4), z)
    elif name == "stain":
        rnd_stain("st", r, arg or "blood", 1.0, z, (0.15, 0.35))
    elif name == "bones":
        x, y, a, L = RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), RNG.uniform(0, PI), RNG.uniform(0.15, 0.3)
        bone_prop("fb", (x - math.cos(a) * L / 2, y - math.sin(a) * L / 2, z), (x + math.cos(a) * L / 2, y + math.sin(a) * L / 2, z), r)
    elif name == "skull":
        skull_prop("fs", (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), z - 0.02), r, RNG.uniform(0.8, 1.1), RNG.uniform(0, 6.28), arg)
    elif name == "coins":
        for k in range(RNG.randint(4, 14)):
            cyl("coin%d" % k, 0.035, 0.01, (RNG.uniform(-0.4, 0.4), RNG.uniform(-0.4, 0.4), z + RNG.uniform(0, 0.02)), M["gold"], r,
                (RNG.uniform(-0.4, 0.4), RNG.uniform(-0.4, 0.4), 0), segs=8)
    elif name == "roots":
        for k in range(RNG.randint(1, 3)):
            a0 = RNG.uniform(0, 2 * PI)
            wire("rt%d" % k, (math.cos(a0) * 0.5, math.sin(a0) * 0.5, z), (RNG.uniform(-0.2, 0.2), RNG.uniform(-0.2, 0.2), z), -0.02, 0.022,
                 M[arg or "deadwood"], r, 5, wobble=0.05)
    elif name == "thorns":
        for k in range(RNG.randint(3, 7)):
            x, y = RNG.uniform(-0.4, 0.4), RNG.uniform(-0.4, 0.4)
            spike("th%d" % k, (x, y, z), (x + RNG.uniform(-0.05, 0.05), y + RNG.uniform(-0.05, 0.05), z + RNG.uniform(0.06, 0.15)), 0.015,
                  M["darkwood"], r)
    elif name == "glowcracks":
        for k in range(RNG.randint(1, 3)):
            box("gc%d" % k, (RNG.uniform(0.15, 0.4), 0.02, 0.012), (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), z - 0.015), M[arg], r,
                (0, 0, RNG.uniform(0, PI)))
    elif name == "moss":
        for k in range(RNG.randint(2, 5)):
            box("ms%d" % k, (RNG.uniform(0.04, 0.12), RNG.uniform(0.04, 0.12), 0.006), (RNG.uniform(-0.4, 0.4), RNG.uniform(-0.4, 0.4), z),
                M["moss"], r)
    elif name == "drain":
        cyl("drn", 0.12, 0.01, (RNG.uniform(-0.2, 0.2), RNG.uniform(-0.2, 0.2), z - 0.01), M["black"], r, segs=10)
    elif name == "hazard":
        box("hz", (0.9, 0.07, 0.01), (0, RNG.choice((-0.4, 0.4)), z - 0.01), M["hazard"], r)
    elif name == "candle":
        candle("cd", (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), z - 0.01), RNG.uniform(0.05, 0.14), r)
    elif name == "papers":
        for k in range(RNG.randint(1, 3)):
            box("pp%d" % k, (0.12, 0.09, 0.003), (RNG.uniform(-0.35, 0.35), RNG.uniform(-0.35, 0.35), z), M["paper"], r,
                (0, 0, RNG.uniform(0, PI)))
    elif name == "biomass":
        for k in range(RNG.randint(2, 5)):
            sphere("bm%d" % k, RNG.uniform(0.07, 0.16), (RNG.uniform(-0.38, 0.38), RNG.uniform(-0.38, 0.38), z - 0.04), M[arg or "teal"], r,
                   (1, 1, 0.4), 8, 5, True)
        sphere("bmg", 0.035, (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), z), M["tealglow"], r)
    elif name == "puddle":
        rnd_stain("pd", r, arg or "water", 1.0, z - 0.02, (0.2, 0.45))
    elif name == "leaves":
        for k in range(RNG.randint(4, 9)):
            box("lf%d" % k, (0.06, 0.035, 0.004), (RNG.uniform(-0.42, 0.42), RNG.uniform(-0.42, 0.42), z), M[arg or "rose"], r,
                (0, 0, RNG.uniform(0, PI)))
    elif name == "pipe":
        y0 = RNG.uniform(-0.35, 0.35)
        cyl("fp", 0.05, 1.02, (0, y0, 0.05), M[arg or "steel2"], r, rot=(0, PI / 2, 0), segs=8)
    elif name == "embers":
        for k in range(RNG.randint(3, 8)):
            sphere("em%d" % k, 0.015, (RNG.uniform(-0.42, 0.42), RNG.uniform(-0.42, 0.42), z), M["ember"], r, segs=5, rings=3)
    elif name == "rubble":
        rnd_debris("rb", r, arg or ["marble2", "marble"], RNG.randint(2, 5), z, (0.05, 0.12))


def style_floor(base, layer, a, b, feats, top=0.0):
    def build():
        r = tile_root()
        slab(M[base], top)
        f_layer(r, layer, a, b)
        for name, p in feats:
            f_feature(r, name, p)
        return r, None
    return build


def w_face(r, kind, a, b):
    if kind == "bricks":
        for row in range(7):
            z = 0.07 + row * 0.14
            box("brx%d" % row, (0.012, 1.0, 0.012), (0.505, 0, z + 0.07), M[b], r)
            box("bry%d" % row, (1.0, 0.012, 0.012), (0, 0.505, z + 0.07), M[b], r)
            off = 0.12 if row % 2 else -0.12
            for k in (-1, 0, 1):
                box("bvx%d%d" % (row, k), (0.012, 0.012, 0.14), (0.505, off + k * 0.33, z), M[b], r)
                box("bvy%d%d" % (row, k), (0.012, 0.012, 0.14), (off + k * 0.33, 0.505, z), M[b], r)
    elif kind == "stone":
        stone_faces(r, b)
    elif kind == "panels":
        for nm, loc, size in (("px", (0.505, 0, 0.45), (0.02, 0.72, 0.6)), ("py", (0, 0.505, 0.45), (0.72, 0.02, 0.6))):
            box("pn" + nm, size, loc, M[b], r)
        bolts("pbx", (0.517, 0, 0.45), "x", 0.38, r, 4)
        bolts("pby", (0, 0.517, 0.45), "y", 0.38, r, 4)
    elif kind == "planks":
        for k in range(6):
            u = -0.42 + k * 0.168
            box("wpx%d" % k, (0.02, 0.15, 1.0), (0.51, u, 0.5), M[a if chance(0.8) else b], r)
            box("wpy%d" % k, (0.15, 0.02, 1.0), (u, 0.51, 0.5), M[a if chance(0.8) else b], r)
    elif kind == "rough":
        for k in range(8):
            sz = RNG.uniform(0.2, 0.4)
            box("rk%d" % k, (sz, sz, sz), (RNG.uniform(-0.4, 0.45), RNG.uniform(-0.4, 0.45), RNG.uniform(0.1, 1.0)), M[a if chance(0.7) else b],
                r, (RNG.uniform(0, 1), RNG.uniform(0, 1), RNG.uniform(0, 1)))
    elif kind == "organic":
        for k in range(12):
            face = k % 2
            u, z = RNG.uniform(-0.45, 0.45), RNG.uniform(0.0, 0.95)
            rad = RNG.uniform(0.1, 0.2)
            sphere("og%d" % k, rad, ((0.47, u, z) if face == 0 else (u, 0.47, z)), M[a if chance(0.6) else b], r,
                   ((0.6, 1, 1) if face == 0 else (1, 0.6, 1)), 8, 6, True)
    elif kind == "trunks":
        for k in range(RNG.randint(3, 5)):
            x, y = RNG.uniform(-0.35, 0.35), RNG.uniform(-0.35, 0.35)
            cyl("tr%d" % k, RNG.uniform(0.12, 0.22), 1.1, (x, y, 0.55), M[a], r, segs=7, r2=RNG.uniform(0.05, 0.12))
            for j in range(RNG.randint(1, 3)):
                zz = RNG.uniform(0.4, 1.0)
                ang = RNG.uniform(0, 2 * PI)
                spike("br%d%d" % (k, j), (x, y, zz), (x + math.cos(ang) * 0.45, y + math.sin(ang) * 0.45, zz + RNG.uniform(0.1, 0.3)), 0.04,
                      M[a], r)


def w_feature(r, name, p):
    if not chance(p[0] if isinstance(p, tuple) else p):
        return
    arg = p[1] if isinstance(p, tuple) and len(p) > 1 else None
    u = RNG.uniform(-0.3, 0.3)
    on_x = chance(0.6)

    def at(x_face, along, z):
        return (x_face, along, z) if on_x else (along, x_face, z)
    if name == "banner":
        box("ban", (0.02, 0.26, 0.55) if on_x else (0.26, 0.02, 0.55), at(0.52, u, 0.55), M[arg or "banner"], r)
        box("bant", (0.03, 0.3, 0.03) if on_x else (0.3, 0.03, 0.03), at(0.53, u, 0.84), M["gold"], r)
        sphere("bane", 0.04, at(0.53, u, 0.5), M["gold"], r)
    elif name == "torch":
        bone("tch", at(0.5, u, 0.6), at(0.62, u, 0.72), 0.02, M["iron"], r)
        sphere("tfl", 0.05, at(0.64, u, 0.78), M["torchflame"], r, (1, 1, 1.6), 6, 4)
    elif name == "pipes":
        for k in range(RNG.randint(1, 3)):
            uu = RNG.uniform(-0.4, 0.4)
            cyl("wpp%d" % k, RNG.uniform(0.04, 0.07), 1.0, at(0.54, uu, 0.5), M[arg or "steel2"], r)
    elif name == "glowstrip":
        z = RNG.uniform(0.6, 0.9)
        box("gsx", (0.02, 0.8, 0.04), (0.515, 0, z), M[arg], r)
        box("gsy", (0.8, 0.02, 0.04), (0, 0.515, z), M[arg], r)
    elif name == "sign":
        box("sg", (0.01, 0.22, 0.22) if on_x else (0.22, 0.01, 0.22), at(0.515, u, 0.55), M["hazard"], r)
        cyl("sgc", 0.05, 0.01, at(0.52, u, 0.55), M["black"], r, rot=((0, PI / 2, 0) if on_x else (PI / 2, 0, 0)), segs=3)
    elif name == "thorns":
        for k in range(RNG.randint(2, 4)):
            p1 = at(0.53, RNG.uniform(-0.45, 0.45), 1.0)
            p2 = at(0.56, RNG.uniform(-0.45, 0.45), 0.05)
            wire("vn%d" % k, p1, p2, 0.0, 0.02, M["darkwood"], r, 7, wobble=0.06)
            for j in range(3):
                q = Vector(p1).lerp(Vector(p2), RNG.random())
                spike("vt%d%d" % (k, j), q, q + Vector((0.06, 0.02, 0.03) if on_x else (0.02, 0.06, 0.03)), 0.012, M["darkwood"], r)
            if arg:
                sphere("vr%d" % k, 0.05, Vector(p1).lerp(Vector(p2), RNG.random()), M[arg], r, segs=6, rings=4)
    elif name == "drips":
        for k in range(RNG.randint(2, 5)):
            drip("dr%d" % k, at(0.52, RNG.uniform(-0.4, 0.4), RNG.uniform(0.6, 1.0)), RNG.uniform(0.1, 0.35), 0.02, M[arg or "slime"], r)
    elif name == "smear":
        smear("sm", at(0.515, u, RNG.uniform(0.3, 0.7)), "x" if on_x else "y", RNG.uniform(0.25, 0.45), r, M[arg or "blood"], 4)
    elif name == "chains":
        for k in range(RNG.randint(1, 3)):
            y0 = RNG.uniform(-0.35, 0.35)
            wire("ch%d" % k, at(0.55, y0, 1.0), at(0.56, y0 + 0.02, RNG.uniform(0.3, 0.7)), 0.0, 0.012, M["iron"], r, 6, wobble=0.01)
    elif name == "window":
        box("win", (0.02, 0.4, 0.22) if on_x else (0.4, 0.02, 0.22), at(0.51, u, 0.62), M["black"], r)
        box("wl", (0.01, 0.36, 0.05) if on_x else (0.36, 0.01, 0.05), at(0.515, u, 0.55), M[arg or "glow_orange"], r)
    elif name == "skulls":
        for k in range(RNG.randint(2, 4)):
            skull_prop("ws%d" % k, at(0.47, RNG.uniform(-0.35, 0.35), RNG.uniform(0.15, 0.8)), r, 1.1, 0.0 if on_x else PI / 2, bloody=chance(0.4))
    elif name == "coins":
        for k in range(RNG.randint(5, 12)):
            cyl("wc%d" % k, 0.035, 0.012, at(0.51, RNG.uniform(-0.45, 0.45), RNG.uniform(0.05, 0.95)), M["gold"], r,
                rot=((0, PI / 2, 0) if on_x else (PI / 2, 0, 0)), segs=8)
    elif name == "column":
        for x, y in ((0.45, 0.45),):
            cyl("col", 0.09, 1.0, (x, y, 0.5), M[arg or "marble"], r, segs=10)
            box("colcap", (0.22, 0.22, 0.06), (x, y, 1.0), M[arg or "marble"], r)
    elif name == "valve":
        ring("vl", 0.08, 0.02, at(0.62, u, 0.55), M["armor"], r, rot=((0, PI / 2, 0) if on_x else (PI / 2, 0, 0)), segs=10)
        bone("vls", at(0.55, u, 0.55), at(0.62, u, 0.55), 0.015, M["chrome"], r)
    elif name == "gauge":
        cyl("gg", 0.06, 0.03, at(0.52, u, 0.7), M["white"], r, rot=((0, PI / 2, 0) if on_x else (PI / 2, 0, 0)), segs=10)
        box("ggn", (0.01, 0.05, 0.008) if on_x else (0.05, 0.01, 0.008), at(0.54, u, 0.71), M["glow_red"], r)
    elif name == "vat":
        cyl("vt", 0.2, 0.7, at(0.55, u, 0.45), M["glass"], r, segs=12)
        cyl("vtl", 0.16, 0.6, at(0.55, u, 0.42), M[arg or "tealglow"], r, segs=10)
        cyl("vtc", 0.22, 0.06, at(0.55, u, 0.82), M["steel2"], r, segs=12)
    elif name == "fire":
        for k in range(RNG.randint(3, 6)):
            base = Vector((RNG.uniform(-0.35, 0.35), RNG.uniform(-0.35, 0.35), 1.03))
            spike("wf%d" % k, base, base + Vector((0, 0, RNG.uniform(0.15, 0.35))), 0.06, M["flame" if k % 2 else "flame2"], r)
    elif name == "shield":
        cyl("sh", 0.14, 0.03, at(0.53, u, 0.55), M[arg or "iron"], r, rot=((0, PI / 2, 0) if on_x else (PI / 2, 0, 0)), segs=10)
        cyl("shb", 0.05, 0.04, at(0.54, u, 0.55), M["gold"], r, rot=((0, PI / 2, 0) if on_x else (PI / 2, 0, 0)), segs=8)
    elif name == "glowcracks":
        for k in range(RNG.randint(2, 4)):
            z = RNG.uniform(0.1, 0.9)
            box("wgc%d" % k, (0.02, RNG.uniform(0.15, 0.4), 0.025) if on_x else (RNG.uniform(0.15, 0.4), 0.02, 0.025),
                at(0.51, RNG.uniform(-0.3, 0.3), z), M[arg], r, ((RNG.uniform(-0.8, 0.8), 0, 0) if on_x else (0, RNG.uniform(-0.8, 0.8), 0)))
    elif name == "radsign":
        cyl("rs", 0.12, 0.01, at(0.515, u, 0.6), M["hazard"], r, rot=((0, PI / 2, 0) if on_x else (PI / 2, 0, 0)), segs=12)
        for k in range(3):
            a = k * 2 * PI / 3
            box("rsb%d" % k, (0.01, 0.06, 0.06) if on_x else (0.06, 0.01, 0.06),
                at(0.52, u + math.cos(a) * 0.06, 0.6 + math.sin(a) * 0.06), M["black"], r)
    elif name == "face":
        sphere("fc", 0.13, at(0.48, u, 0.55), M["deadwood"], r, ((0.5, 1, 1.3) if on_x else (1, 0.5, 1.3)), 8, 6, True)
        for s_ in (-1, 1):
            sphere("fce%d" % s_, 0.025, at(0.55, u + s_ * 0.04, 0.6), M[arg or "glow_red"], r)
        box("fcm", (0.02, 0.06, 0.04) if on_x else (0.06, 0.02, 0.04), at(0.55, u, 0.5), M["black"], r)
    elif name == "moss":
        for k in range(RNG.randint(2, 5)):
            box("wm%d" % k, (0.02, RNG.uniform(0.08, 0.25), RNG.uniform(0.06, 0.25)) if on_x else (RNG.uniform(0.08, 0.25), 0.02, RNG.uniform(0.06, 0.25)),
                at(0.505, RNG.uniform(-0.4, 0.4), RNG.uniform(0.05, 0.5)), M["moss"], r)


def style_wall(base, cap, face, a, b, feats):
    def build():
        r = wall_base(base, cap)
        w_face(r, face, a, b)
        for name, p in feats:
            w_feature(r, name, p)
        return r, None
    return build


# 12 environments: 2 floors + 2 walls each (props below)
TILES = {
    # Circle I - Limbo
    "floor_ash": style_floor("ash", "earth", "ash", "marble2", [("rubble", 0.6), ("bones", 0.3), ("skull", 0.15), ("cracks", 0.3)]),
    "floor_marble": style_floor("marble2", "tiles", "marble", "marble2", [("cracks", (0.8, "marble2")), ("rubble", 0.5), ("stain", (0.2, "ash"))]),
    "wall_marble": style_wall("marble", "marble2", "stone", "marble", "marble2", [("column", 0.5), ("smear", (0.2, "ash")), ("moss", 0.3), ("skulls", 0.2)]),
    "wall_ruin": style_wall("marble2", "ash", "rough", "marble2", "marble", [("column", 0.6), ("moss", 0.4), ("chains", 0.2)]),
    # Circle II - Lust
    "floor_velvet": style_floor("stone", "carpet", "velvet", "gold", [("leaves", 0.7), ("stain", (0.3, "blood")), ("cracks", 0.2)]),
    "floor_storm": style_floor("stone", "flag", "stone", "marble2", [("puddle", (0.6, "water")), ("leaves", 0.6), ("glowcracks", (0.2, "pinkglow"))]),
    "wall_thorn": style_wall("stone", "darkwood", "stone", "stone", "concrete2", [("thorns", (1.0, "rose")), ("thorns", (0.6, "rose")), ("smear", 0.3)]),
    "wall_silk": style_wall("velvet", "gilded", "panels", "velvet", "silk", [("banner", (0.8, "silk")), ("torch", 0.5), ("smear", 0.3)]),
    # Circle III - Gluttony
    "floor_mud": style_floor("mud", "earth", "mud", "mud2", [("puddle", (0.6, "sludge")), ("bones", 0.3), ("debris", (0.3, ["rot", "mud2"]))]),
    "floor_rot": style_floor("mud2", "cobble", "rot", "mud", [("debris", (0.8, ["flesh", "rot", "bone_dirty"])), ("stain", (0.5, "sludge")), ("skull", 0.2)]),
    "wall_mudbrick": style_wall("mud", "mud2", "bricks", "mud", "mud2", [("drips", (0.8, "sludge")), ("moss", 0.4), ("skulls", 0.2)]),
    "wall_gorge": style_wall("mutant", "flesh", "organic", "mutant", "flesh", [("drips", (0.8, "blood")), ("face", (0.5, "glow_yellow")), ("smear", 0.5)]),
    # Circle IV - Greed
    "floor_gold": style_floor("stone", "flag", "tombstone", "stone", [("coins", 0.9), ("coins", 0.5), ("cracks", 0.2)]),
    "floor_vault": style_floor("gilded", "tiles", "tombstone", "gilded", [("coins", 0.4), ("stain", (0.15, "blood"))]),
    "wall_vault": style_wall("gilded", "gold", "panels", "gilded", "gold", [("coins", 0.7), ("banner", (0.4, "banner")), ("torch", 0.4)]),
    "wall_hoard": style_wall("tombstone", "gold", "stone", "tombstone", "gilded", [("coins", 1.0), ("coins", 0.6), ("skulls", 0.3)]),
    # Circle V - Wrath (Styx swamp)
    "floor_bog": style_floor("peat", "liquid", "bog", "peat", [("roots", 0.5), ("bones", 0.2), ("moss", 0.4)], top=-0.02),
    "floor_peat": style_floor("peat", "earth", "peat", "mud2", [("roots", 0.7), ("moss", 0.5), ("puddle", (0.3, "bog"))]),
    "wall_bogrock": style_wall("concrete2", "moss", "rough", "concrete2", "peat", [("moss", 1.0), ("drips", (0.5, "bog")), ("chains", 0.2)]),
    "wall_deadtree": style_wall("peat", "peat", "trunks", "deadwood", "peat", [("face", (0.3, "glow_yellow")), ("moss", 0.4)]),
    # Circle VI - Heresy (burning tombs)
    "floor_tomb": style_floor("tombstone", "flag", "tombstone", "cinder", [("glowcracks", (0.6, "lava")), ("candle", 0.25), ("skull", 0.15)]),
    "floor_cinder": style_floor("cinder", "earth", "cinder", "ash", [("embers", 0.8), ("glowcracks", (0.3, "ember")), ("bones", 0.2)]),
    "wall_tomb": style_wall("tombstone", "cinder", "stone", "tombstone", "cinder", [("fire", 0.6), ("glowcracks", (0.4, "lava")), ("skulls", 0.3)]),
    "wall_pyre": style_wall("iron", "cinder", "panels", "iron", "rust2", [("fire", 0.9), ("glowcracks", (0.6, "ember")), ("chains", 0.3)]),
    # Circle VII - Violence (river of blood, thorn wood)
    "floor_bloodriver": style_floor("hellrock", "liquid", "bloodwater", "hellrock", [("bones", 0.4), ("skull", 0.2)], top=-0.02),
    "floor_thornwood": style_floor("peat", "earth", "deadwood", "peat", [("thorns", 0.8), ("roots", 0.5), ("stain", (0.3, "blood"))]),
    "wall_thorntree": style_wall("deadwood", "peat", "trunks", "darkwood", "deadwood", [("face", (0.6, "glow_red")), ("smear", 0.4)]),
    "wall_bloodrock": style_wall("hellrock", "hellrock", "rough", "hellrock", "bull", [("drips", (0.9, "blood")), ("smear", 0.6), ("skulls", 0.3)]),
    # Nuclear facility
    "floor_reactor": style_floor("darkmetal", "plates", "lead", "hazard", [("hazard", 0.4), ("glowcracks", (0.4, "radglow")), ("stain", (0.3, "oil"))]),
    "floor_radtile": style_floor("steel2", "tiles", "labwhite", "lead", [("puddle", (0.4, "radglow")), ("cracks", 0.3), ("papers", 0.2)]),
    "wall_reactor": style_wall("concrete", "lead", "panels", "concrete", "lead", [("radsign", 0.7), ("glowstrip", (0.6, "radglow")), ("gauge", 0.4)]),
    "wall_coolant": style_wall("lead", "darkmetal", "panels", "lead", "steel2", [("pipes", (1.0, "chrome")), ("glowstrip", (0.5, "radglow")), ("valve", 0.5)]),
    # Biotech
    "floor_cleanroom": style_floor("steel2", "tiles", "labwhite", "teal", [("papers", 0.3), ("stain", (0.2, "blood")), ("biomass", (0.15, "teal"))]),
    "floor_biogrowth": style_floor("labwhite", "tiles", "labwhite", "teal", [("biomass", (1.0, "teal")), ("biomass", (0.6, "leech")), ("stain", (0.3, "slime"))]),
    "wall_cleanroom": style_wall("labwhite", "steel2", "panels", "labwhite", "teal", [("glowstrip", (0.8, "tealglow")), ("window", (0.5, "tealglow")), ("smear", 0.3)]),
    "wall_vat": style_wall("steel2", "darkmetal", "panels", "steel2", "teal", [("vat", (1.0, "tealglow")), ("pipes", 0.5), ("gauge", 0.4)]),
    # Sewage treatment
    "floor_sewer": style_floor("sewerbrick", "flag", "sewerbrick", "concrete2", [("drain", 0.4), ("puddle", (0.5, "sludge")), ("debris", 0.4)]),
    "floor_sludge": style_floor("mud2", "liquid", "sludge", "sewerbrick", [("debris", (0.6, ["rubber", "rust2", "paper"])), ("bones", 0.2)], top=-0.02),
    "wall_sewerbrick": style_wall("sewerbrick", "concrete2", "bricks", "sewerbrick", "concrete2", [("drips", (0.8, "slime")), ("pipes", (0.5, "rust")), ("moss", 0.5)]),
    "wall_outflow": style_wall("concrete", "concrete2", "stone", "concrete", "sewerbrick", [("pipes", (1.0, "rust")), ("drips", (1.0, "sludge")), ("valve", 0.4)]),
    # Chemical plant
    "floor_catwalk": style_floor("black", "grate", "corroded", "chempurple", [("pipe", (0.3, "corroded")), ("hazard", 0.3)], top=-0.02),
    "floor_corroded": style_floor("corroded", "plates", "corroded", "rust2", [("puddle", (0.5, "chemyellow")), ("puddle", (0.3, "chempurple")), ("cracks", 0.3)]),
    "wall_chemtank": style_wall("corroded", "darkmetal", "panels", "corroded", "steel2", [("gauge", 0.7), ("pipes", (0.6, "corroded")), ("sign", 0.5), ("valve", 0.4)]),
    "wall_corroded": style_wall("corroded", "rust2", "panels", "corroded", "rust", [("drips", (0.9, "chemyellow")), ("smear", (0.5, "chempurple")), ("glowstrip", (0.3, "purpleglow"))]),
    # Medieval castle
    "floor_cobble": style_floor("concrete2", "cobble", "cobble", "stone", [("moss", 0.3), ("stain", (0.15, "blood")), ("bones", 0.1)]),
    "floor_hall": style_floor("stone", "carpet", "carpet", "gold", [("candle", 0.15), ("stain", (0.15, "blood"))]),
    "wall_castle": style_wall("cobble", "stone", "bricks", "cobble", "concrete2", [("banner", 0.5), ("torch", 0.5), ("shield", 0.3), ("moss", 0.3)]),
    "wall_keep": style_wall("wood", "stone", "planks", "wood", "darkwood", [("shield", 0.6), ("torch", 0.5), ("banner", (0.3, "banner"))]),
}


# ---------------------------------------------------------------- props (one solid + one decor per environment)
def prop(fn):
    def build():
        r = tile_root()
        fn(r)
        return r, None
    return build


def p_column(r):
    cyl("c", 0.2, RNG.uniform(0.5, 1.1), (0, 0, 0.4), M["marble"], r, segs=10)
    box("cb", (0.5, 0.5, 0.12), (0, 0, 0.06), M["marble2"], r)
    rnd_debris("cd", r, ["marble", "marble2"], 4, 0.0, (0.06, 0.14))


def p_ashpile(r):
    sphere("a", 0.3, (0, 0, -0.05), M["ash"], r, (1.3, 1, 0.35), 9, 6, True)
    bone_prop("ab", (-0.2, 0.1, 0.05), (0.15, 0.2, 0.06), r)
    skull_prop("as", (0.05, -0.1, 0.02), r, 0.9, 1.0)


def p_bed(r):
    box("bf", (0.9, 0.6, 0.25), (0, 0, 0.15), M["darkwood"], r)
    box("bm", (0.86, 0.56, 0.1), (0, 0, 0.32), M["velvet"], r)
    for x in (-0.42, 0.42):
        for y in (-0.27, 0.27):
            bone("bp", (x, y, 0), (x, y, 0.75 if x < 0 else 0.4), 0.025, M["gold"], r)
    smear("bs", (0, 0, 0.37), "x", 0.3, r, n=3)


def p_rosebush(r):
    for k in range(6):
        a = RNG.uniform(0, 2 * PI)
        wire("rb%d" % k, (0, 0, 0), (math.cos(a) * 0.35, math.sin(a) * 0.35, RNG.uniform(0.2, 0.5)), 0.0, 0.015, M["darkwood"], r, 5, wobble=0.04)
        sphere("rr%d" % k, 0.05, (math.cos(a) * 0.35, math.sin(a) * 0.35, RNG.uniform(0.2, 0.5)), M["rose"], r, segs=6, rings=4)


def p_cauldron(r):
    sphere("cal", 0.35, (0, 0, 0.3), M["iron"], r, (1, 1, 0.8), 12, 8, True)
    cyl("cs", 0.3, 0.02, (0, 0, 0.52), M["sludge"], r, segs=12)
    meat("cm", (0.05, 0, 0.55), 0.1, r, M["flesh"], 3)
    skull_prop("ck", (-0.1, 0.1, 0.5), r, 0.8, 0.5)
    for k in range(3):
        a = k * 2 * PI / 3
        bone("cl", (math.cos(a) * 0.25, math.sin(a) * 0.25, 0.1), (math.cos(a) * 0.32, math.sin(a) * 0.32, 0.0), 0.03, M["iron"], r)


def p_feast(r):
    for k in range(8):
        meat("fm%d" % k, (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), 0.03 + k * 0.01), RNG.uniform(0.07, 0.12), r,
             M[RNG.choice(["rot", "flesh", "guts"])], 3)
    pool("fp", (0, 0, 0.002), 0.7, r, M["sludge"], 4)


def p_chest(r):
    box("cb", (0.6, 0.4, 0.3), (0, 0, 0.15), M["wood"], r)
    box("ct", (0.62, 0.42, 0.1), (0, 0, 0.33), M["wood"], r, (0.3, 0, 0))
    for x in (-0.25, 0.25):
        box("cbd", (0.04, 0.42, 0.32), (x, 0, 0.16), M["gold"], r)
    f_feature(r, "coins", 1.0)


def p_coinpile(r):
    sphere("cp", 0.3, (0, 0, -0.05), M["gold"], r, (1.2, 1, 0.45), 10, 6, True)
    f_feature(r, "coins", 1.0)
    skull_prop("cps", (0.1, 0.05, 0.08), r, 0.9, 0.3, M["gold"])


def p_deadtree(r):
    cyl("dt", 0.16, 1.3, (0, 0, 0.65), M["deadwood"], r, segs=7, r2=0.05)
    for k in range(4):
        z = RNG.uniform(0.5, 1.1)
        a = RNG.uniform(0, 2 * PI)
        spike("db%d" % k, (0, 0, z), (math.cos(a) * 0.45, math.sin(a) * 0.45, z + 0.25), 0.04, M["deadwood"], r)
    wire("dn", (0.2, 0.1, 0.9), (0.25, 0.12, 0.4), 0.0, 0.01, M["rubber"], r, 4)
    skull_prop("dts", (0.25, 0.12, 0.3), r, 0.8, 0.2)


def p_swampcorpse(r):
    pool("sp", (0, 0, 0.002), 0.6, r, M["bog"], 4)
    sphere("sb", 0.15, (0, 0, 0.06), M["plague"], r, (2.2, 1.1, 0.5), 9, 6, True)
    skull_prop("ss", (0.35, 0, 0.0), r, 1.1, 0.2, M["plague"])
    f_feature(r, "roots", 1.0)


def p_burningtomb(r):
    box("tb", (0.8, 0.5, 0.42), (0, 0, 0.21), M["tombstone"], r)
    box("tl", (0.84, 0.54, 0.08), (0.25, 0.2, 0.3), M["tombstone"], r, (0.4, 0.2, 0.5))
    for k in range(6):
        base = Vector((RNG.uniform(-0.3, 0.3), RNG.uniform(-0.15, 0.15), 0.42))
        spike("tf%d" % k, base, base + Vector((0, 0, RNG.uniform(0.2, 0.45))), 0.07, M["flame" if k % 2 else "flame2"], r)


def p_candelabra(r):
    bone("cs", (0, 0, 0), (0, 0, 0.7), 0.025, M["iron"], r)
    for k in range(5):
        a = k * 2 * PI / 5
        bone("ca%d" % k, (0, 0, 0.6), (math.cos(a) * 0.15, math.sin(a) * 0.15, 0.7), 0.012, M["iron"], r)
        candle("cc%d" % k, (math.cos(a) * 0.15, math.sin(a) * 0.15, 0.7), 0.08, r)


def p_spikerack(r):
    box("sr", (0.7, 0.15, 0.08), (0, 0, 0.04), M["darkwood"], r)
    for k in range(5):
        spike("sk%d" % k, (-0.3 + k * 0.15, 0, 0.05), (-0.3 + k * 0.15, 0, 0.9), 0.03, M["iron"], r)
    meat("srm", (0.0, 0, 0.6), 0.12, r, M["muscle"], 3)
    drip("srd", (0.0, 0.03, 0.5), 0.4, 0.014, M["blood"], r)
    pool("srp", (0, 0, 0.002), 0.4, r, M["blood"], 3)


def p_bloodpool(r):
    pool("bp", (0, 0, 0.003), 0.8, r, M["bloodwater"], 6)
    for k in range(3):
        bone_prop("bb%d" % k, (RNG.uniform(-0.3, 0), RNG.uniform(-0.3, 0.3), 0.02), (RNG.uniform(0, 0.3), RNG.uniform(-0.3, 0.3), 0.02), r)


def p_raddrum(r):
    cyl("rd", 0.27, 0.72, (0, 0, 0.36), M["hazard"], r, segs=12)
    for z in (0.12, 0.6):
        ring("rb", 0.285, 0.05, (0, 0, z), M["darkmetal"], r, segs=12)
    cyl("rl", 0.2, 0.02, (0, 0, 0.725), M["radglow"], r, segs=12)
    w_feature(r, "radsign", 1.0)
    drip("rdd", (0.25, 0.1, 0.73), 0.25, 0.02, M["radglow"], r)


def p_fuelrods(r):
    box("fb", (0.6, 0.6, 0.1), (0, 0, 0.05), M["lead"], r)
    for i in range(3):
        for j in range(3):
            cyl("fr%d%d" % (i, j), 0.05, 0.7, (-0.18 + i * 0.18, -0.18 + j * 0.18, 0.45), M["chrome"], r, segs=8)
            cyl("fg%d%d" % (i, j), 0.03, 0.05, (-0.18 + i * 0.18, -0.18 + j * 0.18, 0.82), M["radglow"], r, segs=6)


def p_biovat(r):
    cyl("vb", 0.34, 0.12, (0, 0, 0.06), M["steel2"], r, segs=12)
    cyl("vl", 0.28, 0.9, (0, 0, 0.58), M["tealglow"], r, segs=12)
    cyl("vg", 0.31, 1.0, (0, 0, 0.62), M["glass"], r, segs=14)
    cyl("vt", 0.34, 0.1, (0, 0, 1.15), M["steel2"], r, segs=12)
    sphere("vs", 0.13, (0, 0, 0.65), M["muscle"], r, (1, 0.8, 1.5), 8, 6, True)
    for k in range(4):
        a = k * PI / 2
        wire("vt%d" % k, (math.cos(a) * 0.05, math.sin(a) * 0.05, 0.5), (math.cos(a) * 0.22, math.sin(a) * 0.22, 0.2), 0.0, 0.015, M["vein"], r, 4)


def p_spectable(r):
    box("st", (0.85, 0.45, 0.06), (0, 0, 0.45), M["steel2"], r)
    for x in (-0.38, 0.38):
        for y in (-0.18, 0.18):
            bone("sl", (x, y, 0), (x, y, 0.42), 0.02, M["chrome"], r)
    sphere("sb", 0.15, (0, 0, 0.53), M["muscle"], r, (2.2, 1, 0.5), 9, 6, True)
    guts("sg", (0.1, 0.0, 0.55), (1, 0.4, -0.2), 6, 0.025, r)
    pool("sp", (0.1, 0.1, 0.002), 0.3, r, M["blood"], 3)


def p_outflow(r):
    cyl("op", 0.22, 0.6, (0, 0, 0.35), M["rust"], r, rot=(0, PI / 2 * 0.0, 0), segs=12)
    ring("or", 0.24, 0.06, (0, 0, 0.66), M["darkmetal"], r, segs=12)
    cyl("os", 0.2, 0.02, (0, 0, 0.66), M["sludge"], r, segs=12)
    for k in range(3):
        drip("od%d" % k, (math.cos(k * 2) * 0.2, math.sin(k * 2) * 0.2, 0.66), RNG.uniform(0.2, 0.5), 0.025, M["sludge"], r)
    pool("opl", (0.2, 0, 0.002), 0.5, r, M["sludge"], 4)


def p_trash(r):
    for k in range(9):
        box("tr%d" % k, (RNG.uniform(0.06, 0.16),) * 2 + (RNG.uniform(0.03, 0.1),), (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), 0.04),
            M[RNG.choice(["rubber", "rust2", "paper", "crate", "zcloth"])], r, (RNG.uniform(0, 1), 0, RNG.uniform(0, 3)))
    pool("tp", (0, 0, 0.002), 0.5, r, M["sludge"], 3)
    skull_prop("ts", (0.15, -0.1, 0.03), r, 0.8, 0.4)


def p_chemdrum(r):
    cyl("cd", 0.27, 0.72, (0, 0, 0.36), M["corroded"], r, segs=12)
    for z in (0.12, 0.6):
        ring("cb", 0.285, 0.05, (0, 0, z), M["darkmetal"], r, segs=12)
    cyl("cl", 0.2, 0.02, (0, 0, 0.725), M["chempurple"], r, segs=12)
    drip("cdd", (0.26, 0.1, 0.73), 0.3, 0.02, M["chemyellow"], r)
    pool("cdp", (0.3, 0.1, 0.002), 0.3, r, M["chemyellow"], 3)


def p_valvestation(r):
    box("vs", (0.3, 0.3, 0.6), (0, 0, 0.3), M["corroded"], r)
    for k in range(3):
        ring("vw%d" % k, 0.07, 0.02, (0.16, -0.08 + k * 0.08, 0.35 + k * 0.08), M["armor"], r, rot=(0, PI / 2, 0), segs=10)
    w_feature(r, "gauge", 1.0)
    for k in range(2):
        cyl("vp%d" % k, 0.05, 0.8, (-0.1, -0.1 + k * 0.2, 0.4), M["corroded"], r, rot=(PI / 2, 0, 0), segs=8)


def p_armorstand(r):
    bone("as", (0, 0, 0), (0, 0, 0.9), 0.02, M["darkwood"], r)
    box("ap", (0.2, 0.32, 0.36), (0, 0, 0.75), M["iron"], r)
    box("ah", (0.16, 0.16, 0.18), (0, 0, 1.02), M["iron"], r)
    box("av", (0.02, 0.12, 0.02), (0.08, 0, 1.03), M["black"], r)
    cyl("ash", 0.16, 0.03, (0.12, 0.2, 0.6), M["iron"], r, rot=(0, PI / 2, 0), segs=10)
    bone("asw", (0.1, -0.2, 0.2), (0.1, -0.2, 1.0), 0.015, M["chrome"], r)


def p_torchstand(r):
    bone("ts", (0, 0, 0), (0, 0, 0.8), 0.025, M["iron"], r)
    cyl("tb", 0.08, 0.08, (0, 0, 0.82), M["iron"], r, r2=0.12, segs=8)
    for k in range(4):
        spike("tf%d" % k, (0, 0, 0.84), (RNG.uniform(-0.05, 0.05), RNG.uniform(-0.05, 0.05), 1.1), 0.05, M["flame" if k % 2 else "flame2"], r)


PROPS = {
    "column_broken": (p_column, (96, 112), 0.4, "solid"), "ashpile": (p_ashpile, (96, 96), 0.1, "decor"),
    "lustbed": (p_bed, (96, 112), 0.3, "solid"), "rosebush": (p_rosebush, (96, 96), 0.2, "decor"),
    "cauldron": (p_cauldron, (96, 96), 0.3, "solid"), "feast": (p_feast, (96, 96), 0.1, "decor"),
    "chest": (p_chest, (96, 96), 0.2, "solid"), "coinpile": (p_coinpile, (96, 96), 0.1, "decor"),
    "deadtree": (p_deadtree, (96, 144), 0.7, "solid"), "swampcorpse": (p_swampcorpse, (96, 96), 0.1, "decor"),
    "burningtomb": (p_burningtomb, (96, 112), 0.35, "solid"), "candelabra": (p_candelabra, (96, 112), 0.4, "decor"),
    "spikerack": (p_spikerack, (96, 128), 0.5, "solid"), "bloodpool": (p_bloodpool, (96, 96), 0.05, "decor"),
    "raddrum": (p_raddrum, (96, 96), 0.4, "solid"), "fuelrods": (p_fuelrods, (96, 112), 0.4, "decor"),
    "biovat": (p_biovat, (96, 128), 0.6, "solid"), "spectable": (p_spectable, (96, 96), 0.3, "decor"),
    "outflow": (p_outflow, (96, 112), 0.35, "solid"), "trashpile": (p_trash, (96, 96), 0.1, "decor"),
    "chemdrum": (p_chemdrum, (96, 96), 0.4, "solid"), "valvestation": (p_valvestation, (96, 112), 0.35, "decor"),
    "armorstand": (p_armorstand, (96, 128), 0.55, "solid"), "torchstand": (p_torchstand, (96, 128), 0.5, "decor"),
}


# ================================================================ creature generator
def head_build(kind, hp, sp):
    skin, glow = M[sp.get("skin", "zskin")], M[sp.get("glow", "glow_red")]
    if kind in ("skull", "crown", "bullskull"):
        sphere("hs", 0.12, (0.02, 0, 0.06), M["bone"], hp, (1.1, 0.9, 0.95), 9, 7, True)
        box("hj", (0.11, 0.12, 0.05), (0.08, 0, -0.04), M["bone"], hp)
        for s_ in (-1, 1):
            sphere("he%d" % s_, 0.026, (0.12, s_ * 0.045, 0.07), glow, hp)
        if kind == "crown":
            ring("hc", 0.1, 0.06, (0.0, 0, 0.16), M["gold"], hp, segs=8)
            for k in range(5):
                a = k * 2 * PI / 5
                spike("hcs%d" % k, (math.cos(a) * 0.1, math.sin(a) * 0.1, 0.18), (math.cos(a) * 0.11, math.sin(a) * 0.11, 0.3), 0.02, M["gold"], hp)
        if kind == "bullskull":
            for s_ in (-1, 1):
                tube("hbh%d" % s_, [Vector((0, s_ * 0.08, 0.1)), Vector((0, s_ * 0.22, 0.16)), Vector((0.08, s_ * 0.3, 0.28))], 0.035, M["bone"], hp,
                     segs=6, r_end=0.005)
    elif kind == "horned":
        sphere("hh", 0.1, (0.02, 0, 0.05), skin, hp, (1.2, 0.9, 1.0), 8, 6, True)
        for s_ in (-1, 1):
            tube("hho%d" % s_, [Vector((0, s_ * 0.06, 0.1)), Vector((-0.06, s_ * 0.12, 0.2)), Vector((-0.16, s_ * 0.14, 0.24))], 0.025,
                 M["bone_dirty"], hp, segs=5, r_end=0.004)
            sphere("he%d" % s_, 0.02, (0.11, s_ * 0.04, 0.07), glow, hp)
        box("hjw", (0.08, 0.1, 0.04), (0.1, 0, -0.03), skin, hp)
    elif kind == "hood":
        cyl("hd", 0.15, 0.32, (0, 0, 0.1), M[sp.get("cloth", "robe")], hp, r2=0.03, segs=10)
        box("hdf", (0.04, 0.14, 0.16), (0.11, 0, 0.05), M["black"], hp)
        for s_ in (-1, 1):
            sphere("he%d" % s_, 0.022, (0.13, s_ * 0.035, 0.07), glow, hp)
    elif kind == "eyeless":
        sphere("he", 0.11, (0.02, 0, 0.06), skin, hp, (1, 0.85, 1.3), 9, 7, True)
        cyl("hm", 0.05, 0.02, (0.12, 0, 0.0), M["blood"], hp, rot=(0, PI / 2, 0))
        for k in range(5):
            a = k * 2 * PI / 5
            spike("ht%d" % k, (0.12, math.cos(a) * 0.045, math.sin(a) * 0.045), (0.16, math.cos(a) * 0.025, math.sin(a) * 0.025), 0.01, M["tooth"], hp)
    elif kind == "maw":
        for s_ in (-1, 1):
            sphere("hm%d" % s_, 0.1, (0.03, s_ * 0.06, 0.06), skin, hp, (1.1, 0.6, 1.2), 8, 6, True)
            for k in range(4):
                spike("mt%d%d" % (s_, k), (0.08, s_ * 0.02, -0.02 + k * 0.05), (0.08, -s_ * 0.02, -0.02 + k * 0.05), 0.012, M["tooth"], hp)
        sphere("hmi", 0.06, (0.03, 0, 0.06), M["blood"], hp)
    elif kind == "helmet":
        box("hl", (0.2, 0.18, 0.24), (0.02, 0, 0.08), M["iron"], hp)
        box("hlv", (0.02, 0.14, 0.025), (0.125, 0, 0.1), glow, hp)
        spike("hlp", (0, 0, 0.2), (-0.06, 0, 0.36), 0.03, M[sp.get("accent", "banner")], hp)
    elif kind == "brain":
        sphere("hb", 0.1, (0.04, 0, 0.0), skin, hp, (1.3, 0.9, 0.8), 8, 6, True)
        sphere("hbb", 0.085, (0.02, 0, 0.07), M["brain"], hp, (1.3, 0.9, 0.7), 9, 7, True)
        for k in range(5):
            spike("hbt%d" % k, (0.14, -0.04 + k * 0.02, -0.04), (0.14, -0.04 + k * 0.02, -0.08), 0.009, M["tooth"], hp)
    elif kind == "mushroom":
        sphere("hm", 0.08, (0.02, 0, 0.0), skin, hp, segs=8, rings=6, smooth=True)
        sphere("hmc", 0.2, (0, 0, 0.1), M[sp.get("accent", "leech2")], hp, (1, 1, 0.45), 12, 7, True)
        for k in range(8):
            a = RNG.uniform(0, 2 * PI)
            sphere("hms%d" % k, 0.025, (math.cos(a) * 0.14, math.sin(a) * 0.14, 0.15), glow, hp, segs=5, rings=3)
    elif kind == "gasmask":
        sphere("hg", 0.12, (0.02, 0, 0.06), M[sp.get("accent", "hazmat")], hp, (1, 0.95, 1.1), 9, 7, True)
        ring("hgl", 0.06, 0.03, (0.12, 0, 0.08), M["darkmetal"], hp, rot=(0, PI / 2, 0))
        cyl("hgg", 0.055, 0.01, (0.13, 0, 0.08), glow, hp, rot=(0, PI / 2, 0))
        cyl("hgf", 0.04, 0.08, (0.13, 0, -0.02), M["darkmetal"], hp, rot=(0, PI / 2, 0))
    elif kind == "melted":
        sphere("hml", 0.12, (0.02, 0, 0.03), skin, hp, (1, 0.9, 1.25), 9, 7, True)
        sphere("hmo", 0.05, (0.1, -0.03, 0.0), M["blood"], hp, (0.6, 1, 1.5))
        sphere("he1", 0.025, (0.1, 0.05, 0.08), glow, hp)
        sphere("he2", 0.02, (0.11, -0.04, -0.04), glow, hp)
        for k in range(4):
            drip("hd%d" % k, (RNG.uniform(-0.05, 0.1), RNG.uniform(-0.08, 0.08), -0.04), RNG.uniform(0.08, 0.2), 0.02, skin, hp)
    elif kind == "hound":
        sphere("hh", 0.11, (0.08, 0, 0.0), skin, hp, (1.7, 0.85, 0.85), 9, 6, True)
        box("hj", (0.18, 0.1, 0.04), (0.18, 0, -0.06), skin, hp)
        for k in range(6):
            spike("ht%d" % k, (0.2 + (k % 3) * 0.03, -0.03 + (k // 3) * 0.06, -0.04), (0.2 + (k % 3) * 0.03, -0.03 + (k // 3) * 0.06, -0.08),
                  0.008, M["tooth"], hp)
        for s_ in (-1, 1):
            sphere("he%d" % s_, 0.02, (0.17, s_ * 0.05, 0.04), glow, hp)
            spike("hear%d" % s_, (0.02, s_ * 0.05, 0.07), (-0.04, s_ * 0.08, 0.17), 0.03, skin, hp)
    else:   # plain
        sphere("hp", 0.11, (0.02, 0, 0.06), skin, hp, (1, 0.9, 1.05), 8, 6, True)
        for s_ in (-1, 1):
            sphere("he%d" % s_, 0.022, (0.12, s_ * 0.04, 0.08), glow, hp)


def weapon_build(kind, hand, sp):
    """hand: empty at the hand; weapon points along +X."""
    if kind == "gun":
        box("gb", (0.3, 0.06, 0.08), (0.12, 0, 0), M["darkmetal"], hand)
        bone("gbr", (0.27, 0, 0.01), (0.48, 0, 0.01), 0.022, M["chrome"], hand)
        box("gm", (0.05, 0.04, 0.12), (0.1, 0, -0.08), M["darkmetal"], hand)
        box("gs", (0.04, 0.04, 0.03), (0.2, 0, 0.06), M[sp.get("glow", "glow_red")], hand)
    elif kind == "minigun":
        cyl("mgb", 0.08, 0.3, (0.1, 0, 0), M["darkmetal"], hand, rot=(0, PI / 2, 0), segs=10)
        for k in range(6):
            a = k * PI / 3
            bone("mgbr%d" % k, (0.25, math.cos(a) * 0.04, math.sin(a) * 0.04), (0.6, math.cos(a) * 0.04, math.sin(a) * 0.04), 0.012, M["chrome"], hand)
        ring("mgr", 0.06, 0.03, (0.55, 0, 0), M["darkmetal"], hand, rot=(0, PI / 2, 0))
        wire("mgw", (-0.05, 0, -0.05), (-0.2, 0.1, -0.3), 0.0, 0.02, M["rubber"], hand, 4)
    elif kind == "sword":
        box("sw", (0.6, 0.02, 0.05), (0.33, 0, 0), M["chrome"], hand)
        box("swg", (0.03, 0.16, 0.03), (0.03, 0, 0), M["gold"], hand)
    elif kind == "cleaver":
        th = sp.get("thick", 1.0)
        skin = M[sp.get("skin", "zskin")]
        sphere("cvfist", 0.055 * th, (0, 0, 0), skin, hand, (1.15, 1, 0.9), 8, 6, True)           # the hand gripping it
        for k in range(3):
            bone("cvfing%d" % k, (0.03, -0.035 + k * 0.035, 0.03), (0.05, -0.035 + k * 0.035, -0.03), 0.016 * th, skin, hand)
        bone("cvhandle", (-0.09, 0, 0.0), (0.17, 0, 0.0), 0.022, M["darkwood"], hand)              # wrapped wooden handle
        for x in (-0.07, 0.1, 0.15):
            ring("cvwrap%.2f" % x, 0.025, 0.012, (x, 0, 0), M["rust2"], hand, rot=(0, PI / 2, 0), segs=6)
        sphere("cvpommel", 0.03, (-0.1, 0, 0), M["iron"], hand, segs=6, rings=4)
        box("cvbolster", (0.04, 0.05, 0.06), (0.18, 0, -0.01), M["iron"], hand)
        box("cv", (0.36, 0.025, 0.24), (0.38, 0, -0.09), M["rust"], hand)                           # heavy blade below the spine
        box("cvspine", (0.36, 0.04, 0.03), (0.38, 0, 0.03), M["iron"], hand)
        box("cvedge", (0.36, 0.012, 0.03), (0.38, 0, -0.205), M["chrome"], hand)
        cyl("cvhole", 0.025, 0.03, (0.5, 0, -0.01), M["black"], hand, rot=(PI / 2, 0, 0), segs=8)
        drip("cvd", (0.42, 0.014, -0.18), 0.1, 0.014, M["blood"], hand)
        drip("cvd2", (0.3, -0.014, -0.15), 0.07, 0.01, M["blood"], hand)
    elif kind == "staff":
        bone("st", (-0.3, 0, -0.1), (0.5, 0, 0.05), 0.015, M["darkwood"], hand)
        sphere("sto", 0.06, (0.52, 0, 0.06), M[sp.get("glow", "glow_red")], hand)
    elif kind == "crossbow":
        box("cb", (0.3, 0.05, 0.05), (0.12, 0, 0), M["wood"], hand)
        tube("cbb", [Vector((0.25, -0.18, 0)), Vector((0.3, 0, 0)), Vector((0.25, 0.18, 0))], 0.012, M["wood"], hand, segs=5)
        bone("cbbolt", (0.0, 0, 0.03), (0.35, 0, 0.03), 0.006, M["iron"], hand)
    elif kind == "blades":
        spike("bl", (0, 0, 0), (0.55, 0, -0.1), 0.03, M["bone"], hand)
    elif kind == "claws":
        for k in range(3):
            spike("cl%d" % k, (0, -0.02 + k * 0.02, 0), (0.12, -0.03 + k * 0.03, -0.04), 0.012, M["bone"], hand)
    elif kind == "fists":
        sphere("fi", 0.09, (0.02, 0, 0), M[sp.get("skin", "zskin")], hand, segs=7, rings=5, smooth=True)


def body_extras(torso, sp, th):
    skin = M[sp.get("skin", "zskin")]
    for ex in sp.get("extras", []):
        if ex == "spikes":
            for k in range(5):
                y = (k - 2) * 0.06
                spike("xs%d" % k, (-0.12 * th, y, 0.2 + abs(y)), (-0.3 * th, y * 1.5, 0.35 + abs(y) * 1.5), 0.03, M["bone_dirty"], torso)
        elif ex == "tank":
            box("xt", (0.12, 0.2, 0.26), (-0.18 * th, 0, 0.25), M[sp.get("glowmat", "radglow")], torso)
            wire("xtw", (-0.2 * th, 0.05, 0.38), (0.05, 0.05, 0.5), 0.0, 0.018, M["rubber"], torso, 5, bulge=(-0.08, 0, 0.08))
        elif ex == "melt":
            for k in range(8):
                drip("xm%d" % k, (RNG.uniform(-0.1, 0.12) * th, RNG.uniform(-0.15, 0.15) * th, RNG.uniform(0.0, 0.4)), RNG.uniform(0.08, 0.25),
                     0.025 * th, skin, torso)
            for k in range(4):
                sphere("xmb%d" % k, RNG.uniform(0.05, 0.09) * th, (RNG.uniform(-0.1, 0.12) * th, RNG.uniform(-0.15, 0.15) * th, RNG.uniform(0, 0.4)),
                       skin, torso, (1, 1, 1.4), 7, 5, True)
        elif ex == "robe":
            cyl("xr", 0.22 * th, 0.75, (0, 0, -0.1), M[sp.get("cloth", "robe")], torso, r2=0.12 * th, segs=10)
            for k in range(6):
                a = k * PI / 3
                box("xrt%d" % k, (0.06, 0.08, 0.2), (math.cos(a) * 0.2 * th, math.sin(a) * 0.2 * th, -0.5), M[sp.get("cloth", "robe")], torso)
        elif ex == "armor":
            box("xa", (0.3 * th, 0.4 * th, 0.3), (0.0, 0, 0.3), M["iron"], torso)
            for s_ in (-1, 1):
                box("xap%d" % s_, (0.2, 0.15, 0.1), (0, s_ * 0.24 * th, 0.48), M["iron"], torso)
        elif ex == "coat":
            box("xc", (0.28 * th, 0.36 * th, 0.55), (0, 0, 0.15), M[sp.get("cloth", "whitecoat")], torso)
        elif ex == "wings":
            for s_ in (-1, 1):
                wg = empty("xw%d" % s_, (-0.08, s_ * 0.12, 0.35), torso, (0, 0, 0))
                for k in range(4):
                    bone("xwb%d%d" % (s_, k), (0, 0, 0), (-0.25 - k * 0.05, s_ * (0.3 + k * 0.08), 0.25 - k * 0.15), 0.012, M["bone_dirty"], wg)
                box("xwm%d" % s_, (0.3, 0.45, 0.01), (-0.2, s_ * 0.3, 0.1), M[sp.get("cloth", "velvet")], wg, (s_ * 0.4, 0.3, 0))
        elif ex == "tubes":
            for k in range(3):
                wire("xtb%d" % k, (-0.12 * th, RNG.uniform(-0.1, 0.1), RNG.uniform(0.1, 0.4)), (0.05, RNG.uniform(-0.05, 0.05), 0.55), 0.0, 0.014,
                     M[RNG.choice(["rubber", "vein", "wire_red"])], torso, 5, bulge=(-0.1, 0, 0.05))
        elif ex == "gold":
            for k in range(10):
                cyl("xg%d" % k, 0.03, 0.01, (RNG.uniform(-0.1, 0.12) * th, RNG.uniform(-0.15, 0.15) * th, RNG.uniform(0.05, 0.45)), M["gold"], torso,
                    rot=(RNG.uniform(0, 3), RNG.uniform(0, 3), 0), segs=8)
        elif ex == "thorns":
            for k in range(8):
                p0 = Vector((RNG.uniform(-0.12, 0.12) * th, RNG.uniform(-0.15, 0.15) * th, RNG.uniform(0.05, 0.45)))
                spike("xth%d" % k, p0, p0 + Vector((RNG.uniform(-0.1, 0.1), RNG.uniform(-0.1, 0.1), RNG.uniform(0.05, 0.15))), 0.015, M["darkwood"], torso)
        elif ex == "fire":
            for k in range(6):
                p0 = Vector((RNG.uniform(-0.1, 0.05), RNG.uniform(-0.12, 0.12), RNG.uniform(0.3, 0.55)))
                spike("xf%d" % k, p0, p0 + Vector((-0.08, 0, RNG.uniform(0.2, 0.35))), 0.06, M["flame" if k % 2 else "flame2"], torso)
        elif ex == "ghost":
            for k in range(5):
                a = k * 2 * PI / 5
                box("xgt%d" % k, (0.06, 0.1, 0.35), (math.cos(a) * 0.15, math.sin(a) * 0.15, -0.3), M["ghost"], torso, (0.2, 0, a))
        elif ex == "core":
            sphere("xcore", 0.08 * th, (0.12 * th, 0, 0.3), M[sp.get("glowmat", "glow_red")], torso, segs=8, rings=6, smooth=True)
            ring("xcr", 0.1 * th, 0.04, (0.12 * th, 0, 0.3), M["darkmetal"], torso, rot=(0, PI / 2, 0))
        elif ex == "biomass":
            for k in range(6):
                sphere("xbm%d" % k, RNG.uniform(0.05, 0.1) * th, (RNG.uniform(-0.12, 0.12) * th, RNG.uniform(-0.15, 0.15) * th, RNG.uniform(0, 0.45)),
                       M[sp.get("accent", "teal")], torso, segs=7, rings=5, smooth=True)
            sphere("xbmg", 0.04, (0.12 * th, 0.05, 0.3), M["tealglow"], torso)


def build_creature(sp):
    plan = sp["plan"]
    th = sp.get("thick", 1.0)
    skin, skin2 = M[sp.get("skin", "zskin")], M[sp.get("skin2", sp.get("skin", "zskin"))]
    root = empty("cr_root")
    s = sp.get("scale", 1.0)
    root.scale = (s, s, s)
    anim = {}

    if plan in ("biped", "hulk", "mech", "flyer"):
        fly = plan == "flyer"
        if not fly:
            J = biped_legs(root, 0.8, 0.11 * th, 0.38, 0.36, 0.05 * th, 0.04 * th, skin2, skin, (0.18, 0.09, 0.05),
                           M["iron" if plan == "mech" else sp.get("skin2", "zskin2")], "b")
            anim["legs"] = J
        body = empty("cr_body", (0, 0, 0.3 if fly else 0), root)
        anim["body"] = body
        torso = empty("cr_torso", (0, 0, 0.82), body, (0, sp.get("hunch", 0.2), 0))
        chest_mat = M["iron"] if plan == "mech" else skin
        sphere("chest", 0.17 * th, (0, 0, 0.25), chest_mat, torso, (0.85, 1.1, 1.4), 9, 7, plan != "mech")
        if plan == "hulk":
            sphere("belly", 0.2 * th, (0.06, 0, 0.05), skin, torso, (1, 1.1, 0.9), 9, 6, True)
        body_extras(torso, sp, th)
        head = empty("cr_head", (0.05, 0, 0.55 * (1 + 0.15 * (th - 1))), torso, (0, -sp.get("hunch", 0.2), 0))
        anim["head"] = head
        head_build(sp.get("head", "plain"), head, sp)
        arms = {}
        for side, y in (("L", 0.2 * th), ("R", -0.2 * th)):
            sh = empty("csh" + side, (0, y, 0.42), torso)
            sphere("cso" + side, 0.06 * th, (0, 0, 0), chest_mat, sh, segs=7, rings=5, smooth=True)
            arm_style = sp.get("arms", "claws")
            if arm_style == "tentacles":
                tj = tentacle("ct" + side, (0, 0, 0), (1, 0, -0.6), 6, 0.1 * th, 0.04 * th, sh, M[sp.get("accent", "muscle")])
                anim.setdefault("tents", []).append(tj)
            else:
                bone("cup" + side, (0, 0, 0), (0.12, 0, -0.22), 0.035 * th, skin, sh)
                bone("cfo" + side, (0.12, 0, -0.22), (0.3, 0, -0.18), 0.03 * th, skin, sh)
                hand = empty("chand" + side, (0.3, 0, -0.18), sh)
                wpn = sp.get("weapon") if side == "R" else sp.get("weapon2", sp.get("weapon") if sp.get("dual") else None)
                weapon_build(wpn or arm_style, hand, sp)
            arms[side] = sh
        anim["arms"] = arms

    elif plan == "quad":
        body = empty("q_body", (0, 0, 0.48 * th), root)
        anim["body"] = body
        sphere("qch", 0.2 * th, (0.12, 0, 0.05), skin, body, (1.5, 1.0, 0.85), 10, 7, True)
        sphere("qhi", 0.17 * th, (-0.25, 0, 0.0), skin2, body, (1.3, 1.0, 0.8), 9, 6, True)
        body_extras(body, sp, th)
        head = empty("q_head", (0.38 * th, 0, 0.1), body)
        anim["head"] = head
        head_build(sp.get("head", "hound"), head, sp)
        legs = []
        for i, (x, sy) in enumerate(((0.2, 1), (0.2, -1), (-0.28, 1), (-0.28, -1))):
            hip = empty("ql%d" % i, (x * th, sy * 0.13 * th, -0.02), body)
            bone("qa%d" % i, (0, 0, 0), (0.06, sy * 0.03, -0.24 * th), 0.045 * th, skin, hip)
            bone("qb%d" % i, (0.06, sy * 0.03, -0.24 * th), (0.0, sy * 0.04, -0.48 * th), 0.03 * th, skin2, hip)
            legs.append((hip, (0, 0.5, 0.5, 0)[i]))
        bone("qtail", (-0.4 * th, 0, 0.05), (-0.75 * th, 0, 0.2), 0.03 * th, skin2, body, r2=0.005)
        anim["quadlegs"] = legs

    elif plan in ("insect", "worm"):
        body = empty("i_body", (0, 0, 0.3 * th), root)
        anim["body"] = body
        segs_ = []
        n = sp.get("segments", 4 if plan == "insect" else 7)
        for i in range(n):
            rr = 0.14 * th * (1 - abs(i - n * 0.35) / n)
            seg = empty("is%d" % i, (0.25 - i * 0.16 * th, 0, 0), body)
            sphere("isb%d" % i, rr + 0.04, (0, 0, 0), skin if i % 2 == 0 else skin2, seg, (1, 1, 0.8), 9, 6, True)
            segs_.append(seg)
        anim["segs"] = segs_
        body_extras(segs_[1], sp, th * 0.8)
        head = empty("i_head", (0.18 * th, 0, 0.0), segs_[0])
        head_build(sp.get("head", "maw"), head, sp)
        if plan == "insect":
            legs = []
            for s_ in (1, -1):
                for i in range(3):
                    hip = empty("il%d%d" % (s_, i), (0.1 - i * 0.16 * th, s_ * 0.1 * th, 0), body, (0, 0, s_ * math.radians(55 + i * 35)))
                    lift = empty("ilf%d%d" % (s_, i), (0, 0, 0), hip)
                    bone("ilu%d%d" % (s_, i), (0, 0, 0), (0.28 * th, 0, 0.18 * th), 0.025 * th, skin2, lift)
                    bone("ild%d%d" % (s_, i), (0.28 * th, 0, 0.18 * th), (0.5 * th, 0, -0.3 * th), 0.02 * th, skin2, lift, r2=0.004)
                    legs.append((hip, lift, hip.rotation_euler.z, s_, 0.0 if (i % 2 == 0) == (s_ == 1) else 0.5))
            anim["insectlegs"] = legs

    elif plan == "blob":
        body = empty("bl_body", (0, 0, 0), root)
        anim["body"] = body
        sphere("blm", 0.4 * th, (0, 0, 0.4 * th), skin, body, (1.2, 1.1, 1.0), 14, 9, True)
        for k in range(6):
            a, b = RNG.uniform(0, 2 * PI), RNG.uniform(-0.3, 0.8)
            p0 = Vector((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b))) * 0.42 * th
            sphere("blb%d" % k, RNG.uniform(0.08, 0.16) * th, p0 + Vector((0, 0, 0.4 * th)), skin2, body, segs=8, rings=6, smooth=True)
        head = empty("bl_head", (0.38 * th, 0, 0.45 * th), body)
        head_build(sp.get("head", "maw"), head, sp)
        for k in range(5):
            sphere("ble%d" % k, 0.04, (RNG.uniform(0.1, 0.4) * th, RNG.uniform(-0.3, 0.3) * th, RNG.uniform(0.4, 0.8) * th), M[sp.get("glow", "glow_yellow")], body)
        tents = []
        for k in range(sp.get("tentacles", 4)):
            a = k * 2 * PI / max(1, sp.get("tentacles", 4)) + 0.3
            tents.append(tentacle("blt%d" % k, (math.cos(a) * 0.35 * th, math.sin(a) * 0.35 * th, 0.25 * th), (math.cos(a), math.sin(a), 0.2),
                                  6, 0.1 * th, 0.05 * th, body, M[sp.get("accent", "muscle")]))
        anim["tents"] = tents
        body_extras(body, sp, th)

    elif plan == "serpent":
        body = empty("sp_body", (0, 0, 0), root)
        anim["body"] = body
        coil = []
        n = 12
        for i in range(n):
            t = i / (n - 1)
            seg = empty("ss%d" % i, (-0.5 + 0.1 * math.cos(t * 6) - t * 0.4, 0.3 * math.sin(t * 5), 0.15 + (1 - t) * 1.0 * th), body)
            sphere("ssb%d" % i, 0.16 * th * (1 - t * 0.6), (0, 0, 0), skin if i % 2 else skin2, seg, (1, 1, 1), 9, 6, True)
            if i % 2 == 0:
                spike("ssp%d" % i, (0, 0, 0.12 * th * (1 - t * 0.6)), (-0.05, 0, 0.25 * th * (1 - t * 0.6)), 0.03, M["bone_dirty"], seg)
            coil.append(seg)
        anim["coil"] = coil
        head = empty("sp_head", (0.12, 0, 0.05), coil[0])
        head_build(sp.get("head", "maw"), head, sp)
        head.scale = (1.6, 1.6, 1.6)
        body_extras(coil[2], sp, th)

    elif plan == "tree":
        body = empty("tr_body", (0, 0, 0), root)
        anim["body"] = body
        cyl("trk", 0.25 * th, 1.4, (0, 0, 0.7), M[sp.get("skin", "deadwood")], body, segs=8, r2=0.12 * th)
        for k in range(5):
            a = k * 2 * PI / 5
            wire("trr%d" % k, (0, 0, 0.2), (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.0), 0.0, 0.05, M[sp.get("skin", "deadwood")], body, 4,
                 bulge=(0, 0, 0.1))
        head = empty("tr_head", (0.18 * th, 0, 1.0), body)
        sphere("trf", 0.16, (0, 0, 0), M["deadwood"], head, (0.6, 1, 1.3), 8, 6, True)
        for s_ in (-1, 1):
            sphere("tre%d" % s_, 0.03, (0.08, s_ * 0.05, 0.05), M[sp.get("glow", "glow_red")], head)
        box("trm", (0.03, 0.08, 0.06), (0.09, 0, -0.06), M["black"], head)
        tents = []
        for k in range(sp.get("tentacles", 4)):
            a = k * 2 * PI / sp.get("tentacles", 4)
            tents.append(tentacle("trt%d" % k, (math.cos(a) * 0.15, math.sin(a) * 0.15, 1.1), (math.cos(a), math.sin(a), 0.6), 6, 0.12 * th,
                                  0.04 * th, body, M["darkwood"]))
        anim["tents"] = tents
        body_extras(body, sp, th)

    def pose(an, t):
        ph = 2 * PI * t
        if "legs" in anim:
            walk_legs(anim["legs"], t, sp.get("stride_amp", 0.4), 0.5)
        if "body" in anim:
            b = anim["body"]
            if plan == "flyer":
                b.location.z = 0.3 + math.sin(ph) * 0.06
            elif plan in ("biped", "hulk", "mech"):
                b.rotation_euler.x = math.sin(ph) * (0.06 if plan != "hulk" else 0.1)
                b.location.z = -abs(math.sin(ph)) * 0.03
            elif plan == "blob":
                sc_ = 1 + 0.05 * math.sin(ph)
                b.scale = (sc_, sc_, 1 / sc_)
        if "arms" in anim:
            for k, side in enumerate(("L", "R")):
                if sp.get("hold"):        # both hands forward, gripping a (player-style) gun drawn in-game
                    anim["arms"][side].rotation_euler.y = -0.55
                    anim["arms"][side].rotation_euler.z = -0.45 if side == "L" else 0.45
                elif not sp.get("weapon") or side == "L":
                    anim["arms"][side].rotation_euler.y = math.sin(ph + k * PI) * 0.3
                else:
                    anim["arms"][side].rotation_euler.y = -0.2
        for k, tj in enumerate(anim.get("tents", [])):
            for i, j in enumerate(tj):
                j.rotation_euler.x = math.sin(ph + k * 1.3 - i * 0.7) * 0.35
                j.rotation_euler.y = math.cos(ph * 2 + k - i * 0.5) * 0.25
        for hip, off in anim.get("quadlegs", []):
            hip.rotation_euler.y = math.sin(ph + off * 2 * PI) * 0.5
        for hip, lift, base, s_, off in anim.get("insectlegs", []):
            p = ph + off * 2 * PI
            hip.rotation_euler.z = base + s_ * 0.25 * math.cos(p)
            lift.rotation_euler.y = -0.3 * max(0.0, math.sin(p))
        for i, seg in enumerate(anim.get("segs", [])):
            if plan == "worm":
                seg.location.y = math.sin(ph - i * 0.9) * 0.05 * (0.4 + i * 0.2)
        for i, seg in enumerate(anim.get("coil", [])):
            seg.location.y += 0.0
            seg.rotation_euler.z = math.sin(ph - i * 0.5) * 0.15
        if "head" in anim and plan != "serpent":
            anim["head"].rotation_euler.x = math.sin(ph * 2) * 0.08
    return root, pose


def creature(sp):
    return lambda: build_creature(sp)


# 24 enemies (2 per environment) and 24 bosses (2 per environment).
ENEMY_SPECS = {
    # Limbo
    "shade": dict(plan="flyer", skin="ghost", head="hood", cloth="ghost", glow="soul", extras=["ghost"], arms="claws"),
    "hollow": dict(plan="biped", skin="ash", skin2="marble2", head="eyeless", thick=0.8, arms="claws", extras=["spikes"]),
    # Lust
    "siren": dict(plan="flyer", skin="velvet", head="horned", glow="pinkglow", extras=["wings"], cloth="silk", arms="claws"),
    "thornling": dict(plan="insect", skin="darkwood", skin2="rose", head="maw", extras=["thorns"], thick=0.8),
    # Gluttony
    "glutton": dict(plan="hulk", skin="rot", skin2="mud", head="maw", thick=1.5, extras=["melt"], arms="fists"),
    "maggot": dict(plan="worm", skin="candle", skin2="paper", head="maw", thick=0.9),
    # Greed
    "hoarder": dict(plan="biped", skin="mutant", head="plain", extras=["gold"], hunch=0.6, arms="claws", glow="glow_yellow"),
    "goldgolem": dict(plan="hulk", skin="gold", skin2="gilded", head="helmet", thick=1.4, arms="fists", glow="glow_yellow"),
    # Wrath
    "berserker": dict(plan="hulk", skin="hellskin", head="horned", thick=1.2, extras=["spikes"], arms="blades", weapon="cleaver", dual=True),
    "drowned": dict(plan="biped", skin="plague", skin2="bog", head="melted", extras=["melt"], hunch=0.4, glow="glow_green"),
    # Heresy
    "heretic": dict(plan="biped", skin="hellskin", head="hood", cloth="robe2", extras=["robe"], weapon="staff", glow="glow_orange", arms="claws"),
    "pyrewraith": dict(plan="biped", skin="charred", head="skull", glow="glow_orange", extras=["fire"], thick=0.8, arms="claws"),
    # Violence
    "flayed": dict(plan="biped", skin="muscle", head="brain", weapon="gun", extras=["melt", "tubes"], glow="glow_red", arms="claws"),
    "harpy": dict(plan="flyer", skin="bull", head="horned", extras=["wings"], cloth="robe2", glow="glow_red", arms="claws"),
    # Nuclear
    "meltgunner": dict(plan="biped", skin="meltgreen", head="melted", weapon="gun", extras=["melt", "tank"], glow="radglow", glowmat="radglow"),
    "radhound": dict(plan="quad", skin="meltgreen", skin2="muscle", head="hound", glow="radglow", extras=["spikes"]),
    # Biotech
    "specimen": dict(plan="biped", skin="labwhite", skin2="muscle", head="eyeless", thick=0.8, arms="blades", extras=["tubes"]),
    "sporewalker": dict(plan="biped", skin="plague", head="mushroom", accent="leech2", glow="tealglow", extras=["biomass"], arms="claws"),
    # Sewage
    "eelmaw": dict(plan="biped", skin="leech", skin2="sludge", head="maw", arms="tentacles", accent="leech2", thick=1.2, glow="glow_yellow"),
    "sludgegunner": dict(plan="biped", skin="melt", skin2="sludge", head="melted", weapon="gun", extras=["melt"], glow="glow_yellow"),
    # Chemical
    "meltman": dict(plan="biped", skin="melt", head="gasmask", accent="hazmat", weapon="gun", extras=["melt", "tank"], glowmat="chempurple",
                    glow="purpleglow"),
    "acidcrab": dict(plan="insect", skin="corroded", skin2="chemyellow", head="maw", thick=1.0),
    # Castle
    "revenant": dict(plan="biped", skin="bone", head="helmet", accent="banner", extras=["armor"], weapon="sword", glow="soul"),
    "bowman": dict(plan="biped", skin="bone", head="skull", weapon="crossbow", thick=0.8, glow="soul", arms="claws"),
}

BOSS_SPECS = {
    "gatekeeper": dict(plan="flyer", skin="ghost", head="hood", cloth="robe", glow="soul", extras=["ghost", "robe"], weapon="staff", thick=1.4),
    "ashcolossus": dict(plan="hulk", skin="marble2", skin2="ash", head="eyeless", thick=1.6, arms="fists", extras=["spikes"]),
    "tempestqueen": dict(plan="flyer", skin="velvet", head="crown", glow="pinkglow", extras=["wings", "core"], glowmat="pinkglow", cloth="silk"),
    "entwined": dict(plan="blob", skin="mutant", skin2="velvet", head="maw", tentacles=6, accent="rose", thick=1.2),
    "gorged": dict(plan="blob", skin="rot", skin2="mud", head="maw", tentacles=4, thick=1.5, extras=["melt"]),
    "triplemaw": dict(plan="quad", skin="hellskin", skin2="charred", head="hound", glow="glow_orange", extras=["spikes", "fire"], thick=1.4),
    "goldenmaw": dict(plan="quad", skin="gold", skin2="gilded", head="bullskull", glow="glow_yellow", extras=["gold"], thick=1.5),
    "midasengine": dict(plan="mech", skin="gilded", skin2="gold", head="crown", weapon="minigun", dual=True, extras=["core"], glowmat="glow_yellow"),
    "wrathful": dict(plan="hulk", skin="hellskin", head="horned", thick=1.7, extras=["spikes", "fire"], weapon="cleaver", dual=True),
    "leviathan": dict(plan="serpent", skin="bog", skin2="plague", head="maw", glow="glow_green", thick=1.5),
    "archheretic": dict(plan="flyer", skin="hellskin", head="crown", cloth="robe2", extras=["robe", "fire"], weapon="staff", glow="glow_orange"),
    "tombtitan": dict(plan="mech", skin="tombstone", skin2="cinder", head="skull", extras=["armor", "fire"], arms="fists", thick=1.5,
                      glow="glow_orange"),
    "butcherking": dict(plan="hulk", skin="bull", head="bullskull", thick=1.6, weapon="cleaver", extras=["spikes"], glow="glow_red"),
    "thornmother": dict(plan="tree", skin="deadwood", glow="glow_red", tentacles=6, extras=["thorns"], thick=1.3),
    "coreabom": dict(plan="blob", skin="meltgreen", skin2="lead", head="melted", tentacles=5, extras=["core", "melt"], glowmat="radglow",
                     glow="radglow", thick=1.5),
    "liquidator": dict(plan="mech", skin="hazmat", skin2="lead", head="gasmask", accent="hazmat", weapon="minigun", dual=True, extras=["tank"],
                       glowmat="radglow", glow="radglow", thick=1.3),
    "subjectzero": dict(plan="hulk", skin="labwhite", skin2="muscle", head="eyeless", arms="tentacles", accent="muscle", thick=1.5,
                        extras=["tubes", "biomass"]),
    "hivemind": dict(plan="flyer", skin="brain", head="brain", extras=["tubes", "biomass", "core"], glowmat="tealglow", thick=1.6, arms="tentacles",
                     accent="vein"),
    "sewerking": dict(plan="hulk", skin="leech", skin2="sludge", head="crown", arms="tentacles", accent="leech2", thick=1.6, extras=["melt"],
                      glow="glow_yellow"),
    "gatorbeast": dict(plan="quad", skin="corroded", skin2="sludge", head="hound", glow="glow_yellow", extras=["spikes"], thick=1.6),
    "distiller": dict(plan="mech", skin="corroded", skin2="steel2", head="gasmask", accent="corroded", extras=["tank", "core"], glowmat="chempurple",
                      weapon="minigun", glow="purpleglow", thick=1.4),
    "melttitan": dict(plan="hulk", skin="melt", skin2="sludge", head="melted", weapon="gun", dual=True, extras=["melt", "tank"], glowmat="chemyellow",
                      thick=1.7, glow="glow_yellow"),
    "blackknight": dict(plan="biped", skin="iron", head="helmet", accent="black", extras=["armor"], weapon="sword", thick=1.4, glow="glow_red"),
    "necroking": dict(plan="flyer", skin="bone", head="crown", cloth="robe", extras=["robe", "core"], weapon="staff", glow="soul", glowmat="soul",
                      thick=1.2),
}

for _n, _spec in TILES.items():
    ASSETS[_n] = (_spec, 1, {"idle": 1}, (96, 112) if _n.startswith("wall_") else (72, 72), 0.5 if _n.startswith("wall_") else 0.0)
for _n, (_fn, _res, _tz, _kind) in PROPS.items():
    ASSETS[_n] = (prop(_fn), 1, {"idle": 1}, _res, _tz)
for _n, _spec in ENEMY_SPECS.items():
    _big = _spec.get("thick", 1.0) > 1.2 or _spec["plan"] in ("hulk",)
    ASSETS[_n] = (creature(_spec), 8, {"walk": 6}, (160, 160) if _big else (128, 128), 0.7 if _spec["plan"] != "worm" else 0.3)
for _n, _spec in BOSS_SPECS.items():
    _spec = dict(_spec)
    _spec["scale"] = 2.3
    ASSETS["boss_" + _n] = (creature(_spec), 8, {"walk": 4}, (256, 300), 1.9)
CHARACTER_ASSETS = CHARACTER_ASSETS + tuple(ENEMY_SPECS) + ("boss_",)


# ================================================================ new weapon archetypes
def gun_tac_nuke(p, on_body):
    zr, y = 1.33, (-0.14 if on_body else 0.0)
    cyl("tn_tube", 0.085, 0.8, (0.2, y, zr), M["darkmetal"], p, rot=(0, PI / 2, 0), segs=12)
    for x in (-0.12, 0.3):
        ring("tn_band%.2f" % x, 0.09, 0.05, (x, y, zr), M["hazard"], p, rot=(0, PI / 2, 0), segs=12)
    sphere("tn_head", 0.1, (0.66, y, zr), M["radglow"], p, segs=10, rings=7, smooth=True)
    ring("tn_collar", 0.1, 0.05, (0.6, y, zr), M["lead"], p, rot=(0, PI / 2, 0), segs=12)
    cyl("tn_sym", 0.06, 0.01, (0.2, y + 0.086, zr), M["hazard"], p, rot=(PI / 2, 0, 0), segs=12)
    box("tn_grip", (0.05, 0.05, 0.13), (0.3, y, zr - 0.12), M["darkmetal"], p)
    box("tn_fore", (0.05, 0.05, 0.1), (0.48, y, zr - 0.11), M["darkmetal"], p)
    return dict(muzzle=(0.76, zr), grip=(0.3, y, zr - 0.15), fore=(0.48, y + 0.02, zr - 0.13), rear=(0.0, zr - 0.05))


def gun_nuke(p, on_body):
    zr, y = 1.36, (-0.15 if on_body else 0.0)
    cyl("nk_tube", 0.11, 1.15, (0.2, y, zr), M["lead"], p, rot=(0, PI / 2, 0), segs=14)
    for x in (-0.3, 0.1, 0.5):
        ring("nk_band%.1f" % x, 0.115, 0.06, (x, y, zr), M["hazard"], p, rot=(0, PI / 2, 0), segs=14)
    cyl("nk_war", 0.13, 0.3, (0.92, y, zr), M["hazard"], p, rot=(0, PI / 2, 0), r2=0.02, segs=12)
    sphere("nk_core", 0.07, (0.86, y, zr + 0.11), M["radglow"], p, segs=8, rings=6)
    for k in range(4):
        a = k * PI / 2
        box("nk_fin%d" % k, (0.18, 0.015, 0.1), (-0.38, y + math.cos(a) * 0.12, zr + math.sin(a) * 0.12), M["darkmetal"], p, (a, 0, 0))
    box("nk_grip", (0.06, 0.06, 0.14), (0.25, y, zr - 0.15), M["darkmetal"], p)
    box("nk_fore", (0.06, 0.06, 0.12), (0.5, y, zr - 0.14), M["darkmetal"], p)
    wire("nk_cab", (0.0, y, zr - 0.1), (-0.2, y + 0.05, zr - 0.3), 0.0, 0.02, M["rubber"], p, 4)
    return dict(muzzle=(1.07, zr), grip=(0.25, y, zr - 0.18), fore=(0.5, y + 0.02, zr - 0.16), rear=(0.0, zr - 0.06))


def gun_saw(p, on_body):
    z = GZ
    box("sw_body", (0.36, 0.1, 0.13), (0.45, 0, z), M["hazard"], p)
    cyl("sw_motor", 0.07, 0.14, (0.3, 0, z + 0.08), M["darkmetal"], p, segs=10)
    blade = empty("sw_blade", (0.7, 0, z + 0.1), p)
    cyl("sw_disk", 0.13, 0.012, (0, 0, 0), M["chrome"], blade, segs=16)
    for k in range(12):
        a = k * math.tau / 12
        spike("sw_t%d" % k, (math.cos(a) * 0.12, math.sin(a) * 0.12, 0), (math.cos(a + 0.3) * 0.16, math.sin(a + 0.3) * 0.16, 0), 0.015,
              M["chrome"], blade)
    cyl("sw_hub", 0.03, 0.03, (0, 0, 0), M["darkmetal"], blade, segs=8)
    box("sw_guard", (0.2, 0.12, 0.02), (0.62, 0, z + 0.03), M["darkmetal"], p)
    g_grip(p, 0.36, z)
    box("sw_stock", (0.16, 0.07, 0.1), (0.18, 0, z - 0.01), M["darkmetal"], p)
    return dict(muzzle=(0.86, z + 0.1), grip=(0.36, -0.03, z - 0.09), fore=(0.6, 0.06, z - 0.05), rear=(0.28, z))


def _sprayer(p, on_body, tank_mat, glow_mat, pre):
    z = GZ - 0.01
    box(pre + "body", (0.3, 0.08, 0.11), (0.45, 0, z), M["darkmetal"], p)
    bone(pre + "noz", (0.6, 0, z + 0.02), (0.95, 0, z + 0.02), 0.035, M["steel2"], p, r2=0.05)
    ring(pre + "mouth", 0.055, 0.05, (0.95, 0, z + 0.02), M[glow_mat], p, rot=(0, PI / 2, 0))
    for k in range(3):
        ring(pre + "r%d" % k, 0.045, 0.025, (0.68 + k * 0.08, 0, z + 0.02), M[tank_mat], p, rot=(0, PI / 2, 0))
    box(pre + "handle", (0.04, 0.04, 0.1), (0.72, 0, z - 0.07), M["darkmetal"], p)
    g_grip(p, 0.38, z)
    if on_body:
        for s in (1, -1):
            cyl(pre + "tank%d" % s, 0.055, 0.34, (-0.3, s * 0.075, 1.12), M[tank_mat], p, segs=10)
            cyl(pre + "tg%d" % s, 0.035, 0.05, (-0.3, s * 0.075, 1.31), M[glow_mat], p, segs=8)
        wire(pre + "hose", (-0.28, 0.07, 0.95), (0.4, 0.04, z - 0.05), 0.15, 0.022, M["rubber"], p, 8)
    else:
        cyl(pre + "tank", 0.05, 0.25, (0.45, 0.0, z - 0.1), M[tank_mat], p, rot=(0, PI / 2, 0), segs=10)
    return dict(muzzle=(0.98, z + 0.02), grip=(0.38, -0.03, z - 0.09), fore=(0.72, 0.05, z - 0.1), rear=(0.3, z))


def gun_chem(p, on_body):
    return _sprayer(p, on_body, "chemyellow", "radglow", "ch_")


def gun_cryo(p, on_body):
    r = _sprayer(p, on_body, "ice", "glow_cyan", "cr_")
    for k in range(5):
        spike("cr_frost%d" % k, (0.75 + k * 0.04, 0.03 * (k % 2 * 2 - 1), GZ + 0.04), (0.76 + k * 0.04, 0.05 * (k % 2 * 2 - 1), GZ + 0.1),
              0.012, M["ice"], p)
    return r


_NEW_GUNS = {"tac_nuke": gun_tac_nuke, "nuke": gun_nuke, "saw": gun_saw, "chem": gun_chem, "cryo": gun_cryo}
GUNS.update(_NEW_GUNS)
for _arch in _NEW_GUNS:
    ASSETS["torso_" + _arch] = (torso_builder(_arch), 16, {"idle": 1}, (128, 128), 0.6)
    ASSETS["gun_" + _arch] = (gunpickup_builder(_arch), 1, {"idle": 8}, (80, 80), 0.3)


# ================================================================ signature enemies (one per biome)
mat("pinkmelt", (0.75, 0.25, 0.4), 0.0, 0.08)
mat("pinkmelt2", (0.55, 0.12, 0.25), 0.0, 0.1)
_old_extras = body_extras


def body_extras(torso, sp, th):
    _old_extras(torso, sp, th)
    for ex in sp.get("extras", []):
        if ex == "chains":
            for k in range(5):
                y0 = RNG.uniform(-0.15, 0.15) * th
                wire("xch%d" % k, (RNG.uniform(-0.1, 0.1), y0, 0.45), (RNG.uniform(-0.1, 0.15), y0 * 1.4, RNG.uniform(-0.3, 0.0)), 0.0, 0.014,
                     M["iron"], torso, 6, wobble=0.03)
                sphere("xchh%d" % k, 0.03, (0.05, y0 * 1.4, -0.3), M["iron"], torso, segs=6, rings=4)
        elif ex == "towershield":
            box("xts", (0.05, 0.42, 0.75), (0.32 * th, 0.12, 0.1), M["iron"], torso)
            box("xtsb", (0.055, 0.32, 0.65), (0.34 * th, 0.12, 0.1), M["banner"], torso)
            sphere("xtsc", 0.06, (0.37 * th, 0.12, 0.15), M["gold"], torso)
        elif ex == "veil":
            cyl("xv", 0.2 * th, 0.5, (0.02, 0, 0.55), M[sp.get("cloth", "marble")], torso, r2=0.08, segs=10)
            for k in range(6):
                drip("xvt%d" % k, (RNG.uniform(-0.1, 0.12), RNG.uniform(-0.15, 0.15), 0.4), RNG.uniform(0.1, 0.3), 0.03, M[sp.get("cloth", "marble")], torso)


SIG_SPECS = {
    "pinkmelt": dict(plan="biped", skin="pinkmelt", skin2="pinkmelt2", head="melted", extras=["melt", "melt"], hold=True, glow="glow_yellow", arms="none"),
    "bonepriest": dict(plan="biped", skin="bone", head="skull", extras=["robe", "core"], cloth="velvet", weapon="staff", glow="soul", glowmat="soul"),
    "rustbound": dict(plan="hulk", skin="rust", skin2="rust2", head="eyeless", extras=["chains", "spikes"], thick=1.3, arms="claws"),
    "wendigo": dict(plan="quad", skin="frost", skin2="bone_dirty", head="bullskull", glow="glow_cyan", extras=["spikes"], thick=1.1),
    "cinderfiend": dict(plan="insect", skin="hellrock", skin2="cinder", head="maw", extras=["fire"], thick=1.1, glow="glow_orange"),
    "mourner": dict(plan="biped", skin="marble", skin2="marble2", head="eyeless", extras=["veil", "robe"], cloth="marble", arms="claws", hunch=0.5),
    "enthraller": dict(plan="flyer", skin="velvet", head="horned", extras=["wings", "core"], cloth="silk", glow="pinkglow", glowmat="pinkglow", arms="claws"),
    "devourer": dict(plan="blob", skin="rot", skin2="flesh", head="maw", tentacles=2, thick=1.3, glow="glow_yellow"),
    "chestmimic": dict(plan="blob", skin="wood", skin2="gold", head="maw", tentacles=4, thick=0.8, accent="flesh", glow="glow_yellow", extras=["gold"]),
    "boghag": dict(plan="biped", skin="plague", head="hood", cloth="peat", extras=["robe", "biomass"], accent="moss", weapon="staff", glow="glow_green", hunch=0.6),
    "flagellant": dict(plan="biped", skin="muscle", head="hood", cloth="robe2", extras=["chains", "spikes"], arms="claws", glow="glow_red"),
    "hookman": dict(plan="biped", skin="bull", head="maw", weapon="cleaver", dual=True, extras=["armor"], glow="glow_red", thick=1.1),
    "raddrone": dict(plan="flyer", skin="hazmat", head="gasmask", accent="hazmat", extras=["tank", "core"], glowmat="radglow", glow="radglow", arms="claws"),
    "clone": dict(plan="biped", skin="labwhite", skin2="teal", head="eyeless", extras=["tubes"], thick=0.9, arms="claws", glow="tealglow"),
    "lurker": dict(plan="worm", skin="sludge", skin2="leech", head="maw", thick=1.15, glow="glow_yellow"),
    "hazmatsprayer": dict(plan="biped", skin="hazmat", head="gasmask", accent="hazmat", weapon="gun", extras=["tank"], glowmat="chemyellow", glow="radglow"),
    "shieldbearer": dict(plan="biped", skin="iron", head="helmet", accent="banner", extras=["armor", "towershield"], weapon="sword", glow="glow_red"),
}
for _n, _spec in SIG_SPECS.items():
    _big = _spec.get("thick", 1.0) > 1.2 or _spec["plan"] == "hulk"
    ASSETS[_n] = (creature(_spec), 8, {"walk": 6}, (160, 160) if _big else (128, 128), 0.7 if _spec["plan"] != "worm" else 0.3)
CHARACTER_ASSETS = CHARACTER_ASSETS + tuple(SIG_SPECS)

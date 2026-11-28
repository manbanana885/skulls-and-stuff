# Spawning stations (replace the old generic hive pod). Exec'd by build_assets.py after monsters.py.
#   st_carcass     a huge rotting carcass, ribs open, crawling with maggots     - maggots, leeches, roaches
#   st_grave       a cracked tombstone over a heaving grave, a hand clawing out  - zombies and the other risen dead
#   st_vat         a big glass tank of pink fluid with something melting inside - the melty gunners and lab mutants
#   st_fabricator  a hazard-striped factory box with a glowing hatch and an arm - robots
#   st_hellgate    a rune circle of horns round a pit of fire                   - imps and the other demons
#   st_nest        a clutch of leathery eggs in webbing, one hatched            - spiders, snakes, scorpions

mat("dirt", (0.13, 0.09, 0.06), 0.0, 0.95)
mat("dirt2", (0.08, 0.055, 0.035), 0.0, 1.0)
mat("tombstone", (0.36, 0.36, 0.38), 0.0, 0.85)
mat("tombmoss", (0.10, 0.16, 0.06), 0.0, 0.9)
mat("rotflesh", (0.38, 0.13, 0.10), 0.0, 0.45)
mat("rotflesh2", (0.30, 0.20, 0.12), 0.0, 0.6)
mat("maggot", (0.88, 0.84, 0.70), 0.0, 0.35)
mat("pinkfluid", (0.95, 0.35, 0.65), 0.0, 0.1, emit=(1.0, 0.35, 0.7), strength=1.1, alpha=0.5)
mat("pinkflesh", (0.35, 0.05, 0.18), 0.0, 0.3)
mat("hellfire", (1.0, 0.45, 0.05), 0.0, 0.3, emit=(1.0, 0.4, 0.05), strength=6.0)
mat("hellrune", (1.0, 0.2, 0.05), 0.0, 0.3, emit=(1.0, 0.18, 0.04), strength=5.0)
mat("horn", (0.22, 0.17, 0.12), 0.0, 0.4)
mat("eggshell", (0.55, 0.50, 0.36), 0.0, 0.35)
mat("eggshell2", (0.40, 0.34, 0.22), 0.0, 0.45)
mat("web", (0.80, 0.80, 0.78), 0.0, 0.6)


def build_st_carcass():
    r = tile_root()
    pool("cpool", (0.0, 0.0, 0.002), 1.1, r, n=5)
    body = empty("cbody", (0, 0, 0), r)
    sphere("hide", 0.55, (-0.12, 0.0, 0.16), M["rotflesh"], body, (1.25, 0.72, 0.5), 14, 9, True)
    sphere("hide2", 0.32, (-0.42, 0.12, 0.14), M["rotflesh2"], body, (1.1, 0.9, 0.6), 10, 7, True)
    rc = ribcage("crib", (0.1, 0.0, 0.26), body, 2.1, M["bone_dirty"], broken=True)
    rc.rotation_euler = (0, -1.4, 0.0)
    guts("cgut", (0.15, 0.05, 0.2), (0.6, 0.4, -1), 7, 0.045, body, droop=0.3)
    guts("cgut2", (0.05, -0.1, 0.2), (0.3, -0.7, -1), 6, 0.04, body, droop=0.3)
    skull_prop("chead", (0.58, -0.05, 0.05), r, 2.4, 0.3, M["bone_dirty"])
    for k, sgn in enumerate((-1, 1)):                     # horns on the dead beast's skull
        spike("chorn%d" % k, (0.62, sgn * 0.12, 0.28), (0.5, sgn * 0.34, 0.5), 0.045, M["horn"], r)
    for k in range(4):                                    # legs sticking up stiff
        a = -0.6 + k * 0.4
        sg = (-1) ** k
        knee = (-0.3 + k * 0.14, sg * 0.5, 0.34)
        bone("cleg%d" % k, (-0.25 + k * 0.12, sg * 0.28, 0.2), knee, 0.05, M["rotflesh2"], body)
        bone("cshin%d" % k, knee, (-0.38 + k * 0.16, sg * 0.66, 0.12), 0.035, M["bone_dirty"], body)
    mags = []
    for k in range(14):
        a = k * 2.4
        rr = 0.15 + 0.3 * ((k * 37) % 10) / 10
        m = sphere("mag%d" % k, 0.045, (math.cos(a) * rr - 0.05, math.sin(a) * rr * 0.7, 0.32 + 0.06 * math.sin(k)), M["maggot"],
                   body, (1.8, 1.0, 0.9), 6, 4, True, (0, 0, a))
        mags.append((m, m.location.copy(), a))
    for k in range(5):
        drip("cdrip%d" % k, (math.cos(k * 1.3) * 0.4, math.sin(k * 1.3) * 0.25, 0.12), 0.1, 0.02, M["blood"], body)

    def pose(anim, t):
        s = 1.0 + 0.04 * math.sin(2 * PI * t)
        body.scale = (s, s, 1.0 / s)
        for i, (m, base, a) in enumerate(mags):
            ph = 2 * PI * t + i
            m.location = (base.x + 0.03 * math.cos(a) * math.sin(ph), base.y + 0.03 * math.sin(a) * math.sin(ph), base.z)
            m.rotation_euler.z = a + 0.5 * math.sin(ph)
    return r, pose


def build_st_grave():
    r = tile_root()
    mound = empty("mound", (0, 0, 0), r)
    sphere("dirt", 0.5, (0.05, 0.0, 0.0), M["dirt"], mound, (1.15, 0.8, 0.28), 12, 8, True)
    for k in range(9):
        a = k * 0.7
        sphere("clod%d" % k, 0.06 + 0.02 * (k % 3), (math.cos(a) * 0.5, math.sin(a) * 0.4, 0.05), M["dirt2"], mound,
               (1, 1, 0.7), 6, 4)
    stone = empty("stone", (-0.38, 0.0, 0.0), r, (0, 0.12, 0))
    box("slab", (0.12, 0.42, 0.62), (0, 0, 0.31), M["tombstone"], stone)
    cyl("slabtop", 0.21, 0.12, (0, 0, 0.62), M["tombstone"], stone, (PI / 2, 0, PI / 2), segs=12)
    box("crack", (0.13, 0.025, 0.3), (0, 0.06, 0.45), M["black"], stone, (0.5, 0, 0))
    box("moss", (0.13, 0.36, 0.1), (0, 0, 0.06), M["tombmoss"], stone)
    box("plinth", (0.2, 0.52, 0.08), (0, 0, 0.04), M["concrete2"], stone)
    box("cross1", (0.02, 0.05, 0.22), (0.07, 0, 0.42), M["concrete"], stone)
    box("cross2", (0.02, 0.18, 0.05), (0.07, 0, 0.46), M["concrete"], stone)
    hand = empty("hand", (0.2, 0.05, 0.12), r)
    hand.scale = (1.6, 1.6, 1.6)
    bone("arm", (0, 0, -0.1), (0.05, 0.02, 0.22), 0.035, M["zskin"], hand)
    for k in range(4):
        a = -0.6 + k * 0.4
        bone("fing%d" % k, (0.05, 0.02, 0.22), (0.05 + math.cos(a) * 0.05, 0.02 + math.sin(a) * 0.08, 0.34), 0.012, M["bone_dirty"], hand)
    skull_prop("gsk", (0.3, -0.3, 0.02), r, 0.8, 1.2, M["bone_dirty"])
    bone_prop("gb1", (-0.05, 0.35, 0.03), (0.25, 0.42, 0.03), r)
    for k, (x, y) in enumerate(((-0.25, 0.32), (-0.2, -0.33))):
        cyl("gcan%d" % k, 0.03, 0.12, (x, y, 0.06), M["candle"], r, segs=6)
        sphere("gfl%d" % k, 0.022, (x, y, 0.14), M["candleflame"], r, (1, 1, 1.6), 6, 4)

    def pose(anim, t):
        hand.rotation_euler = (0.25 * math.sin(2 * PI * t), 0.15 * math.cos(2 * PI * t), 0)
        s = 1.0 + 0.05 * math.sin(2 * PI * t + 1)
        mound.scale = (1, 1, s)
    return r, pose


def build_st_vat():
    r = tile_root()
    cyl("vbase", 0.46, 0.18, (0, 0, 0.09), M["darkmetal"], r, segs=14)
    box("vhaz", (0.02, 0.4, 0.08), (0.46, 0, 0.09), M["hazard"], r)
    cyl("vtop", 0.44, 0.12, (0, 0, 1.36), M["darkmetal"], r, segs=14)
    cyl("vcap", 0.2, 0.1, (0, 0, 1.46), M["steel"], r, segs=10)
    fluid = cyl("vfluid", 0.38, 1.12, (0, 0, 0.74), M["pinkfluid"], r, segs=14)
    thing = empty("thing", (0, 0, 0.72), r)
    sphere("tb", 0.17, (0, 0, 0), M["pinkflesh"], thing, (1, 0.9, 1.35), 10, 8, True)
    sphere("th", 0.1, (0.02, 0, 0.28), M["pinkflesh"], thing, (1, 1, 1.1), 8, 6, True)
    sphere("teye", 0.025, (0.11, 0.03, 0.3), M["glow_white"], thing, segs=6, rings=4)
    for k, sgn in enumerate((-1, 1)):
        bone("tarm%d" % k, (0, sgn * 0.14, 0.08), (0.06, sgn * 0.24, -0.15), 0.05, M["pinkflesh"], thing)
    for k in range(3):
        drip("tdrip%d" % k, (math.cos(k * 2.1) * 0.12, math.sin(k * 2.1) * 0.1, -0.15), 0.12, 0.03, M["pinkflesh"], thing)
    for k in range(4):                                     # frame struts
        a = k * PI / 2 + PI / 4
        box("vstrut%d" % k, (0.04, 0.04, 1.2), (math.cos(a) * 0.42, math.sin(a) * 0.42, 0.75), M["steel2"], r)
    for k in range(3):
        a = k * 2.1 + 0.5
        wire("vpipe%d" % k, (math.cos(a) * 0.3, math.sin(a) * 0.3, 1.42), (math.cos(a) * 0.62, math.sin(a) * 0.62, 0.02), 0.0, 0.035,
             M["rubber" if k else "wire_red"], r, 6, bulge=(math.cos(a) * 0.2, math.sin(a) * 0.2, 0.15))
    sphere("vlight", 0.035, (0.32, 0.25, 1.4), M["glow_red"], r)
    bubs = []
    for k in range(8):
        b = sphere("vbub%d" % k, 0.022, (math.cos(k * 1.9) * 0.25, math.sin(k * 1.9) * 0.25, 0.3), M["glow_white"], r, segs=6, rings=4)
        bubs.append((b, k / 8))

    def pose(anim, t):
        thing.location.z = 0.72 + 0.04 * math.sin(2 * PI * t)
        thing.rotation_euler.z = 0.3 * math.sin(2 * PI * t)
        for b, off in bubs:
            b.location.z = 0.25 + ((t + off) % 1.0) * 1.0
    return r, pose


def build_st_fabricator():
    r = tile_root()
    box("fbody", (0.86, 0.86, 0.62), (0, 0, 0.31), M["steel2"], r)
    box("froof", (0.9, 0.9, 0.06), (0, 0, 0.65), M["darkmetal"], r)
    for k in range(5):                                     # hazard stripes round the base
        box("fstripe%d" % k, (0.88, 0.07, 0.05), (0, -0.36 + k * 0.18, 0.05), M["hazard" if k % 2 else "black"], r, (0, 0, 0))
    box("fhatch", (0.04, 0.5, 0.36), (0.43, 0, 0.26), M["black"], r)
    glow_ = box("fglow", (0.03, 0.44, 0.3), (0.44, 0, 0.26), M["glow_orange"], r)
    for k in range(4):                                     # shutter slats
        box("fslat%d" % k, (0.03, 0.5, 0.03), (0.455, 0, 0.12 + k * 0.1), M["darkmetal"], r)
    box("rollers", (0.3, 0.5, 0.05), (0.6, 0, 0.04), M["rubber"], r)
    for k in range(4):
        cyl("roll%d" % k, 0.03, 0.5, (0.48 + k * 0.08, 0, 0.07), M["steel"], r, (PI / 2, 0, 0), segs=6)
    for k in range(3):
        box("fvent%d" % k, (0.5, 0.03, 0.03), (-0.05, -0.43, 0.35 + k * 0.08), M["black"], r)
    cyl("fstack", 0.08, 0.3, (-0.25, 0.25, 0.83), M["darkmetal"], r, segs=8)
    arm = empty("arm", (0.1, -0.1, 0.68), r)
    cyl("abase", 0.1, 0.06, (0, 0, 0.03), M["hazard"], arm, segs=10)
    bone("a1", (0, 0, 0.03), (0.12, 0, 0.32), 0.04, M["steel"], arm)
    bone("a2", (0.12, 0, 0.32), (0.32, 0, 0.22), 0.032, M["steel"], arm)
    sphere("ajoint", 0.05, (0.12, 0, 0.32), M["darkmetal"], arm)
    spike("aclaw1", (0.32, 0.02, 0.22), (0.38, 0.06, 0.12), 0.015, M["chrome"], arm)
    spike("aclaw2", (0.32, -0.02, 0.22), (0.38, -0.06, 0.12), 0.015, M["chrome"], arm)
    lights = [sphere("flight%d" % k, 0.035, (0.2 + k * 0.1, -0.36, 0.66), M["glow_red" if k == 1 else "glow_yellow"], r) for k in range(3)]
    box("fpanel", (0.02, 0.2, 0.14), (-0.43, 0.15, 0.4), M["circuit"], r)

    def pose(anim, t):
        arm.rotation_euler.z = 1.2 * math.sin(2 * PI * t)
        for k, l in enumerate(lights):
            l.hide_render = (int(t * 4) + k) % 3 == 0
        glow_.scale = (1, 1, 0.85 + 0.15 * math.sin(2 * PI * t))
    return r, pose


def build_st_hellgate():
    r = tile_root()
    cyl("hstone", 0.58, 0.06, (0, 0, 0.03), M["hellrock"], r, segs=16)
    ring("hrune", 0.5, 0.02, (0, 0, 0.065), M["hellrune"], r, segs=20)
    ring("hrune2", 0.36, 0.02, (0, 0, 0.065), M["hellrune"], r, segs=16)
    for k in range(5):                                     # pentagram lines
        a1, a2 = k * 2 * PI / 5, (k + 2) * 2 * PI / 5
        p1 = Vector((math.cos(a1) * 0.5, math.sin(a1) * 0.5, 0.068))
        p2 = Vector((math.cos(a2) * 0.5, math.sin(a2) * 0.5, 0.068))
        bone("hline%d" % k, p1, p2, 0.012, M["hellrune"], r)
    pit = empty("pit", (0, 0, 0.07), r)
    cyl("hpit", 0.26, 0.02, (0, 0, 0.0), M["lava"], pit, segs=14)
    cyl("hpit2", 0.16, 0.025, (0, 0, 0.005), M["hellfire"], pit, segs=12)
    flames = []
    for k in range(7):
        a = k * 2 * PI / 7
        f = spike("hfl%d" % k, (math.cos(a) * 0.12, math.sin(a) * 0.12, 0.0), (math.cos(a) * 0.08, math.sin(a) * 0.08, 0.35),
                  0.05, M["flame" if k % 2 else "hellfire"], pit)
        flames.append(f)
    for k in range(5):                                     # horn pillars at the star's points
        a = k * 2 * PI / 5
        x, y = math.cos(a) * 0.5, math.sin(a) * 0.5
        spike("hhorn%d" % k, (x, y, 0.06), (x * 0.85, y * 0.85, 0.55), 0.06, M["horn"], r)
        skull_prop("hsk%d" % k, (x * 1.05, y * 1.05, 0.06), r, 0.6, a, M["bone_dirty"])

    def pose(anim, t):
        pit.rotation_euler.z = 2 * PI * t / 5
        for k, f in enumerate(flames):
            f.scale = (1, 1, 0.75 + 0.35 * abs(math.sin(2 * PI * t + k)))
    return r, pose


def build_st_nest():
    r = tile_root()
    pool("npool", (0, 0, 0.002), 0.55, r, M["slime"], 4)
    sphere("nbed", 0.5, (0, 0, 0.0), M["dirt2"], r, (1.1, 1.0, 0.18), 12, 6, True)
    eggs = []
    spots = [(-0.15, -0.1, 0.24), (0.15, -0.15, 0.2), (0.0, 0.2, 0.22), (-0.32, 0.15, 0.17), (0.3, 0.18, 0.16), (0.1, 0.0, 0.3)]
    for k, (x, y, s) in enumerate(spots):
        e = sphere("egg%d" % k, s * 0.75, (x, y, s * 0.5), M["eggshell" if k % 2 else "eggshell2"], r, (0.85, 0.85, 1.25), 10, 8, True)
        eggs.append((e, k))
        for j in range(2):
            a = k + j * 2.5
            bone("ev%d_%d" % (k, j), (x + math.cos(a) * s * 0.4, y + math.sin(a) * s * 0.4, s * 0.25),
                 (x + math.cos(a) * s * 0.3, y + math.sin(a) * s * 0.3, s * 0.85), 0.008, M["vein"], e)
    # the hatched one: torn shell halves and goo
    sphere("eggb", 0.12, (0.38, -0.25, 0.05), M["eggshell"], r, (1, 1, 0.6), 8, 6, True)
    sphere("eggg", 0.07, (0.38, -0.25, 0.1), M["glow_green_dim"], r, (1, 1, 0.5), 8, 5, True)
    spike("shard1", (0.3, -0.3, 0.05), (0.27, -0.36, 0.18), 0.03, M["eggshell"], r)
    spike("shard2", (0.46, -0.2, 0.05), (0.5, -0.16, 0.16), 0.03, M["eggshell"], r)
    for k in range(6):                                     # webbing over the clutch
        a = k * PI / 3
        wire("nweb%d" % k, (math.cos(a) * 0.55, math.sin(a) * 0.5, 0.02), (math.cos(a + PI) * 0.2, math.sin(a + PI) * 0.2, 0.32),
             0.0, 0.006, M["web"], r, 5, bulge=(0, 0, 0.12))
    bone_prop("nb1", (-0.45, -0.3, 0.03), (-0.2, -0.42, 0.03), r)

    def pose(anim, t):
        for e, k in eggs:
            s = 1.0 + 0.06 * math.sin(2 * PI * t + k * 1.3)
            e.scale = (0.85 * s, 0.85 * s, 1.25 / s)
    return r, pose


for _n, _fn, _canvas, _tz in (("st_carcass", build_st_carcass, (144, 128), 0.3), ("st_grave", build_st_grave, (128, 128), 0.4),
                              ("st_vat", build_st_vat, (128, 176), 0.8), ("st_fabricator", build_st_fabricator, (144, 144), 0.45),
                              ("st_hellgate", build_st_hellgate, (144, 128), 0.3), ("st_nest", build_st_nest, (128, 128), 0.25)):
    ASSETS[_n] = (_fn, 1, {"idle": 4}, _canvas, _tz)
CHARACTER_ASSETS = CHARACTER_ASSETS + ("st_",)

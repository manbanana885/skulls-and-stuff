# Heavy gunners, vermin, fire demons and the Ocularch. Exec'd by build_assets.py after expansion.py (uses its helpers).
#   Pink Heavy, imp, pit demon, devil: the shared creature() builder (plus a trident and a devil's tail added here)
#   viper, cobra, scorpion, roach: hand-built bodies with their own walk cycles
#   boss_ocularch: a floating eye ringed with eyestalks, each eye glowing the colour of its ray

mat("roachshell", (0.22, 0.09, 0.03), 0.0, 0.18)
mat("roachshell2", (0.12, 0.05, 0.02), 0.0, 0.3)
mat("roachleg", (0.16, 0.08, 0.03), 0.0, 0.45)
mat("viperscale", (0.30, 0.34, 0.10), 0.0, 0.35)
mat("viperscale2", (0.16, 0.14, 0.05), 0.0, 0.4)
mat("viperbelly", (0.62, 0.56, 0.32), 0.0, 0.5)
mat("cobrascale", (0.12, 0.10, 0.08), 0.0, 0.3)
mat("cobrahood", (0.55, 0.42, 0.14), 0.0, 0.4)
mat("scorpshell", (0.30, 0.16, 0.04), 0.1, 0.22)
mat("scorpshell2", (0.12, 0.06, 0.02), 0.1, 0.3)
mat("eyewhite", (0.92, 0.88, 0.82), 0.0, 0.15)
mat("oculflesh", (0.42, 0.20, 0.40), 0.0, 0.35)
mat("oculflesh2", (0.26, 0.10, 0.26), 0.0, 0.45)
mat("ocul_iris", (0.95, 0.70, 0.15), 0.0, 0.3, emit=(1.0, 0.75, 0.2), strength=3.0)
mat("tongue", (0.75, 0.12, 0.18), 0.0, 0.3)
mat("venomglow", (0.55, 0.95, 0.25), 0.0, 0.3, emit=(0.55, 1.0, 0.2), strength=4.0)


# ---------------------------------------------------------------- additions to the shared creature builder
_mon_old_weapon_build = weapon_build


def weapon_build(kind, hand, sp):
    if kind == "trident":
        bone("trs", (-0.35, 0, -0.12), (0.55, 0, 0.06), 0.017, M["darkmetal"], hand)
        bone("trc", (0.52, -0.09, 0.055), (0.52, 0.09, 0.055), 0.016, M["darkmetal"], hand)
        for s_ in (-1, 0, 1):
            spike("trt%d" % s_, (0.52, s_ * 0.09, 0.055), (0.74 - abs(s_) * 0.05, s_ * 0.1, 0.09), 0.02, M["chrome"], hand)
        sphere("trg", 0.035, (0.5, 0, 0.055), M[sp.get("glow", "glow_red")], hand)
    else:
        _mon_old_weapon_build(kind, hand, sp)


_mon_old_extras = body_extras


def body_extras(torso, sp, th):
    _mon_old_extras(torso, sp, th)
    for ex in sp.get("extras", []):
        if ex == "tail":           # a long whip of a tail ending in a spade
            pts = [Vector((-0.1, 0, 0.02)), Vector((-0.22, 0.03, -0.14)), Vector((-0.36, -0.03, -0.26)), Vector((-0.5, 0.03, -0.27)),
                   Vector((-0.6, 0.0, -0.18))]
            tube("xtl", pts, 0.03 * th, M[sp.get("skin", "hellskin")], torso, segs=6, r_end=0.012)
            spike("xtls", (-0.6, 0, -0.18), (-0.66, 0, -0.05), 0.05, M[sp.get("skin2", sp.get("skin", "hellskin"))], torso)
        elif ex == "batwings":     # leathery, bigger than the cloth wings
            for s_ in (-1, 1):
                wg = empty("xbw%d" % s_, (-0.1, s_ * 0.12, 0.38), torso)
                tips = [(-0.15, s_ * 0.55, 0.45), (-0.3, s_ * 0.7, 0.15), (-0.32, s_ * 0.6, -0.15)]
                for k, tp in enumerate(tips):
                    bone("xbwb%d%d" % (s_, k), (0, 0, 0), tp, 0.016, M["bone_dirty"], wg)
                box("xbwm%d" % s_, (0.32, 0.6, 0.012), (-0.2, s_ * 0.36, 0.12), M[sp.get("wingskin", "charred")], wg, (s_ * 0.35, 0.25, 0))


MON_SPECS = {
    "pinkheavy": dict(plan="hulk", skin="pinkmelt", skin2="pinkmelt2", head="melted", extras=["melt", "melt"], hold=True,
                      glow="glow_yellow", arms="none", thick=1.5),
    "imp": dict(plan="flyer", skin="hellskin", skin2="charred", head="horned", extras=["batwings", "tail"], thick=0.7, scale=0.78,
                arms="claws", glow="glow_orange"),
    "pitdemon": dict(plan="hulk", skin="hellskin", skin2="charred", head="horned", extras=["spikes", "fire", "tail"], thick=1.55,
                     arms="claws", glow="glow_orange"),
    "devil": dict(plan="biped", skin="hellskin", skin2="black", head="horned", extras=["batwings", "tail"], weapon="trident",
                  glow="glow_yellow", thick=1.0, wingskin="black"),
}
for _n, _spec in MON_SPECS.items():
    _big = _spec["plan"] == "hulk"
    ASSETS[_n] = (creature(_spec), 8, {"walk": 6}, (160, 160) if _big else (128, 128), 0.7)


# ---------------------------------------------------------------- snakes
def build_snake(cobra=False):
    root = empty("sn_root")
    body = empty("sn_body", (0, 0, 0), root)
    n = 18
    segs = []
    skin = M["cobrascale" if cobra else "viperscale"]
    skin2 = M["cobrahood" if cobra else "viperscale2"]
    rise = 5 if cobra else 0                # the cobra rears up its front segments
    for i in range(n):
        t = i / (n - 1)
        r = (0.085 if cobra else 0.07) * (0.75 + 0.55 * math.sin(math.pi * min(1.0, 0.25 + t * 0.9))) * (1 - 0.6 * t * t)
        if i < rise:
            u = (rise - i) / rise
            loc = (0.18 - i * 0.03, 0, r + 0.42 * u)
        else:
            loc = (0.18 - rise * 0.03 - (i - rise) * 0.075, 0, r)
        seg = empty("sns%d" % i, loc, body)
        sphere("snb%d" % i, r, (0, 0, 0), skin if (i // 2) % 2 == 0 else skin2, seg, (1.35, 1, 0.85), 9, 6, True)
        sphere("snu%d" % i, r * 0.8, (0, 0, -r * 0.35), M["viperbelly"], seg, (1.3, 0.9, 0.5), 7, 4, True)
        segs.append((seg, loc))
    if cobra:   # the hood: a broad flat flap behind the head, with an eye-spot
        sphere("snhood", 0.11, (-0.01, 0, -0.06), M["cobrahood"], segs[1][0], (0.35, 1.7, 1.5), 10, 7, True)
        sphere("snhs", 0.03, (-0.05, 0, -0.04), M["black"], segs[1][0], (0.3, 1.6, 1.0), 6, 4, True)
    head = empty("snh", (0.08 if not cobra else 0.06, 0, 0.0 if not cobra else 0.02), segs[0][0], (0, 0.15 if cobra else 0, 0))
    sphere("snhd", 0.075 if not cobra else 0.085, (0.05, 0, 0), skin, head, (1.6, 1.15, 0.7), 10, 7, True)
    sphere("snjw", 0.06, (0.06, 0, -0.03), M["viperbelly"], head, (1.5, 1.0, 0.4), 8, 5, True)
    for s_ in (-1, 1):
        sphere("sne%d" % s_, 0.018, (0.1, s_ * 0.05, 0.03), M["venomglow"] if not cobra else M["glow_red"], head)
        spike("snf%d" % s_, (0.15, s_ * 0.02, -0.02), (0.16, s_ * 0.02, -0.07), 0.008, M["tooth"], head)
    bone("snt", (0.17, 0, -0.02), (0.27, 0, -0.03), 0.006, M["tongue"], head)
    for s_ in (-1, 1):
        bone("snt%d" % s_, (0.27, 0, -0.03), (0.31, s_ * 0.02, -0.035), 0.004, M["tongue"], head)

    def pose(an, t):
        ph = 2 * PI * t
        for i, (seg, loc) in enumerate(segs):
            if i < rise:
                seg.location = (loc[0], math.sin(ph * 2 + i * 0.3) * 0.012, loc[2])
            else:
                k = i - rise
                amp = 0.09 * min(1.0, (k + 1) / 4)
                seg.location = (loc[0], math.sin(ph - k * 0.55) * amp, loc[2])
                seg.rotation_euler.z = math.cos(ph - k * 0.55) * 0.5 * min(1.0, (k + 1) / 4)
        head.rotation_euler.z = math.sin(ph) * 0.12
    return root, pose


ASSETS["viper"] = (lambda: build_snake(False), 8, {"walk": 6}, (128, 128), 0.25)
ASSETS["cobra"] = (lambda: build_snake(True), 8, {"walk": 6}, (128, 128), 0.45)


# ---------------------------------------------------------------- scorpion
def build_scorpion():
    root = empty("sc_root")
    body = empty("sc_body", (0, 0, 0.2), root)
    sh, sh2 = M["scorpshell"], M["scorpshell2"]
    sphere("scc", 0.15, (0.12, 0, 0.0), sh, body, (1.25, 1.05, 0.5), 12, 8, True)
    for k in range(5):        # abdomen plates
        r = 0.15 - k * 0.012
        sphere("sca%d" % k, r, (-0.04 - k * 0.085, 0, 0.0), sh if k % 2 == 0 else sh2, body, (0.6, 1.1, 0.5), 10, 6, True)
    for s_ in (-1, 1):
        sphere("sce%d" % s_, 0.018, (0.24, s_ * 0.035, 0.06), M["glow_red"], body)
    legs = []
    for s_ in (1, -1):
        for i in range(4):
            hip = empty("scl%d%d" % (s_, i), (0.08 - i * 0.09, s_ * 0.1, -0.01), body, (0, 0, s_ * math.radians(70 + i * 22)))
            lift = empty("sclf%d%d" % (s_, i), (0, 0, 0), hip)
            bone("sclu%d%d" % (s_, i), (0, 0, 0), (0.2, 0, 0.12), 0.02, sh2, lift)
            bone("scld%d%d" % (s_, i), (0.2, 0, 0.12), (0.36, 0, -0.2), 0.016, sh, lift, r2=0.004)
            legs.append((hip, lift, hip.rotation_euler.z, s_, 0.0 if (i % 2 == 0) == (s_ == 1) else 0.5))
    claws = []
    for s_ in (1, -1):        # pincers held forward
        arm = empty("scp%d" % s_, (0.22, s_ * 0.1, 0.0), body, (0, 0, s_ * 0.35))
        bone("scpu%d" % s_, (0, 0, 0), (0.17, 0, 0.03), 0.032, sh, arm)
        bone("scpf%d" % s_, (0.17, 0, 0.03), (0.3, -s_ * 0.06, 0.04), 0.03, sh2, arm)
        sphere("scph%d" % s_, 0.07, (0.36, -s_ * 0.06, 0.04), sh, arm, (1.5, 1.05, 0.75), 10, 7, True)
        fing = empty("scpg%d" % s_, (0.42, -s_ * 0.06, 0.04), arm)
        spike("scpg1%d" % s_, (0, s_ * 0.03, 0), (0.16, s_ * 0.0, 0), 0.03, sh2, fing)
        mov = empty("scpm%d" % s_, (0, -s_ * 0.03, 0), fing)
        spike("scpg2%d" % s_, (0, 0, 0), (0.15, s_ * 0.025, 0), 0.026, sh, mov)
        claws.append((mov, s_))
    tail = empty("sc_tail", (-0.42, 0, 0.02), body)
    pts = []
    for k in range(7):        # arcs up and over the back
        th_ = math.radians(180 - k * 30)
        pts.append(Vector((0.12 + math.cos(th_) * 0.18 + k * 0.01, 0, 0.0 + math.sin(th_) * 0.36 + k * 0.03)))
    for k in range(len(pts) - 1):
        bone("sct%d" % k, pts[k], pts[k + 1], 0.05 - k * 0.005, sh if k % 2 == 0 else sh2, tail, r2=0.045 - k * 0.005)
        sphere("sctj%d" % k, 0.05 - k * 0.005, pts[k + 1], sh2 if k % 2 == 0 else sh, tail, segs=8, rings=5, smooth=True)
    end = pts[-1]
    sphere("scvb", 0.055, end + Vector((0.04, 0, 0)), M["venomglow"], tail, (1.3, 1, 1), 8, 6, True)
    spike("scst", end + Vector((0.07, 0, -0.01)), end + Vector((0.16, 0, -0.12)), 0.022, M["black"], tail)

    def pose(an, t):
        ph = 2 * PI * t
        for hip, lift, base, s_, off in legs:
            p = ph + off * 2 * PI
            hip.rotation_euler.z = base + s_ * 0.22 * math.cos(p)
            lift.rotation_euler.y = -0.3 * max(0.0, math.sin(p))
        tail.rotation_euler.x = math.sin(ph) * 0.12
        tail.rotation_euler.y = math.sin(ph * 2) * 0.06
        for mov, s_ in claws:
            mov.rotation_euler.z = s_ * (0.15 + 0.2 * max(0.0, math.sin(ph * 2)))
    return root, pose


ASSETS["scorpion"] = (build_scorpion, 8, {"walk": 6}, (160, 160), 0.3)


# ---------------------------------------------------------------- giant cockroach
def build_roach():
    root = empty("rc_root")
    body = empty("rc_body", (0, 0, 0.13), root)
    sh, sh2 = M["roachshell"], M["roachshell2"]
    sphere("rcp", 0.12, (0.2, 0, 0.02), sh, body, (0.85, 1.15, 0.38), 12, 8, True)       # pronotum shield
    sphere("rcps", 0.07, (0.22, 0, 0.045), sh2, body, (0.8, 1.0, 0.3), 10, 6, True)
    sphere("rch", 0.055, (0.31, 0, -0.03), sh2, body, (0.9, 1.1, 0.8), 8, 6, True)
    for s_ in (-1, 1):
        sphere("rcwe%d" % s_, 0.15, (-0.12, s_ * 0.055, 0.02), sh, body, (2.0, 0.72, 0.4), 12, 8, True)     # wing covers
        sphere("rcey%d" % s_, 0.016, (0.33, s_ * 0.035, -0.01), M["black"], body)
    sphere("rcab", 0.14, (-0.1, 0, -0.03), sh2, body, (1.9, 1.15, 0.35), 10, 6, True)
    ants = []
    for s_ in (-1, 1):
        a_ = empty("rcan%d" % s_, (0.34, s_ * 0.025, 0.0), body)
        tube("rcat%d" % s_, [Vector((0, 0, 0)), Vector((0.2, s_ * 0.08, 0.08)), Vector((0.42, s_ * 0.2, 0.06)), Vector((0.6, s_ * 0.34, 0.0))],
             0.008, M["roachleg"], a_, segs=4, r_end=0.003)
        ants.append((a_, s_))
        spike("rcce%d" % s_, (-0.38, s_ * 0.03, -0.02), (-0.47, s_ * 0.06, 0.0), 0.012, sh2, body)
    legs = []
    for s_ in (1, -1):
        for i in range(3):
            hip = empty("rcl%d%d" % (s_, i), (0.14 - i * 0.12, s_ * 0.07, -0.04), body, (0, 0, s_ * math.radians(50 + i * 40)))
            lift = empty("rclf%d%d" % (s_, i), (0, 0, 0), hip)
            ln = 1.0 + i * 0.25
            bone("rclu%d%d" % (s_, i), (0, 0, 0), (0.16 * ln, 0, 0.08), 0.018, M["roachleg"], lift)
            bone("rcld%d%d" % (s_, i), (0.16 * ln, 0, 0.08), (0.32 * ln, 0, -0.12), 0.012, M["roachleg"], lift, r2=0.003)
            for k in range(2):     # leg spines
                f = 0.45 + k * 0.3
                p0 = Vector((0.16 * ln, 0, 0.08)).lerp(Vector((0.32 * ln, 0, -0.12)), f)
                spike("rcls%d%d%d" % (s_, i, k), p0, p0 + Vector((0.02, 0, 0.04)), 0.005, sh2, lift)
            legs.append((hip, lift, hip.rotation_euler.z, s_, 0.0 if (i % 2 == 0) == (s_ == 1) else 0.5))

    def pose(an, t):
        ph = 2 * PI * t
        for hip, lift, base, s_, off in legs:
            p = ph + off * 2 * PI
            hip.rotation_euler.z = base + s_ * 0.3 * math.cos(p)
            lift.rotation_euler.y = -0.35 * max(0.0, math.sin(p))
        for a_, s_ in ants:
            a_.rotation_euler.z = s_ * 0.15 * math.sin(ph * 2 + s_)
            a_.rotation_euler.y = -0.1 * math.sin(ph * 2)
        body.location.z = 0.13 + 0.008 * math.sin(ph * 4)
    return root, pose


ASSETS["roach"] = (build_roach, 8, {"walk": 6}, (128, 128), 0.2)


# ---------------------------------------------------------------- boss: the Ocularch
OCUL_EYES = ["glow_red", "glow_cyan", "glow_green", "pinkglow", "glow_white", "glow_orange", "purpleglow", "glow_yellow"]


def build_ocularch():
    root = empty("oc_root")
    body = empty("oc_body", (0, 0, 1.5), root)
    fl, fl2 = M["oculflesh"], M["oculflesh2"]
    sphere("ocb", 0.72, (0, 0, 0), fl, body, (1, 1, 0.95), 20, 14, True)
    for k in range(14):           # warty hide
        a, b = RNG.uniform(0, 2 * PI), RNG.uniform(-0.8, 1.0)
        p0 = Vector((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b))) * 0.68
        if p0.x > 0.35 and abs(p0.z) < 0.4:
            continue              # keep the face clear
        sphere("ocw%d" % k, RNG.uniform(0.06, 0.12), p0, fl2, body, segs=8, rings=6, smooth=True)
    # the great central eye
    sphere("ocew", 0.34, (0.5, 0, 0.1), M["eyewhite"], body, (0.9, 1, 1), 16, 12, True)
    sphere("ocei", 0.18, (0.77, 0, 0.1), M["ocul_iris"], body, (0.35, 1, 1), 14, 10, True)
    sphere("ocep", 0.085, (0.83, 0, 0.1), M["black"], body, (0.3, 0.55, 1.35), 10, 8, True)
    sphere("oclid", 0.37, (0.44, 0, 0.27), fl2, body, (0.9, 1.15, 0.35), 14, 8, True)       # heavy brow
    for k in range(6):
        a = (k - 2.5) * 0.18
        bone("ocvn%d" % k, (0.62, math.sin(a) * 0.3, 0.1 + math.cos(a) * 0.18), (0.74, math.sin(a) * 0.15, 0.1 + math.cos(a) * 0.1),
             0.008, M["vein"], body)
    # a wide toothy maw beneath it
    sphere("ocm", 0.3, (0.52, 0, -0.38), M["black"], body, (0.55, 1.35, 0.4), 14, 8, True)
    for k in range(9):
        y = (k - 4) * 0.085
        spike("octu%d" % k, (0.66 - abs(y) * 0.3, y, -0.3), (0.68 - abs(y) * 0.3, y, -0.4), 0.025, M["tooth"], body)
        spike("octl%d" % k, (0.64 - abs(y) * 0.3, y, -0.48), (0.66 - abs(y) * 0.3, y, -0.38), 0.022, M["tooth"], body)
    # eyestalks: a crown of eight, each eye a different colour (one per ray)
    stalks = []
    for k in range(8):
        a = k * 2 * PI / 8 + PI / 8
        lat = 0.75
        base = Vector((math.cos(a) * math.cos(lat), math.sin(a) * math.cos(lat), math.sin(lat))) * 0.66
        out = Vector((math.cos(a) * 0.7, math.sin(a) * 0.7, 1.0))
        js = tentacle("ocs%d" % k, base, out, 4, 0.16, 0.055, body, fl2)
        tip = js[-1]
        sphere("ocse%d" % k, 0.085, (0, 0, 0.27), M["eyewhite"], tip, segs=10, rings=8, smooth=True)
        sphere("ocsi%d" % k, 0.05, (0.06, 0, 0.29), M[OCUL_EYES[k]], tip, (0.5, 1, 1), 8, 6, True)
        stalks.append(js)
    # dangling feeder tendrils underneath
    tents = []
    for k in range(5):
        a = k * 2 * PI / 5
        tents.append(tentacle("oct%d" % k, (math.cos(a) * 0.35, math.sin(a) * 0.35, -0.55), (math.cos(a) * 0.3, math.sin(a) * 0.3, -1.0),
                              4, 0.14, 0.04, body, fl2))

    def pose(an, t):
        ph = 2 * PI * t
        body.location.z = 1.5 + math.sin(ph) * 0.08
        body.rotation_euler.x = math.sin(ph) * 0.04
        for k, js in enumerate(stalks):
            for i, j in enumerate(js):
                j.rotation_euler.x = math.sin(ph + k * 0.8 - i * 0.6) * 0.22
                j.rotation_euler.y = math.cos(ph + k * 1.3 - i * 0.5) * 0.18
        for k, js in enumerate(tents):
            for i, j in enumerate(js):
                j.rotation_euler.x = math.sin(ph + k - i * 0.7) * 0.3
    return root, pose


ASSETS["boss_ocularch"] = (build_ocularch, 8, {"walk": 4}, (256, 300), 1.9)

CHARACTER_ASSETS = CHARACTER_ASSETS + tuple(MON_SPECS) + ("viper", "cobra", "scorpion", "roach")

# Playable characters besides the Skelebot: CanBot (drum on tank treads, gun on a turret) and Super Mutant
# (pink, melting, blistered). Like the Skelebot, each is a LOWER half (<char>_legs: 8 move directions, walk/idle)
# and an UPPER half per weapon (<prefix><arch>: 16 aim directions), composited in-game so the top turns on its own.
# Guns sit at the same torso-space spot as on the Skelebot, so game/weapons.py MUZZLE stays valid for everyone.
# exec'd by build_assets.py after modules.py.

mat("blister", (0.92, 0.62, 0.5), 0.0, 0.06)
mat("meltdrip", (0.65, 0.18, 0.32), 0.0, 0.05)
mat("tread", (0.05, 0.05, 0.055), 0.6, 0.6)
CHARACTER_ASSETS = CHARACTER_ASSETS + ("canbot_", "mutant_", "cbtorso_", "mttorso_")


# ---------------------------------------------------------------- CanBot
TREAD_LS, TREAD_R, TREAD_Z, TREAD_N = 0.42, 0.11, 0.13, 22
TREAD_P = 2 * TREAD_LS + 2 * PI * TREAD_R


def _tread_path(u):
    """Position (x, z) and pitch along a stadium-shaped track loop, u in [0, TREAD_P)."""
    u %= TREAD_P
    half = TREAD_LS / 2
    if u < TREAD_LS:                                  # bottom run, front to back... moving backward under the hull
        return half - u, TREAD_Z - TREAD_R, 0.0
    u -= TREAD_LS
    arc = PI * TREAD_R
    if u < arc:                                       # rear wheel, going up
        a = u / TREAD_R
        return -half - math.sin(a) * TREAD_R, TREAD_Z - math.cos(a) * TREAD_R, -a
    u -= arc
    if u < TREAD_LS:                                  # top run, back to front
        return -half + u, TREAD_Z + TREAD_R, -PI
    u -= TREAD_LS
    a = u / TREAD_R                                   # front wheel, going down
    return half + math.sin(a) * TREAD_R, TREAD_Z + math.cos(a) * TREAD_R, -PI - a


def build_canbot_legs():
    root = empty("cl_root")
    pads = []
    for s_ in (1, -1):
        y = s_ * 0.2
        box("cl_trackbody%d" % s_, (TREAD_LS, 0.1, TREAD_R * 2 - 0.02), (0, y, TREAD_Z), M["darkmetal"], root)
        for x in (-TREAD_LS / 2, TREAD_LS / 2):
            cyl("cl_sprocket%d%.2f" % (s_, x), TREAD_R - 0.01, 0.1, (x, y, TREAD_Z), M["steel2"], root, rot=(PI / 2, 0, 0), segs=12)
            cyl("cl_hub%d%.2f" % (s_, x), 0.04, 0.13, (x, y, TREAD_Z), M["chrome"], root, rot=(PI / 2, 0, 0), segs=8)
        for k, x in enumerate((-0.1, 0.0, 0.1)):
            cyl("cl_wheel%d%d" % (s_, k), 0.055, 0.11, (x, y, TREAD_Z - 0.04), M["steel2"], root, rot=(PI / 2, 0, 0), segs=10)
            cyl("cl_whub%d%d" % (s_, k), 0.025, 0.125, (x, y, TREAD_Z - 0.04), M["chrome"], root, rot=(PI / 2, 0, 0), segs=6)
        for k in range(TREAD_N):
            pe = empty("cl_pe%d%d" % (s_, k), (0, y, 0), root)
            box("cl_pad%d%d" % (s_, k), (0.042, 0.13, 0.022), (0, 0, 0), M["tread"], pe)
            box("cl_grous%d%d" % (s_, k), (0.012, 0.13, 0.03), (0, 0, -0.012), M["steel"], pe)
            pads.append(pe)
        box("cl_skirt%d" % s_, (0.56, 0.035, 0.07), (0, s_ * 0.27, 0.29), M["armor"], root)
        bolts("cl_skb%d" % s_, (0, s_ * 0.29, 0.29), "y", 0.03, root, 4)
    box("cl_chassis", (0.5, 0.34, 0.1), (0, 0, 0.31), M["steel2"], root)
    box("cl_hazard", (0.06, 0.34, 0.05), (0.26, 0, 0.32), M["hazard"], root)
    for s_ in (1, -1):
        sphere("cl_light%d" % s_, 0.025, (0.27, s_ * 0.1, 0.33), M["glow_yellow"], root)
    cyl("cl_ring", 0.22, 0.05, (0, 0, 0.38), M["darkmetal"], root, segs=16)

    def pose(anim, t):
        shift = (t if anim == "walk" else 0.0) * TREAD_P / TREAD_N
        for i, pe in enumerate(pads):
            k = i % TREAD_N
            x, z, pitch = _tread_path(k * TREAD_P / TREAD_N + shift)
            pe.location.x, pe.location.z = x, z
            pe.rotation_euler.y = pitch
    return root, pose


def canbot_upper(root):
    """The drum: cameras, antennas, exhaust, the player's cyan core, and a turret ring on top."""
    cyl("cb_drum", 0.26, 0.62, (0, 0, 0.72), M["darkmetal"], root, segs=20)
    ring("cb_band", 0.265, 0.16, (0, 0, 0.72), M["armor"], root, segs=20)
    ring("cb_stripe", 0.266, 0.035, (0, 0, 0.55), M["hazard"], root, segs=20)
    for z in (0.46, 0.98):
        ring("cb_lip%.2f" % z, 0.268, 0.03, (0, 0, z), M["steel2"], root, segs=20)
        for k in range(14):
            a = k * math.tau / 14
            sphere("cb_rivet%.2f_%d" % (z, k), 0.012, (math.cos(a) * 0.27, math.sin(a) * 0.27, z + 0.03), M["chrome"], root, segs=4, rings=3)
    cyl("cb_lid", 0.27, 0.04, (0, 0, 1.04), M["steel2"], root, segs=20)
    cyl("cb_turret", 0.15, 0.07, (0, 0, 1.09), M["darkmetal"], root, segs=14)
    ring("cb_turretring", 0.155, 0.025, (0, 0, 1.09), M["chrome"], root, segs=14)
    for s_ in (1, -1):              # twin cameras on the front of the drum
        box("cb_cam%d" % s_, (0.07, 0.07, 0.06), (0.27, s_ * 0.09, 0.86), M["steel"], root)
        cyl("cb_lens%d" % s_, 0.024, 0.03, (0.31, s_ * 0.09, 0.86), M["glow_red"], root, rot=(0, PI / 2, 0), segs=8)
        ring("cb_lensr%d" % s_, 0.03, 0.02, (0.31, s_ * 0.09, 0.86), M["chrome"], root, rot=(0, PI / 2, 0), segs=8)
    bone("cb_stalk", (0.04, -0.15, 1.06), (0.07, -0.17, 1.3), 0.012, M["chrome"], root)      # periscope camera
    box("cb_peri", (0.08, 0.06, 0.05), (0.09, -0.17, 1.32), M["darkmetal"], root)
    sphere("cb_perilens", 0.02, (0.135, -0.17, 1.32), M["glow_cyan"], root)
    bone("cb_ant1", (-0.12, 0.14, 1.05), (-0.18, 0.17, 1.78), 0.008, M["chrome"], root)
    sphere("cb_ant1t", 0.022, (-0.18, 0.17, 1.78), M["glow_red"], root)
    bone("cb_ant2", (-0.16, 0.08, 1.05), (-0.2, 0.1, 1.42), 0.006, M["chrome"], root)
    for s_ in (1, -1):              # exhaust stacks
        bone("cb_ex%d" % s_, (-0.25, s_ * 0.1, 0.62), (-0.3, s_ * 0.1, 1.02), 0.028, M["chrome"], root)
        sphere("cb_ext%d" % s_, 0.02, (-0.3, s_ * 0.1, 1.03), M["glow_orange"], root)
    sphere("cb_core", 0.065, (-0.27, 0, 0.74), M["glow_cyan"], root)
    ring("cb_coreg", 0.07, 0.04, (-0.27, 0, 0.74), M["chrome"], root, rot=(0, PI / 2, 0))
    for k in range(3):
        box("cb_vent%d" % k, (0.02, 0.16, 0.012), (-0.262, 0, 0.88 + k * 0.03), M["black"], root)


def mount_turret(info, root):
    """Turret yoke rising from the ring on top of the drum to cradle the gun under its grip."""
    gx, gy, gz = info["grip"]
    top = max(1.12, gz + 0.06)
    bone("cb_yoke", (min(gx, 0.12), gy, 1.1), (gx, gy, top), 0.028, M["steel2"], root)
    box("cb_cradle", (0.12, 0.07, 0.03), (gx + 0.03, gy, top), M["darkmetal"], root)
    wire("cb_feed", (-0.05, 0.05, 1.1), (gx, gy + 0.04, top), 0.04, 0.014, M["rubber"], root, 5)


# ---------------------------------------------------------------- Super Mutant
def _blisters(name, center, radii, n, parent, rmin=0.018, rmax=0.042):
    cx, cy, cz = center
    rx, ry, rz = radii
    for k in range(n):
        a = RNG.uniform(0, math.tau)
        b = RNG.uniform(-1.1, 1.1)
        p = (cx + math.cos(a) * math.cos(b) * rx, cy + math.sin(a) * math.cos(b) * ry, cz + math.sin(b) * rz)
        sphere("%s%d" % (name, k), RNG.uniform(rmin, rmax), p, M["blister"], parent, (1, 1, 0.8), 8, 6, True)


def build_mutant_legs():
    root = empty("ml_root")
    sphere("ml_hips", 0.17, (0, 0, 0.8), M["pinkmelt"], root, (0.9, 1.3, 0.75), 12, 8, True)
    box("ml_loin", (0.2, 0.3, 0.14), (0.02, 0, 0.74), M["zcloth"], root, (0, 0.1, 0))
    box("ml_belt", (0.24, 0.38, 0.05), (0, 0, 0.86), M["armor"], root)
    sphere("ml_buckle", 0.045, (0.13, 0, 0.86), M["glow_cyan"], root)
    _blisters("ml_hb", (0, 0, 0.8), (0.14, 0.2, 0.1), 6, root)
    for k in range(4):
        spike("ml_drip%d" % k, (RNG.uniform(-0.1, 0.1), RNG.uniform(-0.15, 0.15), 0.72), (RNG.uniform(-0.1, 0.1),
              RNG.uniform(-0.15, 0.15), 0.6 - RNG.uniform(0, 0.08)), 0.02, M["meltdrip"], root)
    J = {}
    for side, y in (("L", 0.14), ("R", -0.14)):
        hip = empty("mhip" + side, (0, y, 0.76), root)
        bone("mthigh" + side, (0, 0, 0), (0, 0, -0.34), 0.075, M["pinkmelt"], hip, r2=0.06)
        _blisters("mtb" + side, (0, 0, -0.17), (0.07, 0.07, 0.14), 4, hip)
        knee = empty("mknee" + side, (0, 0, -0.36), hip)
        sphere("mkneeb" + side, 0.065, (0, 0, 0), M["pinkmelt2"], knee)
        bone("mshin" + side, (0, 0, 0), (0, 0, -0.32), 0.058, M["pinkmelt"], knee, r2=0.045)
        _blisters("msb" + side, (0, 0, -0.15), (0.05, 0.05, 0.12), 3, knee, 0.015, 0.03)
        spike("mshdrip" + side, (0.03, 0, -0.1), (0.05, 0, -0.22), 0.018, M["meltdrip"], knee)
        ankle = empty("mankle" + side, (0, 0, -0.33), knee)
        sphere("mfoot" + side, 0.08, (0.04, 0, -0.03), M["pinkmelt2"], ankle, (1.4, 0.9, 0.6), 10, 6, True)
        for k, yy in enumerate((-0.04, 0, 0.04)):
            spike("mclaw%s%d" % (side, k), (0.13, yy, -0.04), (0.2, yy * 1.3, -0.06), 0.016, M["tooth"], ankle)
        J[side] = (hip, knee, ankle)

    def pose(anim, t):
        for side, off in (("L", 0.0), ("R", 0.5)):
            hip, knee, ankle = J[side]
            if anim == "idle":
                hip.rotation_euler.y = knee.rotation_euler.y = ankle.rotation_euler.y = 0
                continue
            ph = 2 * PI * (t + off)
            swing = math.sin(ph) * 0.5
            bend = 0.1 + 0.75 * max(0.0, math.cos(ph))
            hip.rotation_euler.y = -swing
            knee.rotation_euler.y = bend
            ankle.rotation_euler.y = (swing - bend) * 0.8
    return root, pose


def mutant_upper(root):
    """Hunched, melting, blistered bulk in a red-and-cyan cyber harness (so it reads as a player, not the pink enemy)."""
    sphere("mu_chest", 0.22, (0.02, 0, 1.13), M["pinkmelt"], root, (0.95, 1.25, 1.05), 14, 10, True)
    sphere("mu_belly", 0.16, (0.08, 0, 0.98), M["pinkmelt2"], root, (1, 1.2, 0.9), 12, 8, True)
    sphere("mu_hump", 0.15, (-0.13, 0.03, 1.3), M["pinkmelt"], root, (1, 1.1, 0.9), 12, 8, True)
    _blisters("mu_bl", (0.02, 0, 1.13), (0.21, 0.27, 0.22), 18, root)
    for k in range(6):
        x, y = RNG.uniform(-0.1, 0.15), RNG.uniform(-0.2, 0.2)
        spike("mu_drip%d" % k, (x, y, 0.95), (x + 0.02, y, 0.84 - RNG.uniform(0, 0.08)), 0.025, M["meltdrip"], root)
    for s_ in (1, -1):
        sphere("mu_shoulder%d" % s_, 0.1, (0, s_ * 0.25, 1.3), M["pinkmelt"], root, (1, 1, 0.85), 10, 8, True)
    sphere("mu_head", 0.11, (0.12, 0.02, 1.42), M["pinkmelt"], root, (1, 0.95, 0.85), 12, 8, True)
    sphere("mu_brow", 0.07, (0.15, -0.03, 1.48), M["pinkmelt2"], root, (1, 1.2, 0.6), 10, 6, True)
    sphere("mu_eyeL", 0.03, (0.21, 0.05, 1.44), M["glow_red"], root)
    sphere("mu_eyeR", 0.022, (0.215, -0.04, 1.43), M["glow_red"], root)
    box("mu_mouth", (0.05, 0.12, 0.03), (0.2, 0.01, 1.37), M["black"], root)
    for k in range(5):
        box("mu_tooth%d" % k, (0.012, 0.015, 0.025), (0.22, -0.04 + k * 0.022, 1.385), M["tooth"], root)
    _blisters("mu_hb", (0.12, 0.02, 1.42), (0.1, 0.1, 0.09), 5, root, 0.012, 0.025)
    # harness: armour straps + a cyan core on the back, wired into the flesh
    for s_ in (1, -1):
        box("mu_strap%d" % s_, (0.04, 0.05, 0.42), (0.13, s_ * 0.1, 1.12), M["armor"], root, (s_ * 0.4, 0.15, 0))
    box("mu_pack", (0.1, 0.2, 0.18), (-0.25, 0, 1.15), M["darkmetal"], root)
    sphere("mu_core", 0.06, (-0.31, 0, 1.15), M["glow_cyan"], root)
    ring("mu_coreg", 0.065, 0.04, (-0.31, 0, 1.15), M["chrome"], root, rot=(0, PI / 2, 0))
    for s_ in (1, -1):
        wire("mu_tube%d" % s_, (-0.22, s_ * 0.08, 1.22), (-0.1, s_ * 0.18, 1.28), 0.0, 0.014, M["wire_red" if s_ > 0 else "rubber"],
             root, 4, bulge=(0, 0, 0.04))


def flesh_arm(side, sh, hand, sgn, root):
    sh, hand = Vector(sh), Vector(hand)
    el = (sh + hand) / 2 + Vector((-0.05, 0.07 * sgn, -0.12))
    bone("mua" + side, sh, el, 0.055, M["pinkmelt"], root, r2=0.045)
    sphere("mue" + side, 0.05, el, M["pinkmelt2"], root)
    bone("muf" + side, el, hand, 0.045, M["pinkmelt"], root, r2=0.038)
    mid = (sh + el) / 2
    for k in range(2):
        sphere("mub%s%d" % (side, k), 0.022 - k * 0.006, mid + Vector((0.02 * k, 0.03 * sgn, 0.03 - 0.03 * k)), M["blister"], root)
    sphere("muh" + side, 0.055, hand, M["pinkmelt2"], root, (1.2, 1, 0.9), 8, 6, True)
    for k in (-1, 1):
        spike("mucl%s%d" % (side, k), hand + Vector((0.03, k * 0.025, 0)), hand + Vector((0.08, k * 0.03, -0.03)), 0.012, M["tooth"], root)


def char_torso_builder(char, arch):
    def build():
        root = empty("ct_root")
        if char == "canbot":
            canbot_upper(root)
            info = GUNS[arch](root, True)
            mount_turret(info, root)
        else:
            mutant_upper(root)
            info = GUNS[arch](root, True)
            flesh_arm("R", (0, -0.25, 1.3), info["grip"], -1, root)
            flesh_arm("L", (0, 0.25, 1.3), info["fore"], 1, root)
        EXTRA_META["muzzle"] = list(info["muzzle"])
        return root, lambda anim, t: None
    return build


ASSETS["canbot_legs"] = (build_canbot_legs, 8, {"walk": 8, "idle": 1}, (128, 128), 0.6)
ASSETS["mutant_legs"] = (build_mutant_legs, 8, {"walk": 8, "idle": 1}, (128, 128), 0.6)
for _arch in list(GUNS):
    ASSETS["cbtorso_" + _arch] = (char_torso_builder("canbot", _arch), 16, {"idle": 1}, (128, 128), 0.6)
    ASSETS["mttorso_" + _arch] = (char_torso_builder("mutant", _arch), 16, {"idle": 1}, (128, 128), 0.6)

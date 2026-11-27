# Module sprites (gun arm, bile leech, retaliation core, skull familiar, decoy, mine spine, aura emitter, bone battery,
# autoloader, jump jets, tether beam, loot magnet). exec'd by build_assets.py after support_items.py.
# Centred on the origin (tz=0): the game draws them hovering at their own height. Single direction, 8-frame idle loop.

mat("bilegreen", (0.35, 0.55, 0.05), 0.0, 0.15, (0.4, 0.7, 0.05), 0.6)
mat("fleshpink", (0.6, 0.22, 0.25), 0.0, 0.3)
mat("soulfire", (0.3, 0.8, 1.0), 0.0, 0.2, (0.3, 0.8, 1.0), 2.0)
mat("holo", (0.2, 0.7, 0.9), 0.0, 0.1, (0.25, 0.8, 1.0), 1.5)
mat("emberglow", (1.0, 0.45, 0.1), 0.0, 0.2, (1.0, 0.45, 0.1), 1.8)
mat("tealglow", (0.2, 1.0, 0.85), 0.0, 0.2, (0.2, 1.0, 0.85), 1.8)
mat("magred", (0.6, 0.05, 0.05), 0.3, 0.35)


def _spin_root(name):
    root = empty(name + "_root")
    spin = empty(name + "_spin", (0, 0, 0), root)
    return root, spin


def _spin_pose(spin, turns=1.0, bob=None):
    def pose(anim, t):
        spin.rotation_euler.z = math.tau * t * turns
        if bob is not None:
            bob.location.z = math.sin(t * math.tau) * 0.02
    return pose


def build_sup_gunarm():
    root, spin = _spin_root("ga")
    cyl("ga_mount", 0.09, 0.08, (-0.18, 0, -0.12), M["darkmetal"], spin, segs=10)
    bolts("ga_b", (-0.18, 0, -0.08), "z", 0.07, spin, 4)
    pts = [(-0.18, 0, -0.06), (-0.12, 0, 0.12), (0.06, 0, 0.2), (0.22, 0, 0.1)]
    for k in range(3):
        bone("ga_seg%d" % k, pts[k], pts[k + 1], 0.035, M["steel2"], spin)
        sphere("ga_j%d" % k, 0.05, pts[k + 1], M["hazard"] if k == 1 else M["chrome"], spin)
    for k in range(2):
        wire("ga_hose%d" % k, (pts[0][0], 0.04 - k * 0.08, pts[0][2]), (pts[2][0], 0.03 - k * 0.06, pts[2][2]), 0.05, 0.012,
             M["rubber" if k else "wire_red"], spin, 6)
    box("ga_clamp", (0.12, 0.08, 0.06), (0.28, 0, 0.08), M["darkmetal"], spin)
    for s_ in (-1, 1):
        box("ga_jaw%d" % s_, (0.08, 0.015, 0.05), (0.34, s_ * 0.035, 0.08), M["chrome"], spin)
    sphere("ga_eye", 0.018, (0.3, 0.045, 0.12), M["glow_red"], spin)
    return root, _spin_pose(spin)


def build_sup_leech():
    root, spin = _spin_root("lc")
    sphere("lc_sac", 0.17, (0, 0, 0), M["fleshpink"], spin, (1.1, 1, 0.9), 14, 10, True)
    for k in range(6):
        a = k * math.tau / 6
        sphere("lc_vein%d" % k, 0.06, (math.cos(a) * 0.14, math.sin(a) * 0.13, 0.04 * (k % 2)), M["vein"], spin, (1.6, 0.5, 0.5), 8, 6, True,
               rot=(0, 0, a))
    sphere("lc_bile", 0.08, (0, 0, 0.14), M["bilegreen"], spin, (1, 1, 0.7), 10, 8, True)
    ring("lc_clamp", 0.15, 0.04, (0, 0, -0.1), M["darkmetal"], spin, segs=12)
    for k in range(3):
        a = k * math.tau / 3 + 0.3
        end = (math.cos(a) * 0.3, math.sin(a) * 0.3, -0.18)
        wire("lc_tongue%d" % k, (math.cos(a) * 0.1, math.sin(a) * 0.1, -0.06), end, 0.0, 0.018, M["flesh"], spin, 6,
             bulge=(0, 0, -0.05), wobble=0.02)
        for j in range(4):
            b = j * math.tau / 4
            spike("lc_tooth%d%d" % (k, j), end, (end[0] + math.cos(b) * 0.04, end[1] + math.sin(b) * 0.04, end[2] - 0.04), 0.008,
                  M["tooth"], spin)
    return root, _spin_pose(spin)


def build_sup_core():
    root, spin = _spin_root("cr")
    sphere("cr_orb", 0.11, (0, 0, 0), M["emberglow"], spin, segs=12, rings=8, smooth=True)
    for k in range(3):
        ring("cr_cage%d" % k, 0.17, 0.03, (0, 0, 0), M["darkmetal"], spin, rot=(PI / 2, 0, k * PI / 3), segs=14)
    for s_ in (-1, 1):
        cyl("cr_cap%d" % s_, 0.08, 0.05, (0, 0, s_ * 0.17), M["steel2"], spin, segs=10)
        spike("cr_spike%d" % s_, (0, 0, s_ * 0.19), (0, 0, s_ * 0.3), 0.025, M["chrome"], spin)
    for k in range(4):
        a = k * math.tau / 4
        box("cr_fin%d" % k, (0.1, 0.015, 0.08), (math.cos(a) * 0.2, math.sin(a) * 0.2, 0), M["hazard"], spin, (0, 0, a))
    return root, _spin_pose(spin, 0.5)


def build_sup_skull():
    root = empty("sk_root")
    body = empty("sk_body", (0, 0, 0), root)
    sphere("sk_cran", 0.15, (-0.02, 0, 0.04), M["bone"], body, (1.15, 0.95, 1.0), 14, 10, True)
    box("sk_jaw", (0.12, 0.13, 0.05), (0.08, 0, -0.08), M["bone"], body)
    for s_ in (-1, 1):
        sphere("sk_sock%d" % s_, 0.04, (0.11, s_ * 0.05, 0.03), M["black"], body)
        sphere("sk_eye%d" % s_, 0.022, (0.13, s_ * 0.05, 0.03), M["soulfire"], body)
    for k in range(5):
        box("sk_tooth%d" % k, (0.015, 0.018, 0.03), (0.14, -0.04 + k * 0.02, -0.04), M["tooth"], body)
    flames = []
    for k in range(7):
        a = k * math.tau / 7
        f = empty("sk_fl%d" % k, (-0.08 + math.cos(a) * 0.06, math.sin(a) * 0.08, 0.12), body)
        spike("sk_flame%d" % k, (0, 0, 0), (-0.12, 0, 0.14), 0.04, M["soulfire"], f)
        flames.append(f)
    bolts("sk_b", (-0.02, 0, 0.04), "x", 0.13, body, 3)

    def pose(anim, t):
        body.location.z = math.sin(t * math.tau) * 0.02
        for k, f in enumerate(flames):
            f.scale = (1, 1, 0.7 + 0.4 * (0.5 + 0.5 * math.sin(t * math.tau * 2 + k)))
    return root, pose


def build_sup_decoy():
    root, spin = _spin_root("dc")
    cyl("dc_base", 0.13, 0.06, (0, 0, -0.1), M["darkmetal"], spin, segs=12)
    ring("dc_ring", 0.135, 0.03, (0, 0, -0.07), M["holo"], spin, segs=12)
    cyl("dc_lens", 0.06, 0.05, (0, 0, -0.04), M["glass"], spin, segs=10)
    cyl("dc_cone", 0.02, 0.32, (0, 0, 0.12), M["holo"], spin, r2=0.11, segs=10, caps=False)
    sphere("dc_head", 0.04, (0, 0, 0.2), M["holo"], spin)
    box("dc_torso", (0.05, 0.08, 0.1), (0, 0, 0.1), M["holo"], spin)
    for s_ in (-1, 1):
        box("dc_ant%d" % s_, (0.015, 0.015, 0.08), (0.07, s_ * 0.09, -0.06), M["chrome"], spin)
    return root, _spin_pose(spin)


def build_sup_mines():
    root, spin = _spin_root("mn")
    box("mn_spine", (0.32, 0.08, 0.06), (0, 0, 0.0), M["darkmetal"], spin)
    for k in range(4):
        x = -0.12 + k * 0.08
        cyl("mn_mine%d" % k, 0.045, 0.03, (x, 0, 0.06), M["steel2"], spin, segs=10)
        sphere("mn_led%d" % k, 0.012, (x, 0, 0.08), M["glow_red"], spin)
        for s_ in (-1, 1):
            spike("mn_rib%d%d" % (k, s_), (x, s_ * 0.04, 0), (x, s_ * 0.12, -0.06), 0.012, M["bone"], spin)
    box("mn_hazard", (0.32, 0.085, 0.015), (0, 0, -0.035), M["hazard"], spin)
    return root, _spin_pose(spin)


def build_sup_aura():
    root, spin = _spin_root("au")
    cyl("au_body", 0.08, 0.14, (0, 0, 0), M["steel2"], spin, segs=10)
    for z in (-0.06, 0.0, 0.06):
        ring("au_coil%.2f" % z, 0.09, 0.025, (0, 0, z), M["copper"], spin, segs=12)
    ring("au_halo", 0.22, 0.03, (0, 0, -0.1), M["emberglow"], spin, segs=20)
    for k in range(4):
        a = k * math.tau / 4
        bone("au_arm%d" % k, (0, 0, -0.05), (math.cos(a) * 0.2, math.sin(a) * 0.2, -0.1), 0.012, M["darkmetal"], spin)
    sphere("au_top", 0.05, (0, 0, 0.1), M["emberglow"], spin)
    return root, _spin_pose(spin)


def build_sup_battery():
    root, spin = _spin_root("bb")
    cyl("bb_glass", 0.08, 0.26, (0, 0, 0), M["glass"], spin, segs=12)
    cyl("bb_fill", 0.06, 0.18, (0, 0, -0.03), M["glow_green_dim"], spin, segs=10)
    for s_ in (-1, 1):
        cyl("bb_cap%d" % s_, 0.09, 0.04, (0, 0, s_ * 0.14), M["darkmetal"], spin, segs=12)
    for k in range(3):
        a = k * math.tau / 3
        bone_prop("bb_rib%d" % k, (math.cos(a) * 0.1, math.sin(a) * 0.1, -0.12), (math.cos(a) * 0.1, math.sin(a) * 0.1, 0.12), spin, 0.016)
    sphere("bb_skull", 0.045, (0, 0, 0.2), M["bone"], spin, (1.1, 1, 1), 10, 8, True)
    bone("bb_term", (0, 0, 0.16), (0, 0, 0.18), 0.015, M["copper"], spin)
    return root, _spin_pose(spin, 0.5)


def build_sup_autoloader():
    root, spin = _spin_root("al")
    cyl("al_drum", 0.13, 0.1, (0, 0, 0), M["darkmetal"], spin, rot=(PI / 2, 0, 0), segs=14)
    ring("al_band", 0.135, 0.03, (0, 0, 0), M["hazard"], spin, rot=(PI / 2, 0, 0), segs=14)
    for k in range(8):
        a = k * math.tau / 8
        cyl("al_rnd%d" % k, 0.015, 0.06, (math.cos(a) * 0.08, 0.06, math.sin(a) * 0.08), M["brass"], spin, rot=(PI / 2, 0, 0), segs=6)
    for k in range(6):
        box("al_belt%d" % k, (0.03, 0.05, 0.025), (0.14 + k * 0.025, 0, -0.06 - k * 0.012), M["brass"], spin)
    box("al_motor", (0.08, 0.06, 0.08), (-0.12, 0, 0.0), M["steel2"], spin)
    sphere("al_led", 0.015, (-0.12, 0.035, 0.03), M["glow_green"], spin)
    return root, _spin_pose(spin)


def build_sup_jets():
    root, spin = _spin_root("jj")
    box("jj_harness", (0.06, 0.26, 0.12), (0, 0, 0.02), M["darkmetal"], spin)
    for s_ in (-1, 1):
        cyl("jj_pod%d" % s_, 0.06, 0.24, (0, s_ * 0.12, 0), M["steel2"], spin, segs=12)
        ring("jj_band%d" % s_, 0.063, 0.03, (0, s_ * 0.12, 0.05), M["hazard"], spin, segs=12)
        cyl("jj_noz%d" % s_, 0.05, 0.06, (0, s_ * 0.12, -0.14), M["darkmetal"], spin, r2=0.035, segs=12)
        cyl("jj_flame%d" % s_, 0.035, 0.1, (0, s_ * 0.12, -0.21), M["emberglow"], spin, r2=0.005, segs=8)
    return root, _spin_pose(spin)


def build_sup_tether():
    root, spin = _spin_root("tb")
    sphere("tb_core", 0.08, (0, 0, 0), M["tealglow"], spin, segs=10, rings=8, smooth=True)
    for k in range(3):
        a = k * math.tau / 3
        bone("tb_prong%d" % k, (math.cos(a) * 0.08, math.sin(a) * 0.08, 0), (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.06), 0.018,
             M["chrome"], spin)
        sphere("tb_tip%d" % k, 0.025, (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.06), M["tealglow"], spin)
    ring("tb_ring", 0.12, 0.03, (0, 0, -0.04), M["darkmetal"], spin, segs=14)
    cyl("tb_spool", 0.05, 0.08, (0, 0, -0.1), M["copper"], spin, segs=10)
    return root, _spin_pose(spin)


def build_sup_magnet():
    root, spin = _spin_root("lm")
    n = 9
    for k in range(n):
        a = PI * k / (n - 1)
        box("lm_arc%d" % k, (0.06, 0.06, 0.05), (math.cos(a) * 0.14, 0, math.sin(a) * 0.14 - 0.02), M["magred"], spin, (0, -a, 0))
    for s_ in (-1, 1):
        box("lm_pole%d" % s_, (0.065, 0.065, 0.08), (s_ * 0.14, 0, -0.08), M["chrome"], spin)
    sphere("lm_spark", 0.02, (0, 0, -0.1), M["glow_white"], spin)
    box("lm_hub", (0.06, 0.06, 0.04), (0, 0, 0.13), M["darkmetal"], spin)
    return root, _spin_pose(spin)


for _n, _b in (("gunarm", build_sup_gunarm), ("leech", build_sup_leech), ("core", build_sup_core), ("decoy", build_sup_decoy),
               ("mines", build_sup_mines), ("aura", build_sup_aura), ("battery", build_sup_battery),
               ("autoloader", build_sup_autoloader), ("jets", build_sup_jets), ("tether", build_sup_tether),
               ("magnet", build_sup_magnet)):
    ASSETS["sup_" + _n] = (_b, 1, {"idle": 8}, (72, 72), 0.0)
ASSETS["sup_skull"] = (build_sup_skull, 8, {"hover": 4}, (72, 72), 0.0)

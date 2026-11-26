# Environmental trap models - exec'd by build_assets.py after expansion.py (shares its helpers/materials).
# Every trap faces +x at dir 0; animated pieces are posed through the returned pose(anim, t) callback.

mat("brass", (0.55, 0.38, 0.12), 0.9, 0.35)
mat("gold_t", (0.85, 0.6, 0.15), 1.0, 0.25)
mat("lip", (0.42, 0.08, 0.1), 0.0, 0.35)
mat("gum", (0.6, 0.18, 0.22), 0.0, 0.3)
mat("maw_dark", (0.03, 0.0, 0.0), 0.0, 0.6)
mat("dirt", (0.09, 0.07, 0.05), 0.0, 0.95)
mat("bramble", (0.07, 0.05, 0.03), 0.0, 0.8)
mat("thorn_red", (0.35, 0.02, 0.02), 0.0, 0.4)
mat("chemglass", (0.5, 0.9, 0.1), 0.0, 0.1, (0.6, 1.0, 0.1), 3.0)
mat("radglass", (0.2, 1.0, 0.3), 0.0, 0.1, (0.3, 1.0, 0.35), 3.0)
mat("teslaglow", (0.5, 0.8, 1.0), 0.0, 0.2, (0.5, 0.8, 1.0), 6.0)


def _plate(r, size=0.9, material="darkmetal", holes=3):
    box("tp_plate", (size, size, 0.05), (0, 0, 0.025), M[material], r)
    for s in (-1, 1):
        box("tp_rx%d" % s, (size, 0.04, 0.07), (0, s * size / 2, 0.035), M["steel2"], r)
        box("tp_ry%d" % s, (0.04, size, 0.07), (s * size / 2, 0, 0.035), M["steel2"], r)
    step = size / holes
    for i in range(holes):
        for j in range(holes):
            cyl("tp_h%d%d" % (i, j), 0.055, 0.012, ((i - (holes - 1) / 2) * step, (j - (holes - 1) / 2) * step, 0.052), M["black"], r, segs=8)
    bolts("tp_b", (0, size / 2 - 0.03, 0.06), "x", size * 0.8, r, 4)


def build_trap_spikes(bone_kind=False):
    def build():
        r = tile_root()
        if bone_kind:
            box("tsb_slab", (0.9, 0.9, 0.05), (0, 0, 0.025), M["bone_dirty"], r)
            for k in range(7):
                bone_prop("tsb_bp%d" % k, (RNG.uniform(-0.42, 0.42), RNG.uniform(-0.42, 0.42), 0.06),
                          (RNG.uniform(-0.42, 0.42), RNG.uniform(-0.42, 0.42), 0.06), r, 0.02)
            for k in range(9):
                cyl("tsb_h%d" % k, 0.06, 0.012, ((k % 3 - 1) * 0.28, (k // 3 - 1) * 0.28, 0.052), M["maw_dark"], r, segs=7)
            pool("tsb_bl", (0.1, -0.1, 0.055), 0.35, r, M["blood"], 3)
        else:
            _plate(r)
            pool("ts_bl", (0.15, 0.1, 0.06), 0.25, r, M["blood"], 3)
        grp = empty("ts_spikes", (0, 0, 0.05), r)
        for k in range(9):
            x, y = (k % 3 - 1) * 0.28, (k // 3 - 1) * 0.28
            h = RNG.uniform(0.45, 0.6)
            tip = (x + RNG.uniform(-0.04, 0.04), y + RNG.uniform(-0.04, 0.04), h)
            if bone_kind:
                spike("tsb_s%d" % k, (x, y, 0), tip, 0.06, M["bone"], grp)
                ring("tsb_r%d" % k, 0.05, 0.03, (x, y, h * 0.35), M["bone_dirty"], grp, segs=7)
            else:
                spike("ts_s%d" % k, (x, y, 0), tip, 0.05, M["chrome"], grp)
                cyl("ts_c%d" % k, 0.05, 0.08, (x, y, 0.04), M["steel2"], grp, segs=7)
            if k % 2 == 0:
                drip("ts_d%d" % k, (tip[0], tip[1], h * 0.8), 0.15, 0.015, M["blood"], grp)

        def pose(anim, t):
            h = [0.02, 0.35, 0.8, 1.0][min(3, int(t * 4 + 0.01))]
            grp.scale = (1, 1, h)
        return r, pose
    return build


def build_trap_saw():
    r = tile_root()
    box("tsw_slot", (0.95, 0.12, 0.03), (0, 0, 0.015), M["black"], r)
    for s in (-1, 1):
        box("tsw_lip%d" % s, (0.95, 0.06, 0.05), (0, s * 0.09, 0.025), M["hazard"], r)
    hub = empty("tsw_hub", (0, 0, 0.28), r)
    cyl("tsw_disc", 0.34, 0.03, (0, 0, 0), M["chrome"], hub, rot=(PI / 2, 0, 0), segs=24)
    cyl("tsw_disc2", 0.22, 0.035, (0, 0, 0), M["steel2"], hub, rot=(PI / 2, 0, 0), segs=16)
    cyl("tsw_axle", 0.06, 0.09, (0, 0, 0), M["darkmetal"], hub, rot=(PI / 2, 0, 0), segs=8)
    for k in range(14):
        a = 2 * PI * k / 14
        p1 = (math.cos(a) * 0.32, 0, math.sin(a) * 0.32)
        p2 = (math.cos(a + 0.2) * 0.43, 0, math.sin(a + 0.2) * 0.43)
        spike("tsw_t%d" % k, p1, p2, 0.035, M["chrome"], hub)
    for k in range(4):
        a = 2 * PI * k / 4
        cyl("tsw_hole%d" % k, 0.04, 0.04, (math.cos(a) * 0.14, 0, math.sin(a) * 0.14), M["black"], hub, rot=(PI / 2, 0, 0), segs=8)
    pool("tsw_blood", (0.12, 0.0, 0.2), 0.18, hub, M["blood"], 3)
    for s in (-1, 1):
        box("tsw_guard%d" % s, (0.12, 0.04, 0.12), (s * 0.4, 0, 0.06), M["darkmetal"], r)

    def pose(anim, t):
        hub.rotation_euler.y = -2 * PI * t / 14
    return r, pose


def build_trap_vent():
    r = tile_root()
    box("tv_frame", (0.8, 0.8, 0.06), (0, 0, 0.03), M["steel2"], r)
    box("tv_pit", (0.66, 0.66, 0.02), (0, 0, 0.055), M["black"], r)
    for k in range(7):
        box("tv_slat%d" % k, (0.66, 0.035, 0.03), (0, -0.3 + k * 0.1, 0.075), M["darkmetal"], r)
    box("tv_bar", (0.035, 0.66, 0.035), (0, 0, 0.08), M["darkmetal"], r)
    bolts("tv_b", (0, 0.37, 0.065), "x", 0.6, r, 4)
    bolts("tv_b2", (0, -0.37, 0.065), "x", 0.6, r, 4)
    for s in (-1, 1):
        tube("tv_pipe%d" % s, [Vector((s * 0.42, -0.3, 0.05)), Vector((s * 0.5, 0.0, 0.08)), Vector((s * 0.46, 0.35, 0.04))], 0.035, M["rust"], r, segs=7)
    rnd_stain("tv_st", r, "oil", 0.8, 0.09, (0.12, 0.25))
    return r, None


def build_trap_hole():
    r = tile_root()
    ring("th_rim", 0.38, 0.08, (0, 0, 0.03), M["flesh"], r, segs=14, scale=(1, 1, 0.8))
    cyl("th_pit", 0.33, 0.02, (0, 0, 0.02), M["maw_dark"], r, segs=14)
    for k in range(9):
        a = 2 * PI * k / 9 + RNG.uniform(-0.2, 0.2)
        meat("th_m%d" % k, (math.cos(a) * 0.42, math.sin(a) * 0.42, 0.03), RNG.uniform(0.07, 0.12), r, M[RNG.choice(["flesh", "muscle", "guts"])], 2)
    for k in range(5):
        a = RNG.uniform(0, 2 * PI)
        spike("th_t%d" % k, (math.cos(a) * 0.34, math.sin(a) * 0.34, 0.05), (math.cos(a) * 0.24, math.sin(a) * 0.24, 0.14), 0.025, M["tooth"], r)
    for k in range(3):
        a = RNG.uniform(0, 2 * PI)
        drip("th_d%d" % k, (math.cos(a) * 0.36, math.sin(a) * 0.36, 0.06), 0.1, 0.02, M["slime"], r)
    pool("th_slime", (0, 0, 0.004), 0.55, r, M["blood"], 4)
    return r, None


def build_trap_reactor(glass="chemglass", accent="chemyellow"):
    def build():
        r = tile_root()
        cyl("tr_base", 0.42, 0.1, (0, 0, 0.05), M["darkmetal"], r, segs=12)
        box("tr_hz", (0.86, 0.86, 0.03), (0, 0, 0.015), M["hazard"], r)
        cyl("tr_tank", 0.32, 0.8, (0, 0, 0.5), M["steel2"], r, segs=14)
        cyl("tr_cap", 0.34, 0.08, (0, 0, 0.93), M["darkmetal"], r, segs=14, r2=0.22)
        cyl("tr_win", 0.33, 0.45, (0, 0, 0.5), M[glass], r, segs=14, scale=(1, 1, 1))
        for z in (0.25, 0.75):
            ring("tr_band%d" % int(z * 100), 0.34, 0.06, (0, 0, z), M["darkmetal"], r, segs=14)
        for k in range(6):
            a = 2 * PI * k / 6
            box("tr_rib%d" % k, (0.04, 0.04, 0.5), (math.cos(a) * 0.335, math.sin(a) * 0.335, 0.5), M["darkmetal"], r, (0, 0, a))
        cyl("tr_valve", 0.06, 0.12, (0, 0, 1.02), M[accent], r, segs=8)
        ring("tr_wheel", 0.1, 0.02, (0, 0, 1.09), M["glow_red"], r, segs=10)
        for s in (-1, 1):
            tube("tr_pipe%d" % s, [Vector((0.2 * s, 0.2, 0.9)), Vector((0.45 * s, 0.35, 0.7)), Vector((0.45 * s, 0.4, 0.05))], 0.04, M["rust"], r, segs=7)
        box("tr_sign", (0.02, 0.2, 0.16), (0.33, 0, 0.82), M["hazard"], r)
        sphere("tr_lamp", 0.04, (0.3, 0.15, 0.95), M["glow_red"], r)
        pool("tr_leak", (0.25, -0.2, 0.005), 0.35, r, M[accent], 3)
        return r, None
    return build


def build_trap_turret():
    r = tile_root()
    cyl("tt_ring", 0.4, 0.05, (0, 0, 0.025), M["hazard"], r, segs=16)
    cyl("tt_hole", 0.33, 0.02, (0, 0, 0.05), M["black"], r, segs=16)
    doors = []
    for s in (-1, 1):
        d = empty("tt_door%d" % s, (0, 0, 0.055), r)
        box("tt_dp%d" % s, (0.33, 0.66, 0.02), (s * 0.165, 0, 0), M["darkmetal"], d)
        box("tt_ds%d" % s, (0.05, 0.6, 0.025), (s * 0.03, 0, 0.005), M["hazard"], d)
        doors.append((d, s))
    riser = empty("tt_riser", (0, 0, 0.05), r)
    cyl("tt_col", 0.12, 0.35, (0, 0, 0.17), M["mech"], riser, segs=10)
    head = empty("tt_head", (0, 0, 0.42), riser)
    box("tt_body", (0.34, 0.3, 0.18), (0, 0, 0), M["darkmetal"], head)
    box("tt_arm", (0.28, 0.32, 0.05), (0.0, 0, 0.11), M["mech"], head)
    for s in (1, -1):
        bone("tt_bar%d" % s, (0.15, s * 0.07, 0.0), (0.5, s * 0.07, 0.0), 0.025, M["chrome"], head)
        ring("tt_mz%d" % s, 0.032, 0.04, (0.5, s * 0.07, 0.0), M["darkmetal"], head, rot=(0, PI / 2, 0))
    sphere("tt_eye", 0.04, (0.18, 0, 0.08), M["glow_red"], head)
    box("tt_ammo", (0.14, 0.1, 0.12), (-0.06, 0.2, -0.02), M["crate"], head)

    def pose(anim, t):
        k = min(1.0, t / 0.75)
        riser.scale = (1, 1, max(0.02, k))
        for d, s in doors:
            d.location.x = s * 0.3 * k
        head.rotation_euler.y = 0.0
    return r, pose


def build_trap_tesla():
    r = tile_root()
    cyl("tc_base", 0.36, 0.12, (0, 0, 0.06), M["darkmetal"], r, segs=10)
    box("tc_hz", (0.8, 0.8, 0.03), (0, 0, 0.015), M["hazard"], r)
    cyl("tc_col", 0.1, 0.8, (0, 0, 0.5), M["black"], r, segs=10)
    for k in range(9):
        ring("tc_coil%d" % k, 0.16 - k * 0.006, 0.035, (0, 0, 0.2 + k * 0.075), M["copper"], r, segs=12)
    ring("tc_torus", 0.2, 0.07, (0, 0, 0.98), M["chrome"], r, segs=14)
    sphere("tc_orb", 0.13, (0, 0, 1.05), M["teslaglow"], r, segs=12, rings=8, smooth=True)
    for s in (-1, 1):
        wire("tc_cab%d" % s, (s * 0.2, 0.1, 0.1), (s * 0.5, 0.4, 0.01), 0.02, 0.025, M["wire_blue"], r, 5)
    box("tc_box", (0.18, 0.12, 0.14), (0.28, -0.2, 0.13), M["mech"], r)
    sphere("tc_led", 0.02, (0.37, -0.2, 0.17), M["glow_cyan"], r)
    return r, None


def build_trap_maw():
    r = tile_root()
    pool("tm_gore", (0, 0, 0.003), 0.7, r, M["blood"], 4)
    cyl("tm_throat", 0.3, 0.02, (0, 0, 0.012), M["maw_dark"], r, segs=14, scale=(0.6, 1, 1))
    ring("tm_lips", 0.34, 0.06, (0, 0, 0.02), M["lip"], r, segs=14, scale=(0.75, 1, 0.8))
    jaws = []
    for s in (-1, 1):
        j = empty("tm_jaw%d" % s, (0, 0, 0.03), r)
        box("tm_gum%d" % s, (0.6, 0.3, 0.05), (0, s * 0.16, 0), M["gum"], j)
        for k in range(6):
            x = -0.25 + k * 0.1
            spike("tm_tooth%d_%d" % (s, k), (x, s * 0.03, 0.02), (x + RNG.uniform(-0.02, 0.02), s * 0.02, 0.15 + RNG.uniform(0, 0.05)), 0.03, M["tooth"], j)
        for k in range(3):
            drip("tm_dr%d_%d" % (s, k), (-0.2 + k * 0.2, s * 0.25, 0.0), 0.06, 0.015, M["slime"], j)
        jaws.append((j, s))

    def pose(anim, t):
        a = [0.0, 0.55, 1.1, PI / 2 - 0.08][min(3, int(t * 4 + 0.01))]
        for j, s in jaws:
            j.rotation_euler.x = s * a
    return r, pose


def build_trap_hands():
    r = tile_root()
    pool("thd_dirt", (0, 0, 0.003), 0.8, r, M["dirt"], 5)
    rnd_debris("thd_db", r, ["dirt", "bone_dirty"], 6, 0.0, (0.04, 0.08))
    grp = empty("thd_grp", (0, 0, 0.0), r)
    for k in range(5):
        a = 2 * PI * k / 5 + RNG.uniform(-0.3, 0.3)
        x, y = math.cos(a) * 0.24, math.sin(a) * 0.24
        mt = M["bone"] if k % 2 else M["zskin"]
        lean = (math.cos(a) * 0.1, math.sin(a) * 0.1)
        top = (x + lean[0], y + lean[1], RNG.uniform(0.45, 0.6))
        bone("thd_arm%d" % k, (x, y, -0.05), top, 0.06, mt, grp)
        ring("thd_cuff%d" % k, 0.07, 0.05, (x, y, 0.06), M["zcloth"], grp, segs=8)
        sphere("thd_palm%d" % k, 0.09, top, mt, grp, (1, 0.7, 1.2))
        for f in range(5):
            fa = a + (f - 2) * 0.45
            p2 = (top[0] + math.cos(fa) * 0.1 - lean[0] * 0.5, top[1] + math.sin(fa) * 0.1 - lean[1] * 0.5, top[2] + 0.18)
            p3 = (p2[0] - lean[0] * 0.6, p2[1] - lean[1] * 0.6, p2[2] + 0.05)
            bone("thd_f%d_%d" % (k, f), top, p2, 0.022, mt, grp)
            spike("thd_n%d_%d" % (k, f), p2, p3, 0.018, M["bone_dirty"], grp)
        if k % 2 == 0:
            drip("thd_bl%d" % k, top, 0.12, 0.015, M["blood"], grp)

    def pose(anim, t):
        k = [0.08, 0.4, 0.8, 1.0][min(3, int(t * 4 + 0.01))]
        grp.scale = (1, 1, k)
    return r, pose


def build_trap_thorns():
    r = tile_root()
    pool("tth_bl", (0, 0, 0.003), 0.6, r, M["blood"], 3)
    for k in range(16):
        a = RNG.uniform(0, 2 * PI)
        d = RNG.uniform(0.0, 0.38)
        base = Vector((math.cos(a) * d, math.sin(a) * d, 0.0))
        pts = [base]
        for i in range(5):
            pts.append(pts[-1] + Vector((RNG.uniform(-0.17, 0.17), RNG.uniform(-0.17, 0.17), RNG.uniform(0.06, 0.15))))
        tube("tth_v%d" % k, pts, 0.045, M["bramble"], r, segs=5, r_end=0.008)
        for i, p in enumerate(pts[1:]):
            for _ in range(2):
                q = (p.x + RNG.uniform(-0.09, 0.09), p.y + RNG.uniform(-0.09, 0.09), p.z + RNG.uniform(-0.02, 0.06))
                spike("tth_t%d_%d_%d" % (k, i, _), tuple(p), q, 0.02, M["thorn_red" if RNG.random() < 0.6 else "bone"], r)
    for k in range(3):
        drip("tth_d%d" % k, (RNG.uniform(-0.2, 0.2), RNG.uniform(-0.2, 0.2), 0.35), 0.15, 0.015, M["blood"], r)
    skull_prop("tth_sk", (0.18, -0.15, 0.05), r, 0.5, RNG.uniform(0, 6), bloody=True)
    return r, None


def build_trap_pendulum():
    r = tile_root()
    for s in (-1, 1):
        box("tpd_post%d" % s, (0.14, 0.14, 1.75), (0, s * 0.55, 0.875), M["iron"] if "iron" in M else M["darkmetal"], r)
        box("tpd_foot%d" % s, (0.3, 0.3, 0.08), (0, s * 0.55, 0.04), M["stone"], r)
        bolts("tpd_b%d" % s, (0.075, s * 0.55, 1.5), "z", 0.2, r, 3)
    box("tpd_beam", (0.16, 1.3, 0.16), (0, 0, 1.75), M["darkmetal"], r)
    box("tpd_trk", (0.95, 0.12, 0.02), (0, 0, 0.01), M["black"], r)
    arm = empty("tpd_arm", (0, 0, 1.68), r)
    bone("tpd_rod", (0, 0, 0), (0, 0, -1.25), 0.03, M["chrome"], arm)
    ring("tpd_hinge", 0.06, 0.18, (0, 0, 0), M["darkmetal"], arm, rot=(PI / 2, 0, 0))
    blade = empty("tpd_blade", (0, 0, -1.4), arm)
    cyl("tpd_bl", 0.42, 0.03, (0, 0, 0), M["chrome"], blade, rot=(PI / 2, 0, 0), segs=20, scale=(1, 1, 1))
    box("tpd_cut", (0.9, 0.06, 0.5), (0, 0, 0.27), M["darkmetal"], blade)
    for k in range(7):
        a = PI + 0.25 + k * (PI - 0.5) / 6
        p = (math.cos(a) * 0.42, 0, math.sin(a) * 0.42)
        drip("tpd_dr%d" % k, p, RNG.uniform(0.04, 0.12), 0.012, M["blood"], blade) if k % 2 else None
    pool("tpd_blood", (0.1, 0.0, -0.3), 0.2, blade, M["blood"], 3)

    def pose(anim, t):
        arm.rotation_euler.y = 1.0 * math.sin(2 * PI * t)
    return r, pose


TRAP_ASSETS = {
    "trap_spikes": (build_trap_spikes(False), 1, {"rise": 4}, (96, 96), 0.15),
    "trap_bonespikes": (build_trap_spikes(True), 1, {"rise": 4}, (96, 96), 0.15),
    "trap_saw": (build_trap_saw, 4, {"spin": 4}, (96, 96), 0.25),
    "trap_vent": (build_trap_vent, 1, {"idle": 1}, (80, 72), 0.0),
    "trap_hole": (build_trap_hole, 1, {"idle": 1}, (80, 72), 0.0),
    "trap_chemreactor": (build_trap_reactor("chemglass", "chemyellow"), 1, {"idle": 1}, (96, 128), 0.55),
    "trap_radreactor": (build_trap_reactor("radglass", "radglow"), 1, {"idle": 1}, (96, 128), 0.55),
    "trap_turret": (build_trap_turret, 16, {"rise": 4}, (96, 96), 0.25),
    "trap_tesla": (build_trap_tesla, 1, {"idle": 1}, (96, 144), 0.6),
    "trap_maw": (build_trap_maw, 1, {"bite": 4}, (96, 96), 0.1),
    "trap_hands": (build_trap_hands, 1, {"grab": 4}, (96, 96), 0.25),
    "trap_thorns": (build_trap_thorns, 1, {"idle": 1}, (96, 96), 0.25),
    "trap_pendulum": (build_trap_pendulum, 4, {"swing": 12}, (144, 176), 0.9),
}
ASSETS.update(TRAP_ASSETS)

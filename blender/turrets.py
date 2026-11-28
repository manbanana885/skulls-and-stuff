# Deployable turret modules: MG turret and mortar. dep_<kind> is the deployed unit (aims via direction frames);
# sup_<kind> is the same model spinning, used for the pickup / inventory icon. exec'd after characters.py.

if "olive" not in M:
    mat("olive", (0.18, 0.2, 0.1), 0.2, 0.6)


def turret_mg(root):
    for k in range(3):                                   # tripod
        a = k * math.tau / 3 + PI / 3
        bone("mg_leg%d" % k, (0, 0, 0.32), (math.cos(a) * 0.32, math.sin(a) * 0.32, 0.0), 0.022, M["steel2"], root)
        box("mg_foot%d" % k, (0.07, 0.05, 0.02), (math.cos(a) * 0.32, math.sin(a) * 0.32, 0.01), M["darkmetal"], root, (0, 0, a))
    cyl("mg_post", 0.05, 0.2, (0, 0, 0.4), M["darkmetal"], root, segs=10)
    head = empty("mg_head", (0, 0, 0.52), root)
    box("mg_recv", (0.3, 0.14, 0.13), (0.05, 0, 0.0), M["olive"], head)
    box("mg_shield", (0.03, 0.34, 0.24), (0.18, 0, 0.04), M["steel2"], head)
    box("mg_stripe", (0.032, 0.34, 0.04), (0.18, 0, 0.12), M["hazard"], head)
    for s_ in (1, -1):
        bone("mg_bar%d" % s_, (0.18, s_ * 0.045, 0.0), (0.56, s_ * 0.045, 0.0), 0.02, M["darkmetal"], head)
        ring("mg_muz%d" % s_, 0.026, 0.04, (0.56, s_ * 0.045, 0.0), M["steel"], head, rot=(0, PI / 2, 0), segs=8)
        box("mg_jacket%d" % s_, (0.2, 0.05, 0.05), (0.32, s_ * 0.045, 0.0), M["steel2"], head)
    box("mg_ammo", (0.14, 0.1, 0.12), (-0.03, -0.14, -0.06), M["olive"], head)
    for k in range(5):
        box("mg_belt%d" % k, (0.025, 0.035, 0.02), (0.02 + k * 0.02, -0.09 + k * 0.012, 0.02 - k * 0.008), M["brass"], head)
    box("mg_sensor", (0.06, 0.06, 0.05), (0.05, 0.05, 0.1), M["darkmetal"], head)
    sphere("mg_eye", 0.018, (0.085, 0.05, 0.1), M["glow_red"], head)
    sphere("mg_core", 0.03, (-0.11, 0, 0.0), M["glow_cyan"], head)
    return head


def turret_mortar(root):
    box("mo_plate", (0.4, 0.4, 0.04), (0, 0, 0.02), M["darkmetal"], root)
    bolts("mo_pb", (0, 0, 0.045), "z", 0.15, root, 4)
    box("mo_crate", (0.14, 0.18, 0.12), (-0.12, 0.13, 0.1), M["olive"], root)
    for k in range(3):
        cyl("mo_shell%d" % k, 0.025, 0.12, (-0.16 + k * 0.035, 0.13, 0.22), M["brass"], root, segs=8)
    cyl("mo_turn", 0.12, 0.06, (0, 0, 0.07), M["steel2"], root, segs=14)
    tube = empty("mo_tube", (0.0, 0, 0.12), root, (0, 0.85, 0))           # tilted ~50 degrees up, firing toward +X
    cyl("mo_barrel", 0.065, 0.62, (0, 0, 0.3), M["olive"], tube, segs=14)
    ring("mo_band1", 0.07, 0.04, (0, 0, 0.12), M["hazard"], tube, segs=14)
    ring("mo_band2", 0.07, 0.03, (0, 0, 0.45), M["darkmetal"], tube, segs=14)
    ring("mo_mouth", 0.072, 0.04, (0, 0, 0.6), M["steel"], tube, segs=14)
    cyl("mo_bore", 0.05, 0.02, (0, 0, 0.615), M["black"], tube, segs=12)
    for s_ in (1, -1):                                   # bipod to the plate
        bone("mo_bip%d" % s_, (0.3, s_ * 0.05, 0.4), (0.44, s_ * 0.16, 0.03), 0.016, M["steel2"], root)
    box("mo_sight", (0.06, 0.04, 0.05), (0.05, -0.1, 0.28), M["darkmetal"], root)
    sphere("mo_lens", 0.015, (0.08, -0.1, 0.3), M["glow_red"], root)
    sphere("mo_core", 0.028, (-0.12, -0.1, 0.1), M["glow_cyan"], root)


def build_dep_mgturret():
    root = empty("dmg_root")
    turret_mg(root)
    return root, lambda anim, t: None


def build_dep_mortar():
    root = empty("dmo_root")
    turret_mortar(root)
    return root, lambda anim, t: None


def _icon(fn):
    def build():
        root = empty("ti_root")
        spin = empty("ti_spin", (0, 0, -0.3), root)
        fn(spin)

        def pose(anim, t):
            spin.rotation_euler.z = math.tau * t
        return root, pose
    return build


ASSETS["dep_mgturret"] = (build_dep_mgturret, 16, {"idle": 1}, (96, 96), 0.35)
ASSETS["dep_mortar"] = (build_dep_mortar, 16, {"idle": 1}, (96, 96), 0.35)
ASSETS["sup_mgturret"] = (_icon(turret_mg), 1, {"idle": 8}, (72, 72), 0.0)
ASSETS["sup_mortar"] = (_icon(turret_mortar), 1, {"idle": 8}, (72, 72), 0.0)
CHARACTER_ASSETS = CHARACTER_ASSETS + ("dep_",)

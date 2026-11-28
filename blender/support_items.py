# Barrage launcher, coil guns, microwave emitter + the support gadgets (sawbot, arc shield, medbot, gun drone).
# exec'd by build_assets.py after heavy_guns.py; muzzle values must match game/weapons.py MUZZLE.
# Support bots are modelled centred on the origin (tz=0): the game draws them at their hover height.

mat("coilglow", (0.55, 0.7, 1.0), 0.0, 0.2, (0.55, 0.7, 1.0), 6.0)
mat("mwglow", (0.7, 0.25, 0.85), 0.0, 0.2, (0.85, 0.3, 1.0), 2.2)
mat("shieldglow", (0.2, 0.5, 0.8), 0.0, 0.1, (0.3, 0.7, 1.0), 1.6)
mat("medwhite", (0.85, 0.87, 0.9), 0.1, 0.35)
mat("bladesteel", (0.75, 0.77, 0.8), 1.0, 0.18)


# ---------------------------------------------------------------- guns
def gun_barrage(p, on_body):
    z = GZ + 0.07
    box("ba_pod", (0.5, 0.27, 0.2), (0.62, 0, z), M["darkmetal"], p)
    for s_ in (-1, 1):
        box("ba_stripe%d" % s_, (0.5, 0.012, 0.05), (0.62, s_ * 0.137, z + 0.04), M["hazard"], p)
        box("ba_rail%d" % s_, (0.46, 0.02, 0.02), (0.62, s_ * 0.12, z + 0.11), M["steel2"], p)
    box("ba_face", (0.03, 0.28, 0.21), (0.875, 0, z), M["steel2"], p)
    for c in range(4):
        for r in range(2):
            y, zz = (c - 1.5) * 0.055, z + (r - 0.5) * 0.07
            cyl("ba_tube%d%d" % (c, r), 0.024, 0.1, (0.93, y, zz), M["darkmetal"], p, rot=(0, PI / 2, 0), segs=8)
            cyl("ba_hole%d%d" % (c, r), 0.018, 0.012, (0.981, y, zz), M["black"], p, rot=(0, PI / 2, 0), segs=8)
            cyl("ba_tip%d%d" % (c, r), 0.014, 0.04, (0.96, y, zz), M["glow_orange"], p, rot=(0, PI / 2, 0), r2=0.002, segs=6)
    for k in range(3):     # heat vents on top
        box("ba_vent%d" % k, (0.06, 0.2, 0.012), (0.5 + k * 0.09, 0, z + 0.104), M["black"], p)
    box("ba_sight", (0.1, 0.05, 0.05), (0.5, 0.09, z + 0.14), M["darkmetal"], p)
    sphere("ba_lens", 0.016, (0.555, 0.09, z + 0.14), M["glow_red"], p)
    bolts("ba_b", (0.62, -0.14, z - 0.02), "y", 0.07, p, 4)
    # under-slung grips: the right hand holds the rear, the left a forward handle
    g_grip(p, 0.4, z - 0.1)
    bone("ba_h1", (0.7, 0.02, z - 0.1), (0.7, 0.02, z - 0.2), 0.018, M["rubber"], p)
    wire("ba_cab", (0.38, -0.1, z - 0.08), (0.05, -0.12, z - 0.28), 0.05, 0.02, M["rubber"], p, 5)
    return dict(muzzle=(0.98, z), grip=(0.4, -0.03, z - 0.2), fore=(0.7, 0.05, z - 0.2), rear=(0.38, z - 0.1))


def gun_coil_pistol(p, on_body):
    z = GZ + 0.02
    box("cp_body", (0.2, 0.06, 0.08), (0.5, 0, z + 0.02), M["chrome"], p)
    box("cp_cell", (0.08, 0.02, 0.04), (0.5, 0.035, z + 0.02), M["coilglow"], p)
    g_grip(p, 0.43, z)
    bone("cp_core", (0.58, 0, z + 0.03), (0.7, 0, z + 0.03), 0.012, M["darkmetal"], p)
    for k in range(4):
        ring("cp_coil%d" % k, 0.03, 0.016, (0.61 + 0.027 * k, 0, z + 0.03), M["copper"], p, rot=(0, PI / 2, 0), segs=8)
    for s_ in (-1, 1):
        spike("cp_prong%d" % s_, (0.62, s_ * 0.03, z + 0.05), (0.72, s_ * 0.012, z + 0.04), 0.009, M["chrome"], p)
    sphere("cp_tip", 0.02, (0.73, 0, z + 0.03), M["coilglow"], p)
    return dict(muzzle=(0.74, z + 0.03), grip=(0.43, -0.03, z - 0.08), fore=(0.46, 0.04, z - 0.06), rear=(0.4, z))


def gun_coil_rifle(p, on_body):
    z = GZ + 0.01
    box("cr_body", (0.36, 0.08, 0.11), (0.46, 0, z), M["darkmetal"], p)
    box("cr_top", (0.3, 0.085, 0.03), (0.46, 0, z + 0.07), M["chrome"], p)
    for k in range(3):
        cyl("cr_cell%d" % k, 0.02, 0.08, (0.38 + k * 0.06, 0.05, z + 0.02), M["coilglow"], p, segs=8)
    bone("cr_core", (0.64, 0, z), (1.06, 0, z), 0.016, M["darkmetal"], p)
    for k in range(7):
        ring("cr_coil%d" % k, 0.042, 0.022, (0.68 + k * 0.055, 0, z), M["copper"], p, rot=(0, PI / 2, 0), segs=10)
    for s_ in (-1, 1):
        spike("cr_prong%d" % s_, (0.98, s_ * 0.045, z), (1.11, s_ * 0.015, z), 0.012, M["chrome"], p)
    sphere("cr_tip", 0.026, (1.11, 0, z), M["coilglow"], p)
    box("cr_stock", (0.2, 0.06, 0.1), (0.18, 0, z - 0.01), M["darkmetal"], p)
    wire("cr_cab", (0.3, -0.05, z - 0.03), (0.66, -0.04, z - 0.02), 0.04, 0.012, M["wire_blue"], p, 5)
    g_grip(p, 0.35, z)
    return dict(muzzle=(1.12, z), grip=(0.35, -0.03, z - 0.09), fore=(0.62, 0.06, z - 0.06), rear=(0.27, z))


def gun_coil_heavy(p, on_body):
    z = GZ - 0.03
    box("ch_body", (0.42, 0.17, 0.2), (0.4, 0, z), M["darkmetal"], p)
    box("ch_plate", (0.36, 0.18, 0.03), (0.42, 0, z + 0.11), M["hazard"], p)
    for k in range(3):       # capacitor tanks on top
        cyl("ch_cap%d" % k, 0.035, 0.12, (0.3 + k * 0.1, -0.05, z + 0.18), M["coilglow"], p, segs=8)
        ring("ch_capr%d" % k, 0.04, 0.02, (0.3 + k * 0.1, -0.05, z + 0.24), M["steel2"], p, segs=8)
    bone("ch_core", (0.6, 0, z), (1.15, 0, z), 0.024, M["darkmetal"], p)
    for k in range(7):       # tesla stack tapering toward the muzzle
        rr = 0.085 - k * 0.006
        ring("ch_coil%d" % k, rr, 0.03, (0.64 + k * 0.07, 0, z), M["copper"], p, rot=(0, PI / 2, 0), segs=12)
    ring("ch_torus", 0.095, 0.05, (1.16, 0, z), M["chrome"], p, rot=(0, PI / 2, 0), segs=14)
    sphere("ch_tip", 0.045, (1.2, 0, z), M["coilglow"], p, segs=8, rings=6)
    for k in range(3):
        a = k * math.tau / 3
        spike("ch_fork%d" % k, (1.1, math.cos(a) * 0.07, z + math.sin(a) * 0.07), (1.22, math.cos(a) * 0.03, z + math.sin(a) * 0.03),
              0.012, M["chrome"], p)
    bone("ch_h1", (0.32, 0.0, z + 0.12), (0.38, 0.0, z + 0.3), 0.014, M["steel2"], p)
    bone("ch_h2", (0.6, 0.0, z + 0.12), (0.54, 0.0, z + 0.3), 0.014, M["steel2"], p)
    bone("ch_h3", (0.38, 0.0, z + 0.3), (0.54, 0.0, z + 0.3), 0.018, M["rubber"], p)
    g_grip(p, 0.26, z - 0.03)
    wire("ch_cab", (0.2, 0.06, z - 0.06), (0.04, 0.12, z - 0.26), 0.0, 0.022, M["wire_blue"], p, 5)
    return dict(muzzle=(1.22, z), grip=(0.26, -0.03, z - 0.12), fore=(0.46, 0.06, z + 0.28), rear=(0.22, z))


def gun_microwave(p, on_body):
    z = GZ
    box("mw_body", (0.32, 0.12, 0.14), (0.44, 0, z), M["steel2"], p)
    for k in range(6):       # cooling fins
        box("mw_fin%d" % k, (0.012, 0.15, 0.17), (0.32 + k * 0.045, 0, z), M["darkmetal"], p)
    box("mw_guide", (0.12, 0.07, 0.06), (0.65, 0, z), M["copper"], p)
    cyl("mw_horn", 0.045, 0.26, (0.84, 0, z), M["darkmetal"], p, rot=(0, PI / 2, 0), r2=0.14, segs=4)
    cyl("mw_glow", 0.12, 0.012, (0.968, 0, z), M["mwglow"], p, rot=(0, PI / 2, 0), segs=4)
    ring("mw_lip", 0.142, 0.03, (0.97, 0, z), M["hazard"], p, rot=(0, PI / 2, PI / 4), segs=4)
    sphere("mw_led", 0.016, (0.45, 0.07, z + 0.05), M["mwglow"], p)
    box("mw_stock", (0.18, 0.06, 0.1), (0.18, 0, z - 0.01), M["darkmetal"], p)
    wire("mw_cab", (0.3, -0.07, z - 0.04), (0.62, -0.04, z - 0.02), 0.05, 0.014, M["wire_red"], p, 5)
    g_grip(p, 0.36, z)
    return dict(muzzle=(0.98, z), grip=(0.36, -0.03, z - 0.09), fore=(0.62, 0.06, z - 0.05), rear=(0.27, z))


_NEW = {"barrage": gun_barrage, "coil_pistol": gun_coil_pistol, "coil_rifle": gun_coil_rifle,
        "coil_heavy": gun_coil_heavy, "microwave": gun_microwave}
GUNS.update(_NEW)
for _arch in _NEW:
    ASSETS["torso_" + _arch] = (torso_builder(_arch), 16, {"idle": 1}, (128, 128), 0.6)
    ASSETS["gun_" + _arch] = (gunpickup_builder(_arch), 1, {"idle": 8}, (96, 80), 0.3)


# ---------------------------------------------------------------- support gadgets
def build_sup_sawbot():
    root = empty("ss_root")
    body = empty("ss_body", (0, 0, 0), root)
    sphere("ss_core", 0.13, (0, 0, 0.03), M["darkmetal"], body, (1, 1, 0.8), 12, 8, True)
    cyl("ss_hub", 0.1, 0.06, (0, 0, -0.03), M["hazard"], body, segs=12)
    ring("ss_band", 0.135, 0.04, (0, 0, 0.0), M["steel2"], body, segs=12)
    sphere("ss_eye", 0.04, (0.12, 0, 0.06), M["glow_red"], body)
    bone("ss_ant", (-0.05, 0.03, 0.1), (-0.08, 0.04, 0.22), 0.007, M["chrome"], body)
    sphere("ss_antt", 0.015, (-0.08, 0.04, 0.22), M["glow_yellow"], body)
    blade = empty("ss_blade", (0, 0, -0.03), root)
    cyl("ss_disc", 0.3, 0.014, (0, 0, 0), M["bladesteel"], blade, segs=28)
    ring("ss_disc_in", 0.2, 0.018, (0, 0, 0), M["steel2"], blade, segs=20)
    teeth = 14
    for k in range(teeth):
        a = k * math.tau / teeth
        a2 = a + 0.2
        spike("ss_t%d" % k, (math.cos(a) * 0.28, math.sin(a) * 0.28, 0), (math.cos(a2) * 0.37, math.sin(a2) * 0.37, 0), 0.03,
              M["bladesteel"], blade)

    def pose(anim, t):
        blade.rotation_euler.z = -t * math.tau / teeth      # one tooth per loop -> seamless
    return root, pose


def build_sup_shield():
    root = empty("sh_root")
    spin = empty("sh_spin", (0, 0, 0), root)
    cyl("sh_puck", 0.1, 0.06, (0, 0, -0.16), M["darkmetal"], spin, segs=12)
    ring("sh_puckr", 0.105, 0.03, (0, 0, -0.14), M["shieldglow"], spin, segs=12)
    n = 9
    for k in range(n):
        a = -1.0 + 2.0 * k / (n - 1)
        box("sh_plate%d" % k, (0.03, 0.075, 0.3), (math.cos(a) * 0.24, math.sin(a) * 0.24, 0.02), M["shieldglow"], spin, (0, 0, a))
    for s_ in (-1, 1):
        a = s_ * 1.08
        cyl("sh_node%d" % s_, 0.025, 0.36, (math.cos(a) * 0.24, math.sin(a) * 0.24, 0.02), M["steel2"], spin, segs=8)
        sphere("sh_nodet%d" % s_, 0.03, (math.cos(a) * 0.24, math.sin(a) * 0.24, 0.2), M["glow_white"], spin)

    def pose(anim, t):
        spin.rotation_euler.z = math.tau * t
    return root, pose


def build_sup_medbot():
    root = empty("sm_root")
    body = empty("sm_body", (0, 0, 0), root)
    sphere("sm_shell", 0.15, (0, 0, 0), M["medwhite"], body, (1.1, 1, 0.85), 14, 10, True)
    ring("sm_band", 0.16, 0.04, (0, 0, -0.01), M["steel2"], body, segs=14, scale=(1.1, 1, 1))
    for s_ in (-1, 1):       # red crosses on both flanks
        box("sm_cv%d" % s_, (0.04, 0.012, 0.11), (0, s_ * 0.15, 0.02), M["glow_red"], body)
        box("sm_ch%d" % s_, (0.11, 0.012, 0.04), (0, s_ * 0.15, 0.02), M["glow_red"], body)
    ring("sm_visor", 0.06, 0.03, (0.16, 0, 0.03), M["darkmetal"], body, rot=(0, PI / 2, 0))
    sphere("sm_eye", 0.045, (0.16, 0, 0.03), M["glow_green"], body)
    rotor = empty("sm_rotor", (0, 0, 0.17), body)
    cyl("sm_mast", 0.015, 0.05, (0, 0, -0.02), M["chrome"], rotor, segs=6)
    for k in range(2):
        box("sm_blade%d" % k, (0.36, 0.035, 0.008), (0, 0, 0.01), M["darkmetal"], rotor, (0, 0, k * PI / 2))
    arm = empty("sm_arm", (0.05, 0, -0.1), body)
    bone("sm_a1", (0, 0, 0), (0.08, 0, -0.08), 0.012, M["chrome"], arm)
    cyl("sm_syr", 0.022, 0.09, (0.1, 0, -0.12), M["glass"], arm, rot=(0, -0.6, 0), segs=8)
    cyl("sm_syrf", 0.014, 0.06, (0.1, 0, -0.12), M["glow_green"], arm, rot=(0, -0.6, 0), segs=6)
    spike("sm_needle", (0.13, 0, -0.16), (0.17, 0, -0.21), 0.005, M["chrome"], arm)
    cyl("sm_thrust", 0.05, 0.03, (0, 0, -0.14), M["glow_green"], body, segs=10)

    def pose(anim, t):
        rotor.rotation_euler.z = t * PI          # two-bladed rotor: half a turn per loop is seamless
        arm.rotation_euler.y = math.sin(t * math.tau) * 0.2
    return root, pose


def build_sup_gunbot():
    root = empty("sg_root")
    body = empty("sg_body", (0, 0, 0), root)
    box("sg_hull", (0.26, 0.18, 0.1), (0, 0, 0), M["darkmetal"], body)
    box("sg_top", (0.18, 0.14, 0.04), (-0.02, 0, 0.07), M["hazard"], body)
    box("sg_nose", (0.06, 0.12, 0.07), (0.15, 0, -0.005), M["steel2"], body)
    sphere("sg_eye", 0.03, (0.18, 0, 0.03), M["glow_red"], body)
    for s_ in (-1, 1):
        bone("sg_bar%d" % s_, (0.12, s_ * 0.045, -0.04), (0.32, s_ * 0.045, -0.04), 0.016, M["darkmetal"], body)
        ring("sg_muz%d" % s_, 0.02, 0.03, (0.32, s_ * 0.045, -0.04), M["steel2"], body, rot=(0, PI / 2, 0), segs=8)
    box("sg_mag", (0.08, 0.05, 0.06), (0.02, 0.1, -0.05), M["brass"], body)
    rotors = []
    for k in range(4):
        a = PI / 4 + k * PI / 2
        x, y = math.cos(a) * 0.2, math.sin(a) * 0.2
        bone("sg_arm%d" % k, (0, 0, 0.02), (x, y, 0.05), 0.014, M["steel2"], body)
        ring("sg_duct%d" % k, 0.085, 0.03, (x, y, 0.05), M["darkmetal"], body, segs=12)
        r_ = empty("sg_rot%d" % k, (x, y, 0.05), body)
        for j in range(2):
            box("sg_b%d%d" % (k, j), (0.15, 0.02, 0.005), (0, 0, 0), M["chrome"], r_, (0, 0, j * PI / 2))
        rotors.append(r_)
    cyl("sg_glow", 0.04, 0.02, (0, 0, -0.06), M["glow_orange"], body, segs=8)

    def pose(anim, t):
        for k, r_ in enumerate(rotors):
            r_.rotation_euler.z = (1 if k % 2 else -1) * t * PI / 2   # 4-way symmetric blades
    return root, pose


CHARACTER_ASSETS = CHARACTER_ASSETS + ("sup_",)      # lit like characters, not like the moody environment
ASSETS["sup_sawbot"] = (build_sup_sawbot, 1, {"spin": 8}, (72, 72), 0.0)
ASSETS["sup_shield"] = (build_sup_shield, 1, {"idle": 8}, (72, 72), 0.0)
ASSETS["sup_medbot"] = (build_sup_medbot, 8, {"hover": 4}, (72, 72), 0.0)
ASSETS["sup_gunbot"] = (build_sup_gunbot, 16, {"hover": 4}, (72, 72), 0.0)


# ---- forward / rear shields: fixed walls instead of an orbiting ring
mat("shieldglow_gold", (0.8, 0.55, 0.15), 0.0, 0.1, (1.0, 0.7, 0.25), 1.8)
mat("shieldglow_violet", (0.45, 0.25, 0.8), 0.0, 0.1, (0.65, 0.4, 1.0), 1.8)


def build_sup_shield_front():
    """A tall curved wall of glowing plates on a heavy emitter sled, studded like a tower shield."""
    root = empty("sf_root")
    spin = empty("sf_spin", (0, 0, 0), root)
    box("sf_sled", (0.16, 0.42, 0.06), (-0.04, 0, -0.18), M["darkmetal"], spin)
    box("sf_rail", (0.04, 0.44, 0.03), (0.05, 0, -0.14), M["hazard"], spin)
    n = 7
    for k in range(n):
        a = -0.6 + 1.2 * k / (n - 1)
        x, y = math.cos(a) * 0.26 - 0.2, math.sin(a) * 0.26
        box("sf_plate%d" % k, (0.03, 0.075, 0.36), (x, y, 0.03), M["shieldglow_gold"], spin, (0, 0, a))
        sphere("sf_stud%d" % k, 0.014, (x + 0.02, y, 0.18), M["chrome"], spin)
    for s_ in (-1, 1):
        a = s_ * 0.68
        x, y = math.cos(a) * 0.26 - 0.2, math.sin(a) * 0.26
        cyl("sf_post%d" % s_, 0.03, 0.42, (x, y, 0.03), M["steel2"], spin, segs=8)
        sphere("sf_tip%d" % s_, 0.035, (x, y, 0.25), M["glow_orange"], spin)
    sphere("sf_boss", 0.05, (0.08, 0, 0.05), M["brass"], spin, (0.6, 1, 1))

    def pose(anim, t):
        spin.rotation_euler.z = math.tau * t
    return root, pose


def build_sup_shield_rear():
    """A ribbed violet shell on a backpack frame: a turtle's back for watching your six."""
    root = empty("sr_root")
    spin = empty("sr_spin", (0, 0, 0), root)
    box("sr_frame", (0.12, 0.26, 0.3), (0.06, 0, -0.02), M["darkmetal"], spin)
    for s_ in (-1, 1):
        bone("sr_strap%d" % s_, (0.12, s_ * 0.09, 0.12), (0.12, s_ * 0.09, -0.15), 0.018, M["rubber"], spin)
    n = 6
    for k in range(n):
        a = -0.95 + 1.9 * k / (n - 1)
        x, y = -math.cos(a) * 0.2, math.sin(a) * 0.2
        box("sr_rib%d" % k, (0.035, 0.08, 0.32), (x, y, 0.02), M["shieldglow_violet"], spin, (0, 0, -a))
        box("sr_ridge%d" % k, (0.04, 0.02, 0.34), (x - 0.01, y, 0.02), M["steel2"], spin, (0, 0, -a))
    sphere("sr_dome", 0.09, (-0.08, 0, 0.2), M["steel2"], spin, (1, 1.6, 0.5), 12, 8, True)
    sphere("sr_eye", 0.025, (-0.16, 0, 0.21), M["glow_red"], spin)

    def pose(anim, t):
        spin.rotation_euler.z = math.tau * t
    return root, pose


ASSETS["sup_shield_front"] = (build_sup_shield_front, 1, {"idle": 8}, (72, 72), 0.0)
ASSETS["sup_shield_rear"] = (build_sup_shield_rear, 1, {"idle": 8}, (72, 72), 0.0)

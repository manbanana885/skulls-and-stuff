# Heavy weapons (chaingun, railgun) - exec'd by build_assets.py after expansion.py / traps.py.
# muzzle values returned here must match game/weapons.py MUZZLE.

mat("railglow", (0.4, 0.85, 1.0), 0.0, 0.2, (0.4, 0.85, 1.0), 5.0)


def gun_chaingun(p, on_body):
    z = GZ - 0.04
    box("cg_recv", (0.36, 0.17, 0.2), (0.4, 0, z), M["darkmetal"], p)
    box("cg_plate", (0.3, 0.18, 0.04), (0.42, 0, z + 0.12), M["hazard"], p)
    bolts("cg_bb", (0.4, 0.09, z), "y", 0.07, p, 4)
    cyl("cg_motor", 0.07, 0.12, (0.25, 0, z + 0.02), M["steel2"], p, rot=(0, PI / 2, 0), segs=10)
    cluster = empty("cg_cluster", (0.6, 0, z), p)
    for k in range(6):
        a = k * math.tau / 6
        oy, oz = math.cos(a) * 0.055, math.sin(a) * 0.055
        bone("cg_bar%d" % k, (0.0, oy, oz), (0.6, oy, oz), 0.019, M["darkmetal"], cluster)
        ring("cg_tip%d" % k, 0.022, 0.03, (0.6, oy, oz), M["steel2"], cluster, rot=(0, PI / 2, 0), segs=6)
    for x in (0.08, 0.3, 0.52):
        ring("cg_clamp%.2f" % x, 0.085, 0.04, (x, 0, 0), M["steel2"], cluster, rot=(0, PI / 2, 0), segs=10)
    cyl("cg_hub", 0.03, 0.62, (0.3, 0, 0), M["chrome"], cluster, rot=(0, PI / 2, 0), segs=8)
    # ammo drum + belt feeding in from the side
    cyl("cg_drum", 0.13, 0.12, (0.36, -0.2, z - 0.06), M["darkmetal"], p, rot=(PI / 2, 0, 0), segs=14)
    ring("cg_drumband", 0.135, 0.03, (0.36, -0.2, z - 0.06), M["hazard"], p, rot=(PI / 2, 0, 0), segs=14)
    for k in range(6):
        box("cg_belt%d" % k, (0.035, 0.05, 0.03), (0.42 + math.sin(k * 0.6) * 0.02, -0.12 + k * 0.018, z + 0.04 - k * 0.012), M["brass"], p)
    # carry handle (the left hand grabs it) and rear grip
    bone("cg_h1", (0.36, 0.0, z + 0.14), (0.42, 0.0, z + 0.24), 0.014, M["steel2"], p)
    bone("cg_h2", (0.62, 0.0, z + 0.14), (0.56, 0.0, z + 0.24), 0.014, M["steel2"], p)
    bone("cg_h3", (0.42, 0.0, z + 0.24), (0.56, 0.0, z + 0.24), 0.018, M["rubber"], p)
    g_grip(p, 0.28, z - 0.03)
    wire("cg_cab", (0.22, 0.05, z - 0.05), (0.05, 0.12, z - 0.25), 0.0, 0.02, M["rubber"], p, 5)
    return dict(muzzle=(1.2, z), grip=(0.28, -0.03, z - 0.12), fore=(0.5, 0.06, z + 0.22), rear=(0.24, z))


def gun_railgun(p, on_body):
    z = GZ + 0.02
    box("rg_body", (0.42, 0.12, 0.16), (0.36, 0, z - 0.02), M["darkmetal"], p)
    for k in range(4):     # capacitor cells
        cyl("rg_cell%d" % k, 0.028, 0.12, (0.22 + k * 0.08, 0.075, z - 0.02), M["railglow"], p, segs=8)
        ring("rg_cellr%d" % k, 0.032, 0.02, (0.22 + k * 0.08, 0.075, z + 0.03), M["steel2"], p, segs=8)
    for s_ in (-1, 1):    # twin rails
        box("rg_rail%d" % s_, (0.88, 0.03, 0.035), (1.0, 0, z + s_ * 0.05), M["chrome"], p)
    for k in range(6):    # accelerator coils between the rails
        x = 0.65 + k * 0.14
        ring("rg_coil%d" % k, 0.075, 0.035, (x, 0, z), M["copper"], p, rot=(0, PI / 2, 0), segs=10)
        sphere("rg_glow%d" % k, 0.022, (x, 0, z), M["railglow"], p, segs=6, rings=4)
    box("rg_spine", (0.88, 0.02, 0.02), (1.0, 0, z - 0.085), M["darkmetal"], p)
    box("rg_tip", (0.06, 0.05, 0.16), (1.45, 0, z), M["darkmetal"], p)
    bone("rg_scope", (0.3, 0, z + 0.12), (0.55, 0, z + 0.12), 0.03, M["darkmetal"], p)
    sphere("rg_lens", 0.025, (0.56, 0, z + 0.12), M["glow_cyan"], p)
    box("rg_stock", (0.24, 0.07, 0.13), (0.1, 0, z - 0.04), M["darkmetal"], p)
    box("rg_pad", (0.05, 0.08, 0.15), (-0.03, 0, z - 0.04), M["rubber"], p)
    wire("rg_cab", (0.2, -0.06, z - 0.08), (0.62, -0.06, z - 0.06), 0.05, 0.016, M["wire_blue"], p, 5)
    g_grip(p, 0.3, z - 0.02)
    box("rg_fore", (0.05, 0.05, 0.1), (0.66, 0, z - 0.12), M["darkmetal"], p)
    return dict(muzzle=(1.47, z), grip=(0.3, -0.03, z - 0.11), fore=(0.66, 0.05, z - 0.16), rear=(0.28, z))


_HEAVY = {"chaingun": gun_chaingun, "railgun": gun_railgun}
GUNS.update(_HEAVY)
for _arch in _HEAVY:
    ASSETS["torso_" + _arch] = (torso_builder(_arch), 16, {"idle": 1}, (128, 128), 0.6)
    ASSETS["gun_" + _arch] = (gunpickup_builder(_arch), 1, {"idle": 8}, (96, 80), 0.3)

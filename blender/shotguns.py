# Shotgun family: drum-fed auto shotgun and the break-action double / triple / quad barrels.
# exec'd before characters.py so every body gets a torso holding each one. Muzzles must match game/weapons.py MUZZLE.
# Slug shells (dum-dum / sabot) reuse these models - they only change what comes out of the barrel.

if "walnut" not in M:
    mat("walnut", (0.2, 0.09, 0.035), 0.0, 0.55)
if "walnut2" not in M:
    mat("walnut2", (0.12, 0.05, 0.02), 0.0, 0.6)
if "blued" not in M:
    mat("blued", (0.03, 0.04, 0.06), 0.9, 0.3)


def gun_auto_shotgun(p, on_body):
    z = GZ + 0.02
    box("as_rec", (0.34, 0.09, 0.13), (0.45, 0, z), M["darkmetal"], p)
    box("as_upper", (0.3, 0.07, 0.03), (0.46, 0, z + 0.08), M["steel2"], p)
    for k in range(5):
        box("as_rail%d" % k, (0.02, 0.075, 0.015), (0.34 + k * 0.055, 0, z + 0.1), M["black"], p)
    bone("as_bar", (0.62, 0, z + 0.01), (1.0, 0, z + 0.01), 0.032, M["steel2"], p)
    box("as_shield", (0.3, 0.08, 0.05), (0.78, 0, z + 0.05), M["darkmetal"], p)
    for k in range(5):
        box("as_vent%d" % k, (0.025, 0.084, 0.02), (0.67 + k * 0.055, 0, z + 0.06), M["black"], p)
    box("as_brake", (0.07, 0.08, 0.07), (1.01, 0, z + 0.01), M["darkmetal"], p)
    for s_ in (-1, 1):
        box("as_port%d" % s_, (0.045, 0.01, 0.03), (1.01, s_ * 0.041, z + 0.01), M["black"], p)
    # the drum: a fat round magazine slung under the receiver
    cyl("as_drum", 0.13, 0.1, (0.5, 0, z - 0.15), M["darkmetal"], p, rot=(PI / 2, 0, 0), segs=16)
    ring("as_drumband", 0.133, 0.035, (0.5, 0, z - 0.15), M["hazard"], p, rot=(PI / 2, 0, 0), segs=16)
    cyl("as_hub", 0.035, 0.11, (0.5, 0, z - 0.15), M["chrome"], p, rot=(PI / 2, 0, 0), segs=8)
    for k in range(6):
        a = k * PI / 3
        box("as_rib%d" % k, (0.02, 0.104, 0.07), (0.5 + math.cos(a) * 0.085, 0, z - 0.15 + math.sin(a) * 0.085), M["steel2"], p,
            (0, -a, 0))
    box("as_feed", (0.08, 0.07, 0.05), (0.5, 0, z - 0.04), M["steel2"], p)
    box("as_stock", (0.2, 0.06, 0.11), (0.18, 0, z - 0.01), M["darkmetal"], p)
    box("as_pad", (0.04, 0.07, 0.13), (0.07, 0, z - 0.01), M["rubber"], p)
    bone("as_fore", (0.78, 0, z - 0.03), (0.78, 0, z - 0.13), 0.02, M["rubber"], p)
    box("as_glow", (0.08, 0.092, 0.012), (0.42, 0, z - 0.02), M["glow_orange"], p)
    g_grip(p, 0.36, z)
    return dict(muzzle=(1.04, z + 0.01), grip=(0.36, -0.03, z - 0.09), fore=(0.78, 0.05, z - 0.13), rear=(0.27, z))


def _break_action(p, tag, holes, z, barrel_mat, wood, reach=0.98):
    """Shared break-action body: receiver, hinge, wooden forend and stock. holes = [(y, dz)] barrel centres."""
    for i, (y, dz) in enumerate(holes):
        bone("%s_bar%d" % (tag, i), (0.48, y, z + dz), (reach, y, z + dz), 0.026, M[barrel_mat], p)
        ring("%s_mz%d" % (tag, i), 0.029, 0.03, (reach, y, z + dz), M["steel2"], p, rot=(0, PI / 2, 0), segs=10)
        cyl("%s_bore%d" % (tag, i), 0.017, 0.01, (reach + 0.016, y, z + dz), M["black"], p, rot=(0, PI / 2, 0), segs=8)
    top = max(dz for _, dz in holes)
    low = min(dz for _, dz in holes)
    wide = max(abs(y) for y, _ in holes)
    box("%s_rib" % tag, (reach - 0.5, 0.02, 0.012), ((reach + 0.5) / 2, 0, z + top + 0.03), M["darkmetal"], p)
    sphere("%s_bead" % tag, 0.011, (reach - 0.02, 0, z + top + 0.042), M["chrome"], p)
    for x in (0.62, 0.86):          # clamp bands holding the barrel bundle together
        box("%s_band%.2f" % (tag, x), (0.03, wide * 2 + 0.06, top - low + 0.06), (x, 0, z + (top + low) / 2), M["darkmetal"], p)
    box("%s_rec" % tag, (0.17, wide * 2 + 0.05, top - low + 0.1), (0.4, 0, z + (top + low) / 2 - 0.01), M["steel2"], p)
    cyl("%s_hinge" % tag, 0.022, wide * 2 + 0.06, (0.48, 0, z + low - 0.04), M["chrome"], p, rot=(PI / 2, 0, 0), segs=8)
    box("%s_lever" % tag, (0.05, 0.02, 0.02), (0.34, 0, z + top + 0.05), M["chrome"], p, (0, 0, 0.4))
    box("%s_forend" % tag, (0.22, wide * 2 + 0.03, 0.05), (0.62, 0, z + low - 0.045), M[wood], p)
    box("%s_stock" % tag, (0.26, 0.065, 0.11), (0.2, 0, z - 0.04), M[wood], p, (0, 0.14, 0))
    box("%s_butt" % tag, (0.03, 0.07, 0.13), (0.07, 0, z - 0.06), M["rubber"], p, (0, 0.14, 0))
    g_grip(p, 0.33, z, wood)
    return top, low, wide


def gun_shotgun_2(p, on_body):
    """Side-by-side double: twin blued barrels, walnut furniture, two exposed hammers."""
    z = GZ + 0.03
    _break_action(p, "d2", [(-0.028, 0.0), (0.028, 0.0)], z, "blued", "walnut")
    for s_ in (-1, 1):
        box("d2_hammer%d" % s_, (0.03, 0.014, 0.045), (0.34, s_ * 0.03, z + 0.055), M["darkmetal"], p, (0, -0.4, 0))
    for k in range(2):
        box("d2_shell%d" % k, (0.012, 0.03, 0.014), (0.24 + 0.03 * k, 0.04, z - 0.02), M["armor"], p)
    return dict(muzzle=(1.0, z), grip=(0.33, -0.03, z - 0.09), fore=(0.62, 0.05, z - 0.08), rear=(0.3, z))


def gun_shotgun_3(p, on_body):
    """Three-barrel drilling: two side by side, one riding on top; chrome barrels, bone-inlaid dark stock."""
    z = GZ + 0.02
    top, low, wide = _break_action(p, "d3", [(-0.028, 0.0), (0.028, 0.0), (0.0, 0.046)], z, "chrome", "walnut2")
    for k in range(3):                # bone inlays down the stock
        box("d3_inlay%d" % k, (0.05, 0.068, 0.012), (0.14 + k * 0.06, 0, z - 0.01 - k * 0.008), M["bone"], p, (0, 0.14, 0))
    box("d3_hammer", (0.035, 0.016, 0.05), (0.34, 0, z + 0.1), M["darkmetal"], p, (0, -0.4, 0))
    sphere("d3_skull", 0.022, (0.4, 0.05, z + 0.02), M["bone"], p, (0.9, 0.5, 1))
    return dict(muzzle=(1.0, z + 0.02), grip=(0.33, -0.03, z - 0.09), fore=(0.62, 0.06, z - 0.08), rear=(0.3, z))


def gun_shotgun_4(p, on_body):
    """Quad block: four barrels in a 2x2 bundle, hazard-striped bands, a side saddle of spare shells."""
    z = GZ + 0.02
    top, low, wide = _break_action(p, "d4", [(-0.029, -0.026), (0.029, -0.026), (-0.029, 0.026), (0.029, 0.026)],
                                   z + 0.03, "darkmetal", "walnut", reach=0.97)
    for x in (0.74,):
        box("d4_hz%.2f" % x, (0.035, wide * 2 + 0.065, top - low + 0.065), (x, 0, z + 0.03), M["hazard"], p)
    box("d4_saddle", (0.14, 0.02, 0.07), (0.4, 0.075, z + 0.02), M["darkmetal"], p)
    for k in range(4):
        cyl("d4_shell%d" % k, 0.012, 0.06, (0.35 + k * 0.032, 0.088, z + 0.02), M["armor"], p, segs=6)
        cyl("d4_cap%d" % k, 0.013, 0.012, (0.35 + k * 0.032, 0.088, z - 0.012), M["brass"], p, segs=6)
    for s_ in (-1, 1):
        box("d4_hammer%d" % s_, (0.03, 0.014, 0.05), (0.34, s_ * 0.032, z + 0.1), M["darkmetal"], p, (0, -0.4, 0))
    box("d4_pad", (0.05, 0.08, 0.15), (0.06, 0, z - 0.06), M["rubber"], p, (0, 0.14, 0))
    return dict(muzzle=(0.99, z + 0.03), grip=(0.33, -0.03, z - 0.09), fore=(0.62, 0.06, z - 0.06), rear=(0.3, z))


_SHOTGUNS = {"auto_shotgun": gun_auto_shotgun, "shotgun_2": gun_shotgun_2, "shotgun_3": gun_shotgun_3, "shotgun_4": gun_shotgun_4}
GUNS.update(_SHOTGUNS)
for _arch in _SHOTGUNS:
    ASSETS["torso_" + _arch] = (torso_builder(_arch), 16, {"idle": 1}, (128, 128), 0.6)
    ASSETS["gun_" + _arch] = (gunpickup_builder(_arch), 1, {"idle": 8}, (80, 80), 0.3)

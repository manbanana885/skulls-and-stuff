# Cluster bomb launcher: a fat, short tube with a drum magazine and a striped bomb sitting in the muzzle.
# exec'd before characters.py so every body gets a torso holding it. Muzzle must match game/weapons.py MUZZLE.

if "olive" not in M:
    mat("olive", (0.18, 0.2, 0.1), 0.2, 0.6)


def gun_cluster(p, on_body):
    z = GZ + 0.01
    cyl("cl_tube", 0.085, 0.5, (0.7, 0, z + 0.03), M["olive"], p, rot=(0, PI / 2, 0), segs=14)
    for x, m in ((0.5, "hazard"), (0.72, "darkmetal"), (0.93, "hazard")):
        ring("cl_band%.2f" % x, 0.09, 0.04, (x, 0, z + 0.03), M[m], p, rot=(0, PI / 2, 0), segs=14)
    sphere("cl_bomb", 0.07, (0.95, 0, z + 0.03), M["darkmetal"], p, (0.9, 1, 1), 12, 8, True)
    ring("cl_bombstripe", 0.072, 0.025, (0.95, 0, z + 0.03), M["glow_orange"], p, rot=(0, PI / 2, 0), segs=12)
    box("cl_body", (0.3, 0.1, 0.14), (0.36, 0, z), M["darkmetal"], p)
    cyl("cl_drum", 0.1, 0.12, (0.4, 0, z - 0.1), M["olive"], p, rot=(PI / 2, 0, 0), segs=12)
    ring("cl_drumband", 0.103, 0.03, (0.4, 0, z - 0.1), M["hazard"], p, rot=(PI / 2, 0, 0), segs=12)
    for k in range(6):
        a = k * PI / 3
        cyl("cl_cell%d" % k, 0.022, 0.125, (0.4 + math.cos(a) * 0.06, 0, z - 0.1 + math.sin(a) * 0.06), M["black"], p,
            rot=(PI / 2, 0, 0), segs=6)
    box("cl_sight", (0.1, 0.04, 0.06), (0.5, 0.07, z + 0.14), M["darkmetal"], p)
    sphere("cl_lens", 0.016, (0.55, 0.07, z + 0.15), M["glow_red"], p)
    box("cl_stock", (0.18, 0.06, 0.1), (0.15, 0, z - 0.01), M["darkmetal"], p)
    box("cl_pad", (0.04, 0.07, 0.12), (0.05, 0, z - 0.01), M["rubber"], p)
    bone("cl_fore", (0.6, 0, z - 0.06), (0.6, 0, z - 0.16), 0.02, M["rubber"], p)
    g_grip(p, 0.3, z)
    return dict(muzzle=(1.0, z + 0.03), grip=(0.3, -0.03, z - 0.09), fore=(0.6, 0.05, z - 0.16), rear=(0.22, z))


GUNS["cluster"] = gun_cluster
ASSETS["torso_cluster"] = (torso_builder("cluster"), 16, {"idle": 1}, (128, 128), 0.6)
ASSETS["gun_cluster"] = (gunpickup_builder("cluster"), 1, {"idle": 8}, (96, 80), 0.3)

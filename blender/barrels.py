# Explosive barrels, colour-coded by what they release: red = fire, green = chemical waste, yellow = radiation,
# orange = shrapnel. exec'd after turrets.py.

mat("bar_red", (0.45, 0.04, 0.03), 0.4, 0.4)
mat("bar_green", (0.08, 0.3, 0.05), 0.4, 0.45)
mat("bar_yellow", (0.75, 0.55, 0.03), 0.4, 0.4)
mat("bar_orange", (0.8, 0.28, 0.03), 0.4, 0.4)
mat("trefoil", (0.02, 0.02, 0.02), 0.0, 0.6)


def barrel_builder(kind):
    paint = {"fire": "bar_red", "chem": "bar_green", "rad": "bar_yellow", "shrap": "bar_orange"}[kind]
    lid = {"fire": "glow_orange", "chem": "glow_green", "rad": "glow_green", "shrap": "darkmetal"}[kind]

    def build():
        r = tile_root()
        cyl("body", 0.27, 0.72, (0, 0, 0.36), M[paint], r, segs=14)
        for z in (0.12, 0.6):
            ring("band%.2f" % z, 0.285, 0.05, (0, 0, z), M["darkmetal"], r, segs=14)
        cyl("lid", 0.2, 0.02, (0, 0, 0.725), M[lid], r, segs=12)
        cyl("bung", 0.04, 0.03, (0.1, 0.08, 0.74), M["steel2"], r, segs=8)
        box("dent", (0.02, 0.1, 0.12), (0.255, -0.15, 0.5), M["rust2"], r, (0, 0, -0.5))
        if kind == "fire":                       # flame decal + scorch, a little flame licking out of the bung
            box("label", (0.02, 0.18, 0.2), (0.27, 0, 0.36), M["hazard"], r)
            for k in range(3):
                spike("flame%d" % k, (0.282, -0.05 + k * 0.05, 0.28), (0.282, -0.05 + k * 0.05 + 0.01, 0.42 + 0.03 * (k % 2)), 0.025,
                      M["glow_orange"], r)
            spike("lick", (0.1, 0.08, 0.75), (0.11, 0.09, 0.86), 0.02, M["glow_orange"], r)
        elif kind == "chem":                     # slime leaking down the sides and pooling
            box("label", (0.02, 0.18, 0.18), (0.27, 0, 0.36), M["hazard"], r)
            drip("bdrip1", (0.25, 0.12, 0.73), 0.22, 0.02, M["slime"], r)
            drip("bdrip2", (0.18, -0.19, 0.73), 0.14, 0.018, M["slime"], r)
            pool("bpool", (0.3, 0.1, 0.002), 0.25, r, M["slime"], 3)
        elif kind == "rad":                      # black trefoil on yellow
            cyl("tre_c", 0.03, 0.01, (0.276, 0, 0.38), M["trefoil"], r, rot=(0, PI / 2, 0), segs=10)
            for k in range(3):
                a = k * math.tau / 3 + PI / 2
                box("tre%d" % k, (0.01, 0.09, 0.07), (0.276, math.cos(a) * 0.075, 0.38 + math.sin(a) * 0.075), M["trefoil"], r, (a, 0, 0))
            ring("tre_ring", 0.13, 0.012, (0.27, 0, 0.38), M["trefoil"], r, rot=(0, PI / 2, 0), segs=16)
        else:                                    # shrapnel: hazard stripes and studs of packed fragments
            for z in (0.24, 0.48):
                ring("stripe%.2f" % z, 0.274, 0.06, (0, 0, z), M["hazard"], r, segs=14)
            for k in range(12):
                a = k * math.tau / 12
                sphere("stud%d" % k, 0.022, (math.cos(a) * 0.272, math.sin(a) * 0.272, 0.36), M["chrome"], r, segs=5, rings=4)
        return r, None
    return build


for _k in ("fire", "chem", "rad", "shrap"):
    ASSETS["barrel_" + _k] = (barrel_builder(_k), 1, {"idle": 1}, (96, 96), 0.4)

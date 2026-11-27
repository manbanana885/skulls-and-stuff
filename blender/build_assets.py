"""
Skulls & Stuff - procedural asset builder.

Builds every model from code and renders isometric (2:1 dimetric) sprites.

    blender -b -P blender/build_assets.py -- [asset names ...] [--quick]

Asset names may end in * as a prefix match (e.g. gib_*).
--quick renders only a couple of directions / one frame (for previews).
Output: assets/sprites/<asset>/<anim>_<dir>_<frame>.png + assets/sprites/manifest.json
"""
import bpy
import bmesh
import math
import os
import sys
import json
import random
import zlib
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "assets", "sprites")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in argv
ONLY = [a for a in argv if not a.startswith("--")]

PI = math.pi
TILE_W = 128                                  # pixel width of one floor tile (game reads this from the manifest)
RS = TILE_W / 64                              # resolution scale vs. the 64px base sizes in the registry
K = (TILE_W / 2) / math.cos(math.radians(45))  # pixels per blender unit on the camera plane
ZPIX = K * math.cos(math.radians(30))          # pixels per unit of height

# ---------------------------------------------------------------- scene setup
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
print("Render engine:", scene.render.engine)

scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.resolution_percentage = 100
scene.render.filter_size = 1.0
try:
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
except Exception:
    pass
try:
    scene.eevee.taa_render_samples = 24
except Exception:
    pass

world = bpy.data.worlds.new("World")
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
if world.node_tree:
    bg = world.node_tree.nodes.get("Background")
    if bg is None:
        bg = world.node_tree.nodes.new("ShaderNodeBackground")
        out = world.node_tree.nodes.get("World Output") or world.node_tree.nodes.new("ShaderNodeOutputWorld")
        world.node_tree.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs[0].default_value = (0.32, 0.34, 0.42, 1.0)
    bg.inputs[1].default_value = 0.9

cam_data = bpy.data.cameras.new("Cam")
cam_data.type = "ORTHO"
cam_data.clip_start = 0.1
cam_data.clip_end = 200
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
CAM_ROT = Euler((math.radians(60), 0, math.radians(135)))
cam.rotation_euler = CAM_ROT
CAM_FWD = CAM_ROT.to_matrix() @ Vector((0, 0, -1))


def aim_camera(res, target_z):
    rx, ry = res
    scene.render.resolution_x = rx
    scene.render.resolution_y = ry
    cam_data.ortho_scale = max(rx, ry) / K
    cam.location = Vector((0, 0, target_z)) - CAM_FWD * 40


def add_sun(name, direction, energy, color):
    ld = bpy.data.lights.new(name, "SUN")
    ld.energy = energy
    ld.color = color
    try:
        ld.angle = math.radians(3)
    except Exception:
        pass
    ob = bpy.data.objects.new(name, ld)
    scene.collection.objects.link(ob)
    ob.rotation_euler = Vector(direction).normalized().to_track_quat("-Z", "Y").to_euler()
    return ob


# Key light from screen top-left (world -Y), cool fill from screen right, rim from behind.
LIGHTS = [
    (add_sun("Key", (0.25, 1.0, -1.25), 4.0, (1.0, 0.93, 0.82)), 4.0),
    (add_sun("Fill", (-1.0, -0.2, -0.6), 0.9, (0.55, 0.7, 1.0)), 0.9),
    (add_sun("Rim", (1.0, 1.0, -0.22), 1.6, (0.75, 0.8, 1.0)), 1.6),
]
CHARACTER_ASSETS = ("player_", "torso_", "gun_", "zombie", "spider", "leech", "drone", "gib_", "health", "power", "spawner",
                    "brute", "crawler", "spitter", "turret", "walker", "bloater", "skull", "hellspawn", "wretch", "stalker", "mimic")


def set_lighting(name):
    """Environment is lit darker and moodier than characters so they pop."""
    env = not name.startswith(CHARACTER_ASSETS)
    for ob, energy in LIGHTS:
        ob.data.energy = energy * (0.5 if env else 1.0)
    if world.node_tree:
        world.node_tree.nodes["Background"].inputs[1].default_value = 0.45 if env else 0.9

# ---------------------------------------------------------------- materials
M = {}


def mat(name, color, metal=0.0, rough=0.5, emit=None, strength=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    m.diffuse_color = (*color, alpha)
    p = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
    if p is None and m.node_tree:
        p = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = m.node_tree.nodes.get("Material Output") or m.node_tree.nodes.new("ShaderNodeOutputMaterial")
        m.node_tree.links.new(p.outputs[0], out.inputs[0])
    if p:
        p.inputs["Base Color"].default_value = (*color, 1.0)
        p.inputs["Metallic"].default_value = metal
        p.inputs["Roughness"].default_value = rough
        if emit:
            p.inputs["Emission Color"].default_value = (*emit, 1.0)
            p.inputs["Emission Strength"].default_value = strength
        if alpha < 1.0:
            p.inputs["Alpha"].default_value = alpha
            for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
                try:
                    setattr(m, attr, val)
                except Exception:
                    pass
    M[name] = m
    return m


mat("bone", (0.78, 0.72, 0.58), 0.0, 0.55)
mat("bone_dirty", (0.5, 0.42, 0.3), 0.0, 0.6)
mat("chrome", (0.8, 0.82, 0.86), 1.0, 0.22)
mat("darkmetal", (0.07, 0.075, 0.09), 0.85, 0.38)
mat("armor", (0.6, 0.06, 0.04), 0.35, 0.3)          # player red
mat("black", (0.01, 0.01, 0.012), 0.0, 0.8)
mat("glow_cyan", (0.1, 0.8, 1.0), 0, 0.3, (0.15, 0.85, 1.0), 6.0)
mat("glow_red", (1.0, 0.1, 0.05), 0, 0.3, (1.0, 0.08, 0.03), 9.0)
mat("glow_green", (0.3, 1.0, 0.2), 0, 0.3, (0.35, 1.0, 0.15), 5.0)
mat("glow_green_dim", (0.2, 0.6, 0.1), 0, 0.3, (0.3, 1.0, 0.12), 1.6)
mat("glow_yellow", (1.0, 0.8, 0.1), 0, 0.3, (1.0, 0.75, 0.1), 6.0)
mat("glow_blue", (0.2, 0.4, 1.0), 0, 0.3, (0.25, 0.45, 1.0), 7.0)
mat("glow_white", (1.0, 1.0, 1.0), 0, 0.3, (1.0, 0.95, 0.9), 5.0)
mat("glow_orange", (1.0, 0.4, 0.05), 0, 0.3, (1.0, 0.45, 0.08), 8.0)
mat("zskin", (0.3, 0.38, 0.2), 0.0, 0.8)
mat("zskin2", (0.22, 0.26, 0.15), 0.0, 0.8)
mat("zcloth", (0.12, 0.09, 0.14), 0.0, 0.9)
mat("flesh", (0.4, 0.03, 0.03), 0.0, 0.35)
mat("guts", (0.55, 0.17, 0.17), 0.0, 0.12)
mat("blood", (0.16, 0.0, 0.0), 0.0, 0.06)
mat("vein", (0.22, 0.01, 0.05), 0.0, 0.3)
mat("slime", (0.25, 0.7, 0.08), 0.0, 0.05, (0.3, 0.9, 0.1), 0.8)
mat("chitin", (0.08, 0.035, 0.1), 0.2, 0.28)
mat("chitin2", (0.2, 0.06, 0.08), 0.2, 0.3)
mat("leech", (0.33, 0.1, 0.09), 0.0, 0.15)
mat("leech2", (0.6, 0.38, 0.28), 0.0, 0.2)
mat("hazard", (0.85, 0.55, 0.02), 0.3, 0.4)
mat("steel", (0.075, 0.08, 0.095), 0.35, 0.55)
mat("steel2", (0.11, 0.115, 0.135), 0.35, 0.5)
mat("cap", (0.035, 0.035, 0.045), 0.0, 0.85)
mat("concrete", (0.12, 0.105, 0.095), 0.0, 0.95)
mat("concrete2", (0.06, 0.055, 0.05), 0.0, 0.95)
mat("stone", (0.13, 0.1, 0.09), 0.0, 0.9)
mat("rust", (0.3, 0.11, 0.04), 0.5, 0.7)
mat("rust2", (0.18, 0.06, 0.02), 0.4, 0.8)
mat("barrel", (0.08, 0.16, 0.05), 0.5, 0.45)
mat("crate", (0.18, 0.16, 0.08), 0.1, 0.8)
mat("white", (0.9, 0.9, 0.9), 0.0, 0.4)
mat("rubber", (0.02, 0.02, 0.025), 0.0, 0.55)
mat("wire_red", (0.55, 0.02, 0.02), 0.0, 0.4)
mat("wire_yellow", (0.75, 0.5, 0.02), 0.0, 0.4)
mat("wire_blue", (0.03, 0.12, 0.6), 0.0, 0.4)
mat("copper", (0.8, 0.35, 0.15), 1.0, 0.3)
mat("circuit", (0.02, 0.22, 0.07), 0.2, 0.4)
mat("glass", (0.6, 0.85, 0.8), 0.0, 0.05, alpha=0.28)
mat("brain", (0.75, 0.42, 0.45), 0.0, 0.25)
mat("tooth", (0.85, 0.82, 0.68), 0.0, 0.3)

# ---------------------------------------------------------------- geometry helpers
COLL = None
RNG = random.Random(7)


def new_collection(name):
    global COLL
    COLL = bpy.data.collections.new(name)
    scene.collection.children.link(COLL)
    return COLL


def finish(name, bm, material, parent, loc, rot=(0, 0, 0), scale=(1, 1, 1), smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if material is not None:
        me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    ob.rotation_euler = rot
    ob.scale = scale
    return ob


def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    COLL.objects.link(e)
    e.parent = parent
    e.location = loc
    e.rotation_euler = rot
    return e


def box(name, size, loc, material, parent=None, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    return finish(name, bm, material, parent, loc, rot)


def cyl(name, r, depth, loc, material, parent=None, rot=(0, 0, 0), segs=8, r2=None, caps=True, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=segs, radius1=r,
                          radius2=r if r2 is None else r2, depth=depth)
    return finish(name, bm, material, parent, loc, rot, scale)


def ring(name, r, depth, loc, material, parent=None, rot=(0, 0, 0), segs=10, scale=(1, 1, 1)):
    return cyl(name, r, depth, loc, material, parent, rot, segs, caps=False, scale=scale)


def sphere(name, r, loc, material, parent=None, scale=(1, 1, 1), segs=8, rings=6, smooth=False, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    return finish(name, bm, material, parent, loc, rot, scale, smooth)


def bone(name, p1, p2, r, material, parent=None, segs=6, r2=None):
    """Cylinder from p1 to p2 (in parent space)."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    if d.length < 1e-5:
        return None
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r,
                          radius2=r if r2 is None else r2, depth=d.length)
    rot = d.to_track_quat("Z", "Y").to_euler()
    return finish(name, bm, material, parent, (p1 + p2) / 2, rot)


def spike(name, p1, p2, r, material, parent=None):
    return bone(name, p1, p2, r, material, parent, segs=5, r2=r * 0.08)


def tube(name, pts, r, material, parent, segs=6, r_end=None, smooth_joints=True):
    n = len(pts) - 1
    for i in range(n):
        ra = r if r_end is None else r + (r_end - r) * i / n
        rb = r if r_end is None else r + (r_end - r) * (i + 1) / n
        bone("%s%d" % (name, i), pts[i], pts[i + 1], ra, material, parent, segs, rb)
        if i > 0 and smooth_joints:
            sphere("%sj%d" % (name, i), ra, pts[i], material, parent, segs=segs, rings=4)


def curve_pts(p1, p2, sag=0.0, n=6, bulge=(0, 0, 0), wobble=0.0):
    pts = []
    for k in range(n + 1):
        t = k / n
        p = Vector(p1).lerp(Vector(p2), t)
        p.z -= sag * 4 * t * (1 - t)
        p += Vector(bulge) * 4 * t * (1 - t)
        if wobble and 0 < k < n:
            p += Vector((RNG.uniform(-1, 1), RNG.uniform(-1, 1), RNG.uniform(-1, 1))) * wobble
        pts.append(p)
    return pts


def wire(name, p1, p2, sag, r, material, parent, n=6, bulge=(0, 0, 0), wobble=0.0):
    tube(name, curve_pts(p1, p2, sag, n, bulge, wobble), r, material, parent, segs=5)


def guts(name, start, direction, n, r, parent, droop=0.35, material=None):
    p = Vector(start)
    d = Vector(direction).normalized()
    pts = [p.copy()]
    for _ in range(n):
        d = (d + Vector((RNG.uniform(-0.7, 0.7), RNG.uniform(-0.7, 0.7), -droop))).normalized()
        p = p + d * r * 1.7
        pts.append(p.copy())
    tube(name, pts, r, material or M["guts"], parent, segs=7)
    return pts[-1]


def drip(name, loc, length, r, material, parent):
    loc = Vector(loc)
    sphere(name, r, loc - Vector((0, 0, length / 2)), material, parent, (1, 1, length / (2 * r)), 6, 4, True)
    sphere(name + "b", r * 1.25, loc - Vector((0, 0, length * 0.95)), material, parent, segs=6, rings=4, smooth=True)


def meat(name, loc, size, parent, material=None, n=3):
    material = material or M["flesh"]
    root = empty(name, loc, parent)
    for k in range(n):
        off = Vector((RNG.uniform(-1, 1), RNG.uniform(-1, 1), RNG.uniform(-0.5, 0.5))) * size * 0.5
        sc = (RNG.uniform(0.7, 1.2), RNG.uniform(0.7, 1.2), RNG.uniform(0.5, 0.9))
        sphere("%s_%d" % (name, k), size * RNG.uniform(0.5, 0.8), off, material, root, sc, 7, 5, True)
    return root


def pool(name, loc, size, parent, material=None, n=4):
    """Flat irregular puddle lying on the ground."""
    material = material or M["blood"]
    for k in range(n):
        off = Vector((RNG.uniform(-1, 1), RNG.uniform(-1, 1), 0)) * size * 0.5
        cyl("%s_%d" % (name, k), size * RNG.uniform(0.35, 0.6), 0.006, Vector(loc) + off, material, parent, segs=10,
            scale=(RNG.uniform(0.7, 1.3), RNG.uniform(0.7, 1.3), 1))


def smear(name, center, axis, size, parent, material=None, n=4):
    """Splatter on a vertical wall face. axis='x' -> on +X face, 'y' -> on +Y face."""
    material = material or M["blood"]
    c = Vector(center)
    for k in range(n):
        u, v = RNG.uniform(-1, 1) * size * 0.5, RNG.uniform(-1, 1) * size * 0.4
        s = size * RNG.uniform(0.25, 0.45)
        if axis == "x":
            cyl("%s_%d" % (name, k), s, 0.01, c + Vector((0, u, v)), material, parent, rot=(0, PI / 2, 0), segs=9,
                scale=(RNG.uniform(0.6, 1.4), RNG.uniform(0.6, 1.3), 1))
        else:
            cyl("%s_%d" % (name, k), s, 0.01, c + Vector((u, 0, v)), material, parent, rot=(PI / 2, 0, 0), segs=9,
                scale=(RNG.uniform(0.6, 1.3), RNG.uniform(0.6, 1.4), 1))
    # run-down drips
    for k in range(2):
        u = RNG.uniform(-1, 1) * size * 0.4
        ln = RNG.uniform(0.1, 0.25)
        p = c + (Vector((0, u, -0.02)) if axis == "x" else Vector((u, 0, -0.02)))
        drip("%s_d%d" % (name, k), p, ln, 0.018, material, parent)


def skull_prop(name, loc, parent, scale=1.0, yaw=0.0, material=None, bloody=False):
    material = material or M["bone"]
    s = empty(name, loc, parent, (0, 0, yaw))
    s.scale = (scale, scale, scale)
    sphere(name + "_c", 0.1, (0, 0, 0.09), material, s, (1.1, 0.9, 0.95), 8, 6, True)
    box(name + "_j", (0.09, 0.1, 0.04), (0.05, 0, 0.02), material, s)
    for k in range(4):
        box(name + "_t%d" % k, (0.012, 0.015, 0.02), (0.095, -0.03 + k * 0.02, 0.045), M["tooth"], s)
    sphere(name + "_e1", 0.025, (0.1, 0.035, 0.09), M["black"], s)
    sphere(name + "_e2", 0.025, (0.1, -0.035, 0.09), M["black"], s)
    box(name + "_n", (0.01, 0.015, 0.025), (0.108, 0, 0.065), M["black"], s)
    if bloody:
        drip(name + "_bd", (0.1, 0.035, 0.075), 0.06, 0.01, M["blood"], s)
    return s


def bone_prop(name, p1, p2, parent, r=0.018, material=None):
    material = material or M["bone"]
    bone(name, p1, p2, r, material, parent)
    for tag, p in (("_a", p1), ("_b", p2)):
        p = Vector(p)
        d = (Vector(p2) - Vector(p1)).normalized()
        side = d.cross(Vector((0, 0, 1))).normalized() * r * 0.9
        sphere(name + tag + "1", r * 1.6, p + side, material, parent, segs=6, rings=4, smooth=True)
        sphere(name + tag + "2", r * 1.6, p - side, material, parent, segs=6, rings=4, smooth=True)


def ribcage(name, loc, parent, scale=1.0, material=None, broken=False):
    material = material or M["bone"]
    rc = empty(name, loc, parent)
    rc.scale = (scale, scale, scale)
    bone(name + "_sp", (-0.1, 0, 0), (-0.1, 0, 0.32), 0.022, material, rc)
    for k in range(4):
        z = 0.06 + k * 0.07
        r = 0.11 + 0.02 * math.sin(k * 0.9)
        for s in (1, -1):
            if broken and RNG.random() < 0.3:
                continue
            pts = [Vector((-0.1 + 0.1 * (1 - math.cos(a)) * 1.0, s * r * math.sin(a), z - 0.03 * math.sin(a)))
                   for a in (0.0, 0.8, 1.6, 2.3)]
            tube(name + "_r%d%d" % (k, s), pts, 0.012, material, rc, segs=5)
    return rc


def bolts(name, center, axis, spread, parent, n=4):
    c = Vector(center)
    for k in range(n):
        a = k / n * 2 * PI + 0.785
        off = Vector((0, math.cos(a), math.sin(a))) if axis == "x" else (
            Vector((math.cos(a), 0, math.sin(a))) if axis == "y" else Vector((math.cos(a), math.sin(a), 0)))
        sphere("%s%d" % (name, k), 0.014, c + off * spread, M["chrome"], parent, segs=6, rings=4)


# ================================================================ CHARACTERS
# Every builder returns (root, pose_fn). Models face +X; root is rotated for directions.

def build_player_legs():
    root = empty("pl_root")
    box("pelvis", (0.2, 0.32, 0.12), (0, 0, 0.8), M["darkmetal"], root)
    box("belt", (0.23, 0.36, 0.045), (0, 0, 0.86), M["armor"], root)
    sphere("buckle", 0.045, (0.12, 0, 0.84), M["glow_cyan"], root)
    for s in (1, -1):
        box("pouch%d" % s, (0.1, 0.06, 0.09), (0.0, s * 0.2, 0.82), M["darkmetal"], root)
        bolts("pbolt%d" % s, (0.0, s * 0.231, 0.82), "y", 0.03, root, 2)
    for k in range(3):  # tail bone vertebrae
        sphere("coccyx%d" % k, 0.025 - k * 0.005, (-0.11 - k * 0.03, 0, 0.77 - k * 0.04), M["bone"], root, segs=6, rings=4)
    wire("pwire", (-0.1, 0.12, 0.84), (-0.1, -0.12, 0.84), 0.06, 0.012, M["wire_yellow"], root, 5)
    J = {}
    for side, y in (("L", 0.12), ("R", -0.12)):
        hip = empty("hip" + side, (0, y, 0.76), root)
        sphere("hipball" + side, 0.065, (0, 0, 0), M["chrome"], hip)
        bone("thigh" + side, (0, 0, 0), (0, 0, -0.34), 0.04, M["bone"], hip)
        box("thighplate" + side, (0.07, 0.11, 0.2), (0.05, 0, -0.15), M["armor"], hip)
        bolts("tb" + side, (0.086, 0, -0.15), "x", 0.045, hip, 4)
        wire("hose" + side, (-0.05, 0, -0.04), (-0.05, 0, -0.32), 0.0, 0.016, M["rubber"], hip, 5, bulge=(-0.05, 0, 0))
        wire("tw" + side, (0.02, 0.05, -0.04), (0.02, 0.05, -0.3), 0.0, 0.008, M["wire_red"], hip, 4, bulge=(0, 0.03, 0))
        knee = empty("knee" + side, (0, 0, -0.36), hip)
        sphere("kneeball" + side, 0.055, (0, 0, 0), M["chrome"], knee)
        box("kneecap" + side, (0.05, 0.09, 0.08), (0.055, 0, 0), M["darkmetal"], knee)
        spike("kspike" + side, (0.07, 0, 0.01), (0.13, 0, 0.05), 0.02, M["chrome"], knee)
        bone("shin" + side, (0, 0, 0), (0, 0, -0.32), 0.035, M["bone"], knee)
        bone("fibula" + side, (-0.02, 0.03, -0.03), (-0.02, 0.03, -0.29), 0.015, M["bone"], knee)
        bone("piston" + side, (-0.05, 0, -0.04), (-0.04, 0, -0.28), 0.018, M["chrome"], knee)
        wire("shose" + side, (0.03, -0.03, -0.03), (0.03, -0.03, -0.3), 0.0, 0.012, M["rubber"], knee, 4, bulge=(0.03, 0, 0))
        ankle = empty("ankle" + side, (0, 0, -0.33), knee)
        box("foot" + side, (0.16, 0.11, 0.06), (0.02, 0, -0.035), M["darkmetal"], ankle)
        for k, yy in enumerate((-0.035, 0, 0.035)):
            bone("toe%s%d" % (side, k), (0.09, yy, -0.04), (0.16, yy * 1.2, -0.05), 0.016, M["bone"], ankle)
            spike("claw%s%d" % (side, k), (0.16, yy * 1.2, -0.05), (0.21, yy * 1.3, -0.07), 0.014, M["chrome"], ankle)
        spike("heel" + side, (-0.05, 0, -0.04), (-0.11, 0, -0.06), 0.02, M["chrome"], ankle)
        J[side] = (hip, knee, ankle)

    def pose(anim, t):
        for side, off in (("L", 0.0), ("R", 0.5)):
            hip, knee, ankle = J[side]
            if anim == "idle":
                hip.rotation_euler.y = knee.rotation_euler.y = ankle.rotation_euler.y = 0
                continue
            ph = 2 * PI * (t + off)
            swing = math.sin(ph) * 0.55
            bend = 0.08 + 0.8 * max(0.0, math.cos(ph))
            hip.rotation_euler.y = -swing
            knee.rotation_euler.y = bend
            ankle.rotation_euler.y = (swing - bend) * 0.8
    return root, pose


GZ = 1.13
EXTRA_META = {}


def build_torso_body(root):
    for i in range(5):
        cyl("vert%d" % i, 0.05, 0.04, (0, 0, 0.885 + i * 0.05), M["bone"], root, r2=0.042)
        spike("vspine%d" % i, (-0.04, 0, 0.885 + i * 0.05), (-0.08, 0, 0.87 + i * 0.05), 0.018, M["bone"], root)
    wire("spcable", (-0.06, 0.03, 0.86), (-0.06, 0.03, 1.25), 0.0, 0.014, M["rubber"], root, 5, bulge=(-0.02, 0, 0))
    box("pack", (0.14, 0.28, 0.3), (-0.18, 0, 1.15), M["darkmetal"], root)
    sphere("core", 0.075, (-0.26, 0, 1.15), M["glow_cyan"], root)
    ring("coreguard", 0.08, 0.05, (-0.26, 0, 1.15), M["chrome"], root, rot=(0, PI / 2, 0))
    for k in range(3):
        box("fin%d" % k, (0.06, 0.3, 0.012), (-0.27, 0, 1.03 + k * 0.035), M["steel2"], root)
    bolts("packbolt", (-0.251, 0, 1.15), "x", 0.12, root, 4)
    bone("exL", (-0.2, 0.1, 1.25), (-0.23, 0.1, 1.44), 0.03, M["chrome"], root)
    bone("exR", (-0.2, -0.1, 1.25), (-0.23, -0.1, 1.44), 0.03, M["chrome"], root)
    sphere("exLt", 0.02, (-0.23, 0.1, 1.45), M["glow_orange"], root)
    sphere("exRt", 0.02, (-0.23, -0.1, 1.45), M["glow_orange"], root)
    for i, (z, r) in enumerate(((1.05, 0.12), (1.12, 0.145), (1.19, 0.155), (1.26, 0.145))):
        ring("rib%d" % i, r, 0.03, (0.02, 0, z), M["bone"], root, scale=(1, 1.35, 1))
    sphere("heart", 0.058, (0.03, 0.02, 1.15), M["glow_red"], root, (1, 0.9, 1.1), 8, 6, True)
    wire("hvein1", (0.03, 0.05, 1.18), (-0.13, 0.08, 1.2), 0.03, 0.013, M["wire_red"], root, 4)
    wire("hvein2", (0.03, -0.02, 1.12), (-0.13, -0.08, 1.08), 0.02, 0.013, M["rubber"], root, 4)
    box("sternum", (0.04, 0.06, 0.24), (0.17, 0, 1.16), M["chrome"], root)
    bolts("stb", (0.191, 0, 1.16), "x", 0.03, root, 2)
    box("clavicle", (0.05, 0.46, 0.04), (0.02, 0, 1.31), M["bone"], root)
    for side, y in (("L", 0.22), ("R", -0.22)):
        box("pad" + side, (0.19, 0.13, 0.09), (0, y, 1.34), M["armor"], root)
        bolts("padb" + side, (0, y, 1.386), "z", 0.06, root, 4)
        spike("padspike" + side, (-0.03, y * 1.1, 1.38), (-0.06, y * 1.3, 1.48), 0.025, M["chrome"], root)
        sphere("sh" + side, 0.06, (0, y, 1.28), M["chrome"], root)
    bone("neck", (0, 0, 1.32), (0.01, 0, 1.42), 0.035, M["chrome"], root)
    for s in (1, -1):
        wire("neckw%d" % s, (-0.05, s * 0.04, 1.46), (-0.08, s * 0.13, 1.33), 0.0, 0.009,
             M["wire_red" if s > 0 else "wire_yellow"], root, 4, bulge=(-0.04, 0, 0))
    sphere("skull", 0.13, (0.03, 0, 1.52), M["bone"], root, (1.1, 0.9, 0.95), 10, 8, True)
    box("jaw", (0.13, 0.15, 0.05), (0.09, 0, 1.415), M["bone"], root)
    for k in range(6):
        box("tooth%d" % k, (0.015, 0.018, 0.028), (0.155, -0.05 + k * 0.02, 1.447), M["tooth"], root)
    box("sockets", (0.03, 0.19, 0.05), (0.155, 0, 1.53), M["black"], root)
    box("nose", (0.02, 0.025, 0.035), (0.165, 0, 1.49), M["black"], root)
    box("crack1", (0.005, 0.006, 0.08), (0.12, 0.09, 1.57), M["black"], root, (0.4, 0, 0))
    sphere("eyeL", 0.03, (0.168, 0.05, 1.53), M["glow_red"], root)
    sphere("eyeR", 0.03, (0.168, -0.05, 1.53), M["glow_red"], root)
    ring("lensR", 0.042, 0.03, (0.175, -0.05, 1.53), M["chrome"], root, rot=(0, PI / 2, 0))
    box("cranium", (0.2, 0.21, 0.05), (-0.01, 0, 1.63), M["chrome"], root)
    bolts("cranb", (-0.01, 0, 1.656), "z", 0.08, root, 4)
    bone("antenna", (-0.06, 0.07, 1.64), (-0.1, 0.09, 1.84), 0.008, M["chrome"], root)
    sphere("antip", 0.02, (-0.1, 0.09, 1.84), M["glow_red"], root)


def arm_to(side, sh, hand, sgn, root):
    sh, hand = Vector(sh), Vector(hand)
    el = (sh + hand) / 2 + Vector((-0.04, 0.06 * sgn, -0.13))
    bone("upper" + side, sh, el, 0.03, M["bone"], root)
    sphere("elbow" + side, 0.04, el, M["chrome"], root)
    bone("fore" + side, el, hand, 0.027, M["bone"], root)
    bone("fore2" + side, el + Vector((0, 0, -0.02)), hand + Vector((0, 0, -0.02)), 0.012, M["bone"], root)
    wire("armw" + side, sh, el, 0.0, 0.009, M["wire_red"], root, 4, bulge=(0, 0, 0.03))
    box("hand" + side, (0.06, 0.06, 0.06), hand, M["chrome"], root)


def g_grip(p, x, z, mat_="darkmetal"):
    box("grip%.2f" % x, (0.05, 0.05, 0.12), (x, 0, z - 0.08), M[mat_], p, (0, -0.25, 0))


# ---- gun archetypes: each builds in torso space (barrel along +X) and returns hand/muzzle info
def gun_pistol(p, on_body):
    z = GZ + 0.02
    box("slide", (0.22, 0.05, 0.06), (0.52, 0, z + 0.03), M["steel2"], p)
    box("frame", (0.2, 0.045, 0.04), (0.51, 0, z - 0.015), M["darkmetal"], p)
    bone("pbarrel", (0.62, 0, z + 0.03), (0.66, 0, z + 0.03), 0.016, M["chrome"], p)
    g_grip(p, 0.44, z)
    sphere("psight", 0.012, (0.62, 0, z + 0.065), M["glow_red"], p)
    bolts("pb", (0.52, 0.026, z + 0.03), "y", 0.02, p, 2)
    return dict(muzzle=(0.67, z + 0.03), grip=(0.43, -0.03, z - 0.08), fore=(0.46, 0.04, z - 0.06), rear=(0.41, z))


def gun_revolver(p, on_body):
    z = GZ + 0.03
    box("rframe", (0.16, 0.05, 0.07), (0.5, 0, z), M["chrome"], p)
    cyl("rcyl", 0.048, 0.08, (0.5, 0, z), M["steel2"], p, rot=(0, PI / 2, 0), segs=6)
    for k in range(6):
        a = k * PI / 3
        cyl("rch%d" % k, 0.012, 0.01, (0.545, math.cos(a) * 0.028, z + math.sin(a) * 0.028), M["black"], p, rot=(0, PI / 2, 0), segs=6)
    bone("rbarrel", (0.56, 0, z + 0.025), (0.78, 0, z + 0.025), 0.022, M["chrome"], p)
    box("rrib", (0.22, 0.015, 0.015), (0.67, 0, z + 0.05), M["darkmetal"], p)
    box("rhammer", (0.03, 0.02, 0.04), (0.43, 0, z + 0.04), M["darkmetal"], p)
    g_grip(p, 0.42, z, "crate")
    return dict(muzzle=(0.79, z + 0.025), grip=(0.41, -0.03, z - 0.08), fore=(0.44, 0.04, z - 0.06), rear=(0.4, z))


def gun_smg(p, on_body):
    z = GZ
    box("srec", (0.3, 0.07, 0.1), (0.47, 0, z), M["darkmetal"], p)
    box("srail", (0.26, 0.03, 0.02), (0.47, 0, z + 0.06), M["steel2"], p)
    cyl("ssup", 0.032, 0.18, (0.71, 0, z + 0.01), M["darkmetal"], p, rot=(0, PI / 2, 0), segs=10)
    box("smag", (0.05, 0.04, 0.2), (0.55, 0, z - 0.14), M["steel2"], p, (0, 0.15, 0))
    g_grip(p, 0.4, z)
    bone("sst1", (0.32, 0, z + 0.02), (0.16, 0, z), 0.01, M["chrome"], p)
    bone("sst2", (0.32, 0, z - 0.04), (0.16, 0, z - 0.05), 0.01, M["chrome"], p)
    box("sbutt", (0.02, 0.05, 0.1), (0.15, 0, z - 0.02), M["darkmetal"], p)
    box("sglow", (0.1, 0.072, 0.015), (0.47, 0, z - 0.02), M["glow_yellow"], p)
    return dict(muzzle=(0.8, z + 0.01), grip=(0.4, -0.03, z - 0.09), fore=(0.55, 0.05, z - 0.13), rear=(0.32, z))


def gun_shotgun(p, on_body):
    z = GZ + 0.01
    box("grec", (0.26, 0.08, 0.11), (0.42, 0, z), M["darkmetal"], p)
    bone("gbar", (0.55, 0, z + 0.03), (0.98, 0, z + 0.03), 0.03, M["steel2"], p)
    bone("gtube", (0.55, 0, z - 0.025), (0.88, 0, z - 0.025), 0.022, M["darkmetal"], p)
    box("gpump", (0.16, 0.075, 0.075), (0.72, 0, z - 0.02), M["crate"], p)
    for k in range(4):
        box("gring%d" % k, (0.012, 0.078, 0.078), (0.66 + k * 0.04, 0, z - 0.02), M["black"], p)
    box("gstock", (0.24, 0.06, 0.1), (0.2, 0, z - 0.03), M["crate"], p, (0, 0.12, 0))
    sphere("gbead", 0.01, (0.97, 0, z + 0.065), M["chrome"], p)
    for k in range(4):
        box("gshell%d" % k, (0.03, 0.012, 0.014), (0.36 + 0.04 * k, 0.046, z), M["armor"], p)
    return dict(muzzle=(0.99, z + 0.03), grip=(0.33, -0.03, z - 0.07), fore=(0.72, 0.05, z - 0.05), rear=(0.3, z))


def gun_carbine(p, on_body):
    gz = GZ
    box("gunbody", (0.42, 0.1, 0.13), (0.42, 0, gz), M["darkmetal"], p)
    box("gunshroud", (0.32, 0.12, 0.06), (0.5, 0, gz + 0.085), M["armor"], p)
    bone("barrel", (0.62, 0, gz + 0.01), (1.0, 0, gz + 0.01), 0.035, M["chrome"], p)
    for k in range(3):
        ring("cool%d" % k, 0.048, 0.025, (0.68 + k * 0.07, 0, gz + 0.01), M["darkmetal"], p, rot=(0, PI / 2, 0))
    ring("muzzle", 0.05, 0.05, (0.98, 0, gz + 0.01), M["glow_cyan"], p, rot=(0, PI / 2, 0))
    bone("scope", (0.36, 0, gz + 0.14), (0.52, 0, gz + 0.14), 0.022, M["darkmetal"], p)
    sphere("scopelens", 0.018, (0.525, 0, gz + 0.14), M["glow_red"], p)
    box("cell", (0.13, 0.04, 0.06), (0.36, 0.07, gz), M["glow_green"], p)
    box("stock", (0.14, 0.08, 0.1), (0.15, 0, gz - 0.02), M["darkmetal"], p)
    box("grip", (0.05, 0.06, 0.12), (0.32, 0, gz - 0.1), M["darkmetal"], p)
    return dict(muzzle=(1.01, gz + 0.01), grip=(0.31, -0.06, gz - 0.07), fore=(0.56, 0.07, gz - 0.03), rear=(0.28, gz))


def gun_assault(p, on_body):
    z = GZ
    box("arec", (0.36, 0.08, 0.12), (0.45, 0, z), M["darkmetal"], p)
    box("aupper", (0.3, 0.07, 0.04), (0.45, 0, z + 0.08), M["steel2"], p)
    box("ahand", (0.26, 0.085, 0.09), (0.76, 0, z + 0.01), M["steel2"], p)
    for k in range(4):
        box("avent%d" % k, (0.03, 0.088, 0.02), (0.68 + k * 0.05, 0, z + 0.03), M["black"], p)
    bone("abar", (0.89, 0, z + 0.02), (1.05, 0, z + 0.02), 0.02, M["chrome"], p)
    box("abrake", (0.05, 0.05, 0.05), (1.06, 0, z + 0.02), M["darkmetal"], p)
    box("amag1", (0.06, 0.045, 0.1), (0.56, 0, z - 0.1), M["armor"], p, (0, 0.25, 0))
    box("amag2", (0.06, 0.045, 0.1), (0.6, 0, z - 0.18), M["armor"], p, (0, 0.5, 0))
    box("asight", (0.08, 0.05, 0.06), (0.45, 0, z + 0.13), M["darkmetal"], p)
    sphere("alens", 0.016, (0.49, 0, z + 0.13), M["glow_red"], p)
    box("astock", (0.22, 0.06, 0.11), (0.18, 0, z - 0.01), M["darkmetal"], p)
    g_grip(p, 0.36, z)
    return dict(muzzle=(1.09, z + 0.02), grip=(0.36, -0.03, z - 0.09), fore=(0.74, 0.06, z - 0.05), rear=(0.27, z))


def gun_sniper(p, on_body):
    z = GZ + 0.01
    box("nrec", (0.34, 0.07, 0.1), (0.42, 0, z), M["darkmetal"], p)
    bone("nbar", (0.59, 0, z + 0.02), (1.3, 0, z + 0.02), 0.022, M["darkmetal"], p, r2=0.018)
    box("nbrake", (0.07, 0.06, 0.05), (1.32, 0, z + 0.02), M["steel2"], p)
    bone("nscope", (0.3, 0, z + 0.12), (0.6, 0, z + 0.12), 0.035, M["darkmetal"], p)
    for x in (0.3, 0.6):
        ring("nsr%.1f" % x, 0.045, 0.04, (x, 0, z + 0.12), M["steel2"], p, rot=(0, PI / 2, 0))
        box("nmount%.1f" % x, (0.03, 0.03, 0.07), (x + 0.03, 0, z + 0.07), M["darkmetal"], p)
    sphere("nlens", 0.03, (0.62, 0, z + 0.12), M["glow_red"], p)
    bone("nbolt", (0.4, 0.04, z + 0.02), (0.4, 0.11, z - 0.02), 0.01, M["chrome"], p)
    sphere("nboltk", 0.02, (0.4, 0.11, z - 0.02), M["chrome"], p)
    box("nstock", (0.26, 0.06, 0.12), (0.16, 0, z - 0.02), M["bone"], p)
    box("ncheek", (0.12, 0.065, 0.04), (0.2, 0, z + 0.06), M["bone_dirty"], p)
    for s in (1, -1):
        bone("nbipod%d" % s, (0.9, 0, z - 0.01), (1.12, s * 0.02, z - 0.03), 0.008, M["chrome"], p)
    g_grip(p, 0.32, z)
    return dict(muzzle=(1.35, z + 0.02), grip=(0.32, -0.03, z - 0.09), fore=(0.64, 0.05, z - 0.04), rear=(0.28, z))


def gun_grenade(p, on_body):
    z = GZ
    cyl("ldrum", 0.1, 0.16, (0.48, 0, z), M["darkmetal"], p, rot=(0, PI / 2, 0), segs=8)
    ring("lband", 0.103, 0.04, (0.48, 0, z), M["hazard"], p, rot=(0, PI / 2, 0), segs=8)
    for k in range(6):
        a = k * PI / 3
        cyl("lhole%d" % k, 0.024, 0.01, (0.565, math.cos(a) * 0.062, z + math.sin(a) * 0.062), M["black"], p, rot=(0, PI / 2, 0))
    bone("lbar", (0.56, 0, z + 0.04), (0.86, 0, z + 0.04), 0.05, M["steel2"], p)
    ring("lmouth", 0.056, 0.04, (0.85, 0, z + 0.04), M["hazard"], p, rot=(0, PI / 2, 0))
    box("ltop", (0.4, 0.05, 0.04), (0.6, 0, z + 0.11), M["darkmetal"], p)
    bone("lst1", (0.38, 0, z + 0.03), (0.17, 0, z + 0.01), 0.012, M["chrome"], p)
    box("lbutt", (0.03, 0.06, 0.12), (0.16, 0, z - 0.02), M["darkmetal"], p)
    g_grip(p, 0.37, z)
    return dict(muzzle=(0.87, z + 0.04), grip=(0.37, -0.03, z - 0.09), fore=(0.66, 0.06, z - 0.03), rear=(0.32, z))


def gun_rocket(p, on_body):
    zr, y = 1.33, (-0.14 if on_body else 0.0)
    cyl("rtube", 0.075, 1.05, (0.22, y, zr), M["darkmetal"], p, rot=(0, PI / 2, 0), segs=12)
    for x in (-0.22, 0.25, 0.66):
        ring("rband%.2f" % x, 0.079, 0.05, (x, y, zr), M["hazard"], p, rot=(0, PI / 2, 0), segs=12)
    cyl("rhead", 0.062, 0.14, (0.8, y, zr), M["armor"], p, rot=(0, PI / 2, 0), r2=0.005, segs=10)
    ring("rexh", 0.07, 0.05, (-0.29, y, zr), M["glow_orange"], p, rot=(0, PI / 2, 0), segs=12)
    box("rsight", (0.08, 0.04, 0.06), (0.3, y + 0.09, zr + 0.05), M["darkmetal"], p)
    sphere("rlens", 0.015, (0.34, y + 0.09, zr + 0.05), M["glow_red"], p)
    box("rgrip", (0.05, 0.05, 0.13), (0.32, y, zr - 0.12), M["darkmetal"], p)
    box("rfore", (0.05, 0.05, 0.1), (0.52, y, zr - 0.11), M["darkmetal"], p)
    return dict(muzzle=(0.88, zr), grip=(0.32, y, zr - 0.15), fore=(0.52, y + 0.02, zr - 0.13), rear=(0.05, zr - 0.05))


def gun_laser_pistol(p, on_body):
    z = GZ + 0.02
    box("lpbody", (0.2, 0.05, 0.07), (0.5, 0, z + 0.02), M["chrome"], p)
    g_grip(p, 0.43, z)
    for k in range(3):
        ring("lpcoil%d" % k, 0.03, 0.015, (0.61 + 0.03 * k, 0, z + 0.03), M["glow_red"], p, rot=(0, PI / 2, 0))
    bone("lpemit", (0.6, 0, z + 0.03), (0.71, 0, z + 0.03), 0.012, M["darkmetal"], p)
    sphere("lptip", 0.018, (0.72, 0, z + 0.03), M["glow_red"], p)
    for s in (1, -1):
        box("lpfin%d" % s, (0.12, 0.005, 0.05), (0.5, s * 0.03, z + 0.07), M["darkmetal"], p)
    return dict(muzzle=(0.73, z + 0.03), grip=(0.43, -0.03, z - 0.08), fore=(0.46, 0.04, z - 0.06), rear=(0.4, z))


def gun_laser_rifle(p, on_body):
    z = GZ
    box("lrbody", (0.4, 0.08, 0.11), (0.5, 0, z), M["chrome"], p)
    box("lrtop", (0.36, 0.09, 0.04), (0.5, 0, z + 0.07), M["darkmetal"], p)
    bone("lrtube", (0.7, 0, z + 0.01), (1.05, 0, z + 0.01), 0.025, M["darkmetal"], p)
    for k in range(4):
        ring("lrcoil%d" % k, 0.042, 0.02, (0.76 + k * 0.08, 0, z + 0.01), M["glow_red"], p, rot=(0, PI / 2, 0))
    sphere("lrprism", 0.032, (1.08, 0, z + 0.01), M["glow_red"], p, segs=6, rings=4)
    box("lrbatt", (0.16, 0.02, 0.05), (0.5, 0.05, z), M["glow_red"], p)
    box("lrstock", (0.2, 0.06, 0.1), (0.2, 0, z - 0.01), M["darkmetal"], p)
    g_grip(p, 0.36, z)
    return dict(muzzle=(1.1, z + 0.01), grip=(0.36, -0.03, z - 0.09), fore=(0.66, 0.06, z - 0.05), rear=(0.28, z))


def gun_plasma(p, on_body):
    z = GZ
    box("plbody", (0.36, 0.11, 0.13), (0.46, 0, z), M["darkmetal"], p)
    sphere("plglass", 0.075, (0.6, 0, z + 0.09), M["glass"], p, segs=10, rings=7, smooth=True)
    sphere("plcore", 0.048, (0.6, 0, z + 0.09), M["glow_green"], p, segs=8, rings=6, smooth=True)
    for k in range(3):
        a = k * 2 * PI / 3
        spike("plprong%d" % k, (0.66, math.cos(a) * 0.045, z + math.sin(a) * 0.045),
              (0.97, math.cos(a) * 0.065, z + math.sin(a) * 0.065), 0.018, M["chrome"], p)
    sphere("plmuz", 0.032, (0.8, 0, z), M["glow_green"], p)
    wire("plhose", (0.4, 0.06, z + 0.05), (0.58, 0.05, z + 0.12), 0.0, 0.012, M["wire_yellow"], p, 4, bulge=(0, 0.04, 0.04))
    box("plstock", (0.16, 0.07, 0.1), (0.2, 0, z - 0.01), M["darkmetal"], p)
    g_grip(p, 0.37, z)
    return dict(muzzle=(0.98, z), grip=(0.37, -0.03, z - 0.09), fore=(0.62, 0.07, z - 0.05), rear=(0.3, z))


def gun_flamer(p, on_body):
    z = GZ - 0.01
    box("fbody", (0.3, 0.08, 0.11), (0.45, 0, z), M["rust"], p)
    bone("fnoz", (0.6, 0, z + 0.02), (0.98, 0, z + 0.02), 0.03, M["darkmetal"], p)
    for k in range(4):
        ring("fshield%d" % k, 0.042, 0.03, (0.66 + k * 0.08, 0, z + 0.02), M["rust2"], p, rot=(0, PI / 2, 0))
    bone("fign", (0.6, 0, z - 0.03), (0.97, 0, z - 0.03), 0.01, M["chrome"], p)
    sphere("fpilot", 0.02, (0.99, 0, z - 0.03), M["glow_orange"], p)
    box("fhandle", (0.04, 0.04, 0.1), (0.72, 0, z - 0.07), M["darkmetal"], p)
    g_grip(p, 0.38, z)
    if on_body:
        for s in (1, -1):
            cyl("ftank%d" % s, 0.055, 0.34, (-0.3, s * 0.075, 1.12), M["hazard"], p, segs=10)
            cyl("ftcap%d" % s, 0.04, 0.04, (-0.3, s * 0.075, 1.31), M["darkmetal"], p, segs=8)
        wire("fhose", (-0.28, 0.07, 0.95), (0.4, 0.04, z - 0.05), 0.15, 0.022, M["rubber"], p, 8)
    else:
        cyl("ftank", 0.05, 0.25, (0.45, 0.0, z - 0.1), M["hazard"], p, rot=(0, PI / 2, 0), segs=10)
    return dict(muzzle=(1.0, z + 0.02), grip=(0.38, -0.03, z - 0.09), fore=(0.72, 0.05, z - 0.1), rear=(0.3, z))


GUNS = {
    "pistol": gun_pistol, "revolver": gun_revolver, "smg": gun_smg, "shotgun": gun_shotgun,
    "carbine": gun_carbine, "assault": gun_assault, "sniper": gun_sniper, "grenade": gun_grenade,
    "rocket": gun_rocket, "laser_pistol": gun_laser_pistol, "laser_rifle": gun_laser_rifle,
    "plasma": gun_plasma, "flamer": gun_flamer,
}


def torso_builder(arch):
    def build():
        root = empty("pt_root")
        build_torso_body(root)
        info = GUNS[arch](root, True)
        arm_to("R", (0, -0.22, 1.28), info["grip"], -1, root)
        arm_to("L", (0, 0.22, 1.28), info["fore"], 1, root)
        rx, rz = info["rear"]
        wire("feed1", (-0.12, -0.13, 1.03), (rx, -0.045, rz - 0.03), 0.14, 0.02, M["rubber"], root, 7)
        wire("feed2", (-0.12, 0.13, 1.06), (rx + 0.06, 0.05, rz), 0.1, 0.011, M["wire_yellow"], root, 6)
        EXTRA_META["muzzle"] = list(info["muzzle"])
        return root, lambda anim, t: None
    return build


def gunpickup_builder(arch):
    def build():
        r = tile_root()
        spin = empty("gspin", (0, 0, 0.32), r)
        holder = empty("gholder", (0, 0, 0), spin)
        info = GUNS[arch](holder, False)
        mx, rx = info["muzzle"][0], info["rear"][0]
        holder.location = (-(mx + rx) / 2, 0, -info["muzzle"][1])

        def pose(anim, t):
            spin.rotation_euler = (0.25, 0, 2 * PI * t)
        return r, pose
    return build


def build_zombie():
    root = empty("z_root")
    body = empty("z_body", (0, 0, 0), root)
    box("pants", (0.2, 0.3, 0.16), (0, 0, 0.78), M["zcloth"], body)
    box("belt", (0.21, 0.31, 0.03), (0, 0, 0.84), M["rust2"], body)
    J = {}
    for side, y in (("L", 0.1), ("R", -0.1)):
        hip = empty("zhip" + side, (0, y, 0.74), root)
        bone("zthigh" + side, (0, 0, 0), (0, 0, -0.36), 0.065, M["zcloth"], hip, r2=0.055)
        knee = empty("zknee" + side, (0, 0, -0.36), hip)
        if side == "L":   # stripped shin: exposed bone + tatters
            bone("zshinb" + side, (0, 0, 0), (0, 0, -0.32), 0.025, M["bone_dirty"], knee)
            sphere("zkneecap", 0.04, (0.03, 0, 0), M["bone_dirty"], knee)
            for k in range(3):
                meat("zshred%d" % k, (RNG.uniform(-0.02, 0.02), RNG.uniform(-0.02, 0.02), -0.06 - k * 0.09), 0.05, knee, M["flesh"], 2)
            drip("zlegdrip", (0.0, 0.02, -0.12), 0.08, 0.012, M["blood"], knee)
        else:
            bone("zshin" + side, (0, 0, 0), (0, 0, -0.32), 0.045, M["zskin"], knee, r2=0.035)
        ankle = empty("zank" + side, (0, 0, -0.33), knee)
        box("zfoot" + side, (0.18, 0.09, 0.06), (0.04, 0, -0.03), M["zskin2"], ankle)
        J[side] = (hip, knee, ankle)
    torso = empty("z_torso", (0, 0, 0.82), body, (0, 0.45, 0))
    box("zchest", (0.22, 0.34, 0.36), (0, 0, 0.2), M["zskin"], torso)
    box("zshirt", (0.235, 0.355, 0.2), (0, 0, 0.1), M["zcloth"], torso)
    # belly wound with guts spilling out
    box("zcavity", (0.03, 0.16, 0.12), (0.11, 0.02, 0.08), M["blood"], torso)
    guts("zgut1", (0.12, 0.04, 0.08), (1, 0.2, -0.6), 9, 0.032, torso)
    guts("zgut2", (0.12, -0.02, 0.1), (1, -0.4, -0.3), 6, 0.026, torso)
    smear("zshirtblood", (0.12, 0.0, 0.0), "x", 0.2, torso, n=3)
    # exposed ribs over a dark cavity
    box("zribhole", (0.17, 0.02, 0.2), (0.0, 0.171, 0.24), M["blood"], torso)
    for i in range(4):
        bone("zrib%d" % i, (0.07, 0.178, 0.16 + i * 0.05), (-0.07, 0.178, 0.17 + i * 0.05), 0.013, M["bone"], torso)
    box("zspine", (0.05, 0.06, 0.3), (-0.11, 0, 0.22), M["bone"], torso)
    for k in range(3):
        spike("zspur%d" % k, (-0.12, RNG.uniform(-0.06, 0.06), 0.12 + k * 0.1), (-0.22, RNG.uniform(-0.1, 0.1), 0.18 + k * 0.1),
              0.025, M["bone_dirty"], torso)
    # mutant implants: tubes into the skull, glowing vial on the back
    box("zvial", (0.06, 0.1, 0.16), (-0.15, 0.08, 0.3), M["glow_green"], torso)
    box("zvialcage", (0.07, 0.11, 0.03), (-0.15, 0.08, 0.38), M["rust"], torso)
    wire("ztube1", (-0.15, 0.08, 0.38), (-0.06, 0.05, 0.56), 0.0, 0.016, M["rubber"], torso, 5, bulge=(-0.08, 0, 0))
    wire("ztube2", (-0.15, -0.02, 0.33), (-0.05, -0.05, 0.53), 0.0, 0.012, M["rust"], torso, 5, bulge=(-0.06, 0, 0))
    head = empty("z_head", (0.05, 0, 0.45), torso, (0, -0.25, 0))
    sphere("zhead", 0.13, (0.02, 0, 0.06), M["zskin"], head, (1.0, 0.9, 1.05), 8, 6, True)
    box("zjaw", (0.1, 0.12, 0.05), (0.08, 0, -0.08), M["zskin2"], head, (0, 0.5, 0))
    for k in range(5):
        box("ztooth%d" % k, (0.012, 0.014, 0.025), (0.125, -0.04 + k * 0.02, -0.035), M["tooth"], head)
    box("zmouth", (0.03, 0.1, 0.04), (0.13, 0, -0.02), M["blood"], head)
    drip("zdrool1", (0.13, 0.02, -0.06), 0.12, 0.012, M["blood"], head)
    drip("zdrool2", (0.12, -0.03, -0.07), 0.07, 0.01, M["blood"], head)
    sphere("zeyeL", 0.025, (0.13, 0.045, 0.08), M["glow_yellow"], head)
    sphere("zsocketR", 0.028, (0.125, -0.045, 0.08), M["black"], head)
    drip("zeyedrip", (0.135, -0.045, 0.06), 0.06, 0.009, M["blood"], head)
    sphere("zbrain", 0.07, (-0.02, 0.05, 0.15), M["brain"], head, (1, 1, 0.8), 8, 6, True)
    for k in range(3):
        bone("zstitch%d" % k, (0.06 - k * 0.04, -0.09, 0.14), (0.06 - k * 0.04, -0.05, 0.17), 0.006, M["black"], head)
    arms = {}
    for side, y in (("L", 0.2), ("R", -0.2)):
        sh = empty("zsh" + side, (0, y, 0.33), torso)
        bone("zup" + side, (0, 0, 0), (0.25, 0, -0.02), 0.045, M["zskin"], sh)
        if side == "R":   # flesh stripped forearm, bones showing
            bone("zfo1" + side, (0.25, 0.01, -0.02), (0.48, 0.01, 0.0), 0.014, M["bone"], sh)
            bone("zfo2" + side, (0.25, -0.02, -0.02), (0.48, -0.015, 0.0), 0.012, M["bone"], sh)
            meat("zarmmeat", (0.29, 0, -0.02), 0.06, sh, M["flesh"], 3)
            drip("zarmdrip", (0.3, 0, -0.05), 0.09, 0.012, M["blood"], sh)
            for k in range(3):
                spike("zfinger%d" % k, (0.5, -0.02 + k * 0.02, 0), (0.58, -0.03 + k * 0.03, -0.03), 0.012, M["bone"], sh)
        else:
            bone("zfo" + side, (0.25, 0, -0.02), (0.48, 0, 0.0), 0.038, M["zskin"], sh, r2=0.03)
            sphere("zhand" + side, 0.05, (0.5, 0, 0.0), M["zskin2"], sh)
        arms[side] = sh

    def pose(anim, t):
        ph = 2 * PI * t
        for side, off in (("L", 0.0), ("R", 0.5)):
            hip, knee, ankle = J[side]
            p = ph + off * 2 * PI
            sw = math.sin(p) * 0.38
            bend = 0.1 + 0.5 * max(0.0, math.cos(p))
            hip.rotation_euler.y = -sw
            knee.rotation_euler.y = bend
            ankle.rotation_euler.y = (sw - bend) * 0.8
            arms[side].rotation_euler.y = -0.55 + math.sin(p + 1.0) * 0.18
        body.rotation_euler.x = math.sin(ph) * 0.12
        body.location.z = -abs(math.sin(ph)) * 0.03
        head.rotation_euler.x = math.sin(ph + 0.8) * 0.25
    return root, pose


def build_spider():
    root = empty("s_root")
    root.scale = (1.25, 1.25, 1.25)
    body = empty("s_body", (0, 0, 0), root)
    sphere("ceph", 0.28, (0.12, 0, 0.5), M["chitin"], body, (1.2, 1.0, 0.7), 10, 7, True)
    sphere("abdo", 0.42, (-0.5, 0, 0.66), M["chitin"], body, (1.25, 1.0, 0.9), 12, 8, True)
    # biomechanical tubing along the back
    for s in (1, -1):
        wire("spipe%d" % s, (0.15, s * 0.12, 0.66), (-0.8, s * 0.16, 0.84), 0.0, 0.028, M["rust"], body, 8,
             bulge=(0, s * 0.05, 0.3))
        for k in range(3):
            ring("sclamp%d%d" % (s, k), 0.036, 0.03, curve_pts((0.15, s * 0.12, 0.66), (-0.8, s * 0.16, 0.84), 0, 8,
                 (0, s * 0.05, 0.3))[2 + k * 2], M["darkmetal"], body, rot=(0, PI / 2 - 0.4, 0))
    for i, (x, z, r) in enumerate(((-0.35, 1.0, 0.06), (-0.55, 0.99, 0.075), (-0.75, 0.9, 0.055))):
        sphere("mark%d" % i, r, (x, 0, z), M["glow_red"], body)
    for i, (x, y, z) in enumerate(((-0.4, 0.25, 0.92), (-0.6, -0.27, 0.9), (-0.8, 0.2, 0.78), (-0.25, -0.22, 0.88),
                                   (-0.55, 0.32, 0.8), (-0.3, 0.05, 1.02))):
        spike("spike%d" % i, (x, y, z - 0.05), (x - 0.06, y * 1.25, z + 0.15), 0.035, M["chitin2"], body)
    # glowing egg sacs underneath + slime
    for k in range(7):
        sphere("egg%d" % k, RNG.uniform(0.05, 0.08), (-0.55 + RNG.uniform(-0.2, 0.2), RNG.uniform(-0.2, 0.2), 0.32),
               M["slime"], body, segs=8, rings=6, smooth=True)
    drip("eggdrip", (-0.5, 0.05, 0.3), 0.14, 0.016, M["slime"], body)
    sphere("shead", 0.16, (0.48, 0, 0.47), M["chitin2"], body, (1.0, 1.0, 0.85), 8, 6, True)
    for i, (y, z) in enumerate(((0.045, 0.53), (-0.045, 0.53), (0.09, 0.5), (-0.09, 0.5), (0.03, 0.58), (-0.03, 0.58))):
        sphere("seye%d" % i, 0.028, (0.62, y, z), M["glow_red"], body)
    for s in (1, -1):
        bone("chel%d" % s, (0.58, s * 0.06, 0.44), (0.66, s * 0.06, 0.36), 0.045, M["chitin2"], body, r2=0.03)
        spike("fang%d" % s, (0.66, s * 0.06, 0.36), (0.72, s * 0.035, 0.2), 0.03, M["bone"], body)
        drip("venom%d" % s, (0.72, s * 0.035, 0.21), 0.09, 0.011, M["slime"], body)
    meat("smouthgore", (0.64, 0, 0.34), 0.05, body, M["blood"], 2)
    legs = []
    for s in (1, -1):
        for i, (ax, ang) in enumerate(((0.32, 40), (0.2, 72), (0.06, 105), (-0.06, 138))):
            base = s * math.radians(ang)
            hip = empty("sh%d%d" % (s, i), (ax, s * 0.16, 0.5), body, (0, 0, base))
            lift = empty("sl%d%d" % (s, i), (0, 0, 0), hip)
            bone("sfem%d%d" % (s, i), (0, 0, 0), (0.5, 0, 0.36), 0.045, M["chitin"], lift, r2=0.035)
            sphere("skn%d%d" % (s, i), 0.05, (0.5, 0, 0.36), M["chitin2"], lift)
            spike("sknsp%d%d" % (s, i), (0.5, 0, 0.38), (0.55, 0, 0.5), 0.025, M["chitin2"], lift)
            for k in range(3):
                t = 0.25 + k * 0.25
                p = Vector((0.5 * t, 0, 0.36 * t))
                spike("shair%d%d%d" % (s, i, k), p, p + Vector((0.02, 0, 0.08)), 0.012, M["chitin2"], lift)
            bone("stib%d%d" % (s, i), (0.5, 0, 0.36), (0.95, 0, -0.5), 0.035, M["chitin"], lift, r2=0.008)
            group = (i % 2 == 0) == (s == 1)
            legs.append((hip, lift, base, s, 0.0 if group else 0.5))

    def pose(anim, t):
        for hip, lift, base, s, off in legs:
            p = 2 * PI * (t + off)
            hip.rotation_euler.z = base + s * 0.22 * math.cos(p)
            lift.rotation_euler.y = -0.3 * max(0.0, math.sin(p))
        body.location.z = math.sin(4 * PI * t) * 0.02
    return root, pose


def build_leech():
    root = empty("l_root")
    root.scale = (1.45, 1.45, 1.45)
    radii = [0.15, 0.19, 0.21, 0.2, 0.18, 0.15, 0.11]
    segs = []
    for i, r in enumerate(radii):
        x = 0.42 - i * 0.15
        seg = empty("lseg%d" % i, (x, 0, r * 0.82), root)
        sphere("lbody%d" % i, r, (0, 0, 0), M["leech" if i % 2 == 0 else "leech2"], seg, (0.9, 1.0, 0.82), 10, 7, True)
        if i in (1, 3, 5):
            sphere("lspot%d" % i, r * 0.32, (0, 0, r * 0.72), M["glow_green"], seg)
        # veins over the skin
        for k in range(2):
            a0 = RNG.uniform(0.4, 1.2) * (1 if k else -1)
            pts = [Vector((dx, math.sin(a0 + dx * 3) * r * 0.95, math.cos(a0 + dx * 3) * r * 0.8))
                   for dx in (-0.07, -0.02, 0.03, 0.07)]
            tube("lvein%d%d" % (i, k), pts, 0.011, M["vein"], seg, segs=5)
        if 0 < i < 6:
            spike("lbarb%d" % i, (0, 0.03, r * 0.75), (-0.06, 0.05, r * 0.75 + 0.1), 0.022, M["bone_dirty"], seg)
            drip("lslime%d" % i, (0.0, RNG.uniform(-0.1, 0.1), -r * 0.55), RNG.uniform(0.04, 0.09), 0.014, M["slime"], seg)
        segs.append((seg, x, r))
    head = segs[0][0]
    ring("llip", 0.12, 0.06, (0.13, 0, 0), M["flesh"], head, rot=(0, PI / 2, 0), segs=12)
    cyl("lmouth", 0.1, 0.02, (0.12, 0, 0), M["blood"], head, rot=(0, PI / 2, 0), segs=12)
    for ringi, (rad, n, ln) in enumerate(((0.085, 10, 0.07), (0.05, 7, 0.05))):
        for k in range(n):
            a = 2 * PI * k / n + ringi * 0.3
            p = Vector((0.15 - ringi * 0.03, math.cos(a) * rad, math.sin(a) * rad))
            spike("ltooth%d%d" % (ringi, k), p, p + Vector((ln, -math.cos(a) * 0.035, -math.sin(a) * 0.035)), 0.018,
                  M["tooth"], head)
    for k in range(3):
        drip("lmouthblood%d" % k, (0.15, -0.06 + k * 0.06, -0.08), RNG.uniform(0.05, 0.1), 0.012, M["blood"], head)
    for k, (y, z) in enumerate(((0.05, 0.12), (-0.05, 0.12), (0.0, 0.14))):
        sphere("leye%d" % k, 0.02, (0.05, y, z), M["black"], head, segs=6, rings=4, smooth=True)

    def pose(anim, t):
        ph = 2 * PI * t
        for i, (seg, x, r) in enumerate(segs):
            seg.location.y = math.sin(ph - i * 0.9) * 0.05 * (0.4 + i * 0.25)
            seg.location.x = x + math.sin(ph * 1 - i * 0.6) * 0.02
            sc = 1.0 + 0.07 * math.sin(ph - i * 0.9 + 1.5)
            seg.scale = (1.0 / sc, sc, sc)
    return root, pose


def build_drone():
    root = empty("d_root")
    root.scale = (1.35, 1.35, 1.35)
    body = empty("d_body", (0, 0, 0.9), root)
    sphere("dcore", 0.22, (0, 0, 0), M["chrome"], body, (1.1, 1.0, 0.8), 12, 8, True)
    ring("dband", 0.235, 0.07, (0, 0, 0), M["darkmetal"], body, segs=12, scale=(1.1, 1.0, 1.0))
    bolts("dbandb", (0, 0, 0), "z", 0.25, body, 8)
    # brain in a jar on top, plugged in with tubes
    cyl("djarbase", 0.15, 0.04, (-0.02, 0, 0.16), M["darkmetal"], body, segs=12)
    sphere("djar", 0.15, (-0.02, 0, 0.2), M["glass"], body, (1, 1, 0.85), 12, 8, True)
    for k in range(4):
        sphere("dbrain%d" % k, 0.07, (-0.02 + (k % 2 - 0.5) * 0.07, (k // 2 - 0.5) * 0.06, 0.22 + (k % 3) * 0.015),
               M["brain"], body, (1.1, 0.8, 0.8), 8, 6, True)
    for k in range(3):
        a = 2 * PI * k / 3
        wire("dbtube%d" % k, (-0.02 + math.cos(a) * 0.06, math.sin(a) * 0.06, 0.18), (math.cos(a) * 0.2, math.sin(a) * 0.18, 0.05),
             0.0, 0.012, M["wire_red" if k else "rubber"], body, 4, bulge=(math.cos(a) * 0.05, math.sin(a) * 0.05, 0.05))
    ring("dhouse", 0.09, 0.08, (0.22, 0, 0.02), M["darkmetal"], body, rot=(0, PI / 2, 0))
    sphere("deye", 0.07, (0.22, 0, 0.02), M["glow_red"], body)
    # circuit board panel
    box("dpanel", (0.12, 0.015, 0.09), (0.0, -0.232, -0.02), M["circuit"], body)
    for k in range(3):
        box("dchip%d" % k, (0.025, 0.01, 0.02), (-0.03 + k * 0.03, -0.241, -0.01 + (k % 2) * 0.03), M["copper"], body)
    for s in (1, -1):
        box("dpod%d" % s, (0.26, 0.08, 0.08), (0.08, s * 0.28, -0.05), M["darkmetal"], body)
        bone("dbar%d" % s, (0.2, s * 0.28, -0.05), (0.36, s * 0.28, -0.05), 0.022, M["chrome"], body)
        sphere("dtip%d" % s, 0.022, (0.37, s * 0.28, -0.05), M["glow_red"], body)
        box("dstrut%d" % s, (0.06, 0.1, 0.03), (0.04, s * 0.22, -0.05), M["chrome"], body)
        wire("dpodw%d" % s, (-0.04, s * 0.28, -0.08), (-0.12, s * 0.15, -0.1), 0.05, 0.01, M["wire_yellow"], body, 4)
    for k in range(3):
        a = 2 * PI * k / 3 + PI / 3
        fin = empty("dfin%d" % k, (0, 0, -0.12), body, (0, 0, a))
        box("dfinb%d" % k, (0.16, 0.025, 0.16), (0.12, 0, -0.05), M["darkmetal"], fin, (0, -0.5, 0))
    cyl("dthrust", 0.08, 0.06, (0, 0, -0.2), M["glow_blue"], body)
    # torn dangling wires with sparking ends
    for k, (x, y, c) in enumerate(((0.08, 0.1, "wire_red"), (-0.1, -0.05, "wire_yellow"), (0.02, -0.12, "wire_blue"), (-0.06, 0.12, "rubber"))):
        end = Vector((x + RNG.uniform(-0.06, 0.06), y + RNG.uniform(-0.05, 0.05), -0.42 - RNG.uniform(0, 0.12)))
        wire("ddang%d" % k, (x, y, -0.14), end, 0.0, 0.01, M[c], body, 5, wobble=0.025)
        sphere("dspark%d" % k, 0.018, end, M["glow_white" if k % 2 else "glow_yellow"], body, segs=6, rings=4)
    # manipulator claw
    claw = empty("dclaw", (0.1, 0, -0.15), body)
    bone("dcl1", (0, 0, 0), (0.12, 0, -0.14), 0.016, M["chrome"], claw)
    sphere("dclj", 0.022, (0.12, 0, -0.14), M["darkmetal"], claw)
    bone("dcl2", (0.12, 0, -0.14), (0.24, 0, -0.12), 0.013, M["chrome"], claw)
    for s in (1, -1):
        spike("dclf%d" % s, (0.24, 0, -0.12), (0.31, s * 0.035, -0.15), 0.014, M["darkmetal"], claw)
    bone("dant", (-0.12, 0.05, 0.12), (-0.17, 0.06, 0.36), 0.008, M["chrome"], body)
    sphere("dantt", 0.018, (-0.17, 0.06, 0.36), M["glow_red"], body)
    spin = empty("dspin", (0, 0, -0.02), body)
    for k in range(3):
        a = 2 * PI * k / 3
        sphere("dlight%d" % k, 0.025, (math.cos(a) * 0.255, math.sin(a) * 0.235, 0), M["glow_yellow"], spin)

    def pose(anim, t):
        ph = 2 * PI * t
        body.location.z = 0.9 + math.sin(ph) * 0.05
        body.rotation_euler.y = math.sin(ph + 1) * 0.06
        spin.rotation_euler.z = ph / 3
        claw.rotation_euler.y = math.sin(ph) * 0.25
    return root, pose


# ---------------------------------------------------------------- tiles & props
ROOT_TILE = None


def tile_root():
    global ROOT_TILE
    ROOT_TILE = empty("tile_root")
    return ROOT_TILE


mat("oil", (0.012, 0.011, 0.014), 0.2, 0.08)
mat("water", (0.04, 0.055, 0.07), 0.0, 0.03)
mat("moss", (0.06, 0.1, 0.03), 0.0, 0.9)
mat("paper", (0.7, 0.68, 0.6), 0.0, 0.8)


def chance(p):
    return RNG.random() < p


def rnd_cracks(name, r, z=0.0, n=None, mat_="black", length=(0.15, 0.4)):
    n = RNG.randint(0, 3) if n is None else n
    for k in range(n):
        x, y = RNG.uniform(-0.35, 0.35), RNG.uniform(-0.35, 0.35)
        a, L = RNG.uniform(0, PI), RNG.uniform(*length)
        box("%s%d" % (name, k), (L, 0.014, 0.012), (x, y, z), M[mat_], r, (0, 0, a))
        if chance(0.6):
            b = a + RNG.choice((-1, 1)) * RNG.uniform(0.5, 1.1)
            box("%s%db" % (name, k), (L * 0.5, 0.01, 0.012),
                (x + math.cos(a) * L * 0.25 + math.cos(b) * L * 0.2, y + math.sin(a) * L * 0.25 + math.sin(b) * L * 0.2, z),
                M[mat_], r, (0, 0, b))


def rnd_debris(name, r, mats, n=None, z=0.0, size=(0.03, 0.08)):
    n = RNG.randint(0, 4) if n is None else n
    for k in range(n):
        s = RNG.uniform(*size)
        box("%s%d" % (name, k), (s, s * RNG.uniform(0.7, 1.4), s * 0.6),
            (RNG.uniform(-0.42, 0.42), RNG.uniform(-0.42, 0.42), z + s * 0.25), M[RNG.choice(mats)], r,
            (RNG.uniform(0, 0.5), RNG.uniform(0, 0.5), RNG.uniform(0, PI)))


def rnd_stain(name, r, mat_, p, z=0.003, size=(0.15, 0.4)):
    if chance(p):
        pool(name, (RNG.uniform(-0.25, 0.25), RNG.uniform(-0.25, 0.25), z), RNG.uniform(*size), r, M[mat_], RNG.randint(2, 4))


def plates(name, r, mat_, layout, z=0.0, gap=0.04):
    """Returns the plate rects (cx, cy, w, h) so callers can put rivets on them."""
    if layout == "one":
        rects = [(0, 0, 0.88, 0.88)]
    elif layout == "twox":
        rects = [(-0.22, 0, 0.42, 0.88), (0.22, 0, 0.42, 0.88)]
    elif layout == "twoy":
        rects = [(0, -0.22, 0.88, 0.42), (0, 0.22, 0.88, 0.42)]
    elif layout == "four":
        rects = [(x, y, 0.42, 0.42) for x in (-0.22, 0.22) for y in (-0.22, 0.22)]
    else:   # "three": one long + two small
        rects = [(-0.22, 0, 0.42, 0.88), (0.22, -0.22, 0.42, 0.42), (0.22, 0.22, 0.42, 0.42)]
    for k, (x, y, w, h) in enumerate(rects):
        box("%s%d" % (name, k), (w, h, 0.02), (x, y, z + RNG.uniform(-0.002, 0.004)), M[mat_], r)
    return rects


def slab(material, top=0.0, h=0.1, size=1.02):
    return box("slab", (size, size, h), (0, 0, top - h / 2), material, ROOT_TILE)


def build_floor_metal():
    r = tile_root()
    slab(M["steel"])
    rects = plates("plate", r, "steel2", RNG.choice(["one", "twox", "twoy", "four", "three"]))
    for k, (x, y, w, h) in enumerate(rects):
        for sx in (-1, 1):
            for sy in (-1, 1):
                if chance(0.85):
                    sphere("rv%d%d%d" % (k, sx, sy), 0.022, (x + sx * (w / 2 - 0.05), y + sy * (h / 2 - 0.05), 0.014), M["chrome"], r)
    if chance(0.25):
        cyl("drain", 0.12, 0.01, (RNG.uniform(-0.2, 0.2), RNG.uniform(-0.2, 0.2), 0.012), M["black"], r, segs=10)
    if chance(0.2):
        box("hzedge", (0.88, 0.07, 0.022), (0, RNG.choice((-0.4, 0.4)), 0.004), M["hazard"], r)
    for k in range(RNG.randint(0, 3)):
        box("scuff%d" % k, (RNG.uniform(0.1, 0.3), RNG.uniform(0.03, 0.08), 0.004), (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), 0.012),
            M["rust2"], r, (0, 0, RNG.uniform(0, PI)))
    rnd_stain("oil", r, "oil", 0.3, 0.013)
    rnd_debris("bolt", r, ["chrome", "darkmetal"], RNG.randint(0, 2), 0.012, (0.02, 0.04))
    return r, None


def build_floor_cables():
    r = tile_root()
    slab(M["steel"])
    plates("plate", r, "steel2", RNG.choice(["one", "twox", "twoy"]))
    mats = ["rubber", "wire_red", "rubber", "wire_yellow", "wire_blue"]
    for k in range(RNG.randint(2, 5)):
        rad = RNG.uniform(0.014, 0.035)
        y0 = RNG.uniform(-0.38, 0.38)
        pts = [Vector((-0.51, y0, rad + 0.01))]
        for t in (0.3, 0.6):
            pts.append(Vector((-0.51 + t * 1.02, y0 + RNG.uniform(-0.15, 0.15), rad + 0.01)))
        pts.append(Vector((0.51, y0 + RNG.uniform(-0.2, 0.2), rad + 0.01)))
        tube("cab%d" % k, pts, rad, M[RNG.choice(mats)], r, segs=6)
    if chance(0.3):
        box("jbox", (0.14, 0.12, 0.07), (RNG.uniform(-0.25, 0.25), RNG.uniform(-0.25, 0.25), 0.04), M["hazard"], r)
    return r, None


def build_floor_grate():
    r = tile_root()
    slab(M["darkmetal"], -0.06)
    if chance(0.7):
        box("goo", (0.9, 0.9, 0.01), (0, 0, -0.05), M["glow_green_dim"], r)
    if chance(0.4):
        meat("sunk", (RNG.uniform(-0.2, 0.2), RNG.uniform(-0.2, 0.2), -0.04), 0.1, r, M["flesh"], 2)
    along_x = chance(0.5)
    n = RNG.randint(5, 8)
    missing = RNG.randrange(n) if chance(0.3) else -1
    for k in range(n):
        if k == missing:
            continue
        u = -0.4 + k * 0.8 / (n - 1)
        size = (0.94, 0.045, 0.04) if along_x else (0.045, 0.94, 0.04)
        box("bar%d" % k, size, (0, u, -0.02) if along_x else (u, 0, -0.02), M["steel"], r)
    for (sx, sy, x, y) in ((1.02, 0.08, 0, 0.47), (1.02, 0.08, 0, -0.47), (0.08, 1.02, 0.47, 0), (0.08, 1.02, -0.47, 0)):
        box("frame", (sx, sy, 0.05), (x, y, -0.025), M["steel2"], r)
    return r, None


def build_floor_concrete():
    r = tile_root()
    slab(M["concrete"])
    if chance(0.35):
        box("patch", (RNG.uniform(0.25, 0.5), RNG.uniform(0.25, 0.5), 0.01), (RNG.uniform(-0.2, 0.2), RNG.uniform(-0.2, 0.2), 0.001),
            M["concrete2"], r, (0, 0, RNG.choice((0, PI / 2))))
    rnd_cracks("crk", r, 0.001, RNG.randint(0, 4), "concrete2")
    rnd_debris("rub", r, ["concrete2", "stone"], RNG.randint(0, 4))
    rnd_stain("puddle", r, "water", 0.2, 0.002)
    rnd_stain("oil", r, "oil", 0.12, 0.002, (0.1, 0.25))
    if chance(0.18):
        box("paint", (0.9, 0.04, 0.004), (0, RNG.uniform(-0.3, 0.3), 0.002), M["hazard"], r)
    return r, None


def build_floor_hazard():
    r = tile_root()
    slab(M["darkmetal"])
    along_x = chance(0.5)
    for k in range(5):
        u = -0.4 + k * 0.2
        L = 0.96 if chance(0.7) else RNG.uniform(0.4, 0.8)
        size = (L, 0.1, 0.02) if along_x else (0.1, L, 0.02)
        box("stripe%d" % k, size, (0, u, 0.0) if along_x else (u, 0, 0.0), M["hazard"], r)
    rnd_debris("hd", r, ["rust2", "concrete2"], RNG.randint(0, 3), 0.01)
    return r, None


def build_floor_bones():
    r = tile_root()
    slab(M["concrete"])
    rnd_stain("bpool", r, "blood", 0.6, 0.002, (0.25, 0.45))
    for k in range(RNG.randint(0, 2)):
        skull_prop("sk%d" % k, (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), 0.0), r, RNG.uniform(0.8, 1.1), RNG.uniform(0, 6.28),
                   bloody=chance(0.5))
    for k in range(RNG.randint(1, 4)):
        x, y, a, L = RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), RNG.uniform(0, PI), RNG.uniform(0.15, 0.3)
        bone_prop("b%d" % k, (x - math.cos(a) * L / 2, y - math.sin(a) * L / 2, 0.03), (x + math.cos(a) * L / 2, y + math.sin(a) * L / 2, 0.03), r)
    rnd_cracks("crk", r, 0.001, RNG.randint(0, 2), "concrete2")
    return r, None


def build_floor_gore():
    r = tile_root()
    slab(M["concrete"])
    pool("gpool", (RNG.uniform(-0.1, 0.1), RNG.uniform(-0.1, 0.1), 0.002), RNG.uniform(0.5, 0.85), r, n=RNG.randint(4, 7))
    for k in range(RNG.randint(2, 6)):
        meat("gm%d" % k, (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), 0.03), RNG.uniform(0.05, 0.11), r,
             M["flesh" if k % 2 else "guts"], 3)
    if chance(0.6):
        guts("ggut", (RNG.uniform(-0.3, 0), RNG.uniform(-0.3, 0.3), 0.03), (1, RNG.uniform(-0.6, 0.6), 0), RNG.randint(5, 9), 0.025, r, droop=0.0)
    if chance(0.5):
        bone_prop("gb", (0.2, -0.3, 0.025), (0.35, -0.05, 0.025), r, 0.015, M["bone_dirty"])
    return r, None


def build_floor_flesh():
    r = tile_root()
    slab(M["leech"], 0.0, 0.1, 1.04)
    for k in range(9):
        sphere("lump%d" % k, RNG.uniform(0.1, 0.18), (RNG.uniform(-0.4, 0.4), RNG.uniform(-0.4, 0.4), -0.04),
               M["leech" if k % 3 else "leech2"], r, (1, 1, 0.45), 8, 6, True)
    for k in range(4):
        a = RNG.uniform(0, 2 * PI)
        p1 = Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, 0.025))
        p2 = Vector((RNG.uniform(-0.15, 0.15), RNG.uniform(-0.15, 0.15), 0.035))
        wire("fvein%d" % k, p1, p2, -0.02, 0.016, M["vein"], r, 5, wobble=0.04)
    for k in range(3):
        sphere("fpus%d" % k, 0.04, (RNG.uniform(-0.35, 0.35), RNG.uniform(-0.35, 0.35), 0.03), M["slime"], r, segs=8, rings=6, smooth=True)
    return r, None


def wall_base(material, cap="cap"):
    r = tile_root()
    box("block", (1, 1, 1), (0, 0, 0.5), M[material], r)
    box("capb", (1.02, 1.02, 0.07), (0, 0, 1.0), M[cap], r)
    return r


def build_wall_tech():
    r = wall_base("steel")
    glow = RNG.choice(["glow_cyan", "glow_cyan", "glow_red", "glow_yellow"])
    for name, loc, size in (("px", (0.505, 0, 0.45), (0.02, 0.72, 0.6)), ("py", (0, 0.505, 0.45), (0.72, 0.02, 0.6))):
        if chance(0.5):
            box("panel" + name, size, loc, M["steel2"], r)
        else:
            half = (size[0], size[1] * 0.46, size[2]) if name == "px" else (size[0] * 0.46, size[1], size[2])
            for s_ in (-1, 1):
                off = (0, s_ * 0.19, 0) if name == "px" else (s_ * 0.19, 0, 0)
                box("panel%s%d" % (name, s_), half, (loc[0] + off[0], loc[1] + off[1], loc[2]), M["steel2"], r)
    bolts("pbx", (0.517, 0, 0.45), "x", 0.38, r, 4)
    bolts("pby", (0, 0.517, 0.45), "y", 0.38, r, 4)
    zs = RNG.uniform(0.7, 0.9)
    box("stripx", (0.02, 0.8, 0.04), (0.515, 0, zs), M[glow], r)
    box("stripy", (0.8, 0.02, 0.04), (0, 0.515, zs), M[glow], r)
    if chance(0.8):
        box("basex", (0.04, 1.0, 0.08), (0.51, 0, 0.04), M["hazard"], r)
        box("basey", (1.0, 0.04, 0.08), (0, 0.51, 0.04), M["hazard"], r)
    if chance(0.5):
        u = RNG.uniform(-0.25, 0.25)
        box("ventx", (0.02, 0.3, 0.16), (0.52, u, 0.28), M["black"], r)
        for k in range(4):
            box("slat%d" % k, (0.025, 0.3, 0.015), (0.53, u, 0.22 + k * 0.04), M["steel2"], r)
    if chance(0.35):
        box("screen", (0.02, 0.22, 0.14), (0.52, RNG.uniform(-0.2, 0.2), 0.55), M["glow_green_dim"], r)
    if chance(0.6):
        for k, (c, rad, sag) in enumerate((("rubber", 0.03, 0.12), ("wire_red", 0.016, 0.17), ("wire_yellow", 0.014, 0.08))):
            wire("cbx%d" % k, (0.54, -0.5, 0.74 - k * 0.02), (0.54, 0.5, 0.74 - k * 0.02), sag * RNG.uniform(0.6, 1.3), rad, M[c], r, 7)
    if chance(0.5):
        for k, (c, rad, sag) in enumerate((("rubber", 0.03, 0.12), ("wire_red", 0.016, 0.17))):
            wire("cby%d" % k, (-0.5, 0.54, 0.7 - k * 0.02), (0.5, 0.54, 0.7 - k * 0.02), sag * RNG.uniform(0.6, 1.3), rad, M[c], r, 7)
    if chance(0.35):
        y0 = RNG.uniform(-0.3, 0.3)
        wire("hang", (0.54, y0, 0.68), (0.6, y0 + 0.05, 0.38), 0.0, 0.01, M["wire_blue"], r, 4, wobble=0.02)
        sphere("hangspark", 0.02, (0.6, y0 + 0.05, 0.38), M["glow_white"], r, segs=6, rings=4)
    if chance(0.4):
        smear("bloodx", (0.515, RNG.uniform(-0.3, 0.3), RNG.uniform(0.3, 0.6)), "x", RNG.uniform(0.2, 0.4), r, n=4)
    if chance(0.25):
        smear("bloody", (RNG.uniform(-0.3, 0.3), 0.515, RNG.uniform(0.3, 0.6)), "y", RNG.uniform(0.2, 0.4), r, n=3)
    return r, None


def build_wall_skull():
    r = wall_base("stone")
    n = RNG.randint(3, 6)
    for i in range(n):
        u, z = RNG.uniform(-0.35, 0.35), RNG.uniform(0.18, 0.9)
        skull_prop("skx%d" % i, (0.47, u, z - 0.08), r, RNG.uniform(1.0, 1.3), RNG.uniform(-0.3, 0.3), bloody=chance(0.4))
    for i in range(RNG.randint(3, 6)):
        u, z = RNG.uniform(-0.35, 0.35), RNG.uniform(0.18, 0.9)
        skull_prop("sky%d" % i, (-u, 0.47, z - 0.08), r, RNG.uniform(1.0, 1.3), PI / 2 + RNG.uniform(-0.3, 0.3), bloody=chance(0.4))
    for k in range(RNG.randint(1, 4)):
        bone_prop("wbx%d" % k, (0.5, RNG.uniform(-0.4, 0.4), RNG.uniform(0.2, 0.9)), (0.62, RNG.uniform(-0.45, 0.45), RNG.uniform(0.2, 0.9)), r)
        bone_prop("wby%d" % k, (RNG.uniform(-0.4, 0.4), 0.5, RNG.uniform(0.2, 0.9)), (RNG.uniform(-0.45, 0.45), 0.62, RNG.uniform(0.2, 0.9)), r)
    if chance(0.5):
        rc = ribcage("wrib", (0.5, RNG.uniform(-0.2, 0.2), 0.3), r, 0.9, broken=True)
        rc.rotation_euler = (0, 0, PI)
    if chance(0.5):
        smear("bly", (RNG.uniform(-0.3, 0.3), 0.505, 0.6), "y", 0.3, r, n=3)
    return r, None


def build_wall_pipe():
    r = wall_base("rust")
    n = RNG.randint(2, 4)
    us = sorted(RNG.uniform(-0.38, 0.38) for _ in range(n))
    for i, u in enumerate(us):
        mat_p = M[RNG.choice(["chrome", "steel2", "steel2", "rust2"])]
        rad = RNG.uniform(0.045, 0.075)
        cyl("pipex%d" % i, rad, 1.0, (0.53, u, 0.5), mat_p, r)
        cyl("pipey%d" % i, rad, 1.0, (u, 0.53, 0.5), mat_p, r)
        for z in (0.2, 0.8):
            ring("clx%d%d" % (i, z * 10), rad + 0.008, 0.04, (0.53, u, z), M["darkmetal"], r)
            ring("cly%d%d" % (i, z * 10), rad + 0.008, 0.04, (u, 0.53, z), M["darkmetal"], r)
    if chance(0.5):
        ring("valve", 0.08, 0.02, (0.62, us[0], 0.55), M["armor"], r, rot=(0, PI / 2, 0), segs=10)
        bone("valvestem", (0.59, us[0], 0.55), (0.62, us[0], 0.55), 0.015, M["chrome"], r)
    if chance(0.6):
        v = RNG.uniform(-0.2, 0.2)
        box("ventx", (0.03, 0.3, 0.12), (0.6, v, 0.3), M["glow_green"], r)
        drip("slimex", (0.61, v - 0.04, 0.24), RNG.uniform(0.1, 0.25), 0.02, M["slime"], r)
        pool("slpool", (0.62, v, 0.002), 0.18, r, M["slime"], 3)
    if chance(0.5):
        v = RNG.uniform(-0.2, 0.2)
        box("venty", (0.3, 0.03, 0.12), (v, 0.6, 0.6), M["glow_green"], r)
        drip("slimey", (v + 0.04, 0.61, 0.54), RNG.uniform(0.1, 0.3), 0.02, M["slime"], r)
    if chance(0.6):
        smear("rustx", (0.505, RNG.uniform(-0.35, 0.35), RNG.uniform(0.4, 0.7)), "x", 0.3, r, M["rust2"], 3)
    return r, None


def build_wall_flesh():
    """Tech wall consumed by biomass."""
    r = wall_base("steel")
    box("stripx", (0.02, 0.8, 0.04), (0.515, 0, 0.88), M["glow_cyan"], r)
    for k in range(14):
        face = k % 2
        u, z = RNG.uniform(-0.45, 0.45), RNG.uniform(0.0, 0.95) ** 1.6
        rad = RNG.uniform(0.1, 0.22) * (1.3 - z * 0.6)
        loc = (0.47, u, z) if face == 0 else (u, 0.47, z)
        sc = (0.6, 1, 1) if face == 0 else (1, 0.6, 1)
        sphere("flesh%d" % k, rad, loc, M["leech" if k % 3 else "flesh"], r, sc, 9, 7, True)
    for k in range(4):
        sphere("cap%d" % k, RNG.uniform(0.14, 0.22), (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), 1.03), M["leech"], r,
               (1, 1, 0.5), 9, 6, True)
    for k in range(5):
        face = k % 2
        p1 = (0.53, RNG.uniform(-0.4, 0.4), 1.0) if face == 0 else (RNG.uniform(-0.4, 0.4), 0.53, 1.0)
        p2 = (0.58, RNG.uniform(-0.4, 0.4), 0.05) if face == 0 else (RNG.uniform(-0.4, 0.4), 0.58, 0.05)
        wire("tend%d" % k, p1, p2, 0.0, 0.022, M["vein"], r, 6, wobble=0.05)
    for k in range(5):
        face = k % 2
        loc = (0.6, RNG.uniform(-0.35, 0.35), RNG.uniform(0.2, 0.8)) if face == 0 else (RNG.uniform(-0.35, 0.35), 0.6, RNG.uniform(0.2, 0.8))
        sphere("pus%d" % k, RNG.uniform(0.04, 0.07), loc, M["slime"], r, segs=8, rings=6, smooth=True)
    # a mouth full of teeth
    mouth = empty("mouth", (0.6, -0.15, 0.45), r)
    cyl("mhole", 0.09, 0.02, (0, 0, 0), M["blood"], mouth, rot=(0, PI / 2, 0), segs=10)
    for k in range(8):
        a = 2 * PI * k / 8
        p = Vector((0.0, math.cos(a) * 0.095, math.sin(a) * 0.07))
        spike("mt%d" % k, p, p + Vector((0.05, -math.cos(a) * 0.04, -math.sin(a) * 0.03)), 0.014, M["tooth"], mouth)
    drip("mdrip", (0.62, -0.15, 0.38), 0.15, 0.015, M["blood"], r)
    pool("fpool", (0.65, 0.0, 0.002), 0.3, r, M["blood"], 3)
    return r, None


def build_barrel():
    r = tile_root()
    cyl("body", 0.27, 0.72, (0, 0, 0.36), M["barrel"], r, segs=12)
    for z in (0.12, 0.6):
        ring("band", 0.285, 0.05, (0, 0, z), M["darkmetal"], r, segs=12)
    cyl("lid", 0.2, 0.02, (0, 0, 0.725), M["glow_green"], r, segs=12)
    box("label", (0.02, 0.18, 0.18), (0.27, 0, 0.36), M["hazard"], r)
    box("dent", (0.02, 0.1, 0.12), (0.255, -0.15, 0.5), M["rust2"], r, (0, 0, -0.5))
    drip("bdrip1", (0.25, 0.12, 0.73), 0.22, 0.02, M["slime"], r)
    drip("bdrip2", (0.18, -0.19, 0.73), 0.14, 0.018, M["slime"], r)
    pool("bpool", (0.3, 0.1, 0.002), 0.25, r, M["slime"], 3)
    return r, None


def build_crate():
    r = tile_root()
    box("body", (0.74, 0.74, 0.6), (0, 0, 0.3), M["crate"], r)
    for x in (-0.36, 0.36):
        for y in (-0.36, 0.36):
            box("edge", (0.06, 0.06, 0.62), (x, y, 0.3), M["steel2"], r)
    box("band", (0.76, 0.76, 0.06), (0, 0, 0.3), M["steel2"], r)
    box("mark", (0.02, 0.3, 0.12), (0.375, 0, 0.45), M["hazard"], r)
    smear("cblood", (0.375, 0.15, 0.3), "x", 0.25, r, n=3)
    guts("cgut", (0.3, 0.37, 0.61), (0.2, 1, -0.2), 5, 0.025, r)
    return r, None


def build_skullpile():
    r = tile_root()
    pool("sppool", (0, 0, 0.002), 0.6, r, n=4)
    for i, (x, y, z, s, yaw) in enumerate(((0, 0, 0, 1.3, 0.6), (0.18, -0.15, 0, 1.0, 1.2), (-0.15, 0.17, 0, 1.0, 0.1),
                                             (0.05, 0.05, 0.17, 1.1, 0.9), (-0.2, -0.15, 0, 0.9, 2.0))):
        skull_prop("ps%d" % i, (x, y, z), r, s, yaw, bloody=(i % 2 == 0))
    bone_prop("pb1", (-0.35, 0.0, 0.03), (-0.05, -0.3, 0.03), r)
    bone_prop("pb2", (0.3, 0.1, 0.03), (0.05, 0.35, 0.05), r)
    meat("spm", (0.25, 0.25, 0.03), 0.07, r, M["flesh"], 2)
    return r, None


def build_gorepile():
    r = tile_root()
    pool("gp", (0, 0, 0.002), 0.85, r, n=6)
    for k in range(6):
        meat("gm%d" % k, (RNG.uniform(-0.25, 0.25), RNG.uniform(-0.25, 0.25), 0.04 + k * 0.02), RNG.uniform(0.08, 0.13), r,
             M["flesh" if k % 2 else "guts"], 3)
    rc = ribcage("grib", (0.05, 0.0, 0.05), r, 1.1, broken=True)
    rc.rotation_euler = (0.3, 1.2, 0.6)
    guts("gg1", (0.0, 0.0, 0.15), (1, 0.3, -0.3), 10, 0.03, r, droop=0.2)
    skull_prop("gsk", (-0.2, 0.18, 0.05), r, 1.1, 2.4, bloody=True)
    bone_prop("gb1", (0.15, -0.3, 0.03), (0.38, -0.1, 0.03), r)
    return r, None


def build_corpse():
    """A fallen cyborg skeleton - some poor earlier krew member."""
    r = tile_root()
    pool("cpool", (0.05, 0.0, 0.002), 0.5, r, n=4)
    skull_prop("csk", (0.3, 0.05, 0.0), r, 1.3, 0.4)
    box("ccran", (0.18, 0.17, 0.04), (0.3, 0.05, 0.25), M["chrome"], r, (0.3, 0.2, 0.4))
    rc = ribcage("crib", (0.02, 0.0, 0.1), r, 1.0, broken=True)
    rc.rotation_euler = (0, -1.45, 0.3)
    box("cpack", (0.26, 0.28, 0.12), (-0.05, -0.05, 0.06), M["darkmetal"], r, (0, 0, 0.3))
    sphere("ccore", 0.05, (-0.05, -0.05, 0.13), M["glow_red"], r)
    bone_prop("cl1", (-0.2, 0.1, 0.03), (-0.45, 0.25, 0.03), r)
    bone_prop("cl2", (-0.2, -0.12, 0.03), (-0.42, -0.3, 0.03), r)
    box("cpad", (0.16, 0.12, 0.07), (0.1, 0.3, 0.04), M["armor"], r, (0.2, 0, 0.6))
    wire("cw1", (-0.05, -0.05, 0.12), (0.25, -0.3, 0.02), 0.0, 0.012, M["wire_red"], r, 5, bulge=(0, 0, 0.06))
    wire("cw2", (-0.05, 0.0, 0.12), (-0.1, 0.35, 0.02), 0.0, 0.015, M["rubber"], r, 5, bulge=(0, 0, 0.05))
    return r, None


def build_tank():
    """Specimen tank - glass cylinder with something floating inside."""
    r = tile_root()
    cyl("tbase", 0.36, 0.14, (0, 0, 0.07), M["darkmetal"], r, segs=12)
    cyl("ttop", 0.36, 0.1, (0, 0, 1.15), M["darkmetal"], r, segs=12)
    cyl("fluid", 0.3, 0.9, (0, 0, 0.6), M["glow_green_dim"], r, segs=12)
    cyl("glass", 0.33, 1.0, (0, 0, 0.64), M["glass"], r, segs=14)
    sk = skull_prop("tsk", (0.05, 0, 0.75), r, 1.6, 0.9)
    rc = ribcage("trib", (0.0, 0.0, 0.35), r, 1.0)
    rc.rotation_euler = (0, 0, 0.9)
    guts("tgut", (0.05, 0.0, 0.4), (0.3, 0.3, -1), 5, 0.025, r, droop=0.1)
    for k in range(5):
        sphere("bub%d" % k, 0.02, (RNG.uniform(-0.2, 0.2), RNG.uniform(-0.2, 0.2), RNG.uniform(0.3, 1.0)), M["glow_white"], r, segs=6, rings=4)
    for k in range(3):
        a = k * 2.1
        wire("tcab%d" % k, (math.cos(a) * 0.25, math.sin(a) * 0.25, 1.2), (math.cos(a) * 0.55, math.sin(a) * 0.55, 0.02), 0.0, 0.025,
             M["rubber" if k else "wire_red"], r, 6, bulge=(math.cos(a) * 0.15, math.sin(a) * 0.15, 0.1))
    box("tlabel", (0.02, 0.2, 0.06), (0.36, 0, 0.1), M["hazard"], r)
    sphere("tlight", 0.03, (0.3, 0.2, 1.2), M["glow_red"], r)
    return r, None


def build_cables():
    r = tile_root()
    for k, (c, rad) in enumerate((("rubber", 0.04), ("rubber", 0.03), ("wire_red", 0.02), ("wire_yellow", 0.018), ("wire_blue", 0.015))):
        pts = curve_pts((-0.5, -0.3 + k * 0.1, rad), (0.4, 0.45 - k * 0.12, rad), 0, 6, (0.1, 0.1, 0), wobble=0.04)
        for p in pts:
            p.z = rad + 0.005
        tube("cb%d" % k, pts, rad, M[c], r, segs=6)
    sphere("cbspark", 0.025, (0.4, 0.45 - 4 * 0.12, 0.02), M["glow_white"], r, segs=6, rings=4)
    return r, None


def build_portal():
    r = tile_root()
    cyl("base", 0.48, 0.08, (0, 0, 0.04), M["darkmetal"], r, segs=12)
    ring("ring", 0.42, 0.04, (0, 0, 0.1), M["glow_cyan"], r, segs=16)
    cyl("pad", 0.32, 0.02, (0, 0, 0.09), M["glow_blue"], r, segs=12)
    for k in range(4):
        a = PI / 4 + k * PI / 2
        p = (math.cos(a) * 0.45, math.sin(a) * 0.45)
        box("pylon%d" % k, (0.1, 0.1, 0.5), (p[0], p[1], 0.25), M["steel2"], r, (0, 0, a))
        sphere("pyltip%d" % k, 0.05, (p[0], p[1], 0.53), M["glow_cyan"], r)
        wire("pcab%d" % k, (p[0], p[1], 0.1), (p[0] * 1.25, p[1] * 1.25, 0.02), 0.0, 0.02, M["rubber"], r, 3, bulge=(0, 0, 0.04))
    orb = empty("orbit", (0, 0, 0), r)
    for k in range(6):
        a = 2 * PI * k / 6
        sphere("mote%d" % k, 0.04, (math.cos(a) * 0.25, math.sin(a) * 0.25, 0.25 + 0.12 * math.sin(a * 2)), M["glow_white"], orb)

    def pose(anim, t):
        orb.rotation_euler.z = 2 * PI * t / 3
    return r, pose


def build_spawner():
    r = tile_root()
    body = empty("pod", (0, 0, 0), r)
    pool("spool", (0, 0, 0.002), 1.0, r, M["blood"], 5)
    sphere("mound", 0.46, (0, 0, 0.05), M["flesh"], body, (1, 1, 0.6), 12, 8, True)
    sphere("mound2", 0.3, (0, 0, 0.25), M["leech"], body, (1, 1, 0.8), 10, 7, True)
    ring("mouth", 0.13, 0.1, (0, 0, 0.47), M["leech2"], body, segs=10)
    cyl("hole", 0.11, 0.02, (0, 0, 0.5), M["glow_green"], body, segs=10)
    for k in range(10):
        a = 2 * PI * k / 10
        p = Vector((math.cos(a) * 0.12, math.sin(a) * 0.12, 0.5))
        spike("ptooth%d" % k, p, p + Vector((-math.cos(a) * 0.04, -math.sin(a) * 0.04, 0.07)), 0.018, M["tooth"], body)
    for k in range(6):
        a = 2 * PI * k / 6 + 0.3
        sphere("pust%d" % k, 0.06, (math.cos(a) * 0.36, math.sin(a) * 0.36, 0.2), M["glow_green"], body)
        bone("vein%d" % k, (math.cos(a) * 0.15, math.sin(a) * 0.15, 0.45), (math.cos(a) * 0.43, math.sin(a) * 0.43, 0.08),
             0.025, M["vein"], body)
    for k in range(4):  # tendrils plugging into the floor
        a = 2 * PI * k / 4 + 0.8
        wire("tendril%d" % k, (math.cos(a) * 0.35, math.sin(a) * 0.35, 0.1), (math.cos(a) * 0.62, math.sin(a) * 0.62, 0.0), 0.0, 0.03,
             M["leech"], body, 4, bulge=(0, 0, 0.08))
    for k in range(3):
        drip("pdrip%d" % k, (math.cos(k * 2) * 0.12, math.sin(k * 2) * 0.12, 0.5), 0.12, 0.015, M["slime"], body)
    skull_prop("pskull", (0.3, -0.25, 0.0), r, 0.9, 0.5)

    def pose(anim, t):
        s = 1.0 + 0.07 * math.sin(2 * PI * t)
        body.scale = (s, s, 1.0 / s ** 0.5)
    return r, pose


def build_health():
    r = tile_root()
    spin = empty("spin", (0, 0, 0), r)
    cyl("can", 0.1, 0.26, (0, 0, 0.3), M["white"], spin, segs=10)
    cyl("capt", 0.11, 0.04, (0, 0, 0.44), M["chrome"], spin, segs=10)
    cyl("capb", 0.11, 0.04, (0, 0, 0.16), M["chrome"], spin, segs=10)
    box("crossv", (0.02, 0.05, 0.15), (0.1, 0, 0.3), M["glow_red"], spin)
    box("crossh", (0.02, 0.15, 0.05), (0.1, 0, 0.3), M["glow_red"], spin)
    box("crossv2", (0.02, 0.05, 0.15), (-0.1, 0, 0.3), M["glow_red"], spin)
    box("crossh2", (0.02, 0.15, 0.05), (-0.1, 0, 0.3), M["glow_red"], spin)

    def pose(anim, t):
        spin.rotation_euler.z = 2 * PI * t
    return r, pose


def build_power():
    r = tile_root()
    spin = empty("spin", (0, 0, 0.32), r)
    sphere("orb", 0.11, (0, 0, 0), M["glow_blue"], spin, segs=10, rings=7, smooth=True)
    for k in range(3):
        ring("cage%d" % k, 0.15, 0.025, (0, 0, 0), M["chrome"], spin, rot=(PI / 2, 0, k * PI / 3), segs=12)

    def pose(anim, t):
        spin.rotation_euler.z = 2 * PI * t / 3
    return r, pose


# ---------------------------------------------------------------- gibs (tumbling chunks)
def gib_builder(fn):
    def build():
        r = tile_root()
        inner = empty("gib_inner", (0, 0, 0), r)
        fn(inner)

        def pose(anim, t):
            inner.rotation_euler = (2 * PI * t, PI * t + 0.4, 0.7)
        return r, pose
    return build


def g_bone(p):
    bone_prop("gb", (-0.17, 0, 0), (0.17, 0, 0), p, 0.026)


def g_rib(p):
    pts = [Vector((math.cos(a) * 0.15 - 0.05, math.sin(a) * 0.15, 0)) for a in (-1.2, -0.5, 0.2, 0.9)]
    tube("gr", pts, 0.017, M["bone"], p, segs=5)
    drip("grb", pts[1], 0.04, 0.01, M["blood"], p)


def g_skull(p):
    s = skull_prop("gs", (0, 0, -0.09), p, 1.25, 0.0, bloody=True)
    meat("gsm", (-0.08, 0.0, 0.0), 0.05, s, M["flesh"], 2)


def g_jaw(p):
    for sgn in (1, -1):
        bone("gj%d" % sgn, (0, sgn * 0.06, 0), (0.1, sgn * 0.02, -0.01), 0.02, M["bone"], p)
        bone("gjr%d" % sgn, (0, sgn * 0.06, 0), (-0.01, sgn * 0.065, 0.06), 0.018, M["bone"], p)
    for k in range(4):
        box("gjt%d" % k, (0.014, 0.014, 0.025), (0.06 + (k % 2) * 0.03, -0.03 + k * 0.02, 0.02), M["tooth"], p)


def g_meat(p):
    meat("gm", (0, 0, 0), 0.13, p, M["flesh"], 4)
    sphere("gmf", 0.04, (0.05, 0.03, 0.05), M["guts"], p, segs=6, rings=4, smooth=True)


def g_meat_green(p):
    meat("gmg", (0, 0, 0), 0.12, p, M["zskin"], 3)
    meat("gmg2", (0.04, 0, 0.02), 0.07, p, M["flesh"], 2)


def g_gut(p):
    RNG.seed(11)
    guts("gg", (-0.12, 0, 0), (1, 0.5, 0.2), 8, 0.032, p, droop=0.0)


def g_eye(p):
    sphere("ge", 0.07, (0, 0, 0), M["white"], p, segs=10, rings=7, smooth=True)
    cyl("gei", 0.035, 0.02, (0.065, 0, 0), M["glow_red"], p, rot=(0, PI / 2, 0), segs=10)
    cyl("gep", 0.015, 0.02, (0.073, 0, 0), M["black"], p, rot=(0, PI / 2, 0), segs=8)
    wire("gen", (-0.06, 0, 0), (-0.2, 0.05, -0.02), 0.0, 0.014, M["vein"], p, 4, bulge=(0, 0.04, 0.03))


def g_chitin(p):
    sphere("gc", 0.14, (0, 0, 0), M["chitin"], p, (1.2, 1, 0.35), 8, 6, True)
    spike("gcs", (0, 0, 0.03), (-0.04, 0.02, 0.14), 0.025, M["chitin2"], p)
    meat("gcm", (0, 0, -0.03), 0.06, p, M["slime"], 2)


def g_spiderleg(p):
    bone("gl1", (-0.2, 0, 0), (0.05, 0, 0.06), 0.035, M["chitin"], p, r2=0.03)
    sphere("glk", 0.04, (0.05, 0, 0.06), M["chitin2"], p)
    bone("gl2", (0.05, 0, 0.06), (0.22, 0, -0.05), 0.028, M["chitin"], p, r2=0.006)
    sphere("glg", 0.04, (-0.2, 0, 0), M["slime"], p, segs=6, rings=4, smooth=True)


def g_leech(p):
    sphere("gls", 0.13, (0, 0, 0), M["leech"], p, (0.8, 1, 0.8), 10, 7, True)
    sphere("glsp", 0.05, (0, 0, 0.1), M["glow_green"], p)
    cyl("glcut", 0.1, 0.01, (-0.1, 0, 0), M["blood"], p, rot=(0, PI / 2, 0), segs=10)
    drip("gld", (0, 0, -0.08), 0.06, 0.015, M["slime"], p)


def g_metal(p):
    box("gp", (0.22, 0.16, 0.02), (0, 0, 0), M["steel2"], p, (0.2, 0.1, 0.3))
    box("gp2", (0.1, 0.16, 0.02), (0.13, 0, 0.03), M["steel2"], p, (0, -0.5, 0.3))
    bolts("gpb", (0, 0, 0.015), "z", 0.06, p, 3)


def g_gear(p):
    cyl("gg", 0.09, 0.03, (0, 0, 0), M["chrome"], p, segs=12)
    for k in range(8):
        a = 2 * PI * k / 8
        box("gt%d" % k, (0.04, 0.03, 0.03), (math.cos(a) * 0.1, math.sin(a) * 0.1, 0), M["chrome"], p, (0, 0, a))
    cyl("gh", 0.03, 0.04, (0, 0, 0), M["black"], p, segs=8)


def g_wire(p):
    for k, c in enumerate(("wire_red", "wire_yellow", "rubber")):
        wire("gw%d" % k, (-0.15, -0.02 + k * 0.02, 0), (0.15, 0.05 - k * 0.04, 0.03), 0.0, 0.012, M[c], p, 5,
             bulge=(0, 0.06 * (k - 1), 0.05), wobble=0.02)
    sphere("gws", 0.025, (0.16, 0.0, 0.03), M["glow_yellow"], p, segs=6, rings=4)


def g_chrome(p):
    bone("gcb", (-0.14, 0, 0), (0.14, 0, 0), 0.03, M["chrome"], p)
    sphere("gcj", 0.045, (0.14, 0, 0), M["chrome"], p)
    wire("gcw", (-0.14, 0, 0), (-0.22, 0.04, -0.04), 0.0, 0.01, M["wire_red"], p, 3, wobble=0.01)


def g_armor(p):
    box("ga", (0.19, 0.13, 0.08), (0, 0, 0), M["armor"], p)
    bolts("gab", (0, 0, 0.041), "z", 0.05, p, 4)


def g_pod(p):
    meat("gpd", (0, 0, 0), 0.13, p, M["leech"], 3)
    sphere("gpg", 0.06, (0.05, 0.02, 0.06), M["glow_green"], p)
    spike("gpt", (0, 0, 0.05), (0.03, 0, 0.14), 0.02, M["tooth"], p)


def g_barrel(p):
    box("gbr", (0.22, 0.02, 0.2), (0, 0, 0), M["barrel"], p, (0, 0, 0.2))
    box("gbb", (0.22, 0.025, 0.04), (0, 0, 0.08), M["darkmetal"], p, (0, 0, 0.2))
    drip("gbs", (0.05, 0, -0.05), 0.07, 0.02, M["slime"], p)


mat("mutant", (0.34, 0.2, 0.2), 0.0, 0.55)
mat("mutant2", (0.3, 0.33, 0.12), 0.0, 0.5)
mat("mech", (0.55, 0.42, 0.05), 0.4, 0.4)
mat("flame", (1.0, 0.3, 0.03), 0, 0.3, (1.0, 0.28, 0.02), 3.0)
mat("flame2", (0.9, 0.08, 0.01), 0, 0.3, (1.0, 0.1, 0.01), 2.5)


def biped_legs(root, hip_z, spread, thigh, shin, r_thigh, r_shin, mat_thigh, mat_shin, foot, mat_foot, prefix):
    J = {}
    for side, y in (("L", spread), ("R", -spread)):
        hip = empty(prefix + "hip" + side, (0, y, hip_z), root)
        bone(prefix + "th" + side, (0, 0, 0), (0, 0, -thigh), r_thigh, mat_thigh, hip, r2=r_thigh * 0.85)
        knee = empty(prefix + "kn" + side, (0, 0, -thigh), hip)
        sphere(prefix + "kb" + side, r_shin * 1.15, (0, 0, 0), mat_shin, knee, segs=6, rings=4)
        bone(prefix + "sh" + side, (0, 0, 0), (0, 0, -shin), r_shin, mat_shin, knee, r2=r_shin * 0.8)
        ankle = empty(prefix + "an" + side, (0, 0, -shin), knee)
        box(prefix + "ft" + side, foot, (foot[0] * 0.3, 0, -foot[2] / 2), mat_foot, ankle)
        J[side] = (hip, knee, ankle)
    return J


def walk_legs(J, t, amp=0.45, bend=0.6):
    for side, off in (("L", 0.0), ("R", 0.5)):
        hip, knee, ankle = J[side]
        ph = 2 * PI * (t + off)
        sw = math.sin(ph) * amp
        bd = 0.08 + bend * max(0.0, math.cos(ph))
        hip.rotation_euler.y = -sw
        knee.rotation_euler.y = bd
        ankle.rotation_euler.y = (sw - bd) * 0.8


def build_brute():
    root = empty("b_root")
    J = biped_legs(root, 0.88, 0.2, 0.44, 0.42, 0.11, 0.085, M["zcloth"], M["mutant"], (0.3, 0.18, 0.1), M["rust2"], "b")
    body = empty("b_body", (0, 0, 0), root)
    box("bpelvis", (0.32, 0.52, 0.22), (0, 0, 0.92), M["zcloth"], body)
    box("bbelt", (0.34, 0.54, 0.06), (0, 0, 1.0), M["rust"], body)
    for k, y in enumerate((-0.14, 0.14)):
        skull_prop("bbs%d" % k, (0.17, y, 0.93), body, 0.8, 0.0)
    torso = empty("b_torso", (0, 0, 1.0), body, (0, 0.35, 0))
    sphere("bchest", 0.38, (0.02, 0, 0.36), M["mutant"], torso, (0.9, 1.25, 1.0), 12, 8, True)
    sphere("bbelly", 0.3, (0.1, 0, 0.08), M["mutant"], torso, (1, 1.1, 0.9), 10, 7, True)
    for k in range(5):
        meat("bmus%d" % k, (RNG.uniform(0.1, 0.3), RNG.uniform(-0.35, 0.35), RNG.uniform(0.1, 0.5)), 0.12, torso, M["flesh"], 2)
    for k in range(6):
        y = (k - 2.5) * 0.12
        spike("bspk%d" % k, (-0.25, y, 0.4 + abs(y) * 0.3), (-0.48, y * 1.3, 0.62 + abs(y) * 0.2), 0.05, M["bone_dirty"], torso)
    box("btank", (0.14, 0.2, 0.26), (-0.32, 0.1, 0.3), M["glow_green"], torso)
    box("btankc", (0.16, 0.22, 0.04), (-0.32, 0.1, 0.45), M["rust"], torso)
    wire("btube1", (-0.32, 0.1, 0.45), (0.12, 0.05, 0.7), 0.0, 0.025, M["rubber"], torso, 6, bulge=(-0.1, 0, 0.12))
    wire("btube2", (-0.3, -0.1, 0.3), (0.1, -0.08, 0.66), 0.0, 0.02, M["rust"], torso, 6, bulge=(-0.12, 0, 0.1))
    head = empty("b_head", (0.24, 0, 0.66), torso, (0, -0.3, 0))
    sphere("bhead", 0.13, (0, 0, 0.04), M["mutant"], head, (1, 0.95, 0.9), 8, 6, True)
    box("bjaw", (0.15, 0.2, 0.08), (0.06, 0, -0.06), M["mutant"], head)
    for s in (1, -1):
        spike("btusk%d" % s, (0.12, s * 0.07, -0.05), (0.17, s * 0.09, 0.07), 0.025, M["tooth"], head)
        sphere("beye%d" % s, 0.025, (0.12, s * 0.045, 0.07), M["glow_yellow"], head)
    box("bplate", (0.14, 0.16, 0.04), (-0.02, 0, 0.15), M["chrome"], head, (0, 0.2, 0))
    bolts("bpb", (-0.02, 0, 0.175), "z", 0.05, head, 4)
    drip("bdrool", (0.13, 0, -0.1), 0.15, 0.014, M["blood"], head)
    arms = {}
    for side, y in (("L", 0.46), ("R", -0.46)):
        sphere("bsho" + side, 0.17, (0, y, 0.5), M["mutant"], torso, segs=9, rings=6, smooth=True)
        sh = empty("bsh" + side, (0, y * 1.05, 0.48), torso)
        if side == "L":
            bone("bup", (0, 0, 0), (0.15, 0.05, -0.38), 0.1, M["mutant"], sh)
            bone("bfo", (0.15, 0.05, -0.38), (0.38, 0.03, -0.66), 0.13, M["mutant"], sh, r2=0.1)
            sphere("bfist", 0.14, (0.4, 0.03, -0.72), M["mutant"], sh, segs=9, rings=6, smooth=True)
            for k in range(3):
                spike("barmsp%d" % k, (0.2 + k * 0.07, 0.1, -0.42 - k * 0.08), (0.18 + k * 0.07, 0.24, -0.38 - k * 0.08),
                      0.03, M["bone_dirty"], sh)
        else:
            bone("bcup", (0, 0, 0), (0.12, -0.04, -0.36), 0.07, M["chrome"], sh)
            sphere("bcel", 0.08, (0.12, -0.04, -0.36), M["darkmetal"], sh)
            bone("bpist", (0.05, -0.08, -0.05), (0.14, -0.1, -0.34), 0.025, M["chrome"], sh)
            box("bcfo", (0.36, 0.14, 0.14), (0.28, -0.03, -0.55), M["darkmetal"], sh, (0, 0.7, 0))
            sphere("bclight", 0.03, (0.3, -0.11, -0.52), M["glow_red"], sh)
            for k in range(3):
                a = (k - 1) * 0.5
                spike("bclaw%d" % k, (0.4, -0.03 + math.sin(a) * 0.06, -0.7), (0.52, -0.03 + math.sin(a) * 0.12, -0.92),
                      0.035, M["chrome"], sh)
            wire("bcw", (0.0, -0.05, 0.0), (0.24, -0.1, -0.48), 0.0, 0.018, M["wire_red"], sh, 5, bulge=(-0.05, -0.06, 0))
        arms[side] = sh

    def pose(anim, t):
        walk_legs(J, t, 0.35, 0.5)
        ph = 2 * PI * t
        body.rotation_euler.x = math.sin(ph) * 0.08
        body.location.z = -abs(math.sin(ph)) * 0.05
        arms["L"].rotation_euler.y = math.sin(ph) * 0.3
        arms["R"].rotation_euler.y = -math.sin(ph) * 0.3
    return root, pose


def build_crawler():
    root = empty("c_root")
    body = empty("c_body", (0, 0, 0.3), root)
    sphere("cskull", 0.2, (0, 0, 0.05), M["bone"], body, (1.15, 0.95, 0.85), 10, 8, True)
    box("cjaw", (0.16, 0.17, 0.06), (0.12, 0, -0.08), M["bone"], body)
    for k in range(6):
        box("ctooth%d" % k, (0.018, 0.02, 0.03), (0.2, -0.06 + k * 0.024, -0.04), M["tooth"], body)
    sphere("csock", 0.04, (0.2, 0.06, 0.07), M["black"], body)
    sphere("ceye", 0.045, (0.2, -0.06, 0.07), M["glow_red"], body)
    ring("clens", 0.05, 0.03, (0.21, -0.06, 0.07), M["chrome"], body, rot=(0, PI / 2, 0))
    box("cplate", (0.18, 0.16, 0.04), (-0.04, 0, 0.22), M["chrome"], body, (0, 0.15, 0))
    bone("cant", (-0.08, 0.05, 0.22), (-0.15, 0.08, 0.4), 0.008, M["chrome"], body)
    sphere("cantt", 0.016, (-0.15, 0.08, 0.4), M["glow_red"], body)
    for s in (1, -1):
        spike("cmand%d" % s, (0.18, s * 0.08, -0.06), (0.3, s * 0.03, -0.12), 0.025, M["chrome"], body)
    drip("cdrip", (0.2, 0, -0.1), 0.08, 0.012, M["blood"], body)
    legs = []
    for s in (1, -1):
        for i, ang in enumerate((50, 95, 140)):
            base = s * math.radians(ang)
            hip = empty("chip%d%d" % (s, i), (0.05 - i * 0.07, s * 0.12, -0.02), body, (0, 0, base))
            lift = empty("clift%d%d" % (s, i), (0, 0, 0), hip)
            bone("cf%d%d" % (s, i), (0, 0, 0), (0.22, 0, 0.14), 0.022, M["chrome"], lift)
            sphere("ck%d%d" % (s, i), 0.028, (0.22, 0, 0.14), M["darkmetal"], lift)
            bone("ct%d%d" % (s, i), (0.22, 0, 0.14), (0.42, 0, -0.28), 0.018, M["chrome"], lift, r2=0.006)
            legs.append((hip, lift, base, s, 0.0 if (i % 2 == 0) == (s == 1) else 0.5))

    def pose(anim, t):
        for hip, lift, base, s, off in legs:
            p = 2 * PI * (t + off)
            hip.rotation_euler.z = base + s * 0.3 * math.cos(p)
            lift.rotation_euler.y = -0.4 * max(0.0, math.sin(p))
        body.location.z = 0.3 + math.sin(4 * PI * t) * 0.025
    return root, pose


def build_spitter():
    root = empty("sp_root")
    J = biped_legs(root, 0.74, 0.09, 0.36, 0.33, 0.045, 0.035, M["mutant2"], M["mutant2"], (0.16, 0.08, 0.05), M["zskin2"], "sp")
    body = empty("sp_body", (0, 0, 0), root)
    box("sppel", (0.16, 0.24, 0.12), (0, 0, 0.78), M["zcloth"], body)
    torso = empty("sp_torso", (0, 0, 0.8), body, (0, 0.55, 0))
    sphere("spchest", 0.16, (0, 0, 0.2), M["mutant2"], torso, (0.9, 1.1, 1.3), 9, 7, True)
    for k in range(7):
        sphere("sppus%d" % k, RNG.uniform(0.03, 0.05), (-0.13, RNG.uniform(-0.12, 0.12), RNG.uniform(0.08, 0.36)), M["glow_green"], torso)
    for k in range(4):
        spike("spsp%d" % k, (-0.12, 0, 0.1 + k * 0.08), (-0.22, 0, 0.13 + k * 0.08), 0.02, M["bone_dirty"], torso)
    neck = empty("sp_neck", (0.05, 0, 0.38), torso, (0, -0.4, 0))
    bone("spneck", (0, 0, 0), (0.18, 0, 0.14), 0.05, M["mutant2"], neck)
    sphere("spsac", 0.16, (0.12, 0, 0.0), M["slime"], neck, (1.1, 1.0, 0.9), 10, 8, True)
    for k in range(4):
        a = k * 1.4
        wire("spvein%d" % k, (0.12 + math.cos(a) * 0.08, math.sin(a) * 0.14, 0.12), (0.18, math.sin(a) * 0.1, -0.12),
             0.0, 0.01, M["vein"], neck, 4, bulge=(0.08, 0, 0))
    sphere("sphead", 0.1, (0.24, 0, 0.2), M["mutant2"], neck, (1.4, 0.9, 0.8), 8, 6, True)
    cyl("spmouth", 0.06, 0.02, (0.37, 0, 0.17), M["glow_green"], neck, rot=(0, PI / 2, 0))
    for k in range(6):
        a = k * PI / 3
        spike("spt%d" % k, (0.37, math.cos(a) * 0.06, 0.17 + math.sin(a) * 0.05), (0.42, math.cos(a) * 0.035, 0.17 + math.sin(a) * 0.03),
              0.012, M["tooth"], neck)
    for k in range(3):
        drip("spdrool%d" % k, (0.37, -0.03 + k * 0.03, 0.12), RNG.uniform(0.1, 0.2), 0.012, M["slime"], neck)
    for s in (1, -1):
        sphere("speye%d" % s, 0.02, (0.33, s * 0.05, 0.25), M["glow_yellow"], neck)
    arms = {}
    for side, y in (("L", 0.14), ("R", -0.14)):
        sh = empty("spsh" + side, (0, y, 0.3), torso)
        bone("spup" + side, (0, 0, 0), (0.12, 0, -0.2), 0.03, M["mutant2"], sh)
        bone("spfo" + side, (0.12, 0, -0.2), (0.3, 0, -0.22), 0.025, M["mutant2"], sh)
        for k in range(3):
            spike("spcl%s%d" % (side, k), (0.3, -0.02 + k * 0.02, -0.22), (0.38, -0.03 + k * 0.03, -0.28), 0.012, M["bone"], sh)
        arms[side] = sh

    def pose(anim, t):
        walk_legs(J, t, 0.35, 0.5)
        ph = 2 * PI * t
        body.rotation_euler.x = math.sin(ph) * 0.1
        neck.rotation_euler.x = math.sin(ph + 1) * 0.2
        neck.scale = (1, 1, 1)
        for k, side in enumerate(("L", "R")):
            arms[side].rotation_euler.y = math.sin(ph + k * PI) * 0.25
    return root, pose


def build_turret():
    root = empty("t_root")
    for k in range(3):
        a = 2 * PI * k / 3 + PI / 3
        bone("tleg%d" % k, (0, 0, 0.42), (math.cos(a) * 0.42, math.sin(a) * 0.42, 0.0), 0.03, M["darkmetal"], root)
        box("tfoot%d" % k, (0.1, 0.1, 0.03), (math.cos(a) * 0.42, math.sin(a) * 0.42, 0.015), M["mech"], root)
    cyl("tbase", 0.14, 0.12, (0, 0, 0.45), M["mech"], root, segs=10)
    head = empty("t_head", (0, 0, 0.6), root)
    box("thead", (0.34, 0.3, 0.2), (0, 0, 0), M["darkmetal"], head)
    box("tarmor", (0.3, 0.32, 0.05), (0.02, 0, 0.12), M["mech"], head)
    for s in (1, -1):
        bone("tbar%d" % s, (0.15, s * 0.07, -0.02), (0.55, s * 0.07, -0.02), 0.025, M["chrome"], head)
        ring("tmz%d" % s, 0.032, 0.04, (0.55, s * 0.07, -0.02), M["darkmetal"], head, rot=(0, PI / 2, 0))
    box("tsensor", (0.06, 0.12, 0.05), (0.17, 0, 0.08), M["black"], head)
    sphere("teye", 0.035, (0.2, 0, 0.08), M["glow_red"], head)
    box("tammo", (0.16, 0.12, 0.12), (-0.05, 0.22, -0.04), M["crate"], head)
    for k in range(5):
        box("tbelt%d" % k, (0.03, 0.04, 0.02), (0.03 + k * 0.03, 0.14, -0.06 + math.sin(k) * 0.01), M["hazard"], head)
    wire("tcab", (-0.15, -0.1, -0.08), (-0.1, -0.2, -0.55), 0.0, 0.018, M["rubber"], head, 6, bulge=(-0.12, -0.05, 0))
    dish = empty("t_dish", (-0.08, 0, 0.18), head)
    bone("tdpole", (0, 0, 0), (0, 0, 0.1), 0.01, M["chrome"], dish)
    cyl("tdish", 0.07, 0.02, (0.02, 0, 0.12), M["steel2"], dish, rot=(0, 1.2, 0), segs=10)
    sphere("tblink", 0.02, (-0.15, -0.1, 0.12), M["glow_red"], head)

    def pose(anim, t):
        dish.rotation_euler.z = 2 * PI * t
        head.location.z = 0.6 + math.sin(2 * PI * t) * 0.005
    return root, pose


def build_walker():
    root = empty("w_root")
    body = empty("w_body", (0, 0, 1.0), root)
    box("wcock", (0.5, 0.44, 0.34), (0, 0, 0.05), M["mech"], body)
    box("wtop", (0.4, 0.38, 0.06), (-0.03, 0, 0.25), M["darkmetal"], body)
    box("wvisor", (0.04, 0.3, 0.08), (0.255, 0, 0.1), M["glow_red"], body)
    box("wchin", (0.12, 0.4, 0.1), (0.22, 0, -0.08), M["darkmetal"], body, (0, 0.4, 0))
    bolts("wbb", (0.252, 0, 0.0), "x", 0.12, body, 4)
    for s in (1, -1):
        pod = empty("wpod%d" % s, (0.0, s * 0.33, 0.08), body)
        box("wpodb%d" % s, (0.34, 0.14, 0.2), (0, 0, 0), M["darkmetal"], pod)
        for k in range(4):
            yy, zz = (k % 2 - 0.5) * 0.06, (k // 2 - 0.5) * 0.08
            cyl("wrk%d%d" % (s, k), 0.025, 0.06, (0.19, yy, zz), M["armor"], pod, rot=(0, PI / 2, 0), r2=0.004)
        wire("wpw%d" % s, (-0.1, -s * 0.05, -0.1), (-0.2, -s * 0.12, -0.05), 0.04, 0.014, M["wire_red"], pod, 4)
    for s in (1, -1):
        bone("wexh%d" % s, (-0.25, s * 0.12, 0.1), (-0.35, s * 0.12, 0.35), 0.03, M["darkmetal"], body)
        sphere("wexg%d" % s, 0.025, (-0.35, s * 0.12, 0.36), M["glow_orange"], body)
    bone("want", (-0.15, 0.1, 0.28), (-0.2, 0.12, 0.55), 0.008, M["chrome"], body)
    sphere("wantt", 0.018, (-0.2, 0.12, 0.55), M["glow_red"], body)
    wire("wbelly", (-0.15, 0.15, -0.12), (0.1, -0.15, -0.12), 0.08, 0.02, M["rubber"], body, 6)
    J = {}
    for side, y in (("L", 0.2), ("R", -0.2)):
        hip = empty("whip" + side, (0, y, -0.12), body)
        sphere("whb" + side, 0.07, (0, 0, 0), M["darkmetal"], hip)
        bone("wth" + side, (0, 0, 0), (0.22, 0, -0.38), 0.05, M["mech"], hip)
        bone("wpis" + side, (0.04, 0.05, -0.05), (0.2, 0.05, -0.32), 0.018, M["chrome"], hip)
        knee = empty("wkn" + side, (0.22, 0, -0.38), hip)
        sphere("wkb" + side, 0.06, (0, 0, 0), M["darkmetal"], knee)
        bone("wsh" + side, (0, 0, 0), (-0.2, 0, -0.42), 0.04, M["darkmetal"], knee)
        ankle = empty("wan" + side, (-0.2, 0, -0.42), knee)
        for k in (-1, 0, 1):
            spike("wtoe%s%d" % (side, k), (0, 0, 0), (0.16, k * 0.08, -0.08), 0.03, M["mech"], ankle)
        spike("wheel" + side, (0, 0, 0), (-0.12, 0, -0.08), 0.03, M["mech"], ankle)
        J[side] = (hip, knee, ankle)

    def pose(anim, t):
        for side, off in (("L", 0.0), ("R", 0.5)):
            hip, knee, ankle = J[side]
            ph = 2 * PI * (t + off)
            sw = math.sin(ph) * 0.4
            lift = 0.4 * max(0.0, math.cos(ph))
            hip.rotation_euler.y = -sw - lift * 0.5
            knee.rotation_euler.y = -lift * 0.3
            ankle.rotation_euler.y = sw + lift * 0.8
        body.location.z = 1.0 - abs(math.sin(2 * PI * t)) * 0.04
        body.rotation_euler.x = math.sin(2 * PI * t) * 0.04
    return root, pose


def build_bloater():
    root = empty("bl_root")
    J = biped_legs(root, 0.36, 0.14, 0.18, 0.17, 0.06, 0.05, M["mutant2"], M["mutant2"], (0.16, 0.1, 0.05), M["zskin2"], "bl")
    body = empty("bl_body", (0, 0, 0), root)
    sphere("blbelly", 0.42, (0.04, 0, 0.72), M["mutant2"], body, (1.1, 1.05, 1.0), 14, 10, True)
    for k in range(14):
        a, b = RNG.uniform(-1.3, 1.3), RNG.uniform(-0.7, 1.0)
        p = Vector((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b))) * 0.43
        sphere("blpus%d" % k, RNG.uniform(0.03, 0.07), Vector((0.04, 0, 0.72)) + Vector((p.x * 1.1, p.y * 1.05, p.z)),
               M["glow_green"] if k % 3 else M["slime"], body, segs=8, rings=6, smooth=True)
    for k in range(6):
        a = RNG.uniform(0, 2 * PI)
        p1 = Vector((0.04 + math.cos(a) * 0.3, math.sin(a) * 0.3, 1.05))
        p2 = Vector((0.3 + math.cos(a) * 0.15, math.sin(a) * 0.3, 0.55))
        wire("blvein%d" % k, p1, p2, 0.0, 0.012, M["vein"], body, 5, bulge=(0.15, 0, 0), wobble=0.02)
    for k in range(4):
        bone("blstitch%d" % k, (0.44, -0.12 + k * 0.08, 0.68), (0.44, -0.12 + k * 0.08, 0.8), 0.008, M["black"], body)
    sphere("blnavel", 0.04, (0.46, 0.08, 0.6), M["slime"], body)
    drip("blooze", (0.47, 0.08, 0.58), 0.18, 0.018, M["slime"], body)
    head = empty("bl_head", (0.1, 0, 1.15), body)
    sphere("blhead", 0.11, (0, 0, 0.05), M["mutant2"], head, segs=8, rings=6, smooth=True)
    for s in (1, -1):
        sphere("bleye%d" % s, 0.022, (0.1, s * 0.04, 0.08), M["glow_yellow"], head)
    box("blmouth", (0.04, 0.08, 0.03), (0.1, 0, 0.0), M["blood"], head)
    drip("bldrool", (0.11, 0, -0.01), 0.12, 0.012, M["slime"], head)
    arms = {}
    for side, y in (("L", 0.4), ("R", -0.4)):
        sh = empty("blsh" + side, (0.05, y, 0.85), body)
        bone("blarm" + side, (0, 0, 0), (0.15, y * 0.3, -0.25), 0.045, M["mutant2"], sh)
        sphere("blhand" + side, 0.05, (0.16, y * 0.3, -0.27), M["zskin2"], sh)
        arms[side] = sh

    def pose(anim, t):
        walk_legs(J, t, 0.4, 0.4)
        ph = 2 * PI * t
        body.rotation_euler.x = math.sin(ph) * 0.15
        body.location.z = -abs(math.sin(ph)) * 0.04
        s = 1 + 0.03 * math.sin(2 * ph)
        head.rotation_euler.x = -math.sin(ph) * 0.2
        for k, side in enumerate(("L", "R")):
            arms[side].rotation_euler.x = math.sin(ph + k * PI) * 0.3
    return root, pose


def build_skull():
    root = empty("fs_root")
    body = empty("fs_body", (0, 0, 1.0), root)
    sphere("fsskull", 0.22, (0, 0, 0.04), M["bone"], body, (1.15, 0.92, 0.95), 12, 8, True)
    box("fsjaw", (0.2, 0.22, 0.07), (0.1, 0, -0.17), M["chrome"], body, (0, 0.15, 0))
    for k in range(7):
        box("fstooth%d" % k, (0.02, 0.022, 0.035), (0.22, -0.075 + k * 0.025, -0.11), M["tooth"], body)
    for s in (1, -1):
        sphere("fssock%d" % s, 0.055, (0.2, s * 0.075, 0.06), M["black"], body)
        sphere("fseye%d" % s, 0.035, (0.23, s * 0.075, 0.06), M["glow_orange"], body)
    box("fsnose", (0.03, 0.04, 0.05), (0.245, 0, -0.03), M["black"], body)
    bolts("fsb", (0.0, 0, 0.245), "z", 0.1, body, 6)
    box("fscrack", (0.005, 0.008, 0.12), (0.18, -0.12, 0.15), M["black"], body, (0.5, 0, 0))
    flames = []
    for k in range(9):
        a = RNG.uniform(-1.2, 1.2)
        b = RNG.uniform(0.2, 1.2)
        base = Vector((-0.08, math.sin(a) * 0.14, 0.12 + b * 0.06))
        tip = base + Vector((-0.35 - RNG.uniform(0, 0.2), math.sin(a) * 0.15, 0.15 + b * 0.15))
        f = empty("fsfl%d" % k, base, body)
        spike("fsflame%d" % k, (0, 0, 0), tip - base, 0.08 * RNG.uniform(0.6, 1.0), M["flame" if k % 2 else "flame2"], f)
        flames.append((f, RNG.uniform(0, 2 * PI)))

    def pose(anim, t):
        ph = 2 * PI * t
        body.location.z = 1.0 + math.sin(ph) * 0.06
        body.rotation_euler.x = math.sin(ph) * 0.08
        for f, o in flames:
            s = 0.75 + 0.35 * (0.5 + 0.5 * math.sin(ph * 2 + o))
            f.scale = (s, 1, s)
    return root, pose


def g_plank(p):
    box("gpl", (0.32, 0.08, 0.025), (0, 0, 0), M["crate"], p, (0, 0, 0.1))
    for k in (-0.12, 0.12):
        bone("gpn%.2f" % k, (k, 0, 0.0), (k, 0, 0.05), 0.006, M["chrome"], p)


mat("hellskin", (0.22, 0.07, 0.04), 0.1, 0.45)
mat("bandage", (0.5, 0.45, 0.36), 0.0, 0.9)
mat("labwhite", (0.62, 0.64, 0.68), 0.2, 0.5)
mat("ice", (0.6, 0.75, 0.9), 0.1, 0.08)
mat("snow", (0.82, 0.85, 0.9), 0.0, 0.9)
mat("charred", (0.04, 0.025, 0.02), 0.0, 0.8)
mat("hellrock", (0.11, 0.04, 0.03), 0.0, 0.85)
mat("lava", (1.0, 0.35, 0.05), 0, 0.3, (1.0, 0.3, 0.03), 4.0)
mat("ember", (1.0, 0.1, 0.02), 0, 0.3, (1.0, 0.08, 0.01), 3.0)
mat("candle", (0.85, 0.8, 0.62), 0.0, 0.5)
mat("candleflame", (1.0, 0.7, 0.2), 0, 0.3, (1.0, 0.65, 0.2), 6.0)
mat("muscle", (0.45, 0.05, 0.06), 0.0, 0.25)
mat("frost", (0.75, 0.85, 0.95), 0.0, 0.6)


# ---------------------------------------------------------------- shared bits
def tentacle(name, base, direction, n, seg, r, parent, material=None):
    """Chain of joints; returns list of joint empties to animate."""
    material = material or M["muscle"]
    d = Vector(direction).normalized()
    rot_ = d.to_track_quat("Z", "Y").to_euler()
    joint = empty(name + "_j0", base, parent, rot_)
    joints = [joint]
    for i in range(n):
        rr = r * (1 - i / (n + 1))
        bone("%s_s%d" % (name, i), (0, 0, 0), (0, 0, seg), rr, material, joint, r2=rr * 0.85)
        sphere("%s_b%d" % (name, i), rr * 1.05, (0, 0, seg), material, joint, segs=6, rings=4, smooth=True)
        if i < n - 1:
            joint = empty("%s_j%d" % (name, i + 1), (0, 0, seg), joint)
            joints.append(joint)
    spike(name + "_tip", (0, 0, seg), (0, 0, seg + r * 3), r * 0.6, M["bone"], joint)
    return joints


def candle(name, loc, h, parent):
    cyl(name, 0.025, h, (loc[0], loc[1], loc[2] + h / 2), M["candle"], parent, segs=6)
    sphere(name + "f", 0.018, (loc[0], loc[1], loc[2] + h + 0.025), M["candleflame"], parent, (1, 1, 1.6), 6, 4)
    drip(name + "w", (loc[0] + 0.02, loc[1], loc[2] + h), h * 0.4, 0.008, M["candle"], parent)


def stone_faces(r, mat_):
    for k in range(3):
        z = 0.2 + k * 0.33
        box("mx%d" % k, (0.01, 1.0, 0.02), (0.505, 0, z), M[mat_], r)
        box("my%d" % k, (1.0, 0.01, 0.02), (0, 0.505, z), M[mat_], r)
    for k in range(4):
        off = 0.25 if k % 2 else -0.15
        z = 0.03 + k * 0.33
        box("vx%d" % k, (0.01, 0.02, 0.31), (0.505, off, z + 0.17), M[mat_], r)
        box("vy%d" % k, (0.02, 0.01, 0.31), (off, 0.505, z + 0.17), M[mat_], r)


# ---------------------------------------------------------------- ossuary
def build_wall_crypt():
    r = wall_base("stone")
    stone_faces(r, "concrete2")
    if chance(0.7):
        u = RNG.uniform(-0.25, 0.25)
        box("niche", (0.04, 0.34, 0.3), (0.49, u, 0.45), M["black"], r)
        if chance(0.8):
            skull_prop("nsk", (0.43, u, 0.33), r, 1.1, RNG.uniform(-0.4, 0.4))
            bone_prop("nb", (0.45, u - 0.14, 0.32), (0.45, u + 0.14, 0.32), r)
    if chance(0.4):
        u = RNG.uniform(-0.25, 0.25)
        box("nichey", (0.34, 0.04, 0.3), (u, 0.49, 0.5), M["black"], r)
        skull_prop("nsky", (u, 0.43, 0.38), r, 1.0, PI / 2)
    for k in range(RNG.randint(0, 5)):
        candle("cn%d" % k, (RNG.uniform(-0.4, 0.4), RNG.uniform(-0.4, 0.4), 1.03), RNG.uniform(0.04, 0.16), r)
    if chance(0.3):
        for k in range(RNG.randint(2, 4)):
            box("cmoss%d" % k, (0.02, RNG.uniform(0.08, 0.2), RNG.uniform(0.06, 0.2)), (0.505, RNG.uniform(-0.4, 0.4), RNG.uniform(0.05, 0.4)),
                M["moss"], r)
    if chance(0.5):
        smear("cbl", (RNG.uniform(-0.3, 0.3), 0.505, 0.5), "y", 0.25, r, n=3)
    return r, None


def build_floor_flagstone():
    r = tile_root()
    slab(M["concrete2"])
    layout = RNG.choice(["2x2", "3x3", "long", "2x2"])
    if layout == "2x2":
        rects = [(x, y, 0.46, 0.46) for x in (-0.25, 0.25) for y in (-0.25, 0.25)]
    elif layout == "3x3":
        rects = [(x, y, 0.3, 0.3) for x in (-0.33, 0, 0.33) for y in (-0.33, 0, 0.33)]
    else:
        rects = [(-0.25, 0, 0.46, 0.95), (0.25, -0.25, 0.46, 0.46), (0.25, 0.25, 0.46, 0.46)]
    for k, (x, y, w, h) in enumerate(rects):
        if chance(0.06):
            continue   # a missing stone
        box("flag%d" % k, (w, h, 0.03), (x, y, 0.004 + RNG.uniform(0, 0.012)), M["stone"], r, (RNG.uniform(-0.02, 0.02), RNG.uniform(-0.02, 0.02),
            RNG.uniform(-0.04, 0.04)))
    rnd_cracks("crk", r, 0.02, RNG.randint(0, 2))
    if chance(0.25):
        for k in range(RNG.randint(2, 5)):
            box("moss%d" % k, (RNG.uniform(0.04, 0.1), RNG.uniform(0.04, 0.1), 0.006), (RNG.uniform(-0.4, 0.4), RNG.uniform(-0.4, 0.4), 0.02),
                M["moss"], r)
    if chance(0.12):
        candle("fc", (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), 0.02), RNG.uniform(0.05, 0.12), r)
    if chance(0.15):
        bone_prop("fb", (-0.2, 0.1, 0.05), (0.05, 0.25, 0.05), r)
    rnd_stain("fbl", r, "blood", 0.1, 0.025, (0.1, 0.25))
    return r, None


def build_candles():
    r = tile_root()
    pool("wax", (0, 0, 0.002), 0.4, r, M["candle"], 3)
    for k in range(7):
        a, d = RNG.uniform(0, 2 * PI), RNG.uniform(0, 0.25)
        candle("c%d" % k, (math.cos(a) * d, math.sin(a) * d, 0.0), RNG.uniform(0.08, 0.3), r)
    skull_prop("csk", (0.05, -0.05, 0.0), r, 0.9, 0.6)
    return r, None


def build_sarcophagus():
    r = tile_root()
    box("sbody", (0.8, 0.5, 0.42), (0, 0, 0.21), M["stone"], r)
    box("slid", (0.84, 0.54, 0.08), (0.05, 0.04, 0.46), M["stone"], r, (0, 0, 0.12))
    skull_prop("ssk", (0.08, 0.04, 0.5), r, 1.3, 0.12)
    for k in range(3):
        bone("sfinger%d" % k, (0.42, -0.2 + k * 0.04, 0.42), (0.5, -0.22 + k * 0.05, 0.3), 0.012, M["bone"], r)
    box("sband", (0.82, 0.52, 0.04), (0, 0, 0.08), M["concrete2"], r)
    smear("sbl", (0.405, 0.1, 0.25), "x", 0.2, r, n=2)
    return r, None


# ---------------------------------------------------------------- otherworld (rust)
def build_wall_rust():
    r = wall_base("rust2", "rust2")
    for k in range(2):
        box("plx%d" % k, (0.02, 0.46, 0.44), (0.51, -0.24 + k * 0.48, 0.5 + RNG.uniform(-0.05, 0.05)), M["rust"], r)
        box("ply%d" % k, (0.46, 0.02, 0.44), (-0.24 + k * 0.48, 0.51, 0.5 + RNG.uniform(-0.05, 0.05)), M["rust"], r)
    bolts("rbx", (0.522, -0.24, 0.5), "x", 0.18, r, 4)
    bolts("rby", (0.24, 0.522, 0.5), "y", 0.18, r, 4)
    for k in range(RNG.randint(1, 3)):
        smear("rbl%d" % k, (0.53, RNG.uniform(-0.3, 0.3), RNG.uniform(0.35, 0.8)), "x", RNG.uniform(0.3, 0.5), r, n=5)
    if chance(0.6):
        smear("rbly", (RNG.uniform(-0.3, 0.3), 0.53, RNG.uniform(0.3, 0.7)), "y", 0.45, r, n=5)
    if chance(0.6):
        for k in range(6):
            box("meshv%d" % k, (0.01, 0.01, 0.6), (0.54, -0.45 + k * 0.07, 0.35), M["darkmetal"], r, (0.5, 0, 0))
            box("meshw%d" % k, (0.01, 0.01, 0.6), (0.54, -0.45 + k * 0.07, 0.35), M["darkmetal"], r, (-0.5, 0, 0))
    if chance(0.5):
        for k in range(RNG.randint(1, 3)):
            y0 = RNG.uniform(-0.3, 0.4)
            wire("chain%d" % k, (0.55, y0, 1.0), (0.56, y0 + 0.02, RNG.uniform(0.3, 0.7)), 0.0, 0.012, M["darkmetal"], r, 6, wobble=0.01)
    if chance(0.25):
        meat("rhook", (0.6, RNG.uniform(-0.2, 0.2), 0.55), 0.1, r, M["flesh"], 3)
    return r, None


def build_wall_fence():
    r = tile_root()
    box("fbase", (1.0, 1.0, 0.18), (0, 0, 0.09), M["concrete"], r)
    for x in (-0.47, 0.47):
        for y in (-0.47, 0.47):
            cyl("post", 0.03, 1.0, (x, y, 0.5), M["rust"], r, segs=6)
    for side in range(4):
        for k in range(8):
            u = -0.45 + k * 0.13
            for sgn in (1, -1):
                if side == 0:
                    loc, rot_ = (0.48, u, 0.58), (sgn * 0.6, 0, 0)
                elif side == 1:
                    loc, rot_ = (u, 0.48, 0.58), (0, sgn * 0.6, 0)
                elif side == 2:
                    loc, rot_ = (-0.48, u, 0.58), (sgn * 0.6, 0, 0)
                else:
                    loc, rot_ = (u, -0.48, 0.58), (0, sgn * 0.6, 0)
                box("m%d%d%d" % (side, k, sgn), (0.008, 0.008, 0.95), loc, M["darkmetal"], r, rot_)
    for k in range(3):
        ring("barb%d" % k, 0.07, 0.01, (0.48, -0.3 + k * 0.3, 1.04), M["darkmetal"], r, rot=(0, PI / 2, 0), segs=8)
        ring("barby%d" % k, 0.07, 0.01, (-0.3 + k * 0.3, 0.48, 1.04), M["darkmetal"], r, rot=(PI / 2, 0, 0), segs=8)
    meat("fmeat", (0.5, 0.2, 0.7), 0.08, r, M["flesh"], 2)
    drip("fdrip", (0.52, 0.2, 0.65), 0.2, 0.012, M["blood"], r)
    return r, None


def build_floor_rustgrate():
    r = tile_root()
    slab(M["black"], -0.1)
    if chance(0.75):
        box("deepglow", (0.9, 0.9, 0.01), (0, 0, -0.09), M["ember"], r)
    n = RNG.randint(4, 7)
    for k in range(n):
        u = -0.42 + k * 0.84 / (n - 1)
        box("gx%d" % k, (0.98, 0.04, 0.04), (0, u, -0.02), M["rust"], r)
        if chance(0.85):
            box("gy%d" % k, (0.04, 0.98, 0.03), (u, 0, -0.03), M["rust2"], r)
    for (sx, sy, x, y) in ((1.02, 0.06, 0, 0.48), (1.02, 0.06, 0, -0.48), (0.06, 1.02, 0.48, 0), (0.06, 1.02, -0.48, 0)):
        box("gf", (sx, sy, 0.05), (x, y, -0.025), M["rust2"], r)
    if chance(0.2):
        meat("rgm", (RNG.uniform(-0.2, 0.2), RNG.uniform(-0.2, 0.2), 0.0), 0.07, r, M["flesh"], 2)
    return r, None


def build_floor_rust():
    r = tile_root()
    slab(M["rust2"])
    rects = plates("rplate", r, "rust", RNG.choice(["one", "twox", "twoy", "four"]))
    for k, (x, y, w, h) in enumerate(rects):
        if chance(0.5):
            for sx in (-1, 1):
                sphere("rrv%d%d" % (k, sx), 0.02, (x + sx * (w / 2 - 0.05), y + h / 2 - 0.05, 0.014), M["darkmetal"], r)
    for k in range(RNG.randint(0, 4)):
        box("streak%d" % k, (RNG.uniform(0.2, 0.6), RNG.uniform(0.02, 0.04), 0.005), (RNG.uniform(-0.2, 0.2), RNG.uniform(-0.3, 0.3), 0.013),
            M["blood" if chance(0.6) else "rust2"], r, (0, 0, RNG.uniform(0, PI)))
    if chance(0.2):
        cyl("hole", RNG.uniform(0.05, 0.12), 0.01, (RNG.uniform(-0.3, 0.3), RNG.uniform(-0.3, 0.3), 0.013), M["black"], r, segs=8)
    rnd_stain("rbl", r, "blood", 0.15, 0.013, (0.15, 0.3))
    return r, None


def build_gurney():
    r = tile_root()
    for x in (-0.35, 0.35):
        for y in (-0.18, 0.18):
            cyl("gleg", 0.015, 0.4, (x, y, 0.2), M["rust"], r, segs=6)
    box("gframe", (0.85, 0.42, 0.04), (0, 0, 0.42), M["rust"], r)
    box("gsheet", (0.8, 0.4, 0.06), (0, 0, 0.47), M["bandage"], r)
    sphere("gbody", 0.15, (0.05, 0, 0.53), M["bandage"], r, (2.3, 0.9, 0.5), 10, 6, True)
    sphere("ghead", 0.09, (0.33, 0, 0.55), M["bandage"], r, (1, 1, 0.8), 8, 6, True)
    pool("gbl", (0.05, 0.05, 0.505), 0.3, r, M["blood"], 3)
    for x in (-0.2, 0.15):
        box("gstrap%.1f" % x, (0.05, 0.44, 0.02), (x, 0, 0.55), M["rubber"], r)
    bone("ivpole", (-0.42, 0.22, 0.0), (-0.42, 0.22, 1.0), 0.012, M["chrome"], r)
    box("ivbag", (0.04, 0.08, 0.14), (-0.42, 0.26, 0.92), M["blood"], r)
    drip("gdrip", (0.0, 0.2, 0.44), 0.3, 0.012, M["blood"], r)
    pool("gfloor", (0.05, 0.2, 0.002), 0.35, r, M["blood"], 3)
    return r, None


def build_bodybag():
    r = tile_root()
    pool("bbpool", (0, 0, 0.002), 0.55, r, M["blood"], 4)
    sphere("bag", 0.16, (0, 0, 0.1), M["rubber"], r, (2.6, 1.1, 0.6), 10, 6, True)
    sphere("baghead", 0.11, (0.36, 0, 0.1), M["rubber"], r, (1, 1, 0.7), 8, 6, True)
    box("zip", (0.85, 0.012, 0.01), (0.05, 0, 0.19), M["chrome"], r)
    sphere("handout", 0.03, (0.1, 0.19, 0.06), M["zskin"], r)
    bone("finger", (0.1, 0.19, 0.06), (0.18, 0.26, 0.02), 0.01, M["zskin"], r)
    return r, None


# ---------------------------------------------------------------- outpost (arctic)
def build_wall_ice():
    r = wall_base("steel2", "snow")
    sphere("snowcap", 0.55, (RNG.uniform(-0.05, 0.05), RNG.uniform(-0.05, 0.05), 1.02), M["snow"], r, (1, 1, RNG.uniform(0.12, 0.25)), 10, 6, True)
    for k in range(7):
        u = -0.42 + k * 0.14
        if chance(0.8):
            spike("icx%d" % k, (0.51, u, 0.95), (0.52, u, 0.95 - RNG.uniform(0.08, 0.35)), 0.025, M["ice"], r)
        if chance(0.8):
            spike("icy%d" % k, (u, 0.51, 0.95), (u, 0.52, 0.95 - RNG.uniform(0.08, 0.35)), 0.025, M["ice"], r)
    h = RNG.uniform(0.15, 0.4)
    box("frostx", (0.02, 0.9, h), (0.505, 0, h / 2), M["frost"], r)
    box("frosty", (0.9, 0.02, h), (0, 0.505, h / 2), M["frost"], r)
    if chance(0.6):
        u = RNG.uniform(-0.2, 0.2)
        box("winx", (0.02, 0.4, 0.22), (0.51, u, 0.6), M["black"], r)
        box("winlight", (0.01, 0.36, 0.06), (0.515, u, 0.52), M["glow_orange" if chance(0.7) else "glow_cyan"], r)
    if chance(0.6):
        box("hazx", (0.02, 0.9, 0.05), (0.512, 0, 0.82), M["hazard"], r)
    if chance(0.25):
        smear("ibl", (0.51, RNG.uniform(-0.3, 0.3), 0.4), "x", 0.3, r, n=4)
    return r, None


def build_wall_lab():
    r = wall_base("labwhite", "steel2")
    box("lstripx", (0.02, 1.0, 0.06), (0.505, 0, 0.55), M["darkmetal"], r)
    box("lstripy", (1.0, 0.02, 0.06), (0, 0.505, 0.55), M["darkmetal"], r)
    if chance(0.6):
        box("lwin", (0.02, 0.5, 0.2), (0.51, RNG.uniform(-0.15, 0.15), 0.75), M["black"], r)
    if chance(0.4):
        box("lwiny", (0.5, 0.02, 0.2), (RNG.uniform(-0.15, 0.15), 0.51, 0.75), M["black"], r)
    sphere("lalarm", 0.04, (0.52, RNG.uniform(0.2, 0.4), 0.9), M["glow_red" if chance(0.6) else "glow_yellow"], r)
    if chance(0.5):
        box("lsign", (0.01, 0.2, 0.1), (0.515, RNG.uniform(-0.3, 0.3), 0.35), M["hazard"], r)
    for k in range(RNG.randint(0, 3)):
        smear("lh%d" % k, (0.51, RNG.uniform(-0.35, 0.35), RNG.uniform(0.2, 0.45)), "x", 0.15, r, n=2)
    if chance(0.5):
        smear("lhy", (RNG.uniform(-0.3, 0.3), 0.51, 0.4), "y", 0.3, r, n=4)
    if chance(0.3):
        sphere("lsnow", 0.4, (0, 0, 1.02), M["snow"], r, (1, 1, 0.12), 8, 5, True)
    return r, None


def build_floor_snow():
    r = tile_root()
    slab(M["snow"])
    for k in range(6):
        sphere("drift%d" % k, RNG.uniform(0.15, 0.3), (RNG.uniform(-0.35, 0.35), RNG.uniform(-0.35, 0.35), -0.06), M["snow"], r,
               (1.2, 1, 0.35), 8, 5, True)
    for k in range(4):
        box("print%d" % k, (0.07, 0.04, 0.005), (-0.3 + k * 0.18, 0.05 + (k % 2) * 0.08, 0.012), M["frost"], r, (0, 0, 0.3))
    return r, None


def build_floor_snowblood():
    r, _ = build_floor_snow()
    pool("snowblood", (0.1, -0.1, 0.01), 0.55, r, M["blood"], 5)
    bone_prop("sbb", (-0.3, 0.2, 0.03), (-0.05, 0.35, 0.03), r)
    return r, None


def build_floor_lab():
    r = tile_root()
    slab(M["steel2"])
    n = RNG.choice([2, 2, 4])
    step = 1.0 / n
    for i in range(n):
        for j in range(n):
            if chance(0.04):
                box("lth%d%d" % (i, j), (step - 0.03, step - 0.03, 0.005), (-0.5 + step * (i + 0.5), -0.5 + step * (j + 0.5), -0.004),
                    M["black"], r)
                continue
            box("lt%d%d" % (i, j), (step - 0.03, step - 0.03, 0.02), (-0.5 + step * (i + 0.5), -0.5 + step * (j + 0.5), 0.0), M["labwhite"], r)
    rnd_cracks("lcr", r, 0.011, RNG.randint(0, 2), "steel2", (0.1, 0.25))
    if chance(0.35):
        box("ldrag", (RNG.uniform(0.4, 0.8), 0.06, 0.004), (0.0, RNG.uniform(-0.3, 0.3), 0.012), M["blood"], r, (0, 0, RNG.uniform(-0.6, 0.6)))
    rnd_stain("lbl", r, "blood", 0.12, 0.012, (0.1, 0.25))
    for k in range(RNG.randint(0, 3) if chance(0.4) else 0):
        box("paper%d" % k, (0.12, 0.09, 0.003), (RNG.uniform(-0.35, 0.35), RNG.uniform(-0.35, 0.35), 0.013), M["paper"], r,
            (0, 0, RNG.uniform(0, PI)))
    return r, None


def build_thingcorpse():
    """Two bodies fused mid-transformation, burned black."""
    r = tile_root()
    pool("tcp", (0, 0, 0.002), 0.8, r, M["blood"], 5)
    sphere("tcmass", 0.22, (0, 0, 0.12), M["charred"], r, (1.6, 1.1, 0.6), 10, 7, True)
    sphere("tcmass2", 0.16, (0.15, 0.1, 0.22), M["muscle"], r, (1.2, 1, 0.8), 9, 6, True)
    skull_prop("tch1", (0.32, 0.05, 0.08), r, 1.1, 0.3, M["charred"])
    skull_prop("tch2", (-0.25, 0.18, 0.12), r, 1.0, 2.4, M["bone_dirty"])
    for k in range(4):
        a = k * 1.6
        bone("tclimb%d" % k, (0, 0, 0.12), (math.cos(a) * 0.42, math.sin(a) * 0.42, 0.05), 0.03, M["charred"], r)
        spike("tcclaw%d" % k, (math.cos(a) * 0.42, math.sin(a) * 0.42, 0.05), (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.0),
              0.015, M["bone"], r)
    for k in range(5):
        a = RNG.uniform(0, 2 * PI)
        wire("tctend%d" % k, (0.05, 0.05, 0.25), (math.cos(a) * 0.35, math.sin(a) * 0.35, 0.45 + RNG.uniform(0, 0.2)), 0.0, 0.018,
             M["muscle"], r, 5, wobble=0.05)
    return r, None


def build_generator():
    r = tile_root()
    box("genb", (0.7, 0.6, 0.55), (0, 0, 0.28), M["hazard"], r)
    box("gent", (0.72, 0.62, 0.06), (0, 0, 0.58), M["darkmetal"], r)
    for k in range(5):
        box("gvent%d" % k, (0.02, 0.45, 0.03), (0.355, 0, 0.15 + k * 0.07), M["black"], r)
    cyl("gcoil", 0.1, 0.25, (0, 0, 0.72), M["glow_orange"], r, segs=10)
    for k in range(3):
        ring("gcr%d" % k, 0.12, 0.02, (0, 0, 0.63 + k * 0.08), M["copper"], r, segs=10)
    for k in range(3):
        a = k * 2.2
        wire("gcab%d" % k, (0.2 * math.cos(a), 0.2 * math.sin(a), 0.3), (0.6 * math.cos(a), 0.6 * math.sin(a), 0.02), 0.0, 0.025,
             M["rubber"], r, 5, bulge=(0, 0, 0.1))
    sphere("gsnow", 0.4, (0, 0, 0.6), M["snow"], r, (1, 1, 0.12), 8, 5, True)
    return r, None


# ---------------------------------------------------------------- hell
def build_wall_hellrock():
    r = wall_base("hellrock", "hellrock")
    for k in range(8):
        sz = RNG.uniform(0.2, 0.4)
        loc = (RNG.uniform(-0.4, 0.45), RNG.uniform(-0.4, 0.45), RNG.uniform(0.1, 1.0))
        box("rk%d" % k, (sz, sz, sz), loc, M["hellrock"], r, (RNG.uniform(0, 1), RNG.uniform(0, 1), RNG.uniform(0, 1)))
    for k in range(5):
        z = RNG.uniform(0.1, 0.9)
        box("lcx%d" % k, (0.02, RNG.uniform(0.2, 0.5), 0.025), (0.51, RNG.uniform(-0.3, 0.3), z), M["lava"], r, (RNG.uniform(-0.8, 0.8), 0, 0))
        box("lcy%d" % k, (RNG.uniform(0.2, 0.5), 0.02, 0.025), (RNG.uniform(-0.3, 0.3), 0.51, z), M["lava"], r, (0, RNG.uniform(-0.8, 0.8), 0))
    skull_prop("hsk", (0.47, -0.25, 0.45), r, 1.2, 0.0, M["bone_dirty"])
    drip("hlava", (0.52, 0.2, 0.3), 0.2, 0.02, M["lava"], r)
    return r, None


def build_wall_spine():
    r = wall_base("mutant", "hellrock")
    for (x, y) in ((0.45, 0.45), (0.45, -0.45), (-0.45, 0.45)):
        for k in range(8):
            cyl("vt%.1f%.1f%d" % (x, y, k), 0.09, 0.08, (x, y, 0.06 + k * 0.125), M["bone_dirty"], r, segs=8)
            spike("vs%.1f%.1f%d" % (x, y, k), (x, y, 0.06 + k * 0.125), (x * 1.3, y * 1.3, 0.1 + k * 0.125), 0.03, M["bone"], r)
    for k in range(4):
        z = 0.25 + k * 0.2
        pts = [Vector((0.53, -0.45 + t * 0.9, z + 0.12 * math.sin(t * PI))) for t in (0, 0.33, 0.66, 1.0)]
        tube("rbx%d" % k, pts, 0.018, M["bone"], r, segs=5)
        pts = [Vector((-0.45 + t * 0.9, 0.53, z + 0.12 * math.sin(t * PI))) for t in (0, 0.33, 0.66, 1.0)]
        tube("rby%d" % k, pts, 0.018, M["bone"], r, segs=5)
    box("musx", (0.02, 0.8, 0.9), (0.5, 0, 0.5), M["muscle"], r)
    box("musy", (0.8, 0.02, 0.9), (0, 0.5, 0.5), M["muscle"], r)
    return r, None


def build_floor_brimstone():
    r = tile_root()
    slab(M["hellrock"])
    for k in range(2):
        box("seam%d" % k, (RNG.uniform(0.15, 0.35), 0.02, 0.012), (RNG.uniform(-0.25, 0.25), RNG.uniform(-0.35, 0.35), 0.0),
            M["lava"], r, (0, 0, RNG.uniform(0, PI)))
    for k in range(3):
        box("rb%d" % k, (0.08, 0.1, 0.05), (RNG.uniform(-0.4, 0.4), RNG.uniform(-0.4, 0.4), 0.02), M["hellrock"], r, (0, 0, k))
    return r, None


def build_floor_rune():
    r = tile_root()
    slab(M["hellrock"])
    r1 = RNG.uniform(0.36, 0.44)
    ring("rr1", r1, 0.01, (0, 0, 0.002), M["ember"], r, segs=24)
    if chance(0.7):
        ring("rr2", r1 - 0.1, 0.01, (0, 0, 0.002), M["ember"], r, segs=24)
    n = RNG.choice([6, 8, 10])
    for k in range(n):
        a = k * 2 * PI / n
        box("glyph%d" % k, (0.06, 0.02, 0.012), (math.cos(a) * (r1 - 0.05), math.sin(a) * (r1 - 0.05), 0.002), M["ember"], r, (0, 0, a + 0.6))
        if chance(0.7):
            box("ray%d" % k, (0.2, 0.015, 0.008), (math.cos(a) * 0.15, math.sin(a) * 0.15, 0.002), M["ember"], r, (0, 0, a))
    if chance(0.6):
        sphere("eye", 0.05, (0, 0, 0.01), M["glow_red"], r, (1, 1, 0.3))
    rnd_cracks("rc", r, 0.003, RNG.randint(0, 2))
    return r, None


def build_brazier():
    r = tile_root()
    for k in range(3):
        a = k * 2 * PI / 3
        bone("bleg%d" % k, (math.cos(a) * 0.25, math.sin(a) * 0.25, 0.0), (0, 0, 0.45), 0.025, M["darkmetal"], r)
    cyl("bowl", 0.26, 0.15, (0, 0, 0.52), M["darkmetal"], r, r2=0.16, segs=10)
    sphere("coals", 0.2, (0, 0, 0.58), M["lava"], r, (1, 1, 0.3), 8, 5)
    for k in range(7):
        a = RNG.uniform(0, 2 * PI)
        d = RNG.uniform(0, 0.12)
        base = Vector((math.cos(a) * d, math.sin(a) * d, 0.6))
        spike("bfl%d" % k, base, base + Vector((RNG.uniform(-0.05, 0.05), RNG.uniform(-0.05, 0.05), RNG.uniform(0.25, 0.45))),
              0.07, M["flame" if k % 2 else "flame2"], r)
    skull_prop("bsk", (0.2, 0.15, 0.62), r, 0.8, 0.5, M["charred"])
    return r, None


def build_impaler():
    r = tile_root()
    pool("ipool", (0, 0, 0.002), 0.5, r, M["blood"], 4)
    bone("stake", (0, 0, 0.0), (0, 0, 1.35), 0.035, M["darkmetal"], r, r2=0.005)
    rc = ribcage("irib", (0.0, 0.0, 0.62), r, 1.0)
    skull_prop("isk", (0.03, 0, 0.98), r, 1.2, 0.4)
    meat("imeat", (0.03, 0.0, 0.75), 0.1, r, M["muscle"], 3)
    for s in (1, -1):
        bone_prop("iarm%d" % s, (0, s * 0.12, 0.88), (0.15, s * 0.3, 0.6), r)
    guts("igut", (0.08, 0, 0.6), (0.3, 0.2, -1), 7, 0.025, r, droop=0.4)
    drip("idrip", (0, 0.03, 0.55), 0.4, 0.014, M["blood"], r)
    return r, None


# ---------------------------------------------------------------- rubble (destroyed walls)
def build_floor_rubble():
    r = tile_root()
    slab(M["concrete"])
    for k in range(9):
        s = RNG.uniform(0.05, 0.14)
        box("rub%d" % k, (s, s * 1.3, s * 0.7), (RNG.uniform(-0.4, 0.4), RNG.uniform(-0.4, 0.4), s * 0.3), M["concrete2" if k % 2 else "stone"],
            r, (RNG.uniform(0, 1), RNG.uniform(0, 1), RNG.uniform(0, 3)))
    bone("rebar", (-0.3, 0.2, 0.03), (0.2, 0.3, 0.12), 0.01, M["rust"], r)
    return r, None


def g_rubble(p):
    box("gr1", (0.16, 0.12, 0.1), (0, 0, 0), M["concrete"], p, (0.3, 0.2, 0.1))
    box("gr2", (0.08, 0.1, 0.07), (0.08, 0.05, 0.04), M["stone"], p, (0.1, 0.5, 0.3))
    bone("grb", (-0.05, -0.05, 0), (0.12, -0.08, 0.06), 0.008, M["rust"], p)


# ================================================================ new enemies
def build_hellspawn():
    root = empty("h_root")
    J = biped_legs(root, 0.78, 0.11, 0.38, 0.36, 0.05, 0.04, M["hellskin"], M["hellskin"], (0.18, 0.08, 0.05), M["charred"], "h")
    body = empty("h_body", (0, 0, 0), root)
    torso = empty("h_torso", (0, 0, 0.8), body, (0, 0.25, 0))
    sphere("hchest", 0.17, (0, 0, 0.25), M["hellskin"], torso, (0.8, 1.15, 1.35), 9, 7, True)
    for k in range(4):
        bone("hrib%d" % k, (0.1, 0.16, 0.12 + k * 0.07), (0.1, -0.16, 0.12 + k * 0.07), 0.014, M["bone_dirty"], torso)
    for k in range(6):
        y = (k - 2.5) * 0.06
        spike("hspk%d" % k, (-0.12, y, 0.2 + abs(y)), (-0.3, y * 1.5, 0.35 + abs(y) * 1.5), 0.03, M["bone_dirty"], torso)
    for s in (1, -1):
        spike("hsho%d" % s, (0, s * 0.18, 0.45), (-0.05, s * 0.32, 0.62), 0.04, M["bone_dirty"], torso)
    head = empty("h_head", (0.06, 0, 0.55), torso, (0, -0.2, 0))
    sphere("hhead", 0.1, (0.02, 0, 0.05), M["hellskin"], head, (1.2, 0.9, 1.0), 8, 6, True)
    for s in (1, -1):
        tube("hhorn%d" % s, [Vector((0, s * 0.06, 0.1)), Vector((-0.06, s * 0.12, 0.2)), Vector((-0.16, s * 0.14, 0.24)),
                             Vector((-0.24, s * 0.12, 0.2))], 0.025, M["bone_dirty"], head, segs=5, r_end=0.004)
        sphere("heye%d" % s, 0.02, (0.11, s * 0.04, 0.07), M["glow_orange"], head)
    box("hjaw", (0.08, 0.1, 0.04), (0.1, 0, -0.03), M["hellskin"], head)
    for k in range(4):
        spike("hfang%d" % k, (0.13, -0.03 + k * 0.02, -0.01), (0.14, -0.03 + k * 0.02, -0.05), 0.01, M["tooth"], head)
    arms = {}
    for side, y in (("L", 0.2), ("R", -0.2)):
        sh = empty("hsh" + side, (0, y, 0.42), torso)
        bone("hup" + side, (0, 0, 0), (0.12, 0, -0.22), 0.035, M["hellskin"], sh)
        bone("hfo" + side, (0.12, 0, -0.22), (0.3, 0, -0.18), 0.03, M["hellskin"], sh)
        for k in range(3):
            spike("hcl%s%d" % (side, k), (0.3, -0.02 + k * 0.02, -0.18), (0.4, -0.03 + k * 0.03, -0.22), 0.012, M["bone"], sh)
        arms[side] = sh
    fire = empty("h_fire", (0.38, -0.02, -0.12), arms["R"])
    sphere("hfball", 0.08, (0, 0, 0), M["lava"], fire, segs=8, rings=6, smooth=True)
    for k in range(4):
        a = k * PI / 2
        spike("hfl%d" % k, (0, 0, 0), (math.cos(a) * 0.05, math.sin(a) * 0.05, 0.16), 0.05, M["flame"], fire)

    def pose(anim, t):
        walk_legs(J, t, 0.45, 0.6)
        ph = 2 * PI * t
        body.rotation_euler.x = math.sin(ph) * 0.08
        arms["L"].rotation_euler.y = math.sin(ph) * 0.4
        arms["R"].rotation_euler.y = -0.6 + math.sin(ph) * 0.15
        s = 1 + 0.2 * math.sin(ph * 2)
        fire.scale = (s, s, s)
    return root, pose


def build_wretch():
    root = empty("wr_root")
    J = biped_legs(root, 0.86, 0.08, 0.42, 0.4, 0.04, 0.032, M["bandage"], M["zskin2"], (0.14, 0.07, 0.04), M["zskin2"], "wr")
    body = empty("wr_body", (0, 0, 0), root)
    torso = empty("wr_torso", (0, 0, 0.88), body)
    sphere("wrchest", 0.15, (0, 0, 0.32), M["bandage"], torso, (0.75, 1.0, 2.2), 9, 7, True)
    for k in range(5):
        box("wrstrap%d" % k, (0.24, 0.32, 0.025), (0, 0, 0.1 + k * 0.11), M["rubber"], torso, (0, 0, 0.3 * (k % 2)))
    # arms bound across the chest (straitjacket)
    box("wrarms", (0.12, 0.34, 0.1), (0.12, 0, 0.35), M["bandage"], torso, (0, 0.1, 0))
    box("wrbuckle", (0.02, 0.05, 0.04), (0.18, 0, 0.35), M["chrome"], torso)
    for k in range(3):
        smear("wrbl%d" % k, (0.13, RNG.uniform(-0.1, 0.1), 0.2 + k * 0.12), "x", 0.12, torso, n=2)
    head = empty("wr_head", (0, 0, 0.72), torso)
    bone("wrneck", (0, 0, -0.1), (0, 0, 0.05), 0.035, M["zskin2"], head)
    sphere("wrhead", 0.11, (0.02, 0, 0.13), M["bandage"], head, (1.0, 0.85, 1.4), 9, 7, True)
    sphere("wrlump", 0.07, (0.07, 0.03, 0.2), M["muscle"], head, (1, 1, 1.2), 8, 6, True)
    for k in range(4):
        box("wrwrap%d" % k, (0.2, 0.2, 0.015), (0.02, 0, 0.05 + k * 0.06), M["bandage"], head, (0.3 * (k % 2 - 0.5), 0.2, 0))
    drip("wrdrip", (0.12, 0, 0.08), 0.15, 0.012, M["blood"], head)

    def pose(anim, t):
        walk_legs(J, t, 0.3, 0.4)
        ph = 2 * PI * t
        jerk = 1 if int(t * 6) % 3 == 0 else 0
        head.rotation_euler = (math.sin(ph * 3) * 0.5 * jerk + 0.2, math.cos(ph * 5) * 0.3, math.sin(ph * 7) * 0.6)
        torso.rotation_euler = (math.sin(ph * 2) * 0.15, 0.1 + math.sin(ph * 3) * 0.1, 0)
    return root, pose


def build_stalker():
    root = empty("st_root")
    body = empty("st_body", (0, 0, 0.42), root, (0, 0.15, 0))
    sphere("stchest", 0.18, (0.05, 0, 0.05), M["muscle"], body, (1.6, 1.0, 0.75), 10, 7, True)
    sphere("sthips", 0.14, (-0.28, 0, 0.0), M["muscle"], body, (1.2, 1.0, 0.8), 9, 6, True)
    for k in range(8):
        x = -0.36 + k * 0.08
        spike("stsp%d" % k, (x, 0, 0.12), (x - 0.03, 0, 0.2), 0.022, M["bone_dirty"], body)
    for k in range(4):
        bone("stmusc%d" % k, (0.15 - k * 0.08, 0.15, 0.0), (0.12 - k * 0.08, 0.15, 0.12), 0.012, M["flesh"], body)
    head = empty("st_head", (0.36, 0, 0.05), body)
    sphere("stskull", 0.1, (0.04, 0, 0.0), M["muscle"], head, (1.3, 0.9, 0.8), 8, 6, True)
    sphere("stbrain", 0.085, (0.02, 0, 0.07), M["brain"], head, (1.3, 0.9, 0.7), 9, 7, True)
    for k in range(6):
        spike("stteeth%d" % k, (0.14, -0.05 + k * 0.02, -0.04), (0.14, -0.05 + k * 0.02, -0.08), 0.009, M["tooth"], head)
    tongue = tentacle("sttongue", (0.15, 0, -0.06), (1, 0, -0.6), 5, 0.07, 0.022, head, M["guts"])
    legs = []
    for i, (x, sy) in enumerate(((0.16, 1), (0.16, -1), (-0.3, 1), (-0.3, -1))):
        hip = empty("stl%d" % i, (x, sy * 0.13, -0.02), body)
        if i < 2:   # arms with long claws
            bone("sta%d" % i, (0, 0, 0), (0.12, sy * 0.06, -0.22), 0.03, M["muscle"], hip)
            bone("stb%d" % i, (0.12, sy * 0.06, -0.22), (0.18, sy * 0.08, -0.42), 0.025, M["muscle"], hip)
            for k in range(3):
                spike("stc%d%d" % (i, k), (0.18, sy * 0.08 + (k - 1) * 0.02, -0.42), (0.32, sy * 0.08 + (k - 1) * 0.04, -0.45),
                      0.012, M["bone"], hip)
        else:
            bone("sta%d" % i, (0, 0, 0), (0.15, sy * 0.05, -0.2), 0.04, M["muscle"], hip)
            bone("stb%d" % i, (0.15, sy * 0.05, -0.2), (-0.02, sy * 0.06, -0.42), 0.03, M["muscle"], hip)
        legs.append((hip, i))

    def pose(anim, t):
        ph = 2 * PI * t
        for hip, i in legs:
            off = (0, 0.5, 0.5, 0)[i]
            hip.rotation_euler.y = math.sin(ph + off * 2 * PI) * 0.5
        body.location.z = 0.42 + abs(math.sin(ph)) * 0.04
        for k, j in enumerate(tongue):
            j.rotation_euler.x = math.sin(ph * 2 - k * 0.8) * 0.4
    return root, pose


def build_mimic():
    root = empty("mi_root")
    pool("mipool", (0, 0, 0.002), 0.9, root, M["blood"], 5)
    body = empty("mi_body", (0, 0, 0.0), root)
    # dormant: a corpse lying in blood (only these show in the dormant frame)
    dorm = empty("mi_dorm", (0, 0, 0), body)
    sphere("mid_torso", 0.15, (0, 0, 0.1), M["zcloth"], dorm, (2.0, 1.1, 0.6), 9, 6, True)
    skull_prop("mid_head", (0.38, 0, 0.0), dorm, 1.2, 0.3, M["zskin"])
    for s in (1, -1):
        bone("mid_arm%d" % s, (0.15, s * 0.15, 0.06), (0.3, s * 0.35, 0.04), 0.035, M["zskin"], dorm)
        bone("mid_leg%d" % s, (-0.25, s * 0.08, 0.06), (-0.6, s * 0.15, 0.04), 0.045, M["zcloth"], dorm)
    # awakened: split-open mass of tentacles, teeth and a head on a stalk
    act = empty("mi_act", (0, 0, 0), body)
    sphere("mi_mass", 0.3, (0, 0, 0.4), M["muscle"], act, (1.3, 1.1, 1.0), 12, 8, True)
    sphere("mi_mass2", 0.22, (-0.15, 0.1, 0.65), M["flesh"], act, (1, 1, 1), 10, 7, True)
    for k in range(10):   # ribcage split open like jaws
        a = (k - 4.5) * 0.25
        tube("mi_jaw%d" % k, [Vector((0.15, math.sin(a) * 0.18, 0.4)), Vector((0.35, math.sin(a) * 0.3, 0.55)),
                              Vector((0.45, math.sin(a) * 0.32, 0.75))], 0.018, M["bone"], act, segs=5, r_end=0.004)
    for k in range(8):
        spike("mi_tooth%d" % k, (0.25, -0.14 + k * 0.04, 0.38), (0.32, -0.14 + k * 0.04, 0.32), 0.014, M["tooth"], act)
    stalk = tentacle("mi_stalk", (-0.05, 0, 0.6), (0.1, 0, 1), 5, 0.1, 0.04, act, M["muscle"])
    skull_prop("mi_shead", (0, 0, 0.06), stalk[-1], 1.3, 0.0, M["zskin"])
    tents = []
    for k in range(6):
        a = k * PI / 3 + 0.3
        tents.append(tentacle("mi_t%d" % k, (math.cos(a) * 0.25, math.sin(a) * 0.25, 0.35),
                              (math.cos(a), math.sin(a), 0.5), 6, 0.11, 0.06, act, M["leech2"]))
    for k in range(5):
        sphere("mi_eye%d" % k, 0.03, (RNG.uniform(-0.2, 0.2), RNG.uniform(-0.2, 0.2), RNG.uniform(0.45, 0.75)), M["glow_yellow"], act)
    legs = []
    for k in range(4):
        a = k * PI / 2 + PI / 4
        hip = empty("mi_leg%d" % k, (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.3), act, (0, 0, a))
        bone("mi_l1%d" % k, (0, 0, 0), (0.3, 0, 0.1), 0.04, M["bone_dirty"], hip)
        bone("mi_l2%d" % k, (0.3, 0, 0.1), (0.45, 0, -0.3), 0.03, M["bone_dirty"], hip, r2=0.006)
        legs.append(hip)

    def pose(anim, t):
        if anim == "dormant":
            dorm.hide_render, act.hide_render = False, True
            for o in act.children_recursive:
                o.hide_render = True
            for o in dorm.children_recursive:
                o.hide_render = False
            return
        dorm.hide_render, act.hide_render = True, False
        for o in dorm.children_recursive:
            o.hide_render = True
        for o in act.children_recursive:
            o.hide_render = False
        ph = 2 * PI * t
        for k, tj in enumerate(tents):
            for i, j in enumerate(tj):
                j.rotation_euler.x = math.sin(ph + k * 1.1 - i * 0.7) * 0.35
                j.rotation_euler.y = math.cos(ph * 2 + k - i * 0.5) * 0.25
        for i, j in enumerate(stalk):
            j.rotation_euler.y = math.sin(ph - i * 0.6) * 0.18
        for k, hp_ in enumerate(legs):
            hp_.rotation_euler.y = math.sin(ph + k * PI / 2) * 0.25
    return root, pose


GIBS = {
    "gib_bone": g_bone, "gib_rib": g_rib, "gib_skull": g_skull, "gib_jaw": g_jaw, "gib_meat": g_meat,
    "gib_meat_green": g_meat_green, "gib_gut": g_gut, "gib_eye": g_eye, "gib_chitin": g_chitin,
    "gib_spiderleg": g_spiderleg, "gib_leech": g_leech, "gib_metal": g_metal, "gib_gear": g_gear,
    "gib_wire": g_wire, "gib_chrome": g_chrome, "gib_armor": g_armor, "gib_pod": g_pod, "gib_barrel": g_barrel, "gib_plank": g_plank, "gib_rubble": g_rubble,
}

# ================================================================ registry
# name: (builder, dirs, {anim: frames}, base resolution at 64px tiles, camera target z)
ASSETS = {
    "player_legs":  (build_player_legs, 8, {"walk": 8, "idle": 1}, (128, 128), 0.6),
    "brute":        (build_brute, 8, {"walk": 6}, (192, 192), 0.9),
    "crawler":      (build_crawler, 8, {"walk": 6}, (128, 128), 0.25),
    "spitter":      (build_spitter, 8, {"walk": 6}, (128, 128), 0.6),
    "turret":       (build_turret, 8, {"walk": 6}, (128, 128), 0.4),
    "walker":       (build_walker, 8, {"walk": 6}, (160, 160), 0.8),
    "bloater":      (build_bloater, 8, {"walk": 6}, (128, 128), 0.6),
    "skull":        (build_skull, 8, {"walk": 6}, (128, 128), 1.0),
    "hellspawn":    (build_hellspawn, 8, {"walk": 6}, (128, 128), 0.6),
    "wretch":       (build_wretch, 8, {"walk": 6}, (128, 144), 0.8),
    "stalker":      (build_stalker, 8, {"walk": 6}, (128, 128), 0.4),
    "mimic":        (build_mimic, 8, {"dormant": 1, "walk": 6}, (160, 160), 0.4),
    "wall_crypt":   (build_wall_crypt, 1, {"idle": 1}, (96, 112), 0.5),
    "floor_flagstone": (build_floor_flagstone, 1, {"idle": 1}, (72, 72), 0.0),
    "candles":      (build_candles, 1, {"idle": 1}, (96, 96), 0.1),
    "sarcophagus":  (build_sarcophagus, 1, {"idle": 1}, (96, 96), 0.3),
    "wall_rust":    (build_wall_rust, 1, {"idle": 1}, (96, 112), 0.5),
    "wall_fence":   (build_wall_fence, 1, {"idle": 1}, (96, 112), 0.5),
    "floor_rustgrate": (build_floor_rustgrate, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_rust":   (build_floor_rust, 1, {"idle": 1}, (72, 72), 0.0),
    "gurney":       (build_gurney, 1, {"idle": 1}, (96, 112), 0.45),
    "bodybag":      (build_bodybag, 1, {"idle": 1}, (96, 96), 0.1),
    "wall_ice":     (build_wall_ice, 1, {"idle": 1}, (96, 112), 0.5),
    "wall_lab":     (build_wall_lab, 1, {"idle": 1}, (96, 112), 0.5),
    "floor_snow":   (build_floor_snow, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_lab":    (build_floor_lab, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_snowblood": (build_floor_snowblood, 1, {"idle": 1}, (72, 72), 0.0),
    "thingcorpse":  (build_thingcorpse, 1, {"idle": 1}, (96, 96), 0.2),
    "generator":    (build_generator, 1, {"idle": 1}, (96, 112), 0.4),
    "wall_hellrock": (build_wall_hellrock, 1, {"idle": 1}, (96, 112), 0.5),
    "wall_spine":   (build_wall_spine, 1, {"idle": 1}, (96, 112), 0.5),
    "floor_brimstone": (build_floor_brimstone, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_rune":   (build_floor_rune, 1, {"idle": 1}, (72, 72), 0.0),
    "brazier":      (build_brazier, 1, {"idle": 1}, (96, 112), 0.45),
    "impaler":      (build_impaler, 1, {"idle": 1}, (96, 128), 0.6),
    "floor_rubble": (build_floor_rubble, 1, {"idle": 1}, (72, 72), 0.0),
    "zombie":       (build_zombie, 8, {"walk": 6}, (128, 128), 0.6),
    "spider":       (build_spider, 8, {"walk": 6}, (192, 192), 0.5),
    "leech":        (build_leech, 8, {"walk": 6}, (128, 128), 0.3),
    "drone":        (build_drone, 8, {"walk": 6}, (128, 128), 0.8),
    "floor_metal":  (build_floor_metal, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_cables": (build_floor_cables, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_grate":  (build_floor_grate, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_concrete": (build_floor_concrete, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_hazard": (build_floor_hazard, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_bones":  (build_floor_bones, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_gore":   (build_floor_gore, 1, {"idle": 1}, (72, 72), 0.0),
    "floor_flesh":  (build_floor_flesh, 1, {"idle": 1}, (72, 72), 0.0),
    "wall_tech":    (build_wall_tech, 1, {"idle": 1}, (96, 112), 0.5),
    "wall_skull":   (build_wall_skull, 1, {"idle": 1}, (96, 112), 0.5),
    "wall_pipe":    (build_wall_pipe, 1, {"idle": 1}, (96, 112), 0.5),
    "wall_flesh":   (build_wall_flesh, 1, {"idle": 1}, (96, 112), 0.5),
    "barrel":       (build_barrel, 1, {"idle": 1}, (96, 96), 0.4),
    "crate":        (build_crate, 1, {"idle": 1}, (96, 96), 0.35),
    "tank":         (build_tank, 1, {"idle": 1}, (96, 128), 0.6),
    "skullpile":    (build_skullpile, 1, {"idle": 1}, (96, 96), 0.15),
    "gorepile":     (build_gorepile, 1, {"idle": 1}, (96, 96), 0.15),
    "corpse":       (build_corpse, 1, {"idle": 1}, (96, 96), 0.1),
    "cables":       (build_cables, 1, {"idle": 1}, (96, 96), 0.05),
    "portal":       (build_portal, 1, {"idle": 8}, (96, 96), 0.25),
    "spawner":      (build_spawner, 1, {"idle": 4}, (96, 96), 0.3),
    "health":       (build_health, 1, {"idle": 8}, (64, 64), 0.3),
    "power":        (build_power, 1, {"idle": 8}, (64, 64), 0.3),
}
for _name, _fn in GIBS.items():
    ASSETS[_name] = (gib_builder(_fn), 1, {"spin": 8}, (40, 40), 0.0)
for _arch in GUNS:
    ASSETS["torso_" + _arch] = (torso_builder(_arch), 16, {"idle": 1}, (128, 128), 0.6)
    ASSETS["gun_" + _arch] = (gunpickup_builder(_arch), 1, {"idle": 8}, (80, 80), 0.3)


FLOOR_VARIANTS = 10
WALL_VARIANTS = 10
FEW_VARIANTS = {"floor_hazard": 5, "floor_rune": 6, "floor_flesh": 8, "wall_fence": 6, "wall_spine": 6}


def variant_count(name):
    if name in FEW_VARIANTS:
        return FEW_VARIANTS[name]
    if name.startswith("floor_"):
        return FLOOR_VARIANTS
    if name.startswith("wall_"):
        return WALL_VARIANTS
    return 1


def render_variants(name, nvar):
    """Static tiles: rebuild the model with a different seed per variant -> idle frames."""
    builder, dirs, anims, base_res, tz = ASSETS[name]
    res = (int(base_res[0] * RS), int(base_res[1] * RS))
    outdir = os.path.join(OUT, name)
    os.makedirs(outdir, exist_ok=True)
    for v in range(1 if QUICK else nvar):
        RNG.seed(zlib.crc32(name.encode()) + v * 7919)
        for c in scene.collection.children:
            c.hide_render = True
        coll = new_collection("%s_v%d" % (name, v))
        builder()
        coll.hide_render = False
        aim_camera(res, tz)
        set_lighting(name)
        scene.render.filepath = os.path.join(outdir, "idle_00_%02d.png" % v)
        bpy.ops.render.render(write_still=True)
        coll.hide_render = True
        for ob in list(coll.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(coll)
    return {"dirs": 1, "anims": {"idle": nvar}, "size": list(res), "anchor": [res[0] / 2, res[1] / 2 + tz * ZPIX], "variants": nvar}


def render_asset(name):
    nvar = variant_count(name)
    if nvar > 1:
        return render_variants(name, nvar)
    builder, dirs, anims, base_res, tz = ASSETS[name]
    res = (int(base_res[0] * RS), int(base_res[1] * RS))
    RNG.seed(zlib.crc32(name.encode()))
    EXTRA_META.clear()
    for c in scene.collection.children:
        c.hide_render = True
    coll = new_collection(name)
    root, pose = builder()
    coll.hide_render = False
    aim_camera(res, tz)
    set_lighting(name)
    outdir = os.path.join(OUT, name)
    os.makedirs(outdir, exist_ok=True)
    for anim, nframes in anims.items():
        dlist = range(dirs)
        flist = range(nframes)
        if QUICK:
            dlist = sorted(set([0, dirs // 8, (dirs * 5) // 8])) if dirs > 1 else [0]
            flist = [0]
        for d in dlist:
            root.rotation_euler.z = 2 * PI * d / dirs
            for f in flist:
                if pose:
                    pose(anim, f / nframes)
                scene.render.filepath = os.path.join(outdir, "%s_%02d_%02d.png" % (anim, d, f))
                bpy.ops.render.render(write_still=True)
    coll.hide_render = True
    meta = {
        "dirs": dirs,
        "anims": anims,
        "size": list(res),
        "anchor": [res[0] / 2, res[1] / 2 + tz * ZPIX],
    }
    meta.update(EXTRA_META)
    return meta


def main():
    os.makedirs(OUT, exist_ok=True)
    mpath = os.path.join(OUT, "manifest.json")
    manifest = {}
    if os.path.exists(mpath):
        with open(mpath) as fh:
            manifest = json.load(fh)
    if manifest.get("_meta", {}).get("tile_w") != TILE_W:
        manifest = {}   # resolution changed: stale entries are useless
    manifest["_meta"] = {"tile_w": TILE_W}
    names = []
    for a in (ONLY or list(ASSETS.keys())):
        if a.endswith("*"):
            names += [n for n in ASSETS if n.startswith(a[:-1])]
        else:
            names.append(a)
    for n in names:
        print("=== rendering", n)
        entry = render_asset(n)
        # re-read before writing so parallel Blender runs don't clobber each other
        try:
            with open(mpath) as fh:
                manifest = json.load(fh)
        except Exception:
            pass
        manifest["_meta"] = {"tile_w": TILE_W}
        manifest[n] = entry
        with open(mpath, "w") as fh:
            json.dump(manifest, fh, indent=1)
    print("DONE", len(names), "assets")


exec(open(os.path.join(HERE, "expansion.py"), encoding="utf-8").read())
exec(open(os.path.join(HERE, "traps.py"), encoding="utf-8").read())
exec(open(os.path.join(HERE, "heavy_guns.py"), encoding="utf-8").read())
exec(open(os.path.join(HERE, "support_items.py"), encoding="utf-8").read())
exec(open(os.path.join(HERE, "modules.py"), encoding="utf-8").read())
exec(open(os.path.join(HERE, "characters.py"), encoding="utf-8").read())
exec(open(os.path.join(HERE, "turrets.py"), encoding="utf-8").read())

main()

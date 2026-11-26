"""Sprite loading + isometric math. Sprites come from blender/build_assets.py."""
import os
import json
import math
import random
import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPR_DIR = os.path.join(ROOT, "assets", "sprites")
MANIFEST = os.path.join(SPR_DIR, "manifest.json")


def _read_manifest():
    try:
        with open(MANIFEST) as fh:
            return json.load(fh)
    except Exception:
        return None


_manifest = _read_manifest()
TILE_W = (_manifest or {}).get("_meta", {}).get("tile_w", 64)
S = TILE_W / 64.0            # global pixel scale (1 = 64px tiles, 2 = 128px tiles)

# 2:1 dimetric projection, must match the Blender camera (rot 60/0/135)
HALF_W = TILE_W / 2.0
HALF_H = TILE_W / 4.0
ZPIX = (HALF_W / math.cos(math.radians(45))) * math.cos(math.radians(30))
TAU = math.tau


def to_screen(x, y, z=0.0):
    """World (tile units, z up) -> screen offset in pixels (before camera offset)."""
    return (y - x) * HALF_W, (x + y) * HALF_H - z * ZPIX


def screen_to_world_dir(dx, dy):
    """A direction on screen -> normalized direction on the ground plane."""
    wx = dy / HALF_H - dx / HALF_W
    wy = dy / HALF_H + dx / HALF_W
    l = math.hypot(wx, wy)
    if l < 1e-9:
        return 0.0, 0.0
    return wx / l, wy / l


def dir_index(wx, wy, n):
    """World direction -> sprite direction index (sprites rendered at angle 2*pi*i/n)."""
    a = math.atan2(wy, wx)
    return int(round(a / (TAU / n))) % n


def outlined(surf, color=(10, 6, 10)):
    mask = pygame.mask.from_surface(surf, 100)
    sil = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    r = max(1, int(S))
    for d in range(1, r + 1):
        for dx, dy in ((-d, 0), (d, 0), (0, -d), (0, d)):
            out.blit(sil, (dx, dy))
    if r > 1:
        for dx, dy in ((-1, -1), (1, 1), (-1, 1), (1, -1)):
            out.blit(sil, (dx, dy))
    out.blit(surf, (0, 0))
    return out


class Sprite:
    def __init__(self, name, meta, outline=False):
        self.name = name
        self.dirs = meta["dirs"]
        self.anims = meta["anims"]
        self.ax, self.ay = meta["anchor"]
        self.frames = {}
        for anim, n in self.anims.items():
            per_dir = []
            for d in range(self.dirs):
                fr = []
                for f in range(n):
                    p = os.path.join(SPR_DIR, name, "%s_%02d_%02d.png" % (anim, d, f))
                    s = pygame.image.load(p).convert_alpha()
                    if outline:
                        s = outlined(s)
                    fr.append(s)
                per_dir.append(fr)
            self.frames[anim] = per_dir
        self.first_anim = next(iter(self.anims))
        self._flash = {}
        self._fade = {}

    def get(self, anim, d, f=0):
        fr = self.frames[anim][d % self.dirs]
        return fr[int(f) % len(fr)]

    def flash(self, surf):
        s = self._flash.get(id(surf))
        if s is None:
            m = pygame.mask.from_surface(surf, 100)
            s = m.to_surface(setcolor=(255, 255, 255, 230), unsetcolor=(0, 0, 0, 0))
            self._flash[id(surf)] = s
        return s

    def faded(self, surf, alpha=90):
        s = self._fade.get(id(surf))
        if s is None:
            s = surf.copy()
            s.set_alpha(alpha)
            self._fade[id(surf)] = s
        return s


OUTLINED = {"player_legs", "player_torso", "zombie", "spider", "leech", "drone", "health", "power", "spawner"}


def load_all():
    if not _manifest:
        raise SystemExit("No sprites found. Run build_assets.bat first (renders assets with Blender).")
    return {name: Sprite(name, meta, name in OUTLINED or name.startswith(("gib_", "torso_")))
            for name, meta in _manifest.items() if not name.startswith("_")}


# ---------------------------------------------------------------- procedural fx surfaces
_glow_cache = {}


def glow(radius, color):
    radius = max(2, int(radius))
    key = (radius, color)
    s = _glow_cache.get(key)
    if s is None:
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -1):
            k = (1 - r / radius) ** 1.6
            pygame.draw.circle(s, (int(color[0] * k), int(color[1] * k), int(color[2] * k)), (radius, radius), r)
        _glow_cache[key] = s
    return s


_shadow_cache = {}


def shadow(rx):
    rx = max(2, int(rx))
    s = _shadow_cache.get(rx)
    if s is None:
        s = pygame.Surface((rx * 2, rx), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 90), s.get_rect())
        _shadow_cache[rx] = s
    return s


_splat_cache = {}


def splat(color, radius, variant):
    """Irregular blood/goo splat squashed into iso perspective. radius in pixels."""
    radius = max(3, int(radius))
    key = (color, radius, variant)
    s = _splat_cache.get(key)
    if s is not None:
        return s
    rng = random.Random(variant * 7919 + radius)
    size = radius * 5
    base = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    dark = tuple(max(0, int(v * 0.6)) for v in color)
    lite = tuple(min(255, int(v * 1.35 + 8)) for v in color)
    blobs = [(c, c, radius)]
    for _ in range(rng.randint(4, 8)):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(0.3, 1.0) * radius
        blobs.append((c + math.cos(a) * d, c + math.sin(a) * d, radius * rng.uniform(0.3, 0.65)))
    for x, y, r in blobs:
        pygame.draw.circle(base, (*dark, 235), (x, y), r + max(1, radius // 8))
    for x, y, r in blobs:
        pygame.draw.circle(base, (*color, 235), (x, y), r)
    # spatter droplets + streaks flung outward
    for _ in range(rng.randint(6, 14)):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(1.1, 2.3) * radius
        r = max(1, radius * rng.uniform(0.06, 0.18))
        x, y = c + math.cos(a) * d, c + math.sin(a) * d
        pygame.draw.circle(base, (*color, 230), (x, y), r)
        if rng.random() < 0.4:
            pygame.draw.line(base, (*color, 220), (c + math.cos(a) * radius * 0.8, c + math.sin(a) * radius * 0.8), (x, y),
                             max(1, int(r)))
    # glossy highlight
    pygame.draw.circle(base, (*lite, 200), (c - radius * 0.3, c - radius * 0.3), max(1, radius * 0.22))
    s = pygame.transform.smoothscale(base, (size, size // 2))
    _splat_cache[key] = s
    return s


def vignette(size):
    w, h = size
    s = pygame.Surface(size)
    s.fill((85, 85, 95))
    steps = 40
    for i in range(steps):
        k = i / steps
        c = int(255 - 170 * (1 - k) ** 2.2)
        rect = pygame.Rect(0, 0, w * (1.5 - 0.6 * k), h * (1.6 - 0.65 * k))
        rect.center = (w // 2, h // 2)
        pygame.draw.ellipse(s, (c, c, c), rect)
    return s

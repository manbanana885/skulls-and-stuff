"""Skulls & Stuff - isometric twin-stick shooter with procedurally generated sectors."""
import os
import sys
import math
import json
import random
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assets as A  # noqa: E402
from assets import load_all, to_screen, dir_index, glow, shadow, vignette, ROOT  # noqa: E402
from world import World, Particle  # noqa: E402
import characters as CH  # noqa: E402
import weapons as WP  # noqa: E402
from biomes import BIOMES, biome_for  # noqa: E402
from bosses import eel_points  # noqa: E402
import sfx  # noqa: E402
import netplay as NP  # noqa: E402

S = A.S
W, H = int(960 * S), int(540 * S)
HW, HH = A.HALF_W, A.HALF_H
SAVE = os.environ.get("SKULLS_SAVE") or os.path.join(ROOT, "save.json")   # tests point this somewhere harmless
rnd = random.Random()


def sc(v):
    return int(v * S)


# ================================================================ input
def scan_devices():
    """All connected gamepads as ('pad', controller) or ('joy', joystick) tuples."""
    devs = []
    try:
        from pygame._sdl2 import controller as C
        C.init()
        for i in range(C.get_count()):
            if C.is_controller(i):
                devs.append(("pad", C.Controller(i)))
    except Exception:
        pass
    if not devs:
        for i in range(pygame.joystick.get_count()):
            devs.append(("joy", pygame.joystick.Joystick(i)))
    return devs


class Input:
    DEAD = 0.22

    def __init__(self, keyboard=True, dev=None):
        self.keyboard = keyboard
        self.pad = None
        self.joy = None
        self.set_device(dev)
        self.mouse_mode = keyboard
        self.move = (0.0, 0.0)
        self.aim = None
        self.fire = False
        self._prev = {}
        self.pressed = set()
        self.pending = set()

    def set_device(self, dev):
        self.dev = dev
        self.pad = dev[1] if dev and dev[0] == "pad" else None
        self.joy = dev[1] if dev and dev[0] == "joy" else None

    def scan(self):
        pass

    @property
    def device_name(self):
        if self.pad:
            try:
                return self.pad.name
            except Exception:
                return "Gamepad"
        if self.joy:
            return self.joy.get_name()
        return None

    def stick(self, x, y):
        m = math.hypot(x, y)
        if m < self.DEAD:
            return 0.0, 0.0, 0.0
        s = (min(1.0, m) - self.DEAD) / (1 - self.DEAD)
        return x / m * s, y / m * s, s

    def edge(self, name, down):
        was = self._prev.get(name, False)
        self._prev[name] = down
        if down and not was:
            self.pressed.add(name)

    def poll(self, player_screen):
        self.pressed = set(self.pending)
        self.pending.clear()
        keys = pygame.key.get_pressed() if self.keyboard else _NOKEYS
        kx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        ky = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        km = math.hypot(kx, ky)
        move = (kx / km, ky / km) if km else (0.0, 0.0)
        aim, fire = None, False
        lx = ly = rx = ry = rt = 0.0
        start = a = bx = by = lb = rb = back = False
        try:
            if self.pad:
                g = self.pad.get_axis
                lx, ly = g(pygame.CONTROLLER_AXIS_LEFTX) / 32767, g(pygame.CONTROLLER_AXIS_LEFTY) / 32767
                rx, ry = g(pygame.CONTROLLER_AXIS_RIGHTX) / 32767, g(pygame.CONTROLLER_AXIS_RIGHTY) / 32767
                rt = g(pygame.CONTROLLER_AXIS_TRIGGERRIGHT) / 32767
                start = self.pad.get_button(pygame.CONTROLLER_BUTTON_START)
                a = self.pad.get_button(pygame.CONTROLLER_BUTTON_A)
                bx = self.pad.get_button(pygame.CONTROLLER_BUTTON_X)
                by = self.pad.get_button(pygame.CONTROLLER_BUTTON_Y)
                lb = self.pad.get_button(pygame.CONTROLLER_BUTTON_LEFTSHOULDER)
                rb = self.pad.get_button(pygame.CONTROLLER_BUTTON_RIGHTSHOULDER)
                back = self.pad.get_button(pygame.CONTROLLER_BUTTON_BACK)
            elif self.joy:
                j = self.joy
                n = j.get_numaxes()
                lx, ly = j.get_axis(0), j.get_axis(1)
                if n >= 4:
                    rx, ry = j.get_axis(2), j.get_axis(3)
                if n >= 6:
                    rt = (j.get_axis(5) + 1) / 2
                nb = j.get_numbuttons()
                start = nb > 7 and j.get_button(7)
                a = nb > 0 and j.get_button(0)
                bx = nb > 2 and j.get_button(2)
                by = nb > 3 and j.get_button(3)
                lb = nb > 4 and j.get_button(4)
                rb = nb > 5 and j.get_button(5)
                back = nb > 6 and j.get_button(6)
        except Exception:
            pass
        mx, my, ms = self.stick(lx, ly)
        if ms > 0:
            move = (mx, my)
            self.mouse_mode = False
        ax, ay, am = self.stick(rx, ry)
        if am > 0:
            aim = (ax, ay)
            fire = am > 0.35
            self.mouse_mode = False
        if rt > 0.3:
            fire = True
            self.mouse_mode = False
        if self.mouse_mode and self.keyboard:
            mpos = pygame.mouse.get_pos()
            dx, dy = mpos[0] - player_screen[0], mpos[1] - player_screen[1]
            if math.hypot(dx, dy) > 4:
                aim = (dx, dy)
            fire = pygame.mouse.get_pressed()[0] or keys[pygame.K_SPACE]
        self.move, self.aim, self.fire = move, aim, fire
        self.edge("start", bool(start) or keys[pygame.K_RETURN])
        self.edge("a", bool(a))
        self.edge("reload", bool(bx) or keys[pygame.K_r])
        self.edge("swap", bool(by) or keys[pygame.K_q])
        self.edge("dash", bool(lb) or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        bb = False
        try:
            if self.pad:
                bb = self.pad.get_button(pygame.CONTROLLER_BUTTON_B)
            elif self.joy:
                bb = self.joy.get_numbuttons() > 1 and self.joy.get_button(1)
        except Exception:
            pass
        self.edge("deploy", bool(bb or rb) or keys[pygame.K_f])
        self.edge("interact", bool(a) or keys[pygame.K_e])
        self.edge("back", bool(back))
        up = dn = lf = rg = False
        try:
            if self.pad:
                b = self.pad.get_button
                up, dn = b(pygame.CONTROLLER_BUTTON_DPAD_UP), b(pygame.CONTROLLER_BUTTON_DPAD_DOWN)
                lf, rg = b(pygame.CONTROLLER_BUTTON_DPAD_LEFT), b(pygame.CONTROLLER_BUTTON_DPAD_RIGHT)
            elif self.joy and self.joy.get_numhats():
                hx, hy = self.joy.get_hat(0)
                up, dn, lf, rg = hy > 0, hy < 0, hx < 0, hx > 0
        except Exception:
            pass
        for k_, (d_, key_) in enumerate(((up, pygame.K_1), (rg, pygame.K_2), (dn, pygame.K_3), (lf, pygame.K_4))):
            self.edge("slot%d" % (k_ + 1), bool(d_) or keys[key_])
        up = up or ly < -0.6 or keys[pygame.K_w] or keys[pygame.K_UP]
        dn = dn or ly > 0.6 or keys[pygame.K_s] or keys[pygame.K_DOWN]
        lf = lf or lx < -0.6 or keys[pygame.K_a] or keys[pygame.K_LEFT]
        rg = rg or lx > 0.6 or keys[pygame.K_d] or keys[pygame.K_RIGHT]
        self.edge("nav_up", bool(up))
        self.edge("nav_down", bool(dn))
        self.edge("nav_left", bool(lf))
        self.edge("nav_right", bool(rg))
        self.edge("confirm", bool(a) or keys[pygame.K_e] or keys[pygame.K_SPACE])


class _NoKeys:
    def __getitem__(self, k):
        return False


_NOKEYS = _NoKeys()


WORN = {"gunarm", "leech", "core", "decoy", "mines", "aura", "battery", "autoloader", "jets", "magnet", "tether",
        "grenade", "barrel", "mgturret", "mortar"}


# ================================================================ cached floor
class FloorLayer:
    """Floor tiles pre-composited into screen-space chunks (hundreds of blits -> a dozen)."""
    CH = 512

    SHADES = (0.82, 0.9, 1.0, 1.07, 1.14)

    def __init__(self, level, spr, decals):
        self.L = level
        self.spr = spr
        self.decals = decals
        self.chunks = {}
        self.warm = False
        self.tiles = {}
        # coarse value-noise grid -> smooth light/dark patches across the floor
        rng = random.Random(level.seed ^ 0x5EED)
        self.cell = 5
        self.nw, self.nh = level.W // self.cell + 2, level.H // self.cell + 2
        self.noise = [rng.random() for _ in range(self.nw * self.nh)]

    def shade_at(self, x, y):
        fx, fy = x / self.cell, y / self.cell
        ix, iy = int(fx), int(fy)
        tx, ty = fx - ix, fy - iy
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        n, w = self.noise, self.nw
        a = n[iy * w + ix] * (1 - tx) + n[iy * w + ix + 1] * tx
        b = n[(iy + 1) * w + ix] * (1 - tx) + n[(iy + 1) * w + ix + 1] * tx
        v = a * (1 - ty) + b * ty
        return min(len(self.SHADES) - 1, int(v * len(self.SHADES)))

    def tile(self, name, x, y):
        """Pick a variant, mirroring and shade for this cell (all cached)."""
        sp = self.spr[name]
        h = (x * 73856093) ^ (y * 19349663) ^ 0x2545F491
        h = (h ^ (h >> 13)) * 0x5bd1e995 & 0xFFFFFFFF
        nvar = sp.anims["idle"]
        v = h % nvar
        flip = bool((h >> 8) & 1)
        shade = self.shade_at(x, y)
        key = (name, v, flip, shade)
        img = self.tiles.get(key)
        if img is None:
            img = sp.get("idle", 0, v)
            if flip:
                img = pygame.transform.flip(img, True, False)
            k = self.SHADES[shade]
            if k != 1.0:
                img = img.copy()
                if k < 1:
                    c = int(255 * k)
                    img.fill((c, c, c), special_flags=pygame.BLEND_RGB_MULT)
                else:
                    c = int(255 * (k - 1))
                    img.fill((c, c, c), special_flags=pygame.BLEND_RGB_ADD)
            self.tiles[key] = img
        return img, sp

    def invalidate_cell(self, x, y):
        sx, sy = to_screen(x + 0.5, y + 0.5)
        r = HW * 1.6
        CH = self.CH
        for cx in range(int((sx - r) // CH), int((sx + r) // CH) + 1):
            for cy in range(int((sy - r) // CH), int((sy + r) // CH) + 1):
                self.chunks.pop((cx, cy), None)

    def build(self, cx, cy):
        CH = self.CH
        L = self.L
        surf = pygame.Surface((CH, CH), pygame.SRCALPHA)
        x0, y0 = cx * CH, cy * CH
        s_lo, s_hi = int(y0 / HH) - 4, int((y0 + CH) / HH) + 4
        d_lo, d_hi = int(x0 / HW) - 3, int((x0 + CH) / HW) + 3
        solid, floor, W_ = L.solid, L.floor, L.W
        for ssum in range(s_lo, s_hi + 1):
            for diff in range(d_lo, d_hi + 1):
                if (ssum - diff) % 2:
                    continue
                X, Y = (ssum - diff) // 2, (ssum + diff) // 2
                if not (0 <= X < L.W and 0 <= Y < L.H):
                    continue
                i = Y * W_ + X
                if solid[i] == 1 or not floor[i]:
                    continue
                img, sp = self.tile(floor[i], X, Y)
                surf.blit(img, ((Y - X) * HW - sp.ax - x0, (X + Y + 1) * HH - sp.ay - y0))
        dc = self.decals.chunks.get((cx, cy))
        if dc is not None:
            # blood/stains composited in, masked to where there actually is floor
            temp = dc.copy()
            mask = surf.copy()
            mask.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
            temp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(temp, (0, 0))
        self.chunks[(cx, cy)] = surf
        return surf

    def draw(self, target, ox, oy):
        CH = self.CH
        for x, y in self.L.changed:
            self.invalidate_cell(x, y)
        self.L.changed.clear()
        x_lo, x_hi = int((-ox) // CH), int((W - ox) // CH)
        y_lo, y_hi = int((-oy) // CH), int((H - oy) // CH)
        built = 0
        for cx in range(x_lo, x_hi + 1):
            for cy in range(y_lo, y_hi + 1):
                surf = self.chunks.get((cx, cy))
                if surf is None:
                    if built >= 2 and self.warm:   # spread rebuild cost over frames
                        continue
                    surf = self.build(cx, cy)
                    built += 1
                target.blit(surf, (cx * CH + ox, cy * CH + oy))
        self.warm = True
        if len(self.chunks) > 60:   # evict far-away chunks
            for key in [k for k in self.chunks if not (x_lo - 2 <= k[0] <= x_hi + 2 and y_lo - 2 <= k[1] <= y_hi + 2)]:
                del self.chunks[key]


# ================================================================ persistent gore
class DecalLayer:
    """Blood splats baked into lazily-allocated screen-space chunks: permanent and cheap to draw."""
    CH = 512

    def __init__(self):
        self.chunks = {}

    def bake(self, decals, floor_chunks=None):
        """Bake any splats the world added since last call (also straight into cached floor chunks)."""
        CH = self.CH
        for x, y, col, r, var in decals:
            img = A.splat(col, r * HW, var)
            wx, wy = to_screen(x, y)
            x0, y0 = wx - img.get_width() / 2, wy - img.get_height() / 2
            x1, y1 = x0 + img.get_width(), y0 + img.get_height()
            for cx in range(int(x0 // CH), int(x1 // CH) + 1):
                for cy in range(int(y0 // CH), int(y1 // CH) + 1):
                    surf = self.chunks.get((cx, cy))
                    if surf is None:
                        surf = self.chunks[(cx, cy)] = pygame.Surface((CH, CH), pygame.SRCALPHA)
                    surf.blit(img, (x0 - cx * CH, y0 - cy * CH))
                    if floor_chunks is not None:
                        fc = floor_chunks.get((cx, cy))
                        if fc is not None:
                            fc.blit(img, (x0 - cx * CH, y0 - cy * CH))
        decals.clear()

    def draw(self, target, ox, oy):
        CH = self.CH
        for cx in range(int((-ox) // CH), int((W - ox) // CH) + 1):
            for cy in range(int((-oy) // CH), int((H - oy) // CH) + 1):
                surf = self.chunks.get((cx, cy))
                if surf is not None:
                    target.blit(surf, (cx * CH + ox, cy * CH + oy))


# ================================================================ fx textures
def make_puffs(n=6, size=64, seed=3):
    """Soft, lumpy white blobs used (tinted, additive) for flames."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        surf = pygame.Surface((size, size))
        surf.fill((0, 0, 0))
        for _ in range(14):
            cx = size / 2 + rng.gauss(0, size * 0.12)
            cy = size / 2 + rng.gauss(0, size * 0.12)
            r = rng.uniform(0.12, 0.3) * size
            blob = pygame.Surface((size, size))
            blob.fill((0, 0, 0))
            for k in range(6, 0, -1):
                v = int(60 * (1 - k / 7))
                pygame.draw.circle(blob, (v, v, v), (cx, cy), r * k / 6)
            surf.blit(blob, (0, 0), special_flags=pygame.BLEND_ADD)
        arr = pygame.surfarray.pixels3d(surf)
        arr[:] = (arr.astype("float32") / max(1, arr.max()) * 255).astype("uint8")
        del arr
        out.append(surf)
    return out


CHEM_RAMP = [(240, 255, 200), (215, 245, 110), (180, 225, 50), (140, 190, 30), (100, 150, 20), (70, 110, 15), (45, 70, 10), (25, 40, 6)]
CRYO_RAMP = [(240, 250, 255), (200, 235, 255), (150, 210, 255), (110, 180, 250), (80, 140, 220), (55, 100, 180), (35, 65, 120), (20, 35, 70)]
FLAME_RAMP = [(255, 250, 215), (255, 225, 120), (255, 175, 55), (255, 120, 25), (225, 70, 12), (150, 35, 6), (80, 18, 4), (40, 10, 3)]


def make_static(w, h, frames=4, seed=9):
    rng = random.Random(seed)
    out = []
    lw, lh = w // 6, h // 6
    for _ in range(frames):
        s = pygame.Surface((lw, lh))
        arr = pygame.surfarray.pixels3d(s)
        import numpy as np
        noise = np.array([rng.randrange(256) for _ in range(lw * lh)], dtype="uint8").reshape(lw, lh)
        arr[:, :, 0] = noise
        arr[:, :, 1] = noise
        arr[:, :, 2] = noise
        del arr
        out.append(pygame.transform.scale(s, (w, h)))
    return out


class Ambient:
    """Screen-space weather: snow, ash, embers, dust."""

    def __init__(self, kind):
        self.kind = kind
        r = random.Random()
        n = {"snow": 160, "ash": 110, "embers": 70, "dust": 50, "rain": 170, "petals": 90, "spores": 70, "fumes": 45, "radglow": 70}.get(kind, 0)
        self.p = [[r.uniform(0, W), r.uniform(0, H), r.uniform(0.4, 1.0), r.uniform(0, 6.28)] for _ in range(n)]

    def update_draw(self, s, dt, cam_dx, cam_dy, t, add_glow):
        k = self.kind
        for q in self.p:
            depth = q[2]
            if k == "snow":
                q[0] += (math.sin(t + q[3]) * 20 - 25) * S * dt * depth
                q[1] += 55 * S * dt * depth
            elif k == "ash":
                q[0] += math.sin(t * 0.7 + q[3]) * 18 * S * dt
                q[1] += 18 * S * dt * depth
            elif k == "embers" or k == "radglow" or k == "spores":
                q[0] += math.sin(t * 2 + q[3]) * 25 * S * dt
                q[1] -= (35 if k != "spores" else 14) * S * dt * depth
            elif k == "rain":
                q[0] -= 160 * S * dt * depth
                q[1] += 700 * S * dt * depth
            elif k == "petals":
                q[0] += (math.sin(t * 0.9 + q[3]) * 40 - 30) * S * dt
                q[1] += 30 * S * dt * depth
            elif k == "fumes":
                q[0] += math.sin(t * 0.2 + q[3]) * 10 * S * dt
                q[1] -= 6 * S * dt
            else:
                q[0] += math.sin(t * 0.3 + q[3]) * 6 * S * dt
                q[1] += math.cos(t * 0.2 + q[3]) * 6 * S * dt
            q[0] -= cam_dx * depth
            q[1] -= cam_dy * depth
            q[0] %= W
            q[1] %= H
            x, y = q[0], q[1]
            if k == "snow":
                pygame.draw.circle(s, (225, 235, 255), (x, y), max(1, 2.2 * S * depth))
            elif k == "ash":
                c = int(90 + 60 * depth)
                pygame.draw.rect(s, (c, c - 8, c - 12), (x, y, sc(3) * depth, sc(2) * depth))
            elif k == "embers":
                fl = 0.6 + 0.4 * math.sin(t * 8 + q[3])
                pygame.draw.circle(s, (255, int(140 * fl), 30), (x, y), max(1, 1.6 * S * depth))
                add_glow(x, y, sc(6), (int(90 * fl), int(30 * fl), 5))
            elif k in ("radglow", "spores"):
                fl = 0.6 + 0.4 * math.sin(t * 5 + q[3])
                c = (120, 255, 60) if k == "radglow" else (90, 255, 220)
                pygame.draw.circle(s, c, (x, y), max(1, 1.5 * S * depth))
                add_glow(x, y, sc(7), (int(c[0] * 0.3 * fl), int(c[1] * 0.3 * fl), int(c[2] * 0.3 * fl)))
            elif k == "rain":
                pygame.draw.line(s, (120, 130, 150), (x, y), (x + 4 * S * depth, y - 18 * S * depth), max(1, int(S)))
            elif k == "petals":
                pygame.draw.rect(s, (200, 40, 90), (x, y, sc(4) * depth, sc(2.5) * depth))
            elif k == "fumes":
                add_glow(x, y, sc(30) * depth, (30, 8, 40))
            else:
                c = int(70 * depth)
                pygame.draw.circle(s, (c, c, c + 10), (x, y), max(1, S * depth))


# ================================================================ game
_smoke_cache = {}


def smoke_surf(r, alpha, color):
    key = (r, alpha // 8, color)
    s = _smoke_cache.get(key)
    if s is None:
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for k in range(4):
            rr = int(r * (1 - k * 0.2))
            pygame.draw.circle(s, (*color, int(alpha * (0.35 + k * 0.2))), (r, r), rr)
        _smoke_cache[key] = s
    return s


class Game:
    def __init__(self, windowed=False):
        pygame.init()
        sfx.init()
        flags = pygame.SCALED | (pygame.RESIZABLE if windowed else pygame.FULLSCREEN)
        self.screen = pygame.display.set_mode((W, H), flags)
        pygame.display.set_caption("Skulls & Stuff")
        self.spr = load_all()
        self.font = pygame.font.Font(None, sc(22))
        self.mid = pygame.font.Font(None, sc(34))
        self.big = pygame.font.Font(None, sc(78))
        self.small = pygame.font.Font(None, sc(18))
        self.ammo_font = pygame.font.Font(None, sc(50))
        self._tint = {}
        self._p2 = {}
        self._pillar = {}
        self._pool = {}
        self.last_o = (0, 0)
        self.vig = vignette((W, H))
        self.vig_biome = self.vig
        self.puffs = make_puffs(6, sc(48))
        self._flame = {}
        self.static_frames = make_static(W, H)
        self.ambient = None
        self.run_seed = random.randrange(1 << 30)
        self.biome = "facility"
        self.devices = scan_devices()
        self.inputs = [Input(True, self.devices[0] if self.devices else None)]
        self.spare = {}
        self.refresh_spares()
        self.state = "title"
        self.world = None
        self.cam = [0.0, 0.0]
        self.time = 0.0
        self.banner = ("", 0.0)
        self.transition = 0.0
        self.best = 0
        self.damage_numbers = False         # option: coloured damage numbers (off by default)
        self.chars = ["skelebot", "canbot"]  # character picked by P1 / P2 on the title screen
        self.last_host = ""                 # last address typed on the join screen
        self.last_name = ""                 # ... and the game name
        self.player_name = ""               # your name in net games
        try:
            with open(SAVE) as fh:
                data = json.load(fh)
                self.best = data.get("best", 0)
                self.damage_numbers = bool(data.get("damage_numbers", False))
                self.chars = [c if c in CH.CHARS else d for c, d in zip(data.get("chars", self.chars), self.chars)]
                self.last_host = str(data.get("last_host", ""))[:60]
                self.last_name = str(data.get("last_name", ""))[:40]
                self.player_name = str(data.get("player_name", ""))[:14]
        except Exception:
            pass
        self.minimap = None
        self._mouse_was = False
        self._mouse_pos = None
        self.net = None                     # net play: a HostSession, GuestSession or JoinScreen
        self.menu_i = 0                     # title menu: 0 play, 1 host, 2 join
        self.title_msg = ("", 0.0)
        self.W, self.H = W, H
        sfx.music("requiem")

    # ------------------------------------------------------------ input devices / co-op
    @property
    def input(self):
        return self.inputs[0]

    @input.setter
    def input(self, value):
        self.inputs[0] = value

    def owned(self):
        return [inp.dev for inp in self.inputs if inp.dev is not None]

    def refresh_spares(self):
        """Inputs for gamepads nobody owns yet (polled only to detect a join)."""
        owned = [id(d[1]) for d in self.owned()]
        self.spare = {id(d[1]): Input(False, d) for d in self.devices if id(d[1]) not in owned}

    def on_devices_changed(self):
        self.devices = scan_devices()
        ids = {id(d[1]) for d in self.devices}
        for i, inp in enumerate(self.inputs):
            if inp.dev is not None and id(inp.dev[1]) not in ids:
                inp.set_device(None)
        if self.inputs[0].dev is None and len(self.inputs) == 1 and self.devices:
            self.inputs[0].set_device(self.devices[0])
        self.refresh_spares()

    def try_join(self):
        """Second player: BACK/SELECT (or START) on a free pad. With a single pad, P1 keeps the keyboard and P2 takes the pad."""
        if len(self.inputs) >= 2 or self.state not in ("play", "title") or self.net is not None:
            return
        dev = None
        for inp in self.spare.values():
            if "back" in inp.pressed or "start" in inp.pressed:
                dev = inp.dev
                break
        self.join_from_p1 = False
        if dev is None and self.inputs[0].dev is not None and "back" in self.inputs[0].pressed:
            dev = self.inputs[0].dev          # hand P1's only pad to P2
            self.inputs[0].set_device(None)
            self.inputs[0].mouse_mode = True
            self.join_from_p1 = True
        if dev is None:
            return
        self.inputs.append(Input(False, dev))
        self.refresh_spares()
        sfx.play("weapon_pickup")
        if self.world and self.state == "play":
            self.state = "join"               # P2 picks a body first; the game waits

    def cancel_join(self):
        """P2 backed out of the pick screen: drop their input (and give a borrowed pad back to P1)."""
        inp = self.inputs.pop()
        if getattr(self, "join_from_p1", False) and self.inputs[0].dev is None:
            self.inputs[0].set_device(inp.dev)
            self.inputs[0].mouse_mode = False
        self.join_from_p1 = False
        self.refresh_spares()
        self.state = "play"
        sfx.play("swap", 0.6)

    def pick_char(self, i, inp):
        """LEFT / RIGHT on input inp cycles player i's body."""
        for name, d in (("nav_left", -1), ("nav_right", 1)):
            if name in inp.pressed:
                self.chars[i] = CH.ORDER[(CH.ORDER.index(self.chars[i]) + d) % len(CH.ORDER)]
                sfx.play("swap", 0.6)
                self.save_settings()

    def any_pressed(self, name):
        return any(name in inp.pressed for inp in self.inputs)

    # ------------------------------------------------------------ flow
    def new_world(self, depth, player=None, score=0):
        if player is None:
            from world import Player
            player = [Player(0, 0, i, self.chars[min(i, 1)]) for i in range(len(self.inputs))]
        if depth == 1:
            self.run_seed = random.randrange(1 << 30)
        self.biome = biome_for(depth, self.run_seed)
        self.world = World(depth, player, score, biome=self.biome)
        self.world.show_numbers = self.damage_numbers
        self.setup_view()

    def setup_view(self):
        """Biome look, floor / splat caches, camera, minimap and banner for the current world."""
        B = BIOMES[self.world.biome]
        depth = self.world.depth
        self.vig_biome = self.vig.copy()
        self.vig_biome.fill(B["tint"], special_flags=pygame.BLEND_MULT)
        self.ambient = Ambient(B["ambient"])
        self.decal_layer = DecalLayer()
        self.floor_layer = FloorLayer(self.world.level, self.spr, self.decal_layer)
        self.cam = list(self.cam_target())
        L = self.world.level
        self.minimap = pygame.Surface((L.W + L.H + 2, (L.W + L.H) // 2 + 2), pygame.SRCALPHA)
        self.banner = ("SECTOR %d  -  %s" % (depth, B["title"]), 3.0)
        sfx.music(B["music"], 2000)

    sc = staticmethod(sc)

    def local_players(self):
        """The players sitting at this machine (all of them, unless this is a net game)."""
        w = self.world
        if w is None:
            return []
        if self.net is None or not getattr(self.net, "local", None):
            return w.players
        return [p for p in w.players if p.idx in self.net.local] or w.players[:1]

    @staticmethod
    def pname(p):
        """A player's display name: what they typed, else P1..P4."""
        return getattr(p, "name", "") or "P%d" % (p.idx + 1)

    def leave_net(self):
        if self.net is not None:
            self.net.leave(self)
        self.net = None
        self.world = None
        self.transition = 0.0
        self.state = "title"
        sfx.stop_loops()
        sfx.music("requiem")

    def net_error(self, msg):
        self.leave_net()
        self.title_msg = (msg, 8.0)

    def save_best(self):
        if self.world and self.world.score > self.best:
            self.best = self.world.score
            self.save_settings()

    def save_settings(self):
        try:
            with open(SAVE, "w") as fh:
                json.dump({"best": self.best, "damage_numbers": self.damage_numbers, "chars": self.chars,
                           "last_host": self.last_host, "last_name": self.last_name,
                           "player_name": self.player_name}, fh)
        except Exception:
            pass

    def toggle_numbers(self):
        self.damage_numbers = not self.damage_numbers
        if self.world:
            self.world.show_numbers = self.damage_numbers
        self.save_settings()
        sfx.play("swap", 0.6)

    def run(self):
        clock = pygame.time.Clock()
        while True:
            dt = min(clock.tick(60) / 1000.0, 1 / 30)
            self.time += dt
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.save_best()
                    return
                if ev.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    self.inputs[0].mouse_mode = True
                if ev.type == pygame.MOUSEWHEEL and self.state == "play":
                    self.inputs[0].pending.add("swap")
                if ev.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED,
                               getattr(pygame, "CONTROLLERDEVICEADDED", -1), getattr(pygame, "CONTROLLERDEVICEREMOVED", -1)):
                    self.on_devices_changed()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()
                    elif self.net is not None and hasattr(self.net, "key") and self.net.key(self, ev):
                        pass                          # typed into a lobby / join screen box
                    elif ev.key == pygame.K_ESCAPE and self.net is not None:
                        if self.state == "play":      # Esc in a net game: menu first, then leave the game
                            self.state = "pause"
                        else:
                            self.leave_net()
                    elif ev.key == pygame.K_ESCAPE:
                        # Esc pauses; Esc again (or on title / game over) quits
                        if self.state == "play":
                            self.state = "pause"
                        else:
                            self.save_best()
                            return
            for i, inp in enumerate(self.inputs):
                inp.poll(self.player_on_screen(i))
            for inp in self.spare.values():
                inp.poll((0, 0))
            self.try_join()
            self.update(dt)
            self.draw()
            pygame.display.flip()

    def player_on_screen(self, i=0):
        mine = self.local_players()
        if i >= len(mine):
            return (W / 2, H / 2)
        p = mine[i]
        sx, sy = to_screen(p.x, p.y, 1.1)
        return (sx - self.cam[0] + W / 2, sy - self.cam[1] + H / 2)

    TITLE_MENU = ("PLAY", "HOST NET GAME", "JOIN NET GAME")

    def update(self, dt):
        inp = self.inputs
        self.title_msg = (self.title_msg[0], self.title_msg[1] - dt)
        if self.net is not None:
            self.net.update(self, dt)
            return
        if self.state != "play" or self.transition > 0:
            sfx.stop_loops()
        if self.state == "title":
            if self.any_pressed("swap"):
                self.toggle_numbers()
                return
            for i, inp_ in enumerate(self.inputs[:2]):
                self.pick_char(i, inp_)
            if self.any_pressed("nav_up") or self.any_pressed("nav_down"):
                self.menu_i = (self.menu_i + (1 if self.any_pressed("nav_down") else -1)) % len(self.TITLE_MENU)
                sfx.play("tink", 0.5)
            clicked = False
            if self.inputs[0].keyboard:           # the mouse: pointing at a box picks it, clicking it goes
                down = pygame.mouse.get_pressed()[0]
                pos = pygame.mouse.get_pos()
                over = next((i for i, r in enumerate(self.title_menu_rects()) if r.collidepoint(pos)), None)
                if over is not None and pos != self._mouse_pos:
                    self.menu_i = over
                self._mouse_pos = pos
                clicked = down and not self._mouse_was and over is not None
                if clicked:
                    self.menu_i = over
                self._mouse_was = down
            if clicked or any(("start" in i.pressed or "a" in i.pressed) for i in self.inputs):
                sfx.play("start")
                if self.menu_i == 0:
                    self.new_world(1)
                    self.state = "play"
                elif self.menu_i == 1:
                    try:
                        self.net = NP.HostSession(self)
                    except OSError as ex:
                        self.net = None
                        self.title_msg = ("Can't host a game here: %s" % (ex.strerror or ex), 8.0)
                else:
                    self.net = NP.JoinScreen(self)
            return
        if self.state == "join":
            p2 = self.inputs[1]
            self.pick_char(1, p2)
            if "a" in p2.pressed or "start" in p2.pressed:
                self.world.add_player(self.chars[1])
                self.state = "play"
            elif "deploy" in p2.pressed or "back" in p2.pressed:
                self.cancel_join()
            return
        if self.state == "pause":
            if self.any_pressed("start"):
                self.state = "play"
                return
            if self.any_pressed("swap"):
                self.toggle_numbers()
            for i, p in enumerate(self.world.players):
                if i < len(self.inputs):
                    self.inventory_input(p, self.inputs[i])
            return
        if self.state == "dead":
            self.world.update(dt, inp)
            self.update_camera(dt)
            if self.time > self.dead_at + 1.5 and (self.any_pressed("start") or self.any_pressed("a")):
                self.new_world(1)
                self.state = "play"
            return
        if self.any_pressed("start"):
            self.state = "pause"
            return
        w = self.world
        if self.transition > 0:
            self.transition -= dt
            if self.transition <= 0:
                for p in w.players:
                    p.hp = min(p.max_hp, p.hp + 25)
                self.new_world(w.depth + 1, w.players, w.score)
            return
        w.update(dt, inp)
        self.banner = (self.banner[0], self.banner[1] - dt)
        self.update_camera(dt)
        if w.exit_reached:
            self.transition = 0.9
            sfx.play("portal")
        if not any(p.alive for p in w.players):
            self.state = "dead"
            self.dead_at = self.time
            sfx.music(None, 3000)
            self.save_best()

    def cam_target(self):
        """Frame every living player; aim look-ahead only when playing solo."""
        mine = self.local_players()
        alive = [p for p in mine if p.alive] or mine[:1]
        pts = [to_screen(p.x, p.y, 0.8) for p in alive]
        tx = sum(a for a, _ in pts) / len(pts)
        ty = sum(b for _, b in pts) / len(pts)
        if len(alive) == 1:
            ax, ay = alive[0].aim
            tx += (ay - ax) * HW * 1.4
            ty += (ax + ay) * HH * 1.4
        return tx, ty

    def update_camera(self, dt):
        tx, ty = self.cam_target()
        k = min(1.0, dt * 5)
        self.cam[0] += (tx - self.cam[0]) * k
        self.cam[1] += (ty - self.cam[1]) * k

    # ------------------------------------------------------------ rendering
    def draw(self):
        s = self.screen
        if self.net is not None and self.net.draw(self, s):
            return
        if self.state == "title" or self.world is None:
            self.draw_title(s)
            return
        self.draw_world(s)
        self.draw_hud(s)
        if self.state == "pause":
            self.draw_inventory(s)
        elif self.state == "join":
            self.overlay(s, 225)
            self.center_text(s, self.big, "PLAYER 2", sc(120), self.PLAYER_COLORS[1])
            self.draw_char_row(s, [1], H / 2 + sc(40))
            self.center_text(s, self.font, "P2: LEFT / RIGHT choose a body   -   A / START join   -   B / BACK cancel",
                             H / 2 + sc(150), (255, 220, 120))
        elif self.state == "dead":
            a = min(170, int((self.time - self.dead_at) * 200))
            self.overlay(s, a)
            if self.time > self.dead_at + 0.6:
                self.center_text(s, self.big, "SYSTEMS OFFLINE", H / 2 - sc(60), (255, 70, 50))
                w = self.world
                self.center_text(s, self.mid, "Score %d   -   Sector %d   -   %d kills" % (w.score, w.depth, w.kills), H / 2, (230, 230, 230))
                self.center_text(s, self.font, "Best %d" % self.best, H / 2 + sc(34), (170, 180, 200))
                if self.net is not None and not self.net.is_host:
                    self.center_text(s, self.font, "Waiting for the host to reboot", H / 2 + sc(70), (120, 230, 255))
                elif self.time > self.dead_at + 1.5:
                    self.center_text(s, self.font, "Press START / ENTER to reboot", H / 2 + sc(70), (120, 230, 255))
        if self.transition > 0:
            self.overlay(s, int(255 * (1 - self.transition / 0.9)), (200, 240, 255))
        if self.net is not None:
            st = self.net.status_line(self)
            if st:
                img = self.small.render(st, True, (120, 200, 220))
                s.blit(img, (W - img.get_width() - sc(12), H - sc(20)))

    # ------------------------------------------------------------ pause menu: gear + backpack
    INV_COLS, INV_ROWS = 4, 4          # row 0 = your two guns, row 1 = the 4 module slots (D-pad), rows 2-3 = the 8 backpack slots

    def inv_item(self, p, col, row):
        if row == 0:
            return p.weapons[col] if col < 2 else None
        if row == 1:
            return p.gear[col]
        k = (row - 2) * self.INV_COLS + col
        return p.pack[k] if k < len(p.pack) else None

    def inventory_input(self, p, inp):
        import world as WD
        pr = inp.pressed
        c, r = p.inv_cur
        moved = False
        for name, dc, dr in (("nav_left", -1, 0), ("nav_right", 1, 0), ("nav_up", 0, -1), ("nav_down", 0, 1)):
            if name in pr:
                r = (r + dr) % self.INV_ROWS
                c = (c + dc) % (2 if r == 0 else self.INV_COLS)
                moved = True
        if r == 0:
            c = min(c, 1)
        if moved:
            p.inv_cur = (c, r)
            sfx.play("swap", 0.4)
        item = self.inv_item(p, c, r)
        if r == 0:                                   # guns: confirm takes the highlighted gun in hand
            if "confirm" in pr and c != p.cur:
                p.weapon.reload_t = 0.0
                p.cur = c
                sfx.play("swap")
            return
        if "confirm" in pr and item is not None:
            if r == 1:
                if p.unequip(c):
                    sfx.play("reload", 0.6)
                else:
                    self.world.message("Backpack full - drop something first", (255, 140, 120))
            else:
                p.equip_from_pack((r - 2) * self.INV_COLS + c, c)
                sfx.play("power", 0.6)
        if "reload" in pr and item is not None:          # X / R drops the highlighted module
            if r == 1:
                p.gear[c] = None
            else:
                p.pack.pop((r - 2) * self.INV_COLS + c)
            self.world.drop_item(p, item)
            sfx.play("weapon_pickup", 0.6)
        assert len(p.pack) <= WD.PACK_SIZE

    def draw_inventory(self, s):
        self.overlay(s, 220)
        mine = self.local_players()
        coop = len(mine) > 1
        netg = self.net is not None
        self.center_text(s, self.big, "MENU" if netg else "PAUSED", sc(40), (230, 235, 255))
        self.center_text(s, self.font, ("START / ENTER back to the game   -   ESC leave the net game" if netg else
                                        "START / ENTER resume   -   ESC quit") + "   -   [Q / Y] damage numbers: %s"
                         % ("ON" if self.damage_numbers else "OFF"), sc(78), (150, 160, 180))
        if netg:
            self.center_text(s, self.small, "The game keeps running for everyone while you're in here", sc(96), (255, 170, 130))
        if not coop:      # grid on the left, card beside it
            box, gap, card = sc(62), sc(10), sc(370)
            gw = box * self.INV_COLS + gap * (self.INV_COLS - 1)
            x0 = int(W / 2 - (gw + sc(30) + card) / 2)
            self.draw_gear_panel(s, mine[0], x0, sc(104), box, gap, (x0 + gw + sc(30), sc(140)), card)
        else:             # one column per player, card under the grid
            box, gap, card = sc(46), sc(8), sc(370)
            x0 = W / 2 - (card * 2 + sc(80)) / 2
            for i, p in enumerate(mine):
                x = int(x0 + i * (card + sc(80)))
                gw = box * self.INV_COLS + gap * (self.INV_COLS - 1)
                self.draw_gear_panel(s, p, x + (card - gw) // 2, sc(100), box, gap, None, card)

    def inv_icon(self, img, w_, h_):
        key = ("icon", id(img), w_, h_)
        icon = self._tint.get(key)
        if icon is None:              # crop the sprite's empty margins so it fills the box
            bb = img.get_bounding_rect()
            sub = img.subsurface(bb)
            k = min(w_ * 0.85 / max(1, bb.width), h_ * 0.8 / max(1, bb.height))
            icon = self._tint[key] = pygame.transform.smoothscale(sub, (max(1, int(bb.width * k)), max(1, int(bb.height * k))))
        return icon

    def draw_gear_panel(self, s, p, x, y, box, gap, card_at, card_w):
        w = self.world
        coop = len(w.players) > 1
        col = self.PLAYER_COLORS[p.idx % 4] if coop else (150, 210, 230)
        gw = box * self.INV_COLS + gap * (self.INV_COLS - 1)
        cur = p.inv_cur
        cy = y
        for row in range(self.INV_ROWS):
            label = {0: (self.pname(p) + "  " if coop else "") + "WEAPONS", 1: "MODULES", 2: "BACKPACK"}.get(row)
            if label:
                f_ = self.mid if row < 2 else self.small
                s.blit(f_.render(label, True, col if row < 2 else (140, 145, 160)), (x, cy))
                cy += f_.get_height() + sc(4)
            if row == 0:                            # two wide gun slots
                ww = (gw - gap) // 2
                for c in range(2):
                    rect = pygame.Rect(x + c * (ww + gap), cy, ww, box)
                    wp = p.weapons[c]
                    self.panel(s, rect, 230)
                    pygame.draw.rect(s, wp.color, rect.inflate(-sc(4), -sc(4)), max(1, sc(2)))
                    gsp = self.spr.get("gun_" + WP.sprite_arch(wp.arch))
                    if gsp:
                        if (c, 0) == cur:
                            img = gsp.get("idle", 0, self.time * 8)
                        else:                      # resting: the spin frame that shows the gun most side-on
                            bf = self._tint.get(("sideon", wp.arch))
                            if bf is None:
                                bf = self._tint[("sideon", wp.arch)] = max(range(len(gsp.frames["idle"][0])),
                                                                           key=lambda f_: gsp.get("idle", 0, f_).get_bounding_rect().width)
                            img = gsp.get("idle", 0, bf)
                        icon = self.inv_icon(img, ww, box)
                        s.blit(icon, icon.get_rect(center=rect.center))
                    if c == p.cur:
                        t_ = self.small.render("IN HAND", True, (255, 220, 120))
                        t_ = self.scaled(t_, 0.8)
                        s.blit(t_, (rect.x + sc(5), rect.bottom - t_.get_height() - sc(3)))
                    if (c, 0) == cur:
                        pygame.draw.rect(s, (255, 230, 120), rect.inflate(sc(6), sc(6)), max(2, sc(3)))
                cy += box + gap + sc(6)
                continue
            for c in range(self.INV_COLS):
                bx = x + c * (box + gap)
                rect = pygame.Rect(bx, cy, box, box)
                item = self.inv_item(p, c, row)
                self.panel(s, rect, 230 if row == 1 else 190)
                if item is not None:
                    pygame.draw.rect(s, item.color, rect.inflate(-sc(4), -sc(4)), max(1, sc(2)))
                    sp = self.spr[item.sprite]
                    img = sp.get(sp.first_anim, 0, self.time * 8 if (c, row) == cur else 0)
                    icon = self.inv_icon(img, box, box)
                    s.blit(icon, icon.get_rect(center=rect.center))
                elif row == 1:
                    t = self.small.render("SLOT %d" % (c + 1), True, (90, 95, 110))
                    s.blit(t, t.get_rect(center=rect.center))
                if row == 1:                       # which D-pad direction / number key selects this slot
                    on = c == p.sel
                    t = self.scaled(self.small.render(("UP", "RIGHT", "DOWN", "LEFT")[c] + "  " + str(c + 1) + ("  *" if on else ""),
                                                      True, (255, 230, 120) if on else (150, 160, 175)), 0.75)
                    s.blit(t, (rect.x + sc(3), rect.y + sc(2)))
                if (c, row) == cur:
                    pygame.draw.rect(s, (255, 230, 120), rect.inflate(sc(6), sc(6)), max(2, sc(3)))
            cy += box + gap
        item = self.inv_item(p, *cur)
        cx, cy = card_at if card_at else ((x + gw // 2) - card_w // 2, cy + sc(30))
        keyboard = p.idx == 0 and self.inputs[0].keyboard
        if cur[1] == 0:
            wp = item
            other = p.weapons[1 - cur[0]]
            hint = "in hand" if cur[0] == p.cur else (("[E]" if keyboard else "[A]") + " take in hand")
            if getattr(self, "_measure", None) is None:
                self._measure = pygame.Surface((sc(800), sc(700)), pygame.SRCALPHA)
            r_ = self.weapon_card(self._measure, wp, 0, 0, compare=other, alpha=245)
            cy = min(cy, H - r_.height - sc(10))
            if cx + r_.width > W - sc(10):
                cx = W - sc(10) - r_.width
            s.blit(self.small.render(hint, True, (255, 220, 120)), (cx, cy - sc(24)))
            self.weapon_card(s, wp, cx, cy, compare=other, alpha=245)
        elif item is not None:
            act = "unequip" if cur[1] == 1 else "equip"
            keys = ("[E] %s   [R] drop" if keyboard else "[A] %s   [X] drop") % act
            s.blit(self.small.render(keys, True, (255, 220, 120)), (cx, cy - sc(24)))
            other = None
            if cur[1] > 1 and p.gear[cur[0]] is not None and p.gear[cur[0]].kind == item.kind:
                other = p.gear[cur[0]]
            self.support_card(s, item, cx, cy, compare=other, width=card_w, alpha=245)
        else:
            s.blit(self.small.render("empty slot" if cur[1] == 1 else "empty", True, (110, 115, 130)), (cx, cy))

    def overlay(self, s, alpha, color=(0, 0, 0)):
        o = pygame.Surface((W, H))
        o.fill(color)
        o.set_alpha(alpha)
        s.blit(o, (0, 0))

    def center_text(self, s, font, text, y, color):
        img = font.render(text, True, color)
        sh = font.render(text, True, (0, 0, 0))
        r = img.get_rect(center=(W / 2, y))
        s.blit(sh, r.move(sc(2), sc(2)))
        s.blit(img, r)

    def draw_world(self, surf):
        w = self.world
        L = w.level
        mine = self.local_players()
        p = next((q for q in mine if q.alive), None) or (mine[0] if mine else w.player)
        spr = self.spr
        shx = rnd.uniform(-1, 1) * w.shake * S
        shy = rnd.uniform(-1, 1) * w.shake * S
        ox = W / 2 - self.cam[0] + shx
        oy = H / 2 - self.cam[1] + shy
        surf.fill((9, 8, 13))
        alive = [q for q in mine if q.alive] or [p]
        pcx = int(sum(q.x for q in alive) / len(alive))
        pcy = int(sum(q.y for q in alive) / len(alive))
        pscr = [(to_screen(q.x, q.y)[0] + ox, to_screen(q.x, q.y)[1] + oy, q.x + q.y) for q in alive if q.alive]
        psx, psy = to_screen(p.x, p.y)
        psx += ox
        psy += oy
        pkey = p.x + p.y
        items = []
        n = 0
        R = 21
        m60, m24, m90 = sc(60), sc(24), sc(90)
        fade_dx, fade_up, fade_dn, fade_h = sc(52), sc(52), sc(18), sc(74)
        solid, floor, Wd = L.solid, L.floor, L.W
        for cx in range(max(0, pcx - R), min(L.W, pcx + R + 1)):
            for cy in range(max(0, pcy - R), min(L.H, pcy + R + 1)):
                sx = (cy - cx) * HW + ox
                sy = (cx + cy + 1) * HH + oy
                if sx < -m60 or sx > W + m60 or sy < -m24 or sy > H + m90:
                    continue
                i = cy * Wd + cx
                if solid[i] == 1:
                    if not L.edge[i]:
                        continue
                    sp = spr[L.wallkind[i]]
                    img = sp.get("idle", 0, ((cx * 92821) ^ (cy * 68917)) % 1009)
                    key = cx + cy + 1
                    for qx_, qy_, qk_ in pscr:
                        if key > qk_ + 0.3 and abs(sx - qx_) < fade_dx and sy - fade_up < qy_ and sy + fade_dn > qy_ - fade_h:
                            img = sp.faded(img)
                            break
                    n += 1
                    items.append((key, n, img, sx - sp.ax, sy - sp.ay))
                else:
                    prop = L.props.get((cx, cy))
                    if prop:
                        sp = spr[prop]
                        n += 1
                        items.append((cx + cy + 1, n, sp.get("idle", 0), sx - sp.ax, sy - sp.ay))

        def ground(x, y, z=0.0):
            a, b = to_screen(x, y, z)
            return a + ox, b + oy

        def on_screen(gx, gy):
            return -sc(120) < gx < W + sc(120) and -sc(60) < gy < H + sc(160)

        # floor layer: baked blood, then resting gibs / casings
        self.decal_layer.bake(w.decals, self.floor_layer.chunks)
        self.floor_layer.draw(surf, ox, oy)
        for g in w.gibs:
            if g.rest:
                gx, gy = ground(g.x, g.y)
                if on_screen(gx, gy):
                    sp = spr[g.sprite]
                    surf.blit(sp.get("spin", 0, g.frame), (gx - sp.ax, gy - sp.ay - sc(3)))
        self.last_o = (ox, oy)
        self.draw_trap_floor(surf, w, ground, on_screen)
        for wn in w.warnings:
            gx, gy = ground(wn[0], wn[1])
            if on_screen(gx, gy):
                k_ = 1 - wn[3] / wn[4]
                rx = int(wn[2] * HW * 1.414)
                rect = pygame.Rect(0, 0, rx * 2, rx)
                rect.center = (gx, gy)
                c = wn[5]
                # growing shadow of what's coming down
                shade = self._tint.get(("warnshadow", rx))
                if shade is None:
                    shade = self._tint[("warnshadow", rx)] = pygame.Surface((rx * 2, rx), pygame.SRCALPHA)
                    pygame.draw.ellipse(shade, (0, 0, 0, 255), shade.get_rect())
                sh_ = shade.copy()
                sh_.set_alpha(int(40 + 120 * k_))
                sr = rect.inflate(-rx * 2 * (1 - k_) * 0.7, -rx * (1 - k_) * 0.7)
                surf.blit(pygame.transform.scale(sh_, sr.size), sr.topleft)
                # bright outer ring + an inner ring closing in; flashes faster as impact nears
                blink = (int(self.time * (6 + 18 * k_)) % 2 == 0)
                ring_c = (255, 255, 255) if (k_ > 0.75 and blink) else c
                pygame.draw.ellipse(surf, ring_c, rect, max(2, sc(3)))
                inner = rect.inflate(-rx * 2 * (1 - k_), -rx * (1 - k_))
                if inner.width > 2:
                    pygame.draw.ellipse(surf, (min(255, c[0]), min(255, c[1]), min(255, c[2])), inner, max(1, sc(2)))
                self.add_glow(gx, gy, int(rx * 0.8), (c[0] // 6, c[1] // 6, c[2] // 6))
        for hz in w.hazards:
            gx, gy = ground(hz[0], hz[1])
            if on_screen(gx, gy):
                if hz[4] in ("acid", "acidp"):
                    self.draw_pool(gx, gy, hz)
                elif hz[4] == "jet":
                    self.draw_jet_pool(gx, gy, hz)
                elif hz[4] == "rad":
                    self.draw_rad(gx, gy, hz)
                elif hz[4] == "gas":
                    self.draw_gas(gx, gy, hz)
                else:
                    f = min(1.0, hz[3])
                    big = 1.6 if hz[4] == "blaze" else 1.3
                    self.add_glow(gx, gy, int(hz[2] * HW * big), (int(140 * f), int(50 * f), int(8 * f)))

        n = self.trap_items(w, items, n, ground, on_screen)

        # portal
        ex, ey = L.exit
        gx, gy = ground(ex, ey)
        if on_screen(gx, gy):
            sp = spr["portal"]
            locked = bool(w.bosses)
            pimg = sp.get("idle", 0, 0 if locked else self.time * 10)
            if locked:
                pimg = self.tinted(pimg, (255, 70, 60))
            n += 1
            items.append((ex + ey, n, pimg, gx - sp.ax, gy - sp.ay))
            n += 1
            pc = (90, 20, 15) if locked else (30, 90, 120)
            items.append((ex + ey, n, None, lambda gx=gx, gy=gy, c=pc: self.add_glow(gx, gy - sc(14), sc(40), c), 0))

        for s in w.spawners:
            gx, gy = ground(s.x, s.y)
            if on_screen(gx, gy):
                sp = spr["spawner"]
                img = sp.get("idle", 0, s.t * 5)
                n += 1
                items.append((s.x + s.y, n, img, gx - sp.ax, gy - sp.ay))
                if s.flash > 0:
                    n += 1
                    items.append((s.x + s.y, n, sp.flash(img), gx - sp.ax, gy - sp.ay))

        for lt in w.loot:
            gx, gy = ground(lt.x, lt.y)
            if not on_screen(gx, gy):
                continue
            surf.blit(shadow(sc(10)), (gx - sc(10), gy - sc(5)))
            bob = math.sin(lt.t * 3) * sc(4) - lt.z * A.ZPIX
            key = lt.x + lt.y
            if lt.kind == "weapon":
                sp = spr["gun_" + WP.sprite_arch(lt.item.arch)]
                col, rar = lt.item.color, lt.item.rarity
                n += 1
                items.append((key, n, None, lambda gx=gx, gy=gy, c=col, r=rar: self.draw_pillar(gx, gy, c, r), 0))
                if rar >= WP.DEMONIC:            # top-tier pickups glow hard
                    n += 1
                    items.append((key, n, None, lambda gx=gx, gy=gy, c=col: self.add_glow(gx, gy - sc(30), sc(70), (c[0] // 3, c[1] // 3, c[2] // 3)), 0))
                n += 1
                items.append((key, n, sp.get("idle", 0, lt.t * 8), gx - sp.ax, gy - sp.ay + bob))
            elif lt.kind == "support":
                sp = spr[lt.item.sprite]
                col, rar = lt.item.color, lt.item.rarity
                n += 1
                items.append((key, n, None, lambda gx=gx, gy=gy, c=col, r=rar: self.draw_pillar(gx, gy, c, r), 0))
                img = sp.get(sp.first_anim, int(lt.t * 2), lt.t * 8)
                n += 1
                items.append((key, n, img, gx - sp.ax, gy - sp.ay + bob - sc(26)))
            else:
                if lt.kind == "buff":
                    sp = spr["power"]
                    col = lt.item.color
                    img = self.tinted(sp.get("idle", 0, lt.t * 10), col)
                else:
                    sp = spr["health"]
                    col = (255, 60, 60)
                    img = sp.get("idle", 0, lt.t * 10)
                n += 1
                items.append((key, n, img, gx - sp.ax, gy - sp.ay + bob))
                gc = (col[0] // 3, col[1] // 3, col[2] // 3)
                n += 1
                items.append((key, n, None, lambda gx=gx, gy=gy + bob, c=gc: self.add_glow(gx, gy - sc(12), sc(24), c), 0))

        for b in w.bosses:
            gx, gy = ground(b.x, b.y)
            if not on_screen(gx, gy):
                continue
            rx = int(b.r * 50 * S)
            surf.blit(shadow(rx), (gx - rx, gy - rx // 2))
            sp = spr.get("boss_" + b.kind)
            if sp:
                img = sp.get("walk", b.dir, b.frame)
                n += 1
                items.append((b.x + b.y, n, img, gx - sp.ax, gy - sp.ay))
                if b.flash > 0 or (b.telegraph > 0 and int(self.time * 16) % 2):
                    n += 1
                    items.append((b.x + b.y, n, sp.flash(img), gx - sp.ax, gy - sp.ay))
            if b.eels:
                n += 1
                items.append((b.x + b.y + 0.4, n, None, lambda b=b, ox=ox, oy=oy: self.draw_eels(b, ox, oy), 0))
        for e in w.enemies:
            gx, gy = ground(e.x, e.y)
            if not on_screen(gx, gy):
                continue
            bdis = (e.bdef or {}).get("disguise") if e.state == "dormant" else None
            if bdis:      # chest mimic sits there looking like loot
                dsp = spr[bdis]
                n += 1
                items.append((e.x + e.y, n, dsp.get("idle", 0, int(e.phase * 10)), gx - dsp.ax, gy - dsp.ay))
                continue
            if (e.state == "dormant" and e.kind != "mimic") or getattr(e, "submerged", False):
                continue
            if e.eels:
                n += 1
                items.append((e.x + e.y + 0.3, n, None, lambda e=e, ox=ox, oy=oy: self.draw_eels(e, ox, oy), 0))
            rx = int(e.r * 44 * S) if e.kind != "drone" else sc(12)
            surf.blit(shadow(rx), (gx - rx, gy - rx // 2))
            sp = spr[e.kind]
            img = sp.get("dormant" if e.state == "dormant" else "walk", e.dir, e.frame)
            if e.weapon is not None and e.alive:      # Pink Melter holds its actual gun model
                gsp = spr.get("gun_" + WP.sprite_arch(e.weapon.arch))
                if gsp:
                    a_ = e.dir * math.tau / 8
                    ga, gb = to_screen(e.x + math.cos(a_) * 0.35, e.y + math.sin(a_) * 0.35, 0.7)
                    gimg = gsp.get("idle", 0, e.dir)
                    n += 1
                    items.append((e.x + e.y + 0.02, n, gimg, ga + ox - gsp.ax, gb + oy - gsp.ay))
            if getattr(e, "frozen", 0) > 0:
                img = self.tinted(img, (150, 210, 255))
            elif getattr(e, "chill", 0) > 0.35:
                img = self.tinted(img, (190, 220, 255))
            n += 1
            items.append((e.x + e.y, n, img, gx - sp.ax, gy - sp.ay))
            if e.flash > 0:
                n += 1
                items.append((e.x + e.y, n, sp.flash(img), gx - sp.ax, gy - sp.ay))

        for pl in w.players:
            plx, ply = ground(pl.x, pl.y)
            plkey = pl.x + pl.y
            if not pl.alive:      # downed: bones to stand on, with a revive ring
                if len(w.players) > 1:
                    gsp = spr["gib_skull" if pl.char == "skelebot" else ("gib_gear" if pl.char == "canbot" else "gib_meat")]
                    n += 1
                    items.append((plkey, n, gsp.get("spin", 0, 0), plx - gsp.ax, ply - gsp.ay))
                    n += 1
                    items.append((plkey + 0.01, n, None, lambda pl=pl, x_=plx, y_=ply: self.draw_revive(pl, x_, y_), 0))
                continue
            surf.blit(shadow(sc(14)), (plx - sc(14), ply - sc(7)))
            blink = pl.invuln > 0 and int(self.time * 24) % 2 == 0
            if not blink:
                C = CH.CHARS[pl.char]
                legs, torso = spr[C["legs"]], spr[C["torso"] + WP.sprite_arch(pl.weapon.arch)]
                stride = C["stride"]
                if pl.moving:
                    limg = legs.get("walk", pl.legs_dir, pl.walk / stride * 8)
                    bob = -abs(math.sin(pl.walk / stride * math.tau)) * sc(2)
                else:
                    limg = legs.get("idle", pl.legs_dir, 0)
                    bob = 0
                timg = torso.get("idle", dir_index(pl.aim[0], pl.aim[1], 16))
                if pl.idx % 4:
                    limg, timg = self.player_colors(limg, pl.idx), self.player_colors(timg, pl.idx)
                if "chill" in pl.status:
                    timg = self.tinted(timg, (160, 210, 255))
                    limg = self.tinted(limg, (160, 210, 255))
                elif "confuse" in pl.status:
                    timg = self.tinted(timg, (255, 150, 220))
                n += 1
                items.append((plkey, n, limg, plx - legs.ax, ply - legs.ay))
                n += 1
                items.append((plkey, n, timg, plx - torso.ax, ply - torso.ay + bob))
                if pl.flash > 0:
                    n += 1
                    items.append((plkey, n, torso.flash(timg), plx - torso.ax, ply - torso.ay + bob))
                aura = {WP.SACRED: (140, 140, 130), WP.ELDRITCH: (30, 120, 30), WP.DEMONIC: (140, 28, 14)}.get(pl.weapon.rarity)
                if aura:
                    pk_ = 0.75 + 0.25 * math.sin(self.time * 3)
                    n += 1
                    items.append((plkey - 0.05, n, None, lambda x_=plx, y_=ply, c=aura, k=pk_:
                                  self.add_glow(x_, y_ - sc(40), int(sc(74) * k), c), 0))
                    if rnd.random() < 0.45:
                        w.add(Particle("fire" if pl.weapon.rarity == WP.DEMONIC else "glow", pl.x + rnd.uniform(-0.3, 0.3),
                                       pl.y + rnd.uniform(-0.3, 0.3), rnd.uniform(0.3, 1.3), 0, 0, rnd.uniform(0.6, 1.4), 0.6,
                                       {WP.ELDRITCH: (90, 255, 90), WP.SACRED: (255, 255, 235)}.get(pl.weapon.rarity, (255, 70, 30)),
                                       8 if pl.weapon.rarity == WP.DEMONIC else 2))
                if len(w.players) > 1:   # who's who
                    n += 1
                    items.append((plkey + 0.02, n, None, lambda pl=pl, x_=plx, y_=ply: self.draw_tag(pl, x_, y_), 0))
            if pl.muzzle > 0:
                ax, ay = pl.aim
                mf, mz = WP.MUZZLE[pl.weapon.arch]
                sd = WP.SHOULDER.get(pl.weapon.arch, 0.0)
                mx, my = ground(pl.x + ax * mf + ay * sd, pl.y + ay * mf - ax * sd, mz)
                mc = pl.muzzle_color
                n += 1
                items.append((plkey + 0.01, n, None, lambda mx=mx, my=my, c=mc: self.add_glow(mx, my, sc(24), c), 0))

        n = self.support_items(w, items, n, ground, on_screen)

        # flying gibs
        for g in w.gibs:
            if g.rest:
                continue
            gx, gy = ground(g.x, g.y)
            if not on_screen(gx, gy):
                continue
            surf.blit(shadow(sc(6)), (gx - sc(6), gy - sc(3)))
            sp = spr[g.sprite]
            hx, hy = ground(g.x, g.y, g.z)
            n += 1
            items.append((g.x + g.y, n, sp.get("spin", 0, g.frame), hx - sp.ax, hy - sp.ay))

        for b in w.projs:
            hx, hy = ground(b.x, b.y, b.z)
            if not on_screen(hx, hy):
                continue
            if b.kind in ("grenade", "acid"):
                gx, gy = ground(b.x, b.y)
                surf.blit(shadow(sc(6)), (gx - sc(6), gy - sc(3)))
            n += 1
            items.append((b.x + b.y, n, None, lambda b=b, ox=ox, oy=oy: self.draw_proj(b, ox, oy), 0))

        for q in w.particles:
            if q.kind == "ring":
                gx, gy = ground(q.x, q.y)
                if on_screen(gx, gy):
                    n += 1
                    items.append((q.x + q.y - 0.8, n, None, lambda gx=gx, gy=gy, q=q: self.draw_ring(gx, gy, q), 0))
                continue
            qx, qy = ground(q.x, q.y, q.z)
            if not on_screen(qx, qy):
                continue
            n += 1
            key = q.x + q.y + (0.6 if q.kind in ("smoke", "fire") else 0)
            items.append((key, n, None, lambda qx=qx, qy=qy, q=q, ox=ox, oy=oy: self.draw_particle(qx, qy, q, ox, oy), 0))

        items.sort(key=lambda t: (t[0], t[1]))
        for key, _, img, x, y in items:
            if img is None:
                x()
            else:
                surf.blit(img, (round(x), round(y)))
        for bm in w.beams:
            self.draw_beam(bm, ox, oy)
        for a_ in w.arcs:
            self.draw_arc(a_, ox, oy)
        for x_, y_, z_, txt, col, life in w.popups:
            a, b = to_screen(x_, y_, z_)
            f_ = self.small if txt in ("WEAK", "RESIST") else self.font
            img = f_.render(txt, True, col)
            img.set_alpha(int(255 * min(1.0, life / 0.4)))
            sh = f_.render(txt, True, (0, 0, 0))
            sh.set_alpha(img.get_alpha())
            surf.blit(sh, (a + ox - img.get_width() / 2 + 2, b + oy + 2))
            surf.blit(img, (a + ox - img.get_width() / 2, b + oy))

        if self.ambient:
            last = getattr(self, "_last_cam", tuple(self.cam))
            self.ambient.update_draw(surf, 1 / 60, self.cam[0] - last[0], self.cam[1] - last[1], self.time, self.add_glow)
            self._last_cam = tuple(self.cam)
        surf.blit(self.vig_biome, (0, 0), special_flags=pygame.BLEND_MULT)
        if w.static > 0.02:
            st = self.static_frames[int(self.time * 30) % len(self.static_frames)]
            st.set_alpha(int(min(1.0, w.static) * 32))
            surf.blit(st, (0, 0))
        if w.hurt_flash > 0:
            self.overlay(surf, int(w.hurt_flash * 300), (160, 0, 0))
        if getattr(w, "flash_white", 0) > 0:
            self.overlay(surf, int(min(1.0, w.flash_white * 2) * 230), (235, 255, 210))

    def add_glow(self, x, y, r, col):
        g = glow(r, col)
        self.screen.blit(g, (x - r, y - r), special_flags=pygame.BLEND_ADD)

    def tinted(self, img, col):
        key = (id(img), col)
        t = self._tint.get(key)
        if t is None:
            t = img.copy()
            t.fill((80, 80, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
            t.fill((*col, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._tint[key] = t
        return t

    def draw_pillar(self, gx, gy, col, rarity):
        key = (col, rarity)
        img = self._pillar.get(key)
        if img is None:
            h = sc(60 + 30 * min(rarity, 6))
            wdt = sc(14)
            img = pygame.Surface((wdt, h))
            for yy in range(h):
                k = (yy / h) ** 1.8 * min(1.0, 0.35 + 0.12 * rarity)
                for xx in range(wdt):
                    e = 1 - abs(xx - wdt / 2) / (wdt / 2)
                    img.set_at((xx, yy), (int(col[0] * k * e), int(col[1] * k * e), int(col[2] * k * e)))
            self._pillar[key] = img
        pulse = 0.85 + 0.15 * math.sin(self.time * 4)
        self.screen.blit(img, (gx - img.get_width() / 2, gy - img.get_height() + sc(4)), special_flags=pygame.BLEND_ADD)
        self.add_glow(gx, gy, int(sc(22) * pulse), (col[0] // 4, col[1] // 4, col[2] // 4))

    def draw_jet_pool(self, gx, gy, hz):
        col = {"napalm": (255, 110, 30), "cryo": (160, 220, 255), "rad": (170, 255, 60)}[hz[7]]
        k = min(1.0, hz[3] / hz[6] * 2)
        rx = max(2, int(hz[2] * HW * 1.3))
        a = int(14 * k)
        key = ("jetpool", hz[7], rx, a)
        img = self._pool.get(key)
        if img is None:
            img = pygame.Surface((rx * 2, rx), pygame.SRCALPHA)
            pygame.draw.ellipse(img, (*[v // 2 for v in col], 12 * a), img.get_rect())
            pygame.draw.ellipse(img, (*col, 10 * a), img.get_rect().inflate(-rx * 0.6, -rx * 0.3))
            self._pool[key] = img
        self.screen.blit(img, (gx - rx, gy - rx // 2))
        self.add_glow(gx, gy, int(rx * 0.9), tuple(int(v * 0.25 * k) for v in col))

    def draw_pool(self, gx, gy, hz):
        a = int(min(1.0, hz[3]) * 8)
        rx = int(hz[2] * HW)
        key = (rx, a)
        img = self._pool.get(key)
        if img is None:
            img = pygame.Surface((rx * 2, rx), pygame.SRCALPHA)
            pygame.draw.ellipse(img, (60, 190, 30, 18 * a), img.get_rect())
            pygame.draw.ellipse(img, (140, 255, 80, 14 * a), img.get_rect().inflate(-rx * 0.5, -rx * 0.25))
            self._pool[key] = img
        self.screen.blit(img, (gx - rx, gy - rx // 2))
        self.add_glow(gx, gy, int(rx * 0.8), (20, 60, 10))

    def flame_puff(self, shape, step, size, ramp=None):
        ramp = ramp or FLAME_RAMP
        size = max(4, (size // 4) * 4)
        key = (shape, step, size, id(ramp))
        img = self._flame.get(key)
        if img is None:
            img = pygame.transform.smoothscale(self.puffs[shape], (size, size))
            c = ramp[step]
            img.fill(c, special_flags=pygame.BLEND_MULT)
            self._flame[key] = img
        return img

    def draw_rad(self, gx, gy, hz):
        f = min(1.0, hz[3] / 2.0)
        pulse = 0.8 + 0.2 * math.sin(self.time * 4 + hz[0])
        rx = int(hz[2] * HW)
        key = ("rad", rx, int(f * 6))
        img = self._pool.get(key)
        if img is None:
            img = pygame.Surface((rx * 2, rx), pygame.SRCALPHA)
            a = int(14 * int(f * 6))
            pygame.draw.ellipse(img, (90, 200, 40, a), img.get_rect())
            pygame.draw.ellipse(img, (170, 255, 90, a // 2 + 10), img.get_rect(), max(2, sc(3)))
            self._pool[key] = img
        self.screen.blit(img, (gx - rx, gy - rx // 2))
        self.add_glow(gx, gy, int(rx * 0.9), (int(30 * f * pulse), int(70 * f * pulse), int(10 * f * pulse)))

    def draw_gas(self, gx, gy, hz):
        f = min(1.0, hz[3] / hz[6] * 1.5)
        r = max(3, int(hz[2] * HW * 1.1))
        for k in range(3):
            a = self.time * 0.6 + k * 2.1 + hz[0]
            ox_, oy_ = math.cos(a) * r * 0.3, math.sin(a) * r * 0.15
            img = smoke_surf(r, int(120 * f), (150, 185, 40))
            self.screen.blit(img, (gx + ox_ - r, gy + oy_ - r * 0.8))
        self.add_glow(gx, gy, r, (int(25 * f), int(35 * f), 0))

    # ------------------------------------------------------------ environmental traps
    def draw_trap_floor(self, surf, w, ground, on_screen):
        """Flat trap parts: liquid pools, saw tracks, vent grates, tentacle holes, laser beams."""
        t = self.time
        for tr in w.traps:
            m = tr.mech
            if m == "pool":
                col, hi = tr.col, tr.hi
                dark = tuple(c // 2 for c in col)
                for (cx, cy) in tr.cells:
                    p0 = ground(cx, cy)
                    if not on_screen(*p0):
                        continue
                    pts = [p0, ground(cx + 1, cy), ground(cx + 1, cy + 1), ground(cx, cy + 1)]
                    pygame.draw.polygon(surf, col, pts)
                    h = ((cx * 7919) ^ (cy * 104729)) % 97 / 97.0
                    k = 0.3 + 0.25 * math.sin(t * (1.5 + h) + h * 9)
                    mid = tuple(int(a + (b - a) * k) for a, b in zip(col, hi))
                    inset = [ground(cx + 0.5 + (px - 0.5) * 0.7, cy + 0.5 + (py - 0.5) * 0.7) for px, py in ((0, 0), (1, 0), (1, 1), (0, 1))]
                    pygame.draw.polygon(surf, mid, inset)
                    for e in range(4):        # pool rim against dry floor
                        nx, ny = ((cx, cy - 1), (cx + 1, cy), (cx, cy + 1), (cx - 1, cy))[e]
                        if (nx, ny) not in tr.cells:
                            pygame.draw.line(surf, dark, pts[e], pts[(e + 1) % 4], max(2, sc(3)))
                    ph = (t * 0.7 + h * 5) % 1.0
                    if ph < 0.35:
                        bx, by = ground(cx + 0.2 + h * 0.6, cy + 0.7 - h * 0.4)
                        pygame.draw.circle(surf, hi, (bx, by), max(1, int(sc(5) * ph / 0.35)), max(1, sc(1)))
                    if tr.style == "lava" and (cx + cy) % 2 == 0:
                        gx, gy = ground(cx + 0.5, cy + 0.5)
                        self.add_glow(gx, gy, sc(40), (70, 25, 4))
            elif m == "saw":
                a_, b_ = ground(*tr.a), ground(*tr.b)
                if on_screen(*a_) or on_screen(*b_):
                    pygame.draw.line(surf, (12, 10, 12), a_, b_, max(3, sc(8)))
                    pygame.draw.line(surf, (70, 64, 58), a_, b_, max(1, sc(2)))
            elif m == "vent":
                gx, gy = ground(tr.x, tr.y)
                if on_screen(gx, gy):
                    sp = self.spr[tr.sprite]
                    img = sp.get("idle", 0)
                    if tr.style == "geyser":
                        img = self.tinted(img, (160, 150, 100))
                    surf.blit(img, (gx - sp.ax, gy - sp.ay))
                    st = tr.state()
                    if tr.style == "fire" and st != "idle":
                        self.add_glow(gx, gy, sc(70 if st == "blast" else 30), (140, 55, 10) if st == "blast" else (60, 22, 4))
            elif m == "tentacle":
                gx, gy = ground(tr.x, tr.y)
                if on_screen(gx, gy):
                    sp = self.spr["trap_hole"]
                    img = sp.get("idle", 0)
                    if tr.hole_tint:
                        img = self.tinted(img, tr.hole_tint)
                    surf.blit(img, (gx - sp.ax, gy - sp.ay))
                    if tr.state == "windup" and tr.target is not None and int(t * 12) % 2:   # telegraph the slam lane
                        ex, ey = tr.reach()
                        pygame.draw.line(surf, (200, 40, 40), (gx, gy), ground(ex, ey), max(1, sc(3)))
            elif m == "laser":
                st = tr.state()
                (ax, ay), (bx, by) = tr.a, tr.b
                a_, b_ = ground(ax, ay, 0.5), ground(bx, by, 0.5)
                if not (on_screen(*a_) or on_screen(*b_)):
                    continue
                for (px, py) in ((ax, ay), (bx, by)):
                    pygame.draw.line(surf, (30, 30, 36), ground(px, py, 0.15), ground(px, py, 0.75), max(3, sc(9)))
                    pygame.draw.circle(surf, (255, 60, 50) if st != "off" else (90, 20, 20), ground(px, py, 0.5), max(2, sc(4)))
                if st == "on":
                    for wd, c in ((sc(9), (90, 10, 10)), (sc(5), (220, 30, 30)), (sc(2), (255, 200, 190))):
                        pygame.draw.line(surf, c, a_, b_, max(1, wd))
                    for k in range(3):
                        u = (k + 0.5) / 3
                        self.add_glow(a_[0] + (b_[0] - a_[0]) * u, a_[1] + (b_[1] - a_[1]) * u, sc(30), (70, 8, 8))
                elif st == "warn" and int(t * 16) % 2:
                    pygame.draw.line(surf, (160, 30, 30), a_, b_, 1)

    def trap_items(self, w, items, n, ground, on_screen):
        """Upright trap parts go into the depth-sorted draw list."""
        import traps as TR
        spr = self.spr
        t = self.time
        for tr in w.traps:
            m = tr.mech
            if m in ("pool", "vent", "laser", "wind"):
                continue
            if m == "strike":
                n += 1
                items.append((1e9, n, None, lambda tr=tr: self.draw_strikes(tr, ground), 0))
                continue
            gx, gy = ground(tr.x, tr.y)
            if not on_screen(gx, gy):
                continue
            key = tr.x + tr.y
            img = None
            sp = spr[tr.sprite] if tr.sprite and m != "tentacle" else None
            if m == "spikes":
                img = sp.get("rise", 0, tr.frame(t))
            elif m == "saw":
                img = sp.get("spin", tr.axis, t * 24)
            elif m in ("reactor", "tesla", "thorns"):
                img = sp.get("idle", 0)
                if m == "reactor" and tr.fuse >= 0 and int(t * 10) % 2:
                    img = self.tinted(img, (255, 120, 100))
                if m == "thorns" and int(tr.x * 13 + tr.y * 7) % 2:
                    img = self.flipped(img)
            elif m == "turret":
                img = sp.get("rise", dir_index(tr.aim[0], tr.aim[1], 16), tr.frame())
            elif m == "maw":
                img = sp.get("bite", 0, tr.frame())
            elif m == "hands":
                img = sp.get("grab", 0, tr.frame())
            elif m == "pendulum":
                img = sp.get("swing", tr.axis, tr.frame())
            if img is not None:
                tint = TR.TINT.get(tr.style)
                if tint and m in ("spikes", "saw", "turret", "pendulum"):
                    img = self.tinted(img, tint)
                n += 1
                items.append((key, n, img, gx - sp.ax, gy - sp.ay))
                if tr.flash > 0:
                    n += 1
                    items.append((key, n, sp.flash(img), gx - sp.ax, gy - sp.ay))
            if m == "tentacle":
                n += 1
                items.append((key + 0.05, n, None, lambda tr=tr: self.draw_tentacle(tr, ground), 0))
            elif m == "tesla":
                n += 1
                items.append((key + 0.05, n, None, lambda tr=tr, ch=tr.charge(): self.draw_tesla(tr, ch, ground), 0))
            elif m == "reactor":
                col = (60, 110, 10) if tr.style == "chem" else (20, 110, 40)
                if tr.fuse >= 0:
                    col = (160, 40, 20) if int(t * 10) % 2 else (90, 120, 20)
                n += 1
                items.append((key + 0.05, n, None, lambda g=ground(tr.x, tr.y, 0.5), c=col: self.add_glow(g[0], g[1], sc(46), c), 0))
        return n

    def flipped(self, img):
        key = ("flip", id(img))
        out = self._tint.get(key)
        if out is None:
            out = self._tint[key] = pygame.transform.flip(img, True, False)
        return out

    def draw_tentacle(self, tr, ground):
        pts = tr.points(self.time)
        if not pts:
            return
        s = self.screen
        n = len(pts)
        flash = tr.flash > 0
        for i, (x, y, z) in enumerate(pts):
            u = i / (n - 1)
            r = max(2, int(sc(13) * (1 - u * 0.75) * (0.6 + 0.4 * tr.k)))
            c = (255, 255, 255) if flash else tuple(int(a + (b - a) * u) for a, b in zip(tr.col, tr.tip))
            gx, gy = ground(x, y, z)
            pygame.draw.circle(s, (20, 10, 12), (gx, gy), r + max(1, sc(2)))
            pygame.draw.circle(s, c, (gx, gy), r)
            pygame.draw.circle(s, tuple(min(255, int(v * 1.25)) for v in c), (gx - r // 3, gy - r // 3), max(1, r // 3))
            if i % 2 and r > sc(4):
                pygame.draw.circle(s, (240, 200, 190), (gx + r // 2, gy + r // 3), max(1, r // 4))

    def draw_tesla(self, tr, ch, ground):
        gx, gy = ground(tr.x, tr.y, 1.05)
        if ch > 0:
            self.add_glow(gx, gy, int(sc(20) + sc(50) * ch), (int(60 * ch), int(90 * ch), int(140 * ch)))
        for (x2, y2, life) in tr.arcs:
            ex, ey = ground(x2, y2, 0.6)
            for wd, c in ((sc(5), (60, 90, 200)), (sc(2), (220, 235, 255))):
                pts = [(gx, gy)]
                for k in range(1, 8):
                    u = k / 8
                    pts.append((gx + (ex - gx) * u + rnd.uniform(-1, 1) * sc(14), gy + (ey - gy) * u + rnd.uniform(-1, 1) * sc(14)))
                pts.append((ex, ey))
                pygame.draw.lines(self.screen, c, False, pts, max(1, wd))
            self.add_glow(ex, ey, sc(30), (40, 60, 120))

    def draw_strikes(self, tr, ground):
        s = self.screen
        for (x, y, h) in tr.falling():
            gx, gy = ground(x, y, h * 9)
            if tr.style == "icicle":
                pts = [(gx, gy + sc(26)), (gx - sc(7), gy - sc(14)), (gx, gy - sc(22)), (gx + sc(7), gy - sc(14))]
                pygame.draw.polygon(s, (205, 235, 255), pts)
                pygame.draw.polygon(s, (90, 130, 170), pts, max(1, sc(2)))
            elif tr.style == "meteor":
                self.add_glow(gx, gy, sc(40), (160, 70, 15))
                pygame.draw.circle(s, (255, 190, 80), (gx, gy), sc(9))
                pygame.draw.line(s, (255, 120, 40), (gx, gy), (gx + sc(30), gy - sc(60)), max(2, sc(6)))
        for (x, y, life) in tr.bolts:
            gx, gy = ground(x, y)
            pts = [(gx + rnd.uniform(-1, 1) * sc(30), gy - sc(900))]
            for k in range(1, 10):
                pts.append((gx + rnd.uniform(-1, 1) * sc(26) * (1 - k / 10), gy - sc(900) * (1 - k / 10)))
            pts.append((gx, gy))
            for wd, c in ((sc(10), (80, 70, 160)), (sc(4), (230, 225, 255))):
                pygame.draw.lines(s, c, False, pts, max(1, wd))
            self.add_glow(gx, gy, sc(90), (90, 80, 140))

    PLAYER_COLORS = ((255, 90, 70), (70, 230, 230), (255, 210, 70), (180, 120, 255))
    PALETTE = {1: (0.15, 0.85, 0.95), 2: (0.95, 0.8, 0.15), 3: (0.6, 0.35, 1.0)}    # red armour -> teal / gold / violet

    def player_colors(self, img, idx):
        """Players 2-4: the red armour (and red glows) palette-swapped to their colour."""
        key = (id(img), idx)
        kr, kg, kb = self.PALETTE[idx % 4]
        out = self._p2.get(key)
        if out is None:
            import numpy as np
            out = img.copy()
            rgb = pygame.surfarray.pixels3d(out)
            r = rgb[:, :, 0].astype(np.int32)
            g = rgb[:, :, 1].astype(np.int32)
            b = rgb[:, :, 2].astype(np.int32)
            m = (r > g * 1.5) & (r > b * 1.5) & (r > 50)
            rgb[:, :, 0][m] = np.minimum(255, r[m] * kr).astype(np.uint8)
            rgb[:, :, 1][m] = np.minimum(255, r[m] * kg).astype(np.uint8)
            rgb[:, :, 2][m] = np.minimum(255, r[m] * kb).astype(np.uint8)
            del rgb
            self._p2[key] = out
        return out

    def draw_tag(self, pl, x, y):
        c = self.PLAYER_COLORS[pl.idx % 4]
        tip = (x, y - sc(84))
        pygame.draw.polygon(self.screen, c, [(tip[0] - sc(7), tip[1] - sc(10)), (tip[0] + sc(7), tip[1] - sc(10)), tip])
        lbl = self.small.render(self.pname(pl), True, c)
        self.screen.blit(lbl, (x - lbl.get_width() / 2, tip[1] - sc(28)))

    def draw_revive(self, pl, x, y):
        c = self.PLAYER_COLORS[pl.idx % 4]
        r = sc(26)
        rect = pygame.Rect(0, 0, r * 2, r)
        rect.center = (x, y)
        pygame.draw.ellipse(self.screen, (c[0] // 3, c[1] // 3, c[2] // 3), rect, max(1, sc(2)))
        if pl.revive_t > 0:
            pygame.draw.arc(self.screen, c, rect.inflate(sc(6), sc(4)), 0, math.tau * min(1.0, pl.revive_t / 2.5), max(2, sc(4)))
        if int(self.time * 3) % 2:
            lbl = self.small.render("%s DOWN" % self.pname(pl), True, c)
            self.screen.blit(lbl, (x - lbl.get_width() / 2, y - sc(60)))

    def draw_eels(self, e, ox, oy):
        """Snake/eel arms: chains of glowing segments with a darker core, thinning to the tip."""
        c = e.eel_color
        dark = (c[0] // 4, c[1] // 4, c[2] // 4)
        for k in range(e.eels):
            pts, s_ = eel_points(e, k, self.world.time)
            prev = None
            n = len(pts)
            for i, (x, y, z) in enumerate(pts):
                a, b = to_screen(x, y, z)
                sx_, sy_ = a + ox, b + oy
                rad = max(2, int(sc(9) * (1 - i / n) + sc(3)))
                if prev:
                    pygame.draw.line(self.screen, dark, prev, (sx_, sy_), rad * 2)
                prev = (sx_, sy_)
            for i, (x, y, z) in enumerate(pts):
                a, b = to_screen(x, y, z)
                rad = max(2, int(sc(9) * (1 - i / n) + sc(3)))
                self.add_glow(a + ox, b + oy, rad + sc(4), (c[0] // 3, c[1] // 3, c[2] // 3))
                pygame.draw.circle(self.screen, c if i % 2 else dark, (a + ox, b + oy), max(1, rad // 2))
            a, b = to_screen(*pts[-1])
            self.add_glow(a + ox, b + oy, sc(14) + int(s_ * sc(10)), (c[0] // 2, c[1] // 2, c[2] // 2))

    def draw_beam(self, bm, ox, oy):
        x1, y1, x2, y2, z, life, mx, col, wf = bm
        k = max(0.0, life / mx)
        a, b = to_screen(x1, y1, z)
        c, d = to_screen(x2, y2, z)
        p1, p2 = (a + ox, b + oy), (c + ox, d + oy)
        s = self.screen
        pygame.draw.line(s, (int(col[0] * k * 0.6), int(col[1] * k * 0.6), int(col[2] * k * 0.6)), p1, p2, max(1, int(sc(8) * wf * k)))
        pygame.draw.line(s, (255, 255, 255), p1, p2, max(1, int(sc(2.5) * wf * k)))
        self.add_glow(p2[0], p2[1], sc(16), (col[0] // 3, col[1] // 3, col[2] // 3))
        self.add_glow(p1[0], p1[1], sc(12), (col[0] // 3, col[1] // 3, col[2] // 3))

    def draw_proj(self, b, ox, oy):
        s = self.screen
        c = b.color
        k = b.kind
        a, bb = to_screen(b.x, b.y, b.z)
        hx, hy = a + ox, bb + oy
        if k in ("bullet", "pellet", "slug", "bolt"):
            if b.hostile:
                self.add_glow(hx, hy, sc(16), (c[0] // 2, c[1] // 2, c[2] // 2))
                pygame.draw.circle(s, (255, 200, 160), (hx, hy), sc(3.5))
                return
            tl = {"bullet": 0.025, "pellet": 0.02, "slug": 0.045, "bolt": 0.035}[k]
            if b.effect == "dumdum":          # a fat, glowing lump of lead with a short smoky tail
                ta, tb = to_screen(b.x - b.vx * 0.035, b.y - b.vy * 0.035, b.z)
                self.add_glow(hx, hy, sc(20), (c[0] // 2, c[1] // 3, c[2] // 4))
                pygame.draw.line(s, (120, 90, 60), (ta + ox, tb + oy), (hx, hy), sc(6))
                pygame.draw.circle(s, c, (hx, hy), sc(5))
                pygame.draw.circle(s, (255, 250, 230), (hx, hy), sc(2.5))
                return
            if b.effect == "sabot":           # a long, thin, white-hot needle
                ta, tb = to_screen(b.x - b.vx * 0.03, b.y - b.vy * 0.03, b.z)
                self.add_glow(hx, hy, sc(10), (70, 80, 95))
                pygame.draw.line(s, (150, 175, 210), (ta + ox, tb + oy), (hx, hy), sc(3))
                pygame.draw.line(s, (255, 255, 255), (ta + ox, tb + oy), (hx, hy), max(1, sc(1.2)))
                return
            ta, tb = to_screen(b.x - b.vx * tl, b.y - b.vy * tl, b.z)
            tx, ty = ta + ox, tb + oy
            wdt = {"slug": sc(4.5), "pellet": sc(2.5), "bolt": sc(3.5)}.get(k, sc(3))
            self.add_glow(hx, hy, sc(12 if k != "pellet" else 8), (c[0] // 3, c[1] // 3, c[2] // 3))
            pygame.draw.line(s, c, (tx, ty), (hx, hy), wdt)
            pygame.draw.line(s, (255, 255, 255), ((tx + hx) / 2, (ty + hy) / 2), (hx, hy), max(1, wdt // 3))
        elif k == "rail":
            ta, tb = to_screen(b.x - b.vx * 0.03, b.y - b.vy * 0.03, b.z)
            tx, ty = ta + ox, tb + oy
            self.add_glow(hx, hy, sc(34), (c[0] // 2, c[1] // 2, c[2] // 2))
            pygame.draw.line(s, c, (tx, ty), (hx, hy), sc(7))
            pygame.draw.line(s, (255, 255, 255), (tx, ty), (hx, hy), sc(3))
        elif k == "plasma":
            self.add_glow(hx, hy, sc(28), (c[0] // 2, c[1] // 2, c[2] // 2))
            pygame.draw.circle(s, c, (hx, hy), sc(6))
            pygame.draw.circle(s, (255, 255, 255), (hx, hy), sc(3))
        elif k == "flame":
            t = min(0.999, b.age / 0.65)
            step = int(t * (len(FLAME_RAMP) - 1))
            size = max(4, int(b.r * HW * 2.4))
            shape = id(b) % len(self.puffs)
            img = self.flame_puff(shape, step, size)
            s.blit(img, (hx - size / 2, hy - size / 2), special_flags=pygame.BLEND_ADD)
            # trailing puff fills the gap to the previous flame so the stream reads as one roaring jet
            ta, tb = to_screen(b.x - b.vx * 0.022, b.y - b.vy * 0.022, b.z)
            img2 = self.flame_puff((shape + 2) % len(self.puffs), min(len(FLAME_RAMP) - 1, step + 1), max(4, int(size * 0.85)))
            s.blit(img2, (ta + ox - size * 0.42, tb + oy - size * 0.42), special_flags=pygame.BLEND_ADD)
            if t < 0.5:
                core = self.flame_puff((shape + 1) % len(self.puffs), 0, max(3, size // 2))
                s.blit(core, (hx - size / 4, hy - size / 4), special_flags=pygame.BLEND_ADD)
            ga, gb = to_screen(b.x, b.y, 0)
            gl = int(70 * (1 - t))
            self.add_glow(ga + ox, gb + oy, max(3, size // 2), (gl, gl // 3, 0))
        elif k in ("chem", "cryo"):
            ramp = CHEM_RAMP if k == "chem" else CRYO_RAMP
            t = min(0.999, b.age / 0.65)
            step = int(t * (len(ramp) - 1))
            size = max(4, int(b.r * HW * 2.2))
            shape = id(b) % len(self.puffs)
            s.blit(self.flame_puff(shape, step, size, ramp), (hx - size / 2, hy - size / 2), special_flags=pygame.BLEND_ADD)
            ta, tb = to_screen(b.x - b.vx * 0.022, b.y - b.vy * 0.022, b.z)
            s.blit(self.flame_puff((shape + 2) % len(self.puffs), min(7, step + 1), int(size * 0.85), ramp),
                   (ta + ox - size * 0.42, tb + oy - size * 0.42), special_flags=pygame.BLEND_ADD)
        elif k == "nuke":
            ta, tb = to_screen(b.x - b.vx * 0.04, b.y - b.vy * 0.04, b.z)
            tx, ty = ta + ox, tb + oy
            pygame.draw.line(s, (60, 70, 55), (tx, ty), (hx, hy), sc(7))
            pygame.draw.line(s, (230, 200, 40), (tx, ty), ((tx + hx) / 2, (ty + hy) / 2), sc(7))
            pygame.draw.circle(s, (170, 255, 70), (hx, hy), sc(5))
            self.add_glow(hx, hy, sc(22), (60, 110, 20))
            self.add_glow(tx, ty, sc(18), (110, 80, 20))
        elif k == "chain":
            o = b.owner
            if o is not None and o.alive:
                oa, ob = to_screen(o.x, o.y, o.hz)
                pygame.draw.line(s, (90, 85, 80), (oa + ox, ob + oy), (hx, hy), max(2, sc(3)))
                pygame.draw.line(s, (170, 165, 155), (oa + ox, ob + oy), (hx, hy), max(1, sc(1)))
            pygame.draw.circle(s, (200, 195, 185), (hx, hy), sc(5))
            pygame.draw.circle(s, (60, 55, 50), (hx, hy), sc(5), max(1, sc(2)))
        elif k in ("saw", "cleaver"):
            rx, ry = sc(11), sc(5.5)
            rect = pygame.Rect(0, 0, rx * 2, ry * 2)
            rect.center = (hx, hy)
            pygame.draw.ellipse(s, (20, 20, 24), rect.inflate(sc(3), sc(2)))
            pygame.draw.ellipse(s, (190, 195, 205) if k == "saw" else (170, 60, 55), rect)
            for i in range(10):
                a = b.spin + i * math.tau / 10
                x1, y1 = hx + math.cos(a) * rx, hy + math.sin(a) * ry
                x2, y2 = hx + math.cos(a + 0.25) * (rx + sc(4)), hy + math.sin(a + 0.25) * (ry + sc(2))
                pygame.draw.line(s, (235, 235, 245), (x1, y1), (x2, y2), max(1, sc(2)))
            pygame.draw.ellipse(s, (60, 62, 70), rect.inflate(-rx, -ry))
            self.add_glow(hx, hy, sc(10), (40, 40, 45))
        elif k == "fireball":
            img = self.flame_puff(int(b.age * 20) % len(self.puffs), 1, sc(34))
            s.blit(img, (hx - sc(17), hy - sc(17)), special_flags=pygame.BLEND_ADD)
            self.add_glow(hx, hy, sc(30), (140, 50, 8))
            pygame.draw.circle(s, (255, 240, 200), (hx, hy), sc(4))
        elif k == "orb":
            # bullet-hell readability: dark rim, saturated body, hot white core
            rad = max(3, int(b.r * HW * 0.62))
            self.add_glow(hx, hy, rad * 2 + sc(4), (c[0] // 2, c[1] // 2, c[2] // 2))
            pygame.draw.circle(s, (15, 10, 12), (hx, hy), rad + max(1, sc(1.5)))
            pygame.draw.circle(s, c, (hx, hy), rad)
            pygame.draw.circle(s, (255, 255, 255), (hx, hy), max(1, rad // 2))
        elif k == "mortar":
            pygame.draw.circle(s, (60, 55, 50), (hx, hy), sc(6))
            self.add_glow(hx, hy, sc(16), (c[0] // 2, c[1] // 3, c[2] // 3))
        elif k == "grenade" and b.effect == "cluster":
            pygame.draw.circle(s, (20, 22, 18), (hx, hy), sc(8.5))
            pygame.draw.circle(s, (70, 78, 50), (hx, hy), sc(7.5))
            pygame.draw.line(s, (230, 170, 40), (hx - sc(7), hy), (hx + sc(7), hy), max(2, sc(3)))
            if int(b.age * 8) % 2 == 0:
                pygame.draw.circle(s, (255, 90, 40), (hx, hy - sc(4)), sc(2.5))
                self.add_glow(hx, hy, sc(16), (110, 40, 10))
        elif k == "grenade" and b.effect == "bomblet":
            pygame.draw.circle(s, (40, 40, 36), (hx, hy), sc(3.2))
            if int(b.age * 14) % 2 == 0:
                pygame.draw.circle(s, (255, 150, 50), (hx, hy), sc(1.6))
        elif k == "grenade":
            pygame.draw.circle(s, (45, 50, 40), (hx, hy), sc(4.5))
            if int(b.age * 8) % 2 == 0:
                pygame.draw.circle(s, (255, 60, 40), (hx, hy - sc(2)), sc(1.8))
                self.add_glow(hx, hy, sc(10), (90, 20, 10))
        elif k == "missile":
            ta, tb = to_screen(b.x - b.vx * 0.025, b.y - b.vy * 0.025, b.z)
            tx, ty = ta + ox, tb + oy
            pygame.draw.line(s, (60, 62, 60), (tx, ty), (hx, hy), max(2, sc(3.5)))
            pygame.draw.circle(s, c, (hx, hy), max(1, sc(2)))
            self.add_glow(tx, ty, sc(12), (c[0] // 2, c[1] // 3, c[2] // 4))
        elif k == "wave":
            self.draw_wave(b, ox, oy)
        elif k == "jet":
            ta, tb = to_screen(b.x - b.vx * 0.035, b.y - b.vy * 0.035, b.z)
            tx, ty = ta + ox, tb + oy
            pygame.draw.line(s, tuple(v // 2 for v in c), (tx, ty), (hx, hy), max(2, sc(6)))
            pygame.draw.line(s, c, (tx, ty), (hx, hy), max(2, sc(4)))
            pygame.draw.line(s, (255, 255, 255), ((tx + hx) / 2, (ty + hy) / 2), (hx, hy), max(1, sc(1.5)))
            self.add_glow(hx, hy, sc(10), (c[0] // 3, c[1] // 3, c[2] // 3))
        elif k == "rocket":
            ta, tb = to_screen(b.x - b.vx * 0.03, b.y - b.vy * 0.03, b.z)
            tx, ty = ta + ox, tb + oy
            pygame.draw.line(s, (70, 72, 70), (tx, ty), (hx, hy), sc(5))
            pygame.draw.circle(s, c, (hx, hy), sc(2.5))
            self.add_glow(tx, ty, sc(18), (c[0] // 2, c[1] // 3, c[2] // 4))
        elif k == "acid":
            self.add_glow(hx, hy, sc(16), (40, 110, 20))
            pygame.draw.circle(s, (130, 255, 70), (hx, hy), sc(5))
            pygame.draw.circle(s, (220, 255, 180), (hx - sc(1.5), hy - sc(1.5)), sc(1.8))

    def draw_wave(self, b, ox, oy):
        """Microwave ring: an arc of the circle around the muzzle; segments behind walls are shadowed out."""
        s = self.screen
        c = b.color
        rad = math.hypot(b.x - b.ox, b.y - b.oy)
        base = math.atan2(b.vy, b.vx)
        k = max(0.0, min(1.0, b.life / 0.35))
        n, m = len(b.reach), 15
        runs, cur = [], []
        for j in range(m):
            u = j / (m - 1)
            f = u * (n - 1)
            i0 = int(f)
            i1 = min(n - 1, i0 + 1)
            reach = b.reach[i0] + (b.reach[i1] - b.reach[i0]) * (f - i0)
            a = base - b.cone + 2 * b.cone * u
            if rad <= reach:
                p_ = to_screen(b.ox + math.cos(a) * rad, b.oy + math.sin(a) * rad, b.z * 0.8)
                cur.append((p_[0] + ox, p_[1] + oy))
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        dim = (int(c[0] * 0.55 * k), int(c[1] * 0.55 * k), int(c[2] * 0.55 * k))
        hot = tuple(min(255, int((v * 0.5 + 128) * k)) for v in c)
        for run in runs:
            if len(run) < 2:
                continue
            pygame.draw.lines(s, dim, False, run, max(2, int(sc(9) * k)))
            pygame.draw.lines(s, hot, False, run, max(1, int(sc(3) * k)))
            mid = run[len(run) // 2]
            self.add_glow(mid[0], mid[1], int(sc(18) + rad * sc(6)), (c[0] // 5, c[1] // 6, c[2] // 5))

    def draw_arc(self, a_, ox, oy):
        """Coil lightning: a jagged bolt re-randomised every frame through all its bounce / chain points."""
        pts, life, mx, c, wf = a_
        k = max(0.0, life / mx)
        scr = []
        for (x, y, z) in pts:
            p_ = to_screen(x, y, z)
            scr.append((p_[0] + ox, p_[1] + oy))
        path = [scr[0]]
        for (x1, y1), (x2, y2) in zip(scr, scr[1:]):
            L_ = math.hypot(x2 - x1, y2 - y1)
            m = max(2, int(L_ / sc(16)))
            nx_, ny_ = (-(y2 - y1) / (L_ or 1), (x2 - x1) / (L_ or 1))
            for j in range(1, m):
                u = j / m
                jit = rnd.uniform(-1, 1) * sc(9) * math.sin(u * math.pi) ** 0.5
                path.append((x1 + (x2 - x1) * u + nx_ * jit, y1 + (y2 - y1) * u + ny_ * jit))
            path.append((x2, y2))
        s = self.screen
        if len(path) >= 2:
            pygame.draw.lines(s, (int(c[0] * 0.5 * k), int(c[1] * 0.5 * k), int(c[2] * 0.6 * k)), False, path, max(2, int(sc(7) * wf * k)))
            pygame.draw.lines(s, (230, 235, 255), False, path, max(1, int(sc(2.2) * wf * k)))
        for p_ in scr[1:]:
            self.add_glow(p_[0], p_[1], sc(26), (c[0] // 3, c[1] // 3, c[2] // 3))
        self.add_glow(scr[0][0], scr[0][1], sc(20), (c[0] // 3, c[1] // 3, c[2] // 3))

    # ------------------------------------------------------------ support gadgets
    def scaled(self, img, k):
        if abs(k - 1.0) < 0.03:
            return img
        key = ("scale", id(img), round(k, 2))
        out = self._tint.get(key)
        if out is None:
            w_, h_ = img.get_size()
            out = self._tint[key] = pygame.transform.smoothscale(img, (max(1, int(w_ * k)), max(1, int(h_ * k))))
        return out

    def support_items(self, w, items, n, ground, on_screen):
        """Every equipped module: its body (sprite at its own hover point) plus whatever it projects into the world."""
        spr = self.spr
        t = self.time
        for tr in w.turrets:                    # deployed turrets
            gx, gy = ground(tr.x, tr.y)
            if on_screen(gx, gy):
                sp = spr["dep_" + tr.kind]
                img = sp.get("idle", dir_index(tr.aim[0], tr.aim[1], 16))
                n += 1
                items.append((tr.x + tr.y - 0.3, n, None, lambda gx=gx, gy=gy: self.screen.blit(shadow(sc(14)), (gx - sc(14), gy - sc(7))), 0))
                n += 1
                items.append((tr.x + tr.y, n, img, gx - sp.ax, gy - sp.ay))
                if tr.flash > 0:
                    n += 1
                    items.append((tr.x + tr.y, n, sp.flash(img), gx - sp.ax, gy - sp.ay))
                if tr.muzzle > 0:
                    mx_, my_ = ground(tr.x + tr.aim[0] * 0.55, tr.y + tr.aim[1] * 0.55, 0.55 if tr.kind == "mgturret" else 0.8)
                    n += 1
                    items.append((tr.x + tr.y + 0.01, n, None, lambda mx_=mx_, my_=my_: self.add_glow(mx_, my_, sc(20), (140, 90, 30)), 0))
                if tr.hp < tr.max_hp:
                    n += 1
                    items.append((tr.x + tr.y + 0.02, n, None, lambda tr=tr, gx=gx, gy=gy: self.draw_turret_bar(tr, gx, gy), 0))
        for d in w.decoys:                      # decoy holograms
            gx, gy = ground(d.x, d.y)
            if on_screen(gx, gy):
                n += 1
                items.append((d.x + d.y, n, None, lambda d=d, gx=gx, gy=gy: self.draw_decoy(d, gx, gy), 0))
        for pl, su in [(pl, g) for pl in w.players for g in pl.equipped()]:
            if not pl.alive:
                continue
            pkey = pl.x + pl.y
            kind = su.kind
            if kind == "shield":
                n += 1
                items.append((pkey - 0.02, n, None, lambda su=su, pl=pl: self.draw_shield(su, pl, ground, False), 0))
                n += 1
                items.append((pkey + 0.35, n, None, lambda su=su, pl=pl: self.draw_shield(su, pl, ground, True), 0))
                continue
            # things a module puts in the world
            if kind == "mines":
                for mn in su.mines:
                    gx, gy = ground(mn[0], mn[1])
                    if on_screen(gx, gy):
                        n += 1
                        items.append((mn[0] + mn[1] - 0.2, n, None, lambda gx=gx, gy=gy, mn=mn: self.draw_mine(gx, gy, mn), 0))
            elif kind == "aura":
                n += 1
                items.append((pkey - 0.4, n, None, lambda su=su, pl=pl: self.draw_aura(su, pl, ground), 0))
            elif kind == "leech":
                for e, grow in su.latched:
                    n += 1
                    items.append((max(pkey, e.x + e.y) + 0.05, n, None, lambda su=su, e=e, gr=grow: self.draw_tongue(su, e, gr, ground), 0))
            elif kind == "tether" and su.beam:
                n += 1
                items.append((pkey + 0.05, n, None, lambda su=su, pl=pl: self.draw_tether(su, pl, ground), 0))
            elif kind == "magnet" and su.beam:
                n += 1
                items.append((pkey + 0.05, n, None, lambda su=su: self.draw_magnet_pull(su, ground), 0))
            if kind == "gunarm":                 # grows out of the backpack; drawn in front of / behind the body
                front = (su.tx + su.ty) > pkey
                n += 1
                items.append((pkey + (0.03 if front else -0.03), n, None, lambda su=su, pl=pl: self.draw_gun_arm(su, pl, ground), 0))
                continue
            # the module body
            if kind in ("mgturret", "mortar") and su.deployed is not None:
                continue
            if kind == "skull" and su.state == "reform":
                continue
            if kind == "tether" and su.beam and not su.beam[4]:
                bx_, by_ = su.sat
                bz = 1.0
            else:
                bx_, by_, bz = su.x, su.y, su.z
            gx, gy = ground(bx_, by_)
            if not on_screen(gx, gy):
                continue
            sp = spr[su.sprite]
            k = su.size * (1.2 if kind == "sawbot" else 1.0) * (0.75 if kind in WORN else 1.0)
            if kind == "sawbot":
                img = sp.get("spin", 0, t * 30)
            elif kind == "medbot":
                img = sp.get("hover", dir_index(su.aim[0], su.aim[1], 8), t * 8)
            elif kind == "gunbot":
                img = sp.get("hover", dir_index(su.aim[0], su.aim[1], 16), t * 8)
            elif kind == "skull":
                img = sp.get("hover", dir_index(su.aim[0], su.aim[1], 8), t * 8)
            else:
                img = sp.get(sp.first_anim, 0, t * 8)
            if kind in ("core", "aura", "grenade") and su.elem:
                img = self.tinted(img, su.tint)
            if kind == "core" and su.cd > 0:
                img = sp.faded(img, 150)
            img = self.scaled(img, k)
            hx, hy = ground(bx_, by_, bz)
            rx = int(sc(9) * k)
            key = bx_ + by_
            n += 1
            items.append((key - 0.3, n, None, lambda gx=gx, gy=gy, rx=rx: self.screen.blit(shadow(rx), (gx - rx, gy - rx // 2)), 0))
            n += 1
            items.append((key, n, img, hx - sp.ax * k, hy - sp.ay * k))
            if su.flash > 0:
                n += 1
                items.append((key, n, sp.flash(img), hx - sp.ax * k, hy - sp.ay * k))
            fill = min(1.0, su.charge / max(1, su.p.get("capacity", 1)))
            glow_c = {"medbot": (20, 70, 35), "sawbot": (60, 45, 15), "skull": (20, 70, 100), "tether": (10, 80, 70),
                      "battery": (int(40 * fill) + 10, int(70 * fill) + 10, 15),
                      "core": tuple(c // 4 for c in su.tint), "aura": tuple(c // 4 for c in su.tint)}.get(kind)
            if glow_c:
                n += 1
                items.append((key + 0.01, n, None, lambda hx=hx, hy=hy, c=glow_c: self.add_glow(hx, hy, sc(18), c), 0))
            if kind == "medbot" and su.healing:
                px_, py_ = ground(pl.x, pl.y, 0.95)
                n += 1
                items.append((max(key, pkey) + 0.02, n, None, lambda a=(hx, hy), b=(px_, py_): self.draw_heal_beam(a, b), 0))
            elif kind == "gunbot" and su.muzzle > 0:
                mx_, my_ = ground(su.x + su.aim[0] * 0.3, su.y + su.aim[1] * 0.3, su.z - 0.1)
                n += 1
                items.append((key + 0.01, n, None, lambda mx_=mx_, my_=my_: self.add_glow(mx_, my_, sc(16), (120, 70, 40)), 0))
            elif kind == "jets" and su.trail_t > 0:
                n += 1
                items.append((key + 0.01, n, None, lambda hx=hx, hy=hy: self.add_glow(hx, hy + sc(14), sc(30), (120, 60, 10)), 0))
        return n

    def draw_turret_bar(self, tr, gx, gy):
        bw = sc(40)
        k = max(0.0, tr.hp / max(1, tr.max_hp))
        y = gy - sc(70)
        pygame.draw.rect(self.screen, (20, 20, 24), (gx - bw // 2 - 1, y - 1, bw + 2, sc(5) + 2))
        col = (120, 220, 90) if k > 0.5 else ((240, 200, 60) if k > 0.25 else (255, 70, 50))
        pygame.draw.rect(self.screen, col, (gx - bw // 2, y, int(bw * k), sc(5)))

    def draw_gun_arm(self, su, pl, ground):
        """Pipe arm bolted to the backpack: mount -> raised elbow -> wrist, holding the stowed gun's floor sprite."""
        s = self.screen
        wp = pl.weapons[1 - pl.cur]
        bob = -abs(math.sin(pl.walk / 1.1 * math.tau)) * sc(2) if pl.moving else 0
        bx, by = ground(su.x, su.y, su.z)
        by += bob
        ex_ = su.x + (su.tx - su.x) * 0.45
        ey_ = su.y + (su.ty - su.y) * 0.45
        mx_, my_ = ground(ex_, ey_, su.z + 0.22)
        my_ += bob
        wx, wy = ground(su.tx, su.ty, su.z - 0.05)
        pts = [(bx, by), (mx_, my_), (wx, wy)]
        for wd, c in ((sc(5.5), (16, 16, 20)), (sc(3.5), (92, 94, 104)), (sc(1.2), (180, 182, 190))):
            pygame.draw.lines(s, c, False, pts, max(1, int(wd)))
        for (px_, py_), r_, c in (((bx, by), sc(3.5), (60, 62, 70)), ((mx_, my_), sc(2.8), (220, 160, 40)), ((wx, wy), sc(2.2), (150, 152, 160))):
            pygame.draw.circle(s, (12, 12, 14), (int(px_), int(py_)), int(r_) + 1)
            pygame.draw.circle(s, c, (int(px_), int(py_)), int(r_))
        gsp = self.spr.get("gun_" + WP.sprite_arch(wp.arch))
        if gsp:
            a = math.atan2(su.aim[1], su.aim[0])
            img = self.scaled(gsp.get("idle", 0, int(round(a / (math.tau / 8))) % 8), 0.8)
            ga, gb = ground(su.tx, su.ty, su.z - 0.35)
            s.blit(img, (ga - gsp.ax * 0.8, gb - gsp.ay * 0.8 + bob))
        if su.muzzle > 0:
            mf = WP.MUZZLE[wp.arch][0] * 0.5
            gx_, gy_ = ground(su.tx + su.aim[0] * mf, su.ty + su.aim[1] * mf, su.z - 0.05)
            self.add_glow(gx_, gy_, sc(22), wp.st["color"])

    def draw_tongue(self, su, e, grow, ground):
        s = self.screen
        a = ground(su.x, su.y, su.z - 0.1)
        b = ground(e.x, e.y, (getattr(e, "st", None) or {}).get("hz", 0.8) * 0.6)
        tip = (a[0] + (b[0] - a[0]) * grow, a[1] + (b[1] - a[1]) * grow)
        mid = ((a[0] + tip[0]) / 2, (a[1] + tip[1]) / 2 + sc(18) * grow)
        pts = [a]
        for i in range(1, 9):
            u = i / 8
            pts.append(((1 - u) ** 2 * a[0] + 2 * u * (1 - u) * mid[0] + u * u * tip[0],
                        (1 - u) ** 2 * a[1] + 2 * u * (1 - u) * mid[1] + u * u * tip[1] + math.sin(self.time * 9 + u * 6) * sc(2)))
        pygame.draw.lines(s, (60, 10, 14), False, pts, max(2, sc(6)))
        pygame.draw.lines(s, (170, 50, 60), False, pts, max(1, sc(3)))
        if grow >= 1:
            for j in range(3):                   # gulps travelling back up the tongue
                u = 1 - ((self.time * 1.6 + j / 3) % 1.0)
                q = pts[min(8, int(u * 8))]
                pygame.draw.circle(s, (170, 220, 60), (int(q[0]), int(q[1])), max(2, sc(4)))

    def draw_decoy(self, d, gx, gy):
        if d.t < 1.0 and int(self.time * 20) % 2:
            return
        legs, torso = self.spr["player_legs"], self.spr["torso_" + WP.sprite_arch(d.pl.weapon.arch)]
        limg = self.tinted(legs.get("idle", 1, 0), (90, 230, 255))
        timg = self.tinted(torso.get("idle", dir_index(d.aim[0], d.aim[1], 16)), (90, 230, 255))
        jit = (int(self.time * 30) % 3 - 1) if int(self.time * 7) % 5 == 0 else 0
        for img, sp in ((limg, legs), (timg, torso)):
            ghost = img.copy()
            ghost.set_alpha(150 if d.flash <= 0 else 230)
            self.screen.blit(ghost, (gx - sp.ax + jit * sc(2), gy - sp.ay))
        self.add_glow(gx, gy - sc(30), sc(34), (15, 60, 75))

    def draw_mine(self, gx, gy, mn):
        s = self.screen
        r = sc(7)
        rect = pygame.Rect(0, 0, r * 2, r)
        rect.center = (gx, gy)
        pygame.draw.ellipse(s, (30, 30, 34), rect.inflate(sc(3), sc(2)))
        pygame.draw.ellipse(s, (95, 95, 100), rect)
        on = mn[2] <= 0 and int(self.time * 4 + mn[0] * 3) % 2 == 0
        pygame.draw.circle(s, (255, 60, 40) if on else (90, 20, 15), (gx, gy - sc(1)), max(1, sc(2)))
        if on:
            self.add_glow(gx, gy, sc(10), (90, 15, 10))

    def draw_aura(self, su, pl, ground):
        c = su.tint
        R = su.p["radius"]
        pulse = 0.75 + 0.25 * math.sin(self.time * 4)
        cx, cy = ground(pl.x, pl.y)
        rx = int(R * HW * 1.414)
        for k, (f, a) in enumerate(((1.0, 0.9), (0.66, 0.5))):
            rect = pygame.Rect(0, 0, int(rx * 2 * f), int(rx * f))
            rect.center = (cx, cy)
            col = tuple(int(v * a * pulse) for v in c)
            pygame.draw.ellipse(self.screen, col, rect, max(1, sc(3 - k)))
        self.add_glow(cx, cy, int(rx * 0.9), tuple(int(v * 0.12 * pulse) for v in c))

    def draw_tether(self, su, pl, ground):
        x1, y1, x2, y2, coop = su.beam
        a = ground(x1, y1, 0.9)
        b = ground(x2, y2, 0.9 if coop else 1.0)
        s = self.screen
        ph = 0.6 + 0.4 * math.sin(self.time * 12)
        pts = [a]
        for i in range(1, 8):
            u = i / 8
            pts.append((a[0] + (b[0] - a[0]) * u + math.sin(self.time * 20 + i * 2) * sc(3),
                        a[1] + (b[1] - a[1]) * u + math.cos(self.time * 17 + i * 3) * sc(3)))
        pts.append(b)
        pygame.draw.lines(s, (10, int(90 * ph), 80), False, pts, max(2, sc(7)))
        pygame.draw.lines(s, (180, 255, 235), False, pts, max(1, sc(2)))
        self.add_glow(b[0], b[1], sc(20), (10, 70, 60))

    def draw_magnet_pull(self, su, ground):
        a = ground(su.x, su.y, su.z - 0.1)
        for (x, y) in su.beam:
            b = ground(x, y, 0.3)
            if int(self.time * 15 + x) % 2:
                pygame.draw.line(self.screen, (200, 90, 90), a, b, 1)
            self.add_glow(b[0], b[1], sc(10), (60, 15, 15))

    def draw_heal_beam(self, a, b):
        s = self.screen
        ph = 0.5 + 0.5 * math.sin(self.time * 9)
        pygame.draw.line(s, (30, int(110 + 60 * ph), 55), a, b, max(2, sc(4)))
        pygame.draw.line(s, (190, 255, 210), a, b, max(1, sc(1.5)))
        self.add_glow(b[0], b[1], int(sc(14) + sc(8) * ph), (20, 80, 35))

    def draw_shield(self, su, pl, ground, front):
        """Partial energy ring orbiting the player; drawn in two halves so it wraps around the body in depth."""
        r = su.radius()
        half = su.p["arc"] / 2
        m = 16
        down = su.down > 0
        if down and int(self.time * 12) % 3:
            return
        frac = max(0.0, su.charge / max(1, su.p["capacity"]))
        if su.flash > 0:
            col = (235, 250, 255)
        elif down:
            col = (70, 60, 90)
        else:
            col = tuple(int(a + (b - a) * frac) for a, b in zip((255, 110, 110), (110, 200, 255)))
        lo, hi = [], []
        for j in range(m + 1):
            a = su.ang - half + 2 * half * j / m
            x, y = pl.x + math.cos(a) * r, pl.y + math.sin(a) * r
            in_front = (x + y) > (pl.x + pl.y)
            lo.append((ground(x, y, 0.3), in_front))
            hi.append((ground(x, y, 1.25), in_front))
        s = self.screen
        segs = [j for j in range(m) if lo[j][1] == front or lo[j + 1][1] == front]
        if not segs:
            return
        xs = [p_[0][0] for p_ in lo + hi]
        ys = [p_[0][1] for p_ in lo + hi]
        x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
        box_ = pygame.Surface((int(max(xs)) - x0 + 4, int(max(ys)) - y0 + 4))
        fill = (col[0] // 7, col[1] // 6, col[2] // 5)
        for j in segs:
            quad = [(lo[j][0][0] - x0, lo[j][0][1] - y0), (lo[j + 1][0][0] - x0, lo[j + 1][0][1] - y0),
                    (hi[j + 1][0][0] - x0, hi[j + 1][0][1] - y0), (hi[j][0][0] - x0, hi[j][0][1] - y0)]
            pygame.draw.polygon(box_, fill, quad)
        s.blit(box_, (x0, y0), special_flags=pygame.BLEND_ADD)
        wd = max(1, sc(3))
        for j in segs:
            pygame.draw.line(s, col, hi[j][0], hi[j + 1][0], wd)
            pygame.draw.line(s, tuple(c_ // 2 for c_ in col), lo[j][0], lo[j + 1][0], max(1, sc(2)))
            if j % 3 == 0:
                pygame.draw.line(s, tuple(c_ // 3 for c_ in col), lo[j][0], hi[j][0], 1)
        for j in (0, m):        # emitter nodes at the tips
            if lo[j][1] == front:
                e1, e2 = lo[j][0], hi[j][0]
                pygame.draw.line(s, (40, 44, 52), e1, e2, max(2, sc(5)))
                pygame.draw.circle(s, col, (int(e2[0]), int(e2[1])), max(2, sc(4)))
                self.add_glow(e2[0], e2[1], sc(16), (col[0] // 4, col[1] // 4, col[2] // 4))
        mid = hi[segs[len(segs) // 2]][0]
        self.add_glow(mid[0], mid[1] + sc(14), sc(34), (col[0] // 8, col[1] // 7, col[2] // 6))

    def support_card(self, s, su, x, y, compare=None, title=None, width=None, alpha=170):
        import support as SU
        lines = [(self.mid, su.name, su.color),
                 (self.small, "%s %s  -  LVL %d" % (su.rarity_name, su.label, su.level), (170, 175, 190)),
                 (self.small, "MODULE: " + su.blurb(), (150, 220, 160))]
        dt_ = su.dtype()
        if dt_:
            import damage as DM
            lines.append((self.small, [("DAMAGE: ", (130, 135, 150)), (dt_.upper(), DM.COLOR.get(dt_, (220, 220, 220)))], None))
        stats = su.card_lines()
        rows = (len(stats) + 2) // 3
        h = sc(12) + sum(f.get_height() + sc(2) for f, _, _ in lines) + sc(22) * rows + (sc(20) if title else 0)
        rect = pygame.Rect(x, y, width or sc(370), h)
        self.panel(s, rect, alpha)
        pygame.draw.rect(s, su.color, (x, y, sc(4), h))
        cy = y + sc(6)
        if title:
            s.blit(self.small.render(title, True, (255, 220, 120)), (x + sc(12), cy))
            cy += sc(20)
        for f, txt, col in lines:
            if isinstance(txt, list):          # multi-coloured line: [(text, colour), ...]
                xx = x + sc(12)
                for part, pc in txt:
                    img = f.render(part, True, pc)
                    s.blit(img, (xx, cy))
                    xx += img.get_width()
            else:
                s.blit(f.render(txt, True, col), (x + sc(12), cy))
            cy += f.get_height() + sc(2)
        params = [(k_, v_) for k_, v_ in SU.KINDS[su.kind]["params"].items()
                  if not (su.kind == "battery" and k_ == ("dmg" if su.elem == "revive" else "heal"))]
        for i, ((lbl, val), (name, (lo, hi, _, _))) in enumerate(zip(stats, params)):
            col = (230, 230, 230)
            if compare is not None and compare.kind == su.kind and abs(su.p[name] - compare.p[name]) > 1e-6:
                better = (su.p[name] > compare.p[name]) == (hi > lo)
                col = (110, 255, 120) if better else (255, 100, 90)
            col_x = x + sc(12) + (i % 3) * sc(118)
            row_y = cy + (i // 3) * sc(22)
            s.blit(self.small.render(lbl, True, (130, 135, 150)), (col_x, row_y))
            s.blit(self.small.render(val, True, col), (col_x + sc(66), row_y))
        return rect

    def draw_ring(self, gx, gy, q):
        k = max(0.0, q.life / q.max)
        rx = q.size * HW
        rect = pygame.Rect(0, 0, rx * 2, rx)
        rect.center = (gx, gy)
        c = q.color
        pygame.draw.ellipse(self.screen, (int(c[0] * k), int(c[1] * k), int(c[2] * k)), rect, max(1, int(sc(4) * k + 1)))
        self.add_glow(gx, gy, int(rx * 0.7) + 2, (int(c[0] * k * 0.35), int(c[1] * k * 0.35), int(c[2] * k * 0.35)))

    def draw_bullet(self, hx, hy, tx, ty, b):
        s = self.screen
        c = b.color
        if b.hostile:
            self.add_glow(hx, hy, sc(16), (c[0] // 2, c[1] // 2, c[2] // 2))
            pygame.draw.circle(s, (255, 200, 160), (hx, hy), sc(3.5))
        else:
            self.add_glow(hx, hy, sc(10), (c[0] // 3, c[1] // 3, c[2] // 3))
            pygame.draw.line(s, c, (tx, ty), (hx, hy), sc(3))
            pygame.draw.line(s, (255, 255, 255), ((tx + hx) / 2, (ty + hy) / 2), (hx, hy), max(1, sc(1.2)))

    def draw_particle(self, x, y, q, ox, oy):
        s = self.screen
        k = max(0.0, q.life / q.max)
        kind = q.kind
        if kind == "blood":
            pygame.draw.circle(s, q.color, (x, y), max(1, q.size * S * 0.5))
        elif kind == "chunk":
            sz = max(2, int(q.size * S))
            pygame.draw.rect(s, q.color, (x - sz / 2, y - sz / 2, sz, sz))
        elif kind == "shell":
            c = q.color if not q.rest else (q.color[0] * 3 // 4, q.color[1] * 3 // 4, q.color[2] * 3 // 4)
            wd, ht = max(2, int(sc(1.5 * q.size))), max(1, int(sc(q.size)))
            pygame.draw.rect(s, c, (x - wd // 2, y - ht // 2, wd, ht))
            if q.size >= 4:               # laser battery: a dying red charge strip
                pygame.draw.rect(s, (255, 70, 60) if not q.rest else (110, 30, 30), (x - wd // 2 + 1, y - 1, max(1, wd // 3), 2))
            elif q.size >= 2.5:           # shotgun hull: brass base
                pygame.draw.rect(s, (200, 160, 60), (x - wd // 2, y - ht // 2, max(1, wd // 4), ht))
        elif kind == "spark":
            a, b = to_screen(q.x - q.vx * 0.025, q.y - q.vy * 0.025, q.z - q.vz * 0.025)
            pygame.draw.line(s, q.color, (a + ox, b + oy), (x, y), max(1, sc(1.5)))
        elif kind == "smoke":
            r = max(2, int(q.size * HW))
            img = smoke_surf(r, int(150 * k), q.color)
            s.blit(img, (x - r, y - r))
        elif kind == "fire":
            c = q.color
            r = max(2, int(q.size * S * (0.4 + k * 0.6)))
            self.add_glow(x, y, r, (int(c[0] * k), int(c[1] * k), int(c[2] * k)))
        elif kind == "glow":
            c = q.color
            self.add_glow(x, y, sc(6), (int(c[0] * k * 0.6), int(c[1] * k * 0.6), int(c[2] * k * 0.6)))
            pygame.draw.rect(s, c, (x - sc(1), y - sc(1), sc(2), sc(2)))

    # ------------------------------------------------------------ HUD
    def tier_text(self, font, txt, rarity, default_col):
        """Weapon name lettered for its tier: Demonic = black with a red outline, Eldritch = black with green, Sacred = white."""
        spec = WP.TIER_TEXT.get(rarity)
        if not spec:
            return font.render(txt, True, default_col)
        col, out = spec
        key = ("tiertext", id(font), txt, rarity)
        img = self._tint.get(key)
        if img is None:
            base = font.render(txt, True, col)
            if out is None:
                img = base
            else:
                ol = font.render(txt, True, out)
                img = pygame.Surface((base.get_width() + 4, base.get_height() + 4), pygame.SRCALPHA)
                for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)):
                    img.blit(ol, (2 + dx, 2 + dy))
                img.blit(base, (2, 2))
            self._tint[key] = img
        return img

    def panel(self, s, rect, alpha=125):
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        bg.fill((8, 8, 14, alpha))
        s.blit(bg, rect.topleft)

    def weapon_card(self, s, wp, x, y, compare=None, title=None, alpha=None):
        B = WP.BRANDS[wp.brand]
        lines = [(self.mid, wp.name, ("tier", wp.rarity, wp.color)),
                 (self.small, "%s %s  -  LVL %d" % (wp.rarity_name, wp.st["label"], wp.level), (170, 175, 190)),
                 (self.small, [(wp.brand.upper(), B["color"]), ("  -  " + B["blurb"], (150, 150, 165))], None),
                 (self.small, WP.brand_summary(wp.brand), tuple(int(c_ * 0.8 + 40) for c_ in B["color"]))]
        for m in wp.mods:
            lines.append((self.small, "+ %s: %s" % (m["adj"], m["desc"]), (150, 220, 160)))
        st_ = wp.st
        fx_ = WP.TIER_FX.get(wp.rarity)
        if wp.rarity == WP.SACRED:
            lines.append((self.small, "SACRED: heals you %.0f integrity/s while wielded" % fx_["regen"], (255, 255, 255)))
        elif wp.rarity == WP.ELDRITCH:
            lines.append((self.small, "ELDRITCH: drains %.0f integrity/s while wielded, heals you %d%% of damage dealt"
                          % (-fx_["regen"], round(fx_["leech"] * 100)), (90, 255, 90)))
        elif wp.rarity == WP.DEMONIC:
            lines.append((self.small, "DEMONIC: burns you %.1f integrity/s while wielded, +%d%% damage"
                          % (-fx_["regen"], round(st_["demonic_bonus"] * 100)), (255, 70, 50)))
        import damage as DM
        sec = DM.secondary(st_)
        main_ = st_["dtype"].upper() + ((" (%s)" % DM.AMMO_LABEL[st_["ammo"]]) if st_.get("ammo") else "")
        lines.append((self.small, [("DAMAGE: ", (130, 135, 150)), (main_, DM.COLOR[st_["dtype"]])]
                      + [x_ for t in sec for x_ in (("  +  ", (130, 135, 150)), (t.upper(), DM.COLOR[t]))], None))
        if st_.get("shell"):
            n_ = max(1, st_["barrels"])
            lines.append((self.small, "SHELLS: %s  (%s)" % (WP.SHELLS[st_["shell"]]["label"],
                          ("one slug" if n_ == 1 else "%d slugs, one per barrel" % n_)), (255, 215, 150)))
        elif WP.is_shotgun(wp.arch):
            lines.append((self.small, "SHELLS: Buckshot", (255, 215, 150)))
        if st_.get("barrels"):
            lines.append((self.small, "Break-action: all %d barrels fire at once, reload every shot" % st_["barrels"], (255, 200, 120)))
        if st_.get("ammo"):
            lines.append((self.small, "AMMO: " + {"pen": "Penetrating Core  (+2 pierce, x1.35 robots & constructs)",
                                                   "exp": "Expanding  (x1.35 undead & mutants, x0.75 robots & constructs)"}[st_["ammo"]],
                          (230, 230, 235)))
        if st_.get("salvo"):
            lines.append((self.small, "Fires %d-missile homing barrages" % st_["salvo"], (255, 200, 120)))
        if st_.get("cluster"):
            lines.append((self.small, "Shells burst into %d bouncing bomblets" % st_["cluster"], (255, 200, 120)))
        if st_.get("chain"):
            lines.append((self.small, "Lightning chains %d targets, ricochets %d walls" % (st_["chain"], st_["bounce"]), (170, 190, 255)))
        if st_["proj"] == "wave":
            lines.append((self.small, "Rings sweep a %d deg cone, hitting everything" % round(math.degrees(st_["cone"] * 2)), (235, 160, 255)))
        if wp.st.get("heavy", 1.0) > 1.0:
            lines.append((self.small, "LIGHT: +%d%% move speed" % round((wp.st["heavy"] - 1) * 100), (140, 230, 255)))
        if wp.st.get("heavy", 1.0) < 1.0:
            extra = "  -  spins up" if wp.st.get("spinup") else ("  -  pierces %d walls" % wp.st["wallpierce"] if wp.st.get("wallpierce") else "")
            lines.append((self.small, "HEAVY: -%d%% move speed%s" % (round((1 - wp.st["heavy"]) * 100), extra), (255, 170, 90)))
        stats = wp.card_lines()
        other = dict(compare.card_lines()) if compare else {}
        h = sc(12) + sum(f.get_height() + sc(2) for f, _, _ in lines) + sc(22) * 2 + (sc(20) if title else 0)
        widest = max(sum(f.size(p_)[0] for p_, _ in t_) if isinstance(t_, list) else f.size(t_)[0] for f, t_, _ in lines)
        if title:
            widest = max(widest, self.small.size(title)[0])
        wdt = max(sc(370), widest + sc(24))          # cards grow to fit long lines instead of spilling over
        rect = pygame.Rect(x, y, wdt, h)
        self.panel(s, rect, alpha or 125)
        pygame.draw.rect(s, wp.color, (x, y, sc(4), h))
        cy = y + sc(6)
        if title:
            s.blit(self.small.render(title, True, (255, 220, 120)), (x + sc(12), cy))
            cy += sc(20)
        for f, txt, col in lines:
            if isinstance(txt, list):          # multi-coloured line: [(text, colour), ...]
                xx = x + sc(12)
                for part, pc in txt:
                    img = f.render(part, True, pc)
                    s.blit(img, (xx, cy))
                    xx += img.get_width()
            elif isinstance(col, tuple) and col and col[0] == "tier":
                s.blit(self.tier_text(f, txt, col[1], col[2]), (x + sc(10), cy - 2))
            else:
                s.blit(f.render(txt, True, col), (x + sc(12), cy))
            cy += f.get_height() + sc(2)
        cx = x + sc(12)
        for i, (lbl, val) in enumerate(stats):
            col = (230, 230, 230)
            if compare and lbl in other:
                try:
                    mine, theirs = float(val.split("/")[0].split("s")[0].split(" ")[0]), float(other[lbl].split("/")[0].split("s")[0].split(" ")[0])
                    better = mine < theirs if lbl == "RELOAD" else mine > theirs
                    if abs(mine - theirs) > 1e-6:
                        col = (110, 255, 120) if better else (255, 100, 90)
                except ValueError:
                    pass
            col_x = cx + (i % 3) * sc(118)
            row_y = cy + (i // 3) * sc(22)
            s.blit(self.small.render(lbl, True, (130, 135, 150)), (col_x, row_y))
            s.blit(self.small.render(val, True, col), (col_x + sc(56), row_y))
        return rect

    def draw_player_hud(self, s, p, right=False):
        w = self.world
        bw = sc(180)
        c = self.PLAYER_COLORS[p.idx % 4] if len(w.players) > 1 else (150, 210, 230)
        tag = (self.pname(p) + "  ") if len(w.players) > 1 else ""
        label = self.font.render("%sINTEGRITY  %d / %d" % (tag, max(0, p.hp), p.max_hp) if p.alive else "%sDOWN" % tag, True, c)
        x = W - sc(16) - max(bw + sc(4), label.get_width()) if right else sc(16)
        y = sc(260) if right else sc(14)
        s.blit(label, (x, y))
        pygame.draw.rect(s, (20, 20, 28), (x, y + sc(18), bw + sc(4), sc(14)))
        frac = max(0.0, p.hp / p.max_hp)
        col = ((60, 220, 255), (70, 240, 200), (255, 215, 90), (190, 140, 255))[p.idx % 4] if frac > 0.35 else (255, 70, 50)
        pygame.draw.rect(s, col, (x + sc(2), y + sc(20), int(bw * frac), sc(10)))
        by = y + sc(40)
        for kind, (mag, left) in sorted(p.buffs.items()):
            title, bcol = WP.BUFFS[kind][0], WP.BUFFS[kind][1]
            s.blit(self.small.render("%s  %.0fs" % (title, left), True, bcol), (x, by))
            pygame.draw.rect(s, bcol, (x, by + sc(15), int(bw * min(1.0, left / 20)), sc(3)))
            by += sc(22)
        if p.perm_dmg > 1.001:
            s.blit(self.small.render("CALIBRATED  +%d%% dmg" % round((p.perm_dmg - 1) * 100), True, (255, 180, 80)), (x, by))
            by += sc(22)
        for su in p.equipped():
            s.blit(self.small.render(su.name, True, su.color), (x, by))
            if su.kind == "shield":
                cap = max(1, su.p["capacity"])
                k = 1 - su.down / su.p["recharge"] if su.down > 0 else su.charge / cap
                pygame.draw.rect(s, (30, 34, 44), (x, by + sc(16), bw, sc(4)))
                pygame.draw.rect(s, (90, 90, 120) if su.down > 0 else (110, 200, 255), (x, by + sc(16), int(bw * k), sc(4)))
            elif su.kind == "medbot" and su.healing:
                s.blit(self.small.render("+%.1f/s" % su.p["heal"], True, (120, 255, 150)), (x + bw - sc(40), by))
            elif su.kind in ("mgturret", "mortar"):
                if su.rebuild_t > 0:
                    st_txt, st_col = "REBUILD %.0fs" % su.rebuild_t, (255, 140, 90)
                elif su.deployed is not None:
                    st_txt, st_col = "DEPLOYED %d/%d" % (max(0, su.deployed.hp), su.p["hp"]), (170, 220, 120)
                else:
                    st_txt, st_col = "[F / B] DEPLOY", (200, 200, 160)
                im_ = self.small.render(st_txt, True, st_col)
                s.blit(im_, (x + bw - im_.get_width(), by))
            by += sc(22)
        # always-on weapon readout: name, ammo, stowed gun. The full card only fades in after a swap / pickup.
        wp = p.weapon
        name_img = self.tier_text(self.mid, wp.name, wp.rarity, wp.color)
        bx = W - sc(16) - max(sc(220), name_img.get_width()) if right else sc(16)
        top = H - sc(108)
        s.blit(name_img, (bx, top))
        ax, ay = bx, top + sc(34)
        oy_ = top + sc(80)
        if p.card_t > 0:
            fade = min(1.0, p.card_t / 0.5, (3.0 - p.card_t) / 0.15 + 0.2)
            card = self._card_surf if getattr(self, "_card_surf", None) is not None else None
            if card is None:
                card = self._card_surf = pygame.Surface((sc(720), sc(560)), pygame.SRCALPHA)
            card.fill((0, 0, 0, 0))
            r_ = self.weapon_card(card, wp, 0, 0)
            card.set_alpha(int(255 * max(0.0, min(1.0, fade))))
            cx_ = W - sc(16) - r_.width if right else sc(16)
            s.blit(card, (cx_, top - sc(10) - r_.height), r_)
            card.set_alpha(None)
        if wp.reload_t > 0:
            k = 1 - wp.reload_t / wp.st["reload"]
            s.blit(self.mid.render("RELOADING", True, (255, 200, 90)), (ax, ay))
            pygame.draw.rect(s, (40, 40, 50), (ax, ay + sc(30), sc(150), sc(6)))
            pygame.draw.rect(s, (255, 200, 90), (ax, ay + sc(30), int(sc(150) * k), sc(6)))
        else:
            inf = "infinite" in p.buffs
            txt = "INF" if inf else "%d / %d" % (wp.ammo, wp.st["mag"])
            s.blit(self.ammo_font.render(txt, True, (240, 240, 240) if wp.ammo or inf else (255, 80, 70)), (ax, ay - sc(4)))
        other = p.weapons[1 - p.cur]
        s.blit(self.small.render("[Q / Y]  %s" % other.name if p.idx == 0 else "[Y]  %s" % other.name, True,
                                 tuple(int(c_ * 0.7) for c_ in other.color)), (ax, oy_))
        # a barrel / your turret in reach: say what E / A will do with it
        tg = getattr(w, "pickup_by", {}).get(p.idx)
        if tg is not None and tg[0] in ("barrel", "turret") and p.alive:
            import support as SU
            key = "[E / A]" if p.idx == 0 else "[A]"
            if tg[0] == "barrel":
                bx_, by_ = tg[1][0] + 0.5, tg[1][1] + 0.5
                elem = w.barrel_kind.get(tg[1], "chem")
                name = {"fire": "Fire Barrel", "chem": "Chem Barrel", "rad": "Rad Barrel", "shrap": "Shrapnel Barrel"}.get(elem, "Barrel")
                txt, col = "%s  PICK UP %s" % (key, name), SU.ELEMENT_COLOR.get(elem, (230, 230, 230))
            else:
                bx_, by_ = tg[1].x, tg[1].y
                if p.gear[p.sel] is None:
                    txt, col = "%s  PACK UP %s  ->  slot %d" % (key, tg[1].mod.label, p.sel + 1), (170, 230, 140)
                else:
                    txt, col = "Select an empty D-pad slot to pack up the %s" % tg[1].mod.label, (255, 170, 130)
            ox, oy = self.last_o
            gx, gy = to_screen(bx_, by_, 1.6)
            img = self.font.render(txt, True, col)
            r_ = img.get_rect(midbottom=(gx + ox, gy + oy - sc(8)))
            self.panel(s, r_.inflate(sc(14), sc(8)), 190)
            s.blit(img, r_)
        # nearby loot comparison
        lt = w.near_loot_by.get(p.idx)
        if lt is not None and p.alive:
            ox, oy = self.last_o
            gx, gy = to_screen(lt.x, lt.y)
            cx, cy = gx + ox + (sc(30) if not right else -sc(400)), gy + oy - sc(190)
            cx = min(max(sc(10), cx), W - sc(385))
            cy = min(max(sc(70), cy), H - sc(260))
            key = "[E / A]" if p.idx == 0 else "[A]"
            who = (self.pname(p) + " ") if len(w.players) > 1 else ""
            if lt.kind == "support":
                free = next((i for i, g in enumerate(p.gear) if g is None), None)
                if free is not None:
                    dest = "equips in slot %d" % (free + 1)
                elif len(p.pack) < 8:
                    dest = "goes to backpack"
                else:
                    dest = "full: swaps with %s" % p.gear[0].name
                same = next((g for g in p.equipped() if g.kind == lt.item.kind), None)
                self.support_card(s, lt.item, int(cx), int(cy), compare=same, title="%s%s  TAKE  (%s)" % (who, key, dest))
            else:
                ttl = "%s%s  TAKE  (swaps with %s)" % (who, key, wp.name)
                if getattr(self, "_measure", None) is None:
                    self._measure = pygame.Surface((sc(800), sc(700)), pygame.SRCALPHA)
                r_ = self.weapon_card(self._measure, lt.item, 0, 0, compare=wp, title=ttl)      # measure, then fit on screen
                cx = min(max(sc(10), cx), W - r_.width - sc(10))
                cy = min(max(sc(70), cy), H - r_.height - sc(10))
                self.weapon_card(s, lt.item, int(cx), int(cy), compare=wp, title=ttl)

    def draw_team(self, s, others):
        """Net play: a slim integrity bar for each of the other players, under your own."""
        y = sc(54)
        for p in others:
            c = self.PLAYER_COLORS[p.idx % 4]
            txt = "%s  %s" % (self.pname(p), CH.CHARS[p.char]["name"]) + ("" if p.alive else "  -  DOWN")
            img = self.small.render(txt, True, c)
            s.blit(img, (sc(16), y))
            frac = max(0.0, p.hp / p.max_hp) if p.alive else 0.0
            pygame.draw.rect(s, (20, 20, 28), (sc(16), y + sc(14), sc(120), sc(6)))
            pygame.draw.rect(s, c, (sc(17), y + sc(15), int(sc(118) * frac), sc(4)))
            y += sc(26)

    def draw_dpad_faded(self, s, p, cx, cy):
        """The D-pad cross, shown after a D-pad press and faded out over its last half second."""
        a = min(1.0, p.dpad_t / 0.5)
        if a >= 1.0:
            self.draw_dpad(s, p, cx, cy)
            return
        bw, bh = sc(420), sc(300)
        layer = pygame.Surface((bw, bh), pygame.SRCALPHA)
        self.draw_dpad(layer, p, bw // 2, bh // 2)
        layer.fill((255, 255, 255, int(255 * a)), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(layer, (cx - bw // 2, cy - bh // 2))

    def draw_dpad(self, s, p, cx, cy):
        """The four module slots as a D-pad cross: icon, cooldown dimming, a flash when used."""
        b = sc(40)
        for k, (dx, dy) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
            rect = pygame.Rect(0, 0, b, b)
            rect.center = (cx + dx * (b + sc(4)), cy + dy * (b + sc(4)))
            su = p.gear[k]
            self.panel(s, rect, 150)
            if su is None:
                pygame.draw.rect(s, (60, 64, 76), rect, 1)
                continue
            sp = self.spr[su.sprite]
            icon = self.inv_icon(sp.get(sp.first_anim, 0, 0), b, b)
            busy = 0.0
            if su.kind in ("core", "jets", "decoy") and su.cd > 0:
                busy = min(1.0, su.cd / max(0.1, su.p.get("cooldown", 1.0)))
            elif su.kind == "skull" and su.state != "idle":
                busy = 1.0
            elif su.kind == "grenade" and su.cd > 0:
                busy = min(1.0, su.cd / su.p["cooldown"])
            elif su.kind == "shield" and su.down > 0:
                busy = su.down / su.p["recharge"]
            s.blit(icon, icon.get_rect(center=rect.center))
            if busy > 0:
                sh = pygame.Surface((b, int(b * busy)), pygame.SRCALPHA)
                sh.fill((0, 0, 0, 160))
                s.blit(sh, (rect.x, rect.bottom - int(b * busy)))
            col = su.color
            if su.kind in ("mgturret", "mortar") and su.deployed is not None:
                col = (120, 230, 120)
            pygame.draw.rect(s, (255, 255, 255) if su.flash > 0 else col, rect, max(1, sc(2)))
        k = p.sel
        dx, dy = ((0, -1), (1, 0), (0, 1), (-1, 0))[k]
        rect = pygame.Rect(0, 0, b, b)
        rect.center = (cx + dx * (b + sc(4)), cy + dy * (b + sc(4)))
        pygame.draw.rect(s, (255, 230, 120), rect.inflate(sc(6), sc(6)), max(2, sc(3)))
        su = p.gear[k]
        if su is not None:
            nm = self.scaled(self.small.render(su.label, True, (255, 230, 120)), 0.75)
            s.blit(nm, (cx - nm.get_width() // 2, cy - b * 1.5 - sc(10) - nm.get_height()))
        hint = self.scaled(self.small.render("D-PAD / 1-4 select   F / B use", True, (120, 125, 140)), 0.75)
        s.blit(hint, (cx - hint.get_width() // 2, cy + b * 1.5 + sc(10)))

    def draw_hud(self, s):
        w = self.world
        mine = self.local_players()
        for k, p in enumerate(mine):
            self.draw_player_hud(s, p, right=k == 1)
        if self.net is not None:
            self.draw_team(s, [p for p in w.players if p not in mine])
        for p in mine:
            if p.alive and any(p.gear) and p.dpad_t > 0:
                if len(mine) > 1:
                    self.draw_dpad_faded(s, p, W / 2 + (-sc(150) if p.idx == 0 else sc(150)), H - sc(90))
                else:
                    self.draw_dpad_faded(s, p, W - sc(90), H - sc(110))
        scr = self.mid.render("%07d" % w.score, True, (240, 240, 240))
        s.blit(scr, (W / 2 - scr.get_width() / 2, sc(10)))
        info = self.font.render("SECTOR %d   -   HIVES %d   -   find the exit portal" % (w.depth, len(w.spawners)), True, (160, 170, 190))
        s.blit(info, (W / 2 - info.get_width() / 2, sc(38)))
        self.draw_minimap(s)
        if len(w.players) == 1 and self.state == "play" and self.net is None and int(self.time * 0.5) % 2 == 0:
            hint = self.small.render("P2: press BACK / SELECT on a controller to pick a body and join", True, (90, 200, 200))
            s.blit(hint, (W / 2 - hint.get_width() / 2, H - sc(22)))
        # messages
        my = int(H * 0.66)
        for txt, col, t in reversed(w.messages):
            img = self.font.render(txt, True, col)
            img.set_alpha(int(255 * min(1.0, t)))
            s.blit(img, (W / 2 - img.get_width() / 2, my))
            my -= sc(24)
        for b in w.bosses:
            if not b.awake:
                continue
            bw_, bh_ = sc(600), sc(14)
            bx_, by_ = W / 2 - bw_ / 2, sc(64)
            title = self.mid.render(b.title, True, b.color)
            s.blit(title, (W / 2 - title.get_width() / 2, by_))
            pygame.draw.rect(s, (25, 10, 10), (bx_, by_ + sc(30), bw_, bh_))
            pygame.draw.rect(s, b.color, (bx_ + sc(2), by_ + sc(32), int((bw_ - sc(4)) * max(0, b.hp) / b.maxhp), bh_ - sc(4)))
            for f in (0.33, 0.66):
                pygame.draw.line(s, (0, 0, 0), (bx_ + bw_ * f, by_ + sc(30)), (bx_ + bw_ * f, by_ + sc(30) + bh_), max(1, sc(2)))
            break
        if w.bosses and not any(b.awake for b in w.bosses):
            pass
        elif w.bosses:
            hint = self.small.render("the portal is sealed until the guardian falls", True, (255, 140, 120))
            s.blit(hint, (W / 2 - hint.get_width() / 2, sc(112)))
        name, t = self.banner
        if t > 0:
            img = self.big.render(name, True, (230, 240, 255))
            img.set_alpha(int(255 * min(1.0, t)))
            s.blit(img, (W / 2 - img.get_width() / 2, H * 0.28))

    def draw_minimap(self, s):
        w = self.world
        L = w.level
        mm = self.minimap
        for x, y in w.explore_dirty:
            c = (120, 128, 150, 230) if L.solid[L.i(x, y)] == 1 else (45, 50, 62, 200)
            mm.set_at(((y - x) + L.W, (x + y) // 2), c)
        w.explore_dirty.clear()
        scale = 1.6 * S
        out = pygame.transform.scale(mm, (int(mm.get_width() * scale), int(mm.get_height() * scale)))
        left, top = W - out.get_width() - sc(12), sc(12)

        def mpos(x, y):
            return (left + ((y - x) + L.W) * scale, top + (x + y) / 2 * scale)
        bg = pygame.Surface(out.get_size(), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 110))
        s.blit(bg, (left, top))
        s.blit(out, (left, top))
        ex, ey = L.exit
        if w.explored[L.i(int(ex), int(ey))] and int(self.time * 3) % 2:
            pygame.draw.circle(s, (80, 220, 255), mpos(ex, ey), sc(3))
        for sp in w.spawners:
            if w.explored[L.i(int(sp.x), int(sp.y))]:
                pygame.draw.circle(s, (150, 255, 80), mpos(sp.x, sp.y), sc(2))
        for pl in w.players:
            c = (255, 255, 255) if len(w.players) == 1 else self.PLAYER_COLORS[pl.idx % 4]
            pygame.draw.circle(s, c if pl.alive else (90, 90, 90), mpos(pl.x, pl.y), sc(2.5))

    # ------------------------------------------------------------ title
    def title_menu_rects(self):
        mx = W / 2 - sc(330)
        return [pygame.Rect(int(mx + i * sc(230)), int(H - sc(98)), sc(200), sc(38)) for i in range(len(self.TITLE_MENU))]

    def draw_title_bg(self, s, vig=True):
        """The scrolling floor behind the title / lobby screens."""
        s.fill((12, 10, 18))
        t = self.time
        fl = self.spr["floor_metal"].get("idle", 0)
        alt = [self.spr[n].get("idle", 0) for n in ("floor_grate", "floor_gore", "floor_cables", "floor_bones")]
        fax, fay = self.spr["floor_metal"].ax, self.spr["floor_metal"].ay
        for cx in range(-14, 16):
            for cy in range(-14, 16):
                sx = (cy - cx) * HW + W / 2 + (t * 20 * S) % (HW * 2) - HW
                sy = (cx + cy) * HH + H / 2 + sc(60) + (t * 10 * S) % (HH * 2)
                if -sc(40) < sx < W + sc(40) and -sc(20) < sy < H + sc(40):
                    h = (cx * 7 + cy * 13) % 11
                    s.blit(alt[h % 4] if h < 4 else fl, (sx - fax, sy - fay))
        if vig:
            s.blit(self.vig, (0, 0), special_flags=pygame.BLEND_MULT)

    def draw_title(self, s):
        self.draw_title_bg(s, vig=False)
        self.draw_char_row(s, list(range(min(2, len(self.inputs)))), H / 2 + sc(100))
        self.draw_title_text(s)

    def draw_char_row(self, s, who, row_y, chars=None):
        """Character select: three bodies walking in place, tops spinning; a P1 / P2 tag over each player's pick."""
        chars = self.chars if chars is None else chars
        t = self.time
        guns = ("carbine", "shotgun_2", "rocket", "flamer", "sniper", "auto_shotgun", "plasma", "chaingun", "coil_rifle", "shotgun_4")
        arch = guns[int(t / 2.5) % len(guns)]
        for i, ch in enumerate(CH.ORDER):
            C = CH.CHARS[ch]
            legs, torso = self.spr[C["legs"]], self.spr[C["torso"] + arch]
            picked = [k for k in who if chars[k] == ch]
            z = 1.5 if picked else 1.15
            big_l = pygame.transform.scale_by(legs.get("walk", 1, t * 10), z)
            big_t = pygame.transform.scale_by(torso.get("idle", int(-t * 4 + i * 5) % 16), z)
            bob = -abs(math.sin(t * 10 / 8 * math.tau)) * sc(3) * z
            cx, cy = W / 2 + (i - 1) * sc(300), row_y
            sh = pygame.transform.scale_by(shadow(sc(14)), z)
            s.blit(sh, (cx - sh.get_width() / 2, cy - sh.get_height() / 2))
            if not picked:
                big_l.set_alpha(150)
                big_t.set_alpha(150)
            s.blit(big_l, (cx - legs.ax * z, cy - legs.ay * z))
            s.blit(big_t, (cx - torso.ax * z, cy - torso.ay * z + bob))
            col = (235, 240, 255) if picked else (130, 135, 150)
            nm = self.mid.render(C["name"], True, col)
            s.blit(nm, (cx - nm.get_width() / 2, cy + sc(18)))
            info = "%s  -  %s" % (C["cat"].upper(), "   ".join(CH.stat_lines(ch)))
            im = self.small.render(info, True, (170, 180, 200) if picked else (100, 105, 120))
            s.blit(im, (cx - im.get_width() / 2, cy + sc(44)))
            de = self.small.render(C["desc"], True, (150, 160, 180) if picked else (90, 95, 110))
            s.blit(de, (cx - de.get_width() / 2, cy + sc(60)))
            for k in picked:
                tag = self.mid.render("P%d" % (k + 1), True, self.PLAYER_COLORS[k])
                s.blit(tag, (cx - tag.get_width() / 2 + (picked.index(k) - (len(picked) - 1) / 2) * sc(40), cy - sc(128)))

    def draw_title_text(self, s):
        t = self.time
        s.blit(self.vig, (0, 0), special_flags=pygame.BLEND_MULT)
        self.center_text(s, self.big, "SKULLS & STUFF", sc(70), (235, 240, 255))
        self.center_text(s, self.font, "an isometric twin-stick shooter  -  procedurally generated sectors", sc(112), (150, 170, 200))
        dev = self.input.device_name
        lines = [
            "Pad: L-STICK move - R-STICK aim - RT fire - A pick up - X reload - Y swap - LB dash - D-PAD module - B/RB use - START menu",
            "Keys: WASD move - MOUSE aim - CLICK fire - E pick up - R reload - Q swap - SHIFT dash - 1-4 module - F use - ENTER menu",
            ("Controller detected: %s" % dev) if dev else "No controller detected (plug one in any time)",
            "CO-OP: a 2nd controller presses BACK / SELECT to join on this screen  -  or HOST / JOIN a net game for up to 4"
            + ("   (P2 READY)" if len(self.inputs) > 1 else ""),
        ]
        for i, ln in enumerate(lines):
            self.center_text(s, self.font, ln, sc(150 + i * 22), (190, 195, 210) if i < 2 else ((120, 230, 255) if i == 2 else (90, 230, 210)))
        dn = self.font.render("[Q / Y]  Damage numbers: %s" % ("ON" if self.damage_numbers else "OFF"), True,
                              (255, 220, 120) if self.damage_numbers else (150, 160, 180))
        s.blit(dn, (W - dn.get_width() - sc(16), sc(14)))
        for i, (item, r) in enumerate(zip(self.TITLE_MENU, self.title_menu_rects())):
            on = i == self.menu_i
            self.panel(s, r, 210 if on else 120)
            if on:
                pygame.draw.rect(s, (255, 230, 120), r, max(2, sc(3)))
            img = self.font.render(item, True, (255, 255, 255) if on else (150, 155, 170))
            s.blit(img, img.get_rect(center=r.center))
        if int(t * 2) % 2 == 0:
            self.center_text(s, self.font, "LEFT / RIGHT your body" + (" (each player on their own controller)" if len(self.inputs) > 1 else "")
                             + "   -   UP / DOWN choose   -   START / ENTER / A go", H - sc(40), (255, 220, 120))
        if self.title_msg[1] > 0:
            self.center_text(s, self.mid, self.title_msg[0], sc(246), (255, 140, 120))
        if self.best:
            self.center_text(s, self.font, "Best %d" % self.best, H - sc(14), (140, 150, 170))


if __name__ == "__main__":
    if "--rare-loot" in sys.argv:     # test launcher: everything rolls Mythical / Demonic / Eldritch / Sacred
        WP.RARE_ONLY = True
    Game(windowed="--windowed" in sys.argv).run()

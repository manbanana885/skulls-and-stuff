"""Net play sessions (host and guest) and their screens: lobby, join, and the in-game sync.

Host: runs the real World. Each guest's controls arrive as JSON and drive that guest's player. Every other frame
each guest gets a snapshot of the world around them (plus level edits and the effects / sounds since last time).
Guest: shows the host's world, simulates the cosmetic bits (particles, gibs, splats, sounds) itself, and sends
its controls. Its own gun follows its own aim straight away so aiming never feels laggy.
"""
import math
import time
import zlib

import pygame

import net
import sfx
import characters as CH
from assets import dir_index
from world import World, Particle, screen_to_world_dir, resolve

SNAP_EVERY = 2            # host frames per snapshot (60 fps -> 30 a second)
VIEW = 26                 # tiles around a guest's player that its snapshots cover
MAX_BACKLOG = 128 * 1024  # a guest this far behind skips snapshots until it catches up (effects still queue)
LOBBY_EVERY = 0.5
HELLO_WITHIN = 5.0         # seconds a new connection gets to prove it knows the game name
MAX_UNVERIFIED = 8         # connections allowed to be waiting on that at once
MAX_FAILS = 5              # wrong game names from one address in a minute before it's locked out for a minute
RATE_BYTES = 48 * 1024     # a guest sending more than this a second (controls are ~8 KB/s) is kicked
RATE_MSGS = 360            # ... or more messages than this a second
MAX_JUNK = 10              # ... or this many unreadable / unknown messages
GUEST_KINDS = {"h", "i", "c", "q"}

# World attributes guests never get in snapshots (local-only, rebuilt, or sent separately)
EXCLUDE = {"level", "particles", "gibs", "decals", "grid", "flow", "flow_tile", "explored", "explore_dirty", "explore_t",
           "blocked", "net_events", "actor", "local_idx", "show_numbers", "free_roam", "dot_targets", "shootables",
           "near_loot"}
CULL = ("enemies", "projs", "spawners", "traps", "loot")
# ... and never in the full-world message either
FULL_SKIP = {"particles", "gibs", "decals", "grid", "flow", "flow_tile", "net_events", "actor", "blocked"}


class RemoteInput:
    """A guest's controls as the host's world sees them."""
    keyboard = False
    mouse_mode = False
    dev = None
    device_name = "net"

    def __init__(self):
        self.move = (0.0, 0.0)
        self.aim = None
        self.fire = False
        self.pressed = set()
        self.menu = False
        self.seq = 0            # input number the world is using (the guest replays anything newer on top of our snapshot)
        self.queue = []         # guest frames not yet played: one per host frame, so bunched-up packets don't lose moves

    def poll(self, *_):
        pass

    def feed(self, d):
        try:
            m = d.get("m") or (0, 0)
            move = (max(-1.0, min(1.0, float(m[0]))), max(-1.0, min(1.0, float(m[1]))))
            a = d.get("a")
            aim = (float(a[0]), float(a[1])) if a else None
            self.queue.append((int(d.get("s", 0)), move, aim, bool(d.get("f"))))
            self.menu = bool(d.get("menu"))
            for k in list(d.get("p") or ())[:24]:
                if isinstance(k, str) and len(k) < 16:
                    self.pressed.add(k)
        except (TypeError, ValueError, IndexError):
            pass

    def next_frame(self):
        """Play the next queued guest frame (or keep the last one if none came in)."""
        if len(self.queue) > 6:                  # fallen behind (a stall): skip ahead rather than lag forever
            del self.queue[:-3]
        if self.queue:
            self.seq, self.move, self.aim, self.fire = self.queue.pop(0)


class _Idle:
    """No controls (a player whose menu is open, or a guest that hasn't said anything yet)."""
    move = (0.0, 0.0)
    aim = None
    fire = False
    pressed = frozenset()


IDLE = _Idle()


def near(o, fx, fy, r=VIEW):
    return abs(o.x - fx) < r and abs(o.y - fy) < r


# ================================================================ host
class Guest:
    def __init__(self, conn):
        self.conn = conn
        self.slot = None
        self.char = "skelebot"
        self.name = ""
        self.ready = False
        self.input = RemoteInput()
        self.in_game = False          # has been sent the current world
        self.pending = []             # effects / sounds / level edits queued for the next snapshot
        self.hello = False
        self.applied = 0              # newest input number the world has used
        self.nonce = net.secrets.token_hex(16)
        self.t0 = time.monotonic()
        self.win_t = self.t0          # flood check: bytes / messages this second
        self.win_bytes = 0
        self.win_msgs = 0
        self.junk = 0


class HostSession:
    is_host = True

    def __init__(self, g, port=net.PORT):
        self.server = net.HostServer(port)
        self.version = net.game_version()
        self.addresses = net.local_addresses()
        self.guests = []
        self.local = {0}
        self.frame = 0
        self.lobby_t = 0.0
        self.world_id = None
        self.seen_p = set()
        self.seen_g = set()
        self.level_copy = None
        self.in_update = False
        self.status = ""
        self.name = net.random_name()    # the game name guests must type (it's the password)
        self.editing = False
        self.editing_me = False         # typing your own player name (N)
        self.before_me = ""
        self.typed = False
        self.before = self.name
        self.fails = {}                  # ip -> times of wrong game names
        self.tailscale = net.TailscaleProbe()
        self.public = net.PublicIPProbe()
        sfx.router = self.route_sound
        sfx.music_router = self.route_music
        g.state = "lobby"

    # ---- sound forwarding (only what the world does, not the host's menus)
    def route_sound(self, name, vol):
        w = self.world_ref
        if not self.in_update or w is None or w.net_events is None:
            return True
        a = w.actor
        w.net_events.append(("u", name, vol, a.idx if a is not None else -1))
        return a is None or a.idx in self.local

    def route_music(self, track, fade):
        w = self.world_ref
        if self.in_update and w is not None and w.net_events is not None:
            w.net_events.append(("m", track, fade))

    world_ref = None

    # ---- connections
    def slots_used(self):
        return {0} | {gu.slot for gu in self.guests if gu.slot is not None}

    def kick(self, gu, why):
        if not gu.conn.closed:
            gu.conn.send_json("x", {"msg": why})
            gu.conn.flush()
            gu.conn.close(why)

    def poll(self, g):
        now = time.monotonic()
        for conn in self.server.accept():
            if sum(1 for gu in self.guests if not gu.hello) >= MAX_UNVERIFIED:
                conn.close("busy")
                continue
            gu = Guest(conn)
            self.guests.append(gu)
            conn.send_json("n", {"nonce": gu.nonce})
        for gu in list(self.guests):
            if not gu.hello and now - gu.t0 > HELLO_WITHIN:
                self.kick(gu, "No game name given.")
            r0 = gu.conn.recv_bytes
            msgs = gu.conn.poll()
            gu.win_bytes += gu.conn.recv_bytes - r0
            gu.win_msgs += len(msgs)
            if now - gu.win_t >= 1.0:
                gu.win_t, gu.win_bytes, gu.win_msgs = now, 0, 0
            elif gu.win_bytes > RATE_BYTES or gu.win_msgs > RATE_MSGS:
                self.kick(gu, "Kicked: sending far too much data.")
                msgs = []
            for kind, payload in msgs:
                d = net.read_json(payload, strict=True)
                if d is None or kind not in GUEST_KINDS:
                    gu.junk += 1
                    if gu.junk > MAX_JUNK:
                        self.kick(gu, "Kicked: sending garbage.")
                        break
                    continue
                if kind == "h":
                    if not gu.hello:
                        self.on_hello(g, gu, d)
                elif not gu.hello:
                    continue
                elif kind == "i":
                    gu.input.feed(d)
                elif kind == "c":
                    if d.get("char") in CH.CHARS:
                        gu.char = d["char"]
                    if "name" in d:
                        gu.name = net.clean_player_name(d.get("name", ""))
                    if d.get("ready") and not gu.ready:
                        gu.ready = True
                        if g.state != "lobby" and g.world is not None:
                            self.drop_in(g, gu)
                    self.lobby_t = 0.0
                elif kind == "q":
                    gu.conn.close("left")
            if gu.conn.closed:
                self.guests.remove(gu)
                if gu.slot is not None and g.world is not None and gu.in_game:
                    g.world.remove_player(gu.slot)
                self.lobby_t = 0.0
        self.lobby_t -= 1 / 60
        if self.lobby_t <= 0:
            self.lobby_t = LOBBY_EVERY
            info = self.lobby_info(g)
            for gu in self.guests:
                if gu.hello:
                    gu.conn.send_json("l", info)
        self.server.announce({"v": self.version, "n": 1 + sum(1 for gu in self.guests if gu.hello), "locked": 1,
                              "state": "lobby" if g.state == "lobby" else "play", "depth": g.world.depth if g.world else 0})

    def on_hello(self, g, gu, d):
        ip = (gu.conn.addr or ("?",))[0]
        now = time.monotonic()
        recent = [t for t in self.fails.get(ip, ()) if now - t < 60]
        self.fails[ip] = recent
        if len(recent) >= MAX_FAILS:
            self.kick(gu, "Too many wrong game names from your address. Wait a minute and try again.")
            return
        if d.get("v") != self.version:
            gu.conn.send_json("x", {"msg": "Different game versions (host %s, you %s). Both need the same copy of the game."
                                           % (self.version, str(d.get("v"))[:12])})
            gu.conn.flush()
            gu.conn.close("version")
            return
        if not net.proof_ok(self.name, gu.nonce, d.get("p")):
            recent.append(now)
            self.kick(gu, "Wrong game name. Ask the host for the exact name.")
            return
        free = [s for s in range(1, net.MAX_PLAYERS) if s not in self.slots_used()]
        if not free:
            gu.conn.send_json("x", {"msg": "That game is full (%d players)." % net.MAX_PLAYERS})
            gu.conn.flush()
            gu.conn.close("full")
            return
        gu.slot = free[0]
        gu.hello = True
        gu.name = net.clean_player_name(d.get("name", ""))
        if d.get("char") in CH.CHARS:
            gu.char = d["char"]
        gu.conn.send_json("w", {"slot": gu.slot, "v": self.version})
        self.lobby_t = 0.0

    def lobby_info(self, g):
        ps = [{"slot": 0, "char": g.chars[0], "ready": True, "host": True, "name": g.player_name}]
        for gu in self.guests:
            if gu.hello:
                ps.append({"slot": gu.slot, "char": gu.char, "ready": gu.ready, "host": False, "name": gu.name})
        return {"players": sorted(ps, key=lambda p: p["slot"]), "state": "lobby" if g.state == "lobby" else "play",
                "depth": g.world.depth if g.world else 0}

    # ---- worlds
    def prepare(self, w):
        w.free_roam = True
        w.local_idx = set(self.local)
        w.net_events = []
        self.world_ref = w
        self.seen_p, self.seen_g = set(), set()
        L = w.level
        self.level_copy = (bytes(L.solid), list(L.floor), list(L.wallkind), dict(L.props), bytes(w.explored))

    def start_run(self, g):
        from world import Player
        players = [Player(0, 0, 0, g.chars[0], g.player_name)]
        for gu in self.guests:
            if gu.hello and gu.ready:
                players.append(Player(0, 0, gu.slot, gu.char, gu.name))
        players.sort(key=lambda p: p.idx)
        g.new_world(1, player=players)
        g.state = "play"

    def drop_in(self, g, gu):
        w = g.world
        if all(p.idx != gu.slot for p in w.players):
            w.add_player(gu.char, idx=gu.slot, limit=net.MAX_PLAYERS, name=gu.name)
        self.send_world(g, gu)

    def send_world(self, g, gu):
        w = g.world
        state = {k: v for k, v in vars(w).items() if k not in FULL_SKIP}
        raw = net.pack(state, None)
        gu.conn.zprev = b""
        gu.conn.send("W", zlib.compress(raw, 6))
        gu.pending = []
        gu.in_game = True

    def level_diff(self, w):
        """Cells / props / explored tiles that changed since the last call."""
        L = w.level
        solid0, floor0, wall0, props0, expl0 = self.level_copy
        out = {}
        sb = bytes(L.solid)
        cells = set()
        if sb != solid0:
            cells.update(i for i in range(len(sb)) if sb[i] != solid0[i])
        if L.floor != floor0:
            cells.update(i for i in range(len(L.floor)) if L.floor[i] != floor0[i])
        if L.wallkind != wall0:
            cells.update(i for i in range(len(L.wallkind)) if L.wallkind[i] != wall0[i])
        if cells:
            out["cells"] = [(i, L.solid[i], L.floor[i], L.wallkind[i]) for i in sorted(cells)]
        if L.props != props0:
            ch = {k: v for k, v in L.props.items() if props0.get(k) != v}
            ch.update({k: None for k in props0 if k not in L.props})
            out["props"] = ch
        eb = bytes(w.explored)
        if eb != expl0:
            out["expl"] = [i for i in range(len(eb)) if eb[i] != expl0[i]]
        if out:
            self.level_copy = (sb, list(L.floor), list(L.wallkind), dict(L.props), eb)
        return out

    def collect(self, g):
        """After each host frame: queue what happened (effects, sounds, level edits) for every guest in the game."""
        w = g.world
        ev = w.net_events or []
        w.net_events = []
        parts = [p for p in w.particles if id(p) not in self.seen_p]
        self.seen_p = {id(p) for p in w.particles}
        gibs = [q for q in w.gibs if id(q) not in self.seen_g]
        self.seen_g = {id(q) for q in w.gibs}
        decals = list(w.decals)
        diff = self.level_diff(w)
        for gu in self.guests:
            if not gu.in_game:
                continue
            me = next((p for p in w.players if p.idx == gu.slot), None)
            fx, fy = (me.x, me.y) if me is not None else (w.player.x, w.player.y)
            q = gu.pending
            if diff:
                q.append(("lv", diff))
            for e in ev:
                if e[0] != "s" or abs(e[2] - fx) < 30 and abs(e[3] - fy) < 30:
                    q.append(e)
            for p in parts:
                if abs(p.x - fx) < VIEW and abs(p.y - fy) < VIEW:
                    q.append(("p", (p.kind, p.x, p.y, p.z, p.vx, p.vy, p.vz, p.life, p.color, p.size)))
            for q_ in gibs:
                if near(q_, fx, fy):
                    q.append(("g", q_))
            for d_ in decals:
                if abs(d_[0] - fx) < VIEW and abs(d_[1] - fy) < VIEW:
                    q.append(("d", d_))
            if len(q) > 6000:                     # a guest that's stalled: keep level edits, drop old effects
                gu.pending = [e for e in q if e[0] == "lv"] + [e for e in q if e[0] != "lv"][-2000:]

    def send_snapshots(self, g):
        w = g.world
        base = {k: v for k, v in vars(w).items() if k not in EXCLUDE and k not in CULL}
        gstate = {"state": g.state if g.state != "pause" else "play", "transition": g.transition}
        acks = {gu.slot: gu.applied for gu in self.guests}
        for gu in self.guests:
            if not gu.in_game or gu.conn.closed:
                continue
            if gu.conn.backlog() > MAX_BACKLOG:
                continue
            me = next((p for p in w.players if p.idx == gu.slot), None)
            fx, fy = (me.x, me.y) if me is not None else (w.player.x, w.player.y)
            snap = dict(base)
            for k in CULL:
                snap[k] = [o for o in getattr(w, k) if near(o, fx, fy)]
            snap["_g"] = gstate
            snap["_ack"] = acks.get(gu.slot, 0)
            snap["_ev"] = gu.pending
            gu.pending = []
            try:
                raw = net.pack(snap, w)
            except Exception as ex:          # never let one odd object kill the session
                print("net: snapshot failed:", ex)
                continue
            gu.conn.send_delta("S", raw)

    # ---- per frame
    def update(self, g, dt):
        self.poll(g)
        if g.state == "lobby":
            self.update_lobby(g)
            return True
        w = g.world
        if w is not None and id(w) != self.world_id:          # a new sector (or a restart): everyone moves with us
            self.world_id = id(w)
            self.prepare(w)
            for gu in self.guests:
                if gu.hello and gu.ready:
                    if all(p.idx != gu.slot for p in w.players):
                        w.add_player(gu.char, idx=gu.slot, limit=net.MAX_PLAYERS, name=gu.name)
                    self.send_world(g, gu)
        local = g.inputs[0]
        if g.state in ("play", "pause") and "start" in local.pressed:
            g.state = "pause" if g.state == "play" else "play"
        if g.state == "pause":
            me = next((p for p in w.players if p.idx == 0), None)
            if "swap" in local.pressed:
                g.toggle_numbers()
            elif me is not None:
                g.inventory_input(me, local)
        for gu in self.guests:
            gu.input.next_frame()
        inputs = []
        for p in w.players:
            if p.idx == 0:
                inputs.append(IDLE if g.state == "pause" else local)
                continue
            gu = next((x for x in self.guests if x.slot == p.idx), None)
            if gu is None:
                inputs.append(IDLE)
            elif gu.input.menu:
                g.inventory_input(p, gu.input)
                inputs.append(IDLE)
            else:
                inputs.append(gu.input)
        self.in_update = True
        try:
            if g.state == "dead":
                w.update(dt, inputs)
                g.update_camera(dt)
                if g.time > g.dead_at + 1.5 and ("start" in local.pressed or "a" in local.pressed):
                    self.in_update = False
                    self.start_run(g)
            elif g.transition > 0:
                g.transition -= dt
                if g.transition <= 0:
                    for p in w.players:
                        p.hp = min(p.max_hp, p.hp + 25)
                    self.in_update = False
                    g.new_world(w.depth + 1, w.players, w.score)
            else:
                w.update(dt, inputs)
                g.banner = (g.banner[0], g.banner[1] - dt)
                g.update_camera(dt)
                if w.exit_reached:
                    g.transition = 0.9
                    w.snd("portal", w.player.x, w.player.y)
                if not any(p.alive for p in w.players):
                    g.state = "dead"
                    g.dead_at = g.time
                    sfx.music(None, 3000)
                    g.save_best()
        finally:
            self.in_update = False
        for gu in self.guests:
            gu.input.pressed.clear()
            gu.applied = gu.input.seq          # the inputs this frame's world has seen
        if g.world is w:
            self.collect(g)
            self.frame += 1
            if self.frame % SNAP_EVERY == 0:
                self.send_snapshots(g)
        for gu in self.guests:
            gu.conn.flush()
        return True

    def key(self, g, ev):
        """Keyboard: TAB to type a new game name, ENTER / TAB to finish, ESC to undo."""
        if g.state != "lobby":
            return False
        if ev.key == pygame.K_F1:
            net.open_link(net.TAILSCALE_SHARE if self.tailscale.state == "on" else net.TAILSCALE_DOWNLOAD)
            return True
        if self.editing_me:
            self.typed = True
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                g.player_name = net.clean_player_name(g.player_name)
                g.save_settings()
                self.editing_me = False
                self.lobby_t = 0.0
            elif ev.key == pygame.K_ESCAPE:
                g.player_name = self.before_me
                self.editing_me = False
            elif ev.key == pygame.K_BACKSPACE:
                g.player_name = g.player_name[:-1]
            elif ev.unicode and len(g.player_name) < 14 and net.name_char_ok(ev.unicode):
                g.player_name += ev.unicode
            return True
        if not self.editing:
            if ev.key == pygame.K_TAB:
                self.editing = True
                self.before = self.name
                self.name = ""
                self.typed = True
                return True
            if ev.key == pygame.K_n:
                self.editing_me = True
                self.before_me = g.player_name
                self.typed = True
                return True
            return False
        self.typed = True
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            if len(net.norm_name(self.name)) < 3:
                self.name = self.before
            self.editing = False
        elif ev.key == pygame.K_ESCAPE:
            self.name = self.before
            self.editing = False
        elif ev.key == pygame.K_BACKSPACE:
            self.name = self.name[:-1]
        elif ev.unicode and (ev.unicode.isalnum() or ev.unicode in " -") and len(self.name) < 24:
            self.name += ev.unicode.lower()
        return True

    def update_lobby(self, g):
        inp = g.inputs[0]
        if self.editing or self.editing_me or self.typed:
            self.typed = False
            return
        g.pick_char(0, inp)
        if "swap" in inp.pressed:
            self.name = net.random_name()
            sfx.play("tink", 0.6)
        if "start" in inp.pressed or "a" in inp.pressed:
            sfx.play("start")
            self.start_run(g)
        elif "deploy" in inp.pressed or "back" in inp.pressed:
            g.leave_net()

    def leave(self, g):
        for gu in self.guests:
            gu.conn.send_json("x", {"msg": "The host closed the game."})
            gu.conn.flush()
            gu.conn.close()
        self.server.close()
        sfx.router = None
        sfx.music_router = None

    # ---- screens
    def draw(self, g, s):
        if g.state != "lobby":
            return False
        g.draw_title_bg(s)
        info = self.lobby_info(g)
        g.center_text(s, g.big, "HOSTING", g.sc(58), (235, 240, 255))
        port = "" if self.server.port == net.PORT else ":%d" % self.server.port
        caret = "_" if self.editing and int(g.time * 2) % 2 == 0 else ""
        g.center_text(s, g.font, "GAME NAME  (friends type this to get in - only share it with them)", g.sc(98), (150, 170, 200))
        g.center_text(s, g.big, (self.name + caret) if (self.name or self.editing) else "-", g.sc(132),
                      (255, 230, 120) if self.editing else (120, 230, 255))
        g.center_text(s, g.font, ("type a game name, ENTER to keep it, ESC to undo" if self.editing else
                                  "TAB type your own game name   -   Y / Q new random one   -   N change YOUR name"),
                      g.sc(160), (150, 160, 180))
        self.draw_addresses(g, s, port)
        draw_lobby_players(g, s, info, 0)
        g.center_text(s, g.font, "LEFT / RIGHT your body   -   START / A begin   -   B / ESC stop hosting"
                      + ("   (guests can drop in later too)" if len(info["players"]) == 1 else ""),
                      g.H - g.sc(40), (255, 220, 120))
        g.center_text(s, g.small, "version %s - your friends need the same one" % self.version, g.H - g.sc(16), (120, 125, 140))
        return True

    def draw_addresses(self, g, s, port):
        """What to read out to friends: the game name (above), plus the address for how they're connecting."""
        x = g.W // 2 - g.sc(350)
        y = g.sc(172)
        g.panel(s, pygame.Rect(x - g.sc(12), y - g.sc(5), g.sc(724), g.sc(66)), 215)

        def line(label, text, col, hint=""):
            nonlocal y
            lab = g.font.render(label, True, (150, 160, 180))
            s.blit(lab, (x, y))
            t = g.font.render(text, True, col)
            s.blit(t, (x + g.sc(150), y))
            if hint:
                h = g.small.render(hint, True, (175, 185, 200))
                s.blit(h, (x + g.sc(160) + t.get_width(), y + g.sc(3)))
            y += g.sc(20)
        line("SAME WI-FI:", "   ".join(a + port for a in self.addresses[:2]), (170, 230, 255), "(they'll also see it listed)")
        ts = self.tailscale
        if ts.state == "on":
            line("TAILSCALE:", ts.ip + port, (120, 255, 170),
                 ("(%s)   F1: share this PC with a friend" % ts.name) if ts.name else "F1: share this PC with a friend")
        elif ts.state == "off":
            line("TAILSCALE:", "installed, not connected", (255, 200, 120), "open Tailscale and sign in")
        elif ts.state == "missing":
            line("TAILSCALE:", "not installed", (200, 205, 215), "over the internet? F1 opens %s (free)" % net.TAILSCALE_DOWNLOAD)
        else:
            line("TAILSCALE:", "checking...", (150, 155, 170))
        pub = self.public
        if pub.state == "ok":
            line("INTERNET:", pub.ip + port, (255, 230, 150), "works only if TCP port %d is forwarded to this PC" % self.server.port)
        elif pub.state == "cgnat":
            line("INTERNET:", "not reachable", (255, 160, 120),
                 "your provider shares your address (CGNAT) - use Tailscale")
        elif pub.state == "unknown":
            line("INTERNET:", "couldn't find it", (200, 205, 215), "google \"what is my IP\" on this PC")
        else:
            line("INTERNET:", "checking...", (150, 155, 170))

    def status_line(self, g):
        n = sum(1 for gu in self.guests if gu.in_game)
        return "HOSTING  -  %d guest%s" % (n, "" if n == 1 else "s") if n else ""


def draw_lobby_players(g, s, info, me):
    chars = {p["slot"]: p["char"] for p in info["players"]}
    slots = sorted(chars)
    g.draw_char_row(s, slots, g.H / 2 + g.sc(142), chars=chars)
    x0 = g.W / 2 - g.sc(330)
    for i in range(net.MAX_PLAYERS):
        p = next((q for q in info["players"] if q["slot"] == i), None)
        r = pygame.Rect(int(x0 + i * g.sc(170)), int(g.sc(240)), g.sc(150), g.sc(46))
        g.panel(s, r, 170)
        col = g.PLAYER_COLORS[i]
        if p is None:
            t = g.font.render("P%d  open" % (i + 1), True, (90, 95, 110))
            s.blit(t, t.get_rect(center=r.center))
            continue
        pygame.draw.rect(s, col, r, max(1, g.sc(2)))
        nm = p.get("name") or "P%d" % (i + 1)
        if i == me and getattr(g.net, "editing_me", False):
            nm = (g.player_name or "") + ("_" if int(g.time * 2) % 2 == 0 else " ")
        who = "%s%s%s" % (nm, "  HOST" if p["host"] else "", "  (YOU)" if i == me else "")
        t = g.font.render(who, True, col)
        s.blit(t, (r.x + g.sc(8), r.y + g.sc(6)))
        st = CH.CHARS[p["char"]]["name"] + ("" if p["ready"] else "  -  picking")
        t2 = g.small.render(st, True, (220, 225, 235) if p["ready"] else (150, 155, 170))
        s.blit(t2, (r.x + g.sc(8), r.y + g.sc(26)))


# ================================================================ guest
class GuestSession:
    is_host = False
    dt = 1 / 60

    def __init__(self, g, conn, name=""):
        self.conn = conn
        self.name = name
        self.char0 = g.chars[0]
        self.slot = None
        self.local = set()
        self.version = net.game_version()
        self.lobby = None
        self.ready = False
        self.error = None
        self.last_rx = time.monotonic()
        self.dead_seen = False
        self.seq = 0
        self.history = []             # (input number, move, dt) not yet confirmed by the host
        g.state = "clobby"            # the hello goes out once the host sends its challenge

    def poll(self, g):
        for kind, payload in self.conn.poll():
            self.last_rx = time.monotonic()
            if kind == "n":
                nonce = net.read_json(payload).get("nonce", "")
                self.conn.send_json("h", {"v": self.version, "char": self.char0, "p": net.name_proof(self.name, nonce),
                                          "name": g.player_name})
            elif kind == "w":
                d = net.read_json(payload)
                self.slot = int(d.get("slot", 1))
                self.local = {self.slot}
            elif kind == "l":
                self.lobby = net.read_json(payload)
            elif kind == "x":
                self.error = net.read_json(payload).get("msg", "Disconnected.")
            elif kind == "W":
                try:
                    self.load_world(g, net.unpack(zlib.decompress(payload), None))
                except Exception as ex:
                    self.error = "Couldn't load the host's world (%s)." % ex.__class__.__name__
                    self.conn.close("bad world")
            elif kind == "S" and g.world is not None:
                try:
                    snap = net.unpack(self.conn.read_delta(payload), g.world)
                except Exception as ex:
                    self.error = "Lost sync with the host (%s)." % ex.__class__.__name__
                    self.conn.close("bad snapshot")
                    break
                self.apply(g, snap)
        if self.conn.closed and self.error is None:
            self.error = "Lost connection to the host."

    def load_world(self, g, state):
        w = World.__new__(World)
        w.__dict__.update(state)
        w.particles, w.gibs, w.decals = [], [], []
        w.grid, w.flow, w.flow_tile = {}, None, None
        w.blocked, w.actor, w.net_events = set(), None, None
        w.explore_dirty = [(i % w.level.W, i // w.level.W) for i in range(len(w.explored)) if w.explored[i]]
        w.local_idx = set(self.local)
        w.free_roam = True
        w.show_numbers = g.damage_numbers
        self.conn.zprev = b""
        g.world = w
        g.biome = w.biome
        g.transition = 0.0
        g.setup_view()
        g.state = "play"
        self.dead_seen = False

    def apply(self, g, snap):
        w = g.world
        for k, v in snap.items():
            if not k.startswith("_"):
                setattr(w, k, v)
        L = w.level
        for e in snap.get("_ev", ()):
            k = e[0]
            if k == "p":
                if len(w.particles) < 900:
                    w.particles.append(Particle(*e[1]))
            elif k == "g":
                w.gibs.append(e[1])
                if len(w.gibs) > 220:
                    del w.gibs[:len(w.gibs) - 220]
            elif k == "d":
                w.decals.append(e[1])
            elif k == "s":
                _, name, x, y, vol = e
                me = self.me(w)
                d = math.hypot(x - me.x, y - me.y) if me is not None else 0
                sfx.play(name, vol * max(0.15, min(1.0, 1.25 - d / 12)))
            elif k == "u":
                if e[3] < 0 or e[3] in self.local:
                    sfx.play(e[1], e[2])
            elif k == "m":
                sfx.music(e[1], e[2])
            elif k == "lv":
                d = e[1]
                for i, so, fl, wk in d.get("cells", ()):
                    L.solid[i], L.floor[i], L.wallkind[i] = so, fl, wk
                    L.changed.append((i % L.W, i // L.W))
                for pos, name in d.get("props", {}).items():
                    if name is None:
                        L.props.pop(pos, None)
                    else:
                        L.props[pos] = name
                    L.changed.append(pos)
                for i in d.get("expl", ()):
                    w.explored[i] = 1
                    w.explore_dirty.append((i % L.W, i // L.W))
        gs = snap.get("_g", {})
        st = gs.get("state", "play")
        g.transition = gs.get("transition", 0.0)
        if st == "dead":
            if g.state != "dead":
                g.state = "dead"
                g.dead_at = g.time
                sfx.music(None, 3000)
        elif g.state == "dead":
            g.state = "play"
        self.reconcile(g, snap.get("_ack", 0))
        self.fix_aim(g)

    # ---- prediction: your own body moves the moment you push the stick
    def step(self, w, p, move, dt):
        """The host's walking rule for one frame (knockback / dashes are left to the host's corrections)."""
        mx, my = move
        if "confuse" in p.status:
            mx, my = -mx, -my
        mag = min(1.0, math.hypot(mx, my)) * (0.5 if "chill" in p.status else 1.0) * (0.55 if "mire" in p.status else 1.0)
        if mag <= 0.15 or not p.alive:
            return False
        wx, wy = screen_to_world_dir(mx, my)
        spd = p.SPEED * CH.CHARS[p.char]["speed"] * mag * p.mult("haste") * p.weapon.st.get("heavy", 1.0)
        ox, oy = p.x, p.y
        p.x, p.y = resolve(w.level, p.x + wx * spd * dt, p.y + wy * spd * dt, p.R)
        p.legs_dir = dir_index(wx, wy, 8)
        p.walk += math.hypot(p.x - ox, p.y - oy)
        return True

    def reconcile(self, g, ack):
        """Start from where the host says you are, then replay the moves it hasn't seen yet."""
        self.history = [h for h in self.history if h[0] > ack]
        me = self.me(g.world)
        if me is None or g.state not in ("play", "pause"):
            return
        for _, move, dt in self.history:
            if self.step(g.world, me, move, dt):
                me.moving = True

    def me(self, w):
        return next((p for p in w.players if p.idx in self.local), None)

    def fix_aim(self, g):
        """Your gun points where you're aiming right now, not where the host last heard."""
        me = self.me(g.world) if g.world else None
        a = g.inputs[0].aim
        if me is not None and a is not None and g.state == "play":
            me.aim = screen_to_world_dir(*a)

    def send_input(self, g):
        inp = g.inputs[0]
        menu = g.state == "pause"
        pressed = sorted(inp.pressed - {"start"})
        self.seq += 1
        move = (0.0, 0.0) if menu else (round(inp.move[0], 3), round(inp.move[1], 3))
        self.history.append((self.seq, move, self.dt))
        if len(self.history) > 240:
            del self.history[:-240]
        self.conn.send_json("i", {"s": self.seq, "m": list(move),
                                  "a": [round(inp.aim[0], 2), round(inp.aim[1], 2)] if inp.aim else None,
                                  "f": bool(inp.fire) and not menu, "p": pressed, "menu": menu})

    def update(self, g, dt):
        self.poll(g)
        if self.error:
            g.net_error(self.error)
            return True
        if g.state == "clobby":
            self.update_lobby(g)
            self.conn.flush()
            return True
        inp = g.inputs[0]
        if "start" in inp.pressed and g.state in ("play", "pause"):
            g.state = "pause" if g.state == "play" else "play"
        if g.state == "pause" and "swap" in inp.pressed:
            g.toggle_numbers()
            inp.pressed.discard("swap")
        self.dt = dt
        self.send_input(g)
        w = g.world
        if w is not None:
            self.tick(g, w, dt)
        self.conn.flush()
        return True

    def tick(self, g, w, dt):
        """Between snapshots: move what's flying, run the cosmetic effects, keep the camera moving."""
        L = w.level
        for b in w.projs:
            nx, ny = b.x + b.vx * dt, b.y + b.vy * dt
            if 0 <= nx < L.W and 0 <= ny < L.H and L.solid[int(ny) * L.W + int(nx)] != 1:
                b.x, b.y = nx, ny
        for q in w.gibs:
            q.update(w, dt)
        w.particles = [q for q in w.particles if q.update(w, dt)]
        w.shake = max(0.0, w.shake - dt * 30)
        w.hurt_flash = max(0.0, w.hurt_flash - dt)
        for m in w.messages:
            m[2] -= dt
        g.banner = (g.banner[0], g.banner[1] - dt)
        me = self.me(w)
        if me is not None and self.history and g.state == "play":
            me.moving = self.step(w, me, self.history[-1][1], dt)
        self.fix_aim(g)
        if g.state == "play" and g.transition <= 0:
            w.sound_loops()
        else:
            sfx.stop_loops()
        if w.players:
            g.update_camera(dt)

    def update_lobby(self, g):
        inp = g.inputs[0]
        before = g.chars[0]
        g.pick_char(0, inp)
        changed = g.chars[0] != before
        if ("a" in inp.pressed or "start" in inp.pressed) and not self.ready and self.slot is not None:
            self.ready = True
            changed = True
            sfx.play("start")
        if changed:
            self.conn.send_json("c", {"char": g.chars[0], "ready": self.ready, "name": g.player_name})
        if "deploy" in inp.pressed or "back" in inp.pressed:
            g.leave_net()

    def leave(self, g):
        if not self.conn.closed:
            self.conn.send_json("q", {})
            self.conn.flush()
            self.conn.close()

    def draw(self, g, s):
        if g.state != "clobby":
            return False
        g.draw_title_bg(s)
        g.center_text(s, g.big, "JOINED", g.sc(70), (235, 240, 255))
        lob = self.lobby or {"players": [], "state": "lobby"}
        if self.slot is None:
            g.center_text(s, g.mid, "Talking to the host...", g.sc(140), (150, 170, 200))
        else:
            mine = {"slot": self.slot, "char": g.chars[0], "ready": self.ready, "host": False, "name": g.player_name}
            info = dict(lob, players=[p for p in lob.get("players", []) if p["slot"] != self.slot] + [mine])
            draw_lobby_players(g, s, info, self.slot)
            if lob.get("state") == "play":
                msg = "Game in progress (sector %d): pick a body and press A to drop in" % lob.get("depth", 1)
            elif self.ready:
                msg = "Ready - waiting for the host to start"
            else:
                msg = "Pick a body, then press A when you're ready"
            g.center_text(s, g.mid, msg, g.sc(140), (120, 230, 255))
        g.center_text(s, g.font, "LEFT / RIGHT your body   -   A ready   -   B / ESC leave", g.H - g.sc(40), (255, 220, 120))
        return True

    def status_line(self, g):
        quiet = time.monotonic() - self.last_rx
        return "Waiting for the host..." if quiet > 1.5 else ""


# ================================================================ join screen
class JoinScreen:
    """LAN games found automatically, an address box and a game-name box.
    Rows: one per LAN game, then ADDRESS, then GAME NAME."""
    is_host = False
    local = set()
    games = []

    def __init__(self, g):
        self.finder = net.Finder()
        self.addr = g.last_host or ""
        self.name = getattr(g, "last_name", "") or ""
        self.sel = 0
        self.connector = None
        self.error = None
        self.typed = False
        self.tailscale = net.TailscaleProbe()
        g.state = "netjoin"

    @property
    def addr_row(self):
        return len(self.games)

    @property
    def name_row(self):
        return len(self.games) + 1

    @property
    def me_row(self):
        return len(self.games) + 2

    def key(self, g, ev):
        """Keyboard typing into the address / game-name boxes. Returns True if the key was used here."""
        if ev.key == pygame.K_F1:
            net.open_link(net.TAILSCALE_DOWNLOAD)
            return True
        if self.connector is not None or ev.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_ESCAPE):
            return False                  # arrows move through the rows as menu presses; ESC leaves
        self.typed = True                 # a typed letter also shows up as a menu press (W, S, F...) this frame: ignore that
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            self.advance(g)
            return True
        if self.sel == self.me_row:
            if ev.key == pygame.K_BACKSPACE:
                g.player_name = g.player_name[:-1]
            elif ev.unicode and len(g.player_name) < 14 and net.name_char_ok(ev.unicode):
                g.player_name += ev.unicode
            return True
        field = "name" if self.sel != self.addr_row else "addr"
        if self.sel < self.addr_row:      # typing while a listed game is picked: that's the name
            self.sel = self.name_row
        text = getattr(self, field)
        if ev.key == pygame.K_BACKSPACE:
            text = text[:-1]
        elif ev.unicode and len(text) < 40 and (ev.unicode.isalnum() or ev.unicode in (".:-[]_" if field == "addr" else " -")):
            text += ev.unicode
        setattr(self, field, text)
        return True

    def advance(self, g):
        """A / ENTER: a listed game fills the address; the address box moves on to the name; the name box joins."""
        if self.sel < self.addr_row:
            ip, (info, _) = self.games[self.sel]
            port = info.get("port", net.PORT)
            self.addr = ip if port == net.PORT else "%s:%d" % (ip, port)
            self.sel = self.name_row
            if not self.name.strip():
                return
        elif self.sel == self.addr_row:
            self.sel = self.name_row
            if not self.name.strip():
                return
        elif self.sel == self.me_row:
            self.sel = self.name_row
        if not self.addr.strip():
            self.error = "Type the host's address first."
            self.sel = self.addr_row
        elif len(net.norm_name(self.name)) < 3:
            self.error = "Type the game name the host gave you."
            self.sel = self.name_row
        else:
            self.connect(g)

    def connect(self, g):
        self.error = None
        self.connector = net.Connector(self.addr.strip())
        if self.connector.error:
            self.error = self.connector.error
            self.connector = None
            return
        if not any(self.addr.strip().split(":")[0] == ip for ip, _ in self.games):
            g.last_host = self.addr.strip()
        g.last_name = self.name.strip()
        g.player_name = net.clean_player_name(g.player_name)
        g.save_settings()

    def update(self, g, dt):
        self.games = self.finder.poll()
        self.sel = min(self.sel, self.me_row)
        inp = g.inputs[0]
        pressed = set() if self.typed else inp.pressed
        self.typed = False
        if self.connector is not None:
            conn = self.connector.poll()
            if conn is not None:
                self.finder.close()
                g.net = GuestSession(g, conn, self.name.strip())
            elif self.connector.error:
                self.error = self.connector.error
                self.connector = None
            if "deploy" in pressed or "back" in pressed:
                self.connector = None
            return True
        n = self.me_row + 1
        if "nav_up" in pressed:
            self.sel = (self.sel - 1) % n
        if "nav_down" in pressed:
            self.sel = (self.sel + 1) % n
        if "a" in pressed or "start" in pressed:
            self.advance(g)
        if "deploy" in pressed or "back" in pressed:
            g.leave_net()
        return True

    def box(self, g, s, y, label, text, on, secret_hint=""):
        r = pygame.Rect(0, 0, g.sc(420), g.sc(38))
        r.center = (g.W // 2 + g.sc(60), int(y))
        lab = g.font.render(label, True, (255, 230, 120) if on else (150, 160, 180))
        s.blit(lab, (r.x - lab.get_width() - g.sc(14), r.centery - lab.get_height() // 2))
        g.panel(s, r, 220)
        pygame.draw.rect(s, (255, 230, 120) if on else (90, 95, 110), r, max(2, g.sc(3)))
        caret = "_" if on and int(g.time * 2) % 2 == 0 else " "
        t = g.mid.render((text or "") + caret, True, (255, 255, 255))
        s.blit(t, t.get_rect(center=r.center))
        if secret_hint and not text:
            h = g.small.render(secret_hint, True, (110, 115, 130))
            s.blit(h, h.get_rect(center=r.center))

    def draw(self, g, s):
        g.draw_title_bg(s)
        g.center_text(s, g.big, "JOIN NET GAME", g.sc(70), (235, 240, 255))
        y = g.sc(124)
        g.center_text(s, g.font, "Games on your network:" if self.games else "Looking for games on your network...",
                      y, (150, 170, 200))
        y += g.sc(30)
        for i, (ip, (info, _)) in enumerate(self.games):
            on = i == self.sel
            txt = "%s   -   %d player%s   -   %s" % (ip, info.get("n", 1), "" if info.get("n", 1) == 1 else "s",
                                                    "in lobby" if info.get("state") == "lobby" else "sector %d" % info.get("depth", 1))
            if info.get("v") != net.game_version():
                txt += "   (different version)"
            r = pygame.Rect(0, 0, g.sc(560), g.sc(32))
            r.center = (g.W // 2, int(y))
            g.panel(s, r, 200 if on else 120)
            if on:
                pygame.draw.rect(s, (255, 230, 120), r, max(2, g.sc(3)))
            t = g.font.render(txt, True, (255, 255, 255) if on else (170, 175, 190))
            s.blit(t, t.get_rect(center=r.center))
            y += g.sc(38)
        y += g.sc(20)
        self.box(g, s, y, "ADDRESS", self.addr, self.sel == self.addr_row, "host's address (or pick a listed game)")
        y += g.sc(50)
        self.box(g, s, y, "GAME NAME", self.name, self.sel == self.name_row, "the name the host gave you")
        y += g.sc(50)
        self.box(g, s, y, "YOUR NAME", g.player_name, self.sel == self.me_row, "what the others see (optional)")
        y += g.sc(46)
        if self.connector is not None:
            g.center_text(s, g.mid, "Connecting to %s:%d ..." % (self.connector.host, self.connector.port), y, (120, 230, 255))
        elif self.error:
            g.center_text(s, g.font, self.error, y, (255, 140, 120))
        ts = self.tailscale.state
        tip = {"on": "Tailscale is connected on this PC - type the host's Tailscale address (100.x.x.x)",
               "off": "Tailscale is installed but not connected - open it and sign in to play over the internet",
               "missing": "Playing over the internet? You both install Tailscale (free) - F1 opens " + net.TAILSCALE_DOWNLOAD,
               }.get(ts, "")
        if tip:
            g.center_text(s, g.small, tip, g.H - g.sc(70), (120, 255, 170) if ts == "on" else (150, 165, 185))
        g.center_text(s, g.font, "UP / DOWN choose   -   type with the keyboard   -   A / ENTER next / join   -   B / ESC back",
                      g.H - g.sc(40), (255, 220, 120))
        return True

    def leave(self, g):
        self.finder.close()

    def status_line(self, g):
        return ""

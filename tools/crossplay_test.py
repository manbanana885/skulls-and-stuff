"""Cross-play: a PC host and a Raspberry Pi edition guest in one net game, as two separate processes.

    python tools/make_pi_package.py           (once - builds pi_package/ with the half-size sprites)
    python tools/crossplay_test.py [outdir]

The host runs from this folder (full-size sprites, HIGH demand). The guest runs from pi_package/ (half-size sprites,
960 x 540, LOW demand as a Pi would default to), with this folder's current code copied in first. They talk over a
real localhost socket. Checks: the Pi joins, the session drops to LOW, the guest gets the world, moves, shoots and
sees monsters, and neither side errors."""
import os
import sys
import json
import time
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "pi_package", "skulls-and-stuff")
PORT = 47911


def run_role(role, game_dir, out):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["SKULLS_SAVE"] = os.devnull
    os.environ["SKULLS_OFFLINE"] = "1"
    sys.path.insert(0, game_dir)
    import pygame
    import main
    import netplay as NP
    import perf
    import assets

    class Bot:
        move = (0.0, 0.0)
        aim = None
        fire = False
        keyboard = False
        mouse_mode = False
        dev = None
        device_name = None

        def __init__(self):
            self.pressed = set()
            self.pending = set()

        def poll(self, ps):
            pass

        def set_device(self, d):
            pass

    g = main.Game(windowed=True)
    bot = Bot()
    g.inputs = [bot]
    g.spare = {}
    name_file = os.path.join(out, "game_name.txt")
    res = {"role": role, "tile_w": assets.TILE_W, "screen": list(g.screen.get_size()), "demand": perf.local}

    def step(n=1):
        for _ in range(n):
            g.update(1 / 60)
            bot.pressed = set()
            time.sleep(1 / 120)

    if role == "host":
        g.net = NP.HostSession(g, PORT)
        with open(name_file, "w") as fh:
            fh.write(g.net.name)
        t0 = time.time()
        while time.time() - t0 < 40 and not any(gu.ready for gu in g.net.guests):
            step()
        res["guest_ready"] = any(gu.ready for gu in g.net.guests)
        res["guest_demand"] = [gu.demand for gu in g.net.guests]
        res["session_mode"] = g.net.session_mode()
        bot.pressed = {"a"}
        step()
        res["sim"] = perf.sim
        res["enemies"] = len(g.world.enemies) if g.world else 0
        t0 = time.time()
        track = []                            # where the host has the guest's player, on the shared wall clock
        snap_done = False
        while time.time() - t0 < 16.0:        # stay up until the guest has finished
            step()
            gp = next((p for p in g.world.players if p.idx != 0), None)
            if gp and (not track or time.time() - track[-1][0] > 0.1):
                track.append((time.time(), gp.x, gp.y))
            if not snap_done and time.time() - t0 > 4.0:
                snap_done = True
                res["guests_in_game"] = sum(1 for gu in g.net.guests if gu.in_game)
                res["players"] = len(g.world.players)
                g.draw()
                pygame.image.save(g.screen, os.path.join(out, "host_view.png"))
        res["track"] = track
        g.leave_net()
    else:
        t0 = time.time()
        while not os.path.exists(name_file) and time.time() - t0 < 20:
            time.sleep(0.1)
        g.net = NP.JoinScreen(g)
        g.net.addr = "127.0.0.1:%d" % PORT
        g.net.name = open(name_file).read().strip()
        g.player_name = "Pi"
        g.net.connect(g)
        t0 = time.time()
        while time.time() - t0 < 15 and not (isinstance(g.net, NP.GuestSession) and g.net.slot is not None):
            step()
        res["joined"] = isinstance(g.net, NP.GuestSession) and g.net.slot is not None
        bot.pressed = {"a"}
        step()
        t0 = time.time()
        while time.time() - t0 < 20 and (g.world is None or g.state != "play"):
            step()
        res["got_world"] = g.world is not None and g.state == "play"
        me = next((p for p in g.world.players if p.idx == g.net.slot), None) if g.world else None
        x0, y0 = (me.x, me.y) if me else (0, 0)
        bot.move = (1.0, 0.0)
        bot.aim = (300.0, -40.0)
        bot.fire = True
        t0 = time.time()
        seen = 0
        gtrack = []
        while time.time() - t0 < 6:
            step()
            if g.world:
                seen = max(seen, len(g.world.enemies))
                m_ = next((p for p in g.world.players if p.idx == g.net.slot), None)
                if m_ and (not gtrack or time.time() - gtrack[-1][0] > 0.1):
                    gtrack.append((time.time(), m_.x, m_.y))
        res["track"] = gtrack
        bot.move, bot.fire = (0.0, 0.0), False
        me = next((p for p in g.world.players if p.idx == g.net.slot), None) if g.world else None
        res["moved"] = round(((me.x - x0) ** 2 + (me.y - y0) ** 2) ** 0.5, 2) if me else 0
        res["enemies_seen"] = seen
        res["projectiles_now"] = len(g.world.projs) if g.world else 0
        res["still_connected"] = isinstance(g.net, NP.GuestSession) and not g.net.conn.closed
        g.draw()
        pygame.image.save(g.screen, os.path.join(out, "pi_guest_view.png"))
        step(480)
    print("RESULT " + json.dumps(res))


def main_():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_crossplay_test"))
    os.makedirs(out, exist_ok=True)
    if not os.path.isdir(PKG):
        sys.exit("No Pi package: run  python tools/make_pi_package.py  first")
    for f in os.listdir(os.path.join(ROOT, "game")):        # the Pi copy gets today's code (net play compares it)
        if f.endswith(".py"):
            shutil.copy2(os.path.join(ROOT, "game", f), os.path.join(PKG, "game", f))
    nf = os.path.join(out, "game_name.txt")
    if os.path.exists(nf):
        os.remove(nf)
    me = os.path.abspath(__file__)
    env_h = dict(os.environ, SKULLS_DEMAND="high")
    env_g = dict(os.environ, SKULLS_DEMAND="low")
    host = subprocess.Popen([sys.executable, me, "--role", "host", os.path.join(ROOT, "game"), out], env=env_h,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(3)
    gdir = os.path.join(ROOT, "game") if os.environ.get("XP_SAME") else os.path.join(PKG, "game")
    guest = subprocess.Popen([sys.executable, me, "--role", "guest", gdir, out], env=env_g,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ho, _ = host.communicate(timeout=180)
    go, _ = guest.communicate(timeout=180)
    res = {}
    for name, text in (("host", ho), ("guest", go)):
        line = next((ln for ln in text.splitlines() if ln.startswith("RESULT ")), None)
        if line is None or "Traceback" in text:
            print("---- %s output ----\n%s" % (name, text[-3000:]))
        res[name] = json.loads(line[7:]) if line else {}
    h, gst = res["host"], res["guest"]
    print("host : %s" % h)
    print("guest: %s" % gst)
    fails = []

    def check(ok, msg):
        print(("  ok   " if ok else "  FAIL ") + msg)
        if not ok:
            fails.append(msg)
    check(h.get("tile_w") == 128 and gst.get("tile_w") == 64, "PC draws 128-px tiles, the Pi edition 64-px (%s / %s)"
          % (h.get("tile_w"), gst.get("tile_w")))
    check(gst.get("joined"), "the Pi edition joins the PC's game")
    check(h.get("guest_demand") == ["low"] and h.get("session_mode") == "low" and h.get("sim") == "low",
          "the Pi's LOW setting brings the whole session to LOW")
    check(gst.get("got_world"), "the Pi receives the world and plays")
    check(gst.get("moved", 0) > 2, "the Pi player walks (%.1f tiles in 6 s)" % gst.get("moved", 0))
    check(gst.get("enemies_seen", 0) > 0, "the Pi sees the host's monsters (%s)" % gst.get("enemies_seen"))
    check(gst.get("still_connected"), "still connected at the end")
    check(h.get("guests_in_game") == 1 and h.get("players") == 2, "the host has both players in the world")
    ht, gt = h.get("track", []), gst.get("track", [])
    gaps = []
    for t, x, y in gt:                       # the same moment on both machines: where does each think the Pi player is?
        near = min(ht, key=lambda r: abs(r[0] - t), default=None)
        if near and abs(near[0] - t) < 0.12:
            gaps.append(((near[1] - x) ** 2 + (near[2] - y) ** 2) ** 0.5)
    gaps.sort()
    walked = sum(((b[1] - a[1]) ** 2 + (b[2] - a[2]) ** 2) ** 0.5 for a, b in zip(ht, ht[1:]))
    print("  Pi player: walked %.1f tiles on the PC's screen; PC vs Pi position gap median %.2f, worst %.2f tiles (%d samples)"
          % (walked, gaps[len(gaps) // 2] if gaps else -1, gaps[-1] if gaps else -1, len(gaps)))
    check(walked > 2, "the Pi player's walking shows up on the PC")
    check(gaps and gaps[len(gaps) // 2] < 0.6, "both machines agree where the Pi player is")
    for nm in ("host_view.png", "pi_guest_view.png"):
        print("  screenshot:", os.path.join(out, nm))
    print("FAILED: %d" % len(fails) if fails else "all cross-play checks passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--role":
        run_role(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        main_()

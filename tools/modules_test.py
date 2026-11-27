"""The 12 newer modules, each exercised headless with a pass/fail check and a screenshot.
python tools/modules_test.py <outdir>"""
import os
import sys
import math
import random
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SKULLS_SAVE"] = os.devnull        # never touch the player's save.json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import weapons as WP  # noqa: E402
import support as SU  # noqa: E402
from world import Enemy, Proj, Loot  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(8)
g = main.Game(windowed=True)


class Bot:
    move = (0.0, 0.0)
    aim = None
    fire = False
    pressed = set()
    pending = set()
    device_name = None
    keyboard = True
    mouse_mode = False
    dev = None

    def poll(self, ps):
        pass


bot = Bot()
g.inputs = [bot]
g.spare = {}
main.biome_for = lambda d, s: "facility"
fails = []


def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fails.append(what)


def fresh(players=1):
    g.inputs = [bot] + [Bot() for _ in range(players - 1)]
    g.new_world(2)
    g.state = "play"
    g.banner = ("", 0)
    w = g.world
    w.traps, w.enemies, w.spawners, w.bosses, w.loot, w.shootables = [], [], [], [], [], []
    L = w.level
    p = w.player
    cx, cy = int(L.start[0]), int(L.start[1])
    for x in range(max(1, cx - 9), min(L.W - 1, cx + 10)):      # clean 19x19 arena
        for y in range(max(1, cy - 9), min(L.H - 1, cy + 10)):
            i = L.i(x, y)
            L.solid[i] = 0
            L.floor[i] = L.floor[i] or L.floor[L.i(cx, cy)]
    L.props = {}
    w.barrels, w.crates = {}, {}
    L.exit = (-50.0, -50.0)
    g.floor_layer.chunks.clear()
    for k, q in enumerate(w.players):
        q.x, q.y = cx + 0.5 + k * 1.5, cy + 0.5
        q.invuln = 0
    g.cam = list(g.cam_target())
    bot.move, bot.aim, bot.fire, bot.pressed = (0.0, 0.0), None, False, set()
    return w, p


def mon(w, x, y, hp=1e6, kind="zombie"):
    e = Enemy(kind, x, y, awake=True, depth=1)
    e.hp = hp
    w.enemies.append(e)
    return e


def run(sec, pin=(), shot=None, at=None, keep_hp=None):
    frames = int(sec * 60)
    for f in range(frames):
        for e in pin:
            e.x, e.y, e.vx, e.vy, e.lunge = e._px, e._py, 0, 0, 0
        g.update(1 / 60)
        if keep_hp is not None:
            keep_hp.hp = max(keep_hp.hp, 1)
        if shot and f == (at if at is not None else frames // 2):
            g.draw()
            pygame.image.save(g.screen, os.path.join(out, shot + ".png"))


def pinned(w, spots, **kw):
    ms = []
    for x, y in spots:
        e = mon(w, x, y, **kw)
        e._px, e._py = x, y
        ms.append(e)
    return ms


def module(p, kind, rarity=2, seed=1, elem=None):
    m = SU.generate(2, random.Random(seed), kind=kind, rarity=rarity)
    if elem:
        m.elem = elem
        m.label = SU.ELEMENT_LABEL[elem]
        m.tint = SU.ELEMENT_COLOR.get(elem, m.tint)
    p.give(m)
    return m


def dealt(ms):
    return [round(1e6 - e.hp, 1) for e in ms]


try:
    # ---- gun arm: fires the stowed gun at its own target, the gun in hand stays idle
    w, p = fresh()
    p.weapons = [WP.generate(1, arch="pistol", rarity=0), WP.generate(1, arch="carbine", rarity=0)]
    arm = module(p, "gunarm")
    ms = pinned(w, [(p.x + 4, p.y + 1.5)])
    a0, h0 = p.weapons[1].ammo, p.weapons[0].ammo
    run(3, ms, "mod_gunarm")
    print("  gunarm: monster took %s, stowed carbine ammo %d -> %d, pistol ammo %d -> %d"
          % (dealt(ms), a0, p.weapons[1].ammo, h0, p.weapons[0].ammo))
    check(dealt(ms)[0] > 0 and p.weapons[0].ammo == h0, "gun arm shoots monsters with the stowed gun")
    p.weapons[1] = WP.generate(1, arch="barrage", rarity=0)
    w.enemies = []
    ms = pinned(w, [(p.x + 5, p.y)])
    arm.target = None
    run(2.5, ms)
    check(dealt(ms)[0] > 0, "gun arm can fire barrage salvos (dealt %s)" % dealt(ms))

    # ---- bile leech: drains monsters into you
    w, p = fresh()
    lc = module(p, "leech")
    ms = pinned(w, [(p.x + 2, p.y), (p.x - 1.5, p.y + 1), (p.x, p.y - 2.2)])
    p.hp = 40
    run(3, ms, "mod_leech")
    print("  leech: %d tongues, monsters took %s, player hp 40 -> %.1f" % (lc.p["latches"], dealt(ms), p.hp))
    check(sum(1 for d in dealt(ms) if d > 0) == min(3, lc.p["latches"]) and p.hp > 40, "leech latches, drains and heals")

    # ---- retaliation core, each element
    for elem in ("blast", "magnet", "storm"):
        w, p = fresh()
        core = module(p, "core", elem=elem)
        ms = pinned(w, [(p.x + 1.5, p.y), (p.x - 1.2, p.y + 1), (p.x, p.y + 2)])
        shot_ = Proj("orb", p.x + 1.5, p.y - 1.5, 1.0, -3, 3, 5, hostile=True, life=3, r=0.13)
        w.projs.append(shot_)
        p.hp = p.max_hp = 1000
        run(0.2, ms)
        w.hurt_player(10, p.x + 1, p.y)
        run(0.3, ms, "mod_core_" + elem, at=2)
        print("  core/%s: monsters took %s, cooldown %.1fs, enemy shot reflected: %s" % (elem, dealt(ms), core.cd, not shot_.hostile))
        ok = sum(dealt(ms)) > 0 and core.cd > 0
        if elem == "magnet":
            ok = ok and not shot_.hostile
        check(ok, "retaliation core (%s) fires when hit" % elem)
        before = sum(dealt(ms))
        p.invuln = 0
        w.hurt_player(10, p.x + 1, p.y)
        run(0.2, ms)
        check(sum(dealt(ms)) - before < 1e-6 or elem == "storm" and False, "core respects its cooldown (%s)" % elem)

    # ---- skull familiar
    w, p = fresh()
    sk = module(p, "skull")
    ms = pinned(w, [(p.x + 5, p.y + 1)])
    states = set()
    for f in range(240):
        run(1 / 60, ms)
        states.add(sk.state)
        if f == 40:
            g.draw()
            pygame.image.save(g.screen, os.path.join(out, "mod_skull.png"))
    print("  skull: monster took %s, states seen %s" % (dealt(ms), sorted(states)))
    check(dealt(ms)[0] > 0 and {"dive", "reform"} <= states, "skull dives, explodes and reforms")

    # ---- decoy projector
    w, p = fresh()
    dc = module(p, "decoy")
    ms = [mon(w, p.x + 2 + k * 0.3, p.y + (k - 2) * 0.6, hp=1e6) for k in range(5)]
    run(0.3)
    print("  decoy: active %s, monsters targeting it %d/5" % (bool(w.decoys), sum(1 for e in ms if getattr(e.target, "decoy", False))))
    check(bool(w.decoys) and all(getattr(e.target, "decoy", False) for e in ms), "decoy deploys when swarmed and monsters chase it")
    hp0 = p.hp
    bot.move = (-1.0, 0.0)
    run(1.2, shot="mod_decoy", at=30)
    bot.move = (0.0, 0.0)
    check(p.hp == hp0, "monsters mauling the decoy don't hurt the player (hp %.0f -> %.0f)" % (hp0, p.hp))

    # ---- mine spine
    w, p = fresh()
    mn = module(p, "mines")
    bot.move = (1.0, 0.0)
    run(2.5)
    bot.move = (0.0, 0.0)
    n_mines = len(mn.mines)
    mines_at = [(m_[0], m_[1]) for m_ in mn.mines]
    ms = pinned(w, mines_at[:1])
    run(0.8, ms, "mod_mines", at=10)
    print("  mines: dropped %d (max %d, spacing %.1f), monster on a mine took %s" % (n_mines, mn.p["max"], mn.p["spacing"], dealt(ms)))
    check(n_mines >= 1 and dealt(ms)[0] > 0, "mines are sown while walking and blow up monsters")

    # ---- aura emitter, each element
    for elem in ("burn", "chill", "rad"):
        w, p = fresh()
        au = module(p, "aura", elem=elem)
        ms = pinned(w, [(p.x + 1.0, p.y), (p.x + 6, p.y)])
        run(2, ms, "mod_aura_" + elem)
        d = dealt(ms)
        print("  aura/%s: inside took %.1f, outside took %.1f" % (elem, d[0], d[1]))
        check(d[0] > 0 and d[1] == 0, "aura (%s) hurts only what's inside it" % elem)

    # ---- bone battery
    w, p = fresh()
    bb = module(p, "battery", elem="revive")
    for _ in range(bb.p["capacity"]):
        e = mon(w, p.x + 3, p.y, hp=1)
        w.hit_enemy(e, 5, 1, 0, {})
    check(bb.charge == bb.p["capacity"], "kills charge the battery (%d/%d)" % (bb.charge, bb.p["capacity"]))
    w.hurt_player(999, p.x + 1, p.y)
    check(p.alive and p.hp > 0 and bb.charge == 0, "a charged revive battery brings you back (hp %.0f)" % p.hp)
    w, p = fresh()
    bb = module(p, "battery", elem="nova")
    ms = pinned(w, [(p.x + 2, p.y)])
    for _ in range(bb.p["capacity"]):
        e = mon(w, p.x + 8, p.y, hp=1)
        w.hit_enemy(e, 5, 1, 0, {})
    run(0.2, ms, "mod_battery", at=1)
    check(dealt(ms)[0] > 0 and bb.charge == 0, "a full nova battery detonates (dealt %s)" % dealt(ms))

    # ---- autoloader
    def reload_time(with_mod):
        w, p = fresh()
        p.weapons = [WP.generate(1, arch="assault", rarity=0), WP.generate(1, arch="shotgun", rarity=0)]
        al = module(p, "autoloader") if with_mod else None
        p.weapon.ammo = 0
        p.weapons[1].ammo = 0
        p.weapon.start_reload()
        t = 0.0
        while p.weapon.reload_t > 0 and t < 10:
            g.update(1 / 60)
            t += 1 / 60
        run(4)
        return t, p.weapons[1].ammo, p.weapons[1].st["mag"], al
    t0, s0, _, _ = reload_time(False)
    t1, s1, mag, al = reload_time(True)
    print("  autoloader: reload %.2fs -> %.2fs (x%.2f), stowed shotgun %d -> %d/%d" % (t0, t1, al.p["reload"], s0, s1, mag))
    check(t1 < t0 * 0.95 and s1 == mag and s0 == 0, "autoloader speeds reloads and refills the stowed gun")

    # ---- jump jets
    w, p = fresh()
    jj = module(p, "jets", rarity=4)
    ms = pinned(w, [(p.x + 1.5, p.y + 0.0)])
    x0 = p.x
    aim_v = (1.0, 0.0)
    p.aim = aim_v
    bot.aim = None
    bot.pressed = {"dash"}
    g.update(1 / 60)
    bot.pressed = set()
    run(0.6, ms, "mod_jets", at=4)
    moved = p.x - x0
    print("  jets: dashed %.1f tiles (rolled %.1f), cooldown %.1fs, trail hit %s" % (moved, jj.p["dist"], jj.cd, dealt(ms)))
    check(moved > jj.p["dist"] * 0.6, "jump jets dash")
    bot.pressed = {"dash"}
    xb = p.x
    g.update(1 / 60)
    bot.pressed = set()
    run(0.3)
    check(abs(p.x - xb) < 0.5, "jets respect their cooldown")

    # ---- tether beam: solo satellite, then co-op heal
    w, p = fresh()
    tb = module(p, "tether")
    L_ = tb.p["length"]
    ring = [(p.x + math.cos(a) * L_ * 0.6, p.y + math.sin(a) * L_ * 0.6) for a in (0.5, 2.6, 4.7)]
    ms = pinned(w, ring)
    run(5, ms, "mod_tether")
    print("  tether solo: monsters on the beam's sweep took %s" % dealt(ms))
    check(sum(1 for d in dealt(ms) if d > 0) >= 2, "solo tether beam sweeps and burns monsters")
    w, p = fresh(players=2)
    tb = module(p, "tether")
    tb.p["heal"] = 0.5
    p2 = w.players[1]
    p2.x, p2.y = p.x + 3, p.y
    p.hp, p2.hp = 50, 50
    mid = pinned(w, [(p.x + 1.5, p.y)])
    run(3, mid, "mod_tether_coop")
    print("  tether co-op: P1 %.1f P2 %.1f, monster between them took %s" % (p.hp, p2.hp, dealt(mid)))
    check(p.hp > 50 and p2.hp > 50 and dealt(mid)[0] > 0, "co-op tether heals both players and burns what's between")

    # ---- loot magnet
    w, p = fresh()
    lm = module(p, "magnet")
    p.hp = 40
    w.loot = [Loot("health", p.x + lm.p["radius"] * 0.8, p.y)]
    run(3, shot="mod_magnet", at=20)
    check(not w.loot and p.hp > 40, "loot magnet pulls health in (hp %.0f)" % p.hp)

    # ---- inventory with 3 duplicates + soak
    w, p = fresh()
    for k in range(3):
        module(p, "gunbot", seed=k)
    run(0.5)
    pos = [(round(m_.x, 1), round(m_.y, 1)) for m_ in p.equipped()]
    check(len(set(pos)) == 3, "three duplicate drones take different stations %s" % pos)
    errs = 0
    rr = random.Random(3)
    for d, biome in ((1, "facility"), (4, "hell"), (6, "sewer")):
        main.biome_for = lambda d_, s_, b=biome: b
        g.new_world(d)
        g.state = "play"
        w = g.world
        p = w.player
        p.hp = p.max_hp = 1e6
        for kind in rr.sample(list(SU.KINDS), 3):
            p.give(SU.generate(d, kind=kind, rarity=3))
        bot.fire = True
        try:
            for f in range(60 * 12):
                bot.move = (math.cos(f / 50), math.sin(f / 70))
                bot.aim = (math.cos(f / 30) * 300, math.sin(f / 30) * 300)
                bot.pressed = {"dash"} if f % 90 == 0 else set()
                g.update(1 / 60)
                if p.hp < 1e5:
                    p.hp = 1e6
                if f % 4 == 0:
                    g.draw()
            pygame.image.save(g.screen, os.path.join(out, "soak_%s.png" % biome))
            print("  soak %s with %s: kills %d" % (biome, [m_.kind for m_ in p.equipped()], w.kills))
        except Exception:
            traceback.print_exc()
            errs += 1
    bot.fire = False
    check(errs == 0, "soak with random module loadouts runs without errors")
except Exception:
    traceback.print_exc()
    fails.append("crash")
print()
print("FAILED:", fails if fails else "none")

"""The title screen: the startup story, the LOCAL / ONLINE / SETTINGS pages and the generated maps behind them.
python tools/title_test.py [outdir]   (saves a screenshot of each screen)"""
import os
import sys
import json
import random
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
SAVE = os.path.join(tempfile.mkdtemp(), "save.json")
os.environ["SKULLS_SAVE"] = SAVE
os.environ.pop("SKULLS_DEMAND", None)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import pygame  # noqa: E402
import main  # noqa: E402
import story  # noqa: E402
import sfx  # noqa: E402
import netplay as NP  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "_title_test")
os.makedirs(out, exist_ok=True)
fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


# ---- the story generator
print("== story")
seen = [story.generate(random.Random(i)) for i in range(40)]
check(len({s.text() for s in seen}) == 40, "40 launches, 40 different stories")
check(len({s.lines[2] for s in seen}) > 20 and len({s.lines[3] for s in seen}) > 20, "the subject and how it woke up vary")
s0 = seen[0]
check(s0.subject in s0.lines[2] and s0.subject in s0.lines[-1] and s0.codename in s0.tagline,
      "the subject number / codename it invents carry through the story and the title tagline")
check(all(len(s.lines) == 10 and all(ln.strip() for ln in s.lines) for s in seen), "every story has all ten lines")
print("    e.g.  " + "\n          ".join(s0.lines))

# ---- startup: the intro plays, a press shows it all, another goes to the menu
print("== intro")
g = main.Game(windowed=True)
inp = g.inputs[0]


def frames(n, press=None, draw_every=1):
    for i in range(n):
        inp.pressed = {press} if (press and i == 0) else set()
        g.time += 1 / 60
        g.update(1 / 60)
        if draw_every and i % draw_every == 0:
            g.draw()


check(g.state == "intro", "the game opens on the story")
frames(90)
starts, end = g.intro_times()
check(0 < g._intro_typed < sum(len(ln) for ln in g.story.lines), "it types itself out (%d characters so far)" % g._intro_typed)
pygame.image.save(g.screen, os.path.join(out, "intro_typing.png"))
frames(1, "start")
check(g.state == "intro" and g.intro_t >= end, "a press shows the whole story at once")
frames(2)
pygame.image.save(g.screen, os.path.join(out, "intro.png"))
frames(1, "a")
check(g.state == "title" and g.title_page == "main", "a second press goes to the main menu")
check(g.story.tagline and g.story.codename in g.story.tagline, "the menu shows this story's tagline")

# ---- the generated map behind the menus
print("== background")
sc_ = g.title_scene
check(bool(sc_) and sc_.world.level is not None, "a real generated sector sits behind the menus (%s)" % (sc_ and sc_.title))
first, cam0 = sc_.world, list(sc_.state["cam"])
frames(60)
check(sc_.state["cam"] != cam0, "the camera pans across it")
check(g.world is None and g.cam == [0.0, 0.0] or g.world is None, "the game's own world / camera stay untouched")
pygame.image.save(g.screen, os.path.join(out, "main.png"))
biomes = {sc_.biome}
for _ in range(3):
    frames(int(60 * (main.TitleScene.SHOW + 0.5)), draw_every=1)
    biomes.add(g.title_scene.biome)
check(g.title_scene.world is not first and len(biomes) >= 3, "every few seconds it cuts to a new sector (%s)" % ", ".join(sorted(biomes)))
random.seed(1234)
a = [random.random() for _ in range(3)]
random.seed(1234)
g.title_scene.new()
check([random.random() for _ in range(3)] == a, "building a background map doesn't touch the game's random numbers")
played = []
orig = sfx.play
sfx.play = lambda name, *a_, **k: played.append(name)
g.title_scene.new()
sfx.play = orig
check(not played, "...and makes no sound")

# ---- main menu -> pages
print("== pages")
keys = [k for k, _ in g.TITLE_PAGES["main"]]
check(keys == ["local", "online", "settings", "quit"], "main menu: LOCAL PLAY, ONLINE PLAY, SETTINGS, QUIT")
frames(1, "a")
check(g.title_page == "local", "A on LOCAL PLAY opens its page")
frames(1, "nav_right")
check(g.chars[0] == "canbot", "LEFT / RIGHT there picks a body")
frames(20)
pygame.image.save(g.screen, os.path.join(out, "local.png"))
frames(1, "deploy")
check(g.title_page == "main" and g.menu_i == 0, "B goes back, with LOCAL PLAY still highlighted")
frames(1, "nav_down")
frames(1, "a")
check(g.title_page == "online", "ONLINE PLAY opens its page")
frames(20)
pygame.image.save(g.screen, os.path.join(out, "online.png"))
frames(1, "nav_down")
frames(1, "a")
check(isinstance(g.net, NP.JoinScreen), "JOIN NET GAME opens the join screen")
g.draw()
pygame.image.save(g.screen, os.path.join(out, "join_screen.png"))
g.leave_net()
check(g.state == "title" and g.title_page == "online", "leaving it comes back to the ONLINE PLAY page")
g.title_page, g.menu_i = "main", 2
frames(1, "a")
check(g.title_page == "settings", "SETTINGS opens its page")

# ---- settings
print("== settings")
rows = [k for k, _ in g.TITLE_PAGES["settings"]]
g.menu_i = rows.index("sound")
frames(1, "nav_left")
frames(1, "nav_left")
check(abs(g.sound_vol - 0.8) < 1e-6 and abs(sfx.sound_level - 0.8) < 1e-6, "SOUND VOLUME: LEFT x2 -> 80%, applied to the mixer")
g.menu_i = rows.index("music")
frames(1, "nav_left")
check(abs(sfx.music_level - 0.9) < 1e-6, "MUSIC VOLUME: LEFT -> 90%")
g.menu_i = rows.index("intro")
frames(1, "a")
check(g.intro_on is False, "STORY AT STARTUP can be turned off")
g.menu_i = rows.index("numbers")
frames(1, "nav_right")
check(g.damage_numbers is True, "DAMAGE NUMBERS toggles")
frames(20)
pygame.image.save(g.screen, os.path.join(out, "settings.png"))
saved = json.load(open(SAVE))
check(saved.get("sound") == 0.8 and saved.get("music") == 0.9 and saved.get("intro") is False and saved.get("damage_numbers") is True,
      "settings are saved as they change (%s)" % {k: saved.get(k) for k in ("sound", "music", "intro", "damage_numbers")})
g2 = main.Game(windowed=True)
check(g2.state == "title" and abs(g2.sound_vol - 0.8) < 1e-6 and not g2.intro_on, "next launch: no story, volumes kept")
g.menu_i = rows.index("story")
old = g.story.text()
frames(1, "a")
check(g.state == "intro" and g.story.text() != old, "TELL ME A NEW STORY plays a fresh one")
frames(1, "start")
frames(1, "start")
check(g.state == "title", "...and returns to the menu")

# ---- mouse: hovering highlights, clicking picks
print("== mouse")
g.title_page, g.menu_i = "main", 0
r = g.title_menu_rects()[2]
pygame.mouse.get_pos = lambda: r.center
pygame.mouse.get_pressed = lambda *a: (True, False, False)
g._mouse_was = False
frames(1)
pygame.mouse.get_pressed = lambda *a: (False, False, False)
check(g.title_page == "settings", "clicking SETTINGS opens it")

# ---- starting a run frees the background map; the lobby still gets one
print("== play")
g.title_page, g.menu_i = "local", 0
frames(1, "a")
check(g.state == "play" and g.world is not None and g.title_scene is None, "START RUN starts the game and drops the menu map")
g.state, g.world = "title", None
g.net = NP.HostSession(g, 47931)
g.draw()
check(bool(g.title_scene), "the host lobby has a map behind it too")
pygame.image.save(g.screen, os.path.join(out, "host_lobby.png"))
g.leave_net()

print("FAILED: %d" % len(fails) if fails else "all title checks passed")
sys.exit(1 if fails else 0)

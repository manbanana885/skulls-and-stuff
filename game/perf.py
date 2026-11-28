"""Demand modes: HIGH / MID / LOW.

Lower modes put fewer monsters on the map (the main cost on a small machine) and make up for it with tougher,
angrier ones - LOW is about half the monsters at about twice the health, so a room carries roughly the same
total threat. They also trim purely cosmetic load: fewer particles and gibs, and LOW draws with half-size
sprites at 960 x 540, stretched to the screen (a quarter of the pixels; chosen at startup, so a change to or
from LOW takes effect next launch).

  local  - this machine's choice (saved; a Raspberry Pi starts on LOW, a PC on HIGH)
  sim    - the mode the current world was built with. Single player: local. Net play: the host uses the
           LOWEST mode of everyone in the session, so a Pi joining a PC game isn't buried in monsters.
"""
import os
import json

ORDER = ("low", "mid", "high")
MODES = {
    # count: monsters per room / spawner output / cap;  hp: health;  aggro: added to the depth aggression
    # (attack timers run faster, senses reach further);  speed: walking speed;  fx: share of the particle budget;
    # keep: share of cosmetic particles actually spawned;  gibs: share of gibs;  half: half-size sprites at 960 x 540
    "high": dict(label="HIGH", count=1.0, hp=1.0, aggro=0.0, speed=1.0, fx=1.0, keep=1.0, gibs=1.0, half=False,
                 blurb="every monster, full detail"),
    "mid":  dict(label="MID", count=0.66, hp=1.4, aggro=0.15, speed=1.06, fx=0.6, keep=0.7, gibs=0.6, half=False,
                 blurb="~3/4 the monsters, tougher and angrier; fewer particles and gibs"),
    "low":  dict(label="LOW", count=0.4, hp=2.0, aggro=0.3, speed=1.12, fx=0.35, keep=0.45, gibs=0.35, half=True,
                 blurb="half the monsters, 2x health and angrier; low-res sprites, far fewer particles and gibs"),
}


def is_raspberry_pi():
    try:
        with open("/proc/device-tree/model", "rb") as fh:
            return b"raspberry pi" in fh.read().lower()
    except OSError:
        return False


def default_mode():
    env = os.environ.get("SKULLS_DEMAND", "").lower()
    if env in MODES:
        return env
    return "low" if is_raspberry_pi() else "high"


def saved_mode():
    """The demand mode saved by the settings page (None if there isn't one, or SKULLS_DEMAND overrides it)."""
    if os.environ.get("SKULLS_DEMAND", "").lower() in MODES:
        return None
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.environ.get("SKULLS_SAVE") or os.path.join(root, "save.json")) as fh:
            m = json.load(fh).get("demand")
        return m if m in MODES else None
    except Exception:
        return None


local = saved_mode() or default_mode()
sim = local
boot = local          # the mode the game started in: it fixed the sprite size (see half_res)


def half_res():
    """Draw with half-size sprites at 960 x 540? Decided once, at startup (SKULLS_RES=half / full overrides)."""
    env = os.environ.get("SKULLS_RES", "").lower()
    if env in ("half", "full"):
        return env == "half"
    return MODES[boot]["half"]


def needs_restart():
    """The sprite size the current setting wants differs from the one loaded."""
    return MODES[local]["half"] != MODES[boot]["half"] and not os.environ.get("SKULLS_RES")


def lowest(modes):
    """The least demanding of several modes (unknown values are ignored)."""
    ok = [m for m in modes if m in MODES]
    return min(ok, key=ORDER.index) if ok else "high"


def cycle(mode):
    return ORDER[(ORDER.index(mode) - 1) % len(ORDER)]     # HIGH -> MID -> LOW -> HIGH


def S():
    """Stats of the mode the current world runs at (monster count, health, aggression)."""
    return MODES[sim]


def FX():
    """This machine's cosmetic budget."""
    return MODES[local]["fx"]


def KEEP():
    """Share of cosmetic particles this machine spawns."""
    return MODES[local]["keep"]


def GIBS():
    """Share of gibs this machine spawns."""
    return MODES[local]["gibs"]

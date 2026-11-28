"""Demand modes: HIGH / MID / LOW.

Lower modes put fewer monsters on the map (the main cost on a small machine) and make up for it with tougher,
angrier ones - LOW is about half the monsters at about twice the health, so a room carries roughly the same
total threat. They also trim purely cosmetic load (particle budget).

  local  - this machine's choice (saved; a Raspberry Pi starts on LOW, a PC on HIGH)
  sim    - the mode the current world was built with. Single player: local. Net play: the host uses the
           LOWEST mode of everyone in the session, so a Pi joining a PC game isn't buried in monsters.
"""
import os

ORDER = ("low", "mid", "high")
MODES = {
    # count: monsters per room / spawner output / cap;  hp: health;  aggro: added to the depth aggression
    # (attack timers run faster, senses reach further);  speed: walking speed;  fx: share of the particle budget
    "high": dict(label="HIGH", count=1.0, hp=1.0, aggro=0.0, speed=1.0, fx=1.0,
                 blurb="every monster"),
    "mid":  dict(label="MID", count=0.66, hp=1.4, aggro=0.15, speed=1.06, fx=0.6,
                 blurb="~3/4 the monsters, tougher and angrier"),
    "low":  dict(label="LOW", count=0.4, hp=2.0, aggro=0.3, speed=1.12, fx=0.35,
                 blurb="half the monsters, 2x health and angrier"),
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


local = default_mode()
sim = local


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

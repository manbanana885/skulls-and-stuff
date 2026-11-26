"""Sound + music playback. Audio is synthesized offline by tools/make_sfx.py and tools/make_music.py."""
import os
import glob
import random
import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR = os.path.join(ROOT, "assets", "audio", "sfx")
MUSIC_DIR = os.path.join(ROOT, "assets", "audio", "music")

# relative mix levels
VOLUME = {
    "shot": 0.32, "shot_spread": 0.34, "explosion": 0.9, "explosion_small": 0.6, "enemy_shot": 0.45,
    "hit_flesh": 0.45, "hit_metal": 0.3, "ricochet": 0.16, "splat": 0.35, "bones": 0.35, "clatter": 0.18,
    "death_zombie": 0.55, "death_spider": 0.55, "death_leech": 0.5, "death_drone": 0.6, "lunge": 0.3,
    "spawn": 0.45, "hive_death": 0.9, "hurt": 0.7, "player_death": 1.0, "pickup": 0.5, "power": 0.55,
    "portal": 0.6, "step": 0.22, "start": 0.8,
    "shot_pistol": 0.3, "shot_revolver": 0.42, "shot_smg": 0.24, "shot_shotgun": 0.5, "shot_assault": 0.3,
    "shot_sniper": 0.55, "shot_grenade": 0.45, "shot_rocket": 0.5, "shot_laser": 0.28, "shot_beam": 0.22,
    "shot_plasma": 0.4, "shot_flame": 0.22, "reload": 0.45, "empty": 0.4, "swap": 0.4, "weapon_pickup": 0.55,
    "tink": 0.25, "shock": 0.35, "acid_spit": 0.45, "sizzle": 0.35, "brute_roar": 0.75, "stomp": 0.45,
    "turret_shot": 0.3, "turret_beep": 0.4, "walker_rocket": 0.45, "bloater_pop": 0.85, "skull_screech": 0.4,
    "death_brute": 0.85, "death_skull": 0.5,
    "flame_loop": 0.5, "static_loop": 0.35, "fireball": 0.45, "wretch_blink": 0.5, "tongue": 0.5,
    "stalker_screech": 0.45, "mimic_scream": 0.8, "crumble": 0.75,
    "shot_nuke": 0.6, "nuke_blast": 1.0, "shot_saw": 0.4, "saw_bounce": 0.35, "chem_loop": 0.4, "cryo_loop": 0.4,
    "freeze": 0.55, "shatter": 0.6,
    "trap_spikes": 0.45, "trap_vent": 0.4, "trap_saw": 0.3, "zap": 0.45, "thunder": 0.8, "chomp": 0.6, "klaxon": 0.45,
    "servo": 0.35, "tentacle": 0.55, "bubble": 0.25, "shot_chaingun": 0.3, "shot_railgun": 0.75,
}
# minimum seconds between two plays of the same sound (prevents machine-gun pile-ups)
MIN_GAP = {
    "hit_flesh": 0.035, "hit_metal": 0.05, "ricochet": 0.07, "splat": 0.05, "bones": 0.06, "clatter": 0.04,
    "death_zombie": 0.06, "death_leech": 0.06, "death_spider": 0.1, "death_drone": 0.08, "spawn": 0.15,
    "enemy_shot": 0.05, "explosion": 0.06, "explosion_small": 0.05,
    "shot_flame": 0.07, "shot_smg": 0.045, "tink": 0.08, "shock": 0.1, "stomp": 0.12, "turret_shot": 0.06,
    "sizzle": 0.25, "skull_screech": 0.2, "brute_roar": 0.4, "acid_spit": 0.1,
    "crumble": 0.1, "wretch_blink": 0.15, "saw_bounce": 0.05, "freeze": 0.08, "shatter": 0.06, "stalker_screech": 0.25, "fireball": 0.1, "tongue": 0.1,
    "trap_spikes": 0.12, "trap_vent": 0.2, "trap_saw": 0.35, "zap": 0.12, "thunder": 0.3, "chomp": 0.1, "klaxon": 0.5,
    "servo": 0.2, "tentacle": 0.2, "bubble": 0.3, "shot_chaingun": 0.04,
}
MUSIC_VOLUME = 0.55

_sounds = {}
_last = {}
_enabled = False
_track = None
_rng = random.Random()


def init():
    global _enabled
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init(44100, -16, 2, 512)
        pygame.mixer.set_num_channels(48)
        pygame.mixer.set_reserved(4)
    except pygame.error:
        return
    _enabled = True
    for path in sorted(glob.glob(os.path.join(SFX_DIR, "*.wav"))):
        base = os.path.basename(path)[:-4]
        name = base.rsplit("_", 1)[0]
        try:
            _sounds.setdefault(name, []).append(pygame.mixer.Sound(path))
        except pygame.error:
            pass


def play(name, vol=1.0):
    if not _enabled:
        return
    variants = _sounds.get(name)
    if not variants:
        return
    now = pygame.time.get_ticks() / 1000.0
    gap = MIN_GAP.get(name, 0.0)
    if gap and now - _last.get(name, -1) < gap:
        return
    _last[name] = now
    snd = _rng.choice(variants)
    ch = snd.play()
    if ch is not None:
        ch.set_volume(min(1.0, VOLUME.get(name, 0.5) * vol * _rng.uniform(0.85, 1.0)))


LOOP_CHANNEL = {"flame_loop": 0, "static_loop": 1, "chem_loop": 2, "cryo_loop": 3}
_loop_on = {}


def loop(name, on, vol=1.0):
    """Continuous sounds (flamethrower roar, radio static) on reserved channels."""
    if not _enabled or name not in LOOP_CHANNEL or not _sounds.get(name):
        return
    ch = pygame.mixer.Channel(LOOP_CHANNEL[name])
    if on:
        if not _loop_on.get(name):
            ch.play(_sounds[name][0], loops=-1, fade_ms=60)
            _loop_on[name] = True
        ch.set_volume(min(1.0, VOLUME.get(name, 0.5) * vol))
    elif _loop_on.get(name):
        ch.fadeout(160)
        _loop_on[name] = False


def stop_loops():
    for name in LOOP_CHANNEL:
        loop(name, False)


def music(track, fade_ms=1500):
    """Start (or keep) a looping music track. None fades out."""
    global _track
    if not _enabled or track == _track:
        return
    _track = track
    if track is None:
        pygame.mixer.music.fadeout(fade_ms)
        return
    path = os.path.join(MUSIC_DIR, track + ".wav")
    if not os.path.exists(path):
        return
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
        pygame.mixer.music.play(-1, fade_ms=fade_ms)
    except pygame.error:
        pass

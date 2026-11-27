"""Synthesize all sound effects -> assets/audio/sfx/<name>_<variant>.wav

Style target: chunky 16-bit console action (punchy low-mid shots, crunchy explosions,
sample-rate grit + short echo) rather than piercing beeps.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsp import (SR, n_of, tt, R, expdec, ar, noise, saw, pulse, sine, lp, hp, bp, sweep_lp, drive, crush,  # noqa: E402
                 echo, place, fade_out, normalize, write)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "audio", "sfx")


def finish(x, bits=10, hold=2, fc=8000, echo_d=0.0, echo_fb=0.0, peak=0.9):
    if bits:
        x = crush(x, bits, hold)
    x = lp(x, fc)
    if echo_d:
        x = echo(x, echo_d, echo_fb, 3)
    x = hp(x, 35)
    return normalize(fade_out(x, 0.015), peak)


def mix(*parts):
    n = max(len(p) for p, _ in parts)
    out = np.zeros(n)
    for p, off in parts:
        place(out, p, n_of(off))
    return out


# ---------------------------------------------------------------- weapons
def gun(seed, pitch=1.0):
    r = R(seed)
    n = n_of(0.34)
    t = tt(n)
    click = noise(n, r) * expdec(n, 0.0015)
    crack = bp(noise(n, r), 650 * pitch, 2400 * pitch) * expdec(n, 0.018) * 2.2
    f = 48 + 125 * pitch * np.exp(-t / 0.022)
    thump = sine(f, n) * expdec(n, 0.065) * 1.4
    tail = lp(noise(n, r), 1000) * expdec(n, 0.085) * 1.0
    x = drive(click * 0.5 + crack + thump + tail, 2.2)
    return finish(x, 9, 2, 6000, 0.07, 0.22)


def spread(seed):
    r = R(seed)
    a = gun(seed, 0.82)
    b = gun(seed + 50, 1.05)
    n = n_of(0.3)
    t = tt(n)
    f = 110 + 230 * np.exp(-t / 0.05)
    fw = lp(pulse(f, n, 0.3), 1300) * expdec(n, 0.09) * 0.5
    fw += lp(noise(n, r), 700) * expdec(n, 0.12) * 0.4
    x = mix((a, 0), (b * 0.6, 0.014), (fw, 0))
    return finish(x, 9, 2, 6000, 0.08, 0.25)


def explosion(seed, size=1.0):
    r = R(seed)
    dur = 0.9 + 0.9 * size
    n = n_of(dur)
    t = tt(n)
    env = ar(n, 0.004, 0.22 * size + 0.08)
    body = sweep_lp(noise(n, r), env ** 0.7, 120, 5000) * env * 1.7
    f = 24 + 75 * np.exp(-t / (0.12 * size))
    boom = sine(f, n) * ar(n, 0.002, 0.35 * size) * 1.7
    crack = np.zeros(n)
    for _ in range(int(45 * size)):
        p = int(min(n - 400, r.exponential(0.17 * size) * SR))
        k = n_of(0.008)
        c = bp(noise(k, r), 900, 5000) * expdec(k, 0.002)
        place(crack, c, p, r.uniform(0.3, 1.0))
    x = drive(body + boom + crack * 0.6, 3.0)
    return finish(x, 9, 2, 7000, 0.12, 0.3)


def enemy_shot(seed):
    r = R(seed)
    n = n_of(0.3)
    t = tt(n)
    f = 150 + 380 * np.exp(-t / 0.06)
    x = lp(pulse(f, n, 0.4), 1800) * expdec(n, 0.15) + lp(noise(n, r), 900) * expdec(n, 0.05) * 0.6
    return finish(drive(x, 2), 9, 2, 5000, 0.06, 0.2)


# ---------------------------------------------------------------- impacts / gore
def hit_flesh(seed):
    r = R(seed)
    n = n_of(0.16)
    t = tt(n)
    sq = bp(noise(n, r), 250, 1300) * expdec(n, 0.03) * 1.5
    f = 60 + 50 * np.exp(-t / 0.02)
    bump = sine(f, n) * expdec(n, 0.05) * 0.9
    wet = lp(noise(n, r), 550) * expdec(n, 0.07) * 0.6
    return finish(drive(sq + bump + wet, 1.8), 10, 2, 5500)


def splat(seed):
    r = R(seed)
    n = n_of(0.22)
    t = tt(n)
    bub = 0.6 + 0.4 * np.sign(sine(r.uniform(16, 32), n))
    x = lp(noise(n, r), r.uniform(600, 1100)) * ar(n, 0.004, 0.06) * bub
    f = 55 + 40 * np.exp(-t / 0.015)
    x += sine(f, n) * expdec(n, 0.04) * 0.6
    return finish(x, 10, 2, 4500)


def bones(seed):
    r = R(seed)
    n = n_of(0.16)
    x = np.zeros(n)
    for _ in range(r.integers(3, 7)):
        k = n_of(0.01)
        c = hp(noise(k, r), r.uniform(1500, 3000)) * expdec(k, 0.003)
        place(x, c, int(r.uniform(0, 0.08) * SR), r.uniform(0.4, 1))
    k = n_of(0.05)
    x[:k] += bp(noise(k, r), 400, 1300) * expdec(k, 0.012) * 0.8
    return finish(x, 10, 2, 7000)


def metal(seed, base=None, dur=0.4):
    r = R(seed)
    base = base or r.uniform(600, 1000)
    n = n_of(dur)
    x = np.zeros(n)
    for ratio, dec, amp in ((1, 0.22, 1), (1.47, 0.16, 0.7), (2.09, 0.11, 0.5), (2.56, 0.08, 0.4), (3.3, 0.05, 0.3)):
        x += sine(base * ratio * r.uniform(0.98, 1.02), n) * expdec(n, dec) * amp
    x += hp(noise(n, r), 2000) * expdec(n, 0.004) * 0.8
    return finish(drive(x, 1.5), 10, 2, 6000, 0.05, 0.15)


def ricochet(seed):
    r = R(seed)
    n = n_of(0.12)
    t = tt(n)
    f = 1200 + 500 * np.exp(-t / 0.04)
    x = sine(f, n) * expdec(n, 0.035) * 0.35 + bp(noise(n, r), 1000, 4000) * expdec(n, 0.006)
    return finish(x, 10, 2, 4500)


def clatter(seed):
    """Small hard bits landing (bones, gears)."""
    r = R(seed)
    n = n_of(0.12)
    x = np.zeros(n)
    for _ in range(r.integers(1, 3)):
        k = n_of(0.05)
        place(x, sine(r.uniform(1500, 2600), k) * expdec(k, 0.012) * 0.5 + hp(noise(k, r), 2500) * expdec(k, 0.003),
              int(r.uniform(0, 0.05) * SR))
    return finish(x, 10, 2, 6000)


# ---------------------------------------------------------------- creatures
def growl(seed):
    r = R(seed)
    dur = 0.8
    n = n_of(dur)
    t = tt(n)
    jit = lp(noise(n, r), 12) * 40
    f = (r.uniform(75, 100) + jit) * (1 - 0.4 * t / dur)
    src = saw(f, n) + 0.3 * noise(n, r)
    x = bp(src, 350, 800) + 0.6 * bp(src, 1000, 1600) + 0.25 * bp(src, 2200, 2900)
    x = drive(x * ar(n, 0.04, 0.32) * 2.5, 2.0)
    x = mix((x, 0), (splat(seed + 5) * 0.7, 0.0))
    return finish(x, 10, 2, 6000, 0.08, 0.15)


def shriek(seed):
    r = R(seed)
    dur = 0.65
    n = n_of(dur)
    t = tt(n)
    f = 1100 * (1 - 0.5 * t / dur)
    fm = sine(f + 380 * sine(f * 1.41, n), n)
    nz = bp(noise(n, r), 1300, 3800)
    x = (fm * 0.45 + nz * 0.8) * ar(n, 0.01, 0.18)
    x = mix((x, 0), (bones(seed + 2), 0.02), (splat(seed + 3) * 0.6, 0.05))
    return finish(x, 9, 2, 5000, 0.07, 0.15)


def gurgle(seed, pitch=1.0, dur=0.6):
    r = R(seed)
    n = n_of(dur)
    x = lp(noise(n, r), 450) * expdec(n, dur * 0.4) * 0.7
    for _ in range(12):
        k = n_of(r.uniform(0.03, 0.06))
        f0 = r.uniform(140, 380) * pitch
        f = f0 * (1 + 0.9 * tt(k) / (k / SR))
        b = sine(f, k) * np.sin(np.linspace(0, np.pi, k))
        place(x, b, int(r.uniform(0, dur * 0.7) * SR), r.uniform(0.3, 0.8))
    return finish(x, 10, 2, 4000)


def zap_death(seed):
    r = R(seed)
    n = n_of(0.5)
    t = tt(n)
    f = 140 + 1300 * np.exp(-t / 0.06)
    z = lp(pulse(f, n, 0.3), 2800) * expdec(n, 0.14) * 0.7
    sp = np.zeros(n)
    for _ in range(20):
        k = n_of(0.006)
        place(sp, hp(noise(k, r), 3000) * expdec(k, 0.002), int(r.uniform(0, 0.4) * SR), r.uniform(0.2, 0.7))
    x = mix((z + sp, 0), (explosion(seed + 9, 0.35) * 0.8, 0.02), (metal(seed + 4, 900, 0.3) * 0.4, 0.0))
    return finish(x, 9, 2, 6500, 0.09, 0.2)


def hiss(seed):
    r = R(seed)
    n = n_of(0.3)
    x = bp(noise(n, r), 2000, 6000) * ar(n, 0.03, 0.1)
    return finish(x, 10, 2, 6500)


# ---------------------------------------------------------------- player / ui
def hurt(seed):
    r = R(seed)
    n = n_of(0.25)
    buzz = drive(pulse(92, n, 0.5), 2) * expdec(n, 0.08) * 0.5
    x = mix((metal(seed, 450, 0.35), 0), (lp(buzz, 1500), 0), (bones(seed + 1) * 0.6, 0.01))
    return finish(x, 9, 2, 5500)


def player_death(seed):
    r = R(seed)
    parts = [(explosion(seed, 1.35), 0)]
    for k in range(6):
        parts.append((metal(seed + 10 + k, r.uniform(500, 1300), 0.35) * (0.8 - k * 0.1), 0.1 + k * 0.13 + r.uniform(0, 0.05)))
    parts.append((growl(seed + 3) * 0.4, 0.05))
    return finish(mix(*parts), 9, 2, 6500, 0.14, 0.3)


def hive_death(seed):
    return finish(mix((explosion(seed, 0.8), 0), (gurgle(seed + 1, 0.7, 0.9), 0.05), (splat(seed + 2), 0.0),
                      (splat(seed + 3), 0.12)), 9, 2, 6000, 0.1, 0.25)


def notes_arp(midis, gap, seed, width=0.25, dec=0.12):
    n = n_of(gap * len(midis) + 0.4)
    x = np.zeros(n)
    for i, m in enumerate(midis):
        f = 440 * 2 ** ((m - 69) / 12)
        k = n_of(0.35)
        tone = lp(pulse(f, k, width), 3200) * 0.5 + sine(f, k) * 0.5
        place(x, tone * ar(k, 0.002, dec), n_of(i * gap))
    return x


def pickup(seed):
    return finish(notes_arp([76, 83, 88], 0.06, seed), 10, 2, 7000, 0.09, 0.35)


def power(seed):
    return finish(notes_arp([64, 67, 71, 76, 79, 83, 88], 0.045, seed, 0.5), 10, 2, 7000, 0.1, 0.4)


def portal(seed):
    r = R(seed)
    dur = 1.3
    n = n_of(dur)
    t = tt(n)
    env = (t / dur) ** 1.5
    wh = sweep_lp(hp(noise(n, r), 300), env, 300, 9000) * np.sin(np.pi * t / dur) * 0.8
    f = 120 * (8 ** (t / dur))
    tone = sine(f * (1 + 0.01 * sine(6, n)), n) * np.sin(np.pi * t / dur) * 0.5
    return finish(wh + tone, 10, 2, 8000, 0.12, 0.35)


def step(seed):
    r = R(seed)
    n = n_of(0.12)
    t = tt(n)
    f = 85 + 70 * np.exp(-t / 0.01)
    x = sine(f, n) * expdec(n, 0.03) + hp(noise(n, r), 2500) * expdec(n, 0.003) * 0.5
    x += sine(r.uniform(1600, 2100), n) * expdec(n, 0.03) * 0.15
    return finish(x, 10, 2, 5000)


def spawn(seed):
    return finish(mix((gurgle(seed, 0.6, 0.5), 0), (splat(seed + 1), 0.02)), 10, 2, 4500)


def start(seed):
    r = R(seed)
    n = n_of(1.0)
    x = np.zeros(n)
    for m in (40, 47, 52, 59):
        f = 440 * 2 ** ((m - 69) / 12)
        x += saw(f * 1.003, n) + saw(f * 0.997, n)
    x = sweep_lp(x, expdec(n, 0.15), 200, 4500) * ar(n, 0.005, 0.35) * 0.3
    x = mix((drive(x, 2), 0), (explosion(seed, 0.4) * 0.7, 0))
    return finish(x, 10, 2, 8000, 0.13, 0.3)


# ---------------------------------------------------------------- weapon family
def gun_shaped(seed, pitch=1.0, dur=0.34, crack=1.0, thump=1.0, tail_tau=0.085, drv=2.2, echo_d=0.07, echo_fb=0.22, fc=6000):
    r = R(seed)
    n = n_of(dur)
    t = tt(n)
    click = noise(n, r) * expdec(n, 0.0015)
    cr = bp(noise(n, r), 650 * pitch, 2400 * pitch) * expdec(n, 0.018) * 2.2 * crack
    f = 45 + 125 * pitch * np.exp(-t / 0.022)
    th = sine(f, n) * expdec(n, 0.065 / pitch ** 0.5) * 1.4 * thump
    tail = lp(noise(n, r), 1000 * pitch) * expdec(n, tail_tau) * 1.0
    x = drive(click * 0.5 + cr + th + tail, drv)
    return finish(x, 9, 2, fc, echo_d, echo_fb)


def clicks(seed, times, base=2500):
    r = R(seed)
    n = n_of(max(times) + 0.08)
    x = np.zeros(n)
    for k, tm in enumerate(times):
        m = n_of(0.04)
        c = hp(noise(m, r), base) * expdec(m, 0.004) + sine(r.uniform(900, 1600), m) * expdec(m, 0.012) * 0.4
        place(x, c, n_of(tm))
    return x


def shotgun(seed):
    r = R(seed)
    n = n_of(0.5)
    t = tt(n)
    blast = lp(noise(n, r), 2500) * expdec(n, 0.06) * 1.6 + bp(noise(n, r), 500, 2000) * expdec(n, 0.025) * 1.5
    boom = sine(38 + 110 * np.exp(-t / 0.03), n) * expdec(n, 0.12) * 1.8
    x = drive(blast + boom, 2.6)
    pump = clicks(seed + 1, (0.36, 0.47), 1800)
    return finish(mix((x, 0), (pump * 0.6, 0)), 9, 2, 6000, 0.09, 0.3)


def sniper(seed):
    r = R(seed)
    n = n_of(0.6)
    t = tt(n)
    crack = bp(noise(n, r), 900, 4000) * expdec(n, 0.025) * 2.0
    boom = sine(32 + 150 * np.exp(-t / 0.025), n) * expdec(n, 0.2) * 1.8
    tail = lp(noise(n, r), 700) * expdec(n, 0.18)
    x = drive(crack + boom + tail, 2.8)
    return finish(x, 9, 2, 6500, 0.19, 0.42)


def thoomp(seed):
    r = R(seed)
    n = n_of(0.4)
    t = tt(n)
    x = sine(70 + 160 * np.exp(-t / 0.04), n) * expdec(n, 0.1) * 1.5 + lp(noise(n, r), 600) * expdec(n, 0.06)
    x = mix((drive(x, 2), 0), (clicks(seed, (0.12,), 2000) * 0.5, 0))
    return finish(x, 9, 2, 5000, 0.08, 0.2)


def rocket_launch(seed, dur=0.9):
    r = R(seed)
    n = n_of(dur)
    t = tt(n)
    env = np.minimum(1, t / 0.04) * np.exp(-t / (dur * 0.45))
    sw = 0.3 + 0.7 * np.exp(-t / 0.25)
    whoosh = sweep_lp(noise(n, r), sw, 300, 6000) * env * 1.5
    ign = sine(60 + 120 * np.exp(-t / 0.03), n) * expdec(n, 0.08) * 1.2
    return finish(drive(whoosh + ign, 2), 9, 2, 6500, 0.1, 0.25)


def laser(seed):
    """Soft, rounded 'pew' - lowpassed and short so rapid fire never gets shrill."""
    r = R(seed)
    n = n_of(0.16)
    t = tt(n)
    f = 230 + 650 * np.exp(-t / 0.03) * r.uniform(0.9, 1.1)
    x = lp(pulse(f, n, 0.5), 1600) * expdec(n, 0.05) + lp(noise(n, r), 900) * expdec(n, 0.03) * 0.4
    x += sine(f * 0.5, n) * expdec(n, 0.06) * 0.5
    return finish(x, 10, 2, 3200, 0.05, 0.15)


def beam(seed):
    r = R(seed)
    n = n_of(0.14)
    x = bp(saw(110 * r.uniform(0.95, 1.05), n) + saw(165, n) * 0.6 + noise(n, r) * 0.4, 200, 2200)
    x *= ar(n, 0.005, 0.06)
    return finish(drive(x, 2), 10, 2, 3500)


def plasma(seed):
    r = R(seed)
    n = n_of(0.4)
    t = tt(n)
    f = (90 + 260 * np.exp(-t / 0.06)) * (1 + 0.08 * np.sin(2 * np.pi * 28 * t))
    x = lp(pulse(f, n, 0.35), 1400) * expdec(n, 0.14) + lp(noise(n, r), 700) * expdec(n, 0.05) * 0.5
    return finish(drive(x, 1.8), 10, 2, 4000, 0.07, 0.25)


def flame(seed):
    r = R(seed)
    n = n_of(0.2)
    x = lp(noise(n, r), 1300) * ar(n, 0.02, 0.07) + bp(noise(n, r), 150, 700) * ar(n, 0.01, 0.1) * 1.2
    for _ in range(4):
        k = n_of(0.01)
        place(x, bp(noise(k, r), 1500, 4000) * expdec(k, 0.002) * 0.4, int(r.uniform(0, 0.15) * SR))
    return finish(x, 10, 2, 4500)


def reload_snd(seed):
    r = R(seed)
    x = mix((metal(seed, 1400, 0.12) * 0.4, 0.0), (clicks(seed, (0.0, 0.22, 0.3), 2200), 0.0),
            (sine(140, n_of(0.08)) * expdec(n_of(0.08), 0.02) * 0.6, 0.2))
    return finish(x, 10, 2, 6000)


def empty_click(seed):
    return finish(clicks(seed, (0.0,), 3000), 10, 2, 6000)


def swap(seed):
    r = R(seed)
    n = n_of(0.25)
    rustle = bp(noise(n, r), 600, 3000) * ar(n, 0.03, 0.06) * 0.6
    return finish(mix((rustle, 0), (clicks(seed, (0.12, 0.17), 2000), 0)), 10, 2, 6000)


def weapon_pickup(seed):
    return finish(mix((clicks(seed, (0.0, 0.06), 1800), 0), (notes_arp([64, 71, 76], 0.05, seed, 0.25, 0.08) * 0.6, 0.05)),
                  10, 2, 6500, 0.08, 0.25)


def tink(seed):
    return finish(metal(seed, R(seed).uniform(1500, 2200), 0.15) * 0.6, 10, 2, 5000)


def shock_snd(seed):
    r = R(seed)
    n = n_of(0.3)
    buzz = drive(saw(60, n) + saw(90, n) * 0.5, 3) * ar(n, 0.005, 0.1) * 0.4
    cr = np.zeros(n)
    for _ in range(25):
        k = n_of(0.006)
        place(cr, bp(noise(k, r), 1000, 5000) * expdec(k, 0.0015), int(r.uniform(0, 0.25) * SR), r.uniform(0.3, 1))
    return finish(lp(buzz, 2500) + cr, 10, 2, 5500)


def spit(seed):
    r = R(seed)
    n = n_of(0.3)
    x = bp(noise(n, r), 500, 2400) * ar(n, 0.005, 0.04) * 1.2
    return finish(mix((x, 0), (gurgle(seed, 1.4, 0.25) * 0.6, 0.02)), 10, 2, 4500)


def sizzle(seed):
    r = R(seed)
    n = n_of(0.7)
    fizz = hp(noise(n, r), 2500) * (0.5 + 0.5 * (r.random(n) > 0.6)) * ar(n, 0.02, 0.25)
    x = lp(fizz, 6000) * 0.6
    place(x, splat(seed) * 0.5, 0)
    return finish(x, 10, 2, 6000)


def roar(seed):
    r = R(seed)
    dur = 1.2
    n = n_of(dur)
    t = tt(n)
    jit = lp(noise(n, r), 10) * 30
    f = (r.uniform(48, 60) + jit) * (1 + 0.15 * np.sin(np.pi * t / dur))
    src = saw(f, n) + 0.4 * noise(n, r)
    x = bp(src, 250, 650) + 0.7 * bp(src, 800, 1300) + 0.3 * bp(src, 1800, 2600)
    return finish(drive(x * ar(n, 0.08, 0.5) * 3, 2.5), 9, 2, 5000, 0.1, 0.2)


def stomp(seed):
    r = R(seed)
    n = n_of(0.3)
    t = tt(n)
    x = sine(40 + 50 * np.exp(-t / 0.02), n) * expdec(n, 0.08) * 1.5 + lp(noise(n, r), 400) * expdec(n, 0.05)
    return finish(drive(x, 2), 10, 2, 3000)


def turret_shot(seed):
    return finish(mix((gun_shaped(seed, 1.35, 0.2, 0.9, 0.6, 0.04), 0), (metal(seed, 2400, 0.1) * 0.25, 0)), 9, 2, 5500)


def beep(seed):
    return finish(notes_arp([81, 81], 0.12, seed, 0.5, 0.05) * 0.5, 10, 2, 3500)


def bloater_pop(seed):
    return finish(mix((explosion(seed, 0.6), 0), (splat(seed + 1), 0), (splat(seed + 2), 0.05), (gurgle(seed + 3, 0.5, 0.7), 0.02)),
                  9, 2, 5000, 0.1, 0.25)


def skull_screech(seed):
    r = R(seed)
    n = n_of(0.5)
    t = tt(n)
    f = 700 * (1 - 0.4 * t / 0.5)
    x = (sine(f + 200 * sine(f * 0.5, n), n) * 0.4 + bp(noise(n, r), 800, 2500) * 0.7) * ar(n, 0.02, 0.15)
    whoosh = lp(noise(n, r), 900) * ar(n, 0.05, 0.2) * 0.6
    return finish(x + whoosh, 9, 2, 4500)


def death_brute(seed):
    return finish(mix((roar(seed) * 0.8, 0), (bones(seed + 1), 0.05), (splat(seed + 2), 0), (stomp(seed + 3), 0.3)), 9, 2, 5500)


def skull_death(seed):
    return finish(mix((bones(seed), 0), (explosion(seed + 1, 0.3) * 0.6, 0)), 9, 2, 6000)


# ---------------------------------------------------------------- loops + new creatures
def seamless(x, n, fade=0.25):
    """Crossfade the tail into the head so the clip loops without a click."""
    f = n_of(fade)
    out = x[:n].copy()
    ramp = np.linspace(0, 1, f)
    out[:f] = out[:f] * ramp + x[n:n + f] * (1 - ramp)
    return out


def loop_finish(x, fc=6000, peak=0.85):
    x = hp(lp(crush(x, 10, 2), fc), 35)
    return normalize(x, peak)


def flame_loop(seed):
    r = R(seed)
    dur = 1.6
    n = n_of(dur)
    m = n + n_of(0.3)
    t = tt(m)
    roar = lp(noise(m, r), 900) * (0.8 + 0.2 * np.sin(2 * np.pi * 3.1 * t))
    body = bp(noise(m, r), 120, 500) * 1.3
    hiss = bp(noise(m, r), 1500, 4000) * 0.25
    crack = np.zeros(m)
    for _ in range(60):
        k = n_of(0.008)
        place(crack, bp(noise(k, r), 1200, 5000) * expdec(k, 0.002), int(r.uniform(0, m - k)), r.uniform(0.2, 0.8))
    x = drive(roar + body + hiss + crack * 0.5, 1.6)
    return loop_finish(seamless(x, n), 5500)


def static_loop(seed):
    r = R(seed)
    dur = 1.5
    n = n_of(dur)
    m = n + n_of(0.3)
    t = tt(m)
    hiss = bp(noise(m, r), 800, 6000) * 0.5
    am = 0.6 + 0.4 * (np.sin(2 * np.pi * 7.3 * t) > 0.3)
    hum = sine(60, m) * 0.15 + sine(120, m) * 0.08
    crack = np.zeros(m)
    for _ in range(40):
        k = n_of(0.01)
        place(crack, hp(noise(k, r), 1500) * expdec(k, 0.003), int(r.uniform(0, m - k)), r.uniform(0.3, 1.0))
    x = hiss * am + hum + crack * 0.6
    return loop_finish(seamless(x, n), 6500, 0.7)


def fireball(seed):
    r = R(seed)
    n = n_of(0.5)
    t = tt(n)
    wh = sweep_lp(noise(n, r), np.exp(-t / 0.2), 200, 3500) * ar(n, 0.02, 0.2) * 1.4
    th = sine(70 + 90 * np.exp(-t / 0.05), n) * expdec(n, 0.12)
    return finish(drive(wh + th, 2), 9, 2, 5000, 0.08, 0.2)


def wretch_blink(seed):
    r = R(seed)
    n = n_of(0.35)
    x = np.zeros(n)
    for k in range(7):
        m = n_of(r.uniform(0.015, 0.04))
        f = r.uniform(80, 400)
        seg = (pulse(f, m, 0.3) * 0.5 + bp(noise(m, r), 500, 5000)) * 0.8
        place(x, seg, int(r.uniform(0, 0.3) * SR))
    return finish(x, 7, 3, 6000, 0.06, 0.25)


def tongue(seed):
    r = R(seed)
    n = n_of(0.25)
    t = tt(n)
    whip = bp(noise(n, r), 600, 3500) * ar(n, 0.01, 0.04) * 1.3
    wet = splat(seed + 4)[:n] if len(splat(seed + 4)) >= n else np.pad(splat(seed + 4), (0, n - len(splat(seed + 4))))
    return finish(whip + wet * 0.7, 10, 2, 5000)


def stalker_screech(seed):
    r = R(seed)
    n = n_of(0.5)
    t = tt(n)
    f = 500 + 300 * np.sin(np.pi * t / 0.5)
    x = (bp(saw(f, n) + noise(n, r) * 0.6, 600, 2600) * ar(n, 0.03, 0.18)) * 1.3
    return finish(drive(x, 2.5), 9, 2, 4500, 0.07, 0.2)


def mimic_scream(seed):
    return finish(mix((roar(seed) * 0.7, 0), (shriek(seed + 1) * 0.6, 0.05), (gurgle(seed + 2, 0.6, 0.8) * 0.6, 0.0),
                      (splat(seed + 3), 0.0), (splat(seed + 4), 0.1)), 9, 2, 5000, 0.12, 0.3)


def crumble(seed):
    r = R(seed)
    n = n_of(1.0)
    x = lp(noise(n, r), 500) * ar(n, 0.01, 0.35) * 1.2
    for _ in range(40):
        k = n_of(0.03)
        place(x, bp(noise(k, r), 300, 2500) * expdec(k, 0.008), int(r.exponential(0.2) * SR) % (n - k), r.uniform(0.3, 1))
    boom = sine(45 + 40 * np.exp(-tt(n) / 0.05), n) * expdec(n, 0.2)
    return finish(drive(x + boom, 2), 9, 2, 4500, 0.1, 0.2)


# ---------------------------------------------------------------- nukes, saws, sprays, ice
def nuke_launch(seed):
    return finish(mix((rocket_launch(seed, 1.1), 0), (thoomp(seed + 1) * 0.8, 0)), 9, 2, 5500, 0.12, 0.3)


def nuke_blast(seed):
    r = R(seed)
    dur = 3.5
    n = n_of(dur)
    t = tt(n)
    env = ar(n, 0.006, 0.9)
    body = sweep_lp(noise(n, r), env ** 0.5, 80, 4000) * env * 1.8
    boom = sine(20 + 60 * np.exp(-t / 0.3), n) * ar(n, 0.003, 1.1) * 2.0
    rumble = lp(noise(n, r), 120) * ar(n, 0.3, 1.4) * 1.5
    return finish(drive(body + boom + rumble, 3.2), 9, 2, 6000, 0.2, 0.35)


def saw_launch(seed):
    r = R(seed)
    n = n_of(0.35)
    t = tt(n)
    f = 180 + 120 * np.exp(-t / 0.1)
    whirr = bp(saw(f, n) * (0.6 + 0.4 * sine(38, n)), 200, 1800) * ar(n, 0.005, 0.15)
    return finish(mix((whirr, 0), (clicks(seed, (0.0,), 1500) * 0.7, 0)), 10, 2, 4000, 0.05, 0.15)


def saw_bounce(seed):
    return finish(mix((metal(seed, R(seed).uniform(700, 1000), 0.2) * 0.6, 0), (clicks(seed, (0.0, 0.02), 2000), 0)), 10, 2, 4500)


def spray_loop(seed, kind):
    r = R(seed)
    dur = 1.5
    n = n_of(dur)
    m = n + n_of(0.3)
    t = tt(m)
    if kind == "chem":
        x = bp(noise(m, r), 600, 3500) * (0.8 + 0.2 * np.sin(2 * np.pi * 4 * t)) + lp(noise(m, r), 300) * 0.5
        for _ in range(30):       # bubbling
            k = n_of(0.03)
            place(x, sine(r.uniform(200, 500) * np.linspace(1, 1.6, k), k) * np.sin(np.linspace(0, np.pi, k)) * 0.4, int(r.uniform(0, m - k)))
    else:
        x = bp(noise(m, r), 1500, 6000) * 0.7 * (0.85 + 0.15 * np.sin(2 * np.pi * 2.3 * t)) + lp(noise(m, r), 500) * 0.4
        for _ in range(25):       # crystal ticks
            k = n_of(0.02)
            place(x, sine(r.uniform(2500, 3500), k) * expdec(k, 0.005) * 0.25, int(r.uniform(0, m - k)))
    return loop_finish(seamless(x, n), 5500, 0.75)


def freeze_snd(seed):
    r = R(seed)
    n = n_of(0.5)
    x = np.zeros(n)
    for _ in range(40):
        k = n_of(0.012)
        place(x, hp(noise(k, r), 2500) * expdec(k, 0.003), int(r.exponential(0.12) * SR) % (n - k), r.uniform(0.2, 0.8))
    x += sine(1800 * (1 + 0.3 * tt(n)), n) * expdec(n, 0.15) * 0.15
    return finish(x, 10, 2, 6000, 0.08, 0.2)


def shatter_snd(seed):
    r = R(seed)
    n = n_of(0.6)
    x = np.zeros(n)
    for _ in range(18):
        k = n_of(0.08)
        place(x, sine(r.uniform(1500, 3200), k) * expdec(k, 0.03) * 0.4 + hp(noise(k, r), 3000) * expdec(k, 0.005),
              int(r.exponential(0.06) * SR) % (n - k), r.uniform(0.3, 1))
    return finish(x + splat(seed)[:n] * 0.3 if len(splat(seed)) >= n else x, 10, 2, 6500, 0.06, 0.2)


# name: (function, variants)
# ---------------------------------------------------------------- environmental traps (kept low & chunky)
def spikes_snd(seed):
    r = R(seed)
    n = n_of(0.45)
    thunk = sine(70 + 60 * np.exp(-tt(n) / 0.03), n) * expdec(n, 0.08)
    scrape = bp(noise(n, r), 600, 2200) * ar(n, 0.003, 0.06) * 0.7
    return finish(mix((drive(thunk, 2) + scrape, 0), (metal(seed, r.uniform(500, 700), 0.25) * 0.35, 0.01)), 9, 2, 4000)


def vent_snd(seed):
    r = R(seed)
    n = n_of(1.3)
    env = ar(n, 0.04, 0.45)
    hissx = lp(bp(noise(n, r), 300, 3000), 2800) * env
    rumble = lp(noise(n, r), 160) * env * 1.6
    return finish(hissx + rumble, 10, 2, 3500)


def saw_grind(seed):
    r = R(seed)
    n = n_of(0.5)
    t = tt(n)
    grind = drive(saw(85 + 6 * np.sin(t * 40), n) + saw(127, n) * 0.6, 3) * ar(n, 0.02, 0.18)
    grit = bp(noise(n, r), 400, 1800) * ar(n, 0.01, 0.12) * 0.5
    return finish(lp(grind, 1400) + grit, 9, 2, 3000)


def zap_snd(seed):
    r = R(seed)
    n = n_of(0.5)
    buzz = drive(saw(48, n) + saw(73, n) * 0.6, 4) * ar(n, 0.003, 0.14) * 0.6
    cr = np.zeros(n)
    for _ in range(18):
        k = n_of(0.008)
        place(cr, bp(noise(k, r), 500, 2500) * expdec(k, 0.002), int(r.uniform(0, 0.35) * SR), r.uniform(0.3, 1))
    return finish(lp(buzz, 1800) + cr * 0.7, 9, 2, 3500, 0.06, 0.2)


def thunder(seed):
    r = R(seed)
    n = n_of(1.8)
    crack = lp(noise(n, r), 1800) * ar(n, 0.002, 0.05) * 1.2
    roll = lp(noise(n, r), 140) * ar(n, 0.06, 0.7) * 2.2
    boom = sine(40 + 30 * np.exp(-tt(n) / 0.1), n) * expdec(n, 0.4)
    return finish(drive(crack + roll + boom, 1.8), 10, 2, 3200, 0.18, 0.3)


def chomp(seed):
    r = R(seed)
    n = n_of(0.35)
    snap = lp(noise(n, r), 1200) * ar(n, 0.002, 0.03) * 1.3
    crunch = np.zeros(n)
    for _ in range(10):
        k = n_of(0.02)
        place(crunch, bp(noise(k, r), 300, 1600) * expdec(k, 0.006), int(r.uniform(0.01, 0.12) * SR), r.uniform(0.4, 1))
    return finish(mix((snap + crunch, 0), (gurgle(seed, 0.8, 0.3) * 0.5, 0.03)), 9, 2, 3500)


def klaxon(seed):
    n = n_of(1.0)
    t = tt(n)
    f = np.where((t * 4).astype(int) % 2 == 0, 220.0, 165.0)
    ph = np.cumsum(f) / SR
    tone = np.sin(2 * np.pi * ph) + 0.3 * np.sin(4 * np.pi * ph)
    return finish(lp(drive(tone, 1.6), 1200) * ar(n, 0.02, 0.6), 10, 2, 2500, peak=0.7)


def servo(seed):
    r = R(seed)
    n = n_of(0.5)
    t = tt(n)
    whirr = saw(70 + 90 * np.clip(t / 0.4, 0, 1), n) * ar(n, 0.03, 0.2) * 0.5
    clunk = lp(noise(n, r), 500) * expdec(n, 0.03)
    return finish(lp(whirr, 1300) + mix((clunk, 0.38))[:n] * 0.8, 10, 2, 3000)


def tentacle_snd(seed):
    r = R(seed)
    n = n_of(0.7)
    wet = lp(noise(n, r), 700) * ar(n, 0.06, 0.25)
    return finish(mix((wet, 0), (gurgle(seed, 0.6, 0.6) * 0.8, 0.05), (growl(seed) * 0.35, 0.1)), 9, 2, 3000)


def bubble_snd(seed):
    return finish(gurgle(seed, 0.5, 0.5) * 0.6, 10, 2, 2500)



# ---------------------------------------------------------------- heavy weapons
def chaingun(seed):
    r = R(seed)
    base = gun_shaped(seed, r.uniform(0.78, 0.86), 0.24, 0.8, 1.5, 0.05, 2.6, 0.0, 0.0, 4500)
    return finish(base, 10, 2, 4500)


def railgun(seed):
    r = R(seed)
    n = n_of(1.3)
    t = tt(n)
    charge = lp(saw(55 + 120 * np.clip(t / 0.12, 0, 1), n), 900) * ar(n, 0.08, 0.04) * 0.5
    crack = lp(noise(n, r), 3200) * ar(n, 0.002, 0.03)
    boom = sine(38 + 80 * np.exp(-tt(n) / 0.05), n) * expdec(n, 0.35) * 1.4
    tail = sweep_lp(noise(n, r), np.exp(-t / 0.25), 200, 2600) * ar(n, 0.005, 0.45) * 0.9
    shot = np.zeros(n)
    place(shot, crack + boom + tail, n_of(0.1))
    return finish(drive(charge + shot[:n], 1.8), 10, 2, 3800, 0.12, 0.25)


# ---------------------------------------------------------------- barrage / coil / microwave / support gadgets
def barrage(seed):
    """Small missile leaving its tube: soft pop + short hissing whoosh (one per missile in the salvo)."""
    r = R(seed)
    n = n_of(0.42)
    t = tt(n)
    pop = sine(70 + 90 * np.exp(-t / 0.02), n) * expdec(n, 0.05) * 1.1
    puff = lp(noise(n, r), 900) * expdec(n, 0.03) * 0.9
    whoosh = sweep_lp(noise(n, r), np.clip(1 - t / 0.35, 0, 1), 250, 1900) * ar(n, 0.02, 0.12) * 0.7
    return finish(drive(pop + puff + whoosh, 1.6), 10, 2, 3500, 0.05, 0.15)


def coil(seed):
    """Coil discharge: a fat low buzz with a dull crackle on top, kept well under 4 kHz."""
    r = R(seed)
    n = n_of(0.32)
    t = tt(n)
    f = 85 * (1 + 0.25 * np.exp(-t / 0.04)) * r.uniform(0.92, 1.08)
    buzz = drive(saw(f, n) + saw(f * 1.5, n) * 0.4, 3.0) * ar(n, 0.002, 0.07) * 0.55
    cr = np.zeros(n)
    for _ in range(14):
        k = n_of(0.01)
        place(cr, bp(noise(k, r), 400, 2200) * expdec(k, 0.0025), int(r.uniform(0, 0.12) * SR), r.uniform(0.4, 1))
    thump = sine(55 + 60 * np.exp(-t / 0.015), n) * expdec(n, 0.04) * 0.8
    return finish(lp(buzz, 1600) + cr * 0.8 + thump, 9, 2, 3200, 0.05, 0.18)


def microwave(seed):
    """Microwave pulse: a warbling low 'wum' that sweeps down, like a hum being thrown."""
    r = R(seed)
    n = n_of(0.45)
    t = tt(n)
    f = 140 * np.exp(-t / 0.18) + 55
    am = 0.6 + 0.4 * np.sin(2 * np.pi * 28 * t)
    body = (sine(f, n) + 0.35 * saw(f * 0.5, n)) * am * ar(n, 0.01, 0.16)
    hum = lp(noise(n, r), 500) * ar(n, 0.01, 0.12) * 0.35
    return finish(lp(drive(body, 1.8), 1400) + hum, 10, 2, 2400, 0.07, 0.2)


def shield_block(seed):
    """Shot absorbed by the arc shield: muffled thunk with a short fizz."""
    r = R(seed)
    n = n_of(0.25)
    t = tt(n)
    thunk = sine(130 + 120 * np.exp(-t / 0.01), n) * expdec(n, 0.05) * 1.1
    fizz = bp(noise(n, r), 300, 1800) * ar(n, 0.003, 0.05) * 0.5
    return finish(thunk + fizz, 10, 2, 3000)


def shield_down(seed):
    r = R(seed)
    n = n_of(0.7)
    t = tt(n)
    f = 220 * np.exp(-t / 0.25) + 40
    wind = lp(saw(f, n), 1200) * ar(n, 0.005, 0.3) * 0.7
    crack = lp(noise(n, r), 1500) * ar(n, 0.002, 0.06)
    return finish(drive(wind + crack, 1.6), 10, 2, 2800, 0.08, 0.2)


def shield_up(seed):
    n = n_of(0.5)
    t = tt(n)
    f = 70 + 160 * np.clip(t / 0.35, 0, 1)
    rise = lp(saw(f, n) + sine(f * 2, n) * 0.4, 1300) * ar(n, 0.08, 0.15) * 0.7
    return finish(rise, 10, 2, 2600)



SOUNDS = {
    "shot_nuke": (nuke_launch, 2),
    "nuke_blast": (nuke_blast, 2),
    "shot_saw": (saw_launch, 3),
    "saw_bounce": (saw_bounce, 4),
    "chem_loop": (lambda s: spray_loop(s, "chem"), 1),
    "cryo_loop": (lambda s: spray_loop(s, "cryo"), 1),
    "freeze": (freeze_snd, 3),
    "shatter": (shatter_snd, 3),
    "flame_loop": (flame_loop, 1),
    "static_loop": (static_loop, 1),
    "fireball": (fireball, 3),
    "wretch_blink": (wretch_blink, 3),
    "tongue": (tongue, 3),
    "stalker_screech": (stalker_screech, 3),
    "mimic_scream": (mimic_scream, 2),
    "crumble": (crumble, 3),
    "shot_pistol": (lambda s: gun_shaped(s, R(s).uniform(1.1, 1.25), 0.25, 0.9, 0.7, 0.05), 5),
    "shot_revolver": (lambda s: gun_shaped(s, R(s).uniform(0.7, 0.8), 0.6, 1.2, 1.4, 0.14, 3.0, 0.13, 0.35), 4),
    "shot_smg": (lambda s: gun_shaped(s, R(s).uniform(1.25, 1.4), 0.18, 0.8, 0.6, 0.035), 6),
    "shot_shotgun": (shotgun, 4),
    "shot_assault": (lambda s: gun_shaped(s, R(s).uniform(0.9, 1.0), 0.32, 1.2, 1.1, 0.07), 6),
    "shot_sniper": (sniper, 3),
    "shot_grenade": (thoomp, 3),
    "shot_rocket": (rocket_launch, 3),
    "shot_laser": (laser, 5),
    "shot_beam": (beam, 4),
    "shot_plasma": (plasma, 4),
    "shot_flame": (flame, 6),
    "reload": (reload_snd, 3),
    "empty": (empty_click, 2),
    "swap": (swap, 2),
    "weapon_pickup": (weapon_pickup, 2),
    "tink": (tink, 4),
    "shock": (shock_snd, 3),
    "acid_spit": (spit, 3),
    "sizzle": (sizzle, 3),
    "brute_roar": (roar, 3),
    "stomp": (stomp, 4),
    "turret_shot": (turret_shot, 4),
    "turret_beep": (beep, 1),
    "walker_rocket": (lambda s: rocket_launch(s, 0.6), 3),
    "bloater_pop": (bloater_pop, 3),
    "skull_screech": (skull_screech, 3),
    "death_brute": (death_brute, 2),
    "death_skull": (skull_death, 3),
    "shot": (lambda s: gun(s, R(s).uniform(0.88, 1.12)), 6),
    "shot_spread": (spread, 4),
    "explosion": (lambda s: explosion(s, 1.0), 3),
    "explosion_small": (lambda s: explosion(s, 0.45), 3),
    "enemy_shot": (enemy_shot, 3),
    "hit_flesh": (hit_flesh, 5),
    "hit_metal": (lambda s: metal(s, None, 0.25), 4),
    "ricochet": (ricochet, 4),
    "splat": (splat, 6),
    "bones": (bones, 5),
    "clatter": (clatter, 5),
    "death_zombie": (growl, 4),
    "death_spider": (shriek, 3),
    "death_leech": (lambda s: gurgle(s, 1.0, 0.6), 3),
    "death_drone": (zap_death, 3),
    "lunge": (hiss, 3),
    "spawn": (spawn, 3),
    "hive_death": (hive_death, 2),
    "hurt": (hurt, 3),
    "player_death": (player_death, 1),
    "pickup": (pickup, 1),
    "power": (power, 1),
    "portal": (portal, 1),
    "step": (step, 5),
    "start": (start, 1),
    "trap_spikes": (spikes_snd, 3), "trap_vent": (vent_snd, 3), "trap_saw": (saw_grind, 3), "zap": (zap_snd, 3),
    "thunder": (thunder, 3), "chomp": (chomp, 3), "klaxon": (klaxon, 1), "servo": (servo, 2), "tentacle": (tentacle_snd, 3),
    "bubble": (bubble_snd, 3),
    "shot_chaingun": (chaingun, 6), "shot_railgun": (railgun, 2),
    "shot_barrage": (barrage, 5), "shot_coil": (coil, 5), "shot_microwave": (microwave, 4),
    "shield_block": (shield_block, 4), "shield_down": (shield_down, 1), "shield_up": (shield_up, 1),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1:]
    for name, (fn, count) in SOUNDS.items():
        if only and name not in only:
            continue
        for v in range(count):
            seed = sum(map(ord, name)) * 31 + v * 7 + 1
            x = fn(seed)
            write(os.path.join(OUT, "%s_%d.wav" % (name, v)), x)
        print("sfx", name, count)


if __name__ == "__main__":
    main()

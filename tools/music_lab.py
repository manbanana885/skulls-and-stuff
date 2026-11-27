"""Music lab: ~35-second darksynth sketches for choosing the soundtrack's direction.

Original pieces in the aggressive 80s-horror darksynth vein (think Carpenter Brut / GosT / Perturbator /
Megadrive 198X): distorted growl and reese basses pumping against the kick, gated-reverb snares and toms,
brass stabs, sequencer arps, gliding leads, Karplus-Strong metal guitars, saturated master.

    python tools/music_lab.py [name ...]   ->  samples/music/<nn>_<name>.wav
"""
import os
import sys
import time
import random
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsp import (SR, n_of, tt, R, expdec, ar, adsr, noise, saw, pulse, sine, lp, hp, bp, sweep_lp, drive, crush,  # noqa: E402
                 shift, reverb_ir, gated_ir, convolve, place, normalize, write)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "samples", "music")
TAU = 2 * np.pi

NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
        "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def m(name):
    return 12 * (int(name[-1]) + 1) + NOTE[name[:-1]]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


CH = {"m": [0, 3, 7], "M": [0, 4, 7], "m7": [0, 3, 7, 10], "M7": [0, 4, 7, 11], "m9": [0, 3, 7, 10, 14], "7": [0, 4, 7, 10],
      "sus4": [0, 5, 7], "5": [0, 7, 12], "dim": [0, 3, 6], "m6": [0, 3, 7, 8]}


def chord(root, kind):
    return [root + i for i in CH[kind]]


def tail(x, d=0.02):
    k = min(len(x), n_of(d))
    x = x.copy()
    x[-k:] *= np.linspace(1, 0, k)
    return x


_cache = {}


def cached(fn):
    def wrap(*a):
        key = (fn.__name__,) + tuple(tuple(v) if isinstance(v, list) else v for v in a)
        if key not in _cache:
            _cache[key] = fn(*a)
        return _cache[key]
    return wrap


# ================================================================ instruments
@cached
def ks(f, dur, bright=0.5, sustain=0.996, seed=0):
    """Karplus-Strong plucked string. Delay line processed a period at a time, so it stays fast in numpy."""
    n = n_of(dur)
    Li = max(2, int(round(SR / f - 0.5)))
    exc = lp(noise(Li + 1, R(seed)), 500 + bright * 9000)
    exc -= exc.mean()
    x = np.zeros(n)
    x[:min(n, len(exc))] = exc[:n]
    P = Li + 1
    y = np.zeros(n + P)
    g = sustain * 0.5
    for s in range(0, n, Li):
        e = min(s + Li, n)
        i = np.arange(s, e) + P
        y[i] = x[s:e] + g * (y[i - Li] + y[i - Li - 1])
    return tail(y[P:] * 2.5)


@cached
def string(f, dur, pick=0.13, bright=0.8, sustain=0.9985, seed=0):
    """Plucked steel string: Karplus-Strong with a pick-position comb on the excitation (picking near the bridge
    thins the tone the way a real pick does) and the pluck shaped by how hard it was hit."""
    n = n_of(dur)
    Li = max(2, int(round(SR / f - 0.5)))
    r = R(seed)
    exc = lp(r.uniform(-1, 1, Li + 1), 400 + bright * 7000)
    k = max(1, int(pick * Li))
    exc = exc - np.roll(exc, k)
    exc -= exc.mean()
    x = np.zeros(n)
    x[:min(n, len(exc))] = exc[:n]
    P = Li + 1
    y = np.zeros(n + P)
    g = sustain * 0.5
    for s0 in range(0, n, Li):
        e = min(s0 + Li, n)
        i = np.arange(s0, e) + P
        y[i] = x[s0:e] + g * (y[i - Li] + y[i - Li - 1])
    return y[P:] * 2.0


def amp_cab(x, gain=7.0, chug=False):
    """Light mid push -> two asymmetric soft-clip stages -> 4x12 cab: low thump, scooped low-mids, a little bite,
    then a steep roll-off so there's no fizz."""
    x = hp(x, 75)
    x = x + bp(x, 700, 1400) * 0.5
    x = np.tanh(x * gain + 0.25) - np.tanh(0.25)
    x = lp(x, 6000)
    x = np.tanh(x * 2.0) / np.tanh(2.0)
    x = x + lp(x, 240, 2) * (4.0 if chug else 3.0)          # cabinet thump / body
    x = x - bp(x, 450, 1200) * 0.6                           # metal scoop
    x = x + bp(x, 2200, 3400) * 0.12                         # pick bite
    x = lp(x, 4800, 4)
    return hp(x, 55) * 0.4


@cached
def guitar(root, dur, mute=False, seed=0):
    """Power chord (root, fifth, octave) on three strings through amp_cab. Six round-robin takes per note via seed;
    palm mutes use a dull, heavily damped pluck."""
    f = hz(root)
    r = R(1000 + seed)
    n = n_of(dur + (0.02 if mute else 0.08))
    x = np.zeros(n)
    for k, (ratio, w) in enumerate(((1.0, 1.0), (1.4983, 0.85), (2.0, 0.45))):
        cents = r.uniform(-4, 4)
        fk = f * ratio * 2 ** (cents / 1200)
        st = string(fk, n / SR, r.uniform(0.1, 0.17), 0.25 if mute else r.uniform(0.6, 0.85), 0.972 if mute else 0.9988,
                    seed * 11 + k)
        st = shift(st, n_of(r.uniform(0, 0.006)) * k, n)          # strum: strings a few ms apart
        x += st * w
    if mute:
        x *= ar(n, 0.001, 0.07)
    y = amp_cab(x, 5.5 if mute else 7.0, mute)
    return tail(y, 0.03 if not mute else 0.012)


@cached
def fm(f, dur, ratio, index, idecay, a=0.002, decay=0.5, floor=0.0):
    n = n_of(dur)
    t = tt(n)
    I = index * (floor + (1 - floor) * np.exp(-t / idecay))
    y = np.sin(TAU * f * t + I * np.sin(TAU * f * ratio * t))
    return tail(y * ar(n, a, decay))


def bell(f, dur=3.0):
    return fm(f, dur, 3.5, 5.0, 0.5, 0.001, dur * 0.3) * 0.6 + fm(f * 2.0, dur, 1.41, 2.0, 0.3, 0.001, dur * 0.15) * 0.25


def epiano(f, dur=2.0):
    x = fm(f, dur, 1.0, 1.6, 0.5, 0.002, 0.9) * 0.6
    tine = fm(f, min(0.3, dur), 14.0, 1.2, 0.04, 0.001, 0.06) * 0.15
    x[:len(tine)] += tine
    return x


@cached
def clang(f):
    n = n_of(1.6)
    x = fm(f, 1.6, 2.76, 9.0, 0.25, 0.001, 0.45) + fm(f * 1.41, 1.6, 3.17, 6.0, 0.15, 0.001, 0.3) * 0.6
    x[:n_of(0.03)] += bp(noise(n_of(0.03), R(int(f))), 800, 4000) * 0.6
    return lp(x, 6000) * 0.5


@cached
def blip(f):
    return crush(fm(f, 0.16, 2.0, 3.0, 0.03, 0.001, 0.06), 6, 3) * 0.6


@cached
def fmbass(f, dur, index=2.5):
    n = n_of(dur + 0.05)
    t = tt(n)
    I = index * (0.25 + 0.75 * np.exp(-t / 0.12))
    y = np.sin(TAU * f * t + I * np.sin(TAU * f * t)) + 0.5 * sine(f / 2, n)
    return drive(tail(y * adsr(n, 0.003, 0.2, 0.75, 0.04, dur)) * 0.8, 2.0)


@cached
def subbass(f, dur, round_=True):
    n = n_of(dur + 0.08)
    x = sine(f, n) + 0.25 * sine(2 * f, n) + 0.12 * lp(saw(f, n), 400)
    return drive(x * adsr(n, 0.02 if round_ else 0.003, 0.3, 0.85, 0.07, dur) * 0.7, 1.4)


@cached
def organ(midis, dur, bright=1.0):
    n = n_of(dur + 0.15)
    t = tt(n)
    x = np.zeros(n)
    rr = R(sum(midis))
    for mm in midis:
        f = hz(mm)
        for h, w in zip((0.5, 1, 2, 3, 4, 6, 8), (0.5, 1, 0.6, 0.3 * bright, 0.35 * bright, 0.12 * bright, 0.15 * bright)):
            if f * h < 7000:
                x += w * sine(f * h, n, rr.random())
    x *= adsr(n, 0.012, 0.08, 1.0, 0.12, dur) / max(1, len(midis)) ** 0.6
    x[:n_of(0.008)] += bp(noise(n_of(0.008), rr), 1000, 3500) * 0.15      # key click
    rot = np.sin(TAU * 5.6 * t)                                            # rotating speaker
    return (drive(x * (1 + 0.22 * rot) * 0.5, 1.3), drive(x * (1 - 0.22 * rot) * 0.5, 1.3))


FORMANTS = {"a": (800, 1150, 2900), "o": (450, 800, 2830), "u": (325, 700, 2530), "e": (400, 1600, 2700)}


@cached
def choir(midis, dur, vowel="a", seed=0, attack=0.7):
    n = n_of(dur + 1.0)
    t = tt(n)
    r = R(seed)
    x = np.zeros(n)
    for mm in midis:
        f = hz(mm)
        for k in range(4):
            vib = 1 + 0.005 * np.sin(TAU * r.uniform(4.4, 5.4) * t + r.random() * TAU)
            x += saw(f * (1 + r.uniform(-0.006, 0.006)) * vib, n, r.random())
    y = np.zeros(n)
    for f0, g in zip(FORMANTS[vowel], (1.0, 0.55, 0.2)):
        y += bp(x, f0 * 0.88, f0 * 1.12) * g
    return tail(y * adsr(n, attack, 0.6, 0.85, 0.9, dur) * 0.22 / max(1, len(midis)) ** 0.5)


def choir2(midis, dur, vowel="a", attack=0.7):
    return (choir(midis, dur, vowel, 1, attack), choir(midis, dur, vowel, 2, attack))


@cached
def supersaw(midis, dur, cutoff=2500, attack=0.02, release=0.3, seed=0):
    n = n_of(dur + release + 0.1)
    r = R(seed)
    L, Rr = np.zeros(n), np.zeros(n)
    for mm in midis:
        f = hz(mm)
        for k in range(7):
            s = saw(f * (1 + (k - 3) * 0.0045), n, r.random())
            if k == 3:
                L += s * 0.7
                Rr += s * 0.7
            elif k % 2:
                L += s
            else:
                Rr += s
    env = adsr(n, attack, 0.3, 0.8, release, dur) * 0.12 / max(1, len(midis)) ** 0.5
    return tail(lp(L, cutoff) * env), tail(lp(Rr, cutoff) * env)


@cached
def lead(midi, dur, bright=3500):
    f = hz(midi)
    n = n_of(dur + 0.3)
    t = tt(n)
    vib = 1 + 0.007 * np.sin(TAU * 5.3 * t) * np.clip((t - 0.2) / 0.3, 0, 1)
    x = saw(f * vib, n) + 0.6 * saw(f * vib * 1.006, n, 0.3) + 0.4 * pulse(f * vib * 0.5, n, 0.4)
    x = sweep_lp(x, 0.4 + 0.6 * expdec(n, 0.4), 700, bright)
    return drive(tail(x * adsr(n, 0.02, 0.4, 0.75, 0.25, dur)) * 0.35, 1.5)


@cached
def horn(midi, dur):
    f = hz(midi)
    n = n_of(dur + 0.3)
    t = tt(n)
    swell = np.clip(t / 0.25, 0, 1)
    vib = 1 + 0.004 * np.sin(TAU * 5 * t)
    x = saw(f * vib, n) + saw(f * 1.005 * vib, n, 0.4) + 0.5 * saw(f * 0.5 * vib, n, 0.1)
    x = sweep_lp(x, 0.3 + 0.6 * swell * (0.6 + 0.4 * expdec(n, 0.8)), 300, 2600)
    return drive(tail(x * adsr(n, 0.08, 0.5, 0.8, 0.25, dur)) * 0.3, 1.6)


@cached
def drone(midi, dur, seed=0):
    n = n_of(dur)
    t = tt(n)
    f = hz(midi)
    x = saw(f, n) + saw(f * 1.5 * 1.003, n, 0.3) * 0.6 + saw(f * 0.998, n, 0.6) + sine(f / 2, n)
    env01 = 0.5 + 0.5 * np.sin(TAU * t / 11.0 + seed)
    return sweep_lp(x, env01, 120, 1400) * np.clip(t / 3, 0, 1) * 0.25


# ---- drums
@cached
def kick(kind="tight"):
    if kind == "punch":
        return punch()
    if kind == "boom":
        n = n_of(0.9)
        t = tt(n)
        x = sine(40 + 85 * np.exp(-t / 0.05), n) * ar(n, 0.001, 0.45)
    elif kind == "ind":
        n = n_of(0.4)
        t = tt(n)
        x = np.tanh(sine(48 + 140 * np.exp(-t / 0.025), n) * ar(n, 0.001, 0.2) * 3.5)
        x += lp(noise(n, R(4)), 2500) * expdec(n, 0.006) * 0.5
    else:
        n = n_of(0.45)
        t = tt(n)
        x = sine(50 + 120 * np.exp(-t / 0.022), n) * ar(n, 0.001, 0.22) + lp(noise(n, R(1)), 3000) * expdec(n, 0.003) * 0.35
    return drive(x, 1.5)


@cached
def snare(kind="gate", var=0):
    r = R(10 + var)
    if kind == "rim":
        n = n_of(0.12)
        return (bp(noise(n, r), 1400, 3200) * expdec(n, 0.012) + sine(420, n) * expdec(n, 0.02) * 0.6) * 0.8
    if kind == "clap":
        n = n_of(0.4)
        x = np.zeros(n)
        for k in range(3):
            place(x, bp(noise(n_of(0.012), r), 900, 2600), n_of(0.011 * k), 0.8)
        x += bp(noise(n, r), 900, 2800) * ar(n, 0.033, 0.11) * 0.6
        return x
    if kind == "doom":
        n = n_of(0.8)
        t = tt(n)
        return drive(sine(170 - 30 * t, n) * expdec(n, 0.1) + bp(noise(n, r), 600, 5000) * expdec(n, 0.22) * 1.1, 1.5)
    n = n_of(0.35)
    t = tt(n)
    return drive(sine(185 - 20 * t, n) * expdec(n, 0.07) * 0.8 + bp(noise(n, r), 1200, 7000) * expdec(n, 0.12), 1.6)


@cached
def hat(open_=False, var=0):
    n = n_of(0.3 if open_ else 0.06)
    return lp(hp(noise(n, R(20 + var)), 6500), 10000) * expdec(n, 0.12 if open_ else 0.018) * 0.4


@cached
def ride(var=0):
    n = n_of(1.4)
    x = sum(pulse(f, n, 0.5) for f in (205, 304, 369, 522, 540, 800)) / 6
    x = hp(x, 5500) * expdec(n, 0.5) * 0.35 + hp(noise(n, R(70 + var)), 7000) * expdec(n, 0.05) * 0.15
    return lp(x, 9500)


@cached
def tom(f, dec=0.3):
    n = n_of(dec * 2.5)
    t = tt(n)
    return sine(f * (1 + 0.5 * np.exp(-t / 0.04)), n) * expdec(n, dec) + bp(noise(n, R(5)), 200, 2500) * expdec(n, 0.02) * 0.3


@cached
def taiko(f=58):
    n = n_of(1.2)
    t = tt(n)
    x = sine(f * (1 + 0.45 * np.exp(-t / 0.05)), n) * ar(n, 0.002, 0.45)
    x += lp(noise(n, R(8)), 1800) * expdec(n, 0.03) * 0.5
    return drive(x * 1.2, 1.4)


@cached
def frame(kind="dum", var=0):
    r = R(40 + var)
    if kind == "dum":
        n = n_of(0.45)
        t = tt(n)
        return sine(105 * (1 + 0.3 * np.exp(-t / 0.03)), n) * expdec(n, 0.18) + lp(noise(n, r), 900) * expdec(n, 0.02) * 0.4
    n = n_of(0.12)
    return bp(noise(n, r), 2000, 5500) * expdec(n, 0.018) * 0.7


@cached
def shaker(var=0):
    n = n_of(0.09)
    return hp(noise(n, R(60 + var)), 4500) * ar(n, 0.012, 0.03) * 0.25


@cached
def crash():
    n = n_of(2.5)
    return lp(hp(noise(n, R(30)), 3500), 9500) * ar(n, 0.002, 0.8) * 0.35


@cached
def drip(f):
    n = n_of(0.12)
    t = tt(n)
    return sine(f * (1 + 1.4 * np.clip(t / 0.05, 0, 1)), n) * ar(n, 0.001, 0.025) * 0.5


@cached
def riser(dur):
    n = n_of(dur)
    t = tt(n)
    env = (t / dur) ** 2
    return sweep_lp(hp(noise(n, R(77)), 200), env, 200, 8000) * env * 0.4


# ================================================================ effects + mixer
def chorus(x2, depth_ms=5.0, rate=0.35):
    n = x2.shape[1]
    idx = np.arange(n, dtype=float)
    out = np.empty_like(x2)
    for c in range(2):
        d = n_of(0.012) + n_of(depth_ms / 1000) * (0.5 + 0.5 * np.sin(TAU * rate * idx / SR + c * np.pi))
        out[c] = 0.7 * x2[c] + 0.6 * np.interp(idx - d, idx, x2[c])
    return out


def tape_echo(x2, delay, fb, taps=6, dark=3200, pingpong=True):
    mono = x2.mean(axis=0)
    out = np.zeros_like(x2)
    d = n_of(delay)
    for k in range(1, taps + 1):
        y = lp(hp(mono, 150 + 40 * k), max(500, dark - 350 * k)) * fb ** k
        ch = (k % 2) if pingpong else None
        if ch is None:
            place(out[0], y, k * d)
            place(out[1], y, k * d)
        else:
            place(out[ch], y, k * d, 1.3)
    return out


class Clock:
    """Beats (quarter notes) -> seconds, with swing on 16th offbeats and humanized timing."""

    def __init__(self, bpm, swing=0.0, human=0.004, seed=1):
        self.q = 60.0 / bpm
        self.swing = swing
        self.human = human
        self.r = random.Random(seed)

    def __call__(self, beat):
        s16 = beat * 4
        extra = 0.0
        if self.swing and abs(s16 - round(s16)) < 1e-6 and int(round(s16)) % 2:
            extra = self.swing * self.q / 4
        return max(0.0, beat * self.q + extra + self.r.gauss(0, self.human))

    def d(self, beats):
        return beats * self.q


# mix level (active RMS, dB) each kind of part is balanced to, and the low cut that keeps it out of the bass's way
ROLE = {"kick": (-15, 0), "beat": (-15, 0), "drum": (-16, 0), "snare": (-18, 120), "clap": (-19, 150), "rim": (-21, 200),
        "hat": (-25, 3000), "cym": (-24, 2000), "perc": (-21, 150), "bass": (-16, 0), "pad": (-20, 160), "organ": (-16, 70),
        "choir": (-16, 160), "bell": (-19, 300), "lead": (-15, 180), "melo": (-16, 180), "stab": (-18, 150), "arp": (-19, 200),
        "clang": (-21, 200), "fx": (-23, 150), "skank": (-17, 200), "horn": (-15, 120), "gtrL": (-15, 90), "gtrR": (-15, 90),
        "drone": (-17, 45), "swell": (-18, 120), "keys": (-17, 150), "wind": (-30, 200), "blip": (-18, 300),
        "growl": (-15, 0), "reese": (-16, 0), "gtr": (-17, 90), "tom": (-18, 60), "lead2": (-18, 180)}


def active_db(x):
    mono = np.abs(x).mean(axis=0)
    env = lp(mono, 4)
    on = env > env.max() * 0.12
    if not on.any():
        return -120.0
    return 10 * np.log10(np.mean(x[:, on] ** 2) + 1e-12)


class Mix:
    def __init__(self, sec, seed=0):
        self.sec = sec
        self.N = n_of(sec + 8)
        self.bus = {}
        self.opts = {}
        self.kicks = []
        self.r = random.Random(seed)

    def setup(self, name, **o):
        self.opts[name] = o

    def add(self, bus, x, t, gain=1.0, pan=0.0, hum=0.15):
        if bus not in self.bus:
            self.bus[bus] = np.zeros((2, self.N))
        B = self.bus[bus]
        gain *= 1 - self.r.random() * hum
        s = n_of(max(0.0, t))
        if isinstance(x, tuple):
            place(B[0], x[0], s, gain)
            place(B[1], x[1], s, gain)
        else:
            a = (pan + 1) * np.pi / 4
            place(B[0], x, s, gain * np.cos(a) * 1.414)
            place(B[1], x, s, gain * np.sin(a) * 1.414)

    def kick(self, t, kind="tight", gain=1.0, bus="kick"):
        self.add(bus, kick(kind), t, gain, hum=0.05)
        self.kicks.append(n_of(t))

    def render(self, verb=2.5, damp=5000, master_lp=10000, fade=2.5, duck_tau=0.13, drive=1.4):
        N = self.N
        sc = np.ones(N)
        curve = 1 - np.exp(-tt(n_of(0.6)) / duck_tau)
        for p in self.kicks:
            seg = sc[p:p + len(curve)]
            np.minimum(seg, curve[:len(seg)], out=seg)
        out = np.zeros((2, N))
        send = np.zeros((2, N))
        for name, x in self.bus.items():
            o = self.opts.get(name, {})
            level, cut = ROLE.get(name, (-18, 100))
            level = o.get("level", level)
            if cut:
                x = hp(x, cut)
            x = x * 10 ** ((level - active_db(x)) / 20)
            if o.get("crush"):
                x = np.stack([crush(c, *o["crush"]) for c in x])
            if o.get("hp"):
                x = hp(x, o["hp"])
            if o.get("lp"):
                x = lp(x, o["lp"])
            if o.get("chorus"):
                x = chorus(x, *o["chorus"])
            if o.get("gate"):          # 80s gated reverb
                ir = gated_ir()
                x = x + np.stack([convolve(ch, ir) for ch in x]) * o["gate"]
            if o.get("echo"):
                x = x + tape_echo(x, *o["echo"])
            if o.get("duck"):
                x = x * (1 - o["duck"] * (1 - sc))
            g = o.get("gain", 1.0)
            out += x * g
            send += x * g * o.get("verb", 0.15)
        irL, irR = reverb_ir(verb, 99, damp)
        out[0] += convolve(send[0], irL)
        out[1] += convolve(send[1], irR)
        out = lp(hp(out, 30), master_lp)
        out = out - lp(out, 60) * 0.35 + bp(out, 1200, 4000) * 0.25       # tame the sub, a little presence
        pk = np.max(np.abs(out)) or 1
        out = np.tanh(out / pk * drive) / np.tanh(drive)       # glue / saturation
        out = out[:, :n_of(self.sec)]
        out[:, :n_of(0.03)] *= np.linspace(0, 1, n_of(0.03))
        out[:, -n_of(fade):] *= np.linspace(1, 0, n_of(fade))
        return normalize(out.T, 0.89)


# ================================================================ darksynth instruments
@cached
def punch():
    """80s drum-machine kick: fast pitch dive, click, a little drive."""
    n = n_of(0.42)
    t = tt(n)
    x = sine(52 + 170 * np.exp(-t / 0.018), n) * ar(n, 0.001, 0.26)
    x += hp(noise(n, R(3)), 2500) * expdec(n, 0.0025) * 0.5
    return drive(x * 1.3, 2.2)


@cached
def growl(midi, dur, bright=1.0, drv=4.0):
    """Distorted saw bass with a snappy filter envelope - the core darksynth bass."""
    f = hz(midi)
    n = n_of(dur + 0.03)
    x = saw(f * 1.005, n) + saw(f * 0.995, n, 0.4) + 0.7 * pulse(f * 0.5, n, 0.5)
    x = sweep_lp(x, 0.12 + 0.88 * expdec(n, 0.07 + 0.05 * bright) * bright, 140, 5500)
    x *= adsr(n, 0.002, 0.1, 0.85, 0.02, dur)
    return tail(lp(np.tanh(x * drv) * 0.5, 6500), 0.01)


@cached
def reese2(midi, dur, cutoff=1600, drv=3.0):
    """Wide phasing reese with a sine sub, overdriven."""
    f = hz(midi)
    n = n_of(dur + 0.03)
    x = saw(f * 1.008, n) + saw(f * 0.992, n, 0.5) + saw(f, n, 0.2) * 0.6
    x = lp(x, cutoff) + 0.8 * sine(f / 2, n)
    x *= adsr(n, 0.003, 0.15, 0.9, 0.03, dur)
    return tail(np.tanh(x * drv) * 0.45, 0.01)


@cached
def pluck2(midi, dur=0.2, top=6000):
    """Sequencer pluck: pulse + saw through a fast-closing filter."""
    f = hz(midi)
    n = n_of(dur + 0.15)
    x = pulse(f, n, 0.25) + 0.6 * saw(f * 1.004, n, 0.2)
    x = sweep_lp(x, expdec(n, 0.05), 350, top)
    return tail(x * ar(n, 0.001, 0.14) * 0.4)


@cached
def stab(midis, dur, top=5000):
    """CS-80-ish brass stab: detuned saws with a swelling-then-closing filter."""
    n = n_of(dur + 0.2)
    t = tt(n)
    x = np.zeros(n)
    for mm in midis:
        f = hz(mm)
        x += saw(f * 1.006, n) + saw(f * 0.994, n, 0.5) + 0.5 * saw(f * 2.003, n, 0.25)
    env01 = np.clip(t / 0.025, 0, 1) * (0.55 + 0.45 * expdec(n, 0.18))
    x = sweep_lp(x, env01, 250, top)
    return tail(drive(x * adsr(n, 0.006, 0.18, 0.65, 0.12, dur) * 0.2 / max(1, len(midis)) ** 0.4, 1.8))


def lead_line(events, total, glide=0.06, bright=4500, drv=2.5, detune=0.007, vib=0.007):
    """Monophonic lead with portamento between notes and delayed vibrato. events: (start_s, dur_s, midi)."""
    from scipy.signal import lfilter, lfilter_zi
    n = n_of(total)
    f = np.zeros(n)
    g = np.zeros(n)
    for st, du, mid in sorted(events):
        s, e = n_of(st), min(n, n_of(st + du))
        f[s:e] = hz(mid)
        g[s:e] = 1.0
    idx = np.where(f > 0, np.arange(n), 0)
    np.maximum.accumulate(idx, out=idx)
    f = f[idx]
    first = int(np.argmax(f > 0))
    f[:first] = f[first]

    def smooth(x, tau):
        a = 1 - np.exp(-1 / (tau * SR))
        b_, a_ = [a], [1, -(1 - a)]
        return lfilter(b_, a_, x, zi=lfilter_zi(b_, a_) * x[0])[0]
    f = np.exp(smooth(np.log(f), glide))
    t = tt(n)
    f = f * (1 + vib * np.sin(TAU * 5.4 * t) * smooth(g, 0.35) ** 2)
    env = smooth(g, 0.012)
    x = saw(f, n) + 0.7 * saw(f * (1 + detune), n, 0.3) + 0.35 * pulse(f * 0.5, n, 0.4)
    x = np.tanh(lp(x, bright) * drv) / np.tanh(drv)
    return lp(x, bright * 1.4) * env * 0.3


def fill(mx, c, start, beats, freqs=(210, 180, 150, 125, 100, 82)):
    k = int(beats * 4)
    for i in range(k):
        mx.add("tom", tom(freqs[min(len(freqs) - 1, i * len(freqs) // k)], 0.22), c(start + i / 4), 0.6 + 0.4 * i / k,
               0.6 - 1.2 * i / max(1, k - 1))


def beat(mx, c, b0, bar, kicks=(0, 1, 2, 3), snares=(1, 3), hats=16, use_ride=False):
    for k in kicks:
        mx.kick(c(b0 + k), "punch")
    for s in snares:
        mx.add("snare", snare("gate", bar % 2), c(b0 + s), 1.0)
        mx.add("snare", snare("clap", bar % 2), c(b0 + s), 0.45)
    for i in range(hats):
        st = i * 4 / hats
        if use_ride:
            mx.add("hat", ride(i % 3), c(b0 + st), 0.5)
        else:
            mx.add("hat", hat(hats == 8 and i % 2 == 1, i % 3), c(b0 + st), 0.45 if i % 2 else 0.28)


def snare_roll(mx, c, start, beats=4):
    k = int(beats * 4)
    for i in range(k):
        mx.add("snare", snare("gate", i % 2), c(start + i / 4), 0.2 + 0.8 * (i / k) ** 2)


# ================================================================ darksynth sketches
def nightcrawler():
    """Carpenter Brut-ish: 118 bpm F minor. Octave-pumping growl bass, horror arp, brass stabs, gated snare,
    a gliding horror lead over a darker B section."""
    c = Clock(118, human=0.003)
    bars = 18
    mx = Mix(c.d(bars * 4) + 1.0)
    mx.setup("growl", duck=0.8)
    mx.setup("arp", duck=0.5, verb=0.25, echo=(c.d(0.75), 0.35, 4, 4500))
    mx.setup("stab", duck=0.5, verb=0.35)
    mx.setup("pad", duck=0.6, verb=0.5, chorus=(6, 0.3))
    mx.setup("snare", gate=0.7, verb=0.25)
    mx.setup("tom", gate=0.6, verb=0.2)
    mx.setup("lead", verb=0.45, echo=(c.d(0.75), 0.3, 3, 4000))
    Fm, Db, Eb, C, Bbm = (m("F2"), "m"), (m("Db2"), "M"), (m("Eb2"), "M"), (m("C2"), "M"), (m("Bb1"), "m")
    prog = [Fm, Db, Eb, C] + [Fm, Fm, Db, Eb, Fm, C] + [Fm, Db, Bbm, C, Fm, Db] + [Fm, Fm]
    for bar, (r0, q) in enumerate(prog):
        b0 = bar * 4
        ch = chord(r0 + 24, q)
        intro, outro = bar < 4, bar >= 16
        arp = [ch[0], ch[2], ch[1], ch[2], ch[0] + 12, ch[2], ch[1] + 12, ch[2]]
        top = 1200 + 4800 * (bar / 4) if intro else 6000
        for i in range(16):
            mx.add("arp", pluck2(arp[i % 8] + 12, 0.18, top), c(b0 + i / 4), 0.5, (-0.4, 0.4)[i % 2])
        if not intro:
            for i in range(16):
                o = 12 if i % 2 else 0
                if i == 14 and bar % 2:
                    o = 1
                mx.add("growl", growl(r0 + o, c.d(0.25) * 0.8, 1.0 if bar >= 10 else 0.7), c(b0 + i / 4), 0.9 if i % 4 == 0 else 0.75)
            mx.add("pad", supersaw(ch, c.d(4) * 0.98, 2400, 0.05, 0.4, bar), c(b0), 0.6)
        if 2 <= bar < 4:
            for k in range(4):
                mx.kick(c(b0 + k), "punch")
        if bar == 3:
            snare_roll(mx, c, b0, 4)
        if 4 <= bar < 16:
            beat(mx, c, b0, bar, hats=16)
            if bar % 4 == 3:
                fill(mx, c, b0 + 3, 1)
        if 4 <= bar < 10 or outro:
            for st, ln in ((0, 0.75), (1.5, 0.5), (2.5, 0.5), (3.5, 0.5)):
                mx.add("stab", stab([n + 12 for n in ch], c.d(ln)), c(b0 + st), 0.9)
        if outro:
            mx.kick(c(b0), "punch")
            mx.add("snare", snare("gate", 0), c(b0 + 2), 1.0)
    mel = [(10, 0, 2, "C5"), (10, 2, 1, "Ab4"), (10, 3, 1, "F4"), (11, 0, 1.5, "Ab4"), (11, 1.5, 0.5, "Bb4"), (11, 2, 1, "C5"),
           (11, 3, 1, "Db5"), (12, 0, 2, "F5"), (12, 2, 1, "Db5"), (12, 3, 1, "Bb4"), (13, 0, 1, "C5"), (13, 1, 1, "E4"),
           (13, 2, 1, "G4"), (13, 3, 1, "Bb4"), (14, 0, 1, "Ab4"), (14, 1, 1, "C5"), (14, 2, 2, "F5"), (15, 0, 1, "Eb5"),
           (15, 1, 1, "Db5"), (15, 2, 2, "C5")]
    ev = [(c(b * 4 + st), c.d(ln) * 0.97, m(nn)) for b, st, ln, nn in mel]
    total = c.d(bars * 4) + 1
    mx.add("lead", lead_line(ev, total, 0.05, 5000), 0, 1.0, -0.05)
    mx.add("lead", lead_line([(s, d, n - 12) for s, d, n in ev], total, 0.05, 3000) * 0.5, 0, 1.0, 0.1)
    mx.add("fx", riser(c.d(8)), c(8), 0.8)
    for b in (4, 10, 16):
        mx.add("fx", crash(), c(b * 4), 0.9)
    return mx.render(verb=2.2, damp=6000, master_lp=12000, drive=2.2, duck_tau=0.11)


def black_mass():
    """GosT-ish: 150 bpm D Phrygian. Bit-crushed reese riff with the flat second, double-time kicks, choir,
    a half-time doom breakdown with distorted guitar, then the riff returns with a screaming arp."""
    c = Clock(150, human=0.002)
    bars = 20
    mx = Mix(c.d(bars * 4) + 1.0)
    mx.setup("reese", duck=0.6, crush=(8, 2))
    mx.setup("growl", duck=0.7)
    mx.setup("choir", verb=0.6, duck=0.3)
    mx.setup("snare", gate=0.6, verb=0.3)
    mx.setup("tom", gate=0.6)
    mx.setup("gtr", verb=0.15)
    mx.setup("arp", verb=0.3, echo=(c.d(0.5), 0.3, 3, 5000), duck=0.3)
    D2 = m("D2")
    riff = [0, 0, 12, 0, 1, 0, 0, 12, 0, 0, 3, 0, 1, 0, 13, 12]
    roots = [0, 0, 1, 0, 0, 0, -2, -4]
    chords = {0: [D2 + 12, D2 + 15, D2 + 19], 1: [D2 + 13, D2 + 17, D2 + 20], -2: [D2 + 10, D2 + 14, D2 + 17], -4: [D2 + 8, D2 + 12, D2 + 15]}
    for bar in range(bars):
        b0 = bar * 4
        rt = roots[bar % 8]
        breakdown = 12 <= bar < 16
        if bar % 2 == 0:
            mx.add("choir", choir2([n + 12 for n in chords[rt]], c.d(8) * 0.98, "a", 0.4), c(b0), 0.8)
        if not breakdown:
            for i, o in enumerate(riff):
                cut = 500 + 1500 * min(1, bar / 3) if bar < 4 else 2000
                mx.add("reese", reese2(D2 + rt + o, c.d(0.25) * 0.85, cut, 3.5), c(b0 + i / 4), 0.85)
                if bar >= 4:
                    mx.add("growl", growl(D2 + rt + o - 12 + 12, c.d(0.25) * 0.7, 0.9, 5.0), c(b0 + i / 4), 0.6)
        if bar == 3:
            snare_roll(mx, c, b0, 4)
        if 4 <= bar < 12 or bar >= 16:
            beat(mx, c, b0, bar, kicks=[k / 2 for k in range(8)], hats=8, use_ride=True)
            if bar % 4 == 3:
                fill(mx, c, b0 + 3, 1)
        if breakdown:
            hb = bar - 12
            seq = [[(0, 2, 0), (2, 2, 1)], [(0, 3, 0), (3, 1, -2)], [(0, 2, -4), (2, 2, -5)], [(0, 2, 0), (2, 1, 1), (3, 1, 3)]][hb]
            for st, ln, o in seq:
                for side, sd, pan in (("gtr", 1, -0.8), ("gtr", 2, 0.8)):
                    mx.add(side, guitar(D2 + o, c.d(ln) * 0.97, False, sd + bar), c(b0 + st) + (0.012 if sd == 2 else 0), 0.8, pan)
                mx.add("growl", growl(D2 + o - 12, c.d(ln) * 0.95, 0.4, 3.0), c(b0 + st), 0.8)
            mx.kick(c(b0), "punch")
            mx.kick(c(b0 + 2.75), "punch")
            mx.add("snare", snare("doom", hb % 2), c(b0 + 2), 1.0)
            mx.add("fx", crash(), c(b0), 0.6)
        if bar >= 16:
            scale = [D2 + 36 + s for s in (0, 1, 3, 5, 7, 8, 10, 12)]
            line = [7, 6, 5, 4, 5, 3, 1, 0, 1, 3, 4, 5, 7, 6, 4, 1]
            for i, k in enumerate(line):
                mx.add("arp", pluck2(scale[k] + (1 if rt == 1 and k == 0 else 0), 0.15, 6500), c(b0 + i / 4), 0.5, (-0.5, 0.5)[i % 2])
    for b in (4, 12, 16):
        mx.add("fx", crash(), c(b * 4), 0.9)
    mx.add("fx", riser(c.d(8)), c(8), 0.7)
    mx.add("fx", riser(c.d(8)), c(56), 0.7)
    return mx.render(verb=2.0, damp=5000, master_lp=11000, drive=2.5, duck_tau=0.08)


def turbo():
    """Megadrive 198X-ish: 132 bpm E minor. Palm-muted guitar gallops doubled by the bass, open power chords,
    a synth arp, then a heroic harmonized twin lead over i-VI-III-VII."""
    c = Clock(132, human=0.003)
    bars = 18
    mx = Mix(c.d(bars * 4) + 1.0)
    mx.setup("gtr", verb=0.12)
    mx.setup("growl", duck=0.6)
    mx.setup("arp", duck=0.5, verb=0.25, echo=(c.d(0.75), 0.3, 3, 5000))
    mx.setup("pad", duck=0.5, verb=0.4, chorus=(5, 0.3))
    mx.setup("snare", gate=0.6, verb=0.25)
    mx.setup("tom", gate=0.5)
    mx.setup("lead", verb=0.4, echo=(c.d(0.75), 0.25, 3, 4500))
    mx.setup("lead2", verb=0.4, echo=(c.d(0.75), 0.25, 3, 4500))
    E2, C2, G2, D2, B1 = m("E2"), m("C2"), m("G2"), m("D2"), m("B1")
    prog = [(E2, "m"), (C2, "M"), (G2, "M"), (D2, "M")] * 3 + [(E2, "m"), (C2, "M"), (D2, "M"), (B1, "M")] + [(E2, "m"), (E2, "m")]
    for bar, (r0, q) in enumerate(prog):
        b0 = bar * 4
        ch = chord(r0 + 24, q)
        intro = bar < 4
        gal = [(k + s, ln) for k in range(4) for s, ln in ((0, 0.5), (0.5, 0.25), (0.75, 0.25))]
        for i, (st, ln) in enumerate(gal):
            open_ = st == 0 and not intro
            if open_:
                for sd, pan in ((1, -0.85), (2, 0.85)):
                    mx.add("gtr", guitar(r0, c.d(1) * 0.95, False, sd), c(b0) + (0.01 if sd == 2 else 0), 0.9, pan)
                continue
            if st < 1 and not intro:
                continue
            for sd, pan in ((3, -0.85), (4, 0.85)):
                mx.add("gtr", guitar(r0, c.d(ln) * 0.9, True, sd * 10 + (i * 7 + bar) % 6), c(b0 + st) + (0.009 if sd == 4 else 0),
                       (0.75 if intro else 0.8) * (1.0 if st % 1 == 0 else 0.85), pan)
            if not intro:
                mx.add("growl", growl(r0 - 12 + 12, c.d(ln) * 0.85, 0.6, 3.0), c(b0 + st), 0.8)
        arp = [ch[0], ch[1], ch[2], ch[1] + 12, ch[2] + 12, ch[1] + 12, ch[2], ch[1]]
        for i in range(16):
            mx.add("arp", pluck2(arp[i % 8] + 12, 0.15, 6500), c(b0 + i / 4), 0.45, (-0.5, 0.5)[i % 2])
        if not intro and bar < 16:
            mx.add("pad", supersaw(ch, c.d(4) * 0.98, 2600, 0.05, 0.4, bar), c(b0), 0.5)
            kicks = [k + s for k in range(4) for s in (0, 0.5, 0.75)] if bar >= 8 else (0, 1, 2, 3)
            beat(mx, c, b0, bar, kicks=kicks, hats=8)
            if bar % 4 == 3:
                fill(mx, c, b0 + 2, 2)
        if bar == 3:
            snare_roll(mx, c, b0 + 2, 2)
        if bar >= 16:
            mx.kick(c(b0), "punch")
            mx.add("snare", snare("gate", 1), c(b0 + 2), 0.9)
    mel = [(8, 0, 1, "B4"), (8, 1, 1, "E5"), (8, 2, 1, "F#5"), (8, 3, 1, "G5"), (9, 0, 1.5, "G5"), (9, 1.5, 0.5, "F#5"),
           (9, 2, 1, "E5"), (9, 3, 1, "G5"), (10, 0, 2, "D5"), (10, 2, 1, "B4"), (10, 3, 1, "D5"), (11, 0, 2, "F#5"),
           (11, 2, 1, "E5"), (11, 3, 1, "D5"), (12, 0, 1, "E5"), (12, 1, 0.5, "F#5"), (12, 1.5, 0.5, "G5"), (12, 2, 1, "A5"),
           (12, 3, 1, "B5"), (13, 0, 2, "C6"), (13, 2, 1, "B5"), (13, 3, 1, "G5"), (14, 0, 1, "A5"), (14, 1, 1, "F#5"),
           (14, 2, 1, "D5"), (14, 3, 1, "A5"), (15, 0, 4, "B5")]
    scale = {4, 6, 7, 9, 11, 0, 2}
    ev = [(c(b * 4 + st), c.d(ln) * 0.95, m(nn)) for b, st, ln, nn in mel]
    ev2 = [(s, d, n - 3 if (n - 3) % 12 in scale else n - 4) for s, d, n in ev]
    total = c.d(bars * 4) + 1
    mx.add("lead", lead_line(ev, total, 0.04, 4200, 4.0), 0, 1.0, -0.35)
    mx.add("lead2", lead_line(ev2, total, 0.04, 4000, 4.0), 0, 1.0, 0.35)
    for b in (4, 8, 12, 16):
        mx.add("fx", crash(), c(b * 4), 0.9)
    mx.add("fx", riser(c.d(4)), c(12), 0.6)
    return mx.render(verb=2.0, damp=6000, master_lp=12000, drive=2.2, duck_tau=0.1)


def requiem():
    """Perturbator-ish: 104 bpm C# minor. A gritty 16th sequenced bass whose filter slowly opens, huge gated snare,
    cinematic chords, ping-pong arp, a slow gliding lead over i-VI-iv-V."""
    c = Clock(104, human=0.003)
    bars = 16
    mx = Mix(c.d(bars * 4) + 1.0)
    mx.setup("growl", duck=0.75)
    mx.setup("pad", duck=0.6, verb=0.55, chorus=(7, 0.25))
    mx.setup("arp", duck=0.4, verb=0.3, echo=(c.d(0.75), 0.4, 4, 4000))
    mx.setup("snare", gate=0.9, verb=0.35)
    mx.setup("tom", gate=0.7)
    mx.setup("lead", verb=0.6, echo=(c.d(0.75), 0.35, 4, 3800))
    Cs, A, Fs, Gs = m("C#2"), m("A1"), m("F#2"), m("G#1")
    prog = [(Cs, "m"), (A, "M"), (Fs, "m"), (Gs, "M")] * 4
    acc = [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0]
    for bar, (r0, q) in enumerate(prog):
        b0 = bar * 4
        ch = chord(r0 + 24, q)
        open_ = min(1.0, 0.25 + bar / 10)
        mx.add("pad", supersaw([n + 12 for n in ch] + [ch[0]], c.d(4) * 0.98, 900 + 2200 * open_, 0.2, 0.8, bar), c(b0), 0.7)
        if bar >= 2:
            for i in range(16):
                o = 12 if i in (6, 14) else 0
                mx.add("growl", growl(r0 + o, c.d(0.25) * 0.75, 0.35 + 0.65 * open_ * (1.0 if acc[i] else 0.7), 3.5), c(b0 + i / 4),
                       0.9 if acc[i] else 0.6)
        arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[0] + 24, ch[2] + 12, ch[1] + 12]
        if bar >= 1:
            for i in range(16):
                mx.add("arp", pluck2(arp[i % 6], 0.2, 2500 + 4000 * open_), c(b0 + i / 4), 0.4, (-0.6, 0.6)[i % 2])
        if 4 <= bar:
            beat(mx, c, b0, bar, kicks=(0, 1.5, 2) if bar % 2 == 0 else (0, 1.5, 2, 3.75), hats=16)
            if bar % 4 == 3:
                fill(mx, c, b0 + 3, 1)
        if bar == 3:
            snare_roll(mx, c, b0, 4)
    mel = [(8, 0, 3, "E5"), (8, 3, 0.5, "D#5"), (8, 3.5, 0.5, "C#5"), (9, 0, 2, "C#5"), (9, 2, 2, "E5"), (10, 0, 3, "F#5"),
           (10, 3, 1, "E5"), (11, 0, 2, "D#5"), (11, 2, 2, "C5"), (12, 0, 2, "G#5"), (12, 2, 1, "E5"), (12, 3, 1, "C#5"),
           (13, 0, 2, "E5"), (13, 2, 1, "C#5"), (13, 3, 1, "A4"), (14, 0, 2, "F#5"), (14, 2, 2, "A5"), (15, 0, 4, "G#5")]
    ev = [(c(b * 4 + st), c.d(ln) * 0.97, m(nn)) for b, st, ln, nn in mel]
    mx.add("lead", lead_line(ev, c.d(bars * 4) + 1, 0.09, 3800, 2.0, 0.008, 0.009), 0, 1.0)
    for b in (4, 8, 12):
        mx.add("fx", crash(), c(b * 4), 0.9)
    mx.add("fx", riser(c.d(8)), c(8), 0.7)
    return mx.render(verb=3.0, damp=5000, master_lp=11000, drive=2.0, duck_tau=0.14)


def hunter():
    """Boss-fight darksynth: 140 bpm A minor / Phrygian. Syncopated reese+growl riff hit together with brass stabs
    and kicks, tom-heavy fills, a fast horror arp, then a siren-like gliding lead."""
    c = Clock(140, human=0.002)
    bars = 18
    mx = Mix(c.d(bars * 4) + 1.0)
    mx.setup("reese", duck=0.5)
    mx.setup("growl", duck=0.6)
    mx.setup("stab", duck=0.3, verb=0.3)
    mx.setup("snare", gate=0.7, verb=0.25)
    mx.setup("tom", gate=0.7)
    mx.setup("arp", verb=0.25, echo=(c.d(0.375), 0.3, 3, 5000), duck=0.4)
    mx.setup("lead", verb=0.5, echo=(c.d(0.75), 0.3, 3, 4000))
    A1 = m("A1")
    hits = [(0, 0), (0.75, 0), (1.5, 0), (2.5, 1), (3, 0), (3.5, 12)]
    roots = [0, 0, -4, -5]           # Am Am F E
    for bar in range(bars):
        b0 = bar * 4
        rt = roots[(bar // 2) % 4] if bar < 16 else 0
        q = "M" if rt in (-4, -5) else "m"
        ch = chord(A1 + rt + 24, q)
        intro = bar < 2
        for st, o in hits:
            ln = 0.5 if st < 3.5 else 0.4
            cut = 700 if intro else 2200
            mx.add("reese", reese2(A1 + rt + o, c.d(ln) * 0.9, cut, 3.0), c(b0 + st), 0.85)
            if not intro:
                mx.add("growl", growl(A1 + rt + o + 12, c.d(ln) * 0.8, 1.0, 4.0), c(b0 + st), 0.6)
                if st in (0, 0.75, 1.5):
                    mx.add("stab", stab([n + 12 for n in ch], c.d(0.4)), c(b0 + st), 0.9)
                mx.kick(c(b0 + st), "punch")
        if not intro and bar < 16:
            for s in (1, 3):
                mx.add("snare", snare("gate", bar % 2), c(b0 + s), 1.0)
            for i in range(16):
                mx.add("hat", hat(False, i % 3), c(b0 + i / 4), 0.4 if i % 2 else 0.25)
            if bar % 4 == 3:
                fill(mx, c, b0 + 2, 2, (240, 210, 180, 150, 120, 95, 80))
        if bar == 1:
            snare_roll(mx, c, b0, 4)
        if 6 <= bar < 16:
            line = [12, 13, 12, 7, 12, 13, 15, 13, 12, 8, 7, 3, 7, 8, 12, 13]
            for i, k in enumerate(line):
                mx.add("arp", pluck2(A1 + 36 + rt + k, 0.12, 7000), c(b0 + i / 4), 0.4, (-0.5, 0.5)[i % 2])
    mel = [(10, 0, 2, "E5"), (10, 2, 2, "F5"), (11, 0, 3, "E5"), (11, 3, 1, "C5"), (12, 0, 2, "C5"), (12, 2, 2, "A4"),
           (13, 0, 2, "G#4"), (13, 2, 2, "B4"), (14, 0, 2, "E5"), (14, 2, 2, "F5"), (15, 0, 2, "G#5"), (15, 2, 2, "B5"), (16, 0, 8, "A5")]
    ev = [(c(b * 4 + st), c.d(ln) * 0.97, m(nn)) for b, st, ln, nn in mel]
    mx.add("lead", lead_line(ev, c.d(bars * 4) + 1, 0.12, 4200, 3.0, 0.009, 0.012), 0, 1.0)
    for b in (2, 6, 10, 16):
        mx.add("fx", crash(), c(b * 4), 0.9)
    return mx.render(verb=2.0, damp=6000, master_lp=12000, drive=2.4, duck_tau=0.08)


SKETCHES = [("nightcrawler", nightcrawler, "Carpenter Brut-ish: octave-pumping bass, horror arp, brass stabs, gliding lead"),
            ("black_mass", black_mass, "GosT-ish: 150 bpm crushed reese riff, double kicks, choir, doom-guitar breakdown"),
            ("turbo", turbo, "Megadrive 198X-ish: palm-muted guitar gallops, synth arp, heroic twin lead"),
            ("requiem", requiem, "Perturbator-ish: gritty sequenced bass, huge gated snare, cinematic chords, slow lead"),
            ("hunter", hunter, "boss fight: syncopated reese + stab riff, tom fills, horror arp, siren lead")]


def main():
    os.makedirs(OUT, exist_ok=True)
    want = sys.argv[1:]
    lines = []
    for i, (name, fn, desc) in enumerate(SKETCHES, 1):
        fname = "%02d_%s.wav" % (i, name)
        lines.append(fname)
        if want and name not in want:
            continue
        t0 = time.time()
        _cache.clear()
        x = fn()
        write(os.path.join(OUT, fname), x)
        print("%-12s %4.1fs  (%4.1fs to render)  %s" % (name, len(x) / SR, time.time() - t0, desc))
    with open(os.path.join(OUT, "all_samples.m3u"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

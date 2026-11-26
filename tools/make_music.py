"""Synthesize the darksynth soundtrack -> assets/audio/music/<track>.wav

Original compositions in the style of 80s-horror-inspired darksynth: sidechained saw basses,
gated-reverb snares, ping-pong arps, brass stabs, distorted reese basses.

    python tools/make_music.py [title] [combat] [deep]
"""
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsp import (SR, n_of, tt, R, expdec, ar, adsr, noise, saw, pulse, sine, lp, hp, bp, sweep_lp, drive,  # noqa: E402
                 shift, reverb_ir, gated_ir, convolve, place, normalize, write)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "audio", "music")

NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
        "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def m(name):
    p, o = name[:-1], int(name[-1])
    return 12 * (o + 1) + NOTE[p]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def triad(root, quality):
    return [root, root + (3 if quality == "m" else 4), root + 7]


# ================================================================ instruments
_cache = {}


def cached(fn):
    def wrap(*args):
        key = (fn.__name__,) + tuple(tuple(a) if isinstance(a, list) else a for a in args)
        if key not in _cache:
            _cache[key] = fn(*args)
        return _cache[key]
    return wrap


@cached
def kick(vel=1.0):
    n = n_of(0.45)
    t = tt(n)
    f = 46 + 115 * np.exp(-t / 0.028)
    x = sine(f, n) * ar(n, 0.001, 0.24)
    x += lp(noise(n, R(1)), 3000) * expdec(n, 0.004) * 0.4
    return drive(x * vel, 1.8)


@cached
def snare(var=0):
    r = R(10 + var)
    n = n_of(0.35)
    t = tt(n)
    body = sine(180 - 20 * t, n) * expdec(n, 0.08) * 0.8
    nz = bp(noise(n, r), 1200, 8000) * expdec(n, 0.13)
    return drive(body + nz, 1.6)


@cached
def hat(open_=False, var=0):
    r = R(20 + var)
    n = n_of(0.35 if open_ else 0.08)
    return hp(noise(n, r), 7500) * expdec(n, 0.16 if open_ else 0.022) * 0.5


@cached
def crash():
    r = R(30)
    n = n_of(2.2)
    return lp(hp(noise(n, r), 3500), 11000) * ar(n, 0.002, 0.8) * 0.45


@cached
def tom(f):
    n = n_of(0.4)
    t = tt(n)
    return sine(f * (1 + 0.6 * np.exp(-t / 0.04)), n) * expdec(n, 0.18) + bp(noise(n, R(5)), 300, 3000) * expdec(n, 0.03) * 0.3


@cached
def bass(midi, dur, bright=1.0, dr=2.2):
    f = hz(midi)
    n = n_of(dur + 0.04)
    x = saw(f * 1.004, n) + saw(f * 0.996, n, 0.3) + 0.3 * sine(f, n)
    x = sweep_lp(x, expdec(n, 0.07 + 0.05 * bright), 120 + 80 * bright, 300 + 2400 * bright)
    x *= adsr(n, 0.003, 0.12, 0.7, 0.025, dur)
    return drive(x * 0.6, dr)


@cached
def reese(midi, dur, dr=4.0):
    f = hz(midi)
    n = n_of(dur + 0.04)
    x = saw(f * 1.007, n) + saw(f * 0.993, n, 0.5) + saw(f, n, 0.25) + 0.35 * sine(f, n)
    x = sweep_lp(x, expdec(n, 0.09), 350, 2600)
    x = drive(x * adsr(n, 0.002, 0.15, 0.8, 0.02, dur) * 0.6, dr)
    return lp(x, 3500)


@cached
def pluck(midi, dur, dark=0.0):
    f = hz(midi)
    n = n_of(dur + 0.25)
    x = pulse(f, n, 0.3) + 0.4 * saw(f * 1.003, n)
    x = sweep_lp(x, expdec(n, 0.07), 300, 5200 - 3000 * dark)
    return x * ar(n, 0.002, 0.15) * 0.45


@cached
def pad(midis, dur, seed):
    r = R(seed)
    n = n_of(dur + 1.0)
    out = []
    for side in range(2):
        x = np.zeros(n)
        for mm in midis:
            f = hz(mm)
            for k in range(3):
                x += saw(f * (1 + r.uniform(-0.004, 0.004)), n, r.random())
        x = lp(x, 1500, 2) * adsr(n, 0.6, 1.2, 0.8, 0.9, dur) * 0.12
        out.append(x)
    return out


@cached
def lead(midi, dur, octave_glow=0.5):
    f = hz(midi)
    n = n_of(dur + 0.3)
    t = tt(n)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.18) / 0.25, 0, 1)
    x = saw(f * vib, n) + 0.5 * pulse(f * vib * 1.002, n, 0.5) + octave_glow * 0.25 * saw(f * 2 * vib, n)
    x = sweep_lp(x, 0.45 + 0.55 * expdec(n, 0.35), 900, 5000)
    x *= adsr(n, 0.015, 0.4, 0.75, 0.2, dur)
    return drive(x * 0.5, 1.4)


@cached
def brass(midis, dur):
    n = n_of(dur + 0.2)
    x = np.zeros(n)
    for mm in midis:
        f = hz(mm)
        x += saw(f * 1.004, n) + saw(f * 0.996, n, 0.5)
    x = sweep_lp(x, expdec(n, 0.12), 280, 4200)
    return drive(x * adsr(n, 0.01, 0.2, 0.55, 0.12, dur) * 0.22, 1.6)


@cached
def riser(dur):
    n = n_of(dur)
    t = tt(n)
    env = (t / dur) ** 2
    x = sweep_lp(hp(noise(n, R(77)), 200), env, 200, 10000) * env * 0.6
    return x


@cached
def drone(midi, dur):
    f = hz(midi)
    n = n_of(dur + 1.0)
    x = saw(f, n) + saw(f * 1.5 * 1.002, n) * 0.5 + sine(f / 2, n)
    return lp(x, 400) * adsr(n, 1.5, 2, 0.8, 1.0, dur) * 0.35


# ================================================================ sequencer
class Song:
    def __init__(self, name, bpm, bars):
        self.name = name
        self.bpm = bpm
        self.bars = bars
        self.s16 = 60.0 / bpm / 4
        self.length = n_of(bars * 16 * self.s16)
        N = self.length + n_of(4.0)
        self.N = N
        self.bus = {k: np.zeros(N) for k in ("kick", "snare", "hat", "bass", "arp", "padL", "padR", "lead",
                                             "brass", "fx", "perc")}
        self.kicks = []

    def at(self, step):
        return int(round(step * self.s16 * SR))

    def add(self, bus, x, step, gain=1.0):
        place(self.bus[bus], x, self.at(step), gain)

    def dur(self, steps):
        return steps * self.s16

    def k(self, step, vel=1.0):
        self.add("kick", kick(1.0), step, vel)
        self.kicks.append(self.at(step))

    def render(self, sc_depth=0.6, sc_tau=0.12, verb=0.25, verb_len=2.4):
        b = self.bus
        N = self.N
        # sidechain pump keyed from kicks
        sc = np.ones(N)
        t = tt(n_of(0.6))
        curve = 1 - sc_depth * np.exp(-t / sc_tau)
        for p in self.kicks:
            seg = sc[p:p + len(curve)]
            np.minimum(seg, curve[:len(seg)], out=seg)
        # gated snare
        sn = b["snare"] + convolve(b["snare"], gated_ir()) * 0.32
        drums = hp(b["kick"], 38) * 0.75 + sn * 1.2 + b["perc"]
        hatL, hatR = lp(b["hat"], 9000) * 0.6, lp(b["hat"], 9000) * 0.9
        # ping-pong arp
        d = self.at(3)
        arp = b["arp"] * sc
        arpL = arp + shift(arp, 2 * d, N) * 0.35 + shift(arp, 4 * d, N) * 0.15
        arpR = shift(arp, d, N) * 0.5 + shift(arp, 3 * d, N) * 0.25
        bass = hp(b["bass"], 40) * sc * 0.55
        # wide pads: decorrelated sides + short Haas offset
        padL = b["padL"] * sc * 1.6
        padR = shift(b["padR"], n_of(0.013), N) * sc * 1.6
        brass = b["brass"]
        brassL = brass + shift(brass, n_of(0.011), N) * 0.3
        brassR = shift(brass, n_of(0.017), N) + brass * 0.3
        lead = b["lead"] * 1.5
        L = drums + hatL + bass + arpL * 1.5 + padL + lead + brassL * 1.3 + b["fx"]
        Rr = drums + hatR + bass + arpR * 1.5 + padR + lead + brassR * 1.3 + b["fx"]
        # hall reverb send
        send = lead * 0.6 + arp * 0.6 + (padL + padR) * 0.3 + sn * 0.25 + brass * 0.4
        irL, irR = reverb_ir(verb_len, 99)
        L = L + convolve(send, irL) * verb
        Rr = Rr + convolve(send, irR) * verb
        out = np.stack([L, Rr], axis=1)
        out = hp(out.T, 30).T
        out = out + hp(out.T, 2500).T * 0.45          # presence / air lift
        out = np.tanh(out / np.max(np.abs(out)) * 1.6) / np.tanh(1.6)
        # wrap the tail onto the start so the loop is seamless
        loop = out[:self.length].copy()
        tail = out[self.length:]
        loop[:len(tail)] += tail
        return normalize(loop, 0.9)


# ================================================================ compositions
def bass_pattern16():
    # driving 16ths with octave jumps
    return [0, 0, 12, 0, 0, 12, 0, 12, 0, 0, 12, 0, 0, 12, 0, 12]


def title_theme():
    s = Song("title", 96, 32)
    prog = [(m("D3"), "m"), (m("Bb2"), "M"), (m("G2"), "m"), (m("A2"), "M")]
    for bar in range(32):
        root, q = prog[(bar // 2) % 4]
        ch = triad(root, q)
        if bar % 2 == 0:
            L, Rr = pad([c + 12 for c in ch], s.dur(32), bar % 8)
            s.add("padL", L, bar * 16)
            s.add("padR", Rr, bar * 16)
        # ominous 8th-note ostinato
        pat = [ch[0] + 24, ch[2] + 12, ch[0] + 24, ch[2] + 12, ch[1] + 24, ch[2] + 12, ch[0] + 24, ch[2] + 12]
        for i, nn in enumerate(pat):
            s.add("arp", pluck(nn, s.dur(2), 0.4), bar * 16 + i * 2, 0.8 if bar < 8 else 0.6)
        if bar >= 8:
            for i in range(8):
                s.add("bass", bass(root - 12 + (12 if i % 4 == 3 else 0), s.dur(2) * 0.9, 0.45), bar * 16 + i * 2, 0.9)
        if 8 <= bar < 16:
            s.k(bar * 16)
            s.k(bar * 16 + 8)
            for i in range(8):
                s.add("hat", hat(False, i % 3), bar * 16 + i * 2, 0.5)
        if bar >= 16:
            s.k(bar * 16)
            s.k(bar * 16 + 8)
            if bar % 4 == 3:
                s.k(bar * 16 + 14, 0.7)
            s.add("snare", snare(0), bar * 16 + 4)
            s.add("snare", snare(1), bar * 16 + 12)
            for i in range(16):
                s.add("hat", hat(i % 4 == 2, i % 3), bar * 16 + i, 0.55 if i % 2 == 0 else 0.35)
    s.add("fx", riser(s.dur(32)), 14 * 16, 0.6)
    for i, st in enumerate((15 * 16 + 8, 15 * 16 + 10, 15 * 16 + 12, 15 * 16 + 14)):
        s.add("perc", tom(150 - i * 22), st, 0.7)
    s.add("fx", crash(), 16 * 16, 0.8)
    s.add("fx", crash(), 24 * 16, 0.6)
    melody = [(0, 24, "A4"), (24, 4, "G4"), (28, 4, "F4"),
              (32, 16, "F4"), (48, 12, "D5"), (60, 4, "C5"),
              (64, 16, "Bb4"), (80, 8, "A4"), (88, 8, "G4"),
              (96, 16, "A4"), (112, 8, "C#5"), (120, 8, "E5")]
    for rep, (start, octv) in enumerate(((16 * 16, 0), (24 * 16, 12))):
        for st, ln, nn in melody:
            s.add("lead", lead(m(nn) + octv, s.dur(ln)), start + st, 0.55)
    return s.render(sc_depth=0.45, verb=0.35, verb_len=3.0)


def combat_theme():
    s = Song("combat", 118, 48)
    prog = [(m("E2"), "m"), (m("C2"), "M"), (m("D2"), "M"), (m("B1"), "M")]
    P1 = [(0, 6, "B4"), (6, 2, "G4"), (8, 4, "A4"), (12, 4, "B4"),
          (16, 6, "C5"), (22, 2, "B4"), (24, 4, "G4"), (28, 4, "E4"),
          (32, 6, "D5"), (38, 2, "C5"), (40, 4, "A4"), (44, 4, "F#4"),
          (48, 8, "D#5"), (56, 4, "F#5"), (60, 4, "B4")]
    P2 = [(0, 6, "E5"), (6, 2, "D5"), (8, 4, "B4"), (12, 4, "G4"),
          (16, 4, "C5"), (20, 4, "E5"), (24, 8, "G5"),
          (32, 6, "F#5"), (38, 2, "E5"), (40, 4, "D5"), (44, 4, "A4"),
          (48, 4, "B4"), (52, 4, "D#5"), (56, 8, "F#5")]
    for bar in range(48):
        root, q = prog[bar % 4]
        ch = triad(root + 24, q)
        b0 = bar * 16
        intro = bar < 8
        breakdown = 40 <= bar < 44
        # pads (every bar, chord)
        L, Rr = pad([c + 12 for c in ch], s.dur(16), bar % 4)
        s.add("padL", L, b0, 0.8)
        s.add("padR", Rr, b0, 0.8)
        # bass
        bright = 0.25 + 0.75 * bar / 8 if intro else (0.3 if breakdown else 1.0)
        for i, o in enumerate(bass_pattern16()):
            s.add("bass", bass(root + o, s.dur(1) * 0.85, round(bright, 2)), b0 + i, 0.85)
        # arp
        if not intro:
            arp = [ch[0], ch[1], ch[2], ch[0] + 12, ch[2], ch[1], ch[0] + 12, ch[1] + 12] * 2
            for i, nn in enumerate(arp):
                s.add("arp", pluck(nn + 12, s.dur(1), 0.1), b0 + i, 0.35 if 24 <= bar < 40 else 0.5)
        # drums
        if not breakdown:
            for beat in range(4):
                s.k(b0 + beat * 4)
            for i in range(16):
                if bar >= 4 or intro and bar >= 4:
                    s.add("hat", hat(i % 4 == 2, i % 3), b0 + i, 0.55 if i % 4 == 2 else 0.3)
            if bar >= 8:
                s.add("snare", snare(bar % 2), b0 + 4)
                s.add("snare", snare(1 - bar % 2), b0 + 12)
                if bar % 8 == 7:
                    for j, st in enumerate((13, 14, 15)):
                        s.add("snare", snare(j % 2), b0 + st, 0.6)
        # brass stabs in the B section and finale
        if 24 <= bar < 40 or bar >= 44:
            stab = [c + 12 for c in ch]
            s.add("brass", brass(stab, s.dur(3)), b0, 0.9)
            s.add("brass", brass(stab, s.dur(2)), b0 + 6, 0.7)
        # lead
        if 24 <= bar < 40 and bar % 4 == 0:
            phrase = (P1, P2, P1, P2)[(bar - 24) // 4]
            for st, ln, nn in phrase:
                s.add("lead", lead(m(nn), s.dur(ln)), b0 + st, 0.5)
        if bar == 44:
            for st, ln, nn in P2:
                s.add("lead", lead(m(nn) + 12, s.dur(ln), 0.8), b0 + st, 0.42)
    s.add("fx", riser(s.dur(32)), 6 * 16, 0.7)
    s.add("fx", riser(s.dur(32)), 42 * 16, 0.7)
    for b in (8, 24, 44):
        s.add("fx", crash(), b * 16, 0.8)
    return s.render(sc_depth=0.65, verb=0.22)


def deep_theme():
    s = Song("deep", 132, 48)
    roots = [m("F#2"), m("G2"), m("F#2"), m("E2")]
    quals = ["m", "M", "m", "M"]
    riff1 = [0, 0, None, 0, 1, None, 0, None, 0, 0, 3, None, 0, None, 7, 6]
    riff2 = [0, 0, None, 0, 1, None, 0, None, 12, None, 10, None, 8, 7, 6, 1]
    lead_ph = [(0, 8, "C#5"), (8, 4, "D5"), (12, 4, "C#5"), (16, 12, "A4"), (28, 4, "G4"),
               (32, 8, "D5"), (40, 4, "E5"), (44, 4, "D5"), (48, 12, "B4"), (60, 4, "G4"),
               (64, 8, "C#5"), (72, 4, "F#5"), (76, 4, "E5"), (80, 8, "D5"), (88, 8, "C#5"),
               (96, 16, "B4"), (112, 8, "G#4"), (120, 8, "E5")]
    for bar in range(48):
        idx = (bar // 2) % 4
        root, q = roots[idx], quals[idx]
        ch = triad(root + 24, q)
        b0 = bar * 16
        riff = riff1 if bar % 2 == 0 else riff2
        blast = 24 <= bar < 32
        breakdown = 32 <= bar < 40
        if bar % 2 == 0:
            L, Rr = pad([c + 12 for c in ch], s.dur(32), 40 + idx)
            s.add("padL", L, b0, 0.7)
            s.add("padR", Rr, b0, 0.7)
        if bar % 8 == 0:
            s.add("fx", drone(m("F#1"), s.dur(128)), b0, 0.5)
        # bass
        if breakdown:
            for i in (0, 3, 6, 10, 12):
                s.add("bass", reese(root - 12, s.dur(2)), b0 + i, 1.0)
                s.k(b0 + i)
        elif blast:
            for i in range(0, 16, 4):
                s.add("bass", reese(root + (0 if i < 8 else (1 if i == 8 else 0)), s.dur(4) * 0.95), b0 + i, 0.9)
        else:
            for i, o in enumerate(riff):
                if o is not None:
                    s.add("bass", reese(root + o, s.dur(1) * 0.9), b0 + i, 0.9)
        # drums
        if bar >= 4 and not breakdown:
            if blast:   # heavy half-time groove (was a blast beat)
                for i in (0, 6, 10):
                    s.k(b0 + i, 0.9 if i == 0 else 0.7)
                s.add("snare", snare(0), b0 + 8, 0.9)
                for i in range(0, 16, 4):
                    s.add("hat", hat(i % 8 == 4, i % 3), b0 + i, 0.25)
            else:
                for i, o in enumerate(riff):
                    if o == 0 and i in (0, 3, 8):
                        s.k(b0 + i, 0.9)
                if bar < 8:
                    s.add("snare", snare(0), b0 + 8)
                else:
                    s.add("snare", snare(0), b0 + 4)
                    s.add("snare", snare(1), b0 + 12)
                for i in range(0, 16, 2):
                    s.add("hat", hat(False, i % 3), b0 + i, 0.3)
        if breakdown:
            s.add("snare", snare(0), b0 + 8)
            stab = [c + 12 for c in ch]
            s.add("brass", brass(stab, s.dur(4)), b0, 1.0)
            s.add("brass", brass([n_ + 1 for n_ in stab], s.dur(2)), b0 + 10, 0.8)
        # arps (minor triad + b2 tension)
        if 8 <= bar < 24 or bar >= 40:
            arp = [ch[0], ch[0] + 1, ch[1], ch[2], ch[0] + 12, ch[2], ch[1], ch[0] + 1] * 2
            for i, nn in enumerate(arp):
                s.add("arp", pluck(nn + 12, s.dur(1), 0.0), b0 + i, 0.4)
        if (bar == 24 or bar == 40):
            for st, ln, nn in lead_ph:
                s.add("lead", lead(m(nn), s.dur(ln), 0.9), b0 + st, 0.5)
    for b in (8, 24, 32, 40):
        s.add("fx", crash(), b * 16, 0.9)
    s.add("fx", riser(s.dur(32)), 22 * 16, 0.7)
    s.add("fx", riser(s.dur(32)), 38 * 16, 0.7)
    return s.render(sc_depth=0.5, verb=0.2, verb_len=2.0)


# ================================================================ extra instruments
@cached
def clang(f, dur=1.6):
    n = n_of(dur)
    r = R(int(f))
    x = np.zeros(n)
    for ratio, dec, amp in ((1, 0.9, 1), (1.47, 0.6, 0.7), (2.09, 0.4, 0.5), (2.71, 0.3, 0.4), (3.6, 0.2, 0.3)):
        x += sine(f * ratio * r.uniform(0.99, 1.01), n) * expdec(n, dec) * amp
    x += bp(noise(n, r), 800, 4000) * expdec(n, 0.01)
    return lp(x, 5000) * 0.3


@cached
def musicbox(midi, dur):
    f = hz(midi)
    n = n_of(dur + 1.2)
    x = sine(f, n) + 0.35 * sine(f * 3, n) * expdec(n, 0.3) + 0.15 * sine(f * 5.02, n) * expdec(n, 0.15)
    return x * ar(n, 0.002, 0.9) * 0.3


@cached
def siren(dur, lo, hi):
    n = n_of(dur)
    t = tt(n)
    f = lo + (hi - lo) * np.sin(np.pi * t / dur) ** 2
    return lp(sine(f, n) + 0.3 * saw(f, n), 1200) * np.sin(np.pi * t / dur) * 0.12


def dread_theme():
    """Rust biome: industrial dread - drones, heartbeat, clangs, a broken music box. No busy drums."""
    s = Song("dread", 84, 32)
    prog = [(m("C#3"), "m"), (m("A2"), "M"), (m("F#2"), "m"), (m("G2"), "M")]
    s.add("fx", drone(m("C#1"), s.dur(32 * 16)), 0, 0.7)
    s.add("fx", drone(m("G1"), s.dur(16 * 16)), 16 * 16, 0.35)
    rng = R(66)
    box_ph = [(0, 6, "C#6"), (6, 2, "E6"), (8, 4, "D#6"), (12, 4, "G5"),
              (16, 6, "C#6"), (22, 2, "G#5"), (24, 8, "A5"), (32, 6, "F#5"), (38, 2, "G5"), (40, 12, "C#6")]
    for bar in range(32):
        b0 = bar * 16
        root, q = prog[(bar // 4) % 4]
        if bar % 4 == 0:
            L, Rr = pad(triad(root, q), s.dur(64), 70 + bar)
            s.add("padL", L, b0, 0.9)
            s.add("padR", Rr, b0, 0.9)
        if bar >= 4:   # heartbeat
            s.k(b0, 0.55)
            s.k(b0 + 2, 0.4)
        if bar >= 16 and bar % 2 == 1:
            s.add("snare", snare(1), b0 + 8, 0.35)
        if rng.random() < 0.55:
            s.add("lead", clang(rng.choice([180, 233, 311, 415])), b0 + int(rng.integers(0, 16)), 0.8)
        if 8 <= bar and bar % 4 == 0:
            for st, ln, nn in box_ph:
                if st < 64:
                    s.add("arp", musicbox(m(nn), s.dur(ln)), b0 + st, 0.9)
        if bar % 8 == 4:
            s.add("fx", siren(s.dur(64), 220, 620), b0, 0.8)
        if bar in (7, 15, 23):
            s.add("fx", riser(s.dur(16)), b0, 0.4)
    return s.render(sc_depth=0.15, verb=0.45, verb_len=4.0)


def frost_theme():
    """Outpost biome: cold, minimal pulse-synth paranoia."""
    s = Song("frost", 90, 40)
    prog = [(m("A1"), "m"), (m("F1"), "M"), (m("D2"), "m"), (m("E1"), "M")]
    lead_ph = [(0, 12, "E5"), (12, 4, "D5"), (16, 16, "C5"), (32, 12, "B4"), (44, 4, "C5"), (48, 16, "A4")]
    for bar in range(40):
        b0 = bar * 16
        root, q = prog[(bar // 4) % 4]
        if bar % 4 == 0:
            L, Rr = pad([c + 24 for c in triad(root, q)], s.dur(64), 90 + bar)
            s.add("padL", L, b0, 0.8)
            s.add("padR", Rr, b0, 0.8)
        for st in (0, 3, 8, 11):   # dum-dum ... dum-dum
            s.add("bass", bass(root, s.dur(2), 0.3, 1.6), b0 + st, 0.9 if st in (0, 8) else 0.6)
        if bar % 2 == 1 and bar >= 4:
            ch = triad(root + 36, q)
            for i, nn in enumerate((ch[0], ch[2], ch[1] + 12, ch[2])):
                s.add("arp", pluck(nn, s.dur(2), 0.6), b0 + i * 4, 0.35)
        if 16 <= bar < 36:
            s.k(b0, 0.6)
            s.k(b0 + 8, 0.5)
            for i in range(0, 16, 4):
                s.add("hat", hat(False, i % 3), b0 + i + 2, 0.18)
        if 24 <= bar < 36:
            s.add("snare", snare(0), b0 + 12, 0.35)
        if bar in (24, 32):
            for st, ln, nn in lead_ph:
                s.add("lead", lead(m(nn), s.dur(ln), 0.2), b0 + st, 0.4)
    s.add("fx", riser(s.dur(32)), 14 * 16, 0.4)
    return s.render(sc_depth=0.3, verb=0.4, verb_len=3.5)


def inferno_theme():
    """Hell biome: heavy half-time darksynth - reese, brass stabs, big but sparse drums."""
    s = Song("inferno", 104, 48)
    roots = [m("D2"), m("Eb2"), m("C2"), m("D2")]
    quals = ["m", "M", "m", "m"]
    lead_ph = [(0, 8, "D5"), (8, 4, "Eb5"), (12, 4, "F5"), (16, 12, "D5"), (28, 4, "C5"),
               (32, 8, "Eb5"), (40, 8, "G5"), (48, 16, "F5"),
               (64, 8, "D5"), (72, 4, "C5"), (76, 4, "Bb4"), (80, 16, "A4"),
               (96, 8, "D5"), (104, 8, "Eb5"), (112, 16, "D5")]
    for bar in range(48):
        idx = (bar // 2) % 4
        root, q = roots[idx], quals[idx]
        b0 = bar * 16
        intro = bar < 4
        breakdown = 40 <= bar < 44
        if bar % 2 == 0:
            L, Rr = pad([c + 12 for c in triad(root + 12, q)], s.dur(32), 120 + idx)
            s.add("padL", L, b0, 0.8)
            s.add("padR", Rr, b0, 0.8)
        if bar % 8 == 0:
            s.add("fx", drone(root - 12, s.dur(128)), b0, 0.45)
        if not intro:
            for st, ln, o in ((0, 4, 0), (6, 2, 0), (8, 4, 1), (14, 2, 0)):
                s.add("bass", reese(root + o, s.dur(ln) * 0.95, 3.0), b0 + st, 0.85 if not breakdown else 0.5)
        if not intro and not breakdown:
            s.k(b0, 0.95)
            s.k(b0 + 10, 0.7)
            s.add("snare", snare(bar % 2), b0 + 8, 0.95)
            for i in range(0, 16, 2):
                s.add("hat", hat(i % 4 == 2, i % 3), b0 + i, 0.22)
            if bar % 8 == 7:
                for j, st in enumerate((12, 13, 14, 15)):
                    s.add("perc", tom(160 - j * 25), b0 + st, 0.6)
        if 16 <= bar < 32 or bar >= 44:
            stab = [c + 12 for c in triad(root + 12, q)]
            s.add("brass", brass(stab, s.dur(4)), b0, 0.9)
            if bar % 2:
                s.add("brass", brass([n_ + 1 for n_ in stab], s.dur(2)), b0 + 12, 0.6)
        if bar in (32,):
            for st, ln, nn in lead_ph:
                s.add("lead", lead(m(nn), s.dur(ln), 0.7), b0 + st, 0.5)
        if 24 <= bar < 32 or breakdown:
            ch = triad(root + 36, q)
            for i, nn in enumerate([ch[0], ch[0] + 1, ch[1], ch[2]] * 4):
                s.add("arp", pluck(nn, s.dur(1), 0.2), b0 + i, 0.3)
    for b in (4, 16, 32, 44):
        s.add("fx", crash(), b * 16, 0.7)
    s.add("fx", riser(s.dur(32)), 2 * 16, 0.6)
    s.add("fx", riser(s.dur(32)), 42 * 16, 0.6)
    return s.render(sc_depth=0.45, verb=0.28, verb_len=2.6)


def boss_theme():
    """Boss fights: urgent and driving, but with restrained half-time drums."""
    s = Song("boss", 140, 32)
    roots = [m("C2"), m("Ab1"), m("Bb1"), m("G1")]
    quals = ["m", "M", "M", "M"]
    lead_ph = [(0, 6, "G4"), (6, 2, "Ab4"), (8, 8, "C5"), (16, 6, "Bb4"), (22, 2, "Ab4"), (24, 8, "G4"),
               (32, 6, "Eb5"), (38, 2, "D5"), (40, 8, "C5"), (48, 4, "B4"), (52, 4, "D5"), (56, 8, "G5")]
    for bar in range(32):
        root, q = roots[bar % 4], quals[bar % 4]
        b0 = bar * 16
        ch = triad(root + 24, q)
        L, Rr = pad([c + 12 for c in ch], s.dur(16), 200 + bar % 4)
        s.add("padL", L, b0, 0.7)
        s.add("padR", Rr, b0, 0.7)
        for i, o in enumerate(bass_pattern16()):
            s.add("bass", bass(root + o, s.dur(1) * 0.85, 0.9, 2.6), b0 + i, 0.85)
        if bar >= 2:
            s.k(b0, 1.0)
            s.k(b0 + 6, 0.7)
            s.k(b0 + 10, 0.8)
            s.add("snare", snare(bar % 2), b0 + 8, 0.95)
            for i in range(0, 16, 2):
                s.add("hat", hat(i % 4 == 2, i % 3), b0 + i, 0.22)
            if bar % 8 == 7:
                for j, st in enumerate((12, 13, 14, 15)):
                    s.add("perc", tom(170 - j * 25), b0 + st, 0.6)
        arp = [ch[0], ch[1], ch[2], ch[0] + 12] * 4
        for i, nn in enumerate(arp):
            s.add("arp", pluck(nn + 12, s.dur(1), 0.1), b0 + i, 0.32)
        if bar >= 8:
            stab = [c + 12 for c in ch]
            s.add("brass", brass(stab, s.dur(3)), b0, 0.85)
            s.add("brass", brass(stab, s.dur(2)), b0 + 10, 0.6)
        if bar in (16, 24):
            for st, ln, nn in lead_ph:
                s.add("lead", lead(m(nn), s.dur(ln), 0.8), b0 + st, 0.5)
    for b in (0, 8, 16, 24):
        s.add("fx", crash(), b * 16, 0.7)
    return s.render(sc_depth=0.55, verb=0.22, verb_len=2.2)


TRACKS = {"boss": boss_theme, "title": title_theme, "combat": combat_theme, "deep": deep_theme, "dread": dread_theme,
          "frost": frost_theme, "inferno": inferno_theme}


def main():
    os.makedirs(OUT, exist_ok=True)
    names = sys.argv[1:] or list(TRACKS)
    for n in names:
        t0 = time.time()
        _cache.clear()
        x = TRACKS[n]()
        write(os.path.join(OUT, n + ".wav"), x)
        print("music %-7s %.1fs long, rendered in %.1fs" % (n, len(x) / SR, time.time() - t0))


if __name__ == "__main__":
    main()

"""Full-length soundtrack built from the music-lab instruments -> assets/audio/music/<track>.ogg

Each track is arranged in sections (intro / verses / lead sections / breakdowns / outro) and ends where its intro
begins, so the game can loop it. Original compositions in the darksynth vein, plus one spooky Halloween romp.

    python tools/make_soundtrack.py [track ...]
"""
import os
import sys
import time
import random
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music_lab as L  # noqa: E402
from music_lab import (Clock, Mix, chord, m, hz, guitar, growl, reese2, pluck2, stab, lead_line, fill, beat, snare_roll,  # noqa: E402
                       supersaw, choir2, organ, fm, tom, crash, riser, kick, snare, hat, ride, subbass, fmbass)
from dsp import SR, n_of, tt, R, ar, adsr, noise, saw, sine, lp, hp, bp, sweep_lp, drive  # noqa: E402,F401
from music_lab import tail as _t  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "audio", "music")


def layout(plan):
    """[(section, bars), ...] -> list of (bar, section, bar_in_section, section_index), total bars."""
    out, b = [], 0
    for k, (name, n) in enumerate(plan):
        for i in range(n):
            out.append((b, name, i, k))
            b += 1
    return out, b


def section_starts(plan, names):
    b, out = 0, []
    for name, n in plan:
        if name in names:
            out.append((b, name))
        b += n
    return out


def melody_events(c, starts, mel, shift=0, octave_for=None):
    ev = []
    for b0, name in starts:
        tr = shift + (12 if octave_for and name in octave_for else 0)
        for bar, st, ln, nn in mel:
            ev.append((c(b0 * 4 + bar * 4 + st), c.d(ln) * 0.96, m(nn) + tr))
    return ev


# ================================================================ 1. Nightcrawler (facility / greed / nuclear / chemical)
def nightcrawler():
    c = Clock(118, human=0.003)
    plan = [("intro", 4), ("A", 8), ("B", 8), ("A", 8), ("brk", 4), ("B", 8), ("B2", 8), ("A", 8), ("outro", 4)]
    bars, nb = layout(plan)
    mx = Mix(c.d(nb * 4) + 0.5)
    mx.setup("growl", duck=0.8)
    mx.setup("arp", duck=0.5, verb=0.25, echo=(c.d(0.75), 0.35, 4, 4500))
    mx.setup("stab", duck=0.5, verb=0.35)
    mx.setup("pad", duck=0.6, verb=0.5, chorus=(6, 0.3))
    mx.setup("choir", verb=0.6, duck=0.3)
    mx.setup("snare", gate=0.7, verb=0.25)
    mx.setup("tom", gate=0.6, verb=0.2)
    mx.setup("lead", verb=0.45, echo=(c.d(0.75), 0.3, 3, 4000))
    Fm, Db, Eb, C_, Bbm = (m("F2"), "m"), (m("Db2"), "M"), (m("Eb2"), "M"), (m("C2"), "M"), (m("Bb1"), "m")
    progs = {"intro": [Fm, Db, Eb, C_], "A": [Fm, Fm, Db, Eb, Fm, Fm, Db, C_], "B": [Fm, Db, Bbm, C_, Fm, Db, Bbm, C_],
             "brk": [Db, Eb, Fm, C_], "outro": [Fm, Fm, Db, C_]}
    for b, sec, i, k in bars:
        b0 = b * 4
        r0, q = progs.get(sec, progs["B"])[i % len(progs.get(sec, progs["B"]))]
        ch = chord(r0 + 24, q)
        arp = [ch[0], ch[2], ch[1], ch[2], ch[0] + 12, ch[2], ch[1] + 12, ch[2]]
        top = 1200 + 4800 * (i / 4) if sec == "intro" else (3000 if sec == "brk" else 6000)
        for j in range(16):
            mx.add("arp", pluck2(arp[j % 8] + 12, 0.18, top), c(b0 + j / 4), 0.5, (-0.4, 0.4)[j % 2])
        if sec in ("A", "B", "B2"):
            for j in range(16):
                o = 12 if j % 2 else 0
                if j == 14 and b % 2:
                    o = 1
                mx.add("growl", growl(r0 + o, c.d(0.25) * 0.8, 1.0 if sec != "A" else 0.7), c(b0 + j / 4), 0.9 if j % 4 == 0 else 0.75)
            mx.add("pad", supersaw(ch, c.d(4) * 0.98, 2400, 0.05, 0.4, b % 8), c(b0), 0.6)
            beat(mx, c, b0, b, hats=16)
            if i % 4 == 3:
                fill(mx, c, b0 + 3, 1)
            if sec == "A":
                for st, ln in ((0, 0.75), (1.5, 0.5), (2.5, 0.5), (3.5, 0.5)):
                    mx.add("stab", stab([n + 12 for n in ch], c.d(ln)), c(b0 + st), 0.9)
            if i == 0:
                mx.add("fx", crash(), c(b0), 0.9)
        elif sec == "brk":
            mx.add("pad", supersaw(ch, c.d(4) * 0.98, 1400, 0.4, 0.8, b % 8), c(b0), 0.7)
            mx.add("choir", choir2([n + 12 for n in ch], c.d(4) * 0.98, "o", 0.6), c(b0), 0.7)
            mx.add("growl", subbass(hz(r0), c.d(4) * 0.95), c(b0), 0.7)
            if i == 3:
                snare_roll(mx, c, b0, 4)
        elif sec == "intro":
            if i >= 2:
                for kk in range(4):
                    mx.kick(c(b0 + kk), "punch")
            if i == 3:
                snare_roll(mx, c, b0, 4)
        elif sec == "outro":
            mx.kick(c(b0), "punch")
            mx.add("stab", stab([n + 12 for n in ch], c.d(1.5)), c(b0), 0.8)
            mx.add("pad", supersaw(ch, c.d(4) * 0.98, 1600, 0.2, 0.6, b % 8), c(b0), 0.5)
    mel = [(0, 0, 2, "C5"), (0, 2, 1, "Ab4"), (0, 3, 1, "F4"), (1, 0, 1.5, "Ab4"), (1, 1.5, 0.5, "Bb4"), (1, 2, 1, "C5"),
           (1, 3, 1, "Db5"), (2, 0, 2, "F5"), (2, 2, 1, "Db5"), (2, 3, 1, "Bb4"), (3, 0, 1, "C5"), (3, 1, 1, "E4"),
           (3, 2, 1, "G4"), (3, 3, 1, "Bb4"), (4, 0, 1, "Ab4"), (4, 1, 1, "C5"), (4, 2, 2, "F5"), (5, 0, 1, "Eb5"),
           (5, 1, 1, "Db5"), (5, 2, 2, "C5"), (6, 0, 2, "F5"), (6, 2, 1, "Eb5"), (6, 3, 1, "Db5"), (7, 0, 4, "C5")]
    ev = melody_events(c, section_starts(plan, ("B", "B2")), mel, octave_for=("B2",))
    total = c.d(nb * 4) + 0.5
    mx.add("lead", lead_line(ev, total, 0.05, 5000), 0, 1.0)
    lo_l, lo_r = lead_line([(s, d, n - 12) for s, d, n in ev], total, 0.05, 3000)
    mx.add("lead", (lo_l * 0.45, lo_r * 0.45), 0, 1.0)
    for b0, _ in section_starts(plan, ("brk",)):
        mx.add("fx", riser(c.d(16)), c(b0 * 4), 0.7)
    return mx.render(verb=2.2, damp=6000, master_lp=12000, drive=2.2, duck_tau=0.11, fade=0.25)


# ================================================================ 2. Black Mass (hell / heresy / violence)
def black_mass():
    c = Clock(150, human=0.002)
    plan = [("intro", 4), ("A", 8), ("A2", 8), ("doom", 8), ("A", 8), ("C", 8), ("A2", 8), ("outro", 4)]
    bars, nb = layout(plan)
    mx = Mix(c.d(nb * 4) + 0.5)
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
    scale = [D2 + 36 + s for s in (0, 1, 3, 5, 7, 8, 10, 12)]
    line = [7, 6, 5, 4, 5, 3, 1, 0, 1, 3, 4, 5, 7, 6, 4, 1]
    doom = [[(0, 2, 0), (2, 2, 1)], [(0, 3, 0), (3, 1, -2)], [(0, 2, -4), (2, 2, -5)], [(0, 2, 0), (2, 1, 1), (3, 1, 3)]]
    for b, sec, i, k in bars:
        b0 = b * 4
        rt = roots[i % 8]
        if i % 2 == 0:
            mx.add("choir", choir2([n + 12 for n in chords[rt]], c.d(8) * 0.98, "a", 0.4), c(b0), 0.8 if sec != "intro" else 0.6)
        if sec in ("intro", "A", "A2", "C", "outro"):
            cut = 500 + 1500 * min(1, i / 3) if sec == "intro" else (900 if sec == "outro" else 2000)
            for j, o in enumerate(riff):
                mx.add("reese", reese2(D2 + rt + o, c.d(0.25) * 0.85, cut, 3.5), c(b0 + j / 4), 0.85)
                if sec in ("A", "A2", "C"):
                    mx.add("growl", growl(D2 + rt + o, c.d(0.25) * 0.7, 0.9, 5.0), c(b0 + j / 4), 0.6)
        if sec in ("A", "A2"):
            beat(mx, c, b0, b, kicks=[kk / 2 for kk in range(8)], hats=8, use_ride=True)
            if i % 4 == 3:
                fill(mx, c, b0 + 3, 1)
        if sec == "C":                                   # half-time stomp under the riff
            mx.kick(c(b0), "punch")
            mx.kick(c(b0 + 2.75), "punch")
            mx.add("snare", snare("doom", i % 2), c(b0 + 2), 1.0)
            mx.add("hat", ride(i % 3), c(b0 + 1), 0.4)
            mx.add("hat", ride((i + 1) % 3), c(b0 + 3), 0.4)
        if sec in ("A2", "C"):
            for j, kk in enumerate(line):
                mx.add("arp", pluck2(scale[kk] + (1 if rt == 1 and kk == 0 else 0), 0.15, 6500), c(b0 + j / 4), 0.5, (-0.5, 0.5)[j % 2])
        if sec == "doom":
            for st, ln, o in doom[i % 4]:
                for sd, pan in ((1, -0.8), (2, 0.8)):
                    mx.add("gtr", guitar(D2 + o, c.d(ln) * 0.97, False, sd + i), c(b0 + st) + (0.012 if sd == 2 else 0), 0.8, pan)
                mx.add("growl", growl(D2 + o - 12, c.d(ln) * 0.95, 0.4, 3.0), c(b0 + st), 0.8)
            mx.kick(c(b0), "punch")
            mx.kick(c(b0 + 2.75), "punch")
            mx.add("snare", snare("doom", i % 2), c(b0 + 2), 1.0)
            if i % 4 == 0:
                mx.add("fx", crash(), c(b0), 0.6)
        if sec == "intro" and i == 3:
            snare_roll(mx, c, b0, 4)
        if i == 0 and sec in ("A", "A2", "doom", "C"):
            mx.add("fx", crash(), c(b0), 0.9)
    for b0, _ in section_starts(plan, ("doom", "C")):
        mx.add("fx", riser(c.d(8)), c(b0 * 4 - 8), 0.7)
    return mx.render(verb=2.0, damp=5000, master_lp=11000, drive=2.5, duck_tau=0.08, fade=0.25)


# ================================================================ 3. Turbo (outpost / biotech)
def turbo():
    c = Clock(132, human=0.003)
    plan = [("intro", 4), ("V", 8), ("L", 8), ("V", 8), ("bridge", 4), ("L2", 8), ("V", 8), ("outro", 4)]
    bars, nb = layout(plan)
    mx = Mix(c.d(nb * 4) + 0.5)
    mx.setup("gtr", verb=0.12)
    mx.setup("growl", duck=0.6)
    mx.setup("arp", duck=0.5, verb=0.25, echo=(c.d(0.75), 0.3, 3, 5000))
    mx.setup("pad", duck=0.5, verb=0.4, chorus=(5, 0.3))
    mx.setup("snare", gate=0.6, verb=0.25)
    mx.setup("tom", gate=0.5)
    mx.setup("lead", verb=0.4, echo=(c.d(0.75), 0.25, 3, 4500))
    mx.setup("lead2", verb=0.4, echo=(c.d(0.75), 0.25, 3, 4500))
    E2, C2, G2, D2, B1 = m("E2"), m("C2"), m("G2"), m("D2"), m("B1")
    progs = {"V": [(E2, "m"), (C2, "M"), (G2, "M"), (D2, "M")], "L": [(E2, "m"), (C2, "M"), (G2, "M"), (D2, "M"), (E2, "m"), (C2, "M"),
             (D2, "M"), (B1, "M")], "bridge": [(C2, "M"), (D2, "M"), (E2, "m"), (E2, "m")], "intro": [(E2, "m"), (C2, "M"), (G2, "M"), (D2, "M")],
             "outro": [(E2, "m"), (C2, "M"), (D2, "M"), (E2, "m")]}
    gal = [(kk + s, ln) for kk in range(4) for s, ln in ((0, 0.5), (0.5, 0.25), (0.75, 0.25))]
    for b, sec, i, k in bars:
        b0 = b * 4
        pr = progs.get(sec, progs["L"])
        r0, q = pr[i % len(pr)]
        ch = chord(r0 + 24, q)
        if sec == "bridge":                               # big open chords, toms
            for sd, pan in ((1, -0.85), (2, 0.85)):
                mx.add("gtr", guitar(r0, c.d(4) * 0.95, False, sd + i), c(b0) + (0.01 if sd == 2 else 0), 0.9, pan)
            mx.add("growl", subbass(hz(r0), c.d(4) * 0.95), c(b0), 0.8)
            mx.add("pad", supersaw(ch, c.d(4) * 0.98, 2200, 0.1, 0.5, b % 8), c(b0), 0.6)
            fill(mx, c, b0 + 2, 2)
            mx.kick(c(b0), "punch")
            continue
        for j, (st, ln) in enumerate(gal):
            if st == 0 and sec != "intro":
                for sd, pan in ((1, -0.85), (2, 0.85)):
                    mx.add("gtr", guitar(r0, c.d(1) * 0.95, False, sd), c(b0) + (0.01 if sd == 2 else 0), 0.9, pan)
                continue
            if st < 1 and sec != "intro":
                continue
            for sd, pan in ((3, -0.85), (4, 0.85)):
                mx.add("gtr", guitar(r0, c.d(ln) * 0.9, True, sd * 10 + (j * 7 + b) % 6), c(b0 + st) + (0.009 if sd == 4 else 0),
                       (0.75 if sec == "intro" else 0.8) * (1.0 if st % 1 == 0 else 0.85), pan)
            if sec != "intro":
                mx.add("growl", growl(r0, c.d(ln) * 0.85, 0.6, 3.0), c(b0 + st), 0.8)
        arp = [ch[0], ch[1], ch[2], ch[1] + 12, ch[2] + 12, ch[1] + 12, ch[2], ch[1]]
        for j in range(16):
            mx.add("arp", pluck2(arp[j % 8] + 12, 0.15, 6500), c(b0 + j / 4), 0.45, (-0.5, 0.5)[j % 2])
        if sec in ("V", "L", "L2"):
            mx.add("pad", supersaw(ch, c.d(4) * 0.98, 2600, 0.05, 0.4, b % 8), c(b0), 0.5)
            kicks = [kk + s for kk in range(4) for s in (0, 0.5, 0.75)] if sec != "V" else (0, 1, 2, 3)
            beat(mx, c, b0, b, kicks=kicks, hats=8)
            if i % 4 == 3:
                fill(mx, c, b0 + 2, 2)
            if i == 0:
                mx.add("fx", crash(), c(b0), 0.9)
        if sec == "intro" and i == 3:
            snare_roll(mx, c, b0 + 2, 2)
        if sec == "outro":
            mx.kick(c(b0), "punch")
            mx.add("snare", snare("gate", 1), c(b0 + 2), 0.9)
    mel = [(0, 0, 1, "B4"), (0, 1, 1, "E5"), (0, 2, 1, "F#5"), (0, 3, 1, "G5"), (1, 0, 1.5, "G5"), (1, 1.5, 0.5, "F#5"),
           (1, 2, 1, "E5"), (1, 3, 1, "G5"), (2, 0, 2, "D5"), (2, 2, 1, "B4"), (2, 3, 1, "D5"), (3, 0, 2, "F#5"),
           (3, 2, 1, "E5"), (3, 3, 1, "D5"), (4, 0, 1, "E5"), (4, 1, 0.5, "F#5"), (4, 1.5, 0.5, "G5"), (4, 2, 1, "A5"),
           (4, 3, 1, "B5"), (5, 0, 2, "C6"), (5, 2, 1, "B5"), (5, 3, 1, "G5"), (6, 0, 1, "A5"), (6, 1, 1, "F#5"),
           (6, 2, 1, "D5"), (6, 3, 1, "A5"), (7, 0, 4, "B5")]
    scale = {4, 6, 7, 9, 11, 0, 2}
    ev = melody_events(c, section_starts(plan, ("L", "L2")), mel, shift=-12, octave_for=("L2",))
    ev = [(s, d, n + 12) for s, d, n in ev]
    ev2 = [(s, d, n - 3 if (n - 3) % 12 in scale else n - 4) for s, d, n in ev]
    total = c.d(nb * 4) + 0.5
    mx.add("lead", lead_line(ev, total, 0.04, 4200, 4.0), 0, 1.0)
    mx.add("lead2", lead_line(ev2, total, 0.04, 4000, 4.0), 0, 1.0)
    return mx.render(verb=2.0, damp=6000, master_lp=12000, drive=2.2, duck_tau=0.1, fade=0.25)


# ================================================================ 4. Requiem (otherworld / limbo / lust / sewer, and the title)
def requiem():
    c = Clock(104, human=0.003)
    plan = [("intro", 4), ("build", 4), ("A", 8), ("B", 8), ("brk", 4), ("B", 8), ("A", 8), ("outro", 4)]
    bars, nb = layout(plan)
    mx = Mix(c.d(nb * 4) + 0.5)
    mx.setup("growl", duck=0.75)
    mx.setup("pad", duck=0.6, verb=0.55, chorus=(7, 0.25))
    mx.setup("arp", duck=0.4, verb=0.3, echo=(c.d(0.75), 0.4, 4, 4000))
    mx.setup("choir", verb=0.7, duck=0.3)
    mx.setup("snare", gate=0.9, verb=0.35)
    mx.setup("tom", gate=0.7)
    mx.setup("lead", verb=0.6, echo=(c.d(0.75), 0.35, 4, 3800))
    Cs, A, Fs, Gs = m("C#2"), m("A1"), m("F#2"), m("G#1")
    prog = [(Cs, "m"), (A, "M"), (Fs, "m"), (Gs, "M")]
    acc = [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0]
    for b, sec, i, k in bars:
        b0 = b * 4
        r0, q = prog[b % 4]
        ch = chord(r0 + 24, q)
        open_ = {"intro": 0.2, "build": 0.3 + 0.15 * i, "A": 0.85, "B": 1.0, "brk": 0.35, "outro": 0.3}[sec]
        mx.add("pad", supersaw([n + 12 for n in ch] + [ch[0]], c.d(4) * 0.98, 900 + 2200 * open_, 0.2, 0.8, b % 8), c(b0), 0.7)
        if sec in ("build", "A", "B"):
            for j in range(16):
                o = 12 if j in (6, 14) else 0
                mx.add("growl", growl(r0 + o, c.d(0.25) * 0.75, 0.35 + 0.65 * open_ * (1.0 if acc[j] else 0.7), 3.5), c(b0 + j / 4),
                       0.9 if acc[j] else 0.6)
        arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[0] + 24, ch[2] + 12, ch[1] + 12]
        for j in range(16):
            mx.add("arp", pluck2(arp[j % 6], 0.2, 2500 + 4000 * open_), c(b0 + j / 4), 0.4, (-0.6, 0.6)[j % 2])
        if sec in ("A", "B"):
            beat(mx, c, b0, b, kicks=(0, 1.5, 2) if b % 2 == 0 else (0, 1.5, 2, 3.75), hats=16)
            if i % 4 == 3:
                fill(mx, c, b0 + 3, 1)
            if i == 0:
                mx.add("fx", crash(), c(b0), 0.9)
        if sec == "brk":
            mx.add("choir", choir2([n + 12 for n in ch], c.d(4) * 0.98, "u", 0.8), c(b0), 0.8)
        if sec == "build" and i == 3:
            snare_roll(mx, c, b0, 4)
        if sec == "brk" and i == 3:
            snare_roll(mx, c, b0 + 2, 2)
    mel = [(0, 0, 3, "E5"), (0, 3, 0.5, "D#5"), (0, 3.5, 0.5, "C#5"), (1, 0, 2, "C#5"), (1, 2, 2, "E5"), (2, 0, 3, "F#5"),
           (2, 3, 1, "E5"), (3, 0, 2, "D#5"), (3, 2, 2, "C5"), (4, 0, 2, "G#5"), (4, 2, 1, "E5"), (4, 3, 1, "C#5"),
           (5, 0, 2, "E5"), (5, 2, 1, "C#5"), (5, 3, 1, "A4"), (6, 0, 2, "F#5"), (6, 2, 2, "A5"), (7, 0, 4, "G#5")]
    ev = melody_events(c, section_starts(plan, ("B",)), mel)
    mx.add("lead", lead_line(ev, c.d(nb * 4) + 0.5, 0.09, 3800, 2.0, 0.008, 0.009), 0, 1.0)
    for b0, _ in section_starts(plan, ("B",)):
        mx.add("fx", riser(c.d(8)), c(b0 * 4 - 8), 0.6)
    return mx.render(verb=3.0, damp=5000, master_lp=11000, drive=2.0, duck_tau=0.14, fade=0.25)


# ================================================================ 5. Hunter (boss fights)
def hunter():
    c = Clock(140, human=0.002)
    plan = [("intro", 2), ("A", 8), ("B", 8), ("C", 8), ("brk", 4), ("A", 8), ("C", 8), ("outro", 2)]
    bars, nb = layout(plan)
    mx = Mix(c.d(nb * 4) + 0.5)
    mx.setup("reese", duck=0.5)
    mx.setup("growl", duck=0.6)
    mx.setup("stab", duck=0.3, verb=0.3)
    mx.setup("snare", gate=0.7, verb=0.25)
    mx.setup("tom", gate=0.7)
    mx.setup("choir", verb=0.6)
    mx.setup("arp", verb=0.25, echo=(c.d(0.375), 0.3, 3, 5000), duck=0.4)
    mx.setup("lead", verb=0.5, echo=(c.d(0.75), 0.3, 3, 4000))
    A1 = m("A1")
    hits = [(0, 0), (0.75, 0), (1.5, 0), (2.5, 1), (3, 0), (3.5, 12)]
    roots = [0, 0, -4, -5]
    line = [12, 13, 12, 7, 12, 13, 15, 13, 12, 8, 7, 3, 7, 8, 12, 13]
    for b, sec, i, k in bars:
        b0 = b * 4
        rt = roots[(i // 2) % 4]
        q = "M" if rt in (-4, -5) else "m"
        ch = chord(A1 + rt + 24, q)
        quiet = sec in ("intro", "brk", "outro")
        for st, o in hits:
            ln = 0.5 if st < 3.5 else 0.4
            mx.add("reese", reese2(A1 + rt + o, c.d(ln) * 0.9, 700 if quiet else 2200, 3.0), c(b0 + st), 0.85)
            if not quiet:
                mx.add("growl", growl(A1 + rt + o + 12, c.d(ln) * 0.8, 1.0, 4.0), c(b0 + st), 0.6)
                if st in (0, 0.75, 1.5):
                    mx.add("stab", stab([n + 12 for n in ch], c.d(0.4)), c(b0 + st), 0.9)
                mx.kick(c(b0 + st), "punch")
        if not quiet:
            for s_ in (1, 3):
                mx.add("snare", snare("gate", b % 2), c(b0 + s_), 1.0)
            for j in range(16):
                mx.add("hat", hat(False, j % 3), c(b0 + j / 4), 0.4 if j % 2 else 0.25)
            if i % 4 == 3:
                fill(mx, c, b0 + 2, 2, (240, 210, 180, 150, 120, 95, 80))
            if i == 0:
                mx.add("fx", crash(), c(b0), 0.9)
        if sec in ("B", "C"):
            for j, kk in enumerate(line):
                mx.add("arp", pluck2(A1 + 36 + rt + kk, 0.12, 7000), c(b0 + j / 4), 0.4, (-0.5, 0.5)[j % 2])
        if sec == "brk":
            mx.add("choir", choir2([n + 12 for n in ch], c.d(4) * 0.98, "a", 0.3), c(b0), 0.8)
            if i == 3:
                snare_roll(mx, c, b0, 4)
        if sec == "intro" and i == 1:
            snare_roll(mx, c, b0, 4)
    mel = [(0, 0, 2, "E5"), (0, 2, 2, "F5"), (1, 0, 3, "E5"), (1, 3, 1, "C5"), (2, 0, 2, "C5"), (2, 2, 2, "A4"),
           (3, 0, 2, "G#4"), (3, 2, 2, "B4"), (4, 0, 2, "E5"), (4, 2, 2, "F5"), (5, 0, 2, "G#5"), (5, 2, 2, "B5"), (6, 0, 8, "A5")]
    ev = melody_events(c, section_starts(plan, ("C",)), mel)
    mx.add("lead", lead_line(ev, c.d(nb * 4) + 0.5, 0.12, 4200, 3.0, 0.009, 0.012), 0, 1.0)
    return mx.render(verb=2.0, damp=6000, master_lp=12000, drive=2.4, duck_tau=0.08, fade=0.2)


# ================================================================ 6. Bone Dance (ossuary / gluttony / wrath / castle) - the Halloween one
@L.cached
def xylo(midi, dur=0.5):
    """Skeleton xylophone: hard woody FM mallet."""
    f = hz(midi)
    x = fm(f, dur, 3.98, 2.6, 0.025, 0.001, 0.16) * 0.55 + fm(f * 2, dur, 1.0, 0.6, 0.02, 0.001, 0.06) * 0.25
    return x


@L.cached
def tuba(midi, dur):
    """Oom-pah brass bass."""
    f = hz(midi)
    n = n_of(dur + 0.08)
    t = tt(n)
    swell = np.clip(t / 0.03, 0, 1)
    x = saw(f, n) + 0.6 * saw(f * 1.004, n, 0.3) + 0.8 * sine(f, n)
    x = sweep_lp(x, 0.25 + 0.5 * swell * np.exp(-t / 0.25), 150, 1400)
    return _t(drive(x * adsr(n, 0.02, 0.15, 0.6, 0.06, dur) * 0.5, 1.6))


def theremin_line(events, total, glide=0.16):
    """Wailing theremin: pure-ish tone, long glides, wide wobbly vibrato that swells in."""
    from scipy.signal import lfilter, lfilter_zi
    n = n_of(total)
    f = np.zeros(n)
    g = np.zeros(n)
    for st, du, mid in sorted(events):
        s0, e0 = n_of(st), min(n, n_of(st + du))
        f[s0:e0] = hz(mid)
        g[s0:e0] = 1.0
    idx = np.where(f > 0, np.arange(n), 0)
    np.maximum.accumulate(idx, out=idx)
    f = f[idx]
    first = int(np.argmax(f > 0))
    f[:first] = f[first]

    def smooth(x, tau):
        a = 1 - np.exp(-1 / (tau * SR))
        return lfilter([a], [1, -(1 - a)], x, zi=lfilter_zi([a], [1, -(1 - a)]) * x[0])[0]
    f = np.exp(smooth(np.log(f), glide))
    t = tt(n)
    env = smooth(g, 0.08)
    f = f * (1 + 0.022 * np.sin(2 * np.pi * 5.8 * t) * smooth(g, 0.5))
    x = sine(f, n) + 0.18 * lp(saw(f, n), 1600)
    return (x * env * 0.22, np.roll(x * env * 0.22, n_of(0.011)))


def bone_dance():
    c = Clock(152, human=0.004)

    def sw(beat_):                                     # swung eighths: the off-beat lands on the triplet
        whole = int(beat_)
        fr = beat_ - whole
        return whole + (0.67 if abs(fr - 0.5) < 1e-6 else fr)

    plan = [("intro", 4), ("A", 8), ("B", 8), ("A", 8), ("C", 8), ("B", 8), ("A", 8), ("outro", 4)]
    bars, nb = layout(plan)
    mx = Mix(c.d(nb * 4) + 0.5)
    mx.setup("bass", duck=0.3)
    mx.setup("xylo", verb=0.35)
    mx.setup("organ", verb=0.5)
    mx.setup("choir", verb=0.8)
    mx.setup("snare", verb=0.3)
    mx.setup("hat", verb=0.1)
    mx.setup("lead", verb=0.6, echo=(c.d(0.75), 0.3, 3, 3000))
    mx.setup("fx", verb=0.5)
    E2 = m("E2")
    Em, Am, B7, C_, G_, F_ = (E2, "m"), (m("A2"), "m"), (m("B1"), "7"), (m("C2"), "M"), (m("G2"), "M"), (m("F2"), "M")
    progs = {"intro": [Em, Em, Am, B7], "A": [Em, Em, Am, B7, Em, C_, B7, Em], "B": [Em, G_, C_, B7, Am, Em, F_, B7],
             "C": [Am, Em, F_, B7, Am, Em, F_, B7], "outro": [Em, Am, B7, Em]}
    for b, sec, i, k in bars:
        b0 = b * 4
        r0, q = progs[sec][i % len(progs[sec])]
        ch = chord(r0 + 24, q)
        if sec in ("A", "B", "C"):
            fifth = r0 + 7 - (12 if r0 + 7 > m("D3") else 0)
            for st, nn in ((0, r0 - 12 + 12), (2, fifth)):     # oom ... pah
                mx.add("bass", tuba(nn, c.d(0.8)), c(b0 + st), 0.9)
            if sec != "C":
                for st in (1, 3):                              # off-beat xylophone chord plinks
                    for nn in ch[:3]:
                        mx.add("xylo", xylo(nn + 24, 0.4), c(b0 + st), 0.18, (nn % 3 - 1) * 0.4)
            mx.kick(c(b0), "tight", 0.8)
            mx.kick(c(b0 + 2), "tight", 0.7)
            mx.add("snare", snare("rim", b % 2), c(b0 + 1), 0.7)
            mx.add("snare", snare("rim", 1 - b % 2), c(b0 + 3), 0.7)
            for st in (0, 1, sw(1.5), 2, 3, sw(3.5)):
                mx.add("hat", ride(int(st * 3) % 3), c(b0 + st), 0.35 if st % 1 else 0.25)
        if sec == "C":                                         # creepy carnival organ, oom-pah on the organ
            for st in (1, 3):
                mx.add("organ", organ([nn + 12 for nn in ch], c.d(0.45), 1.0), c(b0 + st), 0.55)
            mx.add("organ", organ([r0], c.d(0.9), 0.4), c(b0), 0.5)
        if sec == "intro":
            mx.add("organ", organ([nn + 12 for nn in ch], c.d(4) * 0.98, 0.7), c(b0), 0.5)
            mx.add("organ", organ([r0 - 12, r0 - 5], c.d(4) * 0.98, 0.3), c(b0), 0.45)
        if sec == "B" and i % 2 == 0:
            mx.add("choir", choir2([nn + 12 for nn in ch], c.d(8) * 0.98, "o", 1.2), c(b0), 0.5)
        if sec == "outro":
            mx.add("organ", organ([nn + 12 for nn in ch], c.d(4) * 0.98, 0.6), c(b0), 0.5)
            mx.add("bass", tuba(r0, c.d(3)), c(b0), 0.7)
        if i == len(progs.get(sec, [])) - 1 and sec in ("A", "B"):     # chromatic tumble into the next section
            for j, nn in enumerate(("E6", "D#6", "D6", "C#6", "C6", "B5")):
                mx.add("xylo", xylo(m(nn), 0.3), c(b0 + 2 + j / 3), 0.4, 0.3)
    melA = [(0, 0, 0.5, "E5"), (0, 0.5, 0.5, "G5"), (0, 1, 1, "B5"), (0, 2, 0.5, "A#5"), (0, 2.5, 1.5, "B5"),
            (1, 0, 1, "G5"), (1, 1, 0.5, "F#5"), (1, 1.5, 0.5, "G5"), (1, 2, 2, "E5"),
            (2, 0, 1, "A5"), (2, 1, 1, "C6"), (2, 2, 0.5, "B5"), (2, 2.5, 0.5, "A5"), (2, 3, 1, "G5"),
            (3, 0, 1, "F#5"), (3, 1, 1, "D#5"), (3, 2, 2, "B4"),
            (4, 0, 0.5, "E5"), (4, 0.5, 0.5, "G5"), (4, 1, 1, "B5"), (4, 2, 1, "E6"), (4, 3, 1, "D#6"),
            (5, 0, 1, "E6"), (5, 1, 1, "C6"), (5, 2, 1, "G5"), (5, 3, 1, "E5"),
            (6, 0, 0.5, "D#5"), (6, 0.5, 0.5, "E5"), (6, 1, 0.5, "F#5"), (6, 1.5, 0.5, "A5"), (6, 2, 1, "B5"), (6, 3, 1, "A5"),
            (7, 0, 2, "G5"), (7, 2, 2, "E5")]
    for b0, _ in section_starts(plan, ("A",)):
        for bar, st, ln, nn in melA:
            mx.add("xylo", xylo(m(nn), 0.5), c(b0 * 4 + bar * 4 + sw(st)), 0.55, -0.15)
    melB = [(0, 0, 2, "B4"), (0, 2, 2, "E5"), (1, 0, 1.5, "D5"), (1, 1.5, 0.5, "B4"), (1, 2, 2, "G4"), (2, 0, 3, "E5"),
            (2, 3, 1, "G5"), (3, 0, 2, "F#5"), (3, 2, 2, "D#5"), (4, 0, 2, "A5"), (4, 2, 1, "C6"), (4, 3, 1, "B5"),
            (5, 0, 2, "G5"), (5, 2, 2, "E5"), (6, 0, 2, "F5"), (6, 2, 1, "A5"), (6, 3, 1, "C6"), (7, 0, 4, "B5")]
    mx.add("lead", theremin_line(melody_events(c, section_starts(plan, ("B",)), melB), c.d(nb * 4) + 0.5), 0, 1.0)
    intro_wail = [(c(0.5), c.d(3), m("E5")), (c(4), c.d(2), m("G5")), (c(6), c.d(2), m("F#5")), (c(8), c.d(4), m("B5")),
                  (c(12), c.d(3.5), m("A#5"))]
    mx.add("lead", theremin_line(intro_wail, c.d(16) + 1), 0, 0.8)
    n_ = n_of(3.0)
    thunder = lp(noise(n_, R(13)), 300) * ar(n_, 0.01, 1.0) * 1.4 + lp(noise(n_, R(14)), 1500) * ar(n_, 0.002, 0.08)
    mx.add("fx", (thunder, np.roll(thunder, n_of(0.02))), 0.05, 0.9)
    for b0, _ in section_starts(plan, ("C",)):
        mx.add("fx", (thunder * 0.6, thunder * 0.6), c(b0 * 4), 0.7)
    return mx.render(verb=2.6, damp=4500, master_lp=10000, drive=1.8, duck_tau=0.12, fade=0.25)


TRACKS = {"nightcrawler": nightcrawler, "black_mass": black_mass, "turbo": turbo, "requiem": requiem, "hunter": hunter,
          "bone_dance": bone_dance}


def main():
    import soundfile as sf
    os.makedirs(OUT, exist_ok=True)
    for name in sys.argv[1:] or list(TRACKS):
        t0 = time.time()
        L._cache.clear()
        x = TRACKS[name]()
        x = np.ascontiguousarray(x.astype(np.float32))
        # the Vorbis encoder overflows its stack on one huge write, so feed it a couple of seconds at a time
        with sf.SoundFile(os.path.join(OUT, name + ".ogg"), "w", SR, 2, format="OGG", subtype="VORBIS") as fh:
            for i in range(0, len(x), SR * 2):
                fh.write(x[i:i + SR * 2])
        print("music %-12s %5.1fs  rendered in %.0fs  %.1f MB" % (name, len(x) / SR, time.time() - t0,
                                                                 os.path.getsize(os.path.join(OUT, name + ".ogg")) / 1e6))


if __name__ == "__main__":
    main()

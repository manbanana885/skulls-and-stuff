"""Small numpy/scipy DSP toolkit used to synthesize all game audio offline."""
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 44100


def n_of(d):
    return max(1, int(round(d * SR)))


def tt(n):
    return np.arange(n) / SR


def R(seed):
    return np.random.default_rng(seed)


def expdec(n, tau):
    return np.exp(-tt(n) / max(tau, 1e-5))


def ar(n, a, tau):
    """Linear attack, exponential decay."""
    e = expdec(n, tau)
    na = min(n, n_of(a))
    if na > 1:
        e[:na] *= np.linspace(0, 1, na)
    return e


def adsr(n, a, d, s, r, gate):
    t = tt(n)
    a = max(a, 1e-4)
    env = np.where(t < a, t / a, s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    gi = min(n - 1, n_of(gate))
    g = env[gi]
    rel = t >= gate
    env[rel] = g * np.exp(-(t[rel] - gate) / max(r, 1e-4))
    return env


def noise(n, rng):
    return rng.uniform(-1, 1, n)


def _farr(freq, n):
    return np.broadcast_to(np.asarray(freq, dtype=float), (n,)).astype(float)


def saw(freq, n, ph0=0.0):
    """Band-limited (polyBLEP) sawtooth."""
    dt = _farr(freq, n) / SR
    t = (ph0 + np.cumsum(dt)) % 1.0
    y = 2 * t - 1
    m = t < dt
    x = t[m] / dt[m]
    y[m] -= x + x - x * x - 1
    m = t > 1 - dt
    x = (t[m] - 1) / dt[m]
    y[m] -= x * x + x + x + 1
    return y


def pulse(freq, n, width=0.5, ph0=0.0):
    return saw(freq, n, ph0) - saw(freq, n, ph0 + width)


def sine(freq, n, ph0=0.0):
    return np.sin(2 * np.pi * (ph0 + np.cumsum(_farr(freq, n)) / SR))


def lp(x, fc, order=2):
    fc = min(max(fc, 20), SR * 0.45)
    b, a = signal.butter(order, fc / (SR / 2))
    return signal.lfilter(b, a, x)


def hp(x, fc, order=2):
    fc = min(max(fc, 20), SR * 0.45)
    b, a = signal.butter(order, fc / (SR / 2), "high")
    return signal.lfilter(b, a, x)


def bp(x, lo, hi, order=2):
    lo = max(lo, 20)
    hi = min(hi, SR * 0.45)
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def sweep_lp(x, env01, fmin, fmax, steps=8):
    """Time-varying low-pass: crossfade between statically filtered copies, driven by env01 (0..1)."""
    cuts = np.geomspace(fmin, fmax, steps)
    V = np.stack([lp(x, c) for c in cuts])
    idx = np.clip(env01, 0, 1) * (steps - 1)
    i0 = np.floor(idx).astype(int)
    i1 = np.minimum(i0 + 1, steps - 1)
    fr = idx - i0
    ar_ = np.arange(len(x))
    return V[i0, ar_] * (1 - fr) + V[i1, ar_] * fr


def drive(x, k):
    return np.tanh(x * k) / np.tanh(k)


def crush(x, bits=10, hold=2):
    """SNES-ish grit: sample-and-hold rate reduction + quantization."""
    y = np.repeat(x[::hold], hold)[:len(x)]
    q = 2 ** (bits - 1)
    return np.round(y * q) / q


def echo(x, delay, fb, taps=4):
    d = n_of(delay)
    out = np.zeros(len(x) + d * taps)
    out[:len(x)] += x
    for k in range(1, taps + 1):
        out[k * d:k * d + len(x)] += lp(x, 6000 - k * 900) * (fb ** k)
    return out


def shift(x, d, n=None):
    n = n or len(x)
    out = np.zeros(n)
    if d < n:
        m = min(len(x), n - d)
        out[d:d + m] = x[:m]
    return out


def reverb_ir(dur, seed, damp=5000, predelay=0.012):
    r = R(seed)
    n = n_of(dur)
    e = np.exp(-tt(n) * 6.9 / dur)
    irs = []
    for _ in range(2):
        ir = lp(noise(n, r) * e, damp)
        ir = np.concatenate([np.zeros(n_of(predelay)), ir])
        irs.append(ir / np.sqrt(np.sum(ir ** 2)))
    return irs


def gated_ir(gate=0.26, seed=3):
    r = R(seed)
    n = n_of(gate + 0.03)
    e = np.ones(n)
    k = n_of(0.03)
    e[-k:] = np.linspace(1, 0, k)
    e *= np.linspace(1.0, 0.75, n)
    ir = lp(noise(n, r), 7000) * e
    return ir / np.sqrt(np.sum(ir ** 2))


def convolve(x, ir):
    return signal.fftconvolve(x, ir)[:len(x)]


def place(buf, x, start, gain=1.0):
    if start >= len(buf) or start + len(x) <= 0:
        return
    s0 = max(0, start)
    x0 = s0 - start
    m = min(len(x) - x0, len(buf) - s0)
    buf[s0:s0 + m] += x[x0:x0 + m] * gain


def fade_out(x, dur=0.01):
    k = min(len(x), n_of(dur))
    x = x.copy()
    x[-k:] *= np.linspace(1, 0, k)
    return x


def normalize(x, peak=0.95):
    m = np.max(np.abs(x))
    return x if m < 1e-9 else x * (peak / m)


def write(path, x):
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    wavfile.write(path, SR, data)

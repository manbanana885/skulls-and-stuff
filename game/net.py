"""Net play plumbing: wire format, game-state codec, host / client connections and LAN discovery.

The host runs the real game. Guests send their controls; the host sends each guest the world around it.

Wire: every message is [4-byte big-endian length][1-byte type][payload].
  guest -> host payloads are JSON (the host never unpickles anything a guest sends);
  host -> guest world data is a restricted pickle (only game classes, nothing callable), zlib-compressed.
Snapshots are compressed against the previous snapshot sent on the same connection (TCP keeps them in order),
so the unchanged part of the world costs almost nothing.

Everything is non-blocking and polled from the game loop: no threads.
"""
import errno
import hashlib
import hmac
import io
import json
import os
import pickle
import secrets
import socket
import struct
import time
import zlib

PORT = 47777          # TCP: the game itself
DISCOVERY = 47778     # UDP: "there's a game here" beacons on the local network
PROTOCOL = 2
MAX_FRAME = 32 << 20          # host -> guest (a whole world can be big)
GUEST_MAX_FRAME = 4096        # guest -> host: controls and lobby picks are tiny; anything bigger gets you kicked
GUEST_MAX_BUFFER = 64 * 1024
MAX_PLAYERS = 4
HERE = os.path.dirname(os.path.abspath(__file__))


def game_version():
    """Short hash of the game's code: host and guests must run the same version (state is shared as objects).
    Line endings are normalised so a Windows checkout and a Mac / Linux one agree."""
    h = hashlib.sha1(b"proto%d" % PROTOCOL)
    for name in sorted(os.listdir(HERE)):
        if name.endswith(".py"):
            with open(os.path.join(HERE, name), "rb") as fh:
                h.update(name.encode())
                h.update(fh.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:8]


def local_addresses():
    """This machine's LAN address(es), for the host to read out to friends."""
    found = []
    try:                                   # the address the OS would use to reach the internet (no packet is sent)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        found.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in found and not ip.startswith("127."):
                found.append(ip)
    except OSError:
        pass
    return found or ["127.0.0.1"]


# ================================================================ game names (the join password)
_ADJ = ("grim", "rusty", "bony", "sly", "feral", "hollow", "toxic", "frozen", "rabid", "silent", "crooked", "molten",
        "ashen", "gloomy", "jagged", "wicked", "brittle", "vile", "spooky", "rotten")
_NOUN = ("otter", "skull", "crow", "jackal", "lantern", "coffin", "badger", "raven", "cleaver", "gremlin", "ghoul",
         "pickle", "wombat", "goblet", "beetle", "hatchet", "moth", "toad", "kettle", "spleen")


def random_name():
    return "%s-%s-%02d" % (secrets.choice(_ADJ), secrets.choice(_NOUN), secrets.randbelow(100))


def norm_name(text):
    """Game names ignore case, spaces and dashes: 'Grim Otter 47' == 'grim-otter-47'."""
    return "".join(c for c in str(text).lower() if c.isalnum())


def name_proof(name, nonce):
    """Proof that a guest knows the game name, without sending the name itself."""
    return hmac.new(norm_name(name).encode(), ("skulls:" + str(nonce)).encode(), hashlib.sha256).hexdigest()


def proof_ok(name, nonce, proof):
    return isinstance(proof, str) and hmac.compare_digest(proof, name_proof(name, nonce))


# ================================================================ codec
GAME_MODULES = ("world", "weapons", "support", "traps", "bosses", "bestiary", "characters", "biomes", "damage", "level")
SAFE_GLOBALS = {("builtins", "set"), ("builtins", "frozenset"), ("builtins", "bytearray"), ("builtins", "complex"),
                ("builtins", "slice"), ("random", "Random"), ("collections", "deque"), ("collections", "OrderedDict"),
                ("collections", "defaultdict")}


class Registry:
    """The game's static tables and the functions inside them (weapon mods, buff effects...), each given a path.
    Objects in here travel as their path, not their contents: smaller, and functions can't be pickled anyway."""

    def __init__(self):
        import importlib
        self.by_id = {}
        self.by_path = {}
        self.mods = {}
        for mname in GAME_MODULES:
            m = importlib.import_module(mname)
            self.mods[mname] = m
            for name, val in sorted(vars(m).items()):
                if not name.startswith("__"):
                    self._walk(val, (mname, name), 0)

    def _walk(self, val, path, depth):
        if callable(val) and not isinstance(val, type):
            if getattr(val, "__module__", None) not in GAME_MODULES and depth == 0:
                return                          # imported helpers (math.hypot...) - not ours
            self._add(val, path)
            return
        if isinstance(val, (dict, list, tuple)) and depth < 5:
            if isinstance(val, tuple) and not val:
                return
            self._add(val, path)
            items = val.items() if isinstance(val, dict) else enumerate(val)
            for k, v in items:
                if isinstance(k, (str, int)):
                    self._walk(v, path + (k,), depth + 1)

    def _add(self, obj, path):
        if id(obj) not in self.by_id:
            self.by_id[id(obj)] = path
            self.by_path[path] = obj


_REG = None


def registry():
    global _REG
    if _REG is None:
        _REG = Registry()
    return _REG


class _Pickler(pickle.Pickler):
    def __init__(self, f, world):
        super().__init__(f, protocol=5)
        self.world = world
        self.reg = registry().by_id

    def persistent_id(self, obj):
        if obj is self.world:
            return "W"
        if self.world is not None and obj is self.world.level:
            return "L"
        if isinstance(obj, (dict, list, tuple)) or callable(obj) and not isinstance(obj, type):
            return self.reg.get(id(obj))
        return None


class _Unpickler(pickle.Unpickler):
    def __init__(self, f, world):
        super().__init__(f)
        self.world = world
        self.reg = registry().by_path

    def persistent_load(self, pid):
        if pid == "W":
            return self.world
        if pid == "L":
            return self.world.level
        try:
            return self.reg[tuple(pid)]
        except (KeyError, TypeError):
            raise pickle.UnpicklingError("unknown shared object %r" % (pid,))

    def find_class(self, module, name):
        if module in GAME_MODULES:
            obj = getattr(registry().mods[module], name, None)
            if isinstance(obj, type) and obj.__module__ == module:
                return obj
        elif (module, name) in SAFE_GLOBALS:
            return super().find_class(module, name)
        raise pickle.UnpicklingError("refused %s.%s" % (module, name))


def pack(obj, world=None):
    f = io.BytesIO()
    _Pickler(f, world).dump(obj)
    return f.getvalue()


def unpack(data, world=None):
    return _Unpickler(io.BytesIO(data), world).load()


# ================================================================ connection
class Conn:
    """One non-blocking TCP connection with framed messages."""

    def __init__(self, sock, addr=None, max_frame=MAX_FRAME, max_buffer=None):
        sock.setblocking(False)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        self.sock = sock
        self.addr = addr
        self.inbuf = bytearray()
        self.outbuf = bytearray()
        self.closed = False
        self.error = None
        self.sent_bytes = 0
        self.recv_bytes = 0
        self.zprev = b""              # last snapshot sent / received (compression dictionary)
        self.max_frame = max_frame
        self.max_buffer = max_buffer or max_frame * 2 + 16

    def send(self, kind, payload):
        if self.closed:
            return
        self.outbuf += struct.pack(">IB", len(payload) + 1, ord(kind)) + payload
        self.flush()

    def send_json(self, kind, obj):
        self.send(kind, json.dumps(obj, separators=(",", ":")).encode())

    def backlog(self):
        return len(self.outbuf)

    def flush(self):
        while self.outbuf and not self.closed:
            try:
                n = self.sock.send(self.outbuf[:1 << 16])
            except (BlockingIOError, InterruptedError):
                return
            except OSError as ex:
                if ex.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                    return
                self.close(str(ex))
                return
            if n <= 0:
                return
            self.sent_bytes += n
            del self.outbuf[:n]

    def poll(self):
        """Read what's arrived; returns a list of (type, payload)."""
        out = []
        if self.closed:
            return out
        self.flush()
        while True:
            try:
                chunk = self.sock.recv(1 << 18)
            except (BlockingIOError, InterruptedError):
                break
            except OSError as ex:
                if ex.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                    break
                self.close(str(ex))
                break
            if not chunk:
                self.close("disconnected")
                break
            self.recv_bytes += len(chunk)
            self.inbuf += chunk
            if len(self.inbuf) > self.max_buffer:
                self.close("sent too much at once")
                return out
        while len(self.inbuf) >= 5:
            n = struct.unpack(">I", self.inbuf[:4])[0]
            if n < 1 or n > self.max_frame:
                self.close("message too big")
                break
            if len(self.inbuf) < 4 + n:
                break
            kind = chr(self.inbuf[4])
            payload = bytes(self.inbuf[5:4 + n])
            del self.inbuf[:4 + n]
            out.append((kind, payload))
        return out

    def close(self, why="closed"):
        if not self.closed:
            self.closed = True
            self.error = why
            try:
                self.sock.close()
            except OSError:
                pass

    # snapshots: compressed against the previous one sent on this connection
    def send_delta(self, kind, raw):
        z = zlib.compressobj(1, zdict=self.zprev[-32768:]) if self.zprev else zlib.compressobj(1)
        data = z.compress(raw) + z.flush()
        self.zprev = raw
        self.send(kind, data)

    def read_delta(self, data):
        z = zlib.decompressobj(zdict=self.zprev[-32768:]) if self.zprev else zlib.decompressobj()
        raw = z.decompress(data, MAX_FRAME)
        self.zprev = raw
        return raw


def read_json(payload, strict=False):
    """A JSON object, or {} (None with strict=True) if it isn't one."""
    try:
        v = json.loads(payload.decode())
        if isinstance(v, dict):
            return v
    except (ValueError, UnicodeDecodeError, RecursionError):
        pass
    return None if strict else {}


# ================================================================ host side
class HostServer:
    """Listens for guests and announces itself on the LAN."""

    def __init__(self, port=PORT):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", port))
        self.sock.listen(8)
        self.sock.setblocking(False)
        self.beacon = None
        try:
            b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            b.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            b.setblocking(False)
            self.beacon = b
        except OSError:
            self.beacon = None
        self.beacon_t = 0.0

    def accept(self):
        out = []
        while True:
            try:
                s, addr = self.sock.accept()
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break
            out.append(Conn(s, addr, GUEST_MAX_FRAME, GUEST_MAX_BUFFER))
        return out

    def announce(self, info):
        """Broadcast a beacon about once a second so guests on the same network see the game listed."""
        now = time.monotonic()
        if self.beacon is None or now - self.beacon_t < 1.0:
            return
        self.beacon_t = now
        msg = json.dumps(dict(info, g="skulls", port=self.port)).encode()
        for dest in ("255.255.255.255", "<broadcast>"):
            try:
                self.beacon.sendto(msg, (dest, DISCOVERY))
                break
            except OSError:
                continue

    def close(self):
        for s in (self.sock, self.beacon):
            try:
                if s:
                    s.close()
            except OSError:
                pass


class Finder:
    """Listens for host beacons on the LAN."""

    def __init__(self):
        self.games = {}            # ip -> (info, last seen)
        self.sock = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except OSError:
                    pass
            s.bind(("", DISCOVERY))
            s.setblocking(False)
            self.sock = s
        except OSError:
            self.sock = None

    def poll(self):
        if self.sock is not None:
            while True:
                try:
                    data, addr = self.sock.recvfrom(2048)
                except (BlockingIOError, InterruptedError):
                    break
                except OSError:
                    break
                info = read_json(data)
                if info.get("g") == "skulls":
                    self.games[addr[0]] = (info, time.monotonic())
        now = time.monotonic()
        for ip in [ip for ip, (_, t) in self.games.items() if now - t > 4.0]:
            del self.games[ip]
        return sorted(self.games.items())

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass


def parse_address(text):
    """'192.168.1.5', 'host.local:47777', '[::1]:5000' -> (host, port)."""
    text = text.strip()
    host, port = text, PORT
    if text.startswith("["):
        end = text.find("]")
        host = text[1:end]
        rest = text[end + 1:]
        if rest.startswith(":") and rest[1:].isdigit():
            port = int(rest[1:])
    elif text.count(":") == 1:
        h, p = text.split(":")
        if p.isdigit():
            host, port = h, int(p)
    return host, port


class Connector:
    """Non-blocking connect to a host (so the join screen keeps animating)."""

    def __init__(self, text, timeout=6.0):
        self.host, self.port = parse_address(text)
        self.deadline = time.monotonic() + timeout
        self.conn = None
        self.error = None
        self.sock = None
        try:
            infos = socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM)
            fam, _, _, _, addr = infos[0]
            self.sock = socket.socket(fam, socket.SOCK_STREAM)
            self.sock.setblocking(False)
            err = self.sock.connect_ex(addr)
            if err not in (0, errno.EINPROGRESS, errno.EWOULDBLOCK, getattr(errno, "WSAEWOULDBLOCK", 10035), errno.EALREADY):
                self.fail(os.strerror(err) if err < 1000 else "can't reach %s" % self.host)
        except (OSError, IndexError) as ex:
            self.fail("can't find %s (%s)" % (self.host, ex.__class__.__name__))

    def fail(self, why):
        self.error = why
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    def poll(self):
        """None while waiting; a Conn when connected; sets .error on failure."""
        if self.sock is None:
            return None
        import select
        try:
            _, w, x = select.select([], [self.sock], [self.sock], 0)
        except (OSError, ValueError):
            self.fail("connection failed")
            return None
        if w or x:
            err = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if err:
                self.fail("no game at %s:%d (%s)" % (self.host, self.port, os.strerror(err) if err < 1000 else "refused"))
                return None
            self.conn = Conn(self.sock, (self.host, self.port))
            self.sock = None
            return self.conn
        if time.monotonic() > self.deadline:
            self.fail("no answer from %s:%d" % (self.host, self.port))
        return None

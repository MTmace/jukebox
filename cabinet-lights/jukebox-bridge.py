#!/usr/bin/env python3
"""Jukebox bridge: Teensy keypad controller + Fruitbox status -> cabinet lights.

Reads two things:
  - The Teensy's USB serial "E:<event>" lines (key presses, coins, buttons),
    see arduino/seeburg_keypad. Other lines are ignored.
  - Fruitbox's state file, written by a hidden [status] box in the skin
    (playing / idle, attract mode on / off).
and shows a light pattern to match what the jukebox is doing, either:
  - on LED strips wired straight to the Pi, one data pin per strip, or
  - by switching presets on a WLED controller over Wi-Fi.

Settings: /home/mtmace/fruitbox/jukebox-bridge.ini (see jukebox-bridge.ini).
Needs: sudo apt install python3-serial python3-evdev pulseaudio-utils (python3-spidev only for SPI pins)
Test without changing anything: python3 jukebox-bridge.py --dry-run
Show every theme's patterns on the strips, 6 s each: python3 jukebox-bridge.py --demo
"""
VERSION = "1.4"   # bump on every change; the status page shows it
import argparse, colorsys, configparser, glob, json, math, os, random, signal, sys, threading, time, urllib.request

CONFIG = "/home/mtmace/fruitbox/jukebox-bridge.ini"
DEFAULTS = {
    "teensy": {"port": ""},
    # sleep_file exists while the jukebox sleeps (Pause key, made by jukebox-keys)
    "fruitbox": {"state_file": "/dev/shm/jukebox_state.txt", "sleep_file": "/dev/shm/jukebox_sleep",
                 # the jukebox state, one word, from the state manager (jukebox-state)
                 "mode_file": "/dev/shm/jukebox_mode"},
    # strips: the patterned strips, top to bottom (each has a [strip <name>]
    # section); white: the white strip behind the numbers
    "leds": {"enabled": "no", "strips": "third window subs", "white": "white",
             "white_level": "70", "rgbw": "yes", "color_order": "GRB", "brightness": "60", "fps": "40"},
    # each strip: its data pin (see README "Pi setup"), LEDs, its place in a
    # chain sharing that pin, and reverse = yes if data runs through it right to left
    "strip window": {"device": "/dev/leds-fire", "leds": "52", "chain": "1", "reverse": "no"},
    "strip subs": {"device": "/dev/leds-fire", "leds": "55", "chain": "2", "reverse": "yes"},
    "strip third": {"device": "/dev/leds-fire", "leds": "53", "chain": "3", "reverse": "no"},
    "strip white": {"device": "/dev/leds-fire", "leds": "46", "chain": "4", "reverse": "no"},
    # each theme: the pattern for idle, for active (playing / typing) and for attract
    "themes": {"order": "white fire rising relay duet vu firestar lava ocean rainbow",
               "white": "white white white",
               "rising": "candle rising flow", "relay": "candle relay flow",
               "duet": "candle duet flow",
               "vu": "breathe vu aurora",
               "fire": "candle fire aurora", "firestar": "breathe firestar aurora",
               "lava": "lava lava aurora", "ocean": "ocean ocean aurora",
               "rainbow": "breathe rainbow aurora", "coin": "sparkle"},
    "sound": {"enabled": "yes", "react": "playing selecting", "floor": "35",
              "capture": "runuser -u mtmace -- env XDG_RUNTIME_DIR=/run/user/1000 "
                         "parec -d @DEFAULT_MONITOR@ --format=s16le --rate=11025 "
                         "--channels=1 --raw --latency-msec=20"},
    "levels": {"idle": "70", "playing": "100", "selecting": "100", "coin": "100",
               "attract": "35", "sleep": "15"},
    "controls": {"off_key": "KEY_SCROLLLOCK KEY_F13", "dim_up_key": "KEY_PAGEUP KEY_F14",
                 "dim_down_key": "KEY_PAGEDOWN KEY_F15", "theme_key": "KEY_INSERT KEY_F16",
                 "dim_step": "10", "preview_seconds": "6"},
    "wled": {"enabled": "no", "host": "wled-jukebox.local"},
    "presets": {"idle": "1", "playing": "2", "selecting": "3", "coin": "4",
                "attract": "5", "sleep": "5", "off": "0"},
    "timing": {"selecting_seconds": "30", "coin_seconds": "3"},
}

def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)

# ---- LED strips on the Pi's pins -----------------------------------------
# WS2812B / WS2811 LEDs need a 800 kHz signal with exact timing, which Linux
# can't make by switching a pin. The Pi 5's "ws2812-pio" overlay makes it on
# any pin in hardware (/dev/leds-...). An SPI pin (/dev/spidevX.Y) works too:
# it sends 8 bits per LED bit at 6.4 MHz, 11111000 = "1", 11000000 = "0".
SPI_HZ = 6_400_000
_BITS = [bytes(0xF8 if b & (0x80 >> i) else 0xC0 for i in range(8)) for b in range(256)]
_RESET = bytes(64)   # 80 us of low after a frame tells the LEDs to show it

# ---- the music, read straight from the Pi's sound output ----------------
# Fruitbox plays through PipeWire (the Pi desktop's sound system). PipeWire
# offers a "monitor" of every output: a copy of exactly what goes to the DAC.
# The bridge records that copy (no microphone), so the lights follow the
# music itself, not the room. AUDIO.bass and AUDIO.level run 0..1, scaled to
# the music's own loudness (so it works at any Fruitbox volume), and
# AUDIO.beat_t is the time of the last bass hit.
class Audio:
    RATE = 11025
    CHUNK = 256                     # about 23 ms of sound per update

    def __init__(self):
        self.bass = self.level = 0.0
        self.beat_t = -1.0
        self.live = False           # True while sound is coming in
        self._lp = 0.0
        self._bass_peak = self._lvl_peak = 1e-3
        self._bass_avg = 0.0

    def beat(self, now, length=0.25):
        """1.0 right on a beat, fading to 0 over `length` seconds."""
        return max(0.0, 1 - (now - self.beat_t) / length) if self.live else 0.0

    def feed(self, raw):
        import array
        a = array.array("h", raw)
        if not a:
            return
        k = 2 * math.pi * 150 / self.RATE  # one-pole low-pass at about 150 Hz
        k = k / (k + 1)
        lp, bsum, ssum = self._lp, 0.0, 0.0
        for x in a:
            lp += (x - lp) * k
            bsum += lp * lp
            ssum += x * x
        self._lp = lp
        bass = math.sqrt(bsum / len(a)) / 32768
        lvl = math.sqrt(ssum / len(a)) / 32768
        # auto gain: remember the loudest recent value, let it sink slowly
        self._bass_peak = max(bass, self._bass_peak * 0.998, 1e-3)
        self._lvl_peak = max(lvl, self._lvl_peak * 0.998, 1e-3)
        b = bass / self._bass_peak
        self.bass += (b - self.bass) * (0.6 if b > self.bass else 0.15)   # fast up, slower down
        self.level += (lvl / self._lvl_peak - self.level) * 0.3
        now = time.monotonic()
        if b > 0.35 and b > self._bass_avg * 1.5 and now - self.beat_t > 0.18:
            self.beat_t = now
        self._bass_avg += (b - self._bass_avg) * 0.08
        self.live = lvl > 0.002

    def run(self, cmd):
        import shlex, subprocess
        while True:
            try:
                p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL)
                log("sound: listening to the Pi's output")
                while True:
                    raw = p.stdout.read(self.CHUNK * 2)
                    if not raw:
                        break
                    self.feed(raw)
            except OSError as e:
                log("sound:", e)
            self.live, self.bass, self.level = False, 0.0, 0.0
            log("sound: capture stopped, retrying in 5 s")
            time.sleep(5)

AUDIO = Audio()

# Firestar colours (red, yellow, lime) as RGB
RED, YELLOW, LIME, GOLD = (255, 20, 0), (255, 170, 0), (120, 255, 0), (255, 120, 0)

def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))

def _scale(c, k):
    return tuple(int(x * k) for x in c)

# Each pattern is f(n, t, since, mem) -> list of n (r, g, b) for ONE strip:
# t = seconds since the bridge started, since = seconds since this pattern
# began, mem = a dict the pattern can keep between frames (one per strip).
def pat_off(n, t, since, mem):
    return [(0, 0, 0)] * n

def _heat_color(h):
    # black -> red -> orange -> yellow-white, like glowing embers
    if h < 0.4:
        return _mix((0, 0, 0), (255, 0, 0), h / 0.4)
    if h < 0.8:
        return _mix((255, 0, 0), (255, 140, 0), (h - 0.4) / 0.4)
    return _mix((255, 140, 0), (255, 220, 120), (h - 0.8) / 0.2)

def pat_fire(n, t, since, mem):
    # playing: flames rising from LED 0 along the strip (classic "Fire2012")
    heat = mem.setdefault("heat", [0.3] * n)
    for i in range(n):                                   # cool down
        heat[i] = max(0.0, heat[i] - random.uniform(0, 0.09))
    for i in range(n - 1, 1, -1):                        # heat drifts up
        heat[i] = (heat[i] + heat[i - 1] + heat[i - 2]) / 3
    react = mem.get("react", False) and AUDIO.live
    chance = 0.15 + 0.85 * AUDIO.bass if react else 0.5
    for _ in range(max(1, n // 20)):                     # new flames, anywhere along the strip
        if random.random() < chance:
            j = random.randrange(n)
            heat[j] = min(1.0, heat[j] + random.uniform(0.6, 1.0))
    if react and mem.get("beat_t") != AUDIO.beat_t:     # a bass hit: a burst of flames
        mem["beat_t"] = AUDIO.beat_t
        for _ in range(max(2, n // 8)):
            j = random.randrange(n)
            heat[j] = min(1.0, heat[j] + 0.8)
    # the whole strip glows like embers; flames flicker on top
    return [_heat_color(0.25 + 0.75 * h * random.uniform(0.8, 1.0)) for h in heat]

def pat_white(n, t, since, mem):
    # plain bright white (on 4-colour strips, just the white chips)
    return [(255, 255, 255)] * n

def pat_candle(n, t, since, mem):
    # idle: soft warm candle light, every LED flickering gently on its own
    lv = mem.setdefault("lv", [0.8] * n)
    out = []
    for i in range(n):
        lv[i] += (random.uniform(0.55, 1.0) - lv[i]) * 0.15
        out.append(_scale((255, 110, 20), lv[i]))
    return out

def pat_aurora(n, t, since, mem):
    # attract: slow waves of green, teal and violet, like the northern lights
    out = []
    for i in range(n):
        x = i / max(n, 1)
        w1 = 0.5 + 0.5 * math.sin(2 * math.pi * (x * 1.3 + t * 0.05))
        w2 = 0.5 + 0.5 * math.sin(2 * math.pi * (x * 0.7 - t * 0.03) + 1.7)
        c = _mix((0, 255, 80), (0, 150, 255), w1)        # green -> teal
        c = _mix(c, (140, 0, 255), w2 * 0.6)             # some violet
        out.append(_scale(c, 0.25 + 0.75 * w1 * w2))
    return out

def pat_lava(n, t, since, mem):
    # slow blobs of deep red and orange sliding past each other, like a lava lamp
    out = []
    for i in range(n):
        x = i / max(n, 1)
        a = 0.5 + 0.5 * math.sin(2 * math.pi * (x * 1.5 - t * 0.06))
        b = 0.5 + 0.5 * math.sin(2 * math.pi * (x * 2.3 + t * 0.04) + 2.0)
        c = _mix((150, 0, 0), (255, 90, 0), a * b)
        out.append(_scale(c, 0.35 + 0.65 * max(a, b)))
    return out

def pat_ocean(n, t, since, mem):
    # calm blue and teal swells
    out = []
    for i in range(n):
        x = i / max(n, 1)
        a = 0.5 + 0.5 * math.sin(2 * math.pi * (x * 1.1 - t * 0.07))
        b = 0.5 + 0.5 * math.sin(2 * math.pi * (x * 3.1 + t * 0.05) + 1.0)
        c = _mix((0, 40, 200), (0, 200, 180), a)
        out.append(_scale(c, 0.3 + 0.7 * (a * 0.7 + b * 0.3)))
    return out

def pat_breathe(n, t, since, mem):
    # slow warm red glow that rises and falls every 6 s
    k = 0.25 + 0.75 * (0.5 - 0.5 * math.cos(t * 2 * math.pi / 6))
    return [_scale(RED, k)] * n

def pat_firestar(n, t, since, mem):
    # red -> yellow -> lime bands drifting slowly along the strip
    out = []
    for i in range(n):
        x = (i / max(n, 1) * 2 - t * 0.15) % 1.0
        if x < 1 / 3:
            c = _mix(RED, YELLOW, x * 3)
        elif x < 2 / 3:
            c = _mix(YELLOW, LIME, x * 3 - 1)
        else:
            c = _mix(LIME, RED, x * 3 - 2)
        out.append(c)
    return out

def pat_pulse(n, t, since, mem):
    # bright yellow, quick pulse twice a second
    k = 0.55 + 0.45 * math.cos(since * 2 * math.pi * 2)
    return [_scale(YELLOW, k)] * n

def pat_sparkle(n, t, since, mem):
    # gold sparkles that fade out
    sparks = mem.setdefault("sparks", {})
    for _ in range(max(1, n // 15)):
        sparks[random.randrange(n)] = 1.0
    out = [(0, 0, 0)] * n
    for i in list(sparks):
        out[i] = _scale(GOLD, sparks[i])
        sparks[i] -= 0.08
        if sparks[i] <= 0:
            del sparks[i]
    return out

def pat_rainbow(n, t, since, mem):
    # full rainbow chasing along the strip
    return [tuple(int(v * 255) for v in colorsys.hsv_to_rgb((i / max(n, 1) - t * 0.2) % 1.0, 1, 1))
            for i in range(n)]

def pat_vu(n, t, since, mem):
    # a jukebox VU meter: lights grow out from the middle with the music,
    # lime -> yellow -> red toward the ends, and the peak dot falls back slowly
    half = n / 2
    lvl = (0.6 * AUDIO.bass + 0.4 * AUDIO.level) if AUDIO.live else 0.0
    peak = max(lvl, mem.get("peak", 0.0) - 0.012)
    mem["peak"] = peak
    out = []
    for i in range(n):
        d = abs(i + 0.5 - half) / half                  # 0 in the middle, 1 at the ends
        c = _mix(LIME, YELLOW, d * 2) if d < 0.5 else _mix(YELLOW, RED, d * 2 - 1)
        if d <= lvl:
            out.append(c)
        elif abs(d - peak) < 1.0 / n:
            out.append(c)
        else:
            out.append(_scale(c, 0.06))                  # faint glow for the unlit part
    return out

PATTERNS = {"off": pat_off, "white": pat_white, "vu": pat_vu, "fire": pat_fire, "candle": pat_candle, "aurora": pat_aurora,
            "lava": pat_lava, "ocean": pat_ocean,
            "breathe": pat_breathe, "firestar": pat_firestar, "pulse": pat_pulse,
            "sparkle": pat_sparkle, "rainbow": pat_rainbow}

# ---- scenes: patterns that use all the strips together -------------------
# A scene is f(ns, t, since, mems) -> one colour list per patterned strip,
# where ns = LEDs on each strip in [leds] strips order (top to bottom) and
# mems = one dict per strip. Positions run left to right on every strip
# (reverse = yes in a strip's section fixes a strip fed from the other end).
# The "path" goes along the top strip, back along the next one, and so on,
# like a snake, so something moving off the end of one strip carries on into
# the next.
def _on_path(ns, colors):
    out, i = [], 0
    for s, n in enumerate(ns):
        part = colors[i:i + n]
        out.append(part[::-1] if s % 2 else part)
        i += n
    return out

def scene_flow(ns, t, since, mems):
    # attract: the aurora flows as one long wave through all the strips
    return _on_path(ns, pat_aurora(sum(ns), t, since, mems[0]))

def scene_rising(ns, t, since, mems):
    # flames start on the bottom strip and rise into the strips above: each
    # strip shows the heat of the strip below a moment later, a bit cooler,
    # so a burst on a bass hit climbs from the subs up to the window
    bottom = len(ns) - 1
    out = [None] * len(ns)
    out[bottom] = pat_fire(ns[bottom], t, since, mems[bottom])
    hist = mems[0].setdefault("hist", [])
    hist.insert(0, list(mems[bottom]["heat"]))
    del hist[6 * len(ns):]
    for s in range(bottom - 1, -1, -1):
        d = bottom - s                                   # strips above the bottom one
        heat = hist[min(len(hist) - 1, 5 * d)]
        n, m = ns[s], len(heat)
        out[s] = [_heat_color(0.15 + 0.85 * heat[i * m // n] * (0.8 ** d) * random.uniform(0.75, 1.0))
                  for i in range(n)]
    return out

def scene_relay(ns, t, since, mems):
    # fireballs run along the top strip, drop to the next and run back, and so
    # on through every strip, over a glow of embers; with music each bass hit
    # sends a new one, otherwise one leaves every 2.5 s
    m = mems[0]
    total = sum(ns)
    dt = min(0.1, t - m.get("t", t))
    m["t"] = t
    balls = m.setdefault("balls", [])
    react = m.get("react", False) and AUDIO.live
    if react:
        if m.get("beat_t") != AUDIO.beat_t and len(balls) < 6:
            m["beat_t"] = AUDIO.beat_t
            balls.append(0.0)
    elif since - m.get("last", -99) > 2.5:
        m["last"] = since
        balls.append(0.0)
    speed = 70.0                                         # LEDs a second, about 1 s per strip
    balls[:] = [b + speed * dt for b in balls if b < total + 20]
    glow = [_scale(c, 0.2) for c in pat_candle(total, t, since, m)]
    for b in balls:
        for k in range(16):                              # a bright head with a fading tail
            i = int(b) - k
            if 0 <= i < total:
                c = _mix((255, 230, 140), YELLOW, k / 3) if k < 3 else _mix(YELLOW, RED, (k - 3) / 12)
                glow[i] = tuple(max(x, y) for x, y in zip(glow[i], _scale(c, 1 - k / 16)))
    return _on_path(ns, glow)

def scene_duet(ns, t, since, mems):
    # the strips take turns: one burns bright while the others drop to embers,
    # then they swap; with music they swap on the beat, otherwise every 1.5 s
    m = mems[0]
    react = m.get("react", False) and AUDIO.live
    if react:
        if m.get("beat_t") != AUDIO.beat_t:
            m["beat_t"] = AUDIO.beat_t
            m["turn"] = m.get("turn", 0) + 1
    elif since - m.get("last", -99) > 1.5:
        m["last"] = since
        m["turn"] = m.get("turn", 0) + 1
    lead = m.get("turn", 0) % len(ns)
    w = m.setdefault("w", [0.3] * len(ns))
    out = []
    for s, n in enumerate(ns):
        w[s] += ((1.0 if s == lead else 0.18) - w[s]) * 0.2   # fade over a few frames
        mems[s]["react"] = react
        out.append([_scale(c, w[s]) for c in pat_fire(n, t + s * 7.3, since, mems[s])])
    return out

SCENES = {"flow": scene_flow, "rising": scene_rising, "relay": scene_relay, "duet": scene_duet}

SAVED = "/var/lib/jukebox-bridge/lights.json"   # on/off and dim level, kept across reboots

RESEND_SECONDS = 10      # a steady picture is sent again this often

class Output:
    """One strip's data pin. /dev/leds-... is a Pi 5 "ws2812-pio" pin (any
    GPIO, set up in /boot/firmware/config.txt); /dev/spidevX.Y is an SPI pin."""
    def __init__(self, path, leds, order, rgbw=False):
        self.path, self.leds, self.order, self.rgbw = path, leds, order, rgbw
        self.fd = self.spi = None
        self.warned = False
        # Only send a frame when it changes (plus one repeat, and a refresh
        # every few seconds): every frame sent over the long 3.3 V data wire
        # is a chance for a bit to be misread, which shows as a random blink.
        self.last, self.repeats, self.sent_at = None, 0, 0.0
        if "spidev" in path:
            self.spi = self.open_spi(path, leds)
        else:
            self.fd = os.open(path, os.O_WRONLY)
            os.pwrite(self.fd, b"\0", 0)     # brightness 0 = send our colours unchanged
            log("LEDs:", leds, "on", path)

    @staticmethod
    def open_spi(path, leds):
        import spidev   # python3-spidev
        bus, dev = map(int, path.split("spidev")[-1].split("."))
        spi = spidev.SpiDev()
        spi.open(bus, dev)
        spi.max_speed_hz = SPI_HZ
        spi.mode = 0
        try:   # a frame sent in pieces flickers; see README "spidev.bufsiz"
            bufsiz = int(open("/sys/module/spidev/parameters/bufsiz").read())
            if bufsiz < leds * 24 + len(_RESET):
                log(f"warning: spidev.bufsiz is {bufsiz}, need {leds * 24 + len(_RESET)} for {leds} LEDs")
        except (OSError, ValueError):
            pass
        log("LEDs:", leds, "on", path, "(SPI)")
        return spi

    def send(self, colors):
        o = self.order
        if self.rgbw:
            # 4-colour LEDs: the white part of each colour goes to the white chip
            colors = [(r - w, g - w, b - w, w) for r, g, b in colors
                      for w in (min(r, g, b),)]
        if self.spi:
            buf = bytearray()
            for c in colors:
                for j in o:
                    buf += _BITS[min(255, int(c[j]))]
                if self.rgbw:
                    buf += _BITS[min(255, int(c[3]))]
            self.spi.writebytes2(bytes(buf) + _RESET)
            return
        # ws2812-pio sends each pixel's bytes in the order 2nd, 1st, 3rd of
        # what we write, so put the colours where the strip's order wants them
        buf = bytearray(4 * len(colors))
        for i, c in enumerate(colors):
            buf[4 * i] = min(255, int(c[o[1]]))
            buf[4 * i + 1] = min(255, int(c[o[0]]))
            buf[4 * i + 2] = min(255, int(c[o[2]]))
            if self.rgbw:
                buf[4 * i + 3] = min(255, int(c[3]))
        now = time.monotonic()
        data = bytes(buf)
        if data == self.last:
            if self.repeats >= 1 and now - self.sent_at < RESEND_SECONDS:
                return
            self.repeats += 1
        else:
            self.repeats = 0
        self.last, self.sent_at = data, now
        try:
            os.pwrite(self.fd, data, 0)
        except OSError as e:
            if e.errno in (27, 28) and not self.warned:    # EFBIG / ENOSPC
                self.warned = True
                log(f"{self.path}: num_leds in config.txt is smaller than leds = {self.leds}")
            elif e.errno not in (27, 28):
                raise

class LedStrip:
    """The cabinet strips, each on its own data pin. The patterned strips run
    a theme: either the same pattern on each strip (each with its own
    flicker), or a scene that plays the strips off each other. The white
    strip behind the numbers stays white. The off key and the dimmer change
    every strip, attract mode dims the white strip too, and the theme key
    changes only the patterned strips. Runs in its own thread so the
    animation stays smooth."""
    def __init__(self, cfg, dry_run=False):
        c = cfg["leds"]
        self.order = [{"R": 0, "G": 1, "B": 2}[ch] for ch in c.get("color_order").upper() if ch in "RGB"]
        self.names = c.get("strips").split()
        wname = c.get("white", "").strip()

        def strip_cfg(name):
            sec = "strip " + name
            leds = cfg.getint(sec, "leds", fallback=61)
            return (cfg.get(sec, "device", fallback=""), leds,
                    cfg.getboolean(sec, "reverse", fallback=False))
        self.cfgs = [strip_cfg(n) for n in self.names]
        self.ns = [x[1] for x in self.cfgs]
        self.white = strip_cfg(wname) if wname else None
        self.white_level = c.getint("white_level") / 100
        self.n = sum(self.ns) + (self.white[1] if self.white else 0)
        self.bright = max(0, min(100, c.getint("brightness")))
        self.period = 1 / max(1, c.getint("fps"))
        self.themes, self.levels = cfg["themes"], cfg["levels"]
        snd = cfg["sound"]
        self.react = snd.get("react").split() if snd.getboolean("enabled") else []
        self.floor = snd.getint("floor") / 100
        self.theme_list = [x for x in self.themes.get("order").split() if x in self.themes]
        self.theme = self.theme_list[0] if self.theme_list else ""
        self.dry = dry_run
        self.on = True
        self.state, self.started = "off", time.monotonic()
        self.mem = [{} for _ in self.ns]
        self.cur_name = None
        # After the theme key, show the theme's active pattern for a few
        # seconds: at idle most themes share the same candle glow, so the
        # change would otherwise not show until a song plays.
        self.preview_s = cfg.getfloat("controls", "preview_seconds", fallback=6)
        self.preview_until = 0.0
        self.load()
        # One output per data pin. Strips can share a pin by being chained end
        # to end: they're sent in the order of `chain` in each one's section
        # (1 = nearest the Pi), or in the order listed if that's not set. A
        # pin that isn't set up yet is skipped.
        allnames = self.names + ([wname] if self.white else [])
        allcfgs = self.cfgs + ([self.white] if self.white else [])
        pins = {}
        for k, (name, (dev, leds, _)) in enumerate(zip(allnames, allcfgs)):
            if dev:
                pos = cfg.getint("strip " + name, "chain", fallback=0) or 100 + k
                pins.setdefault(dev, []).append((pos, k))
        self.pins = []                     # (output, [strip numbers in chain order])
        for dev, items in pins.items():
            idx = [k for _, k in sorted(items)]
            total = sum(allcfgs[k][1] for k in idx)
            out = None
            if not dry_run:
                try:
                    out = Output(dev, total, self.order, c.getboolean("rgbw"))
                except (OSError, ImportError) as e:
                    log(f"strip {' + '.join(allnames[k] for k in idx)}: can't open {dev} ({e}); skipping it")
            if len(idx) > 1:
                log(dev, "chain:", " -> ".join(allnames[k] for k in idx))
            self.pins.append((out, idx))
        self.stopped = False
        threading.Thread(target=self.run, daemon=True).start()

    def blank(self):
        """Turn every strip off and stop animating. Called when the service
        stops (the Pi shutting down or rebooting, or systemctl stop): the
        strips have their own power supply and would otherwise keep showing
        the last frame after the Pi is off."""
        self.stopped = True
        time.sleep(2 * self.period)        # let a frame being sent finish
        for out, idx in self.pins:
            if out and out.fd is not None:
                for _ in range(2):         # twice, in case a bit is misread
                    try:
                        os.pwrite(out.fd, bytes(4 * out.leds), 0)
                    except OSError:
                        pass
                    time.sleep(0.02)
            elif out:
                out.send([(0, 0, 0)] * out.leds)

    # ---- on/off and dimming (from the keyboard or knob) ----------------
    def load(self):
        try:
            d = json.load(open(SAVED))
            self.on, self.bright = bool(d["on"]), int(d["brightness"])
            if d.get("theme") in self.theme_list:
                self.theme = d["theme"]
        except (OSError, ValueError, KeyError, TypeError):
            pass

    def save(self):
        if self.dry:
            return
        try:
            os.makedirs(os.path.dirname(SAVED), exist_ok=True)
            json.dump({"on": self.on, "brightness": self.bright, "theme": self.theme},
                      open(SAVED, "w"))
        except OSError as e:
            log("can't save light settings:", e)

    def toggle(self):
        self.on = not self.on
        log("lights", "on" if self.on else "off")
        self.save()

    def dim(self, step):
        self.on = True
        self.bright = max(5, min(100, self.bright + step))
        log("lights brightness", self.bright, "%")
        self.save()

    def next_theme(self):
        if self.theme_list:
            i = self.theme_list.index(self.theme) if self.theme in self.theme_list else -1
            self.theme = self.theme_list[(i + 1) % len(self.theme_list)]
            self.on = True
            self.preview_until = time.monotonic() + self.preview_s
            log("lights theme", self.theme, "->", self.pattern_name(self.state))
            self.save()

    def set_theme(self, name):
        """Jump straight to one theme (the favourite keys)."""
        if name not in self.theme_list:
            log("favourite theme not in [themes] order:", name)
            return
        self.on = True
        if name != self.theme:
            self.theme = name
        self.preview_until = time.monotonic() + self.preview_s
        log("lights theme", self.theme, "->", self.pattern_name(self.state))
        self.save()

    # ---- states and frames ---------------------------------------------
    def show(self, state):
        if state != self.state:
            self.state, self.started = state, time.monotonic()
            self.mem = [{} for _ in self.ns]
            log("LEDs", state, "->", self.pattern_name(state))

    def pattern_name(self, state):
        if state == "coin":
            return self.themes.get("coin", "sparkle")
        names = (self.themes.get(self.theme, "") or "").split()
        if state == "sleep":               # the theme's 4th pattern, or else its idle one
            return names[3] if len(names) > 3 else (names[0] if names else "off")
        slot = {"idle": 0, "playing": 1, "selecting": 1, "attract": 2}.get(state)
        if slot is not None and time.monotonic() < self.preview_until:
            slot = 1                       # just picked: show the theme's active look
        return names[slot] if slot is not None and slot < len(names) else "off"

    def colors(self, now, t0):
        """One colour list per strip: the patterned strips, then the white one."""
        name = self.pattern_name(self.state)
        if name != self.cur_name:          # a new pattern starts fresh
            self.cur_name, self.started = name, now
            self.mem = [{} for _ in self.ns]
        k = self.levels.getint(self.state, fallback=100) / 100 * self.bright / 100 if self.on else 0
        react = self.state in self.react and AUDIO.live
        if react and name not in ("vu", "relay", "duet", "white"):
            # brightness rides the bass (never below `floor`), with a lift on each beat
            # (the VU meter, relay and duet already show the beat their own way)
            k *= min(1.0, self.floor + (1 - self.floor) * max(AUDIO.bass, AUDIO.beat(now)))
        for m in self.mem:
            m["react"] = react
        if name in SCENES:
            parts = SCENES[name](self.ns, now - t0, now - self.started, self.mem)
        else:
            f = PATTERNS.get(name, pat_off)
            parts = [f(n, now - t0 + s * 7.3, now - self.started, self.mem[s])
                     for s, n in enumerate(self.ns)]
        out = []
        for part, (_, _, rev) in zip(parts, self.cfgs):
            part = [_scale(c, k) for c in part]
            out.append(part[::-1] if rev else part)
        if self.white:
            lw = self.levels.getint(self.state, fallback=100) if self.state in ("attract", "sleep", "idle") else 100
            if self.state == "off":        # shutting down: everything dark
                lw = 0
            w = int(255 * self.white_level * lw / 100 * self.bright / 100) if self.on else 0
            out.append([(w, w, w)] * self.white[1])
        return out

    def run(self):
        t0 = time.monotonic()
        while not self.stopped:
            now = time.monotonic()
            parts = self.colors(now, t0)
            for out, idx in self.pins:
                if out and not self.stopped:
                    try:
                        out.send([c for k in idx for c in parts[k]])
                    except OSError as e:
                        log("LED strip", out.path, e)
                        time.sleep(1)
            time.sleep(max(0, self.period - (time.monotonic() - now)))

# ---- keyboard / knob controls -------------------------------------------
# Watches every keyboard on the Pi (without taking keys away from Fruitbox)
# for the off, dim and theme keys set in [controls]. The defaults are keys
# Fruitbox doesn't use (Scroll Lock, Page Up/Down, Insert, F13-F16, and
# keypad 1-3 for the favourite themes); a
# programmable USB knob set to F14/F15 when turned and F13 when pressed makes
# a dimmer with an off button.
def watch_keys(cfg, leds):
    try:
        import evdev   # python3-evdev
    except ImportError:
        log("controls off: sudo apt install python3-evdev")
        return
    from select import select
    c = cfg["controls"]
    step = c.getint("dim_step")
    actions = {}
    for key, fn in ((c.get("off_key"), leds.toggle),
                    (c.get("dim_up_key"), lambda: leds.dim(step)),
                    (c.get("dim_down_key"), lambda: leds.dim(-step)),
                    (c.get("theme_key"), leds.next_theme)):
        for name in key.split():
            code = evdev.ecodes.ecodes.get(name.upper())
            if code is None:
                log("unknown key name in [controls]:", name)
            else:
                actions[code] = fn
    devices, last_scan = {}, 0
    while True:
        if time.monotonic() - last_scan > 5:            # keyboards plugged in later
            last_scan = time.monotonic()
            for path in evdev.list_devices():
                if path not in devices:
                    try:
                        d = evdev.InputDevice(path)
                        keys = d.capabilities().get(evdev.ecodes.EV_KEY, [])
                        if any(k in actions for k in keys):
                            devices[path] = d
                            log("controls: watching", d.name)
                    except OSError:
                        pass
        if not devices:
            time.sleep(1)
            continue
        ready, _, _ = select(list(devices.values()), [], [], 1)
        for d in ready:
            try:
                for ev in d.read():
                    if ev.type == evdev.ecodes.EV_KEY and ev.value in (1, 2) and ev.code in actions:
                        actions[ev.code]()
            except OSError:                              # unplugged
                devices.pop(d.path, None)

class Bridge:
    def __init__(self, cfg, dry_run=False):
        self.cfg, self.dry = cfg, dry_run
        self.sent_preset = None
        self.flash = None            # (preset, until) for selecting / coin
        self.state_mtime = None
        self.playing = False
        self.attract_mode = False
        self.attract_song = False
        self.mode = None             # the state manager's state; None = it isn't running
        self.leds = LedStrip(cfg, dry_run) if cfg.getboolean("leds", "enabled") else None
        if self.leds and not dry_run:
            threading.Thread(target=watch_keys, args=(cfg, self.leds), daemon=True).start()
            if cfg.getboolean("sound", "enabled"):
                threading.Thread(target=AUDIO.run, args=(cfg.get("sound", "capture"),),
                                 daemon=True).start()

    # ---- Fruitbox state -------------------------------------------------
    def read_state(self):
        path = self.cfg.get("fruitbox", "state_file")
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return
        if mtime == self.state_mtime:
            return
        self.state_mtime = mtime
        try:
            text = open(path, encoding="utf-8", errors="ignore").read().upper()
        except OSError:
            return
        self.playing = "PLAYING" in text
        self.attract_mode = "ATTRACT_ON" in text
        self.attract_song = "ATTRACT_SONG" in text
        log("fruitbox:", "playing" if self.playing else "idle",
            "| attract", "on" if self.attract_mode else "off",
            "| attract song" if self.attract_song else "")

    def read_mode(self):
        try:
            with open(self.cfg.get("fruitbox", "mode_file")) as f:
                mode = f.read().strip().lower() or None
        except OSError:
            mode = None
        if mode != self.mode:
            log("jukebox state:", mode or "no state manager (lights decide for themselves)")
            self.mode = mode

    # ---- events from the Teensy -----------------------------------------
    def on_event(self, ev):
        log("event:", ev)
        kind = ev.split()[0] if ev else ""
        t = self.cfg["timing"]
        if kind in ("key", "select", "page", "cancel") and not self.mode:
            # (with the state manager running, a key makes the jukebox active instead)
            self.flash = ("selecting", time.monotonic() + t.getfloat("selecting_seconds"))
        elif kind == "coin":
            self.flash = ("coin", time.monotonic() + t.getfloat("coin_seconds"))
        # Attract mode itself comes from Fruitbox's state file, which knows
        # whether the button turned it on, off or to another genre.

    # ---- WLED -----------------------------------------------------------
    def wanted(self):
        # The state manager (jukebox-state) decides the jukebox's state for
        # every part; the lights only show it, in the current theme:
        #   active -> the theme's active look     idle / starting -> its idle look
        #   attract -> its attract look           sleep -> its sleep look (4th
        #   pattern, or the idle one)             shutdown -> dark
        # A coin still sparkles for a few seconds (not in sleep or shutdown).
        if self.mode:
            if self.mode == "shutdown":
                return "off"
            if self.mode == "sleep":
                self.flash = None
                return "sleep"
            if self.flash and time.monotonic() < self.flash[1]:
                return self.flash[0]
            self.flash = None
            return {"active": "playing", "attract": "attract"}.get(self.mode, "idle")
        # No state manager (not installed, or stopped): decide from Fruitbox
        # and the sleep file as before.
        if os.path.exists(self.cfg.get("fruitbox", "sleep_file")):
            self.flash = None
            return "sleep"
        if self.flash and time.monotonic() < self.flash[1]:
            return self.flash[0]
        self.flash = None
        if self.playing:
            return "playing"
        return "attract" if self.attract_mode else "idle"

    def update_lights(self):
        name = self.wanted()
        if self.leds:
            self.leds.show(name)
        if not self.cfg.getboolean("wled", "enabled"):
            return
        preset = self.cfg.getint("presets", name)
        if preset == self.sent_preset:
            return
        body = {"on": True, "ps": preset} if preset > 0 else {"on": False}
        url = f"http://{self.cfg.get('wled', 'host')}/json/state"
        if self.dry:
            log("WLED", name, "->", body)
            self.sent_preset = preset
            return
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=2).read()
            log("WLED", name, "preset", preset)
            self.sent_preset = preset
        except OSError as e:
            log("WLED not reachable:", e)    # try again next time round

    # ---- main loop ------------------------------------------------------
    def handle_line(self, line):
        if line.startswith("E:"):
            self.on_event(line[2:].strip())

    def tick(self):
        self.read_mode()
        self.read_state()
        self.update_lights()

def find_port(cfg):
    if cfg.get("teensy", "port"):
        return cfg.get("teensy", "port")
    ports = (glob.glob("/dev/serial/by-id/*Teensy*") + glob.glob("/dev/serial/by-id/*Arduino*")
             + glob.glob("/dev/ttyACM*"))
    return ports[0] if ports else None

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=CONFIG)
    ap.add_argument("--port", help="serial port (default: find the Teensy)")
    ap.add_argument("--dry-run", action="store_true", help="print instead of changing the lights")
    ap.add_argument("--demo", action="store_true", help="show every theme's patterns, 6 s each, then stop")
    args = ap.parse_args()

    cfg = configparser.ConfigParser()
    cfg.read_dict(DEFAULTS)
    cfg.read(args.config)
    if args.port:
        cfg.set("teensy", "port", args.port)
    if args.demo:
        cfg.set("leds", "enabled", "yes")
        strip = LedStrip(cfg, args.dry_run)
        strip.on = True
        for theme in strip.theme_list:
            strip.theme = theme
            for state in ("idle", "playing", "attract"):
                log("demo: theme", theme, "|", state)
                strip.show("off")
                strip.show(state)
                time.sleep(6)
        strip.show("coin")
        time.sleep(3)
        strip.show("off")
        time.sleep(0.5)
        return
    b = Bridge(cfg, args.dry_run)

    def stop(signum, frame):               # shutdown, reboot or systemctl stop
        log("stopping: lights off")
        if b.leds:
            b.leds.blank()
        sys.exit(0)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log("jukebox bridge started;",
        f"{b.leds.n} LEDs on the Pi" if b.leds else "no Pi LEDs",
        "| WLED at " + cfg.get("wled", "host") if cfg.getboolean("wled", "enabled") else "| WLED off")

    import serial   # python3-serial
    while True:
        b.tick()
        port = find_port(cfg)
        if not port:
            time.sleep(1)
            continue
        try:
            with serial.Serial(port, 115200, timeout=0.1) as s:
                log("reading", port)
                while True:
                    raw = s.readline()
                    if raw:
                        b.handle_line(raw.decode(errors="ignore").strip())
                    b.tick()
        except (serial.SerialException, OSError) as e:
            log("serial:", e)   # Teensy unplugged or restarting; retry
            time.sleep(1)

if __name__ == "__main__":
    main()

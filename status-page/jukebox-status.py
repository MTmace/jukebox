#!/usr/bin/env python3
"""Jukebox status page: one place to see everything the jukebox is set to.

  Web page:   http://jukebox.local   (or http://<the Pi's IP>)   refreshes every 5 s
  Raw data:   http://jukebox.local/api/status   (JSON)
  On screen:  macro pad key F24 shows a summary on the main screen for 30 s
              (press it again to close it early). See jukebox-status-overlay.py.

The status page only shows; changes are on the separate Control page
(http://jukebox.local/control): state buttons and start / stop / restart for
the jukebox services.

Where each value comes from
  Fruitbox volume, mute, pause, song, genre, queue, credits, skin
      /dev/shm/jukebox_fruitbox.txt, written once a second by a hidden status
      box that install-status.sh adds to the skin (jukebox_status.txt)
  Fruitbox start-up settings      /home/mtmace/fruitbox/fruitbox.ini
  Bass                            /dev/shm/jukebox_bass.txt or ~/.config/jukebox-bass/level
  Pi output volume, sound output  wpctl (PipeWire)
  DAC level                       amixer -c BossDAC
  Lights on/off, brightness, theme  /var/lib/jukebox-lights/lights.json
  Lights settings                 /home/mtmace/fruitbox/jukebox-lights.ini
  Lights showing                  /dev/shm/jukebox_mode (same mapping as jukebox-lights)
  Jukebox state (state manager)   /dev/shm/jukebox_mode
  Screens                         xrandr, xset
  Network                         hostname -I, nmcli, /proc/net/wireless
  Pi health                       vcgencmd, /proc

Runs as mtmace (systemd service jukebox-status). Log: journalctl -u jukebox-status -f
Test by hand:  python3 /usr/local/bin/jukebox-status.py --print
"""
VERSION = "1.5"   # bump on every change; the status page shows it
# 1.5: the cabinet lights service is now jukebox-lights (was jukebox-bridge).

import configparser, html, json, os, re, shutil, socket, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOME = "/home/mtmace"
FB = HOME + "/fruitbox"
FRUITBOX_INI = FB + "/fruitbox.ini"
FRUITBOX_FILE = "/dev/shm/jukebox_fruitbox.txt"
LIGHTS_STATE = "/dev/shm/jukebox_state.txt"
JUKEBOX_MODE = "/dev/shm/jukebox_mode"      # written by jukebox-state (state manager)
# Cabinet lights (jukebox-lights). Until install-lights.sh has run, the files
# still have the old jukebox-bridge names, so use those if the new ones are missing.
def _either(new, old):
    return new if os.path.exists(new) or not os.path.exists(old) else old
LIGHTS_INI = _either(FB + "/jukebox-lights.ini", FB + "/jukebox-bridge.ini")
LIGHTS_SAVED = _either("/var/lib/jukebox-lights/lights.json", "/var/lib/jukebox-bridge/lights.json")
BASS_SHOW = "/dev/shm/jukebox_bass.txt"
BASS_SAVED = HOME + "/.config/jukebox-bass/level"
CONFIG_TXT = "/boot/firmware/config.txt"
CMDLINE_TXT = "/boot/firmware/cmdline.txt"
MUSIC_MOUNT = "/mnt/music"
LOGS = [FB + "/launcher.log", FB + "/fruitbox.log", FB + "/jukebox-state.log"]

PORTS = [80, 8080]                 # first one that is free
SHOW_KEYS = ["KEY_F24"]            # macro pad key that shows the summary on screen
OVERLAY = "/usr/local/bin/jukebox-status-overlay.py"

# Our services are found by name: every jukebox-*.service installed on the Pi.
SYSTEM_UNIT_DIR = "/etc/systemd/system"
USER_UNIT_DIR = HOME + "/.config/systemd/user"
STATE_PROGRAM = "jukebox-state"             # the state manager; its WEB_REQUESTS make the state buttons
REQUEST_FILE = "/dev/shm/jukebox_request"   # read by jukebox-state 1.4+
SELF = "jukebox-status"                     # this page: restart only (stop would take the page away)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sh(cmd, timeout=4):
    """Run a command, return its output ('' if it fails)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           shell=isinstance(cmd, str))
        return (r.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def read(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return default


def tail(path, n=15):
    return read(path).splitlines()[-n:]


def age(path):
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return None


def ini_lines(path):
    """The settings in an ini file, without comments or blank lines."""
    out = []
    for ln in read(path).splitlines():
        s = ln.strip()
        if s and not s.startswith(("#", ";")):
            out.append(s)
    return out


# ---------------------------------------------------------------- collectors
def fruitbox():
    d = {"running": False}
    for pid in os.listdir("/proc"):
        if pid.isdigit() and read(f"/proc/{pid}/comm").strip() == "fruitbox":
            d["running"] = True
            break
    a = age(FRUITBOX_FILE)
    d["status_age"] = a
    vals = {}
    for ln in read(FRUITBOX_FILE).splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            vals[k.strip().lower()] = v.strip()
    d.update(vals)
    d["have_status"] = bool(vals)
    # start-up settings from fruitbox.ini
    ini = {}
    for ln in ini_lines(FRUITBOX_INI):
        m = re.match(r"(\w+)\s*=\s*(.*)", ln)
        if m and m.group(1) in ("SongVolume", "SongVolumeStep", "MaxVolume", "MaxPlayQueueLength",
                                "SkinChooserTimeout", "MusicGroupIncludeAllSongs",
                                "MusicGroupAllSongsLabel", "AutoPlay", "AttractMode", "FreePlay"):
            ini.setdefault(m.group(1), m.group(2))
    d["ini"] = ini
    # one MusicPath line per song folder; a folder can belong to several groups
    # (songs in two playlists sit in one shared folder so All Songs has no repeats)
    paths, groups = {}, []
    for ln in ini_lines(FRUITBOX_INI):
        m = re.match(r"MusicPath\s*=\s*([^=]*?)\s*(?:=\s*(.*))?$", ln, re.I)
        if m:
            folder = os.path.basename(m.group(1).rstrip("/"))
            label = (m.group(2) or "").strip() or folder
            paths[folder] = label
            for g in label.split(","):
                if g.strip() and g.strip() not in groups:
                    groups.append(g.strip())
    d["music_paths"] = len(paths)
    d["path_labels"] = paths
    d["groups"] = groups
    d["version"] = sh(["dpkg-query", "-W", "-f=${Version}", "fruitbox"])
    return d


def sound():
    d = {}
    vol = sh(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    m = re.search(r"([\d.]+)", vol)
    d["pi_volume"] = f"{round(float(m.group(1)) * 100)}%" if m else "?"
    d["pi_muted"] = "MUTED" in vol
    insp = sh(["wpctl", "inspect", "@DEFAULT_AUDIO_SINK@"])
    m = re.search(r'node\.description = "([^"]*)"', insp) or re.search(r'node\.name = "([^"]*)"', insp)
    d["output"] = m.group(1) if m else "?"
    d["bass_output_default"] = "jukebox_bass" in insp or "Jukebox Bass" in insp
    bass = read(BASS_SHOW).strip()
    if not bass:
        lv = read(BASS_SAVED).strip()
        bass = f"{float(lv):+g} dB" if re.match(r"^-?[\d.]+$", lv) else ""
    d["bass"] = bass or "flat (0 dB)"
    dig = sh(["amixer", "-c", "BossDAC", "sget", "Digital"])
    m = re.findall(r"\[(\d+%)\]\s*\[([-\d.]+dB)\]", dig)
    d["dac_digital"] = f"{m[0][0]} ({m[0][1]})" if m else ("DAC not found" if not dig else "?")
    cards = read("/proc/asound/cards")
    d["dac_present"] = "BossDAC" in cards or "Boss" in cards
    return d


def lights():
    d = {"on": None, "brightness": None, "theme": None}
    try:
        s = json.loads(read(LIGHTS_SAVED) or "{}")
        d.update(on=s.get("on"), brightness=s.get("brightness"), theme=s.get("theme"))
    except ValueError:
        pass
    cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
    try:
        cfg.read_string(read(LIGHTS_INI))
    except configparser.Error:
        pass
    g = lambda sec, key: cfg.get(sec, key, fallback="")
    d["favorites"] = g("themes", "favorites")
    d["theme_order"] = g("themes", "order")
    d["levels"] = {k: v for k, v in cfg.items("levels")} if cfg.has_section("levels") else {}
    d["white_level"] = g("leds", "white_level")
    d["start_brightness"] = g("leds", "brightness")
    d["sound_reactive"] = g("sound", "enabled")
    d["strips"] = g("leds", "strips")
    if d["brightness"] is None and d["start_brightness"]:
        d["brightness"] = f"{d['start_brightness']} (from ini, never changed)"
    st = read(LIGHTS_STATE).upper()
    d["fruitbox_state"] = ("attract" if "ATTRACT_ON" in st else "playing" if "PLAYING" in st
                           else "idle" if st else "unknown (no state file)")
    ov = [ln for ln in ini_lines(CONFIG_TXT) if "ws2812" in ln]
    d["overlay"] = ov
    d["led_devices"] = sorted(p for p in os.listdir("/dev") if p.startswith("leds"))
    return d


def screens():
    d = {}
    # --current: read X's screen layout without probing the HDMI ports. A full
    # probe (--query) every page refresh switched sleeping screens back on.
    xr = sh(["xrandr", "--current"])
    outs = []
    for ln in xr.splitlines():
        m = re.match(r"^(\S+) (connected|disconnected)( primary)?\s*(\d+x\d+\+\d+\+\d+)?\s*(inverted|left|right|normal)?", ln)
        if m and m.group(2) == "connected":
            outs.append({"name": m.group(1), "geometry": m.group(4) or "off",
                         "rotation": m.group(5) or "normal", "primary": bool(m.group(3))})
    d["outputs"] = outs
    d["x_ok"] = bool(xr)
    xs = sh(["xset", "-q"])
    m = re.search(r"Monitor is (\w+)", xs)
    d["power"] = m.group(1) if m else "?"
    return d


def network():
    d = {"hostname": socket.gethostname()}
    d["ips"] = [ip for ip in sh(["hostname", "-I"]).split() if ":" not in ip]
    ssid, signal = "", ""
    for ln in sh(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "device", "wifi", "list", "--rescan", "no"]).splitlines():
        p = ln.split(":")
        if p and p[0] == "yes":
            ssid, signal = ":".join(p[1:-1]), p[-1] + "%"
    if not ssid:
        ssid = sh(["iwgetid", "-r"])
    d["dbm"] = None
    for ln in read("/proc/net/wireless").splitlines()[2:]:
        p = ln.split()
        if len(p) > 3:
            signal = (signal + " " if signal else "") + f"({p[3].rstrip('.')} dBm)"
            try:
                d["dbm"] = float(p[3].rstrip("."))
            except ValueError:
                pass
    d["wifi"] = ssid or "not on WiFi"
    d["signal"] = signal
    eth = read("/sys/class/net/eth0/operstate").strip()
    d["ethernet"] = "connected" if eth == "up" else "not connected"
    gw = sh("ip route | awk '/default/ {print $3; exit}'")
    d["gateway"] = gw
    d["ping_router"] = ping(gw) if gw else None
    pc = music_host()
    d["music_host"] = pc
    d["ping_music"] = ping(pc) if pc else None
    return d


_ping_cache = {}


def ping(host, count=4):
    """(average ms, % lost) to a host, cached for 15 s so the page stays quick."""
    hit = _ping_cache.get(host)
    if hit and time.monotonic() - hit[0] < 15:
        return hit[1]
    out = sh(["ping", "-n", "-q", "-c", str(count), "-i", "0.2", "-W", "1", host], timeout=8)
    m = re.search(r"([\d.]+)% packet loss", out)
    loss = float(m.group(1)) if m else 100.0
    m = re.search(r"= [\d.]+/([\d.]+)/", out)
    res = (float(m.group(1)) if m else None, loss)
    _ping_cache[host] = (time.monotonic(), res)
    return res


def music_host():
    """The PC the music share comes from (//PC/share in /proc/mounts)."""
    for ln in read("/proc/mounts").splitlines():
        p = ln.split()
        if len(p) > 1 and p[1] == MUSIC_MOUNT and p[0].startswith("//"):
            return p[0][2:].split("/")[0]
    return ""


THROTTLE_BITS = {0: "under-voltage NOW", 1: "CPU speed capped NOW", 2: "throttled NOW",
                 3: "temperature limit NOW", 16: "under-voltage since boot",
                 17: "speed capped since boot", 18: "throttled since boot",
                 19: "temperature limit since boot"}


_cpu_prev = []


def cpu_busy():
    """% of CPU time spent working since the last check (or over 0.3 s the first time).
    Unlike 'load', this ignores programs that are only waiting on WiFi, disk or LEDs."""
    def snap():
        v = [int(x) for x in read("/proc/stat").split("\n", 1)[0].split()[1:]]
        return sum(v), v[3] + (v[4] if len(v) > 4 else 0)       # total, idle + iowait
    if not _cpu_prev:
        _cpu_prev.append(snap())
        time.sleep(0.3)
    try:
        (t0, i0), (t1, i1) = _cpu_prev[-1], snap()
    except (ValueError, IndexError):
        return None
    _cpu_prev[:] = [(t1, i1)]
    return round(100 * (1 - (i1 - i0) / (t1 - t0))) if t1 > t0 else None


def system():
    d = {}
    d["model"] = read("/proc/device-tree/model").strip("\x00\n ")
    up = float(read("/proc/uptime", "0").split()[0] or 0)
    d["uptime"] = f"{int(up // 86400)} d {int(up % 86400 // 3600)} h {int(up % 3600 // 60)} min"
    t = read("/sys/class/thermal/thermal_zone0/temp").strip()
    d["temp_c"] = round(int(t) / 1000, 1) if t.isdigit() else None
    th = sh(["vcgencmd", "get_throttled"])
    m = re.search(r"0x([0-9a-fA-F]+)", th)
    v = int(m.group(1), 16) if m else None
    d["throttled"] = ([w for b, w in THROTTLE_BITS.items() if v & (1 << b)] or ["none"]) if v is not None else ["?"]
    adc = sh(["vcgencmd", "pmic_read_adc", "EXT5V_V"])
    m = re.search(r"=([\d.]+)V", adc)
    d["supply_v"] = float(m.group(1)) if m else None
    d["load"] = read("/proc/loadavg").split()[:3]
    d["cpu_pct"] = cpu_busy()
    d["cores"] = os.cpu_count() or 4
    mem = dict(re.findall(r"(\w+):\s+(\d+)", read("/proc/meminfo")))
    if mem.get("MemTotal"):
        tot, av = int(mem["MemTotal"]), int(mem.get("MemAvailable", 0))
        d["mem_pct"] = round((tot - av) * 100 / tot)
        d["memory"] = f"{(tot - av) // 1024} of {tot // 1024} MB used ({d['mem_pct']}%)"
    du = shutil.disk_usage("/")
    d["disk_pct"] = round(du.used * 100 / du.total)
    d["disk"] = f"{du.free // 2**30} GB free of {du.total // 2**30} GB ({d['disk_pct']}% used)"
    osr = dict(re.findall(r'(\w+)="?([^"\n]*)', read("/etc/os-release")))
    d["os"] = osr.get("PRETTY_NAME", "?")
    d["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return d


def music():
    d = {"share_mounted": os.path.ismount(MUSIC_MOUNT)}
    for name in ("JukeboxGroups", "JukeboxGenres"):
        p = os.path.join(HOME, name)
        if os.path.isdir(p):
            try:
                subs = sorted(x for x in os.listdir(p) if not x.startswith("."))
            except OSError:
                d[name] = "?"
                continue
            d[name] = len(subs)
    return d


def devices():
    usb = [ln.split(" ", 6)[-1] for ln in sh(["lsusb"]).splitlines() if "root hub" not in ln]
    tty = sorted(x for x in os.listdir("/dev") if re.match(r"ttyACM\d+$", x))
    teensy = os.listdir("/dev/serial/by-id") if os.path.isdir("/dev/serial/by-id") else []
    return {"usb": usb, "serial": tty, "teensy": any("Teensy" in x or "16c0" in x.lower() for x in teensy) or bool(tty)}


_version_cache = {}


def program_path(unit, user=False):
    """The script file a service runs (from its ExecStart), or '' if not found."""
    ex = sh(["systemctl"] + (["--user"] if user else []) + ["show", unit, "-p", "ExecStart", "--value"])
    m = re.search(r"argv\[\]=([^;]*)", ex)
    args = m.group(1).split() if m else []
    prog = next((a for a in args[1:] if a.endswith((".py", ".sh"))), args[0] if args else "")
    return prog if prog and os.path.isfile(prog) else ""


_settings_cache = {}


def program_settings(unit, user=False):
    """The number settings at the top of the script a service runs, read from the installed
    file, e.g. {"DEFAULT_DB": 10.0, "MIN_DB": -12.0}. Lines like NAME = 10 or A, B = -12, 12.
    So the page never has its own copy of a setting that could drift from the service."""
    prog = program_path(unit, user)
    if not prog:
        return {}
    try:
        mt = os.stat(prog).st_mtime
        hit = _settings_cache.get(prog)
        if hit and hit[0] == mt:
            return hit[1]
        vals = {}
        num = r"-?\d+(?:\.\d+)?"
        for line in open(prog, encoding="utf-8", errors="replace"):
            m = re.match(rf"^([A-Z][A-Z0-9_]*(?:\s*,\s*[A-Z][A-Z0-9_]*)*)\s*=\s*"
                         rf"({num}(?:\s*,\s*{num})*)\s*(?:#.*)?$", line.rstrip())
            if m:
                names = [x.strip() for x in m.group(1).split(",")]
                nums = [float(x) for x in m.group(2).split(",")]
                if len(names) == len(nums):
                    vals.update(zip(names, nums))
        _settings_cache[prog] = (mt, vals)
        return vals
    except OSError:
        return {}


def num(v):
    """10.0 -> '10', 2.5 -> '2.5'."""
    return f"{v:g}" if isinstance(v, (int, float)) else "?"


def program_version(unit, user=False):
    """('v1.0', '<file> · installed <date> · id <7 chars>') for the program a service runs.

    The version is the script's VERSION = "..." line (bumped on every change).
    The id is the file's git blob hash (what `git hash-object <file>` prints): it matches the repo copy
    of that exact file, so it shows which commit's version is installed."""
    prog = program_path(unit, user)
    if not prog:
        return "", ""
    try:
        st = os.stat(prog)
        hit = _version_cache.get(prog)
        if not hit or hit[0] != st.st_mtime:
            import hashlib
            data = open(prog, "rb").read()
            m = re.search(rb"^VERSION\s*=\s*[\"']([^\"']+)", data, re.M)
            hit = (st.st_mtime, hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()[:7],
                   m.group(1).decode() if m else "")
            _version_cache[prog] = hit
    except OSError:
        return "", ""
    ver = f"v{hit[2]}" if hit[2] else "no version"
    return ver, f"{os.path.basename(prog)} · installed {time.strftime('%b %d %H:%M', time.localtime(hit[0]))} · id {hit[1]}"


def bass_note():
    """'start +10 dB · range -12 to +12 dB', from the installed jukebox-bass script."""
    b = program_settings("jukebox-bass", user=True)
    parts = []
    if "DEFAULT_DB" in b:
        parts.append(f"start {b['DEFAULT_DB']:+g} dB")
    if "MIN_DB" in b and "MAX_DB" in b:
        parts.append(f"range {b['MIN_DB']:+g} to {b['MAX_DB']:+g} dB")
    return " · ".join(parts) + ", 0 = flat" if parts else "0 = flat"


def _units(folder):
    import glob
    return sorted(os.path.basename(p)[:-len(".service")]
                  for p in glob.glob(os.path.join(folder, "jukebox-*.service")))


def system_services():
    """Our system services: every jukebox-*.service in /etc/systemd/system."""
    return _units(SYSTEM_UNIT_DIR)


def user_services():
    """Our user services (run as mtmace): every jukebox-*.service in ~/.config/systemd/user."""
    return _units(USER_UNIT_DIR)


def services():
    out = []
    for s in system_services():
        out.append({"name": s, "state": sh(["systemctl", "is-active", s]) or "not installed",
                    "boot": sh(["systemctl", "is-enabled", s]) or "-", "version": program_version(s)})
    for s in user_services():
        out.append({"name": s + " (user)", "state": sh(["systemctl", "--user", "is-active", s]) or "not installed",
                    "boot": sh(["systemctl", "--user", "is-enabled", s]) or "-",
                    "version": program_version(s, user=True)})
    return out


def logs():
    d = {}
    for p in LOGS:
        if os.path.exists(p):
            d[p] = tail(p, 15)
    for s in system_services():
        d["journal: " + s] = sh(["journalctl", "-u", s, "-n", "12", "--no-pager", "-o", "short"]).splitlines()
    for s in user_services():
        d["journal: " + s] = sh(["journalctl", "--user", "-u", s, "-n", "12", "--no-pager", "-o", "short"]).splitlines()
    return d


def files():
    return {FRUITBOX_INI: ini_lines(FRUITBOX_INI), LIGHTS_INI: ini_lines(LIGHTS_INI),
            CONFIG_TXT: ini_lines(CONFIG_TXT), CMDLINE_TXT: [read(CMDLINE_TXT).strip()]}


def problems(s):
    """Plain-English warnings for the top of the page."""
    p = []
    f, so, li, sc, ne, sy, mu = (s["fruitbox"], s["sound"], s["lights"], s["screens"],
                                 s["network"], s["system"], s["music"])
    if not f["running"]:
        p.append("Fruitbox is not running.")
    elif not f["have_status"]:
        p.append("Fruitbox isn't writing its status (skin line missing?): volume and song unknown. "
                 "Run install-status.sh again.")
    if f.get("mute") == "yes":
        p.append("Fruitbox is MUTED (knob 1 press).")
    if f.get("paused") == "yes":
        p.append("Fruitbox is PAUSED.")
    if so["pi_muted"]:
        p.append("The Pi's sound output is muted.")
    if not so["dac_present"]:
        p.append("The DAC (BossDAC) is not detected.")
    if not so["bass_output_default"] and any(x["name"].startswith("jukebox-bass") and x["state"] == "active"
                                             for x in s["services"]):
        p.append("The Jukebox Bass output is not the default sound output: the bass knob won't do anything.")
    if li["on"] is False:
        p.append("Cabinet lights are switched OFF (knob 3 press).")
    for x in s["services"]:
        if x["state"] not in ("active", "not installed"):
            p.append(f"Service {x['name']} is {x['state']}.")
    if not mu["share_mounted"]:
        p.append(f"The music share {MUSIC_MOUNT} is not connected.")
    if sy["temp_c"] and sy["temp_c"] >= 75:
        p.append(f"Pi is hot: {sy['temp_c']} °C.")
    if any("NOW" in w or "voltage" in w for w in sy["throttled"]):
        p.append("Pi power or heat warning: " + ", ".join(sy["throttled"]) + ".")
    if sy["disk_pct"] >= 90:
        p.append("The USB drive is nearly full: " + sy["disk"] + ".")
    if sc["power"] == "Off":
        p.append("Screens are asleep (any keypad press wakes them).")
    for key, what in (("ping_router", "the WiFi router"), ("ping_music", "the music PC")):
        r = ne.get(key)
        if r and (r[1] >= 25 or (r[0] or 0) > 100):
            p.append(f"Slow or patchy connection to {what}: {fmt_ping(r)}.")
    if isinstance(mu.get("JukeboxGroups"), int) and f["music_paths"] < mu["JukeboxGroups"]:
        p.append(f"Fruitbox loads {f['music_paths']} of the {mu['JukeboxGroups']} song folders: "
                 "some songs are missing from Change Playlist (see launcher.log).")
    usb = " ".join(s["devices"]["usb"]).lower()
    if not ("side-keyboard" in usb or "koolertron" in usb):
        p.append("The macro pad isn't plugged in (or not detected).")
    if not s["devices"]["teensy"]:
        p.append("The keypad Teensy isn't detected: the selection keypad won't work.")
    if not ne["ips"]:
        p.append("No network connection.")
    return p


def collect(with_extras=True):
    s = {"fruitbox": fruitbox(), "sound": sound(), "lights": lights(), "screens": screens(),
         "network": network(), "system": system(), "music": music(), "devices": devices(),
         "services": services()}
    s["problems"] = problems(s)
    if with_extras:
        s["files"], s["logs"] = files(), logs()
    return s


def user_env():
    """Lets wpctl, xrandr and systemctl --user reach the desktop session."""
    uid = os.getuid()
    os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{uid}/bus")
    os.environ.setdefault("DISPLAY", ":0")
    os.environ.setdefault("XAUTHORITY", f"/home/{os.environ.get('USER', 'mtmace')}/.Xauthority")
    return True


# ---------------------------------------------------------------- summary
def fmt_ping(r):
    if not r:
        return "?"
    ms, loss = r
    return ("no reply" if ms is None else f"{ms:.0f} ms") + f", {loss:.0f}% lost"


def lv(value, good, ok):
    """'ok' / 'warn' / 'bad' for a number, where good/ok are tests."""
    if value is None:
        return None
    return "ok" if good(value) else "warn" if ok(value) else "bad"


def summary_rows(s):
    """(section, [(label, value, level, normal range)]) for the page and the on-screen box.
    level is ok / warn / bad (green / amber / red) or None (no right or wrong)."""
    f, so, li, sc, ne, sy = (s["fruitbox"], s["sound"], s["lights"], s["screens"], s["network"], s["system"])
    now = "-"
    if f.get("playing") == "yes":
        now = f"{f.get('title', '')} - {f.get('artist', '')}".strip(" -")
    vol = f.get("volume", "?")
    if f.get("mute") == "yes":
        vol += " (MUTED)"
    url = f"http://{ne['hostname'].lower()}.local"
    R = lambda label, value, level=None, normal="": (label, value, level, normal)
    thr = sy["throttled"]
    thr_lv = ("ok" if thr == ["none"] else "bad" if any("NOW" in w for w in thr)
              else None if thr == ["?"] else "warn")
    pr, pm = ne.get("ping_router"), ne.get("ping_music")
    ping_lv = lambda r: None if not r else ("bad" if r[0] is None or r[1] >= 25 or r[0] > 100 else
                                            "warn" if r[1] > 0 or r[0] > 20 else "ok")
    return [
        ("Playing", [
            R("Jukebox state", read(JUKEBOX_MODE).strip().upper() or "unknown (jukebox-state not running?)",
              None if read(JUKEBOX_MODE).strip() else "warn"),
            R("Now playing", now + (" (paused)" if f.get("paused") == "yes" else "")),
            R("Genre / playlist", f.get("group", "?")),
            R("Songs in queue", f.get("queue", "?")),
            R("Attract mode", f.get("attract", "?")),
            R("Credits", f.get("credits", "?")),
            R("Songs in library", f.get("songs", "?")),
        ]),
        ("Sound", [
            R(f"Vol (0-{f['ini'].get('MaxVolume', '?')})", vol, "warn" if f.get("mute") == "yes" else None),
            R("Vol step / start", f"{f['ini'].get('SongVolumeStep', '?')} / {f['ini'].get('SongVolume', '?')}"),
            R("Bass", so["bass"], None, bass_note()),
            R("DAC Digital level", so["dac_digital"], None if so["dac_present"] else "bad"),
            R("Pi output vol", so["pi_volume"] + (" (muted)" if so["pi_muted"] else ""),
              "ok" if so["pi_volume"] == "100%" and not so["pi_muted"] else "warn", "100%"),
            R("Sound output", so["output"], "ok" if so["bass_output_default"] else "warn", "Jukebox Bass"),
        ]),
        ("Lights", [
            R("Lights", "on" if li["on"] else "OFF" if li["on"] is False else "?",
              "warn" if li["on"] is False else None),
            R("Brightness", f"{li['brightness']}%" if isinstance(li["brightness"], int) else str(li["brightness"] or "?")),
            R("Theme", li["theme"] or "?"),
            R("Favourites 1/2/3", li["favorites"] or "-"),
            R("Lights showing", LIGHT_LOOK.get(read(JUKEBOX_MODE).strip(), li["fruitbox_state"])),
            R("Idle / sleep / white level", f"{li['levels'].get('idle', '?')}% / {li['levels'].get('sleep', '?')}% / "
                                            f"{li['white_level'] or '?'}%"),
        ]),
        ("Screens", [
            R("Skin", f.get("skin", "?")),
        ] + [R(o["name"] + (" (main)" if o["primary"] else ""), f"{o['geometry']} {o['rotation']}")
             for o in sc["outputs"]] + [R("Screens power", sc["power"])]),
        ("Network", [
            R("Name", ne["hostname"]),
            R("IP address", ", ".join(ne["ips"]) or "none", None if ne["ips"] else "bad"),
            R("WiFi signal", f"{ne['wifi']} {ne['signal']}".strip(),
              lv(ne.get("dbm"), lambda v: v >= -67, lambda v: v >= -75),
              "-30 to -67 dBm (closer to 0 is stronger)"),
            R("Ping to router", fmt_ping(pr), ping_lv(pr), "under 20 ms, 0% lost"),
            R("Ping to music PC", fmt_ping(pm) + (f" ({ne['music_host']})" if ne.get("music_host") else ""),
              ping_lv(pm), "under 20 ms, 0% lost"),
            R("Status page", url),
        ]),
        ("Pi", [
            R("Temperature", f"{sy['temp_c']} °C" if sy["temp_c"] is not None else "?",
              lv(sy["temp_c"], lambda v: v < 70, lambda v: v < 80), "under 70 °C (slows down at 80-85)"),
            R("Power / heat warnings", ", ".join(thr), thr_lv, "none"),
            R("5 V supply", f"{sy['supply_v']:.2f} V" if sy["supply_v"] else "?",
              lv(sy["supply_v"], lambda v: v >= 4.9, lambda v: v >= 4.75), "4.9 to 5.2 V"),
            R("CPU use", f"{sy['cpu_pct']}%" if sy.get("cpu_pct") is not None else "?",
              lv(sy.get("cpu_pct"), lambda v: v < 60, lambda v: v < 85), "under 60%"),
            R("Load (1 min, info only)", sy["load"][0] if sy["load"] else "?"),
            R("Memory", sy.get("memory", "?"), lv(sy.get("mem_pct"), lambda v: v < 80, lambda v: v < 90), "under 80% used"),
            R("USB drive", sy["disk"], lv(sy["disk_pct"], lambda v: v < 80, lambda v: v < 90), "under 80% used"),
            R("Up for", sy["uptime"]),
        ]),
    ]


# ---------------------------------------------------------------- web page
CSS = """
:root{--bg:#120d0b;--panel:#1d1512;--line:#3a2a22;--text:#f3e9df;--dim:#b29d8c;--red:#e8392b;--amber:#ffb627;--ok:#7ed957;--good:#8fae7e;--warn:#c9a45c;--bad:#c9675c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.4 system-ui,Segoe UI,Arial,sans-serif}
header{padding:14px 16px;border-bottom:3px solid var(--bad);display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline}
h1{margin:0;font-size:22px;letter-spacing:.06em;color:var(--amber)}header span{color:var(--dim);font-size:14px}
main{padding:16px;display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));max-width:1500px}
section{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
h2{margin:0 0 8px;font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:var(--amber)}
table{width:100%;border-collapse:collapse}td{padding:3px 0;vertical-align:top}td:first-child{color:var(--dim);width:1%;white-space:nowrap;padding-right:14px}
.problems{grid-column:1/-1;border-color:#5e4632}.problems li{margin:3px 0}.allgood{color:var(--good)}
.wide{grid-column:1/-1}details{margin:6px 0}summary{cursor:pointer;color:var(--text)}
pre{white-space:pre-wrap;word-break:break-word;background:#0b0807;padding:8px;border-radius:6px;font-size:13px;margin:6px 0;max-height:420px;overflow:auto}
.lv-ok{color:var(--good)}.lv-warn{color:var(--warn)}.lv-bad{color:var(--bad)}
.normal{color:var(--dim);opacity:.75;font-size:12px;font-weight:400;white-space:normal;margin-bottom:2px}
.st-active{color:var(--good)}.st-bad{color:var(--bad)}
tr.hero td{vertical-align:baseline}
tr.hero td:last-child{font-size:20px;font-weight:700;letter-spacing:.06em}
tr.hero td.lv-warn{color:var(--warn)}.more{font-size:15px;font-weight:400;letter-spacing:0;padding-top:6px}a{color:var(--text)}.more a{display:inline-block;color:var(--text);text-decoration:none;border:1px solid var(--line);border-radius:6px;padding:3px 10px;background:#241a16}.more a:hover{border-color:var(--dim)}tr.spacer td{height:14px;padding:0}
"""


# Which look the cabinet lights show for each jukebox state.
LIGHT_LOOK = {"active": "active look", "idle": "idle look", "starting": "idle look",
              "attract": "attract look", "sleep": "sleep look", "shutdown": "off"}

# What each state of the state manager (jukebox-state) means. The {names} are filled in
# from the installed jukebox-state.py's settings (ACTIVE_SECONDS etc.) when the page is shown.
STATES = [
    ("starting", "Starting up",
     "From power-on until Fruitbox is up and running.",
     "Fruitbox has started.",
     "Screens show the desktop, then Fruitbox. Keys do nothing yet."),
    ("idle", "Idle",
     "No song playing and nobody has touched a key, knob or coin for {active} seconds.",
     "A song starts, any key or knob is used, or a coin goes in (goes to Active). "
     "{sleep_rule}",
     "Screens on, no music. Lights show the theme's idle look; the selection lamps twinkle."),
    ("active", "Active",
     "A song is playing, or a key, knob or coin was used in the last {active} seconds.",
     "{active} seconds after the last song ends and the last key press (goes to Idle). "
     "Pause pressed twice goes to Sleep.",
     "Screens on, music plays. Lights show the theme's playing look."),
    ("attract", "Attract",
     "Attract mode is on (the attract key): Fruitbox plays random songs by itself.",
     "The attract key again (goes to Active or Idle), or Pause pressed twice (Sleep). "
     "It never goes to sleep by itself.",
     "Screens on, random songs play. Lights show the theme's attract look."),
    ("sleep", "Sleep",
     "{sleep_when}",
     "Any keypad key, macro pad key or knob PRESS, or a coin (goes to Active). "
     "That press only wakes it; it does nothing else. Turning a knob does not wake it.",
     "Both screens off, music stopped, queue cleared, attract off, Fruitbox paused. "
     "Lights dim to their sleep glow."),
    ("shutdown", "Shutting down",
     "Reboot (F20), Rebuild Playlist (F21) or Shut Down (F22) pressed twice within {confirm} seconds.",
     "The Pi restarts (F20, F21) or switches off (F22).",
     "F21 first rescans the music, which takes a minute or two. After F22, wait until "
     "the screens and lights go dark before switching the power off."),
]


def states_page():
    e = html.escape
    now = read(JUKEBOX_MODE).strip().lower()
    out = ["<!doctype html><html lang=en><head><meta charset=utf-8>",
           "<meta name=viewport content='width=device-width,initial-scale=1'>",
           "<title>Jukebox states</title><style>", CSS, STATES_CSS, "</style></head><body>",
           "<header><h1>JUKEBOX STATES</h1><span><a href='/'>back to status</a> · now: "
           f"<b>{e(now.upper() or 'unknown')}</b></span></header><main class=states>"]
    st = program_settings("jukebox-state")
    mins = st.get("SLEEP_MINUTES")
    fill = {"active": num(st.get("ACTIVE_SECONDS")), "confirm": num(st.get("CONFIRM_SECONDS")),
            "sleep_rule": ("It never goes to sleep by itself (SLEEP_MINUTES = 0)." if mins == 0 else
                           f"After {num(mins)} minutes in Idle it goes to Sleep by itself."),
            "sleep_when": ("Pause pressed twice (sleeping by itself is off)." if mins == 0 else
                           f"After {num(mins)} minutes in Idle, or Pause pressed twice.")}
    for key, name, when, leaves, happens in STATES:
        when, leaves, happens = (t.format(**fill) for t in (when, leaves, happens))
        cls = " class=current" if key == now else ""
        out.append(f"<section{cls}><h2>{e(name)}{' · NOW' if key == now else ''}</h2><dl>"
                   f"<dt>When</dt><dd>{e(when)}</dd>"
                   f"<dt>What should happen</dt><dd>{e(happens)}</dd>"
                   f"<dt>Leaves when</dt><dd>{e(leaves)}</dd></dl></section>")
    out.append("<section class=wide><h2>Good to know</h2><p>The state manager (service "
               "<b>jukebox-state</b>) is the only part that decides the state; the lights, lamps "
               "and this page just follow it. Its log is <b>/home/mtmace/fruitbox/jukebox-state.log</b>, "
               "one line for every change with the reason. Service keys and Pause need two presses "
               f"within {fill['confirm']} seconds, so a bumped key does nothing. The times on this "
               "page are read from the installed jukebox-state.py.</p></section>")
    out.append("</main></body></html>")
    return "".join(out)


# Plain words for the light patterns, used when the installed ini has no
# description comments (older ini).
PATTERN_TEXT = {
    "white": "steady white", "candle": "warm candle flicker",
    "fire": "flames rising along each strip, pulsing with the bass",
    "aurora": "northern-lights waves (green, teal, violet)",
    "rising": "flames start on the lower strip and climb into the ones above",
    "flow": "waves flowing through all the strips in turn",
    "relay": "fireballs run along the top strip and drop strip to strip, one per beat",
    "duet": "the strips take turns, one burning bright while the others drop to embers",
    "breathe": "slow red glow", "vu": "VU meter growing from the middle with the music, lime to red",
    "firestar": "red, yellow and lime bands drifting (the skin's colours)",
    "lava": "red and orange lava-lamp blobs", "ocean": "calm blue and teal swells",
    "rainbow": "rainbow chasing along the strips", "sparkle": "sparkles", "pulse": "pulsing glow",
    "off": "off"}


def read_themes():
    """Themes from the installed lights ini: [(name, key, patterns, [(state, text)])], notes.

    The ini documents each theme in comments right above its line:
        # Fire
        #   idle:     warm candle flicker, 20 %
        fire = candle fire aurora
    so this page always matches the lights that are installed."""
    themes, notes, block, in_themes, order = [], [], [], False, []
    for raw in read(LIGHTS_INI).splitlines():
        ln = raw.strip()
        if ln.startswith("["):
            in_themes = ln.lower() == "[themes]"
            block = []
            continue
        if not in_themes:
            continue
        if ln.startswith(("#", ";")):
            block.append(ln.lstrip("#; ").rstrip())
            continue
        m = re.match(r"([\w-]+)\s*=\s*(.*)", ln)
        if not m:
            block = []
            continue
        key, val = m.group(1), m.group(2)
        if key in ("order", "favorites"):
            if key == "order":
                order = val.lower().split()
            block = []
            continue
        title, looks = key.capitalize(), []
        if key == "coin":                       # not a theme: the coin flash, any theme
            themes.append(("Coin drop", key, val.split(), [("any theme", " ".join(block) + f" ({val})")]))
            block = []
            continue
        for i, c in enumerate(block):
            sm = re.match(r"(startup|starting|idle|active|playing|attract|sleep|shutdown)\s*:\s*(.*)", c, re.I)
            if sm:
                looks.append((sm.group(1).lower(), sm.group(2)))
            elif looks == [] and c and not c.lower().startswith(("each theme", "brightness", "patterns", "scenes")):
                if i + 1 < len(block) and re.match(r"(startup|starting|idle)\s*:", block[i + 1], re.I):
                    title = c
                elif not themes:
                    notes.append(c)
            elif not themes and c:
                notes.append(c)
        themes.append((title, key, val.split(), looks))
        block = []
    if order:                                   # theme key's order first; the rest are parked
        rank = {k: i for i, k in enumerate(order)}
        themes = [t + ((t[1].lower() not in rank and t[1] != "coin"),) for t in themes]
        themes.sort(key=lambda t: (t[4], t[1] == "coin", rank.get(t[1].lower(), 99)))
    else:
        themes = [t + (False,) for t in themes]
    return themes, notes


def themes_page():
    e = html.escape
    themes, notes = read_themes()
    li = lights()
    now = (li.get("theme") or "").lower()
    out = ["<!doctype html><html lang=en><head><meta charset=utf-8>",
           "<meta name=viewport content='width=device-width,initial-scale=1'>",
           "<title>Light themes</title><style>", CSS, STATES_CSS, "</style></head><body>",
           "<header><h1>LIGHT THEMES</h1><span><a href='/'>back to status</a> · now: "
           f"<b>{e(now or 'unknown')}</b> · jukebox state: <b>{e(read(JUKEBOX_MODE).strip() or 'unknown')}</b>"
           "</span></header><main class=states>"]
    if not themes:
        out.append(f"<section class=wide><h2>No themes found</h2><p>Couldn't read the [themes] section of "
                   f"{e(LIGHTS_INI)}.</p></section>")
    shown_parked = False
    for title, key, pats, looks, parked in themes:
        if parked and not shown_parked:
            shown_parked = True
            out.append("<section class=wide><h2>Parked themes</h2><p>Not in the theme key's list "
                       "(the order line in " + e(os.path.basename(LIGHTS_INI)) + "), so the theme key skips them.</p></section>")
        cur = key.lower() == now
        mode = read(JUKEBOX_MODE).strip()
        mode = {"starting": "startup"}.get(mode, mode)
        mark = lambda st: " style='color:var(--amber)'" if cur and st == mode else ""
        if not looks:                           # older ini without the comments: describe the patterns
            lv = li.get("levels") or {}
            pct = lambda st: f", {lv[st]} %" if lv.get(st) else ""
            word = lambda i: PATTERN_TEXT.get(pats[i], pats[i]) if i < len(pats) else ""
            looks = [("startup", word(0) + " (idle look)"), ("idle", word(0) + pct("idle")),
                     ("active", word(1) + pct("playing")), ("attract", word(2) + pct("attract")),
                     ("sleep", (word(3) if len(pats) > 3 else word(0)) + pct("sleep")), ("shutdown", "off")]
            if key == "coin":
                looks = [("any theme", "shown for a few seconds when a coin drops: " + word(0))]
        rows = "".join(f"<dt{mark(st)}>{e(st)}{' · now' if mark(st) else ''}</dt><dd>{e(tx)}</dd>"
                       for st, tx in looks)
        cls = " class=current" if cur else " class=parked" if parked else ""
        tag = " · NOW" if cur else " · not active" if parked else ""
        out.append(f"<section{cls}><h2>{e(title)}{tag}</h2>"
                   f"<dl>{rows}</dl></section>")
    if notes:
        out.append("<section class=wide><h2>Good to know</h2><p>" + e(" ".join(notes)) + "</p></section>")
    out.append("</main></body></html>")
    return "".join(out)


STATES_CSS = """
main.states{grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
dl{margin:0}dt{color:var(--dim);font-size:13px;margin-top:8px}dd{margin:2px 0 0}
section.current{border-color:var(--amber);border-width:2px}
header a{color:var(--text)}
section.parked{opacity:.45;filter:grayscale(1)}section.parked h2{color:var(--dim)}
"""

def page(s):
    e = html.escape
    out = ["<!doctype html><html lang=en><head><meta charset=utf-8>",
           "<meta name=viewport content='width=device-width,initial-scale=1'>",
           "<title>Jukebox status</title><style>", CSS, "</style></head><body>",
           f"<header><h1>SEEBURG FIRESTAR · STATUS</h1><span>{e(s['system']['time'])} · refreshes every 5 s · "
           "<a href='/control'>control</a></span></header><main>"]
    pr = s["problems"]
    out.append("<section class=problems><h2>Things to check</h2>")
    out.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in pr) + "</ul>" if pr
               else "<p class=allgood>Nothing wrong found.</p>")
    out.append("</section>")
    for title, rows in summary_rows(s):
        out.append(f"<section><h2>{e(title)}</h2><table>")
        for k, v, level, normal in rows:
            note = f"<div class=normal>normal: {e(normal)}</div>" if normal else ""
            hero = " class=hero" if k == "Jukebox state" else ""
            link = "<div class=more><a href='/states'>status menu</a></div>" if hero else ""
            out.append(f"<tr{hero}><td>{e(k)}{note}</td><td class='lv-{level or 'none'}'>{e(str(v))}{link}</td></tr>")
            if hero:
                out.append("<tr class=spacer><td colspan=2></td></tr>")
        if title == "Lights":
            out.append("<tr><td colspan=2 class=more><a href='/themes'>light themes: what each one shows</a></td></tr>")
        out.append("</table></section>")
    # services, devices, music
    out.append("<section><h2>Services</h2><table>")
    for x in s["services"]:
        cls = "st-active" if x["state"] == "active" else "st-bad" if x["state"] != "not installed" else ""
        ver, detail = x.get("version") or ("", "")
        ver = f"<div class=normal>{e(ver)}</div>" if ver else ""
        detail = f"<div class=normal>{e(detail)}</div>" if detail else ""
        out.append(f"<tr><td>{e(x['name'])}{ver}</td><td class='{cls}'>{e(x['state'])} · at boot: {e(x['boot'])}{detail}</td></tr>")
    f = s["fruitbox"]
    fa = f["status_age"]
    fv = f"<div class=normal>v{e(f['version'])}</div>" if f.get("version") else ""
    out.append(f"<tr><td>fruitbox{fv}</td><td class='{'st-active' if f['running'] else 'st-bad'}'>"
               f"{'running' if f['running'] else 'NOT running'}"
               f"{'' if fa is None else f' · last change {int(fa)} s ago'}</td></tr></table></section>")
    m, dv = s["music"], s["devices"]
    out.append("<section><h2>Music and devices</h2><table>")
    def row(label, ok, text):
        out.append(f"<tr><td>{e(label)}</td><td class='lv-{'ok' if ok else 'bad'}'>{e(text)}</td></tr>")
    row("Music share", m["share_mounted"], "connected" if m["share_mounted"] else "NOT connected")
    def listed(label, count, items, noun):
        out.append(f"<tr><td>{e(label)}</td><td><details><summary>{e(str(count))} {noun}</summary>" +
                   "<br>".join(e(x) for x in items) + "</details></td></tr>")
    listed("Playlists in Fruitbox", len(f.get("groups", [])), f.get("groups", []), "playlists")
    usb = " ".join(dv["usb"]).lower()
    pad = "side-keyboard" in usb or "koolertron" in usb
    row("Macro pad", pad, "found" if pad else "NOT found")
    row("Keypad (Teensy)", dv["teensy"], "found" if dv["teensy"] else "NOT found")
    leds = s["lights"]["led_devices"]
    row("LED strip output", bool(leds), "ready" if leds else "NOT set up")
    out.append("<tr><td>All USB devices</td><td><details><summary>show devices</summary>" +
               "<br>".join(e(u) for u in dv["usb"]) + "</details></td></tr>")
    out.append("</table></section>")
    # settings files and logs
    out.append("<section class=wide><h2>Settings files</h2>")
    for p, lines in s.get("files", {}).items():
        out.append(f"<details><summary>{e(p)}</summary><pre>{e(chr(10).join(lines))}</pre></details>")
    out.append("</section><section class=wide><h2>Recent log lines</h2>")
    for p, lines in s.get("logs", {}).items():
        out.append(f"<details><summary>{e(p)}</summary><pre>{e(chr(10).join(lines) or '(empty)')}</pre></details>")
    out.append("</section></main>")
    # refresh without losing which boxes are open
    out.append("""<script>
const KEY='jbOpen';try{const o=JSON.parse(sessionStorage.getItem(KEY)||'[]');
document.querySelectorAll('details').forEach((d,i)=>{if(o.includes(d.querySelector('summary').textContent))d.open=true})}catch(e){}
setInterval(()=>{try{sessionStorage.setItem(KEY,JSON.stringify([...document.querySelectorAll('details[open] summary')].map(s=>s.textContent)));
sessionStorage.setItem('jbY',scrollY)}catch(e){}location.reload()},5000);
try{scrollTo(0,+sessionStorage.getItem('jbY')||0)}catch(e){}
</script></body></html>""")
    return "".join(out)


# ---------------------------------------------------------------- control page
# Status stays read-only; every action lives on /control, sent as a form POST (a
# link or a page refresh can never trigger one). Nothing here is a list of its
# own: the services are the installed jukebox-*.service files, the state buttons
# are WEB_REQUESTS / WEB_CONFIRM in the installed jukebox-state.py.
SERVICE_OPS = ("start", "restart", "stop")
SERVICE_CONFIRM = ("stop",)


def state_requests():
    """({word: label}, {words that need a confirm}) from the installed state manager."""
    import ast
    prog = program_path(STATE_PROGRAM)
    try:
        text = open(prog, encoding="utf-8").read() if prog else ""
    except OSError:
        text = ""
    found = {}
    for name in ("WEB_REQUESTS", "WEB_CONFIRM"):
        m = re.search(rf"^{name}\s*=\s*([\[({{].*?[\])}}])\s*(?:#.*)?$", text, re.M | re.S)
        try:
            found[name] = ast.literal_eval(m.group(1)) if m else None
        except (ValueError, SyntaxError):
            found[name] = None
    reqs = found["WEB_REQUESTS"] if isinstance(found["WEB_REQUESTS"], dict) else {}
    return ({str(k): str(v) for k, v in reqs.items()},
            set(found["WEB_CONFIRM"] or ()) if reqs else set())


def control_targets():
    """[(unit, user?)] of the services the page may control."""
    return [(u, False) for u in system_services()] + [(u, True) for u in user_services()]


def service_action(unit, user, op):
    """Start / stop / restart one of our services. Returns a message for the page."""
    if (unit, user) not in control_targets() or op not in SERVICE_OPS:
        return "Not one of the jukebox services: nothing done."
    if unit == SELF and op != "restart":
        return "The status page can only restart itself (stopping it would take this page away)."
    cmd = (["systemctl", "--user"] if user else ["sudo", "-n", "systemctl"]) + [op, unit]
    if unit == SELF:
        # answer the browser first, then restart (this process goes away)
        threading.Timer(1.0, lambda: subprocess.run(cmd[:-2] + ["--no-block"] + cmd[-2:])).start()
        return f"Restarting {unit}: the page comes back in a few seconds."
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as ex:
        return f"{op} {unit} failed: {ex}"
    if r.returncode:
        err = (r.stderr or r.stdout or "").strip().splitlines()
        hint = (" (run the status page installer once more: it adds the permission for this)"
                if not user and "password" in " ".join(err).lower() else "")
        return f"{op} {unit} failed: {err[-1] if err else 'code %d' % r.returncode}{hint}"
    state = sh((["systemctl", "--user"] if user else ["systemctl"]) + ["is-active", unit]) or "?"
    log(f"control: {op} {unit} -> {state}")
    return f"{op.capitalize()} {unit}: done, it is now {state}."


def state_action(word):
    reqs, _ = state_requests()
    if word not in reqs:
        return "The installed state manager doesn't take that request: nothing done."
    try:
        tmp = REQUEST_FILE + ".tmp"
        with open(tmp, "w") as f:
            f.write(word + "\n")
        os.replace(tmp, REQUEST_FILE)          # appears in one piece
    except OSError as ex:
        return f"Couldn't send {word}: {ex}"
    log(f"control: asked the state manager for {word}")
    return f"Sent \"{reqs[word]}\" to the state manager; it acts on it within a second or two."


CONTROL_CSS = """
header a{color:var(--text)}
form{display:inline}
button,a.btn{display:inline-block;text-decoration:none;font:inherit;font-size:15px;color:var(--text);background:#241a16;border:1px solid var(--line);
 border-radius:6px;padding:6px 12px;margin:3px 6px 3px 0;cursor:pointer}
button:hover,a.btn:hover{border-color:var(--dim)}button.risky{border-color:#6b3a33}
.big{padding:10px 16px}
.msg{grid-column:1/-1;border-color:var(--amber)}
.confirm{grid-column:1/-1;border-color:var(--bad);border-width:2px}
select{font:inherit;font-size:15px;color:var(--text);background:#241a16;border:1px solid var(--line);
 border-radius:6px;padding:6px 8px;margin:3px 6px 3px 0;max-width:100%}
table.svc{margin-top:10px}
"""


def _form(fields, label, cls=""):
    e = html.escape
    hidden = "".join(f"<input type=hidden name={e(k)} value='{e(v)}'>" for k, v in fields.items())
    return f"<form method=post action=/control>{hidden}<button class='{cls}'>{e(label)}</button></form>"


def control_page(msg="", confirm=None):
    """confirm: dict of form fields waiting for "are you sure?" (shown at the top)."""
    e = html.escape
    now = read(JUKEBOX_MODE).strip().lower()
    reqs, req_confirm = state_requests()
    out = ["<!doctype html><html lang=en><head><meta charset=utf-8>",
           "<meta name=viewport content='width=device-width,initial-scale=1'>",
           "<title>Jukebox control</title><style>", CSS, CONTROL_CSS, "</style></head><body>",
           "<header><h1>JUKEBOX CONTROL</h1><span><a href='/'>back to status</a> · "
           f"state now: <b>{e(now.upper() or 'unknown')}</b> · <a href='/control'>refresh</a></span></header><main>"]
    if confirm:
        what = (f"{confirm['op']} {confirm['unit']}" if confirm.get("kind") == "service"
                else reqs.get(confirm.get("word", ""), confirm.get("word", "")))
        out.append(f"<section class=confirm><h2>Are you sure?</h2><p>{e(what.capitalize())}</p>"
                   + _form(dict(confirm, sure="yes"), "Yes, " + what, "big risky")
                   + "<a class='btn big' href='/control'>Cancel</a></section>")
    if msg:
        out.append(f"<section class=msg><p>{e(msg)}</p></section>")
    out.append("<section><h2>Jukebox state</h2>")
    if reqs:
        opts = "".join(f"<option value='{e(w)}'>{e(l)}{' (asks first)' if w in req_confirm else ''}</option>"
                       for w, l in reqs.items())
        out.append("<p class=normal>Does what the keys do, through the state manager.</p>"
                   "<form method=post action=/control><input type=hidden name=kind value=state>"
                   f"<select name=word aria-label='Jukebox state request'>{opts}</select> "
                   "<button>Go</button></form>")
    else:
        out.append("<p>The installed state manager (jukebox-state) doesn't take requests from this "
                   "page yet: that needs jukebox-state 1.4 or later.</p>")
    out.append("<p><a href='/states'>status menu: what each state means</a></p></section>")
    targets = control_targets()
    units = "".join(f"<option value='{'u' if user else 's'}:{e(unit)}'>{e(unit)}{' (user)' if user else ''}</option>"
                    for unit, user in targets)
    ops = "".join(f"<option value='{op}'>{op.capitalize()}{' (asks first)' if op in SERVICE_CONFIRM else ''}</option>"
                  for op in SERVICE_OPS)
    out.append("<section><h2>Services</h2>"
               "<form method=post action=/control><input type=hidden name=kind value=service>"
               f"<select name=target aria-label=Service>{units}</select> "
               f"<select name=op aria-label=Action>{ops}</select> <button>Go</button></form><table class=svc>")
    for unit, user in targets:
        state = sh((["systemctl", "--user"] if user else ["systemctl"]) + ["is-active", unit]) or "?"
        cls = "st-active" if state == "active" else "st-bad"
        out.append(f"<tr><td>{e(unit)}{' (user)' if user else ''}</td><td class='{cls}'>{e(state)}</td></tr>")
    out.append("</table><p class=normal>Every jukebox-*.service installed on the Pi. "
               "The status page itself can only be restarted.</p></section>")
    out.append("</main></body></html>")
    return "".join(out)


def control_post(fields):
    """Handle one button press. Returns (page, None) to show a confirm page, or
    (None, message) when done: the browser is then sent back to /control with the
    message, so a refresh can't press the button again."""
    kind = fields.get("kind", "")
    sure = fields.get("sure") == "yes"
    if kind == "service":
        if "target" in fields:                       # dropdown value "s:<unit>" or "u:<unit>" (user)
            where, _, unit = fields["target"].partition(":")
            user = where == "u"
        else:                                        # the "are you sure?" form
            unit, user = fields.get("unit", ""), bool(fields.get("user"))
        op = fields.get("op", "")
        if op in SERVICE_CONFIRM and not sure and unit != SELF:
            return control_page(confirm={"kind": "service", "unit": unit, "user": "1" if user else "", "op": op}), None
        return None, service_action(unit, user, op)
    if kind == "state":
        word = fields.get("word", "")
        _, need = state_requests()
        if word in need and not sure:
            return control_page(confirm={"kind": "state", "word": word}), None
        return None, state_action(word)
    return None, "Unknown button: nothing done."


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ("/", "/index.html"):
                body, ctype = page(collect()).encode(), "text/html; charset=utf-8"
            elif path == "/themes":
                body, ctype = themes_page().encode(), "text/html; charset=utf-8"
            elif path == "/states":
                body, ctype = states_page().encode(), "text/html; charset=utf-8"
            elif path == "/control":
                from urllib.parse import parse_qs, urlsplit
                msg = parse_qs(urlsplit(self.path).query).get("msg", [""])[0][:500]
                body, ctype = control_page(msg).encode(), "text/html; charset=utf-8"
            elif path == "/api/status":
                body, ctype = json.dumps(collect(), indent=1, default=str).encode(), "application/json"
            elif path == "/api/summary":
                s = collect(with_extras=False)
                body = json.dumps({"problems": s["problems"], "rows": summary_rows(s)}, default=str).encode()
                ctype = "application/json"
            else:
                self.send_error(404)
                return
        except Exception as ex:                       # never take the page down
            log("error:", repr(ex))
            body, ctype = f"error collecting status: {ex!r}".encode(), "text/plain"
        self.reply(body, ctype)

    def do_POST(self):
        from urllib.parse import parse_qs
        if self.path.split("?")[0] != "/control":
            self.send_error(404)
            return
        try:
            n = min(int(self.headers.get("Content-Length") or 0), 4096)
            fields = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode("utf-8", "replace")).items()}
            page_html, msg = control_post(fields)
        except Exception as ex:                       # never take the page down
            log("control error:", repr(ex))
            page_html, msg = None, f"Error: {ex!r}"
        if page_html is not None:
            self.reply(page_html.encode(), "text/html; charset=utf-8")
            return
        from urllib.parse import quote
        self.send_response(303)
        self.send_header("Location", "/control?msg=" + quote(msg))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def reply(self, body, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass                                # the browser or box hung up first: nothing to do

    def log_message(self, *a):
        pass


# ---------------------------------------------------------------- F24 key
overlay_proc = None


def toggle_overlay(port):
    global overlay_proc
    if overlay_proc and overlay_proc.poll() is None:
        overlay_proc.terminate()
        overlay_proc = None
        log("status box closed")
        return
    log("showing status box on screen")
    overlay_proc = subprocess.Popen([sys.executable, OVERLAY, f"http://127.0.0.1:{port}/api/summary"])


def watch_key(port):
    try:
        import evdev
    except ImportError:
        log("python3-evdev missing: the F24 key won't work (sudo apt install python3-evdev)")
        return
    from select import select
    codes = {evdev.ecodes.ecodes[k] for k in SHOW_KEYS if k in evdev.ecodes.ecodes}
    devs, last = {}, 0
    while True:
        if time.monotonic() - last > 5:
            last = time.monotonic()
            for p in evdev.list_devices():
                if p not in devs:
                    try:
                        d = evdev.InputDevice(p)
                        if codes & set(d.capabilities().get(evdev.ecodes.EV_KEY, [])):
                            devs[p] = d
                            log("watching", d.name, "for", " ".join(SHOW_KEYS))
                    except OSError:
                        pass
        if not devs:
            time.sleep(1)
            continue
        ready, _, _ = select(list(devs.values()), [], [], 1)
        for d in ready:
            try:
                evs = list(d.read())
            except OSError:
                devs.pop(d.path, None)
                continue
            for ev in evs:
                if ev.type == evdev.ecodes.EV_KEY and ev.value == 1 and ev.code in codes:
                    toggle_overlay(port)


def main():
    user_env()
    if "--print" in sys.argv:
        s = collect(with_extras=False)
        for p in s["problems"]:
            print("!", p)
        for title, rows in summary_rows(s):
            print(f"\n== {title}")
            for k, v, level, normal in rows:
                flag = {"warn": " <- check", "bad": " <- PROBLEM"}.get(level, "")
                print(f"  {k:28} {v}{flag}" + (f"   (normal: {normal})" if normal else ""))
                if k == "Jukebox state":
                    print()
        return
    srv = None
    for port in PORTS:
        try:
            srv = ThreadingHTTPServer(("", port), Handler)
            break
        except OSError as ex:
            log(f"port {port} not free ({ex.strerror})")
    if not srv:
        sys.exit("no free port")
    port = srv.server_address[1]
    host = socket.gethostname().lower()
    log(f"status page on http://{host}.local" + ("" if port == 80 else f":{port}"))
    threading.Thread(target=watch_key, args=(port,), daemon=True).start()
    srv.serve_forever()


if __name__ == "__main__":
    main()

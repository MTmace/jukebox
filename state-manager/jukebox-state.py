#!/usr/bin/env python3
"""Jukebox state manager: the one program that decides what state the jukebox is in.

Every other part (cabinet lights, selection lamps, status page) only follows
the state; none of them decides on its own. The state is written as one word to

    /dev/shm/jukebox_mode      starting | idle | active | attract | sleep | shutdown

(a file in memory, gone at power off). The others read it about once a second.

States (see the "Jukebox system states" doc):
  starting   from boot until Fruitbox writes its state file
  idle       no song and no key or coin for ACTIVE_SECONDS (60 s)
  active     a song is playing, or a key / knob / coin in the last 60 s
  attract    attract mode is on (it never goes to sleep by itself)
  sleep      10 min in idle, or the Pause key pressed twice:
             screens off, music stopped, queue cleared, attract off.
             Any key or knob PRESS (or a coin) wakes it into active, and that
             press does nothing else. Knob TURNS are ignored while asleep.
  shutdown   Reboot (F20), Rebuild Playlist (F21) or Shut Down (F22) pressed twice

While asleep Fruitbox is paused (SIGSTOP, resumed on wake): on the Pi 5 its
drawing switches the sleeping screens back on. It is always resumed at start,
on exit, before a service key, and whenever it is found paused while awake.

After every sleep and wake it logs where the sound goes and warns ("WARNING
sound after ...") unless it is Fruitbox -> Jukebox Bass filter -> DAC.

It also does the service keys, all pressed twice within 5 s (a guest bumping a
key can't restart the jukebox or put it to sleep):
    F20 Reboot   F21 Rebuild Playlist (update-jukebox.sh, then reboot)
    F22 Shut Down   Pause Sleep

And the playlist keys (PARKED since 1.5: PLAYLIST_KEYS is empty, keys 1-3 do
nothing; see the note there). When on, pad keys 1 / 2 / 3 (Keypad 1 / 2 / 3) jump
Fruitbox straight to that playlist group (All Songs / Oldies / Christmas).
Fruitbox can only step to the NEXT group (Right Alt), so it presses Right Alt
and reads the group Fruitbox now shows (GROUP= in /dev/shm/jukebox_fruitbox.txt,
written by the status page's hidden skin box) until it is the one wanted. If it
can't read the group, or Fruitbox stops changing it, or the playlist isn't
there, it stops and logs why: never more than one trip round the groups.

Replaces jukebox-keys.py and screen-sleep.sh. The cabinet lights (jukebox-lights)
and the status page read /dev/shm/jukebox_mode; the old /dev/shm/jukebox_sleep
is no longer made (any left over is removed). It tells the keypad Teensy "S" /
"A" on sleep / wake, so the waking press isn't used as a digit.

Runs as root (systemd service jukebox-state) so it can reboot, power off and
hold the keyboards while asleep.
Log: /home/mtmace/fruitbox/jukebox-state.log  (and journalctl -u jukebox-state -f)
Test without the Pi:  python3 jukebox-state.py --selftest
"""
VERSION = "1.5"   # bump on every change; the status page shows it

import glob, os, re, subprocess, sys, threading, time
from select import select

# ---- settings ---------------------------------------------------------------
ACTIVE_SECONDS = 60                       # no song, no key this long: active -> idle
SLEEP_MINUTES = 10                        # this long in idle: -> sleep (0 = never)
CONFIRM_SECONDS = 5                       # second press of a service key within this
RECHECK_SECONDS = 2                       # while asleep: turn screens off again if they came on
SETTLE_SECONDS = 2                        # after Fruitbox's keys, before the screens go off
AUDIO_CHECK_DELAY = 4                     # after sleep / wake, before the sound routing is checked

# Sound must go Fruitbox -> Jukebox Bass filter -> DAC (never to the screens' HDMI).
BASS_SINK = "jukebox_bass"
BASS_OUT = "jukebox_bass.output"
DAC_SINK = "alsa_output.platform-soc_107c000000_sound.stereo-fallback"
FRUITBOX_STREAMS = ("SDL Application", "fruitbox")

USER = "mtmace"
FRUITBOX = "/home/mtmace/fruitbox"
UPDATE = FRUITBOX + "/update-jukebox.sh"
LOG = FRUITBOX + "/jukebox-state.log"
MODE_FILE = "/dev/shm/jukebox_mode"       # the state, one word (read by everything else)
OLD_SLEEP_FILE = "/dev/shm/jukebox_sleep" # made by the old jukebox-keys / screen-sleep.sh; removed if found
FRUITBOX_FILE = "/dev/shm/jukebox_state.txt"  # written by the skin: PLAYING/IDLE, ATTRACT_SONG, ATTRACT_ON
VIRTUAL_NAME = "jukebox-state keys"       # our own virtual keyboard, for keys we send Fruitbox

# service keys: key name -> (label, action); every one needs two presses
SERVICE_KEYS = {"KEY_F20": ("Reboot", "reboot"),
                "KEY_F21": ("Rebuild Playlist", "rebuild"),
                "KEY_F22": ("Shut Down", "shutdown"),
                "KEY_PAUSE": ("Sleep", "sleep")}

# Knob TURNS (ignored while asleep, they don't wake it). Knob presses are
# Left Ctrl (mute), F19 (bass flat) and F13 (lights on/off): those do wake it.
KNOB_TURNS = {"KEY_EQUAL", "KEY_MINUS",            # knob 1 volume
              "KEY_F17", "KEY_F18",                # knob 2 bass
              "KEY_F14", "KEY_F15",                # knob 3 lights dim
              "KEY_HOME", "KEY_END", "KEY_PAGEUP", "KEY_PAGEDOWN"}  # older fallbacks

# Keys sent to Fruitbox when the jukebox goes to sleep (fruitbox.ini [buttons])
FB_ATTRACT = "KEY_APOSTROPHE"             # AttractMode toggle
FB_CLEAR_QUEUE = "KEY_DELETE"             # ClearQueue
FB_SKIP = "KEY_BACKSPACE"                 # Skip: ends the song playing now
FB_GROUP = "KEY_RIGHTALT"                 # MusicGroup: next playlist group
FB_VOL_UP = "KEY_EQUAL"                   # VolUp
FB_VOL_DOWN = "KEY_MINUS"                 # VolDown
MAX_VOLUME = 100                          # fruitbox.ini MaxVolume
# After a sleep, the first song played came out far too loud although Fruitbox
# still showed the set volume (2026-11-16); one step up and back down
# (what he did by hand) makes Fruitbox apply its volume again, at whatever level
# it is set to. Done right at wake, before any song plays (so nothing is heard
# loud), and once more when the first song after the wake starts, in case
# Fruitbox only picks it up then.

# Requests from the status page's Control page (1.4). The page writes one word to
# REQUEST_FILE; this checks it about once a second, does it, and deletes the file.
# The page reads WEB_REQUESTS and WEB_CONFIRM from this installed file to make its
# buttons, so a request is only offered if this version can do it.
REQUEST_FILE = "/dev/shm/jukebox_request"
REQUEST_MAX_AGE = 30                      # older than this (seconds): stale, ignored
WEB_REQUESTS = {"wake": "Wake up",
                "sleep": "Sleep",
                "attract": "Attract mode on / off",
                "reboot": "Reboot",
                "rebuild": "Rebuild playlists (then reboots)",
                "shutdown": "Shut down"}
WEB_CONFIRM = ("sleep", "reboot", "rebuild", "shutdown")   # the page asks "are you sure?" first

# Playlist keys: key -> the start of the playlist group's name (case ignored,
# the song count Fruitbox shows after it, e.g. "Oldies - Rock & Roll (412)", too)
# PARKED 2026-11-17: Fruitbox takes ~23 s per group change (its own
# drawing, any skin), so stepping to a playlist isn't practical. Keys 1-3 do
# nothing until a better option exists. To bring them back:
#   {"KEY_KP1": "All Songs", "KEY_KP2": "Oldies", "KEY_KP3": "Christmas"}
PLAYLIST_KEYS = {}
GROUP_FILE = "/dev/shm/jukebox_fruitbox.txt"  # status page skin box: GROUP=<playlist shown now>
GROUP_WAIT = 3.0                          # Fruitbox writes that file once a second
MAX_GROUPS = 30                           # Fruitbox's own limit


def log(*a):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ---- outside world ------------------------------------------------------------
def x(*args):
    """Run an X command (xset) as mtmace on the jukebox's display."""
    try:
        return subprocess.run(["runuser", "-u", USER, "--", "env", "DISPLAY=:0",
                               "XAUTHORITY=/home/%s/.Xauthority" % USER] + list(args),
                              capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError) as e:
        log("xset:", e)
        return ""


def screens_off():
    x("xset", "s", "off")                  # no screen saver, no automatic blanking
    x("xset", "+dpms")
    x("xset", "dpms", "0", "0", "0")
    x("xset", "dpms", "force", "off")


def screens_on():
    x("xset", "dpms", "force", "on")


def screens_are_on():
    return "Monitor is On" in x("xset", "q")


# ---- freezing Fruitbox while asleep ---------------------------------------------
# On the Pi 5, Fruitbox drawing its screens (60 frames a second) switches sleeping
# HDMI outputs back on behind X's back (tested 2026-11-13: frozen = screens stayed
# off 60 s; un-frozen = back on within 1 s). So while asleep Fruitbox is paused
# (SIGSTOP, not closed: same song list, same position) and resumed on wake.
# Safety: it is resumed at start, on any exit, before every service key, and the
# tick resumes it if it is ever found paused outside sleep.
FRUITBOX_NAME = "fruitbox"                # process name (the self test swaps in a dummy)


def fruitbox_pids():
    pids = []
    for d in glob.glob("/proc/[0-9]*"):
        try:
            with open(d + "/comm") as f:
                if f.read().strip() == FRUITBOX_NAME:
                    pids.append(int(d[6:]))
        except (OSError, ValueError):
            pass
    return pids


def is_stopped(pid):
    try:
        with open("/proc/%d/stat" % pid) as f:
            return f.read().rsplit(")", 1)[1].split()[0] in ("T", "t")
    except (OSError, IndexError):
        return False


def signal_fruitbox(sig):
    done = []
    for pid in fruitbox_pids():
        try:
            os.kill(pid, sig)
            done.append(pid)
        except OSError as e:
            log("could not signal Fruitbox", pid, e)
    return done


def freeze_fruitbox():
    import signal as _s
    return signal_fruitbox(_s.SIGSTOP)


def unfreeze_fruitbox():
    import signal as _s
    return signal_fruitbox(_s.SIGCONT)


class RealIO:
    """Everything the state machine does to the outside world (the self test fakes it)."""
    real = True

    def __init__(self, fruitbox_keys=None):
        self.fbkeys = fruitbox_keys

    def sleep_keys(self, playing, attract):
        if self.fbkeys:
            if attract:
                self.fbkeys.press(FB_ATTRACT)
            self.fbkeys.press(FB_CLEAR_QUEUE)
            if playing or attract:
                self.fbkeys.press(FB_SKIP)
            log("music stopped, queue cleared%s" % (", attract off" if attract else ""))

    def settle(self):
        time.sleep(SETTLE_SECONDS)

    def volume_nudge(self, when):
        """One volume step and back, so Fruitbox applies its volume to the sound again."""
        if not self.fbkeys:
            return
        vol = read_volume()
        first, back = (FB_VOL_DOWN, FB_VOL_UP) if vol is not None and vol >= MAX_VOLUME \
            else (FB_VOL_UP, FB_VOL_DOWN)
        self.fbkeys.press(first)
        self.fbkeys.press(back)
        log("%s: volume re-applied (volume %s, now %s)"
            % (when, "?" if vol is None else vol, read_volume()))

    def freeze(self):
        pids = freeze_fruitbox()
        log("Fruitbox paused while asleep (pid %s)" % (", ".join(map(str, pids)) or "none found"))

    def unfreeze(self, why):
        pids = [p for p in fruitbox_pids() if is_stopped(p)]
        unfreeze_fruitbox()                 # always send it: harmless if it is running
        if pids:
            log("Fruitbox resumed (%s, pid %s)" % (why, ", ".join(map(str, pids))))

    def fruitbox_paused(self):
        """True / False, or None if Fruitbox isn't running."""
        pids = fruitbox_pids()
        return None if not pids else all(is_stopped(p) for p in pids)

    def screens_off(self):
        screens_off()

    def screens_on(self):
        screens_on()

    def screens_are_on(self):
        return screens_are_on()

    def mark_asleep(self, on):
        remove(OLD_SLEEP_FILE)      # no longer used; clear any left by the old scripts
        teensy("S" if on else "A")

    def write_mode(self, state):
        write_file(MODE_FILE, state + "\n")

    def audio_check(self, when):
        check_audio_later(when)


def as_user(*args):
    """Run a PipeWire tool (pw-link, wpctl) as mtmace, in mtmace's audio session."""
    try:
        return subprocess.run(["runuser", "-u", USER, "--", "env",
                               "XDG_RUNTIME_DIR=/run/user/%d" % user_uid()] + list(args),
                              capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError) as e:
        log("audio check:", e)
        return ""


def user_uid():
    try:
        import pwd
        return pwd.getpwnam(USER).pw_uid
    except (ImportError, KeyError):
        return 1000


def parse_links(text):
    """pw-link -l output -> {node: set of nodes it plays into}."""
    out, src = {}, None
    for line in text.splitlines():
        if not line.strip():
            continue
        if not line[0].isspace():
            src = line.strip().rsplit(":", 1)[0]
        elif src and "|->" in line:
            dst = line.split("|->", 1)[1].strip().rsplit(":", 1)[0]
            out.setdefault(src, set()).add(dst)
    return out


def audio_problems(links):
    """What's wrong with the sound routing, as a list of sentences (empty = all good)."""
    bad = []
    fb = [n for n in FRUITBOX_STREAMS if n in links]
    if not fb:
        bad.append("Fruitbox has no sound stream (not playing yet?)")
    for n in fb:
        if links[n] != {BASS_SINK}:
            bad.append("Fruitbox (%s) plays into %s, not %s" % (n, ", ".join(sorted(links[n])), BASS_SINK))
    if links.get(BASS_OUT) != {DAC_SINK}:
        bad.append("Jukebox Bass plays into %s, not the DAC"
                   % (", ".join(sorted(links.get(BASS_OUT, ()))) or "nothing"))
    return bad


def check_audio(when):
    """Log where the sound goes; warn if it isn't Fruitbox -> Jukebox Bass -> DAC."""
    time.sleep(AUDIO_CHECK_DELAY)                    # let the screens' HDMI come and go first
    default = ""
    for line in as_user("wpctl", "inspect", "@DEFAULT_AUDIO_SINK@").splitlines():
        if "node.name" in line:
            default = line.split("=", 1)[1].strip().strip('"')
            break
    bad = audio_problems(parse_links(as_user("pw-link", "-l")))
    if default != BASS_SINK:
        bad.insert(0, "default sound output is %s, not %s" % (default or "unknown", BASS_SINK))
    if bad:
        for b in bad:
            log("WARNING sound after %s: %s" % (when, b))
    else:
        log("sound after %s: ok (Fruitbox -> Jukebox Bass -> DAC)" % when)


def check_audio_later(when):
    threading.Thread(target=check_audio, args=(when,), daemon=True).start()


def teensy(msg):
    """S / A tells the keypad the jukebox is asleep / awake (so the waking press isn't a digit)."""
    ports = glob.glob("/dev/serial/by-id/*Teensy*") + glob.glob("/dev/ttyACM*")
    if ports:
        try:
            with open(ports[0], "w") as f:
                f.write(msg)
        except OSError as e:
            log("could not tell the keypad", msg, e)


def write_file(path, text):
    """Write a small file in one go (others never see half of it)."""
    tmp = "%s.%d.tmp" % (path, threading.get_ident())   # each thread its own temp file
    try:
        with open(tmp, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o666)
        os.replace(tmp, path)
    except OSError as e:
        log("could not write", path, e)


def remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def read_fruitbox():
    """(file found, user song playing, attract mode on) from the skin's state file."""
    try:
        with open(FRUITBOX_FILE, encoding="utf-8", errors="ignore") as f:
            lines = [l.strip().upper() for l in f.read().splitlines()]
    except OSError:
        return False, False, False
    playing = len(lines) > 0 and lines[0] == "PLAYING"
    attract_song = "ATTRACT_SONG" in lines
    attract_on = "ATTRACT_ON" in lines
    return True, playing and not attract_song, attract_on


# ---- playlist keys ----------------------------------------------------------------
def read_volume():
    """Fruitbox's volume now (VOLUME= in the status box file), or None."""
    try:
        with open(GROUP_FILE, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("VOLUME="):
                    return int(line[7:].strip())
    except (OSError, ValueError):
        pass
    return None


def read_group():
    """The playlist group Fruitbox shows now, or None if the status box file isn't there."""
    try:
        with open(GROUP_FILE, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("GROUP="):
                    return line[6:].strip()
    except OSError:
        pass
    return None


def group_matches(group, want):
    name = re.sub(r"\s*\(\d+\)\s*$", "", group or "").strip().lower()
    return bool(name) and name.startswith(want.strip().lower())


def jump_to_group(want, press, read=read_group, wait=GROUP_WAIT,
                  clock=time.monotonic, nap=time.sleep):
    """Press Next Group until Fruitbox shows a group starting with want.
    want() gives the wanted name each step (a newer key press changes it).
    Returns a sentence for the log."""
    target = want()
    group = read()
    if group is None:
        return "can't see the playlist Fruitbox shows (%s missing: status page not installed?)" % GROUP_FILE
    seen = {group}
    for _ in range(MAX_GROUPS + 1):
        if want() != target:                     # another playlist key pressed meanwhile
            target, seen = want(), {group}
        if group_matches(group, target):
            return "playlist %r: Fruitbox shows %r" % (target, group)
        press(FB_GROUP)
        end = clock() + wait
        new = read()
        while new == group and clock() < end:
            nap(0.1)
            new = read()
        if new == group or new is None:
            return "stopped: Fruitbox didn't change playlist from %r after Next Group" % group
        group = new
        if group in seen and not group_matches(group, want()):
            return "no playlist starting %r in Fruitbox's groups; left on %r" % (target, group)
        seen.add(group)
    return "gave up looking for %r after %d groups" % (target, MAX_GROUPS)


class PlaylistKeys:
    """Runs one jump at a time in the background; a new key press re-aims it."""
    def __init__(self, fbkeys):
        self.fbkeys = fbkeys
        self.want = None
        self.lock = threading.Lock()
        self.running = False

    def pressed(self, key_name):
        with self.lock:
            self.want = PLAYLIST_KEYS[key_name]
            if self.running:
                log("playlist key", key_name, "-> now going to", repr(self.want))
                return
            self.running = True
        log("playlist key", key_name, "->", repr(self.want))
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            if not self.fbkeys or not self.fbkeys.ui:
                log("playlist key: no virtual keyboard, can't change playlist")
                return
            log(jump_to_group(lambda: self.want, self.fbkeys.press))
        except Exception as e:                   # never take the state manager down
            log("playlist key failed:", e)
        finally:
            with self.lock:
                self.running = False


class FruitboxKeys:
    """A virtual keyboard, to press Fruitbox's own keys (clear queue, skip, attract, next group)."""
    def __init__(self):
        self.ui = None
        try:
            import evdev
            from evdev import ecodes
            self.ecodes = ecodes
            keys = [ecodes.ecodes[k] for k in (FB_ATTRACT, FB_CLEAR_QUEUE, FB_SKIP, FB_GROUP,
                                                FB_VOL_UP, FB_VOL_DOWN)]
            self.ui = evdev.UInput({ecodes.EV_KEY: keys}, name=VIRTUAL_NAME)
        except Exception as e:                      # no uinput: sleep still works, music keeps going
            log("no virtual keyboard, can't stop the music on sleep:", e)

    def press(self, name):
        if not self.ui:
            return
        code = self.ecodes.ecodes[name]
        self.ui.write(self.ecodes.EV_KEY, code, 1)
        self.ui.syn()
        time.sleep(0.05)
        self.ui.write(self.ecodes.EV_KEY, code, 0)
        self.ui.syn()
        time.sleep(0.3)                             # give Fruitbox time to act on it


# ---- the state machine ----------------------------------------------------------
class Manager:
    def __init__(self, io=None, clock=time.monotonic):
        self.clock = clock
        self.io = io or RealIO()
        self.hw = getattr(self.io, "real", False)
        self.state = None
        self.last_touch = -1e9           # last key, knob or coin
        self.idle_since = None
        self.last_recheck = 0.0
        self.relit = 0
        self.screens_done = False        # asleep and sleep() has turned the screens off
        # Pause's sleep runs in its own thread while the main loop ticks: one at a
        # time, or a tick that read "PLAYING" just before can undo the sleep.
        self.lock = threading.RLock()
        self.last_pause_check = -1e9
        self.renudge = False             # first song after a wake: re-apply the volume
        self.io.mark_asleep(False)                 # left over from before a restart
        self.io.unfreeze("service started")        # never leave Fruitbox paused from before
        self.set("starting", "service started")

    @property
    def asleep(self):
        return self.state == "sleep"

    def set(self, new, why):
        if new == self.state:
            return
        old, self.state = self.state, new
        log("state: %s -> %s (%s)" % (old or "-", new, why))
        if new == "idle":
            self.idle_since = self.clock()
        self.io.write_mode(new)

    # -- inputs --
    def touch(self, key_name):
        """A key, knob or coin on the keypad or macro pad (not a service-key action)."""
        with self.lock:
            return self._touch(key_name)

    def _touch(self, key_name):
        if self.asleep:
            if key_name in KNOB_TURNS:
                return "ignored"           # knob turns don't wake it
            self.wake(key_name)
            return "woke"
        self.last_touch = self.clock()
        if self.state == "idle":
            self.set("active", "key " + key_name)
        return "used"

    def tick(self):
        """About once a second: follow Fruitbox and the timers."""
        with self.lock:
            self._tick()

    def _tick(self):
        self.check_paused()
        if self.state in ("sleep", "shutdown"):
            if self.state == "sleep":
                self.keep_screens_off()
            return
        found, playing, attract = read_fruitbox()
        if self.state == "starting" and not found:
            return                          # Fruitbox not up yet
        now = self.clock()
        if playing:
            self.last_touch = now           # a song counts as use: idle starts 60 s after it ends
            if self.renudge:
                self.renudge = False
                self.io.volume_nudge("first song after wake")
        if attract:
            self.set("attract", "attract mode on")
        elif playing or now - self.last_touch < ACTIVE_SECONDS:
            self.set("active", "song playing" if playing else "key in the last %d s" % ACTIVE_SECONDS)
        else:
            self.set("idle", "no song, no key for %d s" % ACTIVE_SECONDS
                     if self.state != "starting" else "Fruitbox is up")
            if SLEEP_MINUTES and now - self.idle_since >= SLEEP_MINUTES * 60:
                self.sleep("%d min idle" % SLEEP_MINUTES)

    # -- sleep and wake --
    def sleep(self, why):
        with self.lock:                     # decide and switch in one go (see self.lock)
            if self.state in ("sleep", "shutdown"):
                return
            found, playing, attract = read_fruitbox()
            self.screens_done = False       # the recheck waits until the screens are off below
            self.set("sleep", why)
        self.io.mark_asleep(True)
        # Sleep means no music: attract off, queue cleared, the song playing now ended.
        self.io.sleep_keys(playing, attract)
        self.io.settle()                    # let the keys we sent (and Pause's release) go by first
        with self.lock:
            if not self.asleep:             # woken during the wait: leave Fruitbox and screens alone
                return
            self.io.freeze()                # Fruitbox's drawing would switch the screens back on
            self.io.screens_off()
            self.last_recheck, self.relit = self.clock(), 0
            self.screens_done = True
        self.io.audio_check("sleep")

    def wake(self, why):
        if not self.asleep:
            return
        self.last_touch = self.clock()
        self.screens_done = False
        self.set("active", "woken by " + why)
        self.renudge = True
        self.io.unfreeze("woken")           # Fruitbox first, then the screens
        self.io.mark_asleep(False)
        self.io.screens_on()
        self.io.volume_nudge("wake")       # before any song plays: nothing heard loud
        if self.relit:
            log("screens had come back on by themselves %d times while asleep" % self.relit)
        self.io.audio_check("wake")

    def check_paused(self):
        """Fruitbox is paused exactly when asleep (after sleep() finished), never otherwise."""
        if self.clock() - self.last_pause_check < RECHECK_SECONDS:
            return
        self.last_pause_check = self.clock()
        paused = self.io.fruitbox_paused()
        if paused is None:
            return                          # Fruitbox not running
        if self.asleep and self.screens_done and not paused:
            log("WARNING Fruitbox running while asleep (restarted?) - pausing it again")
            self.io.freeze()
        elif not self.asleep and paused:
            log("WARNING Fruitbox was paused while %s - resuming it" % self.state)
            self.io.unfreeze("found paused while " + str(self.state))

    def keep_screens_off(self):
        # Not before sleep() has turned them off itself: turning them off early, before
        # Fruitbox's keys are sent, lets those keys switch them straight back on.
        if not self.screens_done or self.clock() - self.last_recheck < RECHECK_SECONDS:
            return
        self.last_recheck = self.clock()
        if self.io.screens_are_on():
            self.relit += 1
            if self.relit <= 3 or self.relit % 100 == 0:
                log("screens came back on without a key press (%d); off again" % self.relit)
            self.io.screens_off()


busy = threading.Event()


def take_request(path=None, now=None, owners=None):
    """The word in the status page's request file, or None. Deletes the file. Ignores
    it if stale, unknown, or written by anyone but root or the jukebox user."""
    path = path or REQUEST_FILE
    try:
        st = os.stat(path)
        with open(path) as f:
            word = f.read(40).strip().lower()
        os.remove(path)
    except OSError:
        return None
    if owners is None:
        owners = {0}
        try:
            import pwd
            owners.add(pwd.getpwnam(USER).pw_uid)
        except (ImportError, KeyError):
            pass
    if st.st_uid not in owners:
        log("request %r ignored: file not written by root or %s" % (word, USER))
        return None
    if (now if now is not None else time.time()) - st.st_mtime > REQUEST_MAX_AGE:
        log("request %r ignored: stale" % word)
        return None
    if word not in WEB_REQUESTS:
        log("request %r ignored: unknown" % word)
        return None
    return word


def do_request(mgr, word, fbkeys=None):
    """Carry out a status-page request (same as the keys would)."""
    log("status page asks:", word)
    if word == "wake":
        with mgr.lock:
            if mgr.asleep:
                mgr.wake("status page")
            else:
                log("wake: already awake (%s)" % mgr.state)
    elif word == "sleep":
        threading.Thread(target=mgr.sleep, args=("status page",), daemon=True).start()
    elif word == "attract":
        if mgr.asleep:
            log("attract ignored: asleep, wake it first")
        elif not fbkeys or not fbkeys.ui:
            log("attract: no virtual keyboard, can't press Fruitbox's attract key")
        else:
            mgr.touch("status page")
            fbkeys.press(FB_ATTRACT)
    elif word in ("reboot", "rebuild", "shutdown"):
        if busy.is_set():
            log(word, "ignored: already busy")
        else:
            threading.Thread(target=run_service, args=(mgr, word), daemon=True).start()


def run_service(mgr, action):
    busy.set()
    try:
        mgr.io.unfreeze("service key " + action)   # never reboot / shut down with Fruitbox paused
        mgr.set("shutdown", action)
        subprocess.run(["sync"])
        if action == "rebuild":
            log("rebuilding the playlists:", UPDATE)
            r = subprocess.run(["runuser", "-u", USER, "--", "bash", UPDATE],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in (r.stdout or "").splitlines()[-20:]:
                log("  ", line)
            log("update-jukebox.sh finished with code", r.returncode, "- rebooting")
            subprocess.run(["sync"])
            subprocess.run(["systemctl", "reboot"])
        elif action == "reboot":
            log("rebooting")
            subprocess.run(["systemctl", "reboot"])
        elif action == "shutdown":
            log("shutting down")
            subprocess.run(["systemctl", "poweroff"])
    finally:
        busy.clear()


# ---- main loop ------------------------------------------------------------------
def main():
    import evdev   # sudo apt install python3-evdev
    from evdev import ecodes

    install_exit_guard()
    try:
        run(evdev, ecodes)
    finally:
        unfreeze_fruitbox()


def install_exit_guard():
    """Whatever happens to this program (stopped, restarted, crashed), Fruitbox
    must not stay paused."""
    import atexit, signal
    atexit.register(unfreeze_fruitbox)
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))   # systemctl stop -> atexit runs


def run(evdev, ecodes):
    service = {}
    for name, what in SERVICE_KEYS.items():
        service[ecodes.ecodes[name]] = what
    fbkeys = FruitboxKeys()
    mgr = Manager(RealIO(fbkeys))
    playlists = PlaylistKeys(fbkeys)
    remove(REQUEST_FILE)           # never act on a request left from before a restart
    log("version", VERSION, "watching for", ", ".join(f"{n} = {w[0]}" for n, w in SERVICE_KEYS.items()),
        "and playlist keys", ", ".join(f"{n} = {w}" for n, w in PLAYLIST_KEYS.items()))

    first = {}                     # code -> time of the first press
    devices, last_scan = {}, 0
    grabbed = set()                # keyboards held while asleep, so the waking press goes nowhere

    def is_keyboard(d):
        # any real key (not just mouse or touch buttons): the keypad, the macro pad
        return d.name != VIRTUAL_NAME and \
            any(0 < k < 0x100 for k in d.capabilities().get(ecodes.EV_KEY, []))

    def grab_all(on):
        for d in list(devices.values()):
            try:
                if on and d.path not in grabbed:
                    d.grab()
                    grabbed.add(d.path)
                elif not on and d.path in grabbed:
                    d.ungrab()
                    grabbed.discard(d.path)
            except OSError:
                grabbed.discard(d.path)

    last_tick = 0.0
    while True:
        if time.monotonic() - last_scan > 5:          # keyboards plugged in later
            last_scan = time.monotonic()
            for path in evdev.list_devices():
                if path not in devices:
                    try:
                        d = evdev.InputDevice(path)
                        if is_keyboard(d):
                            devices[path] = d
                            log("watching", d.name)
                    except OSError:
                        pass
        if time.monotonic() - last_tick >= 1:
            last_tick = time.monotonic()
            mgr.tick()
            word = take_request()
            if word:
                do_request(mgr, word, fbkeys)
        grab_all(mgr.asleep)
        if not devices:
            time.sleep(1)
            continue
        ready, _, _ = select(list(devices.values()), [], [], 1)
        for d in ready:
            try:
                events = list(d.read())
            except OSError:                            # unplugged
                devices.pop(d.path, None)
                grabbed.discard(d.path)
                continue
            for e in events:
                if e.type != ecodes.EV_KEY or e.value != 1 or not 0 < e.code < 0x100:
                    continue
                name = ecodes.KEY.get(e.code, str(e.code))
                if isinstance(name, list):
                    name = name[0]
                if mgr.asleep:
                    # the keyboards are held, so Fruitbox, the lights and the bass
                    # knob never see this press
                    mgr.touch(name)
                    grab_all(mgr.asleep)
                    continue
                mgr.touch(name)
                if name in PLAYLIST_KEYS:
                    playlists.pressed(name)
                    continue
                if e.code not in service:
                    continue
                label, action = service[e.code]
                now = time.monotonic()
                if busy.is_set():
                    log(label, "ignored: already busy")
                elif now - first.get(e.code, -99) <= CONFIRM_SECONDS:
                    first.pop(e.code, None)
                    log(label, "confirmed")
                    if action == "sleep":
                        threading.Thread(target=mgr.sleep, args=("Pause key",), daemon=True).start()
                    else:
                        threading.Thread(target=run_service, args=(mgr, action), daemon=True).start()
                else:
                    first = {e.code: now}             # a different key cancels the first one
                    log(label, "pressed once - press again within", CONFIRM_SECONDS, "s")


# ---- self test (no Pi needed) -----------------------------------------------------
def shutil_which(name):
    import shutil
    return shutil.which(name)


def selftest():
    global FRUITBOX_FILE, LOG, FRUITBOX_NAME
    import tempfile
    tmp = tempfile.mkdtemp()
    FRUITBOX_FILE, LOG = os.path.join(tmp, "fb.txt"), os.path.join(tmp, "log.txt")
    t = [1000.0]
    clock = lambda: t[0]

    def fb(playing=False, attract_song=False, attract=False):
        with open(FRUITBOX_FILE, "w") as f:
            f.write(("PLAYING" if playing else "IDLE") + "\n"
                    + ("ATTRACT_SONG" if attract_song else "USER_SONG") + "\n"
                    + ("ATTRACT_ON" if attract else "ATTRACT_OFF") + "\n")

    def step(sec, m):
        for _ in range(int(sec)):
            t[0] += 1
            m.tick()

    class FakeIO:
        """Records what the state machine does, in order; Fruitbox 'paused' is simulated."""
        real = False

        def __init__(self):
            self.ev, self.paused = [], False

        def sleep_keys(self, playing, attract):
            self.ev.append("keys" + (" +attract off" if attract else "") + (" +skip" if playing or attract else ""))

        def settle(self):
            self.ev.append("wait %ds" % SETTLE_SECONDS)

        def volume_nudge(self, when):
            self.ev.append("volume nudge")

        def freeze(self):
            self.ev.append("freeze"); self.paused = True

        def unfreeze(self, why):
            self.ev.append("unfreeze"); self.paused = False

        def fruitbox_paused(self):
            return self.paused

        def screens_off(self):
            self.ev.append("screens off")

        def screens_on(self):
            self.ev.append("screens on")

        def screens_are_on(self):
            return False

        def mark_asleep(self, on):
            pass

        def write_mode(self, state):
            pass

        def audio_check(self, when):
            self.ev.append("sound check " + when)

    io = FakeIO()
    m = Manager(io, clock=clock)
    checks = []
    def check(what, want):
        checks.append((what, m.state == want, m.state, want))
    def check_ev(what, want):
        got = ", ".join(io.ev)
        checks.append((what, got == want, got, want))
        del io.ev[:]

    check_ev("startup resumes Fruitbox", "unfreeze")

    step(5, m); check("no Fruitbox file yet", "starting")
    fb(); step(1, m); check("Fruitbox up", "idle")
    m.touch("KEY_1"); check("key in idle", "active")
    step(30, m); check("30 s after key", "active")
    step(31, m); check("61 s after key", "idle")
    fb(playing=True); step(1, m); check("song playing", "active")
    step(600, m); check("still playing after 10 min", "active")
    fb(); step(59, m); check("59 s after song ended", "active")
    step(2, m); check("61 s after song ended", "idle")
    step(9 * 60, m); check("9 min idle", "idle")
    del io.ev[:]
    step(61, m); check("10 min idle", "sleep")
    check_ev("sleep order", "keys, wait %ds, freeze, screens off, sound check sleep" % SETTLE_SECONDS)
    step(10, m); check_ev("asleep 10 s: nothing more", "")
    r = m.touch("KEY_EQUAL"); check("knob turn while asleep (%s)" % r, "sleep")
    check_ev("knob turn: Fruitbox stays paused", "")
    r = m.touch("KEY_LEFTCTRL"); check("knob press while asleep (%s)" % r, "active")
    check_ev("wake order", "unfreeze, screens on, volume nudge, sound check wake")
    fb(attract=True, playing=True, attract_song=True); step(1, m); check("attract on", "attract")
    step(3600, m); check("attract after an hour", "attract")
    del io.ev[:]
    m.sleep("Pause key"); check("Pause key in attract", "sleep")
    check_ev("Pause in attract: attract off, skip",
             "keys +attract off +skip, wait %ds, freeze, screens off, sound check sleep" % SETTLE_SECONDS)
    io.paused = False; step(3, m)
    check_ev("asleep, Fruitbox restarted: paused again", "freeze")
    r = m.touch("KEY_5"); check("keypad digit while asleep (%s)" % r, "active")
    check_ev("keypad wake order", "unfreeze, screens on, volume nudge, sound check wake")
    fb(playing=True); step(2, m); check_ev("first song after wake: volume re-applied once", "volume nudge")
    step(2, m); fb(); step(2, m); fb(playing=True); step(2, m)
    check_ev("second song: no more nudges", "")
    fb(); io.paused = True; step(3, m); check("active, Fruitbox found paused", "active")
    check_ev("active + paused Fruitbox: resumed", "unfreeze")
    m.set("shutdown", "reboot"); step(5, m); check("shutting down stays", "shutdown")

    # the real pause / resume, on a dummy process (never the real Fruitbox)
    real_name = FRUITBOX_NAME
    if os.path.isdir("/proc/self") and shutil_which("sleep"):
        import shutil, signal
        dummy = os.path.join(tmp, "jbtestdummy")
        shutil.copy(shutil_which("sleep"), dummy)
        p = subprocess.Popen([dummy, "60"])
        FRUITBOX_NAME = "jbtestdummy"
        try:
            time.sleep(0.3)
            freeze_fruitbox(); time.sleep(0.2)
            checks.append(("real pause", is_stopped(p.pid), is_stopped(p.pid), True))
            unfreeze_fruitbox(); time.sleep(0.2)
            checks.append(("real resume", not is_stopped(p.pid), is_stopped(p.pid), False))
            # a manager program that pauses it and is then stopped (SIGTERM) must resume it
            child = subprocess.Popen([sys.executable, "-c",
                "import importlib.util as u, os, signal, time\n"
                "s=u.spec_from_file_location('js', %r); m=u.module_from_spec(s); s.loader.exec_module(m)\n"
                "m.FRUITBOX_NAME='jbtestdummy'; m.LOG=%r; m.install_exit_guard(); m.freeze_fruitbox()\n"
                "time.sleep(30)\n" % (os.path.abspath(__file__), LOG)])
            time.sleep(1.0)
            paused_before = is_stopped(p.pid)
            child.send_signal(signal.SIGTERM); child.wait(5); time.sleep(0.2)
            checks.append(("stopped manager resumes Fruitbox", paused_before and not is_stopped(p.pid),
                           "paused=%s then %s" % (paused_before, is_stopped(p.pid)), "paused=True then False"))
        finally:
            FRUITBOX_NAME = real_name
            p.kill()
            p.wait()

    # playlist keys: a fake Fruitbox that steps through its groups on Next Group
    def fake_fb(groups, start=0, stuck=False):
        st = {"i": start, "presses": 0, "t": 0.0}
        def press(k):
            st["presses"] += 1
            if not stuck:
                st["i"] = (st["i"] + 1) % len(groups)
        def nap(s):
            st["t"] += s
        return st, press, (lambda: groups[st["i"]]), (lambda: st["t"]), nap
    groups = ["All Songs (1830)", "Country (412)", "Oldies - Rock & Roll (412)",
              "Everything Else (900)", "Christian (60)", "Christmas (117)"]
    for what, want, start, presses, word in (
            ("playlist: All -> Christmas", "Christmas", 0, 5, "Fruitbox shows 'Christmas"),
            ("playlist: Christmas -> All", "All Songs", 5, 1, "Fruitbox shows 'All Songs"),
            ("playlist: Oldies wraps round", "Oldies", 4, 4, "Fruitbox shows 'Oldies"),
            ("playlist: already there", "Oldies", 2, 0, "Fruitbox shows 'Oldies"),
            ("playlist: missing one stops", "Jazz", 1, 6, "no playlist")):
        st, press, read, clk, nap = fake_fb(groups, start)
        msg = jump_to_group(lambda: want, press, read, 3.0, clk, nap)
        good = st["presses"] == presses and word in msg
        checks.append((what, good, "%d presses: %s" % (st["presses"], msg), "%d presses, %s" % (presses, word)))
    st, press, read, clk, nap = fake_fb(groups, 0, stuck=True)
    msg = jump_to_group(lambda: "Christmas", press, read, 3.0, clk, nap)
    checks.append(("playlist: Fruitbox not changing stops", st["presses"] == 1 and "didn't change" in msg,
                   "%d presses: %s" % (st["presses"], msg), "1 press, didn't change"))
    msg = jump_to_group(lambda: "Christmas", press, lambda: None, 3.0, clk, nap)
    checks.append(("playlist: no status file does nothing", "can't see" in msg, msg, "can't see"))

    # status page requests
    rq = os.path.join(tmp, "request")
    me = {os.getuid()}
    for what, text, age, owners, want in (("request: sleep taken", "sleep\n", 0, me, "sleep"),
                                          ("request: unknown ignored", "format\n", 0, me, None),
                                          ("request: stale ignored", "wake", 60, me, None),
                                          ("request: other user ignored", "wake", 0, {12345}, None)):
        with open(rq, "w") as f:
            f.write(text)
        got = take_request(rq, time.time() + age, owners)
        checks.append((what, got == want and not os.path.exists(rq), repr(got), repr(want)))
    checks.append(("request: no file", take_request(rq, None, me) is None, "None", "None"))

    # sound routing check
    good_links = ("SDL Application:output_FL\n  |-> jukebox_bass:playback_FL\n"
                  "jukebox_bass.output:output_FL\n  |-> %s:playback_FL\n" % DAC_SINK)
    bad_links = ("SDL Application:output_FL\n  |-> alsa_output.platform-107c706400.hdmi.hdmi-stereo:playback_FL\n"
                 "jukebox_bass.output:output_FL\n  |-> alsa_output.platform-107c701400.hdmi.hdmi-stereo:playback_FL\n"
                 "jukebox_bass:monitor_FL\n  |-> parec:input_FL\n")
    for what, text, want in (("sound routing ok", good_links, 0), ("sound to HDMI caught", bad_links, 2)):
        n = len(audio_problems(parse_links(text)))
        checks.append((what, n == want, "%d problems" % n, "%d problems" % want))

    ok = True
    for what, good, got, want in checks:
        print("%-4s %-38s %s" % ("ok" if good else "FAIL", what, got if good else "%s (wanted %s)" % (got, want)))
        ok &= good
    print("ALL PASSED" if ok else "SOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    main()

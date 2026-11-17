#!/usr/bin/env python3
"""Jukebox bass knob.

Listens to the macro pad's bass knob and turns the bass up or down on the
"Jukebox Bass" sound output (see jukebox-bass.conf). The level is saved, so
it comes back after a reboot.

  knob right  -> F17 (or Home)  bass up   2 dB
  knob left   -> F18 (or End)   bass down 2 dB
  knob press  -> F19            bass back to the default (+10 dB)

None of these keys are used by Fruitbox, the cabinet lights or the screen
sleep key. Fruitbox simply ignores them.

Runs as the desktop user (systemd --user service jukebox-bass.service), so
it can talk to PipeWire. Needs: python3-evdev, pipewire-bin (pw-cli, pw-dump)
and the user in the "input" group (the Pi's default user is).

Test from SSH:  python3 /home/mtmace/fruitbox/jukebox-bass.py --set 6
"""
VERSION = "1.1"   # bump on every change; the status page shows it

import json, os, subprocess, sys, time

UP_KEYS    = ["KEY_F17", "KEY_HOME"]
DOWN_KEYS  = ["KEY_F18", "KEY_END"]
FLAT_KEYS  = ["KEY_F19"]
STEP_DB    = 2.0
DEFAULT_DB = 10.0        # every start-up, and the knob press, go back to this
MIN_DB, MAX_DB = -12.0, 12.0
NODE_NAME  = "jukebox_bass"
SAVE_FILE  = os.path.expanduser("~/.config/jukebox-bass/level")
SHOW_FILE  = "/dev/shm/jukebox_bass.txt"     # for a skin or the lights, if wanted


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def load_level():
    try:
        with open(SAVE_FILE) as f:
            return max(MIN_DB, min(MAX_DB, float(f.read().strip())))
    except (OSError, ValueError):
        return 0.0


def save_level(db):
    try:
        os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)
        with open(SAVE_FILE, "w") as f:
            f.write("%g\n" % db)
        with open(SHOW_FILE, "w") as f:
            f.write("%+g dB\n" % db)
    except OSError as e:
        log("could not save:", e)


def find_node():
    """PipeWire's id number for the Jukebox Bass filter, or None."""
    try:
        out = subprocess.run(["pw-dump"], capture_output=True, text=True, timeout=5).stdout
        for obj in json.loads(out or "[]"):
            props = (obj.get("info") or {}).get("props") or {}
            if obj.get("type", "").endswith(":Node") and props.get("node.name") == NODE_NAME:
                return obj["id"]
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        log("pw-dump:", e)
    return None


def apply(db):
    """Send the bass level to PipeWire. True if it worked."""
    node = find_node()
    if node is None:
        log("Jukebox Bass output not found (is jukebox-bass.conf installed?)")
        return False
    r = subprocess.run(["pw-cli", "set-param", str(node), "Props",
                        '{ params = [ "bass:Gain" %.1f ] }' % db],
                       capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        log("pw-cli failed:", r.stderr.strip())
        return False
    return True


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--set":
        db = max(MIN_DB, min(MAX_DB, float(sys.argv[2])))
        if apply(db):
            save_level(db)
            log("bass set to %+g dB" % db)
        return

    import evdev   # sudo apt install python3-evdev
    from select import select
    E = evdev.ecodes

    db = DEFAULT_DB                      # always start at the default (2026-11-17)
    # PipeWire may still be starting at boot: keep trying for a minute
    for _ in range(30):
        if apply(db):
            break
        time.sleep(2)
    save_level(db)
    log("bass at %+g dB" % db)

    actions = {}
    for names, what in ((UP_KEYS, "up"), (DOWN_KEYS, "down"), (FLAT_KEYS, "flat")):
        for n in names:
            actions[E.ecodes[n]] = what

    devices, last_scan = {}, 0.0
    while True:
        if time.monotonic() - last_scan > 5:            # pads plugged in later
            last_scan = time.monotonic()
            for path in evdev.list_devices():
                if path in devices:
                    continue
                try:
                    d = evdev.InputDevice(path)
                    keys = d.capabilities().get(E.EV_KEY, [])
                    if any(k in actions for k in keys):
                        devices[path] = d
                        log("watching", d.name)
                except OSError:
                    pass
        if not devices:
            time.sleep(1)
            continue
        ready, _, _ = select(list(devices.values()), [], [], 1)
        for d in ready:
            try:
                events = list(d.read())
            except OSError:                              # unplugged
                devices.pop(d.path, None)
                continue
            for ev in events:
                if ev.type != E.EV_KEY or ev.value not in (1, 2) or ev.code not in actions:
                    continue
                what = actions[ev.code]
                new = DEFAULT_DB if what == "flat" else db + (STEP_DB if what == "up" else -STEP_DB)
                new = max(MIN_DB, min(MAX_DB, new))
                if new != db and apply(new):
                    db = new
                    save_level(db)
                    log("bass %+g dB" % db)


if __name__ == "__main__":
    main()

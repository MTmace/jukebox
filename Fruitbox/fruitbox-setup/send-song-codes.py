#!/usr/bin/env python3
"""Tell the keypad Teensy which selection codes the skin really has.

Reads the skin's fruitbox.cfg (SelectButtons lines, SelectButtonsSequence,
number of [title strip] sections and SongsPerTitleStrip), works out every code
Fruitbox gives a song slot, and sends them to the Teensy as one line, e.g.

    C100-108,110-118,...,270-278

The Teensy saves the list, so it survives a power cut, and uses it for the
lamps and for which digits it types. launch-fruitbox.sh runs this before it
starts Fruitbox:

    python3 /home/mtmace/fruitbox/send-song-codes.py "/opt/fruitbox/skins/Firestar Ultrawide/fruitbox.cfg"

With --dry-run it only prints the line.
"""
import glob
import itertools
import os
import sys
import time

LOG = os.path.expanduser("~/fruitbox/launcher.log")
DEFAULT_SKIN = "/opt/fruitbox/skins/Firestar Ultrawide/fruitbox.cfg"


def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " send-song-codes: " + msg + "\n")
    except OSError:
        pass


def read_skin(path):
    buttons, sequence, strips, per_strip = [], "rowcol", 0, 1
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.lower() == "[title strip]":
                strips += 1
                continue
            if "=" not in line:
                continue
            key, value = (s.strip() for s in line.split("=", 1))
            key = key.lower()
            if key == "selectbuttons":
                buttons.append(value)
            elif key == "selectbuttonssequence":
                sequence = value.lower()
            elif key == "songspertitlestrip":
                per_strip = int(value)
    return buttons, sequence, strips, per_strip


def song_codes(buttons, sequence, slots):
    """The first `slots` codes in the order Fruitbox hands them out, strip by
    strip. rowcol (Fruitbox's default): the last SelectButtons line changes
    fastest (100, 101, ...). colrow: the whole order is turned round, so the
    first line changes fastest and the last slowest (100, 200, 110, 210, ...,
    170, 270, 101, 201, ...). On the Firestar skin that makes each strip an A/B
    pair, the tens digit the row and the ones digit the column (checked: 178
    and 278 on the Pi, 2026-11-09)."""
    if sequence == "colrow":
        order = (tuple(reversed(d)) for d in itertools.product(*reversed(buttons)))
    else:
        order = itertools.product(*buttons)
    codes = [int("".join(digits)) for digits in itertools.islice(order, slots)]
    return sorted(codes)


def as_ranges(codes):
    ranges = []
    for c in codes:
        if ranges and c == ranges[-1][1] + 1:
            ranges[-1][1] = c
        else:
            ranges.append([c, c])
    return ",".join(f"{a}-{b}" for a, b in ranges)


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    skin = args[0] if args else DEFAULT_SKIN
    try:
        buttons, sequence, strips, per_strip = read_skin(skin)
    except OSError as e:
        log(f"can't read {skin}: {e}")
        return 1
    if not buttons or not strips:
        log(f"{skin} has no SelectButtons or title strips; nothing sent")
        return 1
    line = "C" + as_ranges(song_codes(buttons, sequence, strips * per_strip))
    if dry:
        print(line)
        return 0
    ports = sorted(glob.glob("/dev/serial/by-id/*Teensy*")) + sorted(glob.glob("/dev/ttyACM*"))
    if not ports:
        log("keypad Teensy not found; it keeps the codes it had")
        return 1
    try:
        with open(ports[0], "w") as port:
            port.write(line + "\n")
    except OSError as e:
        log(f"could not write to {ports[0]}: {e}")
        return 1
    log(f"sent {line} to {ports[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

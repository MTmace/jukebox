#!/usr/bin/env python3
"""Builds the keycap STLs and previews from keycap.scad.

    python3 make_keycaps.py                 the caps listed in CAPS
    python3 make_keycaps.py dice-5-fill     just that icon

Needs OpenSCAD (and xvfb-run for the previews on a machine with no screen).
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_MAX = 10.0      # max icon height on the cap, mm (top is 14.5)
ICON_MAX_W = 12.0    # max icon width (lets wide icons like play-pause use the room)
CAPS = ["play-pause", "infinity", "music-note-list",            # Pause/Play, Attract, Change Playlist
        "skip-end-fill", "dice-5-fill", "list-ul", "trash3-fill",   # Next, Random, Fill Queue, Clear Queue
        "palette-fill", "1-circle", "2-circle", "3-circle",         # Change Lighting, Favourite light 1-3
        "moon-fill", "bootstrap-reboot", "database-gear",     # Sleep, Reboot, Rebuild Playlist
        "power"]                                                    # Shut Down


def scad(out, **defs):
    args = ["openscad", "-q", "-o", out]
    for k, v in defs.items():
        args += ["-D", f"{k}={v}"]
    args.append(os.path.join(HERE, "keycap.scad"))
    if out.endswith(".png"):
        args = ["xvfb-run", "-a"] + args[:4] + ["--imgsize=600,600", "--camera=0,0,0,35,0,25,75", "--colorscheme=Tomorrow"] + args[4:]
    subprocess.run(args, check=True, cwd=HERE)


def icon_size(name):
    """Measure the icon outline (via a DXF export) and fit it in ICON_MAX."""
    with tempfile.TemporaryDirectory() as tmp:
        probe = os.path.join(tmp, "p.scad")
        open(probe, "w").write(f'import("{HERE}/icons/{name}.svg");')
        dxf = os.path.join(tmp, "p.dxf")
        subprocess.run(["openscad", "-q", "-o", dxf, probe], check=True)
        lines = open(dxf).read().split("\n")
    xs = [float(lines[i + 1]) for i, l in enumerate(lines) if l.strip() == "10"]
    ys = [float(lines[i + 1]) for i, l in enumerate(lines) if l.strip() == "20"]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    k = min(ICON_MAX_W / w, ICON_MAX / h)
    return round(w * k, 3), round(h * k, 3)


def build(name):
    w, h = icon_size(name)
    common = dict(icon=f'"icons/{name}.svg"', icon_w=w, icon_h=h)
    for part in ("body", "icon"):
        scad(os.path.join(HERE, "stl", f"keycap_{name}_{part}.stl"), part=f'"{part}"', **common)
    scad(os.path.join(HERE, "previews", f"{name}.png"), part='"both"', **common)
    print(name, "icon", w, "x", h, "mm")


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "stl"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "previews"), exist_ok=True)
    for n in sys.argv[1:] or CAPS:
        build(n)
    if not sys.argv[1:]:
        scad(os.path.join(HERE, "stl", "keycap_stem_test.stl"), part='"test"')

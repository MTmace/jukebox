#!/usr/bin/env python3
"""Second keycap set: a smaller icon in the TOP HALF of the cap, next to the
switch's LED (like a store-bought backlit keycap). Fit each cap with the
icon's top toward the LED.

    python3 make_keycaps_top.py            all caps in make_keycaps.CAPS
    python3 make_keycaps_top.py power      just that icon

Writes top-half/: keycaps_top_all.3mf, keycap_top_<icon>.3mf, stl/, previews/.
"""
import os, sys
import trimesh
import make_keycaps as mk
from make_3mf import build

OUT = os.path.join(mk.HERE, "top-half")
ICON_H, ICON_W = 5.0, 10.0    # max icon size, mm
ICON_Y = 4.0                  # icon centre above the cap centre (stem boss reaches 2.8)
# Busy icons that don't read at 5 mm, swapped for simpler ones (Andrew, 2026-11-12)
SWAP = {"trash3-fill": "ban-left",             # Clear Queue
        "bootstrap-reboot": "arrow-clockwise",  # Reboot
        "database-gear": "gear-fill",           # Rebuild Playlist
        # Pad keys 1-3 now pick playlists, not favourite lights (Andrew, 2026-11-16)
        "1-circle": "all-text",                 # Playlist All Songs ("ALL", DejaVu Sans Bold)
        "2-circle": "mic-fill",                 # Playlist Oldies (a microphone)
        "3-circle": "tree-fill"}                # Playlist Christmas (a tree)
EXTRA = ["info-lg"]       # caps only in this set: Status Screen (F24)
GROW = 0.2                    # line widening per side: makes the icons bolder


def size(name):
    mk.ICON_MAX, mk.ICON_MAX_W = ICON_H, ICON_W
    return mk.icon_size(name)


def make(name):
    w, h = size(name)
    d = dict(icon=f'"icons/{name}.svg"', icon_w=w, icon_h=h, icon_y=ICON_Y, icon_grow=GROW, stem_notch=1, wall_pocket=1)
    paths = {}
    for part in ("body", "icon"):
        paths[part] = os.path.join(OUT, "stl", f"keycap_top_{name}_{part}.stl")
        mk.scad(paths[part], part=f'"{part}"', **d)
    preview(name, paths["icon"])
    print(name, "icon", w, "x", h, "mm")
    return (f"keycap {name}", [("body (black)", trimesh.load(paths["body"]), 1),
                               ("icon (white)", trimesh.load(paths["icon"]), 2)])


def preview(name, icon_stl):
    """Top view at 20 px/mm: black cap top, white icon (mirror of the print side)."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    m = trimesh.load(icon_stl)
    sec = m.section(plane_origin=[0, 0, 0.8], plane_normal=[0, 0, 1])
    fig, ax = plt.subplots(figsize=(3, 3), dpi=100)
    ax.add_patch(FancyBboxPatch((-7.25 + 2.2, -7.25 + 2.2), 14.5 - 4.4, 14.5 - 4.4,
                                boxstyle="round,pad=2.2", fc="#111", ec="#555"))
    for p in sec.to_2D(to_2D=trimesh.transformations.identity_matrix())[0].polygons_full:
        x, y = p.exterior.xy
        ax.fill(x, [-v for v in y], color="white")      # print is flipped about X: undo for the top view
        for hole in p.interiors:
            hx, hy = hole.xy
            ax.fill(hx, [-v for v in hy], color="#111")
    ax.set_xlim(-8, 8); ax.set_ylim(-8, 8); ax.set_aspect("equal"); ax.axis("off")
    from matplotlib.patches import Circle
    ax.add_patch(Circle((0, 0), 2.8, fill=False, ls="--", ec="#888", lw=0.8))   # stem underneath
    ax.text(0, 7.7, "LED side", ha="center", va="center", fontsize=7, color="#c00")
    fig.savefig(os.path.join(OUT, "previews", f"{name}.png"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    for sub in ("stl", "previews"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    names = sys.argv[1:] or [SWAP.get(n, n) for n in mk.CAPS] + EXTRA
    caps = [make(n) for n in names]
    for (title, items), n in zip(caps, names):
        build([(title, items)], os.path.join(OUT, f"keycap_top_{n}.3mf"))
    if not sys.argv[1:]:
        build(caps, os.path.join(OUT, "keycaps_top_all.3mf"))

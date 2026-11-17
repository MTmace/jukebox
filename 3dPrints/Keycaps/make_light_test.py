#!/usr/bin/env python3
"""Backlight test plate: the same icon cap twice, to see how the pad's LED
(at the top edge of each switch) lights the icon.

  A  no stem       the black stem can't block any light. It doesn't clip on:
                   just set it on the switch to look at the glow.
  B  clear stem    the stem is printed in the icon filament (filament 2), so
                   it can carry light into the middle of the icon. Note: this
                   makes the printer swap filament on almost every layer.

    python3 make_light_test.py [icon]      default skip-end-fill
Writes keycap_light_test.3mf (+ the STLs in stl/).
"""
import os, sys
import trimesh
from make_keycaps import HERE, scad, icon_size
from make_3mf import build

name = sys.argv[1] if len(sys.argv) > 1 else "skip-end-fill"
w, h = icon_size(name)
common = dict(icon=f'"icons/{name}.svg"', icon_w=w, icon_h=h)
stl = lambda n: os.path.join(HERE, "stl", f"light_test_{n}.stl")

scad(stl("body"), part='"body"', stem_style='"none"', **common)    # both caps: body with no black stem
scad(stl("icon"), part='"icon"', **common)
scad(stl("stem"), part='"stem"', **common)                         # cap B's stem, in the icon filament

L = trimesh.load
icon = L(stl("icon"))
body = L(stl("body"))
build([("A no stem", [("body (black)", body, 1), ("icon (white)", icon, 2)]),
       ("B clear stem", [("body (black)", body.copy(), 1), ("icon (white)", icon.copy(), 2),
                         ("stem (white)", L(stl("stem")), 2)])],
      os.path.join(HERE, "keycap_light_test.3mf"))
print("built keycap_light_test.3mf with", name)

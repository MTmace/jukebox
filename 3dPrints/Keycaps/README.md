# Macro pad keycaps (3D printed, light shines through the icon)

Flat-top 1u caps for the Koolertron 16-key, 3-knob pad (Cherry MX stems).
Each cap is a black body plus a white or natural icon that runs right through
the 1.6 mm top, so the pad's backlight lights up just the icon.

| File | What |
|---|---|
| `keycaps_all.3mf` | **all 15 icon caps on one plate, colours already set** (filament 1 black, 2 white) |
| `keycap_<icon>.3mf` | one icon cap, colours already set |
| `top-half/` | **second set**: bold 5 mm icons in the top half of the cap (the bottom edge just reaches the stem, which has a sloped notch on the LED side so light still gets under it; the LED-side wall is thinned under the icon too), next to the switch LED, like store-bought backlit caps. `keycaps_top_all.3mf` is all 16, including Status Screen (info-lg) (Clear Queue, Reboot and Rebuild Playlist use the simpler ban-left (circle with a slash), arrow-clockwise and gear-fill icons here; the three playlist keys use all-text ("ALL"), mic-fill and tree-fill instead of 1-circle, 2-circle, 3-circle); fit each cap with the icon toward the LED. Built by `make_keycaps_top.py`. |
| `keycap_light_test.3mf` | backlight test: cap A with **no stem** (just set it on the switch), cap B with the **stem in the icon filament** to carry light to the middle of the icon. B makes the AMS swap on almost every layer, so it is slow. |
| `stl/keycap_stem_test.stl` | 4 plain caps, stem sizes 1-4 (1 to 4 dots on top). **Print this first.** |
| `stl/keycap_<icon>_body.stl` | the black body with the icon cut out |
| `stl/keycap_<icon>_icon.stl` | the white icon that fills the cut-out |
| `previews/` | pictures of each cap |
| `keycap.scad`, `make_keycaps.py` | the model and the script that builds the files |
| `icons/` | the Bootstrap Icons used (MIT licence, icons.getbootstrap.com) |

All 15 action caps (picture: `previews/all_caps.png`):
Pause/Play `play-pause`, Attract `infinity`, Change Playlist `music-note-list`,
Next Song `skip-end-fill`, Random Song `dice-5-fill`, Fill Queue `list-ul`,
Clear Queue `trash3-fill`, Change Lighting `palette-fill`,
Favourite Light 1-3 `1-circle` `2-circle` `3-circle`, Sleep `moon-fill`,
Reboot `bootstrap-reboot`, Rebuild Playlist `database-gear`, Shut Down `power`.
They use stem size 2 until the stem test says otherwise. Thin icon lines are
widened 0.15 mm each side (`icon_grow`) so a 0.4 mm nozzle prints them.

## Printing

Material: PLA. Black for the body, white or natural (translucent) PLA for the icon.
Don't mix PLA and PETG in one cap; they don't stick to each other.

All files are already the right way round: top face down on the plate, stem up.

1. **Stem test.** Print `keycap_stem_test.stl` in black. Push each cap onto a key.
   Pick the one that clicks on firmly and doesn't wobble (it should pull off
   without a fight). Tell Claude the number of dots.
2. **Icon caps (AMS).** Open `keycaps_all.3mf` in Bambu Studio. Each cap is one
   object with two parts: the body is already on filament 1 and the icon on
   filament 2. Put black PLA in AMS slot 1 and white/natural in slot 2 (or change
   the filament colours in the left panel to match your slots).
3. Settings: 0.4 mm nozzle is fine; layer height 0.1 mm; textured PEI plate for
   a matte top (smooth plate gives a glossy top). No supports, no brim.

## Sizes (in keycap.scad)

Bottom 18 x 18 mm, top 14.5 x 14.5 mm, 11 mm tall, keys 19.05 mm apart.
Icons are scaled so the longest side is 10 mm (`ICON_MAX` in make_keycaps.py).
Stem slot widths: size 1 = 1.30, 2 = 1.35, 3 = 1.40, 4 = 1.45 mm
(arm length 4.10 - 4.25 mm).

To rebuild the 3MFs after changing STLs: `python3 make_3mf.py`.
To rebuild the backlight test: `python3 make_light_test.py`.
To build another cap: `python3 make_keycaps.py palette-fill` (the icon's SVG must be in `icons/`).

## Printable pad map

`jukebox-pad-map.pdf` (full size) and `jukebox-pad-map-small.pdf` (60%) show what
each key and dial on the Koolertron pad does, laid out as on the pad.
Print the small one at 100% / "Actual size".

| Key (row, col) | Action | Pad sends |
|---|---|---|
| 1,1 | Pause / Play | `;` |
| 1,2 | Next Song | Backspace |
| 1,3 | Status Screen (info-lg; cap: `top-half/keycap_top_info-lg.3mf`) | F24 (status-page/jukebox-status.py) |
| 1,4 | Change Playlist | Right Alt |
| 2,1 | Attract on/off | `'` |
| 2,2 | Random Song | Space |
| 2,3 | Fill Queue | macro M0 = Space x20 |
| 2,4 | Clear Queue | Delete |
| 3,1 | Change Lighting (cycle all themes) | F16 |
| 3,2 | Playlist: All Songs (cap `top-half/keycap_top_all-text.3mf`, "ALL") | Keypad 1 (state-manager/jukebox-state.py) |
| 3,3 | Playlist: Oldies (cap `top-half/keycap_top_mic-fill.3mf`, a microphone) | Keypad 2 (state-manager/jukebox-state.py) |
| 3,4 | Playlist: Christmas (cap `top-half/keycap_top_tree-fill.3mf`, a tree) | Keypad 3 (state-manager/jukebox-state.py) |
| 4,1 | Sleep (screens off, press twice) | Pause (state-manager/jukebox-state.py) |
| 4,2 | Rebuild Playlist | F21 (state-manager/jukebox-state.py) |
| 4,3 | Reboot | F20 (state-manager/jukebox-state.py) |
| 4,4 | Shut Down | F22 (state-manager/jukebox-state.py) |
| Dial 1 | Volume / mute | `=` `-` Left Ctrl |
| Dial 2 | Bass / flat | F17 F18 F19 |
| Dial 3 | Lights dim / on-off | F14 F15 F13 |

Other keys are blank (M1 = no action). `keycap-icons.png` compares the icon choices.

Rebuild the pages: `python3 make_pad_map.py` writes pad_map.html (uses the icons in
icons/), then print it to PDF from a browser.

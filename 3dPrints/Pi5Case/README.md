# Seeburg logo lids for the Pi 5 case

Replacement covers for the **PiAndHatCase r02 Pi 5 case** (cover `PiAndHatCase-r02c - Cover.stl`).
The rim that drops into the case and clicks onto the wall bumps is copied exactly from the
original cover, so they fit the same way. Only the vented top is replaced.

| File | What it is |
|---|---|
| `pi5_lid_solid.stl` | Solid lid, Seeburg logo engraved 0.6 mm into the top (like the Teensy case lid). See `solid_preview.png`. |
| `pi5_lid_hole.stl` | Lid with the logo cut right through. A 1 mm pocket on the underside takes the backing piece. See `hole_underside_preview.png`. |
| `pi5_lid_hole_v2.stl` + `pi5_lid_backing_v2.stl` | **Print these** instead of the hole lid and backing above. Bigger logo (78 mm), bigger B and R centres held by full-thickness 1 mm bridges (stencil style), so they print cleanly. Bigger pocket, so use the v2 backing. Made with `logo_w = 78.2` and `logo_face`/`logo_back` = `seeburg_logo_print_78.2.svg`. Needs the original cover STL beside the .scad to render. |
| `pi5_lid_backing_v2_grip.stl` | v2 backing with tapered grip ribs round the edge (0.2 mm press into the pocket) so it stays in. Use this one with `pi5_lid_hole_v2.stl`. Made with `grip = true`. |
| `pi5_lid_backing.stl` | 1 mm plate in your second colour. Presses into the pocket behind the logo, flush with the underside, so its colour shows through the logo. See `two_colour_preview.png`. |
| `pi5_lid_logotest.stl` | Just the logo strip of the hole lid plus a backing, to try colours and the press fit before printing the whole lid. |
| `pi5_lid_hole_v2_pins.stl` | The v2 hole lid (use with `pi5_lid_backing_v2_grip.stl`) plus a 16 x 6.5 mm slot over the 40-pin header, so the LED plug can go on pins 32 (GPIO 12, data) and 34 (GND) with the lid on. The slot shows pins 27-38. Fit the lid with the two rim gaps over the header (back wall); the logo then reads right from the front (power/HDMI side). See `pin_hole_preview.png`. |
| `pi5_lid_solid_pins.stl` | The solid engraved-logo lid with the same slot. |
| `pi5_lid_hole_v2_shifter.stl` | The v2 hole lid (use with `pi5_lid_backing_v2_grip.stl`) with a slot over the **whole 40-pin header** and two screw holes for the Adafruit Pixel Shifter (level shifter for the cabinet LED data), between the slot and the logo. The logo moves 11.5 mm towards the front to make room. Each hole has an M2.5 nut pocket on the underside. See `pin_shifter_preview.png`. Made with `pin_hole = true`, `pin_all = true`, `shifter = true`, `logo_dy = 11.5`. |
| `pi5_lid_solid_shifter.stl` | The solid engraved-logo lid with the same slot and board mount. |
| `pi5_shifter_spacer.stl` | Two 4 mm spacer tubes that hold the board off the lid (clear of the terminal pins). Fit: M2.5 x 8 screw down through the board, a spacer and the lid, into an M2.5 nut pressed into the pocket from inside. |
| `pi5_lid_pintest.stl` | Just the slot edge of the lid with its rim (about 40 x 15 mm, a few minutes to print). Push it onto the case over the header to check the slot lines up before printing a whole lid. |
| `pi5_lid.scad` | OpenSCAD source (`part = "solid"`, `"hole"`, `"backing"`, `"logotest"`, `"pintest"`; `pin_hole = true` adds the header slot, `pin_side` picks which long side). Needs `pi5_lid_outline.scad`, `seeburg_logo.svg`, `seeburg_logo_cut.svg` and the original cover STL (`PiAndHatCase-r02c - Cover.stl`) beside it. |

| `pi5_case_ears.stl` | The case base (PiAndHatCase r02a) with three screw ears added, like the Teensy and WAGO boxes: 12 x 16 x 4 mm, 4.2 mm hole countersunk for #6 wood screws. Two on the plain back side, one on the front past the power/HDMI ports. None on the ends, where the SD card slot and the USB/Ethernet plugs are. See `case_ears_preview.png`. |
| `pi5_case_ears.scad` | Source for the ears. Needs the original `PiAndHatCase-r02a - PI5-Case.stl` beside it. Ear positions are in `ears`. |

Outside size is the same as the original: 92.1 x 59.1 mm, 3 mm top, 7 mm with the rim.

## Printing (Bambu P1S)
- Print every part flat as exported: the lids print **logo face down**, rim up. No supports.
- PLA prints the fine logo edges more cleanly than PETG.
- The logo reads the right way up when the side of the rim with the two gaps is at the back.

## Logo colour (hole lid)
Press the backing into the pocket from underneath. The centres of the B and R are held by thin
bridges at the back of the lid (1 mm deep, 0.8 mm wide), set back from the front so they hardly
show. If the backing is loose, a drop of glue holds it. `fit` in the .scad = total clearance
round the backing (0.15 mm).

## Airflow
The original cover is mostly vent slots. These lids are closed, so the Pi only breathes through
the vents in the case bottom. Watch the Pi temperature (`vcgencmd measure_temp`) after fitting one.

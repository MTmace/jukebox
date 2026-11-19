# Case for the Teensy board

A two-part 3D-printed box for the Teensy 4.1 plugged into the Treedix
screw-terminal breakout board (66 × 40.6 mm).

![Case preview](preview.png)

- **Base** (`teensy_case_base.stl`): the board sits on a ledge inside, and four
  snap tabs (two in each end wall) click over its short edges to hold it down:
  push the board straight down until it clicks; to take it out, pull the tabs
  outward. Long slots
  on both sides let the wires reach the screw terminals, there's an opening at one
  end for the USB cable, and two ears screw it to the cabinet (#6 wood screws).
- **Lid** (`teensy_case_lid.stl`): pushes on. Version 2 has no posts: the first
  print's posts landed on the Teensy and terminal blocks and bent.
  The Seeburg logo (`seeburg_logo.svg`, keep it next to the .scad) is engraved
  0.6 mm into the top. See `lid_preview.png`.

- **Two-colour lid** (`teensy_case_hole.stl` + `teensy_case_backing.stl`): the
  same lid with the logo cut right through, and a 1 mm plate in a second colour
  that presses into the rim behind it (like the Pi and WAGO box lids). The
  letter centres hang on thin bridges at the back. `seeburg_logo_cut.svg`
  (made by `make_logo_cut.py`) must sit beside the .scad.

Print both flat side down; no supports needed. PLA is fine inside the cabinet.

**Before printing, measure your board** and check the numbers at the top of
`teensy_case.scad`: `board_l`, `board_w` and `stack_h` (height from the board's top
to the top of the Teensy). Put the Teensy's USB end at the end with the opening.
Change a number in OpenSCAD, press F6, and export each part as STL
(`part = "base"`, then `part = "lid"`).

Version 1 was printed 2026-10-30 (board loose, lid posts bent); version 2 adds the snap tabs and drops the posts.

- **Two-colour lid v2** (`teensy_case_hole_v2.stl` + the same `teensy_case_backing.stl`):
  print this instead of `teensy_case_hole.stl`. The logo is a bit bigger (62 mm),
  the B and R centres are bigger (1.1 mm) and are held by 1 mm bridges through the
  full lid (stencil style), so they no longer print distorted. Made with
  `logo_w = 62` and `logo_face`/`logo_back` = `seeburg_logo_print_62.svg`
  (`python3 make_logo_print.py seeburg_logo.svg seeburg_logo_print_62.svg 62`).

- **Grip backing** (`teensy_case_backing_grip.stl`): the backing with small tapered
  grip ribs round the edge (0.2 mm press into the lip ring) so it stays in. Use it
  instead of `teensy_case_backing.stl` with either hole lid. Narrow end in first.

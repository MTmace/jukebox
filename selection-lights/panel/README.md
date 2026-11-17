# Lamp panel (holds the 12 mm bullet LEDs)

A printed plate, 14.5" x 2" (368 x 51 mm), that the ALITOVE 12 mm bullet LEDs push
through from the front. Their plastic clips snap behind the 2 mm plate. A 6 mm rim on
the back keeps the thin plate flat.

## Step 1: print the test piece

`lamp_panel_test.stl` is an 80 x 51 mm piece with four holes: 11.8, 12.0, 12.2 and
12.4 mm. The size is printed on the back under each hole.

- Print it **front face down** on the bed (rim pointing up). No supports.
- PLA or PETG, 0.2 mm layers, 3 walls.
- Push a bullet into each hole. The best one goes in with a firm push, clicks, and
  doesn't wobble or pull back out.

Tell me which hole fits best. If even 12.4 is tight, or 11.8 is loose, I'll make a
new test piece. If the clips don't catch (the plate is too thick or too thin for
them), tell me that too, because the plate thickness can change.

Result (2026-10-09): 12.0 mm fits best.

## Step 1b: thinner around the holes

`lamp_panel_thin_test.stl` is 50 x 51 mm with two 12.0 mm holes 3/4" apart. The
plate stays 2 mm, but a 17 mm ring around each hole is thinned from the back, to
1.2 mm on one and 1.6 mm on the other (printed on the back), so the bullet's clips
can catch. The front stays flat. Print it the same way, front face down.

Result (2026-10-09): 1.2 mm is perfect.

## Step 1c: clips that hug the inner housing

The first clip version hugged the outer housing, which put the bulbs too far back.
`lamp_panel_hug_test.stl` clips onto the **inner housing** instead (26.5 mm tall,
1.8 mm walls, holes 13.8 mm inside). It is about 84 x 30.5 mm, with five 12.0 mm
holes 15.6 mm apart (one 13.8 mm cell + one 1.8 mm wall; 3/4" was too far), thinned
to 1.2 mm. The short ends are open. The two long walls
reach 5.2 mm forward over the top and bottom of the housing (3.7 mm deep), with a small snap ridge
inside each wall tip, so the plate sits right behind the holes.

Print it **back face down** (walls pointing up). No supports.

Settings at the top of the "hug" section of `lamp_panel.scad`: `INNER_H` (housing
height), `FIT` (extra gap), `HOUSING_D` (housing depth; the walls follow it), `HUG_RIDGE` (grip).

## Step 2: the full panel (two halves)

The hug test fits perfectly (2026-10-10), so the full panel uses the same clips,
depth, hole size, 1.2 mm rings and 15.6 mm spacing. It has one row of 20 holes
(1 2, then 0-7, then 0-9; it was 22 until 2026-10-28, when the tens turned out to stop at 7) on a 14.5" (368 mm) strip, split in two so each half
fits a Bambu P1S bed (256 mm):

| File | Size | Holes |
|---|---|---|
| `lamp_panel_half1.stl` | 181 x 31 mm (includes the two dovetail tabs) | 1-10 |
| `lamp_panel_half2.stl` | 171 x 31 mm (has the two dovetail slots) | 11-20 |

Print both **back face down** (walls pointing up), no supports. Push half 1's
two tabs down into half 2's slots so the plates sit flush, then snap the panel onto
the housing. The ends are open, so slide it along until the holes line up.

## Step 3: stronger joint (2026-10-10)

The first joint was loose even when glued, so both halves changed:

- The dovetails are longer (7 mm instead of 4) and wider at the head, and the
  clearance is 0.05 mm instead of 0.15 mm, so they need a firm press.
- Two splice bars (`lamp_panel_splice.stl`, 44 x 5 x 2 mm each, both in one file)
  glue across the joint on the back, one above the holes and one below, centred on
  the joint and 2 mm in from the long edge. They stay clear of the bulbs.

Before reprinting the halves, print `lamp_panel_joint_test.stl` (two small pieces,
25 mm of each side of the joint, a few minutes to print) and press them together.
If it won't go in, change `DOVE_GAP` to 0.1; if it still wiggles, to 0. Then print
both halves and the splice bars **flat, back face down**, press the halves together
with glue in the dovetails, and glue the bars on the back (CA glue or epoxy).

Open the .scad file in OpenSCAD (free, openscad.org) to change sizes: set `part`
to "half1", "half2", "splice", "jointtest" or "panel" (both halves together), press F6, then
File > Export > STL.


## Step 4: 13.5" long, stronger joint (2026-10-28)

The 20 windows span 12.5", so the panel is now 13.5" (342.9 mm) long, leaving
about 0.5" past the windows at each end (the holes are centred). The joint is
stronger: dovetails 10 mm long with a 4.2 mm neck (were 7 and 3), and the splice
bars are 70 x 3 mm (were 44 x 2). Reprint both halves, the splice bars and the
joint test. `lamp_panel_half2_for_old_half1.stl` is gone: an old half 1 is too long now.

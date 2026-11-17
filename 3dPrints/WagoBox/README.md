# WAGO 221 connector box

Holds four WAGO 221-412 (2-way) lever connectors in a row along the back
wall, levers up, wire holes facing an open 30 mm wiring bay.
The input wires come in together through one 10 mm slot in the middle
of the front wall and fan out across the bay. The output wires fan out and leave together
through one 13 mm slot in the left end wall (left as seen from the front). Each connector drops into a pocket with full-depth
side walls (front left open for the wire holes), with 8 mm of finger room between connectors. Outside size
92 x 56 x 18 mm (4 mm of room above the connectors) (plus a 12 mm screw ear at each end).

## Folders

Each box folder has everything to print for that box: the base, its lids and
its colour insert. Superseded versions are in an `old` subfolder of each box.

**`2pin/`** box for 4 x 221-412, 92 x 56 x 18 mm
- `wago_box_base.stl`: output slot in the LEFT end. `wago_box_base_right.stl`: output in the RIGHT end. Both have one input slot in the middle of the front.
- Lids (fit both bases): `wago_box_lid_v3.stl` (logo cut through, stencil-style B and R) or `wago_box_solid_lid_v2.stl` (logo engraved, no insert). The ledge under the lid is cut away over the front slot and both end slots, so the wires aren't pinched.
- `wago_box_insert_grip.stl`: colour plate for the cut-through lid, with grip ribs so it stays in.
- `old/`: `wago_box_lid_v2.stl` and `wago_box_solid_lid.stl` (no ledge cut-outs), `wago_box_lid.stl` (first cut-through lid; B and R printed distorted), `wago_box_insert.stl` (plain plate, fell out).

**`3pin-1hole/`** box for 4 x 221-413, one input slot in the middle, output left, 114.6 x 55.65 x 17.8 mm
- `wago_box_3pin_base.stl`
- Lids: `wago_box_3pin_lid_v2.stl` (logo cut through) or `wago_box_3pin_solid_lid_v2.stl`. The ledge under the lid is cut away over the wire slots.
- `wago_box_3pin_insert_grip.stl`: colour plate.
- `old/`: lids without the ledge cut-outs, plain insert.

**`3pin-2hole/`** box for 4 x 221-413, TWO input slots, each centred between the left pair and the right pair of connectors, output left
- `wago_box_3pin_base_2in_v2.stl`
- Lids: `wago_box_3pin_lid_2in_v2.stl` or `wago_box_3pin_solid_lid_2in_v2.stl`. Only these lids fit this box (the front snap bumps are moved towards the corners).
- `wago_box_3pin_insert_grip.stl`: colour plate (same as the 1-hole box).
- `old/`: the first two-slot box (slots at 35% / 65%) and its lids.

**`tests/`** small test prints: `wago_box_snaptest.stl` (one snap bump), `wago_box_logotest.stl` (logo strip + insert strip), `wago_box_3pin_pockettest.stl` (one 221-413 pocket).

**`previews/`** pictures of the boxes and lids.

**Source (this folder):** `wago_box.scad` (OpenSCAD; needs the `.svg` files beside it), `seeburg_logo.svg`, `seeburg_logo_cut.svg`, `seeburg_logo_print_78.2.svg`, `make_logo_cut.py`, `make_logo_print.py`.
Settings used: 3-pin `wago_w = 18.5`; right output `out_side = "right"`; ledge cut-outs `rim_notch = true`; two slots between pairs `in_pair = true`; v2 logo `logo_w = 78.2` with `logo_face`/`logo_back` = `seeburg_logo_print_78.2.svg`; grip insert `grip = true`; solid lid `part = "solidlid"`.

## Printing (Bambu P1S)
- Both parts print flat side down as exported, no supports. Lid prints logo face down.

## Logo colour
The logo is cut right through the lid. Print the grip insert in a second
colour and press it into the lid's rim from underneath; it sits against the back
of the lid and its colour shows through the logo. The centres of the B and R are
held by thin bridges at the back of the lid (1 mm deep, 0.8 mm wide), so they are
set back from the front and hardly show. See `two_colour_preview.png`.

## Assembly
1. Screw the box down through the ears (#6 wood screws).
2. Wire the connectors outside the box, drop each into its guides, lay the inputs in the front slot and the outputs in the left slot.
3. Press the lid into the top until it clicks.
4. To open, lift the lid edge with a fingertip at one of the wire slots (they run up to the lid).

## Adjusting
Connector size: The 221-412s measure 12.9 x 17.9 mm (`wago_w`, `wago_d`); `n_wago` = number of connectors (4); `fit` = total play round each connector (0.15 mm), `gap` =
space between connectors, `bay` = wiring bay depth, `in_w` / `slot_w` = input / output slot width.
Snap: `bump` = how far each bump sticks out (0.6 mm; bigger = tighter). `lid_gap` = clearance round the lid (0.15 mm).

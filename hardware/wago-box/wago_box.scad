// Box for four WAGO 221-412 (2-way) lever connectors. The connectors sit in a
// row along the back wall with their wire holes facing an open wiring bay at
// the front. The input wires
// come in together through one slot in the middle of the front wall and fan
// out across the bay; the output wires leave together through one slot in the
// left end wall (left as seen from the front).
// Parts:
//   part = "base"    : box with low corner guides for each connector (they just
//                      drop in, with finger room between them), the wiring bay,
//                      U-shaped slots open up to the lid (wires lay in from the
//                      top): one input in the middle of the front wall, one
//                      output in the left wall; two screw ears for mounting
//   part = "lid"     : lid that drops into a step round the top of the walls
//                      and sits flush with the top. Small bumps on the walls click
//                      into holes in the lid's rim. The Seeburg logo is cut right
//                      through, so the insert behind it shows through.
//   part = "insert"  : thin plate in a second colour that presses into the lid's
//                      rim behind the logo (translucent filament lets light through)
//   part = "logotest": the logo strip of the lid plus a matching strip of insert
//                      To open: lift the lid edge at one of the wire slots.
//   part = "snaptest": one bump with its piece of wall and lid, to try the snap
//   part = "pockettest": one connector pocket on a small plate (a few grams)
//   part = "fittest" : bottom 8 mm of the base, to check the connectors in
//                      their guides before the full print
// Render (F6) and export STL. Print flat side down, no supports.
//
// Connector size: The 221-412s measure 12.9 x 17.9 mm (W x D). Side walls
// run the full depth of each connector.

part = "both";            // "base", "lid", "fittest", "pockettest", "snaptest" or "both"

// ---- connectors ------------------------------------------------------------
n_wago    = 4;
wago_w    = 12.9;                 // 221-412 across the levers (measured)
wago_d    = 17.9;                 // front (wire holes) to back
wago_h    = 8.3;                  // height with levers closed
fit       = 0.15;                 // total play round each connector
gap       = 8;                    // finger room between connectors
guide     = 1.6;                  // corner guide wall
guide_l   = 5;                    // corner guide arm length
guide_f   = 1.0;                  // front arms stop at the corners, clear of the wire holes
guide_h   = 5;                    // guides stay low so connectors drop straight in

// ---- box -------------------------------------------------------------------
wall      = 3.0;
floor_t   = 3.0;
lid_t     = 2.5;          // lid plate, flush with the top of the walls
corner_r  = 3;
end_room  = 5;            // finger room between the end connectors and the end walls
bay       = 30;           // open wiring space in front of the connectors
lever_room= 4;            // space above the closed connectors (lift the lid to open levers)
bridge_t  = 1.0;          // the letter centres (B, R) hang on thin bridges this thick at the back
insert_t  = 1.2;          // colour insert behind the lid
insert_gap= 0.15;         // total clearance round the insert inside the rim (snug press fit)
grip      = false;      // true: colour plate gets grip ribs (press fit that stays in)
step      = 1.2;          // the walls are this much thinner where the lid sits
rim_h     = 4;            // lid rim that drops into the step
lid_gap   = 0.15;         // clearance round the lid
bump_d    = 3;            // snap bumps on the walls
bump      = 0.6;          // how far each bump sticks out (bigger = tighter)

row_l     = n_wago * (wago_w + fit) + (n_wago - 1) * gap;
inner_l   = row_l + 2*end_room;
inner_w   = bay + wago_d + fit + guide;
inner_h   = wago_h + lever_room;
outer_l   = inner_l + 2*wall;
outer_w   = inner_w + 2*wall;
outer_h   = floor_t + inner_h + lid_t;    // lid is flush with the top
thin      = wall - step;
recess_z  = outer_h - lid_t - rim_h;      // the step the lid rim sits on
row_x0    = wall + end_room;
row_y0    = wall + bay;                   // front of the connectors
logo_w    = outer_l - 22;
logo_face = "seeburg_logo.svg";      // hole lid: shape cut through the face
logo_back = "seeburg_logo_cut.svg";  // hole lid: shape cut through the back (bridges for the B and R centres)
// v2 hole lid (stronger letters for small lids): set both to a seeburg_logo_print_<w>.svg
// made by make_logo_print.py for the same logo_w; its bridges run the full thickness.
engrave   = 0.6;            // solid lid: depth of the engraved logo

// U-shaped wire slots, open up to the lid
out_side  = "left";       // end wall with the output slot, seen from the front: "left" or "right"
slot_w    = 13;           // output slot in that end wall, centred on the wiring bay
in_w      = 10;           // input slot(s) in the front wall, for the input wires
in_pos    = [0.5];        // where the input slots sit along the front, as fractions of the length
                          // ([0.35, 0.65] = two slots, one each side of centre)
rim_notch = false;        // true: lid rim cut away over the wire slots (more room for wires)
notch_m   = 1;            // extra width each side of a slot for the rim notch
slot_y    = wall + bay/2;
slot_z    = floor_t + 1 + slot_w/2;       // centre of the round bottom; slot runs up to the lid

ear_l     = 12;           // screw ears at both ends, for #6 wood screws
ear_t     = 4;
ear_hole  = 4.2;

$fn = 40;

module rbox(l, w, h, r) {
  translate([r, r, 0]) linear_extrude(h) offset(r) square([l - 2*r, w - 2*r]);
}

function wago_x(i) = row_x0 + i * (wago_w + fit + gap);


// L-shaped guides at the four corners of a connector of width w
module guides(w) { guides_play(w, fit); }
module guides_play(w, play) {
  l = w + play; d = wago_d + play;
  for (cx = [0, 1]) for (cy = [0, 1])
    translate([cx * l, cy * d, 0]) mirror([cx, 0, 0]) mirror([0, cy, 0])
      translate([-guide, -guide, 0]) {
        cube([(cy == 0 ? guide_f : guide_l) + guide, guide, guide_h]);
        cube([guide, d/2 + guide, guide_h]);   // side walls meet in the middle
      }
}

// snap bumps: two on the front wall and two on the back (between the input
// slots) and one on each end wall, towards the back. [x, y, angle the bump faces]
function gap_x(k) = wago_x(k) + wago_w + fit + gap/2;
bump_z    = outer_h - lid_t - rim_h/2;
// in_pair = true: two input slots, each centred in the gap between the two left
// and the two right connectors; the front snap bumps move out towards the corners
in_pair = false;
in_xs   = in_pair ? [gap_x(0), gap_x(n_wago - 2)] : [for (f = in_pos) outer_l*f];
front_bx = in_pair ? [14, outer_l - 14] : [gap_x(0), gap_x(n_wago - 2)];
bumps = [[front_bx[0], thin, 90], [front_bx[1], thin, 90],
         [gap_x(0), outer_w - thin, -90], [gap_x(n_wago - 2), outer_w - thin, -90],
         [thin, outer_w * 0.72, 0], [outer_l - thin, outer_w * 0.72, 180]];

// outline of the lid / step, offset inwards by o from the outside of the box
module outline(o, h) {
  translate([o, o, 0]) rbox(outer_l - 2*o, outer_w - 2*o, h, max(corner_r - o, 0.5));
}

module base() {
  difference() {
    union() {
      difference() {
        rbox(outer_l, outer_w, outer_h, corner_r);
        translate([wall, wall, floor_t]) cube([inner_l, inner_w, outer_h]);
        translate([0, 0, recess_z]) outline(thin, outer_h);
      }
      // snap bumps on the thin top part of the walls
      intersection() {
        for (b = bumps) translate([b[0], b[1], bump_z]) rotate([0, 0, b[2]])
          translate([bump - bump_d/2, 0, 0]) sphere(d = bump_d, $fn = 24);
        outline(0.01, outer_h);           // keep them off the outside faces
      }
      // corner guides for each connector
      for (i = [0:n_wago - 1]) translate([wago_x(i), row_y0, floor_t]) guides(wago_w);
      // screw ears
      for (x = [-ear_l, outer_l - 1]) translate([x, outer_w/2 - 8, 0])
        difference() {
          cube([ear_l + 1, 16, ear_t]);
          translate([x < 0 ? ear_l/2 : ear_l/2 + 1, 8, -1]) cylinder(d = ear_hole, h = ear_t + 2);
        }
    }
    // output slot in the left or right end wall
    translate([out_side == "right" ? outer_l - wall - 1 : -1, slot_y, slot_z]) {
      rotate([0, 90, 0]) cylinder(d = slot_w, h = wall + 2);
      translate([0, -slot_w/2, 0]) cube([wall + 2, slot_w, outer_h]);
    }
    // input slot in the middle of the front wall
    for (x = in_xs) translate([x, -1, floor_t + 1 + in_w/2]) {
      rotate([-90, 0, 0]) cylinder(d = in_w, h = wall + 2);
      translate([-in_w/2, 0, 0]) cube([in_w, wall + 2, outer_h]);
    }
    // countersink the ear holes
    for (x = [-ear_l/2, outer_l + ear_l/2])
      translate([x, outer_w/2, ear_t - 1.6]) cylinder(d1 = ear_hole, d2 = 8.4, h = 1.61);
  }
}

// logo cut from z0 to z1 in lid print coordinates, mirrored so it reads the right
// way up from the front once the lid is flipped onto the box
module logo_cut(file, z0, z1) {
  translate([outer_l/2, outer_w/2, z0]) mirror([1, 0, 0])
    linear_extrude(z1 - z0) resize([logo_w, 0], auto = true) import(file, center = true);
}

// grip ribs for the colour plate: small tapered ribs round the edge that
// stand grip_p proud of the opening and squash as the plate is pressed in,
// so it holds instead of falling out. Plate is l x w, corner at the origin.
grip_p = 0.2;   // how far each rib presses into the wall (per side)
module grip_ribs(l, w, t, gap) {
  r = 0.8; o = gap/2 + grip_p;          // rib reaches this far past the plate edge
  pts = [[l*0.2, 0, 0], [l*0.5, 0, 0], [l*0.8, 0, 0], [l*0.2, w, 1], [l*0.5, w, 1], [l*0.8, w, 1],
         [0, w/2, 2], [l, w/2, 3]];
  for (p = pts) {
    d = p[2] == 0 ? [0, -1] : p[2] == 1 ? [0, 1] : p[2] == 2 ? [-1, 0] : [1, 0];
    translate([p[0] + d[0]*(o - r), p[1] + d[1]*(o - r), 0])
      cylinder(h = t, r1 = r - grip_p - 0.1, r2 = r, $fn = 24);   // narrow end leads in
  }
}

module insert() {   // fits inside the lid rim, against the back of the lid plate
  cube([inner_l - insert_gap, inner_w - insert_gap, insert_t]);
  if (grip) grip_ribs(inner_l - insert_gap, inner_w - insert_gap, insert_t, insert_gap);
}

module lid(solid = false) {   // built upside down, in print orientation: logo face on the bed
  difference() {
    union() {
      outline(thin + lid_gap, lid_t);
      // rim round the edge that sits in the step
      difference() {
        outline(thin + lid_gap, lid_t + rim_h);
        translate([wall, wall, -1]) cube([inner_l, inner_w, lid_t + rim_h + 2]);
      }
    }
    // rim_notch: rim cut away over the wire slots so wires have more room to
    // come in (front slot, and both end slots so the lid fits left or right boxes)
    if (rim_notch) {
      for (x = in_xs) translate([outer_l - x - in_w/2 - notch_m, -1, lid_t - 0.01]) cube([in_w + 2*notch_m, wall + 1, rim_h + 1]);
      for (x = [-1, outer_l - wall - 0.5])
        translate([x, slot_y - slot_w/2 - notch_m, lid_t - 0.01]) cube([wall + 1.5, slot_w + 2*notch_m, rim_h + 1]);
    }
    // holes in the rim for the snap bumps (lid is flipped: x mirrored)
    for (b = bumps) translate([outer_l - b[0], b[1], lid_t + rim_h/2]) rotate([0, 0, 180 - b[2]])
      rotate([0, 90, 0]) cylinder(d = bump_d + 0.4, h = 2*wall, center = true, $fn = 24);
    // Seeburg logo cut right through (seeburg_logo.svg and seeburg_logo_cut.svg
    // must sit beside this file). From the front it is the whole logo; at the back
    // the cut version leaves thin bridges holding the centres of the B and R.
    if (solid) logo_cut("seeburg_logo.svg", -1, engrave);   // solid lid: logo engraved only
    else {
      logo_cut(logo_face, -1, lid_t - bridge_t);
      logo_cut(logo_back, -1, lid_t + 1);
    }
  }
}

echo(str("outside ", outer_l, " x ", outer_w, " x ", outer_h, " mm (without ears)"));

if (part == "base") base();
else if (part == "lid") lid();
else if (part == "solidlid") lid(solid = true);   // no through-cut: logo engraved 0.6 mm   // already print orientation: logo face down
else if (part == "insert") insert();
else if (part == "logotest") {
  intersection() { lid();
    translate([outer_l/2 - logo_w/2 - 3, outer_w/2 - 9, 0]) cube([logo_w + 6, 18, lid_t]); }
  translate([outer_l/2 - logo_w/2 - 3, outer_w/2 + 12, 0]) cube([logo_w + 6, 18, insert_t]);
}
else if (part == "pockettest") {
  // one pocket on a small plate, same guides as the box
  difference() {
    cube([wago_w + fit + 8, wago_d + fit + 8, 1.6]);
    translate([2, 1.2, 1.2]) linear_extrude(1) text(str(wago_w + fit), size = 2.5);
  }
  translate([4, 4, 1.5]) guides(wago_w);
}
else if (part == "fittest") intersection() { base(); translate([-50, -50, 0]) cube([500, 500, 8]); }
else if (part == "snaptest") {
  // one back-wall bump: a 20 mm piece of wall and the matching piece of lid
  intersection() { base(); translate([gap_x(0) - 10, outer_w - 8, 0]) cube([20, 8, outer_h]); }
  translate([0, -20, 0]) intersection() { lid();
    translate([outer_l - gap_x(0) - 10, outer_w - 8, 0]) cube([20, 8, 50]); }
}
else {
  base();
  translate([outer_l, 0, outer_h + 15]) rotate([0, 180, 0]) lid();
}

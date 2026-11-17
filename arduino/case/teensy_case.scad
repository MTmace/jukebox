// Case for the Teensy 4.1 on a Treedix screw-terminal breakout board
// (board 66 x 40.6 mm, terminal rows along both long sides).
// Two printed parts:
//   part = "base" : tray with a ledge the board sits on, four snap tabs (two in
//                   each end wall) that click over the board's short edges,
//                   wire slots along both long sides, USB opening, screw ears
//   part = "hole"    : the same lid with the logo cut right through; the B and R
//                      centres hang on thin bridges set back from the face
//   part = "backing" : 1 mm plate in a second colour that presses into the lid's
//                      rim behind the cut-through logo
//   part = "lid"  : push-fit lid. No posts: v1's posts landed on the Teensy
//                   and terminal blocks and bent, so the tabs hold the board now
// Render each one (F6) and export STL. Print both flat side down, no supports.
//
// MEASURE YOUR BOARD FIRST and change board_l / board_w / stack_h if needed.

part = "both";            // "base", "lid" or "both" (preview)

// ---- board -------------------------------------------------------------
board_l   = 66.0;         // breakout board length
board_w   = 40.6;         // breakout board width
board_t   = 1.6;
under     = 3.0;          // room under the board for solder joints
stack_h   = 22.0;         // top of board to top of Teensy and its pins
clear     = 0.6;          // gap around the board on each side

// ---- case --------------------------------------------------------------
wall      = 2.0;
floor_t   = 2.0;
lid_t     = 2.0;
corner_r  = 3;
logo_w    = 60;           // width of the Seeburg logo on the lid
logo_face = "seeburg_logo.svg";      // hole lid: shape cut through the face
logo_back = "seeburg_logo_cut.svg";  // hole lid: shape cut through the back (bridges for the B and R centres)
// v2 hole lid (stronger letters for small lids): set both to a seeburg_logo_print_<w>.svg
// made by make_logo_print.py for the same logo_w; its bridges run the full thickness.
logo_d    = 0.6;          // how deep the logo is cut into the lid (0 = plain lid)
bridge_t  = 1.0;          // "hole" lid: bridges for the letter centres, this thick at the back
backing_t = 1.0;          // backing plate thickness
backing_fit = 0.15;       // total clearance round the backing inside the lid rim
grip      = false;      // true: colour plate gets grip ribs (press fit that stays in)
ledge_w   = 2.2;          // board edge rests on this
inner_l   = board_l + 2*clear;
inner_w   = board_w + 2*clear;
inner_h   = under + board_t + stack_h + 1;
outer_l   = inner_l + 2*wall;
outer_w   = inner_w + 2*wall;
outer_h   = floor_t + inner_h;

// Wires enter the screw terminals from the long sides.
slot_from = floor_t + under + board_t + 0.5;   // bottom of the wire slots
slot_h    = 4.5;
slot_l    = inner_l - 8;
// Snap-off print supports: thin ribs across each wire slot so its top doesn't
// sag. Twist them out with needle-nose pliers after printing.
slot_ribs = false;
rib_t     = 0.6;          // rib thickness
rib_every = 8;            // rib spacing along the slot

// Micro-USB on the Teensy, at the x = 0 end. Centred across the width;
// move usb_y if your Teensy sits off-centre on the breakout.
usb_y     = 0;
usb_w     = 13;
usb_h     = 9;
usb_z     = floor_t + under + board_t + 8.5;   // Teensy sits on its sockets

ear_l     = 12;           // screw ears at both ends, for #6 wood screws
ear_hole  = 4.2;

// Snap tabs: springy strips cut into each end wall, with a hook at the bottom
// that catches the top of the board. Push the board straight down; it clicks in.
tab_w     = 7;            // tab width
tab_y     = 13;           // tab centre, measured from the middle of the end wall
tab_gap   = 1.0;          // slot either side of a tab
hook      = 1.0;          // how far the hook sticks out from the wall (v2 1.3 was too tight)
hook_h    = 2.0;          // hook height (sloped top)
hook_u    = 0.5;          // underside slopes down this much toward the wall, so a
                          // firm pull upward pushes the tabs out and frees the board
lip       = 1.2;          // lid lip that fits inside the walls
lip_h     = 5;
lip_gap   = 0.1;          // gap between lip and walls (v2 had 0.25: too loose)
grip      = 0.35;         // grip ridges on the lip's long sides push this far
                          // into the walls at the lid end, tapering to 0 at the tip


$fn = 40;

module rbox(l, w, h, r) {
  translate([r, r, 0]) linear_extrude(h) offset(r) square([l - 2*r, w - 2*r]);
}

board_top = floor_t + under + board_t;
tab_root  = floor_t + 1;   // tabs bend from just above the floor

module hooks() {
  // flat underside sits just above the board top, sloped top guides the board in
  for (sy = [-1, 1]) for (end = [0, 1])
    translate([end == 0 ? wall : outer_l - wall, outer_w/2 + sy*tab_y - tab_w/2, board_top + 0.3])
      mirror([end, 0, 0]) rotate([90, 0, 0]) translate([0, 0, -tab_w])
        linear_extrude(tab_w) polygon([[0, -hook_u], [hook, 0], [0, hook_h]]);
}

module base() {
  difference() {
    union() {
      rbox(outer_l, outer_w, outer_h, corner_r);
      // screw ears
      for (x = [-ear_l, outer_l]) translate([x, outer_w/2 - 8, 0])
        difference() {
          cube([ear_l, 16, 3]);
          translate([ear_l/2, 8, -1]) cylinder(d = ear_hole, h = 5);
        }
    }
    // cavity
    translate([wall, wall, floor_t]) cube([inner_l, inner_w, inner_h + 1]);
    // wire slots, both long sides
    for (y = [-1, outer_w - wall - 1])
      translate([(outer_l - slot_l)/2, y, slot_from]) cube([slot_l, wall + 2, slot_h]);
    // USB opening
    translate([-1, outer_w/2 + usb_y - usb_w/2, usb_z - usb_h/2]) cube([wall + 2, usb_w, usb_h]);
    // slots that free the snap tabs (open at the top, joined at the bottom)
    for (x = [-1, outer_l - wall - 1]) for (sy = [-1, 1])
      for (side = [-1, 1])
        translate([x, outer_w/2 + sy*tab_y + side*(tab_w + tab_gap)/2 - tab_gap/2, tab_root])
          cube([wall + 2, tab_gap, outer_h]);
    // countersink the ear holes
    for (x = [-ear_l/2, outer_l + ear_l/2]) translate([x, outer_w/2, 1.5]) cylinder(d1 = ear_hole, d2 = 8, h = 1.6);
  }
  // ledge the board rests on (all round, under the board edge)
  translate([wall, wall, floor_t]) difference() {
    cube([inner_l, inner_w, under]);
    translate([ledge_w, ledge_w, -1]) cube([inner_l - 2*ledge_w, inner_w - 2*ledge_w, under + 2]);
  }
  hooks();
  if (slot_ribs) {
    n = floor(slot_l / rib_every);
    for (y = [0, outer_w - wall]) for (i = [1 : n - 1])
      translate([(outer_l - slot_l)/2 + i*slot_l/n - rib_t/2, y, slot_from - 0.01])
        cube([rib_t, wall, slot_h + 0.02]);
  }
}

// seeburg_logo_cut.svg is made by: python3 make_logo_cut.py seeburg_logo.svg seeburg_logo_cut.svg 0.8 60
module logo_through(file, z0, z1) {
  translate([outer_l/2, outer_w/2, z1]) rotate([180, 0, 0])
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

// fills the opening inside the lid rim, pressed against the back of the top
module backing() {
  cube([inner_l - 2*lip_gap - 2*lip - backing_fit, inner_w - 2*lip_gap - 2*lip - backing_fit, backing_t]);
  if (grip) grip_ribs(inner_l - 2*lip_gap - 2*lip - backing_fit, inner_w - 2*lip_gap - 2*lip - backing_fit, backing_t, backing_fit);
}

module lid(kind = "solid") {
  difference() {
    union() {
      rbox(outer_l, outer_w, lid_t, corner_r);
      // lip that fits inside the walls
      translate([wall + lip_gap, wall + lip_gap, lid_t]) difference() {
        cube([inner_l - 2*lip_gap, inner_w - 2*lip_gap, lip_h]);
        translate([lip, lip, -1]) cube([inner_l - 2*lip_gap - 2*lip, inner_w - 2*lip_gap - 2*lip, lip_h + 2]);
      }
      // grip ridges, three on each long side, tapered so the lid starts on easily
      for (fx = [0.2, 0.5, 0.8]) for (side = [0, 1])
        translate([wall + inner_l*fx,
                   side == 0 ? wall + lip_gap + 1 - grip - lip_gap : outer_w - wall - lip_gap - 1 + grip + lip_gap,
                   lid_t])
          intersection() {
            cylinder(h = lip_h, r1 = 1, r2 = 1 - grip);
            translate([-2, side == 0 ? -2 + 1 : -1, 0]) cube([4, 2, lip_h]);
          }
    }
    // Seeburg logo engraved in the top (seeburg_logo.svg must sit beside this file)
    if (kind == "solid" && logo_d > 0) translate([outer_l/2, outer_w/2, logo_d]) rotate([180, 0, 0])
      linear_extrude(logo_d + 1) resize([logo_w, 0], auto = true)
        import("seeburg_logo.svg", center = true);
    // cut-through logo: full shape through the face, bridged shape through the back
    if (kind == "hole") {
      logo_through(logo_face, -1, lid_t - bridge_t);
      logo_through(logo_back, -1, lid_t + 1);
    }
  }
}

if (part == "base") base();
else if (part == "lid") lid();
else if (part == "hole") lid("hole");
else if (part == "backing") backing();   // already print orientation: flat top down
else {
  base();
  translate([0, outer_w, outer_h + lid_t + 15]) rotate([180, 0, 0]) lid();
}

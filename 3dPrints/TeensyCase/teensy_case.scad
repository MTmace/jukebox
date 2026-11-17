// Case for the Teensy 4.1 on a Treedix screw-terminal breakout board
// (board 66 x 40.6 mm, terminal rows along both long sides).
// Two printed parts:
//   part = "base" : tray with a ledge the board sits on, wire slots along both
//                   long sides, USB opening at one end, two screw ears
//   part = "lid"  : push-fit lid with four posts that hold the board down
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
logo_d    = 0.6;          // how deep the logo is cut into the lid
ledge_w   = 2.2;          // board edge rests on this
inner_l   = board_l + 2*clear;
inner_w   = board_w + 2*clear;
inner_h   = under + board_t + stack_h + 1;
outer_l   = inner_l + 2*wall;
outer_w   = inner_w + 2*wall;
outer_h   = floor_t + inner_h;

// Wires enter the screw terminals from the long sides.
slot_from = floor_t + under + board_t + 0.5;   // bottom of the wire slots
slot_h    = 9.0;
slot_l    = inner_l - 8;

// Micro-USB on the Teensy, at the x = 0 end. Centred across the width;
// move usb_y if your Teensy sits off-centre on the breakout.
usb_y     = 0;
usb_w     = 13;
usb_h     = 9;
usb_z     = floor_t + under + board_t + 8.5;   // Teensy sits on its sockets

ear_l     = 12;           // screw ears at both ends, for #6 wood screws
ear_hole  = 4.2;

post_d    = 5;            // lid posts press on the board's edges
lip       = 1.2;          // lid lip that fits inside the walls
lip_h     = 3;

$fn = 40;

module rbox(l, w, h, r) {
  translate([r, r, 0]) linear_extrude(h) offset(r) square([l - 2*r, w - 2*r]);
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
    // countersink the ear holes
    for (x = [-ear_l/2, outer_l + ear_l/2]) translate([x, outer_w/2, 1.5]) cylinder(d1 = ear_hole, d2 = 8, h = 1.6);
  }
  // ledge the board rests on (all round, under the board edge)
  translate([wall, wall, floor_t]) difference() {
    cube([inner_l, inner_w, under]);
    translate([ledge_w, ledge_w, -1]) cube([inner_l - 2*ledge_w, inner_w - 2*ledge_w, under + 2]);
  }
}

module lid() {
  post_h = inner_h - under - board_t - 0.4;
  difference() {
    union() {
      rbox(outer_l, outer_w, lid_t, corner_r);
      // lip that fits inside the walls
      translate([wall + 0.25, wall + 0.25, lid_t]) difference() {
        cube([inner_l - 0.5, inner_w - 0.5, lip_h]);
        translate([lip, lip, -1]) cube([inner_l - 0.5 - 2*lip, inner_w - 0.5 - 2*lip, lip_h + 2]);
      }
      // posts that press the board onto the ledge (between terminal blocks and corner holes)
      for (x = [wall + clear + 9, outer_l - wall - clear - 9])
        for (y = [wall + clear + 1.2 + post_d/2, outer_w - wall - clear - 1.2 - post_d/2])
          translate([x, y, lid_t]) cylinder(d = post_d, h = post_h);
    }
    // Seeburg logo engraved in the top (seeburg_logo.svg must sit beside this file)
    translate([outer_l/2, outer_w/2, logo_d]) rotate([180, 0, 0])
      linear_extrude(logo_d + 1) resize([logo_w, 0], auto = true)
        import("seeburg_logo.svg", center = true);
  }
}

if (part == "base") base();
else if (part == "lid") lid();   // already print orientation: flat top down, posts up
else {
  base();
  translate([0, outer_w, outer_h + lid_t + 15]) rotate([180, 0, 0]) lid();
}

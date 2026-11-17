// Holder for 13 lever splice connectors (Adafruit 5619, inline 1-in/1-out)
// clipped together side by side, for the keypad wires.
// Measured block of 11 (Andrew): 95.5 wide x 39.4 long (wire direction); 13 = about 112.8
// x 14.75 tall. Open top so the levers work; wires leave both long sides.
//
// The block drops into the tray. A strap across the middle, between the
// levers, has a short peg that goes into the hole on top of each connector,
// and screws down onto the two end walls (M3 x 10 or #4 x 3/8" self-tapping).
//
// part = "fittest"       : tray only 2 connectors wide   } print these two
// part = "strap_fittest" : matching 2-connector strap     } first
// part = "holder"        : the real tray for 13
// part = "strap"         : the real strap for 13
// part = "both"          : preview, strap in place
// Print flat, no supports. The strap prints pegs up.

part = "holder";

count    = 13;
each_w   = 95.5 / 11;     // 8.68 mm per connector: 11 measured 95.5, fit test 2 perfect (13 = about 112.8)
block_w  = count * each_w;
block_l  = 39.4;          // along the wires
block_h  = 14.75;

// ---- groove and hole on top of each connector (Andrew, 2026-10-29) ----
groove_w = 5.5;           // measured: groove across the top for a strap
groove_z = 13.8;          // measured 14.8 (connector bottom to groove floor); Andrew asked 1 mm lower after fit test 2
hole_d   = 2.74;          // measured: round hole in the groove
peg_d    = 2.65;           // peg is a little smaller than the hole
peg_h    = 2.0;           // how deep the peg goes into the hole
hole_y   = 0;             // hole centre offset from the connector's middle, along the wires
hole_x   = 0;             // hole centre offset from the connector's middle, across it

clear_w  = 0.4;           // total extra room across the block
clear_l  = 0.4;           // total extra room along the wires
wall     = 2.4;
floor_t  = 2.0;
side_lip_h = 2.5;         // low lips on the wire sides (keep below the wire holes)
boss_w   = 10;            // screw boss on each end wall, under the strap
boss_t   = 7;             // boss thickness (outward from the wall)
pilot_d  = 2.6;           // pilot hole for the strap screw
strap_w  = groove_w - 0.3; // strap sits in the groove
strap_t  = 3;
screw_d  = 3.4;           // clearance hole in the strap
ear_l    = 12;            // screw ears to fix the tray in the cabinet (#6 wood screws)
ear_hole = 4.2;

fit      = (part == "fittest" || part == "strap_fittest");
n        = fit ? 2 : count;
in_w     = n * each_w + (fit ? 0.15 : clear_w);
in_l     = block_l + clear_l;
out_w    = in_w + 2*wall;
out_l    = in_l + 2*wall;
wall_h   = floor_t + groove_z;        // screw posts level with the groove floor,
groove_d = 0;                         // so the strap is a flat bar with no dip
yc       = out_l / 2;                 // strap centre line

$fn = 40;

module tray() {
  difference() {
    union() {
      cube([out_w, out_l, floor_t]);                          // floor
      for (x = [0, out_w - wall])                             // end walls, tapered
        translate([x, 0, 0]) end_wall();
      for (y = [0, out_l - wall])                             // low wire-side lips
        translate([0, y, 0]) cube([out_w, wall, floor_t + side_lip_h]);
      for (x = [-boss_t, out_w])                              // screw bosses
        translate([x, yc - boss_w/2, 0]) cube([boss_t, boss_w, wall_h]);
      if (!fit)                                               // mounting ears
        for (x = [-boss_t - ear_l, out_w + boss_t]) translate([x, yc - 8, 0])
          difference() {
            cube([ear_l, 16, 3]);
            translate([ear_l/2, 8, -1]) cylinder(d = ear_hole, h = 5);
          }
    }
    for (x = [-boss_t/2, out_w + boss_t/2])                   // strap screw pilots
      translate([x, yc, floor_t + 1]) cylinder(d = pilot_d, h = wall_h);
    // floor window: saves plastic and lets you push the block out from below
    translate([wall + 6, wall + 8, -1]) cube([max(in_w - 12, 2), in_l - 16, floor_t + 2]);
    if (!fit)
      for (x = [-boss_t - ear_l/2, out_w + boss_t + ear_l/2])
        translate([x, yc, 1.5]) cylinder(d1 = ear_hole, d2 = 8, h = 1.6);
  }
}

// End wall: full height only beside the screw post, then sloping down to lip
// height right at the holder's ends, so the levers on the end connectors are free.
module end_wall() {
  low = floor_t + side_lip_h;
  top = boss_w / 2;                     // full height only beside the screw post
  run = yc - top;                       // slope runs all the way to the holder's ends
  rotate([90, 0, 90]) linear_extrude(wall)
    polygon([[0, 0], [out_l, 0], [out_l, low],
             [yc + top + run, low], [yc + top, wall_h],
             [yc - top, wall_h], [yc - top - run, low], [0, low]]);
}

// Strap, modelled in place (bottom face on the connector tops).
module strap() {
  difference() {
    union() {
      translate([-boss_t, yc - strap_w/2, wall_h]) cube([out_w + 2*boss_t, strap_w, strap_t]);
      // the part between the end walls drops into the connectors' groove
      if (groove_d > 0)
        translate([wall + 0.2, yc - strap_w/2, wall_h - groove_d])
          cube([in_w - 0.4, strap_w, groove_d + 0.01]);
      for (i = [0 : n - 1])                                   // one peg per connector
        translate([wall + (in_w - n*each_w)/2 + (i + 0.5)*each_w + hole_x,
                   yc + hole_y, wall_h - groove_d - peg_h])
          cylinder(d1 = peg_d - 0.6, d2 = peg_d, h = 0.6 + 0.01);
      for (i = [0 : n - 1])
        translate([wall + (in_w - n*each_w)/2 + (i + 0.5)*each_w + hole_x,
                   yc + hole_y, wall_h - groove_d - peg_h + 0.6])
          cylinder(d = peg_d, h = peg_h - 0.6 + 0.01);
    }
    for (x = [-boss_t/2, out_w + boss_t/2])
      translate([x, yc, wall_h - 1]) cylinder(d = screw_d, h = strap_t + 2);
  }
}

if (part == "holder" || part == "fittest") tray();
else if (part == "strap" || part == "strap_fittest")
  translate([0, 0, wall_h + strap_t]) rotate([180, 0, 0]) translate([0, -2*yc, 0]) strap();  // pegs up (z<0 parts lifted below)
else { tray(); color("orange") strap(); }

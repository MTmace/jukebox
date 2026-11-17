// PiAndHatCase r02 Pi 5 case base with screw ears added (like the Teensy case
// and WAGO box ears), for #6 wood screws, countersunk.
//
// Needs the original case STL beside this file (case_file below).
// Ears sit where nothing plugs in: two on the plain back side, one on the
// front side past the power/HDMI ports. None at the ends: the SD card slot is
// at one end and the USB/Ethernet plugs at the other.
// Print as exported (bottom on the bed), same as the original case.

case_file = "PiAndHatCase-r02a - PI5-Case.stl";

ear_l    = 12;      // how far each ear sticks out from the wall
ear_w    = 16;
ear_t    = 4;
ear_r    = 3;       // rounded outer corners
ear_hole = 4.2;     // #6 wood screw
sink_d   = 8.4;     // countersink top diameter
overlap  = 1.5;     // ear runs this far into the wall

case_w   = 63.0;    // outside width of the case (y)

// [x position along the case, side]: side 0 = front (ports side, y = 0), 1 = back
ears = [[14, 1], [83, 1], [80, 0]];

$fn = 40;

module ear_shape() {   // ear pointing in -y from y = overlap
  translate([-ear_w/2, -ear_l, 0])
    linear_extrude(ear_t) offset(r = ear_r) offset(delta = -ear_r)
      square([ear_w, ear_l + overlap + ear_r]);
}

module place(e) {
  if (e[1] == 0) translate([e[0], 0, 0]) children();
  else translate([e[0], case_w, 0]) mirror([0, 1, 0]) children();
}

difference() {
  union() {
    import(case_file, convexity = 10);
    // ears, trimmed so nothing pokes inside the wall
    for (e = ears) place(e) intersection() {
      ear_shape();
      translate([-50, -50, -1]) cube([100, 50 + overlap, ear_t + 2]);
    }
  }
  for (e = ears) place(e) translate([0, -ear_l/2, 0]) {
    translate([0, 0, -1]) cylinder(d = ear_hole, h = ear_t + 2);
    translate([0, 0, ear_t - 1.6]) cylinder(d1 = ear_hole, d2 = sink_d, h = 1.61);
  }
}

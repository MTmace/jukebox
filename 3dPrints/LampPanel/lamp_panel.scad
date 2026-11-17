// Selection number lamps: printed panel that holds the 12 mm bullet LEDs
// (ALITOVE WS2811 bullets) behind the 22 numbers.
//
// Print orientation is given for each part below (the hug parts and halves go back face down).
//
// Full panel: 14.5" x 2" (368.3 x 50.8 mm). This file first makes a small
// TEST PIECE with four holes of slightly different sizes, so you can find
// which one the bullet snaps into best before printing the whole panel.
//
//   part = "half1" / "half2" -> the two halves of the full panel (print these)
//   part = "splice"          -> 2 splice bars to glue across the joint on the back
//   part = "jointtest"       -> 50 mm of each half at the joint, to check the fit
//   part = "panel"           -> both halves together, for a preview

part = "hug";        // "test" = 4 hole sizes, "thin" = 2 thinned holes,
                     // "clip" = 5 holes, walls on the back (outer housing; too far back)
                     // "hug" = 5 holes, walls on the front hugging the inner housing

// ---- sizes in mm ----
PANEL_L   = 368.3;   // 14.5"
PANEL_H   = 50.8;    // 2"
PLATE     = 2.0;     // plate thickness the bullet's clips grip
LIP       = 6;       // stiffening rim on the back, depth
LIP_W     = 2.4;     // rim wall width

TEST_L    = 80;                       // test piece length
TEST_HOLES = [11.8, 12.0, 12.2, 12.4]; // hole sizes to try
TEST_LABELS = ["11.8", "12.0", "12.2", "12.4"];

HOLE      = 12.0;    // hole size that fit best (Andrew, 2026-10-09)
PITCH     = 15.6;    // centre to centre: one 13.8 mm cell + one 1.8 mm wall (19.05 was too far apart)

// Thinner ring around each hole, cut from the back so the front stays flat,
// so the bullet's clips can reach past the plastic and catch.
RING      = 15;      // diameter of the thinned area (smaller than PITCH so rings stay apart)
THIN_TEST = [1.2, 1.6];   // plate thickness left around each hole in the "thin" test
THIN      = 1.2;     // thickness used on the full panel (1.2 fit best, 2026-10-09)

// Clip version: the short ends are open and the two long walls hug the
// plastic housing, with a snap ridge on the inside of each wall.
HOUSING_H = 50.8;    // housing height the walls hug (inside gap between walls)
WALL      = 2.0;     // long wall thickness (thin enough to flex)
WALL_D    = 10;      // how far the walls reach back past the plate
RIDGE     = 0.8;     // how far the snap ridge sticks in from each wall
CLIP_HOLES = 5;      // holes in the clip test piece
THIN_L    = 50;      // "thin" test piece length

$fn = 96;

module plate(l, h) {
  difference() {
    union() {
      cube([l, h, PLATE]);
      // rim on the back so the thin plate stays flat
      difference() {
        cube([l, h, PLATE + LIP]);
        translate([LIP_W, LIP_W, -1]) cube([l - 2*LIP_W, h - 2*LIP_W, PLATE + LIP + 2]);
      }
    }
  }
}

module test_piece() {
  n = len(TEST_HOLES);
  step = TEST_L / n;
  difference() {
    plate(TEST_L, PANEL_H);
    for (i = [0 : n - 1]) {
      x = step * (i + 0.5);
      translate([x, PANEL_H * 0.55, -1]) cylinder(d = TEST_HOLES[i], h = PLATE + 2);
      // hole size engraved on the back, under each hole
      translate([x, 9, PLATE - 0.6])
        linear_extrude(1)
          text(TEST_LABELS[i], size = 4.2, halign = "center", valign = "center",
                 font = "Liberation Sans:style=Bold");
    }
  }
}

module thin_hole(t) {
  translate([0, 0, -1]) cylinder(d = HOLE, h = PLATE + 2);
  translate([0, 0, t]) cylinder(d = RING, h = PLATE);
}

module thin_test() {
  difference() {
    plate(THIN_L, PANEL_H);
    for (i = [0 : len(THIN_TEST) - 1]) {
      x = THIN_L / 2 + (i - 0.5) * PITCH;
      translate([x, PANEL_H * 0.55, 0]) thin_hole(THIN_TEST[i]);
      translate([x, 9, PLATE - 0.6])
        linear_extrude(1)
          text(str(THIN_TEST[i]), size = 4.2, halign = "center", valign = "center",
               font = "Liberation Sans:style=Bold");
    }
  }
}

// Long wall with a snap ridge along its tip, on the inside. The ridge has a
// 45 degree underside so it prints face down with no supports, and a sloped
// tip so it slides over the housing edge and clicks behind it.
module clip_wall(l, inside_dir) {
  cube([l, WALL, PLATE + WALL_D]);
  // ridge profile in the y-z plane, extruded along x
  rotate([90, 0, 90]) linear_extrude(l)
    polygon(inside_dir > 0
      ? [[WALL, PLATE + WALL_D - 2.4], [WALL + RIDGE, PLATE + WALL_D - 1.6],
         [WALL + RIDGE, PLATE + WALL_D - 1.0], [WALL, PLATE + WALL_D]]
      : [[0, PLATE + WALL_D - 2.4], [-RIDGE, PLATE + WALL_D - 1.6],
         [-RIDGE, PLATE + WALL_D - 1.0], [0, PLATE + WALL_D]]);
}

module clip_panel(l, holes) {
  h = HOUSING_H + 2 * WALL;
  difference() {
    union() {
      cube([l, h, PLATE]);
      clip_wall(l, 1);                                    // bottom wall
      translate([0, h - WALL, 0]) clip_wall(l, -1);       // top wall (ridge points down)
    }
    for (i = [0 : holes - 1])
      translate([l / 2 + (i - (holes - 1) / 2) * PITCH, h / 2, 0]) thin_hole(THIN);
  }
}

// "hug" version (Andrew, 2026-10-09): the plate sits right against the back of
// the inner housing (26.5 mm tall, 1.8 mm walls, holes 13.8 mm inside) and its
// two long walls reach FORWARD over the housing's top and bottom (3.7 mm deep), so the bulbs
// sit right behind the holes. The thin ring is cut from the front, so it prints
// back face down with the walls pointing up and no supports.
INNER_H   = 26.5;    // inner housing height, outside top to outside bottom
FIT       = 0.3;     // extra gap so it slides on
HOUSING_D = 3.7;     // how far the housing sticks back (Andrew, 2026-10-10)
CATCH     = HOUSING_D + 0.1;   // ridge starts just past the housing edge
HUG_RIDGE = 0.6;     // snap ridge on the inside of each wall tip
HUG_D     = CATCH + 1.4;       // wall reach: ends just past the ridge

module hug_wall(l, inside_dir) {
  cube([l, WALL, PLATE + HUG_D]);
  rotate([90, 0, 90]) linear_extrude(l)
    polygon(inside_dir > 0
      ? [[WALL, PLATE + CATCH], [WALL + HUG_RIDGE, PLATE + CATCH + 0.6],
         [WALL + HUG_RIDGE, PLATE + CATCH + 0.8], [WALL, PLATE + HUG_D]]
      : [[0, PLATE + CATCH], [-HUG_RIDGE, PLATE + CATCH + 0.6],
         [-HUG_RIDGE, PLATE + CATCH + 0.8], [0, PLATE + HUG_D]]);
}

// Built back face down: z = 0 is the back, the walls point forward (+z).
module hug_panel(l, holes) {
  h = INNER_H + FIT + 2 * WALL;
  difference() {
    union() {
      cube([l, h, PLATE]);
      hug_wall(l, 1);
      translate([0, h - WALL, 0]) hug_wall(l, -1);
    }
    for (i = [0 : holes - 1])
      translate([l / 2 + (i - (holes - 1) / 2) * PITCH, h / 2, 0]) {
        translate([0, 0, -1]) cylinder(d = HOLE, h = PLATE + 2);
        translate([0, 0, THIN]) cylinder(d = RING, h = PLATE);
      }
  }
}

// ---- Full panel (Andrew, 2026-10-10: the hug test fits perfectly) ----
// One row of 22 holes (1 2, then 0-9, then 0-9) at the test's spacing, on a
// 14.5" panel, split in two halves for a Bambu P1S (256 mm bed). The halves
// join with two dovetails that press together through the plate; the housing
// they clip onto keeps them in line. The ends are open, so the panel can
// slide along the housing to line the holes up.
FULL_HOLES = 22;
FULL_L     = PANEL_L;          // 368.3 mm
// Joint v2 (Andrew, 2026-10-10: v1 was loose even glued): tighter, longer
// dovetails, plus two splice bars glued across the joint on the back.
DOVE_NECK  = 3;                // dovetail width at the joint
DOVE_HEAD  = 5.4;              // dovetail width at its end (band is 5.9 mm)
DOVE_LEN   = 7;                // how far it reaches into the other half
DOVE_GAP   = 0.05;             // clearance each side: a firm press fit (was 0.15)
SPLICE_L   = 44;               // splice bar length, centred on the joint
SPLICE_T   = 2.0;              // splice bar thickness (sticks out the back)
SPLICE_IN  = 8.3;              // splice bar inner edge, from the hole centre line
                               // (clear of each bulb's 12 mm body plus room for its clips)

function full_h() = INNER_H + FIT + 2 * WALL;

module full_whole() { hug_panel(FULL_L, FULL_HOLES); }

// The joint sits midway between hole 11 and hole 12. Dovetails go in the solid
// bands above and below the holes, clear of the thinned rings.
module dovetails(grow = 0) {
  h = full_h();
  band = (h - 2 * WALL - RING) / 2;          // solid band height between ring and wall
  for (y = [WALL + band / 2, h - WALL - band / 2])
    translate([FULL_L / 2, y, -1])
      linear_extrude(PLATE + 2)
        offset(delta = grow)
          polygon([[-0.01, -DOVE_NECK / 2], [DOVE_LEN, -DOVE_HEAD / 2],
                   [DOVE_LEN, DOVE_HEAD / 2], [-0.01, DOVE_NECK / 2]]);
}

module half(n) {
  h = full_h();
  if (n == 1) {
    intersection() { full_whole(); translate([-1, -1, -1]) cube([FULL_L / 2 + 1, h + 2, 50]); }
    intersection() { dovetails(); translate([0, 0, 0]) cube([FULL_L, h, PLATE]); }
  } else {
    difference() {
      intersection() { full_whole(); translate([FULL_L / 2, -1, -1]) cube([FULL_L / 2 + 1, h + 2, 50]); }
      dovetails(DOVE_GAP);
    }
  }
}

// Splice bar: glue one across the joint in each band on the back (above and
// below the holes), centred on the joint, 2 mm in from the long edge. Printed flat.
function splice_w() = full_h() / 2 - WALL - SPLICE_IN;
module splice() { cube([SPLICE_L, splice_w(), SPLICE_T]); }
module splices_in_place() {
  h = full_h();
  for (y = [WALL, h / 2 + SPLICE_IN])
    translate([FULL_L / 2 - SPLICE_L / 2, y, -SPLICE_T]) splice();
}

if (part == "test") test_piece();
else if (part == "thin") thin_test();
else if (part == "hug") hug_panel(CLIP_HOLES * PITCH + 6, CLIP_HOLES);
else if (part == "clip") clip_panel(CLIP_HOLES * PITCH + 6, CLIP_HOLES);
else if (part == "half1") half(1);
else if (part == "half2") translate([-FULL_L / 2, 0, 0]) half(2);
else if (part == "splice") { splice(); translate([0, splice_w() + 4, 0]) splice(); }   // print 1 set
else if (part == "jointtest") {   // 50 mm of each side of the joint, to check the fit quickly
  translate([-FULL_L / 2 + 25, 0, 0]) intersection() {
    half(1); translate([FULL_L / 2 - 25, -1, -1]) cube([25 + DOVE_LEN + 1, full_h() + 2, 50]); }
  translate([-FULL_L / 2 + 5, full_h() + 6, 0]) intersection() {
    half(2); translate([FULL_L / 2 - 1, -1, -1]) cube([26, full_h() + 2, 50]); }
}
else { half(1); color("orange") half(2); color("green") splices_in_place(); }   // "panel": both halves together

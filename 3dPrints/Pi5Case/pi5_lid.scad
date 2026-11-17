// Seeburg logo lids for the PiAndHatCase Pi 5 case (cover r02c).
//
// The original cover's rim (the part that drops into the case and clicks onto
// the wall bumps) is used exactly as it is; only the vented top plate is
// replaced with a new plate carrying the Seeburg logo.
//
//   part = "solid"    : solid top, logo engraved 0.6 mm into the face (like the Teensy case lid)
//   part = "hole"     : logo cut right through the top; a shallow pocket on the
//                       underside takes the backing piece
//   part = "backing"  : thin plate in a second colour that presses into the pocket
//                       behind the logo, flush with the underside
//   part = "logotest" : the logo strip of the "hole" lid plus a matching strip of backing
//   part = "pintest"  : just the back edge of the lid round the pin hole (with its rim),
//                       to check the hole lines up with the header before printing a whole lid
//   part = "spacer"   : two spacer tubes that hold the Pixel Shifter board off the lid
//
// pin_hole = true adds a slot over the 40-pin header (through the DAC HAT's
// pass-through header) so a plug can reach the LED data pins from above.
//
// Needs beside this file: the original cover STL (cover_file below),
// seeburg_logo.svg and seeburg_logo_cut.svg.
// Everything is in print orientation: logo face down on the bed, rim up. No supports.

part      = "solid";
cover_file= "PiAndHatCase-r02c - Cover.stl";
cover_z   = 24.5;        // the cover STL sits this high off zero; moved down to the bed

plate_t   = 3.0;         // top plate thickness (same as the original)
chamfer   = 1.0;         // 45 degree chamfer round the face edge (same as the original)
logo_w    = 70.2;        // logo width (the bridges in seeburg_logo_cut.svg are made for this width)
logo_face = "seeburg_logo.svg";      // hole lid: shape cut through the face
logo_back = "seeburg_logo_cut.svg";  // hole lid: shape cut through the back (bridges for the B and R centres)
// v2 hole lid (stronger letters for small lids): set both to a seeburg_logo_print_<w>.svg
// made by make_logo_print.py for the same logo_w; its bridges run the full thickness.
engrave   = 0.6;         // solid lid: how deep the logo is cut into the face
bridge_t  = 1.0;         // hole lid: the B and R centres hang on bridges this thick, set back from the face
pocket_d  = 1.0;         // hole lid: pocket depth on the underside = backing thickness
pocket_m  = 3.0;         // pocket margin round the logo
pocket_r  = 2.0;         // pocket corner radius
fit       = 0.15;        // total clearance round the backing in the pocket
grip      = false;      // true: colour plate gets grip ribs (press fit that stays in)

// Pin access slot. Numbers below are for pin_side = "solid" (lid frame, face
// down, rim side without gaps at y = 0 over the case's back wall, where the GPIO
// header sits); "gaps" turns the slot 180 degrees round the lid centre.
// Pi in the case: mounting holes at case x 9.66 / 67.66, y 7 / 56; the lid sits
// at case x + 2.86, y + 1.95 and is turned over (lid y = 61.05 - case y).
// Header pin 1 is at the SD-card end; pin 2n is on the outer row, column n.
// Pins 32 (GPIO 12, LED data) and 34 (GND): lid x 49.8 / 52.3, y 3.8 (outer row).
// The lid fits either way round. pin_side picks which long side gets the slot:
//   "gaps"  : slot on the rim side with the two gaps. Fit the lid with the gaps
//             over the header (back wall); the logo then reads right from the
//             front (power/HDMI side), as with the earlier logo lids.
//   "solid" : slot on the rim side without gaps (lid the other way round).
pin_hole  = false;
pin_side  = "gaps";
pin_x0    = 43.0;  pin_x1 = 59.0;   // slot ends: shows pins 28-38 (outer) and 27-37 (inner)
pin_y0    = 2.0;   pin_y1 = 8.5;    // from the rim's inside face to past the inner row
pin_r     = 1.0;                    // slot corner radius
// pin_all = true: the slot shows the whole 40-pin header (pins 1-40) instead.
pin_all   = false;
pin_pitch = 2.54;
pin32_x   = 49.8;                   // lid x of header column 16 (pins 31/32)

// shifter = true: two screw holes for the Adafruit Pixel Shifter (product 6066,
// 25.4 x 15.24 mm, M2.5 holes at board x 12.7, y 2.54 and 12.7) on the face,
// between the slot and the logo, with a nut pocket under each hole; the logo
// moves away from the slot by logo_dy to make room. Board: M2.5 x 8 screw from
// the top, through the board, a spacer (part = "spacer") and the lid, into an
// M2.5 nut pressed into the pocket from inside the lid.
shifter   = false;
sh_l = 25.4;  sh_w = 15.24;
sh_x0     = 33.3;                   // board corner, lid x (input terminals at the pin-1 end)
sh_y0     = 10.0;                   // board corner, lid y (just past the slot)
sh_holes  = [[12.7, 2.54], [12.7, 12.7]];
sh_hole_d = 2.8;                    // M2.5 clearance
nut_af    = 5.3;   nut_t = 2.2;     // M2.5 nut pocket: across flats (+ clearance), depth
spacer_h  = 4.0;   spacer_od = 5.5; // spacer: clears the terminal pins under the board
logo_dy   = 0;                      // move the logo away from the slot (11.5 with shifter)

lid_l = 92.1;  lid_w = 59.1;
cx = lid_l/2;  cy = lid_w/2;
logo_h = logo_w * 310 / 2138;
pocket_l = logo_w + 2*pocket_m;
pocket_w = logo_h + 2*pocket_m;

include <pi5_lid_outline.scad>   // outline_pts: outer edge of the original plate

module outline2d(inset = 0) offset(delta = -inset) polygon(outline_pts);

module plate() {
  hull() {
    linear_extrude(0.01) outline2d(chamfer);
    translate([0, 0, chamfer]) linear_extrude(plate_t - chamfer) outline2d(0);
  }
}

// original rim only (everything above the plate)
module rim() {
  intersection() {
    translate([0, 0, -cover_z]) import(cover_file, convexity = 10);
    translate([-5, -5, plate_t - 0.01]) cube([lid_l + 10, lid_w + 10, 20]);
  }
}

// logo cut from z0 to z1, mirrored because it prints face down: reads correctly once the lid is turned over
module logo_cut(file, z0, z1) {
  translate([cx, lcy, z0]) mirror([1, 0, 0])
    linear_extrude(z1 - z0) resize([logo_w, 0], auto = true) import(file, center = true);
}

module rounded_rect(l, w, r) {
  translate([-l/2, -w/2]) offset(r = r) offset(delta = -r) square([l, w]);
}

module pin_slot() {
  if (pin_side == "gaps") translate([lid_l, lid_w, 0]) rotate([0, 0, 180]) pin_slot0();
  else pin_slot0();
}
module pin_slot0() {
  x0 = pin_all ? pin32_x - 15*pin_pitch - 2.3 : pin_x0;   // column 1 (pins 1/2) ...
  x1 = pin_all ? pin32_x +  4*pin_pitch + 2.3 : pin_x1;   // ... to column 20 (pins 39/40)
  translate([(x0 + x1)/2, (pin_y0 + pin_y1)/2, -1]) linear_extrude(plate_t + 2)
    rounded_rect(x1 - x0, pin_y1 - pin_y0, pin_r);
  if (shifter) for (h = sh_holes) translate([sh_x0 + h[0], sh_y0 + h[1], 0]) {
    translate([0, 0, -1]) cylinder(d = sh_hole_d, h = plate_t + 2, $fn = 24);
    // nut pocket from the inside (prints as a recess in the top: no overhang)
    translate([0, 0, plate_t - nut_t]) cylinder(d = nut_af / cos(30), h = nut_t + 1, $fn = 6);
  }
}
// logo position: moved away from the slot side by logo_dy
lcy = cy + (pin_side == "gaps" ? -logo_dy : logo_dy);

module lid(kind) {
  difference() {
    union() { plate(); rim(); }
    if (pin_hole) pin_slot();
    if (kind == "solid") logo_cut("seeburg_logo.svg", -1, engrave);
    if (kind == "hole") {
      logo_cut(logo_face, -1, plate_t - pocket_d - bridge_t);
      logo_cut(logo_back, -1, plate_t + 1);
      translate([cx, lcy, plate_t - pocket_d]) linear_extrude(pocket_d + 1)
        rounded_rect(pocket_l, pocket_w, pocket_r);
    }
  }
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

module backing() {
  linear_extrude(pocket_d) rounded_rect(pocket_l - fit, pocket_w - fit, pocket_r - fit/2);
  if (grip) translate([-(pocket_l - fit)/2, -(pocket_w - fit)/2, 0]) grip_ribs(pocket_l - fit, pocket_w - fit, pocket_d, fit);
}

if (part == "solid") lid("solid");
else if (part == "hole") lid("hole");
else if (part == "backing") translate([cx, cy, 0]) backing();
else if (part == "spacer") for (i = [0, 1]) translate([i * (spacer_od + 4), 0, 0])
  difference() { cylinder(d = spacer_od, h = spacer_h, $fn = 40);
                 translate([0, 0, -1]) cylinder(d = sh_hole_d, h = spacer_h + 2, $fn = 24); }
else if (part == "pintest") {
  intersection() {
    lid("solid_plain");
    if (pin_side == "gaps")
      translate([lid_l - pin_x1 - 12, lid_w - pin_y1 - 6, -1]) cube([pin_x1 - pin_x0 + 24, 5 + pin_y1 + 6, 20]);
    else
      translate([pin_x0 - 12, -5, -1]) cube([pin_x1 - pin_x0 + 24, 5 + pin_y1 + 6, 20]);
  }
}
else if (part == "logotest") {
  intersection() {
    lid("hole");
    translate([cx - pocket_l/2 - 3, cy - pocket_w/2 - 3, 0]) cube([pocket_l + 6, pocket_w + 6, plate_t]);
  }
  translate([cx, cy - pocket_w - 6, 0]) backing();
}

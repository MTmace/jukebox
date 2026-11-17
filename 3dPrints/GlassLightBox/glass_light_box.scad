// Glass light box: a printed trough that clips onto the BACK of the original
// Seeburg title-strip panel, behind one strip of coloured glass (one above the
// selection numbers, one below). A 5 V LED strip is taped to the floor of the
// box and shines through the glass from about 2" away, so the light spreads out
// like the old tube lighting instead of showing hot dots.
//
//   floor (strip taped here)                open face (toward the glass)
//   ________________________________        _______
//   |                              |       |       |  <- skirt hugs the
//   |  ==== LED strip ====         |  ...  |       |     panel's two walls
//
// Cross-section (looking along the box):
//
//        skirt |       |  skirt      <- slides over the outside of the
//              |_     _|               side channel's two walls
//              | \   / |  <- ledge: the channel walls stop here
//              |       |
//              |       |  <- 2" of depth for the light to spread
//              |_[==]_|  <- LED strip on the floor, in a shallow guide
//
// Print orientation: FLOOR DOWN, open side up. No supports.
// White or natural PLA/PETG reflects the most light.
//
//   part = "fittest" -> 40 mm long, short walls: checks the clip fit (print first)
//   part = "half1"   -> first half (wire slot in the outer end)
//   part = "half2"   -> second half (wire slot in the outer end)
//   part = "sleeve"  -> clip that slides over the joint (print 1 per box)
//   part = "box"     -> both halves together, for a preview

part = "half1";

// ---- sizes in mm (inches in comments) ----
BOX_L    = 355.6;   // 14" total length (two halves of 177.8)
CH_OUT   = 38.1;    // 1.5": outside width of the panel's side channel (wall to wall,
                    //   outside faces). This is the size the skirt hugs. MEASURE.
FIT      = 0.4;     // extra gap so the skirt slides on
WALL     = 2.0;     // side wall thickness (thin enough for the skirt to flex)
FLOOR    = 2.4;     // floor thickness
DEPTH    = 50.8;    // 2": floor bottom to where the panel's walls stop (the ledge)
SKIRT    = 6;       // how far the skirt reaches over the panel's walls
RIDGE    = 0.6;     // grip ridge inside each skirt tip
LEDGE    = 1.6;     // how far the stop ledge sticks in from each wall
LEDGE_H  = 2;       // ledge height (with a 45 degree chamfer underneath)

STRIP_W  = 12.5;    // LED strip guide width (10 mm strips + room; 12 mm strips fit)
STRIP_D  = 0.6;     // guide depth (flat bottom, tape still sits flat)
SLOT_W   = 14;      // wire slot in the outer end wall, width
SLOT_H   = 8;       // wire slot height above the floor

SLEEVE_L = 40;      // joint sleeve length
SLEEVE_T = 1.6;     // sleeve wall thickness
SLEEVE_FIT = 0.25;  // gap between sleeve and box

FIT_L    = 40;      // fit test length
FIT_H    = 14;      // fit test height below the ledge

// ---- derived ----
IN_W   = CH_OUT + FIT;          // inside width at the skirt
OUT_W  = IN_W + 2*WALL;         // outside width of the box
HALF_L = BOX_L / 2;
TOTAL_H = DEPTH + SKIRT;

$fn = 48;

// The basic trough: floor, two long walls, ledge and skirt. Open ends.
// depth = floor bottom to the ledge, length along X.
module trough(len, depth) {
  difference() {
    cube([len, OUT_W, depth + SKIRT]);
    // inside space
    translate([-1, WALL, FLOOR]) cube([len + 2, IN_W, depth + SKIRT]);
    // LED strip guide in the floor
    translate([-1, (OUT_W - STRIP_W)/2, FLOOR - STRIP_D]) cube([len + 2, STRIP_W, STRIP_D + 0.01]);
  }
  // stop ledges (the panel's walls butt against these), chamfered underneath
  for (side = [0, 1]) {
    y0 = side == 0 ? WALL : WALL + IN_W;
    dir = side == 0 ? 1 : -1;
    translate([0, y0, 0])
      rotate([90, 0, 90])
        linear_extrude(len)
          polygon([[0, depth - LEDGE_H - LEDGE], [dir*LEDGE, depth - LEDGE_H],
                   [dir*LEDGE, depth], [0, depth]]);
  }
  // grip ridges at the skirt tips (chamfered both ways so they print and slide)
  for (side = [0, 1]) {
    y0 = side == 0 ? WALL : WALL + IN_W;
    dir = side == 0 ? 1 : -1;
    translate([0, y0, 0])
      rotate([90, 0, 90])
        linear_extrude(len)
          polygon([[0, depth + SKIRT - 3*RIDGE - 0.8], [dir*RIDGE, depth + SKIRT - 0.8 - RIDGE],
                   [dir*RIDGE, depth + SKIRT - 0.8], [0, depth + SKIRT - 0.2]]);
  }
}

// End wall up to the ledge (the skirt part stays open so it can pass the
// panel's own end walls). slot = wire slot at the floor.
module end_wall(x, slot) {
  translate([x, 0, 0])
    difference() {
      cube([WALL, OUT_W, DEPTH]);
      if (slot)
        translate([-1, (OUT_W - SLOT_W)/2, FLOOR - STRIP_D]) cube([WALL + 2, SLOT_W, SLOT_H]);
    }
}

module half(outer_end_at_zero) {
  trough(HALF_L, DEPTH);
  end_wall(outer_end_at_zero ? 0 : HALF_L - WALL, true);
}

module sleeve() {
  // U-shaped clip that slides over the outside of the joint, up to the ledge
  // height. Glue the halves end to end, then slide this over the joint.
  w = OUT_W + 2*SLEEVE_FIT;
  h = DEPTH - 4;   // stays below the skirt so it doesn't stop the skirt flexing
  difference() {
    cube([SLEEVE_L, w + 2*SLEEVE_T, h + SLEEVE_T]);
    translate([-1, SLEEVE_T, SLEEVE_T]) cube([SLEEVE_L + 2, w, h + 1]);
  }
}

module fittest() {
  trough(FIT_L, FIT_H);
}

if (part == "half1") half(true);
else if (part == "half2") half(false);
else if (part == "sleeve") sleeve();
else if (part == "fittest") fittest();
else if (part == "box") {
  color("white") half(true);
  color("white") translate([HALF_L, 0, 0]) half(false);
  color("grey") translate([HALF_L - SLEEVE_L/2, -SLEEVE_T - SLEEVE_FIT, -SLEEVE_T]) sleeve();
}

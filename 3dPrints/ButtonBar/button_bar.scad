// Glass button bar for the Seeburg Firestar jukebox
// 4 x Kailh Choc v1 low-profile switches in a slim tray that sticks to the
// glass (black border area) with VHB tape. Two printed parts:
//   part = "tray"  : floor + walls, ribbon slot at one end
//   part = "plate" : top plate the switches clip into
// Render each one (F6) and export STL. Print both flat side down.

part = "both";          // "tray", "plate" or "both" (preview)

// ---- layout -------------------------------------------------------------
pitch     = 18.5;       // centre-to-centre of keys (Choc caps are ~17.5 x 16.5)
group_gap = 8;          // extra space between the arrow pair and Genre/Random
// key x positions: [ <, >, Genre, Random ]
keys = [0, pitch, 2*pitch + group_gap, 3*pitch + group_gap];

margin    = 7;          // wall-to-key-edge room at each end
depth     = 26;         // front-to-back size of the bar
wall      = 2.0;
floor_t   = 1.6;        // this face sits on the glass
cavity_h  = 6.0;        // room under the plate for switch bodies, pins and solder
plate_t   = 1.3;        // Choc v1 clips need a 1.2-1.3 mm plate
cut       = 13.8;       // Choc v1 plate cutout (square)
corner_r  = 3;

slot_w    = 10;         // ribbon exit (6-wire 1.27 mm ribbon is ~7.6 mm wide)
slot_h    = 2.2;

screw_pilot = 1.6;      // M2 self-tapping into the bosses
screw_clear = 2.3;
boss_d      = 5;

span   = keys[3] - keys[0];
length = span + cut + 2*margin + 2*wall;
x0     = wall + margin + cut/2;           // x of first key centre
yc     = depth/2;

boss_pos = [[wall + boss_d/2, wall + boss_d/2],
            [length - wall - boss_d/2, wall + boss_d/2],
            [wall + boss_d/2, depth - wall - boss_d/2],
            [length - wall - boss_d/2, depth - wall - boss_d/2]];

module rbox(l, d, h, r) {
    hull() for (x = [r, l - r], y = [r, d - r]) translate([x, y, 0]) cylinder(r = r, h = h, $fn = 32);
}

module tray() {
    difference() {
        rbox(length, depth, floor_t + cavity_h, corner_r);
        // cavity
        translate([wall, wall, floor_t]) cube([length - 2*wall, depth - 2*wall, cavity_h + 1]);
        // ribbon slot, right end, at floor level
        translate([length - wall - 1, yc - slot_w/2, floor_t]) cube([wall + 2, slot_w, slot_h]);
    }
    // screw bosses
    for (p = boss_pos) translate([p[0], p[1], 0]) difference() {
        cylinder(d = boss_d, h = floor_t + cavity_h, $fn = 32);
        translate([0, 0, floor_t]) cylinder(d = screw_pilot, h = cavity_h + 1, $fn = 16);
    }
}

module plate() {
    difference() {
        rbox(length, depth, plate_t, corner_r);
        for (k = keys) translate([x0 + k - cut/2, yc - cut/2, -1]) cube([cut, cut, plate_t + 2]);
        for (p = boss_pos) translate([p[0], p[1], -1]) cylinder(d = screw_clear, h = plate_t + 2, $fn = 16);
    }
}

if (part == "tray") tray();
else if (part == "plate") plate();
else { tray(); color("silver") translate([0, 0, floor_t + cavity_h + 0.01]) plate(); }

echo(str("Bar size: ", length, " x ", depth, " mm, ",
         floor_t + cavity_h + plate_t, " mm tall before switches (~", floor_t + cavity_h + plate_t + 8, " mm with Choc caps)"));

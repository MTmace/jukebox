// Power inlet cover plate for the Seeburg cabinet.
// Covers the old 91 x 41 mm plug hole and holds an IEC C14 inlet
// with fuse and red rocker switch. The inlet has no snap clips: its two
// ear screws hold it. The PLATE has 4 clips on its lip that click
// behind the metal panel.
//
// part = "plate"     full plate
// part = "inlettest" small piece: inlet cutout and ear holes only
// part = "holetest"  thin frame: checks the lip fit, the clips and the
//                    2 screw holes
//
// The cabinet panel is 2 mm steel. The hole stands upright, with an old
// screw hole 6.7 mm out from the middle of each side. The plate uses the
// top and bottom ones (the inlet's ear screws would clash with the side
// ones), and the clips hold it flat.
// The model's X axis is the hole's long (upright) direction.
//
// Print front face DOWN on the bed (the locating lip points up).
// All inlet numbers come from the listing - MEASURE THE REAL PART.

part = "plate";
LOGO = "full";     // "full" Seeburg logo above the inlet, "s" = just the S
                   // swoosh top left, "none"

// ---- cabinet hole -------------------------------------------------
HOLE_W   = 91;     // old plug hole, long side (upright)
HOLE_H   = 41;     // old plug hole, short side
SCREW_OUT = 6.7;   // cabinet screw hole centre, out from the hole edge
LIP_FIT  = 0.1;    // lip is this much smaller than the hole, all round
LIP_WALL = 3;      // locating lip wall
LIP_D    = 8;      // how far the lip reaches into the hole
PANEL_T  = 2;      // cabinet panel (steel) thickness

// ---- logo (engraved into the front face) --------------------------
LOGO_FILE  = "seeburg_logo.svg";
LOGO_S_FILE = "seeburg_s.svg";   // just the S swoosh, cut from the logo
LOGO_DEPTH = 0.8;
LOGO_FULL_W = 56;  // full logo width (about 8 mm tall)
LOGO_S_W   = 24;   // S swoosh width (about 6 mm tall)
LOGO_X     = 36.5; // logo centre, up from the plate centre (between the
                   // inlet flange and the top screw)
LOGO_S_Y   = -18;  // S swoosh centre, left of the plate centre

// ---- clips on the lip -----------------------------------------------
CLIP_X   = 12;     // clip centres, +/- along the long side
CLIP_W   = 8;      // clip width
CLIP_T   = 1.6;    // clip thickness (thinner than the lip so it flexes)
CLIP_SLOT = 1;     // slot each side of a clip
HOOK     = 0.7;    // how far the hook sticks out past the lip
HOOK_GAP = 0.2;    // play between the hook and the back of the panel

// ---- plate --------------------------------------------------------
MARGIN_L = 15.5;   // plate overlap past the hole, top and bottom
MARGIN_S = 14;     // plate overlap past the hole, left and right
PLATE_T  = 6;      // plate thickness
CORNER_R = 6;
EDGE_CH  = 1.2;    // chamfer on the front edge

// cabinet screws: the old #8 hex-head sheet-metal screws (1/4" driver)
CAB_D    = 4.8;    // clearance hole
CAB_CH   = 0.8;    // small chamfer on the hole at the front

// ---- inlet (listing values) ---------------------------------------
CUT_W    = 47.0;   // panel cutout, long side
CUT_H    = 27.5;   // panel cutout, short side
CUT_FIT  = 0.3;    // added to each cutout size
EAR_PITCH = 40;    // ear screw holes, centre to centre
EAR_PILOT = 2.6;   // M3 self-tapping pilot, threads into the 6 mm plate
BODY_GAP = 3;      // clear space round the body behind the plate

$fn = 64;
eps = 0.01;

PLATE_W = HOLE_W + 2*MARGIN_L;
PLATE_H = HOLE_H + 2*MARGIN_S;
LIP_W   = HOLE_W - 2*LIP_FIT;
LIP_H   = HOLE_H - 2*LIP_FIT;
CW = CUT_W + CUT_FIT;
CH = CUT_H + CUT_FIT;
POCKET_W = CW + 2*BODY_GAP;
POCKET_H = CH + 2*BODY_GAP;

module rrect(w, h, r) {
    offset(r) square([w - 2*r, h - 2*r], center = true);
}

module cab_screw(t) {
    translate([0, 0, -1]) cylinder(d = CAB_D, h = t + 2);
    translate([0, 0, -eps]) cylinder(d1 = CAB_D + 2*CAB_CH, d2 = CAB_D, h = CAB_CH);
}

// old top and bottom holes
cab_pts = [for (sx = [-1, 1]) [sx*(HOLE_W/2 + SCREW_OUT), 0]];
LIP_IN = LIP_W/2 - LIP_WALL;            // inside of the lip, along X
clip_pts = [for (sx = [-1, 1], sy = [-1, 1]) [sx*CLIP_X, sy]];

module lip_ring(h) {
    linear_extrude(h) difference() {
        rrect(LIP_W, LIP_H, 2);
        rrect(LIP_W - 2*LIP_WALL, LIP_H - 2*LIP_WALL, 1);
    }
}

// cut each clip free of the lip and thin it (base = z of the lip root)
module clip_cuts(base) {
    y_out = LIP_H/2;
    for (c = clip_pts) translate([c[0], 0, base]) mirror([0, c[1] < 0 ? 1 : 0, 0]) {
        for (sx = [-1, 1])
            translate([sx*(CLIP_W + CLIP_SLOT)/2 - CLIP_SLOT/2, y_out - LIP_WALL - 1, 0])
                cube([CLIP_SLOT, LIP_WALL + 2, LIP_D + 1]);
        translate([-CLIP_W/2, y_out - LIP_WALL - 1, 0]) cube([CLIP_W, LIP_WALL - CLIP_T + 1, LIP_D + 1]);
    }
}

// the hook: flat catch facing the panel, ramp up to the tip
module clip_hooks(base) {
    y_out = LIP_H/2;
    zc = base + PANEL_T + HOOK_GAP;
    zt = base + LIP_D;
    for (c = clip_pts) translate([c[0], 0, 0]) mirror([0, c[1] < 0 ? 1 : 0, 0])
        rotate([90, 0, 90]) translate([0, 0, -CLIP_W/2]) linear_extrude(CLIP_W)
            polygon([[y_out - 0.5, zc], [y_out + HOOK, zc], [y_out + HOOK, zc + 0.8], [y_out - 0.5, zt - 0.3]]);
}

module front_plate() {
    // z = 0 is the front face
    hull() {
        translate([0, 0, EDGE_CH]) linear_extrude(PLATE_T - EDGE_CH) rrect(PLATE_W, PLATE_H, CORNER_R);
        linear_extrude(EDGE_CH) rrect(PLATE_W - 2*EDGE_CH, PLATE_H - 2*EDGE_CH, CORNER_R - EDGE_CH);
    }
}

module lip_and_ribs() {
    translate([0, 0, PLATE_T - eps]) linear_extrude(LIP_D + eps) {
        // ribs: one framing each end of the inlet pocket, one across the
        // middle of each end bay, one along it
        bay = (POCKET_W/2 + LIP_IN)/2;
        for (sx = [-1, 1]) {
            translate([sx*(POCKET_W/2 + 1.5), 0]) square([3, LIP_H - 1], center = true);
            translate([sx*bay, 0]) square([3, LIP_H - 1], center = true);
            translate([sx*bay, 0]) square([LIP_IN - POCKET_W/2, 3], center = true);
        }
    }
    translate([0, 0, PLATE_T - eps]) lip_ring(LIP_D + eps);
}

module inlet_cuts(depth) {
    // through cutout
    translate([0, 0, -1]) linear_extrude(depth + 2) square([CW, CH], center = true);
    // ear screw pilots (they sit right at the hole edge, so plate only)
    for (sy = [-1, 1]) translate([0, sy*EAR_PITCH/2, -1]) cylinder(d = EAR_PILOT, h = PLATE_T + 2);
}

// logo artwork laid on the plate so it reads from the FRONT with the plate
// mounted logo-end up (the swap of X/Y also mirrors it for the face-down print)
module logo_2d(w, s_only) {
    multmatrix([[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0]])
        resize([w, 0], auto = true) import(s_only ? LOGO_S_FILE : LOGO_FILE, center = true);
}

module logo_cut() {
    if (LOGO == "full")
        translate([LOGO_X, 0, -1]) linear_extrude(LOGO_DEPTH + 1) logo_2d(LOGO_FULL_W, false);
    else if (LOGO == "s")
        translate([LOGO_X, LOGO_S_Y, -1]) linear_extrude(LOGO_DEPTH + 1) logo_2d(LOGO_S_W, true);
}

module plate() {
    difference() {
        union() { front_plate(); lip_and_ribs(); clip_hooks(PLATE_T); }
        inlet_cuts(PLATE_T + LIP_D);
        clip_cuts(PLATE_T);
        for (p = cab_pts) translate(p) cab_screw(PLATE_T);
        logo_cut();
    }
}

module inlet_test() {
    // just the inlet zone: cutout and ear holes
    W = POCKET_W + 8; H = EAR_PITCH + 10;
    difference() {
        linear_extrude(PLATE_T) rrect(W, H, 3);
        inlet_cuts(PLATE_T);
    }
}

module hole_test() {
    // 2 mm frame with the 2 screw holes, plus the full lip with clips
    T = 2;
    difference() {
        union() {
            linear_extrude(T) difference() {
                union() {
                    rrect(LIP_W + 8, LIP_H + 8, 4);
                    for (p = cab_pts) hull() { translate(p) circle(d = CAB_D + 8); translate(p*0.8) circle(d = CAB_D + 8); }
                }
                rrect(LIP_W - 2*LIP_WALL, LIP_H - 2*LIP_WALL, 1);
            }
            translate([0, 0, T - eps]) lip_ring(LIP_D + eps);
            clip_hooks(T);
        }
        for (p = cab_pts) translate(p) cab_screw(T);
        clip_cuts(T);
    }
}

if (part == "plate") plate();
else if (part == "inlettest") inlet_test();
else if (part == "holetest") hole_test();

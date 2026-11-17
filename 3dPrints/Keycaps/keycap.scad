// Flat-top 1u keycaps for the Koolertron 16-key macro pad (Cherry MX stems).
// Two colours: a black body and a white/natural icon that runs right through
// the top, so the pad's backlight shines through the icon only.
//
// Everything is exported in PRINT orientation: top face down on the plate,
// stem pointing up. Load body + icon together in Bambu Studio as ONE object
// with two parts (it asks when you open both files at once), then give the
// body black PLA and the icon white or natural PLA.
//
// part = "body"  -> cap body with the icon cut out (black)
// part = "icon"  -> just the icon (white)
// part = "test"  -> 4 plain caps, stem slot sizes 1-4 (dots on the top say which)
// part = "stem"  -> just the stem, for stem_style = "clear" (printed in the icon colour)
// part = "both"  -> preview only

part = "both";
icon = "icons/skip-end-fill.svg";   // any 16x16 Bootstrap icon
slot = 2;                           // stem slot size 1-4, pick from the test print
stem_style = "black";               // "black" (normal), "none" (light test), "clear" (stem printed with the icon)

$fn = 48;

// Cap shape (mm)
BOT   = 18.0;    // skirt width at the bottom (keys are 19.05 apart)
TOP   = 14.5;    // flat top width
H     = 11;      // total height (OEM-like; was 7.5 = DSA)
R_BOT = 1.6;     // corner radius at the bottom
R_TOP = 2.2;     // corner radius at the top
WALL  = 1.4;     // side wall
TOPT  = 1.6;     // top thickness (= icon depth: icon goes all the way through)

// MX stem socket
STEM_D   = 5.6;               // round boss around the cross
SLOT_W   = [1.30, 1.35, 1.40, 1.45];   // cross arm width, sizes 1-4
SLOT_L   = [4.10, 4.15, 4.20, 4.25];   // cross arm length, sizes 1-4
STEM_GAP = 0.6;               // boss stops this far above the skirt bottom

module rsq(w, r, h) {          // rounded square slab, centred
    linear_extrude(h) offset(r) square(w - 2*r, center = true);
}

module shell_solid() {
    hull() {
        rsq(BOT, R_BOT, 0.01);
        translate([0, 0, H - 0.01]) rsq(TOP, R_TOP, 0.01);
    }
}

module cavity() {
    hull() {
        translate([0, 0, -0.01]) rsq(BOT - 2*WALL, max(R_BOT - WALL, 0.3), 0.01);
        translate([0, 0, H - TOPT - 0.01]) rsq(TOP - 2*WALL, max(R_TOP - WALL, 0.3), 0.01);
    }
}

// stem_notch > 0 cuts a sloped notch (45 degrees, prints without support) out of
// the LED side (+y) of the stem where it meets the top, so the LED can light the
// part of the icon that sits over the stem. It only removes the top of the stem,
// well above where the switch's stem reaches (about 4 mm in).
stem_notch = 0;

module notch() {
    zt = H - TOPT;
    y0 = -0.5;                          // the cut starts just past the centre
    rotate([90, 0, 90]) linear_extrude(20, center = true)
        polygon([[y0, zt + 1], [10, zt + 1], [10, zt - (10 - y0)], [y0, zt]]);
}

// wall_pocket > 0 thins the LED-side (+y) wall to about 0.9 mm just under the top, so
// the wall no longer sits under the top edge of the icon. 45-degree slope, no supports.
wall_pocket = 0;

module pocket() {
    zt = H - TOPT;
    rotate([90, 0, 90]) linear_extrude(11, center = true)
        polygon([[4.8, zt], [6.6, zt], [6.6, zt - 0.3], [4.8, zt - 2.1]]);
}

module stem(s) {
    difference() {
        translate([0, 0, STEM_GAP]) cylinder(d = STEM_D, h = H - TOPT - STEM_GAP + 0.01);
        if (stem_notch > 0) notch();
        translate([0, 0, -1]) {
            linear_extrude(H - TOPT + 1) {      // stops at the underside of the top
                square([SLOT_L[s-1], SLOT_W[s-1]], center = true);
                square([SLOT_W[s-1], SLOT_L[s-1]], center = true);
            }
        }
    }
}

// icon_w / icon_h: the icon's drawn size on the cap. make_keycaps.py measures each
// icon and sets these so its longest side is ICON_MAX mm, keeping its proportions.
icon_w = 10;
icon_h = 10;

// Thin lines in the icons (about 0.6 mm) are fattened by icon_grow on each side
// so a 0.4 mm nozzle can print them.
icon_grow = 0.15;

// icon_y moves the icon toward the top edge of the cap (the LED side), mm.
icon_y = 0;

module icon2d() {
    offset(delta = icon_grow) resize([icon_w, icon_h]) import(icon, center = true);
}

module icon3d() {
    translate([0, icon_y, H - TOPT]) linear_extrude(TOPT) icon2d();
}

module dots(n) {               // little dents in the top to number the test caps
    for (i = [0 : n - 1])
        translate([(i - (n - 1) / 2) * 2.4, 0, H - 0.4]) cylinder(d = 1.4, h = 1);
}

module cap_body(s, with_icon = true, ndots = 0) {
    difference() {
        shell_solid();
        cavity();
        if (with_icon) icon3d();
        if (ndots > 0) dots(ndots);
        if (wall_pocket > 0) pocket();
    }
    if (stem_style == "black") intersection() { stem(s); shell_solid(); }
}

module stem_part(s) { intersection() { stem(s); shell_solid(); } }

// Flip into print orientation: top on the plate.
module printed() { translate([0, 0, H]) rotate([180, 0, 0]) children(); }

if (part == "body") printed() cap_body(slot);
else if (part == "icon") printed() icon3d();
else if (part == "stem") printed() stem_part(slot);   // for stem_style = "clear"
else if (part == "test")
    for (s = [1 : 4]) translate([(s - 2.5) * 22, 0, 0]) printed() cap_body(s, false, s);
else {
    color("black") cap_body(slot);
    color("ivory") icon3d();
    if (stem_style == "clear") color("ivory") stem_part(slot);
}

// Frame for the screen 2 status monitor: the 14.5" 2560x720 bar panel
// (364 x 113 mm) and its two boards, behind the clear glass in the right
// panel beside the keypad (glass opening 14.75 x 4.74" = 374.6 x 120.4 mm).
//
// Parts (too long for the P1S bed in one piece, so each layer is split):
//   part = "front_left" / "front_right" : black face with the screen window,
//          a pocket the panel drops into, and screw posts. Print face down.
//   part = "back_left" / "back_right"   : cover that holds the panel in and
//          carries both boards on the outside. Print flat, trays up.
//          The back is split at a different place from the front, so it
//          bridges the front join and screws the two front halves together.
//   part = "tray_test" : just the two board trays, to check the boards snap in.
//   part = "tray_test_main" / "tray_test_small" : one tray each, to print apart.
//   part = "corner_test": one corner of the front, to check the panel's
//          thickness and that the face covers its black border.
//   part = "section_test": a 20 mm slice across the whole height of the front,
//          to slide into the cabinet's glass channel together with the glass.
//          It goes through a screw post top and bottom; "section_test_back" is
//          the matching strip of back cover to screw on.
//   part = "joint_test" : 15 mm either side of the front join, and three copies of
//          the back join marked 0, .05 and .1 (clearance in mm) to pick the tightest
//          press fit before printing the big parts. Set dove_gap to the winner.
//   part = "notch_test" : the middle of the top edge, to check where the
//          panel's ribbon comes out.
//   part = "all"       : assembled preview (not for printing).
// Render each part (F6) and export STL.
//
// MEASURE FIRST: panel_t (panel thickness) and fpc_x (where the panel's ribbon
// leaves its top edge) are estimates from the seller's photos.

part = "all";

// ---- panel -------------------------------------------------------------
panel_w   = 364.0;
panel_h   = 113.0;
panel_t   = 4.0;          // ESTIMATE: measure your panel's thickness
foam_t    = 1.0;          // foam tape between panel back and the cover
pclear    = 0.4;          // gap around the panel on each side
lip       = 2.5;          // face overlaps the panel's black border by this
fpc_x     = 8;            // ribbon centre, from the panel centre (+ = right, seen from the front)
fpc_w     = 40;           // opening for the ribbon in the wall and the cover

// ---- cabinet -----------------------------------------------------------
open_w    = 374.6;        // glass opening 14.75"
open_h    = 120.4;        // glass opening 4.74"
flange    = 8;            // face extends this far past the opening at the ends
flange_v  = 8.5;          // and at the top and bottom (Andrew's channel test: 8.5 fits best)
ear_l     = 0;            // screw ears on the cover ends (0 = none; the frame slides into the glass channel instead)
ear_w     = 24;
ear_hole  = 4.2;          // #6 wood screw

// ---- frame -------------------------------------------------------------
face_t    = 2.0;
wall      = 2.4;
back_t    = 3.0;
boss_d    = 6;
gap_out   = 5;            // room between the walls and the cabinet's bevelled metal (Andrew measured ~5 mm)
cover_out = 4.5;          // back cover and posts stay this close to the walls
pilot     = 2.5;          // M3 x 6 mm self-tapping screw (cover 3 mm + post hole 5 mm; 10 mm would poke through the face)
screw_cl  = 3.4;
split_f   = 0;            // where the front halves join
split_b   = -40;          // where the back pieces join
// Dovetail joints on both splits: tabs on the left piece press into sockets on
// the right piece. dove_gap 0 is a press fit (no clearance); the joint test
// tries 0, 0.05 and 0.1 mm so the tightest one that still goes in can be used.
dove_len  = 7;            // how far each tab reaches into the other piece
dove_neck = 5;
dove_head = 8;
dove_gap  = 0;            // total clearance between tab and socket (0 = press fit)
front_dove_y = [-61.5, 61.5];  // in the top and bottom borders, through the wall
back_dove_y  = [-40, 0, 40];

// ---- feet (optional) ----------------------------------------------------
// Posts on the back so the frame can lie face up on a table without resting
// on the boards. 0 = none; the "_feet" STLs are exported with feet_h = 16.
feet_h    = 0;            // height above the back cover
feet_d    = 12;
feet_xy   = [for (x = [-150, -75, -25, 95, 160], y = [-45, 45]) [x, y]];

// ---- boards ------------------------------------------------------------
main_l = 88;  main_w = 55;    // driver board (seller says 59; set from Andrew's tray tests) (HDMI / USB-C end faces +x)
key_l  = 19;  key_w  = 55.5;    // small button board (set from Andrew's tray tests) (button side faces -x)
pcb_t  = 1.6;
stand  = 3.0;             // room under the boards for solder joints
bclear = 0.4;
main_x = 50;              // left end of the driver board (ribbon end)
key_x  = -170;            // left end of the button board

// ---- derived -----------------------------------------------------------
face_w  = open_w + 2*flange;
face_h  = open_h + 2*flange_v;
pin_w   = panel_w + 2*pclear;
pin_h   = panel_h + 2*pclear;
wall_h  = panel_t + foam_t;
wout_w  = pin_w + 2*wall;
wout_h  = pin_h + 2*wall;
back_z  = face_t + wall_h;            // underside of the cover
boss_y  = wout_h/2 + cover_out - boss_d/2;   // posts merge into the walls so they
boss_ex = wout_w/2 + cover_out - boss_d/2;   // clear the bevelled metal
cover_w = wout_w + 2*cover_out;
cover_h = wout_h + 2*cover_out;
top_x   = [-165, -110, -58, -28, 45, 100, 160];
bot_x   = [-165, -110, -58, -15, 25, 100, 160];
end_y   = [-30, 30];
big     = 1000;
$fn     = 40;

function bosses() = concat(
    [for (x = top_x) [x,  boss_y]],
    [for (x = bot_x) [x, -boss_y]],
    [for (s = [-1, 1], y = end_y) [s*boss_ex, y]]);

module box(w, h, t, z = 0) { translate([-w/2, -h/2, z]) cube([w, h, t]); }

module front() {
    difference() {
        union() {
            box(face_w, face_h, face_t);
            box(wout_w, wout_h, back_z);
            for (p = bosses()) translate([p[0], p[1], 0]) cylinder(d = boss_d, h = back_z);
        }
        box(panel_w - 2*lip, panel_h - 2*lip, 3*big, -big);   // screen window
        box(pin_w, pin_h, big, face_t);                        // panel pocket
        translate([fpc_x - fpc_w/2, pin_h/2 - 1, face_t]) cube([fpc_w, wall + 2, big]);  // ribbon notch
        for (p = bosses()) translate([p[0], p[1], face_t]) cylinder(d = pilot, h = big);
    }
}

// Board tray: rims along the two sides parallel to x, with snap lips in the
// middle and slits either side so the rims flex. stop_end = -1/+1 puts corner
// stops at that x end, 0 = none.
module tray(l, w, stop_end) {
    il = l + 2*bclear;  iw = w + 2*bclear;
    rim = 1.6;  rh = stand + pcb_t + 1.2;
    lip_l = min(30, l - 8);
    difference() {
        union() {
            for (s = [-1, 1]) {
                translate([-il/2, s > 0 ? iw/2 : -iw/2 - rim, 0]) cube([il, rim, rh]);
                translate([-il/2 + 3, s > 0 ? iw/2 - 1.5 : -iw/2, 0]) cube([il - 6, 1.5, stand]);  // ledge
                // lip: flat underside at the board's top face, sloped top to snap in
                translate([0, s*iw/2, stand + pcb_t + 0.2])
                    rotate([0, 90, 0]) linear_extrude(lip_l, center = true)
                        polygon([[0, 0], [-1.0, 0], [-1.0, -s*0.6], [0, -s*1.0]]);
            }
            if (stop_end != 0) for (s = [-1, 1])
                translate([stop_end*(il/2 + 1), s*(iw/2 - 2), 0]) cube([2, 4, rh], center = false);
        }
        for (s = [-1, 1], e = [-1, 1])    // flex slits
            translate([e*(lip_l/2 + 1), s*(iw/2 + rim/2), stand + 0.6]) cube([1.2, rim + 2, 2*rh], center = true);
    }
}

module trays() {
    translate([main_x + main_l/2, 0, 0]) tray(main_l, main_w, -1);
    translate([key_x + key_l/2, 0, 0])   tray(key_l, key_w, 1);
}

module back() {
    difference() {
        union() {
            box(cover_w, cover_h, back_t);
            if (ear_l > 0) for (s = [-1, 1])
                translate([s > 0 ? face_w/2 - 1 : -face_w/2 - ear_l + 1, -ear_w/2, 0])
                    cube([ear_l, ear_w, back_t]);
            translate([0, 0, back_t]) trays();
            if (feet_h > 0) for (p = feet_xy) translate([p[0], p[1], 0]) cylinder(d = feet_d, h = back_t + feet_h);
        }
        for (p = bosses()) translate([p[0], p[1], -1]) cylinder(d = screw_cl, h = back_t + 2);
        translate([fpc_x - fpc_w/2, panel_h/2 - 10, -1]) cube([fpc_w, wout_h/2 - panel_h/2 + 11, back_t + 2]);
        if (ear_l > 0) for (s = [-1, 1])
            translate([s*(face_w/2 + ear_l/2 - 0.5), 0, -1]) cylinder(d = ear_hole, h = back_t + 2);
    }
}

module cut(from, to) { intersection() { children(); translate([from, -big/2, -big/2]) cube([to - from, big, big]); } }

// Everything left of the split plus the dovetail tabs, as a solid.
module left_side(sx, ys, grow) {
    translate([0, 0, -big/2]) linear_extrude(big) offset(delta = grow) union() {
        translate([-big, -big/2]) square([big + sx, big]);
        for (y = ys) polygon([[sx - 1, y - dove_neck/2], [sx + dove_len, y - dove_head/2],
                              [sx + dove_len, y + dove_head/2], [sx - 1, y + dove_neck/2]]);
    }
}
module piece_left(sx, ys, gap = dove_gap)  { intersection() { children(); left_side(sx, ys, -gap/2); } }
module piece_right(sx, ys, gap = dove_gap) { difference()   { children(); left_side(sx, ys,  gap/2); } }

if (part == "front_left")  piece_left(split_f, front_dove_y) front();
if (part == "front_right") piece_right(split_f, front_dove_y) front();
if (part == "back_left")   piece_left(split_b, back_dove_y) back();
if (part == "back_right")  piece_right(split_b, back_dove_y) back();
if (part == "joint_test") {   // front join at dove_gap, plus the back join at three tightnesses
    translate([0, 0, 0])   intersection() { piece_left(split_f, front_dove_y) front(); translate([split_f - 15, -big/2, -1]) cube([15 + dove_len + 1, big, 50]); }
    translate([15, 0, 0])  intersection() { piece_right(split_f, front_dove_y) front(); translate([split_f, -big/2, -1]) cube([15, big, 50]); }
    for (i = [0 : 2]) let(g = [0, 0.05, 0.1][i], ox = 95 + 50*i) {
        translate([ox, 0, 0]) difference() {
            intersection() { piece_left(split_b, back_dove_y, g) back(); translate([split_b - 15, -50, -1]) cube([15 + dove_len + 1, 100, 50]); }
            translate([split_b - 7.5, -46, back_t - 0.6]) linear_extrude(1) text(["0", ".05", ".1"][i], size = 5, halign = "center");
        }
        translate([ox + 15, 0, 0]) intersection() { piece_right(split_b, back_dove_y, g) back(); translate([split_b, -50, -1]) cube([15, 100, 50]); }
    }
}
if (part == "tray_test") {
    translate([-30, 0, 0]) { box(main_l + 8, main_w + 8, 1.2); translate([0, 0, 1.2]) tray(main_l, main_w, -1); }
    translate([45, 0, 0])  { box(key_l + 8, key_w + 8, 1.2);   translate([0, 0, 1.2]) tray(key_l, key_w, 1); }
}
if (part == "tray_test_main")  { box(main_l + 8, main_w + 8, 1.2); translate([0, 0, 1.2]) tray(main_l, main_w, -1); }
if (part == "tray_test_small") { box(key_l + 8, key_w + 8, 1.2);   translate([0, 0, 1.2]) tray(key_l, key_w, 1); }
if (part == "corner_test")  // top-left corner, 60 x 45 mm
    intersection() { front(); translate([-face_w/2 - 1, face_h/2 - 45, -1]) cube([61, 46, 50]); }
if (part == "section_test")  // 20 mm slice through the posts at x = -110; window filled in so it's one piece
    intersection() { union() { front(); box(panel_w, panel_h, face_t); } translate([-120, -big/2, -1]) cube([20, big, 50]); }
if (part == "section_test_back")  // the matching strip of back cover, to screw on
    intersection() { back(); translate([-120, -big/2, -1]) cube([20, big, 50]); }
if (part == "notch_test")   // top edge around the ribbon notch, 80 x 30 mm
    intersection() { front(); translate([fpc_x - 40, face_h/2 - 30, -1]) cube([80, 31, 50]); }
if (part == "all") {
    color("dimgray") front();
    color([0.1, 0.1, 0.15]) translate([0, 0, face_t]) box(panel_w, panel_h, panel_t);
    color("gray", 0.9) translate([0, 0, back_z]) back();
    color("green") translate([0, 0, back_z + back_t + stand]) {     // the boards
        translate([main_x, -main_w/2, 0]) cube([main_l, main_w, pcb_t]);
        translate([key_x, -key_w/2, 0])   cube([key_l, key_w, pcb_t]);
    }
}

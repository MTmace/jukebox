// Glass button bar case for the hot-swap circuit board (button_bar.kicad_pcb)
// Seeburg Firestar jukebox. A low, sloped shape with rounded edges, so it reads as
// part of the glass trim rather than a box stuck on it.
// Two printed parts:
//   part = "tray" : the sloped base; the board sits on its standoffs. Print bottom down.
//   part = "lid"  : the top, with two sunken keycap wells. Printed upside down.
// Four M2 x 10 mm countersunk (flat-head) self-tapping screws go in from underneath,
// through the tray and board, into posts on the lid. No screw heads show on top;
// the countersunk heads sit flush with the underside, which is taped to the glass.
// Coordinates follow the board: x along the bar, key 1 (page left) centre at x = 0.

part = "both";            // "tray", "lid" or "both" (preview)

// ---- board (from make_pcb.py; y here is the board's y flipped) -------------
pcb_x0 = -13.0;  pcb_x1 = 85.75;
pcb_y0 = -10.5;  pcb_y1 = 10.5;
pcb_t  = 1.6;
holes  = [[-11.3, 7.0], [-11.3, -7.0], [31.75, 0], [76.0, 8.5]];
conn_y = [-8.5, 6.5];     // plug tunnel through the right end (JST PH, 6 pin)
conn_h = 5.0;             // tunnel height above the board top

// ---- shape -----------------------------------------------------------------
clr       = 0.4;          // gap around the board
top_wall  = 2.0;          // wall thickness at the top edge
slope     = 6.0;          // how far the sides flare out from top edge to glass
edge_r    = 2.0;          // rounding on the top edges
corner_r  = 4.0;          // plan-view corner radius at the top
floor_t   = 1.6;          // this face sits on the glass
standoff  = 2.5;          // room for the sockets under the board (they are 1.85 mm)
lid_above = 6.5;          // lid top surface height above the board top
lid_t     = 1.6;
post_d    = 4.0;
pilot_d   = 1.6;          // M2 self-tapping, into the lid posts
clear_d   = 2.4;          // through the tray and board
csk_d     = 4.2;          // countersink for an M2 flat head
// keycap wells (Choc caps are 17.5 x 16.5 mm), one per pair of keys
wells   = [[-9.5, 28.0], [35.5, 73.0]];
well_y  = 9.0;
well_r  = 2.0;            // well corner radius
well_ch = 1.0;            // chamfer around the top of each well

cx0 = pcb_x0 - clr;  cx1 = pcb_x1 + clr;     // cavity
cy0 = pcb_y0 - clr;  cy1 = pcb_y1 + clr;
pcb_z  = floor_t + standoff;                 // board bottom
top_z  = pcb_z + pcb_t + lid_above;          // lid top
split_z = top_z - lid_t;                     // tray / lid joint

module rbox(xa, ya, xb, yb, h, r) {
    hull() for (x = [xa + r, xb - r], y = [ya + r, yb - r]) translate([x, y, 0]) cylinder(r = r, h = h, $fn = 48);
}

// Outer body: top outline = cavity + top_wall, flaring by `slope` down to the glass,
// with the top edges rounded by edge_r.
module body() {
    e = edge_r; t = top_wall; s = slope;
    intersection() {
        minkowski() {
            hull() {
                rbox(cx0 - t - s + e, cy0 - t - s + e, cx1 + t + s - e, cy1 + t + s - e, 0.01, corner_r + s - e);
                translate([0, 0, top_z - e - 0.01])
                    rbox(cx0 - t + e, cy0 - t + e, cx1 + t - e, cy1 + t - e, 0.01, corner_r - e);
            }
            sphere(r = e, $fn = 24);
        }
        translate([-500, -500, 0]) cube([1000, 1000, top_z]);
    }
}

module tray() {
    difference() {
        intersection() { body(); translate([-500, -500, 0]) cube([1000, 1000, split_z]); }
        translate([cx0, cy0, floor_t]) cube([cx1 - cx0, cy1 - cy0, top_z]);
        // plug tunnel through the right end
        translate([cx1 - 1, conn_y[0], pcb_z + pcb_t]) cube([50, conn_y[1] - conn_y[0], conn_h]);
        for (h = holes) translate([h[0], h[1], 0]) {
            translate([0, 0, -1]) cylinder(d = clear_d, h = 50, $fn = 16);
            translate([0, 0, -0.01]) cylinder(d1 = csk_d, d2 = clear_d, h = (csk_d - clear_d) / 2, $fn = 24);
        }
    }
    for (h = holes) translate([h[0], h[1], floor_t - 0.01]) difference() {
        cylinder(d = post_d + 1, h = standoff, $fn = 32);
        translate([0, 0, -1]) cylinder(d = clear_d, h = 50, $fn = 16);
    }
}

module well(x0, x1) {
    hull() {
        translate([0, 0, split_z - 1]) rbox(x0, -well_y, x1, well_y, top_z - split_z + 1 - well_ch, well_r);
        translate([0, 0, top_z - 0.01]) rbox(x0 - well_ch, -well_y - well_ch, x1 + well_ch, well_y + well_ch, 1, well_r + well_ch);
    }
}

module lid() {
    difference() {
        union() {
            intersection() {
                body();
                translate([-500, -500, split_z]) cube([1000, 1000, 100]);
            }
            // plug tunnel roof is in the tray; posts press the board down
            for (h = holes) translate([h[0], h[1], pcb_z + pcb_t]) cylinder(d = post_d, h = split_z - pcb_z - pcb_t + 0.01, $fn = 32);
        }
        for (w = wells) well(w[0], w[1]);
        for (h = holes) translate([h[0], h[1], pcb_z]) cylinder(d = pilot_d, h = split_z - pcb_z + lid_t - 0.6, $fn = 16);
    }
}

if (part == "tray") tray();
else if (part == "lid") translate([0, 0, top_z]) mirror([0, 0, 1]) lid();   // flipped for printing
else { tray(); color("dimgray") lid(); }

echo(str("Case footprint on the glass: ", cx1 - cx0 + 2*(top_wall + slope), " x ", cy1 - cy0 + 2*(top_wall + slope),
         " mm; top: ", cx1 - cx0 + 2*top_wall, " x ", cy1 - cy0 + 2*top_wall, " mm; ", top_z, " mm tall"));

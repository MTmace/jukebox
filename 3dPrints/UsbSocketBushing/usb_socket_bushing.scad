// USB-A panel socket bushing for the 31.5 mm hole in the jukebox back panel
// Socket (Amazon listing): 25.5 mm front flange, ~21.7 mm threaded body,
// hex nut, 30.6 mm long. The flange is smaller than the hole, so this
// stepped bushing fills the hole and gives the flange and nut a face to
// clamp against. No cover plate needed.
//
// Stack, outside -> inside:
//   socket flange | bushing lip | metal panel | washer | socket nut
// The bushing's plug is a little shorter than the panel, so the nut
// squeezes the panel between the lip and the washer and holds tight.
//
// part = "bushing" | "washer" | "both"
part = "both";

HOLE_D   = 31.5;   // hole in the panel (measured by Andrew)
FIT      = 0.1;    // plug is this much smaller than the hole, all round
                   // (same value that fitted the power inlet plate lip)
PANEL_T  = 2;      // panel thickness (same steel as the power inlet panel)
BORE_D   = 22.3;   // through hole for the 21.7 mm threaded body
LIP_D    = 40;     // outside lip, covers the hole edge
LIP_T    = 2;      // lip thickness
WASHER_T = 1.6;    // inside washer thickness
SHORT    = 0.2;    // plug shorter than the panel so the nut clamps the panel
CHAMFER  = 0.6;    // soft edge on the visible lip
$fn = 128;

PLUG_D = HOLE_D - 2*FIT;
PLUG_L = PANEL_T - SHORT;

// Printed lip face down (the face you see on the outside of the cabinet).
module bushing() {
    difference() {
        union() {
            cylinder(d1 = LIP_D - 2*CHAMFER, d2 = LIP_D, h = CHAMFER);
            translate([0,0,CHAMFER]) cylinder(d = LIP_D, h = LIP_T - CHAMFER);
            translate([0,0,LIP_T - 0.01]) cylinder(d = PLUG_D, h = PLUG_L + 0.01);
        }
        translate([0,0,-1]) cylinder(d = BORE_D, h = LIP_T + PLUG_L + 2);
    }
}

module washer() {
    difference() {
        cylinder(d = LIP_D, h = WASHER_T);
        translate([0,0,-1]) cylinder(d = BORE_D, h = WASHER_T + 2);
    }
}

if (part == "bushing") bushing();
else if (part == "washer") washer();
else { bushing(); translate([LIP_D + 5, 0, 0]) washer(); }

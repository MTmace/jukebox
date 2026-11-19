# Generates the 4-key Choc v1 hot-swap board for the Firestar glass button bar.
# Run with KiCad 7's python:  python3 make_pcb.py  -> button_bar.kicad_pcb
import pcbnew
from pcbnew import VECTOR2I, FromMM as mm

OUT = "button_bar.kicad_pcb"
KEYS = [("LEFT", 0.0, "<"), ("RIGHT", 18.5, ">"), ("GENRE", 45.0, "GENRE"), ("RANDOM", 63.5, "RANDOM")]
LANE_Y = [8.0, 6.5, 5.0, 3.5]          # front-copper lane per key
GND_Y = 9.2                            # back-copper ground bus
X0 = 73.0                              # where lanes start to jog toward the connector
CX, CY = 79.5, 6.0                     # connector pin 1 (pins step -2 mm in y)
LEFT, RIGHT, TOP, BOT = -13.0, CX + 6.25, -10.5, 10.5
HOLES = [(-11.3, -7.0), (-11.3, 7.0), (31.75, 0.0), (76.0, -8.5)]  # M2, clear of keycaps so the lid posts fit
TRACK, VIA_D, VIA_DRILL = 0.3, 0.6, 0.3

b = pcbnew.BOARD()
b.SetCopperLayerCount(2)
ds = b.GetDesignSettings()
ds.m_CopperEdgeClearance = mm(0.5)

nets = {}
def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(b, name); b.Add(n); nets[name] = n
    return nets[name]

def pt(x, y): return VECTOR2I(mm(x), mm(y))

def npth(fp, x, y, d):
    p = pcbnew.PAD(fp); p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH); p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(pt(d, d)); p.SetDrillSize(pt(d, d)); p.SetLayerSet(p.UnplatedHoleMask())
    fp.Add(p); p.SetPos0(pt(x, y)); p.SetPosition(fp.GetPosition() + pt(x, y)); return p

def line(fp, layer, a, c, w=0.12):
    s = pcbnew.FP_SHAPE(fp); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(layer); s.SetWidth(mm(w))
    fp.Add(s); s.SetStart0(pt(*a)); s.SetEnd0(pt(*c)); s.SetDrawCoord(); return s

def rect(fp, layer, x1, y1, x2, y2, w=0.12):
    for a, c in [((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))]:
        line(fp, layer, a, c, w)

def choc(ref, x, y, gnd, sig, label):
    """Kailh Choc v1 + CPG135001S30 hot-swap socket on the back (front-view coordinates)."""
    fp = pcbnew.FOOTPRINT(b); fp.SetReference(ref); fp.SetValue("Choc_v1_hotswap")
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    b.Add(fp); fp.SetPosition(pt(x, y))
    npth(fp, 0, 0, 3.45)                       # centre post
    npth(fp, -5.5, 0, 1.9); npth(fp, 5.5, 0, 1.9)   # side posts
    npth(fp, 0, -5.95, 3.0); npth(fp, 5, -3.75, 3.0)  # switch pins into the socket
    for num, px, py, n in [("1", -3.275, -5.95, gnd), ("2", 8.275, -3.75, sig)]:
        p = pcbnew.PAD(fp); p.SetNumber(num); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD); p.SetShape(pcbnew.PAD_SHAPE_RECT)
        p.SetSize(pt(2.6, 2.6)); ls = pcbnew.LSET(); [ls.AddLayer(l) for l in (pcbnew.B_Cu, pcbnew.B_Paste, pcbnew.B_Mask)]
        p.SetLayerSet(ls); fp.Add(p); p.SetPos0(pt(px, py)); p.SetPosition(fp.GetPosition() + pt(px, py)); p.SetNet(n)
    rect(fp, pcbnew.F_SilkS, -7.5, -7.5, 7.5, 7.5)      # switch body outline
    rect(fp, pcbnew.F_CrtYd, -7.6, -7.6, 7.6, 7.6, 0.05)
    rect(fp, pcbnew.B_SilkS, -4.8, -7.3, 9.8, -2.2)     # socket outline
    t = pcbnew.FP_TEXT(fp); t.SetText(label); t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pt(1.2, 1.2)); t.SetTextThickness(mm(0.18)); fp.Add(t); t.SetPos0(pt(0, 9.0 if False else -8.6)); t.SetDrawCoord()
    return fp

def track(a, c, layer, n):
    t = pcbnew.PCB_TRACK(b); t.SetStart(pt(*a)); t.SetEnd(pt(*c)); t.SetWidth(mm(TRACK)); t.SetLayer(layer); t.SetNet(n); b.Add(t)

def via(x, y, n):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pt(x, y)); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL)); v.SetNet(n); b.Add(v)

gnd = net("GND")
for i, (name, kx, label) in enumerate(KEYS):
    s = net(name)
    choc(f"SW{i+1}", kx, 0, gnd, s, label)
    # signal: socket pad 2 -> down on back -> via -> front lane
    px = kx + 8.275
    track((px, -3.75), (px, LANE_Y[i]), pcbnew.B_Cu, s)
    via(px, LANE_Y[i], s)
    pin_y = CY - 2 * (i + 1)                 # pins 2..5
    d = LANE_Y[i] - pin_y
    track((px, LANE_Y[i]), (X0, LANE_Y[i]), pcbnew.F_Cu, s)
    track((X0, LANE_Y[i]), (X0 + d, pin_y), pcbnew.F_Cu, s)
    track((X0 + d, pin_y), (CX, pin_y), pcbnew.F_Cu, s)
    # ground: socket pad 1 -> down on back to the bus
    track((kx - 3.275, -5.95), (kx - 3.275, GND_Y), pcbnew.B_Cu, gnd)
track((KEYS[0][1] - 3.275, GND_Y), (CX, GND_Y), pcbnew.B_Cu, gnd)
track((CX, GND_Y), (CX, CY), pcbnew.B_Cu, gnd)

# JST PH 6-pin side-entry, opening flush with the right edge
lib = "/usr/share/kicad/footprints/Connector_JST.pretty"
j = pcbnew.FootprintLoad(lib, "JST_PH_S6B-PH-K_1x06_P2.00mm_Horizontal")
j.SetReference("J1"); b.Add(j); j.SetPosition(pt(CX, CY)); j.SetOrientationDegrees(90)
for p in j.Pads():
    n = {"1": gnd, "2": net("LEFT"), "3": net("RIGHT"), "4": net("GENRE"), "5": net("RANDOM")}.get(p.GetNumber())
    if n: p.SetNet(n)

# mounting holes (M2)
for k, (hx, hy) in enumerate(HOLES):
    fp = pcbnew.FOOTPRINT(b); fp.SetReference(f"H{k+1}"); fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    b.Add(fp); fp.SetPosition(pt(hx, hy)); npth(fp, 0, 0, 2.2)

# board outline, rounded corners
def edge(a, c):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
    s.SetStart(pt(*a)); s.SetEnd(pt(*c)); b.Add(s)
def arc(cx, cy, sx, sy, ang):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_ARC); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
    s.SetCenter(pt(cx, cy)); s.SetStart(pt(sx, sy)); s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T)); b.Add(s)
r = 1.5
edge((LEFT + r, TOP), (RIGHT - r, TOP)); edge((RIGHT, TOP + r), (RIGHT, BOT - r))
edge((RIGHT - r, BOT), (LEFT + r, BOT)); edge((LEFT, BOT - r), (LEFT, TOP + r))
arc(RIGHT - r, TOP + r, RIGHT - r, TOP, 90); arc(RIGHT - r, BOT - r, RIGHT, BOT - r, 90)
arc(LEFT + r, BOT - r, LEFT + r, BOT, 90); arc(LEFT + r, TOP + r, LEFT, TOP + r, 90)

# silkscreen notes
def text(s, x, y, layer=pcbnew.F_SilkS, size=1.0, mirror=False):
    t = pcbnew.PCB_TEXT(b); t.SetText(s); t.SetPosition(pt(x, y)); t.SetLayer(layer)
    t.SetTextSize(pt(size, size)); t.SetTextThickness(mm(size * 0.15)); t.SetMirrored(mirror); b.Add(t)
text("FIRESTAR BUTTON BAR v1", 34.5, 9.6, pcbnew.F_SilkS, 0.9)
text("J1: 1 GND  2 <  3 >  4 GENRE  5 RANDOM  6 spare", 34.5, -9.4, pcbnew.B_SilkS, 0.8, True)

pcbnew.SaveBoard(OUT, b)
print("board", RIGHT - LEFT, "x", BOT - TOP, "mm")

# JLCPCB assembly files (sockets are on the bottom, connector on top)
import csv
with open("jlc_bom.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    w.writerow(["Kailh Choc v1 hot-swap socket CPG135001S30", "SW1,SW2,SW3,SW4", "Choc_hotswap", "C5333465"])
    w.writerow(["JST S6B-PH-K-S side-entry 6-pin header", "J1", "JST_PH_S6B-PH-K", ""])
with open("jlc_cpl.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for i, (_, kx, _l) in enumerate(KEYS):
        w.writerow([f"SW{i+1}", f"{kx + 2.5:.3f}mm", f"{-(-4.85):.3f}mm", "Bottom", 0])
    w.writerow(["J1", f"{CX:.3f}mm", f"{-CY:.3f}mm", "Top", 90])

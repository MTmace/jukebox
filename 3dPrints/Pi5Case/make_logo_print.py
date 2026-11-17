# Build a print-friendly cut-through Seeburg logo for small lids.
#   python3 make_logo_print.py seeburg_logo.svg out.svg <logo_w mm> [min_island mm] [bridge mm]
# The B and R letter centres (islands) are tiny at small sizes (about 2 x 0.6 mm
# on a 60 mm logo) and print badly. This version:
#   - grows each island so it is at least min_island mm across (default 1.1),
#     taking the room from the letter stroke round it,
#   - ties each island to the lid with a straight bridge bridge mm wide
#     (default 1.0) across the letter's top or bottom bar, running the FULL
#     thickness of the lid (stencil style), not just the back.
# The result is one shape: cut it straight through the lid.
import sys
from svgpathtools import svg2paths
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

src, dst, logo_w_mm = sys.argv[1], sys.argv[2], float(sys.argv[3])
min_island = float(sys.argv[4]) if len(sys.argv) > 4 else 1.1
bridge_mm = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0

paths, _ = svg2paths(src)
polys = []
for p in paths:
    for sub in p.continuous_subpaths():
        pts = []
        for seg in sub:
            for i in range(24):
                z = seg.point(i / 24); pts.append((z.real, z.imag))
        polys.append(Polygon(pts).buffer(0))
g = polys[0]
for q in polys[1:]: g = g.symmetric_difference(q)
minx, miny, maxx, maxy = g.bounds
unit = (maxx - minx) / logo_w_mm            # svg units per mm on the lid

def short_side(poly):
    r = poly.minimum_rotated_rectangle
    c = list(r.exterior.coords)
    a = LineString(c[0:2]).length; b = LineString(c[1:3]).length
    return min(a, b)

letters = []
for letter in getattr(g, 'geoms', [g]):
    outer = Polygon(letter.exterior)
    cut = outer
    for h in letter.interiors:
        island = Polygon(h)
        grow = max(0.0, (min_island * unit - short_side(island)) / 2)
        big = island.buffer(grow, join_style=2) if grow > 0 else island
        # straight bridge across the nearer top/bottom bar of the letter
        # (classic stencil look: B and R stay readable)
        ib, ob = big.bounds, outer.bounds
        c = big.centroid
        if ib[1] - ob[1] < ob[3] - ib[3]:
            line = LineString([(c.x, c.y), (c.x, ob[1] - 0.5*unit)])
        else:
            line = LineString([(c.x, c.y), (c.x, ob[3] + 0.5*unit)])
        bridge = line.buffer(bridge_mm * unit / 2, cap_style=2)
        cut = cut.difference(big).difference(bridge)
        print(f'island {short_side(island)/unit:.2f} -> {short_side(big)/unit:.2f} mm', file=sys.stderr)
    letters.append(cut)
cut = unary_union(letters)
thin = cut.area - cut.buffer(-0.35 * unit).buffer(0.35 * unit).area
print(f'cut area narrower than 0.7 mm: {thin/unit/unit:.2f} mm2 of {cut.area/unit/unit:.1f}', file=sys.stderr)

def ring(r):
    return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in r.coords) + ' Z'
d = []
for poly in getattr(cut, 'geoms', [cut]):
    d.append(ring(poly.exterior)); d += [ring(i) for i in poly.interiors]
hdr = open(src).read()
w = hdr.split('width="')[1].split('"')[0]; h = hdr.split('height="')[1].split('"')[0]
vb = hdr.split('viewBox="')[1].split('"')[0]
tr = hdr.split('<g transform="')[1].split('"')[0]
open(dst, 'w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{vb}">\n'
                     f'<g transform="{tr}" fill="#000000"><path fill-rule="evenodd" d="{" ".join(d)}"/></g></svg>\n')

# Build seeburg_logo_cut.svg: the logo with its letter islands kept, each joined
# to the surrounding lid by a thin bridge, so the logo can be cut right through.
import sys
from svgpathtools import svg2paths
from shapely.geometry import Polygon, LineString
from shapely.ops import nearest_points, unary_union
src, dst, bridge_mm, logo_w_mm = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
paths, _ = svg2paths(src)
polys = []
for p in paths:
    for sub in p.continuous_subpaths():
        pts = [(sub.point(0).real, sub.point(0).imag)]
        for seg in sub:
            for i in range(1, 13):
                z = seg.point(i / 12); pts.append((z.real, z.imag))
        polys.append(Polygon(pts).buffer(0))
g = polys[0]
for q in polys[1:]: g = g.symmetric_difference(q)
minx, miny, maxx, maxy = g.bounds
unit = (maxx - minx) / logo_w_mm            # svg units per mm on the lid
bw = bridge_mm * unit
bridges = []
for letter in getattr(g, 'geoms', [g]):
    outer = Polygon(letter.exterior)
    for h in letter.interiors:
        island = Polygon(h)
        a, b = nearest_points(island.exterior, outer.exterior)
        # carry the bridge a little past both edges
        dx, dy = b.x - a.x, b.y - a.y; L = (dx*dx + dy*dy) ** 0.5
        ext = 0.3 * unit
        line = LineString([(a.x - dx/L*ext, a.y - dy/L*ext), (b.x + dx/L*ext, b.y + dy/L*ext)])
        bridges.append(line.buffer(bw / 2, cap_style=2))
cut = g.difference(unary_union(bridges)) if bridges else g
print('islands bridged:', len(bridges), file=sys.stderr)
def ring(r):
    c = list(r.coords)
    return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in c) + ' Z'
d = []
for poly in getattr(cut, 'geoms', [cut]):
    d.append(ring(poly.exterior)); d += [ring(i) for i in poly.interiors]
hdr = open(src).read()
w = hdr.split('width="')[1].split('"')[0]; h = hdr.split('height="')[1].split('"')[0]
vb = hdr.split('viewBox="')[1].split('"')[0]
tr = hdr.split('<g transform="')[1].split('"')[0]
open(dst, 'w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{vb}">\n'
                     f'<g transform="{tr}" fill="#000000"><path fill-rule="evenodd" d="{" ".join(d)}"/></g></svg>\n')

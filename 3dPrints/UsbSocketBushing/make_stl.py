# Builds the STLs with manifold3d using the same numbers as usb_socket_bushing.scad
import manifold3d as m, numpy as np, trimesh
HOLE_D, FIT, PANEL_T, BORE_D, LIP_D, LIP_T, WASHER_T, SHORT, CH = 31.5, 0.1, 2, 22.3, 40, 2, 1.6, 0.2, 0.6
N = 128
PLUG_D, PLUG_L = HOLE_D - 2*FIT, PANEL_T - SHORT
cyl = lambda h, r1, r2=None: m.Manifold.cylinder(h, r1, r1 if r2 is None else r2, N)
def bushing():
    b = cyl(CH, LIP_D/2 - CH, LIP_D/2) + cyl(LIP_T - CH, LIP_D/2).translate([0,0,CH]) \
        + cyl(PLUG_L + 0.01, PLUG_D/2).translate([0,0,LIP_T - 0.01])
    return b - cyl(10, BORE_D/2).translate([0,0,-1])
def washer():
    return cyl(WASHER_T, LIP_D/2) - cyl(10, BORE_D/2).translate([0,0,-1])
def save(s, f):
    mm = s.to_mesh(); t = trimesh.Trimesh(np.array(mm.vert_properties)[:, :3], np.array(mm.tri_verts))
    t.export(f); print(f, t.is_watertight, t.bounds.tolist())
save(bushing(), "usb_socket_bushing.stl")
save(washer(), "usb_socket_washer.stl")
save(bushing() + washer().translate([LIP_D + 5, 0, 0]), "usb_socket_bushing_and_washer.stl")

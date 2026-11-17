#!/usr/bin/env python3
"""Packs each cap's body + icon STLs into one 3MF: one object, two parts,
body on filament 1 (black) and icon on filament 2 (white), for Bambu Studio.

    python3 make_3mf.py            all caps in stl/
"""
import glob, os, zipfile
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))


def mesh_xml(oid, name, m):
    v = "\n".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in m.vertices)
    t = "\n".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
    return (f'<object id="{oid}" name="{name}" type="model"><mesh><vertices>\n{v}\n</vertices>'
            f'<triangles>\n{t}\n</triangles></mesh></object>')


def build(caps, out):
    """caps: list of (cap name, [(part name, trimesh, filament number), ...]).
    Each cap becomes one object; caps sit 25 mm apart, 4 to a row."""
    res, builds, cfgs, nid = [], [], [], 1
    for k, (name, items) in enumerate(caps):
        comps, parts = [], []
        for pname, m, fil in items:
            res.append(mesh_xml(nid, pname, m))
            comps.append(f'<component objectid="{nid}"/>')
            parts.append(f'<part id="{nid}" subtype="normal_part"><metadata key="name" value="{pname}"/>'
                         f'<metadata key="extruder" value="{fil}"/></part>')
            nid += 1
        top = nid; nid += 1
        res.append(f'<object id="{top}" name="{name}" type="model"><components>' + "".join(comps) + '</components></object>')
        cols = min(4, len(caps)); rows = (len(caps) + cols - 1) // cols
        x = 128 + (k % cols - (cols - 1) / 2) * 25
        y = 128 + ((rows - 1) / 2 - k // cols) * 25
        builds.append(f'<item objectid="{top}" transform="1 0 0 0 1 0 0 0 1 {x:.1f} {y:.1f} 0"/>')
        cfgs.append(f'<object id="{top}"><metadata key="name" value="{name}"/><metadata key="extruder" value="1"/>'
                    + "".join(parts) + '</object>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<resources>' + "".join(res) + '</resources><build>' + "".join(builds) + '</build></model>')
    cfg = '<?xml version="1.0" encoding="UTF-8"?>\n<config>' + "".join(cfgs) + '</config>'
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?>\n'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
              '<Default Extension="config" ContentType="text/xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("Metadata/model_settings.config", cfg)


def cap(body):
    name = os.path.basename(body)[len("keycap_"):-len("_body.stl")]
    icon = body.replace("_body.stl", "_icon.stl")
    return name, [("body (black)", trimesh.load(body), 1), ("icon (white)", trimesh.load(icon), 2)]


if __name__ == "__main__":
    caps = [cap(b) for b in sorted(glob.glob(os.path.join(HERE, "stl", "keycap_*_body.stl")))]
    for name, items in caps:
        build([(f"keycap {name}", items)], os.path.join(HERE, f"keycap_{name}.3mf"))
    build([(f"keycap {n}", it) for n, it in caps], os.path.join(HERE, "keycaps_all.3mf"))
    print("built", len(caps), "caps + keycaps_all.3mf")

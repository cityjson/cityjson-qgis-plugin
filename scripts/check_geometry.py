"""
each face flows through it like this:

 CityJSON file ─┐
                ├→ faces ─→ check_face ─→ report
 QGIS layer ────┘           (planar? degenerate? self-intersecting?)


# Data shapes:
   ring = list of (x, y, z) corners, first corner not repeated
   face = list of rings, outer ring first, then holes


# Context

## for multisurface
CityJSON file
└── CityObjects
    └── "building1"
        └── geometry[0]
            └── boundaries           = list of faces
                ├── face 0           = list of rings
                │   ├── ring 0       = outer: list of vertex indices
                │   └── ring 1       = hole (optional)
                └── face 1
                    └── ring 0

## a building wigth 2 faces
"boundaries": [
  [ [0, 1, 2, 3], [4, 5, 6, 7] ],     ← face 0: outer ring + hole
  [ [0, 3, 8, 9] ]                    ← face 1: outer ring only
]

**Python**                          **Gives**                               **What it is**
boundaries	                        [[[0,1,2,3],[4,5,6,7]], [[0,3,8,9]]]	all faces
boundaries[0]	                    [[0,1,2,3],[4,5,6,7]]	                a face
boundaries[0][0]	                [0,1,2,3]	                            a ring: the outer one
boundaries[0][0][1]	                1	                                    a vertex index
vertices[1] → scale + translate	    (85001.0, 446000.0, 0.0)	            a corner

Run on a file:
    python scripts/check_geometry.py path/to/file.city.json
    python scripts/check_geometry.py path/to/file.city.json --tol 0.005

Run on an edited layer, in the QGIS Python console:
    import sys; sys.path.append(r"C:/path/to/cityjson-qgis-plugin")
    from scripts import check_geometry as cg
    cg.print_report(cg.check_faces(cg.faces_from_layer(iface.activeLayer())))
"""

import argparse
import json
import math

# Max distance (metres) a corner may sit off its face's plane.
# val3dity default: https://val3dity.readthedocs.io/main/usage/
PLANARITY_TOL = 0.01

# Below this, a length or area counts as zero (float maths is never exactly 0).
ZERO = 1e-12

# Two edges closer than this (metres) count as touching: 0.001 mm.
# Far below the 1 mm vertex precision of a CityJSON file (scale 0.001).
TOUCH_TOL = 1e-6

# Tolerances reported side by side in the summary, so the result
# does not hinge on one choice: 1 mm, 1 cm, 5 cm.
SWEEP_TOLS = (0.001, 0.01, 0.05)

# Only these geometry types are made of faces.
SURFACE_TYPES = {
    "MultiSurface",
    "CompositeSurface",
    "Solid",
    "MultiSolid",
    "CompositeSolid",
}


# Plain maths


def centroid(ring):
    """Average corner of a ring."""
    n = len(ring)
    total_x = 0
    total_y = 0
    total_z = 0
    for p in ring:
        total_x += p[0]
        total_y += p[1]
        total_z += p[2]
    cx, cy, cz = total_x / n, total_y / n, total_z / n
    return (cx, cy, cz)


def newell_normal(ring):
    """
    gives the direction of the plane.
    (nx, ny, nz) is the normal: the direction of the fitted plane.
    Its length is 2 x the face area.
    """
    # A. centroid
    cx, cy, cz = centroid(ring)

    # B. shift every corner by minus the centroid
    shifted_ring = []
    for p in ring:
        x = p[0] - cx
        y = p[1] - cy
        z = p[2] - cz
        shifted_ring.append((x, y, z))

    # C. sum the cross products of each corner with the next one
    nx = 0
    ny = 0
    nz = 0

    n = len(shifted_ring)
    for p in range(n):
        next_corner = p + 1
        if next_corner == n:
            next_corner = 0
        corner = shifted_ring[p]
        next_cor = shifted_ring[next_corner]

        xi, yi, zi = corner
        xj, yj, zj = next_cor
        nx += (yi * zj) - (zi * yj)
        ny += (zi * xj) - (xi * zj)
        nz += (xi * yj) - (yi * xj)

    return (nx, ny, nz)


def planarity_deviation(face):
    """Face -> how far the worst corner sits off the plane (metres).

    Returns None if the face has no plane (zero area).
    """
    outer_ring = face[0]
    nx, ny, nz = newell_normal(outer_ring)
    length_n = math.sqrt(nx * nx + ny * ny + nz * nz)

    # a normal's length is exactly 2 x the face area
    # if a face has zero area, there's nothing to fit a plane to
    # ex: all corners on one line
    if length_n < ZERO:
        return None

    # scale to length 1 (unit vector)
    ux, uy, uz = nx / length_n, ny / length_n, nz / length_n

    cx, cy, cz = centroid(outer_ring)

    max_d = 0
    for ring in face:  # outer ring + any holes
        for p in ring:  # every corner of that ring
            d = abs(
                ux * (p[0] - cx) + uy * (p[1] - cy) + uz * (p[2] - cz)
            )  # dot product
            if d > max_d:
                max_d = d  # keep the biggest distance

    return max_d


def is_degenerate(face):
    """Face -> True if it isn't really a face, or a ring repeats a corner.

    Three ways a ring can fail, and every ring is checked (outer + holes):
      1. fewer than 3 different corners
      2. the same corner twice in a row
            (val3dity error 102; the last corner counts as next to the first)
      3. zero area
    """
    for ring in face:
        # 1. count different corners: a set throws away exact repeats
        different_corners = set(ring)
        if len(different_corners) < 3:
            return True

        # 2. a corner equal to the next one: an edge of length zero
        n = len(ring)
        for i in range(n):
            if ring[i] == ring[(i + 1) % n]:
                return True

        # 3. zero area: the normal's length is 2 x area, so length ~0 means area ~0
        nx, ny, nz = newell_normal(ring)
        length_n = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length_n < ZERO:
            return True

    return False


def _flatten_to_2d(face):
    """Helper for is_self_intersecting: turn a 3D face into a 2D drawing.

    Idea: This looks at the face from the side it faces most, and get rid of the
    third coordinate. A roof (normal points up) is looked at from above,
    so we drop z. A wall facing east is looked at from the east, so we drop x.

    We drop the axis where the normal is biggest. That is the only choice
    that never squashes the face into a line.

    If the face has no usable normal (a bow-tie's two halves cancel out),
    fall back to dropping the axis where the face is thinnest.
    """
    nx, ny, nz = newell_normal(face[0])
    sizes = (abs(nx), abs(ny), abs(nz))

    if max(sizes) < ZERO:
        # no normal: measure how wide the face is along x, y and z
        all_corners = [p for ring in face for p in ring]
        sizes = []
        for axis in range(3):
            values = [p[axis] for p in all_corners]
            sizes.append(-(max(values) - min(values)))  # minus: thinnest wins below

    drop = sizes.index(max(sizes))  # 0 = drop x, 1 = drop y, 2 = drop z
    keep = [axis for axis in range(3) if axis != drop]

    flat_face = []
    for ring in face:
        flat_ring = [(p[keep[0]], p[keep[1]]) for p in ring]
        flat_face.append(flat_ring)
    return flat_face


def _turn(a, b, c):
    """Helper: walking a -> b -> c, do we turn left (+), right (-) or go straight (0)?

    This is the 2D cross product of (b - a) and (c - a).
    """
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _edges_cross(a, b, c, d):
    """Helper: does edge a-b properly cross edge c-d?

    They cross when c and d are on opposite sides of a-b,
    AND a and b are on opposite sides of c-d.
    (Edges that only touch at an end, or lie on top of each other,
    are not counted here.)
    """
    t1 = _turn(a, b, c)
    t2 = _turn(a, b, d)
    t3 = _turn(c, d, a)
    t4 = _turn(c, d, b)
    opposite_1 = (t1 > ZERO and t2 < -ZERO) or (t1 < -ZERO and t2 > ZERO)
    opposite_2 = (t3 > ZERO and t4 < -ZERO) or (t3 < -ZERO and t4 > ZERO)
    return opposite_1 and opposite_2


def _point_on_edge(p, a, b):
    """Helper: does point p lie on edge a-b (within TOUCH_TOL metres)?

    Two questions:
      1. is p (almost) on the straight line through a and b?
         distance to the line = |turn(a, b, p)| / length of a-b
      2. is p between a and b, not further along the line?
    """
    edge_x, edge_y = b[0] - a[0], b[1] - a[1]
    length = math.sqrt(edge_x * edge_x + edge_y * edge_y)
    if length < ZERO:
        return False  # zero-length edge: is_degenerate catches that

    # 1. distance from p to the line through a and b
    if abs(_turn(a, b, p)) / length > TOUCH_TOL:
        return False

    # 2. how far along a -> b is p? 0 = at a, 1 = at b
    along = ((p[0] - a[0]) * edge_x + (p[1] - a[1]) * edge_y) / (length * length)
    margin = TOUCH_TOL / length
    return -margin <= along <= 1 + margin


def _edges_touch(a, b, c, d):
    """Helper: does edge a-b touch edge c-d, without properly crossing?

    They touch when an end of one edge lies on the other edge.
    This also catches two edges meeting at one shared corner (a "pinch").
    """
    return (
        _point_on_edge(c, a, b)
        or _point_on_edge(d, a, b)
        or _point_on_edge(a, c, d)
        or _point_on_edge(b, c, d)
    )


def is_self_intersecting(face):
    """Face -> True if any two of its edges cross, or two edges of one ring touch.

    Steps:
      1. flatten the face to 2D (see _flatten_to_2d)
      2. list every edge of every ring (outer + holes)
      3. test every pair of edges, skipping neighbours
         (neighbours share a corner, so they always "touch")

    Crossing counts everywhere: a bow-tie ring, or a hole poking out
    through the outer ring.
    Touching counts only inside one ring (val3dity error 104). A hole
    touching the outer ring at one point is allowed in CityJSON, so
    touching between different rings is not flagged.
    """
    flat_face = _flatten_to_2d(face)

    # 2. every edge, remembered with which ring it is in and its position
    edges = []
    for r, ring in enumerate(flat_face):
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            edges.append((r, i, n, ring[i], ring[j]))

    # 3. compare every pair once
    for k in range(len(edges)):
        for m in range(k + 1, len(edges)):
            r1, i1, n1, a, b = edges[k]
            r2, i2, _, c, d = edges[m]

            # skip neighbours: same ring and next to each other (incl. last + first)
            if r1 == r2:
                gap = abs(i1 - i2)
                if gap == 1 or gap == n1 - 1:
                    continue

            if _edges_cross(a, b, c, d):
                return True

            if r1 == r2 and _edges_touch(a, b, c, d):
                return True

    return False


# Checker: runs the three tests on a face, or on many faces.


def check_face(face, tol=PLANARITY_TOL):
    """Runs planarity_deviation(), is_degenerate(), is_self_intersecting().

    Returns a dict of result:
      deviation          max distance off the plane (None if degenerate)
      non_planar         deviation > tol
      degenerate         see is_degenerate
      self_intersecting  see is_self_intersecting
    """
    degenerate = is_degenerate(face)
    deviation = planarity_deviation(face)
    non_planar = deviation is not None and deviation > tol

    # a degenerate face has no proper shape, so the crossing test means nothing
    self_intersecting = False
    if not degenerate:
        self_intersecting = is_self_intersecting(face)

    return {
        "deviation": deviation,
        "non_planar": non_planar,
        "degenerate": degenerate,
        "self_intersecting": self_intersecting,
    }


def check_faces(tagged_faces, tol=PLANARITY_TOL):
    """Runs check_face on every face that comes out of a faces_from_... function.

    Returns a list of results. Each result is the check_face dict plus the tags:
    object id, lod, geometry number and face number.
    """
    results = []
    for tags, face in tagged_faces:
        result = check_face(face, tol)
        result.update(tags)
        result["corners"] = sum(len(ring) for ring in face)
        results.append(result)
    return results


def print_report(results, tol=PLANARITY_TOL):
    """Prints every face with a problem, then a summary with counts."""
    problems = [
        r
        for r in results
        if r["non_planar"] or r["degenerate"] or r["self_intersecting"]
    ]

    print(f"Checked {len(results)} faces, tolerance {tol * 100:g} cm")
    print()

    for r in problems:
        what = []
        if r["degenerate"]:
            what.append("degenerate")
        if r["self_intersecting"]:
            what.append("self-intersecting")
        if r["non_planar"]:
            what.append(f"non-planar ({r['deviation'] * 100:.2f} cm)")
        where = f"{r['id']}  lod {r['lod']}  geometry {r['geometry']}  face {r['face']}"
        print(f"  {where}: {', '.join(what)}")

    if problems:
        print()

    print("Summary")
    print(f"  degenerate:        {sum(r['degenerate'] for r in results)}")
    print(f"  self-intersecting: {sum(r['self_intersecting'] for r in results)}")
    for t in SWEEP_TOLS:
        count = sum(r["deviation"] is not None and r["deviation"] > t for r in results)
        print(f"  non-planar > {t * 100:g} cm: {count}")

    deviations = [r["deviation"] for r in results if r["deviation"] is not None]
    if deviations:
        print(f"  worst deviation:   {max(deviations) * 100:.3f} cm")


# Feeders: turn a CityJSON file or a QGIS layer into tagged faces.
# Each one gives back a list of (tags, face).


def _decode_vertices(citymodel):
    """Turn CityJSON's stored integers into real coordinates.

    Same formula as VerticesCache._transform_vertex in core/geometry.py:
        real = stored * scale + translate
    A file without "transform" (CityJSON 1.0) stores real coordinates directly.
    """
    transform = citymodel.get("transform", {})
    scale = transform.get("scale", [1, 1, 1])
    translate = transform.get("translate", [0, 0, 0])

    corners = []
    for v in citymodel["vertices"]:
        x = v[0] * scale[0] + translate[0]
        y = v[1] * scale[1] + translate[1]
        z = v[2] * scale[2] + translate[2]
        corners.append((x, y, z))
    return corners


def _faces_in_boundaries(boundaries):
    """Peel brackets off "boundaries" until we reach faces.

    Same walk as read_boundaries in core/geometry.py, so face number i here
    is polygon number i in QGIS.

      MultiSurface: [face, face, ...]
      Solid:        [shell, shell, ...]   shell = [face, face, ...]
      MultiSolid:   [solid, solid, ...]

    How to tell we've reached a face: a face is [ring, ring], and a ring is
    [index, index, ...]. So in a face, face[0][0] is a plain number.
    """
    faces = []
    for item in boundaries:
        if len(item) > 0 and len(item[0]) > 0 and isinstance(item[0][0], int):
            faces.append(item)  # it's a face
        else:
            faces += _faces_in_boundaries(item)  # one bracket deeper
    return faces


def faces_from_cityjson(citymodel):
    """CityJSON (already loaded as a dict) -> every face as (x, y, z) corners.

    Gives back a list of (tags, face). tags = {"id", "lod", "geometry", "face"}.

    Skipped, on purpose:
      - points and lines (no faces)
      - GeometryInstance (shared template geometry; checking the template
        once would be the right way, not per instance)
    """
    corners = _decode_vertices(citymodel)
    tagged_faces = []

    for obj_id, obj in citymodel.get("CityObjects", {}).items():
        for g, geometry in enumerate(obj.get("geometry", [])):
            if geometry.get("type") not in SURFACE_TYPES:
                continue

            for f, index_face in enumerate(
                _faces_in_boundaries(geometry["boundaries"])
            ):
                # swap every vertex index for its real corner
                face = []
                for index_ring in index_face:
                    face.append([corners[i] for i in index_ring])

                tags = {
                    "id": obj_id,
                    "lod": geometry.get("lod"),
                    "geometry": g,
                    "face": f,
                }
                tagged_faces.append((tags, face))

    return tagged_faces


def faces_from_layer(layer):
    """Edited QGIS layer -> the same kind of tagged faces, for the experiment.

    Runs inside QGIS only. Not covered by the tests (they run without QGIS):
    try it in the QGIS Python console first.

    Each feature's geometry is a MultiPolygonZ: a list of polygons, and each
    polygon is one face (exterior ring + interior rings = holes).
    QGIS repeats the first corner at the end of a ring; CityJSON doesn't,
    so we drop it to match our ring shape.
    """
    field_names = layer.fields().names()
    tagged_faces = []

    for feature in layer.getFeatures():
        obj_id = feature["uid"] if "uid" in field_names else feature.id()
        lod = feature["lod"] if "lod" in field_names else None

        shape = feature.geometry().constGet()
        if shape is None:
            continue

        # a MultiPolygon holds several polygons; a plain Polygon is just one
        if hasattr(shape, "numGeometries"):
            polygons = [shape.geometryN(i) for i in range(shape.numGeometries())]
        else:
            polygons = [shape]

        for f, polygon in enumerate(polygons):
            qgis_rings = [polygon.exteriorRing()]
            for k in range(polygon.numInteriorRings()):
                qgis_rings.append(polygon.interiorRing(k))

            face = []
            for qgis_ring in qgis_rings:
                ring = []
                for j in range(qgis_ring.numPoints()):
                    ring.append((qgis_ring.xAt(j), qgis_ring.yAt(j), qgis_ring.zAt(j)))
                if len(ring) > 1 and ring[0] == ring[-1]:
                    ring.pop()  # drop the repeated closing corner
                face.append(ring)

            tags = {"id": obj_id, "lod": lod, "geometry": 0, "face": f}
            tagged_faces.append((tags, face))

    return tagged_faces


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def main(argv=None):
    """CLI: python scripts/check_geometry.py file.city.json --tol 0.01, prints the report."""
    parser = argparse.ArgumentParser(
        description="Report non-planar, degenerate and self-intersecting faces."
    )
    parser.add_argument("path", help="CityJSON file to check")
    parser.add_argument(
        "--tol",
        type=float,
        default=PLANARITY_TOL,
        help=f"planarity tolerance in metres (default {PLANARITY_TOL}, the val3dity default)",
    )
    args = parser.parse_args(argv)

    with open(args.path, encoding="utf-8") as file:
        citymodel = json.load(file)

    results = check_faces(faces_from_cityjson(citymodel), args.tol)
    print_report(results, args.tol)


if __name__ == "__main__":
    main()

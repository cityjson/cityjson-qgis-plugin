"""Writes QGIS layers back out as CityJSON."""

import json
import copy
from . import subset
from .layers import _stringify_attribute
from .geometry import (
    GeometryReader,
    VerticesCache,
    read_boundaries,
    DEFAULT_SCALE,
    DEFAULT_TRANSLATE,
)
from .utils import createCityJSON, get_centroid


class CityJSONExporter:
    """Rebuilds a CityJSON model from QGIS layers."""

    def __init__(
        self,
        layers,
        citymodel=None,
        loaded_lod="All",
        keep_unloaded=True,
        semantic_surfaces=False,
        bbox=None,
    ):
        self.layers = layers
        self.citymodel = citymodel
        self.loaded_lod = loaded_lod  # tells the exporter which lod was loaded in qgis
        self.keep_unloaded = keep_unloaded  # what should happen to never loaded things, users decision (keep: default or False : drop)
        self.semantic_surfaces = semantic_surfaces  # true if surfaces were loaded as separate rows (one row per face)
        self.bbox = (
            bbox  # [xmin, ymin, xmax, ymax] in the model's CRS; None = everything
        )

    def export(self) -> dict:  # returns a dictionary representing the CityJSON model
        """
        Export the configured layers as a CityJSON model dictionary.
        1. Create a new CityJSON model with the same version and transform as the original.
        2. Get the surviving IDs from the layers (plus never-loaded objects if keep_unloaded).
        3. For each surviving ID, copy the corresponding CityObject from the original model to the new model.
        4. If keep_unloaded is False, drop geometry entries not at the loaded LoD.
        5. Drop geometry entries whose LoD row was deleted in QGIS.
        6. Rebuild the vertices array from the surviving CityObjects, and update array indices.
        """

        new_cm = createCityJSON()
        new_cm["version"] = self.citymodel["version"]  # copy version
        if "transform" in self.citymodel:  # copy transform if it exists
            new_cm["transform"] = self.citymodel["transform"]

        surviving_ids = self.get_surviving_ids()
        if self.bbox is not None:  # crop to the box
            surviving_ids = self._in_bbox(surviving_ids)
        counts = self._count_rows()
        if self.semantic_surfaces:  # refuse partial surface deletes
            self._check_surface_rows(counts)
        # X10
        edited = self._edited_uids()  # refuse geometry edits (X10)
        if edited:
            raise ValueError(
                "Geometry editing isn't supported. Edited in QGIS: "
                + ", ".join(edited)
                + ". Discard the geometry edits (Toggle Editing → Discard) and export again."
            )
        # x10 end

        has_lod_rows = False  # assume no lod column
        for _uid, lod in counts:
            if lod is not None:
                has_lod_rows = True
                break

        for uid in self.citymodel[
            "CityObjects"
        ]:  # copy the CityObject to the new model, if it exists in the surviving IDs
            if uid in surviving_ids:
                new_cm["CityObjects"][uid] = copy.deepcopy(
                    self.citymodel["CityObjects"][uid]
                )  # copy the CityObject to the new model

        # if the user decides to drop the unloaded lods get rid of them:
        if not self.keep_unloaded:  # if keep_unloaded is false then enters in this loop
            reader = GeometryReader(
                VerticesCache(),
                self.citymodel.get("geometry-templates"),
                lod=self.loaded_lod,
            )  # builds the lod checker

            for obj in new_cm["CityObjects"].values():  # each object
                kept = []
                for geom in obj.get(
                    "geometry", []
                ):  # each geometry of this object (g1,g2; g1 = {"type": "MultiSurface", "lod": "1", "boundaries": [...]},  # LoD1 cube)
                    if reader.has_lod(
                        [geom], self.loaded_lod
                    ):  # is this the loaded lod?
                        kept.append(geom)
                if (
                    "geometry" in obj
                ):  # handles geometry less objects such as CityObjectGroup
                    obj["geometry"] = (
                        kept  # replace with only the loaded-LoD geometries
                    )

        # drop geometry entries whose lod row was deleted in qgis; the object survives if any row survives
        if has_lod_rows:
            reader = GeometryReader(
                VerticesCache(),
                self.citymodel.get("geometry-templates"),
                lod=self.loaded_lod,
            )
            for uid, obj in new_cm["CityObjects"].items():  # each surviving object
                kept = []
                for geom in obj.get("geometry", []):  # each geometry of this object
                    was_loaded = reader.has_lod(
                        [geom], self.loaded_lod
                    )  # was it shown in qgis?
                    lod = str(reader.get_lod(geom))  # e.g. "2"
                    if not was_loaded:
                        kept.append(geom)  # never loaded: keep
                    elif (uid, lod) in counts:
                        kept.append(geom)  # row still exists: keep
                    # else: row deleted, drop
                if "geometry" in obj:
                    obj["geometry"] = kept

        # apply the attribute edits to the copied model, so that the new model has the same attributes as the original model, except for the edits made in QGIS
        self.apply_attribute_edits(new_cm)

        # rebuild the vertices array from the surviving CityObjects, and update array indices
        subset.process_geometry(self.citymodel, new_cm)
        if "appearance" in self.citymodel:  # copy appearance if it exists
            subset.process_appearance(self.citymodel, new_cm)
        if "metadata" in self.citymodel:  # copy metadata if it exists
            new_cm["metadata"] = self.citymodel["metadata"]
        if (
            "geometry-templates" in self.citymodel
        ):  # copy geometry-templates if it exists
            subset.process_templates(self.citymodel, new_cm)
        # prune dangling children from the new model
        self.prune_dangling_children(new_cm, surviving_ids)
        return new_cm

    def _count_rows(
        self,
    ):  # "_" at the start of function is python convention for this method is only used inside this class
        counts = {}  # {(uid, lod): number of rows}.
        for layer in self.layers:
            has_lod = "lod" in layer.fields().names()  # checks if lod column exists
            for feature in layer.getFeatures():
                uid = feature["uid"]  # uid of this row
                lod = feature["lod"] if has_lod else None
                key = (uid, lod)
                if (
                    key in counts
                ):  # count rows per (uid, lod); one object can have several rows
                    counts[key] = counts[key] + 1
                else:
                    counts[key] = 1
        return counts

    def _count_faces(self, geom):
        """Number of faces (polygons) in one geometry."""
        if geom["type"] == "GeometryInstance":  # faces live in the template
            geom = self.citymodel["geometry-templates"]["templates"][geom["template"]]
        polygons, _semantics = read_boundaries(
            geom["boundaries"], None, None
        )  # none, none = dont look up semantics, only count
        return len(polygons)

    def _check_surface_rows(self, counts):
        """Raise if some, but not all, surface rows of an object were deleted."""
        reader = GeometryReader(
            VerticesCache(),
            self.citymodel.get("geometry-templates"),
            lod=self.loaded_lod,
        )
        for (uid, lod), rows in counts.items():
            obj = self.citymodel["CityObjects"][uid]
            faces = 0

            for geom in obj.get("geometry", []):
                if not reader.has_lod([geom], self.loaded_lod):
                    continue  # not loaded in qgis
                if lod is not None and str(reader.get_lod(geom)) != lod:
                    continue  # belongs to another lod's rows
                faces += self._count_faces(geom)
            expected = (
                faces if faces > 1 else 1
            )  # loader makes one row when there's only one face
            if rows < expected:
                raise ValueError(
                    f"{uid}: {rows} of {expected} surface rows left; deleting single surfaces is not supported"
                )

    def get_surviving_ids(self):
        """Ids that survive export: rows in QGIS, never-loaded objects (if kept), and their parents."""
        uids = set()  # set helps us avoid duplicates

        # Part 1: collects objects that has row in qgis
        for uid, lod in self._count_rows():
            uids.add(uid)

        # Part 2: add objects that were never loaded
        reader = GeometryReader(
            VerticesCache(),
            self.citymodel.get("geometry-templates"),
            lod=self.loaded_lod,
        )
        row_uids = set(uids)
        deleted = {  # loaded in QGIS but row gone: the user deleted it
            uid
            for uid, obj in self.citymodel["CityObjects"].items()
            if uid not in row_uids
            and reader.has_lod(obj.get("geometry", []), self.loaded_lod)
        }
        for uid, obj in self.citymodel["CityObjects"].items():
            if self.keep_unloaded and not reader.has_lod(
                obj.get("geometry", []), self.loaded_lod
            ):
                children = obj.get("children", [])
                if children and all(c in deleted for c in children):
                    continue  # never shown, and everything it contained was deleted: drop it too
                uids.add(uid)

        # a surviving child with a deleted parent is a dangling reference; a deleted child creates no such problem, so it stays deleted.
        # walk up every level: a resurrected parent may have deleted parents of its own
        todo = list(uids)
        while todo:
            obj = self.citymodel["CityObjects"][todo.pop()]
            for parent in obj.get("parents", []):
                if parent not in uids:
                    uids.add(parent)
                    todo.append(parent)

        return uids

    def _in_bbox(self, ids):
        """Keep ids whose centroid lies in self.bbox (same rule as get_subset_bbox),
        plus their parents and children."""
        xmin, ymin, xmax, ymax = self.bbox
        inside = set()
        for uid in ids:
            c = get_centroid(self.citymodel, uid)
            if c is not None and xmin <= c[0] < xmax and ymin <= c[1] < ymax:
                inside.add(uid)
        for uid in list(inside):
            obj = self.citymodel["CityObjects"][uid]
            for rel in obj.get("parents", []) + obj.get("children", []):
                if rel in ids:
                    inside.add(rel)
        return inside

    def prune_dangling_children(self, citymodel, surviving_ids):
        """Remove any CityObjects children from the parent parts"""
        for obj in citymodel["CityObjects"].values():
            if "children" in obj:
                obj["children"] = [
                    child for child in obj["children"] if child in surviving_ids
                ]
                if not obj["children"]:
                    del obj["children"]

    def apply_attribute_edits(self, new_cm):
        """Apply the attribute edits from the QGIS layers to the new CityJSON model."""
        for layer in self.layers:
            for feature in layer.getFeatures():
                uid = feature["uid"]
                if (
                    uid in new_cm["CityObjects"]
                ):  # is the key there? True/False, never crashes
                    obj = new_cm["CityObjects"][uid]  # only runs if it is, so it's safe
                    for i in layer.fields():
                        if i.name().startswith(
                            "attribute."
                        ):  # only consider fields that start with "attribute."
                            old_attribute_value = obj.get("attributes", {}).get(
                                i.name()[10:], None
                            )
                            expected_values_for_old_attribute = _stringify_attribute(
                                old_attribute_value
                            )
                            new_attribute_value = feature[i.name()]
                            if new_attribute_value != expected_values_for_old_attribute:
                                if isinstance(old_attribute_value, (dict, list)):
                                    try:
                                        parsed = json.loads(new_attribute_value)
                                    except (json.JSONDecodeError, TypeError) as exc:
                                        raise ValueError(
                                            f"{uid}: attribute '{i.name()[10:]}' is not valid JSON: {new_attribute_value}"
                                        ) from exc
                                    obj.setdefault("attributes", {})[i.name()[10:]] = (
                                        parsed
                                    )
                                else:
                                    obj.setdefault("attributes", {})[i.name()[10:]] = (
                                        new_attribute_value
                                    )

    # X10

    def _reference_reader(self):
        """Reader that rebuilds geometry with real coordinates, same as import."""
        if "transform" in self.citymodel:
            scale = self.citymodel["transform"]["scale"]
            translate = self.citymodel["transform"]["translate"]
        else:
            scale = DEFAULT_SCALE
            translate = DEFAULT_TRANSLATE

        self._scale = scale  # step 2 needs it for the scale/2 tolerance

        vertices_cache = VerticesCache(scale, translate, self.citymodel["vertices"])
        return GeometryReader(
            vertices_cache,
            self.citymodel.get("geometry-templates"),
            lod=self.loaded_lod,
        )

    def _corners(self, geom):
        """QgsGeometry -> parts -> rings -> (x, y, z) corners, in QGIS order."""
        if geom is None or geom.isNull() or geom.isEmpty():
            return []

        shape = geom.constGet()
        if hasattr(shape, "numGeometries"):  # MultiPolygon: several parts
            polygons = [shape.geometryN(i) for i in range(shape.numGeometries())]
        else:  # plain Polygon: one part
            polygons = [shape]

        parts = []
        for polygon in polygons:
            qgis_rings = [polygon.exteriorRing()]
            for k in range(polygon.numInteriorRings()):
                qgis_rings.append(polygon.interiorRing(k))

            rings = []
            for r in qgis_rings:  # closing corner kept: both sides have it
                rings.append(
                    [(r.xAt(j), r.yAt(j), r.zAt(j)) for j in range(r.numPoints())]
                )
            parts.append(rings)
        return parts

    def _same_geometry(self, a, b):
        """True if a and b have the same structure and every corner is within scale/2."""
        parts_a = self._corners(a)
        parts_b = self._corners(b)

        if len(parts_a) != len(parts_b):  # face added or deleted
            return False
        for rings_a, rings_b in zip(parts_a, parts_b):
            if len(rings_a) != len(rings_b):  # hole added or deleted
                return False
            for ring_a, ring_b in zip(rings_a, rings_b):
                if len(ring_a) != len(ring_b):  # corner added or deleted
                    return False
                for pa, pb in zip(ring_a, ring_b):
                    for i in range(3):  # x, y, z
                        if not abs(pa[i] - pb[i]) <= self._scale[i] / 2:  # corner moved
                            return False
        return True

    def _group_rows(self):
        """QGIS rows per building: {(uid, lod): [geometry, ...]} in file order."""
        groups = {}  # {(uid, lod): [(fid, geometry), ...]}
        for layer in self.layers:
            has_lod = "lod" in layer.fields().names()  # lod column exists?
            for feature in layer.getFeatures():
                key = (feature["uid"], feature["lod"] if has_lod else None)
                groups.setdefault(key, []).append((feature.id(), feature.geometry()))

        # sort each building's rows by fid = file order, then keep only the geometries
        return {
            key: [geom for _fid, geom in sorted(rows, key=lambda row: row[0])]
            for key, rows in groups.items()
        }

    def _reference_geoms(self, reader, uid, lod):
        """File version of one building, same shape as its _group_rows list."""
        geoms = self.citymodel["CityObjects"][uid].get("geometry", [])

        if lod is not None:  # LoD rows: only this LoD's geometry entries, file order
            geoms = [g for g in geoms if str(reader.get_lod(g)) == lod]

        if self.semantic_surfaces:  # one row per face → one geometry per face
            polygons, _semantics = reader.get_polygons(geoms)
            return [reader.polygons_to_geometry([p]) for p in polygons]

        return [reader.read_geometry(geoms)]  # one row → one geometry

    def _edited_uids(self):
        """uids whose geometry in QGIS differs from the original file."""
        reader = self._reference_reader()  # also sets self._scale
        edited = []
        for (uid, lod), qgis_geoms in self._group_rows().items():
            if uid not in self.citymodel["CityObjects"]:  # drawn in QGIS, not in file
                edited.append(uid)
                continue
            file_geoms = self._reference_geoms(reader, uid, lod)
            if len(qgis_geoms) != len(file_geoms):  # row count differs
                edited.append(uid)
                continue
            for a, b in zip(qgis_geoms, file_geoms):
                if not self._same_geometry(a, b):
                    edited.append(uid)
                    break
        return sorted(set(edited))  # one name per building, even with several LoD rows


def read_provenance(layers):
    """Group stamped layers by load_id and read their load settings back."""
    groups = {}
    for layer in layers:
        load_id = layer.customProperty("cityjson/load_id")
        if not load_id:
            continue  # not loaded by this plugin
        group = groups.setdefault(
            load_id,
            {
                "source": layer.customProperty("cityjson/source"),
                "lod": json.loads(layer.customProperty("cityjson/lod")),
                "semantic_surfaces": json.loads(
                    layer.customProperty("cityjson/semantic_surfaces")
                ),
                "keep_parent_attributes": json.loads(
                    layer.customProperty("cityjson/keep_parent_attributes")
                ),
                "layers": [],
            },
        )
        group["layers"].append(layer)

    for group in groups.values():
        if sum(layer.featureCount() for layer in group["layers"]) == 0:
            raise ValueError(
                f"The layers loaded from {group['source']} are empty. Temporary layers "
                "lose their contents when a project is reopened. Load the file again."
            )
    return groups


def save_cityjson_model(citymodel: dict, filepath: str) -> None:
    """Save a CityJSON model dictionary to a file."""
    with open(filepath, "w", encoding="utf-8", buffering=8192) as fstream:
        content = json.dumps(citymodel, separators=(",", ":"))
        fstream.write(content)

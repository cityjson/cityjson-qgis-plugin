# ******************************************************************************
# Project: CityJsonLoader - A QGIS Plugin.
#
# Purpose: This plugin allows for CityJSON files to be loaded in QGIS.
#
# GitHub page: https://github.com/cityjson/cityjson-qgis-plugin
#
# Contact: G.Stavropoulou@tudelft.nl
# ******************************************************************************
#
# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ******************************************************************************
"""A module to provide classes for reading geometries of CityJSON"""

from typing import Any, Sequence

from qgis.core import QgsGeometry, QgsLineString, QgsMultiPolygon, QgsPoint, QgsPolygon

DEFAULT_SCALE = (1, 1, 1)
DEFAULT_TRANSLATE = (0, 0, 0)


class VerticesCache:
    """A class to hold the list of vertices of the city model"""

    def __init__(
        self,
        scale: Sequence[float] = DEFAULT_SCALE,
        translate: Sequence[float] = DEFAULT_TRANSLATE,
        vertices: list[list[float]] | None = None,
    ) -> None:
        self._scale = scale
        self._translate = translate
        self._vertices: list[QgsPoint] = []

        if vertices is not None:
            self._vertices = [None] * len(vertices)
            for i, vertex in enumerate(vertices):
                self._vertices[i] = self._transform_vertex(vertex)

    def _transform_vertex(self, vertex: list[float]) -> QgsPoint:
        """Transform and create QgsPoint in one operation"""
        x = vertex[0] * self._scale[0] + self._translate[0]
        y = vertex[1] * self._scale[1] + self._translate[1]
        z = vertex[2] * self._scale[2] + self._translate[2]
        return QgsPoint(x, y, z)

    def set_scale(self, scale: list[float]) -> None:
        """Sets the scale for coordinates of the list"""
        self._scale = scale

    def set_translation(self, translate: list[float]) -> None:
        """Sets the translation for coordinates of the list"""
        self._translate = translate

    def add_vertex(self, vertex: list[float]) -> None:
        """Add a vertex to the list"""
        point = self._transform_vertex(vertex)
        self._vertices.append(point)

    def get_vertex(self, index: int) -> QgsPoint:
        """Get the vertex of a specified index"""
        return self._vertices[index]


class TransformedVerticesCache:
    """A class that decorates a VerticesCache applying a decoration when vertices are requested"""

    def __init__(
        self,
        decorated: VerticesCache,
        translation: QgsPoint,
        transformation_matrix: list[float] | None = None,
    ) -> None:
        """Initialize with transformation parameters"""
        self._decorated = decorated
        self._translation = translation
        self._transformation_matrix = transformation_matrix or [
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        ]

    def get_vertex(self, index: int) -> QgsPoint:
        """Get the vertex at the specified index"""
        original_vertex = self._decorated.get_vertex(index)
        x = original_vertex.x() + self._translation.x()
        y = original_vertex.y() + self._translation.y()
        z = original_vertex.z() + self._translation.z()

        return QgsPoint(x, y, z)


class GeometryReader:
    """A class that translates CityJSON geometries to QgsGeometry"""

    def __init__(
        self,
        vertices_cache: VerticesCache,
        geometry_templates: dict[str, Any] | None = None,
        lod: str | list[str] = "All",
    ) -> None:
        self._vertices_cache = vertices_cache
        self._skipped_geometries = 0
        self._geometry_templates = geometry_templates
        self.lod = lod

        if self._geometry_templates is None:
            self._templates_vertices_cache = VerticesCache()
        else:
            assert geometry_templates is not None
            template_vertex_cache = VerticesCache()
            for vertex in geometry_templates["vertices-templates"]:
                template_vertex_cache.add_vertex(vertex)
            self._templates_vertices_cache = template_vertex_cache

    def read_geometry(self, geometry: list[dict[str, Any]]) -> QgsGeometry:
        """Reads a CityJSON geometry and returns it as QgsGeometry"""
        polygons, _ = self.get_polygons(geometry)

        return self.polygons_to_geometry(polygons)

    def has_lod(
        self, geometries: list[dict[str, Any]], target_lod: str | list[str]
    ) -> bool:
        """Checks if any geometry in the list matches the specified LoD"""
        if target_lod == "All":
            return True

        if isinstance(target_lod, list):
            return any(self.get_lod(geom) in target_lod for geom in geometries)

        return any(self.get_lod(geom) == target_lod for geom in geometries)

    def get_lod(self, geometry: dict[str, Any]) -> str | None:
        """Returns the lod of a give geometry"""
        if geometry["type"] == "GeometryInstance":
            assert self._geometry_templates is not None
            geom_index = geometry["template"]
            return self._geometry_templates["templates"][geom_index].get("lod", None)
        else:
            return geometry.get("lod", None)

    def polygons_to_geometry(self, polygons: list[Any]) -> QgsGeometry:
        """Returns a QgsGeometry object from a list of polygons"""
        geoms = QgsMultiPolygon()
        for polygon in polygons:
            g = self.read_polygon(polygon)
            geoms.addGeometry(g)

        return QgsGeometry(geoms)

    def get_polygons(
        self, geometry: list[dict[str, Any]], attributes: list[str] | None = None
    ) -> tuple[list[Any], list[Any]]:
        """Returns a dictionary where keys are polygons and values are the semantic surfaces"""
        if attributes is None:
            attributes = []
        if geometry is None:
            return [], []

        polygons = []
        semantics = []

        for geom in geometry:
            if not self.has_lod([geom], self.lod) or not self.get_lod(geom):
                continue

            if geom["type"] == "GeometryInstance":
                assert self._geometry_templates is not None
                template_index = geom["template"]
                temp_geom = self._geometry_templates["templates"][template_index]
                translation = self._vertices_cache.get_vertex(geom["boundaries"][0])
                temp_vertices_cache: Any = TransformedVerticesCache(
                    self._templates_vertices_cache, translation
                )
            else:
                temp_geom = geom
                temp_vertices_cache = self._vertices_cache

            additional_semantics = {}
            if "semantics" in temp_geom:
                surfaces = temp_geom["semantics"]["surfaces"]
                values = temp_geom["semantics"]["values"]

                if len(attributes) > 2:
                    for attr in attributes:
                        attr = "+" + attr
                        if (
                            attr.lstrip("+") not in ["type", "on_footprint_edge"]
                            and attr in temp_geom["semantics"]
                        ):
                            additional_semantics[attr.lstrip("+")] = temp_geom[
                                "semantics"
                            ][attr][0]
            else:
                surfaces = None
                values = None

            try:
                new_polygons, new_semantics = read_boundaries(
                    temp_geom["boundaries"], surfaces, values
                )
                new_polygons = self.indexes_to_points(new_polygons, temp_vertices_cache)
                polygons += new_polygons

                if len(additional_semantics) > 0:
                    combined_semantics = []
                    for i, semantic in enumerate(new_semantics):
                        combined_semantics.append(
                            {
                                **semantic,
                                **{
                                    key: str(additional_semantics[key][i])
                                    for key in additional_semantics
                                },
                            }
                        )

                    semantics += combined_semantics
                else:
                    semantics += new_semantics

            except (KeyError, IndexError, TypeError):
                self._skipped_geometries += 1

        return polygons, semantics

    def indexes_to_points(self, polygons: list[Any], vertices_cache: Any) -> list[Any]:
        """Returns the indexed vertices to vertices with coordinates"""
        return [
            [[vertices_cache.get_vertex(index) for index in ring] for ring in polygon]
            for polygon in polygons
        ]

    def read_polygon(self, boundary: list[list[QgsPoint]]) -> QgsPolygon:
        """Reads the specified polygon"""
        g = QgsPolygon()

        for i, ring in enumerate(boundary):
            r = QgsLineString(ring)
            if i == 0:
                g.setExteriorRing(r)
            else:
                g.addInteriorRing(r)

        return g

    def skipped_geometries(self) -> int:
        """Returns the count of geometries that were skipped while reading"""
        return self._skipped_geometries


def read_boundaries(
    boundaries: list[Any], surfaces: list[Any] | None, values: Any
) -> tuple[list[Any], list[Any]]:
    """Return the polygons from a boundaries list"""
    polygons = []
    semantic_surfaces = []

    if isinstance(boundaries[0][0], list):
        if values is not None:
            values_iter = iter(values)
        else:
            values_iter = iter([None for i in range(len(boundaries))])
        for boundary in boundaries:
            new_polygons, new_semantic_surfaces = read_boundaries(
                boundary, surfaces, next(values_iter)
            )
            polygons += new_polygons
            semantic_surfaces += new_semantic_surfaces
    else:
        polygons.append(boundaries)
        if surfaces is None or values is None:
            semantic_surfaces.append(None)
        else:
            semantic_surfaces.append(surfaces[values])

    return polygons, semantic_surfaces

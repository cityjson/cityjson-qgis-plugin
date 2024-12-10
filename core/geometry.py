"""A module to provide classes for reading geometries of CityJSON"""

from qgis.core import QgsPoint, QgsGeometry, QgsLineString, QgsPolygon, QgsMultiPolygon

class VerticesCache:
    """A class to hold the list of vertices of the city model"""

    def __init__(self, scale=(1, 1, 1), translate=(0, 0, 0), vertices=None):
        self._scale = scale
        self._translate = translate
        self._vertices = []
        if vertices is not None:
            for vertex in vertices:
                self.add_vertex(vertex)

    def set_scale(self, scale):
        """Sets the scale for coordinates of the list"""
        self._scale = scale

    def set_translation(self, translate):
        """Sets the translation for coordinates of the list"""
        self._translate = translate

    def add_vertex(self, vertex):
        """Adds a vertex to the list

        Keywords:
        vertex - The original vertex coords from CityJSON
        """
        x = vertex[0] * self._scale[0] + self._translate[0]
        y = vertex[1] * self._scale[1] + self._translate[1]
        z = vertex[2] * self._scale[2] + self._translate[2]

        p = QgsPoint(x, y, z)
        self._vertices.append(p)

    def get_vertex(self, index):
        """Get the vertex of a specified index"""
        return self._vertices[index]

class TransformedVerticesCache:
    """A class that decorates a VerticesCache applying a decoration when
    vertices are requested.
    """

    def __init__(self, decorated, translation, transformation_matrix=None):
        """Initiates the transformed vertices cache with the provided
        transformation paremeters.

        Keyword arguments:
        decorated -- the original VerticesCache
        translation -- a QgsPoint to translation all coordinates by
        transformation_matrix -- a 4x4 matrix to rotate and scale coords
        """
        self._decorated = decorated
        self._translation = translation
        if transformation_matrix is None:
            self._transformation_matrix = [1.0, 0.0, 0.0, 0.0,
                                           0.0, 1.0, 0.0, 0.0,
                                           0.0, 0.0, 1.0, 0.0,
                                           0.0, 0.0, 0.0, 1.0]
        else:
            self._transformation_matrix = transformation_matrix

    def get_vertex(self, index):
        """Get the vertex at the specified index"""
        original_vertex = self._decorated.get_vertex(index)
        x = original_vertex.x() + self._translation.x()
        y = original_vertex.y() + self._translation.y()
        z = original_vertex.z() + self._translation.z()
        return QgsPoint(x, y, z)

class GeometryReader:
    """A class that translates CityJSON geometries to QgsGeometry"""

    def __init__(self, vertices_cache, geometry_templates=None, lod="All"):
        self._vertices_cache = vertices_cache
        self._skipped_geometries = 0
        self._geometry_templates = geometry_templates
        self.lod = lod
        
        if self._geometry_templates is None:
            self._templates_vertices_cache = VerticesCache()
        else:
            template_vertex_cache = VerticesCache()
            for vertex in geometry_templates["vertices-templates"]:
                template_vertex_cache.add_vertex(vertex)
            self._templates_vertices_cache = template_vertex_cache

    def read_geometry(self, geometry, lod="All"):
        """Reads a CityJSON geometry and returns it as QgsGeometry
        """
        polygons, _ = self.get_polygons(geometry, lod)

        return self.polygons_to_geometry(polygons)

    def has_lod(self, geometries, target_lod):
        """Checks if any geometry in the list matches the specified LoD."""
        if target_lod == "All":
            return True
        return any(self.get_lod(geom) == target_lod for geom in geometries)

    def get_lod(self, geometry):
        """Returns the lod of a give geometry"""
        if geometry["type"] == "GeometryInstance":
            geom_index = geometry["template"]
            return self._geometry_templates["templates"][geom_index].get("lod", None)
        else:
            return geometry.get("lod", None)

    def polygons_to_geometry(self, polygons):
        """Returns a QgsGeometry object from a list of polygons"""
        geoms = QgsMultiPolygon()
        for polygon in polygons:
            g = self.read_polygon(polygon)
            geoms.addGeometry(g)
        return QgsGeometry(geoms)

    def get_polygons(self, geometry, attributes={}):
        """Returns a dictionary where keys are polygons and values
        are the semantic surfaces
        """
        polygons = []
        semantics = []

        for geom in geometry:
            # Skip geometries that don't match the target LoD
            if not self.has_lod([geom], self.lod) or not self.get_lod(geom):
                continue

            if geom["type"] == "GeometryInstance":
                template_index = geom["template"]
                temp_geom = self._geometry_templates["templates"][template_index]
                translation = self._vertices_cache.get_vertex(geom["boundaries"][0])
                temp_vertices_cache = TransformedVerticesCache(self._templates_vertices_cache, translation)
            else:
                temp_geom = geom
                temp_vertices_cache = self._vertices_cache

            # Prepare a dictionary to hold surface attributes
            additional_semantics = {}
            try:
                if "semantics" in temp_geom:
                    surfaces = temp_geom["semantics"]["surfaces"]
                    values = temp_geom["semantics"]["values"]
                    if len(attributes) > 2:
                        # Collect additional attributes
                        for attr in attributes:
                            attr = '+' + attr
                            if attr.lstrip("+") not in ['type','on_footprint_edge'] and attr in temp_geom["semantics"]:
                                additional_semantics[attr.lstrip("+")] = temp_geom["semantics"][attr][0]
                else:
                    surfaces = None
                    values = None

                new_polygons, new_semantics = read_boundaries(temp_geom["boundaries"], surfaces, values)
                new_polygons = self.indexes_to_points(new_polygons, temp_vertices_cache)

                polygons += new_polygons

                if len(additional_semantics) > 0:
                    combined_semantics = []
                    for i, semantic in enumerate(new_semantics):
                        combined_semantics.append({
                            **semantic,
                            **{key: str(additional_semantics[key][i]) for key in additional_semantics.keys()}
                        })

                    semantics += combined_semantics
                else:
                    semantics += new_semantics

            except Exception as e:
                self._skipped_geometries += 1

        return polygons, semantics

    def indexes_to_points(self, polygons, vertices_cache):
        """Returns the indexed vertices to vertices with coordinates"""
        new_polygons = []
        for polygon in polygons:
            new_polygon = []
            for ring in polygon:
                new_ring = []
                for index in ring:
                    new_ring.append(vertices_cache.get_vertex(index))
                new_polygon.append(new_ring)
            new_polygons.append(new_polygon)

        return new_polygons

    def read_polygon(self, boundary):
        """Reads the specified polygon"""
        g = QgsPolygon()
        i = 0
        for ring in boundary:
            poly = []
            for point in ring:
                poly.append(point)

            r = QgsLineString(poly)
            if i == 0:
                g.setExteriorRing(r)
            else:
                g.addInteriorRing(r)
            i = 1

        return g

    def skipped_geometries(self):
        """Returns the count of geometries that were skipped while reading"""
        return self._skipped_geometries

def read_boundaries(boundaries, surfaces, values):
    """Return the polygons from a boundaries list"""
    polygons = []
    semantic_surfaces = []

    if isinstance(boundaries[0][0], list):
        if values is not None:
            values_iter = iter(values)
        else:
            values_iter = iter([None for i in range(len(boundaries))])
        for boundary in boundaries:
            new_polygons, new_semantic_surfaces = read_boundaries(boundary, surfaces, next(values_iter))
            polygons += new_polygons
            semantic_surfaces += new_semantic_surfaces
    else:
        polygons.append(boundaries)
        if surfaces is None or values is None:
            semantic_surfaces.append(None)
        else:
            semantic_surfaces.append(surfaces[values])

    return polygons, semantic_surfaces

"""A module to provide classes for reading geometries of CityJSON"""

from qgis.core import QgsPoint, QgsGeometry, QgsLineString, QgsPolygon, QgsMultiPolygon

class VerticesCache:
    """A class to hold the list of vertices of the city model"""

    def __init__(self, scale=(1, 1, 1), translate=(0, 0, 0)):
        self._vertices = []
        self._scale = scale
        self._translate = translate

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

class GeometryReader:
    """A class that translates CityJSON geometries to QgsGeometry"""

    def __init__(self, vertices_cache):
        self._vertices_cache = vertices_cache
        self._skipped_geometries = 0
        self._geometry_templates = None
        self._templates_geometry_reader = None

    def set_geometry_templates(self, geometry_templates):
        """Sets the geometry templates for the geometry reader"""
        if geometry_templates is not None:
            self._geometry_templates = geometry_templates

            template_vertex_cache = VerticesCache()
            for vertex in geometry_templates["vertices-templates"]:
                template_vertex_cache.add_vertex(vertex)
            self._templates_geometry_reader = GeometryReader(template_vertex_cache)

    def read_geometry(self, geometry):
        """Reads a CityJSON geometry and returns it as QgsGeometry
        """
        polygons, _ = self.get_polygons(geometry)

        return self.polygons_to_geometry(polygons)

    def get_lod(self, geometry):
        """Returns the lod of a give geometry"""
        if geometry["type"] == "GeometryInstance":
            geom_index = geometry["template"]
            return self._geometry_templates["templates"][geom_index]["lod"]
        else:
            return geometry["lod"]

    def polygons_to_geometry(self, polygons):
        """Returns a QgsGeometry object from a list of polygons"""
        geoms = QgsMultiPolygon()
        for polygon in polygons:
            g = self.read_polygon(polygon)
            geoms.addGeometry(g)
        return QgsGeometry(geoms)

    def get_polygons(self, geometry):
        """Returns a dictionary where keys are polygons and values
        are the semantic surfaces
        """
        polygons = []
        semantics = []

        for geom in geometry:
            try:
                if "semantics" in geom:
                    surfaces = geom["semantics"]["surfaces"]
                    values = geom["semantics"]["values"]
                else:
                    surfaces = None
                    values = None
                new_polygons, new_semantics = read_boundaries(geom["boundaries"], surfaces, values)
                polygons = polygons + new_polygons
                semantics = semantics + new_semantics
            except:
                self._skipped_geometries += 1

        return polygons, semantics

    def read_polygon(self, boundary):
        """Reads the specified polygon"""
        g = QgsPolygon()
        i = 0
        for ring in boundary:
            poly = []
            for index in ring:
                poly.append(self._vertices_cache.get_vertex(index))

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
            polygons = polygons + new_polygons
            semantic_surfaces = semantic_surfaces + new_semantic_surfaces
    else:
        polygons.append(boundaries)
        if surfaces is None or values is None:
            semantic_surfaces.append(None)
        else:
            semantic_surfaces.append(surfaces[values])

    return polygons, semantic_surfaces

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

    def read_geometry(self, geometry, lod_filter=None):
        """Reads a CityJSON geometry and returns it as QgsGeometry

        TODO: For now supports only Surfaces and Solids
        """
        geoms = QgsMultiPolygon()
        for geom in geometry:
            if lod_filter is not None and geom["lod"] != lod_filter:
                continue

            if "Surface" in geom["type"]:
                for boundary in geom["boundaries"]:
                    g = self.read_polygon(boundary)
                    geoms.addGeometry(g)
                continue
            if geom["type"] == "Solid":
                for solid in geom["boundaries"]:
                    for boundary in solid:
                        g = self.read_polygon(boundary)
                        geoms.addGeometry(g)
                continue
            self._skipped_geometries += 1
        return QgsGeometry(geoms)

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

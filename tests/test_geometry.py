import pytest

from core.geometry import GeometryReader, VerticesCache, read_boundaries
from tests.sample_geometries import *

class TestReadBoundaries:
    """A class to test the read_boundaries function"""

    def test_multisurface_reading(self):
        """Does read_boundaries retuns the correct polygons for
        a multisurface?
        """
        boundaries = example_multisurface_with_semantics[0]["boundaries"]
        surfaces = example_multisurface_with_semantics[0]["semantics"]["surfaces"]
        values = example_multisurface_with_semantics[0]["semantics"]["values"]

        polygons, semantic_surfaces = read_boundaries(boundaries, surfaces, values)

        assert len(polygons) == 5
        assert len(polygons[0][0]) == 4
        assert polygons[0] == [[0, 3, 2, 1]]

        assert len(semantic_surfaces) == 5
        assert [surface["type"] if surface is not None else None for surface in semantic_surfaces] \
                == ["WallSurface", "WallSurface", None, "RoofSurface", "Door"]

class TestGeometryReader:
    """A class that tests the geometry reader."""

    def create_vertices(self, number_of_vertices):
        """Creates an array with the specified number of vertices"""
        vertices = [[float(i), float(i), float(i)]
                    for i in range(number_of_vertices)]

        return vertices
    
    def test_create_vertices(self):
        """Tests the create_vertices function"""
        vertices = self.create_vertices(50)

        assert len(vertices) == 50

    def test_multisurface_with_semantics(self):
        """Tests if the geometry reader parses the correct amount of polygons
        for the example multisurface
        """
        vertices_cache = VerticesCache(vertices=self.create_vertices(50))
        geometry_reader = GeometryReader(vertices_cache)

        polygons, semantics = geometry_reader.get_polygons(example_multisurface_with_semantics)

        assert len(polygons) == 5
        assert len(semantics) == 5

    def test_solid_with_semantics(self):
        """Tests if the geometry reader parses the correct amount of polygons
        for the example solid
        """
        vertices_cache = VerticesCache(vertices=self.create_vertices(900))
        geometry_reader = GeometryReader(vertices_cache)

        polygons, semantics = geometry_reader.get_polygons(example_solid_with_semantics)

        assert len(polygons) == 8
        assert len(semantics) == 8

    def test_simple_composite_solid(self):
        """Tests if the geometry reader parses the correct amount of polygons
        for a simple composite solid
        """
        vertices_cache = VerticesCache(vertices=self.create_vertices(900))
        geometry_reader = GeometryReader(vertices_cache)

        polygons, _ = geometry_reader.get_polygons(example_composite_solid)

        assert len(polygons) == 12
    
    def test_get_lod_with_geometry_template(self):
        """Tests if the get_lod function works for geometry instances"""
        empty_vertices = VerticesCache()
        geometry_template = example_geometry_template
        geometry_reader = GeometryReader(empty_vertices, geometry_template)

        geom = example_geometry_instance[0]
        lod = geometry_reader.get_lod(geom)

        assert lod == 2
    
    def test_get_polygons_with_geometry_instance(self):
        """Tests if the geometry of a geometry instance is read properly"""
        empty_vertices = VerticesCache(vertices=self.create_vertices(900))
        geometry_template = example_geometry_template
        geometry_reader = GeometryReader(empty_vertices, geometry_template)

        geom = example_geometry_instance
        polygons, semantics = geometry_reader.get_polygons(geom)

        assert len(polygons) == 3
        for semantic in semantics:
            assert semantic is None
    
    def test_indices_to_points(self):
        """Tests the indexes_to_points function"""
        vertices = VerticesCache(vertices=[[0, 0, 0], [1, 1, 1], [2, 2, 2], [3, 3, 3]])
        geometry_reader = GeometryReader(vertices)
        
        polygons = [[[0, 1, 2, 3]]]
        new_polygons = geometry_reader.indexes_to_points(polygons, vertices)
        
        assert len(new_polygons) == 1

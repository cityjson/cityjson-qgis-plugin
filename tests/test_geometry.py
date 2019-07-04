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
    """A class that tests the geometry reader"""

    def test_multisurface_with_semantics(self):
        """Tests if the geometry reader parses the correct amount of polygons
        for the example multisurface
        """
        geometry_reader = GeometryReader(VerticesCache())

        polygons, semantics = geometry_reader.get_polygons(example_multisurface_with_semantics)

        assert len(polygons) == 5
        assert len(semantics) == 5

    def test_solid_with_semantics(self):
        """Tests if the geometry reader parses the correct amount of polygons
        for the example solid
        """
        geometry_reader = GeometryReader(VerticesCache())

        polygons, semantics = geometry_reader.get_polygons(example_solid_with_semantics)

        assert len(polygons) == 8
        assert len(semantics) == 8

    def test_simple_composite_solid(self):
        """Tests if the geometry reader parses the correct amount of polygons
        for a simple composite solid
        """
        geometry_reader = GeometryReader(VerticesCache())

        polygons, _ = geometry_reader.get_polygons(example_composite_solid)

        assert len(polygons) == 12
    
    def test_creation_with_geometry_template(self):
        """Tests if the geometry reader is created properly when a geometry
        template is provided
        """
        empty_vertices = VerticesCache()
        geometry_template = example_geometry_template
        geometry_reader = GeometryReader(empty_vertices)
        geometry_reader.set_geometry_templates(geometry_template)

        assert len(geometry_reader._templates_geometry_reader._vertices_cache._vertices) == len(example_geometry_template["vertices-templates"])
    
    def test_get_lod_with_geometry_template(self):
        """Tests if the get_lod function works for geometry instances"""
        empty_vertices = VerticesCache()
        geometry_template = example_geometry_template
        geometry_reader = GeometryReader(empty_vertices)
        geometry_reader.set_geometry_templates(geometry_template)

        geom = example_geometry_instance[0]
        lod = geometry_reader.get_lod(geom)

        assert lod == 2

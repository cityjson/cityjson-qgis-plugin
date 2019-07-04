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

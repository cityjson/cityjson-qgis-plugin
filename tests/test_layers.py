# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

from core.layers import (
    TypeNamingIterator,
    BaseFieldsBuilder,
    NullFieldsBuilder,
    AttributeFieldsDecorator,
    LodFieldsDecorator,
    SemanticSurfaceFieldsDecorator,
)

# cm = {
# "type": "CityJSON",
# "version": "2.0",
# "transform": {
#     "scale": [1.0, 1.0, 1.0],
#     "translate": [0.0, 0.0, 0.0]
# },
# "CityObjects": {
#             "id1": {"type": "Building"},
#             "id2": {"type": "Bridge"},
#             "id3": {"type": "Other"},},
# "vertices": []
# }

SINGLE_CUBE_CITYMODEL = {
    "CityObjects": {
        "id-1": {
            "geometry": [
                {
                    "boundaries": [
                        [
                            [[0, 1, 2, 3]],
                            [[4, 5, 1, 0]],
                            [[5, 6, 2, 1]],
                            [[6, 7, 3, 2]],
                            [[7, 4, 0, 3]],
                            [[7, 6, 5, 4]],
                        ]
                    ],
                    "lod": "1",
                    "type": "Solid",
                    "semantics": {
                        "surfaces": [
                            {"type": "RoofSurface", "material": "tile"},
                            {"type": "WallSurface", "material": "brick"},
                            {"type": "WallSurface", "material": "brick"},
                            {"type": "WallSurface", "material": "brick"},
                            {"type": "WallSurface", "material": "brick"},
                            {"type": "GroundSurface", "material": "concrete"},
                        ],
                        "values": [0, 1, 2, 3, 4, 5],
                    },
                }
            ],
            "attributes": {"function": "something"},
            "type": "GenericCityObject",
        }
    },
    "type": "CityJSON",
    "version": "2.0",
    "vertices": [
        [0, 0, 1000],
        [1000, 0, 1000],
        [1000, 1000, 1000],
        [0, 1000, 1000],
        [0, 0, 0],
        [1000, 0, 0],
        [1000, 1000, 0],
        [0, 1000, 0],
    ],
    "metadata": {"geographicalExtent": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]},
    "transform": {"scale": [0.001, 0.001, 0.001], "translate": [0.0, 0.0, 0.0]},
    "extensions": {},
}
TWO_CUBES_CITYMODEL = {
    "CityObjects": {
        "id-1": {
            "geometry": [
                {
                    "boundaries": [
                        [[0, 1, 2, 3]],
                        [[7, 4, 0, 3]],
                        [[4, 5, 1, 0]],
                        [[5, 6, 2, 1]],
                        [[3, 2, 6, 7]],
                        [[6, 5, 4, 7]],
                    ],
                    "lod": "1",
                    "type": "MultiSurface",
                }
            ],
            "type": "GenericCityObject",
        }
    },
    "type": "CityJSON",
    "version": "2.0",
    "vertices": [
        [1.0, 0.0, 1.0],
        [0.0, 1.0, 1.0],
        [-1.0, 0.0, 1.0],
        [0.0, -1.0, 1.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [-1.0, 0.0, 0.0],
        [0.0, -1.0, 0.0],
    ],
    "metadata": {"geographicalExtent": [-1.0, -1.0, 0.0, 1.0, 1.0, 1.0]},
    "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
}
CITYMODEL_WITH_ATTRIBUTES = {
    "type": "CityJSON",
    "version": "2.0",
    "CityObjects": {
        "id-1": {"type": "Building", "attributes": {"attribute1": 1, "attribute2": 2}},
        "id-2": {"type": "Building", "attributes": {"attribute1": 1, "attribute3": 2}},
    },
    "vertices": [],
    "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
}


class TestTypeNamingIterator:
    """A class to test the TypeNamingIterator class"""

    def test_list_of_layer_names(self):
        """Tests if the amount of types found in the two cubes example CityJSON
        is identified and named properly
        """
        type_naming_iter = TypeNamingIterator("two_cubes", TWO_CUBES_CITYMODEL)

        layers = list(type_naming_iter.all_layers())
        assert len(layers) == 1
        assert layers[0] == "two_cubes - GenericCityObject"


class TestFieldBuilders:
    """A class to test the field builders"""

    def test_base_field_builder(self):
        """Tests that BaseFieldsBuilder builds the 4 fields:
        uid, type, parents and children"""
        builder = BaseFieldsBuilder()

        fields = builder.get_fields()

        assert len(fields) == 4
        assert fields[0].name() == "uid"
        assert fields[1].name() == "type"
        assert fields[2].name() == "parents"
        assert fields[3].name() == "children"

    def test_attributes_fields_builder(self):
        """Tests that AttributeFieldsDecorator creates the attributes of the model"""
        builder = NullFieldsBuilder()
        builder = AttributeFieldsDecorator(builder, CITYMODEL_WITH_ATTRIBUTES)

        fields = builder.get_fields()
        field_names = [field.name() for field in fields]

        assert len(fields) == 3
        assert "attribute.attribute1" in field_names
        assert "attribute.attribute2" in field_names
        assert "attribute.attribute3" in field_names

    def test_lod_fields_builder(self):
        """Tests that LodFieldsBuilder create the lod field"""
        builder = NullFieldsBuilder()
        builder = LodFieldsDecorator(builder)

        fields = builder.get_fields()

        assert len(fields) == 1
        assert fields[0].name() == "lod"

    def test_semantic_surface_fields_builder(self):
        """Tests the SemanticSurfaceFieldsDecorator
        creates the semantic surface fields"""

        builder = NullFieldsBuilder()
        builder = SemanticSurfaceFieldsDecorator(builder, SINGLE_CUBE_CITYMODEL)

        fields = builder.get_fields()

        assert len(fields) == 2
        assert fields[0].name() == "surface.type"
        assert fields[1].name() == "surface.material"

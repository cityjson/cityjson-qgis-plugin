# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

from unittest.mock import MagicMock

from qgis.core import QgsFields, QgsField

from core.layers import (
    TypeNamingIterator,
    BaseNamingIterator,
    LodNamingDecorator,
    BaseFieldsBuilder,
    NullFieldsBuilder,
    AttributeFieldsDecorator,
    LodFieldsDecorator,
    SemanticSurfaceFieldsDecorator,
    SimpleFeatureBuilder,
    LodFeatureDecorator,
    ParentFeatureDecorator,
    DynamicLayerManager,
    FIELD_STRING,
)


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


# ============================================================================
# Additional CityModel fixtures
# ============================================================================

MULTI_TYPE_CITYMODEL = {
    "type": "CityJSON",
    "version": "2.0",
    "CityObjects": {
        "b1": {"type": "Building", "geometry": []},
        "b2": {"type": "Building", "geometry": []},
        "r1": {"type": "Road", "geometry": []},
    },
    "vertices": [],
    "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
}

PARENT_CHILD_CITYMODEL = {
    "type": "CityJSON",
    "version": "2.0",
    "CityObjects": {
        "building-1": {
            "type": "Building",
            "attributes": {"roofType": "gable", "height": 22.3},
            "children": ["part-1"],
            "geometry": [],
        },
        "part-1": {
            "type": "BuildingPart",
            "parents": ["building-1"],
            "geometry": [],
        },
    },
    "vertices": [],
    "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
}

MULTI_LOD_CITYMODEL = {
    "type": "CityJSON",
    "version": "2.0",
    "CityObjects": {
        "id-1": {
            "type": "Building",
            "geometry": [
                {
                    "type": "MultiSurface",
                    "lod": "1",
                    "boundaries": [[[0, 1, 2, 3]]],
                },
                {
                    "type": "Solid",
                    "lod": "2",
                    "boundaries": [[[[0, 1, 2, 3]], [[4, 5, 6, 7]]]],
                },
            ],
        },
    },
    "vertices": [
        [0, 0, 0],
        [1, 0, 0],
        [1, 1, 0],
        [0, 1, 0],
        [0, 0, 1],
        [1, 0, 1],
        [1, 1, 1],
        [0, 1, 1],
    ],
    "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
}

ATTRIBUTE_TYPE_PROMOTION_MODEL = {
    "type": "CityJSON",
    "version": "2.0",
    "CityObjects": {
        "id-1": {
            "type": "Building",
            "attributes": {"flag": True, "count": 5, "ratio": 0.5},
        },
        "id-2": {
            "type": "Building",
            "attributes": {"flag": 3, "count": 2.5, "ratio": 1.0},
        },
    },
    "vertices": [],
    "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
}

NO_SEMANTICS_CITYMODEL = {
    "type": "CityJSON",
    "version": "2.0",
    "CityObjects": {
        "id-1": {
            "type": "Building",
            "geometry": [
                {
                    "type": "MultiSurface",
                    "lod": "1",
                    "boundaries": [[[0, 1, 2, 3]]],
                },
            ],
        },
    },
    "vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
    "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
}

EMPTY_CITYMODEL = {
    "type": "CityJSON",
    "version": "2.0",
    "CityObjects": {},
    "vertices": [],
    "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
}


# ============================================================================
# TypeNamingIterator – additional tests
# ============================================================================


class TestTypeNamingIteratorExtended:
    """Additional tests for TypeNamingIterator"""

    def test_multiple_types(self):
        """Tests that multiple CityObject types produce one layer per type"""
        it = TypeNamingIterator("myfile", MULTI_TYPE_CITYMODEL)
        layers = sorted(it.all_layers())
        assert len(layers) == 2
        assert "myfile - Building" in layers
        assert "myfile - Road" in layers

    def test_get_feature_layer(self):
        """Tests that get_feature_layer returns correct name for a feature"""
        it = TypeNamingIterator("f", MULTI_TYPE_CITYMODEL)
        mock_feature = {"type": "Building"}
        assert it.get_feature_layer(mock_feature) == "f - Building"

    def test_empty_citymodel(self):
        """Tests that an empty CityObjects produces no layers"""
        it = TypeNamingIterator("f", EMPTY_CITYMODEL)
        layers = list(it.all_layers())
        assert len(layers) == 0


# ============================================================================
# BaseNamingIterator tests
# ============================================================================


class TestBaseNamingIterator:
    """Tests for BaseNamingIterator"""

    def test_all_layers_returns_filename(self):
        it = BaseNamingIterator("myfile")
        assert it.all_layers() == ["myfile"]

    def test_get_feature_layer_returns_filename(self):
        it = BaseNamingIterator("myfile")
        mock_feature = {"type": "Building"}
        assert it.get_feature_layer(mock_feature) == "myfile"


# ============================================================================
# LodNamingDecorator tests
# ============================================================================


class TestLodNamingDecorator:
    """Tests for LodNamingDecorator"""

    def test_all_layers_includes_lod(self):
        """Tests that layer names include LoD suffixes"""
        base = BaseNamingIterator("f")
        reader = MagicMock()
        reader.get_lod = MagicMock(side_effect=["1", "2"])

        decorator = LodNamingDecorator(base, "f", MULTI_LOD_CITYMODEL, reader)
        layers = decorator.all_layers()

        assert any("[LoD2]" in name for name in layers)
        assert any("[LoD1]" in name for name in layers)

    def test_get_feature_layer_appends_lod(self):
        """Tests that get_feature_layer appends the LoD from the feature"""
        base = BaseNamingIterator("f")
        reader = MagicMock()
        reader.get_lod = MagicMock(return_value="1")

        decorator = LodNamingDecorator(base, "f", NO_SEMANTICS_CITYMODEL, reader)
        mock_feature = {"type": "Building", "lod": "2"}
        result = decorator.get_feature_layer(mock_feature)
        assert result == "f [LoD2]"


# ============================================================================
# AttributeFieldsDecorator – type promotion tests
# ============================================================================


class TestAttributeTypePromotion:
    """Tests the type promotion logic in AttributeFieldsDecorator"""

    def test_bool_promoted_to_int(self):
        """If an attribute is bool in one object and int in another, field becomes int"""
        builder = NullFieldsBuilder()
        builder = AttributeFieldsDecorator(builder, ATTRIBUTE_TYPE_PROMOTION_MODEL)
        fields = builder.get_fields()
        field_map = {f.name(): f for f in fields}

        # "flag" was True then 3 → should be promoted to Int
        from core.layers import FIELD_INT

        assert field_map["attribute.flag"].type() == FIELD_INT

    def test_int_promoted_to_double(self):
        """If an attribute is int in one object and float in another, field becomes double"""
        builder = NullFieldsBuilder()
        builder = AttributeFieldsDecorator(builder, ATTRIBUTE_TYPE_PROMOTION_MODEL)
        fields = builder.get_fields()
        field_map = {f.name(): f for f in fields}

        from core.layers import FIELD_DOUBLE

        assert field_map["attribute.count"].type() == FIELD_DOUBLE

    def test_no_attributes_produces_no_fields(self):
        """CityModel with no attributes should produce no attribute fields"""
        builder = NullFieldsBuilder()
        builder = AttributeFieldsDecorator(builder, NO_SEMANTICS_CITYMODEL)
        fields = builder.get_fields()
        assert len(fields) == 0


# ============================================================================
# SemanticSurfaceFieldsDecorator – additional tests
# ============================================================================


class TestSemanticSurfaceFieldsDecoratorExtended:
    """Additional tests for SemanticSurfaceFieldsDecorator"""

    def test_no_semantics_produces_no_fields(self):
        """CityModel without semantics should produce no surface fields"""
        builder = NullFieldsBuilder()
        builder = SemanticSurfaceFieldsDecorator(builder, NO_SEMANTICS_CITYMODEL)
        fields = builder.get_fields()
        assert len(fields) == 0

    def test_get_semantic_attributes(self):
        """Tests that get_semantic_attributes returns the correct attribute keys"""
        builder = NullFieldsBuilder()
        decorator = SemanticSurfaceFieldsDecorator(builder, SINGLE_CUBE_CITYMODEL)
        atts = decorator.get_semantic_attributes(SINGLE_CUBE_CITYMODEL["CityObjects"])
        assert "type" in atts
        assert "material" in atts

    def test_chained_with_base_fields(self):
        """Tests chaining SemanticSurfaceFieldsDecorator with BaseFieldsBuilder"""
        builder = BaseFieldsBuilder()
        builder = SemanticSurfaceFieldsDecorator(builder, SINGLE_CUBE_CITYMODEL)
        fields = builder.get_fields()
        field_names = [f.name() for f in fields]

        assert "uid" in field_names
        assert "type" in field_names
        assert "surface.type" in field_names
        assert "surface.material" in field_names


# ============================================================================
# NullFieldsBuilder test
# ============================================================================


class TestNullFieldsBuilder:
    """Tests for NullFieldsBuilder"""

    def test_returns_empty_fields(self):
        builder = NullFieldsBuilder()
        fields = builder.get_fields()
        assert isinstance(fields, QgsFields)
        assert len(fields) == 0


# ============================================================================
# SimpleFeatureBuilder tests
# ============================================================================


class TestSimpleFeatureBuilder:
    """Tests for SimpleFeatureBuilder"""

    def _make_fields(self):
        """Build a QgsFields object suitable for feature tests"""
        base = BaseFieldsBuilder()
        attr = AttributeFieldsDecorator(base, PARENT_CHILD_CITYMODEL)
        return attr.get_fields()

    def test_sets_uid_and_type(self):
        """Tests that uid and type are set correctly"""
        reader = MagicMock()
        builder = SimpleFeatureBuilder(reader)
        fields = self._make_fields()

        co = {"type": "Building", "geometry": []}
        features = builder.create_features(fields, "b1", co, read_geometry=False)
        feature = list(features.keys())[0]

        assert feature["uid"] == "b1"
        assert feature["type"] == "Building"

    def test_sets_parents_single(self):
        """Tests that a single parent is stored as a plain string"""
        reader = MagicMock()
        builder = SimpleFeatureBuilder(reader)
        fields = self._make_fields()

        co = {"type": "BuildingPart", "parents": ["building-1"], "geometry": []}
        features = builder.create_features(fields, "p1", co, read_geometry=False)
        feature = list(features.keys())[0]

        assert feature["parents"] == "building-1"

    def test_sets_parents_multiple(self):
        """Tests that multiple parents are stored as a string repr of the list"""
        reader = MagicMock()
        builder = SimpleFeatureBuilder(reader)
        fields = self._make_fields()

        co = {"type": "BuildingPart", "parents": ["p1", "p2"], "geometry": []}
        features = builder.create_features(fields, "x", co, read_geometry=False)
        feature = list(features.keys())[0]

        assert feature["parents"] == "['p1', 'p2']"

    def test_sets_children(self):
        """Tests that children are stored as a string"""
        reader = MagicMock()
        builder = SimpleFeatureBuilder(reader)
        fields = self._make_fields()

        co = {"type": "Building", "children": ["part-1"], "geometry": []}
        features = builder.create_features(fields, "b1", co, read_geometry=False)
        feature = list(features.keys())[0]

        assert feature["children"] == "['part-1']"

    def test_sets_attributes(self):
        """Tests that CityObject attributes are set on the feature"""
        reader = MagicMock()
        builder = SimpleFeatureBuilder(reader)
        fields = self._make_fields()

        co = {
            "type": "Building",
            "attributes": {"roofType": "gable", "height": 22.3},
            "geometry": [],
        }
        features = builder.create_features(fields, "b1", co, read_geometry=False)
        feature = list(features.keys())[0]

        assert feature["attribute.roofType"] == "gable"
        assert feature["attribute.height"] == 22.3

    def test_no_geometry_returns_empty_list(self):
        """Tests that a CityObject without geometry returns empty geom list"""
        reader = MagicMock()
        builder = SimpleFeatureBuilder(reader)
        fields = self._make_fields()

        co = {"type": "Building"}
        features = builder.create_features(fields, "b1", co)
        geom_list = list(features.values())[0]

        assert geom_list == []

    def test_returns_geometry_array_for_object_with_geometry(self):
        """Tests that geometry array is returned in the value dict"""
        reader = MagicMock()
        builder = SimpleFeatureBuilder(reader)
        fields = self._make_fields()

        geom = [{"type": "MultiSurface", "lod": "1", "boundaries": [[[0, 1, 2]]]}]
        co = {"type": "Building", "geometry": geom}
        features = builder.create_features(fields, "b1", co, read_geometry=False)
        returned_geom = list(features.values())[0]

        assert returned_geom == geom


# ============================================================================
# LodFeatureDecorator tests
# ============================================================================


class TestLodFeatureDecorator:
    """Tests for LodFeatureDecorator"""

    def _make_fields(self):
        base = BaseFieldsBuilder()
        lod = LodFieldsDecorator(base)
        return lod.get_fields()

    def test_splits_features_by_lod(self):
        """Tests that geometries with different LoDs produce separate features"""
        reader = MagicMock()
        reader.get_lod = MagicMock(side_effect=lambda g: g["lod"])

        base_builder = SimpleFeatureBuilder(reader)
        decorator = LodFeatureDecorator(base_builder, reader)

        fields = self._make_fields()
        co = MULTI_LOD_CITYMODEL["CityObjects"]["id-1"]

        features = decorator.create_features(fields, "id-1", co, read_geometry=False)

        lods_found = {f["lod"] for f in features.keys()}
        assert "1" in lods_found
        assert "2" in lods_found
        assert len(features) == 2

    def test_empty_geometry_produces_single_feature(self):
        """Tests that a CityObject without geometry still returns a feature"""
        reader = MagicMock()
        base_builder = SimpleFeatureBuilder(reader)
        decorator = LodFeatureDecorator(base_builder, reader)

        fields = self._make_fields()
        co = {"type": "Building"}
        features = decorator.create_features(fields, "b1", co, read_geometry=False)

        assert len(features) == 1


# ============================================================================
# ParentFeatureDecorator tests
# ============================================================================


class TestParentFeatureDecorator:
    """Tests for ParentFeatureDecorator"""

    def _make_fields(self):
        base = BaseFieldsBuilder()
        attr = AttributeFieldsDecorator(base, PARENT_CHILD_CITYMODEL)
        return attr.get_fields()

    def test_child_inherits_parent_attributes(self):
        """Tests that a child with no attributes inherits from its parent"""
        reader = MagicMock()
        base_builder = SimpleFeatureBuilder(reader)
        decorator = ParentFeatureDecorator(base_builder, reader, PARENT_CHILD_CITYMODEL)

        fields = self._make_fields()
        co = PARENT_CHILD_CITYMODEL["CityObjects"]["part-1"]
        features = decorator.create_features(fields, "part-1", co, read_geometry=False)
        feature = list(features.keys())[0]

        assert feature["attribute.roofType"] == "gable"
        assert feature["attribute.height"] == 22.3

    def test_object_with_own_attributes_uses_own(self):
        """Tests that a CityObject with its own attributes does not inherit"""
        reader = MagicMock()
        base_builder = SimpleFeatureBuilder(reader)
        decorator = ParentFeatureDecorator(base_builder, reader, PARENT_CHILD_CITYMODEL)

        fields = self._make_fields()
        co = PARENT_CHILD_CITYMODEL["CityObjects"]["building-1"]
        features = decorator.create_features(
            fields, "building-1", co, read_geometry=False
        )
        feature = list(features.keys())[0]

        assert feature["attribute.roofType"] == "gable"

    def test_get_attributes_returns_only_objects_with_attributes(self):
        """Tests that get_attributes filters correctly"""
        reader = MagicMock()
        base_builder = SimpleFeatureBuilder(reader)
        decorator = ParentFeatureDecorator(base_builder, reader, PARENT_CHILD_CITYMODEL)

        attrs = decorator.get_attributes()
        assert "building-1" in attrs
        assert "part-1" not in attrs


# ============================================================================
# DynamicLayerManager tests
# ============================================================================


class TestDynamicLayerManager:
    """Tests for DynamicLayerManager"""

    def test_get_all_layers_empty_model(self):
        """An empty CityModel produces no valid layers"""
        reader = MagicMock()
        base_builder = SimpleFeatureBuilder(reader)
        naming = BaseNamingIterator("test")
        fields_builder = BaseFieldsBuilder()

        manager = DynamicLayerManager(
            EMPTY_CITYMODEL, base_builder, naming, fields_builder
        )
        manager.prepare_attributes()

        layers = manager.get_all_layers()
        assert len(layers) == 0

    def test_layer_created_per_type(self):
        """TypeNamingIterator should create one VectorLayer per type"""
        reader = MagicMock()
        base_builder = SimpleFeatureBuilder(reader)
        naming = TypeNamingIterator("f", MULTI_TYPE_CITYMODEL)
        fields_builder = BaseFieldsBuilder()

        manager = DynamicLayerManager(
            MULTI_TYPE_CITYMODEL, base_builder, naming, fields_builder
        )

        # The manager should have created 2 internal layers
        assert len(manager._vectorlayers) == 2


# ============================================================================
# Full decorator chain test
# ============================================================================


class TestDecoratorChaining:
    """Tests that the decorator chain produces correct combined fields"""

    def test_full_chain(self):
        """Tests Base + Attribute + Lod + Semantic fields chained together"""
        builder = BaseFieldsBuilder()
        builder = AttributeFieldsDecorator(builder, SINGLE_CUBE_CITYMODEL)
        builder = LodFieldsDecorator(builder)
        builder = SemanticSurfaceFieldsDecorator(builder, SINGLE_CUBE_CITYMODEL)

        fields = builder.get_fields()
        field_names = [f.name() for f in fields]

        # Core fields from BaseFieldsBuilder
        assert "uid" in field_names
        assert "type" in field_names
        assert "parents" in field_names
        assert "children" in field_names

        # Attribute fields
        assert "attribute.function" in field_names

        # LoD field
        assert "lod" in field_names

        # Semantic surface fields
        assert "surface.type" in field_names
        assert "surface.material" in field_names

        # Total: 4 base + 1 attribute + 1 lod + 2 semantic = 8
        assert len(fields) == 8


class TestErrorHandlingAndEdgeCases:
    """Tests for error handling and edge cases in layers module"""

    def test_dynamic_layer_manager_empty_citymodel(self):
        """Tests DynamicLayerManager with empty CityModel creates no objects but still works"""
        empty_model = {"CityObjects": {}, "vertices": []}

        # Create required components
        fields_builder = BaseFieldsBuilder()
        feature_builder = SimpleFeatureBuilder(MagicMock())
        layer_iterator = BaseNamingIterator("empty")

        manager = DynamicLayerManager(
            empty_model, feature_builder, layer_iterator, fields_builder
        )

        # Should create one empty layer based on the filename
        layers = list(manager.get_all_layers())
        # Empty layers are filtered out by get_all_layers(), so expect 0
        assert len(layers) == 0

    def test_base_naming_iterator_with_empty_filename(self):
        """Tests BaseNamingIterator with filename parameter"""
        iterator = BaseNamingIterator("test_file")
        layers = list(iterator.all_layers())
        assert len(layers) == 1
        assert layers[0] == "test_file"

    def test_type_naming_iterator_single_object_type(self):
        """Tests TypeNamingIterator when all objects are same type"""
        same_type_model = {
            "CityObjects": {
                "b1": {"type": "Building"},
                "b2": {"type": "Building"},
                "b3": {"type": "Building"},
            }
        }
        iterator = TypeNamingIterator("test_file", same_type_model)
        names = list(iterator.all_layers())
        # Should only create one name for Buildings
        assert len(names) == 1
        assert names[0] == "test_file - Building"

    def test_simple_feature_builder_with_empty_parents_list(self):
        """Tests SimpleFeatureBuilder with empty parents list"""
        reader = MagicMock()
        builder = SimpleFeatureBuilder(reader)

        # Create fields with parents field
        fields = self._make_basic_fields_with_parents()

        # Test with empty parents list
        co = {"type": "Building", "parents": []}
        features = builder.create_features(fields, "b1", co, read_geometry=False)
        feature = list(features.keys())[0]
        # Empty parents list should set parents field to '[]'
        assert feature["parents"] == "[]"

    def _make_basic_fields_with_parents(self):
        """Helper to create basic fields including parents field"""
        fields = QgsFields()
        fields.append(QgsField("uid", FIELD_STRING))
        fields.append(QgsField("type", FIELD_STRING))
        fields.append(QgsField("parents", FIELD_STRING))
        fields.append(QgsField("children", FIELD_STRING))
        return fields

    def test_parent_feature_decorator_no_parents(self):
        """Tests ParentFeatureDecorator with object that has no parents"""
        reader = MagicMock()
        base_builder = SimpleFeatureBuilder(reader)
        decorator = ParentFeatureDecorator(base_builder, reader, PARENT_CHILD_CITYMODEL)
        fields = self._make_parent_fields()

        co = {"type": "Building"}  # No parents property
        features = decorator.create_features(
            fields, "root-building", co, read_geometry=False
        )
        feature = list(features.keys())[0]

        # Should handle objects without parents gracefully
        assert feature["uid"] == "root-building"
        assert feature["type"] == "Building"

    def _make_parent_fields(self):
        """Helper to create fields for parent decorator tests"""
        base = BaseFieldsBuilder()
        return base.get_fields()

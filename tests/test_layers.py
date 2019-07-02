import pytest

from loader.layers import TypeNamingIterator, BaseFieldsBuilder, NullFieldsBuilder, AttributeFieldsDecorator, LodFieldsDecorator, SemanticSurfaceFieldsDecorator

two_cubes_citymodel = {"CityObjects":{"id-1":{"geometry":[{"boundaries":[[[0,1,2,3]],[[7,4,0,3]],[[4,5,1,0]],[[5,6,2,1]],[[3,2,6,7]],[[6,5,4,7]]],"lod":1,"type":"MultiSurface"}],"type":"GenericCityObject"}},"type":"CityJSON","version":"0.9","vertices":[[1.0,0.0,1.0],[0.0,1.0,1.0],[-1.0,0.0,1.0],[0.0,-1.0,1.0],[1.0,0.0,0.0],[0.0,1.0,0.0],[-1.0,0.0,0.0],[0.0,-1.0,0.0]],"metadata":{"geographicalExtent":[-1.0,-1.0,0.0,1.0,1.0,1.0]}}
citymodel_with_attributes = {"type":"CityJSON","version":"0.9","CityObjects":{"id-1":{"type":"Building","attributes":{"attribute1":1,"attribute2":2}},"id-2":{"type":"Building","attributes":{"attribute1":1,"attribute3":2}}}}

class TestTypeNamingIterator:
    """A class to test the TypeNamingIterator class"""

    def test_list_of_layer_names(self):
        """Tests if the amount of types found in the two cubes example CityJSON
        is identified and named properly
        """
        type_naming_iter = TypeNamingIterator("two_cubes", two_cubes_citymodel)

        layers = list(type_naming_iter.all_layers())
        assert len(layers) == 1
        assert layers[0] == "two_cubes - GenericCityObject"

class TestFieldBuilders:
    """A class to test the field builders"""

    def test_base_field_builder(self):
        """Tests that BaseFieldsBuilder builds the uid and type fields"""
        builder = BaseFieldsBuilder()

        fields = builder.get_fields()

        assert len(fields) == 2
        assert fields[0].name() == "uid"
        assert fields[1].name() == "type"
    
    def test_attributes_fields_builder(self):
        """Tests that AttributeFieldsDecorator creates the attributes of the model"""
        builder = NullFieldsBuilder()
        builder = AttributeFieldsDecorator(builder, citymodel_with_attributes)

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
        """Tests that LodFieldsBuilder create the lod field"""
        builder = NullFieldsBuilder()
        builder = SemanticSurfaceFieldsDecorator(builder)

        fields = builder.get_fields()

        assert len(fields) == 1
        assert fields[0].name() == "semantic_surface"

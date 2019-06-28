"""A module to manage the vector layers as they are going to be loaded in QGIS"""

import abc

from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant
from qgis.core import QgsFeature, QgsField, QgsFields, QgsVectorLayer

class BaseLayerManager:
    """A base layer manager for the common functionality between current ones"""

    def __init__(self, citymodel, fields_builder, geometry_reader):
        self._citymodel = citymodel
        self._fields_builder = fields_builder
        self._geometry_reader = geometry_reader
        self._geom_type = "MultiPolygon"
        self._fields = QgsFields()
        if "crs" in self._citymodel["metadata"]:
            self._geom_type = "{}?crs=EPSG:{}".format(self._geom_type, self._citymodel["metadata"]["crs"]["epsg"])

    def prepare_attributes(self):
        """Prepares the attributes of the vector layer."""
        self._fields = self._fields_builder.get_fields()

        # Setup attributes on the datasource(s)
        for vl in self.get_all_layers():
            pr = vl.dataProvider()
            pr.addAttributes(self._fields)
            vl.updateFields()

    @abc.abstractmethod
    def get_all_layers(self):
        """Returns all vector layers of the manager"""
        return

class DynamicLayerManager(BaseLayerManager):
    """A class that create a simple layer for all city objects"""

    def __init__(self, citymodel, geometry_reader, layer_iterator, fields_builder):
        super(DynamicLayerManager, self).__init__(citymodel,
                                                  fields_builder,
                                                  geometry_reader)

        self._layer_iterator = layer_iterator
        self._vectorlayers = dict()
        for name in self._layer_iterator.all_layers():
            vl = QgsVectorLayer(self._geom_type, name, "memory")
            self._vectorlayers[name] = vl

    def add_object(self, object_key, cityobject):
        """Adds a cityobject in the respective vector layer"""
        new_feature = create_feature(self._fields, object_key, cityobject)

        geom = self._geometry_reader.read_geometry(cityobject["geometry"])
        new_feature.setGeometry(geom)

        layer_name = self._layer_iterator.get_feature_layer(new_feature)
        provider = self._vectorlayers[layer_name].dataProvider()
        provider.addFeature(new_feature)

        return provider, new_feature

    def get_all_layers(self):
        """Returns all the vector layers from this manager."""
        return [vl for vl_key, vl in self._vectorlayers.items()]

class BaseNamingIterator:
    """A class that iterates through the types"""

    def __init__(self, filename):
        self._filename = filename

    def all_layers(self):
        """Returns the all layer names"""
        return [self._filename]

    def get_feature_layer(self, feature):
        """Returns the layer name for the given city object"""
        return self._filename

class TypeNamingIterator:
    """A class that iterates through the types"""

    def __init__(self, filename, citymodel):
        self._filename = filename
        self._citymodel = citymodel

    def all_layers(self):
        """Returns the all layer names"""
        types = set([obj["type"]
                     for obj in self._citymodel["CityObjects"].values()])

        for t in types:
            yield "{} - {}".format(self._filename, t)

    def get_feature_layer(self, feature):
        """Returns the layer name for the given city object"""
        return "{} - {}".format(self._filename, feature["type"])

class LodNamingDecorator:
    """A decorator class to append LoD in a layer's name"""

    def __init__(self, decorated, filename, citymodel):
        self._decorated = decorated
        self._filename = filename
        self._citymodel = citymodel
        self._lods = set([geom["lod"]
                          for obj in citymodel["CityObjects"].values()
                          for geom in obj["geometry"]])

    def all_layers(self):
        """Returns all layer names with LoD"""
        for lod in self._lods:
            for layer in self._decorated.all_layers():
                yield "{} [LoD{}]".format(layer, str(lod))

class BaseFieldsBuilder:
    """A class that create the basic fields of city objects (uid and type)"""

    def get_fields(self):
        """Creates and returns fields"""
        fields = QgsFields()
        fields.append(QgsField("uid", QVariant.String))
        fields.append(QgsField("type", QVariant.String))

        return fields

class NullFieldsBuilder:
    """A class that creates no fields (used for mocking)"""

    def get_fields(self):
        """Creates no fields"""
        return QgsFields()

class AttributeFieldsDecorator:
    """A class that create fields based on the attributes of the city model"""

    def __init__(self, decorated, citymodel):
        self._decorated = decorated
        self._citymodel = citymodel

    def get_fields(self):
        """Create and returns fields"""
        fields = self._decorated.get_fields()

        attributes = get_attribute_keys(self._citymodel["CityObjects"])

        for att in attributes:
            fields.append(QgsField("attribute.{}".format(att),
                                   QVariant.String))

        return fields

class LodFieldsDecorator:
    """A class that creates an LoD field"""

    def __init__(self, decorated):
        self._decorated = decorated

    def get_fields(self):
        """Create and returns fields"""
        fields = self._decorated.get_fields()

        fields.append(QgsField("lod", QVariant.String))

        return fields

class SemanticSurfaceFieldsDecorator:
    """A class that creates an LoD field"""

    def __init__(self, decorated):
        self._decorated = decorated

    def get_fields(self):
        """Create and returns fields"""
        fields = self._decorated.get_fields()

        fields.append(QgsField("semantic_surface", QVariant.String))

        return fields

def get_attribute_keys(objs):
    """Returns the list of (unique) attributes found in all city objects."""
    atts = []

    for obj in objs.values():
        if "attributes" in obj:
            for att_key in obj["attributes"]:
                if not att_key in atts:
                    atts.append(att_key)

    return atts

def create_feature(fields, object_key, cityobject):
    """Creates a feature based on the city object's semantics"""
    fet = QgsFeature(fields)
    fet["uid"] = object_key
    fet["type"] = cityobject["type"]

    # Load the attributes
    if "attributes" in cityobject:
        for att_key, att_value in cityobject["attributes"].items():
            fet["attribute.{}".format(att_key)] = att_value

    return fet

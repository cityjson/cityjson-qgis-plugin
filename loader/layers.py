"""A module to manage the vector layers as they are going to be loaded in QGIS"""

import abc

from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant
from qgis.core import QgsFeature, QgsField, QgsVectorLayer

class BaseLayerManager:
    """A base layer manager for the common functionality between current ones"""

    def __init__(self, citymodel, filename, geometry_reader):
        self._citymodel = citymodel
        self._geometry_reader = geometry_reader
        self._geom_type = "MultiPolygon"
        if "crs" in self._citymodel["metadata"]:
            self._geom_type = "{}?crs=EPSG:{}".format(self._geom_type, self._citymodel["metadata"]["crs"]["epsg"])
    
    def prepare_attributes(self):
        """Prepares the attributes of the vector layer."""
        # Identify attributes present in the file
        att_keys = get_attribute_keys(self._citymodel["CityObjects"])

        fields = create_fields(att_keys)

        # Setup attributes on the datasource(s)
        for vl in self.get_all_layers():
            pr = vl.dataProvider()
            pr.addAttributes(fields)
            vl.updateFields()
    
    @abc.abstractmethod
    def get_all_layers(self):
        """Returns all vector layers of the manager"""
        return

class SingleLayerManager(BaseLayerManager):
    """A class that create a simple layer for all city objects"""

    def __init__(self, citymodel, filename, geometry_reader):
        super(SingleLayerManager, self).__init__(citymodel, filename, geometry_reader)

        self._vectorlayer = QgsVectorLayer(self._geom_type, filename, "memory")

    def add_object(self, object_key, cityobject):
        """Adds a cityobject in the respective vector layer"""
        pr = self._vectorlayer.dataProvider()
   
        fet = create_feature(pr, object_key, cityobject)

        geom = self._geometry_reader.read_geometry(cityobject["geometry"])
        fet.setGeometry(geom)

        # Add feature to the provider
        pr.addFeature(fet)

        return pr, fet

    def get_all_layers(self):
        """Returns all the vector layers from this manager."""
        return [self._vectorlayer]

class ObjectTypeLayerManager(BaseLayerManager):
    """A class that create a simple layer for all city objects"""

    def __init__(self, citymodel, filename, geometry_reader):
        super(ObjectTypeLayerManager, self).__init__(citymodel, filename, geometry_reader)

        # Identify object types present in the file
        types = set([obj["type"] for obj in self._citymodel["CityObjects"].values()])

        self._vectorlayers = dict()
        for t in types:
            vl = QgsVectorLayer(self._geom_type, "{} - {}".format(filename, t), "memory")
            self._vectorlayers[t] = vl

    def add_object(self, object_key, cityobject):
        """Adds a cityobject in the respective vector layer"""
        pr = self._vectorlayers[cityobject["type"]].dataProvider()

        fet = create_feature(pr, object_key, cityobject)

        geom = self._geometry_reader.read_geometry(cityobject["geometry"])
        fet.setGeometry(geom)

        # Add feature to the provider
        pr.addFeature(fet)

        return pr, fet

    def get_all_layers(self):
        """Returns all the vector layers from this manager."""
        return [vl for vl_key, vl in self._vectorlayers.items()]

def get_attribute_keys(objs):
    """Returns the list of (unique) attributes found in all city objects."""
    atts = []

    for key, obj in objs.items():
        if "attributes" in obj:
            for att_key in obj["attributes"]:
                if not att_key in atts:
                    atts.append(att_key)

    return atts

def create_fields(attributes):
    """Creates fields based on the given attributes"""

    fields = [QgsField("uid", QVariant.String), QgsField("type", QVariant.String)]

    for att in attributes:
        fields.append(QgsField("attribute.{}".format(att), QVariant.String))

    return fields

def create_feature(data_provider, object_key, cityobject):
    """Creates a feature based on the city object's semantics"""
    fet = QgsFeature(data_provider.fields())
    fet["uid"] = object_key
    fet["type"] = cityobject["type"]

    # Load the attributes
    if "attributes" in cityobject:
        for att_key, att_value in cityobject["attributes"].items():
            fet["attribute.{}".format(att_key)] = att_value
    
    return fet
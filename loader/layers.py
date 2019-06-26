"""A module to manage the vector layers as they are going to be loaded in QGIS"""

from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant
from qgis.core import QgsField, QgsVectorLayer

class BasicLayerManager:
    """A class that create a simple layer for all city objects"""

    def __init__(self, citymodel, filename):
        self._citymodel = citymodel
        geom_type = "MultiPolygon"
        if "crs" in self._citymodel["metadata"]:
            geom_type = "{}?crs=EPSG:{}".format(geom_type, self._citymodel["metadata"]["crs"]["epsg"])
        
        self._vectorlayer = QgsVectorLayer(geom_type, filename, "memory")
    
    def prepare_attributes(self):
        """Prepares the attributes of the vector layer."""
        # Identify attributes present in the file
        att_keys = get_attribute_keys(self._citymodel["CityObjects"])

        fields = [QgsField("uid", QVariant.String), QgsField("type", QVariant.String)]

        for att in att_keys:
            fields.append(QgsField("attribute.{}".format(att), QVariant.String))

        # Setup attributes on the datasource
        pr = self._vectorlayer.dataProvider()
        pr.addAttributes(fields)
        self._vectorlayer.updateFields()
   
    def get_object_layer(self, cityobject):
        """Returns the vector layer that corresponds to the provided city object."""
        return self._vectorlayer
    
    def get_all_layers(self):
        """Returns all the vector layers from this manager."""
        return [self._vectorlayer]

class ObjectTypeLayerManager:
    """A class that create a simple layer for all city objects"""

    def __init__(self, citymodel, filename):
        self._citymodel = citymodel
        geom_type = "MultiPolygon"
        if "crs" in self._citymodel["metadata"]:
            geom_type = "{}?crs=EPSG:{}".format(geom_type, self._citymodel["metadata"]["crs"]["epsg"])
        
        # Identify object types present in the file
        types = set()
        for key, obj in self._citymodel["CityObjects"].items():
            types.add(self._citymodel["CityObjects"][key]['type'])

        self._vectorlayers = dict()
        for t in types:
            vl = QgsVectorLayer(geom_type, "{} - {}".format(filename, t), "memory")
            self._vectorlayers[t] = vl
    
    def prepare_attributes(self):
        """Prepares the attributes of the vector layer."""
        # Identify attributes present in the file
        att_keys = get_attribute_keys(self._citymodel["CityObjects"])

        fields = [QgsField("uid", QVariant.String), QgsField("type", QVariant.String)]

        for att in att_keys:
            fields.append(QgsField("attribute.{}".format(att), QVariant.String))

        # Setup attributes on the datasource(s)
        for vl_key, vl in self._vectorlayers.items():
            pr = vl.dataProvider()
            pr.addAttributes(fields)
            vl.updateFields()
   
    def get_object_layer(self, cityobject):
        """Returns the vector layer that corresponds to the provided city object."""
        return self._vectorlayers[cityobject["type"]]
    
    def get_all_layers(self):
        """Returns all the vector layers from this manager."""
        return [vl for vl_key, vl in self._vectorlayers.items()]

def get_attribute_keys(objs):
    """Returns the list of (unique) attributes found in all city objects."""
    atts = []

    for key, obj in objs.items():
        if "attributes" in obj:
            for att_key, att_value in obj["attributes"].items():
                if not att_key in atts:
                    atts.append(att_key)
    
    return atts
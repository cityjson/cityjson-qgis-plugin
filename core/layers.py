"""A module to manage the vector layers as they are going to be loaded in QGIS"""

import abc

from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant
from qgis.core import QgsFeature, QgsField, QgsFields, QgsVectorLayer

class BaseLayerManager:
    """A base layer manager for the common functionality between current ones"""

    def __init__(self, citymodel, fields_builder, srid):
        self._citymodel = citymodel
        self._fields_builder = fields_builder
        self._geom_type = "MultiPolygon"
        self._fields = QgsFields()
        if srid is None:
            if "crs" in self._citymodel["metadata"]:
                srid = self._citymodel["metadata"]["crs"]["epsg"]

        if srid is not None:
            self._geom_type = "{}?crs=EPSG:{}".format(self._geom_type, srid)

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

    def __init__(self, citymodel, feature_builder, layer_iterator, fields_builder, srid=None):
        super(DynamicLayerManager, self).__init__(citymodel,
                                                  fields_builder,
                                                  srid)

        self._feature_builder = feature_builder
        self._layer_iterator = layer_iterator
        self._vectorlayers = dict()
        for name in self._layer_iterator.all_layers():
            vl = QgsVectorLayer(self._geom_type, name, "memory")
            self._vectorlayers[name] = vl

    def add_object(self, object_key, cityobject):
        """Adds a cityobject in the respective vector layer"""
        new_features = self._feature_builder.create_features(self._fields, object_key, cityobject)

        for feature in new_features:
            layer_name = self._layer_iterator.get_feature_layer(feature)
            provider = self._vectorlayers[layer_name].dataProvider()
            provider.addFeature(feature)

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

    def __init__(self, decorated, filename, citymodel, geometry_reader):
        self._decorated = decorated
        self._filename = filename
        self._citymodel = citymodel
        self._geometry_reader = geometry_reader

        lods = [self._geometry_reader.get_lod(geom)
                for obj in citymodel["CityObjects"].values()
                if "geometry" in obj
                for geom in obj["geometry"]]
        lods.append(None)
        self._lods = set(lods)

    def all_layers(self):
        """Returns all layer names with LoD"""
        for lod in self._lods:
            for layer in self._decorated.all_layers():
                yield "{} [LoD{}]".format(layer, str(lod))

    def get_feature_layer(self, feature):
        """Returns the layer name for the given city object"""
        layer = self._decorated.get_feature_layer(feature)
        return "{} [LoD{}]".format(layer, feature["lod"])

class BaseFieldsBuilder:
    """A class that create the basic fields of city objects (uid and type)"""

    def get_fields(self):
        """Creates and returns fields"""
        fields = QgsFields()
        fields.append(QgsField("uid", QVariant.String))
        fields.append(QgsField("type", QVariant.String))
        fields.append(QgsField("parents", QVariant.String, len=1000))
        fields.append(QgsField("children", QVariant.String, len=1000))

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

    def get_attribute_keys(self, objs):
        """Returns the list of (unique) attributes found in all city objects."""
        atts = []

        for obj in objs.values():
            if "attributes" in obj:
                for att_key in obj["attributes"]:
                    if not att_key in atts:
                        atts.append(att_key)

        return atts

    def get_fields(self):
        """Create and returns fields"""
        fields = self._decorated.get_fields()

        attributes = self.get_attribute_keys(self._citymodel["CityObjects"])

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

    def __init__(self, decorated, citymodel):
        self._decorated = decorated
        self._citymodel = citymodel

    def get_semantic_attributes(self, objs):
        """Returns the list of (unique) attributes found in all city objects."""
        atts = []

        for obj in objs.values():
            if "geometry" in obj:
                for geom in obj["geometry"]:
                    if "semantics" in geom:
                        for surface in geom["semantics"]["surfaces"]:
                            for att_key in surface:
                                if not att_key in atts:
                                    atts.append(att_key)

        return atts

    def get_fields(self):
        """Create and returns fields"""
        fields = self._decorated.get_fields()

        attributes = self.get_semantic_attributes(self._citymodel["CityObjects"])

        for att in attributes:
            fields.append(QgsField("surface.{}".format(att),
                                   QVariant.String))

        return fields

class SimpleFeatureBuilder:
    """A class that create features according to their attributes"""

    def __init__(self, geometry_reader):
        self._geometry_reader = geometry_reader

    def create_features(self, fields, object_key, cityobject, read_geometry=True):
        """Creates a feature based on the city object's semantics"""
        new_feature = QgsFeature(fields)
        new_feature["uid"] = object_key
        new_feature["type"] = cityobject["type"]

        if "parents" in cityobject:
            if len(cityobject["parents"]) == 1:
                new_feature["parents"] = cityobject["parents"][0]
            else:
                new_feature["parents"] = str(cityobject["parents"])

        if "children" in cityobject:
            new_feature["children"] = str(cityobject["children"])

        # Load the attributes
        if "attributes" in cityobject:
            for att_key, att_value in cityobject["attributes"].items():
                new_feature["attribute.{}".format(att_key)] = att_value

        if "geometry" in cityobject:
            return_geom = cityobject["geometry"]
            
            if read_geometry:
                geom = self._geometry_reader.read_geometry(cityobject["geometry"])
                new_feature.setGeometry(geom)
        else:
            return_geom = []

        return {new_feature: return_geom}

class LodFeatureDecorator:
    """A class that decorates feature with lod information and geometries"""

    def __init__(self, decorated, geometry_reader):
        self._decorated = decorated
        self._geometry_reader = geometry_reader

    def create_features(self, fields, object_key, cityobject, read_geometry=True):
        """Creates features per LoD in the geometry"""
        features = self._decorated.create_features(fields,
                                                   object_key,
                                                   cityobject,
                                                   False)
        return_features = {}

        for feature, feature_geom in features.items():
            lod_geom_dict = {} # Stores the lod -> geometry dictionary

            if len(feature_geom) > 0:
                for geom in feature_geom:
                    lod_geom_dict.setdefault(self._geometry_reader.get_lod(geom), []).append(geom)

                for lod, geom in lod_geom_dict.items():
                    new_feature = QgsFeature(feature)

                    new_feature["lod"] = lod
                    if read_geometry:
                        qgs_geometry = self._geometry_reader.read_geometry(geom)
                        new_feature.setGeometry(qgs_geometry)

                    return_features[new_feature] = geom
            else:
                return_features[feature] = None

        return return_features

class SemanticSurfaceFeatureDecorator:
    """A class that decorates feature with lod information and geometries"""

    def __init__(self, decorated, geometry_reader):
        self._decorated = decorated
        self._geometry_reader = geometry_reader
    
    def semantic_to_string(self, semantic):
        """Returns a string from a semantic surface object"""
        if semantic is None:
            return "None"
        else:
            return semantic["type"]

    def create_features(self, fields, object_key, cityobject, read_geometry=True):
        """Creates features per semantic surface in each geometry"""
        features = self._decorated.create_features(fields,
                                                   object_key,
                                                   cityobject,
                                                   False)
        return_features = {}

        for feature, feature_geom in features.items():
            polygons, semantics = self._geometry_reader.get_polygons(feature_geom)

            if len(polygons) > 1:
                surf_geom_dict = {}
                for polygon, semantic in zip(polygons, semantics):
                    new_feature = QgsFeature(feature)

                    if not semantic is None:
                        for att in semantic:
                            new_feature[f"surface.{att}"] = semantic[att]

                    if read_geometry:
                        qgs_geometry = self._geometry_reader.polygons_to_geometry([polygon])
                        new_feature.setGeometry(qgs_geometry)

                    return_features[new_feature] = polygon #TODO: This is wrong! There must be a geometry here
            else:
                return_features[feature] = None

        return return_features

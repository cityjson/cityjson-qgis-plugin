# ******************************************************************************
# Project: CityJsonLoader - A QGIS Plugin.
#
# Purpose: This plugin allows for CityJSON files to be loaded in QGIS.
#
# GitHub page: https://github.com/cityjson/cityjson-qgis-plugin
#
# Contact: G.Stavropoulou@tudelft.nl
# ******************************************************************************
#
# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ******************************************************************************
"""A module to manage the vector layers as they are going to be loaded in QGIS"""

import abc
import json
from typing import Any, Iterator

from qgis.core import Qgis, QgsFeature, QgsField, QgsFields, QgsVectorLayer

from . import get_logger

logger = get_logger("layers")

# Define type aliases for field types based on QGIS version
if Qgis.QGIS_VERSION_INT >= 33800:
    from qgis.PyQt.QtCore import QMetaType

    FIELD_STRING = QMetaType.Type.QString
    FIELD_INT = QMetaType.Type.Int
    FIELD_DOUBLE = QMetaType.Type.Double
    FIELD_BOOL = QMetaType.Type.Bool
else:
    from qgis.PyQt.QtCore import QVariant

    FIELD_STRING = QVariant.String
    FIELD_INT = QVariant.Int
    FIELD_DOUBLE = QVariant.Double
    FIELD_BOOL = QVariant.Bool

CORE_FIELD_NAMES = ["uid", "type", "parents", "children", "lod"]
SURFACE_PREFIX = "surface."
DEFAULT_GEOM_TYPE = "MultiPolygonZ"


def _qgis_type(value: Any) -> Any:
    """Return the QGIS field type that best matches a Python value."""
    if isinstance(value, bool):
        return FIELD_BOOL
    if isinstance(value, int):
        return FIELD_INT
    if isinstance(value, float):
        return FIELD_DOUBLE
    return FIELD_STRING


def _stringify_attribute(value: Any) -> Any:
    """Serialize nested structures to JSON so they can be stored in a field."""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


def _register_field_type(attribute_types: dict[str, Any], key: str, value: Any) -> None:
    """Register the type of ``value`` for ``key``, promoting when necessary.

    Promotion rules:
    - a float upgrades the field to Double;
    - a string upgrades the field to String;
    - an int upgrades a Bool field to Int.
    """
    qtype = _qgis_type(value)
    if (
        (
            key not in attribute_types
            or (qtype == FIELD_DOUBLE and attribute_types[key] != FIELD_DOUBLE)
            or (qtype == FIELD_STRING and attribute_types[key] != FIELD_STRING)
        )
        or qtype == FIELD_INT
        and attribute_types[key] == FIELD_BOOL
    ):
        attribute_types[key] = qtype


class BaseLayerManager:
    """A base layer manager for the common functionality between current ones"""

    def __init__(
        self, citymodel: dict[str, Any], fields_builder: Any, srid: str | None
    ) -> None:
        self._citymodel = citymodel
        self._fields_builder = fields_builder
        self._geom_type = DEFAULT_GEOM_TYPE
        self._fields = QgsFields()

        if (
            not srid
            and "metadata" in self._citymodel
            and "crs" in self._citymodel["metadata"]
        ):
            srid = self._citymodel["metadata"]["crs"]["epsg"]

        if srid:
            self._geom_type = f"{self._geom_type}?crs=EPSG:{srid}"

    def prepare_attributes(self) -> None:
        """Prepares the attributes of the vector layer."""
        all_fields = self._fields_builder.get_fields()

        core_fields = QgsFields()
        surface_fields = QgsFields()
        attribute_fields = QgsFields()

        for field in all_fields:
            if field.name() in CORE_FIELD_NAMES:
                core_fields.append(field)
            elif field.name().startswith(SURFACE_PREFIX):
                surface_fields.append(field)
            else:
                attribute_fields.append(field)

        reordered_fields = QgsFields()
        for field_collection in [core_fields, surface_fields, attribute_fields]:
            for field in field_collection:
                reordered_fields.append(field)

        self._fields = reordered_fields

        for vl in self.get_all_layers():
            pr = vl.dataProvider()
            pr.addAttributes(self._fields)
            vl.updateFields()

    @abc.abstractmethod
    def get_all_layers(self) -> list[QgsVectorLayer]:
        """Returns all vector layers of the manager"""
        return []


class DynamicLayerManager(BaseLayerManager):
    """A class that create a simple layer for all city objects"""

    def __init__(
        self,
        citymodel: dict[str, Any],
        feature_builder: Any,
        layer_iterator: Any,
        fields_builder: Any,
        srid: str | None = None,
    ) -> None:
        super().__init__(citymodel, fields_builder, srid)

        self._feature_builder = feature_builder
        self._layer_iterator = layer_iterator
        self._vectorlayers: dict[str, QgsVectorLayer] = {}

        for name in self._layer_iterator.all_layers():
            vl = QgsVectorLayer(self._geom_type, name, "memory")
            self._vectorlayers[name] = vl

    def add_object(self, object_key: str, cityobject: dict[str, Any]) -> None:
        """Adds a cityobject in the respective vector layer"""
        new_features = self._feature_builder.create_features(
            self._fields, object_key, cityobject
        )

        for feature in new_features:
            layer_name = self._layer_iterator.get_feature_layer(feature)
            provider = self._vectorlayers[layer_name].dataProvider()

            if feature.geometry() and not feature.geometry().isEmpty():
                provider.addFeature(feature)

    def get_all_layers(self) -> list[QgsVectorLayer]:
        """Returns all the vector layers from this manager"""
        valid_layers = []
        for layer in self._vectorlayers.values():
            provider = layer.dataProvider()
            provider.addAttributes(self._fields)
            layer.updateFields()

            if provider.featureCount() > 0:
                valid_layers.append(layer)

        return valid_layers


class BaseNamingIterator:
    """A class that iterates through the types"""

    def __init__(self, filename: str) -> None:
        self._filename = filename

    def all_layers(self) -> list[str]:
        """Returns the all layer names"""
        return [self._filename]

    def get_feature_layer(self, feature: Any) -> str:
        """Returns the layer name for the given city object"""
        return self._filename


class TypeNamingIterator:
    """A class that iterates through the types"""

    def __init__(self, filename: str, citymodel: dict[str, Any]) -> None:
        self._filename = filename
        self._citymodel = citymodel

    def all_layers(self) -> Iterator[str]:
        """Returns the all layer names"""
        types = {obj["type"] for obj in self._citymodel["CityObjects"].values()}
        for t in types:
            yield f"{self._filename} - {t}"

    def get_feature_layer(self, feature: Any) -> str:
        """Returns the layer name for the given city object"""
        return "{} - {}".format(self._filename, feature["type"])


class LodNamingDecorator:
    """A decorator class to append LoD in a layer's name"""

    def __init__(
        self,
        decorated: Any,
        filename: str,
        citymodel: dict[str, Any],
        geometry_reader: Any,
    ) -> None:
        self._decorated = decorated
        self._filename = filename
        self._citymodel = citymodel
        self._geometry_reader = geometry_reader

        lods = [
            self._geometry_reader.get_lod(geom)
            for obj in citymodel["CityObjects"].values()
            if "geometry" in obj
            for geom in obj["geometry"]
        ]
        lods.append(None)
        self._lods = set(lods)

    def all_layers(self) -> list[str]:
        """Returns all layer names with LoD sorted by LoD in descending order"""
        sorted_lods = sorted(
            self._lods, key=lambda x: float(x) if x is not None else -1, reverse=True
        )

        layer_names = []
        for lod in sorted_lods:
            for layer in self._decorated.all_layers():
                layer_names.append(f"{layer} [LoD{lod!s}]")

        return layer_names

    def get_feature_layer(self, feature: Any) -> str:
        """Returns the layer name for the given city object"""
        layer = self._decorated.get_feature_layer(feature)

        return "{} [LoD{}]".format(layer, feature["lod"])


class BaseFieldsBuilder:
    """A class that creates the basic fields of city objects
    (uid, type, parents and children)"""

    def get_fields(self) -> QgsFields:
        """Creates and returns fields"""
        fields = QgsFields()
        fields.append(QgsField("uid", FIELD_STRING))
        fields.append(QgsField("type", FIELD_STRING))
        field_parents = QgsField("parents", FIELD_STRING)
        field_parents.setLength(1000)
        fields.append(field_parents)
        field_children = QgsField("children", FIELD_STRING)
        field_children.setLength(1000)
        fields.append(field_children)

        return fields


class NullFieldsBuilder:
    """A class that creates no fields (used for mocking)"""

    def get_fields(self) -> QgsFields:
        """Creates no fields"""
        return QgsFields()


class AttributeFieldsDecorator:
    """A class that create fields based on the attributes of the city model"""

    def __init__(self, decorated: Any, citymodel: dict[str, Any]) -> None:
        self._decorated = decorated
        self._citymodel = citymodel
        self._attribute_types = self._get_attribute_types()

    def _get_attribute_types(self) -> dict[str, Any]:
        attribute_types: dict[str, Any] = {}
        for obj in self._citymodel["CityObjects"].values():
            if "attributes" in obj:
                for att_key, att_value in obj["attributes"].items():
                    _register_field_type(attribute_types, att_key, att_value)

        return attribute_types

    def get_fields(self) -> QgsFields:
        """Create and returns fields"""
        fields = self._decorated.get_fields()
        attributes = self._attribute_types.items()
        try:
            for att, qtype in attributes:
                fields.append(QgsField(f"attribute.{att}", qtype))
        except Exception as e:
            logger.error(f"Error while creating attribute fields: {e}")

        return fields


class LodFieldsDecorator:
    """A class that creates an LoD field"""

    def __init__(self, decorated: Any) -> None:
        self._decorated = decorated

    def get_fields(self) -> QgsFields:
        """Create and returns fields"""
        fields = self._decorated.get_fields()
        fields.append(QgsField("lod", FIELD_STRING))

        return fields


class SemanticSurfaceFieldsDecorator:
    """A class that create fields based on the surface attributes of the city model"""

    def __init__(self, decorated: Any, citymodel: dict[str, Any]) -> None:
        self._decorated = decorated
        self._citymodel = citymodel
        self._attribute_types = self._get_attribute_types()

    def _get_attribute_types(self) -> dict[str, Any]:
        attribute_types: dict[str, Any] = {}
        for obj in self._citymodel["CityObjects"].values():
            for geom in obj.get("geometry", []):
                semantics = geom.get("semantics")
                if not semantics:
                    continue
                for surface in semantics.get("surfaces", []):
                    for att_key, att_value in surface.items():
                        _register_field_type(attribute_types, att_key, att_value)
                for key, value in semantics.items():
                    if key in ["surfaces", "values"]:
                        continue
                    att_key = key.lstrip("+")
                    if isinstance(value, list):
                        for item in value:
                            _register_field_type(attribute_types, att_key, item)
                    else:
                        _register_field_type(attribute_types, att_key, value)
        return attribute_types

    def get_semantic_attributes(self, objs: dict[str, Any]) -> list[str]:
        """Returns the list of (unique) attributes found in all city objects."""
        atts = []
        for obj in objs.values():
            if "geometry" in obj:
                for geom in obj["geometry"]:
                    if "semantics" in geom:
                        for surface in geom["semantics"]["surfaces"]:
                            for att_key in surface:
                                if att_key not in atts:
                                    atts.append(att_key)

                        for key in geom["semantics"]:
                            key = key.lstrip("+")
                            if key not in ["surfaces", "values"] and key not in atts:
                                atts.append(key)

        return atts

    def get_fields(self) -> QgsFields:
        """Create and returns fields"""
        fields = self._decorated.get_fields()

        try:
            for att, qtype in self._attribute_types.items():
                fields.append(QgsField(f"surface.{att}", qtype))
        except Exception as e:
            logger.error(f"Error while creating semantic surface attribute fields: {e}")

        return fields

    def get_attributes(self) -> list[str]:
        """Returns the list of (unique) semantic surface attributes."""
        return list(self._attribute_types.keys())


class SimpleFeatureBuilder:
    """A class that create features according to their attributes"""

    def __init__(self, geometry_reader: Any) -> None:
        self._geometry_reader = geometry_reader

    def create_features(
        self,
        fields: QgsFields,
        object_key: str,
        cityobject: dict[str, Any],
        read_geometry: bool = True,
    ) -> dict[QgsFeature, Any]:
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

        if "attributes" in cityobject:
            for att_key, att_value in cityobject["attributes"].items():
                new_feature[f"attribute.{att_key}"] = _stringify_attribute(att_value)

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

    def __init__(self, decorated: Any, geometry_reader: Any) -> None:
        self._decorated = decorated
        self._geometry_reader = geometry_reader

    def create_features(
        self,
        fields: QgsFields,
        object_key: str,
        cityobject: dict[str, Any],
        read_geometry: bool = True,
    ) -> dict[QgsFeature, Any]:
        """Creates features per LoD in the geometry"""
        features = self._decorated.create_features(
            fields, object_key, cityobject, False
        )
        return_features: dict[QgsFeature, Any] = {}
        for feature, feature_geom in features.items():
            lod_geom_dict: dict[Any, list[Any]] = {}

            if len(feature_geom) > 0:
                for geom in feature_geom:
                    lod_geom_dict.setdefault(
                        self._geometry_reader.get_lod(geom), []
                    ).append(geom)

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

    def __init__(
        self, decorated: Any, geometry_reader: Any, field_decorator: Any
    ) -> None:
        self._decorated = decorated
        self._geometry_reader = geometry_reader
        self._field_decorator = field_decorator
        self._attributes = self._field_decorator.get_attributes()

    def semantic_to_string(self, semantic: Any) -> str:
        """Returns a string from a semantic surface object"""
        if semantic is None:
            return "None"
        else:
            return semantic["type"]

    def create_features(
        self,
        fields: QgsFields,
        object_key: str,
        cityobject: dict[str, Any],
        read_geometry: bool = True,
    ) -> dict[QgsFeature, Any]:
        """Creates features per semantic surface in each geometry"""
        features = self._decorated.create_features(
            fields, object_key, cityobject, False
        )
        return_features = {}
        for feature, feature_geom in features.items():
            polygons, semantics = self._geometry_reader.get_polygons(
                feature_geom, self._attributes
            )

            if len(polygons) > 1:
                for polygon, semantic in zip(polygons, semantics):
                    new_feature = QgsFeature(feature)

                    if semantic is not None:
                        for att in self._attributes:
                            if att in semantic:
                                new_feature[f"surface.{att}"] = semantic[att]

                    if read_geometry:
                        qgs_geometry = self._geometry_reader.polygons_to_geometry(
                            [polygon]
                        )
                        new_feature.setGeometry(qgs_geometry)

                    return_features[new_feature] = (
                        polygon  # TODO: This is wrong! There must be a geometry here
                    )
            else:
                return_features[feature] = None

        return return_features


class ParentFeatureDecorator:
    """A class that decorates feature with parent attributes"""

    def __init__(
        self, decorated: Any, geometry_reader: Any, citymodel: dict[str, Any]
    ) -> None:
        self._decorated = decorated
        self._geometry_reader = geometry_reader
        self._citymodel = citymodel

    def get_attributes(self) -> dict[str, dict[str, Any]]:
        """Get parent attributes for city objects."""
        objs = self._citymodel["CityObjects"]

        return {
            obj: data["attributes"]
            for obj, data in objs.items()
            if data.get("attributes")
        }

    def create_features(
        self,
        fields: QgsFields,
        object_key: str,
        cityobject: dict[str, Any],
        read_geometry: bool = True,
    ) -> dict[QgsFeature, Any]:
        """Creates a feature based on the city object's semantics"""
        features = self._decorated.create_features(
            fields, object_key, cityobject, False
        )

        return_features = {}
        for feature in features:
            new_feature = QgsFeature(feature)
            city_attributes = cityobject.get("attributes", {})

            if city_attributes:
                for att_key, att_value in city_attributes.items():
                    new_feature[f"attribute.{att_key}"] = _stringify_attribute(
                        att_value
                    )
            else:
                parent_attributes = self.get_attributes().get(
                    new_feature["parents"], {}
                )
                for att_key, att_value in parent_attributes.items():
                    new_feature[f"attribute.{att_key}"] = _stringify_attribute(
                        att_value
                    )

            if "geometry" in cityobject:
                return_geom = cityobject["geometry"]

                if read_geometry:
                    geom = self._geometry_reader.read_geometry(cityobject["geometry"])
                    new_feature.setGeometry(geom)
            else:
                return_geom = []

            return_features[new_feature] = return_geom

        return return_features

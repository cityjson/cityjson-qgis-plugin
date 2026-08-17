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
"""A module that provides the logic for loading CityJSON in QGIS"""

import json
import os
import re
from typing import Any

from qgis.core import QgsProject

from . import get_logger
from .geometry import GeometryReader, VerticesCache
from .layers import (
    AttributeFieldsDecorator,
    BaseFieldsBuilder,
    BaseNamingIterator,
    DynamicLayerManager,
    LodFeatureDecorator,
    LodFieldsDecorator,
    LodNamingDecorator,
    ParentFeatureDecorator,
    SemanticSurfaceFeatureDecorator,
    SemanticSurfaceFieldsDecorator,
    SimpleFeatureBuilder,
    TypeNamingIterator,
)
from .styling import (
    Copy2dStyling,
    NullStyling,
    SemanticSurfacesStyling,
    is_3d_styling_available,
    is_rule_based_3d_styling_available,
)

logger = get_logger("loading")


class CityJSONLoader:
    """Class that loads a CityJSON to a QGIS project"""

    def __init__(
        self,
        filepath: str,
        citymodel: dict[str, Any],
        epsg: str | None = None,
        keep_parent_attributes: bool = False,
        divide_by_object: bool = False,
        lod_as: str = "NONE",
        lod: str | list[str] = "All",
        load_semantic_surfaces: bool = False,
        style_semantic_surfaces: bool = False,
    ) -> None:
        filename_with_ext = os.path.basename(filepath)
        filename, _ = os.path.splitext(filename_with_ext)

        self.filepath = filepath
        self.filename = filename
        self.citymodel = citymodel
        self.srid = None
        self.lod = lod

        self.init_vertices()

        geometry_templates = None
        if "geometry-templates" in citymodel:
            geometry_templates = citymodel["geometry-templates"]

        self.geometry_reader: Any = GeometryReader(
            self.vertices_cache, geometry_templates, lod=self.lod
        )
        self.fields_builder: Any = AttributeFieldsDecorator(
            BaseFieldsBuilder(), citymodel
        )
        self.feature_builder: Any = SimpleFeatureBuilder(self.geometry_reader)

        if keep_parent_attributes:
            self.feature_builder = ParentFeatureDecorator(
                self.feature_builder, self.geometry_reader, citymodel
            )

        if lod_as in ["ATTRIBUTES", "LAYERS"]:
            self.fields_builder = LodFieldsDecorator(self.fields_builder)
            self.feature_builder = LodFeatureDecorator(
                self.feature_builder, self.geometry_reader
            )

        if load_semantic_surfaces:
            self.fields_builder = SemanticSurfaceFieldsDecorator(
                self.fields_builder, citymodel
            )
            self.feature_builder = SemanticSurfaceFeatureDecorator(
                self.feature_builder, self.geometry_reader, self.fields_builder
            )

        if divide_by_object:
            self.naming_iterator: Any = TypeNamingIterator(filename, citymodel)
        else:
            self.naming_iterator = BaseNamingIterator(filename)

        if lod_as == "LAYERS":
            self.naming_iterator = LodNamingDecorator(
                self.naming_iterator, filename, citymodel, self.geometry_reader
            )

        if epsg:
            self.srid = epsg

        self.layer_manager = DynamicLayerManager(
            self.citymodel,
            self.feature_builder,
            self.naming_iterator,
            self.fields_builder,
            self.srid,
        )

        self.layer_manager.prepare_attributes()

        if is_3d_styling_available():
            self.styler: Any = Copy2dStyling()
        else:
            self.styler = NullStyling()

        if (
            load_semantic_surfaces
            and is_rule_based_3d_styling_available()
            and style_semantic_surfaces
        ):
            self.styler = SemanticSurfacesStyling()

    def init_vertices(self) -> None:
        """Initialises the vertices cache"""
        self.vertices_cache = VerticesCache()

        if "transform" in self.citymodel:
            self.vertices_cache.set_scale(self.citymodel["transform"]["scale"])
            self.vertices_cache.set_translation(
                self.citymodel["transform"]["translate"]
            )

        verts = self.citymodel["vertices"]

        if len(verts) > 100:  # Only for larger datasets
            scale = self.vertices_cache._scale
            translate = self.vertices_cache._translate
            self.vertices_cache = VerticesCache(scale, translate, verts)
        else:
            # For smaller datasets, use the original method
            for v in verts:
                self.vertices_cache.add_vertex(v)

    def load(self, feedback: Any | None = None) -> int:
        """Loads a specified CityJSON file and returns the number of skipped geometries"""
        city_objects = self.citymodel["CityObjects"]

        current = 1
        step = 100.0 / len(city_objects)
        for key, obj in city_objects.items():
            if not self.geometry_reader.has_lod(obj.get("geometry", []), self.lod):
                continue

            self.layer_manager.add_object(key, obj)

            if feedback is not None:
                feedback.setProgress(int(current * step))
            current += 1

        root = QgsProject.instance().layerTreeRoot()

        if len(self.layer_manager.get_all_layers()) > 1:
            group = root.insertGroup(0, self.filename)

            for vl in self.layer_manager.get_all_layers():
                QgsProject.instance().addMapLayer(vl, False)
                group.insertLayer(0, vl)
                self.styler.apply(vl)

        elif len(self.layer_manager.get_all_layers()) == 1:
            for vl in self.layer_manager.get_all_layers():
                QgsProject.instance().addMapLayer(vl, False)
                root.insertLayer(0, vl)
                self.styler.apply(vl)

        return self.geometry_reader.skipped_geometries()


def load_cityjson_model(filepath: str) -> dict[str, Any]:
    """Returns the citymodel for the given filepath"""
    with open(filepath, encoding="utf-8-sig", buffering=8192) as fstream:
        citymodel = json.load(fstream)
    return citymodel


def get_model_epsg(citymodel: dict[str, Any]) -> str | None:
    """Returns the EPSG of the city model as a string, or None if not found"""

    if "metadata" not in citymodel:
        return None

    metadata = citymodel["metadata"]

    if "referenceSystem" not in metadata and "crs" not in metadata:
        return None

    if "crs" in metadata:
        try:
            crs_string = str(metadata["crs"]["epsg"])
            if crs_string is not None and crs_string != "None":
                return crs_string
            else:
                pass
        except (KeyError, TypeError):
            pass

    if "referenceSystem" in metadata:
        try:
            ref_string = str(metadata["referenceSystem"])

            if "::" in ref_string:
                return ref_string.split("::")[1]

            # Match CRS URL starting with 'https://www.opengis.net/def/crs/' and extract the last number
            p = re.compile(r"^https?://www\.opengis\.net/def/crs/.*/([0-9]+)$")
            m = p.match(ref_string)

            logger.debug(f"Regex match result: {ref_string}")

            if m is not None:
                logger.debug(f"Matching CRS: {m}")
                return m.group(1)
        except (KeyError, TypeError):
            return None

    return None

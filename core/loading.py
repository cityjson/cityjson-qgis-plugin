"""A module that provides the logic for loading CityJSON in QGIS"""

import json
import os
import re

from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsProject

from .geometry import GeometryReader, VerticesCache
from .layers import (AttributeFieldsDecorator, BaseFieldsBuilder,
                     BaseNamingIterator, DynamicLayerManager, ParentFeatureDecorator,
                     LodFeatureDecorator, LodFieldsDecorator,
                     LodNamingDecorator, SemanticSurfaceFeatureDecorator,
                     SemanticSurfaceFieldsDecorator, SimpleFeatureBuilder,
                     TypeNamingIterator)
from .styling import (Copy2dStyling, NullStyling, SemanticSurfacesStyling,
                      is_3d_styling_available,
                      is_rule_based_3d_styling_available)


class CityJSONLoader:
    """Class that loads a CityJSON to a QGIS project"""

    def __init__(self, filepath, citymodel,
                 epsg="None",
                 keep_parent_attributes=False,
                 divide_by_object=False,
                 lod_as='NONE',
                 lod='All',
                 load_semantic_surfaces=False,
                 style_semantic_surfaces=False):

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

        self.geometry_reader = GeometryReader(self.vertices_cache,
                                              geometry_templates,
                                              lod=self.lod)
        self.fields_builder = AttributeFieldsDecorator(BaseFieldsBuilder(),
                                                       citymodel)
        self.feature_builder = SimpleFeatureBuilder(self.geometry_reader)

        if keep_parent_attributes:
            self.feature_builder = ParentFeatureDecorator(self.feature_builder,
                                                          self.geometry_reader,
                                                          citymodel)

        if lod_as in ['ATTRIBUTES', 'LAYERS']:
            self.fields_builder = LodFieldsDecorator(self.fields_builder)
            self.feature_builder = LodFeatureDecorator(self.feature_builder,
                                                       self.geometry_reader)

        if load_semantic_surfaces:
            self.fields_builder = SemanticSurfaceFieldsDecorator(self.fields_builder,
                                                                 citymodel)
            self.feature_builder = SemanticSurfaceFeatureDecorator(self.feature_builder,
                                                                   self.geometry_reader,
                                                                   self.fields_builder)

        if divide_by_object:
            self.naming_iterator = TypeNamingIterator(filename, citymodel)
        else:
            self.naming_iterator = BaseNamingIterator(filename)

        if lod_as == 'LAYERS':
            self.naming_iterator = LodNamingDecorator(self.naming_iterator,
                                                      filename,
                                                      citymodel,
                                                      self.geometry_reader)

        if epsg != "None":
            self.srid = epsg

        self.layer_manager = DynamicLayerManager(self.citymodel,
                                                 self.feature_builder,
                                                 self.naming_iterator,
                                                 self.fields_builder,
                                                 self.srid)

        self.layer_manager.prepare_attributes()

        if is_3d_styling_available():
            self.styler = Copy2dStyling()
        else:
            self.styler = NullStyling()

        if (load_semantic_surfaces and is_rule_based_3d_styling_available() and style_semantic_surfaces):
            self.styler = SemanticSurfacesStyling()

    def init_vertices(self):
        """Initialises the vertices cache"""
        self.vertices_cache = VerticesCache()

        if "transform" in self.citymodel:
            self.vertices_cache.set_scale(self.citymodel["transform"]["scale"])
            self.vertices_cache.set_translation(self.citymodel["transform"]["translate"])

        verts = self.citymodel["vertices"]

        for v in verts:
            self.vertices_cache.add_vertex(v)

    def load(self, feedback=None):
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
            group = root.addGroup(self.filename)

            for vl in self.layer_manager.get_all_layers():
                QgsProject.instance().addMapLayer(vl, False)
                group.addLayer(vl)
                self.styler.apply(vl)

        elif len(self.layer_manager.get_all_layers()) == 1:
            for vl in self.layer_manager.get_all_layers():
                QgsProject.instance().addMapLayer(vl, False)
                root.addLayer(vl)
                self.styler.apply(vl)

        return self.geometry_reader.skipped_geometries()

def load_cityjson_model(filepath):
    """Returns the citymodel for the given filepath"""
    file = open(filepath, encoding='utf-8-sig')
    citymodel = json.load(file)
    file.close()

    return citymodel

def get_model_epsg(citymodel):
    """Returns the EPSG of the city model, if exists it exists in the metadata"""
    if "metadata" in citymodel:
        metadata = citymodel["metadata"]

        if "crs" in metadata:
            return str(metadata["crs"]["epsg"])

        if "referenceSystem" in metadata:
            ref_string = str(metadata["referenceSystem"])

            if ref_string.__contains__("::"):
                return ref_string.split("::")[1]

            p = re.compile(r"https:\/\/www.opengis.net\/def\/crs\/([A-Z]+)\/([0-9]+)\/([0-9]+)")
            m = p.match(ref_string)

            if m:
                return m.group(3)
            else:
                return "None"
        else:
            return "None"

    return "None"

"""A module that provides the logic for loading CityJSON in QGIS"""

import json
import os

from PyQt5.QtWidgets import QMessageBox
from qgis.core import QgsProject

from .geometry import GeometryReader, VerticesCache
from .layers import (AttributeFieldsDecorator, BaseFieldsBuilder,
                     BaseNamingIterator, DynamicLayerManager,
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
                 divide_by_object=False,
                 lod_as='NONE',
                 load_semantic_surfaces=False,
                 style_semantic_surfaces=False):
        filename_with_ext = os.path.basename(filepath)
        filename, _ = os.path.splitext(filename_with_ext)

        self.filepath = filepath
        self.filename = filename
        self.citymodel = citymodel
        self.srid = None

        self.init_vertices()

        geometry_templates = None
        if "geometry-templates" in citymodel:
            geometry_templates = citymodel["geometry-templates"]
        self.geometry_reader = GeometryReader(self.vertices_cache,
                                              geometry_templates)

        self.fields_builder = AttributeFieldsDecorator(BaseFieldsBuilder(),
                                                       citymodel)
        self.feature_builder = SimpleFeatureBuilder(self.geometry_reader)

        if lod_as in ['ATTRIBUTES', 'LAYERS']:
            self.fields_builder = LodFieldsDecorator(self.fields_builder)
            self.feature_builder = LodFeatureDecorator(self.feature_builder,
                                                       self.geometry_reader)

        if load_semantic_surfaces:
            self.fields_builder = SemanticSurfaceFieldsDecorator(self.fields_builder)
            self.feature_builder = SemanticSurfaceFeatureDecorator(self.feature_builder,
                                                                   self.geometry_reader)

        if divide_by_object:
            self.naming_iterator = TypeNamingIterator(filename, citymodel)
        else:
            self.naming_iterator = BaseNamingIterator(filename)

        if load_semantic_surfaces == 'LAYERS':
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

        if (load_semantic_surfaces
                and is_rule_based_3d_styling_available()
                and style_semantic_surfaces):
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

    def load(self):
        """Loads a specified CityJSON file and returns the number of
        skipped geometries
        """
        city_objects = self.citymodel["CityObjects"]

        # Iterate through the city objects
        for key, obj in city_objects.items():
            self.layer_manager.add_object(key, obj)

        # Add the layer(s) to the project
        root = QgsProject.instance().layerTreeRoot()
        group = root.addGroup(self.filename)
        for vl in self.layer_manager.get_all_layers():
            QgsProject.instance().addMapLayer(vl, False)
            group.addLayer(vl)

            self.styler.apply(vl)

        return self.geometry_reader.skipped_geometries()

def load_cityjson_model(filepath):
    """Returns the citymodel for the given filepath"""

    file = open(filepath, encoding='utf-8-sig')
    citymodel = json.load(file)
    file.close()

    return citymodel

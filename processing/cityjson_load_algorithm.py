# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsFeatureSink, QgsProcessing, QgsProcessingAlgorithm,
                       QgsProcessingException, QgsProcessingParameterBoolean,
                       QgsProcessingParameterCrs, QgsProcessingParameterEnum,
                       QgsProcessingParameterFile, QgsProcessingParameterExtent)

from ..core.loading import CityJSONLoader, get_model_epsg, load_cityjson_model
from ..core.utils import get_subset_bbox, get_subset_cotype

class CityJsonLoadAlrogithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.
    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.
    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    DIVIDE_BY_OBJECT_TYPE = 'DIVIDE_BY_OBJECT_TYPE'
    LOD_AS = 'LOD_AS'
    LOAD_SEMANTIC_SURFACES = 'LOAD_SEMANTIC_SURFACES'
    STYLE_BY_SEMANTIC_SURFACES = 'STYLE_BY_SEMANTIC_SURFACES'
    SRID = 'SRID'
    BBOX = 'BBOX'
    OBJECT_TYPE = 'OBJECT_TYPE'

    OBJECTTYPES = ['Building', 'Bridge', 'Road', 'TransportSquare', 'LandUse', 'Railway', 'TINRelief', 'WaterBody', 'PlantCover', 'SolitaryVegetationObject', 'CityFurniture', 'GenericCityObject', 'Tunnel']

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        """
        Returns an instance of the algorithm.
        """
        return CityJsonLoadAlrogithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'loadcityjson'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Load CityJSON')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Import')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'import'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Imports a CityJSON file to QGIS")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                self.tr('CityJSON file'),
                extension='json'
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DIVIDE_BY_OBJECT_TYPE,
                self.tr('Split city objects to layers by type'),
                False
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.LOD_AS,
                self.tr('Load LoD as'),
                ['NONE', 'ATTRIBUTES', 'LAYERS'],
                defaultValue='NONE'
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.LOAD_SEMANTIC_SURFACES,
                self.tr('Load semantic surfaces'),
                defaultValue=False
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.STYLE_BY_SEMANTIC_SURFACES,
                self.tr('Style by semantic surfaces'),
                defaultValue=False
            )
        )

        self.addParameter(
            QgsProcessingParameterCrs(
                self.SRID,
                self.tr('CRS'),
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterExtent(
                self.BBOX,
                self.tr('Filter by area'),
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.OBJECT_TYPE,
                self.tr('Filter by type'),
                self.OBJECTTYPES,
                allowMultiple=True,
                optional=True
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        filepath = self.parameterAsFile(
            parameters,
            self.INPUT,
            context
        )

        if filepath is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT))

        divide_by_type = self.parameterAsBoolean(
            parameters,
            self.DIVIDE_BY_OBJECT_TYPE,
            context
        )

        lod_as = self.parameterAsEnum(
            parameters,
            self.LOD_AS,
            context
        )

        load_semantic_surfaces = self.parameterAsBoolean(
            parameters,
            self.LOAD_SEMANTIC_SURFACES,
            context
        )

        style_semantic_surfaces = self.parameterAsBoolean(
            parameters,
            self.STYLE_BY_SEMANTIC_SURFACES,
            context
        )

        crs = self.parameterAsCrs(
            parameters,
            self.SRID,
            context
        )

        feedback.setProgressText("Loading city model...")
        cm = load_cityjson_model(filepath)

        feedback.pushInfo("Loaded {} objects.".format(len(cm["CityObjects"])))

        if crs.isValid():
            epsg = crs.postgisSrid()
        else:
            feedback.pushInfo("No CRS selected! Looking for CRS definition in metadata...")
            epsg = get_model_epsg(cm)
            if epsg != 'None':
                feedback.pushInfo("CRS found: {}.".format(epsg))
            else:
                feedback.pushInfo("No CRS found.")
        
        if epsg == 'None':
            extent = self.parameterAsExtent(
                parameters,
                self.BBOX,
                context
            )
        else:
            extent = self.parameterAsExtent(
                parameters,
                self.BBOX,
                context,
                crs = crs
            )

        if not extent.isNull():
            feedback.setProgressText("Filtering objects by extent...")
            cm = self.subset_bbox(cm, extent)
            feedback.pushInfo("Found {} objects.".format(len(cm["CityObjects"])))
        
        object_types = self.parameterAsEnums(
            parameters,
            self.OBJECT_TYPE,
            context
        )

        if len(object_types) > 0:
            feedback.setProgressText("Filtering objects by type...")
            cm = self.subset_cotype(cm, [self.OBJECTTYPES[t] for t in object_types])
            feedback.pushInfo("Found {} objects.".format(len(cm["CityObjects"])))

        if len(cm["CityObjects"]) == 0:
            feedback.pushInfo("No objects to load. Skipping!")
            return {'STATUS': 'SUCCESS'}

        feedback.setProgressText("Transforming city objects...")
        loader = CityJSONLoader(filepath,
                                cm,
                                epsg=epsg,
                                divide_by_object=divide_by_type,
                                lod_as=lod_as,
                                load_semantic_surfaces=load_semantic_surfaces,
                                style_semantic_surfaces=style_semantic_surfaces)
        loader.load(feedback=feedback)

        return {'STATUS': 'SUCCESS'}

    def subset_bbox(self, cm, rectangle):
        """
        Returns a subset of the original city model based on the defined
        extent.
        """

        bbox = [
            rectangle.xMinimum(),
            rectangle.yMinimum(),
            rectangle.xMaximum(),
            rectangle.yMaximum()
        ]

        sub_cm = get_subset_bbox(cm, bbox)

        return sub_cm

    def subset_cotype(self, cm, cotype):
        sub_cm = get_subset_cotype(cm, cotype)

        return sub_cm
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

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
)
from qgis.PyQt.QtCore import QCoreApplication

try:
    # When running as QGIS plugin
    from ..core.loading import CityJSONLoader, get_model_epsg, load_cityjson_model
    from ..core.utils import get_subset_bbox, get_subset_cotype
except ImportError:
    # When running tests or standalone
    from core.loading import CityJSONLoader, get_model_epsg, load_cityjson_model
    from core.utils import get_subset_bbox, get_subset_cotype


class CityJsonLoadAlgorithm(QgsProcessingAlgorithm):
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

    INPUT = "INPUT"
    KEEP_PARENT_ATTRIBUTES = "KEEP_PARENT_ATTRIBUTES"
    DIVIDE_BY_OBJECT_TYPE = "DIVIDE_BY_OBJECT_TYPE"
    LOD_AS = "LOD_AS"
    LOD_SELECTION = "LOD_SELECTION"
    LOAD_SEMANTIC_SURFACES = "LOAD_SEMANTIC_SURFACES"
    STYLE_BY_SEMANTIC_SURFACES = "STYLE_BY_SEMANTIC_SURFACES"
    SRID = "SRID"
    BBOX = "BBOX"
    OBJECT_TYPE = "OBJECT_TYPE"

    LODLOADINGTYPES = ["NONE", "ATTRIBUTES", "LAYERS"]
    LODSELECTIONTYPES = [
        "0",
        "1.1",
        "1.2",
        "1.3",
        "2.0",
        "2.1",
        "2.2",
        "2.3",
        "3.0",
        "3.1",
        "3.2",
        "3.3",
    ]
    OBJECTTYPES = [
        "Building",
        "Bridge",
        "Road",
        "TransportSquare",
        "LandUse",
        "Railway",
        "TINRelief",
        "WaterBody",
        "PlantCover",
        "SolitaryVegetationObject",
        "CityFurniture",
        "GenericCityObject",
        "Tunnel",
    ]

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        """
        Returns an instance of the algorithm.
        """
        return CityJsonLoadAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "loadcityjson"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Load CityJSON")

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr("Import")

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "import"

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Imports a CityJSON file to QGIS")

    def flags(self):
        return super().flags() | QgsProcessingAlgorithm.Flag.FlagNoThreading

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT, self.tr("CityJSON file"), extension="json"
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.KEEP_PARENT_ATTRIBUTES, self.tr("Retain parent attributes"), False
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DIVIDE_BY_OBJECT_TYPE,
                self.tr("Split city objects to layers by type"),
                False,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.LOD_AS,
                self.tr("Load LoD as"),
                self.LODLOADINGTYPES,
                defaultValue="NONE",
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.LOD_SELECTION,
                self.tr("Select specific LoD(s) (leave empty for all)"),
                self.LODSELECTIONTYPES,
                allowMultiple=True,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.LOAD_SEMANTIC_SURFACES,
                self.tr("Load semantic surfaces"),
                defaultValue=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.STYLE_BY_SEMANTIC_SURFACES,
                self.tr("Style by semantic surfaces"),
                defaultValue=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterCrs(self.SRID, self.tr("CRS"), optional=True)
        )

        self.addParameter(
            QgsProcessingParameterExtent(
                self.BBOX, self.tr("Filter by area"), optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.OBJECT_TYPE,
                self.tr("Filter by type"),
                self.OBJECTTYPES,
                allowMultiple=True,
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        filepath = self.parameterAsFile(parameters, self.INPUT, context)

        if filepath is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        keep_parent_attributes = self.parameterAsBoolean(
            parameters, self.KEEP_PARENT_ATTRIBUTES, context
        )

        divide_by_type = self.parameterAsBoolean(
            parameters, self.DIVIDE_BY_OBJECT_TYPE, context
        )

        lod_as = self.parameterAsEnum(parameters, self.LOD_AS, context)

        lod_as = self.LODLOADINGTYPES[lod_as]

        lod_selection = self.parameterAsEnums(parameters, self.LOD_SELECTION, context)

        if len(lod_selection) == 0:
            lod = "All"
            feedback.pushInfo("Loading all LoDs")
        elif len(lod_selection) == 1:
            lod = self.LODSELECTIONTYPES[lod_selection[0]]
            feedback.pushInfo(f"Loading LoD: {lod}")
        else:
            lod = [self.LODSELECTIONTYPES[idx] for idx in lod_selection]
            feedback.pushInfo("Loading multiple LoDs: {}".format(", ".join(lod)))

        load_semantic_surfaces = self.parameterAsBoolean(
            parameters, self.LOAD_SEMANTIC_SURFACES, context
        )

        style_semantic_surfaces = self.parameterAsBoolean(
            parameters, self.STYLE_BY_SEMANTIC_SURFACES, context
        )

        crs = self.parameterAsCrs(parameters, self.SRID, context)

        feedback.setProgressText("Loading city model...")
        cm = load_cityjson_model(filepath)

        feedback.pushInfo("Loaded {} objects.".format(len(cm["CityObjects"])))

        if crs.isValid():
            epsg = crs.postgisSrid()
        else:
            feedback.pushInfo(
                "No CRS selected! Looking for CRS definition in metadata..."
            )
            epsg = get_model_epsg(cm)
            if epsg:
                feedback.pushInfo(f"CRS found: {epsg}.")
            else:
                feedback.pushInfo("No CRS found.")

        if epsg is None:
            extent = self.parameterAsExtent(parameters, self.BBOX, context)
        else:
            extent = self.parameterAsExtent(parameters, self.BBOX, context, crs=crs)

        if not extent.isNull():
            feedback.setProgressText("Filtering objects by extent...")
            bbox = [
                extent.xMinimum(),
                extent.yMinimum(),
                extent.xMaximum(),
                extent.yMaximum(),
            ]
            cm = get_subset_bbox(cm, bbox)
            feedback.pushInfo("Found {} objects.".format(len(cm["CityObjects"])))

        object_types = self.parameterAsEnums(parameters, self.OBJECT_TYPE, context)

        if len(object_types) > 0:
            feedback.setProgressText("Filtering objects by type...")
            cm = get_subset_cotype(cm, [self.OBJECTTYPES[t] for t in object_types])
            feedback.pushInfo("Found {} objects.".format(len(cm["CityObjects"])))

        if len(cm["CityObjects"]) == 0:
            feedback.pushInfo("No objects to load. Skipping!")
            return {"STATUS": "SUCCESS"}

        feedback.setProgressText("Transforming city objects...")
        loader = CityJSONLoader(
            filepath,
            cm,
            epsg=epsg,
            keep_parent_attributes=keep_parent_attributes,
            divide_by_object=divide_by_type,
            lod_as=lod_as,
            lod=lod,
            load_semantic_surfaces=load_semantic_surfaces,
            style_semantic_surfaces=style_semantic_surfaces,
        )
        loader.load(feedback=feedback)

        return {"STATUS": "SUCCESS"}

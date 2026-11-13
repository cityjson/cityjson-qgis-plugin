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

import os
from typing import Any

from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterMultipleLayers,
)
from qgis.PyQt.QtCore import QCoreApplication

try:
    # When running as QGIS plugin
    from ..core.exporting import CityJSONExporter, save_cityjson_model
    from ..core.loading import load_cityjson_model
except ImportError:
    # When running tests or standalone
    from core.exporting import CityJSONExporter, save_cityjson_model
    from core.loading import load_cityjson_model


class CityJsonExportAlgorithm(QgsProcessingAlgorithm):
    """
    Exports QGIS layers loaded from a CityJSON file back to CityJSON.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = "INPUT"
    LAYERS = "LAYERS"
    OUTPUT = "OUTPUT"
    LOD_SELECTION = "LOD_SELECTION"
    KEEP_UNLOADED = "KEEP_UNLOADED"
    SEMANTIC_SURFACES = "SEMANTIC_SURFACES"

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

    def tr(self, string: str) -> str:
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def createInstance(self) -> "CityJsonExportAlgorithm":
        """
        Returns an instance of the algorithm.
        """
        return CityJsonExportAlgorithm()

    def name(self) -> str:
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "exportcityjson"

    def displayName(self) -> str:
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Export CityJSON")

    def group(self) -> str:
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr("Export")

    def groupId(self) -> str:
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "export"

    def shortHelpString(self) -> str:
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Export a CityJSON file from QGIS")

    def flags(self) -> Any:
        return super().flags() | QgsProcessingAlgorithm.Flag.FlagNoThreading

    def initAlgorithm(self, config: dict[str, Any] | None = None) -> None:
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.LAYERS,
                self.tr("Layers to export"),
                Qgis.ProcessingSourceType.VectorAnyGeometry,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT, self.tr("Original CityJSON file"), extension="json"
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.LOD_SELECTION,
                self.tr("LoD(s) loaded (leave empty for all)"),
                self.LODSELECTIONTYPES,
                allowMultiple=True,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.KEEP_UNLOADED, self.tr("Keep unloaded LoDs and objects"), True
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SEMANTIC_SURFACES,
                self.tr("Semantic surfaces were loaded"),
                False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, self.tr("Output CityJSON file"), "CityJSON (*.json)"
            )
        )

    def processAlgorithm(
        self, parameters: dict[str, Any], context: Any, feedback: Any
    ) -> dict[str, Any]:
        """
        Here is where the processing itself takes place.
        """
        # Read and validate the source file first
        filepath = self.parameterAsFile(parameters, self.INPUT, context)
        if not filepath:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        # Read the other inputs
        layers = self.parameterAsLayerList(parameters, self.LAYERS, context)
        lod_selection = self.parameterAsEnums(parameters, self.LOD_SELECTION, context)
        keep_unloaded = self.parameterAsBoolean(parameters, self.KEEP_UNLOADED, context)
        semantic_surfaces = self.parameterAsBoolean(
            parameters, self.SEMANTIC_SURFACES, context
        )
        output = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        # Never overwrite the source: export reads it as the original model
        if os.path.normcase(os.path.abspath(output)) == os.path.normcase(
            os.path.abspath(filepath)
        ):
            raise QgsProcessingException(
                "Output file is the same as the original CityJSON file. Choose another path."
            )

        # Convert the LoD
        lod: str | list[str]
        if len(lod_selection) == 0:
            lod = "All"
            feedback.pushInfo("Exporting all LoDs")
        elif len(lod_selection) == 1:
            lod = self.LODSELECTIONTYPES[lod_selection[0]]
            feedback.pushInfo(f"Exporting LoD: {lod}")
        else:
            lod = [self.LODSELECTIONTYPES[idx] for idx in lod_selection]
            feedback.pushInfo("Exporting multiple LoDs: {}".format(", ".join(lod)))

        # Load the original model
        feedback.setProgressText("Loading original CityJSON...")
        citymodel = load_cityjson_model(filepath)
        feedback.pushInfo(
            "Original has {} objects.".format(len(citymodel["CityObjects"]))
        )

        # Export
        feedback.setProgressText("Exporting...")
        exporter = CityJSONExporter(
            layers,
            citymodel,
            loaded_lod=lod,
            keep_unloaded=keep_unloaded,
            semantic_surfaces=semantic_surfaces,
        )
        try:
            exported = exporter.export()
        except ValueError as e:
            raise QgsProcessingException(str(e))

        # Save
        feedback.setProgressText("Writing file...")
        save_cityjson_model(exported, output)
        feedback.pushInfo(
            "Wrote {} objects to {}.".format(len(exported["CityObjects"]), output)
        )

        return {self.OUTPUT: output}

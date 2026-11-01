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

from typing import Any

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFile,
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
            QgsProcessingParameterFile(
                self.INPUT, self.tr("CityJSON file"), extension="json,jsonl"
            )
        )

    def processAlgorithm(
        self, parameters: dict[str, Any], context: Any, feedback: Any
    ) -> dict[str, Any]:
        """
        Here is where the processing itself takes place.
        """
        return {}
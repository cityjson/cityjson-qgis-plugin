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

"""This is a module that contains the provider for
QGIS processing algorithms"""

import os
from typing import Any

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .cityjson_load_algorithm import CityJsonLoadAlgorithm


class Provider(QgsProcessingProvider):
    def loadAlgorithms(self, *args: Any, **kwargs: Any) -> None:
        self.addAlgorithm(CityJsonLoadAlgorithm())

    def id(self, *args: Any, **kwargs: Any) -> str:
        """The ID of your plugin, used for identifying the provider.

        This string should be a unique, short, character only string,
        eg "qgis" or "gdal". This string should not be localised.
        """
        return "cityjsonloader"

    def name(self, *args: Any, **kwargs: Any) -> str:
        """The human friendly name of your plugin in Processing.

        This string should be as short as possible (e.g. "Lastools", not
        "Lastools version 1.0.1 64-bit") and localised.
        """
        return self.tr("CityJSON Loader")

    def icon(self) -> QIcon:
        """Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return QIcon(os.path.join(plugin_dir, "cityjson_logo.svg"))

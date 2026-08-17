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

"""This script initializes the plugin, making it known to QGIS."""

from typing import TYPE_CHECKING

from qgis.gui import QgisInterface

if TYPE_CHECKING:
    from .cityjson_loader import CityJsonLoader


def classFactory(iface: QgisInterface) -> "CityJsonLoader":
    """Load CityJsonLoader class from file CityJsonLoader.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .cityjson_loader import CityJsonLoader

    return CityJsonLoader(iface)

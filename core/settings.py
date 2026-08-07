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
"""A module to manage the settings of the plugin"""

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtGui import QColor

semantic_colors = {
    "RoofSurface": {
        "diffuse": QColor(255, 0, 0),
        "ambient": QColor(255, 0, 0),
        "specular": None,
    },
    "WallSurface": {
        "diffuse": QColor(200, 200, 200),
        "ambient": QColor(255, 255, 255),
        "specular": None,
    },
    "GroundSurface": {
        "diffuse": QColor(0, 0, 0),
        "ambient": QColor(0, 0, 0),
        "specular": None,
    },
    "Door": {
        "diffuse": QColor(255, 200, 0),
        "ambient": QColor(255, 200, 0),
        "specular": None,
    },
    "Window": {
        "diffuse": QColor(0, 100, 255),
        "ambient": QColor(0, 100, 255),
        "specular": None,
    },
}


def get_color_int(color):
    """Returns the int representation of a QColor"""
    return None if color is None else color.getRgb()


def save_defaults():
    """Saves the default values"""
    settings = QSettings()
    settings.beginGroup("CityJSON Loader")
    settings.beginWriteArray("semantic_colors")
    i = 0
    for surface, colors in semantic_colors.items():
        settings.setArrayIndex(i)
        settings.setValue("surface", surface)
        settings.setValue("diffuse", get_color_int(colors["diffuse"]))
        settings.setValue("ambient", get_color_int(colors["ambient"]))
        settings.setValue("specular", get_color_int(colors["specular"]))
        i += 1
    settings.endArray()
    settings.endGroup()


def load_settings():
    """Loads the settings from the app's registry"""

    result = {"semantic_colors": semantic_colors}

    return result

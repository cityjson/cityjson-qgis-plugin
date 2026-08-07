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
"""A module related to apply styling in QGIS layers"""

from qgis.core import Qgis

from .settings import load_settings

try:
    from qgis._3d import (
        QgsPhongMaterialSettings,
        QgsPolygon3DSymbol,
        QgsVectorLayer3DRenderer,
    )

    has_3d = True
except ImportError:
    has_3d = False

try:
    from qgis._3d import QgsRuleBased3DRenderer

    has_rules = True
except ImportError:
    has_rules = False


class NullStyling:
    """A class that applies no styling to the provided layer"""

    def apply(self, vectorlayer):
        """Applies no style to the vector layer"""
        return


class Copy2dStyling:
    """A class that applies to 3D the same color as in 2D"""

    def __init__(self):
        if not has_3d:
            raise Exception("3D styling is not available for this version of QGIS!")

    def apply(self, vectorlayer):
        """Applies the style to the vector layer"""
        material = create_material(vectorlayer.renderer().symbol().color())

        symbol = QgsPolygon3DSymbol()

        # setMaterial method renamed to setMaterialSettings in QGIS 3.30 and is API breaking
        if Qgis.versionInt() < 33000:
            symbol.setMaterial(material)
        else:
            symbol.setMaterialSettings(material)

        symbol.setEdgesEnabled(True)
        symbol.setAltitudeClamping(Qgis.AltitudeClamping.Absolute)

        renderer = QgsVectorLayer3DRenderer()
        renderer.setLayer(vectorlayer)
        renderer.setSymbol(symbol)
        vectorlayer.setRenderer3D(renderer)


class SemanticSurfacesStyling:
    """A class that applies colors for semantic surfaces"""

    def __init__(self, colors=None, else_color=None):
        if colors is None:
            settings = load_settings()
            self._colors = settings["semantic_colors"]
        else:
            self._colors = colors
        self._else_color = else_color
        if not has_rules:
            raise Exception(
                "Rule-based 3D styling is not available for this version of QGIS!"
            )

    def apply(self, vectorlayer):
        """Applies the style to the vector layer"""
        root_rule = QgsRuleBased3DRenderer.Rule(None)
        for surface_type, colors in self._colors.items():
            material = create_material(
                colors["diffuse"], colors["ambient"], colors["specular"]
            )

            symbol = QgsPolygon3DSymbol()

            # setMaterial method renamed to setMaterialSettings in QGIS 3.30 and is API breaking
            if Qgis.versionInt() < 33000:
                symbol.setMaterial(material)
            else:
                symbol.setMaterialSettings(material)

            symbol.setEdgesEnabled(True)

            new_rule = QgsRuleBased3DRenderer.Rule(
                symbol, f"\"surface.type\" = '{surface_type}'"
            )
            root_rule.appendChild(new_rule)

        if self._else_color is None:
            material = create_material(vectorlayer.renderer().symbol().color())
        else:
            material = create_material(self._else_color)

        symbol = QgsPolygon3DSymbol()

        # setMaterial method renamed to setMaterialSettings in QGIS 3.30 and is API breaking
        if Qgis.versionInt() < 33000:
            symbol.setMaterial(material)
        else:
            symbol.setMaterialSettings(material)

        symbol.setEdgesEnabled(True)

        new_rule = QgsRuleBased3DRenderer.Rule(symbol, "ELSE")
        root_rule.appendChild(new_rule)

        renderer = QgsRuleBased3DRenderer(root_rule)
        renderer.setLayer(vectorlayer)
        vectorlayer.setRenderer3D(renderer)


def create_material(diffuse_color, ambient_color=None, specular_color=None):
    """Create a material with the provided colors"""
    material = QgsPhongMaterialSettings()

    material.setDiffuse(diffuse_color)
    if ambient_color is not None:
        material.setAmbient(ambient_color)
    if specular_color is not None:
        material.setSpecular(specular_color)

    return material


def is_3d_styling_available():
    """Returns True if 3D styling through Python is possible"""
    return has_3d


def is_rule_based_3d_styling_available():
    """Returns true if rule-based 3D styling is possible"""
    return has_rules

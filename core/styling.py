"""A module related to apply styling in QGIS layers"""

from qgis.PyQt.QtGui import QColor

try:
    from qgis._3d import (QgsPhongMaterialSettings,
                          QgsPolygon3DSymbol,
                          QgsVectorLayer3DRenderer)
    has_3d = True
except ImportError:
    has_3d = False

try:
    from qgis._3d import QgsRuleBased3DRenderer
    has_rules = True
except ImportError:
    has_rules = False

semantic_colors = {
    "RoofSurface": {
        "diffuse": QColor(255, 0, 0),
        "ambient": QColor(255, 0, 0),
        "specular": None
    },
    "WallSurface": {
        "diffuse": QColor(200, 200, 200),
        "ambient": QColor(255, 255, 255),
        "specular": None
    },
    "GroundSurface": {
        "diffuse": QColor(0, 0, 0),
        "ambient": QColor(0, 0, 0),
        "specular": None
    },
    "Door": {
        "diffuse": QColor(255, 200, 0),
        "ambient": QColor(255, 200, 0),
        "specular": None
    },
    "Window": {
        "diffuse": QColor(0, 100, 255),
        "ambient": QColor(0, 100, 255),
        "specular": None
    }
}

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
        symbol.setMaterial(material)

        renderer = QgsVectorLayer3DRenderer()
        renderer.setLayer(vectorlayer)
        renderer.setSymbol(symbol)
        vectorlayer.setRenderer3D(renderer)

class SemanticSurfacesStyling:
    """A class that applies colors for semantic surfaces"""

    def __init__(self):
        if not has_rules:
            raise Exception("Rule-based 3D styling is not available for this version of QGIS!")

    def apply(self, vectorlayer):
        """Applies the style to the vector layer"""
        root_rule = QgsRuleBased3DRenderer.Rule(None)
        for surface_type, colors in semantic_colors.items():
            material = create_material(colors["diffuse"], colors["ambient"], colors["specular"])

            symbol = QgsPolygon3DSymbol()
            symbol.setMaterial(material)

            new_rule = QgsRuleBased3DRenderer.Rule(symbol, "\"semantic_surface\" = '{surface}'".format(surface=surface_type))
            root_rule.appendChild(new_rule)

        material = create_material(QColor(255, 0, 255))

        symbol = QgsPolygon3DSymbol()
        symbol.setMaterial(material)

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

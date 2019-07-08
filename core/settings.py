"""A module to manage the settings of the plugin"""

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtGui import QColor

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

def get_color_int(color):
    """Returns the int representation of a QColor"""
    if color is None:
        return None
    else:
        return color.getRgb()

def get_color_from_tuple(data):
    """Returns a color created from a tuple"""
    if data is None:
        return None
    else:
        r, g, b, a = data
        return QColor(r, g, b, a)

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
        i = i + 1
    settings.endArray()
    settings.endGroup()

def load_settings():
    """Loads the settings from the app's registry"""
    settings = QSettings()
    if not settings.contains("CityJSON Loader"):
        save_defaults()
    settings.beginGroup("CityJSON Loader")

    colors = {}
    size = settings.beginReadArray("semantic_colors")
    for i in range(size):
        settings.setArrayIndex(i)
        surface = settings.value("surface")
        colors[surface] = {}
        colors[surface]["diffuse"] = get_color_from_tuple(settings.value("diffuse"))
        colors[surface]["ambient"] = get_color_from_tuple(settings.value("ambient"))
        colors[surface]["specular"] = get_color_from_tuple(settings.value("specular"))
        i = i + 1
    settings.endArray()
    settings.endGroup()

    return colors

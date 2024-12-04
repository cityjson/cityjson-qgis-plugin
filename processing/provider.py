"""This is a module that contains the provider for
QGIS processing algorithms"""

from qgis.core import QgsProcessingProvider
from PyQt5.QtGui import QIcon

from .cityjson_load_algorithm import CityJsonLoadAlgorithm

class Provider(QgsProcessingProvider):

    def loadAlgorithms(self, *args, **kwargs):
        self.addAlgorithm(CityJsonLoadAlrogithm())

    def id(self, *args, **kwargs):
        """The ID of your plugin, used for identifying the provider.

        This string should be a unique, short, character only string,
        eg "qgis" or "gdal". This string should not be localised.
        """
        return 'cityjsonloader'

    def name(self, *args, **kwargs):
        """The human friendly name of your plugin in Processing.

        This string should be as short as possible (e.g. "Lastools", not
        "Lastools version 1.0.1 64-bit") and localised.
        """
        return self.tr('CityJSON Loader')

    def icon(self):
        """Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        icon_path = ':/plugins/cityjson_loader/cityjson_logo.svg'
        return QIcon(icon_path)

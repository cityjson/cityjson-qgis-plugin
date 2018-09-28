# CityJSON Loader for QGIS 3

This is a Python plugin for QGIS 3 which adds support for [CityJSON](http://www.cityjson.org) datasets.

## Installation

"Stable" releases are available through the official QGIS plugins repository (although the plugin is still experimental).

* In QGIS 3 select `Plugins`->`Manage and Install Plugins...`
* In the `Settings` panel enable the `Show also experimental plugins`.
* In the `All` panel select the `CityJSON Loader` plugin from the list.

*You should enable *

## Use

After the installation, there must be a new submenu under the `Vector` menu. Select `CityJSON Loader`->`Load CityJSON...` in order to open the CityJSON dialog window. You can select a dataset and add it from there.

You may enable the `Split layers according to object type` option in order to load different object types as different layers in QGIS.

In order to view the 3D data you must have QGIS installed with the 3D capabilities. For every layer of the CityJSON file you have to enable 3D rendering as follows:
* Right-click on the layer and select `Properties...`
* Select the `3D View` panel and check the `Enable 3D renderer` option.
* In QGIS 3 menu select `View`->`New 3D Map View` in order to see the 3D geometry.
# This fork of **cityjson-qgis-plugin** includes fixes and support for additional semantic surface attributes

## Key Updates:

- **New feature(s)**: Support for additional semantic surface attributes when loading a cityjson file using option ***Load semantic surfaces (as individual features)***.
  Compatible with cityjson files generated using my own version of **3d-building-metrics** https://github.com/FLeroux23/3d-building-metrics
- **Fixes**:
     - Fix error: 'QgsPolygon3DSymbol' object has no attribute 'setMaterial'
 
- **New feature(s)**: A checkbox to control whether child objects retain parent attributes
___
# CityJSON Loader for QGIS 3

This is a Python plugin for QGIS 3 which adds support for loading [CityJSON](http://www.cityjson.org) datasets in QGIS.

## Installation

"Stable" releases are available through the official QGIS plugins repository.

* In QGIS 3 select `Plugins`->`Manage and Install Plugins...`
* In the `All` panel select the `CityJSON Loader` plugin from the list.

## Use

After the installation, there must be a new submenu under the `Vector` menu. Select `CityJSON Loader`->`Load CityJSON...` in order to open the CityJSON dialog window. You can select a dataset and add it from there.

You may enable the `Split layers according to object type` option in order to load different object types as different layers in QGIS.

### 3D view in QGIS 3.0

CityJSON Loader automatically enables 3D renderer in QGIS versions 3.2 onwards.
However, if you are using QGIS 3.0 you have to enable it manually.
This can be done as follows:
* Right-click on the layer and select `Properties...`
* Select the `3D View` panel and check the `Enable 3D renderer` option.
* In QGIS 3 menu select `View`->`New 3D Map View` in order to see the 3D geometry.

## Development

You may use `make` to assist you while developing.

The following rules can be useful:
* `make deploy`: will automatically copy the required files to your QGIS plugins' folder. **BEWARE:** *it only works out-of-the-box for macOS. For other operating systems you might have to change the `QGISDIR` variable in `Makefile`.*
* `make package VERSION=GIT_REF`: (where *GIT_REF* is a branch, tag or any other git ref) will make a zip package to be installed manually from QGIS or uploaded to the QGIS plugins' repository.

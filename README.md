# This fork of <ins>**cityjson-qgis-plugin**</ins> includes bug fixes, improvements and support for new features

## Key Updates:
### **New Features Added in This Version**
- **Enhanced User Interface**:
  - **Non-modal Dialog**: Dialog now stays open after processing (geoprocessing tool style)
  - **Asynchronous Processing**: Background file processing with timer-based architecture prevents UI freezing
  - **File Management**: Added file count label and "Clear All" button for better file management
  - **Progress Tracking**: Added progress bar and "Cancel" button for long-running operations
  - **Improved Controls**: Replaced Ok/Cancel buttons with clearer "Load" and "Close" buttons

### **Performance & Quality Of Life Improvements**
- **Smart Field Organization**: Fields are now automatically reordered by type (core fields → surface fields → attribute fields)
- **Enhanced Data Type Detection**: The plugin now automatically detects Boolean, Integer, Double and String data types instead of treating all attributes as strings
- **Improved Layer Sorting**: LoD layers are now sorted by value in descending order for better organization
- **File Caching System**: Stores up to 10 recently processed files in memory to improve performance when switching between files
- **Enhanced User Experience**: Improved GUI with better file management controls and smoother workflow

### **Bug Fixes**
- Fixed an issue where the "Style layers according to semantic surfaces" checkbox was always registered as checked internally regardless of its actual checked/unchecked status
- Fixed an issue where opening multiple instances of the plugin would result in a crash
- Fixed issue where input files with different CRS were all processed using the CRS of the first file in the list widget

## Installation
Open the Command Prompt (CMD) and navigate to the directory where your QGIS plugins are stored. For example:
```
C:\Users\<user>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins
```
If you're unable to find this directory:
- Launch QGIS 3.
- Go to `Settings`->`User Profiles`->`Open Active Profile Folder`
- This will open the folder containing your plugins.

Once you're in the correct directory, run the following Git command to install the plugin:
```
git clone -b main https://github.com/FLeroux23/CityJSON-loader
```
To update the plugin later, use the following command:
```
git pull origin main
```
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

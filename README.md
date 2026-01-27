# CityJSON Loader for QGIS

This is a Python plugin for QGIS 3 which adds support for loading [CityJSON](http://www.cityjson.org) datasets in QGIS.


## Installation

"Stable" releases are available through the official QGIS plugins repository.

* In QGIS 3 select `Plugins`->`Manage and Install Plugins...`
* In the `All` panel select the `CityJSON Loader` plugin from the list.


## Usage

### File loading
After the installation, there must be a new submenu under the `Vector` menu. Select `CityJSON Loader`->`Load CityJSON...` in order to open the CityJSON dialog window. You can select a dataset and add it from there.

You may enable the `Split layers according to object type` option in order to load different object types as different layers in QGIS.

### 3D view 
CityJSON Loader automatically enables 3D renderer in QGIS versions 3.2 onwards.
However, if you are using QGIS 3.0 you have to enable it manually.
This can be done as follows:
* Right-click on the layer and select `Properties...`
* Select the `3D View` panel and check the `Enable 3D renderer` option.
* In QGIS 3 menu select `View`->`New 3D Map View` in order to see the 3D geometry.


## Development

** For more detailed guidelines on contributing, please see the [CONTRIBUTING.md](CONTRIBUTING.md) file.** 



The user interfaces for the loader were developed with QT Designer.

After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect

You may use `make` to assist you while developing.

The following rules can be useful:

* `make deploy`: will automatically copy the required files to your QGIS plugins' folder. **BEWARE:** *it only works out-of-the-box for macOS. For other operating systems you might have to change the `QGISDIR` variable in `Makefile`.*

* `make package VERSION=GIT_REF`: (where *GIT_REF* is a branch, tag or any other git ref) will make a zip package to be installed manually from QGIS or uploaded to the QGIS plugins' repository.

### Code style and pre-commit hooks

This project uses [ruff](https://docs.astral.sh/ruff/) for linting/formatting and [pre-commit](https://pre-commit.com/) to automate code quality checks.

To set up code style checks and pre-commit hooks after cloning the repository:

1. Install ruff and pre-commit (ideally in a virtual environment):
   ```sh
   pip install ruff pre-commit
   ```
2. Install the pre-commit hooks:
   ```sh
   pre-commit install
   ```
3. (Optional) Run all hooks on all files to check/fix issues:
   ```sh
   pre-commit run --all-files
   ```

Now, every time you commit, pre-commit will automatically run ruff and other checks to help keep the codebase clean and consistent.

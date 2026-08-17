# CityJSON Loader for QGIS

This is a Python plugin for QGIS 3 which adds support for loading [CityJSON](http://www.cityjson.org) datasets in QGIS.

**Tested and supported on QGIS 3.40.* (LTR) and QGIS 3.44.* (future LTR/stable). Compatibility with earlier versions is not guaranteed.**


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

### Code style and pre-commit hooks

This project uses [ruff](https://docs.astral.sh/ruff/) for linting/formatting and [pre-commit](https://pre-commit.com/) to automate code quality checks.

To set up code style checks and pre-commit hooks after cloning the repository:

1. Install the development tools (ruff, pre-commit and mypy) — ideally in a virtual environment:
   ```sh
   pip install -r requirements-dev.txt
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


### Type checking

The codebase is annotated with type hints and checked with [mypy](https://mypy.readthedocs.io/). To run it locally:

1. Run the type checker on the plugin source:
   ```sh
   mypy
   ```

Configuration lives in `pyproject.toml` (`[tool.mypy]`), scoped to `cityjson_loader.py`, `core/`, `gui/` and `processing/`. QGIS has no type stubs, so missing imports are ignored; the goal is to catch internal type errors, not to fully type the QGIS API.


### Testing with Docker

To run the test suite in a reproducible environment, you can use Docker. This is especially useful for Mac M1/M2 (Apple Silicon) users, who should specify the amd64 platform for compatibility with QGIS dependencies.

**Build the Docker image:**
For most other systems:
```sh
make docker-build
```

For Mac M1/M2 (Apple Silicon):
```sh
DOCKER_DEFAULT_PLATFORM=linux/amd64 make docker-build
```

**Run the tests in the container:**
```sh
docker run --rm cityjson-qgis-plugin-test
```

Or, using the Makefile for convenience:
```sh
make test-docker
```

For Mac M1/M2 (Apple Silicon):
```sh
DOCKER_DEFAULT_PLATFORM=linux/amd64 make test-docker
```


This will build the image if needed and run the test suite inside the container, matching the CI environment.

### Deployment
The user interfaces for the loader were developed with QT Designer.

After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect

You may use `make` to assist you while developing.

The following rules can be useful:

* `make deploy`: will automatically copy the required files to your QGIS plugins' folder. **BEWARE:** *it only works out-of-the-box for macOS. For other operating systems you might have to change the `QGISDIR` variable in `Makefile`.*

* `make package VERSION=GIT_REF`: (where *GIT_REF* is a branch, tag or any other git ref) will make a zip package to be installed manually from QGIS or uploaded to the QGIS plugins' repository.

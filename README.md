# CityJSON Loader for QGIS

This is a Python plugin for QGIS which adds support for loading [CityJSON](http://www.cityjson.org) datasets in QGIS. It supports standard CityJSON and CityJSONSeq files.

**Tested and supported on QGIS 3.40 (LTR), 3.44 (LTR) and QGIS 4.x (Qt6). Compatibility with earlier versions is not guaranteed.**


## Installation

"Stable" releases are available through the official QGIS plugins repository.

* In QGIS select `Plugins`->`Manage and Install Plugins...`
* In the `All` panel select the `CityJSON Loader` plugin from the list.


## Usage

### File loading
After the installation, there must be a new submenu under the `Vector` menu. Select `CityJSON Loader`->`Load CityJSON...` in order to open the CityJSON dialog window. You can select a dataset and add it from there.

You may enable the `Split layers according to object type` option in order to load different object types as different layers in QGIS.

### 3D view 
CityJSON Loader automatically enables the 3D renderer. To see the 3D geometry, select `View` -> `New 3D Map View` in the QGIS menu.

If the 3D renderer is not enabled automatically:
* Right-click on the layer and select `Properties...`
* Select the `3D View` panel and check the `Enable 3D renderer` option.


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


### Testing

#### Running tests locally

With QGIS installed, create a local `.env` from the example and set
`QGIS_PYTHON` to your QGIS Python interpreter:

```sh
cp example.env .env
# then edit .env if your QGIS path differs
make test
```

#### Running tests against specific QGIS versions (Docker)

The CI and the `Makefile` provide targets for each supported QGIS version
(3.40, 3.44, 4.0, 4.2). Each target builds a Docker image and runs the test
suite inside it:

```sh
make test-340
make test-344
make test-40
make test-42
```

On Mac M1/M2 (Apple Silicon), prefix with the amd64 platform:

```sh
DOCKER_DEFAULT_PLATFORM=linux/amd64 make test-42
```

#### Coverage

Tests are run with coverage. A terminal report is printed, and an HTML report
is written to `htmlcov/index.html`. Coverage is configured in
`pyproject.toml` (`[tool.coverage.*]`).

### Loading the plugin locally into QGIS

To try the plugin in your local QGIS without installing from the plugin
repository, deploy the source directly to your QGIS plugins folder:

```sh
make deploy
```

This copies the required files to
`$(HOME)/$(QGISDIR)/python/plugins/CityJSON-loader/`. On macOS this works
out-of-the-box; on Linux/Windows you may need to adjust the `QGISDIR` variable
in the `Makefile` (or in `.env`) to point at your QGIS profile:

- Linux: `~/.local/share/QGIS/QGIS3/profiles/default`
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default`
- Windows: `%APPDATA%\QGIS\QGIS3\profiles\default`

Then restart QGIS and enable the plugin under `Plugins` -> `Manage and Install
Plugins...`.

### Deployment

The user interfaces for the loader were developed with QT Designer.

After `setupUi` you can access any designer object by doing
`self.<objectname>`, and you can use autoconnect slots (see
<https://doc.qt.io/qt-6/designer-using-a-ui-file.html>).

The following `make` rules are useful:

- `make deploy`: copy the required files to your local QGIS plugins folder.
- `make package VERSION=GIT_REF`: build a zip package from a branch, tag or
  commit, to be installed manually or uploaded to the QGIS plugin repository.

For the full release process, see [RELEASING.md](RELEASING.md).

#################################################
# Edit the following to match your sources lists
#################################################

PLUGINNAME = CityJSON-loader

PY_FILES = \
	__init__.py \
	cityjson_loader.py gui/cityjson_loader_dialog.py \
	core/__init__.py core/layers.py core/geometry.py core/styling.py \
	core/settings.py core/helpers/treemodel.py core/loading.py \
	processing/__init__.py processing/cityjson_load_algorithm.py \
	processing/provider.py core/subset.py core/utils.py

UI_FILES = gui/cityjson_loader_dialog_base.ui

EXTRAS = metadata.txt cityjson_logo.svg Changelog.md

EXTRA_DIRS = 

COMPILED_RESOURCE_FILES = resources.py

# QGISDIR points to the location where your plugin should be installed.
# This varies by platform, relative to your HOME directory:
#	* Linux:
#	  .local/share/QGIS/QGIS3/profiles/default/python/plugins/
#	* Mac OS X:
#	  Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins
#	* Windows:
#	  AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins'

# Load variables from .env if it exists
ifneq (,$(wildcard .env))
	include .env
	export
endif

# Detect OS for Docker and QGISDIR logic
ifeq ($(OS),Windows_NT)     # is Windows_NT on XP, 2000, 7, Vista, 10...
	detected_OS := Windows
else
	detected_OS := $(shell sh -c 'uname 2>/dev/null || echo Unknown')
endif

# Detect platform for Docker (set DOCKER_DEFAULT_PLATFORM on Mac)
ifeq ($(detected_OS),Darwin)
    DOCKER_PLATFORM_PREFIX = DOCKER_DEFAULT_PLATFORM=linux/amd64
else
    DOCKER_PLATFORM_PREFIX =
endif


# If QGISDIR is not set from .env, detect from system
ifndef QGISDIR
ifeq ($(detected_OS),Windows)
	QGISDIR := AppData\Roaming\QGIS\QGIS3\profiles\default
endif
ifeq ($(detected_OS),Darwin)
	QGISDIR := Library/Application Support/QGIS/QGIS3/profiles/default
endif
ifeq ($(detected_OS),Linux)
	QGISDIR := .local/share/QGIS/QGIS3/profiles/default
endif
endif

#################################################
# Normally you would not need to edit below here
#################################################

PLUGIN_UPLOAD = scripts/plugin_upload.py

RESOURCE_SRC=$(shell grep '^ *<file' resources.qrc | sed 's@</file>@@g;s/.*>//g' | tr '\n' ' ')

default: compile

compile: $(COMPILED_RESOURCE_FILES)

%.py : %.qrc $(RESOURCES_SRC)
	pyrcc5 -o $*.py  $<


deploy: compile
# The deploy  target only works on unix like operating system where
# the Python plugin directory is located at:
# $(HOME)/$(QGISDIR)/python/plugins
	@echo
	@echo "------------------------------------------"
	@echo "Deploying plugin to your QGIS3 directory:"
	@echo " $(HOME)/$(QGISDIR)/python/plugins/"
	@echo "------------------------------------------"
	@mkdir -p "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	@rsync -R $(PY_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	@rsync -R $(UI_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	@cp -f $(COMPILED_RESOURCE_FILES) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	@cp -f $(EXTRAS) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"

# Copy extra directories if any
	$(foreach EXTRA_DIR,$(EXTRA_DIRS), cp -R $(EXTRA_DIR) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"/;)
	@echo "------------------------------------------"
	@echo " Deployment Successful!"
	@echo "------------------------------------------"


# The dclean target removes compiled python files from plugin directory
# also deletes any .git entry
dclean:
	@echo
	@echo "-----------------------------------"
	@echo "Removing any compiled python files."
	@echo "-----------------------------------"
	@find "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)" -iname "*.pyc" -delete
	@find "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)" -iname ".git" -prune -exec rm -Rf {} \;

derase:
	@echo
	@echo "-------------------------"
	@echo "Removing deployed plugin."
	@echo "-------------------------"
	@rm -Rf $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)

zip: deploy dclean
# The zip target deploys the plugin and creates a zip file with the deployed
# content. You can then upload the zip file on http://plugins.qgis.org
	@echo
	@echo "---------------------------"
	@echo "Creating plugin zip bundle."
	@echo "---------------------------"
	@rm -f $(PLUGINNAME).zip
	@cp  LICENSE "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/LICENSE"
	@cd "$(HOME)/$(QGISDIR)/python/plugins"; zip -9r $(CURDIR)/$(PLUGINNAME).zip $(PLUGINNAME) -x ".*" "__pycache__/*" "**/__pycache__/*"

package: compile
# Creates a zip package of the plugin named $(PLUGINNAME).zip.
# This requires use of git (your plugin development directory must be a
# git repository).
# To use, pass a valid commit or tag as follows:
#   make package VERSION=v1
	@echo
	@echo "------------------------------------"
	@echo "Exporting plugin to zip package.	"
	@echo "------------------------------------"
	@rm -f $(PLUGINNAME).zip
	@git archive --prefix=$(PLUGINNAME)/ -o $(PLUGINNAME).zip $(VERSION)
	@echo "Created package: $(PLUGINNAME).zip"

upload: zip
	@echo
	@echo "-------------------------------------"
	@echo "Uploading plugin to QGIS Plugin repo."
	@echo "-------------------------------------"
	@python3 ./$(PLUGIN_UPLOAD) $(PLUGINNAME).zip


docker-build-340:
	$(DOCKER_PLATFORM_PREFIX) docker build  -f docker/Dockerfile.qgis-3.40 -t cityjson-qgis-plugin-test-340 .

test-340:
	@if [ -z "$$(docker images -q cityjson-qgis-plugin-test-340)" ]; then \
		echo "Docker image not found. Building..."; \
		$(MAKE) docker-build-340; \
	fi
	$(DOCKER_PLATFORM_PREFIX) docker run --rm cityjson-qgis-plugin-test-340

docker-build-344:
	$(DOCKER_PLATFORM_PREFIX) docker build  -f docker/Dockerfile.qgis-3.44 -t cityjson-qgis-plugin-test-344 .

test-344:
	@if [ -z "$$(docker images -q cityjson-qgis-plugin-test-344)" ]; then \
		echo "Docker image not found. Building..."; \
		$(MAKE) docker-build-344; \
	fi
	$(DOCKER_PLATFORM_PREFIX) docker run --rm cityjson-qgis-plugin-test-344

docker-build-40:
	$(DOCKER_PLATFORM_PREFIX) docker build  -f docker/Dockerfile.qgis-4.0 -t cityjson-qgis-plugin-test-40 .

test-40:
	@if [ -z "$$(docker images -q cityjson-qgis-plugin-test-40)" ]; then \
		echo "Docker image not found. Building..."; \
		$(MAKE) docker-build-40; \
	fi
	$(DOCKER_PLATFORM_PREFIX) docker run --rm cityjson-qgis-plugin-test-40

test: compile 

	@echo "------------------------------------------"
	@echo " Running tests"
	@echo "------------------------------------------"
	export QGIS_DEBUG=0; \
	export QGIS_LOG_FILE=/dev/null; \
	$(QGIS_PYTHON) -m pytest tests  -v -s --cov=core/ --cov=processing/ --cov=gui/
	@echo "------------------------------------------"
	@echo "Test suite completed"
	@echo "------------------------------------------"

format: compile
	uv tool run --with ruff==0.8.4 ruff format .
	uv tool run --with ruff==0.8.4 ruff check . --fix
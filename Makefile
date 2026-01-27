#/***************************************************************************
# CityJsonLoader
#
# This plugin allows for CityJSON files to be loaded in QGIS
#							 -------------------
#		begin				: 2018-06-08
#		git sha				: $Format:%H$
#		copyright			: (C) 2018 by 3D Geoinformation
#		email				: s.vitalis@tudelft.nl
# ***************************************************************************/
#
#/***************************************************************************
# *																		 *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or	 *
# *   (at your option) any later version.								   *
# *																		 *
# ***************************************************************************/

#################################################
# Edit the following to match your sources lists
#################################################


#Add iso code for any locales you want to support here (space separated)
# default is no locales
# LOCALES = af
LOCALES =

# If locales are enabled, set the name of the lrelease binary on your system. If
# you have trouble compiling the translations, you may have to specify the full path to
# lrelease
#LRELEASE = lrelease
#LRELEASE = lrelease-qt4


# translation
SOURCES = \
	__init__.py \
	cityjson_loader.py gui/cityjson_loader_dialog.py \
	core/layers.py core/geometry.py core/styling.py core/settings.py \
	core/subset.py core/utils.py

PLUGINNAME = CityJSON-loader

PY_FILES = \
	__init__.py \
	cityjson_loader.py gui/cityjson_loader_dialog.py \
	core/__init__.py core/layers.py core/geometry.py core/styling.py \
	core/settings.py core/helpers/treemodel.py core/loading.py \
	processing/__init__.py processing/cityjson_load_algorithm.py \
	processing/provider.py core/subset.py core/utils.py

UI_FILES = gui/cityjson_loader_dialog_base.ui

EXTRAS = metadata.txt icon.png cityjson_logo_big.png cityjson_logo.svg Changelog.md

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

# If QGISDIR is not set from .env, detect from system
ifndef QGISDIR
ifeq ($(OS),Windows_NT)     # is Windows_NT on XP, 2000, 7, Vista, 10...
	detected_OS := Windows
else
	detected_OS := $(shell sh -c 'uname 2>/dev/null || echo Unknown')
endif

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

HELP = help/build/html

PLUGIN_UPLOAD = $(c)/plugin_upload.py

RESOURCE_SRC=$(shell grep '^ *<file' resources.qrc | sed 's@</file>@@g;s/.*>//g' | tr '\n' ' ')

default: compile

compile: $(COMPILED_RESOURCE_FILES)

%.py : %.qrc $(RESOURCES_SRC)
	pyrcc5 -o $*.py  $<

%.qm : %.ts
	$(LRELEASE) $<

test: compile transcompile

	@echo "------------------------------------------"
	@echo " Running tests"
	@echo "------------------------------------------"
	export QGIS_DEBUG=0; \
	export QGIS_LOG_FILE=/dev/null; \
	$(QGIS_PYTHON) -m pytest tests  -v -s --cov=core/ --cov=gui
	@echo "------------------------------------------"
	@echo "Test suite completed"
	@echo "------------------------------------------"

deploy: compile doc transcompile
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
	@cp -fr i18n "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)"
	@cp -fr $(HELP) "$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)/help"
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
# Create a zip package of the plugin named $(PLUGINNAME).zip.
# This requires use of git (your plugin development directory must be a
# git repository).
# To use, pass a valid commit or tag as follows:
#   make package VERSION=Version_0.3.2
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
	@$(PLUGIN_UPLOAD) $(PLUGINNAME).zip

transup:
	@echo
	@echo "------------------------------------------------"
	@echo "Updating translation files with any new strings."
	@echo "------------------------------------------------"
	@chmod +x scripts/update-strings.sh
	@scripts/update-strings.sh $(LOCALES)

transcompile:
	@echo
	@echo "----------------------------------------"
	@echo "Compiled translation files to .qm files."
	@echo "----------------------------------------"
	@chmod +x scripts/compile-strings.sh
	@scripts/compile-strings.sh $(LRELEASE) $(LOCALES)

transclean:
	@echo
	@echo "------------------------------------"
	@echo "Removing compiled translation files."
	@echo "------------------------------------"
	@rm -f i18n/*.qm

clean:
	@echo
	@echo "------------------------------------"
	@echo "Removing uic and rcc generated files"
	@echo "------------------------------------"
	@rm $(COMPILED_UI_FILES) $(COMPILED_RESOURCE_FILES)

doc:
	@echo
	@echo "------------------------------------"
	@echo "Building documentation using sphinx."
	@echo "------------------------------------"
	@cd help; make html

format:
	@echo
	@echo "------------------------------------"
	@echo "Formatting code using ruff"
	@echo "------------------------------------"
	@ruff format core/ tests/ processing/ gui/  cityjson_loader.py resources.py __init__.py plugin_upload.py

check:
	@echo
	@echo "------------------------------------"
	@echo "Check issues with ruff"
	@echo "------------------------------------"
	@ruff check core/ tests/ processing/ gui/  cityjson_loader.py resources.py __init__.py plugin_upload.py || true

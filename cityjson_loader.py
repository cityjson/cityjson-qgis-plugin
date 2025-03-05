# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CityJsonLoader
                                 A QGIS plugin
 This plugin allows for CityJSON files to be loaded in QGIS
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2018-06-08
        git sha              : $Format:%H$
        copyright            : (C) 2018 by 3D Geoinformation
        email                : s.vitalis@tudelft.nl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os.path
import json

from PyQt5.QtCore import (QCoreApplication, QSettings, QTranslator, QVariant, Qt,
                          qVersion)
from PyQt5.QtGui import QColor, QIcon, QKeySequence
from PyQt5.QtWidgets import QAction, QDialogButtonBox, QFileDialog, QMessageBox, QShortcut
from qgis.core import QgsApplication, QgsCoordinateReferenceSystem
from qgis.gui import QgsProjectionSelectionDialog

from .core.geometry import GeometryReader, VerticesCache
from .core.helpers.treemodel import (MetadataElement, MetadataModel,
                                     MetadataNode)
from .core.layers import (AttributeFieldsDecorator, BaseFieldsBuilder,
                          BaseNamingIterator, DynamicLayerManager, ParentFeatureDecorator,
                          LodFeatureDecorator, LodFieldsDecorator,
                          LodNamingDecorator, SemanticSurfaceFeatureDecorator,
                          SemanticSurfaceFieldsDecorator, SimpleFeatureBuilder,
                          TypeNamingIterator)
from .core.loading import CityJSONLoader, load_cityjson_model, get_model_epsg
from .core.styling import (Copy2dStyling, NullStyling, SemanticSurfacesStyling,
                           is_3d_styling_available,
                           is_rule_based_3d_styling_available)
# Import the code for the dialog
from .gui.cityjson_loader_dialog import CityJsonLoaderDialog
from .resources import *
from .processing.provider import Provider


class CityJsonLoader:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CityJsonLoader_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = CityJsonLoaderDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&CityJSON Loader')
        # # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'CityJsonLoader')
        self.toolbar.setObjectName(u'CityJsonLoader')

        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self.dlg)
        self.delete_shortcut.activated.connect(self.remove_cityjson_files)

        self.dlg.browseFilesButton.clicked.connect(self.select_cityjson_files)
        self.dlg.browseDirectoryButton.clicked.connect(self.select_cityjson_files_directory)
        self.dlg.listWidget.itemSelectionChanged.connect(self.update_file_list)
        self.dlg.removeFilesButton.clicked.connect(self.remove_cityjson_files)

        self.dlg.changeCrsPushButton.clicked.connect(self.select_crs)
        self.dlg.semanticsLoadingCheckBox.stateChanged.connect(self.semantics_loading_changed)

        self.provider = None
    
    def initProcessing(self):
        """Initialises the processing provider"""
        self.provider = Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def select_cityjson_files(self):
        """Shows a dialog to select CityJSON file(s)"""
        filenames, _ = QFileDialog.getOpenFileNames(self.dlg, "Select CityJSON File(s)", "", "*.json")

        if filenames:
            for filename in filenames:
                existing_items = self.dlg.listWidget.findItems(filename, QtCore.Qt.MatchExactly)

                if not existing_items:
                    self.dlg.listWidget.addItem(filename)

            self.dlg.listWidget.setCurrentRow(0)

    def select_cityjson_files_directory(self):
        """Shows a dialog to select CityJSON file(s)"""
        directory = QFileDialog.getExistingDirectory(self.dlg, "Select Directory", "", QFileDialog.ShowDirsOnly)

        if not directory:
            self.dlg.listWidget.clear()
        else:
            filenames = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.json')]

            if filenames:
                self.dlg.listWidget.clear()
                self.dlg.listWidget.addItems(filenames)
                self.dlg.listWidget.setCurrentRow(0)
            else:

                self.dlg.listWidget.clear()

    def remove_cityjson_files(self):
        """Removes CityJSON file(s) from the list"""
        selected_items = self.dlg.listWidget.selectedItems()
        if selected_items:
            for item in selected_items:
                row = self.dlg.listWidget.row(item)
                self.dlg.listWidget.takeItem(row)

            if self.dlg.listWidget.count() > 0:
                self.dlg.listWidget.setCurrentRow(0)
                self.update_file_list()
            else:
                self.clear_file_information()

    def update_file_list(self):
        """Update metadata fields according to the file selected"""
        selected_item = self.dlg.listWidget.currentItem()
        if selected_item:
            self.update_file_information(selected_item.text())
        else:
            self.clear_file_information()

    def select_crs(self):
        """Shows a dialog to select a new CRS for the model"""
        crs_dialog = QgsProjectionSelectionDialog()
        crs_dialog.setShowNoProjection(True)
        if self.dlg.crsLineEdit.text() != "None":
            old_crs = QgsCoordinateReferenceSystem("EPSG:{}".format(self.dlg.crsLineEdit.text()))
            crs_dialog.setCrs(old_crs)
        crs_dialog.exec()
        if crs_dialog.crs().postgisSrid() == 0:
            self.dlg.crsLineEdit.setText("None")
        else:
            self.dlg.crsLineEdit.setText("{}".format(crs_dialog.crs().postgisSrid()))

    def semantics_loading_changed(self):
        """Update the GUI according to the new state of semantic surfaces loading"""
        if is_rule_based_3d_styling_available():
            self.dlg.semanticSurfacesStylingCheckBox.setEnabled(self.dlg.semanticsLoadingCheckBox.isChecked())

    def clear_file_information(self):
        """Clear all fields related to file information"""
        line_edits = [self.dlg.cityjsonVersionLineEdit,
                      self.dlg.compressedLineEdit,
                      self.dlg.crsLineEdit]
        for line_edit in line_edits:
            line_edit.setText("")
        self.dlg.metadataTreeView.setModel(None)
        self.dlg.changeCrsPushButton.setEnabled(False)
        self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(False)

    def update_file_information(self, filename):
        """Update metadata fields according to the file provided"""
        try:
            fstream = open(filename, encoding='utf-8-sig')
            model = json.load(fstream)
            fstream.close()

            lods = set()
            for _, city_object in model['CityObjects'].items():
                if 'geometry' in city_object:
                    for geom in city_object['geometry']:
                        if 'lod' in geom:
                            lods.add(geom['lod'])

            self.dlg.cityjsonVersionLineEdit.setText(model["version"])
            self.dlg.compressedLineEdit.setText("Yes" if "transform" in model else "No")

            if "metadata" in model:
                self.dlg.crsLineEdit.setText(get_model_epsg(model))
                metadata = model["metadata"]

                if "+metadata-extended" in model:
                    metadata = {**metadata, **model["+metadata-extended"]}
            else:
                metadata = {"Medata missing": "There is no metadata in this file"}

            self.dlg.changeCrsPushButton.setEnabled(True)
            self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
            self.dlg.removeFilesButton.setEnabled(True)

            model = MetadataModel(metadata, self.dlg.metadataTreeView)
            self.dlg.metadataTreeView.setModel(model)
            self.dlg.metadataTreeView.setColumnWidth(0, model.getKeyColumnWidth())

            self.dlg.inheritParentAttributesCheckBox.setEnabled(True)
            self.dlg.splitByTypeCheckBox.setEnabled(True)
            self.dlg.semanticsLoadingCheckBox.setEnabled(True)

            self.dlg.loDLoadingComboBox.setEnabled(True)
            self.dlg.loDSelectionComboBox.clear()
            self.dlg.loDSelectionComboBox.addItem("All")

            if lods:
                self.dlg.loDSelectionComboBox.addItems(sorted(list(lods)))

            self.dlg.loDSelectionComboBox.setEnabled(len(lods) > 0)

        except Exception as exp:
            self.dlg.changeCrsPushButton.setEnabled(False)
            self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
            raise exp

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CityJsonLoader', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/cityjson_loader/cityjson_logo.svg'
        self.add_action(
            icon_path,
            text=self.tr(u'Load CityJSON...'),
            callback=self.run,
            parent=self.iface.mainWindow())

        self.initProcessing()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI"""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&CityJSON Loader'),
                action)
            self.iface.removeToolBarIcon(action)

        del self.toolbar

        QgsApplication.processingRegistry().removeProvider(self.provider)

    def run(self):
        """Run method that performs all the real work"""
        self.dlg.show()
        self.dlg.changeCrsPushButton.setEnabled(False)
        self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.dlg.semanticSurfacesStylingCheckBox.setEnabled(False)

        result = self.dlg.exec_()

        if result:
            filepaths = [self.dlg.listWidget.item(i).text() for i in range(self.dlg.listWidget.count())]
            for filepath in filepaths:
                skipped_geometries = self.load_cityjson(filepath)
                msg = QMessageBox()

                if skipped_geometries > 0:
                    msg.setIcon(QMessageBox.Warning)
                    msg.setText("CityJSON loaded with issues.")
                    msg.setInformativeText("Some geometries were skipped.")
                    msg.setDetailedText("{} geometries could not be loaded (p.s. GeometryInstances are not supported yet).".format(skipped_geometries))

            msg.setIcon(QMessageBox.Information)
            msg.setText("CityJSON loaded successfully.")
            msg.setWindowTitle("CityJSON loading finished")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

    def load_cityjson(self, filepath):
        """Loads the given CityJSON"""
        citymodel = load_cityjson_model(filepath)

        lod_as = 'NONE'
        if self.dlg.loDLoadingComboBox.currentIndex() == 1:
            lod_as = 'ATTRIBUTES'
        elif self.dlg.loDLoadingComboBox.currentIndex() == 2:
            lod_as = 'LAYERS'

        selected_lod = self.dlg.loDSelectionComboBox.currentText()

        if selected_lod == "All":
            lod = 'All'
        else:
            lod = selected_lod

        loader = CityJSONLoader(filepath,
                                citymodel,
                                epsg=self.dlg.crsLineEdit.text(),
                                keep_parent_attributes=self.dlg.inheritParentAttributesCheckBox.isChecked(),
                                divide_by_object=self.dlg.splitByTypeCheckBox.isChecked(),
                                lod_as=lod_as,
                                lod=lod,
                                load_semantic_surfaces=self.dlg.semanticsLoadingCheckBox.isChecked(),
                                style_semantic_surfaces=self.dlg.semanticsLoadingCheckBox.isChecked()
                               )

        skipped_geometries = loader.load()

        return skipped_geometries

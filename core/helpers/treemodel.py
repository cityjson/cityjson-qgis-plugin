from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, Qt, QSize, QRect, QPoint
from qgis.PyQt.QtGui import QFontMetrics, QFont

metadata_realnames = {
    "citymodelIdentifier": "City Model Identifier",
    "datasetTitle": "Dataset Title",
    "datasetReferenceDate": "Dataset Reference Date",
    "geographicLocation": "Geographic Location",
    "datasetLanguage": "Dataset Language",
    "datasetCharacterSet": "Dataset Character Set",
    "datasetTopicCategory": "Dataset Topic Category",
    "distributionFormatVersion": "Distribution Format Version",
    "referenceSystem": "Reference System",
    "geographicalExtent": "Geographical Extent",
    "spatialRepresentationType": "Spatial Representation Type",
    "onlineResource": "Online Resource",
    "fileIdentifier": "File Identifier",
    "datasetPointOfContact": "Dataset Point of Contact",
    "contactName": "Contact Name",
    "phone": "Phone",
    "address": "Address",
    "emailAddress": "Email Address",
    "contactType": "Contact Type",
    "role": "Role",
    "organization": "Organization",
    "website": "Website",
    "metadataStandard": "Metadata Standard",
    "metadataStandardVersion": "Metadata Standard Version",
    "metadataLanguage": "Metadata Language",
    "metadataCharacterSet": "Metadata Character Set",
    "metadataDateStamp": "Metadata Date Stamp",
    "metadataPointOfContact": "Metadata Point of Contact",
    "lineage": "Lineage",
    "statement": "Statement",
    "scope": "Scope",
    "additionalDocumentation": "Additional Documentation",
    "featureIDs": "Feature IDs",
    "source": "Source",
    "description": "Description",
    "sourceSpatialResolution": "Source Spatial Resolution",
    "sourceReferenceSystem": "Source Reference System",
    "sourceCitation": "Source Citation",
    "sourceMetadata": "Source Metadata",
    "processor": "Processor",
    "processStep": "Process Step",
    "rationale": "Rationale",
    "reference": "Reference",
    "stepDateTime": "Step Date and Time",
    "thematicModels": "Thematic Models",
    "geographicalExtent": "Geographical Extent",
    "temporalExtent": "Temporal Extent",
    "startDate": "Start Date",
    "endDate": "End Date",
    "abstract": "Abstract",
    "specificUsage": "Specific Usage",
    "keywords": "Keywords",
    "constraints": "Constraints",
    "legalConstraints": "Legal Constraints",
    "securityConstraints": "Security Constraints",
    "userNote": "User Note",
    "textures": "Textures",
    "materials": "Materials",
    "extensions": "Extensions",
    "transform": "Transform",
    "geometry-templates": "Geometry Templates",
    "presentLoDs": "Present LoDs",
    "cityfeatureMetadata": "City Feature Metadata",
    "uniqueFeatureCount": "Unique Feature Count",
    "aggregateFeatureCount": "Aggregate Feature Count",
}

class TreeNode(object):
    def __init__(self, parent, row):
        self.parent = parent
        self.row = row
        self.subnodes = self._getChildren()

    def _getChildren(self):
        raise NotImplementedError()

class TreeModel(QAbstractItemModel):
    def __init__(self):
        QAbstractItemModel.__init__(self)
        self.rootNodes = self._getRootNodes()

    def _getRootNodes(self):
        raise NotImplementedError()

    def index(self, row, column, parent):
        if not parent.isValid():
            return self.createIndex(row, column, self.rootNodes[row])
        parentNode = parent.internalPointer()
        return self.createIndex(row, column, parentNode.subnodes[row])

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        if node.parent is None:
            return QModelIndex()
        else:
            return self.createIndex(node.parent.row, 0, node.parent)

    def reset(self):
        self.rootNodes = self._getRootNodes()
        QAbstractItemModel.reset(self)

    def rowCount(self, parent):
        if not parent.isValid():
            return len(self.rootNodes)
        node = parent.internalPointer()
        return len(node.subnodes)

class MetadataElement(object): # your internal structure
    def __init__(self, value_pair):
        self.key = value_pair[0]
        if isinstance(value_pair[1], dict):
            self.subelements = value_pair[1]
            self.value = ""
        elif isinstance(value_pair[1], list):
            if value_pair[0] == "geographicalExtent":
                self.subelements = {
                    "min x":value_pair[1][0],
                    "min y":value_pair[1][1],
                    "min z":value_pair[1][2],
                    "max x":value_pair[1][3],
                    "max y":value_pair[1][4],
                    "max z":value_pair[1][5]}
            elif value_pair[0] in ["keywords", "thematicModels"]:
                self.subelements = {v: "" for v in value_pair[1]}
            elif value_pair[0] in metadata_realnames:
                self.subelements = {metadata_realnames[value_pair[0]] + " " + str(i): v for i, v in enumerate(value_pair[1],start = 1)}
            else:
                self.subelements = {i: v for i, v in enumerate(value_pair[1],start = 1)}
            self.value = ""
        else:
            self.subelements = {}
            self.value = value_pair[1]

class MetadataNode(TreeNode):
    def __init__(self, ref, parent, row):
        self.ref = ref
        TreeNode.__init__(self, parent, row)

    def _getChildren(self):
        return [MetadataNode(MetadataElement(elem), self, index)
            for index, elem in enumerate(self.ref.subelements.items())]

class MetadataModel(TreeModel):
    def __init__(self, rootElements, treeview):
        self.rootElements = rootElements
        self.treeview = treeview
        TreeModel.__init__(self)
    
    def getKeyColumnWidth(self):
        width = 100
        padding = 30
        for key, _ in self.rootElements.items():
            metrics = QFontMetrics(self.treeview.font())
            outRect = metrics.boundingRect(get_real_key(key))
            if width < outRect.width() + padding:
                width = outRect.width() + padding
        
        return width

    def _getRootNodes(self):
        return [MetadataNode(MetadataElement(elem), None, index)
            for index, elem in enumerate(self.rootElements.items())]

    def columnCount(self, parent):
        return 2

    def data(self, index, role):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == Qt.DisplayRole and index.column() == 0:
            return get_real_key(node.ref.key)
        elif role == Qt.DisplayRole and index.column() == 1:
            return node.ref.value
        elif role == Qt.SizeHintRole and index.column() == 1:
            baseSize = QSize(self.treeview.columnWidth(index.column()), 16)

            metrics = QFontMetrics(self.treeview.font())
            outRect = metrics.boundingRect(QRect(QPoint(0, 0), baseSize), Qt.AlignLeft + Qt.TextWordWrap, str(self.data(index, Qt.DisplayRole)))
            baseSize.setHeight(outRect.height())

            return baseSize

        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return 'Property'
            elif section == 1:
                return 'Value'
        return None

def get_real_key(key_name):
    if key_name in metadata_realnames:
        return metadata_realnames[key_name]
    else:
        return key_name
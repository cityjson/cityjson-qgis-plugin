from qgis.PyQt.QtCore import QAbstractItemModel, QModelIndex, Qt

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
            self.subelements = {i: v for i, v in enumerate(value_pair[1])}
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
    def __init__(self, rootElements):
        self.rootElements = rootElements
        TreeModel.__init__(self)

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
            return node.ref.key
        elif role == Qt.DisplayRole and index.column() == 1:
            return node.ref.value
        
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return 'Property'
            elif section == 1:
                return 'Value'
        return None
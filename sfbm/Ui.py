import os
import sfbm.Global as G
from PyQt4 import QtCore, QtGui, uic
QtCore.Signal = QtCore.pyqtSignal
QtCore.Slot = QtCore.pyqtSlot

_ROOT = os.path.abspath(os.path.dirname(__file__))


def get_data(path):
    return os.path.join(_ROOT, 'data', path)


class PrefsDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        ui_class, _ = uic.loadUiType(get_data("prefs.ui"))
        self.ui = ui_class()
        self.ui.setupUi(self)
        self.checkboxes = {"ShowHidden": self.ui.showHiddenBox,
                           "IncludePrevious": self.ui.includePreviousBox,
                           "DirsFirst": self.ui.dirsFirstBox}
        self.init_checkboxes(G.default_options)
        self.ui.okButton.clicked.connect(self.accept)
        self.finished.connect(self.on_close)
        self.ui.dirsFirstBox.stateChanged.connect(self.apply_options)
        self.ui.includePreviousBox.stateChanged.connect(self.apply_options)
        self.ui.showHiddenBox.stateChanged.connect(self.apply_options)
        self.ui.upButton.clicked.connect(lambda: self.move_item(-1))
        self.ui.downButton.clicked.connect(lambda: self.move_item(1))
        self.ui.addButton.setIcon(QtGui.QIcon().fromTheme("list-add"))
        self.ui.removeButton.setIcon(QtGui.QIcon().fromTheme("list-remove"))
        self.ui.okButton.setIcon(QtGui.QIcon().fromTheme("dialog-ok"))
        self.ui.downButton.setIcon(QtGui.QIcon().fromTheme("go-down"))
        self.ui.upButton.setIcon(QtGui.QIcon().fromTheme("go-up"))
        self.ui.listView.setModel(G.model)
        self.ui.listView.setEditTriggers(QtGui.QListView.NoEditTriggers)
        self.selection = self.ui.listView.selectionModel()
        self.selection.currentChanged.connect(self.update)

    @QtCore.Slot()
    def apply_options(self):
        for (opt, box) in self.checkboxes.items():
            index = self.ui.listView.currentIndex()
            root = G.model.itemFromIndex(index)
            root.data().options[opt] = box.isChecked()

    @QtCore.Slot(int)
    def on_close(self, i):
        G.settings.write_settings()

    @QtCore.Slot(int)
    def move_item(self, direction):
        index = self.ui.listView.currentIndex()
        row = index.row()
        target = index.sibling(row + direction, index.column())
        if target.isValid():
            item = G.model.takeRow(row)
            G.model.insertRow(row + direction, item)
            self.ui.listView.setCurrentIndex(target)

    @QtCore.Slot()
    def on_addButton_clicked(self):
        newdir = QtGui.QFileDialog.getExistingDirectory(parent=self,
                                directory=os.getenv("HOME"),
                                options=QtGui.QFileDialog.ShowDirsOnly)
        if newdir:
            index = self.ui.listView.currentIndex().row()
            G.App.add_rootentry(newdir, index=index)

    @QtCore.Slot()
    def on_removeButton_clicked(self):
        index = self.ui.listView.currentIndex().row()
        G.App.remove_rootentry(index)

    @QtCore.Slot()
    def on_iconButton_clicked(self):
        fil = QtGui.QFileDialog.getOpenFileName(self, caption="Choose icon")
        if fil:
            index = self.ui.listView.currentIndex()
            item = G.model.itemFromIndex(index)
            item.data().icon_path = fil
            self.update()

    def init_checkboxes(self, options):
        for (opt, box) in self.checkboxes.items():
            if options[opt]:
                box.setCheckState(True)
                box.setTristate(False)
            else:
                box.setCheckState(False)
                box.setTristate(False)

    def activate(self):
        self.ui.listView.setCurrentIndex(G.model.index(0, 0))
        self.update()
        self.show()

    def update(self):
        index = self.ui.listView.currentIndex()
        if index.row() > -1:
            root = G.model.itemFromIndex(index).data()
            self.init_checkboxes(root.options)
            self.ui.iconButton.setIcon(root.icon())

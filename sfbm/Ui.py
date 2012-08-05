import os
import sfbm.Global as G
from sfbm.FileUtil import list_terminals
from PyQt4 import QtCore, QtGui, uic
Slot = QtCore.pyqtSlot

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
        themed_widgets = [[self.ui.addButton, "list-add", "Add"],
                          [self.ui.removeButton, "list-remove", "Remove"],
                          [self.ui.upButton, "go-up", "Move Up"],
                          [self.ui.downButton, "go-down", "Move Down"]]
        self.ui.okButton.clicked.connect(self.accept)
        self.finished.connect(self.on_close)
        self.ui.dirsFirstBox.clicked.connect(lambda c:
                                             self.toggle_checkbox("DirsFirst", c))
        self.ui.includePreviousBox.clicked.connect(lambda c:
                                                   self.toggle_checkbox("IncludePrevious", c))
        self.ui.showHiddenBox.clicked.connect(lambda c:
                                              self.toggle_checkbox("ShowHidden", c))
        self.ui.upButton.clicked.connect(lambda: self.move_item(-1))
        self.ui.downButton.clicked.connect(lambda: self.move_item(1))
        self.ui.okButton.setIcon(QtGui.QIcon().fromTheme("dialog-ok"))
        for wid in themed_widgets:
            self.try_set_icon(*wid)
        self.ui.listView.setModel(G.model)
        self.ui.listView.setEditTriggers(QtGui.QListView.NoEditTriggers)
        self.init_combobox()
        self.selection = self.ui.listView.selectionModel()
        self.selection.currentChanged.connect(self.update)

    @Slot(str, bool)
    def toggle_checkbox(self, option, checked):
        index = self.selection.currentIndex()
        root = G.model.itemFromIndex(index).data()
        root.options[option] = checked

    @Slot(int)
    def on_close(self, i):
        G.settings.write_settings()

    @Slot(int)
    def move_item(self, direction):
        index = self.selection.currentIndex()
        row = index.row()
        target = index.sibling(row + direction, index.column())
        if target.isValid():
            item = G.model.takeRow(row)
            G.model.insertRow(row + direction, item)
            self.ui.listView.setCurrentIndex(target)

    @Slot()
    def on_addButton_clicked(self):
        newdir = QtGui.QFileDialog.getExistingDirectory(parent=self,
                                directory=os.getenv("HOME"),
                                options=QtGui.QFileDialog.ShowDirsOnly)
        if newdir:
            index = self.selection.currentIndex().row()
            G.App.add_rootentry(newdir, index=index)

    @Slot()
    def on_removeButton_clicked(self):
        index = self.selection.currentIndex().row()
        G.App.remove_rootentry(index)

    @Slot()
    def on_trayiconButton_clicked(self):
        fil = QtGui.QFileDialog.getOpenFileName(self, caption="Choose icon")
        if fil:
            icon = QtGui.QIcon(fil)
            if icon:
                G.systray.setIcon(icon)
                G.settings.setValue("Settings/Icon", fil)
                self.ui.trayiconButton.setIcon(G.systray.icon())

    @Slot()
    def on_iconButton_clicked(self):
        fil = QtGui.QFileDialog.getOpenFileName(self, caption="Choose icon")
        if fil:
            index = self.selection.currentIndex()
            item = G.model.itemFromIndex(index)
            item.data().icon_path = fil
            self.update()

    @Slot(int)
    def on_terminalComboBox_activated(self, index):
        name = self.ui.terminalComboBox.itemText(index)
        cmdline = self.ui.terminalComboBox.itemData(index)
        self.ui.terminalLineEdit.setText("{}".format(" ".join(cmdline)))
        G.terminal = (name, cmdline)
        G.settings.setValue("Settings/Terminal", G.terminal)

    @Slot(str)
    def on_terminalLineEdit_textEdited(self, text):
        index = self.ui.terminalComboBox.findText("Other:")
        if self.ui.terminalComboBox.currentIndex() != index:
            cp = self.ui.terminalLineEdit.cursorPosition()
            self.ui.terminalLineEdit.setText(text)
            self.ui.terminalComboBox.setCurrentIndex(index)
            self.ui.terminalLineEdit.setCursorPosition(cp)
        name = self.ui.terminalComboBox.itemText(index)
        cmd, dummy, args = text.lstrip().partition(" ")
        cmdline = [cmd, args]
        self.ui.terminalComboBox.setItemData(index, cmdline)
        G.terminal = (name, cmdline)
        G.settings.setValue("Settings/Terminal", G.terminal)

    def try_set_icon(self, wid, icon_name, text):
        icon = QtGui.QIcon.fromTheme(icon_name)
        wid.setText(text) if icon.isNull() else wid.setIcon(icon)

    def init_checkboxes(self, options):
        for (opt, box) in self.checkboxes.items():
            box.setChecked(options[opt])

    def init_combobox(self):
        for (name, cmdline) in list_terminals():
            self.ui.terminalComboBox.addItem(name, cmdline)

    def activate(self):
        self.ui.listView.setCurrentIndex(G.model.index(0, 0))
        self.ui.trayiconButton.setIcon(G.systray.icon())

        name, cmdline = G.terminal
        index = self.ui.terminalComboBox.findText(name)
        if name == "Other:":
            self.ui.terminalComboBox.setItemData(index, cmdline)
        self.ui.terminalLineEdit.setText("{}".format(" ".join(cmdline)))
        self.ui.terminalComboBox.setCurrentIndex(index)

        self.update()
        self.show()

    def update(self):
        index = self.selection.currentIndex()
        if index.row() > -1:
            root = G.model.itemFromIndex(index).data()
            self.init_checkboxes(root.options)
            self.ui.iconButton.setIcon(root.icon())

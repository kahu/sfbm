from PyQt4 import QtCore
import sfbm.Global as G


class Config(QtCore.QSettings):
    def __init__(self, parent=None):
        QtCore.QSettings.__init__(self)

    def roots(self):
        self.beginGroup("Directories")
        sz = self.beginReadArray("root")
        try:
            if sz:
                for i in range(sz):
                    self.setArrayIndex(i)
                    path = self.value("path")
                    icon = self.value("icon", None)
                    options = self.value("options", None)
                    yield path, icon, options
            else:
                yield "/", None, None
        finally:
            self.endArray()
            self.endGroup()

    def write_settings(self):
        rows = G.model.rowCount()
        self.beginGroup("Settings")
        self.endGroup()
        self.beginGroup("Directories")
        self.beginWriteArray("root")
        self.remove("")
        for i in range(rows):
            self.setArrayIndex(i)
            menu = G.model.item(i).data()
            self.setValue("path", menu.data().absoluteFilePath())
            self.setValue("icon", menu.icon_path)
            self.setValue("options", menu.options)
        self.endArray()
        self.endGroup()
        self.sync()

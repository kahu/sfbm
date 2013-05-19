import sys
import os
import subprocess
from PyQt4 import QtCore, QtGui
from sfbm.Config import Config
from sfbm.Ui import PrefsDialog
from sfbm.FileUtil import guess_terminal, guess_icon_theme, detect_de
from sfbm.FileUtil import set_icon_theme, xdg_icon_provider
from sfbm.ContextMenu import ContextMenu
from sfbm.DirectoryMenu import RootEntry
from sfbm.GuiUtil import draggy_menu
import sfbm.Global as G
Slot = QtCore.pyqtSlot


class SFBM(QtGui.QApplication):
    def __init__(self):
        QtGui.QApplication.__init__(self, sys.argv)

        QtCore.QCoreApplication.setApplicationName("sfbm")
        QtCore.QCoreApplication.setOrganizationName("sfbm")

        G.App = self
        G.bold_font = self.font()
        G.bold_font.setBold(True)
        G.italic_font = self.font()
        G.italic_font.setItalic(True)
        G.desktop = detect_de()
        G.model = QtGui.QStandardItemModel()
        G.settings = Config()
        try:
            setting = G.settings.value("Settings/Terminal", None)
            if setting is None:
                G.terminal = guess_terminal()
                G.settings.setValue("Settings/Terminal", G.terminal)
            else:
                name, cmdline = setting
                G.terminal = (name, cmdline)
        except:
            G.terminal = ("Other:", ["", ""])
            G.settings.setValue("Settings/Terminal", G.terminal)
        set_icon_theme()
        G.prefs_dialog = PrefsDialog()
        G.item_context_menu = ContextMenu()
        G.systray = MainTray()
        self.roots = {}
        self.setAttribute(QtCore.Qt.AA_DontShowIconsInMenus, on=False)
        self.setStyleSheet("QMenu { menu-scrollable: 1; }")
        self.setQuitOnLastWindowClosed(False)
        self.aboutToQuit.connect(self.on_death)

        for (i, (path, icon, options)) in enumerate(G.settings.roots()):
            self.add_rootentry(path, icon=icon, index=i, options=options)

    def add_rootentry(self, path, icon=None, index=0, options=None):
        fi = QtCore.QFileInfo(path)
        if fi.exists() and fi.isDir():
            if not fi.absoluteFilePath() in self.roots.values():
                root = RootEntry(fi, icon_path=icon,
                                 parent=G.systray, options=options)
                G.model.insertRow(index, root.item)
                self.roots[root] = fi.absoluteFilePath()
                return root

    def remove_rootentry(self, index):
        root = G.model.item(index)
        if len(self.roots) > 1 and root:
            self.roots.pop(root.data())
            G.model.removeRow(index)
            return True
        else:
            return False

    @Slot()
    def on_death(self):
        G.settings.write_settings()
        G.systray.hide()
        G.systray.deleteLater()


@draggy_menu
class MainMenu(QtGui.QMenu):
    def __init__(self, parent=None):
        QtGui.QMenu.__init__(self, parent)

        self.app_actions = []
        self.aboutToShow.connect(self.populate_menu)
        self.add_app_action("Settings", G.prefs_dialog.activate,
                            "preferences-other")
        self.add_app_action("Quit", G.App.quit, "application-exit")

    def add_app_action(self, text, func, theme_icon=None):
        action = QtGui.QAction(text, G.systray)
        action.triggered.connect(func)
        if theme_icon:
            action.setIcon(QtGui.QIcon().fromTheme(theme_icon))
        self.app_actions.append(action)

    def populate_menu(self):
        self.clear()
        G.drag_start_action = None
        G.drag_start_position = None
        rows = G.model.rowCount()
        try:
            for row in range(rows):
                root = G.model.item(row).data()
                if root.options["Flatten"]:
                    if row > 0:
                        self.addSeparator()
                    root.setFont(G.bold_font)
                    root.setDisabled(True)
                    self.addAction(root)
                    root.menu().populate()
                    for act in root.menu().get_contents():
                        self.addAction(act)
                    if row < rows:
                        self.addSeparator()
                else:
                    root.setFont(G.App.font())
                    root.setDisabled(False)
                    self.addAction(root)
        finally:
            self.addSeparator()
            self.addActions(self.app_actions)


class MainTray(QtGui.QSystemTrayIcon):
    def __init__(self, parent=None):
        QtGui.QSystemTrayIcon.__init__(self, parent)

        self.icon_path = G.settings.value("Settings/Icon")
        self.menu = MainMenu(parent)
        self.setContextMenu(self.menu)
        self.activated.connect(self.on_activated)
        self.show()

    @Slot(QtGui.QSystemTrayIcon.ActivationReason)
    def on_activated(self, reason):
        if reason == QtGui.QSystemTrayIcon.Trigger:
            G.icon_cache = {}
            self.menu.popup(QtGui.QCursor.pos())

    @property
    def icon_path(self):
        return self._icon_path

    @icon_path.setter
    def icon_path(self, path):
        self._icon_path = path
        icon = QtGui.QIcon(path)
        if (not path) or icon.isNull():
            icon = QtGui.QIcon.fromTheme("user-home")
            if icon.isNull():
                icon = QtGui.QFileIconProvider().icon(QtGui.QFileIconProvider.Drive)
        self.setIcon(icon)
        G.App.setWindowIcon(icon)


def main():
    sys.exit(SFBM().exec_())


if __name__ == "__main__":
    main()

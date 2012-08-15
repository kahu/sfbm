import os
from PyQt4 import QtCore, QtGui
import sfbm.Global as G
from sfbm.FileUtil import launch, maybe_execute, entry_visuals
from sfbm.GuiUtil import DraggyAction, DraggyMenu, actionAtPos, StopPopulating
from xdg import DesktopEntry
Slot = QtCore.pyqtSlot


class DirectoryMenu(QtGui.QMenu, DraggyMenu):
    def __init__(self, root=None, parent=None):
        QtGui.QMenu.__init__(self, parent)

        self.aboutToShow.connect(self.populate)
        self.aboutToHide.connect(self.die)
        self.triggered.connect(self.on_triggered)
        self.root = root

    def eventFilter(self, obj, event):
        if obj is G.App:
            return False
        t = event.type()
        if (t == QtCore.QEvent.ChildAdded or
            t == QtCore.QEvent.ActionAdded or
            t == QtCore.QEvent.KeyPress):
            return False
        return True

    @Slot(QtGui.QAction)
    def on_triggered(self, action):
        if isinstance(self.menuAction(), DraggyAction):
            launch(action.data())

    @Slot()
    def die(self):
        for c in self.children():
            c.deleteLater()

    def get_contents(self):
        for act in self.children():
            if isinstance(act, DraggyAction):
                yield act

    @Slot()
    def populate(self):
        self.clear()
        G.populating = True
        G.abort = False
        directory = QtCore.QDir(self.menuAction().path())
        directory.setSorting(self.root.sorting)
        directory.setFilter(self.root.filter)
        file_list = directory.entryInfoList()
        in_path = self.menuAction().path() in os.get_exec_path()
        try:
            G.App.installEventFilter(self)
            for i, item in enumerate(file_list):
                file_list[i] = MenuEntry(item, root=self.root,
                                         parent=self, in_path=in_path)
            self.addActions(file_list)
        except StopPopulating:
            self.die()
            return None
        finally:
            G.App.removeEventFilter(self)
            G.populating = False

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Escape:
            if G.populating:
                G.abort = True
                return
        if G.populating:
            return
        QtGui.QMenu.keyPressEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            action = actionAtPos(event.globalPos())
            if action and action.menu():
                launch(action.data())
                action.menu().hide()
            self.hide()
            G.systray.menu.hide()
            event.accept()
        else:
            QtGui.QMenu.mouseDoubleClickEvent(self, event)


def decorate_action(action, root=None, in_path=False):
    fi = action.data()
    name = fi.fileName()
    if fi.isDir():
        action.setMenu(DirectoryMenu(root))
        return name, G.icon_provider.icon(fi)
    xec = maybe_execute(fi)
    if isinstance(xec, DesktopEntry.DesktopEntry):
        action.setFont(G.bold_font)
        name, icon = entry_visuals(xec)
        action.setFont(G.bold_font)
        return name, icon
    if not in_path and xec is True:
        action.setFont(G.bold_font)
    return name, G.icon_provider.icon(fi)


class MenuEntry(QtGui.QAction, DraggyAction):
    def __init__(self, fileinfo, root=None, parent=None, in_path=False):
        QtGui.QAction.__init__(self, parent)

        self.root = root
        G.App.processEvents()
        if G.abort:
            raise StopPopulating
        self.setData(fileinfo)
        name, icon = decorate_action(self, root=root, in_path=in_path)
        icon = icon or G.icon_provider.icon(self.data())
        self.setText(name.replace("&", "&&"))
        self.setIcon(icon)

    def path(self):
        return self.data().absoluteFilePath()

    def urllist(self):
        return [QtCore.QUrl.fromLocalFile(self.path())]

    def drag_pixmap(self):
        widget = QtGui.QWidget()
        layout = QtGui.QHBoxLayout(widget)
        text_label = QtGui.QLabel(self.text())
        icon_label = QtGui.QLabel()
        icon_label.setPixmap(QtGui.QPixmap(self.icon().pixmap(24, 24)))
        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        pixmap = QtGui.QPixmap.grabWidget(widget)
        return pixmap


class RootEntry(MenuEntry):
    def __init__(self, fileinfo, icon_path=None, parent=None, options=None):
        MenuEntry.__init__(self, fileinfo, root=self, parent=parent)

        self.item = QtGui.QStandardItem()
        self.item.setData(self)
        self.item.setText(self.data().absoluteFilePath())
        self.icon_path = icon_path
        self.options = options if options else {}
        for opt, val in G.default_options.items():
            if not self.options.get(opt, None):
                self.options[opt] = val

    @property
    def icon_path(self):
        return self._iconpath

    @icon_path.setter
    def icon_path(self, path):
        self._iconpath = path
        if path:
            self.setIcon(QtGui.QIcon(path))
            self.item.setIcon(self.icon())
        else:
            icon = G.icon_provider.icon(self.data())
            self.setIcon(icon)
            self.item.setIcon(icon)

    @property
    def sorting(self):
        _sorting = QtCore.QDir.Name | QtCore.QDir.LocaleAware
        if self.options["DirsFirst"]:
            _sorting = _sorting | QtCore.QDir.DirsFirst
        return _sorting

    @property
    def filter(self):
        _filter = (QtCore.QDir.AllEntries |
                   QtCore.QDir.System |
                   QtCore.QDir.NoDot)
        if self.options["ShowHidden"]:
            _filter = _filter | QtCore.QDir.Hidden
        if not self.options["IncludePrevious"]:
            _filter = _filter | QtCore.QDir.NoDotDot
        return _filter

import os
from PyQt4 import QtGui, QtCore
from sfbm.FileUtil import launch, maybe_execute, entry_visuals
from sfbm.FileUtil import readable_size, terminal_there, opens_with
from sfbm.GuiUtil import DraggyAction, DraggyMenu
import sfbm.Global as G
from xdg import Mime


class PermissionsMenu(QtGui.QMenu):
    def __init__(self, parent=None):
        QtGui.QMenu.__init__(self, parent)

        self.cur_path = None
        self.cur_perm = None
        self.fileinfo = None
        self.aboutToShow.connect(self.update)

    def do_chmod(self, m):
        new_perm = self.cur_perm ^ m
        os.chmod(self.cur_path, new_perm)
        self.cur_perm = new_perm

    def update(self):
        self.clear()
        self.fileinfo.refresh()
        self.cur_path = self.fileinfo.absoluteFilePath()
        self.cur_perm = os.stat(self.cur_path).st_mode
        perm_action = QtGui.QWidgetAction(self)
        perm_widget = QtGui.QWidget()
        perm_action.setDefaultWidget(perm_widget)
        v_lay = QtGui.QVBoxLayout(perm_widget)
        for context, j in zip(["User: ", "Group: ", "Other: "], [0o100, 0o10, 0o1]):
            row = QtGui.QWidget()
            h_lay = QtGui.QHBoxLayout(row)
            h_lay.addWidget(QtGui.QLabel(context))
            for flag, i in zip(["Read", "Write", "Exec"], [4, 2, 1]):
                cbox = QtGui.QCheckBox(flag)
                if self.cur_perm & (i * j):
                    cbox.setChecked(True)
                cbox.stateChanged.connect(lambda s, m=i * j: self.do_chmod(m))
                h_lay.addWidget(cbox)
            v_lay.addWidget(row)
        if self.fileinfo.ownerId() != os.getuid():
            perm_widget.setDisabled(True)
        for own, f in zip(["User: ", "Group: "],
                          [self.fileinfo.owner(),
                           self.fileinfo.group()]):
            act = QtGui.QAction(self)
            act.setText(own + f)
            act.setDisabled(True)
            self.addAction(act)
        self.addAction(perm_action)


class OpenMenu(QtGui.QMenu):
    def __init__(self, actions, parent=None):
        QtGui.QMenu.__init__(self, parent)

        self.aboutToShow.connect(self.populate)
        self.actions = actions

    def populate(self):
        self.clear()
        for path in opens_with(Mime.get_type(self.actions[0].path())):
            name, icon = entry_visuals(path)
            act = QtGui.QAction(name, self)
            if icon:
                act.setIcon(icon)
            act.triggered.connect(lambda dummy,
                                         path=path,
                                         acts=self.actions:
                                         self.open_it(path, self.actions))
            self.addAction(act)

    def open_it(self, path, acts):
        xec = QtCore.QFileInfo(path)
        urllist = [act.urllist()[0] for act in acts]
        launch(xec, urllist=urllist)


class MimeAction(QtGui.QAction, DraggyAction):
    def __init__(self, action, parent=None):
        QtGui.QAction.__init__(self, parent)

        self.setMenu(MimeMenu(action))
        self.mime = Mime.get_type(action.path())
        self.setIcon(G.icon_provider.icon(action.data()))
        self.setText(str(self.mime))

    def urllist(self):
        return [act.urllist()[0] for act in self.menu().actions]

    def drag_pixmap(self):
        rec = self.menu().actionGeometry(self)
        pix = QtGui.QPixmap.grabWidget(self.menu(), rec)
        return pix


class MimeMenu(QtGui.QMenu, DraggyMenu):
    def __init__(self, action, parent=None):
        QtGui.QMenu.__init__(self, parent)

        self.action = action
        self.path = action.path()
        self.aboutToShow.connect(self.prepare)
        self.aboutToHide.connect(self.clear)

    def prepare(self):
        self.clear()
        sibs = self.action.parent().children()
        self.actions = []
        for act in sibs:
            if act.data():
                if self.menuAction().mime == Mime.get_type(act.path()):
                    self.actions.append(act)
        self.open_action = QtGui.QAction("Open With", self)
        self.open_action.setMenu(OpenMenu(self.actions))
        self.addAction(self.open_action)
        self.addActions(self.actions)

    def contextMenuEvent(self, event):
        event.accept()


class ContextMenu(QtGui.QMenu, DraggyMenu):
    def __init__(self, parent=None):
        QtGui.QMenu.__init__(self, parent)

        self.aboutToShow.connect(self.prepare)

    def prepare(self):
        ### Open file
        self.open_action = QtGui.QAction("Open", self)
        self.open_action.triggered.connect(lambda: launch(self.action.data()))

        ### Terminal
        self.term_action = QtGui.QAction("Open Terminal Here", self)
        self.term_action.triggered.connect(lambda: terminal_there(self.action.data()))

        ### Permissions
        self.perm_action = QtGui.QAction("Permissions", self)
        self.perm_menu = PermissionsMenu()
        self.perm_action.setMenu(self.perm_menu)

        self.title_action = QtGui.QAction("", self)
        self.title_action.setEnabled(False)
        self.title_action.setFont(G.bold_font)

        self.size_action = QtGui.QAction("", self)
        self.size_action.setEnabled(False)

        self.addAction(self.title_action)
        self.addAction(self.size_action)
        self.addSeparator()

        self.title_action.setText(self.action.text())
        self.size_action.setText(readable_size(self.action))
        self.perm_menu.fileinfo = self.action.data()
        if maybe_execute(self.action.data(), False):
            self.open_action.setText("Run")
        else:
            self.open_action.setText("Open")
        if not self.action.data().isDir():
            self.mime_action = MimeAction(self.action, parent=self)
            self.addAction(self.mime_action)
        self.addAction(self.open_action)
        self.opact = QtGui.QAction("Open With", self)
        self.opact.setMenu(OpenMenu([self.action]))
        self.addAction(self.opact)
        self.addAction(self.term_action)
        self.addAction(self.perm_action)

    def act(self, action, pos):
        self.clear()
        self.action = action
        self.popup(pos)

import os
from PyQt4 import QtGui
from sfbm.FileUtil import launch, readable_size
import sfbm.Global as G


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
        for own, f in zip(["User: ", "Group: "], [self.fileinfo.owner(), self.fileinfo.group()]):
            act = QtGui.QAction(self)
            act.setText(own + f)
            act.setDisabled(True)
            self.addAction(act)
        self.addAction(perm_action)


class ContextMenu(QtGui.QMenu):
    def __init__(self, parent=None):
        QtGui.QMenu.__init__(self, parent)

        self.title_action = QtGui.QAction("", self)
        self.title_action.setEnabled(False)
        self.title_action.setFont(G.bold_font)

        self.size_action = QtGui.QAction("", self)
        self.size_action.setEnabled(False)

        self.addAction(self.title_action)
        self.addAction(self.size_action)
        self.addSeparator()

        ### Open file
        self.open_action = QtGui.QAction("Open", self)
        self.open_action.triggered.connect(lambda: launch(self.action.data()))
        self.addAction(self.open_action)

        ### Permissions
        self.perm_action = QtGui.QAction("Permissions", self)
        self.perm_menu = PermissionsMenu()
        self.perm_action.setMenu(self.perm_menu)
        self.addAction(self.perm_action)

    def act(self, action, pos):
        self.action = action
        self.title_action.setText(self.action.text())
        self.size_action.setText(readable_size(self.action.data()))
        self.perm_menu.fileinfo = self.action.data()
        self.popup(pos)



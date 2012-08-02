import subprocess
import os
from PyQt4 import QtCore, QtGui
import xdg.Mime as Mime
import xdg.DesktopEntry as DesktopEntry
import xdg.IconTheme as IconTheme
import xdg.Exceptions
import sfbm.Global as G
QtCore.Signal = QtCore.pyqtSignal
QtCore.Slot = QtCore.pyqtSlot


escape_table = {
        r'\s': ' ',
        r'\n': '\n',
        r'\t': '\t',
        r'\r': '\r',
        '\\\\': '\\'}


def unescaper(s, repfunc):
    if not s:
        return s

    def _inner():
        it = zip(s, s[1:])
        for cur, nex in it:
            key = cur + nex
            rep = repfunc(key)
            if rep is not None:
                yield rep
                try:
                    next(it)
                except StopIteration:
                    return
            else:
                yield cur
        yield s[-1]
    return ''.join(_inner())


def unescape_slashes(key):
    if key in escape_table:
        return escape_table[key]
    else:
        return None


def format_stripper(key):
    if key == "%%":
        return "%"
    if key.startswith("%"):
        return ""
    return None


###http://bugs.python.org/issue444582
def which(cmd, mode=os.F_OK | os.X_OK, path=None):
    def _access_check(fn, mode):
        if (os.path.exists(fn) and os.access(fn, mode)
            and not os.path.isdir(fn)):
            return True
        return False

    if _access_check(cmd, mode):
        return cmd
    path = (path or os.environ.get("PATH", os.defpath)).split(os.pathsep)
    files = [cmd]
    seen = set()
    for directory in path:
        directory = os.path.normcase(os.path.abspath(directory))
        if not directory in seen:
            seen.add(directory)
            for thefile in files:
                name = os.path.join(directory, thefile)
                if _access_check(name, mode):
                    return name
    return None


def maybe_execute(fileinfo, execute=False):
    def _really_execute(cmd, shell=False, cwd=None):
        try:
            subprocess.Popen(cmd, shell=shell, cwd=cwd, env=os.environ)
            return True
        except OSError:
            return False

    if execute:
        fileinfo.refresh()
    if fileinfo.isExecutable():
        filepath = fileinfo.absoluteFilePath()
        mimetype = str(Mime.get_type(filepath))
        if mimetype in G.EXECUTABLES:
            if execute:
                return _really_execute([filepath], cwd=os.getenv("HOME"))
            else:
                return True
        if filepath.endswith(".desktop"):
            entry = DesktopEntry.DesktopEntry(filepath)
            tryex = entry.getTryExec()
            tryex = True if tryex == "" else which(tryex)
            if not execute:
                return tryex
            elif tryex:
                xec = unescaper(entry.getExec(), unescape_slashes)
                xec = unescaper(xec, format_stripper)
                path = entry.getPath() or os.getenv("HOME")
                return _really_execute(xec, shell=True, cwd=path)
    return False


def actionAtPos(pos):
    menu = G.App.widgetAt(pos)
    if isinstance(menu, QtGui.QMenu):
        action = menu.actionAt(menu.mapFromGlobal(pos))
        if isinstance(action, MenuEntry):
            return action


class MenuEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        t = event.type()
        if (t == QtCore.QEvent.ChildAdded or
            t == QtCore.QEvent.ActionAdded or
            t == QtCore.QEvent.KeyPress):
            return False
        return True


def launch(fileinfo):
    fileinfo.refresh()
    if fileinfo.isSymLink():
        filename = fileinfo.symLinkTarget()
    else:
        filename = fileinfo.absoluteFilePath()
    if fileinfo.isDir():
        url = QtCore.QUrl.fromUserInput(filename)
        QtGui.QDesktopServices.openUrl(url)
        return
    elif not maybe_execute(fileinfo, execute=True):
        url = QtCore.QUrl.fromUserInput(filename)
        QtGui.QDesktopServices.openUrl(url)


class DirectoryMenu(QtGui.QMenu):
    def __init__(self, parent=None):
        QtGui.QMenu.__init__(self, parent)

        self.aboutToShow.connect(self.populate)
        self.aboutToHide.connect(self.die)

    @QtCore.Slot()
    def die(self):
        for c in self.children():
            c.deleteLater()

    @QtCore.Slot()
    def populate(self):
        self.clear()
        directory = QtCore.QDir(self.menuAction().data().absoluteFilePath())
        directory.setSorting(G.active_root.sorting)
        directory.setFilter(G.active_root.filter)
        file_list = directory.entryInfoList()
        try:
            G.populating = True
            aborter = MenuEventFilter(self)
            G.abort = False
            G.App.installEventFilter(aborter)
            in_path = self.menuAction().data().absoluteFilePath() in os.get_exec_path()
            for i, item in enumerate(file_list):
                G.App.processEvents()
                if G.abort:
                    self.die()
                    return
                file_list[i] = MenuEntry(item, parent=self, in_path=in_path)
            self.addActions(file_list)
        finally:
            G.App.removeEventFilter(aborter)
            aborter.deleteLater()
            G.populating = False

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Escape:
            if G.populating:
                G.abort = True
                return
        if key == QtCore.Qt.Key_F4:
            self.menuAction().terminal()
            if G.populating:
                G.abort = True
            return
        if G.populating:
            return
        QtGui.QMenu.keyPressEvent(self, event)

    def contextMenuEvent(self, event):
        pos = event.globalPos()
        action = actionAtPos(pos)
        if action:
            G.item_context_menu.act(action, pos)
            event.accept()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.globalPos()
            G.drag_start_position = pos
            G.drag_start_action = actionAtPos(pos)
            event.accept()
        QtGui.QMenu.mousePressEvent(self, event)

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

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            action = actionAtPos(event.globalPos())
            if action:
                if action.menu():
                    launch(action.data())
                else:
                    launch(self.menuAction().data())
            event.accept()
        else:
            QtGui.QMenu.mouseReleaseEvent(self, event)

    def mouseMoveEvent(self, event):
        if (event.buttons() != QtCore.Qt.LeftButton or not G.drag_start_position):
            QtGui.QMenu.mouseMoveEvent(self, event)
            return
        distance = (event.globalPos() - G.drag_start_position).manhattanLength()
        if distance < G.App.startDragDistance():
            QtGui.QMenu.mouseMoveEvent(self, event)
            return
        dragged = G.drag_start_action
        if dragged is None:
            QtGui.QMenu.mouseMoveEvent(self, event)
            return
        url = QtCore.QUrl.fromLocalFile(dragged.data().absoluteFilePath())
        mimeData = QtCore.QMimeData()
        mimeData.setUrls([url])

        drag = QtGui.QDrag(self)
        drag.setPixmap(dragged.drag_pixmap())
        drag.setMimeData(mimeData)
        drag.start(QtCore.Qt.MoveAction |
                   QtCore.Qt.CopyAction |
                   QtCore.Qt.LinkAction)
        G.drag_start_action = None
        G.drag_start_position = None


class MenuEntry(QtGui.QAction):
    def __init__(self, fileinfo, parent=None, in_path=False):
        QtGui.QAction.__init__(self, parent)

        self.setData(fileinfo)
        self.setText(fileinfo.fileName().replace("&", "&&"))
        if fileinfo.isDir():
            self.setMenu(DirectoryMenu())
        elif (fileinfo.isExecutable and not in_path and
              maybe_execute(fileinfo, execute=False)):
                self.setFont(G.bold_font)
        icon = G.icon_provider.icon(fileinfo)
        self.setIcon(icon)

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

    def readable_size(self):
        fileinfo = self.data()
        fileinfo.refresh()
        if fileinfo.isFile():
            bs = fileinfo.size()
            for sz in ['bytes', 'KB', 'MB', 'GB', 'TB']:
                if bs < 1024:
                    return '{0:4n} {1}'.format(round(bs, 2), sz)
                bs = bs / 1024
            return '{:4n} PB'.format(round(bs, 2))
        elif fileinfo.isDir():
            directory = QtCore.QDir(fileinfo.absoluteFilePath())
            directory.setSorting(G.active_root.sorting)
            directory.setFilter(G.active_root.filter)
            size = directory.count()
            return "{0} items".format(size)
        else:
            return ""

    def terminal(self):
        fileinfo = self.data()
        fileinfo.refresh()
        if fileinfo.isDir():
            path = fileinfo.absoluteFilePath()
        else:
            path = fileinfo.absolutePath()
        subprocess.Popen(["/usr/bin/konsole", "--workdir", path])


class RootEntry(MenuEntry):
    def __init__(self, fileinfo, icon_path=None, parent=None, options=None):
        MenuEntry.__init__(self, fileinfo, parent=parent)

        self.item = QtGui.QStandardItem()
        self.item.setData(self)
        self.item.setText(self.data().absoluteFilePath())
        self.icon_path = icon_path
        self.options = options if options else G.default_options
        self.hovered.connect(self.set_active)

    @QtCore.Slot()
    def set_active(self):
        G.active_root = self

    @property
    def icon_path(self):
        return self._iconpath

    @icon_path.setter
    def icon_path(self, path):
        self._iconpath = path
        if path:
            self.setIcon(QtGui.QIcon(path))
            self.item.setIcon(self.icon())

    @property
    def sorting(self):
        _sorting = QtCore.QDir.Name | QtCore.QDir.LocaleAware
        if self.options["DirsFirst"]:
            _sorting = _sorting | QtCore.QDir.DirsFirst
        return _sorting

    @property
    def filter(self):
        _filter = QtCore.QDir.AllEntries | QtCore.QDir.System
        if self.options["ShowHidden"]:
            _filter = _filter | QtCore.QDir.Hidden
        if not self.options["IncludePrevious"]:
            _filter = _filter | QtCore.QDir.NoDotAndDotDot
        return _filter

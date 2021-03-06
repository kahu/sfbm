from PyQt4 import QtCore, QtGui
import sfbm.Global as G
from sfbm.FileUtil import launch


def actionAtPos(pos):
    menu = G.App.widgetAt(pos)
    if isinstance(menu, QtGui.QMenu):
        action = menu.actionAt(menu.mapFromGlobal(pos))
        if action and isinstance(action, DraggyAction):
            return action


class StopPopulating(BaseException):
    pass


class DraggyAction():
    def urllist(self):
        pass

    def drag_pixmap(self):
        pass


class DraggyMenu():
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.globalPos()
            G.drag_start_position = pos
            G.drag_start_action = actionAtPos(pos)
            event.accept()
        QtGui.QMenu.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if (event.buttons() != QtCore.Qt.LeftButton or not G.drag_start_position):
            QtGui.QMenu.mouseMoveEvent(self, event)
            return
        distance = (event.globalPos() - G.drag_start_position).manhattanLength()
        if distance < G.App.startDragDistance():
            QtGui.QMenu.mouseMoveEvent(self, event)
            return
        dragged = G.drag_start_action
        if not isinstance(dragged, DraggyAction):
            QtGui.QMenu.mouseMoveEvent(self, event)
            return
        urllist = dragged.urllist()
        mimeData = QtCore.QMimeData()
        mimeData.setUrls(urllist)

        drag = QtGui.QDrag(self)
        drag.setPixmap(dragged.drag_pixmap())
        drag.setMimeData(mimeData)
        drag.start(QtCore.Qt.MoveAction |
                   QtCore.Qt.CopyAction |
                   QtCore.Qt.LinkAction)
        G.drag_start_action = None
        G.drag_start_position = None

    def contextMenuEvent(self, event):
        pos = event.globalPos()
        action = actionAtPos(pos)
        if action:
            G.item_context_menu.act(action, pos)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            return
        if event.button() == QtCore.Qt.MiddleButton:
            action = actionAtPos(event.globalPos())
            if action:
                if action.menu():
                    launch(action.data())
                elif self.menuAction().data():
                    launch(self.menuAction().data())
                else:
                    launch(action.root.data())
            event.accept()
        else:
            QtGui.QMenu.mouseReleaseEvent(self, event)

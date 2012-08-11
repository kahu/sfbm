import subprocess
import os
from PyQt4 import QtCore, QtGui
from xdg import Mime, DesktopEntry
import sfbm.Global as G


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


terminals = (("LXTerminal",
              ["lxterminal", "--working-directory="], "lxde"),
             ("Terminal (XFCE)",
              ["xfce4-terminal", "--working-directory"], "xfce"),
             ("Gnome Terminal",
              ["gnome-terminal", "--working-directory"], "gnome"),
             ("Konsole",
              ["konsole", "--workdir"], "kde"))


def list_terminals():
    try:
        for (name, cmdline, dummy) in reversed(terminals):
            if which(cmdline[0]):
                yield (name, cmdline)
    finally:
        yield ("Other:", ["", ""])


def guess_terminal():
    desktop = os.getenv("DESKTOP_SESSION", "")
    shitterm = None
    for (name, cmdline, de) in terminals:
        if de in desktop:
            return (name, cmdline)
        elif which(cmdline[0]):
            shitterm = (name, cmdline)
    return shitterm


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
    filepath = fileinfo.absoluteFilePath()
    if fileinfo.isExecutable():
        mimetype = str(Mime.get_type(filepath))
        if mimetype in G.EXECUTABLES:
            if execute:
                path = fileinfo.absolutePath()
                if path in os.get_exec_path():
                    path = os.getenv("HOME", path)
                return _really_execute([filepath], cwd=path)
            else:
                return True
    if filepath.endswith(".desktop"):
        if fileinfo.isExecutable() or fileinfo.ownerId() == 0:
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


def readable_size(action):
    fileinfo = action.data()
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
        directory.setSorting(action.root.sorting)
        directory.setFilter(action.root.filter)
        size = directory.count()
        return "{0} items".format(size)
    else:
        return ""


def launch(fileinfo):
    fileinfo.refresh()
    filename = fileinfo.absoluteFilePath()
    if fileinfo.isDir():
        url = QtCore.QUrl.fromUserInput(filename)
        QtGui.QDesktopServices.openUrl(url)
        return
    elif not maybe_execute(fileinfo, execute=True):
        url = QtCore.QUrl.fromUserInput(filename)
        QtGui.QDesktopServices.openUrl(url)


def terminal_there(fi):
    fi.refresh()
    directory = fi.absoluteFilePath() if fi.isDir() else fi.absolutePath()
    dummy, (cmd, args) = G.terminal
    if args.endswith("="):
        cmdline = [cmd.strip(), args.lstrip() + directory]
    else:
        cmdline = [cmd.strip(), args.strip(), directory]
    try:
        subprocess.Popen(cmdline)
    except OSError:
        G.prefs_dialog.activate()

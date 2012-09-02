import subprocess
import os
import itertools
import pipes
from collections import OrderedDict
from PyQt4 import QtCore, QtGui
from xdg import Mime, DesktopEntry, IconTheme, BaseDirectory, IniFile
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
        it = itertools.izip(s, s[1:])
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


def format_expander(key, entry=None, urllist=None):
    if key == "%%":
        return "%"
    if key.startswith("%"):
        if urllist:
            if key == "%f":
                return pipes.quote(urllist[0].path())
            if key == "%F":
                return ' '.join(pipes.quote(u.path()) for u in urllist)
            if key == "%u":
                return pipes.quote(urllist[0].toString())
            if key == "%U":
                return ' '.join(pipes.quote(u.toString()) for u in urllist)
        if key == "%i":
            icon = entry.getIcon()
            if icon:
                return "--icon " + pipes.quote(icon)
        if key == "%c":
            name = entry.getName()
            return pipes.quote(name)
        if key == "%k":
            path = os.path.dirname(entry.getFileName())
            if os.path.isabs(path):
                return pipes.quote(path)
        return ""
    return None


def parse_exec_line(entry, urllist=None):
    xec = unescaper(entry.getExec(), unescape_slashes)
    xec = unescaper(xec, lambda k: format_expander(k, entry=entry, urllist=urllist))
    return xec


def entry_visuals(entry):
    name = entry.getName()
    icon = IconTheme.getIconPath(entry.getIcon(), theme=G.icon_theme)
    icon = QtGui.QIcon(icon) if icon else None
    if (not icon) or icon.isNull():
        icon = None
    return name, icon


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
    shitterm = None
    for (name, cmdline, de) in terminals:
        if de == G.desktop:
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


def list_icon_themes():
    themes = OrderedDict()
    dirs = BaseDirectory.load_data_paths("icons")
    seen = set()
    for d in dirs:
        if d in seen:
            continue
        seen.add(d)
        thlist = os.listdir(d)
        for th in thlist:
            idx = os.path.join(d, th, "index.theme")
            if os.path.exists(idx):
                ini = IniFile.IniFile(idx)
                if (ini.hasGroup("Icon Theme")
                    and ini.hasKey("Directories", "Icon Theme")
                    and not ini.get("Hidden", group="Icon Theme") == "true"):
                    themes[th] = ini
    return sorted(themes.keys())


def guess_icon_theme():
    guesses = {"kde": "oxygen", "gnome": "gnome"}
    themes = list_icon_themes()
    guess = guesses.get(G.desktop)
    if guess in themes:
        return guess


def set_icon_theme(theme=None):
    try:
        theme = theme or G.settings.value("Settings/IconTheme", None)
        G.icon_theme = theme or guess_icon_theme()
    except:
        G.icon_theme = "hicolor"
    finally:
        QtGui.QIcon.setThemeName(G.icon_theme)
        G.settings.setValue("Settings/IconTheme", G.icon_theme)
        if ((G.desktop == "kde" and G.icon_theme == "oxygen")
            or (G.desktop == "gnome" and G.icon_theme == "gnome")):
            G.icon_provider = QtGui.QFileIconProvider()
        else:
            G.icon_provider = xdg_icon_provider()


class xdg_icon_provider():
    def icon(self, fi):
        if fi.isDir():
            return QtGui.QIcon.fromTheme("inode-directory")
        mime = Mime.get_type(fi.absoluteFilePath())
        mimestr = str(mime).replace("/", "-")
        icon = G.icon_cache.get(mimestr)
        if icon:
            return icon
        ipath = IconTheme.getIconPath(mimestr, theme=G.icon_theme)
        if not ipath:
            ipath = IconTheme.getIconPath(mime.media + "-x-generic", theme=G.icon_theme)
        qi = QtGui.QIcon(ipath)
        if qi.isNull():
            qi = QtGui.QIcon.fromTheme("text-plain")
        G.icon_cache[mimestr] = qi
        return qi


### Ugly piece of shit from xdg-mime. Fuck the linux desktop.
def detect_de():
    if os.getenv("KDE_FULL_SESSION") == "true":
        return "kde"
    if os.getenv("GNOME_DESKTOP_SESSION_ID"):
        return "gnome"
    if os.getenv("DESKTOP_SESSION") == "LXDE":
        return "lxde"
    if os.getenv("XDG_CURRENT_DESKTOP") == "LXDE":
        return "lxde"
    if "xfce4" in subprocess.Popen(["xprop", "-root", "_DT_SAVE_MODE"],
                                   stdout=subprocess.PIPE).communicate()[0].decode():
        return "xfce"
    if subprocess.call("dbus-send --print-reply"
                       "--dest=org.freedesktop.DBus"
                       "/org/freedesktop/DBus"
                       "org.freedesktop.DBus.GetNameOwner"
                       "string:org.gnome.SessionManager > /dev/null 2>&1",
                       shell=True) == 0:
        return "gnome"
    return "it's a kitty!"


def opens_with(mimetype):
    def _kde():
        proc = subprocess.Popen(["ktraderclient", "--mimetype", mimetype],
                                stdout=subprocess.PIPE)
        res = proc.communicate()[0].decode().splitlines()
        entries = filter(lambda s: s.startswith("DesktopEntryPath"), res)
        entries = map(lambda s: s.split(':')[1].split("'")[1], entries)
        entries = map(DesktopEntry.DesktopEntry, entries)
        return entries

    def _gnome():
        proc = subprocess.Popen(["gvfs-mime", "--query", mimetype],
                                stdout=subprocess.PIPE)
        res = proc.communicate()[0].decode().splitlines()
        entries = itertools.takewhile(lambda s: s[0] in " \t" and
                                      s.endswith(".desktop"), res[2:])
        entries = [s.strip() for s in entries]
        for i, entry in enumerate(entries):
            if entry.startswith("kde4-"):
                entries[i] = "kde4/" + entry[5:]
        entries = map(lambda s: next(BaseDirectory.load_data_paths(
                                        "applications/" + s)), entries)
        entries = map(DesktopEntry.DesktopEntry, entries)
        return entries

    def _generic():
        entries = OrderedDict()
        seen = set()
        for mapps in itertools.chain(BaseDirectory.load_data_paths("applications/mimeapps.list"),
                                     BaseDirectory.load_data_paths("applications/defaults.list")):
            if mapps in seen:
                continue
            seen.add(mapps)
            with open(mapps) as mf:
                for l in mf:
                    if l.startswith(mimetype):
                        filenames = l.split("=")[1].strip().split(";")
                        for dfile in filenames:
                            if dfile:
                                dpath = BaseDirectory.load_data_paths("applications", dfile)
                                dpath = list(dpath)
                                if dpath:
                                    entry = DesktopEntry.DesktopEntry(dpath[0])
                                    entries[dfile] = entry
        return entries.values()

    desks = {"kde": _kde, "gnome": _gnome}
    try:
        return desks.get(G.desktop)()
    except:
        return _generic()


def get_mime_type(path):
    return str(Mime.get_type(path))


def maybe_execute(fileinfo, execute=False, urllist=None):
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
        mimetype = get_mime_type(filepath)
        if mimetype in G.EXECUTABLES:
            if execute:
                path = fileinfo.absolutePath()
                if path in os.getenv("PATH", os.defpath):
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
                return entry
            elif tryex:
                xec = parse_exec_line(entry, urllist=urllist)
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


def launch(fileinfo, urllist=None):
    fileinfo.refresh()
    filename = fileinfo.absoluteFilePath()
    if fileinfo.isDir():
        url = QtCore.QUrl.fromUserInput(filename)
        QtGui.QDesktopServices.openUrl(url)
        return
    elif not maybe_execute(fileinfo, execute=True, urllist=urllist):
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

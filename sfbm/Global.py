"""They're not global variables; they're in the cloud!"""

App = None
settings = None
bold_font = None
model = None
settings = None
prefs_dialog = None
item_context_menu = None
systray = None
drag_start_position = None
drag_start_action = None
icon_provider = None
abort = False
populating = False
terminal = None
desktop = ""
icon_theme = "oxygen"
icon_cache = {}

EXECUTABLES = {"application/x-executable",
               "application/executable",
               "text/x-shellscript",
               "application/x-shellscript"}

default_options = {"ShowHidden": False,
                   "DirsFirst": True,
                   "IncludePrevious": False,
                   "Flatten": False}

"""
panels.py - console, project browser, asset tree
pyimgui 1.x compatible
"""

import time
import imgui
from editor.imgui_compat import (
    TREE_NODE_OPEN_ON_ARROW, TREE_NODE_SPAN_AVAIL_WIDTH, TREE_NODE_LEAF,
)


# ── log 

class LogEntry:
    __slots__ = ("time_str", "kind", "text")
    def __init__(self, kind, text):
        self.time_str = time.strftime("%H:%M:%S")
        self.kind = kind
        self.text = text.lower()

_LOG = []
_auto_scroll = True

def log_info(msg):  _LOG.append(LogEntry("info",  msg))
def log_warn(msg):  _LOG.append(LogEntry("warn",  msg))
def log_error(msg): _LOG.append(LogEntry("error", msg))
def log_ok(msg):    _LOG.append(LogEntry("ok",    msg))
def log_clear():    _LOG.clear()

_KIND_COLORS = {
    "ok":    (0.27, 0.67, 0.40, 1.0),
    "warn":  (0.80, 0.65, 0.25, 1.0),
    "error": (0.80, 0.27, 0.27, 1.0),
    "info":  (0.70, 0.72, 0.75, 1.0),
}


def draw_console():
    global _auto_scroll

    if imgui.button("clear"):
        log_clear()
    imgui.same_line()
    _, _auto_scroll = imgui.checkbox("auto-scroll", _auto_scroll)
    imgui.separator()

    imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, 0.11, 0.11, 0.11, 1.0)
    imgui.begin_child("console_body", height=0, border=False)
    imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (4, 1))

    for entry in _LOG:
        r, g, b, a = _KIND_COLORS.get(entry.kind, _KIND_COLORS["info"])
        imgui.push_style_color(imgui.COLOR_TEXT, r, g, b, a)
        imgui.text(f"[{entry.time_str}]  {entry.text}")
        imgui.pop_style_color()

    # auto-scroll: skip — set_scroll_here varies too much across pyimgui versions

    imgui.pop_style_var()
    imgui.end_child()
    imgui.pop_style_color()


# ── project browser 

_PROJECT_ITEMS = [
    ("SCN", "main.psscene"),
    ("PY",  "player.py"),
    ("PY",  "enemy.py"),
    ("PY",  "game_manager.py"),
    ("IMG", "texture_diffuse.png"),
    ("MAT", "mat_player"),
    ("MAT", "mat_ground"),
    ("OBJ", "cube.obj"),
    ("OBJ", "terrain.obj"),
    ("OBJ", "tree.obj"),
    ("AUD", "bgm.ogg"),
    ("AUD", "jump.wav"),
    ("SHD", "unlit.glsl"),
    ("SHD", "pbr.glsl"),
    ("DIR", "prefabs"),
    ("DIR", "animations"),
]

_selected_proj = None


def draw_project():
    global _selected_proj

    imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, 0.83, 0.82, 0.80, 1.0)
    imgui.begin_child("proj_path", height=18, border=False)
    imgui.text_disabled("assets / scenes / main")
    imgui.end_child()
    imgui.pop_style_color()

    imgui.separator()

    # pyimgui: get_content_region_available() returns (w, h)
    avail_w = imgui.get_content_region_available()[0]
    cols = max(1, int(avail_w / 72))
    imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (6, 6))

    for i, (icon, name) in enumerate(_PROJECT_ITEMS):
        if i % cols != 0:
            imgui.same_line()

        selected = (_selected_proj == name)
        if selected:
            imgui.push_style_color(imgui.COLOR_BUTTON, 0.196, 0.361, 0.620, 1.0)
            imgui.push_style_color(imgui.COLOR_TEXT,   1.0,   1.0,   1.0,   1.0)

        imgui.push_id(str(i))
        imgui.begin_group()
        label = f"{icon}\n{name[:7]}"
        if imgui.button(label, width=54, height=42):
            _selected_proj = name
        imgui.end_group()
        imgui.pop_id()

        if selected:
            imgui.pop_style_color(2)

    imgui.pop_style_var()


# ── asset tree 

_ASSET_TREE = [
    ("assets", [
        ("scenes",    []),
        ("scripts",   []),
        ("textures",  []),
        ("materials", []),
        ("meshes",    []),
        ("audio",     []),
        ("shaders",   []),
        ("prefabs",   []),
    ]),
]


def draw_assets():
    imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (2, 1))
    _draw_tree(_ASSET_TREE)
    imgui.pop_style_var()


def _draw_tree(nodes):
    for name, children in nodes:
        if children:
            # internal node: tree_node pushes ID, needs tree_pop when expanded
            expanded = imgui.tree_node(f"[d] {name}", TREE_NODE_OPEN_ON_ARROW)
            if expanded:
                _draw_tree(children)
                imgui.tree_pop()
        else:
            # leaf: NO_TREE_PUSH_ON_OPEN so tree_pop is never needed
            imgui.tree_node(f"    {name}", TREE_NODE_LEAF | TREE_NODE_NO_TREE_PUSH_ON_OPEN)

"""
file_explorer.py - project file browser with icon thumbnails
shows folders/files from the project/ directory
icons loaded from assets/icons/: folder.png model.png image.png music.png list.png script.png
"""

import os
import imgui

# ── paths 

_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "project"
)
_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "icons"
)

# ── icon mapping by extension / type 

_EXT_MAP = {
    # models
    ".obj": "model", ".fbx": "model", ".gltf": "model", ".glb": "model",
    ".dae": "model", ".stl": "model", ".ply": "model",
    # images
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".bmp": "image",
    ".tga": "image", ".tiff": "image", ".webp": "image", ".hdr": "image",
    # audio
    ".ogg": "music", ".wav": "music", ".mp3": "music", ".flac": "music",
    ".aac": "music", ".m4a": "music",
    # scripts
    ".py": "script",
    # lists / data
    ".json": "list", ".xml": "list", ".csv": "list", ".yaml": "list",
    ".yml": "list", ".toml": "list", ".txt": "list",
    # scenes
    ".psscene": "list", ".scene": "list",
}

# ── texture cache 

_tex_cache = {}   # icon_name -> gl_texture_id or None

ICON_SIZE = 48    # display size in pixels
ITEM_W    = 72    # total cell width


def _load_icon(name):
    """load icon PNG from assets/icons/, cache and return gl texture id or None"""
    if name in _tex_cache:
        return _tex_cache[name]

    path = os.path.join(_ICONS_DIR, f"{name}.png")
    if not os.path.exists(path):
        _tex_cache[name] = None
        return None

    try:
        from PIL import Image
        import ctypes
        import OpenGL.GL as gl

        img  = Image.open(path).convert("RGBA").resize((ICON_SIZE, ICON_SIZE))
        data = img.tobytes()

        tid = ctypes.c_uint(0)
        gl.glGenTextures(1, ctypes.byref(tid))
        gl.glBindTexture(gl.GL_TEXTURE_2D, tid.value)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, ICON_SIZE, ICON_SIZE,
                        0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, data)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

        _tex_cache[name] = tid.value
        return tid.value

    except Exception as e:
        _tex_cache[name] = None
        return None


def _icon_for(path):
    """return icon name string for a given path"""
    if os.path.isdir(path):
        return "folder"
    ext = os.path.splitext(path)[1].lower()
    return _EXT_MAP.get(ext, "list")


# ── state ─

_cwd        = _ROOT          # current directory being browsed
_selected   = None           # currently selected path
_history    = []             # breadcrumb stack


def _ensure_root():
    global _cwd
    if not os.path.isdir(_cwd):
        os.makedirs(_ROOT, exist_ok=True)
        _cwd = _ROOT


# ── draw 

def draw_file_explorer():
    global _cwd, _selected

    _ensure_root()

    # ── breadcrumb bar ──
    imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, 0.78, 0.77, 0.75, 1.0)
    imgui.begin_child("##fe_crumb", height=22, border=False)
    imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (4, 2))

    # build crumb parts relative to project root parent
    try:
        rel = os.path.relpath(_cwd, os.path.dirname(_ROOT))
    except ValueError:
        rel = _cwd
    parts = rel.replace("\\", "/").split("/")

    # reconstruct paths for each crumb
    base = os.path.dirname(_ROOT)
    crumb_paths = []
    cur = base
    for p in parts:
        cur = os.path.join(cur, p)
        crumb_paths.append((p, cur))

    for i, (label, path) in enumerate(crumb_paths):
        if i: imgui.same_line(spacing=2); imgui.text_disabled(">"); imgui.same_line(spacing=2)
        if imgui.small_button(label):
            if os.path.isdir(path):
                _history.append(_cwd)
                _cwd = path

    imgui.pop_style_var()
    imgui.end_child()
    imgui.pop_style_color()

    imgui.separator()

    # ── file grid ──
    imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, 0.84, 0.83, 0.81, 1.0)
    imgui.begin_child("##fe_grid", height=0, border=False)

    try:
        entries = sorted(os.listdir(_cwd),
                         key=lambda n: (not os.path.isdir(os.path.join(_cwd, n)), n.lower()))
    except PermissionError:
        imgui.text_disabled("  permission denied")
        imgui.end_child()
        imgui.pop_style_color()
        return

    avail_w = imgui.get_content_region_available()[0]
    cols = max(1, int(avail_w / (ITEM_W + 8)))

    imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (6, 6))

    col = 0
    for name in entries:
        if name.startswith("."): continue   # hide hidden files

        full_path  = os.path.join(_cwd, name)
        icon_name  = _icon_for(full_path)
        tex_id     = _load_icon(icon_name)
        is_dir     = os.path.isdir(full_path)
        is_sel     = (full_path == _selected)

        # wrap columns
        if col > 0 and col % cols != 0:
            imgui.same_line()

        imgui.push_id(name)
        imgui.begin_group()

        # highlight selected
        if is_sel:
            imgui.push_style_color(imgui.COLOR_BUTTON,         0.196, 0.361, 0.620, 0.5)
            imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.294, 0.459, 0.718, 0.6)
        else:
            imgui.push_style_color(imgui.COLOR_BUTTON,         0.0, 0.0, 0.0, 0.0)
            imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.3, 0.3, 0.3, 0.15)

        imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (0, 0))

        if tex_id is not None:
            # clickable image button
            clicked = imgui.image_button(tex_id, ICON_SIZE, ICON_SIZE)
        else:
            # fallback: colored text button
            _fallback_colors = {
                "folder": (0.85, 0.70, 0.25, 1.0),
                "model":  (0.40, 0.75, 0.95, 1.0),
                "image":  (0.60, 0.90, 0.50, 1.0),
                "music":  (0.90, 0.50, 0.85, 1.0),
                "script": (0.85, 0.75, 1.00, 1.0),
                "list":   (0.75, 0.75, 0.75, 1.0),
            }
            fc = _fallback_colors.get(icon_name, (0.8, 0.8, 0.8, 1.0))
            imgui.push_style_color(imgui.COLOR_BUTTON, *fc)
            clicked = imgui.button(f"  {icon_name[:3].upper()}  ",
                                   width=ICON_SIZE, height=ICON_SIZE)
            imgui.pop_style_color()

        imgui.pop_style_var()
        imgui.pop_style_color(2)

        if clicked:
            if is_dir and full_path == _selected:
                # double-click behaviour: navigate on second click
                _history.append(_cwd)
                _cwd = full_path
                _selected = None
            else:
                _selected = full_path

        # double-click to open folder
        if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0):
            if is_dir:
                _history.append(_cwd)
                _cwd = full_path
                _selected = None

        # label below icon — truncate long names
        short = name if len(name) <= 9 else name[:8] + "…"
        label_w = imgui.calc_text_size(short)[0]
        imgui.set_cursor_pos_x(imgui.get_cursor_pos()[0] + max(0, (ITEM_W - label_w) / 2))
        imgui.text(short)

        if imgui.is_item_hovered() and len(name) > 9:
            imgui.set_tooltip(name)

        imgui.end_group()
        imgui.pop_id()

        col += 1

    imgui.pop_style_var()
    imgui.end_child()
    imgui.pop_style_color()

    # ── back on right-click empty space ──
    if imgui.begin_popup_context_window("##fe_ctx"):
        if _history and imgui.menu_item("← back")[0]:
            _cwd = _history.pop()
            _selected = None
        if imgui.menu_item("new folder")[0]:
            new_dir = os.path.join(_cwd, "new_folder")
            os.makedirs(new_dir, exist_ok=True)
        imgui.end_popup()

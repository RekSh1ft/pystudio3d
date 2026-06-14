import editor.fonts as fonts
"""
script_editor.py - functional in-editor python script editor
create, edit, save, and hot-reload scripts attached to game objects
"""

import os
import sys
import importlib
import importlib.util
import traceback
import imgui
from editor.panels import log_info, log_warn, log_error, log_ok
from editor.imgui_compat import WINDOW_FIXED, WINDOW_NO_SCROLLBAR

# ── script icon texture 
_script_icon_tex = [None]   # [gl_texture_id] loaded once

def _load_script_icon():
    if _script_icon_tex[0] is not None:
        return _script_icon_tex[0]
    import os, ctypes
    icon_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets", "icons", "script.png"
    )
    if not os.path.exists(icon_path):
        return None
    try:
        from PIL import Image
        import moderngl
        img = Image.open(icon_path).convert("RGBA").resize((48, 48))
        data = img.tobytes()
        # upload as opengl texture using ctypes
        import ctypes
        tex_id = ctypes.c_uint(0)
        import OpenGL.GL as gl
        gl.glGenTextures(1, ctypes.byref(tex_id))
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_id.value)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, 48, 48, 0,
                        gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, data)
        _script_icon_tex[0] = tex_id.value
        return tex_id.value
    except Exception as e:
        log_warn(f"script icon load failed: {e}")
        return None

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "scripts")

# ── script template 

TEMPLATE = '''# {name}.py  —  pystudio3d script
# attach to a gameobject via the script component

class {classname}:
    """
    lifecycle methods:
      start(obj)        called once when play mode begins
      update(obj, dt)   called every frame (dt = seconds since last frame)
      on_destroy(obj)   called when the object is destroyed
    """

    def start(self, obj):
        # runs once at play start
        pass

    def update(self, obj, dt):
        # runs every frame
        # obj.transform.position[0] += 1.0 * dt  # move right
        pass

    def on_destroy(self, obj):
        pass
'''

# ── state 

_open_files  = {}   # path -> {"text": str, "dirty": bool, "module": module|None}
_active_file = None  # currently viewed path
_new_name_buf = [""]
_show_new_dialog = [False]
_loaded_modules  = {}   # path -> module


def ensure_scripts_dir():
    os.makedirs(SCRIPTS_DIR, exist_ok=True)


def list_scripts():
    ensure_scripts_dir()
    return sorted(
        f for f in os.listdir(SCRIPTS_DIR)
        if f.endswith(".py")
    )


def open_script(filename):
    global _active_file
    ensure_scripts_dir()
    path = os.path.join(SCRIPTS_DIR, filename)
    if path not in _open_files:
        if os.path.exists(path):
            with open(path, "r") as f:
                text = f.read()
        else:
            text = ""
        _open_files[path] = {"text": text, "dirty": False, "module": None}
    _active_file = path
    log_info(f"opened {filename}")


def new_script(name):
    ensure_scripts_dir()
    if not name.endswith(".py"):
        name += ".py"
    classname = "".join(w.capitalize() for w in name.replace(".py","").split("_"))
    path = os.path.join(SCRIPTS_DIR, name)
    text = TEMPLATE.format(name=name.replace(".py",""), classname=classname)
    with open(path, "w") as f:
        f.write(text)
    _open_files[path] = {"text": text, "dirty": False, "module": None}
    global _active_file
    _active_file = path
    log_ok(f"created {name}")
    return name


def save_script(path):
    entry = _open_files.get(path)
    if not entry:
        return
    with open(path, "w") as f:
        f.write(entry["text"])
    entry["dirty"] = False
    log_ok(f"saved {os.path.basename(path)}")


def reload_script(path):
    """compile & load script module, return instance or None"""
    entry = _open_files.get(path)
    if not entry:
        return None
    try:
        spec = importlib.util.spec_from_file_location("user_script", path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        entry["module"] = mod
        _loaded_modules[path] = mod
        log_ok(f"reloaded {os.path.basename(path)}")
        return mod
    except Exception:
        log_error(f"error in {os.path.basename(path)}:\n{traceback.format_exc()}")
        return None


def get_script_instance(path, classname=None):
    """get an instance of the first class defined in the script"""
    mod = _loaded_modules.get(path)
    if mod is None:
        mod = reload_script(path)
    if mod is None:
        return None
    # find the user class (first class that isn't a builtin)
    import inspect
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if obj.__module__ == mod.__name__ or True:
            try:
                return obj()
            except:
                pass
    return None


# ── draw 

def draw(scene):
    global _active_file

    avail = imgui.get_content_region_available()
    total_w = avail[0]
    sidebar_w = 160
    editor_w  = max(4, total_w - sidebar_w - 4)

    # ── sidebar: file list ──
    imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, 0.72, 0.71, 0.68, 1.0)
    imgui.begin_child("script_sidebar", width=sidebar_w, height=0, border=True)

    imgui.text("scripts")
    imgui.separator()

    if imgui.button("+ new script", width=sidebar_w - 12):
        _show_new_dialog[0] = True

    imgui.spacing()

    for fname in list_scripts():
        path = os.path.join(SCRIPTS_DIR, fname)
        is_active = (path == _active_file)
        dirty = _open_files.get(path, {}).get("dirty", False)
        label = ("* " if dirty else "  ") + fname
        if is_active:
            imgui.push_style_color(imgui.COLOR_HEADER, 0.196, 0.361, 0.620, 1.0)
            imgui.push_style_color(imgui.COLOR_TEXT,   1.0,   1.0,   1.0,   1.0)
        selected, _ = imgui.selectable(label, is_active)
        if is_active:
            imgui.pop_style_color(2)
        if selected:
            open_script(fname)

        # right-click: attach to selected object
        if imgui.begin_popup_context_item(f"##sc_{fname}"):
            if imgui.menu_item("attach to selected")[0] and scene.selected:
                from scene.scene import ScriptComponent
                sc = ScriptComponent(fname.replace(".py",""))
                sc.script_file = path
                scene.selected.add_component(sc)
                log_info(f"attached {fname} to {scene.selected.name}")
            if imgui.menu_item("delete")[0]:
                try:
                    os.remove(path)
                    if path in _open_files: del _open_files[path]
                    if _active_file == path: _active_file = None
                    log_info(f"deleted {fname}")
                except Exception as e:
                    log_error(str(e))
            imgui.end_popup()

    imgui.end_child()
    imgui.pop_style_color()

    imgui.same_line()

    # ── editor pane ──
    imgui.begin_child("script_editor_pane", width=editor_w, height=0, border=True)

    if _active_file and _active_file in _open_files:
        entry = _open_files[_active_file]
        fname = os.path.basename(_active_file)

        # toolbar
        if imgui.button("save"):
            save_script(_active_file)
        imgui.same_line()
        if imgui.button("save & reload"):
            save_script(_active_file)
            reload_script(_active_file)
        imgui.same_line()
        if imgui.button("run now"):
            save_script(_active_file)
            reload_script(_active_file)
            if scene.selected:
                _run_script_on_object(_active_file, scene.selected)
        imgui.same_line()
        dirty_marker = " *" if entry["dirty"] else ""
        imgui.text_disabled(f"  {fname}{dirty_marker}")

        imgui.separator()

        # text editor — multiline input with code font
        fonts.push_code_font()
        imgui.push_style_color(imgui.COLOR_FRAME_BACKGROUND, 0.13, 0.13, 0.17, 1.0)
        imgui.push_style_color(imgui.COLOR_TEXT, 0.85, 0.90, 0.80, 1.0)
        edit_h = imgui.get_content_region_available()[1] - 4
        changed, new_text = imgui.input_text_multiline(
            "##code",
            entry["text"],
            2**16,
            width=-1,
            height=edit_h,
        )
        imgui.pop_style_color(2)
        fonts.pop_code_font()
        if changed:
            entry["text"] = new_text
            entry["dirty"] = True
    else:
        imgui.text_disabled("  no script open")
        imgui.text_disabled("  select a script from the sidebar")
        imgui.text_disabled("  or click '+ new script'")

    imgui.end_child()

    # ── new script dialog ──
    if _show_new_dialog[0]:
        imgui.open_popup("##new_script_dlg")
        _show_new_dialog[0] = False

    if imgui.begin_popup_modal("##new_script_dlg")[0]:
        # left side: script icon
        icon = _load_script_icon()
        if icon is not None:
            imgui.image(icon, 48, 48)
        else:
            # fallback placeholder box
            imgui.push_style_color(imgui.COLOR_BUTTON, 0.25, 0.18, 0.38, 1.0)
            imgui.button("{ }", width=48, height=48)
            imgui.pop_style_color()
        imgui.same_line(spacing=12)

        # right side: name input + buttons
        imgui.begin_group()
        imgui.text("new script name:")
        imgui.push_item_width(200)
        entered, _new_name_buf[0] = imgui.input_text("##nsname", _new_name_buf[0], 64)
        imgui.pop_item_width()
        if imgui.button("create") or (entered and imgui.is_key_pressed(257)):
            name = _new_name_buf[0].strip()
            if name:
                new_script(name)
                _new_name_buf[0] = ""
                imgui.close_current_popup()
        imgui.same_line()
        if imgui.button("cancel"):
            _new_name_buf[0] = ""
            imgui.close_current_popup()
        imgui.end_group()

        imgui.end_popup()


def _run_script_on_object(path, obj):
    """call start() on the script with the given object"""
    try:
        mod = reload_script(path)
        if mod is None:
            return
        import inspect
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            instance = cls()
            if hasattr(instance, "start"):
                instance.start(obj)
                log_ok(f"ran {os.path.basename(path)}.start() on {obj.name}")
            break
    except Exception:
        log_error(traceback.format_exc())

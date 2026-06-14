"""
app.py - pystudio3d main application
"""

import time
import glfw
import imgui
import moderngl as mgl

from editor.theme import apply_theme
from editor.imgui_compat import WINDOW_FIXED, WINDOW_MENU_BAR, WINDOW_NO_SCROLLBAR
from editor import hierarchy, inspector
from editor.panels import draw_console, draw_project, draw_assets, log_info, log_warn, log_ok
from editor.file_explorer import draw_file_explorer
from editor import script_editor
from editor.object_toolbar import (
    draw_insert_bar, runtime_start, runtime_update, runtime_stop
)
from renderer.renderer import Renderer
import editor.fonts as fonts
from renderer.gizmo import TOOL_NONE, TOOL_TRANSLATE, TOOL_ROTATE, TOOL_SCALE
from scene.scene import Scene, GameObject, MeshRenderer, Camera as CamComp


class PyStudio3D:
    LEFT_W   = 210
    RIGHT_W  = 250
    TOP_H    = 148   # menubar + toolbar + insert bar + playbar
    BOTTOM_H = 180
    STATUS_H = 22

    _TOOLS    = ["hand", "move", "rotate", "scale", "rect"]
    _tool_idx = 1
    _TOOL_MODES = [TOOL_NONE, TOOL_TRANSLATE, TOOL_ROTATE, TOOL_SCALE, TOOL_NONE]
    _shading_opts = ["wireframe", "solid", "unlit"]

    def __init__(self, window, impl):
        self.window = window
        self.impl   = impl

        apply_theme()

        self.renderer = Renderer()
        self.renderer.init()

        self.scene = Scene.make_default()

        self.playing    = False
        self.paused     = False
        self.play_time  = 0.0
        self._prev_time = time.time()

        self._vp_fb:  mgl.Framebuffer | None = None
        self._vp_tex: mgl.Texture | None     = None
        self._vp_size = (0, 0)

        self._last_mouse  = (0.0, 0.0)
        self._vp_origin   = (0.0, 0.0)
        self._page        = 'editor'   # 'editor' | 'scripts'
        self._shading_idx = 1

        # snap & transform state
        self._snap    = False
        self._snap_val = 0.25
        self._local_space = False

        log_ok("pystudio3d initialized")
        log_ok(f"opengl: {self.renderer.ctx.info['GL_RENDERER']}")
        log_info("scene loaded: untitled.psscene")
        log_info("scripts dir: assets/scripts/")

    # ── loop 

    def run(self):
        while not glfw.window_should_close(self.window):
            glfw.poll_events()
            self.impl.process_inputs()

            now = time.time()
            dt  = min(now - self._prev_time, 0.1)
            self._prev_time = now

            if self.playing and not self.paused:
                self.play_time += dt
                runtime_update(self.scene, dt)

            imgui.new_frame()
            self._draw_ui()
            imgui.render()

            w, h = glfw.get_framebuffer_size(self.window)
            self.renderer.ctx.screen.use()
            self.renderer.ctx.clear(0.18, 0.18, 0.18)
            self.impl.render(imgui.get_draw_data())
            glfw.swap_buffers(self.window)

    # ── layout 

    def _wsize(self):
        return glfw.get_window_size(self.window)

    def _layout(self):
        ww, wh = self._wsize()
        cx = self.LEFT_W
        cy = self.TOP_H
        cw = max(4, ww - self.LEFT_W - self.RIGHT_W)
        ch = max(4, wh - self.TOP_H - self.BOTTOM_H - self.STATUS_H)
        return ww, wh, cx, cy, cw, ch

    def _draw_ui(self):
        fonts.push_ui_font()
        ww, wh, cx, cy, cw, ch = self._layout()
        if self._page == 'scripts':
            self._draw_script_page(ww, wh)
        else:
            self._draw_topbar(ww)
            self._draw_hierarchy(cy, wh)
            self._draw_inspector(cx + cw, cy, wh)
            self._draw_viewport(cx, cy, cw, ch)
            self._draw_bottom(cx, cy + ch, cw)
            self._draw_statusbar(ww, wh)
        fonts.pop_ui_font()

    # ── top bar 

    def _draw_topbar(self, ww):
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(ww, self.TOP_H)
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (4, 3))
        imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (4, 3))
        imgui.begin("##topbar", flags=WINDOW_FIXED | WINDOW_MENU_BAR)

        if imgui.begin_menu_bar():
            self._menubar()
            imgui.end_menu_bar()

        # ── tool buttons ──
        imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (12, 10))
        for i, label in enumerate(self._TOOLS):
            if i: imgui.same_line()
            active = (i == self._tool_idx)
            if active:
                imgui.push_style_color(imgui.COLOR_BUTTON,         0.196, 0.361, 0.620, 1.0)
                imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.294, 0.459, 0.718, 1.0)
                imgui.push_style_color(imgui.COLOR_TEXT,           1.0,   1.0,   1.0,   1.0)
            if imgui.button(label):
                self._tool_idx = i
                self.renderer.tool = self._TOOL_MODES[i]
            if active: imgui.pop_style_color(3)

        imgui.same_line(spacing=12)
        imgui.text("|")
        imgui.same_line()

        # shading
        imgui.text("shading:")
        imgui.same_line()
        imgui.push_item_width(80)
        changed, self._shading_idx = imgui.combo("##shd", self._shading_idx, self._shading_opts)
        imgui.pop_item_width()
        if changed:
            self.renderer.shading = self._shading_opts[self._shading_idx]

        imgui.same_line()
        _, self.renderer.show_grid   = imgui.checkbox("grid",   self.renderer.show_grid)
        imgui.same_line()
        _, self.renderer.show_gizmos = imgui.checkbox("gizmos", self.renderer.show_gizmos)
        imgui.same_line()
        _, self._snap = imgui.checkbox("snap", self._snap)
        if self._snap:
            imgui.same_line()
            imgui.push_item_width(44)
            _, self._snap_val = imgui.input_float("##snap", self._snap_val, 0.0, 0.0, "%.2f")
            imgui.pop_item_width()
        imgui.same_line()
        _, self._local_space = imgui.checkbox("local", self._local_space)

        # ── script editor button ──
        imgui.same_line(spacing=16)
        imgui.text("|")
        imgui.same_line()
        imgui.push_style_color(imgui.COLOR_BUTTON,         0.25, 0.18, 0.38, 1.0)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.38, 0.28, 0.55, 1.0)
        imgui.push_style_color(imgui.COLOR_TEXT,           0.85, 0.75, 1.0,  1.0)
        if imgui.button("{ } script editor", width=130, height=40):
            self._page = 'scripts'
        imgui.pop_style_color(3)

        imgui.pop_style_var()  # FRAME_PADDING

        # ── insert bar ──
        imgui.separator()
        imgui.push_style_var(imgui.STYLE_FRAME_PADDING, (10, 10))
        draw_insert_bar(self.scene)
        imgui.pop_style_var()

        imgui.separator()

        # ── play bar ──
        btn_w = 72
        avail = imgui.get_content_region_available()[0]
        imgui.set_cursor_pos_x((avail - btn_w * 3 - 8) / 2)

        r, g, b = (0.55, 0.18, 0.18) if self.playing else (0.196, 0.361, 0.620)
        imgui.push_style_color(imgui.COLOR_BUTTON,         r, g, b, 1.0)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, r+0.08, g+0.08, b+0.08, 1.0)
        lbl = "[ ] stop" if self.playing else "> play"
        if imgui.button(lbl, width=btn_w):
            self.playing = not self.playing
            self.paused  = False
            if self.playing:
                self.play_time = 0.0
                runtime_start(self.scene)
                log_info("--- entering play mode ---")
            else:
                runtime_stop(self.scene)
                log_info("--- exiting play mode ---")
        imgui.pop_style_color(2)

        imgui.same_line()
        if self.paused:
            imgui.push_style_color(imgui.COLOR_BUTTON, 0.196, 0.361, 0.620, 1.0)
        if imgui.button("|| pause", width=btn_w):
            if self.playing: self.paused = not self.paused
        if self.paused:
            imgui.pop_style_color()

        imgui.same_line()
        if imgui.button(">| step", width=btn_w) and self.playing:
            runtime_update(self.scene, 1/60)

        imgui.end()
        imgui.pop_style_var(2)

    # ── menubar 

    def _menubar(self):
        if imgui.begin_menu("file"):
            if imgui.menu_item("new scene")[0]:
                if self.playing:
                    runtime_stop(self.scene)
                    self.playing = False
                self.scene = Scene.make_default()
                log_info("new scene")
            if imgui.menu_item("save scene")[0]:
                self._save_scene()
            imgui.separator()
            if imgui.menu_item("build & run")[0]:
                log_warn("build system coming soon")
            imgui.separator()
            if imgui.menu_item("exit")[0]:
                glfw.set_window_should_close(self.window, True)
            imgui.end_menu()

        if imgui.begin_menu("edit"):
            if imgui.menu_item("duplicate  ctrl+d")[0] and self.scene.selected:
                from editor.object_toolbar import _duplicate
                _duplicate(self.scene, self.scene.selected)
            if imgui.menu_item("delete  del")[0] and self.scene.selected:
                self.scene.delete_object(self.scene.selected)
            imgui.separator()
            imgui.menu_item("preferences...")
            imgui.end_menu()

        if imgui.begin_menu("gameobject"):
            if imgui.menu_item("create empty")[0]:
                obj = GameObject("game object")
                self.scene.add_object(obj)
                self.scene.selected = obj
            if imgui.begin_menu("3d object"):
                for mesh in ["cube","sphere","plane","cylinder","capsule"]:
                    if imgui.menu_item(mesh)[0]:
                        obj = GameObject(mesh)
                        mr  = MeshRenderer(); mr.mesh_name = mesh
                        obj.add_component(mr)
                        self.scene.add_object(obj)
                        self.scene.selected = obj
                imgui.end_menu()
            if imgui.menu_item("point light")[0]:
                from editor.object_toolbar import _create_light
                _create_light(self.scene, "point", 1)
            if imgui.menu_item("camera")[0]:
                from editor.object_toolbar import _create_camera
                _create_camera(self.scene)
            imgui.end_menu()

        if imgui.begin_menu("scripts"):
            if imgui.menu_item("new script")[0]:
                script_editor._show_new_dialog[0] = True
            imgui.separator()
            from editor.script_editor import list_scripts, open_script
            for fname in list_scripts():
                if imgui.menu_item(fname)[0]:
                    open_script(fname)
            imgui.end_menu()

        if imgui.begin_menu("help"):
            imgui.menu_item("about pystudio3d")
            imgui.end_menu()

    # ── keyboard shortcuts 

    def _handle_keys(self):
        io = imgui.get_io()
        if io.keys_down[127] and self.scene.selected:  # Delete
            self.scene.delete_object(self.scene.selected)

    # ── hierarchy 

    def _draw_hierarchy(self, cy, wh):
        h = wh - cy - self.STATUS_H
        imgui.set_next_window_position(0, cy)
        imgui.set_next_window_size(self.LEFT_W, h)
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (4, 4))
        imgui.begin("hierarchy", flags=WINDOW_FIXED & ~WINDOW_NO_SCROLLBAR)
        hierarchy.draw(self.scene)
        imgui.end()
        imgui.pop_style_var()

    # ── inspector 

    def _draw_inspector(self, x, cy, wh):
        h = wh - cy - self.STATUS_H
        imgui.set_next_window_position(x, cy)
        imgui.set_next_window_size(self.RIGHT_W, h)
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (4, 4))
        imgui.begin("inspector", flags=WINDOW_FIXED & ~WINDOW_NO_SCROLLBAR)
        inspector.draw(self.scene)
        imgui.end()
        imgui.pop_style_var()

    # ── viewport 

    def _draw_viewport(self, cx, cy, cw, ch):
        imgui.set_next_window_position(cx, cy)
        imgui.set_next_window_size(cw, ch)
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (0, 0))
        imgui.begin("scene##vp", flags=WINDOW_FIXED)

        avail = imgui.get_content_region_available()
        w, h  = int(avail[0]), int(avail[1])

        if w > 4 and h > 4:
            if (w, h) != self._vp_size:
                self._rebuild_fb(w, h)

            self._vp_fb.use()
            self.renderer.render(w, h, self.scene)
            self.renderer.ctx.screen.use()

            cursor_ss = imgui.get_cursor_screen_pos()
            self._vp_origin = cursor_ss
            imgui.image(self._vp_tex.glo, w, h, uv0=(0, 1), uv1=(1, 0))

            if imgui.is_item_hovered():
                self._handle_mouse()

            if self.playing:
                dl = imgui.get_window_draw_list()
                dl.add_text(
                    cursor_ss[0] + 8, cursor_ss[1] + 8,
                    imgui.get_color_u32_rgba(0.27, 0.85, 0.45, 1.0),
                    f"playing  {self.play_time:.1f}s",
                )

        imgui.end()
        imgui.pop_style_var()

    def _rebuild_fb(self, w, h):
        ctx = self.renderer.ctx
        if self._vp_tex: self._vp_tex.release()
        if self._vp_fb:  self._vp_fb.release()
        self._vp_tex = ctx.texture((w, h), 4)
        depth = ctx.depth_renderbuffer((w, h))
        self._vp_fb = ctx.framebuffer(
            color_attachments=[self._vp_tex], depth_attachment=depth)
        self._vp_size = (w, h)

    def _handle_mouse(self):
        io     = imgui.get_io()
        mx, my = io.mouse_pos
        dx = mx - self._last_mouse[0]
        dy = my - self._last_mouse[1]
        self._last_mouse = (mx, my)

        vp_w, vp_h = self._vp_size
        gizmo = self.renderer.gizmo
        view  = self.renderer._last_view
        proj  = self.renderer._last_proj
        eye   = self.renderer._last_eye
        tool  = self.renderer.tool
        obj   = self.scene.selected

        # ── gizmo drag ──
        if (view is not None and obj is not None
                and tool != TOOL_NONE and not self.playing):

            lx = mx - self._vp_origin[0]
            ly = my - self._vp_origin[1]

            if gizmo.dragging:
                # continue drag
                if imgui.is_mouse_down(0):
                    gizmo.update_drag(obj, lx, ly, vp_w, vp_h, view, proj)
                    # camera blocked while dragging
                    if io.mouse_wheel:
                        self.renderer.zoom(io.mouse_wheel)
                    return
                else:
                    gizmo.end_drag()
            else:
                # always update hover so axis highlights as soon as mouse is over it
                gizmo.update_hover(obj, tool, lx, ly, vp_w, vp_h, view, proj, eye)

                # start drag the moment mouse goes down on a highlighted axis
                if imgui.is_mouse_down(0) and gizmo.active_axis >= 0:
                    gizmo.try_begin_drag(
                        obj, tool, lx, ly, vp_w, vp_h, view, proj, eye)

        # ── camera controls (only when no gizmo axis is active) ──
        if not gizmo.dragging:
            if imgui.is_mouse_down(0) and gizmo.active_axis < 0:
                self.renderer.orbit(dx, dy)
            if imgui.is_mouse_down(2):
                self.renderer.pan(dx, dy)
        if io.mouse_wheel:
            self.renderer.zoom(io.mouse_wheel)

    # ── bottom panel 

    def _draw_bottom(self, cx, y, cw):
        imgui.set_next_window_position(cx, y)
        imgui.set_next_window_size(cw, self.BOTTOM_H)
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (4, 4))
        imgui.begin("##bottom", flags=WINDOW_FIXED)

        if imgui.begin_tab_bar("btabs"):
            if imgui.begin_tab_item("files")[0]:
                draw_file_explorer()
                imgui.end_tab_item()
            if imgui.begin_tab_item("console")[0]:
                draw_console()
                imgui.end_tab_item()
            if imgui.begin_tab_item("project")[0]:
                draw_project()
                imgui.end_tab_item()
            if imgui.begin_tab_item("assets")[0]:
                draw_assets()
                imgui.end_tab_item()
            imgui.end_tab_bar()

        imgui.end()
        imgui.pop_style_var()

    # ── script editor page

    def _draw_script_page(self, ww, wh):
        """full-window script editor page"""
        TOPBAR_H = 34
        STATUS_H = self.STATUS_H

        # ── top bar ──
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(ww, TOPBAR_H)
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (8, 6))
        imgui.begin("##script_topbar", flags=WINDOW_FIXED)

        imgui.push_style_color(imgui.COLOR_BUTTON,         0.196, 0.361, 0.620, 1.0)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.294, 0.459, 0.718, 1.0)
        if imgui.button("< back to editor"):
            self._page = 'editor'
        imgui.pop_style_color(2)

        imgui.same_line(spacing=16)
        imgui.text("|")
        imgui.same_line(spacing=16)
        imgui.push_style_color(imgui.COLOR_TEXT, 0.85, 0.75, 1.0, 1.0)
        imgui.text("{ }  script editor")
        imgui.pop_style_color()
        imgui.same_line(spacing=16)
        imgui.text_disabled("— create, edit and attach python scripts to game objects")

        imgui.end()
        imgui.pop_style_var()

        # ── main script editor area ──
        editor_h = wh - TOPBAR_H - STATUS_H
        imgui.set_next_window_position(0, TOPBAR_H)
        imgui.set_next_window_size(ww, editor_h)
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (6, 6))
        imgui.begin("##script_body", flags=WINDOW_FIXED)
        script_editor.draw(self.scene)
        imgui.end()
        imgui.pop_style_var()

        # ── status bar ──
        self._draw_statusbar(ww, wh)

    # ── status bar 

    def _draw_statusbar(self, ww, wh):
        y = wh - self.STATUS_H
        imgui.set_next_window_position(0, y)
        imgui.set_next_window_size(ww, self.STATUS_H)
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (6, 3))
        imgui.begin("##status", flags=WINDOW_FIXED)

        n = sum(1 for _ in self._all_objects(self.scene.root_objects))
        sel = self.scene.selected.name if self.scene.selected else "none"

        if self.playing:
            imgui.text_colored("  playing", 0.27, 0.85, 0.45, 1.0)
        else:
            imgui.text_colored("  ready",   0.27, 0.67, 0.40, 1.0)
        imgui.same_line()
        imgui.text_disabled(f"  |  objects: {n}  |  selected: {sel}  |  vp: {self._vp_size[0]}x{self._vp_size[1]}  |  python  moderngl  pyimgui")

        imgui.end()
        imgui.pop_style_var()

    def _all_objects(self, objs):
        for o in objs:
            yield o
            yield from self._all_objects(o.children)

    def _save_scene(self):
        import json, os
        data = {"name": self.scene.name, "objects": []}
        for obj in self._all_objects(self.scene.root_objects):
            t = obj.transform
            data["objects"].append({
                "id": obj.id, "name": obj.name,
                "position": t.position, "rotation": t.rotation, "scale": t.scale,
                "components": [c.name for c in obj.components]
            })
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", f"{self.scene.name}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        log_ok(f"scene saved: {path}")

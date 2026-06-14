"""
pystudio3d main
"""

import sys
import glfw
import imgui
from imgui.integrations.glfw import GlfwRenderer
from editor.app import PyStudio3D
import editor.fonts as fonts


def main():
    if not glfw.init():
        print("failed to initialize glfw")
        sys.exit(1)

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)

    window = glfw.create_window(1400, 860, "pystudio3d", None, None)
    if not window:
        glfw.terminate()
        print("failed to create glfw window")
        sys.exit(1)

    glfw.make_context_current(window)
    glfw.swap_interval(1)

    imgui.create_context()

    # load fonts BEFORE creating the renderer (which calls new_frame)
    fonts.ui_font, fonts.code_font = fonts.load_fonts()

    impl = GlfwRenderer(window, attach_callbacks=False)
    glfw.set_key_callback(window, impl.keyboard_callback)
    glfw.set_cursor_pos_callback(window, impl.mouse_callback)
    glfw.set_mouse_button_callback(window, impl.mouse_callback)
    glfw.set_scroll_callback(window, impl.scroll_callback)
    glfw.set_window_size_callback(window, impl.resize_callback)

    app = PyStudio3D(window, impl)
    app.run()

    impl.shutdown()
    glfw.terminate()


if __name__ == "__main__":
    main()

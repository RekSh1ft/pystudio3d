"""
fonts.py - font loading for pystudio3d
Searches in order:
  1. assets/fonts/ (bundled fonts, run get_fonts.py to populate)
  2. Windows system fonts (C:/Windows/Fonts/)
  3. macOS system fonts
  4. imgui default bitmap font
"""

import os
import sys
import imgui

# paths relative to this file
_ASSETS_FONTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "fonts"
)

# preferred fonts in order of preference
# solute.ttf is the custom bundled font — checked first
_UI_FONTS = [
    "solute.ttf",
    "Inter-Regular.otf",
    "Inter-Regular.ttf",
    "Segoe UI.ttf",
    "SegoeUI.ttf",
    "Roboto-Regular.ttf",
    "Ubuntu-R.ttf",
    "Arial.ttf",
    "Helvetica.ttf",
    "DejaVuSans.ttf",
]

_CODE_FONTS = [
    "solute.ttf",            # use solute for code editor too if nothing better found
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Regular.otf",
    "CascadiaCode.ttf",
    "CascadiaMono.ttf",
    "FiraCode-Regular.ttf",
    "Consolas.ttf",
    "CourierNew.ttf",
    "DejaVuSansMono.ttf",
    "LiberationMono-Regular.ttf",
]

_SEARCH_DIRS = [
    _ASSETS_FONTS,
    r"C:\Windows\Fonts",
    os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"),
    "/Library/Fonts",
    "/System/Library/Fonts",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts",
]


def _find(candidates):
    for name in candidates:
        for d in _SEARCH_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    return None


def load_fonts():
    """
    Call after imgui.create_context() and before the first new_frame().
    Returns (ui_font, code_font) — either may be None (= imgui default).
    """
    io = imgui.get_io()
    fonts = io.fonts

    ui_path   = _find(_UI_FONTS)
    code_path = _find(_CODE_FONTS)

    ui_font   = None
    code_font = None

    if ui_path:
        try:
            ui_font = fonts.add_font_from_file_ttf(ui_path, 14.0)
            print(f"[fonts] ui:   {os.path.basename(ui_path)}")
        except Exception as e:
            print(f"[fonts] ui font failed ({e}), using default")
            ui_font = None
    else:
        print("[fonts] ui: no font found, using imgui default")

    if code_path:
        try:
            code_font = fonts.add_font_from_file_ttf(code_path, 13.0)
            print(f"[fonts] code: {os.path.basename(code_path)}")
        except Exception as e:
            print(f"[fonts] code font failed ({e}), using default")
            code_font = None
    else:
        print("[fonts] code: no font found, using imgui default")

    return ui_font, code_font


# module-level handles set after load_fonts() is called
ui_font   = None
code_font = None

def push_ui_font():
    if ui_font: imgui.push_font(ui_font)

def pop_ui_font():
    if ui_font: imgui.pop_font()

def push_code_font():
    if code_font: imgui.push_font(code_font)

def pop_code_font():
    if code_font: imgui.pop_font()

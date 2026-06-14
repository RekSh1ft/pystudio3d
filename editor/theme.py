"""
pystudio3d theme 
"""

import imgui


def apply_theme():
    style = imgui.get_style()

    # flat / squared like win xp - no rounding
    style.window_rounding    = 0.0
    style.child_rounding     = 0.0
    style.frame_rounding     = 0.0
    style.grab_rounding      = 0.0
    style.popup_rounding     = 0.0
    style.scrollbar_rounding = 0.0

    style.window_border_size = 1.0
    style.frame_border_size  = 1.0
    style.child_border_size  = 1.0
    style.popup_border_size  = 1.0

    style.frame_padding      = (4, 2)
    style.item_spacing       = (4, 3)
    style.item_inner_spacing = (4, 4)
    style.indent_spacing     = 14.0
    style.scrollbar_size     = 14.0
    style.grab_min_size      = 10.0
    style.window_padding     = (6, 6)

    c = style.colors

    BG       = (0.780, 0.765, 0.737, 1.0)
    BG_DARK  = (0.675, 0.663, 0.639, 1.0)
    BG_DKST  = (0.580, 0.569, 0.549, 1.0)
    BG_TITLE = (0.196, 0.361, 0.620, 1.0)
    BG_TTL2  = (0.118, 0.239, 0.478, 1.0)
    WIDGET   = (0.910, 0.902, 0.882, 1.0)
    WIDGET2  = (0.855, 0.847, 0.824, 1.0)
    BDR_LT   = (1.0,   1.0,   1.0,   0.9)
    BDR_DK   = (0.502, 0.494, 0.478, 1.0)
    TEXT     = (0.067, 0.067, 0.067, 1.0)
    TEXT_DIM = (0.333, 0.333, 0.333, 1.0)
    ACCENT   = (0.196, 0.361, 0.620, 1.0)
    ACC_HOV  = (0.294, 0.459, 0.718, 1.0)
    ACC_ACT  = (0.118, 0.239, 0.478, 1.0)
    SEP      = (0.502, 0.494, 0.478, 1.0)
    NONE     = (0.0,   0.0,   0.0,   0.0)

    c[imgui.COLOR_TEXT]                    = TEXT
    c[imgui.COLOR_TEXT_DISABLED]           = TEXT_DIM
    c[imgui.COLOR_WINDOW_BACKGROUND]       = BG
    c[imgui.COLOR_CHILD_BACKGROUND]        = BG
    c[imgui.COLOR_POPUP_BACKGROUND]        = BG
    c[imgui.COLOR_BORDER]                  = BDR_DK
    c[imgui.COLOR_BORDER_SHADOW]           = BDR_LT
    c[imgui.COLOR_FRAME_BACKGROUND]        = WIDGET
    c[imgui.COLOR_FRAME_BACKGROUND_HOVERED]= WIDGET2
    c[imgui.COLOR_FRAME_BACKGROUND_ACTIVE] = (0.800, 0.792, 0.773, 1.0)
    c[imgui.COLOR_TITLE_BACKGROUND]        = BG_TTL2
    c[imgui.COLOR_TITLE_BACKGROUND_ACTIVE] = BG_TITLE
    c[imgui.COLOR_TITLE_BACKGROUND_COLLAPSED] = BG_DKST
    c[imgui.COLOR_MENUBAR_BACKGROUND]      = BG_DARK
    c[imgui.COLOR_SCROLLBAR_BACKGROUND]    = BG_DARK
    c[imgui.COLOR_SCROLLBAR_GRAB]          = BG
    c[imgui.COLOR_SCROLLBAR_GRAB_HOVERED]  = WIDGET
    c[imgui.COLOR_SCROLLBAR_GRAB_ACTIVE]   = ACCENT
    c[imgui.COLOR_CHECK_MARK]              = TEXT
    c[imgui.COLOR_SLIDER_GRAB]             = BG_DKST
    c[imgui.COLOR_SLIDER_GRAB_ACTIVE]      = ACCENT
    c[imgui.COLOR_BUTTON]                  = BG
    c[imgui.COLOR_BUTTON_HOVERED]          = WIDGET
    c[imgui.COLOR_BUTTON_ACTIVE]           = BG_DARK
    c[imgui.COLOR_HEADER]                  = ACCENT
    c[imgui.COLOR_HEADER_HOVERED]          = ACC_HOV
    c[imgui.COLOR_HEADER_ACTIVE]           = ACC_ACT
    c[imgui.COLOR_SEPARATOR]               = SEP
    c[imgui.COLOR_SEPARATOR_HOVERED]       = ACC_HOV
    c[imgui.COLOR_SEPARATOR_ACTIVE]        = ACCENT
    c[imgui.COLOR_RESIZE_GRIP]             = BG_DKST
    c[imgui.COLOR_RESIZE_GRIP_HOVERED]     = ACC_HOV
    c[imgui.COLOR_RESIZE_GRIP_ACTIVE]      = ACCENT
    c[imgui.COLOR_PLOT_LINES]              = ACCENT
    c[imgui.COLOR_PLOT_LINES_HOVERED]      = ACC_HOV
    c[imgui.COLOR_PLOT_HISTOGRAM]          = ACCENT
    c[imgui.COLOR_PLOT_HISTOGRAM_HOVERED]  = ACC_HOV
    c[imgui.COLOR_TEXT_SELECTED_BACKGROUND]= (*ACCENT[:3], 0.4)
    c[imgui.COLOR_DRAG_DROP_TARGET]        = (1.0, 1.0, 0.0, 0.9)
    c[imgui.COLOR_NAV_HIGHLIGHT]           = ACCENT

    # tab colours - only set if the constants exist (pyimgui >= 1.4)
    for name, val in [
        ("COLOR_TAB",                  BG_DARK),
        ("COLOR_TAB_HOVERED",          WIDGET),
        ("COLOR_TAB_ACTIVE",           BG),
        ("COLOR_TAB_UNFOCUSED",        BG_DKST),
        ("COLOR_TAB_UNFOCUSED_ACTIVE", BG_DARK),
    ]:
        attr = getattr(imgui, name, None)
        if attr is not None:
            c[attr] = val


def push_header_colors():
    imgui.push_style_color(imgui.COLOR_HEADER,         0.196, 0.361, 0.620, 1.0)
    imgui.push_style_color(imgui.COLOR_HEADER_HOVERED, 0.294, 0.459, 0.718, 1.0)
    imgui.push_style_color(imgui.COLOR_HEADER_ACTIVE,  0.118, 0.239, 0.478, 1.0)
    imgui.push_style_color(imgui.COLOR_TEXT,           1.0,   1.0,   1.0,   1.0)


def pop_header_colors():
    imgui.pop_style_color(4)


def push_panel_dark():
    imgui.push_style_color(imgui.COLOR_CHILD_BACKGROUND, 0.675, 0.663, 0.639, 1.0)


def pop_panel_dark():
    imgui.pop_style_color(1)

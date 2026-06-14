"""
inspector.py - inspector panel
pyimgui 1.x compatible
"""

import imgui
from scene.scene import (
    GameObject, Transform, MeshRenderer, Camera,
    Light, Rigidbody, ScriptComponent, Component,
)
from editor.imgui_compat import (
    TREE_NODE_DEFAULT_OPEN, TREE_NODE_FRAMED,
    TREE_NODE_NO_TREE_PUSH_ON_OPEN, TREE_NODE_NO_AUTO_OPEN_ON_LOG,
)
from editor.theme import push_header_colors, pop_header_colors

_ADDABLE = {
    "mesh renderer": MeshRenderer,
    "camera":        Camera,
    "light":         Light,
    "rigidbody":     Rigidbody,
    "script":        ScriptComponent,
}

_HDR_FLAGS = (TREE_NODE_FRAMED | TREE_NODE_NO_TREE_PUSH_ON_OPEN
              | TREE_NODE_NO_AUTO_OPEN_ON_LOG | TREE_NODE_DEFAULT_OPEN)


def draw(scene):
    obj = scene.selected
    if obj is None:
        imgui.text_disabled("nothing selected")
        return

    imgui.push_item_width(-1)
    changed, new_name = imgui.input_text("##name", obj.name, 128)
    if changed:
        obj.name = new_name
    imgui.pop_item_width()

    _, obj.enabled = imgui.checkbox("enabled", obj.enabled)
    imgui.same_line()
    imgui.text_disabled("  tag:")
    imgui.same_line()
    # pyimgui: push_item_width instead of set_next_item_width
    imgui.push_item_width(80)
    _, obj.tag = imgui.input_text("##tag", obj.tag, 64)
    imgui.pop_item_width()

    imgui.separator()

    to_remove = None
    for comp in obj.components:
        if _draw_component(comp):
            to_remove = comp
    if to_remove:
        obj.remove_component(to_remove)

    imgui.spacing()
    avail_w = imgui.get_content_region_available()[0]  # returns (w, h) tuple
    btn_w = 160
    imgui.set_cursor_pos_x((avail_w - btn_w) * 0.5 + imgui.get_cursor_pos()[0])
    if imgui.button("+ add component", width=btn_w):
        imgui.open_popup("add_comp_popup")

    if imgui.begin_popup("add_comp_popup"):
        imgui.text("add component")
        imgui.separator()
        for name, cls in _ADDABLE.items():
            already = any(isinstance(c, cls) for c in obj.components)
            if already and cls is not ScriptComponent:
                continue
            if imgui.selectable(name)[0]:
                obj.add_component(cls())
                imgui.close_current_popup()
        imgui.end_popup()


def _draw_component(comp: Component) -> bool:
    remove = False
    push_header_colors()
    # pyimgui collapsing_header returns (expanded, visible) — just use [0]
    result = imgui.collapsing_header(
        f"  {comp.name}##comp_{id(comp)}",
        flags=_HDR_FLAGS,
    )
    # older pyimgui returns bool directly, newer returns (bool, bool)
    expanded = result[0] if isinstance(result, tuple) else result
    pop_header_colors()

    if imgui.begin_popup_context_item(f"rm_{id(comp)}"):
        _, comp.enabled = imgui.checkbox("enabled", comp.enabled)
        imgui.separator()
        if not isinstance(comp, Transform):
            if imgui.menu_item("remove component")[0]:
                remove = True
        imgui.end_popup()

    if expanded:
        imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (4, 3))
        imgui.indent(8)
        if not comp.enabled:
            imgui.push_style_var(imgui.STYLE_ALPHA, 0.45)
        comp.draw_inspector()
        if not comp.enabled:
            imgui.pop_style_var()
        imgui.unindent(8)
        imgui.pop_style_var()
        imgui.spacing()

    return remove

"""
hierarchy.py - scene hierarchy panel
pyimgui 1.x — strict push/pop discipline to avoid ID stack mismatch
"""

import imgui
from scene.scene import GameObject, Scene
from editor.imgui_compat import (
    TREE_NODE_OPEN_ON_ARROW,
    TREE_NODE_LEAF,
    TREE_NODE_NO_TREE_PUSH_ON_OPEN,
    TREE_NODE_SELECTED,
)

# NOTE: Do NOT use TREE_NODE_SPAN_AVAIL_WIDTH — it can cause issues in
# older pyimgui when combined with popup context items.


def draw(scene: Scene):
    imgui.push_style_var(imgui.STYLE_ITEM_SPACING, (2, 1))

    if imgui.button("+ create"):
        obj = GameObject("new object")
        scene.add_object(obj)
        scene.selected = obj
    imgui.same_line()
    if imgui.button("delete") and scene.selected:
        scene.delete_object(scene.selected)

    imgui.separator()

    # iterate over a copy so deletions mid-loop are safe
    for obj in list(scene.root_objects):
        _draw_node(scene, obj, depth=0)

    imgui.pop_style_var()


def _draw_node(scene: Scene, obj: GameObject, depth: int):
    has_children = bool(obj.children)

    # Use push_id / pop_id to give every node a unique scope,
    # so popup IDs and tree IDs never collide between siblings.
    imgui.push_id(obj.id)

    if has_children:
        # Internal node — tree_node pushes onto the ID stack when expanded
        flags = TREE_NODE_OPEN_ON_ARROW
        if obj is scene.selected:
            flags |= TREE_NODE_SELECTED

        expanded = imgui.tree_node(f"[+] {obj.name}", flags)

        if imgui.is_item_clicked():
            scene.selected = obj

        _node_context_menu(scene, obj)

        if expanded:
            for child in list(obj.children):
                _draw_node(scene, child, depth + 1)
            imgui.tree_pop()

    else:
        # Leaf node — NO_TREE_PUSH_ON_OPEN so tree_pop is NOT needed
        flags = TREE_NODE_LEAF | TREE_NODE_NO_TREE_PUSH_ON_OPEN
        if obj is scene.selected:
            flags |= TREE_NODE_SELECTED

        imgui.tree_node(f"  {_icon(obj)} {obj.name}", flags)
        # tree_node with NO_TREE_PUSH_ON_OPEN never needs tree_pop

        if imgui.is_item_clicked():
            scene.selected = obj

        _node_context_menu(scene, obj)

    imgui.pop_id()


def _node_context_menu(scene: Scene, obj: GameObject):
    # Use a fixed label — push_id above already scopes it uniquely
    if imgui.begin_popup_context_item("##ctx"):
        if imgui.menu_item("add child")[0]:
            child = GameObject("child object")
            obj.add_child(child)
        imgui.separator()
        if imgui.menu_item("delete")[0]:
            scene.delete_object(obj)
        imgui.end_popup()


def _icon(obj):
    names = [c.__class__.__name__ for c in obj.components]
    if "Camera" in names:       return "[cam]"
    if "Light" in names:        return "[lgt]"
    if "MeshRenderer" in names: return "[obj]"
    return "[---]"

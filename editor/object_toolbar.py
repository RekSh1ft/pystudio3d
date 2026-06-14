"""
object_toolbar.py — quick-insert toolbar for creating scene objects
and a runtime that actually runs scripts on game objects
"""

import os
import traceback
import importlib.util
import imgui
from scene.scene import (
    GameObject, Transform, MeshRenderer, Camera,
    Light, Rigidbody, ScriptComponent
)
from editor.panels import log_info, log_ok, log_warn, log_error

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "scripts")

# ── primitive shapes available 
PRIMITIVES = [
    ("cube",     "cube"),
    ("sphere",   "sphere"),
    ("plane",    "plane"),
    ("cylinder", "cylinder"),
    ("capsule",  "capsule"),
    ("empty",    None),
]

# ── runtime script instances: obj_id -> list of (instance, module) ─────────
_runtime_instances = {}   # only active during play mode


def draw_insert_bar(scene):
    """insert bar with taller buttons ready for icons above text"""
    BTN_H = 40  # tall enough to add an icon above text later

    for label, mesh in PRIMITIVES:
        if imgui.button(label, height=BTN_H):
            _create_primitive(scene, label, mesh)
        imgui.same_line()

    imgui.text("|")
    imgui.same_line()

    if imgui.button("camera", height=BTN_H):
        _create_camera(scene)
    imgui.same_line()

    imgui.text("|")
    imgui.same_line()

    if imgui.button("duplicate", height=BTN_H) and scene.selected:
        _duplicate(scene, scene.selected)
    imgui.same_line()
    if imgui.button("delete obj", height=BTN_H) and scene.selected:
        scene.delete_object(scene.selected)


def _create_primitive(scene, name, mesh_name):
    obj = GameObject(name)
    if mesh_name:
        mr = MeshRenderer()
        mr.mesh_name = mesh_name
        obj.add_component(mr)
    # place slightly in front of origin
    obj.transform.position = [0.0, 0.5, 0.0]
    scene.add_object(obj)
    scene.selected = obj
    log_info(f"created {name}")
    return obj


def _create_light(scene, type_name, type_idx):
    obj = GameObject(f"{type_name} light")
    obj.transform.position = [2.0, 4.0, 2.0]
    l = Light()
    l.light_type = type_idx
    obj.add_component(l)
    scene.add_object(obj)
    scene.selected = obj
    log_info(f"created {type_name} light")


def _create_camera(scene):
    obj = GameObject("camera")
    obj.transform.position = [0.0, 5.0, -10.0]
    obj.transform.rotation = [20.0, 0.0, 0.0]
    obj.add_component(Camera())
    scene.add_object(obj)
    scene.selected = obj
    log_info("created camera")


def _duplicate(scene, obj):
    import copy
    new_obj = GameObject(obj.name + "_copy")
    new_obj.transform.position = [p + 1.0 for p in obj.transform.position]
    new_obj.transform.rotation = list(obj.transform.rotation)
    new_obj.transform.scale    = list(obj.transform.scale)
    # copy non-transform components
    for comp in obj.components:
        if isinstance(comp, Transform):
            continue
        try:
            new_comp = copy.deepcopy(comp)
            new_obj.add_component(new_comp)
        except Exception:
            pass
    scene.add_object(new_obj)
    scene.selected = new_obj
    log_info(f"duplicated {obj.name}")


# ── runtime 

def runtime_start(scene):
    """called when entering play mode — start() all scripts"""
    _runtime_instances.clear()
    for obj in _iter_all(scene.root_objects):
        for comp in obj.components:
            if isinstance(comp, ScriptComponent) and comp.enabled:
                inst = _load_and_start(comp, obj)
                if inst:
                    if obj.id not in _runtime_instances:
                        _runtime_instances[obj.id] = []
                    _runtime_instances[obj.id].append((inst, comp.script_name))


def runtime_update(scene, dt):
    """called every frame in play mode — update() all scripts"""
    for obj in _iter_all(scene.root_objects):
        instances = _runtime_instances.get(obj.id, [])
        for inst, _ in instances:
            if hasattr(inst, "update"):
                try:
                    inst.update(obj, dt)
                except Exception:
                    log_error(traceback.format_exc())


def runtime_stop(scene):
    """called when leaving play mode"""
    for obj in _iter_all(scene.root_objects):
        instances = _runtime_instances.get(obj.id, [])
        for inst, _ in instances:
            if hasattr(inst, "on_destroy"):
                try:
                    inst.on_destroy(obj)
                except Exception:
                    pass
    _runtime_instances.clear()


def _load_and_start(comp, obj):
    """load script file and call start()"""
    # look for script in assets/scripts/
    script_file = getattr(comp, "script_file", None)
    if not script_file:
        # try to find by name
        name = comp.script_name.replace(" ", "_")
        for fname in [name, name + ".py", name.lower() + ".py"]:
            candidate = os.path.join(SCRIPTS_DIR, fname)
            if os.path.exists(candidate):
                script_file = candidate
                break

    if not script_file or not os.path.exists(script_file):
        log_warn(f"script not found: {comp.script_name}")
        return None

    try:
        spec = importlib.util.spec_from_file_location("usr_" + comp.script_name, script_file)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import inspect
        for cname, cls in inspect.getmembers(mod, inspect.isclass):
            try:
                inst = cls()
                if hasattr(inst, "start"):
                    inst.start(obj)
                log_ok(f"started {comp.script_name} on {obj.name}")
                return inst
            except Exception:
                log_error(traceback.format_exc())
    except Exception:
        log_error(traceback.format_exc())
    return None


def _iter_all(objs):
    for o in objs:
        yield o
        yield from _iter_all(o.children)

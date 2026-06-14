import os
"""
scene.py — game object hierarchy and component system
"""

import uuid
import numpy as np


# ── component base 

class Component:
    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    def draw_inspector(self):
        """override to draw custom inspector ui"""
        pass

    def update(self, dt: float):
        pass


# ── built-in components 
class Transform(Component):
    def __init__(self):
        super().__init__("transform")
        self.position = [0.0, 0.0, 0.0]
        self.rotation = [0.0, 0.0, 0.0]   # euler degrees
        self.scale    = [1.0, 1.0, 1.0]

    def draw_inspector(self):
        import imgui
        changed, vals = imgui.input_float3("position", *self.position)
        if changed: self.position = list(vals)
        changed, vals = imgui.input_float3("rotation", *self.rotation)
        if changed: self.rotation = list(vals)
        changed, vals = imgui.input_float3("scale", *self.scale)
        if changed: self.scale = list(vals)


class MeshRenderer(Component):
    def __init__(self):
        super().__init__("mesh renderer")
        self.mesh_name  = "cube"
        self.material   = "default"
        self.cast_shadows = True
        self.recv_shadows = True

    def draw_inspector(self):
        import imgui
        _, self.mesh_name  = imgui.input_text("mesh",     self.mesh_name,  128)
        _, self.material   = imgui.input_text("material", self.material,   128)
        _, self.cast_shadows = imgui.checkbox("cast shadows", self.cast_shadows)
        _, self.recv_shadows = imgui.checkbox("recv shadows", self.recv_shadows)


class Camera(Component):
    def __init__(self):
        super().__init__("camera")
        self.fov   = 60.0
        self.near  = 0.1
        self.far   = 1000.0
        self.is_main = True

    def draw_inspector(self):
        import imgui
        _, self.fov  = imgui.slider_float("fov",  self.fov,  10.0, 170.0)
        _, self.near = imgui.input_float("near", self.near)
        _, self.far  = imgui.input_float("far",  self.far)
        _, self.is_main = imgui.checkbox("main camera", self.is_main)


class Light(Component):
    TYPES = ["directional", "point", "spot"]

    def __init__(self):
        super().__init__("light")
        self.light_type = 0
        self.color     = [1.0, 1.0, 1.0]
        self.intensity = 1.0
        self.range     = 10.0

    def draw_inspector(self):
        import imgui
        _, self.light_type = imgui.combo("type", self.light_type, self.TYPES)
        _c, vals = imgui.color_edit3("color", *self.color)
        if _c: self.color = list(vals)
        _, self.intensity  = imgui.slider_float("intensity", self.intensity, 0.0, 8.0)
        if self.light_type > 0:
            _, self.range  = imgui.input_float("range", self.range)


class Rigidbody(Component):
    def __init__(self):
        super().__init__("rigidbody")
        self.mass        = 1.0
        self.drag        = 0.0
        self.ang_drag    = 0.05
        self.use_gravity = True
        self.is_kinematic = False

    def draw_inspector(self):
        import imgui
        _, self.mass         = imgui.input_float("mass",     self.mass)
        _, self.drag         = imgui.input_float("drag",     self.drag)
        _, self.ang_drag     = imgui.input_float("ang drag", self.ang_drag)
        _, self.use_gravity  = imgui.checkbox("use gravity", self.use_gravity)
        _, self.is_kinematic = imgui.checkbox("is kinematic", self.is_kinematic)


class ScriptComponent(Component):
    def __init__(self, script_name: str = "new_script"):
        super().__init__(f"{script_name} (script)")
        self.script_name = script_name
        self.script_file = None   # full path to .py file, set by editor
        self.fields: dict = {}   # name to (type_str, value)

    def draw_inspector(self):
        import imgui
        _, self.script_name = imgui.input_text("script", self.script_name, 256)
        imgui.separator()
        for key, (typ, val) in list(self.fields.items()):
            if typ == "float":
                changed, new_val = imgui.input_float(key, val)
                if changed:
                    self.fields[key] = (typ, new_val)
            elif typ == "int":
                changed, new_val = imgui.input_int(key, val)
                if changed:
                    self.fields[key] = (typ, new_val)
            elif typ == "bool":
                changed, new_val = imgui.checkbox(key, val)
                if changed:
                    self.fields[key] = (typ, new_val)
            elif typ == "str":
                changed, new_val = imgui.input_text(key, val, 256)
                if changed:
                    self.fields[key] = (typ, new_val)


# ── game object 

class GameObject:
    def __init__(self, name: str = "gameobject"):
        self.id         = str(uuid.uuid4())[:8]
        self.name       = name
        self.enabled    = True
        self.tag        = "untagged"
        self.layer      = "default"
        self.children: list["GameObject"] = []
        self.parent: "GameObject | None"  = None
        self.components: list[Component]  = []

        # every object has a transform
        self.add_component(Transform())

    @property
    def transform(self) -> Transform:
        return self.get_component(Transform)

    def add_component(self, comp: Component):
        self.components.append(comp)
        return comp

    def get_component(self, cls):
        for c in self.components:
            if isinstance(c, cls):
                return c
        return None

    def remove_component(self, comp: Component):
        if comp in self.components and not isinstance(comp, Transform):
            self.components.remove(comp)

    def add_child(self, child: "GameObject"):
        child.parent = self
        self.children.append(child)

    def update(self, dt: float):
        if not self.enabled:
            return
        for comp in self.components:
            if comp.enabled:
                comp.update(dt)
        for child in self.children:
            child.update(dt)


# ── scene 

class Scene:
    def __init__(self, name: str = "untitled"):
        self.name = name
        self.root_objects: list[GameObject] = []
        self.selected: GameObject | None    = None

    def add_object(self, obj: GameObject, parent: GameObject | None = None):
        if parent:
            parent.add_child(obj)
        else:
            self.root_objects.append(obj)
        return obj

    def delete_object(self, obj: GameObject):
        if obj in self.root_objects:
            self.root_objects.remove(obj)
        elif obj.parent:
            obj.parent.children.remove(obj)
        if self.selected is obj:
            self.selected = None

    def find_by_name(self, name: str) -> "GameObject | None":
        def _search(objs):
            for o in objs:
                if o.name == name:
                    return o
                result = _search(o.children)
                if result:
                    return result
            return None
        return _search(self.root_objects)

    def update(self, dt: float):
        for obj in self.root_objects:
            obj.update(dt)

    @classmethod
    def make_default(cls) -> "Scene":
        """create a starter scene with camera, light, and a cube"""
        scene = cls("untitled")

        # camera
        cam_obj = GameObject("main camera")
        cam_obj.transform.position = [0.0, 5.0, -10.0]
        cam_obj.transform.rotation = [20.0, 0.0, 0.0]
        cam_obj.add_component(Camera())
        scene.add_object(cam_obj)

        # directional light
        light_obj = GameObject("directional light")
        light_obj.transform.rotation = [50.0, -30.0, 0.0]
        light_obj.add_component(Light())
        scene.add_object(light_obj)

        # player cube
        player = GameObject("player")
        player.transform.position = [0.0, 0.5, 0.0]
        player.add_component(MeshRenderer())
        player.add_component(Rigidbody())
        sc = ScriptComponent("player_controller")
        sc.script_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "scripts", "player_controller.py"
        )
        sc.fields = {
            "speed":      ("float", 5.0),
            "jump force": ("float", 8.0),
            "health":     ("int",   100),
        }
        player.add_component(sc)
        scene.add_object(player)

        # ground plane
        ground = GameObject("ground")
        ground.transform.position = [0.0, 0.0, 0.0]
        ground.transform.scale    = [20.0, 0.1, 20.0]
        mr = MeshRenderer()
        mr.mesh_name = "plane"
        mr.material  = "mat_ground"
        ground.add_component(mr)
        scene.add_object(ground)

        # environment group
        env = GameObject("environment")
        scene.add_object(env)

        tree1 = GameObject("tree_01")
        tree1.transform.position = [4.0, 0.0, 3.0]
        mr2 = MeshRenderer()
        mr2.mesh_name = "tree.obj"
        tree1.add_component(mr2)
        env.add_child(tree1)

        rock = GameObject("rock_cluster")
        rock.transform.position = [-5.0, 0.0, 6.0]
        mr3 = MeshRenderer()
        mr3.mesh_name = "rock.obj"
        rock.add_component(mr3)
        env.add_child(rock)

        # particle system
        fx = GameObject("particle_system")
        fx.transform.position = [0.0, 2.0, 0.0]
        scene.add_object(fx)

        # ui canvas
        ui = GameObject("ui_canvas")
        scene.add_object(ui)

        scene.selected = player
        return scene

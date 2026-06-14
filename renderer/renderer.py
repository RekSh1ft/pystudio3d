"""
Project Codenamed: Rendrd8
renderer.py — moderngl viewport renderer
draws the 3d scene with a grid, wireframe objects, and transform gizmos
"""

import numpy as np
import moderngl as mgl
from renderer.gizmo import GizmoRenderer, TOOL_TRANSLATE, TOOL_ROTATE, TOOL_SCALE, TOOL_NONE


# ── shaders 

GRID_VERT = """
#version 330 core
in vec3 in_position;
uniform mat4 u_mvp;
void main() {
    gl_Position = u_mvp * vec4(in_position, 1.0);
}
"""

GRID_FRAG = """
#version 330 core
uniform vec4 u_color;
out vec4 fragColor;
void main() {
    fragColor = u_color;
}
"""

SOLID_VERT = """
#version 330 core
in vec3 in_position;
in vec3 in_normal;
uniform mat4 u_mvp;
uniform mat4 u_model;
uniform vec3 u_light_dir;
uniform vec3 u_color;
out vec3 v_color;
void main() {
    gl_Position = u_mvp * vec4(in_position, 1.0);
    mat3 norm_mat = mat3(transpose(inverse(u_model)));
    vec3 world_normal = normalize(norm_mat * in_normal);
    float diff = max(dot(world_normal, normalize(-u_light_dir)), 0.0);
    float ambient = 0.25;
    v_color = u_color * (ambient + diff * 0.75);
}
"""

SOLID_FRAG = """
#version 330 core
in vec3 v_color;
out vec4 fragColor;
void main() {
    fragColor = vec4(v_color, 1.0);
}
"""

WIRE_VERT = """
#version 330 core
in vec3 in_position;
uniform mat4 u_mvp;
void main() {
    gl_Position = u_mvp * vec4(in_position, 1.0);
}
"""

WIRE_FRAG = """
#version 330 core
uniform vec4 u_color;
out vec4 fragColor;
void main() {
    fragColor = u_color;
}
"""

GIZMO_VERT = """
#version 330 core
in vec3 in_position;
in vec3 in_color;
uniform mat4 u_mvp;
out vec3 v_color;
void main() {
    gl_Position = u_mvp * vec4(in_position, 1.0);
    v_color = in_color;
}
"""

GIZMO_FRAG = """
#version 330 core
in vec3 v_color;
out vec4 fragColor;
void main() {
    fragColor = vec4(v_color, 1.0);
}
"""


def perspective(fov_deg, aspect, near, far):
    fov = np.radians(fov_deg)
    f = 1.0 / np.tan(fov / 2.0)
    nf = 1.0 / (near - far)
    return np.array([
        [f/aspect, 0,  0,                    0],
        [0,        f,  0,                    0],
        [0,        0,  (far+near)*nf,        -1],
        [0,        0,  2*far*near*nf,         0],
    ], dtype=np.float32)


def look_at(eye, center, up):
    f = (center - eye); f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return np.array([
        [ r[0],  u[0], -f[0], 0],
        [ r[1],  u[1], -f[1], 0],
        [ r[2],  u[2], -f[2], 0],
        [-np.dot(r,eye), -np.dot(u,eye), np.dot(f,eye), 1],
    ], dtype=np.float32)


def translate(tx, ty, tz):
    m = np.eye(4, dtype=np.float32)
    m[3, 0] = tx; m[3, 1] = ty; m[3, 2] = tz
    return m


def scale_mat(sx, sy, sz):
    m = np.eye(4, dtype=np.float32)
    m[0,0] = sx; m[1,1] = sy; m[2,2] = sz
    return m


def rot_x(deg):
    r = np.radians(deg); c, s = np.cos(r), np.sin(r)
    m = np.eye(4, dtype=np.float32)
    m[1,1]=c; m[2,1]=-s; m[1,2]=s; m[2,2]=c
    return m


def rot_y(deg):
    r = np.radians(deg); c, s = np.cos(r), np.sin(r)
    m = np.eye(4, dtype=np.float32)
    m[0,0]=c; m[2,0]=s; m[0,2]=-s; m[2,2]=c
    return m


class Renderer:
    def __init__(self):
        self.ctx: mgl.Context | None = None
        self.initialized = False

        # camera orbit state
        self.cam_yaw   = 30.0
        self.cam_pitch = 25.0
        self.cam_dist  = 12.0
        self.cam_target = np.array([0.0, 0.5, 0.0], dtype=np.float32)

        # viewport shading mode
        self.shading = "solid"
        # gizmo
        self.gizmo = GizmoRenderer()
        self.tool = TOOL_TRANSLATE   # current tool
        self._last_view = None
        self._last_proj = None
        self._last_eye  = None   # "wireframe" | "solid" | "unlit"
        self.show_grid = True
        self.show_gizmos = True

    def init(self):
        self.ctx = mgl.create_context()
        self.ctx.enable(mgl.DEPTH_TEST)

        # programs
        self.prog_grid  = self.ctx.program(vertex_shader=GRID_VERT,  fragment_shader=GRID_FRAG)
        self.prog_solid = self.ctx.program(vertex_shader=SOLID_VERT, fragment_shader=SOLID_FRAG)
        self.prog_wire  = self.ctx.program(vertex_shader=WIRE_VERT,  fragment_shader=WIRE_FRAG)
        self.prog_gizmo = self.ctx.program(vertex_shader=GIZMO_VERT, fragment_shader=GIZMO_FRAG)

        # geometry
        self._build_grid(20)
        self._build_cube()
        self._build_plane()
        self._build_gizmo()

        self.gizmo.init(self.ctx)
        self.initialized = True

    # ── geometry builders 

    def _build_grid(self, half=20):
        lines = []
        for i in range(-half, half + 1):
            lines += [i, 0, -half,  i, 0,  half]
            lines += [-half, 0, i,   half, 0, i]
        verts = np.array(lines, dtype=np.float32)
        self.vbo_grid = self.ctx.buffer(verts.tobytes())
        self.vao_grid = self.ctx.vertex_array(
            self.prog_grid, [(self.vbo_grid, "3f", "in_position")]
        )
        self._grid_count = len(lines) // 3

    def _build_cube(self):
        # 6 faces × 2 tris × 3 verts  (position + normal)
        v = np.array([
            # pos xyz    normal xyz
            # front
            -0.5,-0.5, 0.5,  0, 0, 1,
             0.5,-0.5, 0.5,  0, 0, 1,
             0.5, 0.5, 0.5,  0, 0, 1,
            -0.5, 0.5, 0.5,  0, 0, 1,
            # back
             0.5,-0.5,-0.5,  0, 0,-1,
            -0.5,-0.5,-0.5,  0, 0,-1,
            -0.5, 0.5,-0.5,  0, 0,-1,
             0.5, 0.5,-0.5,  0, 0,-1,
            # left
            -0.5,-0.5,-0.5, -1, 0, 0,
            -0.5,-0.5, 0.5, -1, 0, 0,
            -0.5, 0.5, 0.5, -1, 0, 0,
            -0.5, 0.5,-0.5, -1, 0, 0,
            # right
             0.5,-0.5, 0.5,  1, 0, 0,
             0.5,-0.5,-0.5,  1, 0, 0,
             0.5, 0.5,-0.5,  1, 0, 0,
             0.5, 0.5, 0.5,  1, 0, 0,
            # top
            -0.5, 0.5, 0.5,  0, 1, 0,
             0.5, 0.5, 0.5,  0, 1, 0,
             0.5, 0.5,-0.5,  0, 1, 0,
            -0.5, 0.5,-0.5,  0, 1, 0,
            # bottom
            -0.5,-0.5,-0.5,  0,-1, 0,
             0.5,-0.5,-0.5,  0,-1, 0,
             0.5,-0.5, 0.5,  0,-1, 0,
            -0.5,-0.5, 0.5,  0,-1, 0,
        ], dtype=np.float32)
        idx = []
        for f in range(6):
            b = f * 4
            idx += [b,b+1,b+2, b,b+2,b+3]
        self.idx_cube = np.array(idx, dtype=np.uint32)
        self.vbo_cube = self.ctx.buffer(v.tobytes())
        self.ibo_cube = self.ctx.buffer(self.idx_cube.tobytes())
        self.vao_cube_solid = self.ctx.vertex_array(
            self.prog_solid,
            [(self.vbo_cube, "3f 3f", "in_position", "in_normal")],
            self.ibo_cube
        )
        # wireframe uses same vbo but edge indices
        edges = []
        edge_set = set()
        for i in range(0, len(idx), 3):
            tri = [idx[i], idx[i+1], idx[i+2]]
            for a, b in [(0,1),(1,2),(2,0)]:
                e = tuple(sorted([tri[a], tri[b]]))
                if e not in edge_set:
                    edge_set.add(e)
                    edges += list(e)
        ibo_wire = self.ctx.buffer(np.array(edges, dtype=np.uint32).tobytes())
        # wire shader only has in_position; use stride "3f 3x4" to skip the
        # 12-byte normal that follows each position in the interleaved VBO
        self.vao_cube_wire = self.ctx.vertex_array(
            self.prog_wire,
            [(self.vbo_cube, "3f 3x4", "in_position")],
            ibo_wire
        )
        self._wire_count = len(edges)

    def _build_plane(self):
        v = np.array([
            -0.5, 0, -0.5,  0, 1, 0,
             0.5, 0, -0.5,  0, 1, 0,
             0.5, 0,  0.5,  0, 1, 0,
            -0.5, 0,  0.5,  0, 1, 0,
        ], dtype=np.float32)
        idx = np.array([0,1,2, 0,2,3], dtype=np.uint32)
        vbo = self.ctx.buffer(v.tobytes())
        ibo = self.ctx.buffer(idx.tobytes())
        self.vao_plane = self.ctx.vertex_array(
            self.prog_solid, [(vbo, "3f 3f", "in_position", "in_normal")], ibo
        )

    def _build_gizmo(self):
        # x=red, y=green, z=blue  axes (lines)
        L = 1.5
        verts = np.array([
            0,0,0, 1,0,0,  L,0,0, 1,0,0,   # X
            0,0,0, 0,1,0,  0,L,0, 0,1,0,   # Y
            0,0,0, 0,0,1,  0,0,L, 0,0,1,   # Z
        ], dtype=np.float32)
        self.vbo_gizmo = self.ctx.buffer(verts.tobytes())
        self.vao_gizmo = self.ctx.vertex_array(
            self.prog_gizmo,
            [(self.vbo_gizmo, "3f 3f", "in_position", "in_color")]
        )

    # ── render ─

    def render(self, width: int, height: int, scene=None):
        if not self.initialized:
            return

        self.ctx.viewport = (0, 0, width, height)
        self.ctx.clear(0.105, 0.105, 0.180)   # dark navy bg

        if width == 0 or height == 0:
            return

        aspect = width / height

        # ── camera ──
        eye = self._orbit_eye()
        proj = perspective(60.0, aspect, 0.1, 1000.0)
        view = look_at(eye, self.cam_target, np.array([0, 1, 0], dtype=np.float32))
        vp   = view @ proj

        # ── grid ──
        if self.show_grid:
            self.prog_grid["u_mvp"].write(np.eye(4, dtype=np.float32) @ vp)
            color = (0.25, 0.30, 0.45, 1.0)
            self.prog_grid["u_color"].value = color
            self.vao_grid.render(mgl.LINES, self._grid_count)

            # centre axes (brighter)
            # X axis
            ax = np.array([-100,0,0, 100,0,0], dtype=np.float32)
            abuf = self.ctx.buffer(ax.tobytes())
            avao = self.ctx.vertex_array(self.prog_grid, [(abuf, "3f", "in_position")])
            self.prog_grid["u_mvp"].write(np.eye(4, dtype=np.float32) @ vp)
            self.prog_grid["u_color"].value = (0.7, 0.2, 0.2, 1.0)
            avao.render(mgl.LINES, 2)
            abuf.release(); avao.release()

        # ── scene objects ──
        light_dir = np.array([-0.5, -1.0, -0.3], dtype=np.float32)
        light_dir /= np.linalg.norm(light_dir)

        if scene:
            all_objs = self._flatten(scene.root_objects)
            for obj in all_objs:
                if not obj.enabled:
                    continue
                self._render_object(obj, vp, light_dir, scene.selected)
        else:
            # demo cube
            model = translate(0, 0.5, 0)
            mvp   = model @ vp
            self.prog_solid["u_mvp"].write(mvp)
            self.prog_solid["u_model"].write(model)
            self.prog_solid["u_light_dir"].value = tuple(light_dir)
            self.prog_solid["u_color"].value = (0.40, 0.55, 0.80)
            self.vao_cube_solid.render()

        # ── transform gizmo on selected object ──
        if self.show_gizmos and scene and scene.selected and not getattr(scene, '_playing', False):
            self.gizmo.render(
                scene.selected, self.tool,
                view, proj, eye
            )

        # store matrices for picking
        self._last_view = view
        self._last_proj = proj
        self._last_eye  = eye

        # ── corner gizmo (mini axes) ──
        if self.show_gizmos:
            self._render_corner_gizmo(width, height, view, proj)

    def _flatten(self, objs):
        result = []
        for o in objs:
            result.append(o)
            result.extend(self._flatten(o.children))
        return result

    def _render_object(self, obj, vp, light_dir, selected):
        mr = None
        for c in obj.components:
            if c.__class__.__name__ == "MeshRenderer":
                mr = c; break
        if not mr:
            return

        t = obj.transform
        model = (translate(*t.position)
                 @ rot_y(t.rotation[1])
                 @ rot_x(t.rotation[0])
                 @ scale_mat(*t.scale))
        mvp = model @ vp

        is_selected = (obj is selected)

        if self.shading in ("solid", "unlit"):
            color = (0.40, 0.55, 0.80) if not is_selected else (0.90, 0.75, 0.25)
            self.prog_solid["u_mvp"].write(mvp)
            self.prog_solid["u_model"].write(model)
            self.prog_solid["u_light_dir"].value = tuple(light_dir)
            self.prog_solid["u_color"].value = color

            mesh = mr.mesh_name.lower()
            if "plane" in mesh or "ground" in mesh:
                self.vao_plane.render()
            else:
                self.vao_cube_solid.render()

        if self.shading == "wireframe" or is_selected:
            wire_color = (0.2, 0.6, 1.0, 1.0) if is_selected else (0.5, 0.6, 0.7, 1.0)
            self.prog_wire["u_mvp"].write(mvp)
            self.prog_wire["u_color"].value = wire_color
            self.ctx.enable(mgl.BLEND)
            self.vao_cube_wire.render(mgl.LINES, self._wire_count)
            self.ctx.disable(mgl.BLEND)

    def _render_corner_gizmo(self, W, H, view, proj):
        """draw xyz axes in bottom-left corner"""
        size = 70
        self.ctx.viewport = (8, 8, size, size)
        eye = self._orbit_eye(dist=4.0)
        mini_view = look_at(eye, np.zeros(3, dtype=np.float32), np.array([0,1,0], dtype=np.float32))
        mini_proj = perspective(60.0, 1.0, 0.1, 100.0)
        mvp = np.eye(4, dtype=np.float32) @ mini_view @ mini_proj
        self.prog_gizmo["u_mvp"].write(mvp)
        self.ctx.disable(mgl.DEPTH_TEST)
        self.vao_gizmo.render(mgl.LINES, 6)
        self.ctx.enable(mgl.DEPTH_TEST)
        self.ctx.viewport = (0, 0, W, H)

    def _orbit_eye(self, dist=None):
        d   = dist or self.cam_dist
        yaw = np.radians(self.cam_yaw)
        pit = np.radians(self.cam_pitch)
        x = d * np.cos(pit) * np.sin(yaw)
        y = d * np.sin(pit)
        z = d * np.cos(pit) * np.cos(yaw)
        return self.cam_target + np.array([x, y, z], dtype=np.float32)

    # ── camera controls 

    def orbit(self, dx: float, dy: float):
        self.cam_yaw   += dx * 0.5
        self.cam_pitch  = np.clip(self.cam_pitch + dy * 0.5, -89.0, 89.0)

    def zoom(self, delta: float):
        self.cam_dist = np.clip(self.cam_dist - delta * 0.8, 1.0, 200.0)

    def pan(self, dx: float, dy: float):
        """pan perpendicular to view direction"""
        yaw = np.radians(self.cam_yaw)
        right = np.array([np.cos(yaw), 0, -np.sin(yaw)], dtype=np.float32)
        up    = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        speed = self.cam_dist * 0.001
        self.cam_target -= right * dx * speed
        self.cam_target += up    * dy * speed


    # ── public matrix accessors (needed by gizmo raycasting) 

    def get_matrices(self, width, height):
        """return (view, proj, eye) for current camera state"""
        aspect = max(width, 1) / max(height, 1)
        proj = perspective(60.0, aspect, 0.1, 1000.0)
        eye  = self._orbit_eye()
        view = look_at(eye, self.cam_target, np.array([0,1,0], dtype=np.float32))
        return view, proj, eye

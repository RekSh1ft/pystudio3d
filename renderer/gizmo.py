"""
Project Codenamed: Rendrd8
gizmo.py — translate / rotate / scale gizmos
Row-major matrices matching renderer.py conventions:
  - translation in m[3, 0:3]
  - MVP = model @ view @ proj
  - written to shader as-is (GLSL receives column-major, numpy row-major is equivalent)
"""

import numpy as np
import moderngl as mgl

GIZMO_V = """
#version 330 core
in vec3 in_position;
uniform mat4 u_mvp;
uniform vec3 u_color;
out vec3 v_color;
void main() {
    gl_Position = u_mvp * vec4(in_position, 1.0);
    v_color = u_color;
}
"""
GIZMO_F = """
#version 330 core
in vec3 v_color;
out vec4 fragColor;
void main() { fragColor = vec4(v_color, 1.0); }
"""

TOOL_NONE      = 0
TOOL_TRANSLATE = 1
TOOL_ROTATE    = 2
TOOL_SCALE     = 3

COLORS = [
    np.array([0.95, 0.15, 0.15], np.float32),  # X red
    np.array([0.10, 0.88, 0.10], np.float32),  # Y green
    np.array([0.15, 0.35, 0.95], np.float32),  # Z blue
]
HOVER = np.array([1.0, 0.85, 0.0], np.float32)

# world-space axis unit vectors
AX = [
    np.array([1,0,0], np.float32),
    np.array([0,1,0], np.float32),
    np.array([0,0,1], np.float32),
]


# ── geometry builders

def _arrow(axis, segs=12, shaft_r=0.045, shaft_l=0.72, cone_r=0.10, cone_l=0.25):
    a0 = AX[axis]
    a1 = AX[(axis+1)%3]
    a2 = AX[(axis+2)%3]
    v = []
    for i in range(segs):
        t0 = 2*np.pi*i/segs
        t1 = 2*np.pi*(i+1)/segs
        def rim(t, along):
            return along*a0 + np.cos(t)*shaft_r*a1 + np.sin(t)*shaft_r*a2
        # shaft quad
        b0=rim(t0,0); b1=rim(t1,0); e0=rim(t0,shaft_l); e1=rim(t1,shaft_l)
        v += [*b0,*e0,*e1, *b0,*e1,*b1]
        # cone
        def cr(t):
            return shaft_l*a0 + np.cos(t)*cone_r*a1 + np.sin(t)*cone_r*a2
        tip = (shaft_l+cone_l)*a0
        c0=cr(t0); c1=cr(t1)
        v += [*c0,*c1,*tip]
        v += [*c0,*(shaft_l*a0),*c1]
    return np.array(v, np.float32)


def _ring(axis, segs=48, r=1.0, w=0.042):
    a0 = AX[axis]
    a1 = AX[(axis+1)%3]
    a2 = AX[(axis+2)%3]
    v = []
    for i in range(segs):
        t0 = 2*np.pi*i/segs
        t1 = 2*np.pi*(i+1)/segs
        for t in (t0,t1):
            c,s = np.cos(t), np.sin(t)
            pi = c*(r-w)*a1 + s*(r-w)*a2
            po = c*(r+w)*a1 + s*(r+w)*a2
        c0,s0 = np.cos(t0),np.sin(t0)
        c1,s1 = np.cos(t1),np.sin(t1)
        pi0 = c0*(r-w)*a1+s0*(r-w)*a2
        po0 = c0*(r+w)*a1+s0*(r+w)*a2
        pi1 = c1*(r-w)*a1+s1*(r-w)*a2
        po1 = c1*(r+w)*a1+s1*(r+w)*a2
        v += [*pi0,*po0,*po1, *pi0,*po1,*pi1]
    return np.array(v, np.float32)


def _scale_axis(axis, segs=8, shaft_r=0.035, shaft_l=0.72, box=0.10):
    a0 = AX[axis]
    a1 = AX[(axis+1)%3]
    a2 = AX[(axis+2)%3]
    v = []
    # shaft
    for i in range(segs):
        t0 = 2*np.pi*i/segs
        t1 = 2*np.pi*(i+1)/segs
        def rim(t, along):
            return along*a0 + np.cos(t)*shaft_r*a1 + np.sin(t)*shaft_r*a2
        b0=rim(t0,0); b1=rim(t1,0); e0=rim(t0,shaft_l); e1=rim(t1,shaft_l)
        v += [*b0,*e0,*e1, *b0,*e1,*b1]
    # box at tip
    ctr = (shaft_l + box)*a0
    h = box
    corners = [ctr + s1*h*a1 + s2*h*a2 + s3*h*a0
               for s1 in (-1,1) for s2 in (-1,1) for s3 in (-1,1)]
    for face in ([0,1,3,2],[4,5,7,6],[0,1,5,4],[2,3,7,6],[0,2,6,4],[1,3,7,5]):
        a,b,c,d = [corners[i] for i in face]
        v += [*a,*b,*c, *a,*c,*d]
    return np.array(v, np.float32)


# ── gizmo renderer 

class GizmoRenderer:
    def __init__(self):
        self.active_axis = -1
        self.dragging    = False
        self._tool       = TOOL_NONE
        self._axis       = 0
        self._pos0       = None
        self._rot0       = None
        self._scl0       = None
        self._hit0       = None   # world-space drag start point
        self._plane_n    = None
        self._plane_d    = 0.0
        self.scale_fac   = 1.5

    def init(self, ctx):
        self.ctx  = ctx
        self.prog = ctx.program(vertex_shader=GIZMO_V, fragment_shader=GIZMO_F)
        self._tr, self._tr_n = self._upload([_arrow(i) for i in range(3)])
        self._ro, self._ro_n = self._upload([_ring(i)  for i in range(3)])
        self._sc, self._sc_n = self._upload([_scale_axis(i) for i in range(3)])

    def _upload(self, vert_list):
        vaos, cnts = [], []
        for v in vert_list:
            vbo = self.ctx.buffer(v.tobytes())
            vao = self.ctx.vertex_array(self.prog, [(vbo, "3f", "in_position")])
            vaos.append(vao); cnts.append(len(v)//3)
        return vaos, cnts

    # ── render 

    def render(self, obj, tool, view, proj, eye):
        if obj is None or tool == TOOL_NONE:
            return

        pos  = np.array(obj.transform.position, np.float32)
        dist = max(float(np.linalg.norm(eye - pos)), 0.01)
        s    = dist * 0.15 * self.scale_fac

        # Row-major: model = scale then translate  =>  T @ S
        # (point p -> S*p -> S*p + pos)
        model = _T(pos) @ _S(s)
        mvp   = model @ view @ proj   # row-major chain, matches renderer.py

        self.ctx.disable(mgl.DEPTH_TEST)

        if   tool == TOOL_TRANSLATE: vaos,cnts = self._tr, self._tr_n
        elif tool == TOOL_ROTATE:    vaos,cnts = self._ro, self._ro_n
        else:                        vaos,cnts = self._sc, self._sc_n

        for i in range(3):
            col = HOVER if self.active_axis == i else COLORS[i]
            self.prog["u_mvp"].write(mvp.tobytes())
            self.prog["u_color"].value = tuple(col)
            vaos[i].render(mgl.TRIANGLES, cnts[i])

        self.ctx.enable(mgl.DEPTH_TEST)

    # ── picking / drag 

    def update_hover(self, obj, tool, mx, my, vp_w, vp_h, view, proj, eye):
        if obj is None or tool == TOOL_NONE:
            self.active_axis = -1; return
        pos  = np.array(obj.transform.position, np.float32)
        dist = max(float(np.linalg.norm(eye - pos)), 0.01)
        s    = dist * 0.15 * self.scale_fac
        ro, rd = _screen_ray(mx, my, vp_w, vp_h, view, proj)
        kwargs = dict(view=view, proj=proj, vp_w=vp_w, vp_h=vp_h, mx=mx, my=my)
        if tool == TOOL_ROTATE:
            self.active_axis = _pick_ring(pos, s, ro, rd, **kwargs)
        else:
            self.active_axis = _pick_arrow(pos, s, ro, rd, **kwargs)

    def try_begin_drag(self, obj, tool, mx, my, vp_w, vp_h, view, proj, eye):
        """Call on mouse-down. Returns True if a gizmo handle was hit."""
        self.update_hover(obj, tool, mx, my, vp_w, vp_h, view, proj, eye)
        if self.active_axis < 0:
            return False

        pos = np.array(obj.transform.position, np.float32)
        ax  = AX[self.active_axis]
        ro, rd = _screen_ray(mx, my, vp_w, vp_h, view, proj)

        # Choose drag plane normal: perpendicular to axis, facing camera as much as possible
        if tool == TOOL_ROTATE:
            # ring lies in the plane whose normal is the axis
            n = ax.copy()
        else:
            # plane contains the axis, faces the camera
            to_cam = eye - pos
            to_cam /= np.linalg.norm(to_cam) + 1e-10
            n = np.cross(ax, np.cross(to_cam, ax))
            nl = np.linalg.norm(n)
            n = n/nl if nl > 1e-6 else to_cam

        self._plane_n = n
        self._plane_d = float(np.dot(n, pos))
        hit = _ray_plane(ro, rd, n, self._plane_d)
        if hit is None:
            return False

        self._hit0  = hit
        self._pos0  = list(obj.transform.position)
        self._rot0  = list(obj.transform.rotation)
        self._scl0  = list(obj.transform.scale)
        self._tool  = tool
        self._axis  = self.active_axis
        self.dragging = True
        return True

    def update_drag(self, obj, mx, my, vp_w, vp_h, view, proj):
        if not self.dragging: return
        ro, rd = _screen_ray(mx, my, vp_w, vp_h, view, proj)
        hit = _ray_plane(ro, rd, self._plane_n, self._plane_d)
        if hit is None: return

        delta = hit - self._hit0
        ax    = AX[self._axis]

        if self._tool == TOOL_TRANSLATE:
            move = float(np.dot(delta, ax))
            p = list(self._pos0)
            p[self._axis] += move
            obj.transform.position = p

        elif self._tool == TOOL_ROTATE:
            # measure angular displacement around the axis
            # project hit and hit0 onto the ring plane, measure angle between them
            c = np.array(self._pos0, np.float32)
            v0 = self._hit0 - c;  v0 -= np.dot(v0, ax)*ax
            v1 = hit         - c;  v1 -= np.dot(v1, ax)*ax
            l0 = np.linalg.norm(v0); l1 = np.linalg.norm(v1)
            if l0 < 1e-6 or l1 < 1e-6: return
            v0 /= l0; v1 /= l1
            cos_a = float(np.clip(np.dot(v0, v1), -1, 1))
            cross  = np.cross(v0, v1)
            sign   = np.sign(float(np.dot(cross, ax)))
            angle  = np.degrees(np.arccos(cos_a)) * (sign if sign != 0 else 1)
            r = list(self._rot0)
            r[self._axis] += angle
            obj.transform.rotation = r

        elif self._tool == TOOL_SCALE:
            move = float(np.dot(delta, ax))
            factor = 1.0 + move * 0.9
            factor = max(0.01, factor)
            s = list(self._scl0)
            s[self._axis] = self._scl0[self._axis] * factor
            obj.transform.scale = s

    def end_drag(self):
        self.dragging = False
        self._hit0    = None


# ── math helpers 

def _T(pos):
    """row-major translation: translation in row 3"""
    m = np.eye(4, dtype=np.float32)
    m[3, 0:3] = pos
    return m

def _S(s):
    m = np.eye(4, dtype=np.float32)
    m[0,0] = m[1,1] = m[2,2] = s
    return m

def _screen_ray(mx, my, vp_w, vp_h, view, proj):
    """
    Unproject mouse pixel to world-space ray.
    Matrices are row-major (matches renderer.py).
    Screen Y: 0 = top, increases downward.
    """
    ndcx =  (2.0 * mx / vp_w) - 1.0
    ndcy = -(2.0 * my / vp_h) + 1.0   # flip: screen-down -> NDC-up

    inv_proj = np.linalg.inv(proj)
    inv_view = np.linalg.inv(view)

    def unproj(ndcz):
        # clip vector as row vector, multiply on right
        clip = np.array([[ndcx, ndcy, ndcz, 1.0]], np.float32)  # (1,4)
        v = clip @ inv_proj;   v /= v[0,3]
        w = v    @ inv_view;   w /= w[0,3]
        return w[0, :3]

    near = unproj(-1.0)
    far  = unproj( 1.0)
    d = far - near
    n = np.linalg.norm(d)
    if n < 1e-10: d = np.array([0,0,-1], np.float32)
    else:         d /= n
    return near, d

def _ray_plane(ro, rd, n, d):
    denom = float(np.dot(rd, n))
    if abs(denom) < 1e-8: return None
    t = (d - float(np.dot(ro, n))) / denom
    if t < 0: return None
    return ro + rd * float(t)

def _project(p, view, proj, vp_w, vp_h):
    """project world point to screen pixel (x, y)"""
    v = np.array([*p, 1.0], np.float32)
    clip = v @ view @ proj
    if abs(clip[3]) < 1e-8:
        return None
    ndc = clip[:3] / clip[3]
    sx = ( ndc[0] + 1.0) * 0.5 * vp_w
    sy = (-ndc[1] + 1.0) * 0.5 * vp_h
    return np.array([sx, sy], np.float32)

def _screen_seg_dist(p0, p1):
    """2D distance from origin (0,0) to segment p0->p1"""
    d = p1 - p0
    l2 = float(np.dot(d, d))
    if l2 < 1e-8:
        return float(np.linalg.norm(p0))
    t = max(0.0, min(1.0, float(np.dot(-p0, d)) / l2))
    closest = p0 + d * t
    return float(np.linalg.norm(closest))

def _pick_arrow(origin, scale, ro, rd, view=None, proj=None, vp_w=1, vp_h=1, mx=0, my=0):
    """screen-space picking: compare pixel distance to each axis arrow"""
    PIXEL_THRESH = 14.0   # pixels — generous so it's easy to click
    best_i, best_d = -1, PIXEL_THRESH
    for i, ax in enumerate(AX):
        tip = origin + ax * scale * 1.1
        s0 = _project(origin, view, proj, vp_w, vp_h)
        s1 = _project(tip,    view, proj, vp_w, vp_h)
        if s0 is None or s1 is None:
            continue
        # distance from mouse pixel to this screen-space segment
        mouse = np.array([mx, my], np.float32)
        d = _screen_seg_dist(s0 - mouse, s1 - mouse)
        if d < best_d:
            best_d = d; best_i = i
    return best_i

def _pick_ring(origin, scale, ro, rd, view=None, proj=None, vp_w=1, vp_h=1, mx=0, my=0):
    """screen-space ring picking: project 16 ring sample points, find closest to mouse"""
    PIXEL_THRESH = 14.0
    best_i, best_d = -1, PIXEL_THRESH
    segs = 16
    for i, ax in enumerate(AX):
        a1 = AX[(i+1)%3]; a2 = AX[(i+2)%3]
        mouse = np.array([mx, my], np.float32)
        for j in range(segs):
            t0 = 2*np.pi * j     / segs
            t1 = 2*np.pi * (j+1) / segs
            p0 = origin + (np.cos(t0)*a1 + np.sin(t0)*a2) * scale
            p1 = origin + (np.cos(t1)*a1 + np.sin(t1)*a2) * scale
            s0 = _project(p0, view, proj, vp_w, vp_h)
            s1 = _project(p1, view, proj, vp_w, vp_h)
            if s0 is None or s1 is None: continue
            d = _screen_seg_dist(s0 - mouse, s1 - mouse)
            if d < best_d:
                best_d = d; best_i = i
    return best_i

def _seg_ray_dist(seg_a, seg_b, ro, rd):
    """min distance from ray to line segment"""
    u  = seg_b - seg_a
    ul = float(np.linalg.norm(u))
    if ul < 1e-8: return float(np.linalg.norm(np.cross(ro - seg_a, rd)))
    u /= ul
    w  = seg_a - ro
    b  = float(np.dot(u, rd))
    denom = 1.0 - b*b
    if abs(denom) < 1e-8:
        sc = 0.0
    else:
        sc = float(np.dot(u, w) - b*np.dot(rd, w)) / denom
        sc = max(0.0, min(ul, sc))
    tc = float(np.dot(rd, w)) + b*sc
    closest = (seg_a + u*sc) - (ro + rd*tc)
    return float(np.linalg.norm(closest))

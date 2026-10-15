"""Collision capsules and contact checks for technique authoring (CLAUDE.md, phase 7).

Every deforming bone of a judoka gets one capsule (a segment with a radius), fitted to the vertices
nearest to the bone and stored in bone-local rest coordinates in capsules.json, so it follows the
pose. check_contacts() samples the Blender timeline frame by frame (the exported YAML reproduces the
timeline, see technique_tools.export_yaml) and reports where capsules of the two judoka, or a capsule
and the mat (z = 0), overlap by more than a tolerance.

Typical use in a technique script, after keying:
    report = contact.check_contacts(allow=[contact.Allow("Tori:RightHand", "Uki:Chest", 0.04)])
    contact.print_report(report)

Fit the capsules again after changing the judoka mesh (tools/blender/build_judoka.py):
    contact.fit_capsules(); contact.save_capsules()
"""
import fnmatch
import json
import math
import os
from dataclasses import dataclass

import bpy
from mathutils import Vector

CAPSULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capsules.json") \
    if "__file__" in globals() else r"C:\proj\judo\tools\blender\capsules.json"

JUDOKA = ("Tori", "Uki")
MAT = "Mat"

# Default allowed overlap (m). Capsules sit a little inside the gi, so touching cloth reads as ~0.
TOLERANCE = 0.015

_capsules = None  # {bone: (p0, p1, radius)} in bone-local rest coordinates; same mesh for both judoka


# --- fitting -----------------------------------------------------------------------------------

# How each bone's capsule is shaped: along the bone (default), across the body at mid-height
# (the torso is wider than deep), a sphere (head) or along the principal axis of its vertices (feet).
SHAPES = {"Hips": "lateral", "Spine": "lateral", "Chest": "lateral", "Head": "sphere",
          "LeftFoot": "pca", "RightFoot": "pca"}


def fit_capsules(mesh="Tori_Body", percentile=80):
    """Fit one capsule per deforming bone (rest pose) to the vertices nearest to that bone's segment.

    The radius is the given percentile of the vertices' distance to the capsule's axis, so the
    capsule stays slightly inside the cloth. See SHAPES for the axis per bone."""
    import numpy as np
    global _capsules
    obj = bpy.data.objects[mesh]
    arm = obj.parent
    bones = [b for b in arm.data.bones if b.use_deform]
    segments = [(b, b.head_local, b.tail_local) for b in bones]
    points = {b.name: [] for b in bones}
    for v in obj.data.vertices:  # mesh space == armature space
        best = min(segments, key=lambda s: segment_distance(v.co, v.co, s[1], s[2])[0])
        points[best[0].name].append(v.co)

    capsules = {}
    hip_low = min(b.head_local.z for b in bones if b.name.endswith("UpLeg")) - 0.08
    for b in bones:
        p = np.array([tuple(b.matrix_local.inverted() @ co) for co in points[b.name]])
        shape = SHAPES.get(b.name, "axial")
        if shape == "lateral":
            # Every vertex in the bone's height band (arms excluded): nearest-bone assignment would
            # give the pelvis to the thighs. Radius = half the depth, ends at the width minus that.
            low = hip_low if b.parent is None else b.head_local.z
            band = np.array([tuple(v.co) for v in obj.data.vertices
                             if low <= v.co.z <= b.tail_local.z and abs(v.co.x) < 0.22])
            y0, y1 = np.percentile(band[:, 1], [8, 92])
            half_width = float(np.percentile(np.abs(band[:, 0]), 92))
            r = float(y1 - y0) / 2
            w = max(half_width - r, 0.0)
            y, z = float(y0 + y1) / 2, (low + b.tail_local.z) / 2
            to_local = b.matrix_local.inverted()
            ends = (to_local @ Vector((-w, y, z)), to_local @ Vector((w, y, z)))
        elif shape == "sphere":
            centre = p.mean(axis=0)
            r = float(np.percentile(np.linalg.norm(p - centre, axis=1), percentile))
            ends = (centre, centre)
        else:
            if shape == "axial":  # bone-local Y runs from head (0) to tail (length)
                centre, axis = np.array([0.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])
            else:  # pca
                centre = p.mean(axis=0)
                axis = np.linalg.svd(p - centre, full_matrices=False)[2][0]
            along = (p - centre) @ axis
            r = float(np.percentile(np.linalg.norm((p - centre) - np.outer(along, axis), axis=1), percentile))
            if shape == "axial":
                lo, hi = 0.0, b.length
            else:
                lo, hi = float(np.percentile(along, 2)) + r, float(np.percentile(along, 98)) - r
                if lo > hi:
                    lo = hi = (lo + hi) / 2
            ends = (centre + lo * axis, centre + hi * axis)
        capsules[b.name] = ([round(float(x), 4) for x in ends[0]], [round(float(x), 4) for x in ends[1]], round(r, 4))
    _capsules = capsules
    return capsules


def save_capsules(path=CAPSULES_FILE):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(_capsules, f, indent=1, sort_keys=True)
        f.write("\n")


def capsules():
    global _capsules
    if _capsules is None:
        with open(CAPSULES_FILE, encoding="utf-8") as f:
            _capsules = json.load(f)
    return _capsules


# --- geometry ----------------------------------------------------------------------------------

def world_capsules(arm):
    """{bone: (p0, p1, radius)} in Blender world space for the armature's current pose."""
    arm = bpy.data.objects[arm] if isinstance(arm, str) else arm
    result = {}
    for bone, (p0, p1, r) in capsules().items():
        pb = arm.pose.bones[bone]
        m = arm.matrix_world @ pb.matrix  # bone-local rest coordinates -> posed world
        result[bone] = (m @ Vector(p0), m @ Vector(p1), r)
    return result


def segment_distance(p1, q1, p2, q2):
    """Closest distance between segments p1-q1 and p2-q2, and the closest points (Ericson, RTCD 5.1.9)."""
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e, f = d1.dot(d1), d2.dot(d2), d2.dot(r)
    eps = 1e-12
    if a <= eps and e <= eps:
        s = t = 0.0
    elif a <= eps:
        s, t = 0.0, min(max(f / e, 0.0), 1.0)
    else:
        c = d1.dot(r)
        if e <= eps:
            t, s = 0.0, min(max(-c / a, 0.0), 1.0)
        else:
            b = d1.dot(d2)
            denom = a * e - b * b
            s = min(max((b * f - c * e) / denom, 0.0), 1.0) if denom > eps else 0.0
            t = (b * s + f) / e
            if t < 0:
                t, s = 0.0, min(max(-c / a, 0.0), 1.0)
            elif t > 1:
                t, s = 1.0, min(max((b - c) / a, 0.0), 1.0)
    c1, c2 = p1 + d1 * s, p2 + d2 * t
    return (c1 - c2).length, c1, c2


def penetration(c1, c2):
    """Overlap depth of two capsules (> 0 = interpenetrating), and the direction pushing c1 out of c2."""
    dist, a, b = segment_distance(c1[0], c1[1], c2[0], c2[1])
    normal = (a - b).normalized() if dist > 1e-9 else Vector((0, 0, 1))
    return c1[2] + c2[2] - dist, normal


def mat_penetration(c):
    """How far a capsule sinks below the mat (z = 0)."""
    return c[2] - min(c[0].z, c[1].z)


# --- checks ------------------------------------------------------------------------------------

@dataclass
class Allow:
    """Contact allowed between two capsules ("Judoka:BonePattern", fnmatch, or "Mat"), with its own
    tolerance and optionally only within a time range (seconds, inclusive)."""
    a: str
    b: str
    tolerance: float = 0.04
    start: float = -math.inf
    end: float = math.inf

    def matches(self, x, y, time):
        if not self.start <= time <= self.end:
            return False
        return ((fnmatch.fnmatchcase(x, self.a) and fnmatch.fnmatchcase(y, self.b)) or
                (fnmatch.fnmatchcase(x, self.b) and fnmatch.fnmatchcase(y, self.a)))


def tolerance_for(x, y, time, allow, default=TOLERANCE):
    return max([default] + [rule.tolerance for rule in allow if rule.matches(x, y, time)])


def contacts_at(time, allow=(), tolerance=TOLERANCE, judoka=JUDOKA):
    """Overlaps beyond tolerance at the current frame: [(a, b, depth, allowed_tolerance)]."""
    caps = {j: world_capsules(j) for j in judoka}
    found = []
    tori, uki = judoka
    for bt, ct in caps[tori].items():
        for bu, cu in caps[uki].items():
            depth, _ = penetration(ct, cu)
            if depth > 0:
                x, y = f"{tori}:{bt}", f"{uki}:{bu}"
                tol = tolerance_for(x, y, time, allow, tolerance)
                if depth > tol:
                    found.append((x, y, depth, tol))
    for j in judoka:
        for bone, c in caps[j].items():
            depth = mat_penetration(c)
            if depth > 0:
                x = f"{j}:{bone}"
                tol = tolerance_for(x, MAT, time, allow, tolerance)
                if depth > tol:
                    found.append((x, MAT, depth, tol))
    return found


def frames(start=None, end=None):
    scene = bpy.context.scene
    return range(scene.frame_start if start is None else start, (scene.frame_end if end is None else end) + 1)


def check_contacts(allow=(), tolerance=TOLERANCE, start=None, end=None):
    """Sample every frame of the timeline; return {(a, b): dict(depth, time, first, last, tolerance)}
    for each pair that overlaps beyond its tolerance (worst depth and when)."""
    scene = bpy.context.scene
    fps = scene.render.fps
    report = {}
    for f in frames(start, end):
        scene.frame_set(f)
        t = f / fps
        for a, b, depth, tol in contacts_at(t, allow, tolerance):
            entry = report.setdefault((a, b), dict(depth=0.0, time=t, first=t, last=t, tolerance=tol))
            entry["last"] = t
            if depth > entry["depth"]:
                entry.update(depth=depth, time=t, tolerance=tol)
    return report


def print_report(report, title="Contact report", limit=25):
    """Print the pairs beyond tolerance, deepest first (at most `limit` lines)."""
    if not report:
        print(f"{title}: no penetration beyond tolerance.")
        return
    print(f"{title}: {len(report)} pair(s) beyond tolerance")
    for (a, b), e in sorted(report.items(), key=lambda kv: -kv[1]["depth"])[:limit]:
        print(f"  {a:24} {b:24} {e['depth'] * 100:5.1f} cm (tol {e['tolerance'] * 100:.1f}) "
              f"worst at {e['time']:.2f}s, {e['first']:.2f}-{e['last']:.2f}s")
    if len(report) > limit:
        print(f"  ... {len(report) - limit} more")


# --- resolving ---------------------------------------------------------------------------------

def separate(mover, other, allow=(), tolerance=TOLERANCE, horizontal=True, iterations=20):
    """Push `mover`'s root out of `other` (current frame) along the deepest overlap until no pair
    exceeds its tolerance. Returns the total translation (Blender space). Call it in a pose
    function before keying, e.g. after placing Uki against Tori."""
    arm = bpy.data.objects[mover]
    t = bpy.context.scene.frame_current / bpy.context.scene.render.fps
    moved = Vector()
    for _ in range(iterations):
        caps_m, caps_o = world_capsules(mover), world_capsules(other)
        worst, push = 0.0, None
        for bm, cm in caps_m.items():
            for bo, co in caps_o.items():
                depth, normal = penetration(cm, co)
                excess = depth - tolerance_for(f"{mover}:{bm}", f"{other}:{bo}", t, allow, tolerance)
                if excess > worst:
                    worst, push = excess, normal
        if push is None:
            break
        if horizontal:
            push = Vector((push.x, push.y, 0))
            if push.length < 1e-6:
                break
            push.normalize()
        step = push * (worst + 0.002)
        arm.location += step
        moved += step
        bpy.context.view_layer.update()
    return moved


# --- debugging ---------------------------------------------------------------------------------

def show_capsules(judoka=JUDOKA, collection="TMP_Capsules"):
    """Add mesh objects for the capsules at the current frame (delete with hide_capsules())."""
    import bmesh
    hide_capsules(collection)
    coll = bpy.data.collections.new(collection)
    bpy.context.scene.collection.children.link(coll)
    for j in judoka:
        for bone, (p0, p1, r) in world_capsules(j).items():
            bm = bmesh.new()
            for p in (p0, p1):
                bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r,
                                          matrix=__import__("mathutils").Matrix.Translation(p))
            axis = p1 - p0
            if axis.length > 1e-4:
                rot = Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4()
                bmesh.ops.create_cone(bm, cap_ends=False, segments=12, radius1=r, radius2=r, depth=axis.length,
                                      matrix=__import__("mathutils").Matrix.Translation((p0 + p1) / 2) @ rot)
            mesh = bpy.data.meshes.new(f"cap_{j}_{bone}")
            bm.to_mesh(mesh)
            bm.free()
            coll.objects.link(bpy.data.objects.new(mesh.name, mesh))


def hide_capsules(collection="TMP_Capsules"):
    coll = bpy.data.collections.get(collection)
    if coll:
        for o in list(coll.objects):
            mesh = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(coll)

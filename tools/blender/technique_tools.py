"""Pose the judoka in Blender and export the poses as technique YAML (data/techniques/*.yaml).

Blender is the authoring tool for technique keyframes: a technique script (tools/blender/techniques/)
poses Tori and Uki per keyframe with these helpers, keys the poses on the timeline, and calls
export_yaml(). The maths mirrors the Godot player (src/Playback/JudokaRig.cs), so a pose seen in
Blender is the pose played in Godot at that keyframe.

Conventions (see CLAUDE.md section 2):
- Godot space: Y-up; Blender (x, y, z) -> Godot (x, z, -y).
- Root position = armature origin (between the feet, on the floor); root rotation in Godot space.
- Bone deltas are expressed in the character frame "A": X = character's right, Y = up,
  -Z = facing direction. A bone's accumulated rotation is parent_accumulated @ delta.
- Euler angles are Godot EulerOrder.Xyz (R = Rx @ Ry @ Rz), which is Blender's Euler order 'ZYX'.
"""
import math
import re

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

FPS = 50  # keyframe times map to frames as round(time * FPS)

B2G = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))   # Blender world -> Godot world
B2A = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))   # Blender armature space -> character frame A

# Must match JudoVisualizer.Data.BoneNames.Skeleton (parents before children).
POSABLE = ["Hips", "Spine", "Chest", "Neck", "Head",
           "LeftShoulder", "LeftArm", "LeftForearm", "LeftHand",
           "RightShoulder", "RightArm", "RightForearm", "RightHand",
           "LeftUpLeg", "LeftLeg", "LeftFoot", "RightUpLeg", "RightLeg", "RightFoot"]


# --- conversions -------------------------------------------------------------------------------

def godot_euler(m3):
    """Rotation matrix -> Godot EulerOrder.Xyz angles in degrees."""
    return tuple(math.degrees(a) for a in m3.to_euler('ZYX'))


def from_godot_euler(degrees):
    return Euler([math.radians(a) for a in degrees], 'ZYX').to_matrix()


def snake(name):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def _arm(name_or_obj):
    return bpy.data.objects[name_or_obj] if isinstance(name_or_obj, str) else name_or_obj


def accumulated(pb):
    """Rotation taking the bone from rest to its current pose, in the character frame A."""
    if pb is None:
        return Matrix.Identity(3)
    r = pb.matrix.to_3x3().normalized() @ pb.bone.matrix_local.to_3x3().inverted()
    return B2A @ r @ B2A.transposed()


def delta(pb):
    """The bone's own delta (what the YAML stores), in frame A."""
    return accumulated(pb.parent).inverted() @ accumulated(pb)


# --- posing ------------------------------------------------------------------------------------

def _update():
    bpy.context.view_layer.update()


def reset(arm):
    """Clear the pose and temporary constraints."""
    arm = _arm(arm)
    for pb in arm.pose.bones:
        for c in [c for c in pb.constraints if c.name.startswith("TMP_")]:
            pb.constraints.remove(c)
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = Matrix.Identity(4)
    _update()


def place(arm, position, rotation=(0, 0, 0)):
    """Root position/rotation in Godot space (as written in the YAML)."""
    arm = _arm(arm)
    p = Vector(position)
    r = B2G.transposed() @ from_godot_euler(rotation) @ B2G
    arm.rotation_mode = 'QUATERNION'
    arm.matrix_world = Matrix.Translation((p.x, -p.z, p.y)) @ r.to_4x4()
    _update()


def _set_accumulated(pb, acc):
    r = B2A.transposed() @ acc @ B2A @ pb.bone.matrix_local.to_3x3()
    pb.matrix = Matrix.Translation(pb.head) @ r.to_4x4()
    _update()


def rot(arm, bone, degrees):
    """Set a bone's delta (Godot Euler XYZ degrees in frame A), exactly as the YAML would."""
    pb = _arm(arm).pose.bones[bone]
    _set_accumulated(pb, accumulated(pb.parent) @ from_godot_euler(degrees))


def turn(arm, bone, degrees):
    """Add a rotation (Godot Euler XYZ degrees in frame A) on top of the bone's current delta."""
    pb = _arm(arm).pose.bones[bone]
    _set_accumulated(pb, accumulated(pb) @ from_godot_euler(degrees))


def aim(arm, bone, direction):
    """Point a bone (head -> tail) along a direction given in frame A, with minimal twist."""
    pb = _arm(arm).pose.bones[bone]
    rest_dir = (B2A @ (pb.bone.tail_local - pb.bone.head_local)).normalized()
    acc = accumulated(pb)
    q = (acc @ rest_dir).rotation_difference(Vector(direction).normalized())
    _set_accumulated(pb, q.to_matrix() @ acc)


def ik(arm, bone, target_arm, target_bone, chain=3, pole=None):
    """Solve an IK chain ending in `bone` onto another bone's head, then bake it into the pose.
    pole: optional direction in frame A (relative to the chain root) the middle joint bends towards."""
    arm, target_arm = _arm(arm), _arm(target_arm)
    pb = arm.pose.bones[bone]
    c = pb.constraints.new('IK')
    c.name = "TMP_IK"
    c.target, c.subtarget, c.chain_count, c.use_tail = target_arm, target_bone, chain, True
    empty = None
    if pole is not None:
        root = pb
        for _ in range(chain - 1):
            root = root.parent
        empty = bpy.data.objects.new("TMP_Pole", None)
        bpy.context.scene.collection.objects.link(empty)
        head_world = arm.matrix_world @ root.head
        empty.location = head_world + arm.matrix_world.to_3x3() @ (B2A.transposed() @ Vector(pole))
        c.pole_target, c.pole_angle = empty, math.radians(-90)
    _update()
    bake(arm)
    if empty:
        bpy.data.objects.remove(empty, do_unlink=True)


def bone_pos(arm, bone, tail=False):
    """World position (Blender space) of a bone's head (or tail)."""
    arm = _arm(arm)
    pb = arm.pose.bones[bone]
    return arm.matrix_world @ (pb.tail if tail else pb.head)


def pin(arm, bone, world_point, tail=False):
    """Translate the root so a bone's head (or tail) lands on a world point (Blender space)."""
    arm = _arm(arm)
    arm.location += Vector(world_point) - bone_pos(arm, bone, tail)
    _update()


def ground(arm):
    """Move the root vertically so the lowest foot rests on the floor (keeps knee bends grounded)."""
    arm = _arm(arm)
    w = arm.matrix_world
    soles = []
    for side in ("Left", "Right"):
        pb = arm.pose.bones[f"{side}Foot"]
        soles += [(w @ pb.head).z - 0.09, (w @ pb.tail).z - 0.02]  # ankle / toe height above the sole
    arm.location.z -= min(soles)
    _update()


def bake(arm):
    """Make the visual pose (including constraints) the actual pose and drop temporary constraints."""
    arm = _arm(arm)
    mats = {pb.name: pb.matrix.copy() for pb in arm.pose.bones}
    for pb in arm.pose.bones:
        for c in [c for c in pb.constraints if c.name.startswith("TMP_")]:
            pb.constraints.remove(c)
    _update()
    for pb in arm.pose.bones:  # parents before children
        pb.matrix = mats[pb.name]
        _update()


def fcurves(arm):
    """The armature's F-curves (Blender 5 layered actions), or an empty list when not animated."""
    arm = _arm(arm)
    ad = arm.animation_data
    if not ad or not ad.action or not ad.action.layers:
        return []
    return ad.action.layers[0].strips[0].channelbag(ad.action_slot).fcurves


def _keyed_quaternion(curves, data_path, frame):
    """The animated quaternion at `frame`, or None if that channel has no keys yet."""
    found = [curves.find(data_path, index=i) for i in range(4)] if curves else []
    if not found or any(fc is None or not fc.keyframe_points for fc in found):
        return None
    return Quaternion([fc.evaluate(frame) for fc in found])


def key(arm, frame, bones=None, root=True):
    """Key the root transform and bone rotations (all, or the named `bones`) at `frame`.

    Keys are linear, like the Godot player's interpolation; easing is added explicitly (ease()) and
    baked into in-between keyframes on export. Each quaternion is flipped if needed to stay on the
    same hemisphere as the animation around it, so Blender interpolates the short way like Godot's slerp."""
    arm = _arm(arm)
    names = bones if bones is not None else [pb.name for pb in arm.pose.bones]
    curves = fcurves(arm)
    targets = ([(arm, "rotation_quaternion")] if root else []) +               [(arm.pose.bones[b], f'pose.bones["{b}"].rotation_quaternion') for b in names]
    for owner, path in targets:
        ref = _keyed_quaternion(curves, path, frame)
        if ref is not None:
            q = owner.rotation_quaternion.copy()
            q.make_compatible(ref)
            owner.rotation_quaternion = q
    if root:
        arm.keyframe_insert("location", frame=frame)
        arm.keyframe_insert("rotation_quaternion", frame=frame)
    for b in names:
        arm.pose.bones[b].keyframe_insert("rotation_quaternion", frame=frame)
    # keyframe_insert ignores the "new interpolation" preference: set it on the new keys.
    paths = {path for _, path in targets} | ({"location"} if root else set())
    for fc in fcurves(arm):
        if fc.data_path in paths:
            for k in fc.keyframe_points:
                if abs(k.co.x - frame) < 0.5:
                    k.interpolation = 'LINEAR'


# --- export ------------------------------------------------------------------------------------

def _num(x, digits):
    x = round(x, digits)
    return 0.0 if x == 0 else x


def export_yaml(path, meta, keyframes, judoka=(("tori", "Tori"), ("uki", "Uki"))):
    """Sample the keyed poses at each keyframe and write technique YAML.

    meta: dict with technique_name, dutch_name, waza_group, category, code, difficulty, kyu_grade,
          belt_name, belt_hex, u18 (optional, default False), source, duration_seconds.
          keyframes: [dict(time, phase, description)].
    Bones that never leave the rest pose are omitted; others are written in every keyframe."""
    scene = bpy.context.scene
    samples = []
    for kf in keyframes:
        scene.frame_set(round(kf["time"] * FPS))
        frame = {}
        for role, name in judoka:
            arm = _arm(name)
            w = arm.matrix_world
            p = B2G @ w.translation
            r = B2G @ w.to_3x3().normalized() @ B2G.transposed()
            frame[role] = (tuple(_num(x, 3) for x in p), tuple(_num(x, 1) for x in godot_euler(r)),
                           {b: tuple(_num(x, 1) for x in godot_euler(delta(arm.pose.bones[b]))) for b in POSABLE})
        samples.append(frame)

    used = {role: [b for b in POSABLE if any(any(abs(a) >= 0.1 for a in s[role][2][b]) for s in samples)]
            for role, _ in judoka}

    def vec(v):
        return "[" + ", ".join(repr(float(x)) for x in v) + "]"

    lines = [f"# Generated by tools/blender/techniques/ - edit the technique script, not this file.",
             f'technique_name: "{meta["technique_name"]}"',
             f'dutch_name: "{meta["dutch_name"]}"',
             f'waza_group: "{meta["waza_group"]}"',
             f'category: "{meta["category"]}"',
             f'code: "{meta["code"]}"',
             f'difficulty: "{meta["difficulty"]}"',
             f'kyu_grade: {meta["kyu_grade"]}',
             "belt_color:",
             f'  name: "{meta["belt_name"]}"',
             f'  hex: "{meta["belt_hex"]}"',
             f'u18: {"true" if meta.get("u18") else "false"}',
             f'source: "{meta["source"]}"',
             f'duration_seconds: {meta["duration_seconds"]}',
             "keyframes:"]
    for kf, s in zip(keyframes, samples):
        lines += [f'  - time: {kf["time"]}',
                  f'    phase: "{kf["phase"]}"',
                  f'    description: "{kf["description"]}"']
        for role, _ in judoka:
            pos, rot_, bones = s[role]
            lines += [f"    {role}:", f"      position: {vec(pos)}", f"      rotation: {vec(rot_)}"]
            if used[role]:
                lines.append("      bones:")
                lines += [f"        {snake(b)}: {vec(bones[b])}" for b in used[role]]
        lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return path

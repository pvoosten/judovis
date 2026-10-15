"""Weight and motion for technique authoring (CLAUDE.md, phase 7): planted feet and steps.

These functions work on the keyed Blender timeline: run them in a technique script after the
keyframe poses have been keyed (technique_tools.key), in time order. They add keys on every frame
of the range they touch; technique_tools.export_yaml bakes such frames into in-between keyframes.

    motion.plant("Tori", "Left", 0, 45)        # left foot stays where it is at frame 0
    motion.step("Tori", "Right", 20, 35)       # lift, move and put down the right foot
    motion.print_sliding(motion.foot_sliding("Tori"))
"""
import math

import bpy
from mathutils import Matrix, Vector

import technique_tools as tt

ANKLE_HEIGHT = 0.09  # ankle (foot head) above the sole, as in technique_tools.ground()
TOE_HEIGHT = 0.02    # toe (foot tail) above the sole


def _update():
    bpy.context.view_layer.update()


def _aim_bone(pb, direction):
    """Rotate a pose bone about its head so it points along `direction` (armature space)."""
    current = (pb.tail - pb.head).normalized()
    q = current.rotation_difference(direction.normalized())
    pb.matrix = Matrix.Translation(pb.head) @ (q.to_matrix() @ pb.matrix.to_3x3()).to_4x4()
    _update()


def foot_matrix(arm, side):
    """World matrix of the foot bone (head = ankle)."""
    arm = tt._arm(arm)
    return arm.matrix_world @ arm.pose.bones[f"{side}Foot"].matrix


def leg_ik(arm, side, ankle, foot_rotation=None):
    """Two-bone IK: bend hip and knee so the ankle reaches `ankle` (world), keeping the knee in its
    current bending plane; then give the foot the world rotation `foot_rotation` (3x3) if given.
    Returns the remaining distance to the target (0 unless out of reach)."""
    arm = tt._arm(arm)
    up, low, foot = (arm.pose.bones[f"{side}{b}"] for b in ("UpLeg", "Leg", "Foot"))
    to_arm = arm.matrix_world.inverted()
    hip, knee, target = up.head.copy(), low.head.copy(), to_arm @ Vector(ankle)
    l1, l2 = (knee - hip).length, (foot.head - low.head).length
    d = target - hip
    dist = min(max(d.length, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
    axis = d.normalized()
    bend = (knee - hip) - axis * (knee - hip).dot(axis)
    if bend.length < 1e-4:
        bend = Vector((0, -1, 0)) - axis * Vector((0, -1, 0)).dot(axis)  # knee forward (character faces -Y)
    bend.normalize()
    a = (l1 * l1 + dist * dist - l2 * l2) / (2 * dist)
    new_knee = hip + axis * a + bend * math.sqrt(max(l1 * l1 - a * a, 0.0))
    _aim_bone(up, new_knee - hip)
    _aim_bone(low, hip + axis * dist - low.head)
    if foot_rotation is not None:
        r = to_arm.to_3x3() @ foot_rotation
        foot.matrix = Matrix.Translation(foot.head) @ r.to_4x4()
        _update()
    return (arm.matrix_world @ foot.head - Vector(ankle)).length


def _leg_bones(side):
    return [f"{side}UpLeg", f"{side}Leg", f"{side}Foot"]


def plant(arm, side, frame_from, frame_to):
    """Keep `side`'s foot ("Left"/"Right") fixed on the mat from frame_from to frame_to (inclusive),
    where it is at frame_from: leg IK on every frame against the moving hips. Returns the worst
    distance the ankle could not reach (> 0.01 m means the hips move too far for the leg)."""
    scene = bpy.context.scene
    scene.frame_set(frame_from)
    m = foot_matrix(arm, side)
    worst = 0.0
    for f in range(frame_from, frame_to + 1):
        scene.frame_set(f)
        worst = max(worst, leg_ik(arm, side, m.translation, m.to_3x3()))
        tt.key(arm, f, bones=_leg_bones(side), root=False)
    if worst > 0.01:
        print(f"plant {arm} {side}: ankle out of reach by {worst * 100:.1f} cm")
    return worst


def step(arm, side, frame_from, frame_to, height=0.06):
    """Move `side`'s foot from where it is at frame_from to where it is at frame_to: it lifts by
    `height` (m), travels with ease-in/out and is put down. Returns the worst unreachable distance."""
    scene = bpy.context.scene
    scene.frame_set(frame_from)
    m0 = foot_matrix(arm, side)
    scene.frame_set(frame_to)
    m1 = foot_matrix(arm, side)
    q0, q1 = m0.to_quaternion(), m1.to_quaternion()
    q1.make_compatible(q0)
    worst = 0.0
    for f in range(frame_from + 1, frame_to):
        s = (f - frame_from) / (frame_to - frame_from)
        e = s * s * (3 - 2 * s)  # smoothstep
        pos = m0.translation.lerp(m1.translation, e) + Vector((0, 0, height * math.sin(math.pi * s)))
        scene.frame_set(f)
        worst = max(worst, leg_ik(arm, side, pos, q0.slerp(q1, e).to_matrix()))
        tt.key(arm, f, bones=_leg_bones(side), root=False)
    if worst > 0.01:
        print(f"step {arm} {side}: ankle out of reach by {worst * 100:.1f} cm")
    return worst


def sole_points(arm, side):
    """World positions of the heel and toe contact points of a foot, at sole level."""
    arm = tt._arm(arm)
    pb = arm.pose.bones[f"{side}Foot"]
    w = arm.matrix_world
    return {"heel": w @ pb.head - Vector((0, 0, ANKLE_HEIGHT)), "toe": w @ pb.tail - Vector((0, 0, TOE_HEIGHT))}


def foot_sliding(arm, start=None, end=None, height=0.02, speed=0.1):
    """Find frames where a heel or toe that is on the mat (below `height`) at two consecutive frames
    moves horizontally faster than `speed` (m/s). Returns {"Tori:Left heel": dict(speed, time,
    distance, first, last)}."""
    scene = bpy.context.scene
    fps = scene.render.fps
    start = scene.frame_start if start is None else start
    end = scene.frame_end if end is None else end
    report, previous = {}, None
    for f in range(start, end + 1):
        scene.frame_set(f)
        points = {f"{arm}:{side} {name}": p for side in ("Left", "Right")
                  for name, p in sole_points(arm, side).items()}
        if previous:
            for name, p in points.items():
                q = previous[name]
                if p.z < height and q.z < height:
                    moved = Vector((p.x - q.x, p.y - q.y)).length
                    v = moved * fps
                    if v > speed:
                        t = f / fps
                        e = report.setdefault(name, dict(speed=0.0, time=t, distance=0.0, first=t, last=t))
                        e["distance"] += moved
                        e["last"] = t
                        if v > e["speed"]:
                            e.update(speed=v, time=t)
        previous = points
    return report


def print_sliding(report, title="Foot sliding"):
    if not report:
        print(f"{title}: none.")
        return
    print(f"{title}:")
    for name, e in sorted(report.items()):
        print(f"  {name:18} slid {e['distance'] * 100:5.1f} cm, up to {e['speed']:.2f} m/s at {e['time']:.2f}s "
              f"({e['first']:.2f}-{e['last']:.2f}s)")

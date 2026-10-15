"""Weight and motion for technique authoring (CLAUDE.md, phase 7): planted feet and steps, centre
of mass and balance, ballistic falls.

These functions work on the keyed Blender timeline: run them in a technique script after the
keyframe poses have been keyed (technique_tools.key), in time order. They add keys on every frame
of the range they touch; technique_tools.export_yaml bakes such frames into in-between keyframes.

    motion.ease(30, "EASE_IN")                 # timing first: segment 30 -> next key starts slowly
    motion.plant("Tori", "Left", 0, 45)        # left foot stays where it is at frame 0
    motion.step("Tori", "Right", 20, 35)       # lift, move and put down the right foot
    motion.print_sliding(motion.foot_sliding("Tori"))
    motion.fall("Uki", 105, 125)               # Uki's centre of mass flies a ballistic path
    motion.print_balance("Tori", motion.balance("Tori"))
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


# --- timing ------------------------------------------------------------------------------------

def ease(frame, easing="EASE_IN_OUT", mode="SINE", judoka=("Tori", "Uki")):
    """Ease the segment that starts at the key on `frame` (up to the next key) for every channel of
    the judoka: easing "EASE_IN" (slow start, e.g. building up kuzushi), "EASE_OUT" (braking, e.g.
    landing) or "EASE_IN_OUT"; mode is a Blender interpolation curve ("SINE", "QUAD", "CUBIC", ...).
    Call it after keying the keyframe poses and before plant/step/fall, which add per-frame keys
    inside segments. The exported YAML bakes the eased motion into in-between keyframes."""
    for j in judoka:
        for fc in tt.fcurves(j):
            for k in fc.keyframe_points:
                if abs(k.co.x - frame) < 0.5:
                    k.interpolation = mode
                    k.easing = easing


# --- centre of mass, balance and falling -------------------------------------------------------

G = 9.81

# Segment mass (fraction of body mass) and centre of mass as a fraction from the bone's head to its
# tail (de Leva 1996, male). Head includes the neck; the trunk is split over Hips/Spine/Chest, whose
# centre is taken at their capsule's centre (None).
SEGMENTS = {
    "Head": (0.0694, 0.5), "Chest": (0.1596, None), "Spine": (0.1633, None), "Hips": (0.1117, None),
    "LeftArm": (0.0271, 0.577), "RightArm": (0.0271, 0.577),
    "LeftForearm": (0.0162, 0.457), "RightForearm": (0.0162, 0.457),
    "LeftHand": (0.0061, 0.79), "RightHand": (0.0061, 0.79),
    "LeftUpLeg": (0.1416, 0.4095), "RightUpLeg": (0.1416, 0.4095),
    "LeftLeg": (0.0433, 0.446), "RightLeg": (0.0433, 0.446),
    "LeftFoot": (0.0137, 0.442), "RightFoot": (0.0137, 0.442),
}


def com(arm):
    """Centre of mass of a judoka in the current pose (Blender world space)."""
    import contact
    arm = tt._arm(arm)
    caps = None
    total = Vector()
    for bone, (mass, along) in SEGMENTS.items():
        pb = arm.pose.bones[bone]
        if along is None:
            caps = caps or contact.world_capsules(arm)
            p0, p1, _ = caps[bone]
            point = (p0 + p1) / 2
        else:
            point = arm.matrix_world @ pb.head.lerp(pb.tail, along)
        total += point * mass
    return total


def support_points(arm, height=0.03):
    """Points where the judoka rests on the mat (xy at z = 0): the corners of every foot whose heel or
    toe is within `height` of the mat, and the lowest point of any other capsule touching the mat."""
    import contact
    arm = tt._arm(arm)
    points = []
    for side in ("Left", "Right"):
        sole = sole_points(arm, side)
        along = Vector((sole["toe"].x - sole["heel"].x, sole["toe"].y - sole["heel"].y))
        across = Vector((-along.y, along.x)).normalized() * 0.045 if along.length > 1e-6 else Vector((0.045, 0))
        for name in ("heel", "toe"):
            p = sole[name]
            if p.z < height:
                points += [Vector((p.x, p.y)) + across, Vector((p.x, p.y)) - across]
    for bone, (p0, p1, r) in contact.world_capsules(arm).items():
        if bone.endswith("Foot"):
            continue
        low = p0 if p0.z < p1.z else p1
        if low.z - r < height:
            points.append(Vector((low.x, low.y)))
    return points


def convex_hull(points):
    """2D convex hull (Andrew's monotone chain), counter-clockwise."""
    pts = sorted({(round(p.x, 5), round(p.y, 5)) for p in points})
    if len(pts) <= 2:
        return [Vector(p) for p in pts]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return [Vector(p) for p in lower[:-1] + upper[:-1]]


def outside_distance(point, hull):
    """How far a 2D point lies outside a convex polygon (0 when inside; inf without a polygon)."""
    if not hull:
        return math.inf
    if len(hull) == 1:
        return (point - hull[0]).length
    inside, best = True, math.inf
    for i, a in enumerate(hull):
        b = hull[(i + 1) % len(hull)]
        edge = b - a
        if len(hull) > 2 and edge.x * (point.y - a.y) - edge.y * (point.x - a.x) < 0:
            inside = False
        t = min(max((point - a).dot(edge) / max(edge.length_squared, 1e-12), 0.0), 1.0)
        best = min(best, (point - (a + edge * t)).length)
    return 0.0 if inside and len(hull) > 2 else best


def balance(arm, start=None, end=None, margin=0.0):
    """Frames where the centre of mass (projected on the mat) lies more than `margin` outside the
    support polygon. Returns dict(worst, time, frames=[(time, distance)]); worst = 0 when balanced."""
    scene = bpy.context.scene
    fps = scene.render.fps
    result = dict(worst=0.0, time=None, frames=[])
    for f in range(scene.frame_start if start is None else start, (scene.frame_end if end is None else end) + 1):
        scene.frame_set(f)
        c = com(arm)
        d = outside_distance(Vector((c.x, c.y)), convex_hull(support_points(arm)))
        if d > margin:
            result["frames"].append((f / fps, d))
            if d > result["worst"]:
                result.update(worst=d, time=f / fps)
    return result


def print_balance(arm, result):
    if not result["frames"]:
        print(f"Balance {arm}: centre of mass always over the support polygon.")
        return
    times = [t for t, _ in result["frames"]]
    worst = "no support" if math.isinf(result["worst"]) else f"{result['worst'] * 100:.1f} cm"
    print(f"Balance {arm}: off balance in {len(times)} frame(s), {times[0]:.2f}-{times[-1]:.2f}s, "
          f"worst {worst} at {result['time']:.2f}s")


def fall(arm, frame_from, frame_to):
    """Move the root so the centre of mass flies a ballistic path (gravity only) from where it is at
    frame_from to where it is at frame_to; the keyed rotations and bone poses are kept. Keys the root
    on every frame in between. Returns the vertical speed at frame_to (m/s, negative = downwards)."""
    scene = bpy.context.scene
    fps = scene.render.fps
    arm = tt._arm(arm)
    scene.frame_set(frame_from)
    p0 = com(arm)
    scene.frame_set(frame_to)
    p1 = com(arm)
    duration = (frame_to - frame_from) / fps
    v0 = (p1 - p0) / duration + Vector((0, 0, 0.5 * G * duration))
    for f in range(frame_from + 1, frame_to):
        t = (f - frame_from) / fps
        target = p0 + v0 * t - Vector((0, 0, 0.5 * G * t * t))
        scene.frame_set(f)
        arm.location += target - com(arm)
        _update()
        tt.key(arm, f, bones=[])
    return v0.z - G * duration


def first_mat_contact(arm, bones, start=None, end=None, height=0.03):
    """Time at which each bone's capsule first comes within `height` of the mat (None = never; the
    capsules sit ~1-2 cm inside the gi). Use it to check ukemi timing: the slapping arm should land
    with the back."""
    import contact
    scene = bpy.context.scene
    fps = scene.render.fps
    result = {b: None for b in bones}
    for f in range(scene.frame_start if start is None else start, (scene.frame_end if end is None else end) + 1):
        scene.frame_set(f)
        caps = contact.world_capsules(arm)
        for b in bones:
            if result[b] is None:
                p0, p1, r = caps[b]
                if min(p0.z, p1.z) - r < height:
                    result[b] = f / fps
    return result


def settle(arm, clearance=0.015):
    """Move the root vertically so the lowest capsule rests on the mat (its bottom `clearance` above
    it; the gi around the capsules makes up the rest). For lying and kneeling poses; standing poses
    use technique_tools.ground()."""
    import contact
    arm = tt._arm(arm)
    lowest = min(min(p0.z, p1.z) - r for p0, p1, r in contact.world_capsules(arm).values())
    arm.location.z += clearance - lowest
    _update()

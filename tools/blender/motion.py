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
from mathutils import Matrix, Quaternion, Vector

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


def reach(arm, side, ankle, foot_rotation=None, max_move=0.08):
    """leg_ik(), moving the hips (root) up or down by up to `max_move` when the ankle cannot be
    reached: down when it is too far (the knees bend more), up when the hips are so low that the
    leg cannot fold enough. So a planted foot stays on the mat. Returns (residual, total move)."""
    arm_obj = tt._arm(arm)
    up = arm_obj.pose.bones[f"{side}UpLeg"]
    low = arm_obj.pose.bones[f"{side}Leg"]
    foot = arm_obj.pose.bones[f"{side}Foot"]
    l1, l2 = (low.head - up.head).length, (foot.head - low.head).length
    residual = leg_ik(arm, side, ankle, foot_rotation)
    moved = 0.0
    while residual > 0.003 and moved < max_move:
        hip = arm_obj.matrix_world @ up.head
        too_far = (Vector(ankle) - hip).length > l1 + l2 - 0.002
        delta = min(residual * 1.2 + 0.002, max_move - moved)
        arm_obj.location.z += -delta if too_far else delta
        moved += delta
        _update()
        residual = leg_ik(arm, side, ankle, foot_rotation)
    return residual, moved


def _leg_bones(side):
    return [f"{side}UpLeg", f"{side}Leg", f"{side}Foot"]


def _lift_heel(toe, ankle, min_heel):
    """Ankle position after rotating the foot about the toe (in its vertical plane) so the heel is at
    least `min_heel` above the mat. Returns (ankle, rotation applied)."""
    from mathutils import Quaternion
    v = ankle - toe
    need = min_heel + ANKLE_HEIGHT - toe.z
    if ankle.z - ANKLE_HEIGHT >= min_heel or v.length < 1e-6:
        return ankle, Quaternion()
    horizontal = Vector((v.x, v.y, 0))
    axis = horizontal.cross(Vector((0, 0, 1))).normalized()
    angle = math.asin(max(-1.0, min(1.0, need / v.length))) - math.asin(max(-1.0, min(1.0, v.z / v.length)))
    q = Quaternion(axis, -angle)
    if (toe + q @ v).z < ankle.z:
        q = Quaternion(axis, angle)
    return toe + q @ v, q


def plant(arm, side, frame_from, frame_to, pivot="ankle", heel_lift=0.025, until_lifted=False):
    """Keep `side`'s foot ("Left"/"Right") fixed on the mat from frame_from to frame_to (inclusive),
    where it is at frame_from: leg IK on every frame against the moving hips.

    pivot="ankle": the whole foot stays put (flat foot). pivot="toe": only the toe stays put and the
    foot keeps its keyed rotation, so the heel can rise (going onto the toes) or the foot can turn
    on the ball (tai-sabaki); the heel is kept at least `heel_lift` off the mat so it does not drag.
    Returns the worst distance the ankle could not reach (> 0.01 m means the hips move too far for
    the leg).

    until_lifted=True: for a judoka who is being lifted (Uki): the foot stays on the mat only while it
    can reach it; from the first frame it cannot, the leg keeps reaching (straight) for that spot
    instead of the hips being lowered, so the foot rises off the mat as the body is lifted. Returns
    that frame (or None) in this mode."""
    scene = bpy.context.scene
    arm_obj = tt._arm(arm)
    scene.frame_set(frame_from)
    m = foot_matrix(arm, side)
    toe = arm_obj.matrix_world @ arm_obj.pose.bones[f"{side}Foot"].tail
    worst = 0.0
    lifted = None
    for f in range(frame_from, frame_to + 1):
        scene.frame_set(f)
        if pivot == "toe":
            current = foot_matrix(arm, side)
            ankle_to_toe = arm_obj.matrix_world @ arm_obj.pose.bones[f"{side}Foot"].tail - current.translation
            ankle, lift = _lift_heel(toe, toe - ankle_to_toe, heel_lift)
            ankle, rotation = ankle, lift.to_matrix() @ current.to_3x3()
        else:
            ankle, rotation = m.translation, m.to_3x3()
        if until_lifted:
            if leg_ik(arm, side, ankle, rotation) > 0.01 and lifted is None:
                lifted = f
            drop = 0.0
        else:
            residual, drop = reach(arm, side, ankle, rotation)
            worst = max(worst, residual)
        tt.key(arm, f, bones=_leg_bones(side), root=drop > 0)
    if until_lifted:
        return lifted
    if worst > 0.01:
        print(f"plant {arm} {side}: ankle out of reach by {worst * 100:.1f} cm")
    return worst


def step(arm, side, frame_from, frame_to, height=0.06, to=None, around=None, lift=0.0):
    """Move `side`'s foot from where it is at frame_from to where it is at frame_to, or to the world
    ankle position `to` (keeping the foot's rotation at frame_to): it lifts by `height` (m), travels
    with ease-in/out and is put down. `around`: a world point the foot swings around in an arc (the
    pivot foot in tai-sabaki) instead of going straight. `lift`: fraction of the step at each end
    in which the foot only goes up / comes down (no sliding at lift-off and touch-down). Returns the
    worst unreachable distance."""
    scene = bpy.context.scene
    scene.frame_set(frame_from)
    m0 = foot_matrix(arm, side)
    scene.frame_set(frame_to)
    m1 = foot_matrix(arm, side)
    if to is not None:
        m1 = Matrix.Translation(Vector(to)) @ m1.to_3x3().to_4x4()
    q0, q1 = m0.to_quaternion(), m1.to_quaternion()
    q1.make_compatible(q0)
    worst = 0.0
    # Key the end frame too: keys added inside the range change how frame_to evaluates.
    for f in range(frame_from + 1, frame_to + 1):
        s = (f - frame_from) / (frame_to - frame_from)
        h = min(max((s - lift) / (1 - 2 * lift), 0.0), 1.0)
        e = h * h * (3 - 2 * h)  # smoothstep
        pos = m0.translation.lerp(m1.translation, e)
        if around is not None:
            c = Vector((around[0], around[1]))
            v0, v1 = m0.translation.to_2d() - c, m1.translation.to_2d() - c
            a0, a1 = math.atan2(v0.y, v0.x), math.atan2(v1.y, v1.x)
            da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi  # the short way round
            r = v0.length + (v1.length - v0.length) * e
            a = a0 + da * e
            pos = Vector((c.x + r * math.cos(a), c.y + r * math.sin(a), pos.z))
        pos += Vector((0, 0, height * math.sin(math.pi * s)))
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


def balance(arm, start=None, end=None, margin=0.0, carrying=None):
    """Frames where the centre of mass (projected on the mat) lies more than `margin` outside the
    support polygon. `carrying`: another judoka whose weight this one bears (e.g. Uki on Tori's
    back): the combined centre of mass is checked against the support of both (Uki may still be
    on his toes). Returns dict(worst, time,
    frames=[(time, distance)]); worst = 0 when balanced."""
    scene = bpy.context.scene
    fps = scene.render.fps
    result = dict(worst=0.0, time=None, frames=[])
    for f in range(scene.frame_start if start is None else start, (scene.frame_end if end is None else end) + 1):
        scene.frame_set(f)
        c = com(arm) if carrying is None else (com(arm) + com(carrying)) / 2
        points = support_points(arm) + (support_points(carrying) if carrying else [])
        d = outside_distance(Vector((c.x, c.y)), convex_hull(points))
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


def pivot(arm, bone, frame_from, frame_to):
    """Move the root on every frame between two keys so `bone`'s head travels in a straight line
    (with the segment's easing) between where it is at frame_from and at frame_to, instead of the
    root. Use it when a judoka rotates a lot about a point other than the feet (Uki turning over
    Tori's back): interpolating the root would swing the body through the partner."""
    scene = bpy.context.scene
    arm = tt._arm(arm)
    scene.frame_set(frame_from)
    p0 = arm.matrix_world @ arm.pose.bones[bone].head
    root0 = arm.location.copy()
    scene.frame_set(frame_to)
    p1 = arm.matrix_world @ arm.pose.bones[bone].head
    root1 = arm.location.copy()
    # The keyed root's progress along its own path gives the segment's (eased) timing. Read it for
    # all frames first: the keys added below change how the following frames evaluate.
    span = root1 - root0
    progress = {}
    for f in range(frame_from + 1, frame_to):
        scene.frame_set(f)
        if span.length_squared > 1e-9:
            progress[f] = (arm.location - root0).dot(span) / span.length_squared
        else:
            progress[f] = (f - frame_from) / (frame_to - frame_from)
    for f in range(frame_from + 1, frame_to):
        scene.frame_set(f)
        target = p0.lerp(p1, min(max(progress[f], 0.0), 1.0))
        arm.location += target - arm.matrix_world @ arm.pose.bones[bone].head
        _update()
        tt.key(arm, f, bones=[])


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


# --- arms ----------------------------------------------------------------------------------------

def _chain(arm, bone, length):
    pb = tt._arm(arm).pose.bones[bone]
    names = []
    for _ in range(length):
        names.insert(0, pb.name)
        pb = pb.parent
    return names


def hold(arm, hand, target_arm, target_bone, frame_from, frame_to, chain=3, pole=None):
    """Keep a gripping hand on a grip bone of the other judoka on every frame (IK on the arm chain),
    not only at the keyframes."""
    scene = bpy.context.scene
    bones = _chain(arm, hand, chain)
    for f in range(frame_from, frame_to + 1):
        scene.frame_set(f)
        tt.ik(arm, hand, target_arm, target_bone, chain, pole)
        tt.key(arm, f, bones=bones, root=False)


def avoid(arm, bones, other, frame_from, frame_to, allow=(), step=12, steps=3, smooth=0.002, relax=1.0,
          max_rate=None, global_search=True):
    """Per frame, tilt each of `bones` (parents first, e.g. ["RightArm", "RightForearm"]) about two
    axes across the bone, so that the bone's chain overlaps `other` and the mat as little as possible
    (beyond the allowed contacts), within +-step*steps degrees. Deterministic: a grid of `step`
    degrees, then downhill steps halved down to 0.5 degrees, scored by the overlap plus `smooth` (m)
    per degree away from the previous frame's tilt (eased back towards none by `relax` degrees per
    frame), so the bone stays on its side of the other judoka and small changes elsewhere give small
    changes here. `max_rate`: the tilt changes at most that many degrees per frame (no snaps).
    Frames without overlap keep the eased tilt. Keys the bones where it tilted. Returns the
    remaining overlap (m, summed) per frame."""
    import contact
    from mathutils import Quaternion
    scene = bpy.context.scene
    fps = scene.render.fps
    arm_obj = tt._arm(arm)
    other_obj = tt._arm(other)
    chain = _descendants(arm_obj, bones[0])
    shapes = contact.capsules()
    limit = step * steps
    previous = {b: (0.0, 0.0) for b in bones}
    remaining = {}

    def excess(t, theirs, tolerances):
        m = arm_obj.matrix_world
        total = 0.0
        for b in chain:
            p0, p1, r = shapes[b]
            bm = m @ arm_obj.pose.bones[b].matrix
            mine = (bm @ Vector(p0), bm @ Vector(p1), r)
            for o, c in theirs.items():
                depth, _ = contact.penetration(mine, c)
                if depth > 0:
                    key = (b, o)
                    if key not in tolerances:
                        tolerances[key] = contact.tolerance_for(f"{arm}:{b}", f"{other}:{o}", t, allow)
                    total += max(0.0, depth - tolerances[key])
            depth = contact.mat_penetration(mine)
            if depth > 0:
                key = (b, contact.MAT)
                if key not in tolerances:
                    tolerances[key] = contact.tolerance_for(f"{arm}:{b}", contact.MAT, t, allow)
                total += max(0.0, depth - tolerances[key])
        return total

    def tilt(pb, base, a1, a2, u, v):
        q = Quaternion(a1, math.radians(u)) @ Quaternion(a2, math.radians(v))
        pb.matrix = Matrix.Translation(pb.head) @ (q.to_matrix() @ base.to_3x3()).to_4x4()
        _update()

    def eased(p):
        n = math.hypot(*p)
        return (0.0, 0.0) if n <= relax else (p[0] * (1 - relax / n), p[1] * (1 - relax / n))

    own = _own_rotations(arm_obj, bones, frame_from, frame_to)
    for f in range(frame_from, frame_to + 1):
        scene.frame_set(f)
        _restore(arm_obj, own[f])
        t = f / fps
        theirs = contact.world_capsules(other_obj)
        tolerances = {}
        starts = {b: eased(previous[b]) for b in bones}
        if all(p == (0.0, 0.0) for p in previous.values()) and excess(t, theirs, tolerances) == 0:
            previous = starts
            remaining[f] = 0.0
            continue
        for b in bones:
            pb = arm_obj.pose.bones[b]
            base = pb.matrix.copy()
            # Tilt axes across the bone that turn with it (its own X and Z): d.orthogonal() would
            # switch axes when the bone's largest component changes, and the tilt carried over
            # from the previous frame would then snap the bone by up to 90 degrees.
            a1 = base.col[0].xyz.normalized()
            a2 = base.col[2].xyz.normalized()
            su, sv = starts[b]

            def score(u, v):
                tilt(pb, base, a1, a2, u, v)
                return excess(t, theirs, tolerances) + smooth * (abs(u - su) + abs(v - sv))

            def allowed(u, v):
                if abs(u) > limit or abs(v) > limit:
                    return False
                return max_rate is None or math.hypot(u - su, v - sv) <= max_rate

            best = (score(su, sv), su, sv)
            if best[0] > 0 and global_search:
                grid = [i * step for i in range(-steps, steps + 1)]
                best = min([best] + [(score(u, v), u, v) for u in grid for v in grid if allowed(u, v)],
                           key=lambda r: r[0])
            if best[0] > 0:
                h = float(step) / 2 if global_search else float(step)
                while h >= 0.5:
                    moved = True
                    while moved:
                        moved = False
                        for du, dv in ((h, 0), (-h, 0), (0, h), (0, -h), (h, h), (-h, -h), (h, -h), (-h, h)):
                            u, v = best[1] + du, best[2] + dv
                            if not allowed(u, v):
                                continue
                            s = score(u, v)
                            if s < best[0] - 1e-7:
                                best, moved = (s, u, v), True
                                break
                    h /= 2
            tilt(pb, base, a1, a2, best[1], best[2])
            previous[b] = (best[1], best[2])
        tt.key(arm, f, bones=bones, root=False)
        remaining[f] = excess(t, theirs, tolerances)
    return remaining


def repose(arm, bones, frame_from, frame_to, pose):
    """Pose `bones` again on every frame from frame_from to frame_to, keyed: `pose(w)` (w = 0..1
    across the segment) places them, e.g. relative to the partner, so a limb that rests on the
    other judoka follows them instead of interpolating its own rotations between the keyframes."""
    scene = bpy.context.scene
    for f in range(frame_from, frame_to + 1):
        scene.frame_set(f)
        pose((f - frame_from) / (frame_to - frame_from))
        tt.key(arm, f, bones=bones, root=False)


def limit_rate(arm, bones, frame_from, frame_to, max_degrees=15.0):
    """Let each of `bones` (parents first) turn at most max_degrees per frame (direction in the
    armature, so the body's own turning does not count), keyed on every frame: takes out the snaps
    avoid() leaves where it switches between two ways round the other judoka (a little more
    overlap there instead). Returns the largest per-frame turn it found before limiting."""
    scene = bpy.context.scene
    arm_obj = tt._arm(arm)
    previous = {}
    worst = 0.0
    own = _own_rotations(arm_obj, bones, frame_from, frame_to)
    for f in range(frame_from, frame_to + 1):
        scene.frame_set(f)
        _restore(arm_obj, own[f])
        for b in bones:
            pb = arm_obj.pose.bones[b]
            d = (pb.tail - pb.head).normalized()
            if b in previous:
                angle = math.degrees(previous[b].angle(d))
                worst = max(worst, angle)
                if angle > max_degrees:
                    d = previous[b].slerp(d, max_degrees / angle)
                    _aim_bone(pb, d)
            previous[b] = d
        tt.key(arm, f, bones=bones, root=False)
    return worst


def smooth(arm, bones, frame_from, frame_to, radius=3):
    """Low-pass the bones' rotations over time (a moving average over +-radius frames, clamped to
    the range), keyed on every frame: takes out frame-to-frame flicker, e.g. after avoid()."""
    scene = bpy.context.scene
    arm_obj = tt._arm(arm)
    frames = range(frame_from, frame_to + 1)
    raw = {}
    for f in frames:
        scene.frame_set(f)
        raw[f] = {b: arm_obj.pose.bones[b].rotation_quaternion.normalized() for b in bones}
    for f in frames:
        scene.frame_set(f)
        for b in bones:
            ref = raw[f][b]
            acc = Vector((0.0, 0.0, 0.0, 0.0))
            for g in range(max(frame_from, f - radius), min(frame_to, f + radius) + 1):
                q = raw[g][b].copy()
                q.make_compatible(ref)
                acc += Vector(q)
            arm_obj.pose.bones[b].rotation_quaternion = Quaternion(acc).normalized()
        tt.key(arm, f, bones=bones, root=False)


def hinge_elbows(arm, frame_from, frame_to, sides=("Left", "Right")):
    """tt.hinge() on every frame: elbows bend like hinges, nothing moves (run after hold/avoid);
    the upper arms twist smoothly from frame to frame. Returns the largest upper-arm twist per side
    (degrees from the rest pose)."""
    scene = bpy.context.scene
    worst = {s: 0.0 for s in sides}
    twist = {s: None for s in sides}
    bones = [f"{s}{b}" for s in sides for b in ("Arm", "Forearm", "Hand")]
    own = _own_rotations(tt._arm(arm), bones, frame_from, frame_to)
    for f in range(frame_from, frame_to + 1):
        scene.frame_set(f)
        _restore(tt._arm(arm), own[f])
        for s in sides:
            twist[s] = tt.hinge(arm, s, previous=twist[s])
            worst[s] = max(worst[s], abs(twist[s]))
        tt.key(arm, f, bones=bones, root=False)
    return worst


def _own_rotations(arm_obj, bones, frame_from, frame_to):
    """The bones' rotations on every frame of the range, read before any keys are added: once frame
    f-1 is keyed, frame f evaluates part of the way towards that key, and a tool that reads, changes
    and keys frame by frame would then stack its changes from one frame to the next."""
    scene = bpy.context.scene
    rotations = {}
    for f in range(frame_from, frame_to + 1):
        scene.frame_set(f)
        rotations[f] = {b: arm_obj.pose.bones[b].rotation_quaternion.copy() for b in bones}
    return rotations


def _restore(arm_obj, rotations):
    for b, q in rotations.items():
        arm_obj.pose.bones[b].rotation_quaternion = q
    _update()


def _descendants(arm_obj, bone):
    pb = arm_obj.pose.bones[bone]
    return [pb.name] + [c.name for c in pb.children_recursive if c.bone.use_deform]


def shift_weight(arm, side, frame_from, frame_to, ramp=5, carrying=None):
    """Move the hips (root) so the centre of mass is over the support: `side`'s foot ("Left" /
    "Right", the part of it on the mat: the ball when on the toes, while the other foot is in the
    air) or both feet ("both"). `carrying`: a judoka this one carries; their combined centre of mass
    is used and the carried judoka moves along. Eases in and out over `ramp` frames at both ends
    (or a pair: frames to ease in, frames to ease out).
    The feet stay where they are in the world (the legs are re-solved and keyed), so run it after
    plant()/step()."""
    scene = bpy.context.scene
    arm_obj = tt._arm(arm)
    carried = tt._arm(carrying) if carrying else None
    sides = ("Left", "Right") if side == "both" else (side,)
    ramp_in, ramp_out = ramp if isinstance(ramp, (tuple, list)) else (ramp, ramp)
    targets, feet = {}, {}
    for f in range(frame_from, frame_to + 1):
        scene.frame_set(f)
        grounded = [p for s_ in sides for p in sole_points(arm, s_).values() if p.z < 0.02]
        if not grounded:
            grounded = [foot_matrix(arm, s_).translation for s_ in sides]
        foot = sum(grounded, Vector()) / len(grounded)
        c = com(arm) if carried is None else (com(arm) + com(carried)) / 2
        w = min(1.0, (f - frame_from) / ramp_in if ramp_in else 1.0, (frame_to - f) / ramp_out if ramp_out else 1.0)
        w = w * w * (3 - 2 * w)
        offset = Vector((foot.x - c.x, foot.y - c.y, 0)) * w
        # Absolute targets: the keys added below change how the following frames evaluate.
        targets[f] = [(arm_obj, arm_obj.location + offset)]
        if carried:
            targets[f].append((carried, carried.location + offset))
        feet[f] = {s_: foot_matrix(arm, s_) for s_ in ("Left", "Right")}
    for f, moves in targets.items():
        scene.frame_set(f)
        for obj, location in moves:
            obj.location = location
            _update()
            tt.key(obj, f, bones=[])
        _update()  # the new keys re-evaluate the action once: before the IK, not halfway through it
        for s_, m in feet[f].items():
            if m.translation.z < ANKLE_HEIGHT + 0.03:  # on the mat: keep it there
                reach(arm, s_, m.translation, m.to_3x3())
            else:
                leg_ik(arm, s_, m.translation, m.to_3x3())
        for s_, m in feet[f].items():  # lowering for the second foot may move the first
            leg_ik(arm, s_, m.translation, m.to_3x3())
        tt.key(arm, f, bones=_leg_bones("Left") + _leg_bones("Right"))


def carry(carrier, carrier_bone, carried, pivot_bone, frame_from, frame_to):
    """Let `carrier` move `carried` between two keys (Uki on Tori's back): the carried judoka's root
    rotation and the position of its `pivot_bone` are interpolated in the frame of the carrier's
    `carrier_bone` instead of in the world, so the carried judoka only rises, turns and moves as the
    carrier does (straightening the legs, bowing, turning). The segment's timing comes from the
    carried judoka's own keyed rotation. Keys the carried root on every frame in between.
    Run it after the carrier's motion is final (feet, weight)."""
    scene = bpy.context.scene
    a, b = tt._arm(carrier), tt._arm(carried)

    def frame_of_carrier():
        return a.matrix_world @ a.pose.bones[carrier_bone].matrix

    def relative():
        c = frame_of_carrier()
        c_rot = c.to_quaternion()
        return (c_rot.inverted() @ b.matrix_world.to_quaternion(),
                c.inverted() @ (b.matrix_world @ b.pose.bones[pivot_bone].head))

    scene.frame_set(frame_from)
    r0, p0 = relative()
    q0 = b.matrix_world.to_quaternion()
    scene.frame_set(frame_to)
    r1, p1 = relative()
    q1 = b.matrix_world.to_quaternion()
    r1.make_compatible(r0)

    def angle(p, q):  # sign-independent: q and -q are the same rotation
        return 2 * math.acos(min(1.0, abs(p.dot(q))))

    total = angle(q0, q1)
    # Progress along the segment from the keyed rotation; read it for all frames before keying.
    progress = {}
    for f in range(frame_from + 1, frame_to):
        scene.frame_set(f)
        if total > 1e-3:
            progress[f] = min(max(angle(q0, b.matrix_world.to_quaternion()) / total, 0.0), 1.0)
        else:
            progress[f] = (f - frame_from) / (frame_to - frame_from)
    for f in range(frame_from + 1, frame_to):
        scene.frame_set(f)
        s = progress[f]
        c = frame_of_carrier()
        rotation = c.to_quaternion() @ r0.slerp(r1, s)
        location = b.location.copy()
        b.matrix_world = Matrix.Translation(location) @ rotation.to_matrix().to_4x4()
        _update()
        target = c @ p0.lerp(p1, s)
        b.location += target - b.matrix_world @ b.pose.bones[pivot_bone].head
        _update()
        tt.key(b, f, bones=[])

"""Standing judo building blocks shared by the technique scripts (tools/blender/techniques/).

Pose helpers work at the current frame in each judoka's own frame A (X = right, Y = up, -Z = the way
they face); directions returned (`facing`, `right_of`, `axis`) and points are Blender world space.
"""
import bpy
from mathutils import Vector

import contact
import motion
import technique_tools as tt

GRIP_DISTANCE = 0.62  # between the two roots while gripping


def frame(t):
    return round(t * tt.FPS)


def lerp(a, b, w):
    return a + (b - a) * w


# --- allowed contacts ----------------------------------------------------------------------------

def pairs(a_bones, b_bones, tolerance, start=float("-inf"), end=float("inf")):
    """contact.Allow for every combination of the two bone lists."""
    return [contact.Allow(a, b, tolerance, start, end) for a in a_bones for b in b_bones]


ARMS = ["*Arm", "*Forearm", "*Hand"]


def body_allow(allow):
    """Allowed contacts plus any contact of an arm: for pushing the bodies apart (arms are posed
    around the bodies afterwards, or by motion.avoid between keyframes)."""
    return list(allow) + [contact.Allow(f"{a}:{b}", f"{o}:*", 1.0)
                          for a, o in (("Tori", "Uki"), ("Uki", "Tori")) for b in ARMS]


def push_back(allow, direction, mover="Uki", other="Tori"):
    """Push `mover` away along `direction` until the bodies (torso, head, legs) no longer overlap
    beyond `allow` (arm contacts ignored)."""
    contact.separate(mover, other, allow=body_allow(allow), direction=direction)


# --- directions ----------------------------------------------------------------------------------

def facing(j):
    """Horizontal direction the judoka faces (Blender world space)."""
    arm = bpy.data.objects[j]
    f = arm.matrix_world.to_3x3() @ (tt.B2A.transposed() @ Vector((0, 0, -1)))
    return Vector((f.x, f.y, 0)).normalized()


def right_of(j):
    f = facing(j)
    return Vector((f.y, -f.x, 0))


def axis(j, a):
    """One of the judoka's own axes (frame A: X = right, Y = up, -Z = facing) in world space; use
    this instead of facing() for a judoka lying down."""
    return (bpy.data.objects[j].matrix_world.to_3x3().normalized() @ (tt.B2A.transposed() @ Vector(a))).normalized()


# --- standing ------------------------------------------------------------------------------------

def stance(j, knee=12, left=4, right=4):
    """Natural stance (shizentai): feet a little apart (`left`/`right`: each leg's spread in
    degrees), knees slightly bent."""
    tt.rot(j, "LeftUpLeg", (knee, 0, -left))
    tt.rot(j, "RightUpLeg", (knee, 0, right))
    tt.rot(j, "LeftLeg", (-2 * knee, 0, 0))
    tt.rot(j, "RightLeg", (-2 * knee, 0, 0))
    tt.rot(j, "LeftFoot", (knee, 0, 0))
    tt.rot(j, "RightFoot", (knee, 0, 0))


def arms_ready(j):
    """Arms forward and down, elbows low: a starting guess for the grip IK."""
    tt.rot(j, "LeftArm", (0, -55, 55))
    tt.rot(j, "RightArm", (0, 55, -55))
    tt.rot(j, "LeftForearm", (0, -40, -30))
    tt.rot(j, "RightForearm", (0, 40, 30))


def arms_down(j):
    tt.aim(j, "LeftArm", (0.15, -1, 0.05))
    tt.aim(j, "RightArm", (-0.15, -1, 0.05))


def on_toes(j, heel=25):
    """Legs straight, heels raised: balance broken forward."""
    tt.rot(j, "LeftUpLeg", (2, 0, -4))
    tt.rot(j, "RightUpLeg", (2, 0, 4))
    tt.rot(j, "LeftFoot", (-heel, 0, 0))
    tt.rot(j, "RightFoot", (-heel, 0, 0))


def crouch(j, depth=50, spread=8):
    """Both knees bent, hips low (Tori's entry under Uki's centre of gravity)."""
    tt.rot(j, "LeftUpLeg", (depth, 0, -spread))
    tt.rot(j, "RightUpLeg", (depth, 0, spread))
    tt.rot(j, "LeftLeg", (-1.6 * depth, 0, 0))
    tt.rot(j, "RightLeg", (-1.6 * depth, 0, 0))
    tt.rot(j, "LeftFoot", (0.6 * depth, 0, 0))
    tt.rot(j, "RightFoot", (0.6 * depth, 0, 0))


def grip():
    """Standard right-handed kumikata: right hand on the opponent's left lapel, left hand on the right sleeve."""
    tt.ik("Tori", "RightHand", "Uki", "LeftLapelGrip")
    tt.ik("Uki", "RightHand", "Tori", "LeftLapelGrip")
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")
    tt.ik("Uki", "LeftHand", "Tori", "RightSleeveGrip")


def ankles_mid(j):
    return (tt.bone_pos(j, "LeftFoot") + tt.bone_pos(j, "RightFoot")) / 2


def stand(j, point, bone_point):
    """Move the judoka horizontally so `bone_point` (a function of the posed judoka giving a world
    point) lands on `point`, then put the feet on the mat."""
    p = bone_point()
    bpy.data.objects[j].location += Vector((point.x - p.x, point.y - p.y, 0))
    tt._update()
    tt.ground(j)


# --- Uki's arms in forward throws (Tori's left hand on Uki's right sleeve) -----------------

def uki_left_arm_on_back(out=0.12, back=0.22):
    """Uki's left arm hangs along Tori's back (or, with a larger `out`, past Tori's left side), the
    hand near Tori's left hip."""
    hips, fwd, right = tt.bone_pos("Tori", "Hips"), facing("Tori"), right_of("Tori")
    tt.aim_at("Uki", "LeftArm", hips - fwd * back - right * out + Vector((0, 0, 0.15)))
    tt.aim_at("Uki", "LeftForearm", hips - fwd * (back - 0.02) - right * (out + 0.08) - Vector((0, 0, 0.05)))


def uki_left_arm_along_side():
    """Uki's free left arm along his own flank, away from Tori (who is under Uki's left shoulder
    while Uki rolls over the right one), the elbow a little bent."""
    tt.aim("Uki", "LeftArm", (-0.3, -0.85, 0.45))
    tt.aim("Uki", "LeftForearm", (-0.2, -0.95, 0.0))


def uki_arm_held(_w=None, ahead=0.4, left=0.3, down=0.3):
    """Uki's right arm stretched towards Tori's left hip, where Tori holds the sleeve and pulls it
    to (fall, ukemi); his left hand then takes the sleeve on that line, in front of his body. Aimed
    from the rest pose, so the upper arm does not pick up twist from frame to frame. The pull point
    is `ahead` of, `left` of and `down` from Tori's chest."""
    pull = (tt.bone_pos("Tori", "Chest") + facing("Tori") * ahead - right_of("Tori") * left
            - Vector((0, 0, down)))
    tt.rot("Uki", "RightArm", (0, 0, 0))
    tt.rot("Uki", "RightForearm", (0, 0, 0))
    tt.aim_at("Uki", "RightArm", pull)


# --- on the mat ----------------------------------------------------------------------------------

def slap(j, side="Left", spread=0.65):
    """Ukemi slap for a judoka lying on the back (after motion.settle): the arm flat on the mat, about
    40 degrees out from the body towards the feet, palm down."""
    sign = 1 if side == "Right" else -1
    shoulder = tt.bone_pos(j, f"{side}Arm")
    out, feet = axis(j, (sign, 0, 0)), -axis(j, (0, 1, 0))
    out.z = feet.z = 0
    direction = (out.normalized() * spread + feet.normalized() * 0.76).normalized()
    # (heights: the arm's capsules resting on the mat)
    tt.aim_at(j, f"{side}Arm", Vector((shoulder.x, shoulder.y, 0.095)) + direction * 0.26)
    tt.aim_at(j, f"{side}Forearm", Vector((shoulder.x, shoulder.y, 0.08)) + direction * 0.52 + out.normalized() * 0.05)
    tt.palm(j, side, (0, 0, -1))


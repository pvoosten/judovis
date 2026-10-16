"""O-soto-gari (right-handed Tori) - authored in Blender, exported to data/techniques/.

Run headless (see tools/blender/README.md):
    blender -b art_source/blender/judoka.blend --python tools/blender/run_technique.py -- o_soto_gari --draft

Tori steps in with the left foot beside Uki's right foot, breaks Uki's balance backwards onto the
right heel (sleeve pulled down, lapel pushed up and back), swings the right leg forward past Uki's
right leg and reaps it away from behind; Uki falls on the back (head away from Tori) and slaps with
the left arm while Tori keeps the sleeve.

Pose helpers work in each judoka's own frame: X = their right, Y = up, -Z = the way they face. Root
positions/rotations are in Godot space; `G()` turns a Godot point into Blender space (world points:
bone_pos, pin, leg IK).
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..") if "__file__" in globals() \
    else r"C:\proj\judo\tools\blender"
sys.path.insert(0, os.path.normpath(TOOLS))
import technique_tools as tt  # noqa: E402
import contact  # noqa: E402
import motion  # noqa: E402
for _m in (tt, contact, motion):
    importlib.reload(_m)

NAME = "o_soto_gari"
OUT = os.path.normpath(os.path.join(TOOLS, "..", "..", "data", "techniques", f"{NAME}.yaml"))

META = dict(technique_name="O-soto-gari", dutch_name="Grote buitenwaartse maaiworp", waza_group="nage_waza",
            category="Ashi-waza (Beenworp)", code="N5-2", difficulty="Easy", kyu_grade=5,
            belt_name="Gele band", belt_hex="#FFD700", source="VJF leerlijn 2015, geel", duration_seconds=2.5)

GRIP_DISTANCE = 0.62
ANKLE = motion.ANKLE_HEIGHT


def frame(t):
    return round(t * tt.FPS)


def G(x, y, z):
    """Godot point -> Blender world point."""
    return Vector((x, -z, y))


# --- allowed contacts (contact.check_contacts) --------------------------------------------------

def _pairs(a_bones, b_bones, tolerance, start=float("-inf"), end=float("inf")):
    return [contact.Allow(a, b, tolerance, start, end) for a in a_bones for b in b_bones]


ALLOW = (
    # Kumikata: hands on lapel and sleeve; the gripping arms rub against each other.
    _pairs(["Tori:RightHand"], ["Uki:Chest", "Uki:LeftShoulder"], 0.07, end=1.4)
    + _pairs(["Uki:RightHand"], ["Tori:Chest", "Tori:LeftShoulder", "Tori:LeftArm"], 0.07, end=1.1)
    + _pairs(["Uki:LeftHand"], ["Tori:RightForearm", "Tori:RightArm"], 0.07, end=1.1)
    + _pairs(["Tori:LeftHand"], ["Uki:RightForearm", "Uki:RightArm", "Uki:RightHand"], 0.07)
    + _pairs(["Tori:LeftForearm"], ["Uki:RightForearm", "Uki:RightHand"], 0.06)
    + _pairs(["Tori:*Forearm", "Tori:*Arm"], ["Uki:*Forearm", "Uki:*Arm"], 0.045, end=1.4)
    # Tori's lapel arm lies across Uki's right shoulder and upper arm (drawn out by the sleeve).
    + _pairs(["Tori:RightHand", "Tori:RightForearm"], ["Uki:RightArm", "Uki:RightShoulder"], 0.07, 0.2, 1.4)
    # Chest to chest: Tori's right side pressed against Uki's right chest and shoulder.
    + _pairs(["Tori:Chest", "Tori:RightShoulder", "Tori:RightArm"], ["Uki:Chest", "Uki:RightShoulder", "Uki:RightArm"],
             0.04, 0.6, 1.4)
    # The reap: Tori's right leg sweeps the back of Uki's right leg.
    + _pairs(["Tori:RightUpLeg", "Tori:RightLeg"], ["Uki:RightUpLeg", "Uki:RightLeg"], 0.04, 0.6, 1.5)
    + _pairs(["*Foot"], [contact.MAT], 0.03)
)

ARMS = ["*Arm", "*Forearm", "*Hand"]
BODY_ALLOW = ALLOW + [contact.Allow(f"{a}:{b}", f"{o}:*", 1.0)
                      for a, o in (("Tori", "Uki"), ("Uki", "Tori")) for b in ARMS]


# --- pose building blocks -----------------------------------------------------------------------

def stance(j, knee=12, left=4, right=4):
    """Natural stance (shizentai): feet a little apart, knees slightly bent."""
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


def grip(lapels=True, sleeves=True, uki=True):
    """Right-handed kumikata: right hand on the opponent's left lapel, left hand on the right sleeve."""
    if lapels:
        tt.ik("Tori", "RightHand", "Uki", "LeftLapelGrip")
        if uki:
            tt.ik("Uki", "RightHand", "Tori", "LeftLapelGrip")
    if sleeves:
        tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")
        if uki:
            tt.ik("Uki", "LeftHand", "Tori", "RightSleeveGrip")


def facing(j):
    """Horizontal direction the judoka faces (Blender world space)."""
    arm = bpy.data.objects[j]
    f = arm.matrix_world.to_3x3() @ (tt.B2A.transposed() @ Vector((0, 0, -1)))
    return Vector((f.x, f.y, 0)).normalized()


def right_of(j):
    f = facing(j)
    return Vector((f.y, -f.x, 0))


def axis(j, a):
    """One of the judoka's own axes (frame A: X = right, Y = up, -Z = facing) in world space."""
    return (bpy.data.objects[j].matrix_world.to_3x3().normalized() @ (tt.B2A.transposed() @ Vector(a))).normalized()


# Flat foot world rotations at yaw 0 (taken from the kumikata stance), per judoka and side.
FLAT = {}


def flat(j, side, yaw=None):
    """World rotation of a flat foot pointing the way the judoka faces (yaw: Godot Y rotation in
    degrees; default the judoka's current yaw relative to kumikata)."""
    if yaw is None:
        f = facing(j)
        base = Vector((0, -1, 0)) if j == "Tori" else Vector((0, 1, 0))
        yaw = math.degrees(math.atan2(base.cross(f).z, base.dot(f)))
    return Matrix.Rotation(math.radians(yaw), 3, "Z") @ FLAT[(j, side)]


def foot_on(j, side, ankle, yaw=None):
    """Put a foot flat on the mat with the ankle on `ankle` (world); the hips go up or down if needed."""
    residual, _ = motion.reach(j, side, ankle, flat(j, side, yaw))
    if residual > 0.01:
        print(f"foot_on {j} {side}: {residual * 100:.1f} cm out of reach")


def tori_on_left(height=0.86, inward=0.03, back=0.0):
    """Tori stands on the left leg: the hips go over the left ankle (`inward`: towards his right,
    `back`: behind it), `height` above the mat; then the foot is put flat on the mat. Use after
    setting the root rotation (a forward tilt swings the trunk and the reaping leg about the hips)."""
    hips = TORI_LEFT + right_of("Tori") * inward - facing("Tori") * back
    tt.pin("Tori", "Hips", Vector((hips.x, hips.y, height)))
    foot_on("Tori", "Left", TORI_LEFT, yaw=-12)


def tori_right_ankle(point, toes=-20):
    """Tori's right (reaping) leg: the ankle onto a world point, the knee bending forward; `toes`
    points the foot (negative: toes down/stretched)."""
    tt.rot("Tori", "RightUpLeg", (80, 0, 0))  # bend plane for the leg IK: knee forward
    tt.rot("Tori", "RightLeg", (-90, 0, 0))
    residual = motion.leg_ik("Tori", "Right", point)
    if residual > 0.01:
        print(f"tori_right_ankle: {residual * 100:.1f} cm out of reach")
    tt.rot("Tori", "RightFoot", (toes, 0, 0))


def tori_turn_to_uki(twist=20, lean=6):
    """Tori's upper body turns right (towards Uki's right chest) and leans right, the hips still
    facing forward (the reaping leg swings past the outside of Uki's right leg)."""
    tt.turn("Tori", "Spine", (0, -twist / 2, -lean / 2))
    tt.turn("Tori", "Chest", (0, -twist / 2, -lean / 2))


def behind_uki_knee(back, out, down):
    """A world point by Uki's right knee: `back` behind it, `out` to Uki's right, `down` below it."""
    return (tt.bone_pos("Uki", "RightLeg") - facing("Uki") * back + right_of("Uki") * out
            - Vector((0, 0, down)))


# Where the feet are (Blender space), set by the poses in keyframe order.
FEET = {}


def lerp(a, b, w):
    return a + (b - a) * w


def push_back(direction):
    """Push Uki away from Tori along `direction` until the bodies no longer overlap beyond the
    allowed contacts."""
    contact.separate("Uki", "Tori", allow=BODY_ALLOW, direction=direction)


def uki_sleeve_pulled(down=0.10, out=0.20, ahead=0.30, forearm_left=0.1, forearm_up=-0.1):
    """Tori's left hand pulls Uki's right sleeve down towards his own left hip: Uki's right arm is
    drawn out in front of Tori's left side (`out` to Tori's left, `ahead` in front of Tori's hips,
    `down` above them), then the hand takes the sleeve there. The forearm points beyond the arm's
    target, `forearm_left` further to Tori's left and `forearm_up` higher."""
    hips = tt.bone_pos("Tori", "Hips")
    target = hips - right_of("Tori") * out + facing("Tori") * ahead + Vector((0, 0, down))
    tt.rot("Uki", "RightArm", (0, 0, 0))
    tt.rot("Uki", "RightForearm", (0, 0, 0))
    tt.aim_at("Uki", "RightArm", target)
    tt.aim_at("Uki", "RightForearm", target - right_of("Tori") * forearm_left + Vector((0, 0, forearm_up)))
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def uki_arm_held(w=1.0):
    """Uki's right arm stretched up towards Tori, who holds the sleeve up: in the air (w = 0) towards
    a point below Tori's chest, on the mat (w = 1) at Tori's left shoulder, as far as the sleeve
    can be reached. Aimed from the rest pose, so the upper arm does not pick up twist from frame to
    frame."""
    low = tt.bone_pos("Tori", "Chest") - right_of("Tori") * 0.15 + facing("Tori") * 0.15 - Vector((0, 0, 0.35))
    past = tt.bone_pos("Tori", "LeftArm") - right_of("Tori") * HELD_OUT  # outside Tori's left arm
    pull = lerp(low, past, w)
    tt.rot("Uki", "RightArm", (0, 0, 0))
    tt.rot("Uki", "RightForearm", (0, 0, 0))
    tt.aim_at("Uki", "RightArm", pull)
    if HELD_FOREARM is not None:  # the elbow bends: the forearm up past the outside of Tori's arm
        out, up = HELD_FOREARM
        tt.aim_at("Uki", "RightForearm", pull - right_of("Tori") * out * w + Vector((0, 0, up * w)))


def tori_free_right_arm():
    """Tori's released right arm down along his side, the elbow a little bent."""
    tt.aim("Tori", "RightArm", (0.3, -1, 0.05))
    tt.aim("Tori", "RightForearm", (0.15, -0.9, -0.4))


# --- keyframe poses ------------------------------------------------------------------------------

def kumikata():
    tt.place("Tori", (0, 0, 0), (0, 0, 0))
    tt.place("Uki", (0, 0, GRIP_DISTANCE), (0, 180, 0))
    for j in ("Tori", "Uki"):
        stance(j)
        tt.rot(j, "Spine", (-6, 0, 0))
        arms_ready(j)
        tt.ground(j)
        for side in ("Left", "Right"):
            FLAT[(j, side)] = motion.foot_matrix(j, side).to_3x3()
            FEET[(j, side)] = motion.foot_matrix(j, side).translation.copy()
    grip()


TORI_LEFT = G(0.48, ANKLE, 0.36)  # Tori's left ankle beside (outside) Uki's right foot


def kuzushi():
    # Uki is pushed back onto the right heel: leaning back and to his right.
    tt.place("Uki", (0.02, 0, 0.64), (7, 180, 2))
    stance("Uki", knee=8)
    tt.rot("Uki", "Spine", (4, 0, 0))
    arms_ready("Uki")
    for side in ("Left", "Right"):
        foot_on("Uki", side, FEET[("Uki", side)], yaw=0)
    # Tori has stepped in with the left foot beside Uki's right foot; the right foot pushes off.
    tt.place("Tori", (0.34, -0.02, 0.38), (0, -6, 0))
    tt.rot("Tori", "Spine", (-6, 0, 0))
    tori_turn_to_uki(8, 3)
    arms_ready("Tori")
    tt.rot("Tori", "LeftUpLeg", (10, 0, -4))
    foot_on("Tori", "Left", TORI_LEFT, yaw=-12)
    # The right foot pushes off on the ball, where it stood.
    tori_right_ankle(FEET[("Tori", "Right")] + Vector((0, -0.04, 0.07)), toes=40)
    grip()
    uki_sleeve_pulled(0.25, 0.10, 0.35)


def tsukuri():
    # Uki is all on the right heel, leaning back further.
    tt.place("Uki", (0.03, 0, 0.66), (10, 180, 3))
    stance("Uki", knee=8)
    tt.rot("Uki", "Spine", (6, 0, 0))
    tt.rot("Uki", "Neck", (-10, 0, 0))
    arms_ready("Uki")
    for side in ("Left", "Right"):
        foot_on("Uki", side, FEET[("Uki", side)], yaw=0)
    # Tori stands on the left leg, chest against Uki's right chest, the right leg swung forward past
    # the outside of Uki's right leg.
    tt.place("Tori", (0.28, 0, 0.44), (0, 0, 0))
    tt.rot("Tori", "Spine", (-8, 0, 0))
    tt.rot("Tori", "Chest", (-4, 0, 0))
    tori_turn_to_uki()
    arms_ready("Tori")
    tori_on_left(0.86)
    tori_right_ankle(behind_uki_knee(0.26, 0.30, 0.25))
    grip()
    uki_sleeve_pulled()


def kake():
    # Tori bows forward and reaps Uki's right leg back from behind; Uki tips over backwards.
    tt.place("Uki", (0.05, -0.03, 0.60), (28, 180, 5))  # close: Tori's right hand keeps the lapel
    tt.rot("Uki", "Spine", (8, 0, 0))
    tt.rot("Uki", "Neck", (-20, 0, 0))
    tt.rot("Uki", "LeftUpLeg", (10, 0, -4))
    tt.rot("Uki", "LeftLeg", (-10, 0, 0))
    tt.rot("Uki", "RightUpLeg", (20, 0, 4))
    tt.rot("Uki", "RightLeg", (-15, 0, 0))
    arms_ready("Uki")
    foot_on("Uki", "Left", FEET[("Uki", "Left")], yaw=0)
    tt.place("Tori", (0.28, 0, 0.46), (12, 0, 0))  # the trunk and the reaping leg swing as one
    tt.rot("Tori", "Spine", (-15, 0, 0))
    tt.rot("Tori", "Chest", (-8, 0, 0))
    tt.rot("Tori", "Neck", (15, 0, 0))
    tori_turn_to_uki()
    arms_ready("Tori")
    tori_on_left(0.84)
    tori_right_ankle(behind_uki_knee(0.18, 0.20, 0.10), toes=-30)
    grip(uki=False)
    # Uki has just let go of the lapel: his forearm still points up, across Tori's pulling forearm.
    uki_sleeve_pulled(0.05, 0.25, 0.25, forearm_left=0.0, forearm_up=0.25)


def nage():
    # Pendulum: Tori's head goes down as the reaping leg goes up; Uki is in the air, on his back.
    tt.place("Tori", (0.28, 0, 0.44), (30, -4, 0))
    tt.rot("Tori", "Spine", (-15, 0, 0))
    tt.rot("Tori", "Chest", (-8, 0, 0))
    tt.rot("Tori", "Neck", (30, 0, 0))
    tt.rot("Tori", "LeftUpLeg", (-25, 0, -4))
    tt.rot("Tori", "RightUpLeg", (-30, 0, 8))
    tt.rot("Tori", "RightLeg", (-10, 0, 0))
    tt.rot("Tori", "RightFoot", (-30, 0, 0))
    arms_ready("Tori")
    tori_on_left(0.80, back=0.05)
    tt.place("Uki", (0.1, 0.3, 0.8), (60, 180, 12))
    tt.rot("Uki", "Neck", (-30, 0, 0))
    tt.rot("Uki", "LeftUpLeg", (25, 0, -6))
    tt.rot("Uki", "LeftLeg", (-20, 0, 0))
    tt.rot("Uki", "RightUpLeg", (45, 0, -10))
    tt.rot("Uki", "RightLeg", (-10, 0, 0))
    tt.aim("Uki", "LeftArm", (-0.6, -0.3, -0.6))
    tt.aim("Uki", "LeftForearm", (-0.4, -0.2, -0.85))
    tt.pin("Uki", "Hips", G(0.10, 0.55, 0.7))
    uki_arm_held(0.0)
    grip(lapels=False, uki=False)
    tt.ik("Tori", "RightHand", "Uki", "LeftLapelGrip")


UKI_YAW = 180  # Uki's heading on the mat (below 180: legs away from Tori's feet)
UKI_LAND_X, UKI_LAND_Z = 0.12, 0.7  # Uki's hips on the mat (Godot x, z)
UKI_CURL, UKI_ROLL = 60, 25
HELD_OUT = 0.4
HELD_FOREARM = (0.5, 0.3)  # Uki's held forearm: out past Tori's left arm, up


def ukemi_pose(legs_up=1.0, curl=None, roll=None):
    # Uki on the back, head away from Tori, chin tucked, legs up (`legs_up` 0: legs down on the
    # mat, knees a little bent), slapping with the left arm. Tori pulls the sleeve up: Uki's shoulders `curl` up off
    # the mat and he rolls `roll` degrees onto his left side, the head stays off the mat.
    curl = UKI_CURL if curl is None else curl
    roll = UKI_ROLL if roll is None else roll
    tt.place("Uki", (0.1, 0, 1.0), (90, UKI_YAW, 8))
    tt.rot("Uki", "LeftUpLeg", (lerp(12, 40, legs_up), 0, -8))
    tt.rot("Uki", "RightUpLeg", (lerp(12, 30, legs_up), 0, -2))
    tt.rot("Uki", "LeftLeg", (lerp(-20, -35, legs_up), 0, 0))
    tt.rot("Uki", "RightLeg", (lerp(-20, -25, legs_up), 0, 0))
    tt.rot("Uki", "Neck", (-30, 0, 0))
    tt.rot("Uki", "Spine", (-curl * 0.6, roll * 0.5, 0))
    tt.rot("Uki", "Chest", (-curl * 0.4, roll * 0.5, 0))
    tt.pin("Uki", "Hips", G(UKI_LAND_X, 0.3, UKI_LAND_Z))
    motion.settle("Uki")
    shoulder = tt.bone_pos("Uki", "LeftArm")
    out, feet = -axis("Uki", (1, 0, 0)), -axis("Uki", (0, 1, 0))
    out.z = feet.z = 0
    slap = (out.normalized() * 0.65 + feet.normalized() * 0.76).normalized()
    tt.aim_at("Uki", "LeftArm", Vector((shoulder.x, shoulder.y, 0.095)) + slap * 0.26)
    tt.aim_at("Uki", "LeftForearm", Vector((shoulder.x, shoulder.y, 0.08)) + slap * 0.52 + out.normalized() * 0.05)
    tt.palm("Uki", "Left", (0, 0, -1))
    uki_arm_held()
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def ukemi():
    # Tori's reaping leg comes down, still on the left foot, holding the sleeve.
    tt.place("Tori", (0.28, -0.08, 0.44), (45, -12, 0))  # bent at the hips over Uki
    tt.rot("Tori", "Spine", (-15, 0, 0))
    tt.rot("Tori", "Chest", (-5, 0, 0))
    tt.rot("Tori", "RightUpLeg", (-25, 0, 6))
    tt.rot("Tori", "RightLeg", (-40, 0, 0))
    tt.rot("Tori", "RightFoot", (20, 0, 0))
    tori_free_right_arm()
    tori_on_left(0.84)
    ukemi_pose(curl=30, roll=10)  # landing: the slapping arm on the mat


TORI_RIGHT = G(0.45, ANKLE, 0.25)  # where Tori puts the reaping foot down after the throw
HIPS_BACK = 0.0  # Tori's hips behind the middle of his feet in zanshin (Blender y)


def zanshin(tilt=15, bow=-10, knee=20, lower=0.06):
    """Tori stands on both feet beside Uki, bent at the hips (`tilt`) and bowing over him (`bow`),
    the hips `lower`, to keep the sleeve up."""
    tt.place("Tori", (0.36, 0, 0.30), (tilt, -12, 0))
    feet = (TORI_LEFT + TORI_RIGHT) / 2  # the hips back over the feet: the body bends forward over them
    tt.pin("Tori", "Hips", Vector((feet.x, feet.y + HIPS_BACK, 0.92 - lower)))
    stance("Tori", knee=knee)
    tt.rot("Tori", "Spine", (bow * 0.7, 0, 0))
    tt.rot("Tori", "Chest", (bow * 0.3, 0, 0))
    tori_free_right_arm()
    foot_on("Tori", "Left", TORI_LEFT, yaw=-12)
    foot_on("Tori", "Right", TORI_RIGHT, yaw=-12)
    ukemi_pose(legs_up=0.0)


KEYFRAMES = [
    dict(time=0.0, phase="Kumikata (Grip)",
         description="Tori en Uki pakken elkaar vast: rechterhand aan de revers, linkerhand aan de mouw.",
         pose=kumikata),
    dict(time=0.4, phase="Kuzushi (Balansverstoring)",
         description="Tori stapt met links naast Uki's rechtervoet, trekt de mouw omlaag en duwt Uki "
                     "achterover op de rechterhiel.",
         pose=kuzushi),
    dict(time=0.8, phase="Tsukuri (Instap)",
         description="Borst tegen borst; Tori staat op het linkerbeen en zwaait het rechterbeen langs "
                     "Uki's rechterbeen naar voren.",
         pose=tsukuri),
    dict(time=1.05, phase="Kake (Maaien)",
         description="Tori maait Uki's rechterbeen van achteren weg en buigt voorover.",
         pose=kake),
    dict(time=1.3, phase="Nage (Worp)",
         description="Hoofd omlaag, maaibeen omhoog: Uki valt achterover.",
         pose=nage),
    dict(time=1.62, phase="Ukemi (Valbreking)",
         description="Uki landt op de rug en slaat af met de linkerarm; Tori houdt de mouw vast.",
         pose=ukemi),
    dict(time=2.1, phase="Zanshin (Controle)",
         description="Tori zet de rechtervoet neer en houdt Uki onder controle aan de mouw.",
         pose=zanshin),
    dict(time=2.5, phase="Zanshin (Controle)",
         description="Tori komt overeind en blijft alert.",
         pose=lambda: zanshin(15, -10, 20, 0.06)),
]


# Tori's right ankle on its way forward: first under his hips (like a walking step), then between his
# left foot and Uki's right leg.
SWING_VIA = (G(0.34, 0.16, 0.30), G(0.39, 0.22, 0.56))


def tori_reaping_foot():
    """The right foot's path (world, not interpolated rotations, which swing it through the mat and
    Uki's leg): forward between the standing foot and Uki's right leg to behind Uki's knee, the reap
    back and up, down behind Tori."""
    motion.step("Tori", "Right", frame(0.36), frame(0.54), height=0.04, to=SWING_VIA[0])
    motion.step("Tori", "Right", frame(0.54), frame(0.66), height=0.0, to=SWING_VIA[1])
    motion.step("Tori", "Right", frame(0.66), frame(0.8), height=0.02)
    motion.step("Tori", "Right", frame(0.8), frame(1.05), height=0.0)
    motion.step("Tori", "Right", frame(1.05), frame(1.3), height=0.12)
    motion.step("Tori", "Right", frame(1.3), frame(1.62), height=0.0)
    motion.step("Tori", "Right", frame(1.62), frame(2.1), height=0.10)
    knee_forward("Tori", "Right", frame(0.36), frame(2.1))


def knee_forward(arm, side, f0, f1, twist=-25):
    """Re-solve a free leg on every frame with the knee bending forward (the IK in step() keeps the
    interpolated bending plane, which can swing the knee sideways); the foot keeps its world pose.
    `twist`: the bending plane turned about the thigh (for Tori's right leg negative: the knee
    passes outside Uki's right thigh)."""
    scene = bpy.context.scene
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        m = motion.foot_matrix(arm, side)
        tt.rot(arm, f"{side}UpLeg", (80, 0, twist))
        tt.rot(arm, f"{side}Leg", (-90, 0, 0))
        motion.leg_ik(arm, side, m.translation, m.to_3x3())
        tt.key(arm, f, bones=[f"{side}UpLeg", f"{side}Leg", f"{side}Foot"], root=False)


def shape():
    """Timing, feet, weight and fall on top of the keyed poses (in this order: see motion.py)."""
    motion.ease(frame(0.0), "EASE_IN")
    motion.ease(frame(0.8), "EASE_IN", "QUAD")  # fast reap
    motion.ease(frame(1.62), "EASE_OUT")
    # Tori: the left foot steps in beside Uki's right foot, the right foot pushes off and swings.
    motion.plant("Tori", "Right", frame(0.0), frame(0.24))
    motion.plant("Tori", "Right", frame(0.24), frame(0.36), pivot="toe")
    motion.plant("Tori", "Left", frame(0.0), frame(0.04))
    motion.step("Tori", "Left", frame(0.04), frame(0.26), height=0.10, to=TORI_LEFT)
    motion.plant("Tori", "Left", frame(0.26), frame(2.5))
    tori_reaping_foot()
    motion.plant("Tori", "Right", frame(2.1), frame(2.5))
    # The weight goes from the right foot to the left one while both are on the mat (0.28-0.36 s).
    motion.shift_weight("Tori", "Right", frame(0.0), frame(0.32), ramp=(4, 2))
    motion.shift_weight("Tori", "Left", frame(0.28), frame(2.1), ramp=(3, 4))
    motion.shift_weight("Tori", "both", frame(2.1), frame(2.5), ramp=6)
    # Uki: both feet on the mat until the reap; the left foot until he tips over.
    motion.plant("Uki", "Right", frame(0.0), frame(0.9))
    motion.plant("Uki", "Left", frame(0.0), frame(0.8))
    motion.plant("Uki", "Left", frame(0.8), frame(1.05), pivot="toe")
    motion.fall("Uki", frame(1.3), frame(1.62))
    # Grips held on every frame, each hand after the arm it holds has its final motion: the lapels sit
    # on the chests, the sleeves on the partner's gripping arm (Tori's sleeve hand comes last).
    # Tori's lapel arm: elbow down and back, not into Uki's chest as he steps in.
    motion.hold("Tori", "RightHand", "Uki", "LeftLapelGrip", frame(0.0), frame(1.3), pole=(0, -1, 1))
    motion.hold("Uki", "RightHand", "Tori", "LeftLapelGrip", frame(0.0), frame(0.95))  # until he tips over
    motion.hold("Uki", "LeftHand", "Tori", "RightSleeveGrip", frame(0.0), frame(0.95))
    motion.repose("Uki", ["RightArm", "RightForearm"], frame(1.3), frame(1.62), uki_arm_held)  # w: 0 -> 1
    motion.repose("Uki", ["RightArm", "RightForearm"], frame(1.62), frame(2.5), lambda _w: uki_arm_held())
    # Arms that have let go find their way around the partner's body.
    for _ in range(2):
        motion.avoid("Uki", ["RightArm", "RightForearm"], "Tori", frame(0.95), frame(1.3), ALLOW, max_rate=6)
        motion.avoid("Uki", ["LeftArm", "LeftForearm"], "Tori", frame(0.95), frame(1.5), ALLOW, max_rate=6)
        motion.avoid("Tori", ["RightArm", "RightForearm"], "Uki", frame(1.3), frame(2.1), ALLOW, max_rate=6)
    motion.smooth("Uki", ["LeftArm", "LeftForearm", "RightArm", "RightForearm"], frame(0.95), frame(1.5))
    for j in ("Tori", "Uki"):
        print(f"Elbow hinge {j}: largest upper-arm twist", motion.hinge_elbows(j, 0, frame(2.5)))
    # The hinge twists the forearms, and with them the sleeves (off the forearm's axis): the sleeve
    # hands take hold again.
    motion.hold("Tori", "LeftHand", "Uki", "RightSleeveGrip", frame(0.0), frame(2.5))
    # Tori's sleeve elbow finds its way round Uki's gripping forearm (the hand taking hold again).
    for _ in range(2):
        motion.avoid("Tori", ["LeftArm"], "Uki", frame(0.0), frame(1.3), ALLOW, step=8, max_rate=3)
        motion.hold("Tori", "LeftHand", "Uki", "RightSleeveGrip", frame(0.0), frame(2.5))
    motion.hold("Uki", "LeftHand", "Tori", "RightSleeveGrip", frame(0.0), frame(0.95))
    # The other gripping arms swing their elbows clear of the arm that moved last.
    motion.clear_arm("Uki", "Right", "Tori", frame(0.0), frame(1.5), max_rate=25)
    motion.clear_arm("Tori", "Left", "Uki", frame(0.0), frame(1.3), max_rate=25)


def check():
    """Print the reports the technique must pass (CLAUDE.md, phase 7)."""
    contact.check_all(ALLOW)
    motion.print_sliding(motion.foot_sliding("Tori"), "Foot sliding Tori")
    motion.print_sliding(motion.foot_sliding("Uki", 0, frame(0.9)), "Foot sliding Uki (on the mat)")
    motion.print_balance("Tori (step in)", motion.balance("Tori", 0, frame(0.4)))
    motion.print_balance("Tori (reap)", motion.balance("Tori", frame(0.4), frame(1.62)))
    motion.print_balance("Tori (after the throw)", motion.balance("Tori", frame(1.62), frame(2.5)))
    landing = motion.first_mat_contact("Uki", ["Hips", "Spine", "LeftHand", "LeftForearm"], frame(1.2))
    print("Uki on the mat:", {b: t for b, t in landing.items()})


def main(upto=None, export=True):
    scene = bpy.context.scene
    scene.render.fps = tt.FPS
    for j in ("Tori", "Uki"):
        arm = bpy.data.objects[j]
        if arm.animation_data:
            arm.animation_data_clear()
    for kf in KEYFRAMES[:upto]:
        f = frame(kf["time"])
        scene.frame_set(f)
        for j in ("Tori", "Uki"):
            tt.reset(j)
        kf["pose"]()
        for j in ("Tori", "Uki"):
            tt.key(j, f)
    scene.frame_start, scene.frame_end = 0, frame(META["duration_seconds"])
    if upto is None:
        shape()
        check()
        if export:
            return tt.export_yaml(OUT, META, [{k: v for k, v in kf.items() if k != "pose"} for kf in KEYFRAMES])


if __name__ == "__main__":
    main()

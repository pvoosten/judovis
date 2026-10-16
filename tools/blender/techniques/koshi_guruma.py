"""Koshi-guruma (right-handed Tori) - authored in Blender, exported to data/techniques/.

Run headless (see tools/blender/README.md):
    blender -b art_source/blender/judoka.blend --python tools/blender/run_technique.py -- koshi_guruma --draft

Tori breaks Uki's balance forward so that Uki bends a little, puts the right arm around Uki's neck,
turns in like ippon-seoi-nage but with the right hip a little past Uki's right hip, bends over to
lift Uki and turns further: Uki wheels over the hip and lands on the back in front of Tori, who keeps
the sleeve.
"""
import importlib
import os
import sys

import bpy
from mathutils import Vector

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..") if "__file__" in globals() \
    else r"C:\proj\judo\tools\blender"
sys.path.insert(0, os.path.normpath(TOOLS))
import technique_tools as tt  # noqa: E402
import contact  # noqa: E402
import motion  # noqa: E402
import poses  # noqa: E402
for _m in (tt, contact, motion, poses):
    importlib.reload(_m)
from poses import (ankles_mid, arms_ready, axis, crouch, facing, frame, grip, on_toes, pairs,  # noqa: E402
                   right_of, stance, stand, uki_arm_held, uki_left_arm_along_side, uki_left_arm_on_back,
                   GRIP_DISTANCE)

NAME = "koshi_guruma"
OUT = os.path.normpath(os.path.join(TOOLS, "..", "..", "data", "techniques", f"{NAME}.yaml"))

META = dict(technique_name="Koshi-guruma", dutch_name="Heupwiel", waza_group="nage_waza",
            category="Koshi-waza (Heupworp)", code="N5-1", difficulty="Easy", kyu_grade=5,
            belt_name="Gele band", belt_hex="#FFD700", source="VJF leerlijn 2015, geel", duration_seconds=2.6)

STANCE_WIDTH = 0.26  # between Tori's ankles in tsukuri
HIP_PAST = 0.03      # Tori's hips to the right of Uki's (his right hip past Uki's right hip)
UKI_SIDE_BEND = -20  # Uki's spine and chest bend to his right, over Tori's right shoulder

ALLOW = (
    # Kumikata: hands on lapel and sleeve; the gripping arms rub against each other.
    pairs(["Tori:RightHand"], ["Uki:Chest", "Uki:LeftShoulder"], 0.07, end=0.5)
    + pairs(["Uki:RightHand"], ["Tori:Chest", "Tori:LeftShoulder", "Tori:LeftArm"], 0.07, end=0.9)
    + pairs(["Uki:LeftHand"], ["Tori:RightForearm", "Tori:RightArm", "Tori:RightShoulder"], 0.07, end=0.9)
    + pairs(["Tori:LeftHand"], ["Uki:RightForearm", "Uki:RightArm", "Uki:RightHand"], 0.07)
    + pairs(["Tori:LeftForearm"], ["Uki:RightForearm", "Uki:RightHand"], 0.06)
    + pairs(["Tori:*Forearm", "Tori:*Arm"], ["Uki:*Forearm", "Uki:*Arm"], 0.045, end=0.9)
    # Tori's right arm round Uki's neck, the hand on the back of the collar (loose gi, a hollow
    # behind the neck the capsules do not model).
    + pairs(["Tori:RightArm", "Tori:RightForearm", "Tori:RightHand"],
            ["Uki:Neck", "Uki:Head", "Uki:Chest", "Uki:RightShoulder", "Uki:LeftShoulder"], 0.07, 0.5, 1.8)
    # Tori's upper arm comes up between Uki's neck and right shoulder (Uki's armpit on it).
    + pairs(["Tori:RightArm", "Tori:RightShoulder"], ["Uki:RightArm", "Uki:RightShoulder"], 0.07, 0.6, 1.8)
    # Uki's head pressed against Tori's right shoulder and head.
    + pairs(["Uki:Head", "Uki:Neck"], ["Tori:RightShoulder", "Tori:Neck", "Tori:Head", "Tori:RightArm"], 0.04, 0.6, 1.8)
    # Tori pulls Uki's right arm (by the sleeve) tight against his chest.
    + pairs(["Uki:RightForearm", "Uki:RightHand", "Uki:RightArm"],
            ["Tori:Chest", "Tori:LeftShoulder", "Tori:LeftForearm", "Tori:LeftArm"], 0.05, 0.6, 2.0)
    # Koshi-waza: Uki's front is pressed on Tori's back and hips, and wheels over the right hip.
    + pairs(["Tori:Chest", "Tori:Spine", "Tori:Hips", "Tori:RightShoulder", "Tori:RightUpLeg"],
            ["Uki:Chest", "Uki:Spine", "Uki:Hips", "Uki:*UpLeg"], 0.04, 0.8, 1.9)
    + pairs(["*Foot"], [contact.MAT], 0.03)
)

BODY_ALLOW = poses.body_allow(ALLOW)
TORI_FEET = {}  # the right toe where Tori steps in (pivot of tai-sabaki), then the middle of the ankles
LAPEL_ARM = {}  # Tori's right arm on Uki's lapel at kuzushi: start of the swing round the neck


def push_back(direction):
    poses.push_back(ALLOW, direction)


def arm_round_neck(_w=None, across=0.07, behind=0.02, pole=(0.3, 0.3, -1.0)):
    """Tori's right arm round Uki's neck, the hand on the back of Uki's collar (a little towards his
    left side), in Uki's own frame (valid however Uki is turned). Two-link solve: the hand lands on
    the collar point and the elbow bends towards `pole` (Uki's frame: right, up, back; default in
    front of his neck). Aimed from the rest pose: no twist builds up frame to frame."""
    right, along, back = axis("Uki", (1, 0, 0)), axis("Uki", (0, 1, 0)), axis("Uki", (0, 0, 1))
    hand = tt.bone_pos("Uki", "BackCollarGrip") - right * across + back * behind
    shoulder = tt.bone_pos("Tori", "RightArm")
    upper = (tt.bone_pos("Tori", "RightArm", tail=True) - shoulder).length
    lower = (tt.bone_pos("Tori", "RightForearm", tail=True) - tt.bone_pos("Tori", "RightForearm")).length
    lower += (tt.bone_pos("Tori", "RightHand", tail=True) - tt.bone_pos("Tori", "RightHand")).length
    reach = hand - shoulder
    d = min(reach.length, 0.98 * (upper + lower))
    u = reach.normalized()
    hint = right * pole[0] + along * pole[1] + back * pole[2]
    perp = (hint - u * hint.dot(u)).normalized()
    a = (upper ** 2 - lower ** 2 + d ** 2) / (2 * d)
    elbow = shoulder + u * a + perp * max(upper ** 2 - a ** 2, 0.0) ** 0.5
    for b in ("RightArm", "RightForearm", "RightHand"):
        tt.rot("Tori", b, (0, 0, 0))
    tt.aim_at("Tori", "RightArm", elbow)
    tt.aim_at("Tori", "RightForearm", shoulder + u * d)


def arm_to_neck(w):
    """Tori's right arm swings from the lapel (kuzushi) round Uki's neck: a blend of the two poses'
    rotations, each of them twist-free, so the elbow does not flip on the way."""
    arm_round_neck()
    pose = bpy.data.objects["Tori"].pose.bones
    s = w * w * (3 - 2 * w)
    for b in ("RightArm", "RightForearm", "RightHand"):
        pose[b].rotation_quaternion = LAPEL_ARM[b].slerp(pose[b].rotation_quaternion.copy(), s)


def uki_arm_swing(w):
    """Uki's held right arm follows him forward over the first 0.2 s of the fall (the pull point moves
    ahead of Tori's chest as Tori comes up), then rests where uki_arm_held() puts it: the hand does not
    move back towards Tori while Uki's body travels away from him."""
    s = min(1.0, w / 0.25)
    uki_arm_held(ahead=0.4 + 0.25 * s * s * (3 - 2 * s))


def uki_arm_under_armpit():
    """Uki's right arm pulled by the sleeve under Tori's raised right arm, across Tori's chest."""
    chest = tt.bone_pos("Tori", "Chest")
    tt.aim_at("Uki", "RightArm", chest + facing("Tori") * 0.30 + right_of("Tori") * 0.05 - Vector((0, 0, 0.10)))
    tt.aim_at("Uki", "RightForearm", chest + facing("Tori") * 0.45 - right_of("Tori") * 0.15 - Vector((0, 0, 0.12)))


def hips_past(offset=HIP_PAST):
    """Move Uki sideways so Tori's hips are `offset` to the right of Uki's."""
    right = right_of("Tori")
    d = (tt.bone_pos("Tori", "Hips") - tt.bone_pos("Uki", "Hips")).dot(right) - offset
    bpy.data.objects["Uki"].location += right * d
    tt._update()


# --- keyframe poses ------------------------------------------------------------------------------

def kumikata():
    tt.place("Tori", (0, 0, 0), (0, 0, 0))
    tt.place("Uki", (0, 0, GRIP_DISTANCE), (0, 180, 0))
    for j in ("Tori", "Uki"):
        stance(j, left=1 if j == "Uki" else 4)
        tt.rot(j, "Spine", (-6, 0, 0))
        arms_ready(j)
        tt.ground(j)
    grip()


def kuzushi():
    # Uki is pulled forward onto the toes and bends a little: Tori's arm goes round his neck.
    tt.place("Uki", (0, 0, 0.58), (0, 180, 0))
    on_toes("Uki")
    tt.rot("Uki", "Spine", (-18, 0, 0))
    tt.rot("Uki", "Chest", (-8, 0, 0))
    tt.rot("Uki", "Neck", (10, 0, 0))
    arms_ready("Uki")
    tt.ground("Uki")
    # Tori steps in with the right foot, toes turned in, and starts turning to the left.
    tt.place("Tori", (0.05, 0, 0.08), (0, 45, 0))
    stance("Tori", knee=18)
    tt.rot("Tori", "RightUpLeg", (30, 0, 4))
    tt.rot("Tori", "RightLeg", (-36, 0, 0))
    tt.rot("Tori", "RightFoot", (6, 0, 0))
    tt.rot("Tori", "LeftUpLeg", (-10, 0, -6))
    tt.rot("Tori", "LeftLeg", (-16, 0, 0))
    tt.rot("Tori", "LeftFoot", (26, 0, 0))
    tt.rot("Tori", "Spine", (-4, 0, 0))
    arms_ready("Tori")
    tt.ground("Tori")
    TORI_FEET["pivot"] = tt.bone_pos("Tori", "RightFoot", tail=True)
    grip()
    for b in ("RightArm", "RightForearm", "RightHand"):
        LAPEL_ARM[b] = bpy.data.objects["Tori"].pose.bones[b].rotation_quaternion.copy()


def tai_sabaki():
    # Uki is drawn further forward, his head pulled down by Tori's arm.
    tt.place("Uki", (0, 0, 0.55), (0, 180, 0))
    on_toes("Uki", 30)
    tt.rot("Uki", "Spine", (-24, 0, UKI_SIDE_BEND / 2))
    tt.rot("Uki", "Chest", (-10, 0, UKI_SIDE_BEND / 2))
    tt.rot("Uki", "Neck", (10, 0, -UKI_SIDE_BEND / 2))
    arms_ready("Uki")
    tt.ground("Uki")
    # Tori pivots on the right foot and swings the left foot back, knees bending.
    tt.place("Tori", (0.04, 0, 0.22), (0, 120, 0))
    crouch("Tori", 30)
    tt.rot("Tori", "Spine", (-8, 0, 0))
    stand("Tori", TORI_FEET["pivot"], lambda: tt.bone_pos("Tori", "RightFoot", tail=True))
    push_back(-facing("Uki"))
    # Uki's right arm is drawn out in front of Tori by the sleeve.
    chest = tt.bone_pos("Tori", "Chest", tail=True)
    tt.aim_at("Uki", "RightArm", chest + facing("Tori") * 0.50 + right_of("Tori") * 0.10 - Vector((0, 0, 0.05)))
    tt.aim_at("Uki", "RightForearm", chest + facing("Tori") * 0.70 - right_of("Tori") * 0.10 - Vector((0, 0, 0.05)))
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")
    arm_round_neck()
    tt.aim("Uki", "LeftArm", (-0.7, -0.65, 0.1))
    tt.aim("Uki", "LeftForearm", (-0.5, -0.6, -0.6))


def tsukuri():
    # Tori has turned his back in, hips low and pushed through: his right hip past Uki's right hip.
    tt.place("Tori", (0, 0, 0.28), (0, 180, 0))
    crouch("Tori", 40)
    tt.rot("Tori", "Spine", (-20, 0, 0))
    tt.rot("Tori", "Chest", (-5, 0, 0))
    stand("Tori", TORI_FEET["pivot"], lambda: tt.bone_pos("Tori", "RightFoot", tail=True))
    TORI_FEET["mid"] = ankles_mid("Tori")
    # Uki is drawn onto Tori's back and hips, still on the toes, his head next to Tori's.
    tt.place("Uki", (0, 0, 0.30), (0, 180, 0))  # too close: push_back() resolves it
    on_toes("Uki", 30)
    # Bent forward and to his right: his head comes over Tori's right shoulder, beside Tori's head.
    tt.rot("Uki", "Spine", (-28, 0, UKI_SIDE_BEND))
    tt.rot("Uki", "Chest", (-12, 0, UKI_SIDE_BEND))
    tt.rot("Uki", "Neck", (15, 0, -UKI_SIDE_BEND))
    tt.ground("Uki")
    hips_past()
    push_back(-facing("Tori"))
    uki_left_arm_on_back()
    uki_arm_under_armpit()
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")
    arm_round_neck()


def kake():
    # Tori straightens his legs a little and bows forward, turning further to the left: Uki comes off
    # the mat, lying across Tori's right hip.
    tt.place("Tori", (0, 0, 0.26), (0, 195, 0))
    crouch("Tori", 25)
    tt.rot("Tori", "Spine", (-32, 0, 0))
    tt.rot("Tori", "Chest", (-12, 0, 0))
    tt.rot("Tori", "Neck", (-10, 0, 0))
    stand("Tori", TORI_FEET["mid"], lambda: ankles_mid("Tori"))
    tt.place("Uki", (0, 0, 0.5), (-50, 180, 15))
    tt.rot("Uki", "Spine", (-12, 0, 0))
    tt.rot("Uki", "Chest", (-8, 0, 0))
    tt.rot("Uki", "LeftUpLeg", (10, 0, -6))
    tt.rot("Uki", "RightUpLeg", (10, 0, 6))
    tt.rot("Uki", "LeftLeg", (-15, 0, 0))
    tt.rot("Uki", "RightLeg", (-15, 0, 0))
    tt.pin("Uki", "Spine", tt.bone_pos("Tori", "Spine", tail=True) - facing("Tori") * 0.10
           + right_of("Tori") * 0.04 + Vector((0, 0, 0.10)))
    push_back(Vector((0, 0, 1)) - facing("Tori"))
    uki_left_arm_along_side()
    uki_arm_under_armpit()
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")
    arm_round_neck()


def nage():
    # Tori bows deeply, turning and pulling the sleeve down towards his left hip: Uki wheels over
    # the right hip, head first.
    tt.place("Tori", (0, 0, 0.24), (0, 215, 0))
    crouch("Tori", 18)
    tt.rot("Tori", "Spine", (-42, 0, 0))
    tt.rot("Tori", "Chest", (-15, 0, 0))
    tt.rot("Tori", "Neck", (-10, 0, 0))
    stand("Tori", TORI_FEET["mid"], lambda: ankles_mid("Tori"))
    tt.place("Uki", (0, 0, 0), (-115, 180, 20))
    tt.rot("Uki", "Spine", (-12, 0, 0))
    tt.rot("Uki", "LeftUpLeg", (25, 0, -6))
    tt.rot("Uki", "RightUpLeg", (25, 0, 6))
    tt.rot("Uki", "LeftLeg", (-25, 0, 0))
    tt.rot("Uki", "RightLeg", (-25, 0, 0))
    uki_left_arm_along_side()
    tt.pin("Uki", "Spine", tt.bone_pos("Tori", "Hips") + right_of("Tori") * 0.12 + facing("Tori") * 0.05
           + Vector((0, 0, 0.25)))
    push_back(Vector((0, 0, 1)) + facing("Tori"))
    uki_arm_held()
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")
    arm_round_neck()


def fall():
    # Tori lets go of the neck; Uki falls back-first in front of Tori, the left arm out for the slap.
    tt.place("Tori", (0, 0, 0.22), (0, 212, 0))
    crouch("Tori", 15)
    tt.rot("Tori", "Spine", (-32, 0, 0))
    tt.rot("Tori", "Chest", (-10, 0, 0))
    tt.aim("Tori", "RightArm", (0.75, -0.3, 0.55))
    tt.aim("Tori", "RightForearm", (0.6, -0.6, 0.2))
    stand("Tori", TORI_FEET["mid"], lambda: ankles_mid("Tori"))
    tt.place("Uki", (0, 0, 0), (-225, 180, 10))
    tt.rot("Uki", "LeftUpLeg", (30, 0, -6))
    tt.rot("Uki", "RightUpLeg", (30, 0, 6))
    tt.rot("Uki", "LeftLeg", (-35, 0, 0))
    tt.rot("Uki", "RightLeg", (-35, 0, 0))
    tt.rot("Uki", "Neck", (-25, 0, 0))
    tt.aim("Uki", "LeftArm", (-0.55, 0.25, -0.8))
    tt.aim("Uki", "LeftForearm", (-0.1, 0.55, -0.83))
    tt.pin("Uki", "Spine", tt.bone_pos("Tori", "Hips") + facing("Tori") * 0.70 + Vector((0, 0, -0.45)))
    uki_arm_held()
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def ukemi_pose(tori_bow):
    tt.rot("Tori", "Spine", (tori_bow, 0, 0))
    tt.aim("Tori", "RightArm", (0.35, -1, 0))
    tt.aim("Tori", "RightForearm", (0.15, -1, -0.3))
    stand("Tori", TORI_FEET["mid"], lambda: ankles_mid("Tori"))
    # Uki on the back, head towards Tori, chin tucked, slapping the mat with the left arm.
    tt.place("Uki", (0, 0, 0), (-270, 180, 5))
    tt.rot("Uki", "LeftUpLeg", (40, 0, -8))
    tt.rot("Uki", "RightUpLeg", (40, 0, 8))
    tt.rot("Uki", "LeftLeg", (-45, 0, 0))
    tt.rot("Uki", "RightLeg", (-45, 0, 0))
    tt.rot("Uki", "Neck", (-25, 0, 0))
    tt.pin("Uki", "Spine", tt.bone_pos("Tori", "Hips") + facing("Tori") * 1.1)
    uki_arm_held()
    motion.settle("Uki")
    poses.slap("Uki", "Left")
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def ukemi():
    tt.place("Tori", (0, 0, 0.28), (0, 208, 0))
    crouch("Tori", 15)
    ukemi_pose(-25)


def zanshin():
    tt.place("Tori", (0, 0, 0.30), (0, 205, 0))
    crouch("Tori", 8)
    ukemi_pose(-12)


KEYFRAMES = [
    dict(time=0.0, phase="Kumikata (Grip)",
         description="Tori en Uki pakken elkaar vast: rechterhand aan de revers, linkerhand aan de mouw.",
         pose=kumikata),
    dict(time=0.4, phase="Kuzushi (Balansverstoring)",
         description="Tori stapt in met rechts, trekt Uki naar voren en slaat de rechterarm om Uki's nek.",
         pose=kuzushi),
    dict(time=0.76, phase="Tsukuri (Instap & Draai)",
         description="Tori draait op de rechtervoet en zwaait de linkervoet terug; Uki's hoofd wordt omlaag getrokken.",
         pose=tai_sabaki),
    dict(time=1.06, phase="Tsukuri (Instap & Draai)",
         description="Tori staat met de rug tegen Uki, door de knieën; zijn rechterheup steekt voorbij die van Uki.",
         pose=tsukuri),
    dict(time=1.4, phase="Kake (Worp)",
         description="Tori buigt voorover en draait verder: Uki komt los van de mat, over Tori's heup.",
         pose=kake),
    dict(time=1.7, phase="Nage (Rotatie)",
         description="Uki draait als een wiel over Tori's rechterheup.",
         pose=nage),
    dict(time=1.96, phase="Nage (Val)",
         description="Tori laat de nek los; Uki valt met de rug naar de mat en zwaait de linkerarm uit.",
         pose=fall),
    dict(time=2.2, phase="Ukemi (Valbreking)",
         description="Uki landt op de rug en slaat af met de linkerarm; Tori houdt de mouw vast.",
         pose=ukemi),
    dict(time=2.6, phase="Zanshin (Controle)",
         description="Tori komt overeind en houdt Uki onder controle aan de mouw.",
         pose=zanshin),
]


def tori_feet():
    """Tori: right foot steps in, then pivots on its ball while the left foot swings back."""
    motion.plant("Tori", "Left", frame(0.0), frame(0.52))
    motion.plant("Tori", "Right", frame(0.0), frame(0.08))
    motion.step("Tori", "Right", frame(0.08), frame(0.36))
    motion.plant("Tori", "Right", frame(0.36), frame(1.06), pivot="toe")
    bpy.context.scene.frame_set(frame(1.06))
    beside = motion.foot_matrix("Tori", "Right").translation - right_of("Tori") * STANCE_WIDTH
    beside.z = motion.ANKLE_HEIGHT
    bpy.context.scene.frame_set(frame(0.52))
    pivot = bpy.data.objects["Tori"].matrix_world @ bpy.data.objects["Tori"].pose.bones["RightFoot"].tail
    motion.step("Tori", "Left", frame(0.52), frame(0.92), height=0.10, to=beside, around=pivot)
    motion.plant("Tori", "Left", frame(0.92), frame(1.06))
    for side in ("Left", "Right"):
        motion.plant("Tori", side, frame(1.06), frame(2.6))


def tori_weight():
    motion.shift_weight("Tori", "Left", frame(0.0), frame(0.44), ramp=4)
    motion.shift_weight("Tori", "Right", frame(0.44), frame(0.92), ramp=4)
    motion.shift_weight("Tori", "both", frame(0.92), frame(2.6), ramp=10)


def shape():
    motion.ease(frame(0.0), "EASE_IN")
    motion.ease(frame(1.06), "EASE_IN", "QUAD")
    motion.ease(frame(2.2), "EASE_OUT")
    motion.pivot("Uki", "Chest", frame(0.76), frame(1.06))
    tori_feet()
    tori_weight()
    contact.resolve("Uki", "Tori", frame(0.4), frame(1.06), BODY_ALLOW, direction=-facing("Tori"))
    for a, b in ((1.06, 1.4), (1.4, 1.7)):
        motion.carry("Tori", "Hips", "Uki", "Hips", frame(a), frame(b))
    contact.resolve("Uki", "Tori", frame(1.08), frame(1.4), BODY_ALLOW, direction=-facing("Tori"))
    contact.resolve("Uki", "Tori", frame(1.4), frame(1.7), BODY_ALLOW, direction=Vector((0, 0, 1)) + facing("Tori"))
    motion.shift_weight("Tori", "both", frame(1.0), frame(1.7) + 1, ramp=(3, 1), carrying="Uki")
    released = []
    for side in ("Left", "Right"):
        motion.plant("Uki", side, frame(0.0), frame(1.06), pivot="toe")
        lifted = motion.plant("Uki", side, frame(1.06), frame(1.4), pivot="toe", until_lifted=True)
        released.append(lifted or frame(1.4))
        print(f"Uki's {side.lower()} foot leaves the mat at {lifted / tt.FPS if lifted else None}s")
    motion.fall("Uki", frame(1.7), frame(2.2))
    motion.repose("Uki", ["RightArm", "RightForearm"], frame(1.7), frame(2.6), uki_arm_swing)
    # Tori's arm stays round Uki's neck however Uki turns, until he lets go.
    motion.repose("Tori", ["RightArm", "RightForearm", "RightHand"], frame(0.4), frame(0.76), arm_to_neck)
    motion.repose("Tori", ["RightArm", "RightForearm", "RightHand"], frame(0.76), frame(1.7), arm_round_neck)
    contact.resolve("Uki", "Tori", frame(1.7) + 1, frame(2.0), BODY_ALLOW, direction=Vector((0, 0, 1)) + facing("Tori"))
    motion.avoid("Uki", ["Chest", "Neck"], "Tori", frame(0.4), frame(1.06), BODY_ALLOW, step=8, max_rate=3)
    motion.hold("Tori", "LeftHand", "Uki", "RightSleeveGrip", frame(0.0), frame(2.6))
    motion.hold("Tori", "RightHand", "Uki", "LeftLapelGrip", frame(0.0), frame(0.4))
    motion.hold("Uki", "RightHand", "Tori", "LeftLapelGrip", frame(0.0), frame(0.4))
    motion.hold("Uki", "LeftHand", "Tori", "RightSleeveGrip", frame(0.0), frame(0.5))
    motion.avoid("Tori", ["Neck"], "Uki", frame(0.8), frame(2.0), ALLOW, step=8, max_rate=3)
    for _ in range(3):
        motion.avoid("Tori", ["RightArm", "RightForearm"], "Uki", frame(0.2), frame(1.9), ALLOW, max_rate=6)
        for side in ("Right", "Left"):
            motion.avoid("Uki", [f"{side}Arm", f"{side}Forearm"], "Tori", frame(0.4), frame(2.1), ALLOW,
                         max_rate=6)
    for side in ("Right", "Left"):
        motion.avoid("Uki", [f"{side}UpLeg", f"{side}Leg"], "Tori", max(released) + 1, frame(1.6), ALLOW, step=6)
    motion.smooth("Uki", ["LeftArm", "LeftForearm", "RightArm", "RightForearm"], frame(0.4), frame(2.14))
    for j in ("Tori", "Uki"):
        print(f"Elbow hinge {j}: largest upper-arm twist", motion.hinge_elbows(j, 0, frame(2.6)))


def check():
    contact.check_all(ALLOW)
    motion.print_sliding(motion.foot_sliding("Tori"), "Foot sliding Tori")
    motion.print_sliding(motion.foot_sliding("Uki", 0, frame(1.4)), "Foot sliding Uki (on the mat)")
    motion.print_balance("Tori (entry)", motion.balance("Tori", 0, frame(1.0)))
    motion.print_balance("Tori (carrying Uki)", motion.balance("Tori", frame(1.0) + 3, frame(1.5), carrying="Uki"))
    motion.print_balance("Tori (throw, dynamic)", motion.balance("Tori", frame(1.5), frame(1.7), carrying="Uki"))
    motion.print_balance("Tori (after the throw)", motion.balance("Tori", frame(1.7) + 1, frame(2.6)))
    landing = motion.first_mat_contact("Uki", ["Hips", "Spine", "LeftHand", "LeftForearm"], frame(1.5))
    print("Uki on the mat:", {b: t for b, t in landing.items()})


def main(upto=None, export=True):
    scene = bpy.context.scene
    scene.render.fps = tt.FPS
    for j in ("Tori", "Uki"):
        arm = bpy.data.objects[j]
        if arm.animation_data:
            arm.animation_data_clear()
    for kf in KEYFRAMES[:upto]:
        scene.frame_set(frame(kf["time"]))
        for j in ("Tori", "Uki"):
            tt.reset(j)
        kf["pose"]()
        for j in ("Tori", "Uki"):
            tt.key(j, frame(kf["time"]))
    scene.frame_start, scene.frame_end = 0, frame(META["duration_seconds"])
    if upto is None:
        shape()
        check()
        if export:
            return tt.export_yaml(OUT, META, [{k: v for k, v in kf.items() if k != "pose"} for kf in KEYFRAMES])


if __name__ == "__main__":
    main()

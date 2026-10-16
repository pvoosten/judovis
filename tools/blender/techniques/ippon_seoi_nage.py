"""Ippon Seoi-nage (right-handed Tori) - authored in Blender, exported to data/techniques/.

Run inside Blender with judoka.blend open (Scripting tab or Blender MCP):
    exec(open(r"tools/blender/techniques/ippon_seoi_nage.py").read())
It keys the poses on the timeline (FPS 50), shapes the motion (easing, planted feet, Uki's
ballistic fall), prints the contact / foot / balance reports and writes
data/techniques/ippon_seoi_nage.yaml.

Pose helpers work in each judoka's own frame: X = their right, Y = up, -Z = the way they face
(see tools/blender/technique_tools.py). Root positions/rotations are in Godot space; Tori starts
at the origin facing +Z, Uki faces Tori. World points (bone_pos, pin) are in Blender space.
"""
import os
import sys

import bpy
from mathutils import Vector

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..") if "__file__" in globals() \
    else r"C:\proj\judo\tools\blender"
sys.path.insert(0, os.path.normpath(TOOLS))
import importlib  # noqa: E402
import technique_tools as tt  # noqa: E402
import contact  # noqa: E402
import motion  # noqa: E402
import poses  # noqa: E402
for _m in (tt, contact, motion, poses):
    importlib.reload(_m)
from poses import (ankles_mid, arms_ready, axis, crouch, facing, frame, grip, lerp, on_toes,  # noqa: E402
                   right_of, stance, stand, uki_arm_held, uki_left_arm_along_side, uki_left_arm_on_back,
                   GRIP_DISTANCE)

OUT = os.path.normpath(os.path.join(TOOLS, "..", "..", "data", "techniques", "ippon_seoi_nage.yaml"))

META = dict(technique_name="Ippon Seoi-nage", dutch_name="Schouderworp aan één arm", waza_group="nage_waza",
            category="Te-waza (Handworp)", code="N4-3", difficulty="Medium",
            kyu_grade=4, belt_name="Oranje band", belt_hex="#FF8C00", source="VJF leerlijn 2015, oranje",
            duration_seconds=2.6)

STANCE_WIDTH = 0.26  # between Tori's ankles in tsukuri


# --- allowed contacts (contact.check_contacts) --------------------------------------------------

ALLOW = (
    # Kumikata: hands on lapel and sleeve; the gripping arms rub against each other.
    poses.pairs(["Tori:RightHand"], ["Uki:Chest", "Uki:LeftShoulder"], 0.07, end=0.8)
    + poses.pairs(["Uki:RightHand"], ["Tori:Chest", "Tori:LeftShoulder", "Tori:LeftArm"], 0.07, end=0.9)
    + poses.pairs(["Uki:LeftHand"], ["Tori:RightForearm", "Tori:RightArm"], 0.07, end=0.9)
    + poses.pairs(["Tori:LeftHand"], ["Uki:RightForearm", "Uki:RightArm", "Uki:RightHand"], 0.07)
    + poses.pairs(["Tori:LeftForearm"], ["Uki:RightForearm", "Uki:RightHand"], 0.06)
    + poses.pairs(["Tori:*Forearm", "Tori:*Arm"], ["Uki:*Forearm", "Uki:*Arm"], 0.045, end=0.9)
    # Ippon seoi: Tori's right upper arm is wedged deep in Uki's armpit, under Uki's chest (a hollow
    # the capsules do not model); forearm and hand clamp Uki's upper arm, pressing loose gi sleeves.
    + poses.pairs(["Tori:RightArm"], ["Uki:RightArm", "Uki:RightShoulder", "Uki:Chest", "Uki:Spine"], 0.12, 0.6, 2.0)
    + poses.pairs(["Tori:RightForearm", "Tori:RightHand", "Tori:RightShoulder"],
             ["Uki:RightArm", "Uki:RightShoulder", "Uki:RightForearm", "Uki:Chest", "Uki:Spine"], 0.09, 0.6, 2.0)
    # Tori pulls Uki's right arm (by the sleeve) tight against his chest and shoulders.
    + poses.pairs(["Uki:RightForearm", "Uki:RightHand", "Uki:RightArm"],
             ["Tori:Chest", "Tori:LeftShoulder", "Tori:RightShoulder", "Tori:LeftForearm", "Tori:LeftArm"], 0.05, 0.6, 2.0)
    # While Uki rolls over Tori's shoulder, Tori's gripping arms are pressed into Uki's body.
    + poses.pairs(["Tori:RightHand", "Tori:RightForearm", "Tori:LeftHand", "Tori:LeftForearm"],
             ["Uki:Chest", "Uki:Spine", "Uki:Hips", "Uki:LeftShoulder", "Uki:LeftArm"], 0.09, 1.3, 2.0)
    # Uki is loaded onto Tori's back and hips.
    + poses.pairs(["Tori:Chest", "Tori:Spine", "Tori:Hips", "Tori:RightShoulder", "Tori:LeftShoulder", "Tori:Neck"],
             ["Uki:Chest", "Uki:Spine", "Uki:Hips"], 0.04, 0.7, 1.9)
    + poses.pairs(["*Foot"], [contact.MAT], 0.03)
)


# --- pose building blocks -----------------------------------------------------------------------

# Where Tori's feet are (Blender space), set by the poses in keyframe order: the right toe where he
# steps in at kuzushi (the pivot of tai-sabaki), the middle between the ankles from tsukuri on.
TORI_FEET = {}


def hook_right_arm(up=(0.25, 0.75, 0.6), fore=(-0.4, 0.2, -0.9)):
    """Tori's right arm clamps Uki's right upper arm in the elbow (ippon seoi grip): the elbow up
    under Uki's armpit, the forearm along Uki's upper arm. Directions in Tori's frame; the variants
    per keyframe come from a small search for the least overlap with Uki's head and neck."""
    tt.aim("Tori", "RightArm", up)
    tt.aim("Tori", "RightForearm", fore)


def hook_on_uki(along=0.10, up=0.08, side=0.07, down=0.10):
    """Tori's right arm hooks Uki's right upper arm where it is (ippon seoi grip): the upper arm comes
    up through Uki's armpit to `up` above Uki's upper arm (`along` out from Uki's shoulder joint), the
    forearm comes down on its outer side (`side` out, `down` below): Uki's arm runs across the crook
    of Tori's elbow."""
    s_u, e_u = tt.bone_pos("Uki", "RightArm"), tt.bone_pos("Uki", "RightArm", tail=True)
    u = (e_u - s_u).normalized()
    over = Vector((0, 0, 1))
    over = (over - u * over.dot(u)).normalized()
    out = u.cross(over)
    if out.dot(s_u - tt.bone_pos("Uki", "Chest")) < 0:
        out = -out
    base = s_u + u * along
    tt.rot("Tori", "RightArm", (0, 0, 0))
    tt.rot("Tori", "RightForearm", (0, 0, 0))
    tt.aim_at("Tori", "RightArm", base + over * up)
    tt.aim_at("Tori", "RightForearm", base + out * side - over * down)


def uki_arm_over_shoulder(up=-0.05, side=0.02, ahead=0.30):
    """Uki's right arm over Tori's right shoulder, forearm hanging in front of Tori's chest. The upper
    arm aims at a point `ahead` in front of Tori's shoulder joint, `side` to Tori's right and `up`."""
    sh = tt.bone_pos("Tori", "RightArm")
    fwd, right = facing("Tori"), right_of("Tori")
    tt.aim_at("Uki", "RightArm", sh + fwd * ahead + right * side + Vector((0, 0, up)))
    tt.aim_at("Uki", "RightForearm", sh + fwd * 0.60 - right * 0.05 - Vector((0, 0, 0.22)))


def uki_arm_loaded(w):
    """Uki's right arm over Tori's shoulder between tsukuri (w = 0) and kake (w = 1)."""
    uki_arm_over_shoulder(up=-0.03, side=lerp(0.08, 0.0, w), ahead=0.20)


def uki_arm_thrown(w):
    """Uki's right arm over the shoulder between kake (w = 0) and nage (w = 1)."""
    uki_arm_over_shoulder(up=lerp(-0.03, -0.05, w), side=lerp(0.0, 0.02, w), ahead=lerp(0.20, 0.30, w))


BODY_ALLOW = poses.body_allow(ALLOW)


def push_back(direction):
    poses.push_back(ALLOW, direction)


# --- keyframe poses ------------------------------------------------------------------------------

def kumikata():
    tt.place("Tori", (0, 0, 0), (0, 0, 0))
    tt.place("Uki", (0, 0, GRIP_DISTANCE), (0, 180, 0))
    for j in ("Tori", "Uki"):
        stance(j, left=1 if j == "Uki" else 4)  # Uki's left foot clear of where Tori's left foot lands
        tt.rot(j, "Spine", (-6, 0, 0))
        arms_ready(j)
        tt.ground(j)
    grip()


def kuzushi():
    # Uki is pulled forward onto the toes.
    tt.place("Uki", (0, 0, 0.58), (0, 180, 0))
    on_toes("Uki")
    tt.rot("Uki", "Spine", (-14, 0, 0))
    tt.rot("Uki", "Chest", (-6, 0, 0))
    arms_ready("Uki")
    tt.ground("Uki")
    # Tori steps in with the right foot, toes turned in, and starts turning to the left.
    tt.place("Tori", (0.02, 0, 0.08), (0, 45, 0))
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


def tai_sabaki():
    # Uki is drawn further forward, chest dropping.
    tt.place("Uki", (0, 0, 0.55), (0, 180, 0))
    on_toes("Uki", 30)
    tt.rot("Uki", "Spine", (-22, 0, 0))
    tt.rot("Uki", "Chest", (-10, 0, 0))
    arms_ready("Uki")
    tt.ground("Uki")
    # Tori pivots on the right foot and swings the left foot back, knees bending.
    tt.place("Tori", (0.04, 0, 0.22), (0, 120, 0))
    crouch("Tori", 30)
    tt.rot("Tori", "Spine", (-10, 0, 0))
    stand("Tori", TORI_FEET["pivot"], lambda: tt.bone_pos("Tori", "RightFoot", tail=True))
    push_back(-facing("Uki"))
    # Uki's right arm is drawn out in front of Tori by the sleeve.
    chest = tt.bone_pos("Tori", "Chest", tail=True)
    tt.aim_at("Uki", "RightArm", chest + facing("Tori") * 0.50 + right_of("Tori") * 0.10 - Vector((0, 0, 0.05)))
    tt.aim_at("Uki", "RightForearm", chest + facing("Tori") * 0.70 - right_of("Tori") * 0.10 - Vector((0, 0, 0.05)))
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")
    hook_on_uki()  # under Uki's armpit, now that Uki's arm is in place
    tt.aim("Uki", "LeftArm", (-0.45, -0.75, -0.5))
    tt.aim("Uki", "LeftForearm", (-0.2, -0.5, -0.85))


def tsukuri():
    # Tori has turned his back in, hips below Uki's belt.
    tt.place("Tori", (0, 0, 0.28), (0, 180, 0))
    crouch("Tori", 45)
    tt.rot("Tori", "Spine", (-25, 0, 0))  # leaning forward: Uki's weight comes over Tori's feet
    tt.rot("Tori", "Chest", (-5, 0, 0))
    tt.rot("Tori", "Neck", (10, 0, 0))
    stand("Tori", TORI_FEET["pivot"], lambda: tt.bone_pos("Tori", "RightFoot", tail=True))
    TORI_FEET["mid"] = ankles_mid("Tori")
    hook_right_arm()
    # Uki is drawn onto Tori's back, still on the toes.
    tt.place("Uki", (0.1, 0, 0.32), (0, 180, 0))  # too close: push_back() resolves it
    on_toes("Uki", 30)
    tt.rot("Uki", "Spine", (-30, 0, 0))
    tt.rot("Uki", "Chest", (-15, 0, 0))
    tt.rot("Uki", "Neck", (15, 0, 0))
    tt.ground("Uki")
    push_back(-facing("Tori"))
    uki_arm_loaded(0)  # on top of Tori's upper arm
    uki_left_arm_on_back()
    # Upper arm back and up into Uki's armpit (behind Tori's right shoulder), forearm forward along
    # Uki's upper arm (from a search for the least overlap with the elbow near the armpit).
    hook_right_arm((0.81, 0.32, 0.49), (-0.57, -0.42, -0.71))
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def kake():
    # Tori straightens his legs and bows forward, turning further to the left: Uki comes off the mat.
    tt.place("Tori", (0, 0, 0.26), (0, 195, 0))
    crouch("Tori", 22)
    tt.rot("Tori", "Spine", (-30, 0, 0))
    tt.rot("Tori", "Chest", (-20, 0, 0))
    tt.rot("Tori", "Neck", (-20, 0, 0))
    stand("Tori", TORI_FEET["mid"], lambda: ankles_mid("Tori"))
    hook_right_arm()
    tt.place("Uki", (0.1, 0.25, 0.5), (-55, 180, 15))
    tt.rot("Uki", "Spine", (-15, 0, 0))
    tt.rot("Uki", "Chest", (-10, 0, 0))
    tt.rot("Uki", "LeftUpLeg", (10, 0, -6))
    tt.rot("Uki", "RightUpLeg", (10, 0, 6))
    tt.rot("Uki", "LeftLeg", (-15, 0, 0))
    tt.rot("Uki", "RightLeg", (-15, 0, 0))
    target = (tt.bone_pos("Tori", "RightShoulder", tail=True) - facing("Tori") * 0.12 + right_of("Tori") * 0.10
              + Vector((0, 0, 0.12)))
    tt.pin("Uki", "Chest", target)
    push_back(Vector((0, 0, 1)) - facing("Tori"))
    uki_arm_loaded(1)
    uki_left_arm_along_side()
    hook_right_arm((0.55, 0.6, 0.5), (-0.6, 0.3, -0.75))
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def nage():
    # Tori bows deeply and pulls the sleeve down towards his left hip; Uki rolls over the right shoulder.
    tt.place("Tori", (0, 0, 0.24), (0, 215, 0))
    crouch("Tori", 15)
    tt.rot("Tori", "Spine", (-40, 0, 0))
    tt.rot("Tori", "Chest", (-22, 0, 0))
    tt.rot("Tori", "Neck", (-10, 0, 0))
    stand("Tori", TORI_FEET["mid"], lambda: ankles_mid("Tori"))
    hook_right_arm()
    tt.place("Uki", (0, 0, 0), (-150, 180, 20))
    tt.rot("Uki", "Spine", (-15, 0, 0))
    tt.rot("Uki", "LeftUpLeg", (25, 0, -6))
    tt.rot("Uki", "RightUpLeg", (25, 0, 6))
    tt.rot("Uki", "LeftLeg", (-25, 0, 0))
    tt.rot("Uki", "RightLeg", (-25, 0, 0))
    uki_left_arm_along_side()
    target = tt.bone_pos("Tori", "RightShoulder", tail=True) + facing("Tori") * 0.12 + Vector((0, 0, 0.22))
    tt.pin("Uki", "Spine", target)
    push_back(Vector((0, 0, 1)) + facing("Tori"))
    uki_arm_thrown(1)
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def fall():
    # Uki falls back-first in front of Tori, the left arm swinging out for the slap.
    # (The root position is replaced by the ballistic path; the rotation and limbs are kept.)
    tt.place("Tori", (0, 0, 0.22), (0, 212, 0))
    crouch("Tori", 15)
    tt.rot("Tori", "Spine", (-32, 0, 0))
    tt.rot("Tori", "Chest", (-10, 0, 0))
    # The released right arm comes down along Tori's right side, clear of Uki's head flying past.
    tt.aim("Tori", "RightArm", (0.45, -0.88, 0.1))
    tt.aim("Tori", "RightForearm", (0.35, -0.85, -0.35))
    stand("Tori", TORI_FEET["mid"], lambda: ankles_mid("Tori"))
    tt.place("Uki", (0, 0, 0), (-225, 180, 10))
    tt.rot("Uki", "LeftUpLeg", (30, 0, -6))
    tt.rot("Uki", "RightUpLeg", (30, 0, 6))
    tt.rot("Uki", "LeftLeg", (-35, 0, 0))
    tt.rot("Uki", "RightLeg", (-35, 0, 0))
    tt.rot("Uki", "Neck", (-25, 0, 0))
    tt.aim("Uki", "LeftArm", (-0.55, 0.25, -0.8))
    tt.aim("Uki", "LeftForearm", (-0.1, 0.55, -0.83))
    tori = tt.bone_pos("Tori", "Hips")
    tt.pin("Uki", "Spine", tori + facing("Tori") * 0.75 + Vector((0, 0, -0.45)))
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
    tori = tt.bone_pos("Tori", "Hips")
    tt.pin("Uki", "Spine", tori + facing("Tori") * 1.15)
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
         description="Tori stapt in met rechts en trekt Uki naar voren op de tenen.",
         pose=kuzushi),
    dict(time=0.76, phase="Tsukuri (Instap & Draai)",
         description="Tori draait op de rechtervoet en zwaait de linkervoet terug; de rechterarm gaat onder Uki's oksel.",
         pose=tai_sabaki),
    dict(time=1.06, phase="Tsukuri (Instap & Draai)",
         description="Tori staat met de rug tegen Uki, door de knieën gezakt; Uki's rechterarm zit geklemd.",
         pose=tsukuri),
    dict(time=1.4, phase="Kake (Worp)",
         description="Tori strekt de benen en buigt voorover: Uki komt over zijn rug en los van de mat.",
         pose=kake),
    dict(time=1.7, phase="Nage (Rotatie)",
         description="Uki rolt met het hoofd voorop over Tori's rechterschouder.",
         pose=nage),
    dict(time=1.96, phase="Nage (Val)",
         description="Uki valt met de rug naar de mat; de linkerarm zwaait uit om af te slaan.",
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
    # The left foot swings back next to the right one (parallel, between Uki's feet): Tori's hips
    # then come under Uki.
    bpy.context.scene.frame_set(frame(1.06))
    beside = motion.foot_matrix("Tori", "Right").translation - right_of("Tori") * STANCE_WIDTH
    beside.z = motion.ANKLE_HEIGHT  # flat on the mat (the right foot is on its toes here)
    bpy.context.scene.frame_set(frame(0.52))
    pivot = bpy.data.objects["Tori"].matrix_world @ bpy.data.objects["Tori"].pose.bones["RightFoot"].tail
    motion.step("Tori", "Left", frame(0.52), frame(0.92), height=0.10, to=beside, around=pivot)  # swing back
    motion.plant("Tori", "Left", frame(0.92), frame(1.06))
    for side in ("Left", "Right"):
        motion.plant("Tori", side, frame(1.06), frame(2.6))


def tori_weight():
    """Tori's centre of mass over the standing foot while the other steps; over both feet (with Uki
    on his back) while loading and throwing. Keeps the planted feet in place."""
    # Contiguous windows (the shift is zero at their ends), so the hips never jump between them.
    motion.shift_weight("Tori", "Left", frame(0.0), frame(0.44), ramp=4)
    motion.shift_weight("Tori", "Right", frame(0.44), frame(0.92), ramp=4)
    # Feet side by side from 0.92 s: the hips over both (then shifted further with Uki on the back).
    motion.shift_weight("Tori", "both", frame(0.92), frame(2.6), ramp=10)


def tori_carries_uki():
    """With Uki on his back, Tori keeps their combined centre of mass over his feet (both move). Uki
    already leans on him just before tsukuri; Tori's hips only come back after the release at 1.7 s
    (motion.fall() then re-keys Uki's flight)."""
    motion.shift_weight("Tori", "both", frame(1.0), frame(1.7) + 1, ramp=(3, 1), carrying="Uki")


def shape():
    """Timing, body paths, feet and fall on top of the keyed poses (in this order: see motion.py)."""
    motion.ease(frame(0.0), "EASE_IN")           # kuzushi builds up
    motion.ease(frame(1.06), "EASE_IN", "QUAD")  # fast kake
    motion.ease(frame(2.2), "EASE_OUT")          # standing up after the throw
    # Uki is drawn onto Tori's back about the chest, not about the feet.
    motion.pivot("Uki", "Chest", frame(0.76), frame(1.06))
    # Feet first; the weight shift then moves the hips over the planted feet.
    tori_feet()
    tori_weight()
    # Until tsukuri Uki stands on his own (toes): where the bodies overlap he gives way backwards.
    contact.resolve("Uki", "Tori", frame(0.4), frame(1.06), BODY_ALLOW, direction=-facing("Tori"))
    # From tsukuri until the throw Uki lies on Tori's back: he only rises and turns as Tori lifts him
    # (straightening the legs, bowing, turning), so his motion follows Tori's chest. Remaining overlaps:
    # backwards (never upwards: only Tori lifts him) while loaded, over the shoulder while thrown.
    for a, b in ((1.06, 1.4), (1.4, 1.7)):
        motion.carry("Tori", "Chest", "Uki", "Chest", frame(a), frame(b))
    contact.resolve("Uki", "Tori", frame(1.08), frame(1.4), BODY_ALLOW, direction=-facing("Tori"))
    contact.resolve("Uki", "Tori", frame(1.4), frame(1.7), BODY_ALLOW, direction=Vector((0, 0, 1)) + facing("Tori"))
    tori_carries_uki()
    # Uki's toes stay put (his hips bend down a little where needed), until Tori has lifted him off.
    released = []
    for side in ("Left", "Right"):
        motion.plant("Uki", side, frame(0.0), frame(1.06), pivot="toe")
        lifted = motion.plant("Uki", side, frame(1.06), frame(1.4), pivot="toe", until_lifted=True)
        released.append(lifted or frame(1.4))
        print(f"Uki's {side.lower()} foot leaves the mat at {lifted / tt.FPS if lifted else None}s")
    # Uki's right arm lies over Tori's shoulder while he is loaded and thrown: it follows Tori on
    # every frame instead of interpolating its own rotations while Uki tips over.
    uki_arm = ["RightArm", "RightForearm"]
    motion.repose("Uki", uki_arm, frame(1.06), frame(1.4), uki_arm_loaded)
    motion.repose("Uki", uki_arm, frame(1.4), frame(1.7), uki_arm_thrown)
    # Uki's flight: from the moment Tori releases the rotation until the landing.
    motion.fall("Uki", frame(1.7), frame(2.2))
    # From the release on, Tori holds Uki's right arm up by the sleeve.
    motion.repose("Uki", uki_arm, frame(1.7), frame(2.6), uki_arm_held)
    # Tori's hips come back after the release: Uki flies clear of his head and shoulders.
    contact.resolve("Uki", "Tori", frame(1.7) + 1, frame(2.0), BODY_ALLOW, direction=Vector((0, 0, 1)) + facing("Tori"))
    # Planting the toes lowers Uki a little (after the bodies were pushed apart): his chest and head
    # give way around Tori's shoulder and head instead.
    motion.avoid("Uki", ["Chest", "Neck"], "Tori", frame(0.4), frame(1.06), BODY_ALLOW, step=8, max_rate=3)
    # Grips held on every frame; arms find their way around the partner's body between keyframes.
    motion.hold("Tori", "LeftHand", "Uki", "RightSleeveGrip", frame(0.0), frame(2.6))
    motion.hold("Tori", "RightHand", "Uki", "LeftLapelGrip", frame(0.0), frame(0.4))
    motion.hold("Uki", "RightHand", "Tori", "LeftLapelGrip", frame(0.0), frame(0.4))
    motion.hold("Uki", "LeftHand", "Tori", "RightSleeveGrip", frame(0.0), frame(0.5))
    # Tori's head turns away from Uki's arms as Uki goes over his shoulder.
    motion.avoid("Tori", ["Neck"], "Uki", frame(1.3), frame(2.0), ALLOW, step=8, max_rate=3)
    for _ in range(3):  # Tori's and Uki's arms adjust to each other
        motion.avoid("Tori", ["RightArm", "RightForearm"], "Uki", frame(0.4), frame(1.9), ALLOW, max_rate=6)
        for side in ("Right", "Left"):
            motion.avoid("Uki", [f"{side}Arm", f"{side}Forearm"], "Tori", frame(0.4), frame(2.1), ALLOW,
                         max_rate=6)
    for side in ("Right", "Left"):  # Uki's legs swing past Tori's once they are off the mat
        motion.avoid("Uki", [f"{side}UpLeg", f"{side}Leg"], "Tori", max(released) + 1, frame(1.5), ALLOW, step=6)
    # Uki's arms: take out what flicker avoid() leaves (up to the slap, which must stay on the mat).
    motion.smooth("Uki", ["LeftArm", "LeftForearm", "RightArm", "RightForearm"], frame(0.4), frame(2.14))
    # Elbows bend like hinges (only twists: nothing moves, the contacts stay the same).
    for j in ("Tori", "Uki"):
        print(f"Elbow hinge {j}: largest upper-arm twist", motion.hinge_elbows(j, 0, frame(2.6)))


def check():
    """Print the reports the technique must pass (CLAUDE.md, phase 7)."""
    contact.check_all(ALLOW)
    motion.print_sliding(motion.foot_sliding("Tori"), "Foot sliding Tori")
    motion.print_sliding(motion.foot_sliding("Uki", 0, frame(1.4)), "Foot sliding Uki (on the mat)")
    # The windows of tori_carries_uki(): Uki leans on Tori from 1.0 s (fully after its 3-frame ramp;
    # the partly loaded frames in between are not checked) until the release at 1.7 s.
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

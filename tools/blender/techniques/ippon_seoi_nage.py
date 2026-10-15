"""Ippon Seoi-nage (right-handed Tori) - authored in Blender, exported to data/techniques/.

Run inside Blender with judoka.blend open (Scripting tab or Blender MCP):
    exec(open(r"tools/blender/techniques/ippon_seoi_nage.py").read())
It keys the poses on the timeline (FPS 50) and writes data/techniques/ippon_seoi_nage.yaml.

Pose helpers work in each judoka's own frame: X = their right, Y = up, -Z = the way they face
(see tools/blender/technique_tools.py). Root positions/rotations are in Godot space; Tori starts
at the origin facing +Z, Uki faces Tori.
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
importlib.reload(tt)

OUT = os.path.normpath(os.path.join(TOOLS, "..", "..", "data", "techniques", "ippon_seoi_nage.yaml"))

META = dict(technique_name="Ippon Seoi-nage", dutch_name="Schouderworp aan één arm", waza_group="nage_waza",
            category="Te-waza (Handworp)", code="N4-3", difficulty="Medium",
            kyu_grade=4, belt_name="Oranje band", belt_hex="#FF8C00", source="VJF leerlijn 2015, oranje",
            duration_seconds=2.6)

GRIP_DISTANCE = 0.62  # between the two roots while gripping


def stance(j, knee=12):
    """Natural stance (shizentai): feet a little apart, knees slightly bent."""
    tt.rot(j, "LeftUpLeg", (knee, 0, -4))
    tt.rot(j, "RightUpLeg", (knee, 0, 4))
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


def on_toes(j, heel=25):
    """Legs straight, heels raised: balance broken forward."""
    tt.rot(j, "LeftUpLeg", (2, 0, -4))
    tt.rot(j, "RightUpLeg", (2, 0, 4))
    tt.rot(j, "LeftFoot", (-heel, 0, 0))
    tt.rot(j, "RightFoot", (-heel, 0, 0))


def crouch(j, depth=50):
    """Both knees deeply bent, hips low (Tori's entry under Uki's centre of gravity)."""
    tt.rot(j, "LeftUpLeg", (depth, 0, -8))
    tt.rot(j, "RightUpLeg", (depth, 0, 8))
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


def kumikata():
    tt.place("Tori", (0, 0, 0), (0, 0, 0))
    tt.place("Uki", (0, 0, GRIP_DISTANCE), (0, 180, 0))
    for j in ("Tori", "Uki"):
        stance(j)
        tt.rot(j, "Spine", (-6, 0, 0))
        arms_ready(j)
        tt.ground(j)
    grip()


def kuzushi():
    # Uki is pulled forward onto the toes.
    tt.place("Uki", (0, 0, 0.60), (0, 180, 0))
    on_toes("Uki")
    tt.rot("Uki", "Spine", (-14, 0, 0))
    tt.rot("Uki", "Chest", (-6, 0, 0))
    arms_ready("Uki")
    tt.ground("Uki")
    # Tori steps in with the right foot and starts turning to the left.
    tt.place("Tori", (0.02, 0, 0.06), (0, 35, 0))
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
    grip()


def tsukuri():
    # Uki is drawn over Tori's back, still on the toes.
    tt.place("Uki", (0, 0, 0.46), (0, 180, 0))
    on_toes("Uki", 30)
    tt.rot("Uki", "Spine", (-30, 0, 0))
    tt.rot("Uki", "Chest", (-15, 0, 0))
    tt.rot("Uki", "Neck", (10, 0, 0))
    tt.ground("Uki")
    # Tori has turned his back in, hips below Uki's belt.
    tt.place("Tori", (0, 0, 0.16), (0, 180, 0))
    crouch("Tori", 45)
    tt.rot("Tori", "Spine", (-12, 0, 0))
    tt.ground("Tori")
    # Tori's right arm hooks up under Uki's right armpit.
    hook_right_arm()
    # Uki's right arm goes over Tori's right shoulder, left hand on Tori's back.
    tt.aim("Uki", "RightArm", (0.05, -0.35, -1))
    tt.aim("Uki", "RightForearm", (0, -0.5, -1))
    tt.aim("Uki", "LeftArm", (-0.3, -0.6, -0.8))
    tt.aim("Uki", "LeftForearm", (0.2, -0.5, -0.9))
    # Tori's left hand keeps pulling Uki's right sleeve.
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def hook_right_arm():
    """Tori's right arm clamps Uki's right upper arm in the elbow (ippon seoi grip)."""
    tt.aim("Tori", "RightArm", (0.25, 0.75, 0.6))
    tt.aim("Tori", "RightForearm", (-0.4, 0.2, -0.9))


def uki_over(pitch, chest_offset, spine=-10, legs=10):
    """Uki pitched forward by `pitch` degrees, his chest pinned relative to Tori's right shoulder
    (offset in Blender world space)."""
    tt.place("Uki", (0, 0, 0), (-pitch, 180, 0))
    tt.rot("Uki", "Spine", (spine, 0, 0))
    tt.rot("Uki", "LeftUpLeg", (legs, 0, -6))
    tt.rot("Uki", "RightUpLeg", (legs, 0, 6))
    tt.rot("Uki", "LeftLeg", (-legs, 0, 0))
    tt.rot("Uki", "RightLeg", (-legs, 0, 0))
    tt.aim("Uki", "LeftArm", (-0.6, -0.2, -0.8))
    tt.aim("Uki", "LeftForearm", (-0.2, -0.3, -0.9))
    tt.pin("Uki", "Chest", tt.bone_pos("Tori", "RightShoulder") + chest_offset)


def kake():
    # Tori straightens his legs and bows forward, turning further to the left.
    tt.place("Tori", (0, 0, 0.14), (0, 195, 0))
    crouch("Tori", 18)
    tt.rot("Tori", "Spine", (-30, 0, 0))
    tt.rot("Tori", "Chest", (-20, 0, 0))
    tt.rot("Tori", "Neck", (-10, 0, 0))
    tt.ground("Tori")
    hook_right_arm()
    # Uki is lifted onto Tori's back.
    uki_over(70, Vector((0, -0.10, 0.16)))
    tt.aim("Uki", "RightArm", (0.1, 0.1, -1))
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def nage():
    # Tori bows deeply and pulls Uki's sleeve down towards his left hip.
    tt.place("Tori", (0, 0, 0.14), (0, 215, 0))
    crouch("Tori", 15)
    tt.rot("Tori", "Spine", (-38, 0, 0))
    tt.rot("Tori", "Chest", (-22, 0, 0))
    tt.rot("Tori", "Neck", (-10, 0, 0))
    tt.ground("Tori")
    hook_right_arm()
    # Uki rolls head first over Tori's right shoulder.
    uki_over(165, Vector((0, 0.18, -0.10)), spine=-15, legs=25)
    tt.aim("Uki", "RightArm", (0.1, -0.3, -1))
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def fall():
    # Tori follows through, pulling the sleeve towards his left hip.
    tt.place("Tori", (0, 0, 0.12), (0, 210, 0))
    crouch("Tori", 15)
    tt.rot("Tori", "Spine", (-32, 0, 0))
    tt.rot("Tori", "Chest", (-10, 0, 0))
    tt.aim("Tori", "RightArm", (0.4, -0.8, -0.4))
    tt.ground("Tori")
    # Uki falls back-first towards the mat in front of Tori, left arm swinging out for the slap.
    tt.place("Uki", (0, 0, 0), (-235, 180, 0))
    tt.rot("Uki", "LeftUpLeg", (25, 0, -6))
    tt.rot("Uki", "RightUpLeg", (25, 0, 6))
    tt.rot("Uki", "LeftLeg", (-30, 0, 0))
    tt.rot("Uki", "RightLeg", (-30, 0, 0))
    tt.rot("Uki", "Neck", (-25, 0, 0))
    tt.rot("Uki", "LeftArm", (0, 0, -20))
    tt.aim("Uki", "RightArm", (0.3, 0.3, -0.9))
    tori = tt.bone_pos("Tori", "Hips")
    tt.pin("Uki", "Spine", Vector((tori.x + 0.08, tori.y + 0.65, 0.5)))
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def ukemi():
    # Tori stands, still holding Uki's right sleeve.
    tt.place("Tori", (0, 0, 0.10), (0, 205, 0))
    crouch("Tori", 15)
    tt.rot("Tori", "Spine", (-25, 0, 0))
    tt.aim("Tori", "RightArm", (0.35, -1, 0))
    tt.aim("Tori", "RightForearm", (0.15, -1, -0.3))
    tt.ground("Tori")
    # Uki lands on his back, head towards Tori, slapping the mat with the left arm.
    tt.place("Uki", (0, 0, 0), (-270, 180, 0))
    tt.rot("Uki", "LeftUpLeg", (40, 0, -8))
    tt.rot("Uki", "RightUpLeg", (40, 0, 8))
    tt.rot("Uki", "LeftLeg", (-45, 0, 0))
    tt.rot("Uki", "RightLeg", (-45, 0, 0))
    tt.rot("Uki", "Neck", (-25, 0, 0))  # chin tucked
    tt.rot("Uki", "LeftArm", (0, 0, 40))
    tt.aim("Uki", "RightArm", (0.3, 0.3, -0.9))
    tori = tt.bone_pos("Tori", "Hips")
    tt.pin("Uki", "Spine", Vector((tori.x + 0.12, tori.y + 0.85, 0.13)))
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


KEYFRAMES = [
    dict(time=0.0, phase="Kumikata (Grip)",
         description="Tori en Uki pakken elkaar vast: rechterhand aan de revers, linkerhand aan de mouw.",
         pose=kumikata),
    dict(time=0.6, phase="Kuzushi (Balansverstoring)",
         description="Tori stapt in met rechts en trekt Uki naar voren op de tenen.",
         pose=kuzushi),
    dict(time=1.2, phase="Tsukuri (Instap & Draai)",
         description="Tori draait in, zakt door de knieën en haakt zijn rechterarm onder Uki's oksel.",
         pose=tsukuri),
    dict(time=1.7, phase="Kake (Worp)",
         description="Tori strekt de benen en buigt voorover: Uki komt over zijn rug.",
         pose=kake),
    dict(time=2.1, phase="Nage (Rotatie)",
         description="Uki rolt met het hoofd voorop over Tori's rechterschouder.",
         pose=nage),
    dict(time=2.35, phase="Nage (Val)",
         description="Uki valt met de rug naar de mat; de linkerarm zwaait uit om af te slaan.",
         pose=fall),
    dict(time=2.6, phase="Ukemi (Valbreking)",
         description="Uki landt op de rug en slaat af met de linkerarm; Tori houdt de mouw vast.",
         pose=ukemi),
]


def main(upto=None):
    scene = bpy.context.scene
    scene.render.fps = tt.FPS
    for j in ("Tori", "Uki"):
        arm = bpy.data.objects[j]
        if arm.animation_data:
            arm.animation_data_clear()
    for kf in KEYFRAMES[:upto]:
        frame = round(kf["time"] * tt.FPS)
        scene.frame_set(frame)
        for j in ("Tori", "Uki"):
            tt.reset(j)
        kf["pose"]()
        for j in ("Tori", "Uki"):
            tt.key(j, frame)
    scene.frame_start, scene.frame_end = 0, round(META["duration_seconds"] * tt.FPS)
    if upto is None:
        return tt.export_yaml(OUT, META, [{k: v for k, v in kf.items() if k != "pose"} for kf in KEYFRAMES])


if __name__ == "__main__":
    main()

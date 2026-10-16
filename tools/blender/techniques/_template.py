"""<Technique name> (right-handed Tori) - authored in Blender, exported to data/techniques/.

Template: copy to <technique>.py (snake_case, = the YAML file name) and fill in the TODOs.
Run headless (see tools/blender/README.md):
    blender -b art_source/blender/judoka.blend --python tools/blender/run_technique.py -- <technique> --draft
"""
import importlib
import os
import sys

import bpy
from mathutils import Vector  # noqa: F401

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..") if "__file__" in globals() \
    else r"C:\proj\judo\tools\blender"
sys.path.insert(0, os.path.normpath(TOOLS))
import technique_tools as tt  # noqa: E402
import contact  # noqa: E402
import motion  # noqa: E402
import poses  # noqa: E402
for _m in (tt, contact, motion, poses):
    importlib.reload(_m)
from poses import frame, grip, stance, GRIP_DISTANCE  # noqa: E402,F401

NAME = "TODO_technique"  # snake_case
OUT = os.path.normpath(os.path.join(TOOLS, "..", "..", "data", "techniques", f"{NAME}.yaml"))

# Copy the metadata from the existing catalogue entry data/techniques/<technique>.yaml.
META = dict(technique_name="TODO", dutch_name="TODO", waza_group="nage_waza", category="TODO",
            code="TODO", difficulty="TODO", kyu_grade=5, belt_name="Gele band", belt_hex="#FFD700",
            source="VJF leerlijn 2015, geel", duration_seconds=2.6)

ALLOW = [
    contact.Allow("Tori:RightHand", "Uki:Chest", 0.07, end=0.8),  # TODO: grips and intended contacts
    contact.Allow("*Foot", contact.MAT, 0.03),
]


def kumikata():
    tt.place("Tori", (0, 0, 0), (0, 0, 0))
    tt.place("Uki", (0, 0, GRIP_DISTANCE), (0, 180, 0))
    for j in ("Tori", "Uki"):
        stance(j)
        tt.rot(j, "Spine", (-6, 0, 0))
        tt.ground(j)
    grip()


KEYFRAMES = [
    dict(time=0.0, phase="Kumikata (Grip)", description="TODO", pose=kumikata),
    # TODO: Kuzushi, Tsukuri, Kake, ... (root rotation change < ~120 degrees between keyframes)
]


def shape():
    """ease -> pivot -> plant/step -> shift_weight -> carry -> contact.resolve -> fall -> hold -> avoid."""
    motion.ease(frame(0.0), "EASE_IN")
    for side in ("Left", "Right"):
        motion.plant("Tori", side, frame(0.0), frame(META["duration_seconds"]))


def check():
    contact.print_report(contact.check_contacts(ALLOW))
    motion.print_sliding(motion.foot_sliding("Tori"), "Foot sliding Tori")
    motion.print_balance("Tori", motion.balance("Tori"))


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

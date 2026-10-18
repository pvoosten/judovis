"""Kami-shiho-gatame - authored in Blender, exported to data/techniques/.

Run headless (see tools/blender/README.md):
    blender -b art_source/blender/judoka.blend --python tools/blender/run_technique.py -- kami_shiho_gatame --draft

Uki lies on his back, head towards Godot +Z. Tori kneels behind Uki's head facing his feet, lowers his
chest onto Uki's chest, slides both arms under Uki's armpits and takes the belt on both sides; his legs
spread wide behind Uki's head. Uki tries to bridge out; Tori widens his base and keeps the hold.
"""
import importlib
import math
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
import edits  # noqa: E402
for _m in (tt, contact, motion, edits):
    importlib.reload(_m)

NAME = "kami_shiho_gatame"
OUT = os.path.normpath(os.path.join(TOOLS, "..", "..", "data", "techniques", f"{NAME}.yaml"))

META = dict(technique_name="Kami-shiho-gatame", dutch_name="Vierpuntshoudgreep vanaf het hoofd", waza_group="osaekomi_waza",
            category="Osaekomi-waza (Houdgreep)", code="O5-2", difficulty="Easy", kyu_grade=5,
            belt_name="Gele band", belt_hex="#FFD700", source="VJF leerlijn 2015, geel", duration_seconds=4.8)


def frame(t):
    return round(t * tt.FPS)


def G(x, y, z):
    """A Godot-space point (x, y up, z) as a Blender world point."""
    return Vector((x, -z, y))


def _pairs(a_bones, b_bones, tolerance, start=float("-inf"), end=float("inf")):
    return [contact.Allow(a, b, tolerance, start, end) for a in a_bones for b in b_bones]

HOLD = 1.8  # from here on Tori is in the hold
_TORI_ARMS = ["Tori:LeftArm", "Tori:LeftForearm", "Tori:LeftHand", "Tori:RightArm", "Tori:RightForearm", "Tori:RightHand"]
_UKI_TORSO = ["Uki:Chest", "Uki:Spine", "Uki:Hips", "Uki:LeftArm", "Uki:RightArm", "Uki:LeftForearm", "Uki:RightForearm",
              "Uki:LeftShoulder", "Uki:RightShoulder", "Uki:LeftHand", "Uki:RightHand"]
ALLOW = (
    [contact.Allow("*", contact.MAT, 0.03)]
    # Tori's arms go under Uki's armpits; Uki's arms lie over them.
    + _pairs(_TORI_ARMS, _UKI_TORSO, 0.05, 0.5)
    # Tori's hands hold the belt beside Uki's hips.
    + _pairs(["Tori:LeftHand", "Tori:RightHand"], ["Uki:Hips", "Uki:LeftUpLeg", "Uki:RightUpLeg", "Uki:Spine"], 0.07, 0.5)
    # Tori's chest and belly press on Uki's head, shoulders and chest.
    + _pairs(["Tori:Chest", "Tori:Spine", "Tori:Neck", "Tori:Head", "Tori:LeftShoulder", "Tori:RightShoulder"],
             ["Uki:Head", "Uki:Neck", "Uki:Chest", "Uki:LeftShoulder", "Uki:RightShoulder", "Uki:Spine"], 0.06, 0.5)
    # Tori's legs and hips next to Uki's head and arms.
    + _pairs(["Tori:Hips", "Tori:LeftUpLeg", "Tori:RightUpLeg"], ["Uki:Head", "Uki:Neck", "Uki:LeftArm", "Uki:RightArm"], 0.04, 0.5)
)


# --- poses ---------------------------------------------------------------------------------------
# Limbs are aimed at Godot-space points (G). Uki's hips are at the origin, his head towards +Z.

LOWER_BODY = ("Hips", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg", "LeftFoot", "RightFoot")


def sit(j, clearance=0.015):
    """Hips and legs rest on the mat (the arms are posed later)."""
    arm = bpy.data.objects[j]
    caps = contact.world_capsules(arm)
    lowest = min(min(caps[b][0].z, caps[b][1].z) - caps[b][2] for b in LOWER_BODY)
    arm.location.z += clearance - lowest
    tt._update()


def limb(j, upper, lower, joint, end):
    """Aim a two-bone limb: the upper bone at `joint`, the lower bone at `end` (Godot points)."""
    tt.aim_at(j, upper, G(*joint))
    tt.aim_at(j, lower, G(*end))


def uki_on_back(bridge=0.0, raised=True):
    """Uki on his back, knees up and feet flat, arms resting out to the sides. `bridge` (0..1) lifts
    the hips off the mat; the feet stay where they are (motion.plant in shape())."""
    tt.place("Uki", (0, 0, 0), (90, 180, 0))
    tt.rot("Uki", "Neck", (-15, 0, 0))
    tt.pin("Uki", "Hips", G(0, 0.2, 0))
    motion.settle("Uki")
    for side, x in (("Left", -1), ("Right", 1)):
        limb("Uki", f"{side}UpLeg", f"{side}Leg", (0.14 * x, 0.38, -0.40), (0.17 * x, 0.10, -0.75))
        tt.aim_at("Uki", f"{side}Foot", G(0.18 * x, 0.03, -0.92))
        limb("Uki", f"{side}Arm", f"{side}Forearm", (0.45 * x, 0.08, 0.35), (0.65 * x, 0.09, 0.15))
        if raised:
            limb("Uki", f"{side}Arm", f"{side}Forearm", (0.66 * x, 0.10, 0.26), (0.88 * x, 0.10, 0.08))
    tt.pin("Uki", "Hips", G(0, 0.2, 0))
    motion.settle("Uki")
    if bridge:
        bpy.data.objects["Uki"].location.z += 0.08 * bridge
        tt._update()


def tori_kneeling(heading=180):
    """Tori high on both knees, shins on the mat, facing `heading` (Godot Y rotation)."""
    tt.place("Tori", (0, 0, 0), (0, heading, 0))
    for side, out in (("Left", -6), ("Right", 6)):
        tt.rot("Tori", f"{side}UpLeg", (10, 0, out))
        tt.rot("Tori", f"{side}Leg", (-95, 0, 0))
        tt.rot("Tori", f"{side}Foot", (-45, 0, 0))
    tt.rot("Tori", "Spine", (-15, 0, 0))


def start():
    uki_on_back()
    tori_kneeling(heading=180)
    tt.pin("Tori", "Hips", G(0, 0.6, 1.25))
    motion.settle("Tori")
    tt.aim("Tori", "LeftArm", (0.2, -0.9, -0.4))
    tt.aim("Tori", "RightArm", (-0.2, -0.9, -0.4))
    tt.aim("Tori", "LeftForearm", (0.1, -0.5, -0.85))
    tt.aim("Tori", "RightForearm", (-0.1, -0.5, -0.85))


HIPS, SPINE, CHEST, NECK = (0, 0.36, 0.84), (0, 0.44, 0.66), (0, 0.40, 0.46), (0, 0.38, 0.36)
PITCH = -35
ELBOW, HAND = (0.28, 0.13, 0.33), (0.24, 0.11, 0.08)


def kami(d=1.0, base=0.0, lift=0.0, shift=0.0, back=0.0):
    """Tori behind Uki's head facing his feet. `d` (0..1): how far he has lowered his chest onto Uki;
    `base` (0..1) spreads the legs wider; `lift` (m): Uki's bridge lifts Tori; `shift` (m) sideways."""
    def L(a, b):
        return tuple(a[i] + (b[i] - a[i]) * d for i in range(3))

    hips = L((0, 0.50, 1.25), HIPS)
    hips = (hips[0], hips[1], hips[2] + back)
    tt.place("Tori", (0, 0, 0), (PITCH * d, 180, 0))
    tt.pin("Tori", "Hips", G(hips[0] + shift, hips[1] + lift, hips[2]))
    for side, x in (("Left", -1), ("Right", 1)):  # Tori faces -Z: his left is world -X
        spread = 0.30 + 0.12 * base
        limb("Tori", f"{side}UpLeg", f"{side}Leg", (x * spread, 0.11, hips[2] + 0.20),
             (x * (spread + 0.20), 0.05, hips[2] + 0.50))
        tt.aim_at("Tori", f"{side}Foot", tt.bone_pos("Tori", f"{side}Foot") + G(x * 0.1, -0.05, 0.25))
    s, c, n = L((0, 0.78, 1.15), SPINE), L((0, 0.95, 1.05), CHEST), L((0, 1.05, 0.98), NECK)
    for bone, p in (("Spine", s), ("Chest", c), ("Neck", n)):
        tt.aim_at("Tori", bone, G(p[0] + shift, p[1] + lift, p[2] + back))
    sit("Tori")
    # Both arms under Uki's armpits, hands on the belt.
    for side, x in (("Left", -1), ("Right", 1)):
        limb("Tori", f"{side}Arm", f"{side}Forearm", (x * ELBOW[0], ELBOW[1], ELBOW[2]), (x * HAND[0], HAND[1], HAND[2]))
        if d > 0.4:  # the hand on Uki's belt, beside his hip
            belt = tt.bone_pos("Uki", "Hips") + G(x * 0.17, 0.06, 0.07)
            tt.ik_point("Tori", f"{side}Hand", belt)


def entry():
    uki_on_back()
    kami(0.5)


def hold():
    uki_on_back(raised=True)
    kami(1.0)


def escape():
    uki_on_back(bridge=1.0, raised=True)
    kami(1.0, base=1.0, lift=0.03, back=0.04)


KEYFRAMES = [
    dict(time=0.0, phase="Uitgangspositie",
         description="Uki ligt op zijn rug. Tori zit op zijn knieën bij Uki's hoofd en kijkt naar zijn voeten.", pose=start),
    dict(time=0.9, phase="Instap",
         description="Tori buigt voorover en schuift zijn beide armen onder Uki's oksels door.", pose=entry),
    dict(time=1.8, phase="Osaekomi (Houdgreep)",
         description="Tori pakt Uki's gordel links en rechts vast. Zijn borst ligt op Uki's borst, zijn benen staan wijd uit elkaar.",
         pose=hold),
    dict(time=3.0, phase="Ontsnappingspoging",
         description="Uki duwt zijn heupen omhoog om weg te komen. Tori zet zijn benen nog wijder en blijft zwaar op Uki liggen.",
         pose=escape),
    dict(time=3.9, phase="Osaekomi (Houdgreep)",
         description="Uki ligt weer plat. Tori houdt de gordel vast en blijft met zijn borst op Uki's borst.", pose=hold),
    dict(time=4.8, phase="Ippon",
         description="Tori heeft de houdgreep lang genoeg vastgehouden: ippon.", pose=hold),
]


def on_mat(j, f0, f1, depth=0.015):
    """Move the root on every frame so the lowest capsule sinks exactly `depth` into the mat; keyed."""
    arm = bpy.data.objects[j]
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        deepest = max(contact.mat_penetration(c) for c in contact.world_capsules(arm).values())
        if abs(deepest - depth) > 0.002:
            arm.location.z += deepest - depth
            tt._update()
            tt.key(j, f, bones=[])


def shape():
    for kf in KEYFRAMES[:-1]:
        motion.ease(frame(kf["time"]))
    end = frame(META["duration_seconds"])
    for side in ("Left", "Right"):
        motion.plant("Uki", side, 0, end)
    on_mat("Tori", 0, frame(1.8))
    for side in ("Right", "Left"):
        motion.avoid("Tori", [f"{side}UpLeg", f"{side}Leg"], "Uki", frame(0.9), frame(1.8), ALLOW, max_rate=6)
    on_mat("Tori", 0, frame(1.8))
    for side in ("Right", "Left"):
        motion.plant("Tori", side, frame(1.8), end)
    for _ in range(3):
        motion.avoid("Tori", ["RightArm", "RightForearm", "LeftArm", "LeftForearm"], "Uki", frame(0.4), end, ALLOW, max_rate=10)
        motion.avoid("Uki", ["LeftArm", "LeftForearm", "RightArm", "RightForearm"], "Tori", frame(0.4), end, ALLOW, max_rate=6)
    for j in ("Tori", "Uki"):
        motion.hinge_elbows(j, 0, end)


def check():
    contact.check_all(ALLOW)
    motion.print_sliding(motion.foot_sliding("Uki"), "Foot sliding Uki")
    motion.print_sliding(motion.foot_sliding("Tori", frame(1.8)), "Foot sliding Tori (in the hold)")
    motion.print_limits(motion.limit_violations("Tori"), "Joint limits Tori")
    motion.print_limits(motion.limit_violations("Uki"), "Joint limits Uki")


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
        edits.apply(NAME)  # pose edits from the app (F3) win over the script
        check()
        if export:
            return tt.export_yaml(OUT, META, [{k: v for k, v in kf.items() if k != "pose"} for kf in KEYFRAMES])


if __name__ == "__main__":
    main()

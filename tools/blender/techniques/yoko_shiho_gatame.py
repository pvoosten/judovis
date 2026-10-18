"""Yoko-shiho-gatame (right side) - authored in Blender, exported to data/techniques/.

Run headless (see tools/blender/README.md):
    blender -b art_source/blender/judoka.blend --python tools/blender/run_technique.py -- yoko_shiho_gatame --draft

Uki lies on his back, head towards Godot +Z, his right side towards +X. Tori kneels at Uki's right
side, slides his left arm under Uki's neck and lowers his chest across Uki's chest, at right angles to
him: legs spread wide on the toes, right hand on Uki's belt, left hand on Uki's far collar. Uki tries
to bridge out; Tori widens his base and keeps the hold.
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

NAME = "yoko_shiho_gatame"
OUT = os.path.normpath(os.path.join(TOOLS, "..", "..", "data", "techniques", f"{NAME}.yaml"))

META = dict(technique_name="Yoko-shiho-gatame", dutch_name="Zijwaartse vierpuntshoudgreep", waza_group="osaekomi_waza",
            category="Osaekomi-waza (Houdgreep)", code="O5-3", difficulty="Easy", kyu_grade=5,
            belt_name="Gele band", belt_hex="#FFD700", source="VJF leerlijn 2015, geel", duration_seconds=5.0)


def frame(t):
    return round(t * tt.FPS)


def G(x, y, z):
    """A Godot-space point (x, y up, z) as a Blender world point."""
    return Vector((x, -z, y))


def _pairs(a_bones, b_bones, tolerance, start=float("-inf"), end=float("inf")):
    return [contact.Allow(a, b, tolerance, start, end) for a in a_bones for b in b_bones]


HOLD = 1.6  # from here on Tori is in the hold
ALLOW = (
    # Lying, kneeling and sitting on the mat: the capsules settle onto it.
    [contact.Allow("*", contact.MAT, 0.03)]
    # Tori's chest, belly and hips press on Uki's chest and ribs; his head lies against Uki's far shoulder.
    + _pairs(["Tori:Chest", "Tori:Spine", "Tori:LeftShoulder", "Tori:RightShoulder", "Tori:Hips"],
             ["Uki:Chest", "Uki:Spine", "Uki:RightShoulder", "Uki:RightArm", "Uki:LeftShoulder"], 0.06, HOLD)
    + _pairs(["Tori:Head", "Tori:Neck"], ["Uki:Chest", "Uki:LeftShoulder", "Uki:Neck", "Uki:Head", "Uki:LeftArm"], 0.08, HOLD)
    # Tori's left arm goes under Uki's neck (a hollow the capsules do not model) to his far collar; Uki's
    # head rests on it.
    + _pairs(["Tori:LeftArm", "Tori:LeftForearm", "Tori:LeftHand"],
             ["Uki:Neck", "Uki:Head", "Uki:Chest", "Uki:LeftShoulder", "Uki:RightShoulder"], 0.16, 0.5)
    # Tori's right arm lies across Uki's belly to the belt.
    + _pairs(["Tori:RightArm", "Tori:RightForearm", "Tori:RightHand"],
             ["Uki:Hips", "Uki:Spine", "Uki:Chest", "Uki:LeftUpLeg", "Uki:RightUpLeg"], 0.08, 0.6)
    # Tori's knees and shins brush Uki's arm and thigh while he spreads his legs.
    + _pairs(["Tori:RightUpLeg", "Tori:LeftUpLeg", "Tori:Hips"], ["Uki:RightArm", "Uki:RightForearm", "Uki:RightHand",
             "Uki:RightUpLeg"], 0.04, 0.4)
    # Uki pushes against Tori's body with his hands.
    + _pairs(["Uki:RightHand", "Uki:LeftHand", "Uki:RightForearm", "Uki:LeftForearm"],
             ["Tori:Spine", "Tori:Chest", "Tori:Hips", "Tori:Head", "Tori:Neck"], 0.05, 0.4)
)


# --- poses ---------------------------------------------------------------------------------------
# Limbs are aimed at Godot-space points (G): on the ground, world targets are easier to reason about
# than joint angles. Uki's hips are at the origin, his head towards +Z, his right side towards +X.

LOWER_BODY = ("Hips", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg", "LeftFoot", "RightFoot")


def sit(j, clearance=0.015):
    """Like motion.settle, but only the hips and legs rest on the mat."""
    arm = bpy.data.objects[j]
    caps = contact.world_capsules(arm)
    lowest = min(min(caps[b][0].z, caps[b][1].z) - caps[b][2] for b in LOWER_BODY)
    arm.location.z += clearance - lowest
    tt._update()


def limb(j, upper, lower, joint, end):
    """Aim a two-bone limb: the upper bone at `joint`, the lower bone at `end` (Godot points)."""
    tt.aim_at(j, upper, G(*joint))
    tt.aim_at(j, lower, G(*end))


def overlap():
    """Summed overlap beyond the allowed contacts at the current frame (m)."""
    t = bpy.context.scene.frame_current / tt.FPS
    return sum(d - tol for _, _, d, tol in contact.contacts_at(t, ALLOW))


def least_overlap(apply, candidates):
    """Pose with each candidate (`apply(c)`) and keep the one with the least overlap; returns it."""
    saved = {j: (bpy.data.objects[j].matrix_world.copy(),
                 {pb.name: pb.matrix_basis.copy() for pb in bpy.data.objects[j].pose.bones}) for j in ("Tori", "Uki")}

    def restore():
        for j, (world, bones) in saved.items():
            arm = bpy.data.objects[j]
            arm.matrix_world = world
            for name, m in bones.items():
                arm.pose.bones[name].matrix_basis = m
        tt._update()

    def score(c):
        restore()
        apply(c)
        return overlap()

    best = min(candidates, key=score)
    restore()
    apply(best)
    return best


POLES = [None] + [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if x or y or z]


def uki_on_back(bridge=0.0, arm_up=True):
    """Uki on his back, knees up and feet flat on the mat. `bridge` (0..1) lifts the hips off the mat
    (the feet stay where they are: motion.plant in shape()). His right arm lies above his head,
    out of the way of Tori's chest."""
    tt.place("Uki", (0, 0, 0), (90, 180, 0))
    tt.pin("Uki", "Hips", G(0, 0.2, 0))  # first: the limb targets below are absolute points
    tt.rot("Uki", "Neck", (-15, 0, 0))
    for side, x in (("Left", -1), ("Right", 1)):
        limb("Uki", f"{side}UpLeg", f"{side}Leg", (0.14 * x, 0.38, -0.40), (0.17 * x, 0.10, -0.75))
        tt.aim_at("Uki", f"{side}Foot", G(0.18 * x, 0.03, -0.92))
    limb("Uki", "LeftArm", "LeftForearm", (-0.45, 0.08, 0.35), (-0.65, 0.09, 0.15))
    if arm_up:
        limb("Uki", "RightArm", "RightForearm", (0.55, 0.08, 0.80), (0.55, 0.09, 1.05))
    else:
        limb("Uki", "RightArm", "RightForearm", (0.45, 0.08, 0.35), (0.65, 0.09, 0.15))
    motion.settle("Uki")
    if bridge:
        bpy.data.objects["Uki"].location.z += 0.08 * bridge
        tt._update()


def tori_kneeling(heading=-90):
    """Tori high on both knees, shins on the mat, facing `heading` (Godot Y rotation)."""
    tt.place("Tori", (0, 0, 0), (0, heading, 0))
    for side, out in (("Left", -6), ("Right", 6)):
        tt.rot("Tori", f"{side}UpLeg", (10, 0, out))
        tt.rot("Tori", f"{side}Leg", (-95, 0, 0))
        tt.rot("Tori", f"{side}Foot", (-45, 0, 0))
    tt.rot("Tori", "Spine", (-15, 0, 0))


def start():
    uki_on_back()
    tori_kneeling()
    tt.pin("Tori", "Hips", G(0.75, 0.6, 0.35))
    motion.settle("Tori")
    tt.aim("Tori", "LeftArm", (0.2, -0.9, -0.4))
    tt.aim("Tori", "RightArm", (-0.2, -0.9, -0.4))
    tt.aim("Tori", "LeftForearm", (0.1, -0.5, -0.85))
    tt.aim("Tori", "RightForearm", (-0.1, -0.5, -0.85))


def grips():
    """Left hand on Uki's far collar (arm under his neck), right hand on his belt."""
    least_overlap(lambda pole: tt.ik("Tori", "LeftHand", "Uki", "BackCollarGrip", pole=pole), POLES)
    least_overlap(lambda pole: tt.ik("Tori", "RightHand", "Uki", "BeltGrip", pole=pole), POLES)


def control():
    """Tori leans over Uki on his knees, close to his right side."""
    uki_on_back()
    tori_kneeling()
    tt.rot("Tori", "Spine", (-50, 0, 0))
    tt.rot("Tori", "Chest", (-15, 0, 0))
    tt.pin("Tori", "Hips", G(0.62, 0.45, 0.33))
    motion.settle("Tori")
    grips()


HIPS, SPINE, CHEST, NECK = (0.56, 0.19, 0.24), (0.34, 0.30, 0.30), (0.12, 0.38, 0.36), (-0.10, 0.36, 0.42)


def yoko(base=0.0, lift=0.0):
    """Yoko-shiho-gatame: Tori lies across Uki's chest at right angles, belly down, head beyond Uki's
    far shoulder, legs spread wide on the toes (right leg towards Uki's feet, left leg towards his head)
    for a stable base. `base` (0..1) spreads the legs wider; `lift` (m): Uki's bridge lifts Tori."""

    def up(p):
        return (p[0], p[1] + lift, p[2])

    tt.place("Tori", (0, 0, 0), (90, 0, 90))
    tt.pin("Tori", "Hips", G(*up(HIPS)))
    s = 0.12 * base
    limb("Tori", "RightUpLeg", "RightLeg", (0.88, 0.12, -0.01 - s), (1.22, 0.07, -0.28 - s))
    limb("Tori", "LeftUpLeg", "LeftLeg", (0.88, 0.12, 0.49 + s), (1.22, 0.07, 0.79 + s))
    for side in ("Left", "Right"):
        tt.aim_at("Tori", f"{side}Foot", tt.bone_pos("Tori", f"{side}Foot") + G(0.05, -0.3, 0))
    tt.aim_at("Tori", "Spine", G(*up(SPINE)))
    tt.aim_at("Tori", "Chest", G(*up(CHEST)))
    tt.aim_at("Tori", "Neck", G(*up(NECK)))
    sit("Tori")
    grips()


def hold():
    uki_on_back()
    yoko()


def escape():
    uki_on_back(bridge=1.0)
    yoko(base=1.0, lift=0.07)


KEYFRAMES = [
    dict(time=0.0, phase="Uitgangspositie",
         description="Uki ligt op zijn rug. Tori zit op zijn knieën naast Uki's rechterkant.", pose=start),
    dict(time=0.8, phase="Controle (Nek en riem)",
         description="Tori buigt zich over Uki heen. Zijn linkerarm gaat onder Uki's nek door: zijn linkerhand "
                     "reikt naar de kraag aan de andere kant. Zijn rechterhand pakt Uki's riem.",
         pose=control),
    dict(time=1.6, phase="Osaekomi (Houdgreep)",
         description="Tori laat zijn borst op Uki's borst zakken, dwars op Uki. Zijn benen staan wijd uit elkaar op "
                     "zijn tenen: dat geeft een stevige basis. Zijn hoofd ligt naast Uki's schouder.", pose=hold),
    dict(time=2.8, phase="Ontsnappingspoging",
         description="Uki duwt zijn heupen omhoog om Tori eraf te krijgen. Tori zet zijn benen nog wijder en blijft "
                     "zwaar op Uki's borst liggen.",
         pose=escape),
    dict(time=3.6, phase="Osaekomi (Houdgreep)",
         description="Uki ligt weer plat. Tori houdt de kraag en de riem vast en blijft op Uki's borst liggen.",
         pose=hold),
    dict(time=5.0, phase="Ippon",
         description="Tori heeft de houdgreep lang genoeg vastgehouden: ippon.", pose=hold),
]


def on_mat(j, f0, f1, depth=0.015):
    """Move the root up or down on every frame so the lowest capsule sinks exactly `depth` into the
    mat (the gi): no sinking in, no floating; keyed."""
    arm = bpy.data.objects[j]
    for f in range(f0, f1 + 1):
        bpy.context.scene.frame_set(f)
        deepest = max(contact.mat_penetration(c) for c in contact.world_capsules(arm).values())
        if abs(deepest - depth) > 0.002:
            arm.location.z += deepest - depth
            tt._update()
            tt.key(j, f, bones=[])


def shape():
    """ease -> plant -> hold -> avoid (see tools/blender/README.md)."""
    for kf in KEYFRAMES[:-1]:
        motion.ease(frame(kf["time"]))
    end = frame(META["duration_seconds"])
    # Uki's feet stay flat on the mat; bridging only lifts his hips.
    for side in ("Left", "Right"):
        motion.plant("Uki", side, 0, end)
    # While he lies down across Uki, Tori's legs swing round: keep him on the mat.
    on_mat("Tori", frame(0.8), frame(1.6))
    for side in ("Right", "Left"):
        motion.avoid("Tori", [f"{side}UpLeg", f"{side}Leg"], "Uki", frame(0.8), frame(1.6), ALLOW, max_rate=6)
    on_mat("Tori", frame(0.8), frame(1.6))
    # In the hold Tori's toes stay put; against the bridge he steps his feet wider and back again.
    scene = bpy.context.scene
    wide = {s: [] for s in ("Left", "Right")}
    narrow = {s: [] for s in ("Left", "Right")}
    for t, out in ((2.8, wide), (3.6, narrow)):
        scene.frame_set(frame(t))
        for side in out:
            out[side].extend(motion.foot_matrix("Tori", side).translation)
    for side in ("Left", "Right"):
        motion.plant("Tori", side, frame(HOLD), frame(2.0), pivot="toe")
        motion.step("Tori", side, frame(2.0), frame(2.5), height=0.04, to=wide[side], lift=0.2)
        motion.plant("Tori", side, frame(2.5), frame(3.0), pivot="toe")
        motion.step("Tori", side, frame(3.0), frame(3.5), height=0.04, to=narrow[side], lift=0.2)
        motion.plant("Tori", side, frame(3.5), end, pivot="toe")
    # Tori keeps both grips on every frame once he has them.
    motion.hold("Tori", "LeftHand", "Uki", "BackCollarGrip", frame(0.95), end)
    motion.hold("Tori", "RightHand", "Uki", "BeltGrip", frame(0.8), end)
    for _ in range(2):
        motion.avoid("Tori", ["LeftArm", "LeftForearm", "RightArm", "RightForearm"], "Uki", frame(0.4), end, ALLOW, max_rate=6)
        motion.avoid("Uki", ["RightArm", "RightForearm", "LeftArm", "LeftForearm"], "Tori", frame(0.4), end, ALLOW, max_rate=6)
    for j in ("Tori", "Uki"):
        motion.hinge_elbows(j, 0, end)
    motion.hold("Tori", "LeftHand", "Uki", "BackCollarGrip", frame(0.95), end)
    motion.hold("Tori", "RightHand", "Uki", "BeltGrip", frame(0.8), end)


GRIPS = (("Tori:LeftHand", "BackCollarGrip", 1.0), ("Tori:RightHand", "BeltGrip", 0.8))


def print_grip_gaps():
    """Largest distance (m) between each hand and its grip bone from the moment it should hold."""
    scene = bpy.context.scene
    print("Grip gaps (hand off its grip):")
    for hand, grip_bone, since in GRIPS:
        j, bone = hand.split(":")
        worst = (0.0, 0.0)
        for f in range(frame(since), frame(META["duration_seconds"]) + 1):
            scene.frame_set(f)
            worst = max(worst, ((tt.bone_pos(j, bone, tail=True) - tt.bone_pos("Uki", grip_bone)).length, f / tt.FPS))
        print(f"  {hand + ' -> Uki:' + grip_bone:40} {worst[0] * 100:5.1f} cm at {worst[1]:.2f}s")


def check():
    contact.check_all(ALLOW)
    print_grip_gaps()
    motion.print_sliding(motion.foot_sliding("Uki"), "Foot sliding Uki")
    motion.print_sliding(motion.foot_sliding("Tori", frame(HOLD)), "Foot sliding Tori (in the hold)")
    motion.print_limits(motion.limit_violations("Tori"), "Joint limits Tori")
    motion.print_limits(motion.limit_violations("Uki"), "Joint limits Uki")


def dump(t):
    def p(j, b, tail=False):
        v = tt.bone_pos(j, b, tail)
        return f"({v.x:.2f},{v.z:.2f},{-v.y:.2f})"  # Godot x, y, z
    print(f"--- {t}s")
    for j, bones in (("Tori", ["Hips", "Chest", "Head", "LeftHand", "RightHand", "LeftFoot", "RightFoot"]),
                     ("Uki", ["Hips", "Chest", "Head", "LeftHand", "RightHand"])):
        print(j, " ".join(f"{b}={p(j, b)}" for b in bones))
    for g in ("BackCollarGrip", "BeltGrip"):
        print(g, p("Uki", g))
    print("overlap", round(overlap(), 3))


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
        if os.environ.get("YOKO_DEBUG"):
            dump(kf["time"])
    scene.frame_start, scene.frame_end = 0, frame(META["duration_seconds"])
    if upto is None:
        shape()
        edits.apply(NAME)  # pose edits from the app (F3) win over the script
        check()
        if export:
            return tt.export_yaml(OUT, META, [{k: v for k, v in kf.items() if k != "pose"} for kf in KEYFRAMES])


if __name__ == "__main__":
    main()

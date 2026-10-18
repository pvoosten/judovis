"""Tate-shiho-gatame - authored in Blender, exported to data/techniques/.

Run headless (see tools/blender/README.md):
    blender -b art_source/blender/judoka.blend --python tools/blender/run_technique.py -- tate_shiho_gatame --draft

Uki lies on his back, head towards Godot +Z, his right side towards +X. Tori kneels at Uki's right
side, takes Uki's right arm and moves on top of him: chest on Uki's chest, legs spread wide on the
mat either side of Uki's body (four points of support), right arm round Uki's head, left hand
holding Uki's right sleeve. Uki tries to bridge out; Tori widens his base and keeps the hold.
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

NAME = "tate_shiho_gatame"
OUT = os.path.normpath(os.path.join(TOOLS, "..", "..", "data", "techniques", f"{NAME}.yaml"))

META = dict(technique_name="Tate-shiho-gatame", dutch_name="Lengte-vierpuntshoudgreep", waza_group="osaekomi_waza",
            category="Osaekomi-waza (Houdgreep)", code="O5-4", difficulty="Easy", kyu_grade=5,
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
    [contact.Allow("*", contact.MAT, 0.03)]
    # Tori's left hand grips Uki's right sleeve; Uki's right arm is clamped against Tori's chest.
    + _pairs(["Tori:LeftHand"], ["Uki:RightForearm", "Uki:RightArm", "Uki:RightHand"], 0.09)
    + _pairs(["Tori:LeftArm", "Tori:LeftForearm"], ["Uki:RightForearm", "Uki:RightArm", "Uki:RightHand"], 0.08, 0.4, 1.0)
    + _pairs(["Uki:RightArm", "Uki:RightForearm", "Uki:RightHand"],
             ["Tori:Chest", "Tori:Spine", "Tori:LeftShoulder", "Tori:LeftArm", "Tori:LeftForearm"], 0.06, 0.7)
    + _pairs(["Tori:LeftUpLeg", "Tori:RightUpLeg"], ["Uki:RightArm", "Uki:RightForearm", "Uki:RightHand"], 0.03, 0.5)
    # Tori lies on Uki: chest on chest, belly on belly, hips on hips (the gi and bodies give way).
    + _pairs(["Tori:Chest", "Tori:Spine", "Tori:Hips", "Tori:RightShoulder", "Tori:LeftShoulder"],
             ["Uki:Chest", "Uki:Spine", "Uki:Hips", "Uki:RightShoulder", "Uki:LeftShoulder"], 0.06, 0.7)
    + _pairs(["Tori:RightUpLeg", "Tori:LeftUpLeg"], ["Uki:Hips", "Uki:LeftUpLeg", "Uki:RightUpLeg"], 0.05, 0.7)
    # Tori's right arm round Uki's head, hand on Uki's collar; the heads touch.
    + _pairs(["Tori:RightArm", "Tori:RightForearm", "Tori:RightHand"],
             ["Uki:Head", "Uki:Neck", "Uki:Chest", "Uki:LeftShoulder", "Uki:LeftArm", "Uki:RightShoulder"], 0.10, 0.4)
    + _pairs(["Tori:Head", "Tori:Neck"], ["Uki:Head", "Uki:Neck", "Uki:RightShoulder", "Uki:LeftShoulder"], 0.06, HOLD)
    + _pairs(["Uki:RightHand"], ["Tori:Spine", "Tori:Chest", "Tori:Hips"], 0.04, 0.4)
    + _pairs(["Uki:LeftArm", "Uki:LeftForearm", "Uki:LeftHand"],
             ["Tori:Chest", "Tori:Spine", "Tori:Hips", "Tori:RightArm", "Tori:RightForearm", "Tori:RightUpLeg"], 0.05, 0.7)
)

LOWER_BODY = ("Hips", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg", "LeftFoot", "RightFoot")
POLES = [None] + [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if x or y or z]


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


def around(p, step=0.08, n=1):
    r = [i * step for i in range(-n, n + 1)]
    return [(p[0] + dx, p[1] + dy, p[2] + dz) for dx in r for dy in r for dz in r]


def uki_on_back(bridge=0.0):
    """Uki on his back, legs stretched and slightly apart, arms resting out to the sides. `bridge`
    (0..1) lifts the hips off the mat; the feet stay where they are (motion.plant in shape())."""
    tt.place("Uki", (0, 0, 0), (90, 180, 0))
    tt.rot("Uki", "Neck", (-15, 0, 0))
    for side, x in (("Left", -1), ("Right", 1)):
        limb("Uki", f"{side}UpLeg", f"{side}Leg", (0.13 * x, 0.12, -0.45), (0.17 * x, 0.10, -0.88))
        tt.aim_at("Uki", f"{side}Foot", G(0.2 * x, 0.12, -1.0))
        limb("Uki", f"{side}Arm", f"{side}Forearm", (0.55 * x, 0.08, 0.30), (0.85 * x, 0.09, 0.28))
    tt.pin("Uki", "Hips", G(0, 0.2, 0))
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
    tt.pin("Tori", "Hips", G(0.75, 0.6, 0.2))
    motion.settle("Tori")
    tt.aim("Tori", "LeftArm", (0.2, -0.9, -0.4))
    tt.aim("Tori", "RightArm", (-0.2, -0.9, -0.4))
    tt.aim("Tori", "LeftForearm", (0.1, -0.5, -0.85))
    tt.aim("Tori", "RightForearm", (-0.1, -0.5, -0.85))


def control():
    uki_on_back()
    tori_kneeling()
    tt.rot("Tori", "Spine", (-40, 0, 0))
    tt.pin("Tori", "Hips", G(0.62, 0.6, 0.25))
    motion.settle("Tori")
    limb("Uki", "RightArm", "RightForearm", UKI_ELBOW, UKI_HAND)

    def pulled(pole):
        tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip", pole=pole)

    least_overlap(pulled, POLES)
    tt.ik_point("Tori", "RightHand", G(-0.40, 0.06, 0.45))


HIPS, SPINE, CHEST, NECK, HEAD = (0.05, 0.43, -0.02), (0.10, 0.50, 0.22), (0.08, 0.54, 0.46), (0.06, 0.52, 0.68), (0.06, 0.40, 0.90)
ARM_ELBOW, ARM_HAND = (-0.12, 0.22, 0.80), (-0.30, 0.15, 0.62)
UKI_ELBOW, UKI_HAND = (0.38, 0.30, 0.62), (0.45, 0.45, 0.40)


def tate(base=0.0, lift=0.0):
    """Tate-shiho-gatame: Tori lies lengthways on Uki, chest on chest, legs wide behind on the mat
    either side of Uki; right arm round Uki's head, left hand on Uki's right sleeve. `base` (0..1)
    spreads the legs wider; `lift` (m): Uki's bridge lifts Tori."""

    def up(p):
        return (p[0], p[1] + lift, p[2])

    tt.place("Tori", (0, 0, 0), (60, 0, 0))
    tt.pin("Tori", "Hips", G(*up(HIPS)))
    w = 0.36 + 0.12 * base
    limb("Tori", "RightUpLeg", "RightLeg", (-w, 0.24, -0.26), (-w - 0.28, 0.08, -0.60))
    limb("Tori", "LeftUpLeg", "LeftLeg", (w + 0.06, 0.24, -0.26), (w + 0.34, 0.08, -0.60))
    for side in ("Right", "Left"):
        tt.aim_at("Tori", f"{side}Foot", tt.bone_pos("Tori", f"{side}Foot") + G(0.0, -0.06, -0.3))
    tt.aim_at("Tori", "Spine", G(*up(SPINE)))
    tt.aim_at("Tori", "Chest", G(*up(CHEST)))
    tt.aim_at("Tori", "Neck", G(*up(NECK)))
    tt.aim_at("Tori", "Head", G(*up(HEAD)))
    least_overlap(lambda eh: limb("Tori", "RightArm", "RightForearm", eh[0], eh[1]),
                  [(e, h) for e in around(up(ARM_ELBOW), 0.05) for h in around(up(ARM_HAND), 0.08)])
    limb("Uki", "RightArm", "RightForearm", up(UKI_ELBOW), up(UKI_HAND))
    least_overlap(lambda pole: tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip", pole=pole), POLES)


def hold():
    uki_on_back()
    tate()


def escape():
    uki_on_back(bridge=1.0)
    tate(base=1.0, lift=0.06)


KEYFRAMES = [
    dict(time=0.0, phase="Uitgangspositie",
         description="Uki ligt op zijn rug. Tori zit op zijn knieën naast Uki's rechterkant.", pose=start),
    dict(time=0.8, phase="Controle (Arm)",
         description="Tori pakt met zijn linkerhand Uki's rechtermouw bij de elleboog en trekt die arm tegen "
                     "zijn borst. Zijn rechterarm gaat over Uki's schouder naar Uki's hoofd.",
         pose=control),
    dict(time=1.6, phase="Osaekomi (Houdgreep)",
         description="Tori ligt in de lengte op Uki, zijn borst op Uki's borst, zijn hoofd naast Uki's hoofd. "
                     "Zijn benen staan wijd uit elkaar op de mat achter Uki's heupen. Zijn rechterarm ligt om "
                     "Uki's hoofd, zijn linkerhand houdt Uki's mouw vast.", pose=hold),
    dict(time=2.8, phase="Ontsnappingspoging",
         description="Uki duwt zijn heupen omhoog om Tori eraf te werpen. Tori zet zijn benen nog wijder en "
                     "blijft met zijn gewicht op Uki liggen.", pose=escape),
    dict(time=3.6, phase="Osaekomi (Houdgreep)",
         description="Uki ligt weer plat. Tori houdt Uki's hoofd en mouw vast, zijn borst zwaar op Uki's borst.",
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


HOLD_AT = 1.4


def freeze(j, bones, f0, f1):
    """Bones keep their pose of frame f0 up to frame f1 (a key at f1 with the same rotations)."""
    scene = bpy.context.scene
    arm = bpy.data.objects[j]
    scene.frame_set(f0)
    saved = {b: arm.pose.bones[b].rotation_quaternion.copy() for b in bones}
    scene.frame_set(f1)
    for b, q in saved.items():
        arm.pose.bones[b].rotation_quaternion = q
    tt._update()
    tt.key(j, f1, bones=bones, root=False)


def shape():
    """ease -> plant -> hold -> avoid (see tools/blender/README.md)."""
    for kf in KEYFRAMES[:-1]:
        motion.ease(frame(kf["time"]))
    end = frame(META["duration_seconds"])
    for side in ("Left", "Right"):
        motion.plant("Uki", side, 0, end)
    on_mat("Tori", frame(0.8), frame(1.6))
    for side in ("Right", "Left"):
        motion.avoid("Tori", [f"{side}UpLeg", f"{side}Leg"], "Uki", frame(0.8), frame(1.6), ALLOW, max_rate=6)
    on_mat("Tori", frame(0.8), frame(1.6))
    # In the hold Tori's feet stay put; against the bridge he steps his legs wider and back again.
    scene = bpy.context.scene
    spots = {}
    for t, name in ((2.8, "wide"), (3.6, "narrow")):
        scene.frame_set(frame(t))
        for side in ("Left", "Right"):
            spots[side, name] = list(motion.foot_matrix("Tori", side).translation)
    for side in ("Left", "Right"):
        motion.plant("Tori", side, frame(HOLD), frame(2.0))
        motion.step("Tori", side, frame(2.0), frame(2.5), height=0.04, to=spots[side, "wide"], lift=0.3)
        motion.plant("Tori", side, frame(2.5), frame(3.0))
        motion.step("Tori", side, frame(3.0), frame(3.5), height=0.04, to=spots[side, "narrow"], lift=0.3)
        motion.plant("Tori", side, frame(3.5), end)
    motion.hold("Tori", "LeftHand", "Uki", "RightSleeveGrip", frame(0.8), end)
    for _ in range(2):
        motion.avoid("Tori", ["RightArm", "RightForearm"], "Uki", frame(0.4), end, ALLOW, max_rate=6)
        motion.avoid("Uki", ["RightArm", "RightForearm"], "Tori", frame(0.4), end, ALLOW, max_rate=6)
    for j in ("Tori", "Uki"):
        motion.hinge_elbows(j, 0, end)
    motion.hold("Tori", "LeftHand", "Uki", "RightSleeveGrip", frame(0.8), end)


def check():
    contact.check_all(ALLOW)
    motion.print_sliding(motion.foot_sliding("Uki"), "Foot sliding Uki")
    motion.print_sliding(motion.foot_sliding("Tori", frame(HOLD)), "Foot sliding Tori (in the hold)")
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

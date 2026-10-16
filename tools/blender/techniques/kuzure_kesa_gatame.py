"""Kuzure-kesa-gatame (right side) - authored in Blender, exported to data/techniques/.

Run headless (see tools/blender/README.md):
    blender -b art_source/blender/judoka.blend --python tools/blender/run_technique.py -- kuzure_kesa_gatame --draft

Uki lies on his back, head towards Godot +Z, his right side towards +X. Tori kneels at Uki's right
side, takes Uki's right arm, slides his right arm under Uki's left armpit and sits through into the
hold: right hip against Uki's ribs, legs spread wide, chest on Uki's chest. Uki tries to bridge out;
Tori widens his base and keeps the hold.
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
for _m in (tt, contact, motion):
    importlib.reload(_m)

NAME = "kuzure_kesa_gatame"
OUT = os.path.normpath(os.path.join(TOOLS, "..", "..", "data", "techniques", f"{NAME}.yaml"))

META = dict(technique_name="Kuzure-kesa-gatame", dutch_name="Afgeleide sjaalhoudgreep", waza_group="osaekomi_waza",
            category="Osaekomi-waza (Houdgreep)", code="O5-1", difficulty="Easy", kyu_grade=5,
            belt_name="Gele band", belt_hex="#FFD700", source="VJF leerlijn 2015, geel", duration_seconds=4.4)


def frame(t):
    return round(t * tt.FPS)


def G(x, y, z):
    """A Godot-space point (x, y up, z) as a Blender world point."""
    return Vector((x, -z, y))


def _pairs(a_bones, b_bones, tolerance, start=float("-inf"), end=float("inf")):
    return [contact.Allow(a, b, tolerance, start, end) for a in a_bones for b in b_bones]


HOLD = 1.0  # from here on Tori is in the hold
ALLOW = (
    # Lying, kneeling and sitting on the mat: the capsules settle onto it.
    [contact.Allow("*", contact.MAT, 0.03)]
    # Tori's left hand grips Uki's right sleeve; Uki's right arm is clamped against Tori's chest and
    # under his left armpit.
    + _pairs(["Tori:LeftHand"], ["Uki:RightForearm", "Uki:RightArm", "Uki:RightHand"], 0.07)
    + _pairs(["Tori:LeftArm", "Tori:LeftForearm"], ["Uki:RightForearm", "Uki:RightArm", "Uki:RightHand"], 0.05, 0.4)
    + _pairs(["Uki:RightArm", "Uki:RightForearm", "Uki:RightHand"],
             ["Tori:Chest", "Tori:Spine", "Tori:LeftShoulder", "Tori:LeftArm", "Tori:LeftForearm"], 0.06, HOLD)
    # Tori sits through past Uki's pulled arm: it brushes his thighs.
    + _pairs(["Tori:LeftUpLeg", "Tori:RightUpLeg"], ["Uki:RightArm", "Uki:RightForearm", "Uki:RightHand"], 0.03, 0.7)
    # Tori's chest presses on Uki's chest, his right hip against Uki's ribs and right shoulder.
    + _pairs(["Tori:Chest", "Tori:Spine", "Tori:RightShoulder", "Tori:Hips", "Tori:RightUpLeg"],
             ["Uki:Chest", "Uki:Spine", "Uki:RightShoulder", "Uki:RightArm"], 0.05, HOLD)
    # Tori's right arm goes over Uki's chest and deep under his left armpit (a hollow the capsules
    # do not model), along his ribs; Uki's bridge presses his chest up into it.
    + _pairs(["Tori:RightArm", "Tori:RightForearm", "Tori:RightHand"], ["Uki:Chest", "Uki:Neck"], 0.05, 0.4)
    + _pairs(["Tori:RightArm", "Tori:RightForearm", "Tori:RightHand"], ["Uki:Spine"], 0.03, 0.4)
    + _pairs(["Tori:RightArm", "Tori:RightForearm", "Tori:RightHand"], ["Uki:LeftShoulder", "Uki:LeftArm"], 0.08, 0.4)
    # Uki pushes against Tori's body with his right hand while Tori takes the arm.
    + _pairs(["Uki:RightHand"], ["Tori:Spine", "Tori:Chest", "Tori:Hips"], 0.04, 0.4)
)


# --- poses ---------------------------------------------------------------------------------------
# Limbs are aimed at Godot-space points (G): on the ground, world targets are easier to reason about
# than joint angles. Uki's hips are at the origin, his head towards +Z, his right side towards +X.

LOWER_BODY = ("Hips", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg", "LeftFoot", "RightFoot")


def sit(j, clearance=0.015):
    """Like motion.settle, but only the hips and legs rest on the mat: the arms are posed later (in
    their T-pose rest they would hang below a bowed torso)."""
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
    """Pose with each candidate (`apply(c)`) and keep the one with the least overlap; returns it.
    Every candidate starts from the same pose (IK solves from the current pose)."""
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
    """Grid of points around p (Godot space), +-n steps per axis."""
    r = [i * step for i in range(-n, n + 1)]
    return [(p[0] + dx, p[1] + dy, p[2] + dz) for dx in r for dy in r for dz in r]


def uki_on_back(bridge=0.0):
    """Uki on his back, knees up and feet flat on the mat, arms resting out to the sides. `bridge`
    (0..1) lifts the hips off the mat (trying to bump Tori off); the feet stay where they are
    (motion.plant in shape())."""
    tt.place("Uki", (0, 0, 0), (90, 180, 0))
    tt.rot("Uki", "Neck", (-15, 0, 0))
    for side, x in (("Left", -1), ("Right", 1)):
        limb("Uki", f"{side}UpLeg", f"{side}Leg", (0.14 * x, 0.38, -0.40), (0.17 * x, 0.10, -0.75))
        tt.aim_at("Uki", f"{side}Foot", G(0.18 * x, 0.03, -0.92))
        limb("Uki", f"{side}Arm", f"{side}Forearm", (0.45 * x, 0.08, 0.35), (0.65 * x, 0.09, 0.15))
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
    # Uki's right arm drawn up against Tori's chest by the sleeve.
    target = tt.bone_pos("Tori", "Chest", tail=True) - G(0, 0.15, 0)

    def pulled(pole):
        tt.aim_at("Uki", "RightArm", target)
        tt.aim_at("Uki", "RightForearm", target + G(0.1, 0, 0.1))
        tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip", pole=pole)

    least_overlap(pulled, POLES)
    tt.ik_point("Tori", "RightHand", G(-0.40, 0.06, 0.45))


def kesa(base=0.0, lift=0.0):
    """Kuzure-kesa-gatame: Tori sits at Uki's right side facing past Uki's head, right hip against
    Uki's ribs, right leg forward, left leg back; chest on Uki's chest, Uki's right arm clamped under
    his left armpit, right arm under Uki's left armpit, hand on the mat. `base` (0..1) spreads the
    legs wider (against an escape); `lift` (m): Uki's bridge lifts Tori's upper body."""

    def up(p):
        return (p[0], p[1] + lift, p[2])

    tt.place("Tori", (0, 0, 0), (0, -25, 0))
    tt.pin("Tori", "Hips", G(*HIPS))
    limb("Tori", "RightUpLeg", "RightLeg", (0.62, 0.10, 0.68), (0.95, 0.08, 0.50))
    limb("Tori", "LeftUpLeg", "LeftLeg", (0.90 + 0.1 * base, 0.10, -0.05 - 0.1 * base), (0.80 + 0.1 * base, 0.08, -0.50))
    # Feet along the mat: the right one on its outside, the left one on its instep, toes back.
    for side, direction in (("Right", (0.3, -0.06, 0.0)), ("Left", (0.0, -0.06, -0.3))):
        tt.aim_at("Tori", f"{side}Foot", tt.bone_pos("Tori", f"{side}Foot") + G(*direction))
    tt.aim_at("Tori", "Spine", G(*up(SPINE)))
    tt.aim_at("Tori", "Chest", G(*up(CHEST)))
    tt.aim_at("Tori", "Neck", G(*up(NECK)))
    sit("Tori")
    # Right arm over Uki's chest and under his left armpit, hand on the mat behind his shoulder;
    # Uki's left arm lies over it.
    least_overlap(lambda eh: limb("Tori", "RightArm", "RightForearm", eh[0], eh[1]),
                  [(e, h) for e in around(up(ARM_ELBOW), 0.05) for h in around(ARM_HAND, 0.08)])
    least_overlap(lambda e: limb("Uki", "LeftArm", "LeftForearm", e, (-0.65, 0.09, 0.45)),
                  around(up(UKI_LEFT_ELBOW), 0.06, 2))
    # Uki's right arm is pulled up along Tori's front and clamped under his left armpit; Tori's left
    # hand holds the sleeve.
    limb("Uki", "RightArm", "RightForearm", up(UKI_ELBOW), up(UKI_HAND))
    least_overlap(lambda pole: tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip", pole=pole), POLES)


POLES = [None] + [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if x or y or z]


ARM_ELBOW, ARM_HAND = (-0.22, 0.30, 0.52), (-0.42, 0.08, 0.62)
UKI_ELBOW, UKI_HAND = (0.32, 0.40, 0.70), (0.55, 0.55, 0.62)
UKI_LEFT_ELBOW = (-0.40, 0.42, 0.45)
HIPS, SPINE, CHEST, NECK = (0.42, 0.15, 0.25), (0.30, 0.33, 0.33), (0.08, 0.40, 0.42), (-0.10, 0.38, 0.55)


def hold():
    uki_on_back()
    kesa()


def escape():
    uki_on_back(bridge=1.0)
    kesa(base=1.0, lift=0.07)


KEYFRAMES = [
    dict(time=0.0, phase="Uitgangspositie",
         description="Uki ligt op zijn rug. Tori zit op zijn knieën naast Uki's rechterkant.", pose=start),
    dict(time=0.7, phase="Controle (Arm)",
         description="Tori pakt met zijn linkerhand Uki's rechtermouw bij de elleboog en trekt die arm tegen "
                     "zijn buik. Zijn rechterarm schuift over Uki's borst en onder Uki's linkeroksel door.",
         pose=control),
    dict(time=1.4, phase="Osaekomi (Houdgreep)",
         description="Tori gaat zitten met zijn rechterheup tegen Uki's ribben. Rechterbeen naar voren, linkerbeen "
                     "naar achteren: benen wijd. Uki's rechterarm zit klem onder Tori's linkeroksel en Tori's borst "
                     "drukt op Uki's borst.", pose=hold),
    dict(time=2.6, phase="Ontsnappingspoging",
         description="Uki duwt zijn heupen omhoog om Tori eraf te werpen. Tori zet zijn linkerbeen verder weg en "
                     "blijft met zijn borst zwaar op Uki liggen.",
         pose=escape),
    dict(time=3.4, phase="Osaekomi (Houdgreep)",
         description="Uki ligt weer plat. Tori houdt de mouw vast, de arm klem en zijn borst op Uki's borst.",
         pose=hold),
    dict(time=4.4, phase="Ippon",
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
    # While he sits through, Tori's hips drop and his legs swing round: keep him on the mat.
    on_mat("Tori", frame(0.7), frame(1.4))
    # Tori's legs find their way along the mat while he sits through; the arms around each other.
    for side in ("Right", "Left"):
        motion.avoid("Tori", [f"{side}UpLeg", f"{side}Leg"], "Uki", frame(0.7), frame(1.4), ALLOW, max_rate=6)
    on_mat("Tori", frame(0.7), frame(1.4))
    # In the hold Tori's feet stay put; against the bridge he steps his left leg wider and back again.
    scene = bpy.context.scene
    wide, narrow = [], []
    for t, out in ((2.6, wide), (3.4, narrow)):
        scene.frame_set(frame(t))
        out.extend(motion.foot_matrix("Tori", "Left").translation)
    motion.plant("Tori", "Right", frame(1.4), end)
    motion.plant("Tori", "Left", frame(1.4), frame(1.9))
    motion.step("Tori", "Left", frame(1.9), frame(2.3), height=0.04, to=wide)
    motion.plant("Tori", "Left", frame(2.3), frame(2.9))
    motion.step("Tori", "Left", frame(2.9), frame(3.3), height=0.04, to=narrow)
    motion.plant("Tori", "Left", frame(3.3), end)
    # Tori keeps the sleeve on every frame.
    motion.hold("Tori", "LeftHand", "Uki", "RightSleeveGrip", frame(0.7), end)
    for _ in range(2):
        motion.avoid("Tori", ["RightArm", "RightForearm"], "Uki", frame(0.4), end, ALLOW, max_rate=6)
        motion.avoid("Uki", ["LeftArm", "LeftForearm"], "Tori", frame(0.4), end, ALLOW, max_rate=6)
        motion.avoid("Uki", ["RightArm", "RightForearm"], "Tori", frame(0.4), end, ALLOW, max_rate=6)
    for j in ("Tori", "Uki"):
        motion.hinge_elbows(j, 0, end)


def check():
    contact.print_report(contact.check_contacts(ALLOW))
    motion.print_sliding(motion.foot_sliding("Uki"), "Foot sliding Uki")
    motion.print_sliding(motion.foot_sliding("Tori", frame(1.4)), "Foot sliding Tori (in the hold)")


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

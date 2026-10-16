"""O-uchi-gari (right-handed Tori) - authored in Blender, exported to data/techniques/.

Run headless (see tools/blender/README.md):
    blender -b art_source/blender/judoka.blend --python tools/blender/run_technique.py -- o_uchi_gari --draft

Tori pushes Uki back onto his left heel, brings his left foot up behind his right one, hooks his
right leg inside Uki's left leg and reaps it out in an arc while driving forward with the chest and
the lapel hand: Uki falls backward over his right leg (ushiro-ukemi, slapping with the left arm),
Tori keeps the sleeve.
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Quaternion, Vector

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..") if "__file__" in globals() \
    else r"C:\proj\judo\tools\blender"
sys.path.insert(0, os.path.normpath(TOOLS))
import technique_tools as tt  # noqa: E402
import contact  # noqa: E402
import motion  # noqa: E402
import poses  # noqa: E402
for _m in (tt, contact, motion, poses):
    importlib.reload(_m)
from poses import GRIP_DISTANCE, arms_ready, axis, facing, frame, pairs, right_of, slap, stance  # noqa: E402

NAME = "o_uchi_gari"
OUT = os.path.normpath(os.path.join(TOOLS, "..", "..", "data", "techniques", f"{NAME}.yaml"))

META = dict(technique_name="O-uchi-gari", dutch_name="Grote binnenwaartse maaiworp", waza_group="nage_waza",
            category="Ashi-waza (Beenworp)", code="N5-4", difficulty="Easy",
            kyu_grade=5, belt_name="Gele band", belt_hex="#FFD700", source="VJF leerlijn 2015, geel",
            duration_seconds=2.6)

KAKE_LEAN, NAGE_LEAN = 16, 22  # Uki tipped back (degrees)
KAKE_BOW, NAGE_BOW = -22, -26  # Tori driving forward with the chest
RELEASE = 1.56  # Tori lets go of the sleeve as Uki reaches the mat (beyond reach after that)
UKI_LAPEL_POLE = (1, -0.3, 0.6)  # Uki's lapel elbow out and back: the forearm points at Tori instead of lying across his chest


# --- allowed contacts (contact.check_contacts) --------------------------------------------------

ALLOW = (
    # Kumikata: hands on lapel and sleeve; the gripping arms rub against each other.
    pairs(["Tori:RightHand"], ["Uki:Chest", "Uki:LeftShoulder"], 0.07, end=1.4)
    + pairs(["Uki:RightHand"], ["Tori:Chest", "Tori:LeftShoulder", "Tori:LeftArm"], 0.07, end=1.5)
    + pairs(["Uki:LeftHand"], ["Tori:RightForearm", "Tori:RightArm"], 0.07, end=1.3)
    + pairs(["Tori:LeftHand"], ["Uki:RightForearm", "Uki:RightArm", "Uki:RightHand"], 0.07)
    + pairs(["Tori:LeftForearm"], ["Uki:RightForearm", "Uki:RightHand"], 0.06)
    + pairs(["Uki:LeftForearm"], ["Tori:RightForearm"], 0.06, end=1.3)  # Uki's sleeve arm, likewise
    + pairs(["Tori:RightHand"], ["Uki:LeftForearm", "Uki:LeftArm"], 0.045, end=1.4)
    # Tori closes in: Uki's lapel arm is pressed against Tori's chest.
    + pairs(["Tori:Chest"], ["Uki:RightForearm"], 0.05, 0.3, 0.9)
    + pairs(["Tori:*Forearm", "Tori:*Arm"], ["Uki:*Forearm", "Uki:*Arm"], 0.045, end=1.4)
    # O-uchi: Tori's right calf hooks the back of Uki's left calf and reaps it.
    + pairs(["Tori:RightLeg", "Tori:RightFoot"], ["Uki:LeftLeg", "Uki:LeftFoot"], 0.05, 0.7, 1.4)
    + pairs(["*Foot"], [contact.MAT], 0.03)
)


# --- pose building blocks ------------------------------------------------------------------------

def grip(sides=("Tori", "Uki")):
    if "Tori" in sides:
        tt.ik("Tori", "RightHand", "Uki", "LeftLapelGrip")
        tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")
    if "Uki" in sides:
        tt.ik("Uki", "RightHand", "Tori", "LeftLapelGrip", pole=UKI_LAPEL_POLE)
        tt.ik("Uki", "LeftHand", "Tori", "RightSleeveGrip")


# World positions (Blender space) and foot rotations remembered by the poses in keyframe order.
SPOTS = {}


def gd(x, z, y=0.0):
    """Godot (x, y, z) -> Blender world point."""
    return Vector((x, -z, y))


def ankle(j, side):
    return tt.bone_pos(j, f"{side}Foot")


def foot_on(j, side, x, z, yaw=0.0):
    """Put a foot flat on the mat with the ankle above Godot (x, z), turned `yaw` degrees from the
    kumikata stance (positive: toes outwards); the hips drop if the leg cannot reach."""
    q = Quaternion((0, 0, 1), math.radians(yaw if side == "Left" else -yaw))
    return motion.reach(j, side, gd(x, z, motion.ANKLE_HEIGHT), q.to_matrix() @ SPOTS[f"{j}{side}"], max_move=0.2)


def feet(j, left, right):
    """Both feet: `left`/`right` = (x, z, yaw)."""
    foot_on(j, "Left", *left)
    foot_on(j, "Right", *right)
    foot_on(j, "Left", *left)  # again, in case the hips dropped for the right foot


HOOK_NOMINAL = (0.10, 0.03, 0.09)  # (up, behind, inside), see hook()
HOOK_CONTACT = 0.035  # wanted calf-on-calf overlap of the capsules (the gi trousers are pressed together)
_hook_last = [HOOK_NOMINAL]


def _hook_at(offset):
    up, behind, inside = offset
    target = (ankle("Uki", "Left") + Vector((0, 0, up)) - facing("Uki") * behind + right_of("Uki") * inside)
    motion.leg_ik("Tori", "Right", target)
    tori, uki = contact.world_capsules("Tori"), contact.world_capsules("Uki")
    return max(contact.penetration(tori[a], uki[b])[0]
               for a in ("RightUpLeg", "RightLeg", "RightFoot") for b in ("LeftUpLeg", "LeftLeg", "LeftFoot"))


def hook(fresh=True):
    """Tori's right calf wraps the back of Uki's left calf from the inside: Tori's right ankle goes
    `up` above Uki's left ankle, `behind` it (Uki's back) and `inside` (towards Uki's other leg).
    The offset is searched (from the previous frame's, unless `fresh`) so the legs touch without
    passing through each other."""
    tt.rot("Tori", "RightFoot", (-25, 0, 0))  # instep stretched, toes down

    def score(o):
        d = _hook_at(o)
        return (max(0.0, d - HOOK_CONTACT) * 20 + max(0.0, HOOK_CONTACT - 0.02 - d) * 5
                + 0.3 * sum(abs(x - n) for x, n in zip(o, HOOK_NOMINAL)))

    best = HOOK_NOMINAL if fresh else _hook_last[0]
    best_score = score(best)
    for step in (0.02, 0.01, 0.005):
        improved = True
        while improved:
            improved = False
            for i in range(3):
                for sign in (-1, 1):
                    o = tuple(x + sign * step if k == i else x for k, x in enumerate(best))
                    sc = score(o)
                    if sc < best_score - 1e-6:
                        best, best_score, improved = o, sc, True
    _hook_last[0] = best
    _hook_at(best)
    return best


# Tori's feet (Godot x, z, yaw): the right foot steps in, the left follows up behind its heel (toes
# out), the right comes down in front after the reap.
TORI_LEFT_START, TORI_RIGHT_START = (0.16, 0.0, 0), (-0.16, 0.0, 0)
TORI_RIGHT_IN = (-0.10, 0.24, 10)
TORI_LEFT_UP = (0.05, 0.20, 40)
TORI_RIGHT_DOWN = (-0.11, 0.47, 15)


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
            SPOTS[f"{j}{side}"] = motion.foot_matrix(j, side).to_3x3()
    SPOTS["uki_right"] = ankle("Uki", "Right")
    SPOTS["fwd"] = facing("Tori")  # from Tori towards Uki
    grip()


def uki_leaning_back(lean):
    """Uki pushed back onto his heels, pivoting about his feet."""
    tt.place("Uki", (0, 0, GRIP_DISTANCE), (lean, 180, 0))
    stance("Uki", knee=8 + lean / 3)
    tt.rot("Uki", "Spine", (-lean / 2, 0, 0))
    tt.rot("Uki", "Neck", (-lean / 2, 0, 0))
    arms_ready("Uki")
    feet("Uki", (-0.16, GRIP_DISTANCE, 0), (0.16, GRIP_DISTANCE, 0))


def tori_body(position, turn, bow, chest=0.0, knee=16):
    tt.place("Tori", position, (0, turn, 0))
    stance("Tori", knee=knee)
    tt.rot("Tori", "Spine", (bow, 0, 0))
    tt.rot("Tori", "Chest", (chest, 0, 0))
    arms_ready("Tori")


def kuzushi():
    # Tori steps in with the right foot between Uki's feet and pushes him back onto the heels.
    uki_leaning_back(10)
    tori_body((-0.02, -0.02, 0.14), -8, -8)
    feet("Tori", TORI_LEFT_START, TORI_RIGHT_IN)
    grip()


def tsukuri():
    # Tori's left foot follows up behind the right heel (T-shape); his chest comes close, the right
    # hand pushes Uki's lapel up and back, the left pulls the sleeve out: Uki's weight is on the left heel.
    uki_leaning_back(16)
    tori_body((-0.02, -0.04, 0.26), -15, -10, -4, knee=20)
    feet("Tori", TORI_LEFT_UP, TORI_RIGHT_IN)
    grip()


def kake():
    # Tori's right leg goes in between Uki's legs and hooks the back of Uki's left calf; Tori drives
    # forward with his chest. Uki, pushed back, leans further back.
    uki_leaning_back(KAKE_LEAN)
    tori_body((0.0, -0.05, 0.28), -20, KAKE_BOW, -6, knee=22)
    feet("Tori", TORI_LEFT_UP, TORI_RIGHT_IN)
    hook()
    grip()


def nage():
    # Tori reaps Uki's left leg out in an arc to Uki's left; Uki tips backward over his right leg.
    tt.place("Uki", (0, 0, GRIP_DISTANCE), (NAGE_LEAN, 180, -8))
    stance("Uki", knee=16)
    tt.rot("Uki", "LeftUpLeg", (25, 0, -30))
    tt.rot("Uki", "LeftLeg", (-20, 0, 0))
    tt.rot("Uki", "Spine", (-10, 0, 0))
    tt.rot("Uki", "Neck", (-20, 0, 0))
    arms_ready("Uki")
    tt.pin("Uki", "RightFoot", SPOTS["uki_right"])
    tori_body((0.02, -0.05, 0.30), -25, NAGE_BOW, -6, knee=22)
    feet("Tori", TORI_LEFT_UP, TORI_RIGHT_IN)
    hook()
    grip()


def fall():
    # Uki sits down backwards over his right foot, the left leg up and out. Tori puts the reaping
    # foot down in front.
    tt.place("Uki", (0, 0, GRIP_DISTANCE), (40, 180, -10))
    tt.rot("Uki", "LeftUpLeg", (70, 0, -30))
    tt.rot("Uki", "LeftLeg", (-30, 0, 0))
    tt.rot("Uki", "RightUpLeg", (80, 0, 10))
    tt.rot("Uki", "RightLeg", (-110, 0, 0))
    tt.rot("Uki", "Spine", (-20, 0, 0))
    tt.rot("Uki", "Chest", (-10, 0, 0))
    tt.rot("Uki", "Neck", (-35, 0, 0))
    tt.aim("Uki", "LeftArm", (-0.7, 0.1, -0.7))
    tt.aim("Uki", "LeftForearm", (-0.6, 0.3, -0.75))
    tt.pin("Uki", "RightFoot", SPOTS["uki_right"])
    tori_body((0.0, -0.06, 0.32), -15, -24, -8, knee=22)
    feet("Tori", TORI_LEFT_UP, TORI_RIGHT_DOWN)
    tt.ik("Tori", "LeftHand", "Uki", "RightSleeveGrip")


def ukemi_pose(tori_bow):
    # Uki on the back, head away from Tori, chin tucked, legs spread, slapping the mat with both arms.
    tt.place("Uki", (0, 0, 0), (90, 180, -6))
    tt.rot("Uki", "LeftUpLeg", (80, 0, -50))
    tt.rot("Uki", "RightUpLeg", (80, 0, 30))
    tt.rot("Uki", "LeftLeg", (-80, 0, 0))
    tt.rot("Uki", "RightLeg", (-85, 0, 0))
    tt.rot("Uki", "Neck", (-30, 0, 0))
    hips = SPOTS["uki_right"] + SPOTS["fwd"] * 0.42
    tt.pin("Uki", "Hips", Vector((hips.x, hips.y, 0.2)))
    motion.settle("Uki")
    slap("Uki", "Left")
    slap("Uki", "Right")
    # Tori has let go: both arms hang loosely in front, elbows a little bent.
    tt.rot("Tori", "Spine", (tori_bow, 0, 0))
    tt.aim("Tori", "RightArm", (0.3, -1, 0))
    tt.aim("Tori", "RightForearm", (0.15, -1, -0.3))
    tt.aim("Tori", "LeftArm", (-0.3, -1, 0))
    tt.aim("Tori", "LeftForearm", (-0.15, -1, -0.3))


def ukemi():
    tori_body((0.0, -0.07, 0.32), -10, -36, -10, knee=24)
    feet("Tori", TORI_LEFT_UP, TORI_RIGHT_DOWN)
    ukemi_pose(-36)


def zanshin():
    tori_body((0.0, -0.04, 0.32), -10, -26, -6, knee=16)
    feet("Tori", TORI_LEFT_UP, TORI_RIGHT_DOWN)
    ukemi_pose(-26)


KEYFRAMES = [
    dict(time=0.0, phase="Kumikata (Grip)",
         description="Tori en Uki pakken elkaar vast: rechterhand aan de revers, linkerhand aan de mouw.",
         pose=kumikata),
    dict(time=0.36, phase="Kuzushi (Balansverstoring)",
         description="Tori stapt in met rechts en duwt Uki naar achteren op de hielen.",
         pose=kuzushi),
    dict(time=0.66, phase="Tsukuri (Instap)",
         description="Tori sluit de linkervoet aan achter de rechterhiel en komt met de borst dichtbij; Uki's gewicht ligt op de linkerhiel.",
         pose=tsukuri),
    dict(time=0.92, phase="Kake (Haak)",
         description="Tori haakt het rechterbeen van binnenuit achter Uki's linkerkuit en drukt naar voren.",
         pose=kake),
    dict(time=1.2, phase="Nage (Maaien)",
         description="Tori maait Uki's linkerbeen in een boog naar buiten; Uki kantelt achterover over het rechterbeen.",
         pose=nage),
    dict(time=1.5, phase="Nage (Val)",
         description="Uki valt achterover en zakt door het rechterbeen; Tori zet de maaivoet neer.",
         pose=fall),
    dict(time=1.8, phase="Ukemi (Valbreking)",
         description="Uki landt op de rug en slaat met beide armen op de mat; Tori laat de mouw los als Uki de mat raakt.",
         pose=ukemi),
    dict(time=2.6, phase="Zanshin (Controle)",
         description="Tori komt overeind en blijft naar Uki kijken, klaar om te reageren.",
         pose=zanshin),
]


def tori_feet():
    """Right foot steps in, left foot follows up behind it (tsugi-ashi); the right leg then hooks and
    reaps (free) and comes down in front."""
    motion.plant("Tori", "Right", frame(0.0), frame(0.04))
    motion.step("Tori", "Right", frame(0.04), frame(0.36), lift=0.15)
    motion.plant("Tori", "Right", frame(0.36), frame(0.74))
    motion.step("Tori", "Right", frame(0.74), frame(0.92), height=0.06, lift=0.2)  # up into the hook
    motion.plant("Tori", "Left", frame(0.0), frame(0.40))
    motion.step("Tori", "Left", frame(0.40), frame(0.66), lift=0.15)
    motion.plant("Tori", "Left", frame(0.66), frame(2.6))
    motion.step("Tori", "Right", frame(1.26), frame(1.44), height=0.03, lift=0.25,
                to=gd(TORI_RIGHT_DOWN[0], TORI_RIGHT_DOWN[1], motion.ANKLE_HEIGHT))
    motion.plant("Tori", "Right", frame(1.44), frame(2.6))


def tori_weight():
    motion.shift_weight("Tori", "Left", frame(0.0), frame(0.38), ramp=4)
    motion.shift_weight("Tori", "Right", frame(0.38), frame(0.68), ramp=4)
    motion.shift_weight("Tori", "Left", frame(0.68), frame(1.44), ramp=(4, 2))
    motion.shift_weight("Tori", "both", frame(1.44), frame(2.6), ramp=8)


def hooked(_w=None):
    hook(fresh=False)


# (judoka, hand, partner, grip bone, held until s, gripping until s, IK pole) in dependency order: lapel hands first (they
# hold the torso), then the sleeve hands, which hold the partner's lapel arm and must follow it.
# Uki keeps the lapel until he falls; out of reach, his arm keeps pointing at it until Tori lets go
# of the sleeve (letting go earlier swings it through Tori's sleeve arm).
GRIPS = [("Uki", "RightHand", "Tori", "LeftLapelGrip", RELEASE, 1.2, UKI_LAPEL_POLE),
         ("Tori", "RightHand", "Uki", "LeftLapelGrip", 1.2, 1.2, None),
         ("Uki", "LeftHand", "Tori", "RightSleeveGrip", 1.2, 1.2, None),
         ("Tori", "LeftHand", "Uki", "RightSleeveGrip", RELEASE, RELEASE, None)]


def hold_grips():
    for j, hand, other, grip_bone, until, _, pole in GRIPS:
        motion.hold(j, hand, other, grip_bone, frame(0.0), frame(until), pole=pole)


def grip_gaps():
    """Largest distance (m) between each holding hand's tail and its grip bone, and when."""
    scene = bpy.context.scene
    result = {}
    for j, hand, other, grip_bone, _, gripping, _ in GRIPS:
        worst = (0.0, 0.0)
        for f in range(0, frame(gripping) + 1):
            scene.frame_set(f)
            worst = max(worst, ((tt.bone_pos(j, hand, tail=True) - tt.bone_pos(other, grip_bone)).length, f / tt.FPS))
        result[f"{j}:{hand} -> {other}:{grip_bone}"] = worst
    return result


def shape():
    motion.ease(frame(0.0), "EASE_IN")
    motion.ease(frame(0.92), "EASE_IN", "QUAD")  # the reap accelerates
    motion.ease(frame(1.8), "EASE_OUT")
    tori_feet()
    tori_weight()
    for side in ("Left", "Right"):
        motion.plant("Uki", side, frame(0.0), frame(0.92))
    motion.plant("Uki", "Right", frame(0.92), frame(1.5))
    # Uki drops onto the back.
    motion.fall("Uki", frame(1.5), frame(1.8))
    # Tori's right calf stays behind Uki's left calf while hooking and reaping.
    motion.repose("Tori", ["RightUpLeg", "RightLeg", "RightFoot"], frame(0.92), frame(1.26), hooked)
    hold_grips()
    # Arms find their way around the partner between keyframes.
    for _ in range(2):
        motion.avoid("Tori", ["RightArm", "RightForearm"], "Uki", frame(0.4), frame(1.8), ALLOW, max_rate=6)
        for side in ("Right", "Left"):
            motion.avoid("Uki", [f"{side}Arm", f"{side}Forearm"], "Tori", frame(0.4), frame(1.8), ALLOW, max_rate=6)
    motion.smooth("Uki", ["LeftArm", "LeftForearm", "RightArm", "RightForearm"], frame(0.4), frame(1.74))
    # Uki's reaped leg comes down past Tori's right thigh.
    motion.avoid("Uki", ["LeftUpLeg", "LeftLeg"], "Tori", frame(1.5), frame(2.0), ALLOW, max_rate=6, smooth=0.0003)
    motion.avoid("Uki", ["LeftArm", "LeftForearm"], "Tori", frame(0.96), frame(1.16), ALLOW, max_rate=3)
    for j in ("Tori", "Uki"):
        print(f"Elbow hinge {j}: largest upper-arm twist", motion.hinge_elbows(j, 0, frame(2.6)))
    # avoid and the elbow twist move the arms (and the sleeve grips on the forearms): grip again.
    hold_grips()
    # The grips pull the sleeve arms through each other again: tilt them clear (a hand may end up 1-2 cm off its grip).
    motion.avoid("Uki", ["LeftArm", "LeftForearm"], "Tori", frame(0.7), frame(1.2), ALLOW, max_rate=3)


def check():
    contact.check_all(ALLOW)
    motion.print_sliding(motion.foot_sliding("Tori"), "Foot sliding Tori")
    motion.print_sliding(motion.foot_sliding("Uki", 0, frame(0.92)), "Foot sliding Uki (before the reap)")
    # From the hook on, Uki's left foot is reaped (swept over the mat): only the right one must stay.
    standing = {k: v for k, v in motion.foot_sliding("Uki", frame(0.92), frame(1.5)).items() if "Right" in k}
    motion.print_sliding(standing, "Foot sliding Uki (standing leg)")
    motion.print_balance("Tori", motion.balance("Tori"))
    print("Grip gaps (hand off its grip):")
    for name, (gap, t) in grip_gaps().items():
        print(f"  {name:40} {gap * 100:5.1f} cm at {t:.2f}s")
    landing = motion.first_mat_contact("Uki", ["Hips", "Spine", "LeftHand", "LeftForearm"], frame(1.2))
    print("Uki on the mat:", landing)
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
        check()
        if export:
            return tt.export_yaml(OUT, META, [{k: v for k, v in kf.items() if k != "pose"} for kf in KEYFRAMES])


if __name__ == "__main__":
    main()

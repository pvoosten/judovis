"""Pose edits made in the app (F3 pose editor): edits/<technique>.json, applied on the Blender timeline.

The edits are corrections by the user and count as more correct than the script: a technique's main()
calls apply(NAME) after shape() (so no tool undoes them) and before check() and export_yaml(), so the
reports and the YAML include them. Mirrors JudoVisualizer.Data.PoseEditing (src/Data/PoseEditing.cs):

- An edit sets one channel of Tori or Uki (a bone delta, the root position or the root rotation) to an
  absolute target at its anchor `time`, with weight 0 at `from`, 1 on `hold_from`..`hold_to`, 0 at `to`
  (smoothstep or linear in between). Per channel the corrections (target minus the unedited value at each
  anchor; rotations as rotation vectors, applied on the left) are summed with their weights.
- A later edit replaces an earlier one whose hold range it overlaps; fades end at the hold ranges of the
  channel's other edits. So every anchor lands exactly on its target and a second application is a no-op.
- Every frame in an edit's [from, to] is keyed (the ends with their current value, pinning them); the
  anchor, the range ends and the inserted keyframes are exported as keyframes (tt.EXTRA_FRAMES).
"""
import json
import math
import os

import bpy
from mathutils import Quaternion, Vector

import technique_tools as tt

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EPS = 1e-3  # s: the same keyframe
JUDOKA = {"tori": "Tori", "uki": "Uki"}


def path(name):
    return os.path.join(ROOT, "edits", f"{name}.json")


def load(name):
    p = path(name)
    if not os.path.exists(p):
        return {"keyframes": [], "edits": []}
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return {"keyframes": data.get("keyframes", []), "edits": data.get("edits", [])}


def _frame(t):
    return round(t * tt.FPS)


class Span:
    def __init__(self, edit):
        t = edit["time"]
        self.edit = edit
        self.hold_from = min(edit.get("hold_from", t), t)
        self.hold_to = max(edit.get("hold_to", t), t)
        self.start = min(edit.get("from", t), self.hold_from)
        self.end = max(edit.get("to", t), self.hold_to)
        self.smooth = edit.get("ease", "smooth") != "linear"

    def weight(self, t):
        if self.hold_from - EPS <= t <= self.hold_to + EPS:
            return 1.0
        if t < self.hold_from:
            if t <= self.start + EPS:
                return 0.0
            s = (t - self.start) / (self.hold_from - self.start)
        else:
            if t >= self.end - EPS:
                return 0.0
            s = (self.end - t) / (self.end - self.hold_to)
        return s * s * (3 - 2 * s) if self.smooth else s


def _channels(edit):
    """(who, channel): channel is "position", "rotation" or a bone name of tt.POSABLE."""
    who = edit.get("who")
    if who not in JUDOKA:
        return []
    if edit.get("bone") == "root":
        return [(who, c) for c in ("position", "rotation") if edit.get(c) is not None]
    bone = next((b for b in tt.POSABLE if tt.snake(b) == edit.get("bone", "").replace("-", "_").lower()
                 or b.lower() == edit.get("bone", "").replace("_", "").lower()), None)
    return [(who, bone)] if bone and edit.get("rotation") is not None else []


def spans(edits):
    """{(who, channel): [Span]} in file order, overlapping hold ranges resolved, fades cut off."""
    groups = {}
    for edit in edits:
        for channel in _channels(edit):
            span = Span(edit)
            group = groups.setdefault(channel, [])
            group[:] = [s for s in group
                        if not (s.hold_from <= span.hold_to + EPS and span.hold_from <= s.hold_to + EPS)]
            group.append(span)
    for group in groups.values():
        for s in group:
            for o in group:
                if o is s:
                    continue
                if o.hold_from > s.hold_to:
                    s.end = min(s.end, o.hold_from)
                else:
                    s.start = max(s.start, o.hold_to)
    return groups


# --- channel values in the YAML convention (Godot space, frame A deltas) at the current frame ---------

def _get(arm, channel):
    if channel == "position":
        return tt.B2G @ arm.matrix_world.translation
    if channel == "rotation":
        return (tt.B2G @ arm.matrix_world.to_3x3().normalized() @ tt.B2G.transposed()).to_quaternion()
    return tt.delta(arm.pose.bones[channel]).to_quaternion()


def _set(arm, channel, value, frame):
    if channel == "position":
        arm.location = (value.x, -value.z, value.y)
        tt.key(arm, frame, bones=[], root=True)
    elif channel == "rotation":
        arm.rotation_mode = 'QUATERNION'
        arm.rotation_quaternion = (tt.B2G.transposed() @ value.to_matrix() @ tt.B2G).to_quaternion()
        tt.key(arm, frame, bones=[], root=True)
    else:
        pb = arm.pose.bones[channel]
        tt._set_accumulated(pb, tt.accumulated(pb.parent) @ value.to_matrix())
        tt.key(arm, frame, bones=[channel], root=False)


def _log(q):
    q = q.normalized()
    if q.w < 0:
        q = -q
    v = Vector((q.x, q.y, q.z))
    sin = v.length
    return Vector((0, 0, 0)) if sin < 1e-8 else v / sin * (2 * math.atan2(sin, q.w))


def _exp(v):
    angle = v.length
    return Quaternion() if angle < 1e-8 else Quaternion(v / angle, angle)


def _target(edit, channel):
    if channel == "position":
        return Vector(edit["position"])
    return tt.from_godot_euler(edit["rotation"]).to_quaternion()


def apply(name):
    """Apply edits/<name>.json to the keyed timeline (after shape()); prints a report. Returns the edits."""
    data = load(name)
    tt.EXTRA_FRAMES = {_frame(t) for t in data["keyframes"]}
    for e in data["edits"]:
        tt.EXTRA_FRAMES |= {_frame(e.get(k, e["time"])) for k in ("from", "hold_from", "time", "hold_to", "to")}
    if not data["edits"] and not data["keyframes"]:
        return []

    scene = bpy.context.scene
    groups = spans(data["edits"])
    lines = []
    for (who, channel), group in groups.items():
        arm = bpy.data.objects[JUDOKA[who]]
        corrections = []
        for s in group:
            scene.frame_set(_frame(s.edit["time"]))
            base, target = _get(arm, channel), _target(s.edit, channel)
            if channel == "position":
                c = target - base
                size = f"{c.length * 100:.1f} cm"
            else:
                c = _log(target @ base.inverted())
                size = f"{math.degrees(c.length):.1f}°"
            corrections.append(c)
            lines.append(f"  {s.edit['time']:.2f} s {who}.{s.edit['bone']} {channel + ' ' if channel in ('position', 'rotation') else ''}"
                         f"{size} (range {s.start:.2f}-{s.end:.2f} s, full {s.hold_from:.2f}-{s.hold_to:.2f} s)")
        # Read every frame before keying any: a new key changes the interpolated values next to it.
        frames = sorted({f for s in group for f in range(_frame(s.start), _frame(s.end) + 1)})
        bases = {}
        for f in frames:
            scene.frame_set(f)
            bases[f] = _get(arm, channel)
        for f in frames:
            scene.frame_set(f)
            t = f / tt.FPS
            total = Vector((0, 0, 0))
            for s, c in zip(group, corrections):
                total += c * s.weight(t)
            base = bases[f]
            _set(arm, channel, base + total if channel == "position" else _exp(total) @ base, f)
    print(f"Pose edits (edits/{name}.json, applied after shape()): {len(data['edits'])} edits on "
          f"{len(groups)} channels, {len(data['keyframes'])} inserted keyframes; correction at each anchor:")
    for line in lines:
        print(line)
    return data["edits"]

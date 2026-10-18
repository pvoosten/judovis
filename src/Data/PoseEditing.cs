using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;

namespace JudoVisualizer.Data;

/// <summary>Rotation maths in the YAML convention (Godot <c>EulerOrder.Xyz</c>: R = Rx·Ry·Rz, degrees).</summary>
public static class Rotations
{
    public static Quaternion FromEuler(Vec3 degrees) =>
        Quaternion.CreateFromAxisAngle(Vector3.UnitX, Radians(degrees.X))
        * Quaternion.CreateFromAxisAngle(Vector3.UnitY, Radians(degrees.Y))
        * Quaternion.CreateFromAxisAngle(Vector3.UnitZ, Radians(degrees.Z));

    /// <summary>Euler XYZ degrees, decomposed as Godot's <c>Basis.GetEuler(EulerOrder.Xyz)</c> does.</summary>
    public static Vec3 ToEuler(Quaternion q)
    {
        q = Quaternion.Normalize(q);
        double x = q.X, y = q.Y, z = q.Z, w = q.W;
        double m00 = 1 - 2 * (y * y + z * z), m01 = 2 * (x * y - z * w), m02 = 2 * (x * z + y * w);
        double m11 = 1 - 2 * (x * x + z * z), m12 = 2 * (y * z - x * w);
        double m21 = 2 * (y * z + x * w), m22 = 1 - 2 * (x * x + y * y);
        double ex, ey, ez;
        if (Math.Abs(m02) < 1 - 1e-6)
        {
            ex = Math.Atan2(-m12, m22);
            ey = Math.Asin(m02);
            ez = Math.Atan2(-m01, m00);
        }
        else
        {
            ex = Math.Atan2(m21, m11);
            ey = Math.Sign(m02) * Math.PI / 2;
            ez = 0;
        }
        return new Vec3(Degrees(ex), Degrees(ey), Degrees(ez));
    }

    /// <summary>Rotation vector (axis × angle in radians) of the shortest rotation equal to <paramref name="q"/>.</summary>
    public static Vector3 Log(Quaternion q)
    {
        q = Quaternion.Normalize(q);
        if (q.W < 0)
            q = Quaternion.Negate(q);
        var v = new Vector3(q.X, q.Y, q.Z);
        var sin = v.Length();
        if (sin < 1e-8f)
            return Vector3.Zero;
        return v / sin * (2 * MathF.Atan2(sin, q.W));
    }

    public static Quaternion Exp(Vector3 rotationVector)
    {
        var angle = rotationVector.Length();
        return angle < 1e-8f ? Quaternion.Identity : Quaternion.CreateFromAxisAngle(rotationVector / angle, angle);
    }

    /// <summary>Angle between two rotations in degrees.</summary>
    public static float Angle(Quaternion a, Quaternion b) =>
        Degrees(2 * Math.Acos(Math.Min(1, Math.Abs(Quaternion.Dot(Quaternion.Normalize(a), Quaternion.Normalize(b))))));

    private static float Radians(float degrees) => degrees * MathF.PI / 180;

    private static float Degrees(double radians) => (float)(radians * 180 / Math.PI);
}

/// <summary>
/// Applies a <see cref="PoseEditFile"/> to a technique, the way <c>tools/blender/edits.py</c> does on the
/// Blender timeline. Per channel (one bone, the root position or the root rotation of one judoka) each edit
/// contributes its correction (target ⊖ unedited value at its anchor) times its weight: 0 at
/// <see cref="PoseEdit.From"/>, 1 on <see cref="PoseEdit.HoldFrom"/>..<see cref="PoseEdit.HoldTo"/>, 0 at
/// <see cref="PoseEdit.To"/>. An edit's fade is cut off at the hold range of the channel's other edits, so
/// every anchor ends up exactly on its target and applying the edits again changes nothing.
/// Rotation corrections are added as rotation vectors and applied on the left (in the parent's frame).
/// </summary>
public static class PoseEditing
{
    public const float Fps = 50;

    /// <summary>Times closer than this (seconds) are the same keyframe.</summary>
    public const float TimeEpsilon = 1e-3f;

    /// <summary>Spacing of the extra keyframes in a smooth fade, so the app shows the curve Blender bakes.</summary>
    private const float SmoothStep = 2 / Fps;

    public static float SnapTime(float seconds) => MathF.Round(seconds * Fps) / Fps;

    /// <summary>A judoka value that edits change: a bone (skeleton name), "position" or "rotation".</summary>
    public readonly record struct Channel(string Who, string Value)
    {
        public const string Position = "position";
        public const string Rotation = "rotation";
    }

    /// <summary>An edit with its times put in order and its fades cut off at the channel's other edits.</summary>
    public readonly record struct Span(PoseEdit Edit, float From, float HoldFrom, float HoldTo, float To, bool Smooth)
    {
        public float Weight(float t)
        {
            float s;
            if (t >= HoldFrom - TimeEpsilon && t <= HoldTo + TimeEpsilon)
                return 1;
            if (t < HoldFrom)
            {
                if (t <= From + TimeEpsilon)
                    return 0;
                s = (t - From) / (HoldFrom - From);
            }
            else
            {
                if (t >= To - TimeEpsilon)
                    return 0;
                s = (To - t) / (To - HoldTo);
            }
            return Smooth ? s * s * (3 - 2 * s) : s;
        }

        public bool Contains(float t) => t >= From - TimeEpsilon && t <= To + TimeEpsilon;

        public bool Holds(float t) => t >= HoldFrom - TimeEpsilon && t <= HoldTo + TimeEpsilon;
    }

    /// <summary>The edit's times in order: From ≤ HoldFrom ≤ Time ≤ HoldTo ≤ To.</summary>
    public static Span Normalize(PoseEdit e)
    {
        var holdFrom = Math.Min(e.HoldFrom, e.Time);
        var holdTo = Math.Max(e.HoldTo, e.Time);
        return new Span(e, Math.Min(e.From, holdFrom), holdFrom, holdTo, Math.Max(e.To, holdTo), e.Ease != PoseEase.Linear);
    }

    /// <summary>The channels an edit changes (a root edit: position and/or rotation).</summary>
    public static IEnumerable<Channel> Channels(PoseEdit e)
    {
        if (e.IsRoot)
        {
            if (e.Position is not null)
                yield return new Channel(e.Who, Channel.Position);
            if (e.Rotation is not null)
                yield return new Channel(e.Who, Channel.Rotation);
        }
        else if (e.Rotation is not null && BoneNames.TryResolve(e.Bone, out var bone))
            yield return new Channel(e.Who, bone);
    }

    /// <summary>
    /// The edits per channel, in file order, as spans: an edit whose hold range overlaps a later edit's on
    /// the same channel is dropped; fades end where another edit's hold range begins.
    /// </summary>
    public static Dictionary<Channel, List<Span>> Spans(IEnumerable<PoseEdit> edits)
    {
        var groups = new Dictionary<Channel, List<Span>>();
        foreach (var edit in edits.Where(e => e.Who is "tori" or "uki"))
            foreach (var channel in Channels(edit))
            {
                if (!groups.TryGetValue(channel, out var spans))
                    groups[channel] = spans = [];
                var span = Normalize(edit);
                spans.RemoveAll(s => s.HoldFrom <= span.HoldTo + TimeEpsilon && span.HoldFrom <= s.HoldTo + TimeEpsilon);
                spans.Add(span);
            }

        foreach (var spans in groups.Values)
            for (var i = 0; i < spans.Count; i++)
            {
                var s = spans[i];
                var (from, to) = (s.From, s.To);
                foreach (var o in spans.Where((_, j) => j != i))
                {
                    if (o.HoldFrom > s.HoldTo)
                        to = Math.Min(to, o.HoldFrom);
                    else
                        from = Math.Max(from, o.HoldTo);
                }
                spans[i] = s with { From = from, To = to };
            }
        return groups;
    }

    /// <summary>Keyframe times that edits need: inserted keyframes and every edit's anchor and range ends.</summary>
    public static SortedSet<float> EditTimes(PoseEditFile file)
    {
        var times = new SortedSet<float>(file.Keyframes);
        foreach (var e in file.Edits)
            times.UnionWith([e.From, e.HoldFrom, e.Time, e.HoldTo, e.To]);
        return times;
    }

    /// <summary>A copy of <paramref name="technique"/> with in-between keyframes sampled at <paramref name="times"/>
    /// (times that already have a keyframe, or lie outside the technique, are skipped).</summary>
    public static Technique WithKeyframes(Technique technique, IEnumerable<float> times)
    {
        var copy = Clone(technique);
        foreach (var time in times)
        {
            var t = Math.Clamp(time, 0, technique.DurationSeconds);
            var keyframes = copy.Keyframes;
            if (keyframes.Count == 0 || keyframes.Any(k => Math.Abs(k.Time - t) < TimeEpsilon))
                continue;
            var inserted = new Keyframe
            {
                Time = t, Inbetween = true,
                Tori = SamplePose(keyframes, k => k.Tori, t), Uki = SamplePose(keyframes, k => k.Uki, t),
            };
            var index = keyframes.FindIndex(k => k.Time > t);
            keyframes.Insert(index < 0 ? keyframes.Count : index, inserted);
        }
        return copy;
    }

    /// <summary>The technique with the edits applied (a new object; <paramref name="technique"/> is unchanged).</summary>
    public static Technique Apply(Technique technique, PoseEditFile file)
    {
        if (!technique.IsAnimated || file.IsEmpty)
            return technique;

        var groups = Spans(file.Edits);
        var times = EditTimes(file);
        foreach (var span in groups.Values.SelectMany(s => s).Where(s => s.Smooth))
            foreach (var (a, b) in new[] { (span.From, span.HoldFrom), (span.HoldTo, span.To) })
                for (var t = a + SmoothStep; t < b - TimeEpsilon; t += SmoothStep)
                    times.Add(SnapTime(t));
        var result = WithKeyframes(technique, times);
        var keyframes = result.Keyframes;

        foreach (var (channel, spans) in groups)
        {
            Func<Keyframe, JudokaPose> pose = channel.Who == "tori" ? k => k.Tori : k => k.Uki;
            if (channel.Value == Channel.Position)
            {
                var corrections = spans.Select(s => s.Edit.Position!.Value.Minus(SamplePosition(keyframes, pose, s.Edit.Time) ?? Vec3.Zero)).ToList();
                var updates = new List<(Keyframe, Vec3)>();
                foreach (var k in keyframes)
                {
                    var sum = Vec3.Zero;
                    var touched = false;
                    for (var i = 0; i < spans.Count; i++)
                        if (spans[i].Weight(k.Time) is > 0 and var w)
                        {
                            sum = sum.Plus(corrections[i].Times(w));
                            touched = true;
                        }
                    if (touched)
                        updates.Add((k, (SamplePosition(keyframes, pose, k.Time) ?? Vec3.Zero).Plus(sum)));
                }
                foreach (var (k, value) in updates)
                    pose(k).Position = value;
            }
            else
            {
                var corrections = spans.Select(s =>
                    Rotations.Log(Rotations.FromEuler(s.Edit.Rotation!.Value)
                                  * Quaternion.Inverse(SampleRotation(keyframes, pose, channel.Value, s.Edit.Time)))).ToList();
                var updates = new List<(Keyframe, Vec3)>();
                foreach (var k in keyframes)
                {
                    var sum = Vector3.Zero;
                    var touched = false;
                    for (var i = 0; i < spans.Count; i++)
                        if (spans[i].Weight(k.Time) is > 0 and var w)
                        {
                            sum += corrections[i] * w;
                            touched = true;
                        }
                    if (touched)
                        updates.Add((k, Rotations.ToEuler(Rotations.Exp(sum) * SampleRotation(keyframes, pose, channel.Value, k.Time))));
                }
                foreach (var (k, value) in updates)
                    SetRotation(pose(k), channel.Value, value);
            }
        }
        return result;
    }

    /// <summary>
    /// Sets <paramref name="who"/>'s <paramref name="bone"/> (skeleton name or <see cref="PoseEdit.Root"/>) at the
    /// keyframe <paramref name="time"/> to the given values (null = leave as is), so that the edited technique
    /// <c>Apply(technique, file)</c> shows them there. Changes the edit that holds this channel at
    /// <paramref name="time"/> (keeping its anchor and range), or adds one with the range of
    /// <paramref name="range"/> (From, HoldFrom, HoldTo, To). Returns the edit.
    /// </summary>
    public static PoseEdit SetValue(PoseEditFile file, Technique technique, string who, string bone, float time,
                                    Vec3? rotation, Vec3? position, (float From, float HoldFrom, float HoldTo, float To) range,
                                    string ease = PoseEase.Smooth)
    {
        var key = bone == PoseEdit.Root ? PoseEdit.Root : FeedbackFile.BoneKey(bone);
        var edit = Holding(file, who, bone, time);
        if (edit is null)
        {
            edit = new PoseEdit
            {
                Who = who, Bone = key, Time = time, Ease = ease,
                From = range.From, HoldFrom = range.HoldFrom, HoldTo = range.HoldTo, To = range.To,
            };
            file.Edits.Add(edit);
        }

        // The edit's target is its anchor value plus the correction wanted at `time` (they are equal on the hold range).
        var keyframes = WithKeyframes(technique, EditTimes(file).Append(time)).Keyframes;
        Func<Keyframe, JudokaPose> pose = who == "tori" ? k => k.Tori : k => k.Uki;
        if (rotation is { } r)
        {
            var channel = bone == PoseEdit.Root ? Channel.Rotation : bone;
            var correction = Rotations.FromEuler(r) * Quaternion.Inverse(SampleRotation(keyframes, pose, channel, time));
            edit.Rotation = Rotations.ToEuler(correction * SampleRotation(keyframes, pose, channel, edit.Time));
        }
        if (position is { } p && bone == PoseEdit.Root)
        {
            var at = SamplePosition(keyframes, pose, time) ?? Vec3.Zero;
            edit.Position = (SamplePosition(keyframes, pose, edit.Time) ?? Vec3.Zero).Plus(p.Minus(at));
        }
        return edit;
    }

    /// <summary>The edit of this channel whose hold range contains <paramref name="time"/>, if any.</summary>
    public static PoseEdit? Holding(PoseEditFile file, string who, string bone, float time)
    {
        var key = bone == PoseEdit.Root ? PoseEdit.Root : FeedbackFile.BoneKey(bone);
        return file.Edits.LastOrDefault(e => e.Who == who && SameBone(e.Bone, key) && Normalize(e).Holds(time));
    }

    private static bool SameBone(string a, string b) =>
        a == b || (BoneNames.TryResolve(a, out var x) && BoneNames.TryResolve(b, out var y) && x == y);

    /// <summary>Root rotation (<see cref="Channel.Rotation"/>) or a bone delta (skeleton name) at time t; identity if never set.</summary>
    public static Quaternion SampleRotation(IReadOnlyList<Keyframe> keyframes, Func<Keyframe, JudokaPose> pose, string channel, float t)
    {
        Func<JudokaPose, Vec3?> get = channel == Channel.Rotation ? p => p.Rotation : p => BoneValue(p, channel);
        var keys = Keys(keyframes, pose, get);
        if (keys.Count == 0)
            return Quaternion.Identity;
        var (a, b, w) = Bracket(keys, t);
        return Quaternion.Slerp(Rotations.FromEuler(a), Rotations.FromEuler(b), w);
    }

    public static Vec3? SamplePosition(IReadOnlyList<Keyframe> keyframes, Func<Keyframe, JudokaPose> pose, float t)
    {
        var keys = Keys(keyframes, pose, p => p.Position);
        if (keys.Count == 0)
            return null;
        var (a, b, w) = Bracket(keys, t);
        return a.Plus(b.Minus(a).Times(w));
    }

    /// <summary>A bone's value at a keyframe by skeleton name, whatever spelling the YAML key uses.</summary>
    public static Vec3? BoneValue(JudokaPose pose, string skeletonBone)
    {
        foreach (var (name, value) in pose.Bones)
            if (BoneNames.TryResolve(name, out var bone) && bone == skeletonBone)
                return value;
        return null;
    }

    private static void SetRotation(JudokaPose pose, string channel, Vec3 value)
    {
        if (channel == Channel.Rotation)
        {
            pose.Rotation = value;
            return;
        }
        var key = pose.Bones.Keys.FirstOrDefault(n => BoneNames.TryResolve(n, out var b) && b == channel)
                  ?? FeedbackFile.BoneKey(channel);
        pose.Bones[key] = value;
    }

    private static List<(float Time, Vec3 Value)> Keys(IReadOnlyList<Keyframe> keyframes, Func<Keyframe, JudokaPose> pose,
                                                       Func<JudokaPose, Vec3?> get)
    {
        var keys = new List<(float, Vec3)>();
        foreach (var k in keyframes)
            if (get(pose(k)) is { } v)
                keys.Add((k.Time, v));
        return keys;
    }

    /// <summary>The keys around t and the blend weight (the first/last key is held outside them), as KeyTrack does.</summary>
    private static (Vec3 A, Vec3 B, float W) Bracket(List<(float Time, Vec3 Value)> keys, float t)
    {
        if (t <= keys[0].Time)
            return (keys[0].Value, keys[0].Value, 0);
        for (var i = 1; i < keys.Count; i++)
            if (t <= keys[i].Time)
            {
                var (t0, v0) = keys[i - 1];
                var (t1, v1) = keys[i];
                return (v0, v1, (t - t0) / (t1 - t0));
            }
        return (keys[^1].Value, keys[^1].Value, 0);
    }

    private static JudokaPose SamplePose(IReadOnlyList<Keyframe> keyframes, Func<Keyframe, JudokaPose> pose, float t)
    {
        var sampled = new JudokaPose { Position = SamplePosition(keyframes, pose, t) };
        if (Keys(keyframes, pose, p => p.Rotation).Count > 0)
            sampled.Rotation = Rotations.ToEuler(SampleRotation(keyframes, pose, Channel.Rotation, t));
        var bones = keyframes.SelectMany(k => pose(k).Bones.Keys).Distinct()
            .Select(n => BoneNames.TryResolve(n, out var b) ? (Key: n, Bone: b) : default)
            .Where(b => b.Bone is not null).DistinctBy(b => b.Bone);
        foreach (var (key, bone) in bones)
            sampled.Bones[key] = Rotations.ToEuler(SampleRotation(keyframes, pose, bone, t));
        return sampled;
    }

    private static Technique Clone(Technique t) => new()
    {
        TechniqueName = t.TechniqueName, DutchName = t.DutchName, WazaGroup = t.WazaGroup, Category = t.Category,
        Code = t.Code, Difficulty = t.Difficulty, KyuGrade = t.KyuGrade,
        BeltColor = new BeltColor { Name = t.BeltColor.Name, Hex = t.BeltColor.Hex },
        U18 = t.U18, Source = t.Source, DurationSeconds = t.DurationSeconds,
        Keyframes = t.Keyframes.Select(k => new Keyframe
        {
            Time = k.Time, Phase = k.Phase, Inbetween = k.Inbetween, Description = k.Description,
            Tori = Clone(k.Tori), Uki = Clone(k.Uki),
        }).ToList(),
    };

    private static JudokaPose Clone(JudokaPose p) => new()
    {
        Position = p.Position, Rotation = p.Rotation, Bones = new Dictionary<string, Vec3>(p.Bones),
    };

    private static Vec3 Plus(this Vec3 a, Vec3 b) => new(a.X + b.X, a.Y + b.Y, a.Z + b.Z);

    private static Vec3 Minus(this Vec3 a, Vec3 b) => new(a.X - b.X, a.Y - b.Y, a.Z - b.Z);

    private static Vec3 Times(this Vec3 a, float s) => new(a.X * s, a.Y * s, a.Z * s);
}

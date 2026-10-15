using System;
using System.Collections.Generic;
using System.Linq;
using JudoVisualizer.Data;

namespace JudoVisualizer.Playback;

/// <summary>Animation tracks of one judoka. A track is null/absent when no keyframe sets that value.</summary>
public sealed class JudokaTracks
{
    private JudokaTracks(KeyTrack? position, KeyTrack? rotation, IReadOnlyDictionary<string, KeyTrack> bones)
    {
        Position = position;
        Rotation = rotation;
        Bones = bones;
    }

    public KeyTrack? Position { get; }

    /// <summary>Root rotation, Euler XYZ degrees.</summary>
    public KeyTrack? Rotation { get; }

    /// <summary>Bone rotation tracks keyed by skeleton bone name (e.g. "RightShoulder").</summary>
    public IReadOnlyDictionary<string, KeyTrack> Bones { get; }

    internal static JudokaTracks Build(IReadOnlyList<Keyframe> keyframes, Func<Keyframe, JudokaPose> pose)
    {
        var position = new List<(float, Vec3)>();
        var rotation = new List<(float, Vec3)>();
        var bones = new Dictionary<string, List<(float, Vec3)>>();
        foreach (var k in keyframes)
        {
            var p = pose(k);
            if (p.Position is { } pos)
                position.Add((k.Time, pos));
            if (p.Rotation is { } rot)
                rotation.Add((k.Time, rot));
            foreach (var (name, value) in p.Bones)
            {
                if (!BoneNames.TryResolve(name, out var bone))
                    continue; // rejected by TechniqueValidator; ignore defensively
                if (!bones.TryGetValue(bone, out var keys))
                    bones[bone] = keys = [];
                keys.Add((k.Time, value));
            }
        }

        return new JudokaTracks(
            position.Count > 0 ? new KeyTrack(position) : null,
            rotation.Count > 0 ? new KeyTrack(rotation) : null,
            bones.ToDictionary(b => b.Key, b => new KeyTrack(b.Value)));
    }
}

/// <summary>
/// The stretch of time in which an authored keyframe's phase is shown: from halfway after the
/// previous authored keyframe to halfway before the next one (the first starts at 0, the last ends
/// at the duration). In-between keyframes have no segment. <see cref="KeyframeIndex"/> indexes
/// <see cref="Technique.Keyframes"/>.
/// </summary>
public readonly record struct PhaseSegment(int KeyframeIndex, float Start, float End, string Phase);

/// <summary>A <see cref="Data.Technique"/> converted into per-value animation tracks.</summary>
public sealed class TechniqueTracks
{
    private const float Epsilon = 1e-4f;

    private TechniqueTracks(Technique technique)
    {
        Technique = technique;
        Tori = JudokaTracks.Build(technique.Keyframes, k => k.Tori);
        Uki = JudokaTracks.Build(technique.Keyframes, k => k.Uki);

        var authored = technique.Keyframes.Select((k, i) => (Keyframe: k, Index: i)).Where(k => !k.Keyframe.Inbetween).ToList();
        Phases = authored.Select((k, i) => new PhaseSegment(k.Index,
            i == 0 ? 0 : (authored[i - 1].Keyframe.Time + k.Keyframe.Time) / 2,
            i == authored.Count - 1 ? technique.DurationSeconds : (k.Keyframe.Time + authored[i + 1].Keyframe.Time) / 2,
            k.Keyframe.Phase)).ToList();
        AuthoredTimes = authored.Select(k => k.Keyframe.Time).ToList();
    }

    public Technique Technique { get; }
    public JudokaTracks Tori { get; }
    public JudokaTracks Uki { get; }
    public float Duration => Technique.DurationSeconds;

    /// <summary>One segment per authored keyframe, in order, covering 0..duration.</summary>
    public IReadOnlyList<PhaseSegment> Phases { get; }

    /// <summary>Times of the authored (not in-between) keyframes: timeline ticks and stepping targets.</summary>
    public IReadOnlyList<float> AuthoredTimes { get; }

    /// <param name="technique">A validated technique (see <see cref="TechniqueValidator"/>).</param>
    public static TechniqueTracks Build(Technique technique) => new(technique);

    /// <summary>
    /// Index (in <see cref="Technique.Keyframes"/>) of the authored keyframe nearest in time, whose
    /// phase is the one shown at <paramref name="time"/>.
    /// </summary>
    public int KeyframeIndexAt(float time)
    {
        for (var i = Phases.Count - 1; i > 0; i--)
            if (time >= Phases[i].Start)
                return Phases[i].KeyframeIndex;
        return Phases[0].KeyframeIndex;
    }

    /// <summary>Time of the first authored keyframe after <paramref name="time"/>, or null if there is none.</summary>
    public float? NextKeyframeTime(float time) =>
        AuthoredTimes.Select(t => (float?)t).FirstOrDefault(t => t > time + Epsilon);

    /// <summary>Time of the last authored keyframe before <paramref name="time"/>, or null if there is none.</summary>
    public float? PreviousKeyframeTime(float time) =>
        AuthoredTimes.Select(t => (float?)t).LastOrDefault(t => t < time - Epsilon);
}

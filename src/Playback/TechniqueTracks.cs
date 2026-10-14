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

/// <summary>A <see cref="Data.Technique"/> converted into per-value animation tracks.</summary>
public sealed class TechniqueTracks
{
    private TechniqueTracks(Technique technique)
    {
        Technique = technique;
        Tori = JudokaTracks.Build(technique.Keyframes, k => k.Tori);
        Uki = JudokaTracks.Build(technique.Keyframes, k => k.Uki);
    }

    public Technique Technique { get; }
    public JudokaTracks Tori { get; }
    public JudokaTracks Uki { get; }
    public float Duration => Technique.DurationSeconds;

    /// <param name="technique">A validated technique (see <see cref="TechniqueValidator"/>).</param>
    public static TechniqueTracks Build(Technique technique) => new(technique);

    /// <summary>Index of the keyframe whose phase is active at <paramref name="time"/> (the last one at or before it).</summary>
    public int KeyframeIndexAt(float time)
    {
        var keyframes = Technique.Keyframes;
        var index = 0;
        for (var i = 1; i < keyframes.Count && keyframes[i].Time <= time; i++)
            index = i;
        return index;
    }
}

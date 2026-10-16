using System.Collections.Generic;
using System.Linq;
using Godot;
using JudoVisualizer.Data;

namespace JudoVisualizer.Playback;

/// <summary>
/// Drives one judoka model (root <see cref="Node3D"/> + its <see cref="Skeleton3D"/>) from its tracks.
/// Bone deltas rotate about the character's own axes in Godot's convention (X = character's right,
/// Y = up, -Z = facing direction; so spine [-45, 0, 0] bows forward) on top of the rest pose;
/// children follow their parents.
/// </summary>
internal sealed class JudokaRig
{
    // The models face +Z (glTF/Godot model front); bone deltas are authored for a -Z-facing character.
    private static readonly Quaternion AuthoringFrame = new(Vector3.Up, Mathf.Pi);

    private readonly Node3D _root;
    private readonly JudokaTracks _tracks;
    private readonly Skeleton3D? _skeleton;
    private readonly Vector3[] _positions;
    private readonly Quaternion[] _rotations;
    private readonly List<BoneBinding> _bones = [];

    private sealed record BoneBinding(int Index, KeyTrack Track, Quaternion[] Deltas,
                                      Quaternion RestLocal, Quaternion CharacterRest);

    public JudokaRig(Node3D root, JudokaTracks tracks)
    {
        _root = root;
        _tracks = tracks;
        _positions = tracks.Position?.Values.Select(ToVector3).ToArray() ?? [];
        _rotations = tracks.Rotation?.Values.Select(ToQuaternion).ToArray() ?? [];

        _skeleton = FindSkeleton(root);
        if (_skeleton is null)
        {
            if (tracks.Bones.Count > 0)
                GD.PushError($"{root.Name}: no Skeleton3D found; bone animation is ignored.");
            return;
        }

        _skeleton.ResetBonePoses(); // bones without a track stay at rest
        foreach (var (name, track) in tracks.Bones)
        {
            var index = _skeleton.FindBone(name);
            if (index < 0)
            {
                GD.PushWarning($"{root.Name}: skeleton has no bone '{name}'; its track is ignored.");
                continue;
            }
            _bones.Add(new BoneBinding(index, track, track.Values.Select(ToQuaternion).ToArray(),
                _skeleton.GetBoneRest(index).Basis.GetRotationQuaternion(),
                AuthoringFrame.Inverse() * _skeleton.GetBoneGlobalRest(index).Basis.GetRotationQuaternion()));
        }
    }

    /// <summary>The model's skeleton: the root itself or its first Skeleton3D descendant.</summary>
    public static Skeleton3D? FindSkeleton(Node3D model) =>
        model as Skeleton3D
        ?? model.FindChildren("*", nameof(Skeleton3D), true, false).OfType<Skeleton3D>().FirstOrDefault();

    /// <summary>
    /// The bones of <paramref name="model"/> as world-space line segments (origin to the child bone's origin;
    /// head, hands and feet get a short stub), for picking with the mouse. Bone names are skeleton names.
    /// </summary>
    internal static List<(string Bone, Vector3 A, Vector3 B)> BoneSegments(Node3D model)
    {
        var segments = new List<(string, Vector3, Vector3)>();
        var skeleton = FindSkeleton(model);
        if (skeleton is null)
            return segments;

        var known = new Dictionary<int, string>();
        for (var i = 0; i < skeleton.GetBoneCount(); i++)
            if (BoneNames.Skeleton.Contains(skeleton.GetBoneName(i)))
                known[i] = skeleton.GetBoneName(i);

        Vector3 Origin(int bone) => skeleton.GlobalTransform * skeleton.GetBoneGlobalPose(bone).Origin;
        int Parent(int bone)
        {
            for (var p = skeleton.GetBoneParent(bone); p >= 0; p = skeleton.GetBoneParent(p))
                if (known.ContainsKey(p))
                    return p;
            return -1;
        }

        var hasChild = new HashSet<int>();
        foreach (var bone in known.Keys)
            if (Parent(bone) is >= 0 and var parent)
            {
                hasChild.Add(parent);
                segments.Add((known[parent], Origin(parent), Origin(bone)));
            }

        var forward = (skeleton.GlobalTransform.Basis * Vector3.Back).Normalized(); // models face +Z at rest
        foreach (var (bone, name) in known.Where(k => !hasChild.Contains(k.Key)))
        {
            var from = Origin(bone);
            var parent = Parent(bone);
            var along = parent >= 0 ? (from - Origin(parent)).Normalized() : Vector3.Up;
            var tip = name.EndsWith("Foot") ? forward * 0.18f : along * (name == "Head" ? 0.22f : 0.09f);
            segments.Add((name, from, from + tip));
        }
        return segments;
    }

    public void Apply(float time)
    {
        if (_tracks.Position is { } position)
        {
            var s = position.Sample(time);
            _root.Position = _positions[s.From].Lerp(_positions[s.To], s.Weight);
        }
        if (_tracks.Rotation is { } rotation)
        {
            var s = rotation.Sample(time);
            _root.Quaternion = _rotations[s.From].Slerp(_rotations[s.To], s.Weight);
        }
        foreach (var bone in _bones)
        {
            var s = bone.Track.Sample(time);
            var delta = bone.Deltas[s.From].Slerp(bone.Deltas[s.To], s.Weight);
            // Express the character-frame delta in the bone's local frame, then apply it after the rest.
            var local = bone.CharacterRest.Inverse() * delta * bone.CharacterRest;
            _skeleton!.SetBonePoseRotation(bone.Index, bone.RestLocal * local);
        }
    }

    private static Vector3 ToVector3(Vec3 v) => new(v.X, v.Y, v.Z);

    private static Quaternion ToQuaternion(Vec3 degrees) =>
        Basis.FromEuler(new Vector3(Mathf.DegToRad(degrees.X), Mathf.DegToRad(degrees.Y), Mathf.DegToRad(degrees.Z)),
                        EulerOrder.Xyz).GetRotationQuaternion();
}

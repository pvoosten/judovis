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

        _skeleton = root as Skeleton3D
                    ?? root.FindChildren("*", nameof(Skeleton3D), true, false).OfType<Skeleton3D>().FirstOrDefault();
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

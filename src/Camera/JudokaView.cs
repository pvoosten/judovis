using Godot;
using JudoVisualizer.Playback;

namespace JudoVisualizer.Camera;

/// <summary>Reads camera-relevant points from a judoka model: hips position and an eye transform.</summary>
internal sealed class JudokaView
{
    // Eyes relative to the Head bone origin (top of the neck), in the character's rest axes
    // (+Y up, +Z facing): a little up and just in front of the face so the own head stays out of view.
    private static readonly Vector3 EyeOffset = new(0, 0.12f, 0.115f);

    private readonly Skeleton3D _skeleton;
    private readonly int _head;
    private readonly int _hips;
    private readonly Basis _headRestInverse;

    private JudokaView(Skeleton3D skeleton, int head, int hips)
    {
        _skeleton = skeleton;
        _head = head;
        _hips = hips;
        _headRestInverse = skeleton.GetBoneGlobalRest(head).Basis.Orthonormalized().Inverse();
    }

    /// <returns>null (with an error logged) if the model has no skeleton with Head and Hips bones.</returns>
    public static JudokaView? Bind(Node3D? model, string role)
    {
        var skeleton = model is null ? null : JudokaRig.FindSkeleton(model);
        var head = skeleton?.FindBone("Head") ?? -1;
        var hips = skeleton?.FindBone("Hips") ?? -1;
        if (skeleton is null || head < 0 || hips < 0)
        {
            GD.PushError($"CameraManager: {role} has no skeleton with Head and Hips bones.");
            return null;
        }
        return new JudokaView(skeleton, head, hips);
    }

    public Vector3 HipsPosition => _skeleton.GlobalTransform * _skeleton.GetBoneGlobalPose(_hips).Origin;

    /// <summary>World transform of the judoka's eyes, looking where the head faces (camera -Z forward).</summary>
    public Transform3D Eyes()
    {
        var pose = _skeleton.GetBoneGlobalPose(_head);
        // Head rotation relative to rest, in skeleton space; the model faces +Z at rest.
        var turn = pose.Basis.Orthonormalized() * _headRestInverse;
        var forward = turn * Vector3.Back;
        var up = turn * Vector3.Up;
        var eyes = new Transform3D(Basis.LookingAt(forward, up), pose.Origin + turn * EyeOffset);
        return _skeleton.GlobalTransform * eyes;
    }
}

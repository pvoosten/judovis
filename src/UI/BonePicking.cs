using System.Collections.Generic;
using System.Linq;
using Godot;
using JudoVisualizer.Playback;

namespace JudoVisualizer.UI;

/// <summary>Mouse picking of a bone of Tori or Uki (dev tools F2 pose feedback and F3 pose editor).</summary>
internal static class BonePicking
{
    private const float PickMetres = 0.12f;

    /// <summary>The bones of "tori" or "uki" as world-space segments (skeleton bone names).</summary>
    public static IEnumerable<(string Who, string Bone, Vector3 A, Vector3 B)> Segments(JudoTechniquePlayer player, string who)
    {
        var model = who == "tori" ? player.Tori : player.Uki;
        return model is null ? [] : JudokaRig.BoneSegments(model).Select(s => (who, s.Bone, s.A, s.B));
    }

    /// <summary>The bone nearest the mouse ray, or null when no bone is close enough.</summary>
    public static BoneHit? At(JudoTechniquePlayer player, Camera3D camera, Vector2 mouse)
    {
        var origin = camera.ProjectRayOrigin(mouse);
        var direction = camera.ProjectRayNormal(mouse);
        var segments = Segments(player, "tori").Concat(Segments(player, "uki"))
            .Select(s => new BoneSegment(s.Who, s.Bone, ToNumerics(s.A), ToNumerics(s.B)));
        return BonePicker.Pick(ToNumerics(origin), ToNumerics(direction), segments, PickMetres);
    }

    private static System.Numerics.Vector3 ToNumerics(Vector3 v) => new(v.X, v.Y, v.Z);
}

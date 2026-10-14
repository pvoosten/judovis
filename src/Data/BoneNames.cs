using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using System.Linq;

namespace JudoVisualizer.Data;

/// <summary>
/// Maps YAML bone keys ("right_shoulder", "left_up_leg") to the skeleton bone names of the
/// Tori/Uki models ("RightShoulder", "LeftUpLeg"). Matching ignores case and underscores.
/// </summary>
public static class BoneNames
{
    /// <summary>Deforming bones of the judoka skeleton (Godot humanoid naming).</summary>
    public static readonly IReadOnlyList<string> Skeleton =
    [
        "Hips", "Spine", "Chest", "Neck", "Head",
        "LeftShoulder", "LeftArm", "LeftForearm", "LeftHand",
        "RightShoulder", "RightArm", "RightForearm", "RightHand",
        "LeftUpLeg", "LeftLeg", "LeftFoot",
        "RightUpLeg", "RightLeg", "RightFoot",
    ];

    private static readonly Dictionary<string, string> ByKey = Skeleton.ToDictionary(Normalize);

    public static bool TryResolve(string yamlName, [NotNullWhen(true)] out string? skeletonName) =>
        ByKey.TryGetValue(Normalize(yamlName), out skeletonName);

    private static string Normalize(string name) => name.Replace("_", "").ToLowerInvariant();
}

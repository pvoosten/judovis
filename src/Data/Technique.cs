using System.Collections.Generic;
using YamlDotNet.Serialization;

namespace JudoVisualizer.Data;

/// <summary>A judo technique as stored in <c>data/techniques/*.yaml</c> (snake_case keys).</summary>
public sealed class Technique
{
    private BeltColor _beltColor = new();
    private List<Keyframe> _keyframes = [];

    public string TechniqueName { get; set; } = "";

    /// <summary>Dutch description of the technique, e.g. "Grote buitenwaartse maaiworp".</summary>
    public string DutchName { get; set; } = "";

    /// <summary>One of <see cref="WazaGroups"/>, e.g. "nage_waza".</summary>
    public string WazaGroup { get; set; } = "";

    /// <summary>Sub-group, e.g. "Te-waza (Handworp)", "Osaekomi-waza (Houdgreep)".</summary>
    public string Category { get; set; } = "";

    /// <summary>
    /// Reference code: waza letter (N nage, O osaekomi, S shime, K kansetsu), grade (kyu, or D for
    /// Dan / extra) and number, e.g. "N5-1".
    /// </summary>
    public string Code { get; set; } = "";

    public string Difficulty { get; set; } = "";

    /// <summary>
    /// 1-6: 6 = 6th kyu (white belt) ... 1 = 1st kyu (brown belt); 0 = Dan / extra.
    /// See <see cref="KyuGrades"/>.
    /// </summary>
    public int KyuGrade { get; set; }

    public BeltColor BeltColor { get => _beltColor; set => _beltColor = value ?? new(); }

    /// <summary>Only taught from U18 (shime- and kansetsu-waza in the VJF leerlijn).</summary>
    public bool U18 { get; set; }

    /// <summary>Where the grade comes from, e.g. "VJF leerlijn 2015, geel".</summary>
    public string Source { get; set; } = "";

    /// <summary>Length of the animation; 0 when the technique is not animated yet.</summary>
    public float DurationSeconds { get; set; }

    /// <summary>Keyframes in ascending <see cref="Keyframe.Time"/> order; empty = not animated yet.</summary>
    public List<Keyframe> Keyframes { get => _keyframes; set => _keyframes = value ?? []; }

    /// <summary>True when the technique has keyframes (catalogue entries without animation do not).</summary>
    [YamlIgnore]
    public bool IsAnimated => _keyframes.Count > 0;
}

/// <summary>Allowed values of <see cref="Technique.WazaGroup"/>.</summary>
public static class WazaGroups
{
    public const string Nage = "nage_waza";
    public const string Osaekomi = "osaekomi_waza";
    public const string Shime = "shime_waza";
    public const string Kansetsu = "kansetsu_waza";

    public static readonly IReadOnlyList<string> All = [Nage, Osaekomi, Shime, Kansetsu];
}

public sealed class BeltColor
{
    /// <summary>Display name, e.g. "Gele band".</summary>
    public string Name { get; set; } = "";

    /// <summary>Colour as "#RRGGBB".</summary>
    public string Hex { get; set; } = "";
}

public sealed class Keyframe
{
    private JudokaPose _tori = new();
    private JudokaPose _uki = new();

    /// <summary>Seconds from the start of the technique.</summary>
    public float Time { get; set; }

    /// <summary>e.g. "Kuzushi", "Tsukuri", "Kake".</summary>
    public string Phase { get; set; } = "";

    public string Description { get; set; } = "";

    public JudokaPose Tori { get => _tori; set => _tori = value ?? new(); }

    public JudokaPose Uki { get => _uki; set => _uki = value ?? new(); }
}

/// <summary>Pose of one judoka at a keyframe.</summary>
public sealed class JudokaPose
{
    private Dictionary<string, Vec3> _bones = [];

    /// <summary>Root position in metres (Godot, Y-up). Null = not keyed here: interpolated from neighbours.</summary>
    public Vec3? Position { get; set; }

    /// <summary>Root rotation, Euler XYZ degrees. Null = not keyed here: interpolated from neighbours.</summary>
    public Vec3? Rotation { get; set; }

    /// <summary>
    /// Bone rotations (Euler XYZ degrees about the character's axes, on top of the T-pose rest),
    /// keyed by YAML bone name such as "right_shoulder". Resolve to skeleton names with
    /// <see cref="BoneNames"/>. Bones not listed here are interpolated from neighbouring keyframes.
    /// </summary>
    public Dictionary<string, Vec3> Bones { get => _bones; set => _bones = value ?? []; }
}

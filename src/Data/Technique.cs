using System.Collections.Generic;

namespace JudoVisualizer.Data;

/// <summary>A judo technique as stored in <c>data/techniques/*.yaml</c> (snake_case keys).</summary>
public sealed class Technique
{
    private BeltColor _beltColor = new();
    private List<Keyframe> _keyframes = [];

    public string TechniqueName { get; set; } = "";

    /// <summary>Technique group, e.g. "Te-waza", "Koshi-waza".</summary>
    public string Category { get; set; } = "";

    /// <summary>Short reference code, e.g. "T1".</summary>
    public string Code { get; set; } = "";

    public string Difficulty { get; set; } = "";

    /// <summary>1-6: 6 = 6th kyu (white belt) ... 1 = 1st kyu (brown belt). See <see cref="KyuGrades"/>.</summary>
    public int KyuGrade { get; set; }

    public BeltColor BeltColor { get => _beltColor; set => _beltColor = value ?? new(); }

    public float DurationSeconds { get; set; }

    /// <summary>Keyframes in ascending <see cref="Keyframe.Time"/> order.</summary>
    public List<Keyframe> Keyframes { get => _keyframes; set => _keyframes = value ?? []; }
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

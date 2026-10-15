using System;
using System.Collections.Generic;
using System.Linq;

namespace JudoVisualizer.Data;

public sealed record KyuGradeInfo(int Grade, string BeltName, string Hex);

/// <summary>Kyu grade to belt colour mapping (6th kyu = beginner; 0 = Dan / extra).</summary>
public static class KyuGrades
{
    /// <summary>Grade of techniques outside the kyu programme (Kodokan waza not in the VJF leerlijn).</summary>
    public const int DanExtra = 0;

    /// <summary>All grades, from beginner (6th kyu) to most advanced (1st kyu), then Dan / extra.</summary>
    public static readonly IReadOnlyList<KyuGradeInfo> All =
    [
        new(6, "White Belt", "#FFFFFF"),
        new(5, "Yellow Belt", "#FFD700"),
        new(4, "Orange Belt", "#FF8C00"),
        new(3, "Green Belt", "#228B22"),
        new(2, "Blue Belt", "#1E90FF"),
        new(1, "Brown Belt", "#8B4513"),
        new(DanExtra, "Black Belt", "#000000"),
    ];

    public static bool IsValid(int grade) => grade is >= DanExtra and <= 6;

    public static KyuGradeInfo Get(int grade) =>
        All.FirstOrDefault(k => k.Grade == grade)
        ?? throw new ArgumentOutOfRangeException(nameof(grade), grade, "Kyu grade must be 0-6.");
}

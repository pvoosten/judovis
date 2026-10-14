using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace JudoVisualizer.Data;

/// <summary>Semantic checks on a parsed technique. Returns human-readable errors; empty = valid.</summary>
public static class TechniqueValidator
{
    private static readonly Regex HexColor = new("^#[0-9A-Fa-f]{6}$");

    public static List<string> Validate(Technique t)
    {
        var errors = new List<string>();

        if (string.IsNullOrWhiteSpace(t.TechniqueName))
            errors.Add("technique_name is required.");

        if (!KyuGrades.IsValid(t.KyuGrade))
            errors.Add($"kyu_grade must be 1-6, got {t.KyuGrade}.");

        if (!HexColor.IsMatch(t.BeltColor.Hex))
            errors.Add($"belt_color.hex must look like #RRGGBB, got '{t.BeltColor.Hex}'.");
        else if (KyuGrades.IsValid(t.KyuGrade)
                 && !string.Equals(t.BeltColor.Hex, KyuGrades.Get(t.KyuGrade).Hex, StringComparison.OrdinalIgnoreCase))
            errors.Add($"belt_color.hex {t.BeltColor.Hex} does not match kyu_grade {t.KyuGrade} ({KyuGrades.Get(t.KyuGrade).Hex}).");

        if (t.DurationSeconds <= 0)
            errors.Add($"duration_seconds must be > 0, got {t.DurationSeconds}.");

        if (t.Keyframes.Count == 0)
            errors.Add("at least one keyframe is required.");

        for (var i = 0; i < t.Keyframes.Count; i++)
        {
            var k = t.Keyframes[i];
            var where = $"keyframes[{i}] (time {k.Time})";
            if (k.Time < 0 || k.Time > t.DurationSeconds)
                errors.Add($"{where}: time must be within 0..duration_seconds ({t.DurationSeconds}).");
            if (i > 0 && k.Time <= t.Keyframes[i - 1].Time)
                errors.Add($"{where}: times must be strictly increasing.");
            CheckBones(errors, $"{where}.tori", k.Tori);
            CheckBones(errors, $"{where}.uki", k.Uki);
        }

        return errors;
    }

    private static void CheckBones(List<string> errors, string where, JudokaPose pose)
    {
        foreach (var name in pose.Bones.Keys)
            if (!BoneNames.TryResolve(name, out _))
                errors.Add($"{where}: unknown bone '{name}'.");
    }
}

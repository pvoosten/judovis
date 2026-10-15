using System;
using System.Collections.Generic;
using System.Linq;
using JudoVisualizer.Data;

namespace JudoVisualizer.UI;

/// <summary>Techniques of one kyu grade, sorted by name.</summary>
public sealed record KyuGroup(KyuGradeInfo Grade, IReadOnlyList<Technique> Techniques);

/// <summary>Groups and filters techniques for the browser. Engine-independent (unit tested).</summary>
public static class TechniqueCatalog
{
    /// <summary>
    /// Non-empty groups from beginner (6th kyu) to advanced (1st kyu).
    /// </summary>
    /// <param name="kyuFilter">Only this grade, or null for all grades.</param>
    public static IReadOnlyList<KyuGroup> Group(IEnumerable<Technique> techniques, int? kyuFilter = null)
    {
        var list = techniques.ToList();
        return KyuGrades.All
            .Where(g => kyuFilter is null || g.Grade == kyuFilter)
            .Select(g => new KyuGroup(g, list.Where(t => t.KyuGrade == g.Grade)
                .OrderBy(t => t.TechniqueName, StringComparer.CurrentCultureIgnoreCase).ToList()))
            .Where(g => g.Techniques.Count > 0)
            .ToList();
    }

    /// <summary>Header text for a grade, e.g. "5th Kyu - Yellow Belt".</summary>
    public static string Title(KyuGradeInfo grade) => $"{grade.Grade}{Ordinal(grade.Grade)} Kyu - {grade.BeltName}";

    /// <summary>Short phase label for tight spaces: "Kake (Worp)" -> "Kake".</summary>
    public static string ShortPhase(string phase)
    {
        var i = phase.IndexOf(" (", StringComparison.Ordinal);
        return i > 0 ? phase[..i] : phase;
    }

    private static string Ordinal(int n) => n switch { 1 => "st", 2 => "nd", 3 => "rd", _ => "th" };
}

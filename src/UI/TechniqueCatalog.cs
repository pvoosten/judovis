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
    /// <summary>Label shown next to techniques taught only from U18 (shime- and kansetsu-waza).</summary>
    public const string U18Tag = "U18+";

    public const string NotAnimated = "Nog geen animatie";

    /// <summary>
    /// Non-empty groups from beginner (6th kyu) to advanced (1st kyu), then Dan / extra.
    /// </summary>
    /// <param name="kyuFilter">Only this grade, or null for all grades.</param>
    /// <param name="includeU18">Also list techniques taught only from U18.</param>
    public static IReadOnlyList<KyuGroup> Group(IEnumerable<Technique> techniques, int? kyuFilter = null,
                                                bool includeU18 = true)
    {
        var list = techniques.Where(t => includeU18 || !t.U18).ToList();
        return KyuGrades.All
            .Where(g => kyuFilter is null || g.Grade == kyuFilter)
            .Select(g => new KyuGroup(g, list.Where(t => t.KyuGrade == g.Grade)
                .OrderBy(t => t.TechniqueName, StringComparer.CurrentCultureIgnoreCase).ToList()))
            .Where(g => g.Techniques.Count > 0)
            .ToList();
    }

    /// <summary>Header text for a grade, e.g. "5th Kyu - Yellow Belt", or "Dan / extra".</summary>
    public static string Title(KyuGradeInfo grade) =>
        grade.Grade == KyuGrades.DanExtra ? "Dan / extra" : $"{grade.Grade}{Ordinal(grade.Grade)} Kyu - {grade.BeltName}";

    /// <summary>Text of a browser entry: the name, tagged "U18+" when applicable.</summary>
    public static string EntryLabel(Technique t) => t.U18 ? $"{t.TechniqueName}  {U18Tag}" : t.TechniqueName;

    /// <summary>
    /// One line about the technique for tooltips and the caption,
    /// e.g. "N5-2 · Ashi-waza (Beenworp) · 5th Kyu - Yellow Belt · VJF leerlijn 2015, geel".
    /// </summary>
    public static string Details(Technique t)
    {
        var parts = new List<string> { t.Code, t.Category };
        if (KyuGrades.IsValid(t.KyuGrade))
            parts.Add(Title(KyuGrades.Get(t.KyuGrade)));
        if (t.U18)
            parts.Add(U18Tag);
        parts.Add(t.Source);
        return string.Join(" · ", parts.Where(p => !string.IsNullOrWhiteSpace(p)));
    }

    /// <summary>Short phase label for tight spaces: "Kake (Worp)" -> "Kake".</summary>
    public static string ShortPhase(string phase)
    {
        var i = phase.IndexOf(" (", StringComparison.Ordinal);
        return i > 0 ? phase[..i] : phase;
    }

    private static string Ordinal(int n) => n switch { 1 => "st", 2 => "nd", 3 => "rd", _ => "th" };
}

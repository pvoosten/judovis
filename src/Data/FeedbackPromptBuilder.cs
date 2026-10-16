using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace JudoVisualizer.Data;

/// <summary>
/// Turns the open comments of one technique into a single compact prompt for Claude Code:
/// grouped by the nearest authored keyframe ("kf3" = third authored keyframe, in-betweens not counted).
/// </summary>
public static class FeedbackPromptBuilder
{
    /// <summary>A comment this close (seconds) to an authored keyframe belongs to that keyframe.</summary>
    public const float SnapSeconds = 0.05f;

    private static readonly Regex Def = new(@"^\s*def\s+(\w+)\s*\(", RegexOptions.Multiline);

    /// <returns>The prompt, or "" when there is no open, non-empty comment.</returns>
    public static string Build(Technique technique, IEnumerable<FeedbackEntry> entries, string? scriptText = null)
    {
        var open = entries.Where(e => e.IsOpen && !string.IsNullOrWhiteSpace(e.Text)).ToList();
        if (open.Count == 0)
            return "";

        var slug = FeedbackFile.Slug(technique.TechniqueName);
        var authored = technique.Keyframes.Where(k => !k.Inbetween).ToList();
        var functions = scriptText is null ? [] : Def.Matches(scriptText).Select(m => m.Groups[1].Value).ToList();

        var groups = open
            .Select(e => (Entry: e, Place: Locate(e.Time, authored)))
            .GroupBy(x => x.Place.Key)
            .OrderBy(g => g.First().Place.Order)
            .ToList();

        var sb = new StringBuilder();
        sb.Append(slug).Append(" (tools/blender/techniques/").Append(slug)
          .AppendLine(".py). Fix these in the pose functions, rerun --draft, then the full run + dotnet test; change nothing else.");

        foreach (var group in groups)
        {
            var place = group.First().Place;
            sb.AppendLine(Heading(place, authored, functions));
            foreach (var line in Lines(group.Select(x => x.Entry), place.Exact))
                sb.AppendLine(line);
        }
        sb.AppendLine("Leave the other keyframes alone.");
        return sb.ToString();
    }

    private sealed record Place(string Key, double Order, int Before, int After, bool Exact);

    /// <summary>Nearest authored keyframe (when within <see cref="SnapSeconds"/>) or the pair around the time.</summary>
    private static Place Locate(float time, List<Keyframe> authored)
    {
        if (authored.Count == 0)
            return new Place("none", 0, -1, -1, false);

        var nearest = 0;
        for (var i = 1; i < authored.Count; i++)
            if (Math.Abs(authored[i].Time - time) < Math.Abs(authored[nearest].Time - time))
                nearest = i;
        if (Math.Abs(authored[nearest].Time - time) <= SnapSeconds)
            return new Place($"kf{nearest}", authored[nearest].Time, nearest, nearest, true);

        var after = authored.FindIndex(k => k.Time > time); // -1 = past the last keyframe
        var before = after < 0 ? authored.Count - 1 : after - 1;
        return new Place($"{before}-{after}", time, before, after, false);
    }

    private static string Heading(Place place, List<Keyframe> authored, List<string> functions)
    {
        if (place.Before < 0 && place.After < 0)
            return "No keyframes:";

        if (place.Exact)
        {
            var kf = authored[place.Before];
            var fn = FunctionFor(kf.Phase, functions);
            return $"kf{place.Before + 1} {Seconds(kf.Time, "0.00")}s {PhaseName(kf.Phase)}{(fn is null ? "" : $" ({fn})")}:";
        }

        var parts = new List<string>();
        var names = new List<string>();
        foreach (var (index, label) in new[] { (place.Before, "after"), (place.After, "before") })
        {
            if (index < 0)
                continue;
            var kf = authored[index];
            parts.Add($"kf{index + 1} ({Seconds(kf.Time, "0.##")} s)");
            if (FunctionFor(kf.Phase, functions) is { } f)
                names.Add(f);
        }
        var text = place.Before >= 0 && place.After >= 0 ? $"between {parts[0]} and {parts[1]}"
            : place.After < 0 ? $"after {parts[0]}" : $"before {parts[0]}";
        return names.Count > 0 ? $"{text} [{string.Join(", ", names.Distinct())}]:" : text + ":";
    }

    /// <summary>One line per bone: identical bones at the same place are merged, empty comments dropped.</summary>
    private static IEnumerable<string> Lines(IEnumerable<FeedbackEntry> entries, bool exact)
    {
        var merged = new List<(string Who, string Bone, List<string> Texts, List<float> Times)>();
        foreach (var e in entries.OrderBy(e => e.Who, StringComparer.Ordinal).ThenBy(e => e.Bone, StringComparer.Ordinal).ThenBy(e => e.Time))
        {
            var text = e.Text.Trim();
            var at = merged.FindIndex(m => m.Who == e.Who && m.Bone == e.Bone);
            if (at < 0)
            {
                merged.Add((e.Who, e.Bone, [text], [e.Time]));
                continue;
            }
            if (!merged[at].Texts.Contains(text))
                merged[at].Texts.Add(text);
            merged[at].Times.Add(e.Time);
        }

        foreach (var (who, bone, texts, times) in merged)
        {
            var line = $"- {who}.{bone}: {string.Join("; ", texts)}";
            if (!exact)
                line += $" ({string.Join("/", times.Distinct().Select(t => Seconds(t, "0.##") + " s"))})";
            yield return line;
        }
    }

    /// <summary>Phase without the Dutch gloss in parentheses: "Kake (Worp &amp; Handeling)" -> "Kake".</summary>
    private static string PhaseName(string phase)
    {
        var cut = phase.IndexOf('(');
        return (cut > 0 ? phase[..cut] : phase).Trim();
    }

    /// <summary>The script function named after the phase ("kake", "pose_kake"), if the script has one.</summary>
    private static string? FunctionFor(string phase, List<string> functions)
    {
        var word = Regex.Match(PhaseName(phase).ToLowerInvariant(), @"[a-z0-9]+").Value;
        if (word.Length == 0)
            return null;
        return functions.FirstOrDefault(f => f.Equals(word, StringComparison.OrdinalIgnoreCase))
            ?? functions.FirstOrDefault(f => f.Equals("pose_" + word, StringComparison.OrdinalIgnoreCase))
            ?? functions.FirstOrDefault(f => f.Equals(word + "_pose", StringComparison.OrdinalIgnoreCase));
    }

    private static string Seconds(float t, string format) => t.ToString(format, CultureInfo.InvariantCulture);
}

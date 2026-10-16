using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace JudoVisualizer.Data;

/// <summary>Allowed values of <see cref="FeedbackEntry.Status"/>.</summary>
public static class FeedbackStatus
{
    public const string Open = "open";
    public const string Done = "done";
}

/// <summary>
/// One pose comment on a technique, made while it was paused (<c>feedback/&lt;technique&gt;.yaml</c>,
/// a flat list of these). Dev tool: not part of the technique schema.
/// </summary>
public sealed class FeedbackEntry
{
    /// <summary>Technique file name without extension, e.g. "ippon_seoi_nage".</summary>
    public string Technique { get; set; } = "";

    /// <summary>Seconds into the technique, rounded to 0.01.</summary>
    public float Time { get; set; }

    /// <summary>Phase name shown at <see cref="Time"/>.</summary>
    public string Phase { get; set; } = "";

    /// <summary>"tori" or "uki".</summary>
    public string Who { get; set; } = "";

    /// <summary>YAML bone key, e.g. "right_arm".</summary>
    public string Bone { get; set; } = "";

    public string Text { get; set; } = "";

    /// <summary><see cref="FeedbackStatus.Open"/> or <see cref="FeedbackStatus.Done"/>.</summary>
    public string Status { get; set; } = FeedbackStatus.Open;

    [YamlIgnore]
    public bool IsOpen => Status != FeedbackStatus.Done;
}

/// <summary>Reads and writes the feedback file of a technique; shared by the app and the converter.</summary>
public static class FeedbackFile
{
    private static readonly IDeserializer Deserializer = new DeserializerBuilder()
        .WithNamingConvention(UnderscoredNamingConvention.Instance)
        .Build();

    private static readonly ISerializer Serializer = new SerializerBuilder()
        .WithNamingConvention(UnderscoredNamingConvention.Instance)
        .DisableAliases()
        .Build();

    /// <summary>File name stem of a technique: "Ippon Seoi-nage" -> "ippon_seoi_nage".</summary>
    public static string Slug(string techniqueName)
    {
        var sb = new StringBuilder();
        foreach (var c in techniqueName.Trim().ToLowerInvariant())
        {
            if (char.IsLetterOrDigit(c))
                sb.Append(c);
            else if (sb.Length > 0 && sb[^1] != '_')
                sb.Append('_');
        }
        return sb.ToString().TrimEnd('_');
    }

    public static string PathFor(string feedbackDirectory, string technique) =>
        Path.Combine(feedbackDirectory, Slug(technique) + ".yaml");

    public static float RoundTime(float seconds) => (float)Math.Round(seconds, 2);

    /// <summary>YAML bone key of a skeleton bone: "RightUpLeg" -> "right_up_leg".</summary>
    public static string BoneKey(string skeletonBone)
    {
        var sb = new StringBuilder();
        foreach (var c in skeletonBone)
        {
            if (char.IsUpper(c) && sb.Length > 0)
                sb.Append('_');
            sb.Append(char.ToLowerInvariant(c));
        }
        return sb.ToString();
    }

    /// <summary>Stable order: time, then who, then bone (then text, so the file is deterministic).</summary>
    public static List<FeedbackEntry> Sorted(IEnumerable<FeedbackEntry> entries) =>
        entries.OrderBy(e => e.Time)
               .ThenBy(e => e.Who, StringComparer.Ordinal)
               .ThenBy(e => e.Bone, StringComparer.Ordinal)
               .ThenBy(e => e.Text, StringComparer.Ordinal)
               .ToList();

    public static List<FeedbackEntry> Parse(string yaml) =>
        Deserializer.Deserialize<List<FeedbackEntry>?>(yaml) ?? [];

    public static string Serialize(IEnumerable<FeedbackEntry> entries) =>
        Serializer.Serialize(Sorted(entries));

    /// <summary>The entries in <paramref name="path"/>; an empty list when the file does not exist yet.</summary>
    public static List<FeedbackEntry> Load(string path) =>
        File.Exists(path) ? Parse(File.ReadAllText(path)) : [];

    /// <summary>Writes the file (creating the directory) via a temp file, so a crash never leaves half a file.</summary>
    public static void Save(string path, IEnumerable<FeedbackEntry> entries)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        var temp = path + ".tmp";
        File.WriteAllText(temp, Serialize(entries), new UTF8Encoding(false));
        File.Move(temp, path, overwrite: true);
    }

    /// <summary>Sets the given entries to done; returns how many changed.</summary>
    public static int MarkDone(IEnumerable<FeedbackEntry> entries)
    {
        var count = 0;
        foreach (var e in entries.Where(e => e.IsOpen))
        {
            e.Status = FeedbackStatus.Done;
            count++;
        }
        return count;
    }
}

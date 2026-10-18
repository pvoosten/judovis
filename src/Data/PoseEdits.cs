using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace JudoVisualizer.Data;

/// <summary>Allowed values of <see cref="PoseEdit.Ease"/>.</summary>
public static class PoseEase
{
    public const string Smooth = "smooth";
    public const string Linear = "linear";
}

/// <summary>
/// A pose correction made in the app (F3): the value one bone (or the root) of Tori or Uki must have at
/// <see cref="Time"/>, faded in and out over a range of the technique. Edits are absolute targets, so
/// applying one to a technique that already has it changes nothing (Blender bakes them into the YAML,
/// the app applies them on top of it). Times are seconds on the 50 fps frame grid.
/// </summary>
public sealed class PoseEdit
{
    /// <summary><see cref="Bone"/> value for the root (position between the feet + root rotation).</summary>
    public const string Root = "root";

    /// <summary>"tori" or "uki".</summary>
    public string Who { get; set; } = "";

    /// <summary>YAML bone key ("right_arm") or <see cref="Root"/>.</summary>
    public string Bone { get; set; } = "";

    /// <summary>The anchor: the keyframe at which the target values hold exactly.</summary>
    public float Time { get; set; }

    /// <summary>Target bone delta or root rotation (Euler XYZ degrees, as in the YAML); null = unchanged.</summary>
    public Vec3? Rotation { get; set; }

    /// <summary>Target root position (metres, Godot space); root only, null = unchanged.</summary>
    public Vec3? Position { get; set; }

    /// <summary>The edit starts here (0 %) ...</summary>
    public float From { get; set; }

    /// <summary>... is fully applied from here ...</summary>
    public float HoldFrom { get; set; }

    /// <summary>... up to here ...</summary>
    public float HoldTo { get; set; }

    /// <summary>... and has faded out here (0 %).</summary>
    public float To { get; set; }

    /// <summary><see cref="PoseEase.Smooth"/> (smoothstep fade) or <see cref="PoseEase.Linear"/>.</summary>
    public string Ease { get; set; } = PoseEase.Smooth;

    [JsonIgnore]
    public bool IsRoot => Bone == Root;
}

/// <summary>
/// <c>edits/&lt;technique&gt;.json</c>: the pose edits of one technique and the keyframes inserted for them.
/// JSON rather than YAML because Blender's Python reads it too (it has no YAML module).
/// </summary>
public sealed class PoseEditFile
{
    public const string Directory = "edits";

    private List<float> _keyframes = [];
    private List<PoseEdit> _edits = [];

    /// <summary>Times of keyframes inserted in the app (in-betweens: no phase, no timeline tick).</summary>
    public List<float> Keyframes { get => _keyframes; set => _keyframes = value ?? []; }

    /// <summary>Applied in this order; a later edit replaces an earlier one whose hold range it overlaps.</summary>
    public List<PoseEdit> Edits { get => _edits; set => _edits = value ?? []; }

    [JsonIgnore]
    public bool IsEmpty => _keyframes.Count == 0 && _edits.Count == 0;

    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = true,
        Converters = { new Vec3JsonConverter() },
    };

    public static string PathFor(string editsDirectory, string technique) =>
        Path.Combine(editsDirectory, FeedbackFile.Slug(technique) + ".json");

    public static PoseEditFile Parse(string json) =>
        JsonSerializer.Deserialize<PoseEditFile>(json, Options) ?? new PoseEditFile();

    /// <summary>Rounded (times 0.1 ms, degrees 0.01, metres 0.1 mm) and in a stable order.</summary>
    public string Serialize()
    {
        var rounded = new PoseEditFile
        {
            Keyframes = Keyframes.Select(t => Round(t, 4)).Distinct().Order().ToList(),
            Edits = Edits.Select(e => new PoseEdit
            {
                Who = e.Who, Bone = e.Bone, Time = Round(e.Time, 4),
                Rotation = e.Rotation is { } r ? Round(r, 2) : null,
                Position = e.Position is { } p ? Round(p, 4) : null,
                From = Round(e.From, 4), HoldFrom = Round(e.HoldFrom, 4),
                HoldTo = Round(e.HoldTo, 4), To = Round(e.To, 4), Ease = e.Ease,
            }).ToList(),
        };
        return JsonSerializer.Serialize(rounded, Options) + "\n";
    }

    /// <summary>The file at <paramref name="path"/>; empty when it does not exist yet.</summary>
    public static PoseEditFile Load(string path) =>
        File.Exists(path) ? Parse(File.ReadAllText(path)) : new PoseEditFile();

    /// <summary>Writes via a temp file (no half files); an empty edit set deletes the file.</summary>
    public void Save(string path)
    {
        if (IsEmpty)
        {
            if (File.Exists(path))
                File.Delete(path);
            return;
        }
        System.IO.Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        var temp = path + ".tmp";
        File.WriteAllText(temp, Serialize(), new UTF8Encoding(false));
        File.Move(temp, path, overwrite: true);
    }

    /// <summary>
    /// <see cref="Save"/> that reports failure instead of throwing: on Windows another process reading the file
    /// (an editor's file watcher, the virus scanner) briefly makes replacing or deleting it fail. Try again later.
    /// </summary>
    public bool TrySave(string path, out string? error)
    {
        try
        {
            Save(path);
            error = null;
            return true;
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            error = e.Message;
            try
            {
                File.Delete(path + ".tmp");
            }
            catch (Exception cleanup) when (cleanup is IOException or UnauthorizedAccessException)
            {
                // a leftover temp file is overwritten by the next attempt
            }
            return false;
        }
    }

    private static float Round(float x, int digits) => (float)Math.Round(x, digits);

    private static Vec3 Round(Vec3 v, int digits) => new(Round(v.X, digits), Round(v.Y, digits), Round(v.Z, digits));
}

/// <summary>Writes <see cref="Vec3"/> as <c>[x, y, z]</c> on one line.</summary>
internal sealed class Vec3JsonConverter : JsonConverter<Vec3>
{
    public override Vec3 Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        var values = JsonSerializer.Deserialize<float[]>(ref reader, options);
        if (values is not { Length: 3 })
            throw new JsonException("expected [x, y, z].");
        return new Vec3(values[0], values[1], values[2]);
    }

    public override void Write(Utf8JsonWriter writer, Vec3 value, JsonSerializerOptions options) =>
        writer.WriteRawValue("[" + string.Join(", ", new[] { value.X, value.Y, value.Z }
            .Select(c => (c == 0 ? 0f : c).ToString("0.0###", CultureInfo.InvariantCulture))) + "]"); // no "-0.0"
}

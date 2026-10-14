using System.Collections.Generic;
using System.IO;
using System.Linq;
using Godot;

namespace JudoVisualizer.Data;

/// <summary>
/// Reads and writes technique YAML through Godot's file system, so <c>res://</c> and
/// <c>user://</c> paths work both in the editor and in exported builds.
/// Exported builds must include the YAML files via an export filter (<c>data/techniques/*.yaml</c>).
/// </summary>
public static class TechniqueLoader
{
    /// <summary>Techniques shipped with the app (read-only in exported builds).</summary>
    public const string BuiltInDirectory = "res://data/techniques";

    /// <summary>Writable location for techniques created or edited by the user.</summary>
    public const string UserDirectory = "user://techniques";

    /// <summary>
    /// Loads every <c>*.yaml</c>/<c>*.yml</c> file in <paramref name="directory"/>, sorted by file name.
    /// Invalid files are reported with <see cref="GD.PushError(string)"/> and skipped.
    /// </summary>
    public static List<Technique> LoadDirectory(string directory = BuiltInDirectory)
    {
        var techniques = new List<Technique>();
        if (!DirAccess.DirExistsAbsolute(directory))
            return techniques;

        var files = DirAccess.GetFilesAt(directory)
            .Where(f => f.EndsWith(".yaml") || f.EndsWith(".yml"))
            .Order();
        foreach (var file in files)
        {
            try
            {
                techniques.Add(Load(directory.PathJoin(file)));
            }
            catch (TechniqueFormatException e)
            {
                GD.PushError(e.Message);
            }
            catch (IOException e)
            {
                GD.PushError(e.Message);
            }
        }
        return techniques;
    }

    /// <exception cref="IOException">The file cannot be read.</exception>
    /// <exception cref="TechniqueFormatException">The file is not a valid technique.</exception>
    public static Technique Load(string path)
    {
        using var file = Godot.FileAccess.Open(path, Godot.FileAccess.ModeFlags.Read)
            ?? throw new IOException($"{path}: cannot open ({Godot.FileAccess.GetOpenError()}).");
        return TechniqueSerializer.Deserialize(file.GetAsText(), path);
    }

    /// <summary>Validates and writes <paramref name="technique"/> as YAML, creating the directory if needed.</summary>
    /// <exception cref="TechniqueFormatException">The technique is invalid; nothing is written.</exception>
    /// <exception cref="IOException">The file cannot be written.</exception>
    public static void Save(Technique technique, string path)
    {
        var errors = TechniqueValidator.Validate(technique);
        if (errors.Count > 0)
            throw new TechniqueFormatException(path, errors);

        DirAccess.MakeDirRecursiveAbsolute(path.GetBaseDir());
        using var file = Godot.FileAccess.Open(path, Godot.FileAccess.ModeFlags.Write)
            ?? throw new IOException($"{path}: cannot write ({Godot.FileAccess.GetOpenError()}).");
        file.StoreString(TechniqueSerializer.Serialize(technique));
    }
}

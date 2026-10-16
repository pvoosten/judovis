using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace JudoVisualizer.Data;

/// <summary>
/// Converter behind <c>dotnet run --project tools/feedback</c>: reads <c>feedback/&lt;t&gt;.yaml</c>,
/// writes <c>build/feedback/&lt;t&gt;.md</c> and returns the prompt.
/// </summary>
public static class FeedbackExporter
{
    public const string FeedbackDirectory = "feedback";
    public const string OutputDirectory = "build/feedback";

    /// <summary>Technique names that have a feedback file.</summary>
    public static List<string> Techniques(string repoRoot)
    {
        var dir = Path.Combine(repoRoot, FeedbackDirectory);
        return Directory.Exists(dir)
            ? Directory.GetFiles(dir, "*.yaml").Select(f => Path.GetFileNameWithoutExtension(f)!).Order().ToList()
            : [];
    }

    /// <returns>The prompt of the open comments, or "" (nothing written) when there are none.</returns>
    /// <param name="markDone">Sets the exported entries to done once the prompt is written.</param>
    public static string Export(string repoRoot, string technique, bool markDone)
    {
        var slug = FeedbackFile.Slug(technique);
        var feedbackPath = FeedbackFile.PathFor(Path.Combine(repoRoot, FeedbackDirectory), slug);
        var entries = FeedbackFile.Load(feedbackPath);

        var techniquePath = Path.Combine(repoRoot, "data", "techniques", slug + ".yaml");
        var loaded = TechniqueSerializer.Deserialize(File.ReadAllText(techniquePath), techniquePath);
        var scriptPath = Path.Combine(repoRoot, "tools", "blender", "techniques", slug + ".py");
        var script = File.Exists(scriptPath) ? File.ReadAllText(scriptPath) : null;

        var prompt = FeedbackPromptBuilder.Build(loaded, entries, script);
        if (prompt.Length == 0)
            return "";

        var output = Path.Combine(repoRoot, OutputDirectory, slug + ".md");
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        File.WriteAllText(output, prompt, new UTF8Encoding(false));

        if (markDone)
        {
            var emitted = entries.Where(e => e.IsOpen && !string.IsNullOrWhiteSpace(e.Text));
            FeedbackFile.MarkDone(emitted);
            FeedbackFile.Save(feedbackPath, entries);
        }
        return prompt;
    }
}

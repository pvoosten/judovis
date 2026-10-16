using JudoVisualizer.Data;

// Usage: dotnet run --project tools/feedback -- <technique|all> [--mark-done]
// Prints one prompt per technique (open comments only) and writes build/feedback/<technique>.md.

var markDone = args.Contains("--mark-done");
var names = args.Where(a => !a.StartsWith("--")).ToList();
if (names.Count != 1)
{
    Console.Error.WriteLine("Usage: FeedbackToPrompt <technique|all> [--mark-done]");
    return 2;
}

var root = FindRepoRoot();
if (root is null)
{
    Console.Error.WriteLine("Run from inside the repository (JudoVisualizer.csproj not found).");
    return 2;
}

var techniques = names[0] == "all" ? FeedbackExporter.Techniques(root) : [names[0]];
var prompts = new List<string>();
try
{
    foreach (var technique in techniques)
    {
        var prompt = FeedbackExporter.Export(root, technique, markDone);
        if (prompt.Length > 0)
            prompts.Add(prompt.TrimEnd());
    }
}
catch (Exception e) when (e is IOException or TechniqueFormatException or YamlDotNet.Core.YamlException)
{
    Console.Error.WriteLine(e.Message);
    return 1;
}

if (prompts.Count == 0)
    Console.Error.WriteLine("No open comments.");
else
    Console.WriteLine(string.Join(Environment.NewLine + Environment.NewLine, prompts));
return 0;

static string? FindRepoRoot()
{
    foreach (var start in new[] { Directory.GetCurrentDirectory(), AppContext.BaseDirectory })
        for (var dir = new DirectoryInfo(start); dir is not null; dir = dir.Parent)
            if (File.Exists(Path.Combine(dir.FullName, "JudoVisualizer.csproj")))
                return dir.FullName;
    return null;
}

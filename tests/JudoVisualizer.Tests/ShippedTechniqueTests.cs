using JudoVisualizer.Data;
using JudoVisualizer.Playback;
using Xunit;

namespace JudoVisualizer.Tests;

/// <summary>Every technique in data/techniques must parse, validate and build tracks.</summary>
public class ShippedTechniqueTests
{
    public static TheoryData<string> Files()
    {
        var data = new TheoryData<string>();
        foreach (var f in Directory.GetFiles(Path.Combine(AppContext.BaseDirectory, "techniques"), "*.yaml"))
            data.Add(Path.GetFileName(f));
        return data;
    }

    [Theory]
    [MemberData(nameof(Files))]
    public void ShippedTechnique_IsValid(string file)
    {
        var path = Path.Combine(AppContext.BaseDirectory, "techniques", file);

        var technique = TechniqueSerializer.Deserialize(File.ReadAllText(path), file);
        var tracks = TechniqueTracks.Build(technique);

        Assert.NotNull(tracks.Tori.Position);
        Assert.NotNull(tracks.Uki.Position);
        Assert.Equal(technique.DurationSeconds, technique.Keyframes[^1].Time);
    }
}

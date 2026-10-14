using JudoVisualizer.Data;
using Xunit;

namespace JudoVisualizer.Tests;

public class TechniqueSerializerTests
{
    private static string ReadTechnique(string file) =>
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "techniques", file));

    private const string Minimal = """
        technique_name: "Test"
        kyu_grade: 6
        belt_color: { name: "Witte band", hex: "#FFFFFF" }
        duration_seconds: 1.0
        keyframes:
          - time: 0.0
            tori: { position: [0, 0, 0], rotation: [0, 0, 0] }
        """;

    [Fact]
    public void IpponSeoiNage_Loads()
    {
        var t = TechniqueSerializer.Deserialize(ReadTechnique("ippon_seoi_nage.yaml"));

        Assert.Equal("Ippon Seoi-nage", t.TechniqueName);
        Assert.Equal("T1", t.Code);
        Assert.Equal(5, t.KyuGrade);
        Assert.Equal("#FFD700", t.BeltColor.Hex);
        Assert.Equal(2.5f, t.DurationSeconds);
        Assert.Equal([0.0f, 0.9f, 1.6f, 2.5f], t.Keyframes.Select(k => k.Time));
        Assert.Equal(new Vec3(0, 0, 1.2f), t.Keyframes[0].Uki.Position);
        Assert.Equal(new Vec3(0, 180, 0), t.Keyframes[0].Uki.Rotation);
        Assert.Equal(new Vec3(20, -10, 15), t.Keyframes[0].Tori.Bones["right_shoulder"]);
        Assert.Empty(t.Keyframes[3].Uki.Bones); // "bones:" with no value
    }

    [Fact]
    public void Serialize_RoundTrips()
    {
        var original = TechniqueSerializer.Deserialize(ReadTechnique("ippon_seoi_nage.yaml"));

        var yaml = TechniqueSerializer.Serialize(original);
        var again = TechniqueSerializer.Deserialize(yaml);

        Assert.Equal(yaml, TechniqueSerializer.Serialize(again));
        Assert.Contains("position: [0.0, 0.0, 1.2]", yaml);
        Assert.Equal(original.Keyframes[2].Uki.Rotation, again.Keyframes[2].Uki.Rotation);
    }

    [Fact]
    public void MissingSections_DefaultToEmpty()
    {
        var t = TechniqueSerializer.Deserialize(Minimal);

        Assert.Null(t.Keyframes[0].Uki.Position);
        Assert.Null(t.Keyframes[0].Uki.Rotation);
        Assert.Empty(t.Keyframes[0].Tori.Bones);
        Assert.DoesNotContain("uki:\n    position", TechniqueSerializer.Serialize(t)); // nulls are omitted
    }

    [Theory]
    [InlineData("technique_name: \"Test\"", "technique_nam: \"Test\"", "line 1")]           // unknown key
    [InlineData("position: [0, 0, 0]", "position: [0, 0]", "expected [x, y, z]")]          // short vector
    [InlineData("position: [0, 0, 0]", "position: [0, a, 0]", "'a' is not a number")]
    [InlineData("kyu_grade: 6", "kyu_grade: 7", "kyu_grade must be 1-6")]
    [InlineData("hex: \"#FFFFFF\"", "hex: \"#FFD700\"", "does not match kyu_grade 6")]
    [InlineData("hex: \"#FFFFFF\"", "hex: \"white\"", "#RRGGBB")]
    [InlineData("duration_seconds: 1.0", "duration_seconds: 0", "duration_seconds must be > 0")]
    [InlineData("rotation: [0, 0, 0] }", "rotation: [0, 0, 0], bones: { elbow: [1, 2, 3] } }", "unknown bone 'elbow'")]
    public void InvalidInput_Throws(string find, string replace, string expectedError)
    {
        var yaml = Minimal.Replace(find, replace);
        Assert.NotEqual(Minimal, yaml);

        var e = Assert.Throws<TechniqueFormatException>(() => TechniqueSerializer.Deserialize(yaml, "test.yaml"));

        Assert.Equal("test.yaml", e.FilePath);
        Assert.Contains(e.Errors, err => err.Contains(expectedError));
    }

    [Fact]
    public void KeyframeTimes_MustIncreaseAndStayWithinDuration()
    {
        var yaml = Minimal + """

              - time: 0.0
              - time: 2.0
            """;

        var e = Assert.Throws<TechniqueFormatException>(() => TechniqueSerializer.Deserialize(yaml));

        Assert.Contains(e.Errors, err => err.StartsWith("keyframes[1]") && err.Contains("strictly increasing"));
        Assert.Contains(e.Errors, err => err.StartsWith("keyframes[2]") && err.Contains("within 0..duration_seconds"));
    }

    [Fact]
    public void EmptyFile_Throws()
    {
        var e = Assert.Throws<TechniqueFormatException>(() => TechniqueSerializer.Deserialize(""));
        Assert.Contains("file is empty.", e.Errors);
    }
}

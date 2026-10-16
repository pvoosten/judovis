using System.Numerics;
using JudoVisualizer.Data;
using JudoVisualizer.Playback;
using Xunit;

namespace JudoVisualizer.Tests;

public class FeedbackTests : IDisposable
{
    private readonly string _dir = Path.Combine(Path.GetTempPath(), "judo-feedback-" + Guid.NewGuid().ToString("N"));

    public void Dispose()
    {
        if (Directory.Exists(_dir))
            Directory.Delete(_dir, recursive: true);
    }

    private static string Fixture(string file) =>
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Fixtures", file));

    private static Technique Sample() => TechniqueSerializer.Deserialize(Fixture("sample_technique.yaml"));

    private static FeedbackEntry Entry(float time, string who, string bone, string text, string status = "open") =>
        new() { Technique = "ippon_seoi_nage", Time = time, Phase = "Kake", Who = who, Bone = bone, Text = text, Status = status };

    [Fact]
    public void Slug_IsSnakeCase() => Assert.Equal("ippon_seoi_nage", FeedbackFile.Slug("Ippon Seoi-nage"));

    [Fact]
    public void BoneKey_MatchesYamlBoneKeys()
    {
        Assert.Equal("right_up_leg", FeedbackFile.BoneKey("RightUpLeg"));
        Assert.All(BoneNames.Skeleton, b => Assert.True(BoneNames.TryResolve(FeedbackFile.BoneKey(b), out var s) && s == b));
    }

    [Fact]
    public void RoundTrip_KeepsEntries()
    {
        var entries = Sorted(Entry(0.8f, "tori", "right_arm", "elleboog te laag"), Entry(1.25f, "uki", "left_foot", "hiel omhoog", "done"));

        var back = FeedbackFile.Parse(FeedbackFile.Serialize(entries));

        Assert.Equal(2, back.Count);
        Assert.Equal(0.8f, back[0].Time);
        Assert.Equal("tori", back[0].Who);
        Assert.Equal("right_arm", back[0].Bone);
        Assert.Equal("elleboog te laag", back[0].Text);
        Assert.Equal("done", back[1].Status);
    }

    [Fact]
    public void Parse_EmptyAndEmptyList() => Assert.Empty(FeedbackFile.Parse("[]\n"));

    [Fact]
    public void Sorted_ByTimeThenWhoThenBone()
    {
        var sorted = FeedbackFile.Sorted([
            Entry(2f, "tori", "a", "x"), Entry(1f, "uki", "b", "x"), Entry(1f, "tori", "z", "x"), Entry(1f, "tori", "c", "x"),
        ]);

        Assert.Equal(["tori.c", "tori.z", "uki.b", "tori.a"], sorted.Select(e => $"{e.Who}.{e.Bone}"));
    }

    [Fact]
    public void Save_CreatesDirectoryAndFile_NoTempLeftBehind()
    {
        var path = FeedbackFile.PathFor(Path.Combine(_dir, "feedback"), "Ippon Seoi-nage");

        FeedbackFile.Save(path, [Entry(1f, "tori", "spine", "buig dieper")]);

        Assert.Equal("ippon_seoi_nage.yaml", Path.GetFileName(path));
        Assert.Single(FeedbackFile.Load(path));
        Assert.False(File.Exists(path + ".tmp"));
        Assert.Empty(FeedbackFile.Load(Path.Combine(_dir, "missing.yaml")));
    }

    [Fact]
    public void RoundTime_TwoDecimals() => Assert.Equal(0.83f, FeedbackFile.RoundTime(0.8333f));

    [Fact]
    public void Prompt_MatchesFixture()
    {
        var prompt = FeedbackPromptBuilder.Build(Sample(), FeedbackFile.Parse(Fixture("sample_feedback.yaml")), Fixture("sample_script.py"));

        Assert.Equal(Fixture("sample_feedback_prompt.txt").ReplaceLineEndings(), prompt.ReplaceLineEndings());
    }

    [Fact]
    public void Prompt_NoFunctionNameWhenScriptHasNone()
    {
        var prompt = FeedbackPromptBuilder.Build(Sample(), [Entry(1.6f, "tori", "spine", "dieper")], "def other(): pass");

        Assert.Contains("kf3 1.60s Kake:", prompt);
    }

    [Fact]
    public void Prompt_BetweenKeyframesNamesBoth_AndAfterLast()
    {
        var prompt = FeedbackPromptBuilder.Build(Sample(), [Entry(1.2f, "tori", "spine", "a"), Entry(2.9f, "uki", "head", "b")]);

        Assert.Contains("between kf2 (0.9 s) and kf3 (1.6 s):", prompt);
        Assert.Contains("after kf4 (2.5 s):", prompt);
    }

    [Fact]
    public void Prompt_SnapsToKeyframeWithinTolerance()
    {
        var prompt = FeedbackPromptBuilder.Build(Sample(), [Entry(1.63f, "tori", "spine", "a")]);

        Assert.Contains("kf3 1.60s", prompt);
        Assert.DoesNotContain("between", prompt);
    }

    [Fact]
    public void Prompt_OnlyOpenNonEmpty_ElseEmpty()
    {
        Assert.Equal("", FeedbackPromptBuilder.Build(Sample(), []));
        Assert.Equal("", FeedbackPromptBuilder.Build(Sample(), [Entry(1f, "tori", "spine", "klaar", "done"), Entry(1f, "tori", "spine", "  ")]));
    }

    [Fact]
    public void Prompt_SkipsInbetweensWhenNumberingKeyframes()
    {
        var technique = Sample();
        technique.Keyframes.Insert(1, new Keyframe { Time = 0.4f, Inbetween = true });

        var prompt = FeedbackPromptBuilder.Build(technique, [Entry(1.6f, "tori", "spine", "a")]);

        Assert.Contains("kf3 1.60s", prompt);
    }

    [Fact]
    public void MarkDone_OnlyEmittedEntries()
    {
        var entries = new List<FeedbackEntry> { Entry(1f, "tori", "spine", "a"), Entry(2f, "tori", "head", "b", "done") };

        Assert.Equal(1, FeedbackFile.MarkDone(entries));
        Assert.All(entries, e => Assert.False(e.IsOpen));
    }

    [Fact]
    public void Export_WritesMarkdown_AndMarkDoneKeepsFileAndSkipsNextTime()
    {
        Directory.CreateDirectory(Path.Combine(_dir, "data", "techniques"));
        File.WriteAllText(Path.Combine(_dir, "data", "techniques", "ippon_seoi_nage.yaml"), Fixture("sample_technique.yaml"));
        FeedbackFile.Save(FeedbackFile.PathFor(Path.Combine(_dir, "feedback"), "ippon_seoi_nage"),
            [Entry(1.6f, "tori", "right_arm", "elleboog te laag"), Entry(1.6f, "tori", "spine", "  ")]);

        var kept = FeedbackExporter.Export(_dir, "ippon_seoi_nage", markDone: false);
        Assert.Contains("- tori.right_arm: elleboog te laag", kept);
        Assert.Equal(kept, File.ReadAllText(Path.Combine(_dir, "build", "feedback", "ippon_seoi_nage.md")));
        Assert.Single(FeedbackFile.Load(FeedbackFile.PathFor(Path.Combine(_dir, "feedback"), "ippon_seoi_nage")), e => e.IsOpen && e.Text.Trim().Length > 0);

        Assert.Equal(kept, FeedbackExporter.Export(_dir, "ippon_seoi_nage", markDone: true));

        var after = FeedbackFile.Load(FeedbackFile.PathFor(Path.Combine(_dir, "feedback"), "ippon_seoi_nage"));
        Assert.Equal(2, after.Count);
        Assert.Single(after, e => !e.IsOpen);
        Assert.Equal("", FeedbackExporter.Export(_dir, "ippon_seoi_nage", markDone: true));
        Assert.Equal(["ippon_seoi_nage"], FeedbackExporter.Techniques(_dir));
    }

    [Fact]
    public void BonePicker_PicksNearestToRay_AndPrefersNearerOnTies()
    {
        var arm = new BoneSegment("tori", "right_arm", new Vector3(0, 1, 5), new Vector3(1, 1, 5));
        var far = new BoneSegment("uki", "left_arm", new Vector3(0, 1, 8), new Vector3(1, 1, 8));
        var other = new BoneSegment("tori", "spine", new Vector3(0, 0, 5), new Vector3(0, 0.5f, 5));
        var ray = (Origin: new Vector3(0.5f, 1.02f, 0), Dir: Vector3.UnitZ);

        var hit = BonePicker.Pick(ray.Origin, ray.Dir, [other, far, arm], 0.07f);

        Assert.Equal("right_arm", hit!.Value.Segment.Bone); // tie on distance: the nearer one wins
        Assert.Equal(0.5f, hit.Value.Along, 3);
        Assert.Null(BonePicker.Pick(new Vector3(0.5f, 3f, 0), Vector3.UnitZ, [arm, far], 0.07f));
    }

    [Fact]
    public void BonePicker_IgnoresBonesBehindTheCamera() =>
        Assert.Null(BonePicker.Pick(Vector3.Zero, Vector3.UnitZ, [new BoneSegment("tori", "head", new Vector3(0, 0, -3), new Vector3(0, 0.2f, -3))], 0.07f));

    private static List<FeedbackEntry> Sorted(params FeedbackEntry[] entries) => FeedbackFile.Sorted(entries);
}

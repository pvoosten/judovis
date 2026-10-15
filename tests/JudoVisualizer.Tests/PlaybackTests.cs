using JudoVisualizer.Data;
using JudoVisualizer.Playback;
using Xunit;

namespace JudoVisualizer.Tests;

public class PlaybackTests
{
    private static Technique SampleTechnique() => TechniqueSerializer.Deserialize(
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Fixtures", "sample_technique.yaml")));

    [Theory]
    [InlineData(-1.0f, 0, 0, 0.0f)]   // before the first key: hold it
    [InlineData(0.0f, 0, 0, 0.0f)]
    [InlineData(0.5f, 0, 1, 0.5f)]
    [InlineData(1.0f, 1, 1, 0.0f)]   // exactly on a key
    [InlineData(2.5f, 1, 2, 0.75f)]
    [InlineData(9.0f, 2, 2, 0.0f)]   // after the last key: hold it
    public void KeyTrack_SamplesBracketingKeys(float time, int from, int to, float weight)
    {
        var track = new KeyTrack([(0f, Vec3.Zero), (1f, new Vec3(1, 0, 0)), (3f, new Vec3(3, 0, 0))]);

        var s = track.Sample(time);

        Assert.Equal(new KeySample(from, to, weight), s);
    }

    [Fact]
    public void KeyTrack_SingleKey_AlwaysHoldsIt()
    {
        var track = new KeyTrack([(1f, new Vec3(1, 2, 3))]);
        Assert.Equal(new KeySample(0, 0, 0), track.Sample(0));
        Assert.Equal(new KeySample(0, 0, 0), track.Sample(5));
    }

    [Fact]
    public void Tracks_OnlyContainKeyframesThatSetTheBone()
    {
        var tracks = TechniqueTracks.Build(SampleTechnique());

        // Tori's right_arm is keyed at 0.0 and 0.9 only: missing at 1.6 and 2.5.
        var rightArm = tracks.Tori.Bones["RightArm"];
        Assert.Equal([0.0f, 0.9f], rightArm.Times);
        Assert.Equal(new KeySample(1, 1, 0), rightArm.Sample(2.0f)); // held after its last key

        // Tori's spine is keyed at 0.0, 0.9, 1.6 and 2.5.
        Assert.Equal(4, tracks.Tori.Bones["Spine"].Times.Count);

        // Uki's right_leg is keyed only at 1.6: held before and after.
        var ukiRightLeg = tracks.Uki.Bones["RightLeg"];
        Assert.Equal([1.6f], ukiRightLeg.Times);
        Assert.Equal(new KeySample(0, 0, 0), ukiRightLeg.Sample(0));

        // Bones never keyed have no track (they stay at rest).
        Assert.False(tracks.Tori.Bones.ContainsKey("Head"));
    }

    [Fact]
    public void Tracks_MissingBoneInterpolatesAcrossTheGap()
    {
        var yaml = """
            technique_name: "Gap"
            kyu_grade: 6
            belt_color: { name: "Wit", hex: "#FFFFFF" }
            duration_seconds: 2.0
            keyframes:
              - time: 0.0
                tori: { bones: { spine: [0, 0, 0], head: [0, 0, 0] } }
              - time: 1.0
                tori: { bones: { head: [10, 0, 0] } }
              - time: 2.0
                tori: { position: [1, 0, 0], bones: { spine: [40, 0, 0] } }
            """;
        var tracks = TechniqueTracks.Build(TechniqueSerializer.Deserialize(yaml));

        // At 1.0 spine is not keyed: it is halfway between its keys at 0.0 and 2.0.
        Assert.Equal(new KeySample(0, 1, 0.5f), tracks.Tori.Bones["Spine"].Sample(1.0f));
        // Position is only keyed at 2.0, so it is held over the whole technique.
        Assert.Equal([2.0f], tracks.Tori.Position!.Times);
        Assert.Null(tracks.Tori.Rotation);
    }

    // Fixture keyframes: 0.0, 0.9, 1.6, 2.5 (duration 2.5) -> phase boundaries at 0.45, 1.25, 2.05.
    [Theory]
    [InlineData(0.0f, 0)]
    [InlineData(0.44f, 0)]
    [InlineData(0.45f, 1)]
    [InlineData(0.9f, 1)]
    [InlineData(1.3f, 2)]
    [InlineData(2.1f, 3)]
    [InlineData(2.5f, 3)]
    public void KeyframeIndexAt_ReturnsNearestKeyframe(float time, int expected) =>
        Assert.Equal(expected, TechniqueTracks.Build(SampleTechnique()).KeyframeIndexAt(time));

    [Fact]
    public void Phases_CoverTheWholeTechniqueWithoutGaps()
    {
        var phases = TechniqueTracks.Build(SampleTechnique()).Phases;

        Assert.Equal([(0f, 0.45f), (0.45f, 1.25f), (1.25f, 2.05f), (2.05f, 2.5f)],
                     phases.Select(p => (MathF.Round(p.Start, 4), MathF.Round(p.End, 4))));
        Assert.Equal("Tsukuri (Instap & Draai)", phases[1].Phase);
    }

    [Theory]
    [InlineData(0.0f, 0.9f, null)]
    [InlineData(0.5f, 0.9f, 0.0f)]
    [InlineData(0.9f, 1.6f, 0.0f)]     // on a keyframe: step to the neighbours, not to itself
    [InlineData(2.5f, null, 1.6f)]
    public void KeyframeStepping(float time, float? next, float? previous)
    {
        var tracks = TechniqueTracks.Build(SampleTechnique());

        Assert.Equal(next, tracks.NextKeyframeTime(time));
        Assert.Equal(previous, tracks.PreviousKeyframeTime(time));
    }

    [Theory]
    [InlineData(1.0f, 0.5f, 1f, false, 1.5f, false)]
    [InlineData(1.0f, 0.5f, 0.25f, false, 1.125f, false)] // slow motion
    [InlineData(2.4f, 0.5f, 1f, false, 2.5f, true)]       // stops at the end
    [InlineData(2.4f, 0.5f, 1f, true, 0.4f, false)]       // wraps around
    [InlineData(0.2f, 0.5f, -1f, false, 0.0f, true)]      // reverse stops at the start
    [InlineData(0.2f, 0.5f, -1f, true, 2.2f, false)]      // reverse wraps to the end
    [InlineData(1.0f, 0.5f, 0f, false, 1.0f, false)]      // speed 0 = frozen
    public void PlaybackClock_Advances(float time, float delta, float speed, bool loop, float expectedTime, bool expectedEnd)
    {
        var (t, end) = PlaybackClock.Advance(time, delta, speed, 2.5f, loop);

        Assert.Equal(expectedTime, t, 4);
        Assert.Equal(expectedEnd, end);
    }
}

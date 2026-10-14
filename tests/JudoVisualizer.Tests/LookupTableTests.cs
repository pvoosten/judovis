using JudoVisualizer.Data;
using Xunit;

namespace JudoVisualizer.Tests;

public class LookupTableTests
{
    [Theory]
    [InlineData("right_shoulder", "RightShoulder")]
    [InlineData("left_up_leg", "LeftUpLeg")]
    [InlineData("left_upleg", "LeftUpLeg")]
    [InlineData("LeftForearm", "LeftForearm")]
    [InlineData("spine", "Spine")]
    public void BoneNames_ResolveYamlKeys(string yaml, string expected)
    {
        Assert.True(BoneNames.TryResolve(yaml, out var name));
        Assert.Equal(expected, name);
    }

    [Theory]
    [InlineData("elbow")]
    [InlineData("LeftLapelGrip")] // grip bones are attachment points, not posable
    public void BoneNames_RejectUnknown(string yaml) => Assert.False(BoneNames.TryResolve(yaml, out _));

    [Fact]
    public void KyuGrades_MatchBeltTable()
    {
        Assert.Equal([6, 5, 4, 3, 2, 1], KyuGrades.All.Select(k => k.Grade));
        Assert.Equal(new KyuGradeInfo(5, "Yellow Belt", "#FFD700"), KyuGrades.Get(5));
        Assert.Equal("#8B4513", KyuGrades.Get(1).Hex);
        Assert.Throws<ArgumentOutOfRangeException>(() => KyuGrades.Get(0));
    }
}

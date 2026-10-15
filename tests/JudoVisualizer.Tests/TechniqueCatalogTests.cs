using JudoVisualizer.Data;
using JudoVisualizer.UI;
using Xunit;

namespace JudoVisualizer.Tests;

public class TechniqueCatalogTests
{
    private static Technique T(string name, int kyu) => new() { TechniqueName = name, KyuGrade = kyu };

    private static readonly Technique[] Techniques =
        [T("Uchi-mata", 2), T("O-soto-gari", 6), T("Ippon Seoi-nage", 5), T("De-ashi-barai", 6)];

    [Fact]
    public void Group_OrdersGradesFromBeginnerAndNamesAlphabetically()
    {
        var groups = TechniqueCatalog.Group(Techniques);

        Assert.Equal([6, 5, 2], groups.Select(g => g.Grade.Grade));
        Assert.Equal(["De-ashi-barai", "O-soto-gari"], groups[0].Techniques.Select(t => t.TechniqueName));
    }

    [Fact]
    public void Group_LeavesOutEmptyGrades() =>
        Assert.DoesNotContain(TechniqueCatalog.Group(Techniques), g => g.Grade.Grade is 4 or 3 or 1);

    [Fact]
    public void Group_FiltersOnOneGrade()
    {
        var groups = TechniqueCatalog.Group(Techniques, kyuFilter: 5);

        var group = Assert.Single(groups);
        Assert.Equal("Ippon Seoi-nage", Assert.Single(group.Techniques).TechniqueName);
        Assert.Empty(TechniqueCatalog.Group(Techniques, kyuFilter: 3));
    }

    [Theory]
    [InlineData(6, "6th Kyu - White Belt")]
    [InlineData(1, "1st Kyu - Brown Belt")]
    [InlineData(2, "2nd Kyu - Blue Belt")]
    public void Title_NamesGradeAndBelt(int grade, string expected) =>
        Assert.Equal(expected, TechniqueCatalog.Title(KyuGrades.Get(grade)));

    [Theory]
    [InlineData("Kake (Worp)", "Kake")]
    [InlineData("Kumikata", "Kumikata")]
    public void ShortPhase_DropsTheTranslation(string phase, string expected) =>
        Assert.Equal(expected, TechniqueCatalog.ShortPhase(phase));
}

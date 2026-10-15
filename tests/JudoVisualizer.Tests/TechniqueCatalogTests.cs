using JudoVisualizer.Data;
using JudoVisualizer.UI;
using Xunit;

namespace JudoVisualizer.Tests;

public class TechniqueCatalogTests
{
    private static Technique T(string name, int kyu, bool u18 = false) =>
        new() { TechniqueName = name, KyuGrade = kyu, U18 = u18 };

    private static readonly Technique[] Techniques =
        [T("Uchi-mata", 2), T("O-soto-gari", 6), T("Ippon Seoi-nage", 5), T("De-ashi-barai", 6)];

    [Fact]
    public void Group_PutsDanExtraAfterFirstKyu()
    {
        var groups = TechniqueCatalog.Group([T("Kani-basami", KyuGrades.DanExtra), T("Uki-otoshi", 1), T("O-goshi", 4)]);

        Assert.Equal([4, 1, KyuGrades.DanExtra], groups.Select(g => g.Grade.Grade));
    }

    [Fact]
    public void Group_CanHideU18Techniques()
    {
        Technique[] techniques = [T("Hadaka-jime", 2, u18: true), T("Uchi-mata", 2)];

        Assert.Equal(2, TechniqueCatalog.Group(techniques).Single().Techniques.Count);
        Assert.Equal("Uchi-mata", TechniqueCatalog.Group(techniques, includeU18: false).Single().Techniques.Single().TechniqueName);
    }

    [Fact]
    public void EntryLabel_TagsU18() =>
        Assert.Equal("Hadaka-jime  U18+", TechniqueCatalog.EntryLabel(T("Hadaka-jime", 2, u18: true)));

    [Fact]
    public void Details_JoinsKnownFields()
    {
        var t = T("Kata-ha-jime", 2, u18: true);
        t.Code = "S2-3";
        t.Category = "Shime-waza (Wurging)";
        t.Source = "VJF leerlijn 2015, blauw";

        Assert.Equal("S2-3 · Shime-waza (Wurging) · 2nd Kyu - Blue Belt · U18+ · VJF leerlijn 2015, blauw",
                     TechniqueCatalog.Details(t));
        Assert.Equal("1st Kyu - Brown Belt", TechniqueCatalog.Details(T("X", 1)));
    }

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
    [InlineData(0, "Dan / extra")]
    public void Title_NamesGradeAndBelt(int grade, string expected) =>
        Assert.Equal(expected, TechniqueCatalog.Title(KyuGrades.Get(grade)));

    [Theory]
    [InlineData("Kake (Worp)", "Kake")]
    [InlineData("Kumikata", "Kumikata")]
    public void ShortPhase_DropsTheTranslation(string phase, string expected) =>
        Assert.Equal(expected, TechniqueCatalog.ShortPhase(phase));
}

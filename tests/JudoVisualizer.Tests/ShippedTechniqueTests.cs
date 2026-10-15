using System.Text.RegularExpressions;
using JudoVisualizer.Data;
using JudoVisualizer.Playback;
using Xunit;

namespace JudoVisualizer.Tests;

/// <summary>
/// Every technique in data/techniques must parse, validate and (if animated) build tracks; together
/// they form the catalogue: the VJF leerlijn plus the other Kodokan waza (CLAUDE.md, phase 6).
/// </summary>
public class ShippedTechniqueTests
{
    private static string Directory_ => Path.Combine(AppContext.BaseDirectory, "techniques");

    public static TheoryData<string> Files()
    {
        var data = new TheoryData<string>();
        foreach (var f in Directory.GetFiles(Directory_, "*.yaml"))
            data.Add(Path.GetFileName(f));
        return data;
    }

    private static Technique Load(string file) =>
        TechniqueSerializer.Deserialize(File.ReadAllText(Path.Combine(Directory_, file)), file);

    private static List<Technique> All() =>
        Directory.GetFiles(Directory_, "*.yaml").Select(f => Load(Path.GetFileName(f))).ToList();

    private static readonly Dictionary<string, char> CodeLetter = new()
    {
        [WazaGroups.Nage] = 'N', [WazaGroups.Osaekomi] = 'O', [WazaGroups.Shime] = 'S', [WazaGroups.Kansetsu] = 'K',
    };

    [Theory]
    [MemberData(nameof(Files))]
    public void ShippedTechnique_IsValid(string file)
    {
        var technique = Load(file);
        if (!technique.IsAnimated)
            return;
        var tracks = TechniqueTracks.Build(technique);

        Assert.NotNull(tracks.Tori.Position);
        Assert.NotNull(tracks.Uki.Position);
        Assert.Equal(technique.DurationSeconds, technique.Keyframes[^1].Time);
    }

    [Theory]
    [MemberData(nameof(Files))]
    public void ShippedTechnique_FollowsCatalogueConventions(string file)
    {
        var t = Load(file);

        Assert.Equal(t.TechniqueName.ToLowerInvariant().Replace('-', '_').Replace(' ', '_') + ".yaml", file);
        Assert.NotEmpty(t.DutchName);
        Assert.NotEmpty(t.Category);
        Assert.NotEmpty(t.Source);
        var grade = t.KyuGrade == KyuGrades.DanExtra ? "D" : t.KyuGrade.ToString();
        Assert.Matches(new Regex($"^{CodeLetter[t.WazaGroup]}{grade}-[0-9]+$"), t.Code);
        Assert.Equal(t.WazaGroup is WazaGroups.Shime or WazaGroups.Kansetsu, t.U18);
    }

    [Fact]
    public void Codes_AreUnique()
    {
        var duplicates = All().GroupBy(t => t.Code).Where(g => g.Count() > 1).Select(g => g.Key);
        Assert.Empty(duplicates);
    }

    [Fact]
    public void Catalogue_CoversVjfLeerlijnAndKodokan()
    {
        var all = All();

        // VJF leerlijn 2015: 20 nage-waza, 9 osaekomi-waza and 17 shime-/kansetsu-waza (U18).
        var vjf = all.Where(t => t.KyuGrade != KyuGrades.DanExtra).ToList();
        Assert.Equal(46, vjf.Count);
        Assert.Equal(20, vjf.Count(t => t.WazaGroup == WazaGroups.Nage));
        Assert.Equal(9, vjf.Count(t => t.WazaGroup == WazaGroups.Osaekomi));
        Assert.Equal(17, vjf.Count(t => t.U18));
        Assert.DoesNotContain(vjf, t => t.KyuGrade == 6); // white belt has no techniques of its own

        // Kodokan: 68 nage-waza and 32 katame-waza; makura-kesa-gatame is VJF-only.
        Assert.Equal(68, all.Count(t => t.WazaGroup == WazaGroups.Nage));
        Assert.Equal(33, all.Count(t => t.WazaGroup != WazaGroups.Nage));
    }

    [Fact]
    public void IpponSeoiNage_IsFourthKyu() =>
        Assert.Equal(4, Load("ippon_seoi_nage.yaml").KyuGrade);
}

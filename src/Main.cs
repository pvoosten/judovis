using System.Linq;
using Godot;
using JudoVisualizer.Data;
using JudoVisualizer.Playback;
using JudoVisualizer.UI;

namespace JudoVisualizer;

/// <summary>
/// Entry scene: loads the technique library into the HUD, dresses the judoka in the loaded
/// technique's belt colour and starts playing the first animated technique.
/// </summary>
public partial class Main : Node3D
{
    public override void _Ready()
    {
        GetNode<DirectionalLight3D>("Sun").RotationDegrees = new Vector3(-55, 35, 0);

        var player = GetNode<JudoTechniquePlayer>("Player");
        player.TechniqueChanged += () =>
        {
            if (player.Technique is null)
                return;
            var belt = Color.FromHtml(player.Technique.BeltColor.Hex);
            foreach (var judoka in new[] { player.Tori, player.Uki })
                if (judoka is not null)
                    JudokaAppearance.SetBeltColor(judoka, belt);
        };

        var techniques = TechniqueLoader.LoadDirectory();
        var animated = techniques.Where(t => t.IsAnimated).ToList();
        GD.Print($"Loaded {techniques.Count} techniques, {animated.Count} animated:");
        foreach (var t in animated)
            GD.Print($"  {t.Code} '{t.TechniqueName}' " +
                     $"({KyuGrades.Get(t.KyuGrade).BeltName}, {t.Keyframes.Count(k => !k.Inbetween)} keyframes + " +
                     $"{t.Keyframes.Count(k => k.Inbetween)} in-betweens, {t.DurationSeconds}s)");
        GetNode<HudController>("UI/Hud").SetTechniques(techniques);

        if (animated.Count > 0)
        {
            player.Load(animated[0]);
            player.Play();
        }
    }
}

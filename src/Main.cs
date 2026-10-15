using Godot;
using JudoVisualizer.Data;
using JudoVisualizer.Playback;
using JudoVisualizer.UI;

namespace JudoVisualizer;

/// <summary>
/// Entry scene: loads the technique library into the HUD, dresses the judoka in the loaded
/// technique's belt colour and starts playing the first technique.
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
        foreach (var t in techniques)
            GD.Print($"Loaded technique {t.Code} '{t.TechniqueName}' " +
                     $"({KyuGrades.Get(t.KyuGrade).BeltName}, {t.Keyframes.Count} keyframes, {t.DurationSeconds}s)");
        GetNode<HudController>("UI/Hud").SetTechniques(techniques);

        if (techniques.Count > 0)
        {
            player.Load(techniques[0]);
            player.Play();
        }
    }
}

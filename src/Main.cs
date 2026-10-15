using Godot;
using JudoVisualizer.Data;
using JudoVisualizer.Playback;

namespace JudoVisualizer;

/// <summary>Entry scene: loads the technique library and plays the first technique.</summary>
public partial class Main : Node3D
{
    public override void _Ready()
    {
        GetNode<DirectionalLight3D>("Sun").RotationDegrees = new Vector3(-55, 35, 0);

        var techniques = TechniqueLoader.LoadDirectory();
        foreach (var t in techniques)
            GD.Print($"Loaded technique {t.Code} '{t.TechniqueName}' " +
                     $"({KyuGrades.Get(t.KyuGrade).BeltName}, {t.Keyframes.Count} keyframes, {t.DurationSeconds}s)");

        if (techniques.Count > 0)
        {
            var player = GetNode<JudoTechniquePlayer>("Player");
            player.Load(techniques[0]);
            player.Play();
        }
    }
}

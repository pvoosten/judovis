using Godot;
using JudoVisualizer.Data;

namespace JudoVisualizer;

/// <summary>Entry scene. Loads the technique library; player, cameras and UI are added in later phases.</summary>
public partial class Main : Node3D
{
    public override void _Ready()
    {
        foreach (var t in TechniqueLoader.LoadDirectory())
            GD.Print($"Loaded technique {t.Code} '{t.TechniqueName}' " +
                     $"({KyuGrades.Get(t.KyuGrade).BeltName}, {t.Keyframes.Count} keyframes, {t.DurationSeconds}s)");
    }
}

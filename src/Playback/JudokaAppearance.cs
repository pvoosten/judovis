using System.Linq;
using Godot;

namespace JudoVisualizer.Playback;

/// <summary>Runtime appearance changes on a judoka model.</summary>
public static class JudokaAppearance
{
    /// <summary>Name of the belt material (band, knot and tails) in Tori.glb / Uki.glb.</summary>
    public const string BeltMaterial = "Belt";

    /// <summary>Recolours the belt of <paramref name="model"/>; other materials are untouched.</summary>
    public static void SetBeltColor(Node3D model, Color color)
    {
        foreach (var mesh in model.FindChildren("*", nameof(MeshInstance3D), true, false).OfType<MeshInstance3D>())
        {
            for (var i = 0; i < mesh.GetSurfaceOverrideMaterialCount(); i++)
            {
                if (mesh.GetSurfaceOverrideMaterial(i) is not BaseMaterial3D { ResourceName: BeltMaterial } belt)
                {
                    if (mesh.Mesh?.SurfaceGetMaterial(i) is not BaseMaterial3D { ResourceName: BeltMaterial } source)
                        continue;
                    belt = (BaseMaterial3D)source.Duplicate(); // own copy: models share the imported material
                    mesh.SetSurfaceOverrideMaterial(i, belt);
                }
                belt.AlbedoColor = color;
            }
        }
    }
}

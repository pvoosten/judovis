namespace JudoVisualizer.Data;

/// <summary>
/// Three floats as written in YAML: <c>[x, y, z]</c>. Positions are metres, rotations are
/// Euler XYZ degrees. Engine-independent so the data layer can be tested without Godot.
/// </summary>
public readonly record struct Vec3(float X, float Y, float Z)
{
    public static readonly Vec3 Zero = new(0, 0, 0);
}

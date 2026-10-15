using System;
using JudoVisualizer.Data;

namespace JudoVisualizer.Camera;

/// <summary>
/// Spectator orbit: the camera circles a target at a fixed height above the floor and looks at it.
/// Engine-independent so it can be unit tested.
/// </summary>
public sealed class OrbitModel
{
    public OrbitModel(float height, float azimuth, float distance, float minDistance, float maxDistance)
    {
        Height = height;
        MinDistance = minDistance;
        MaxDistance = maxDistance;
        Azimuth = Wrap(azimuth);
        Distance = Math.Clamp(distance, minDistance, maxDistance);
    }

    /// <summary>Camera height above the floor in metres; never changes while orbiting.</summary>
    public float Height { get; }

    public float MinDistance { get; }
    public float MaxDistance { get; }

    /// <summary>Radians around the target: 0 = camera on the target's +Z side, π/2 = +X side.</summary>
    public float Azimuth { get; private set; }

    /// <summary>Horizontal distance to the target in metres.</summary>
    public float Distance { get; private set; }

    /// <summary>Circle around the target; positive moves the camera to its own right (screen-relative).</summary>
    public void Orbit(float radians) => Azimuth = Wrap(Azimuth + radians);

    /// <summary>Move towards the target (positive) or away from it (negative), within the distance limits.</summary>
    public void Approach(float metres) => Distance = Math.Clamp(Distance - metres, MinDistance, MaxDistance);

    /// <summary>Camera position for a target; only the target's horizontal position matters.</summary>
    public Vec3 PositionFor(Vec3 target) =>
        new(target.X + MathF.Sin(Azimuth) * Distance, Height, target.Z + MathF.Cos(Azimuth) * Distance);

    private static float Wrap(float radians)
    {
        var r = radians % MathF.Tau;
        return r < 0 ? r + MathF.Tau : r;
    }
}

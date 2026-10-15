using JudoVisualizer.Camera;
using JudoVisualizer.Data;
using Xunit;

namespace JudoVisualizer.Tests;

public class OrbitModelTests
{
    private static OrbitModel Orbit(float azimuthDegrees = 90, float distance = 3) =>
        new(height: 1.6f, azimuth: azimuthDegrees * MathF.PI / 180, distance, minDistance: 1.5f, maxDistance: 8);

    [Theory]
    [InlineData(0f)]
    [InlineData(0.9f)]
    [InlineData(2.3f)]   // Uki in the air: the camera still does not rise
    public void Height_StaysFixed_WhateverTheTargetHeight(float targetHeight)
    {
        var orbit = Orbit();
        orbit.Orbit(1.0f);
        orbit.Approach(0.7f);

        Assert.Equal(1.6f, orbit.PositionFor(new Vec3(0.3f, targetHeight, 0.4f)).Y);
    }

    [Fact]
    public void StartsOnThePlusXSide_AtTheRequestedDistance()
    {
        var p = Orbit(90, 3).PositionFor(new Vec3(0, 1, 0.5f));

        Assert.Equal(3, p.X, 4);
        Assert.Equal(0.5f, p.Z, 4);
    }

    [Theory]
    [InlineData(0f)]
    [InlineData(90f)]
    [InlineData(225f)]
    public void OrbitRight_MovesTheCameraToItsOwnRight(float azimuthDegrees)
    {
        var target = new Vec3(0.2f, 1, 0.4f);
        var orbit = Orbit(azimuthDegrees);
        var before = orbit.PositionFor(target);

        orbit.Orbit(0.05f);
        var after = orbit.PositionFor(target);

        // Camera looks at the target; its right vector is forward x up = (-fz, 0, fx).
        var (fx, fz) = (target.X - before.X, target.Z - before.Z);
        var moved = (X: after.X - before.X, Z: after.Z - before.Z);
        Assert.True(moved.X * -fz + moved.Z * fx > 0, "orbiting right should move the camera to its right");
    }

    [Fact]
    public void Approach_MovesCloserAndIsClamped()
    {
        var orbit = Orbit(distance: 3);

        orbit.Approach(1);
        Assert.Equal(2, orbit.Distance, 4);

        orbit.Approach(10);
        Assert.Equal(1.5f, orbit.Distance);

        orbit.Approach(-100);
        Assert.Equal(8, orbit.Distance);
    }

    [Fact]
    public void Azimuth_WrapsAround()
    {
        var orbit = Orbit(10);
        orbit.Orbit(-MathF.PI);
        Assert.InRange(orbit.Azimuth, 0, MathF.Tau);
    }
}

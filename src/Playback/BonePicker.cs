using System.Collections.Generic;
using System.Numerics;

namespace JudoVisualizer.Playback;

/// <summary>A bone as a line segment in world space; <see cref="Who"/> is "tori" or "uki".</summary>
public readonly record struct BoneSegment(string Who, string Bone, Vector3 A, Vector3 B);

/// <summary>The segment hit by a mouse ray: <see cref="Along"/> 0..1 from the bone's origin to its tip.</summary>
public readonly record struct BoneHit(BoneSegment Segment, float Along, float Distance, float RayDistance);

/// <summary>Picks the bone nearest to a mouse ray (point-to-segment distance, no colliders).</summary>
public static class BonePicker
{
    /// <summary>Bones whose ray distances differ by less than this (metres) count as a tie: the one nearer the camera wins.</summary>
    public const float TieMetres = 0.01f;

    /// <param name="rayDirection">Normalised.</param>
    /// <param name="maxDistance">Largest ray-to-bone distance (metres) that still counts as a hit.</param>
    public static BoneHit? Pick(Vector3 rayOrigin, Vector3 rayDirection, IEnumerable<BoneSegment> segments, float maxDistance)
    {
        BoneHit? best = null;
        foreach (var segment in segments)
        {
            var (along, rayT) = Closest(rayOrigin, rayDirection, segment.A, segment.B);
            var point = segment.A + (segment.B - segment.A) * along;
            var distance = (point - (rayOrigin + rayDirection * rayT)).Length();
            if (distance > maxDistance)
                continue;
            var hit = new BoneHit(segment, along, distance, rayT);
            if (best is not { } b || Better(hit, b))
                best = hit;
        }
        return best;
    }

    private static bool Better(BoneHit hit, BoneHit best) =>
        System.Math.Abs(hit.Distance - best.Distance) <= TieMetres
            ? hit.RayDistance < best.RayDistance
            : hit.Distance < best.Distance;

    /// <summary>Closest points between the ray (t &gt;= 0) and the segment A-B: the parameter on the segment and on the ray.</summary>
    private static (float Along, float RayT) Closest(Vector3 origin, Vector3 dir, Vector3 a, Vector3 b)
    {
        var e = b - a;
        var r = a - origin;
        var eLen2 = Vector3.Dot(e, e);
        if (eLen2 < 1e-10f)
            return (0, System.Math.Max(0, Vector3.Dot(r, dir)));

        // Minimise |r + s*e - t*dir| over s and t (dir is a unit vector), then clamp s to the segment.
        var dirDotE = Vector3.Dot(dir, e);
        var denom = eLen2 - dirDotE * dirDotE;
        var along = denom < 1e-8f ? 0f // ray parallel to the segment
            : System.Math.Clamp((dirDotE * Vector3.Dot(dir, r) - Vector3.Dot(e, r)) / denom, 0, 1);
        var t = Vector3.Dot(r + e * along, dir);
        if (t < 0) // behind the camera: the ray is then just its origin
        {
            t = 0;
            along = System.Math.Clamp(-Vector3.Dot(r, e) / eLen2, 0, 1);
        }
        return (along, t);
    }
}

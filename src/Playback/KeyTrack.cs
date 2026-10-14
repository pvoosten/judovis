using System;
using System.Collections.Generic;
using System.Linq;
using JudoVisualizer.Data;

namespace JudoVisualizer.Playback;

/// <summary>Which two keys to blend at a given time: <c>value = lerp(From, To, Weight)</c>.</summary>
public readonly record struct KeySample(int From, int To, float Weight);

/// <summary>
/// Time-sorted keys of one animated value (a root position/rotation or one bone).
/// Only keyframes that actually set the value contribute keys, so values missing from a
/// keyframe are interpolated between their neighbours. Outside the keyed range the first or
/// last key is held.
/// </summary>
public sealed class KeyTrack
{
    private readonly float[] _times;

    /// <param name="keys">At least one key, in strictly increasing time order.</param>
    public KeyTrack(IEnumerable<(float Time, Vec3 Value)> keys)
    {
        var list = keys.ToList();
        if (list.Count == 0)
            throw new ArgumentException("A track needs at least one key.", nameof(keys));
        _times = list.Select(k => k.Time).ToArray();
        Values = list.Select(k => k.Value).ToArray();
    }

    public IReadOnlyList<float> Times => _times;

    /// <summary>Key values, indexed like <see cref="KeySample.From"/>/<see cref="KeySample.To"/>.</summary>
    public IReadOnlyList<Vec3> Values { get; }

    public KeySample Sample(float time)
    {
        var last = _times.Length - 1;
        if (time <= _times[0])
            return new(0, 0, 0);
        if (time >= _times[last])
            return new(last, last, 0);

        var i = Array.BinarySearch(_times, time);
        if (i >= 0)
            return new(i, i, 0);
        var to = ~i; // first key after time
        var from = to - 1;
        return new(from, to, (time - _times[from]) / (_times[to] - _times[from]));
    }
}

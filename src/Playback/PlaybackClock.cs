namespace JudoVisualizer.Playback;

/// <summary>Advances playback time, handling speed (negative = reverse) and looping.</summary>
public static class PlaybackClock
{
    /// <returns>
    /// The new time in <c>0..duration</c>, and whether a non-looping playback reached the end
    /// (or the start, when playing in reverse).
    /// </returns>
    public static (float Time, bool ReachedEnd) Advance(float time, float delta, float speed, float duration, bool loop)
    {
        if (duration <= 0)
            return (0, true);

        var t = time + delta * speed;
        if (loop)
        {
            t %= duration;
            return (t < 0 ? t + duration : t, false);
        }

        if (t >= duration)
            return (duration, true);
        if (t <= 0 && speed < 0)
            return (0, true);
        return (System.Math.Max(t, 0), false);
    }
}

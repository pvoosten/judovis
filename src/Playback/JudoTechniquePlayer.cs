using System.Collections.Generic;
using Godot;
using JudoVisualizer.Data;

namespace JudoVisualizer.Playback;

/// <summary>
/// Plays a <see cref="Data.Technique"/> on the Tori and Uki models: interpolates root positions
/// (lerp), root and bone rotations (slerp) between keyframes, and manages playback state.
/// A technique without animation (catalogue entry) shows both judoka in rest pose at their start
/// positions; playback calls then do nothing.
/// </summary>
public partial class JudoTechniquePlayer : Node3D
{
    /// <summary>Emitted whenever the pose is updated (playing, seeking or stepping).</summary>
    [Signal] public delegate void TimeChangedEventHandler(float time);

    /// <summary>Emitted when the shown phase changes: <paramref name="index"/> is the nearest keyframe.</summary>
    [Signal] public delegate void KeyframeChangedEventHandler(int index);

    /// <summary>Emitted after <see cref="Load"/>, before the first frame is shown.</summary>
    [Signal] public delegate void TechniqueChangedEventHandler();

    [Signal] public delegate void PlayingChangedEventHandler(bool playing);

    /// <summary>Root node of the Tori model (an instance of Tori.glb).</summary>
    [Export] public Node3D? Tori { get; set; }

    /// <summary>Root node of the Uki model (an instance of Uki.glb).</summary>
    [Export] public Node3D? Uki { get; set; }

    [Export] public bool Loop { get; set; } = true;

    /// <summary>Playback rate: 1 = real time, 0.25 = slow motion, negative = reverse.</summary>
    [Export] public float Speed { get; set; } = 1f;

    // Start positions from the YAML convention: Tori at the origin facing +Z, Uki facing Tori.
    private static readonly Vector3 UkiStart = new(0, 0, 1.2f);

    private TechniqueTracks? _tracks;
    private readonly List<JudokaRig> _rigs = [];

    public Technique? Technique { get; private set; }

    /// <summary>True when the loaded technique has keyframes and can be played.</summary>
    public bool CanPlay => _tracks is not null;
    public float Duration => _tracks?.Duration ?? 0;
    public float CurrentTime { get; private set; }
    public bool IsPlaying { get; private set; }

    /// <summary>Index (in the technique's keyframes) of the active authored keyframe, or -1 when nothing is loaded.</summary>
    public int CurrentKeyframeIndex { get; private set; } = -1;

    public Keyframe? CurrentKeyframe => CurrentKeyframeIndex >= 0 ? Technique!.Keyframes[CurrentKeyframeIndex] : null;

    /// <summary>Loads <paramref name="technique"/>, pauses and shows its first frame (or the rest pose).</summary>
    /// <param name="technique">A validated technique, e.g. from <see cref="TechniqueLoader"/>.</param>
    public void Load(Technique technique)
    {
        Pause();
        Technique = technique;
        _rigs.Clear();
        CurrentKeyframeIndex = -1;
        CurrentTime = 0;
        if (technique.IsAnimated)
        {
            _tracks = TechniqueTracks.Build(technique);
            Bind(Tori, nameof(Tori), _tracks.Tori);
            Bind(Uki, nameof(Uki), _tracks.Uki);
        }
        else
        {
            _tracks = null;
            ShowRestPose();
        }
        EmitSignal(SignalName.TechniqueChanged);
        if (_tracks is null)
            EmitSignal(SignalName.TimeChanged, 0f);
        else
            Seek(0);
    }

    /// <summary>Phase segments of the loaded technique (empty when nothing is loaded).</summary>
    public IReadOnlyList<PhaseSegment> Phases => _tracks?.Phases ?? [];

    /// <summary>Times of the authored keyframes (in-betweens left out); empty when nothing is playable.</summary>
    public IReadOnlyList<float> KeyframeTimes => _tracks?.AuthoredTimes ?? [];

    public void Play()
    {
        if (_tracks is null)
            return;
        if (!Loop && AtEnd)
            Seek(Speed >= 0 ? 0 : Duration);
        SetPlaying(true);
    }

    public void Pause() => SetPlaying(false);

    public void TogglePlay()
    {
        if (IsPlaying)
            Pause();
        else
            Play();
    }

    /// <summary>Pauses and rewinds to the start.</summary>
    public void Stop()
    {
        Pause();
        Seek(0);
    }

    /// <summary>Jumps to <paramref name="time"/> (clamped to the technique) without changing play state.</summary>
    public void Seek(float time)
    {
        if (_tracks is null)
            return;
        CurrentTime = Mathf.Clamp(time, 0, Duration);
        Apply();
    }

    /// <summary>Pauses and moves by <paramref name="seconds"/> (negative = backwards); for frame stepping.</summary>
    public void Step(float seconds)
    {
        Pause();
        Seek(CurrentTime + seconds);
    }

    /// <summary>Pauses and jumps to the next (direction &gt; 0) or previous keyframe, if any.</summary>
    public void StepKeyframe(int direction)
    {
        if (_tracks is null)
            return;
        var target = direction > 0 ? _tracks.NextKeyframeTime(CurrentTime) : _tracks.PreviousKeyframeTime(CurrentTime);
        Pause();
        if (target is { } t)
            Seek(t);
    }

    public override void _Process(double delta)
    {
        if (!IsPlaying || _tracks is null)
            return;
        var (time, reachedEnd) = PlaybackClock.Advance(CurrentTime, (float)delta, Speed, Duration, Loop);
        CurrentTime = time;
        Apply();
        if (reachedEnd)
            Pause();
    }

    private bool AtEnd => Speed >= 0 ? CurrentTime >= Duration : CurrentTime <= 0;

    private void ShowRestPose()
    {
        foreach (var (model, position, yaw) in new[] { (Tori, Vector3.Zero, 0f), (Uki, UkiStart, Mathf.Pi) })
        {
            if (model is null)
                continue;
            model.Position = position;
            model.Quaternion = new Quaternion(Vector3.Up, yaw);
            JudokaRig.FindSkeleton(model)?.ResetBonePoses();
        }
    }

    private void Bind(Node3D? model, string role, JudokaTracks tracks)
    {
        if (model is null)
            GD.PushError($"{Name}: {role} is not assigned; it will not be animated.");
        else
            _rigs.Add(new JudokaRig(model, tracks));
    }

    private void Apply()
    {
        foreach (var rig in _rigs)
            rig.Apply(CurrentTime);

        var keyframe = _tracks!.KeyframeIndexAt(CurrentTime);
        if (keyframe != CurrentKeyframeIndex)
        {
            CurrentKeyframeIndex = keyframe;
            EmitSignal(SignalName.KeyframeChanged, keyframe);
        }
        EmitSignal(SignalName.TimeChanged, CurrentTime);
    }

    private void SetPlaying(bool playing)
    {
        if (playing == IsPlaying)
            return;
        IsPlaying = playing;
        EmitSignal(SignalName.PlayingChanged, playing);
    }
}

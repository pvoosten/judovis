using System;
using System.Collections.Generic;
using Godot;
using JudoVisualizer.Playback;

namespace JudoVisualizer.UI;

/// <summary>
/// Timeline scrubber: shows the phases as labelled bands, a tick per keyframe and the playhead.
/// Click or drag to scrub.
/// </summary>
public partial class PhaseTimeline : Control
{
    public event Action? ScrubStarted;
    public event Action<float>? Scrubbed;
    public event Action? ScrubEnded;

    private static readonly Color[] BandColors = [new(0.22f, 0.26f, 0.32f), new(0.28f, 0.32f, 0.39f)];
    private static readonly Color ActiveBand = new(0.36f, 0.42f, 0.52f);

    private const float LabelHeight = 18f;
    private const float BandHeight = 16f;
    private const int FontSize = 12;

    private IReadOnlyList<PhaseSegment> _phases = [];
    private IReadOnlyList<float> _keyframeTimes = [];
    private float _duration;
    private float _time;
    private int _active = -1;
    private bool _dragging;

    public override void _Ready()
    {
        CustomMinimumSize = new Vector2(0, LabelHeight + BandHeight + 4);
        SizeFlagsHorizontal = SizeFlags.ExpandFill;
        MouseDefaultCursorShape = CursorShape.PointingHand;
        TooltipText = "Click or drag to scrub";
    }

    public void SetTechnique(IReadOnlyList<PhaseSegment> phases, IReadOnlyList<float> keyframeTimes, float duration)
    {
        _phases = phases;
        _keyframeTimes = keyframeTimes;
        _duration = duration;
        QueueRedraw();
    }

    public void SetTime(float time, int activeKeyframe)
    {
        _time = time;
        _active = activeKeyframe;
        QueueRedraw();
    }

    public override void _Draw()
    {
        if (_duration <= 0)
            return;
        var font = GetThemeDefaultFont();
        var bandTop = LabelHeight;

        foreach (var phase in _phases)
        {
            var x0 = X(phase.Start);
            var x1 = X(phase.End);
            var color = phase.KeyframeIndex == _active ? ActiveBand : BandColors[phase.KeyframeIndex % 2];
            DrawRect(new Rect2(x0, bandTop, x1 - x0, BandHeight), color);

            var label = TechniqueCatalog.ShortPhase(phase.Phase);
            var width = x1 - x0;
            if (font.GetStringSize(label, HorizontalAlignment.Left, -1, FontSize).X <= width - 4)
                DrawString(font, new Vector2(x0, LabelHeight - 5), label, HorizontalAlignment.Center, width, FontSize,
                           phase.KeyframeIndex == _active ? UiStyle.Accent : UiStyle.Muted);
        }

        foreach (var t in _keyframeTimes)
        {
            DrawLine(new Vector2(X(t), bandTop + 3), new Vector2(X(t), bandTop + BandHeight - 3), UiStyle.Muted, 1);
        }

        var head = X(_time);
        DrawLine(new Vector2(head, bandTop - 2), new Vector2(head, bandTop + BandHeight + 2), UiStyle.Accent, 2);
        DrawCircle(new Vector2(head, bandTop + BandHeight / 2), 5, UiStyle.Accent);
    }

    public override void _GuiInput(InputEvent e)
    {
        switch (e)
        {
            case InputEventMouseButton { ButtonIndex: MouseButton.Left } button:
                if (button.Pressed && !_dragging)
                {
                    _dragging = true;
                    ScrubStarted?.Invoke();
                    Scrubbed?.Invoke(TimeAt(button.Position.X));
                }
                else if (!button.Pressed && _dragging)
                {
                    _dragging = false;
                    ScrubEnded?.Invoke();
                }
                AcceptEvent();
                break;
            case InputEventMouseMotion motion when _dragging:
                Scrubbed?.Invoke(TimeAt(motion.Position.X));
                AcceptEvent();
                break;
        }
    }

    private float X(float time) => _duration <= 0 ? 0 : Size.X * Math.Clamp(time / _duration, 0, 1);

    private float TimeAt(float x) => _duration * Math.Clamp(x / Math.Max(Size.X, 1), 0, 1);
}

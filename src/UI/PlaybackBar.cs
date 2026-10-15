using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Godot;
using JudoVisualizer.Camera;
using JudoVisualizer.Playback;

namespace JudoVisualizer.UI;

/// <summary>
/// Playback controls: phase timeline/scrubber, play/pause, frame and keyframe stepping,
/// speed (slow motion), reverse, loop and the camera perspective.
/// </summary>
public partial class PlaybackBar : PanelContainer
{
    public static readonly float[] SpeedPresets = [0.1f, 0.25f, 0.5f, 1f, 2f];

    /// <summary>One "frame" for the step buttons, in seconds of technique time.</summary>
    public const float FrameStep = 1f / 30f;

    private JudoTechniquePlayer? _player;
    private PhaseTimeline _timeline = null!;
    private readonly List<Button> _transport = []; // disabled for a technique without animation
    private Button _play = null!;
    private Label _time = null!;
    private OptionButton _speed = null!;
    private CheckBox _reverse = null!;
    private CheckBox _loop = null!;
    private OptionButton _camera = null!;
    private bool _resumeAfterScrub;

    public override void _Ready()
    {
        AddThemeStyleboxOverride("panel", UiStyle.Panel());
        var column = new VBoxContainer();
        column.AddThemeConstantOverride("separation", 6);
        AddChild(column);

        _timeline = new PhaseTimeline();
        column.AddChild(_timeline);

        var row = new HBoxContainer();
        row.AddThemeConstantOverride("separation", 6);
        column.AddChild(row);

        row.AddChild(Button("|<", "Previous keyframe", () => _player?.StepKeyframe(-1)));
        row.AddChild(Button("<", "Step one frame back ( , )", () => _player?.Step(-FrameStep)));
        _play = Button("Play", "Play / pause (Space)", () => _player?.TogglePlay());
        _play.CustomMinimumSize = new Vector2(64, 0);
        row.AddChild(_play);
        row.AddChild(Button(">", "Step one frame forward ( . )", () => _player?.Step(FrameStep)));
        row.AddChild(Button(">|", "Next keyframe", () => _player?.StepKeyframe(1)));
        _transport.AddRange(row.GetChildren().OfType<Button>());

        _time = UiStyle.Label("", 14, UiStyle.Muted);
        _time.CustomMinimumSize = new Vector2(96, 0);
        _time.HorizontalAlignment = HorizontalAlignment.Center;
        row.AddChild(_time);

        row.AddChild(new Control { SizeFlagsHorizontal = SizeFlags.ExpandFill });

        row.AddChild(UiStyle.Label("Speed"));
        _speed = UiStyle.NoFocus(new OptionButton { TooltipText = "Playback speed (slow motion)" });
        foreach (var speed in SpeedPresets)
            _speed.AddItem(speed.ToString("0.##", CultureInfo.InvariantCulture) + "x");
        _speed.Selected = System.Array.IndexOf(SpeedPresets, 1f);
        _speed.ItemSelected += _ => ApplySpeed();
        row.AddChild(_speed);

        _reverse = UiStyle.NoFocus(new CheckBox { Text = "Reverse", TooltipText = "Play backwards" });
        _reverse.Toggled += _ => ApplySpeed();
        row.AddChild(_reverse);

        _loop = UiStyle.NoFocus(new CheckBox { Text = "Loop", ButtonPressed = true });
        _loop.Toggled += on =>
        {
            if (_player is not null)
                _player.Loop = on;
        };
        row.AddChild(_loop);

        row.AddChild(new VSeparator());
        row.AddChild(UiStyle.Label("Camera"));
        _camera = UiStyle.NoFocus(new OptionButton { TooltipText = "Perspective (1 / 2 / 3, C to cycle)" });
        _camera.AddItem("Orbit", (int)CameraMode.Orbit);
        _camera.AddItem("Tori POV", (int)CameraMode.ToriPov);
        _camera.AddItem("Uki POV", (int)CameraMode.UkiPov);
        row.AddChild(_camera);
    }

    public void Bind(JudoTechniquePlayer player, CameraManager? cameraManager)
    {
        _player = player;
        _loop.SetPressedNoSignal(player.Loop);
        ApplySpeed();

        player.TechniqueChanged += () =>
        {
            _timeline.SetTechnique(
                player.Phases, player.Technique?.Keyframes.Select(k => k.Time).ToList() ?? [], player.Duration);
            _timeline.MouseFilter = player.CanPlay ? MouseFilterEnum.Stop : MouseFilterEnum.Ignore;
            foreach (var button in _transport)
                button.Disabled = !player.CanPlay;
        };
        player.TimeChanged += time =>
        {
            _timeline.SetTime(time, player.CurrentKeyframeIndex);
            _time.Text = player.CanPlay
                ? string.Create(CultureInfo.InvariantCulture, $"{time:0.00} / {player.Duration:0.00} s")
                : "–";
        };
        player.PlayingChanged += playing => _play.Text = playing ? "Pause" : "Play";

        _timeline.ScrubStarted += () =>
        {
            _resumeAfterScrub = player.IsPlaying;
            player.Pause();
        };
        _timeline.Scrubbed += time => player.Seek(time);
        _timeline.ScrubEnded += () =>
        {
            if (_resumeAfterScrub)
                player.Play();
        };

        if (cameraManager is null)
        {
            _camera.Disabled = true;
            return;
        }
        _camera.Select(_camera.GetItemIndex((int)cameraManager.Mode));
        _camera.ItemSelected += index => cameraManager.SetMode((CameraMode)_camera.GetItemId((int)index));
        cameraManager.ModeChanged += mode => _camera.Select(_camera.GetItemIndex((int)mode));
    }

    private void ApplySpeed()
    {
        if (_player is null)
            return;
        var speed = SpeedPresets[_speed.Selected];
        _player.Speed = _reverse.ButtonPressed ? -speed : speed;
    }

    private static Button Button(string text, string tooltip, System.Action pressed)
    {
        var button = UiStyle.NoFocus(new Button { Text = text, TooltipText = tooltip, CustomMinimumSize = new Vector2(36, 0) });
        button.Pressed += pressed;
        return button;
    }
}

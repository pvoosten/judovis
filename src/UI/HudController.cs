using System.Collections.Generic;
using Godot;
using JudoVisualizer.Camera;
using JudoVisualizer.Data;
using JudoVisualizer.Playback;

namespace JudoVisualizer.UI;

/// <summary>
/// Root of the HUD (scenes/ui/Hud.tscn): connects the technique browser, caption and playback bar
/// to the <see cref="JudoTechniquePlayer"/> and <see cref="CameraManager"/>.
/// Keyboard: Space = play/pause, comma/period = step one frame back/forward,
/// F2 = pose feedback panel (dev: comment on a bone while paused, see <see cref="PoseFeedback"/>),
/// F3 = pose editor (dev: adjust the judoka and insert keyframes, see <see cref="PoseEditor"/>).
/// </summary>
public partial class HudController : Control
{
    [Export] public JudoTechniquePlayer? Player { get; set; }
    [Export] public CameraManager? CameraManager { get; set; }

    private static readonly (string Action, Key Key)[] Bindings =
    [
        ("playback_toggle", Key.Space), ("playback_step_back", Key.Comma), ("playback_step_forward", Key.Period),
    ];

    private TechniqueBrowser _browser = null!;

    public override void _Ready()
    {
        MouseFilter = MouseFilterEnum.Ignore; // empty HUD area: mouse goes to the 3D view / orbit camera
        foreach (var (action, key) in Bindings)
        {
            if (InputMap.HasAction(action))
                continue;
            InputMap.AddAction(action);
            InputMap.ActionAddEvent(action, new InputEventKey { PhysicalKeycode = key });
        }

        _browser = GetNode<TechniqueBrowser>("Browser");
        if (Player is null)
        {
            GD.PushError($"{Name}: Player is not assigned.");
            return;
        }

        GetNode<TechniqueCaption>("Caption").Bind(Player);
        GetNode<PlaybackBar>("PlaybackBar").Bind(Player, CameraManager);
        _browser.TechniqueSelected += technique =>
        {
            Player.Load(technique);
            Player.Play();
        };
        Player.TechniqueChanged += () => _browser.Select(Player.Technique);

        if (!OS.HasFeature("template")) // dev tool: not in exported builds
        {
            var feedback = new PoseFeedback();
            AddChild(feedback);
            feedback.Bind(Player, CameraManager);
            var editor = new PoseEditor(); // after the browser's TechniqueChanged handler: it swaps in the edited technique
            AddChild(editor);
            editor.Bind(Player, CameraManager);
            feedback.Opened += editor.Close; // one click tool at a time
            editor.Opened += feedback.Close;
        }
    }

    /// <summary>Fills the technique browser.</summary>
    public void SetTechniques(IReadOnlyList<Technique> techniques) => _browser.SetTechniques(techniques);

    public override void _UnhandledInput(InputEvent e)
    {
        if (Player is null)
            return;
        if (e.IsActionPressed("playback_toggle"))
            Player.TogglePlay();
        else if (e.IsActionPressed("playback_step_back", allowEcho: true))
            Player.Step(-PlaybackBar.FrameStep);
        else if (e.IsActionPressed("playback_step_forward", allowEcho: true))
            Player.Step(PlaybackBar.FrameStep);
        else
            return;
        GetViewport().SetInputAsHandled();
    }
}

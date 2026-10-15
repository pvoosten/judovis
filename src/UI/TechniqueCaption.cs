using Godot;
using JudoVisualizer.Playback;

namespace JudoVisualizer.UI;

/// <summary>Caption over the 3D view: the loaded technique and its current phase.</summary>
public partial class TechniqueCaption : PanelContainer
{
    private Label _name = null!;
    private Label _phase = null!;

    public override void _Ready()
    {
        MouseFilter = MouseFilterEnum.Ignore;
        AddThemeStyleboxOverride("panel", UiStyle.Panel());
        var column = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        AddChild(column);
        _name = UiStyle.Label("", 26);
        _phase = UiStyle.Label("", 18, UiStyle.Accent);
        foreach (var label in new[] { _name, _phase })
        {
            label.HorizontalAlignment = HorizontalAlignment.Center;
            column.AddChild(label);
        }
        Visible = false;
    }

    public void Bind(JudoTechniquePlayer player)
    {
        player.TechniqueChanged += () =>
        {
            _name.Text = player.Technique?.TechniqueName ?? "";
            Visible = player.Technique is not null;
        };
        player.KeyframeChanged += index => _phase.Text = player.Technique?.Keyframes[index].Phase ?? "";
    }
}

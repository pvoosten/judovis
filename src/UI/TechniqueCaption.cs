using Godot;
using JudoVisualizer.Playback;

namespace JudoVisualizer.UI;

/// <summary>
/// Caption over the 3D view: the loaded technique, its Dutch name and current phase; for a
/// technique without animation its details and "Nog geen animatie" instead of the phase.
/// </summary>
public partial class TechniqueCaption : PanelContainer
{
    private Label _name = null!;
    private Label _dutchName = null!;
    private Label _details = null!;
    private Label _phase = null!;

    public override void _Ready()
    {
        MouseFilter = MouseFilterEnum.Ignore;
        AddThemeStyleboxOverride("panel", UiStyle.Panel());
        var column = new VBoxContainer { MouseFilter = MouseFilterEnum.Ignore };
        AddChild(column);
        _name = UiStyle.Label("", 26);
        _dutchName = UiStyle.Label("", 15, UiStyle.Muted);
        _details = UiStyle.Label("", 13, UiStyle.Muted);
        _phase = UiStyle.Label("", 18, UiStyle.Accent);
        foreach (var label in new[] { _name, _dutchName, _details, _phase })
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
            var technique = player.Technique;
            Visible = technique is not null;
            if (technique is null)
                return;
            _name.Text = technique.TechniqueName;
            _dutchName.Text = technique.DutchName;
            _dutchName.Visible = technique.DutchName.Length > 0;
            _details.Text = TechniqueCatalog.Details(technique);
            _details.Visible = !technique.IsAnimated;
            _phase.Text = technique.IsAnimated ? "" : TechniqueCatalog.NotAnimated;
            _phase.AddThemeColorOverride("font_color", technique.IsAnimated ? UiStyle.Accent : UiStyle.Disabled);
        };
        player.KeyframeChanged += index => _phase.Text = player.Technique?.Keyframes[index].Phase ?? "";
    }
}

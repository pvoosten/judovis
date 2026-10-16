using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Godot;
using JudoVisualizer.Camera;
using JudoVisualizer.Data;
using JudoVisualizer.Playback;

namespace JudoVisualizer.UI;

/// <summary>
/// Dev tool (F2): while a technique is paused, left-click a limb of Tori or Uki to pick the bone nearest
/// the mouse ray, type a short comment and save it to <c>feedback/&lt;technique&gt;.yaml</c>.
/// Inert unless switched on and paused; a click without a drag selects, a drag still orbits.
/// The comments become a prompt with <c>dotnet run --project tools/feedback</c>.
/// </summary>
public partial class PoseFeedback : PanelContainer
{
    private const float PickMetres = 0.07f;
    private const float ClickPixels = 5f;

    private JudoTechniquePlayer _player = null!;
    private CameraManager? _cameras;
    private Label _selection = null!;
    private LineEdit _text = null!;
    private Button _save = null!;
    private VBoxContainer _list = null!;
    private Label _listTitle = null!;
    private MeshInstance3D _marker = null!;
    private Label3D _markerLabel = null!;

    private List<FeedbackEntry> _entries = [];
    private (string Who, string Bone, float Along, float Time, string Phase)? _picked;
    private Vector2? _pressAt;

    public void Bind(JudoTechniquePlayer player, CameraManager? cameras)
    {
        _player = player;
        _cameras = cameras;
        Visible = false;
        BuildMarker();
        BuildPanel();

        player.TechniqueChanged += () =>
        {
            Deselect();
            LoadEntries();
        };
        player.PlayingChanged += playing =>
        {
            if (playing)
                Deselect();
        };
        player.TimeChanged += time =>
        {
            if (_picked is { } p && Mathf.Abs(p.Time - time) > 0.006f) // p.Time is rounded to 0.01
                Deselect(); // the marker would no longer sit where the comment was meant
        };
    }

    public override void _Process(double delta)
    {
        if (_picked is not { } p)
            return;
        var segment = Segments(p.Who).FirstOrDefault(s => s.Bone == p.Bone);
        if (segment == default)
        {
            Deselect();
            return;
        }
        _marker.GlobalPosition = segment.A.Lerp(segment.B, p.Along);
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if (e is InputEventKey { Pressed: true, Echo: false, PhysicalKeycode: Key.F2 })
        {
            Toggle();
            GetViewport().SetInputAsHandled();
            return;
        }
        if (!Visible || e is not InputEventMouseButton { ButtonIndex: MouseButton.Left } button)
            return;

        if (button.Pressed)
        {
            _pressAt = button.Position;
            return;
        }
        var wasClick = _pressAt is { } at && at.DistanceTo(button.Position) <= ClickPixels;
        _pressAt = null;
        if (wasClick && !_player.IsPlaying && _player.CanPlay)
            Select(button.Position);
    }

    private void Toggle()
    {
        Visible = !Visible;
        if (!Visible)
            Deselect();
        else
            LoadEntries();
    }

    private void Select(Vector2 mouse)
    {
        _text.ReleaseFocus();
        var camera = _cameras?.Camera;
        if (camera is null)
            return;

        var origin = camera.ProjectRayOrigin(mouse);
        var direction = camera.ProjectRayNormal(mouse);
        var segments = Segments("tori").Concat(Segments("uki"))
            .Select(s => new BoneSegment(s.Who, s.Bone, ToNumerics(s.A), ToNumerics(s.B)));
        if (BonePicker.Pick(ToNumerics(origin), ToNumerics(direction), segments, PickMetres) is not { } hit)
        {
            Deselect();
            return;
        }

        var phase = _player.CurrentKeyframe?.Phase ?? "";
        _picked = (hit.Segment.Who, hit.Segment.Bone, hit.Along, FeedbackFile.RoundTime(_player.CurrentTime), phase);
        var label = $"{hit.Segment.Who} · {FeedbackFile.BoneKey(hit.Segment.Bone)} · {Seconds(_picked.Value.Time)} s";
        _selection.Text = label;
        _markerLabel.Text = label;
        _marker.Visible = true;
        _save.Disabled = false;
        _text.GrabFocus();
    }

    private void Deselect()
    {
        _picked = null;
        _marker.Visible = false;
        _save.Disabled = true;
        _selection.Text = "Klik op een lichaamsdeel (op pauze).";
        _text.Text = "";
        _text.ReleaseFocus();
    }

    private void Save()
    {
        if (_picked is not { } p || _player.Technique is null)
            return;
        var text = _text.Text.Trim();
        if (text.Length == 0)
            return;

        _entries.Add(new FeedbackEntry
        {
            Technique = Slug(), Time = p.Time, Phase = p.Phase, Who = p.Who,
            Bone = FeedbackFile.BoneKey(p.Bone), Text = text,
        });
        Persist();
        Deselect();
    }

    private void Persist()
    {
        _entries = FeedbackFile.Sorted(_entries);
        FeedbackFile.Save(PathForTechnique(), _entries);
        RefreshList();
    }

    private void LoadEntries()
    {
        _entries = _player.Technique is null ? [] : FeedbackFile.Sorted(FeedbackFile.Load(PathForTechnique()));
        RefreshList();
    }

    private void RefreshList()
    {
        foreach (var child in _list.GetChildren())
            child.QueueFree();
        _listTitle.Text = $"Opmerkingen ({_entries.Count})";
        foreach (var entry in _entries.ToList())
        {
            var row = new HBoxContainer();
            var label = UiStyle.Label($"{Seconds(entry.Time)} s {entry.Who}.{entry.Bone}: {entry.Text}" +
                                      (entry.IsOpen ? "" : " (klaar)"), 13, entry.IsOpen ? null : UiStyle.Disabled);
            label.SizeFlagsHorizontal = SizeFlags.ExpandFill;
            label.AutowrapMode = TextServer.AutowrapMode.WordSmart;
            row.AddChild(label);
            var delete = UiStyle.NoFocus(new Button { Text = "✕", TooltipText = "Verwijder deze opmerking" });
            delete.Pressed += () =>
            {
                _entries.Remove(entry);
                Persist();
            };
            row.AddChild(delete);
            _list.AddChild(row);
        }
    }

    private string Slug() => FeedbackFile.Slug(_player.Technique?.TechniqueName ?? "");

    private string PathForTechnique() =>
        FeedbackFile.PathFor(ProjectSettings.GlobalizePath("res://" + FeedbackExporter.FeedbackDirectory), Slug());

    private IEnumerable<(string Who, string Bone, Vector3 A, Vector3 B)> Segments(string who)
    {
        var model = who == "tori" ? _player.Tori : _player.Uki;
        return model is null ? [] : JudokaRig.BoneSegments(model).Select(s => (who, s.Bone, s.A, s.B));
    }

    private static System.Numerics.Vector3 ToNumerics(Vector3 v) => new(v.X, v.Y, v.Z);

    private static string Seconds(float t) => t.ToString("0.00", CultureInfo.InvariantCulture);

    private void BuildPanel()
    {
        AnchorLeft = AnchorRight = 1;
        OffsetLeft = -340;
        OffsetRight = -10;
        OffsetTop = 10;
        GrowHorizontal = GrowDirection.Begin;
        AddThemeStyleboxOverride("panel", UiStyle.Panel());

        var column = new VBoxContainer();
        column.AddThemeConstantOverride("separation", 6);
        AddChild(column);

        column.AddChild(UiStyle.Label("Pose-feedback (F2 = aan/uit)", 15, UiStyle.Accent));
        column.AddChild(UiStyle.Label("Pauzeer, klik op een lichaamsdeel en typ wat er niet klopt.", 12, UiStyle.Muted));
        _selection = UiStyle.Label("", 13);
        column.AddChild(_selection);

        _text = new LineEdit { PlaceholderText = "bijv. elleboog te laag", ClearButtonEnabled = true };
        _text.TextSubmitted += _ => Save();
        column.AddChild(_text);

        var buttons = new HBoxContainer();
        _save = UiStyle.NoFocus(new Button { Text = "Opslaan" });
        _save.Pressed += Save;
        var cancel = UiStyle.NoFocus(new Button { Text = "Annuleren" });
        cancel.Pressed += Deselect;
        buttons.AddChild(_save);
        buttons.AddChild(cancel);
        column.AddChild(buttons);

        column.AddChild(new HSeparator());
        _listTitle = UiStyle.Label("", 13, UiStyle.Muted);
        column.AddChild(_listTitle);
        var scroll = new ScrollContainer { CustomMinimumSize = new Vector2(0, 150), HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled };
        _list = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill };
        scroll.AddChild(_list);
        column.AddChild(scroll);
        Deselect();
    }

    private void BuildMarker()
    {
        var material = new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded, AlbedoColor = UiStyle.Accent, NoDepthTest = true,
        };
        _marker = new MeshInstance3D
        {
            Mesh = new SphereMesh { Radius = 0.025f, Height = 0.05f },
            MaterialOverride = material,
            TopLevel = true,
            Visible = false,
        };
        _markerLabel = new Label3D
        {
            Billboard = BaseMaterial3D.BillboardModeEnum.Enabled, NoDepthTest = true, FixedSize = true,
            PixelSize = 0.0007f, FontSize = 36, OutlineSize = 12, Position = new Vector3(0, 0.07f, 0),
        };
        _marker.AddChild(_markerLabel);
        _player.AddChild(_marker);
    }
}

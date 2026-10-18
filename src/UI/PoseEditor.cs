using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Godot;
using JudoVisualizer.Camera;
using JudoVisualizer.Data;
using JudoVisualizer.Playback;

namespace JudoVisualizer.UI;

/// <summary>
/// Dev tool (F3): adjust Tori and Uki at a keyframe and insert keyframes. Click a limb (or pick it from the
/// list), set its rotation (the root also its position) with the sliders, and choose over which keyframes the
/// change fades in and out. Every change is saved straight away in <c>edits/&lt;technique&gt;.json</c> and
/// shown at once (<see cref="PoseEditing.Apply"/> on top of the YAML). The next Blender run of the technique
/// applies the same edits after its own tools (<c>tools/blender/edits.py</c>): they win over the script and
/// end up in the YAML. Ctrl+Z undoes.
/// </summary>
public partial class PoseEditor : PanelContainer
{
    private const float ClickPixels = 5f;
    private const float OnKeyframe = 0.006f; // s: the playhead counts as on a keyframe (time rounding)
    private const ulong GestureMs = 700;     // changes closer together than this are one undo step

    private static readonly string[] Who = ["tori", "uki"];
    private static readonly string[] Axes = ["X", "Y", "Z"];

    private JudoTechniquePlayer _player = null!;
    private CameraManager? _cameras;

    private Technique? _base; // as loaded from the YAML, without edits
    private PoseEditFile _file = new();
    private string _path = "";
    private List<float> _keyframes = []; // what the editor steps through: the YAML's keyframes + the edits' ones
    private string _who = "tori";
    private string _bone = PoseEdit.Root; // skeleton bone name or PoseEdit.Root
    private (string Key, (float From, float HoldFrom, float HoldTo, float To) Range, string Ease)? _pending;

    private readonly List<string> _undo = [];
    private string _gesture = "";
    private ulong _gestureAt;
    private bool _quiet; // set while the code itself updates controls or rebuilds
    private Vector2? _pressAt;

    private Label _keyframe = null!;
    private Button _previous = null!, _next = null!, _insert = null!, _delete = null!, _undoButton = null!;
    private OptionButton _whoOption = null!, _boneOption = null!, _ease = null!;
    private readonly (HSlider Slider, SpinBox Box)[] _rotation = new (HSlider, SpinBox)[3];
    private readonly (HSlider Slider, SpinBox Box)[] _position = new (HSlider, SpinBox)[3];
    private VBoxContainer _positionRows = null!, _list = null!;
    private Control _editControls = null!;
    private readonly OptionButton[] _range = new OptionButton[4]; // from, hold from, hold to, to
    private Label _status = null!, _listTitle = null!;
    private MeshInstance3D _marker = null!;

    /// <summary>Raised when the panel opens (the HUD then closes the pose feedback panel).</summary>
    public event System.Action? Opened;

    public void Bind(JudoTechniquePlayer player, CameraManager? cameras)
    {
        _player = player;
        _cameras = cameras;
        Visible = false;
        BuildMarker();
        BuildPanel();
        BuildHint();

        player.TechniqueChanged += LoadEdits; // a newly loaded technique: apply its edits (even with the panel closed)
        player.TimeChanged += _ => Refresh();
        player.PlayingChanged += _ => Refresh();
    }

    public void Close()
    {
        if (Visible)
            Toggle();
    }

    // --- loading, applying, saving -----------------------------------------------------------------

    private void LoadEdits()
    {
        _base = _player.Technique is { IsAnimated: true } t ? t : null;
        _undo.Clear();
        _pending = null;
        _path = _base is null ? "" : PoseEditFile.PathFor(ProjectSettings.GlobalizePath("res://" + PoseEditFile.Directory), _base.TechniqueName);
        try
        {
            _file = _base is null ? new PoseEditFile() : PoseEditFile.Load(_path);
        }
        catch (System.Exception e) when (e is System.Text.Json.JsonException or System.IO.IOException)
        {
            GD.PushError($"{_path}: {e.Message}");
            _file = new PoseEditFile();
        }
        if (_base is not null && !_file.IsEmpty)
            Rebuild();
        else
            UpdateKeyframes();
        Refresh();
    }

    /// <summary>Shows the base technique with the edits applied, at the same time.</summary>
    private void Rebuild()
    {
        if (_base is null)
            return;
        _quiet = true;
        _player.ReplaceTechnique(PoseEditing.Apply(_base, _file));
        _quiet = false;
        UpdateKeyframes();
    }

    private void Changed(bool rebuild = true)
    {
        try
        {
            _file.Save(_path);
        }
        catch (System.IO.IOException e)
        {
            GD.PushError($"{_path}: {e.Message}");
        }
        if (rebuild)
            Rebuild();
        RefreshList();
        Refresh();
    }

    /// <summary>Remembers the edits for Ctrl+Z, once per gesture (a slider drag, typing in a field).</summary>
    private void PushUndo(string gesture)
    {
        var now = Time.GetTicksMsec();
        if (gesture != _gesture || now - _gestureAt > GestureMs)
            _undo.Add(_file.Serialize());
        _gesture = gesture;
        _gestureAt = now;
    }

    private void Undo()
    {
        if (_undo.Count == 0 || _base is null)
            return;
        _file = PoseEditFile.Parse(_undo[^1]);
        _undo.RemoveAt(_undo.Count - 1);
        _gesture = "";
        Changed();
    }

    private void UpdateKeyframes()
    {
        var keyframes = new List<float>();
        if (_base is not null)
            foreach (var t in _base.Keyframes.Select(k => k.Time).Concat(PoseEditing.EditTimes(_file)).Order())
                if (keyframes.Count == 0 || t - keyframes[^1] > PoseEditing.TimeEpsilon)
                    keyframes.Add(t);
        RefreshList();
        if (keyframes.SequenceEqual(_keyframes) && _range[0].ItemCount == keyframes.Count)
            return;
        _keyframes = keyframes;

        foreach (var option in _range)
        {
            option.Clear();
            foreach (var t in _keyframes)
                option.AddItem(KeyframeName(t, compact: true));
        }
    }

    // --- input ---------------------------------------------------------------------------------------

    public override void _UnhandledInput(InputEvent e)
    {
        if (e is InputEventKey { Pressed: true, Echo: false } key)
        {
            if (key.PhysicalKeycode == Key.F3)
                Toggle();
            else if (Visible && key.PhysicalKeycode == Key.Z && key.CtrlPressed)
                Undo();
            else
                return;
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
        if (wasClick && !_player.IsPlaying && _player.CanPlay && _cameras?.Camera is { } camera
            && BonePicking.At(_player, camera, button.Position) is { } hit)
            Select(hit.Segment.Who, hit.Segment.Bone);
    }

    private void Toggle()
    {
        Visible = !Visible;
        _marker.Visible = false;
        if (!Visible)
            return;
        _player.Pause();
        Refresh();
        Opened?.Invoke();
    }

    private void Select(string who, string bone)
    {
        _who = who;
        _bone = bone;
        _pending = null;
        Refresh();
    }

    // --- the edit at the current keyframe --------------------------------------------------------------

    /// <summary>The keyframe the playhead is on, or null between keyframes.</summary>
    private float? KeyTime()
    {
        if (_base is null)
            return null;
        var now = _player.CurrentTime;
        var nearest = _keyframes.OrderBy(t => Mathf.Abs(t - now)).Select(t => (float?)t).FirstOrDefault();
        return nearest is { } n && Mathf.Abs(n - now) <= OnKeyframe ? n : null;
    }

    private PoseEdit? Holding(float t) => PoseEditing.Holding(_file, _who, _bone, t);

    /// <summary>Range for a new edit at t: from the previous to the next phase keyframe, fully applied at t only.</summary>
    private ((float From, float HoldFrom, float HoldTo, float To) Range, string Ease) PendingFor(float t)
    {
        var key = $"{_who}/{_bone}/{t}";
        if (_pending is { } p && p.Key == key)
            return (p.Range, p.Ease);
        var phases = _base!.Keyframes.Where(k => !k.Inbetween).Select(k => k.Time).ToList();
        var from = phases.Where(x => x < t - PoseEditing.TimeEpsilon).Select(x => (float?)x).LastOrDefault() ?? _keyframes[0];
        var to = phases.Where(x => x > t + PoseEditing.TimeEpsilon).Select(x => (float?)x).FirstOrDefault() ?? _keyframes[^1];
        return ((from, t, t, to), PoseEase.Smooth);
    }

    private void OnRotation()
    {
        if (_quiet || KeyTime() is not { } t || _base is null)
            return;
        PushUndo($"rot/{_who}/{_bone}/{t}");
        var (range, ease) = PendingFor(t);
        PoseEditing.SetValue(_file, _base, _who, _bone, t, Values(_rotation), null, range, ease);
        Commit();
    }

    private void OnPosition()
    {
        if (_quiet || KeyTime() is not { } t || _base is null || _bone != PoseEdit.Root)
            return;
        PushUndo($"pos/{_who}/{t}");
        var (range, ease) = PendingFor(t);
        PoseEditing.SetValue(_file, _base, _who, _bone, t, null, Values(_position), range, ease);
        Commit();
    }

    /// <summary>Applies a slider change without writing the sliders back (they hold what was typed).</summary>
    private void Commit()
    {
        _quiet = true;
        try
        {
            _file.Save(_path);
            _player.ReplaceTechnique(PoseEditing.Apply(_base!, _file));
            UpdateKeyframes();
            RefreshRange(KeyTime());
        }
        catch (System.IO.IOException e)
        {
            GD.PushError($"{_path}: {e.Message}");
        }
        finally
        {
            _quiet = false;
        }
        RefreshStatus(KeyTime());
    }

    private void OnRange(int which, long index)
    {
        if (_quiet || KeyTime() is not { } t || index < 0 || index >= _keyframes.Count)
            return;
        var value = _keyframes[(int)index];
        if (Holding(t) is { } edit)
        {
            PushUndo($"range/{which}/{edit.GetHashCode()}");
            var anchor = edit.Time;
            switch (which)
            {
                case 0: edit.From = Mathf.Min(value, edit.HoldFrom); break;
                case 1: edit.HoldFrom = Mathf.Min(value, Mathf.Min(t, anchor)); edit.From = Mathf.Min(edit.From, edit.HoldFrom); break;
                case 2: edit.HoldTo = Mathf.Max(value, Mathf.Max(t, anchor)); edit.To = Mathf.Max(edit.To, edit.HoldTo); break;
                default: edit.To = Mathf.Max(value, edit.HoldTo); break;
            }
            Changed();
            return;
        }
        var (r, ease) = PendingFor(t);
        r = which switch
        {
            0 => r with { From = Mathf.Min(value, r.HoldFrom) },
            1 => (Mathf.Min(r.From, Mathf.Min(value, t)), Mathf.Min(value, t), r.HoldTo, r.To),
            2 => (r.From, r.HoldFrom, Mathf.Max(value, t), Mathf.Max(r.To, Mathf.Max(value, t))),
            _ => r with { To = Mathf.Max(value, r.HoldTo) },
        };
        _pending = ($"{_who}/{_bone}/{t}", r, ease);
        Refresh();
    }

    private void OnEase(long index)
    {
        if (_quiet || KeyTime() is not { } t)
            return;
        var ease = index == 1 ? PoseEase.Linear : PoseEase.Smooth;
        if (Holding(t) is { } edit)
        {
            PushUndo("ease");
            edit.Ease = ease;
            Changed();
            return;
        }
        _pending = ($"{_who}/{_bone}/{t}", PendingFor(t).Range, ease);
    }

    private void DeleteEdit(PoseEdit edit)
    {
        PushUndo("delete");
        _gesture = "";
        _file.Edits.Remove(edit);
        Changed();
    }

    private void InsertKeyframe()
    {
        if (_base is null || KeyTime() is not null)
            return;
        var t = PoseEditing.SnapTime(_player.CurrentTime);
        PushUndo("insert");
        _gesture = "";
        _file.Keyframes.Add(t);
        Changed();
        _player.Seek(t);
    }

    private void DeleteKeyframe(float t)
    {
        PushUndo("delete keyframe");
        _gesture = "";
        _file.Keyframes.RemoveAll(k => Mathf.Abs(k - t) < PoseEditing.TimeEpsilon);
        Changed();
    }

    private void StepKeyframe(int direction)
    {
        var now = _player.CurrentTime;
        var target = direction > 0
            ? _keyframes.Where(t => t > now + OnKeyframe).Select(t => (float?)t).FirstOrDefault()
            : _keyframes.Where(t => t < now - OnKeyframe).Select(t => (float?)t).LastOrDefault();
        _player.Pause();
        if (target is { } x)
            _player.Seek(x);
    }

    // --- showing the state -------------------------------------------------------------------------------

    private void Refresh()
    {
        if (!Visible || _quiet)
            return;
        var t = KeyTime();
        var editable = t is not null && !_player.IsPlaying;
        _keyframe.Text = _base is null ? "Geen animatie."
            : t is { } k ? $"Keyframe {_keyframes.IndexOf(k) + 1}/{_keyframes.Count} · {KeyframeName(k, compact: false)}"
            : $"Tussen keyframes ({Seconds(_player.CurrentTime)} s)";
        _previous.Disabled = _next.Disabled = _base is null;
        _insert.Disabled = _base is null || t is not null;
        _insert.Text = t is null && _base is not null
            ? $"Keyframe invoegen op {Seconds(PoseEditing.SnapTime(_player.CurrentTime))} s" : "Keyframe invoegen";

        _quiet = true;
        _whoOption.Select(System.Array.IndexOf(Who, _who));
        _boneOption.Select(_bone == PoseEdit.Root ? 0 : BoneNames.Skeleton.ToList().IndexOf(_bone) + 1);
        _positionRows.Visible = _bone == PoseEdit.Root;
        _editControls.Modulate = editable ? Colors.White : new Color(1, 1, 1, 0.45f);
        foreach (var (slider, box) in _rotation.Concat(_position))
        {
            slider.Editable = editable;
            box.Editable = editable;
        }
        if (_player.Technique is { IsAnimated: true } shown)
        {
            System.Func<Keyframe, JudokaPose> pose = _who == "tori" ? kf => kf.Tori : kf => kf.Uki;
            var channel = _bone == PoseEdit.Root ? PoseEditing.Channel.Rotation : _bone;
            var euler = Rotations.ToEuler(PoseEditing.SampleRotation(shown.Keyframes, pose, channel, _player.CurrentTime));
            SetValues(_rotation, euler);
            if (PoseEditing.SamplePosition(shown.Keyframes, pose, _player.CurrentTime) is { } p)
                SetValues(_position, p);
        }
        _quiet = false;
        RefreshRange(t);
        RefreshStatus(t);
    }

    private void RefreshRange(float? t)
    {
        var wasQuiet = _quiet;
        _quiet = true;
        if (t is { } k && _base is not null)
        {
            var edit = Holding(k);
            (float From, float HoldFrom, float HoldTo, float To) range;
            string ease;
            if (edit is not null)
            {
                var n = PoseEditing.Normalize(edit);
                (range, ease) = ((n.From, n.HoldFrom, n.HoldTo, n.To), edit.Ease);
            }
            else
                (range, ease) = PendingFor(k);
            float[] values = [range.From, range.HoldFrom, range.HoldTo, range.To];
            for (var i = 0; i < 4; i++)
                _range[i].Select(Nearest(values[i]));
            _ease.Select(ease == PoseEase.Linear ? 1 : 0);
            _delete.Disabled = edit is null;
        }
        else
            _delete.Disabled = true;
        foreach (var option in _range.Append(_ease))
            option.Disabled = t is null || _player.IsPlaying;
        _undoButton.Disabled = _undo.Count == 0;
        _quiet = wasQuiet;
    }

    private void RefreshStatus(float? t)
    {
        if (_base is null)
        {
            _status.Text = "";
            return;
        }
        var target = $"{_who} · {(_bone == PoseEdit.Root ? "wortel" : FeedbackFile.BoneKey(_bone))}";
        _status.Text = t is { } k && Holding(k) is { } e
            ? $"{target}: aangepast (anker {Seconds(e.Time)} s)."
            : t is null ? $"{target}: ga naar een keyframe of voeg er een in."
            : $"{target}: nog niet aangepast; een schuif maakt een aanpassing.";
        _undoButton.Disabled = _undo.Count == 0;
    }

    private void RefreshList()
    {
        foreach (var child in _list.GetChildren())
            child.QueueFree();
        _listTitle.Text = $"Aanpassingen ({_file.Edits.Count}) en ingevoegde keyframes ({_file.Keyframes.Count}) · edits/{System.IO.Path.GetFileName(_path)}";
        foreach (var edit in _file.Edits.OrderBy(e => e.Time).ToList())
        {
            var bone = edit.IsRoot ? PoseEdit.Root : BoneNames.TryResolve(edit.Bone, out var b) ? b : edit.Bone;
            AddRow($"{Seconds(edit.Time)} s {edit.Who}.{edit.Bone} ({Seconds(edit.From)}–{Seconds(edit.To)} s)",
                   "Ga naar deze aanpassing", () =>
                   {
                       _player.Pause();
                       _player.Seek(edit.Time);
                       Select(edit.Who, bone);
                   }, "Verwijder deze aanpassing", () => DeleteEdit(edit));
        }
        foreach (var t in _file.Keyframes.Order().ToList())
            AddRow($"+ keyframe {Seconds(t)} s", "Ga naar deze keyframe", () =>
            {
                _player.Pause();
                _player.Seek(t);
            }, "Verwijder deze ingevoegde keyframe", () => DeleteKeyframe(t));
    }

    private void AddRow(string text, string goTooltip, System.Action go, string deleteTooltip, System.Action delete)
    {
        var row = new HBoxContainer();
        var label = UiStyle.NoFocus(new Button { Text = text, TooltipText = goTooltip, Flat = true, Alignment = HorizontalAlignment.Left });
        label.AddThemeFontSizeOverride("font_size", 13);
        label.SizeFlagsHorizontal = SizeFlags.ExpandFill;
        label.ClipText = true;
        label.Pressed += go;
        row.AddChild(label);
        var remove = UiStyle.NoFocus(new Button { Text = "✕", TooltipText = deleteTooltip });
        remove.Pressed += delete;
        row.AddChild(remove);
        _list.AddChild(row);
    }

    public override void _Process(double delta)
    {
        if (!Visible || _base is null)
        {
            _marker.Visible = false;
            return;
        }
        if (_bone == PoseEdit.Root)
        {
            var root = _who == "tori" ? _player.Tori : _player.Uki;
            _marker.Visible = root is not null;
            if (root is not null)
                _marker.GlobalPosition = root.GlobalPosition + new Vector3(0, 0.02f, 0);
            return;
        }
        var segment = BonePicking.Segments(_player, _who).FirstOrDefault(s => s.Bone == _bone);
        _marker.Visible = segment != default;
        if (segment != default)
            _marker.GlobalPosition = segment.A.Lerp(segment.B, 0.5f);
    }

    private int Nearest(float t)
    {
        var best = 0;
        for (var i = 1; i < _keyframes.Count; i++)
            if (Mathf.Abs(_keyframes[i] - t) < Mathf.Abs(_keyframes[best] - t))
                best = i;
        return _keyframes.Count == 0 ? -1 : best;
    }

    private string KeyframeName(float t, bool compact)
    {
        var keyframe = _base?.Keyframes.FirstOrDefault(k => Mathf.Abs(k.Time - t) < PoseEditing.TimeEpsilon);
        var name = keyframe is null ? (_file.Keyframes.Any(k => Mathf.Abs(k - t) < PoseEditing.TimeEpsilon) ? "ingevoegd" : "voor aanpassing")
            : keyframe.Inbetween ? "tussenframe" : compact ? keyframe.Phase.Split(' ')[0] : keyframe.Phase;
        return $"{Seconds(t)} s · {name}";
    }

    private static Vec3 Values((HSlider Slider, SpinBox Box)[] rows) =>
        new((float)rows[0].Box.Value, (float)rows[1].Box.Value, (float)rows[2].Box.Value);

    private static void SetValues((HSlider Slider, SpinBox Box)[] rows, Vec3 v)
    {
        float[] values = [v.X, v.Y, v.Z];
        for (var i = 0; i < 3; i++)
        {
            rows[i].Slider.SetValueNoSignal(values[i]);
            rows[i].Box.SetValueNoSignal(values[i]);
        }
    }

    private static string Seconds(float t) => t.ToString("0.00", CultureInfo.InvariantCulture);

    // --- building the panel ------------------------------------------------------------------------------

    private void BuildPanel()
    {
        AnchorLeft = AnchorRight = 1;
        OffsetLeft = -390;
        OffsetRight = -10;
        OffsetTop = 10;
        GrowHorizontal = GrowDirection.Begin;
        AddThemeStyleboxOverride("panel", UiStyle.Panel());

        var column = new VBoxContainer();
        column.AddThemeConstantOverride("separation", 5);
        AddChild(column);
        column.AddChild(UiStyle.Label("Pose-editor (F3 = aan/uit)", 15, UiStyle.Accent));
        var help = UiStyle.Label("Klik op een lichaamsdeel en stel het in op een keyframe. Wordt direct bewaard; " +
                                 "de volgende Blender-run neemt het over (aanpassingen gaan voor).", 12, UiStyle.Muted);
        help.AutowrapMode = TextServer.AutowrapMode.WordSmart;
        column.AddChild(help);

        var nav = new HBoxContainer();
        _previous = SmallButton("◀", "Vorige keyframe (ook tussenframes en ingevoegde)", () => StepKeyframe(-1));
        _next = SmallButton("▶", "Volgende keyframe", () => StepKeyframe(1));
        _keyframe = UiStyle.Label("", 13);
        _keyframe.SizeFlagsHorizontal = SizeFlags.ExpandFill;
        _keyframe.ClipText = true;
        nav.AddChild(_previous);
        nav.AddChild(_keyframe);
        nav.AddChild(_next);
        column.AddChild(nav);
        _insert = UiStyle.NoFocus(new Button { Text = "Keyframe invoegen", TooltipText = "Nieuwe keyframe op de huidige tijd (op 50 fps afgerond)" });
        _insert.Pressed += InsertKeyframe;
        column.AddChild(_insert);

        var edit = new VBoxContainer();
        edit.AddThemeConstantOverride("separation", 4);
        _editControls = edit;
        column.AddChild(edit);

        var target = new HBoxContainer();
        _whoOption = UiStyle.NoFocus(new OptionButton());
        _whoOption.AddItem("Tori");
        _whoOption.AddItem("Uki");
        _whoOption.ItemSelected += i => Select(Who[i], _bone);
        _boneOption = UiStyle.NoFocus(new OptionButton { SizeFlagsHorizontal = SizeFlags.ExpandFill });
        _boneOption.AddItem("Wortel (positie + rotatie)");
        foreach (var bone in BoneNames.Skeleton)
            _boneOption.AddItem(FeedbackFile.BoneKey(bone));
        _boneOption.ItemSelected += i => Select(_who, i == 0 ? PoseEdit.Root : BoneNames.Skeleton[(int)i - 1]);
        target.AddChild(_whoOption);
        target.AddChild(_boneOption);
        edit.AddChild(target);

        edit.AddChild(UiStyle.Label("Rotatie (graden, Euler XYZ; X = rechts, Y = op, -Z = kijkrichting)", 12, UiStyle.Muted));
        for (var i = 0; i < 3; i++)
            _rotation[i] = ValueRow(edit, Axes[i], -180, 180, 0.5, OnRotation);
        _positionRows = new VBoxContainer();
        _positionRows.AddChild(UiStyle.Label("Positie (meter, Godot: Y = op)", 12, UiStyle.Muted));
        for (var i = 0; i < 3; i++)
            _position[i] = ValueRow(_positionRows, Axes[i], i == 1 ? -1 : -3, i == 1 ? 2 : 3, 0.005, OnPosition);
        edit.AddChild(_positionRows);

        edit.AddChild(UiStyle.Label("Bereik: 0 % op 'van' → 100 % → 0 % op 'tot'", 12, UiStyle.Muted));
        var grid = new GridContainer { Columns = 2 };
        string[] labels = ["Van (0 %)", "Volledig vanaf", "Volledig tot", "Tot (0 %)"];
        for (var i = 0; i < 4; i++)
        {
            var which = i;
            grid.AddChild(UiStyle.Label(labels[i], 12));
            _range[i] = UiStyle.NoFocus(new OptionButton { SizeFlagsHorizontal = SizeFlags.ExpandFill, FitToLongestItem = false });
            _range[i].ItemSelected += index => OnRange(which, index);
            grid.AddChild(_range[i]);
        }
        grid.AddChild(UiStyle.Label("Verloop", 12));
        _ease = UiStyle.NoFocus(new OptionButton());
        _ease.AddItem("Vloeiend");
        _ease.AddItem("Lineair");
        _ease.ItemSelected += OnEase;
        grid.AddChild(_ease);
        edit.AddChild(grid);

        var buttons = new HBoxContainer();
        _delete = UiStyle.NoFocus(new Button { Text = "Aanpassing verwijderen" });
        _delete.Pressed += () =>
        {
            if (KeyTime() is { } t && Holding(t) is { } e)
                DeleteEdit(e);
        };
        _undoButton = UiStyle.NoFocus(new Button { Text = "Ongedaan maken (Ctrl+Z)" });
        _undoButton.Pressed += Undo;
        buttons.AddChild(_delete);
        buttons.AddChild(_undoButton);
        column.AddChild(buttons);
        _status = UiStyle.Label("", 12, UiStyle.Accent);
        _status.AutowrapMode = TextServer.AutowrapMode.WordSmart;
        column.AddChild(_status);

        column.AddChild(new HSeparator());
        _listTitle = UiStyle.Label("", 12, UiStyle.Muted);
        _listTitle.AutowrapMode = TextServer.AutowrapMode.WordSmart;
        column.AddChild(_listTitle);
        var scroll = new ScrollContainer { CustomMinimumSize = new Vector2(0, 120), HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled };
        _list = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill };
        scroll.AddChild(_list);
        column.AddChild(scroll);
    }

    private static (HSlider, SpinBox) ValueRow(Container parent, string axis, double min, double max, double step, System.Action changed)
    {
        var row = new HBoxContainer();
        row.AddChild(UiStyle.Label(axis, 13));
        var slider = UiStyle.NoFocus(new HSlider { MinValue = min, MaxValue = max, Step = step, SizeFlagsHorizontal = SizeFlags.ExpandFill });
        slider.SizeFlagsVertical = SizeFlags.ShrinkCenter;
        var box = new SpinBox { MinValue = min, MaxValue = max, Step = step, CustomMinimumSize = new Vector2(96, 0), SelectAllOnFocus = true };
        slider.ValueChanged += v =>
        {
            box.SetValueNoSignal(v);
            changed();
        };
        box.ValueChanged += v =>
        {
            slider.SetValueNoSignal(v);
            changed();
        };
        row.AddChild(slider);
        row.AddChild(box);
        parent.AddChild(row);
        return (slider, box);
    }

    private static Button SmallButton(string text, string tooltip, System.Action pressed)
    {
        var button = UiStyle.NoFocus(new Button { Text = text, TooltipText = tooltip, CustomMinimumSize = new Vector2(32, 0) });
        button.Pressed += pressed;
        return button;
    }

    /// <summary>Always-visible reminder below the F2 one (the panel starts hidden).</summary>
    private void BuildHint()
    {
        var hint = UiStyle.Label("F3 = pose-editor", 12, UiStyle.Muted);
        hint.MouseFilter = MouseFilterEnum.Ignore;
        hint.AnchorLeft = hint.AnchorRight = 1;
        hint.OffsetLeft = -160;
        hint.OffsetRight = -10;
        hint.OffsetTop = 28;
        hint.GrowHorizontal = GrowDirection.Begin;
        hint.HorizontalAlignment = HorizontalAlignment.Right;
        GetParent<Control>().AddChild(hint);
        VisibilityChanged += () => hint.Visible = !Visible;
    }

    private void BuildMarker()
    {
        var material = new StandardMaterial3D
        {
            ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded, AlbedoColor = new Color(0.3f, 0.85f, 1f), NoDepthTest = true,
        };
        _marker = new MeshInstance3D
        {
            Mesh = new SphereMesh { Radius = 0.03f, Height = 0.06f }, MaterialOverride = material, TopLevel = true, Visible = false,
        };
        _player.AddChild(_marker);
    }
}

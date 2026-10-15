using Godot;
using JudoVisualizer.Data;

namespace JudoVisualizer.Camera;

public enum CameraMode
{
    /// <summary>Free spectator camera circling the judoka at a fixed height.</summary>
    Orbit,

    /// <summary>Through Tori's eyes.</summary>
    ToriPov,

    /// <summary>Through Uki's eyes.</summary>
    UkiPov,
}

/// <summary>
/// Drives one <see cref="Camera3D"/> in one of three <see cref="CameraMode"/>s, gliding smoothly
/// when the mode changes.
/// Controls: 1/2/3 = orbit / Tori / Uki, C = next mode. In orbit mode: Left/Right (or mouse drag)
/// circle around the judoka, Up/Down (or mouse wheel) move closer/further.
/// </summary>
public partial class CameraManager : Node
{
    [Signal] public delegate void ModeChangedEventHandler(CameraMode mode);

    [Export] public Camera3D? Camera { get; set; }
    [Export] public Node3D? Tori { get; set; }
    [Export] public Node3D? Uki { get; set; }
    [Export] public CameraMode InitialMode { get; set; } = CameraMode.Orbit;

    [ExportGroup("Orbit")]
    [Export] public float OrbitHeight { get; set; } = 1.6f;
    [Export(PropertyHint.Range, "0,360")] public float OrbitStartAngleDegrees { get; set; } = 90f;
    [Export] public float OrbitDistance { get; set; } = 3.6f;
    [Export] public float OrbitMinDistance { get; set; } = 1.4f;
    [Export] public float OrbitMaxDistance { get; set; } = 8f;
    [Export] public float OrbitDegreesPerSecond { get; set; } = 90f;
    [Export] public float ApproachMetresPerSecond { get; set; } = 2.5f;
    [Export] public float MouseDegreesPerPixel { get; set; } = 0.3f;
    [Export] public float WheelMetresPerStep { get; set; } = 0.3f;

    /// <summary>How quickly the orbit follows the judoka; higher = snappier.</summary>
    [Export] public float TargetFollowRate { get; set; } = 6f;

    [ExportGroup("Transitions")]
    [Export] public float TransitionSeconds { get; set; } = 0.5f;

    public CameraMode Mode { get; private set; }

    private static readonly (string Action, Key Key)[] Bindings =
    [
        ("camera_orbit_left", Key.Left), ("camera_orbit_right", Key.Right),
        ("camera_closer", Key.Up), ("camera_further", Key.Down),
        ("camera_mode_orbit", Key.Key1), ("camera_mode_tori", Key.Key2), ("camera_mode_uki", Key.Key3),
        ("camera_next_mode", Key.C),
    ];

    private OrbitModel _orbit = null!;
    private JudokaView? _tori;
    private JudokaView? _uki;
    private Vector3 _target;
    private Transform3D _blendFrom;
    private float _blend = 1f;

    public override void _Ready()
    {
        ProcessPriority = 100; // after the player has posed the skeletons this frame
        RegisterInputActions();
        _orbit = new OrbitModel(OrbitHeight, Mathf.DegToRad(OrbitStartAngleDegrees), OrbitDistance,
                                OrbitMinDistance, OrbitMaxDistance);
        _tori = JudokaView.Bind(Tori, nameof(Tori));
        _uki = JudokaView.Bind(Uki, nameof(Uki));
        _target = RawTarget();
        Mode = InitialMode;
        if (Camera is null)
            GD.PushError($"{Name}: Camera is not assigned.");
    }

    /// <summary>
    /// Switches perspective. The camera glides there, unless <paramref name="immediate"/>: then it
    /// jumps, and the orbit target snaps to the judoka's current position too.
    /// </summary>
    public void SetMode(CameraMode mode, bool immediate = false)
    {
        if (Camera is not null)
        {
            _blendFrom = Camera.GlobalTransform;
            _blend = immediate ? 1f : 0f;
        }
        if (immediate)
            _target = RawTarget();
        if (mode == Mode)
            return;
        Mode = mode;
        EmitSignal(SignalName.ModeChanged, (int)mode);
    }

    /// <summary>Cycles Orbit -> Tori POV -> Uki POV -> Orbit.</summary>
    public void NextMode() => SetMode((CameraMode)(((int)Mode + 1) % 3));

    public override void _Process(double delta)
    {
        if (Camera is null)
            return;
        var dt = (float)delta;

        if (Mode == CameraMode.Orbit)
        {
            _orbit.Orbit(Mathf.DegToRad(OrbitDegreesPerSecond) * dt *
                         Input.GetAxis("camera_orbit_left", "camera_orbit_right"));
            _orbit.Approach(ApproachMetresPerSecond * dt * Input.GetAxis("camera_further", "camera_closer"));
        }
        _target = _target.Lerp(RawTarget(), 1f - Mathf.Exp(-TargetFollowRate * dt));

        var goal = GoalTransform();
        if (_blend < 1f)
        {
            _blend = Mathf.Min(1f, _blend + dt / Mathf.Max(TransitionSeconds, 0.001f));
            goal = _blendFrom.InterpolateWith(goal, Mathf.SmoothStep(0f, 1f, _blend));
        }
        Camera.GlobalTransform = goal;
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if (e.IsActionPressed("camera_mode_orbit"))
            SetMode(CameraMode.Orbit);
        else if (e.IsActionPressed("camera_mode_tori"))
            SetMode(CameraMode.ToriPov);
        else if (e.IsActionPressed("camera_mode_uki"))
            SetMode(CameraMode.UkiPov);
        else if (e.IsActionPressed("camera_next_mode"))
            NextMode();
        else if (Mode == CameraMode.Orbit)
            HandleOrbitMouse(e);
    }

    private void HandleOrbitMouse(InputEvent e)
    {
        switch (e)
        {
            // Dragging moves the scene with the mouse: drag right -> camera circles to the left.
            case InputEventMouseMotion m when (m.ButtonMask & (MouseButtonMask.Left | MouseButtonMask.Right)) != 0:
                _orbit.Orbit(-Mathf.DegToRad(MouseDegreesPerPixel * m.Relative.X));
                break;
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelUp }:
                _orbit.Approach(WheelMetresPerStep);
                break;
            case InputEventMouseButton { Pressed: true, ButtonIndex: MouseButton.WheelDown }:
                _orbit.Approach(-WheelMetresPerStep);
                break;
        }
    }

    private Transform3D GoalTransform()
    {
        var view = Mode switch
        {
            CameraMode.ToriPov => _tori,
            CameraMode.UkiPov => _uki,
            _ => null,
        };
        if (view is not null)
            return view.Eyes();

        var p = _orbit.PositionFor(new Vec3(_target.X, _target.Y, _target.Z));
        return new Transform3D(Basis.Identity, new Vector3(p.X, p.Y, p.Z)).LookingAt(_target, Vector3.Up);
    }

    /// <summary>Midpoint between both judoka's hips (what the orbit camera looks at).</summary>
    private Vector3 RawTarget() => (_tori, _uki) switch
    {
        ({ } t, { } u) => (t.HipsPosition + u.HipsPosition) / 2,
        ({ } t, null) => t.HipsPosition,
        (null, { } u) => u.HipsPosition,
        _ => new Vector3(0, 0.9f, 0),
    };

    private static void RegisterInputActions()
    {
        foreach (var (action, key) in Bindings)
        {
            if (InputMap.HasAction(action))
                continue;
            InputMap.AddAction(action);
            InputMap.ActionAddEvent(action, new InputEventKey { PhysicalKeycode = key });
        }
    }
}

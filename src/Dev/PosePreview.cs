using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Godot;
using JudoVisualizer.Camera;
using JudoVisualizer.Data;
using JudoVisualizer.Playback;

namespace JudoVisualizer.Dev;

/// <summary>
/// Dev tool: renders screenshots of a technique at given times and camera views, then quits.
/// Needs a rendering window (not --headless):
/// <code>
/// Godot --path . res://scenes/dev/PosePreview.tscn -- --technique=ippon_seoi_nage
///       --times=0,0.6,1.2 --views=side,front --out=C:/tmp/preview
/// </code>
/// Views: side (+X), other_side (-X), front (-Z), back (+Z), three_quarter, top, and the
/// CameraManager modes orbit, tori_pov, uki_pov. Add --ui to include the HUD.
/// Files are written as &lt;out&gt;/&lt;technique&gt;_&lt;time&gt;_&lt;view&gt;.png.
/// --size=480x270 scales each image down. --sheet writes one contact sheet instead,
/// &lt;out&gt;/&lt;technique&gt;_sheet.png: a row per time, a column per view, each labelled
/// "time view" (default cell size 480x270). --zoom=1.5 moves the fixed views closer.
/// --focus=0.2,0.2,0.3 aims the fixed views at another point (Godot space; default 0,0.9,0.2,
/// standing height): ground techniques. --bg=#b3202a hides the tatami and uses a flat background colour.
/// </summary>
public partial class PosePreview : Node
{
    private static readonly Vector3 DefaultFocus = new(0, 0.9f, 0.2f);

    private static readonly Dictionary<string, Vector3> Views = new()
    {
        ["side"] = new(3.4f, 1.4f, 0.2f),
        ["other_side"] = new(-3.4f, 1.4f, 0.2f),
        ["front"] = new(0.4f, 1.4f, -3.2f),
        ["back"] = new(0.4f, 1.4f, 3.6f),
        ["three_quarter"] = new(2.6f, 2.2f, -2.0f),
        ["top"] = new(0.01f, 4.5f, 0.2f),
    };

    /// <summary>Views rendered through the <see cref="CameraManager"/> instead of a fixed position.</summary>
    private static readonly Dictionary<string, CameraMode> CameraModes = new()
    {
        ["orbit"] = CameraMode.Orbit,
        ["tori_pov"] = CameraMode.ToriPov,
        ["uki_pov"] = CameraMode.UkiPov,
    };

    public override async void _Ready()
    {
        var args = OS.GetCmdlineUserArgs()
            .Select(a => a.TrimStart('-').Split('=', 2))
            .ToDictionary(p => p[0], p => p.Length > 1 ? p[1] : "");
        var name = args.GetValueOrDefault("technique", "ippon_seoi_nage");
        var times = args.GetValueOrDefault("times", "0").Split(',')
            .Select(t => float.Parse(t, CultureInfo.InvariantCulture)).ToList();
        var views = args.GetValueOrDefault("views", "side").Split(',');
        var outDir = args.GetValueOrDefault("out", "user://preview");
        DirAccess.MakeDirRecursiveAbsolute(outDir);
        var sheet = args.ContainsKey("sheet");
        var zoom = float.Parse(args.GetValueOrDefault("zoom", "1"), CultureInfo.InvariantCulture);
        var size = ParseSize(args.GetValueOrDefault("size", sheet ? "480x270" : ""));
        var focus = args.TryGetValue("focus", out var f) ? ParseVector(f) : DefaultFocus;

        var main = GD.Load<PackedScene>("res://scenes/main/Main.tscn").Instantiate<Node3D>();
        AddChild(main);
        main.GetNode<CanvasLayer>("UI").Visible = args.ContainsKey("ui");
        if (args.TryGetValue("bg", out var bg))
        {
            main.GetNode<MeshInstance3D>("Tatami").Visible = false;
            main.GetNode<WorldEnvironment>("WorldEnvironment").Environment.BackgroundColor = Color.FromHtml(bg);
        }
        var player = main.GetNode<JudoTechniquePlayer>("Player");
        player.Load(TechniqueLoader.Load($"{TechniqueLoader.BuiltInDirectory}/{name}.yaml"));
        var camera = main.GetNode<Camera3D>("Camera3D");
        var cameraManager = main.GetNode<CameraManager>("CameraManager");
        var label = AddLabel();
        label.Visible = sheet;
        var cells = new List<Image>();

        foreach (var time in times)
        {
            player.Seek(time);
            foreach (var view in views)
            {
                if (CameraModes.TryGetValue(view, out var mode))
                {
                    cameraManager.ProcessMode = ProcessModeEnum.Inherit;
                    cameraManager.SetMode(mode, immediate: true);
                }
                else
                {
                    cameraManager.ProcessMode = ProcessModeEnum.Disabled;
                    camera.LookAtFromPosition(focus + (Views[view] - DefaultFocus) / zoom, focus, view == "top" ? Vector3.Back : Vector3.Up);
                }
                var stamp = time.ToString("0.00", CultureInfo.InvariantCulture);
                label.Text = $"{stamp}s {view}";
                await ToSignal(RenderingServer.Singleton, RenderingServer.SignalName.FramePostDraw);
                await ToSignal(RenderingServer.Singleton, RenderingServer.SignalName.FramePostDraw);
                var image = GetViewport().GetTexture().GetImage();
                if (size is { } s)
                    image.Resize(s.X, s.Y, Image.Interpolation.Lanczos);
                if (sheet)
                {
                    cells.Add(image);
                    continue;
                }
                var file = outDir.PathJoin($"{name}_{stamp}_{view}.png");
                image.SavePng(file);
                GD.Print($"Saved {file}");
            }
        }
        if (sheet)
        {
            var file = outDir.PathJoin($"{name}_sheet.png");
            Sheet(cells, views.Length).SavePng(file);
            GD.Print($"Saved {file} ({times.Count} times x {views.Length} views)");
        }
        GetTree().Quit();
    }

    private static Vector3 ParseVector(string text)
    {
        var v = text.Split(',').Select(x => float.Parse(x, CultureInfo.InvariantCulture)).ToArray();
        return new Vector3(v[0], v[1], v[2]);
    }

    private static Vector2I? ParseSize(string text)
    {
        var parts = text.Split('x');
        return parts.Length == 2 ? new Vector2I(int.Parse(parts[0]), int.Parse(parts[1])) : null;
    }

    /// <summary>Caption in the top-left corner, drawn above the 3D view (and above the HUD).</summary>
    private Label AddLabel()
    {
        var layer = new CanvasLayer { Layer = 100 };
        AddChild(layer);
        var label = new Label { Position = new Vector2(16, 8) };
        label.AddThemeFontSizeOverride("font_size", 48);
        label.AddThemeColorOverride("font_color", Colors.Black);
        label.AddThemeColorOverride("font_outline_color", Colors.White);
        label.AddThemeConstantOverride("outline_size", 12);
        layer.AddChild(label);
        return label;
    }

    /// <summary>Images (all the same size) in a grid of <paramref name="columns"/> columns.</summary>
    private static Image Sheet(List<Image> cells, int columns)
    {
        var w = cells[0].GetWidth();
        var h = cells[0].GetHeight();
        var rows = (cells.Count + columns - 1) / columns;
        var sheet = Image.CreateEmpty(columns * w, rows * h, false, cells[0].GetFormat());
        for (var i = 0; i < cells.Count; i++)
            sheet.BlitRect(cells[i], new Rect2I(0, 0, w, h), new Vector2I(i % columns * w, i / columns * h));
        return sheet;
    }
}

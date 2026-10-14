using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Godot;
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
/// Views: side (+X), other_side (-X), front (-Z), back (+Z), three_quarter, top.
/// Files are written as &lt;out&gt;/&lt;technique&gt;_&lt;time&gt;_&lt;view&gt;.png.
/// </summary>
public partial class PosePreview : Node
{
    private static readonly Vector3 Focus = new(0, 0.9f, 0.2f);

    private static readonly Dictionary<string, Vector3> Views = new()
    {
        ["side"] = new(3.4f, 1.4f, 0.2f),
        ["other_side"] = new(-3.4f, 1.4f, 0.2f),
        ["front"] = new(0.4f, 1.4f, -3.2f),
        ["back"] = new(0.4f, 1.4f, 3.6f),
        ["three_quarter"] = new(2.6f, 2.2f, -2.0f),
        ["top"] = new(0.01f, 4.5f, 0.2f),
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

        var main = GD.Load<PackedScene>("res://scenes/main/Main.tscn").Instantiate<Node3D>();
        AddChild(main);
        var player = main.GetNode<JudoTechniquePlayer>("Player");
        player.Load(TechniqueLoader.Load($"{TechniqueLoader.BuiltInDirectory}/{name}.yaml"));
        var camera = main.GetNode<Camera3D>("Camera3D");

        foreach (var time in times)
        {
            player.Seek(time);
            foreach (var view in views)
            {
                camera.LookAtFromPosition(Views[view], Focus, view == "top" ? Vector3.Back : Vector3.Up);
                await ToSignal(RenderingServer.Singleton, RenderingServer.SignalName.FramePostDraw);
                await ToSignal(RenderingServer.Singleton, RenderingServer.SignalName.FramePostDraw);
                var file = outDir.PathJoin($"{name}_{time.ToString("0.00", CultureInfo.InvariantCulture)}_{view}.png");
                GetViewport().GetTexture().GetImage().SavePng(file);
                GD.Print($"Saved {file}");
            }
        }
        GetTree().Quit();
    }
}

using System;
using System.Collections.Generic;
using Godot;
using JudoVisualizer.Data;

namespace JudoVisualizer.UI;

/// <summary>
/// Sidebar listing the techniques grouped by kyu grade (6th kyu first), with a belt-colour badge
/// per technique and a filter on one grade.
/// </summary>
public partial class TechniqueBrowser : PanelContainer
{
    /// <summary>Raised when the user picks a technique.</summary>
    public event Action<Technique>? TechniqueSelected;

    private readonly ButtonGroup _buttons = new() { AllowUnpress = false };
    private readonly Dictionary<Technique, Button> _buttonFor = [];
    private IReadOnlyList<Technique> _techniques = [];
    private Technique? _selected;
    private OptionButton _filter = null!;
    private VBoxContainer _list = null!;

    public override void _Ready()
    {
        AddThemeStyleboxOverride("panel", UiStyle.Panel());
        var column = new VBoxContainer();
        column.AddThemeConstantOverride("separation", 8);
        AddChild(column);

        column.AddChild(UiStyle.Label("Techniques", 20));

        _filter = UiStyle.NoFocus(new OptionButton { TooltipText = "Show one kyu grade" });
        _filter.AddItem("All grades", 0);
        foreach (var grade in KyuGrades.All)
            _filter.AddItem(TechniqueCatalog.Title(grade), grade.Grade);
        _filter.ItemSelected += _ => Rebuild();
        column.AddChild(_filter);

        var scroll = new ScrollContainer
        {
            SizeFlagsVertical = SizeFlags.ExpandFill,
            HorizontalScrollMode = ScrollContainer.ScrollMode.Disabled,
        };
        column.AddChild(scroll);
        _list = new VBoxContainer { SizeFlagsHorizontal = SizeFlags.ExpandFill };
        _list.AddThemeConstantOverride("separation", 4);
        scroll.AddChild(_list);
    }

    public void SetTechniques(IReadOnlyList<Technique> techniques)
    {
        _techniques = techniques;
        Rebuild();
    }

    /// <summary>Highlights <paramref name="technique"/> without raising <see cref="TechniqueSelected"/>.</summary>
    public void Select(Technique? technique)
    {
        _selected = technique;
        if (technique is not null && _buttonFor.TryGetValue(technique, out var button))
            button.SetPressedNoSignal(true);
    }

    private void Rebuild()
    {
        foreach (var child in _list.GetChildren())
            child.QueueFree();
        _buttonFor.Clear();

        var grade = _filter.GetSelectedId();
        var groups = TechniqueCatalog.Group(_techniques, grade == 0 ? null : grade);
        if (groups.Count == 0)
            _list.AddChild(UiStyle.Label("No techniques for this grade.", 13, UiStyle.Muted));

        foreach (var group in groups)
        {
            var header = new HBoxContainer();
            header.AddThemeConstantOverride("separation", 8);
            header.AddChild(UiStyle.BeltBadge(group.Grade.Hex, 16));
            header.AddChild(UiStyle.Label(TechniqueCatalog.Title(group.Grade), 14, UiStyle.Muted));
            _list.AddChild(header);

            foreach (var technique in group.Techniques)
                _list.AddChild(Entry(technique));
        }
        Select(_selected);
    }

    private Control Entry(Technique technique)
    {
        var row = new HBoxContainer();
        row.AddThemeConstantOverride("separation", 8);
        row.AddChild(new Control { CustomMinimumSize = new Vector2(8, 0) }); // indent under the header
        row.AddChild(UiStyle.BeltBadge(technique.BeltColor.Hex));

        var button = UiStyle.NoFocus(new Button
        {
            Text = technique.TechniqueName,
            TooltipText = $"{technique.Code} · {technique.Category} · {technique.Difficulty}",
            ToggleMode = true,
            ButtonGroup = _buttons,
            Flat = true,
            Alignment = HorizontalAlignment.Left,
            SizeFlagsHorizontal = SizeFlags.ExpandFill,
        });
        button.Pressed += () =>
        {
            _selected = technique;
            TechniqueSelected?.Invoke(technique);
        };
        _buttonFor[technique] = button;
        row.AddChild(button);
        return row;
    }
}

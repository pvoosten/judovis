using Godot;

namespace JudoVisualizer.UI;

/// <summary>Shared look of the HUD panels and controls.</summary>
internal static class UiStyle
{
    public static readonly Color Accent = new(1f, 0.78f, 0.25f);
    public static readonly Color Muted = new(0.75f, 0.77f, 0.8f);

    /// <summary>Text of things that are there but not usable yet (techniques without animation).</summary>
    public static readonly Color Disabled = new(0.5f, 0.52f, 0.55f);

    /// <summary>Semi-transparent rounded panel so the 3D view stays visible behind it.</summary>
    public static StyleBoxFlat Panel() => new()
    {
        BgColor = new Color(0.07f, 0.08f, 0.1f, 0.72f),
        CornerRadiusTopLeft = 8, CornerRadiusTopRight = 8, CornerRadiusBottomLeft = 8, CornerRadiusBottomRight = 8,
        ContentMarginLeft = 12, ContentMarginRight = 12, ContentMarginTop = 10, ContentMarginBottom = 10,
    };

    /// <summary>
    /// Keeps a control from taking keyboard focus, so arrow keys and Space keep driving the
    /// camera and playback instead of navigating the UI.
    /// </summary>
    public static T NoFocus<T>(T control) where T : Control
    {
        control.FocusMode = Control.FocusModeEnum.None;
        return control;
    }

    public static Label Label(string text, int fontSize = 14, Color? color = null)
    {
        var label = new Label { Text = text };
        label.AddThemeFontSizeOverride("font_size", fontSize);
        if (color is { } c)
            label.AddThemeColorOverride("font_color", c);
        return label;
    }

    /// <summary>A small square in a belt colour, with a thin outline so a white belt stays visible.</summary>
    public static Control BeltBadge(string hex, int size = 14)
    {
        var outline = new PanelContainer { CustomMinimumSize = new Vector2(size, size), TooltipText = hex };
        outline.AddThemeStyleboxOverride("panel", new StyleBoxFlat
        {
            BgColor = Color.FromHtml(hex),
            BorderColor = new Color(0, 0, 0, 0.6f),
            BorderWidthLeft = 1, BorderWidthTop = 1, BorderWidthRight = 1, BorderWidthBottom = 1,
            CornerRadiusTopLeft = 3, CornerRadiusTopRight = 3, CornerRadiusBottomLeft = 3, CornerRadiusBottomRight = 3,
        });
        outline.SizeFlagsVertical = Control.SizeFlags.ShrinkCenter;
        outline.MouseFilter = Control.MouseFilterEnum.Pass;
        return outline;
    }
}

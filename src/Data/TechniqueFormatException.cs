using System;
using System.Collections.Generic;

namespace JudoVisualizer.Data;

/// <summary>A technique file could not be parsed or failed validation.</summary>
public sealed class TechniqueFormatException(string source, IReadOnlyList<string> errors, Exception? inner = null)
    : Exception($"{source}: invalid technique:\n - {string.Join("\n - ", errors)}", inner)
{
    /// <summary>File path (or other origin) of the technique.</summary>
    public string FilePath { get; } = source;

    public IReadOnlyList<string> Errors { get; } = errors;
}

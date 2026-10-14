using System;
using System.Collections.Generic;
using System.Globalization;
using YamlDotNet.Core;
using YamlDotNet.Core.Events;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace JudoVisualizer.Data;

/// <summary>
/// Converts between technique YAML text and <see cref="Technique"/>. Parsing is strict: unknown
/// keys, malformed vectors and validation failures raise <see cref="TechniqueFormatException"/>.
/// </summary>
public static class TechniqueSerializer
{
    private static readonly IDeserializer Deserializer = new DeserializerBuilder()
        .WithNamingConvention(UnderscoredNamingConvention.Instance)
        .WithTypeConverter(new Vec3YamlConverter())
        .Build();

    private static readonly ISerializer Serializer = new SerializerBuilder()
        .WithNamingConvention(UnderscoredNamingConvention.Instance)
        .WithTypeConverter(new Vec3YamlConverter())
        .ConfigureDefaultValuesHandling(DefaultValuesHandling.OmitNull)
        .DisableAliases()
        .Build();

    /// <param name="source">Where the text came from (file path), used in error messages.</param>
    public static Technique Deserialize(string yaml, string source = "<yaml>")
    {
        Technique? technique;
        try
        {
            technique = Deserializer.Deserialize<Technique>(yaml);
        }
        catch (YamlException e)
        {
            var reason = e.InnerException?.Message ?? e.Message;
            throw new TechniqueFormatException(source, [$"line {e.Start.Line}, column {e.Start.Column}: {reason}"], e);
        }

        if (technique is null)
            throw new TechniqueFormatException(source, ["file is empty."]);

        var errors = TechniqueValidator.Validate(technique);
        if (errors.Count > 0)
            throw new TechniqueFormatException(source, errors);
        return technique;
    }

    public static string Serialize(Technique technique) => Serializer.Serialize(technique);
}

/// <summary>Reads and writes <see cref="Vec3"/> as a flow sequence: <c>[x, y, z]</c>.</summary>
internal sealed class Vec3YamlConverter : IYamlTypeConverter
{
    public bool Accepts(Type type) => type == typeof(Vec3) || type == typeof(Vec3?);

    public object ReadYaml(IParser parser, Type type, ObjectDeserializer rootDeserializer)
    {
        var start = parser.Consume<SequenceStart>();
        var values = new List<float>(3);
        while (!parser.TryConsume<SequenceEnd>(out _))
        {
            var scalar = parser.Consume<Scalar>();
            if (!float.TryParse(scalar.Value, NumberStyles.Float, CultureInfo.InvariantCulture, out var v))
                throw new YamlException(scalar.Start, scalar.End, $"'{scalar.Value}' is not a number.");
            values.Add(v);
        }

        if (values.Count != 3)
            throw new YamlException(start.Start, start.End, $"expected [x, y, z] but got {values.Count} value(s).");
        return new Vec3(values[0], values[1], values[2]);
    }

    public void WriteYaml(IEmitter emitter, object? value, Type type, ObjectSerializer serializer)
    {
        var v = (Vec3)value!;
        emitter.Emit(new SequenceStart(AnchorName.Empty, TagName.Empty, isImplicit: true, SequenceStyle.Flow));
        foreach (var c in new[] { v.X, v.Y, v.Z })
            emitter.Emit(new Scalar(c.ToString("0.0###", CultureInfo.InvariantCulture)));
        emitter.Emit(new SequenceEnd());
    }
}

using System.Numerics;
using JudoVisualizer.Data;
using Xunit;

namespace JudoVisualizer.Tests;

public class PoseEditTests
{
    // Authored keyframes at 0, 1 and 2 s: Tori walks along X, his right arm is at rest.
    private static Technique Sample() => TechniqueSerializer.Deserialize("""
        technique_name: "Pose Edit Sample"
        waza_group: "nage_waza"
        kyu_grade: 6
        belt_color: { name: "Wit", hex: "#FFFFFF" }
        duration_seconds: 2.0
        keyframes:
          - { time: 0.0, phase: "A", tori: { position: [0, 0, 0], rotation: [0, 0, 0], bones: { right_arm: [0, 0, 0], spine: [-10, 0, 0] } } }
          - { time: 1.0, phase: "B", tori: { position: [1, 0, 0], rotation: [0, 0, 0], bones: { right_arm: [0, 0, 0], spine: [-20, 0, 0] } } }
          - { time: 2.0, phase: "C", tori: { position: [2, 0, 0], rotation: [0, 0, 0], bones: { right_arm: [0, 0, 0], spine: [-10, 0, 0] } } }
        """);

    private static PoseEdit ArmEdit(float time, Vec3 rotation, float from, float to, string ease = PoseEase.Linear) => new()
    {
        Who = "tori", Bone = "right_arm", Time = time, Rotation = rotation,
        From = from, HoldFrom = time, HoldTo = time, To = to, Ease = ease,
    };

    private static Quaternion Arm(Technique t, float time) =>
        PoseEditing.SampleRotation(t.Keyframes, k => k.Tori, "RightArm", time);

    private static Quaternion Spine(Technique t, float time) =>
        PoseEditing.SampleRotation(t.Keyframes, k => k.Tori, "Spine", time);

    [Theory]
    [InlineData(0, 0, 0)]
    [InlineData(30, -45, 60)]
    [InlineData(-120, 80, -170)]
    [InlineData(10, -89, 5)]
    public void Euler_RoundTrips(float x, float y, float z)
    {
        var q = Rotations.FromEuler(new Vec3(x, y, z));

        Assert.True(Rotations.Angle(q, Rotations.FromEuler(Rotations.ToEuler(q))) < 0.01f);
        var e = Rotations.ToEuler(q);
        Assert.Equal(x, e.X, 0.05f);
        Assert.Equal(y, e.Y, 0.05f);
        Assert.Equal(z, e.Z, 0.05f);
    }

    [Fact]
    public void Euler_IsXThenYThenZ_LikeGodot()
    {
        // R = Rx(90)·Ry(90): Ry turns +X to -Z, then Rx turns -Z to +Y.
        var v = Vector3.Transform(Vector3.UnitX, Rotations.FromEuler(new Vec3(90, 90, 0)));

        Assert.True(Vector3.Distance(v, Vector3.UnitY) < 1e-5f);
    }

    [Fact]
    public void LogExp_RoundTrip()
    {
        var q = Rotations.FromEuler(new Vec3(20, -70, 140));

        Assert.True(Rotations.Angle(q, Rotations.Exp(Rotations.Log(q))) < 0.01f);
    }

    [Fact]
    public void Edit_HitsItsTargetAndFadesOut()
    {
        var file = new PoseEditFile { Edits = { ArmEdit(1, new Vec3(0, 0, 60), 0, 2) } };

        var edited = PoseEditing.Apply(Sample(), file);

        Assert.True(Rotations.Angle(Arm(edited, 1), Rotations.FromEuler(new Vec3(0, 0, 60))) < 0.01f);
        Assert.True(Rotations.Angle(Arm(edited, 0), Quaternion.Identity) < 0.01f);
        Assert.True(Rotations.Angle(Arm(edited, 2), Quaternion.Identity) < 0.01f);
        Assert.Equal(30, Rotations.Angle(Arm(edited, 0.5f), Quaternion.Identity), 0.1f); // linear: half way
        Assert.True(Rotations.Angle(Spine(edited, 1), Spine(Sample(), 1)) < 0.01f); // other bones untouched
    }

    [Fact]
    public void SmoothEdit_AddsKeyframesThatFollowTheCurve()
    {
        var file = new PoseEditFile { Edits = { ArmEdit(1, new Vec3(0, 0, 60), 0, 2, PoseEase.Smooth) } };

        var edited = PoseEditing.Apply(Sample(), file);

        Assert.True(edited.Keyframes.Count > 10);
        Assert.All(edited.Keyframes.Where(k => k.Time is not (0 or 1 or 2)), k => Assert.True(k.Inbetween));
        Assert.Equal(60 * 0.15625f, Rotations.Angle(Arm(edited, 0.25f), Quaternion.Identity), 0.2f); // smoothstep(0.25)
        Assert.Empty(TechniqueValidator.Validate(edited));
    }

    [Fact]
    public void ApplyingTwice_ChangesNothing()
    {
        var file = new PoseEditFile
        {
            Edits =
            {
                ArmEdit(1, new Vec3(10, 30, 60), 0, 2, PoseEase.Smooth),
                ArmEdit(1.5f, new Vec3(-20, 0, 45), 0.5f, 2),
                new PoseEdit { Who = "tori", Bone = PoseEdit.Root, Time = 1, Position = new Vec3(1, 0, 0.3f), From = 0, HoldFrom = 1, HoldTo = 1, To = 2 },
            },
        };

        var once = PoseEditing.Apply(Sample(), file);
        var twice = PoseEditing.Apply(once, file);

        Assert.Equal(once.Keyframes.Count, twice.Keyframes.Count);
        foreach (var t in once.Keyframes.Select(k => k.Time))
        {
            Assert.True(Rotations.Angle(Arm(once, t), Arm(twice, t)) < 0.05f, $"arm at {t}");
            var p1 = PoseEditing.SamplePosition(once.Keyframes, k => k.Tori, t)!.Value;
            var p2 = PoseEditing.SamplePosition(twice.Keyframes, k => k.Tori, t)!.Value;
            Assert.True(Math.Abs(p1.Z - p2.Z) < 1e-4f, $"position at {t}");
        }
    }

    [Fact]
    public void OverlappingEdits_BothHitTheirTargets()
    {
        var file = new PoseEditFile { Edits = { ArmEdit(1, new Vec3(0, 0, 60), 0, 2), ArmEdit(1.5f, new Vec3(0, 0, -30), 0.5f, 2) } };

        var edited = PoseEditing.Apply(Sample(), file);

        Assert.True(Rotations.Angle(Arm(edited, 1), Rotations.FromEuler(new Vec3(0, 0, 60))) < 0.01f);
        Assert.True(Rotations.Angle(Arm(edited, 1.5f), Rotations.FromEuler(new Vec3(0, 0, -30))) < 0.01f);
        var spans = PoseEditing.Spans(file.Edits)[new PoseEditing.Channel("tori", "RightArm")];
        Assert.Equal((0f, 1.5f), (spans[0].From, spans[0].To)); // fade cut off at the other anchor
        Assert.Equal((1f, 2f), (spans[1].From, spans[1].To));
    }

    [Fact]
    public void SameHoldRange_LaterEditWins()
    {
        var file = new PoseEditFile { Edits = { ArmEdit(1, new Vec3(0, 0, 60), 0, 2), ArmEdit(1, new Vec3(0, 0, 20), 0, 2) } };

        var edited = PoseEditing.Apply(Sample(), file);

        Assert.True(Rotations.Angle(Arm(edited, 1), Rotations.FromEuler(new Vec3(0, 0, 20))) < 0.01f);
    }

    [Fact]
    public void HoldRange_AppliesTheSameCorrectionThroughout()
    {
        var edit = ArmEdit(1, new Vec3(0, 0, 40), 0, 2);
        edit.HoldFrom = 0.5f;
        edit.HoldTo = 1.5f;
        var file = new PoseEditFile { Keyframes = { 0.5f, 1.5f }, Edits = { edit } };

        var edited = PoseEditing.Apply(Sample(), file);

        Assert.True(Rotations.Angle(Arm(edited, 0.5f), Rotations.FromEuler(new Vec3(0, 0, 40))) < 0.01f);
        Assert.True(Rotations.Angle(Arm(edited, 1.5f), Rotations.FromEuler(new Vec3(0, 0, 40))) < 0.01f);
    }

    [Fact]
    public void InsertedKeyframe_IsSampledFromItsNeighbours()
    {
        var edited = PoseEditing.Apply(Sample(), new PoseEditFile { Keyframes = { 0.5f } });

        var inserted = edited.Keyframes.Single(k => k.Time == 0.5f);
        Assert.True(inserted.Inbetween);
        Assert.Equal(0.5f, inserted.Tori.Position!.Value.X, 1e-4f);
        Assert.Equal(-15, PoseEditing.BoneValue(inserted.Tori, "Spine")!.Value.X, 0.01f);
        Assert.Equal(3, Sample().Keyframes.Count); // the input is not changed
    }

    [Fact]
    public void SetValue_ChangesTheEditHoldingThatKeyframe()
    {
        var technique = Sample();
        var file = new PoseEditFile();
        var range = (0f, 1f, 1f, 2f);
        PoseEditing.SetValue(file, technique, "tori", "RightArm", 1, new Vec3(0, 0, 30), null, range);
        PoseEditing.SetValue(file, technique, "tori", "RightArm", 1, new Vec3(0, 0, 50), null, range);
        PoseEditing.SetValue(file, technique, "tori", PoseEdit.Root, 1, null, new Vec3(1, 0, 0.2f), range);

        Assert.Equal(2, file.Edits.Count);
        var edited = PoseEditing.Apply(technique, file);
        Assert.True(Rotations.Angle(Arm(edited, 1), Rotations.FromEuler(new Vec3(0, 0, 50))) < 0.01f);
        Assert.Equal(0.2f, PoseEditing.SamplePosition(edited.Keyframes, k => k.Tori, 1)!.Value.Z, 1e-4f);
        Assert.Null(file.Edits[1].Rotation); // only the position of the root was changed
    }

    [Fact]
    public void SetValue_InsideAHoldRange_MovesTheAnchorTarget()
    {
        var technique = Sample();
        var file = new PoseEditFile { Keyframes = { 1.5f } };
        var edit = ArmEdit(1, new Vec3(0, 0, 30), 0, 2);
        edit.HoldTo = 1.5f;
        file.Edits.Add(edit);

        PoseEditing.SetValue(file, technique, "tori", "RightArm", 1.5f, new Vec3(0, 0, 45), null, (0, 1.5f, 1.5f, 2));

        Assert.Single(file.Edits);
        Assert.True(Rotations.Angle(Arm(PoseEditing.Apply(technique, file), 1.5f), Rotations.FromEuler(new Vec3(0, 0, 45))) < 0.01f);
    }

    [Fact]
    public void File_RoundTripsAsJson()
    {
        var file = new PoseEditFile { Keyframes = { 1.24f }, Edits = { ArmEdit(1.2f, new Vec3(1.234f, 2, 3), 0.9f, 1.5f) } };

        var json = file.Serialize();
        var back = PoseEditFile.Parse(json);

        Assert.Contains("\"rotation\": [1.23, 2.0, 3.0]", json);
        Assert.Contains("\"hold_from\": 1.2", json);
        Assert.DoesNotContain("position", json);
        Assert.Equal(json, back.Serialize());
    }

    [Fact]
    public void TrySave_FileOpenElsewhere_FailsWithoutThrowingAndSucceedsLater()
    {
        var path = Path.Combine(Path.GetTempPath(), $"pose_edits_{Guid.NewGuid():N}.json");
        var file = new PoseEditFile { Keyframes = { 1 } };
        file.Save(path);
        file.Keyframes.Add(2);

        using (new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read)) // like a file watcher reading it
        {
            Assert.ThrowsAny<Exception>(() => file.Save(path)); // what crashed the editor
            Assert.False(file.TrySave(path, out var error));
            Assert.NotNull(error);
            Assert.False(File.Exists(path + ".tmp"));
        }

        Assert.True(file.TrySave(path, out _));
        Assert.Equal([1f, 2f], PoseEditFile.Load(path).Keyframes);
        File.Delete(path);
    }

    [Fact]
    public void EmptyFile_IsDeleted()
    {
        var path = Path.Combine(Path.GetTempPath(), $"pose_edits_{Guid.NewGuid():N}.json");
        new PoseEditFile { Keyframes = { 1 } }.Save(path);
        Assert.True(File.Exists(path));

        new PoseEditFile().Save(path);

        Assert.False(File.Exists(path));
    }
}

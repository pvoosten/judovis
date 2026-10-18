# Contributing

Thanks for wanting to help. The most welcome contributions are **better techniques**: a pose that is
not how a judo teacher would show it, a grip in the air, a fall that a beginner should not copy. You don't
need to program for that. Everything else is welcome too: new techniques, bug fixes, features, tests,
documentation.

Not sure whether something fits? Open an [issue](https://github.com/pvoosten/judovis/issues) and ask.

## What a technique must be

The app is meant for a beginner learning alone, who will copy every detail, mistakes included. So a
technique shows the textbook (Kodokan / VJF) form, right-handed (migi), as in uchikomi and nage-komi
rather than a competition variant. In short:

- A judo teacher recognises it from the side at normal speed.
- The grip (kumikata) is right and both hands are visibly on the gi.
- Kuzushi comes before kake and goes the right way; the footwork has the right steps in the right order.
- Uki falls safely: on the back or side, never head first, slapping the mat. Tori keeps the sleeve and
  ends in zanshin.
- The phase descriptions say in plain Dutch which hand or foot does what, for a 12-year-old.
- Bodies don't pass through each other, planted feet don't slide, Tori keeps his balance.

The full checklist with the numbers is the
[definition of done in CLAUDE.md](CLAUDE.md#definition-of-done-a-technique-a-6th-kyu-judoka-can-learn-from).
Its *Status* section lists the known issues of each animated technique: good places to start.

## Improving a technique

Pick the way that suits you; each one is a real contribution.

### 1. Say what is wrong (no tools needed)

Open an issue with the technique, the moment (the time or phase shown in the app) and what a teacher
would correct: "o-soto-gari, kake: Tori's supporting foot should be next to Uki's right foot, not
behind it". A screenshot helps.

If you run the app from source, you can also point at it: pause, press **F2**, click the body part and
type the comment. It is saved in `feedback/<technique>.yaml`; send that file in a pull request.

### 2. Fix the pose in the app (Godot only)

Run the app from source (see [Getting started](README.md#getting-started)) and press **F3**:

1. Step to a keyframe with ◀ ▶, or insert one at the playhead with "Keyframe invoegen".
2. Click a body part of Tori or Uki ("Wortel" moves or turns the whole judoka) and set it with the sliders.
3. Choose over which keyframes the correction fades in and out (*van*, *volledig vanaf*, *volledig tot*,
   *tot*). Ctrl+Z undoes.

The correction is saved in `edits/<technique>.json` and shown at once. Send that file in a pull request.
The next Blender run of the technique applies it on top of the script's poses, so it ends up in the
technique for everyone. A correction is taken as more correct than the script, so make sure it is how a
teacher would show it.

### 3. Change the Blender script

The poses come from `tools/blender/techniques/<technique>.py`, run in Blender 5.2.2. Read
[tools/blender/README.md](tools/blender/README.md) first: it describes the tools, the run order and the
template.

```sh
B=/c/tools/blender/blender.exe
$B -b art_source/blender/judoka.blend --python-exit-code 1 --python tools/blender/run_technique.py -- o_soto_gari --draft
```

Work with `--draft` until the poses are right, then do a full run (without `--draft`): it exports
`data/techniques/<technique>.yaml` and writes the reports to `build/reports/<technique>.log`. Put the report
numbers before and after your change in the pull request (contact overlap summed and worst, foot sliding,
balance) and attach a small contact sheet of the moments you changed:

```sh
G=/c/tools/godot/Godot_v4.7.2-stable_mono_win64_console.exe
$G --path . res://scenes/dev/PosePreview.tscn -- --technique=o_soto_gari --times=0.4,1.05,1.62 --views=side,three_quarter --sheet --size=320x180 --zoom=1.6 --out=build/preview
```

Never edit an animated technique's YAML by hand: the next run of its script overwrites it.

## Adding a technique

Techniques are animated per belt, starting with yellow (5th kyu). Next in line are uki-goshi,
kami-shiho-gatame, yoko-shiho-gatame and tate-shiho-gatame; after the yellow belt come orange, green, blue
and brown. Say in an issue which one you take, so no work is done twice.

Copy `tools/blender/techniques/_template.py` (or a similar technique: koshi-guruma for a hip throw,
kuzure-kesa-gatame for a hold) to `<technique>.py`. Copy the metadata of the technique's catalogue entry
in `data/techniques/` (code, kyu, belt, Dutch name) into the script's `META`: the script's export replaces
that file. Then work as in step 3 until the technique meets the definition of done. Whatever it does not meet yet goes in the pull request, so it can be listed under the
known issues.

## Code and other contributions

- `.\build.ps1` must pass: build, unit tests, asset import and a headless smoke run.
- C# namespaces follow the folders under `src/`. `src/Data/` stays free of Godot APIs so it can be tested
  with plain .NET; Godot-free logic elsewhere is listed in the test project. Add unit tests for such logic.
- Commit the `*.uid` and `*.import` files Godot generates. Models, images and `.blend` files go through
  Git LFS (set up by `.gitattributes`).
- The conventions, the YAML schema and the architecture are in [CLAUDE.md](CLAUDE.md). The project is
  developed with [Claude Code](https://claude.com/claude-code), which reads that file; you can use it too,
  but don't have to.

## Pull requests

- One technique per pull request, or one topic for code changes.
- Say what changed and why. For a technique: which items of the definition of done it improves, and
  the report numbers.
- Keep screenshots small and few.

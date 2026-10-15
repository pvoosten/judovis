# Judo Technique Visualizer 3D

Godot 4 (C#) app that plays judo techniques from YAML on two rigged judoka (Tori, Uki); technique
animation is authored in Blender with Python tools. Original spec and phase 0-7 prompts/decisions:
`docs/history.md` (read only when you need the background).

## Resources

- Blender 5.2.2 in c:\tools\blender (`blender.exe`); Godot 4.7.2 in c:\tools\godot
- Uki wears a blue gi, Tori wears a white gi

## Folder structure

The Godot project lives at the repo root (`res://` = repo root).

| Path | Contents |
| ---- | -------- |
| `assets/models/` | Exported `.glb` files (Tori.glb, Uki.glb) |
| `assets/materials/`, `assets/textures/` | Godot materials and textures |
| `data/techniques/` | Technique YAML, one per technique, snake_case (`ippon_seoi_nage.yaml`) |
| `scenes/main/`, `scenes/characters/`, `scenes/ui/` | `.tscn` scenes |
| `src/Data/` | YAML models, serializer/validator, TechniqueLoader (`JudoVisualizer.Data`) |
| `src/Playback/` | JudoTechniquePlayer, JudokaRig, KeyTrack, TechniqueTracks, PlaybackClock |
| `src/Camera/` | CameraManager, OrbitModel |
| `src/UI/` | HudController, TechniqueBrowser, TechniqueCaption, PlaybackBar, PhaseTimeline |
| `src/Dev/`, `scenes/dev/` | PosePreview screenshot renderer |
| `tests/JudoVisualizer.Tests/` | Unit tests; `Fixtures/` = fixed YAML independent of `data/` |
| `art_source/blender/` | `judoka.blend`; ignored by Godot (`.gdignore`) |
| `tools/blender/` | Build/export the judoka, technique tools, `techniques/<technique>.py`; see its `README.md` |
| `docs/` | Project history |

Conventions:
- C# namespaces follow the folder under `src/`.
- Binary assets (`.blend`, `.glb`, images) are in Git LFS.
- Every step is committed.
- `src/Data/` stays free of Godot APIs (except `TechniqueLoader.cs`) so it can be unit tested with plain .NET.
  Godot-free logic elsewhere (`KeyTrack`, `OrbitModel`, `TechniqueCatalog`, ...) is listed file by file in
  `tests/JudoVisualizer.Tests/JudoVisualizer.Tests.csproj`; keep Godot code in separate files.
- Commit Godot's generated `*.uid` and `*.import` files; `.godot/`, `bin/`, `obj/`, `build/` are ignored.
- Export preset "Windows Desktop" (`export_presets.cfg`) includes `data/techniques/*.yaml`.

## Commands

```powershell
.\build.ps1                                    # build, unit tests, asset import, headless smoke run
.\build.ps1 -Configuration Release -Export     # ... plus Windows export to build\windows\JudoVisualizer.exe
```

```sh
dotnet build JudoVisualizer.csproj
dotnet test JudoVisualizer.sln
G=/c/tools/godot/Godot_v4.7.2-stable_mono_win64_console.exe
$G --headless --path . --import                        # after adding/changing assets
$G --headless --path . --quit-after 10                 # smoke test
B=/c/tools/blender/blender.exe
$B -b art_source/blender/judoka.blend --python-exit-code 1 --python tools/blender/run_technique.py -- <technique> [--draft]
$G --path . res://scenes/dev/PosePreview.tscn -- --technique=<t> --times=0.4,1.1 --views=side,three_quarter --sheet --size=320x180 --zoom=1.6 --out=<dir>
```

## Authoring techniques

Technique YAML is generated from Blender, never written by hand (except metadata-only catalogue entries).
**Read `tools/blender/README.md` (API cheat sheet, run order, template) instead of the tool sources.**
- Script: `tools/blender/techniques/<technique>.py` (copy `_template.py` or a similar technique):
  metadata + one pose function per keyframe + `shape()` (weight/contact tools) + `check()` reports.
- Workflow: edit script -> headless run with `--draft` until the poses are right -> full run (exports the
  YAML) -> contact sheet of the doubtful moments -> `dotnet test` -> commit. Prefer the numeric reports
  over screenshots; keep screenshots small and few.
- Keep a root rotation change between consecutive keyframes below ~120° so slerp takes the intended way
  round; add in-between keyframes for big rotations.
- Euler angles are Godot `EulerOrder.Xyz` (R = Rx·Ry·Rz) = Blender Euler order `'ZYX'`.
- Each technique must pass the contact report (no penetration beyond tolerance), no foot sliding, and
  Tori balanced (see the reports in `check()`).

## YAML schema (summary; strict: unknown keys fail, see `TechniqueValidator`)

- Godot space, Y-up, metres, degrees (Euler XYZ). Tori starts at the origin facing +Z; Uki faces
  him with rotation `[0, 180, 0]` (at `[0, 0, 0.62]` when gripping). `position` = root between the feet at floor level.
- Bone rotations are deltas on the T-pose rest about the character's own axes (X = right, Y = up,
  -Z = facing); `spine: [-45, 0, 0]` bows forward. Children follow parents. A value missing from a keyframe
  is interpolated between the neighbouring keyframes that set it (held outside them; rest if never set).
- Fields: `technique_name`, `dutch_name`, `waza_group` (`nage_waza` | `osaekomi_waza` | `shime_waza` |
  `kansetsu_waza`), `category`, `code` (waza letter N/O/S/K + kyu (D = Dan/extra) + leerlijn number, e.g.
  `N4-3`), `difficulty`, `kyu_grade` (0 = Dan/extra), `belt_color {name, hex}`, `u18` (true for
  shime/kansetsu), `source`, optional `duration_seconds` + `keyframes` (both or neither; without them the
  entry is greyed "Nog geen animatie").
- Keyframe: `time`, `phase`, `description`, `tori`/`uki` {`position`, `rotation`, `bones`}; generated
  `inbetween: true` keyframes have no phase/description and no timeline tick.

## Kyu grades and belts (VJF "Leerlijn voor Kyu-graden" 2015)

| Kyu | Belt | Hex |
| --- | ---- | --- |
| 6 | Wit | #FFFFFF |
| 5 | Geel | #FFD700 |
| 4 | Oranje | #FF8C00 |
| 3 | Groen | #228B22 |
| 2 | Blauw | #1E90FF |
| 1 | Bruin | #8B4513 |
| 0 (Dan / extra) | Zwart | #000000 |

A technique's kyu is the belt whose exam lists it; 6th kyu has none. Shime/kansetsu are "extra vanaf U18"
(browser toggle). Kodokan waza not in the leerlijn are kyu 0. `data/techniques/` holds all 101 entries
(46 VJF + 55 Kodokan); the per-kyu list is in `docs/history.md` (phase 6) or via `kyu_grade`/`code`.

## Status

Phases 0-7 done (Blender MCP, judoka models, data model, player, cameras, HUD, catalogue, weight and
contact tools). Ippon-seoi-nage is the only animated technique. Known issues:
- Uki's POV camera can end up inside Tori's head when heads touch.
- Ippon-seoi-nage: overlaps up to ~3 cm beyond tolerance (heads in tsukuri/nage), Tori's feet creep a few
  cm, Tori briefly off balance at ~1.2 s while lifting.

## Phase 8: Animate techniques per kyu — TODO

- Order: 5th kyu (yellow) -> 4th -> 3rd -> 2nd -> 1st, then U18 shime/kansetsu, then Dan / extra.
- Each technique: script in `tools/blender/techniques/`, using the phase 7 tools; must pass the reports.
- Ground techniques (osaekomi, shime, kansetsu) start with Uki already on the mat (on the back or on four
  points); Tori moves into the hold and holds it (~3 s). Needs ground poses/helpers in `technique_tools.py`.
- One commit per technique.

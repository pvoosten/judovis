# Resources

## applications on pc

- Blender 5.2.2 in c:\tools\blender
- Godot 4.7.2 in c:\tools\godot

## judo settings

- Uki wears a blue gi, tori wears a white gi

## Folder structure

The Godot project lives at the repo root (`res://` = repo root).

| Path | Contents |
| ---- | -------- |
| `assets/models/` | Exported `.glb` files (Tori.glb, Uki.glb) |
| `assets/materials/`, `assets/textures/` | Godot materials and textures |
| `data/techniques/` | Technique YAML files, one per technique, named in snake_case (`ippon_seoi_nage.yaml`) |
| `scenes/main/`, `scenes/characters/`, `scenes/ui/` | `.tscn` scenes |
| `src/Data/` | YAML data models + TechniqueLoader (namespace `JudoVisualizer.Data`) |
| `src/Playback/` | JudoTechniquePlayer (`JudoVisualizer.Playback`) |
| `src/Camera/` | CameraManager (`JudoVisualizer.Camera`) |
| `src/UI/` | UI controllers (`JudoVisualizer.UI`) |
| `src/Dev/`, `scenes/dev/` | Developer tools (PosePreview screenshot renderer) |
| `tests/JudoVisualizer.Tests/Fixtures/` | Fixed YAML used by unit tests (independent of `data/`) |
| `tests/` | Unit tests (YAML parsing, interpolation) |
| `art_source/blender/` | Source `.blend` files; ignored by Godot (`.gdignore`) |
| `tools/blender/` | Python scripts: build/export the judoka, author techniques (`techniques/`); ignored by Godot |

Conventions:
- C# namespaces follow the folder under `src/`.
- Binary assets (`.blend`, `.glb`, images) are stored in Git LFS (see `.gitattributes`).
- Every step is committed.
- `src/Data/` stays free of Godot APIs (except `TechniqueLoader.cs`) so it can be unit tested with plain .NET.
  Godot-free logic elsewhere (e.g. `KeyTrack`, `OrbitModel`, `TechniqueCatalog`) is listed file by file in
  `tests/JudoVisualizer.Tests/JudoVisualizer.Tests.csproj`; keep Godot code in separate files.
- Commit Godot's generated `*.uid` and `*.import` files; `.godot/`, `bin/`, `obj/` are ignored.
- Exported builds need an export filter for non-resource files: `data/techniques/*.yaml`.

## Commands

```sh
dotnet build JudoVisualizer.csproj                     # build the Godot C# project
dotnet test JudoVisualizer.sln                         # unit tests (tests/JudoVisualizer.Tests)
G=/c/tools/godot/Godot_v4.7.2-stable_mono_win64_console.exe
$G --headless --path . --import                        # (re)import assets after adding/changing them
$G --headless --path . --quit-after 10                 # run the main scene headless (smoke test)
# Screenshots of a technique at given times/views (opens a window; views: side, other_side,
# front, back, three_quarter, top). Files: <out>/<technique>_<time>_<view>.png
$G --path . res://scenes/dev/PosePreview.tscn -- --technique=ippon_seoi_nage --times=0,1.2,2.6 --views=side --out=C:/tmp/preview
```

## Authoring techniques

Technique YAML is generated from Blender, not written by hand:
- `tools/blender/technique_tools.py`: helpers to pose the judoka (`place`, `rot`, `turn`, `aim`, `ik` onto
  grip bones, `pin`, `ground`), key poses and `export_yaml()`. Its maths mirrors `JudokaRig.cs`.
- `tools/blender/techniques/<technique>.py`: metadata + one pose function per keyframe. Run it in Blender
  (judoka.blend open) to key the timeline (FPS 50) and write `data/techniques/<technique>.yaml`.
- Workflow: edit the technique script -> run it in Blender -> save the .blend -> check with PosePreview
  (also between keyframes) -> `dotnet test` -> commit.
- Keep a root rotation change between consecutive keyframes below ~120° so slerp takes the intended way
  round; add in-between keyframes for big rotations (e.g. Uki's flip).
- Euler angles are Godot `EulerOrder.Xyz` (R = Rx·Ry·Rz), which is Blender's Euler order `'ZYX'`.

# Judo Technique Visualizer 3D - Development Guidelines & Prompts

Project specification and modular execution prompts for building an interactive 3D Judo Technique Visualizer in **Godot 4 (C#)**, integrated with **YamlDotNet** for technique data and **Blender MCP** for live 3D asset inspection/export.

---

## 1. System Architecture Overview

* **Game Engine:** Godot 4.x (C# runtime)
* **Data Serialization:** YamlDotNet (NuGet package)
* **3D Asset Pipeline:** Blender connected live to Claude Code via **Blender MCP Server**
* **Core Functionalities:**
  * Interactive playback control (slow-motion, scrubbing, phase tracking, reverse)
  * Dynamic multi-perspective camera views (Tori POV, Uki POV, Spectator Orbit)
  * Technique filtering by Kyu Grade (1st to 6th) and Belt Colors
  * Bone-level 3D skeleton keyframe interpolation driven by external YAML data


---

## 2. Standardized Judo Technique YAML Schema (`ippon_seoi_nage.yaml`)

Coordinate convention (Godot, Y-up, metres, rotations in degrees as Euler XYZ):
- Tori starts at the origin with rotation 0 and faces +Z (the models' front).
- Uki starts at `[0, 0, 1.2]` with rotation `[0, 180, 0]`, facing Tori.
- `position` is the judoka's root, which is **between the feet at floor level** (y = 0 = standing).
- Bone rotations are applied on top of the T-pose rest, about the character's own axes in Godot
  convention: X = character's right, Y = up, -Z = the way the character faces. So `spine: [-45, 0, 0]`
  bows 45° forward. Child bones follow their parents.
- Any value (position, rotation, bone) may be omitted from a keyframe; it is then interpolated
  between the neighbouring keyframes that set it (see Phase 3).

```yaml
technique_name: "Ippon Seoi-nage"
category: "Te-waza (Handworp)"
code: "T1"
difficulty: "Medium"
kyu_grade: 5 # 5e kyu = Geel
belt_color:
  name: "Gele band"
  hex: "#FFD700"
duration_seconds: 2.5
keyframes:
  - time: 0.0
    phase: "Kuzushi (Balansverstoring)"
    description: "Tori trekt Uki naar voren en uit balans op de teen."
    tori:
      position: [0.0, 0.0, 0.0]
      rotation: [0.0, 0.0, 0.0]
      bones:
        spine: [0.0, 0.0, 0.0]
        right_shoulder: [20.0, -10.0, 15.0]
        right_arm: [45.0, 30.0, -10.0]
        left_arm: [60.0, -20.0, 40.0]
    uki:
      position: [0.0, 0.0, 1.2]
      rotation: [0.0, 180.0, 0.0]
      bones:
        spine: [5.0, 0.0, 0.0]
        left_leg: [0.0, 0.0, -10.0]

  - time: 0.9
    phase: "Tsukuri (Instap & Draai)"
    description: "Tori draait in, duikt onder Uki's arm en klemt de oksel in."
    tori:
      position: [0.0, 0.0, 0.4]
      rotation: [0.0, 90.0, 0.0]
      bones:
        spine: [-15.0, 0.0, 0.0]
        right_shoulder: [85.0, 40.0, -30.0]
        right_arm: [90.0, 0.0, 0.0]
        left_arm: [40.0, -40.0, 20.0]
    uki:
      position: [0.0, 0.8, 0.4]
      rotation: [-15.0, 160.0, -10.0]
      bones:
        spine: [-20.0, 10.0, -15.0]

  - time: 1.6
    phase: "Kake (Worp & Handeling)"
    description: "Tori tilt Uki over zijn heup/rug door te buigen in de heupen."
    tori:
      position: [0.0, 0.0, 0.4]
      rotation: [0.0, 90.0, 0.0]
      bones:
        spine: [-45.0, 0.0, 0.0]
        right_shoulder: [90.0, 60.0, -40.0]
        left_arm: [20.0, -60.0, 10.0]
    uki:
      position: [-0.4, 1.4, -0.2]
      rotation: [-45.0, 90.0, -80.0]
      bones:
        right_leg: [30.0, 0.0, 20.0]

  - time: 2.5
    phase: "Landing / Tatami"
    description: "Uki: ukemi (val) op de mat."
    tori:
      position: [-0.6, 0.0, -0.2]
      rotation: [0.0, 45.0, 0.0]
      bones:
        spine: [0.0, 0.0, 0.0]
    uki:
      position: [-0.8, 0.0, -0.8]
      rotation: [-90.0, 0.0, -90.0]
      bones:
```

## 3. Kyu Grade & Belt Mapping Matrix

| Kyu Grade | Belt Color Name | Hex Code |
| --------- | --------------- | -------- |
| 6th Kyu   | White Belt      | #FFFFFF  |
| 5th Kyu   | Yellow Belt     | #FFD700  |
| 4th Kyu   | Orange Belt     | #FF8C00  |
| 3rd Kyu   | Green Belt      | #228B22  |
| 2nd Kyu   | Blue Belt       | #1E90FF  |
| 1st Kyu   | Brown Belt      | #8B4513  |

# TODO


## Phase 0: Blender MCP Integration Setup — DONE

Status: server registered in project `.mcp.json`; addon connected.

Help me connect my running Blender session to Claude Code via MCP.
1. Run the MCP server command: `claude mcp add blender uvx blender-mcp`
2. Install the Blender Addon via uvx: `uvx blender-mcp install-addon`
3. Instruct me to enable "Interface: MCP for Blender" in Blender Preferences (Edit -> Preferences -> Add-ons) and click "Connect to Claude" in the 3D Viewport sidebar (N-key panel).

## Phase 1: Live Blender Asset Preparation (via MCP) — DONE

Status: judoka are generated by `tools/blender/build_judoka.py` and exported by
`tools/blender/export_judoka.py` to `assets/models/Tori.glb` and `Uki.glb`.
- Skeleton: root bone `Hips` + the bones below; T-pose rest; character faces +Z in Godot, feet at y=0.
- Extra non-deforming grip bones for kumikata: `LeftLapelGrip`, `RightLapelGrip`,
  `LeftSleeveGrip`, `RightSleeveGrip`, `BackCollarGrip`, `BeltGrip` (use with BoneAttachment3D / IK targets).
- After changing the build script: run it, save the .blend, run the export script, commit.

Inspect the active Blender scene via MCP. 
Task 1: Locate the armature/skeleton for the judoka models (Tori and Uki). Standardize the bone names to follow Godot human skeleton standards:
- Spine, Chest, Neck, Head
- LeftShoulder, LeftArm, LeftForearm, LeftHand
- RightShoulder, RightArm, RightForearm, RightHand
- LeftUpLeg, LeftLeg, LeftFoot, RightUpLeg, RightLeg, RightFoot

Task 2: Ensure Tori and Uki have their origin points at [0,0,0] on floor level with transforms applied.
Task 3: Export Tori and Uki as binary glTF (.glb) files directly into the Godot project path `assets/models/`.

## Phase 2: Godot C# Core Data Model & YAML I/O — DONE

Status: Godot project at repo root (`project.godot`, `JudoVisualizer.csproj`, net8.0, YamlDotNet 16.3.0).
- Models: `Technique`, `BeltColor`, `Keyframe`, `JudokaPose`, `Vec3` (YAML `[x, y, z]`), plus
  `KyuGrades` (belt table) and `BoneNames` (YAML key -> skeleton bone, ignoring case/underscores).
- `TechniqueSerializer`: strict YAML <-> model (unknown keys fail) + `TechniqueValidator`
  (kyu 1-6, hex matches kyu, duration > 0, increasing keyframe times, known bone names).
- `TechniqueLoader` (Godot FileAccess): `LoadDirectory("res://data/techniques")`, `Load`, `Save` (use `user://techniques`).
- Test asset: `data/techniques/ippon_seoi_nage.yaml`. Main scene `scenes/main/Main.tscn` logs loaded techniques.

Initialize a new Godot 4 C# project structure for a Judo Technique Visualizer tool. 
Create the core C# data models (using YamlDotNet) matching a strict schema for judo techniques:
- Metadata: 
  - technique_name (string)
  - category (string, e.g. Te-waza, Koshi-waza)
  - difficulty (string)
  - kyu_grade (int, 1-6 representing 6th Kyu White to 1st Kyu Brown)
  - belt_color (struct/class with string 'name' and string 'hex')
  - duration_seconds (float)
- Keyframes array: time, phase (e.g., Kuzushi, Tsukuri, Kake), description, tori/uki states (positions [x,y,z], root rotations [x,y,z], and bone rotation dictionaries).
Integrate YamlDotNet via NuGet, write a service to read and export YAML files, and include a default test asset for "Ippon Seoi-nage" (5th Kyu / Yellow Belt / #FFD700).

## Phase 3: Godot 3D Player & Skeleton Interpolation — DONE

Status:
- Engine-independent (unit tested): `KeyTrack` (per-value keys, bracketing sample, hold outside range),
  `TechniqueTracks` (technique -> tracks per judoka; `Phases`/`KeyframeIndexAt`: the phase shown is that of
  the keyframe nearest in time, i.e. segments run between midpoints of neighbouring keyframes),
  `PlaybackClock` (speed, reverse, loop).
- Godot: `JudoTechniquePlayer` (Node3D; exports `Tori`, `Uki`, `Loop`, `Speed`; `Load`, `Play`, `Pause`,
  `TogglePlay`, `Stop`, `Seek`, `Step`; signals `TimeChanged`, `KeyframeChanged`, `PlayingChanged`)
  and `JudokaRig` (finds the Skeleton3D, binds bones by name, lerp/slerp, applies bone deltas).
- `scenes/main/Main.tscn`: tatami, light, Tori/Uki instances, player, temporary fixed camera.

Write a Godot C# script named `JudoTechniquePlayer.cs` that inherits from Node3D. 
This script should take parsed YAML technique data and drive the imported 3D avatars (Tori and Uki) in real-time. 
It must:
1. Interpolate (lerp for positions, slerp/lerp for rotations) smoothly between keyframes based on current playback time and keyframe timestamps.
2. Target the standardized bone names within Godot `Skeleton3D` nodes dynamically using the bone rotation dictionaries from YAML.
3. Handle playback state (playing, paused, elapsed time tracking, looping).

Missing bones: a keyframe does not have to list every bone. For each bone (per judoka), interpolate
between the nearest earlier and later keyframes that *do* list that bone. Before the first / after
the last keyframe listing it, hold that value. A bone listed in no keyframe stays at its rest pose.

## Phase 4: Dynamic Camera Perspective Manager — DONE

Status:
- `OrbitModel` (engine-independent, unit tested): fixed height, azimuth, clamped distance; `Orbit(+)` moves
  the camera to its own right, `Approach(+)` moves closer.
- `CameraManager` (Node in Main.tscn; exports `Camera`, `Tori`, `Uki`, orbit/transition settings):
  `Mode`, `SetMode(mode, immediate)`, `NextMode()`, signal `ModeChanged`; glides ~0.5 s between modes.
  Orbit looks at the (smoothed) midpoint of both judoka's hips. POV = eyes in front of the face, following
  the Head bone. Runs after the player each frame (ProcessPriority 100).
- Input actions (registered at runtime if missing): `camera_orbit_left/right` (←/→), `camera_closer/further`
  (↑/↓), `camera_mode_orbit/tori/uki` (1/2/3), `camera_next_mode` (C). Mouse drag circles, wheel zooms.
- Known limitation: when heads touch (Tsukuri), Uki's POV camera can end up inside Tori's head.

Create a CameraManager C# script for Godot that manages a central Camera3D and allows seamless switching between three distinct perspectives:
1. Tori's POV: Camera is attached to / follows Tori's head or upper body bone to experience the attacker's viewpoint.
2. Uki's POV: Camera is attached to / follows Uki's head to experience the throw from the receiver's perspective.
3. Spectator Orbit Camera: A free-roaming orbit camera centered between Tori and Uki, controllable with mouse and keyboard to view the throw from any angle.
Provide clean C# methods and events to trigger camera mode switches dynamically.

Spectator orbit camera behaviour:
- It stays at a fixed height above the tatami (it never goes up or down) and always looks at the
  judoka (the point midway between Tori and Uki, following them as they move).
- Arrow keys, relative to what you see: Left/Right circle the camera around the judoka
  (Left = camera moves to the left around them), Up/Down move the camera closer to / further from
  them (with a minimum and maximum distance).


## Phase 5: UI Controller & Kyu Grade Filtering — DONE

Status (`scenes/ui/Hud.tscn` under the `UI` CanvasLayer in Main.tscn; panels build their controls in code):
- `HudController`: wires everything to `JudoTechniquePlayer` + `CameraManager`; keys Space = play/pause,
  `,`/`.` = frame back/forward (runtime input actions). HUD controls never take keyboard focus.
- `TechniqueBrowser` (left): filter per kyu grade, groups 6th -> 1st kyu with belt badges; selecting loads + plays.
- `TechniqueCaption` (top): technique name + current phase.
- `PlaybackBar` (bottom): `PhaseTimeline` scrubber (phase bands, keyframe ticks, playhead), |< < Play > >|,
  time, speed 0.1x-2x, Reverse, Loop, camera mode.
- `JudokaAppearance.SetBeltColor` recolours the `Belt` material; `Main` applies the technique's belt colour.
- Player additions: `TechniqueChanged` signal, `Phases`, `StepKeyframe(direction)`.

Create a Godot UI layout (Control nodes) and a C# UI controller script:
1. Technique Browser Sidebar:
   - Filter and group loaded techniques by Kyu Grade / Belt Color (6th Kyu White, 5th Kyu Yellow, 4th Kyu Orange, 3rd Kyu Green, 2nd Kyu Blue, 1st Kyu Brown).
   - Display a colored UI badge/indicator corresponding to the belt's hex code next to each technique.
2. Playback Control Bar:
   - Play / Pause / Step-frame buttons.
   - Timeline slider (scrubber) displaying phase indicators (Kuzushi, Tsukuri, Kake) and current playback position.
   - Speed multiplier control (slider/buttons) supporting slow-motion (e.g. 0.1x, 0.25x, 0.5x, 1.0x, 2.0x) and reverse playback.
Connect these UI elements cleanly to the JudoTechniquePlayer and TechniqueLoader services.
3. Technique caption:
   - Always visible in the 3D view: shows the name of the technique currently loaded in the player
     (e.g. "Ippon Seoi-nage"), and updates as soon as another technique is selected.
   - Also shows the current phase (e.g. "Kake (Worp)"), updated live during playback and scrubbing
     (from the player's `KeyframeChanged` signal).
4. Belt colour on the judoka:
   - Tori and Uki both wear a belt in the colour of the loaded technique's kyu grade
     (`belt_color.hex`, e.g. yellow for 5th kyu); it changes when another technique is selected.
   - The models' belt material is named `Belt` (belt band, knot and tails); override it per model at runtime.


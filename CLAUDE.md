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
| `tests/` | Unit tests (YAML parsing, interpolation) |
| `art_source/blender/` | Source `.blend` files; ignored by Godot (`.gdignore`) |
| `tools/blender/` | Python scripts for building/exporting the judoka; ignored by Godot |

Conventions:
- C# namespaces follow the folder under `src/`.
- Binary assets (`.blend`, `.glb`, images) are stored in Git LFS (see `.gitattributes`).
- Every step is committed.

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
      position: [0.0, 0.0, -1.2]
      rotation: [0.0, 180.0, 0.0]
      bones:
        spine: [5.0, 0.0, 0.0]
        left_leg: [0.0, 0.0, -10.0]

  - time: 0.9
    phase: "Tsukuri (Instap & Draai)"
    description: "Tori draait in, duikt onder Uki's arm en klemt de oksel in."
    tori:
      position: [0.0, 0.0, -0.4]
      rotation: [0.0, 90.0, 0.0]
      bones:
        spine: [-15.0, 0.0, 0.0]
        right_shoulder: [85.0, 40.0, -30.0]
        right_arm: [90.0, 0.0, 0.0]
        left_arm: [40.0, -40.0, 20.0]
    uki:
      position: [0.0, 0.8, -0.4]
      rotation: [15.0, 160.0, 10.0]
      bones:
        spine: [-20.0, 10.0, -15.0]

  - time: 1.6
    phase: "Kake (Worp & Handeling)"
    description: "Tori tilt Uki over zijn heup/rug door te buigen in de heupen."
    tori:
      position: [0.0, 0.0, -0.4]
      rotation: [0.0, 90.0, 0.0]
      bones:
        spine: [-45.0, 0.0, 0.0]
        right_shoulder: [90.0, 60.0, -40.0]
        left_arm: [20.0, -60.0, 10.0]
    uki:
      position: [0.4, 1.4, 0.2]
      rotation: [45.0, 90.0, 80.0]
      bones:
        right_leg: [30.0, 0.0, 20.0]

  - time: 2.5
    phase: "Landing / Tatami"
    description: "Uki: ukemi (val) op de mat."
    tori:
      position: [0.6, 0.0, 0.2]
      rotation: [0.0, 45.0, 0.0]
      bones:
        spine: [0.0, 0.0, 0.0]
    uki:
      position: [0.8, 0.0, 0.8]
      rotation: [90.0, 0.0, 90.0]
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

## Phase 2: Godot C# Core Data Model & YAML I/O

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

## Phase 3: Godot 3D Player & Skeleton Interpolation

Write a Godot C# script named `JudoTechniquePlayer.cs` that inherits from Node3D. 
This script should take parsed YAML technique data and drive the imported 3D avatars (Tori and Uki) in real-time. 
It must:
1. Interpolate (lerp for positions, slerp/lerp for rotations) smoothly between keyframes based on current playback time and keyframe timestamps.
2. Target the standardized bone names within Godot `Skeleton3D` nodes dynamically using the bone rotation dictionaries from YAML.
3. Handle playback state (playing, paused, elapsed time tracking, looping).

## Phase 4: Dynamic Camera Perspective Manager

Create a CameraManager C# script for Godot that manages a central Camera3D and allows seamless switching between three distinct perspectives:
1. Tori's POV: Camera is attached to / follows Tori's head or upper body bone to experience the attacker's viewpoint.
2. Uki's POV: Camera is attached to / follows Uki's head to experience the throw from the receiver's perspective.
3. Spectator Orbit Camera: A free-roaming orbit camera centered between Tori and Uki, controllable with mouse and keyboard to view the throw from any angle.
Provide clean C# methods and events to trigger camera mode switches dynamically.


## Phase 5: UI Controller & Kyu Grade Filtering

Create a Godot UI layout (Control nodes) and a C# UI controller script:
1. Technique Browser Sidebar:
   - Filter and group loaded techniques by Kyu Grade / Belt Color (6th Kyu White, 5th Kyu Yellow, 4th Kyu Orange, 3rd Kyu Green, 2nd Kyu Blue, 1st Kyu Brown).
   - Display a colored UI badge/indicator corresponding to the belt's hex code next to each technique.
2. Playback Control Bar:
   - Play / Pause / Step-frame buttons.
   - Timeline slider (scrubber) displaying phase indicators (Kuzushi, Tsukuri, Kake) and current playback position.
   - Speed multiplier control (slider/buttons) supporting slow-motion (e.g. 0.1x, 0.25x, 0.5x, 1.0x, 2.0x) and reverse playback.
Connect these UI elements cleanly to the JudoTechniquePlayer and TechniqueLoader services.


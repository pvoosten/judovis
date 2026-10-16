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
| `tools/feedback/` | FeedbackToPrompt: turns `feedback/<technique>.yaml` comments into a Claude Code prompt |
| `feedback/` | Bone comments written by the app (F2); `.gdignore`, not exported |
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
.\run.ps1                                      # build and start the app (-Console: log here; -NoBuild; -Exported)
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

## Pose feedback (dev)

Pause, press F2, click a bone of Tori or Uki, type a comment: saved in `feedback/<technique>.yaml`.
`dotnet run --project tools/feedback -- <technique|all> [--mark-done]` prints one compact prompt per technique
(also `build/feedback/<technique>.md`); `--mark-done` marks the emitted comments done.

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
contact tools). Animated: ippon-seoi-nage, koshi-guruma (phase 8 pilot), o-uchi-gari (3.0 cm summed), kuzure-kesa-gatame (passes all reports; hold 3.0 s), o-soto-gari. Known issues:
- Uki's POV camera can end up inside Tori's head when heads touch.
- Ippon-seoi-nage: overlaps up to ~3 cm beyond tolerance (16 cm summed over 25 pairs, most under
  1 cm: Uki's right arm past Tori's head at 1.72 s, thighs as Tori steps in at 0.46 s and turns at
  0.9-1.3 s, Tori's hook arm past Uki's left arm and hips at 0.5-0.66 s), Tori's feet creep ~1 cm,
  Tori 1.2 cm off balance at the 0.44 s / 0.88 s weight-shift window boundaries.
- Koshi-guruma: 81 cm summed over 28 pairs (worst 10.7 cm): Tori's left hand/forearm into Uki's chest and
  left arm at the fall (1.84-2.0 s), Tori's upper arm against Uki's held forearm (1.44-1.74 s, 8.6 cm).
  Tori's right arm: hand on Uki's back collar (two-link solve in `arm_round_neck`), swings there from the
  lapel 0.4-0.76 s (`arm_to_neck`); Uki's held arm swings ahead during the fall (`uki_arm_swing`).
  Tori could bow deeper at kake.
- O-soto-gari: 16.4 cm summed over 11 pairs, worst 4.7 cm (Definition of done item 12 wants <= 3 cm):
  Tori's sleeve forearm crosses Uki's gripping forearm at the step-in (0.3-0.4 s); a wider step fixes it
  but puts Tori ~6 cm off balance, an elbow pole lifts the elbow to shoulder height. Kuzushi onto
  Uki's right heel at 0.4 s is weak (item 3). Grips: hold() runs after the partner's arm has its final
  motion and again after hinge_elbows() (the forearm twist moves the sleeve grip bones); other
  techniques may have hands off the sleeve that the contact report does not show.

- O-uchi-gari: 3.0 cm summed over 3 pairs, worst 1.5 cm (Uki's sleeve forearm on Tori's forearm up
  to the reap, thighs as Tori steps down at 1.46 s); grip gaps <= 0.2 cm (`check()` reports them).
  Tori lets go of the sleeve as Uki lands (1.56 s; the sleeve is out of reach on the mat) and stands
  in zanshin without it, by the user's choice: Definition of done items 6-7 (keep the sleeve, pull it
  up) are not met. Uki slaps with both arms.

## Ippon-seoi-nage contact report — TODO

Goal: no pairs beyond tolerance (worst first in `build/reports/ippon_seoi_nage.log`). `motion.avoid()`
is deterministic and stable (a 5% parameter change moves the sum ~1 cm), so single runs can be compared.
- Uki's held right arm past Tori's head at 1.72 s (instant switch from over-the-shoulder to the sleeve
  pull). Blending the two targets, also in an arc over Tori's head, is worse: Tori's left hand follows
  the sleeve into Uki's arm.
- Thighs: Tori's right thigh on the step-in (0.46 s, 4.3 cm) and against Uki's left thigh while
  turning (0.9-1.3 s, 3.7 cm). A thigh allowance makes `contact.resolve` push less: deeper (5.8 cm).
- Tori's hook arm on its way into the armpit (0.5-0.66 s) past Uki's left forearm, chest and hips.
- Tried and dropped: the per-frame V-hook (`hook_on_uki`) beyond the tai-sabaki keyframe, a wider
  stance for Uki, smoothing Tori's hook arm, Uki holding Tori's right sleeve beyond 0.5 s.

## Phase 8: Animate techniques per kyu — TODO

- Order: 5th kyu (yellow) -> 4th -> 3rd -> 2nd -> 1st, then U18 shime/kansetsu, then Dan / extra.
- Each technique: script in `tools/blender/techniques/`, using the phase 7 tools; must pass the reports.
- Ground techniques (osaekomi, shime, kansetsu) start with Uki already on the mat (on the back or on four
  points); Tori moves into the hold and holds it (~3 s). Needs ground poses/helpers in `technique_tools.py`.
- One commit per technique.
- Pilot findings (koshi-guruma): a technique close to an existing one is a copy of its script with new
  poses (~1 h to a first version at ~13 runs: draft 55 s, full 85 s). Check poses numerically at a
  keyframe first (bone positions, not screenshots): most problems were bodies placed inside each other.
  Grip IK onto an unreachable grip bone silently stretches the arm straight; aim limbs in the partner's
  own frame (`poses.axis`) and `repose` them. Getting to zero pairs beyond tolerance is the slow part;
  the acceptance threshold is in the definition of done below.

## Definition of done: a technique a 6th kyu judoka can learn from

Audience: a white belt (6th kyu) preparing the yellow-belt exam, watching alone, without a teacher next
to them. They copy what they see, mistakes included, so the animation must show the textbook (Kodokan /
VJF) form, right-handed (migi), static practice (uchikomi / nage-komi), not a competition variant.
Milestone "6th kyu ready": all 8 yellow-belt (5th kyu) entries meet this: N5-1 koshi-guruma, N5-2
o-soto-gari, N5-3 uki-goshi, N5-4 o-uchi-gari, O5-1 kuzure-kesa-gatame, O5-2 kami-shiho-gatame,
O5-3 yoko-shiho-gatame, O5-4 tate-shiho-gatame. Every technique is done when all of these hold:

**Judo content** (check in the contact sheet and the poses; a black belt would sign it off)
1. Recognisable: a judo teacher names the technique from the side view at 1x speed.
2. Kumikata: the grip of the technique (standard: Tori's right hand on Uki's left lapel, left hand on
   Uki's right sleeve at the elbow; technique-specific grips such as koshi-guruma round the neck or
   ippon-seoi-nage's arm under the armpit), both hands visibly on the gi, not in the air.
3. Kuzushi is visible before kake and in the right direction: Uki's weight moves over the toes (forward
   throws) or onto the heel of the attacked leg (o-uchi-gari, o-soto-gari), and Tori's hikite (sleeve
   hand) pulls, not just follows.
4. Footwork is correct and countable: the right number of steps in the right order, the correct foot
   (e.g. o-soto-gari: left foot steps beside Uki's right foot, right leg reaps Uki's right leg from
   behind; hip throws: Tori's feet inside and in front of Uki's, knees bent, hips below Uki's belt).
   Planted feet do not slide.
5. The contact point is right: hip for koshi-waza, back for seoi-nage, the back of the leg/calf for a
   reap (gari), not the knee or foot.
6. Safe falling (ukemi), the thing a beginner copies first: Uki lands on back/side, never head or neck
   first; Uki slaps the mat with the free arm (~45° from the body, palm down); Tori keeps the sleeve to
   the end and pulls it up so Uki's head stays off the mat; Tori stays on his feet and does not fall on
   Uki (except sutemi/makikomi waza).
7. Ends in zanshin: Tori upright, still holding the sleeve, looking at Uki.
8. Osaekomi: Uki on the back; Tori's position matches the hold (kesa: sitting beside Uki's right side,
   Uki's right arm trapped under Tori's armpit, Tori's right arm round the neck, legs spread wide;
   yoko: across the chest from the side; kami: from the head end; tate: astride), visibly controlling
   Uki's shoulders, held still for >= 3 s. Shime/kansetsu: pressure on the neck sides / against the
   joint, never against the throat or the spine.

**Teaching** (the learner reads along)
9. Phases in order with Dutch descriptions on the timeline: Kumikata, Kuzushi, Tsukuri, Kake, (Nage),
   Ukemi, Zanshin for nage-waza; for osaekomi entry, hold, (held). Each description says which hand/foot
   does what and where to, in words a 12-year-old understands; Japanese terms only in the phase name.
10. Readable in slow motion (0.25x): continuous motion, no freezes, snaps, or limbs passing through each
    other; normal speed is realistic (throw 2-3 s, hold >= 3 s after the entry).
11. The key moments (kuzushi, kake, landing) are clear from the side and three_quarter cameras.

**Technical** (numbers from `check()` in `build/reports/<technique>.log`)
12. Contact: no pair deeper than 3 cm beyond tolerance and <= 20 cm summed over all pairs (smaller
    overlaps are not visible to a learner). Zero beyond tolerance stays the aim; document what remains
    under Known issues.
13. Foot sliding: planted feet creep <= 1 cm. Balance: Tori <= 2 cm outside the support area (except
    deliberate sutemi).
14. Metadata matches the VJF leerlijn (code, kyu, belt, Dutch name); `dotnet test` passes; the YAML is
    generated by the script; one commit per technique, with the report numbers in the message.

Review: after the full run, render one small contact sheet of kuzushi, kake and landing and check items
1-11 against it as a judo teacher would; list anything not met under Known issues, not silently.

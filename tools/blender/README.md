# Blender technique tools — cheat sheet

Read this instead of the sources. Signatures are exact; see the docstrings only when a detail matters.
Spaces: root `place`/`rot`/`aim` work in Godot space / the judoka's frame A (X = right, Y = up,
-Z = facing); world points (`bone_pos`, `pin`, `aim_at`, `ik_point`) are **Blender** space (z up).
Frames: `FPS = 50`, `frame(t) = round(t * 50)`. Judoka are `"Tori"` and `"Uki"`; mat = `contact.MAT`.

## Running

```sh
B=/c/tools/blender/blender.exe
$B -b art_source/blender/judoka.blend --python-exit-code 1 --python tools/blender/run_technique.py -- <technique> [--draft] [--no-export] [--save] [--lines=5]
```
- `--draft`: skips `motion.avoid` (the slow part); iterate on poses with it, do the final run without.
- Prints report headers + the worst `--lines` lines each; the full log is `build/reports/<technique>.log`.
- `--save` saves the .blend; don't use it while judoka.blend is open in the Blender UI.

Preview (one labelled image; rows = times, columns = views):
```sh
G=/c/tools/godot/Godot_v4.7.2-stable_mono_win64_console.exe
$G --path . res://scenes/dev/PosePreview.tscn -- --technique=<t> --times=0.4,1.1,1.4,2.2 --views=side,three_quarter --sheet --size=320x180 --zoom=1.6 --out=<scratch>
```
Check the numbers first; take a sheet only for the keyframes in doubt.

## Script layout (copy `techniques/_template.py`, or a similar technique)

`META` -> `ALLOW` (allowed contacts) -> pose helpers -> one pose function per keyframe -> `KEYFRAMES`
-> `shape()` -> `check()` -> `main(upto=None, export=True)` (the runner calls `main`).
`main` clears animation, for each keyframe: `frame_set`, `reset` both, call the pose, `key` both;
then `shape()`, `check()`, `export_yaml`.

Order inside `shape()`: `ease` -> `pivot` -> feet (`plant`/`step`) -> `shift_weight` -> `carry` ->
`contact.resolve` -> `repose` -> `fall` -> `hold` -> `avoid` -> `limit_rate` / `smooth` -> `hinge_elbows`. Tools add keys inside segments; each reads what it
needs before keying, so later tools see earlier ones' results.

## technique_tools (`tt`) — posing at the current frame

| Function | Does |
| --- | --- |
| `reset(arm)` | clear pose and TMP_ constraints |
| `place(arm, position, rotation=(0,0,0))` | root in Godot space (as in the YAML) |
| `rot(arm, bone, (x,y,z))` | set bone delta, Godot Euler XYZ degrees, frame A |
| `turn(arm, bone, (x,y,z))` | add a rotation on top of the current delta |
| `aim(arm, bone, dir_A)` | point bone head->tail along a frame-A direction |
| `aim_at(arm, bone, world_point)` | point bone at a world point (minimal twist from the current pose: `rot(..., (0,0,0))` first for a twist-free aim per frame) |
| `hinge(arm, side)` | elbow bends forward in its hinge plane (upper arm twisted, max +-100°); nothing moves |
| `palm(arm, side, world_dir)` | turn the hand about the forearm so the palm faces a world direction |
| `ik(arm, bone, target_arm, target_bone, chain=3, pole=None)` | IK onto another bone's head (grips), baked |
| `ik_point(arm, bone, world_point, chain=3, pole=None)` | IK onto a world point |
| `bone_pos(arm, bone, tail=False)` | world position of head/tail |
| `pin(arm, bone, world_point, tail=False)` | translate root so the bone lands on the point |
| `ground(arm)` | lowest foot onto the floor (standing poses) |
| `key(arm, frame, bones=None, root=True)` | key linearly, hemisphere-safe quaternions |
| `export_yaml(path, meta, keyframes)` | bake timeline + in-betweens to YAML |

Grip bones: `LeftLapelGrip`, `RightLapelGrip`, `LeftSleeveGrip`, `RightSleeveGrip`, `BackCollarGrip`, `BeltGrip`.
Bones: Hips, Spine, Chest, Neck, Head, {Left,Right}{Shoulder,Arm,Forearm,Hand,UpLeg,Leg,Foot}.

## motion — on the keyed timeline (frames)

| Function | Does / returns |
| --- | --- |
| `ease(frame, easing="EASE_IN_OUT", mode="SINE")` | ease the segment starting at that key (`EASE_IN` build-up, `EASE_OUT` braking) |
| `pivot(arm, bone, f0, f1)` | bone (not root) moves in a straight line, e.g. Uki's Chest |
| `plant(arm, side, f0, f1, pivot="ankle", heel_lift=0.025, until_lifted=False)` | foot fixed on the mat (`pivot="toe"`: on the ball). Returns worst unreachable dist; with `until_lifted` the frame it lets go |
| `step(arm, side, f0, f1, height=0.06, to=None, around=None, lift=0.0)` | lift, move, put down (`around`: arc about a world point; `lift` ~0.15-0.25: fraction at each end with only vertical motion, no sliding at lift-off/touch-down) |
| `shift_weight(arm, side, f0, f1, ramp=5, carrying=None)` | hips so COM is over `"Left"`/`"Right"`/`"both"`; after plant/step; `ramp` may be `(in, out)` |
| `carry(carrier, carrier_bone, carried, pivot_bone, f0, f1)` | carried judoka moves in the carrier bone's frame |
| `fall(arm, f0, f1)` | ballistic COM between two keys; returns landing vertical speed |
| `hold(arm, hand, target_arm, target_bone, f0, f1, chain=3, pole=None)` | grip IK every frame |
| `avoid(arm, bones, other, f0, f1, allow=(), step=12, steps=3, smooth=0.002, relax=1, max_rate=None)` | per-frame tilt (max `step*steps`°) away from partner/mat: coarse grid + downhill refinement scored by distance from the previous frame's tilt, deterministic; `max_rate`: tilt change per frame (deg), no snaps (slow) |
| `repose(arm, bones, f0, f1, pose)` | call `pose(w)` (w 0..1) on every frame and key: limbs resting on the partner follow the partner |
| `limit_rate(arm, bones, f0, f1, max_degrees=15)` | each bone turns at most that much per frame: no avoid snaps (a bit more overlap there) |
| `smooth(arm, bones, f0, f1, radius=3)` | moving average of the rotations (takes out avoid flicker) |
| `hinge_elbows(arm, f0, f1)` | `tt.hinge` on every frame, twist rate-limited; run last |
| `settle(arm, clearance=0.015)` | lowest capsule onto the mat (lying/kneeling poses) |
| `com(arm)` | centre of mass (world) |
| `foot_sliding(arm, start=None, end=None)` + `print_sliding(report, title)` | sliding heels/toes |
| `balance(arm, start=None, end=None, margin=0, carrying=None)` + `print_balance(title, result)` | COM outside support |
| `first_mat_contact(arm, bones, start=None)` | {bone: time} first touching the mat (ukemi timing) |

## contact — capsules

| Function | Does / returns |
| --- | --- |
| `Allow(a, b, tolerance=0.04, start=-inf, end=inf)` | allowed overlap; `"Tori:Right*"` fnmatch patterns or `MAT`; times in s |
| `check_contacts(allow)` + `print_report(report)` | all frames; pairs beyond tolerance, deepest first |
| `separate(mover, other, allow=(), direction=None, max_distance=0.3)` | push mover's root out (current frame, in a pose function) |
| `resolve(mover, other, f0, f1, allow=(), direction=None)` | `separate` on every frame, keyed |
| `show_capsules()` / `hide_capsules()` | visualise capsules (UI only) |
| `fit_capsules(); save_capsules()` | after changing the judoka mesh |

Default tolerance 1.5 cm. Common allows: hands on grip bones (~0.07), arms rubbing (~0.045),
koshi-waza hip/back contact (~0.04), `Allow("*Foot", MAT, 0.03)`.

Arms: pose a forearm by aiming it anywhere, `hinge_elbows` then makes the elbow bend the anatomical
way. Free arms: give the elbow some bend (15-40°), never locked straight. A limb lying on the partner
between keyframes (arm over a shoulder, arm held by the sleeve): `repose` it relative to the partner,
otherwise its own rotations interpolate while the body tips over and it swings out.

## poses — shared building blocks (`from poses import ...`)

`frame(t)`, `lerp`, `GRIP_DISTANCE`; allows: `pairs(a_bones, b_bones, tol, start, end)`, `body_allow(allow)`
(+ any arm contact), `push_back(allow, direction)` (separate Uki ignoring arm contacts); directions
(world, horizontal): `facing(j)`, `right_of(j)`, `axis(j, (1, 0, 0))` (own axes, for a judoka lying down);
standing: `stance(j, knee)`, `arms_ready(j)`, `arms_down(j)`, `on_toes(j, heel)`, `crouch(j, depth, spread)`,
`grip()` (right-handed kumikata, both judoka), `ankles_mid(j)`, `stand(j, point, bone_point)` (move
horizontally so a bone lands on a point, then ground); mat: `slap(j, side)` (ukemi slap, after `settle`).
Technique-specific helpers stay in the script; move one into `poses.py` once a second technique uses it.

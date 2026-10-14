"""Exports Tori and Uki from the current Blender scene to assets/models/<Name>.glb.

Each judoka (armature + child body mesh) is exported on its own, at the origin with
identity transforms and in rest pose. The preview placement in the .blend (Uki facing
Tori) is restored afterwards.

glTF/Godot conventions: Y-up, the character faces +Z (Blender -Y), feet on y=0.
Skeleton contains the deforming humanoid bones plus the non-deforming *Grip bones.

Run inside Blender (Scripting tab, or via the Blender MCP), or headless:
    blender art_source/blender/judoka.blend --background --python tools/blender/export_judoka.py
"""
import os

import bpy
from mathutils import Matrix

JUDOKA = ("Tori", "Uki")
OUT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "models"))


def validate(arm):
    body = arm.children[0]
    assert arm.type == 'ARMATURE' and body.type == 'MESH', f"{arm.name}: expected armature + mesh"
    assert body.matrix_parent_inverse == Matrix.Identity(4), f"{body.name}: parent inverse not applied"
    assert body.matrix_basis == Matrix.Identity(4), f"{body.name}: local transform not applied"
    lowest = min(v.co.z for v in body.data.vertices)
    assert abs(lowest) < 1e-3, f"{body.name}: feet not on the floor (lowest z = {lowest:.4f})"


def export(arm, path):
    saved = arm.matrix_world.copy()
    arm.matrix_world = Matrix.Identity(4)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (arm, *arm.children))
    try:
        bpy.ops.export_scene.gltf(
            filepath=path, export_format='GLB', use_selection=True, export_yup=True,
            export_apply=False,          # keep the armature modifier: skinned mesh
            export_skins=True, export_def_bones=False,  # include non-deforming grip bones
            export_animations=False, export_morph=False, export_materials='EXPORT')
    finally:
        arm.matrix_world = saved


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for name in JUDOKA:
        arm = bpy.data.objects[name]
        validate(arm)
        path = os.path.join(OUT_DIR, f"{name}.glb")
        export(arm, path)
        print(f"exported {path} ({os.path.getsize(path) // 1024} KiB)")


if __name__ == "__main__":
    main()

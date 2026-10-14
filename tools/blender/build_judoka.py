"""Builds the Tori (white gi) and Uki (blue gi) judoka in the current Blender scene.

Each judoka is an armature object (`Tori` / `Uki`) with a child mesh (`<Name>_Body`).
Bones use Godot humanoid names; rest pose is a T-pose, character faces -Y, feet on z=0.
Every body part is rigidly weighted to a single bone.

Run inside Blender (Scripting tab, or via the Blender MCP), or headless:
    blender art_source/blender/judoka.blend --background --python tools/blender/build_judoka.py
Re-running replaces existing Tori/Uki objects. Save the .blend afterwards.
"""
import bpy
import bmesh
from mathutils import Vector, Matrix

TORI_GI = (0.90, 0.90, 0.88)
UKI_GI = (0.02, 0.10, 0.50)


def make_mat(name, rgb, rough=0.8):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*rgb, 1.0)
    return m


def bones_def():
    """(name, parent, head, tail, connected). Character's left is +X."""
    b = [("Hips", None, (0, 0, 0.95), (0, 0, 1.05), False),
         ("Spine", "Hips", (0, 0, 1.05), (0, 0, 1.22), True),
         ("Chest", "Spine", (0, 0, 1.22), (0, 0, 1.42), True),
         ("Neck", "Chest", (0, 0, 1.42), (0, 0, 1.52), True),
         ("Head", "Neck", (0, 0, 1.52), (0, 0, 1.76), True)]
    for side, s in (("Left", 1), ("Right", -1)):
        b += [(f"{side}Shoulder", "Chest", (0.03 * s, 0, 1.40), (0.17 * s, 0, 1.42), False),
              (f"{side}Arm", f"{side}Shoulder", (0.17 * s, 0, 1.42), (0.46 * s, 0, 1.42), True),
              (f"{side}Forearm", f"{side}Arm", (0.46 * s, 0, 1.42), (0.72 * s, 0, 1.42), True),
              (f"{side}Hand", f"{side}Forearm", (0.72 * s, 0, 1.42), (0.82 * s, 0, 1.42), True),
              (f"{side}UpLeg", "Hips", (0.10 * s, 0, 0.93), (0.10 * s, 0, 0.52), False),
              (f"{side}Leg", f"{side}UpLeg", (0.10 * s, 0, 0.52), (0.10 * s, 0, 0.09), True),
              (f"{side}Foot", f"{side}Leg", (0.10 * s, 0, 0.09), (0.10 * s, -0.14, 0.02), True)]
    return b


def build(name, gi_rgb):
    for o in list(bpy.data.objects):
        if o.name.split("_")[0] == name:
            bpy.data.objects.remove(o, do_unlink=True)

    gi = make_mat(f"Gi_{name}", gi_rgb, 0.85)
    mats = [gi, make_mat("Skin", (0.80, 0.55, 0.42), 0.6),
            make_mat("Hair", (0.05, 0.03, 0.02), 0.7), make_mat("Belt", (0.02, 0.02, 0.02), 0.7)]

    adata = bpy.data.armatures.new(f"{name}_Skeleton")
    arm = bpy.data.objects.new(name, adata)
    bpy.context.scene.collection.objects.link(arm)
    adata.display_type = 'STICK'
    arm.show_in_front = True
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.selected_objects:
        o.select_set(False)
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for bn, par, h, t, con in bones_def():
        eb = adata.edit_bones.new(bn)
        eb.head, eb.tail = Vector(h), Vector(t)
        if par:
            eb.parent = adata.edit_bones[par]
            eb.use_connect = con
    bpy.ops.object.mode_set(mode='OBJECT')

    me = bpy.data.meshes.new(f"{name}_Mesh")
    body = bpy.data.objects.new(f"{name}_Body", me)
    bpy.context.scene.collection.objects.link(body)
    for m in mats:
        me.materials.append(m)
    groups = {bn: body.vertex_groups.new(name=bn).index for bn, *_ in bones_def()}
    bm = bmesh.new()
    dl = bm.verts.layers.deform.verify()

    def tag(verts, bone, mi):
        for v in verts:
            v[dl][groups[bone]] = 1.0
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = mi
            f.smooth = True

    def cyl(p1, p2, r1, r2, bone, mi, sy=1.0, seg=20):
        p1, p2 = Vector(p1), Vector(p2)
        d = p2 - p1
        rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        M = Matrix.Translation((p1 + p2) / 2) @ rot @ Matrix.Diagonal((1, sy, 1, 1))
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2,
                                  depth=d.length, matrix=M)
        tag(r["verts"], bone, mi)

    def sph(c, r, bone, mi, sc=(1, 1, 1), cut=None):
        M = Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*sc, 1))
        vs = bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=r, matrix=M)["verts"]
        if cut:
            bmesh.ops.delete(bm, geom=[v for v in vs if cut(v.co)], context='VERTS')
            vs = [v for v in vs if v.is_valid]
        tag(vs, bone, mi)

    G, S, H, B = 0, 1, 2, 3
    # torso
    sph((0, 0, 0.87), 0.165, "Hips", G, (1, 0.72, 0.55))
    cyl((0, 0, 0.86), (0, 0, 1.06), 0.165, 0.16, "Hips", G, 0.72)
    cyl((0, 0, 1.04), (0, 0, 1.24), 0.158, 0.175, "Spine", G, 0.68)
    cyl((0, 0, 1.22), (0, 0, 1.40), 0.178, 0.19, "Chest", G, 0.64)
    sph((0, 0, 1.40), 0.19, "Chest", G, (1, 0.64, 0.32))
    # belt + knot + tails
    cyl((0, 0, 0.975), (0, 0, 1.02), 0.172, 0.172, "Hips", B, 0.75, 28)
    sph((0, -0.128, 0.997), 0.028, "Hips", B, (1.2, 0.6, 1))
    cyl((0.01, -0.13, 0.99), (0.04, -0.14, 0.84), 0.016, 0.016, "Hips", B, 0.4, 8)
    cyl((-0.01, -0.13, 0.99), (-0.05, -0.14, 0.85), 0.016, 0.016, "Hips", B, 0.4, 8)
    # neck + head + hair
    cyl((0, 0, 1.39), (0, 0, 1.56), 0.05, 0.05, "Neck", S)
    sph((0, -0.005, 1.645), 0.105, "Head", S, (0.92, 1.0, 1.12))
    sph((0, 0.008, 1.66), 0.112, "Head", H, (0.95, 1.0, 1.08),
        cut=lambda co: co.y < -0.03 and co.z < 1.72 or co.z < 1.60)
    for side, s in (("Left", 1), ("Right", -1)):
        # arms (T-pose)
        sph((0.17 * s, 0, 1.40), 0.078, f"{side}Shoulder", G)
        cyl((0.17 * s, 0, 1.41), (0.46 * s, 0, 1.42), 0.068, 0.058, f"{side}Arm", G)
        sph((0.46 * s, 0, 1.42), 0.057, f"{side}Forearm", G)
        cyl((0.46 * s, 0, 1.42), (0.64 * s, 0, 1.42), 0.058, 0.054, f"{side}Forearm", G)
        cyl((0.62 * s, 0, 1.42), (0.73 * s, 0, 1.42), 0.038, 0.034, f"{side}Forearm", S)
        sph((0.775 * s, 0, 1.418), 0.05, f"{side}Hand", S, (1.35, 1.0, 0.5))
        sph((0.745 * s, -0.045, 1.415), 0.018, f"{side}Hand", S, (1.6, 1, 1))  # thumb
        # legs
        cyl((0.10 * s, 0, 0.95), (0.10 * s, 0, 0.52), 0.092, 0.072, f"{side}UpLeg", G)
        sph((0.10 * s, 0, 0.52), 0.07, f"{side}Leg", G)
        cyl((0.10 * s, 0, 0.52), (0.10 * s, 0, 0.13), 0.07, 0.066, f"{side}Leg", G)
        cyl((0.10 * s, 0, 0.15), (0.10 * s, 0, 0.05), 0.04, 0.04, f"{side}Leg", S)
        sph((0.10 * s, -0.045, 0.04), 1.0, f"{side}Foot", S, (0.05, 0.12, 0.04))
    bm.to_mesh(me)
    bm.free()
    body.parent = arm
    body.modifiers.new("Armature", 'ARMATURE').object = arm
    return arm


if __name__ == "__main__":
    build("Tori", TORI_GI)
    uki = build("Uki", UKI_GI)
    # Preview placement only: Uki faces Tori. Export resets object transforms to the origin.
    uki.location = (0, -1.0, 0)
    uki.rotation_euler = (0, 0, 3.14159265)

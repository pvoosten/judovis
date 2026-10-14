"""Builds the Tori (white gi) and Uki (blue gi) judoka in the current Blender scene.

Each judoka is an armature object (`Tori` / `Uki`) with a child mesh (`<Name>_Body`).
Bones use Godot humanoid names; rest pose is a T-pose, character faces -Y, feet on z=0.

The judogi is modelled for realistic kumikata (gripping):
- jacket shell with a flared skirt, a thick collar/lapel (eri) crossing left over right
- wide, hollow sleeves (sode) ending above the wrist, wide hollow trousers
- flat belt (obi) with knot and tails
- weights blend across waist, shoulders, elbows and knees so the cloth bends smoothly
- non-deforming grip bones (*Grip) mark where a hand takes hold of the gi

Run inside Blender (Scripting tab, or via the Blender MCP), or headless:
    blender art_source/blender/judoka.blend --background --python tools/blender/build_judoka.py
Re-running replaces existing Tori/Uki objects. Save the .blend afterwards.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

TORI_GI = (0.90, 0.90, 0.88)
UKI_GI = (0.02, 0.10, 0.50)

# Jacket cross-section: (z, half-width x, half-depth y), ascending z.
PROFILE = [(0.70, .200, .150), (0.80, .195, .143), (0.90, .183, .133), (0.97, .172, .127),
           (1.05, .165, .120), (1.15, .168, .120), (1.25, .180, .124), (1.34, .192, .127),
           (1.40, .192, .122), (1.43, .175, .112), (1.455, .130, .090), (1.47, .085, .075),
           (1.48, .070, .066)]

LAPEL_WIDTH, LAPEL_THICK = 0.045, 0.012
D = math.radians
# Lapel keys from the back of the neck: (theta, z, offset) or ('x', x, z, offset).
# theta 0 = back (+y), 90 deg = wearer's left (+x), 180 deg = front (-y).
# The collar part hugs the neck (z ~1.475, where the jacket closes in around it).
TOP_LAPEL = [(0, 1.475, .002), (D(45), 1.474, .002), (D(90), 1.472, .002), (D(135), 1.465, .002),
             (D(160), 1.44, .004), ('x', .05, 1.37, .008), ('x', 0.0, 1.24, .013),
             ('x', -.06, 1.12, .008), ('x', -.10, .99, .004), ('x', -.115, .85, .004),
             ('x', -.12, .71, .004)]
UNDER_LAPEL = [(0, 1.475, .002), (-D(45), 1.474, .002), (-D(90), 1.472, .002), (-D(135), 1.465, .002),
               (-D(160), 1.44, .002), ('x', -.05, 1.37, .002), ('x', 0.0, 1.24, .001),
               ('x', .035, 1.16, -.010)]  # tucks under the top lapel


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def smooth(a, b, v):
    t = clamp((v - a) / (b - a))
    return t * t * (3 - 2 * t)


def prof(z):
    if z <= PROFILE[0][0]:
        return PROFILE[0][1:]
    for (z0, x0, y0), (z1, x1, y1) in zip(PROFILE, PROFILE[1:]):
        if z <= z1:
            t = (z - z0) / (z1 - z0)
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
    return PROFILE[-1][1:]


def surf(th, z, off=0.0):
    """Point on the jacket at angle th / height z, pushed out by off; plus the outward normal."""
    rx, ry = prof(z)
    x, y = rx * math.sin(th), ry * math.cos(th)
    n = Vector((x / (rx * rx), y / (ry * ry), 0)).normalized()
    return Vector((x, y, z)) + n * off, n


def th_front(x, z):
    return math.pi - math.asin(clamp(x / prof(z)[0], -1, 1))


def catmull(keys, n=6):
    pts = [keys[0]] + keys + [keys[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(keys[-1])
    return out


def lapel_path():
    """Collar + lapels as one continuous path: under-lapel tuck -> back of neck -> top-lapel hem.
    Returns [(base_point, outward_normal, is_top)]."""
    def resolve(k, under):
        if k[0] == 'x':
            th = th_front(k[1], k[2]) - (2 * math.pi if under else 0)
            return Vector((th, k[2], k[3]))
        return Vector(k)
    under = [resolve(k, True) for k in reversed(UNDER_LAPEL)]
    top = [resolve(k, False) for k in TOP_LAPEL[1:]]
    path = []
    for v in catmull(under + top):
        p, n = surf(v.x, v.y, v.z)
        path.append((p, n, v.x > 0))
    return path


def torso_w(z, x):
    t1, t2 = smooth(0.99, 1.07, z), smooth(1.17, 1.27, z)
    w = {"Hips": 1 - t1, "Spine": t1 * (1 - t2), "Chest": t2}
    side = "Left" if x > 0 else "Right"
    leg = clamp((0.95 - z) / 0.25) * 0.45 * clamp(abs(x) / 0.12)
    sh = clamp((abs(x) - 0.12) / 0.07) * clamp((z - 1.30) / 0.08) * 0.6
    for extra, bone in ((leg, f"{side}UpLeg"), (sh, f"{side}Shoulder")):
        if extra > 0:
            w = {k: v * (1 - extra) for k, v in w.items()}
            w[bone] = extra
    return w


def arm_w(xa, side):
    if xa < 0.22:
        sh = clamp((0.22 - xa) / 0.07) * 0.5
        return {f"{side}Shoulder": sh, f"{side}Arm": 1 - sh}
    t = smooth(0.40, 0.52, xa)
    return {f"{side}Arm": 1 - t, f"{side}Forearm": t}


def leg_w(z, side):
    if z > 0.85:
        h = clamp((z - 0.85) / 0.12) * 0.4
        return {"Hips": h, f"{side}UpLeg": 1 - h}
    t = smooth(0.46, 0.58, z)
    return {f"{side}UpLeg": t, f"{side}Leg": 1 - t}


def make_mat(name, rgb, rough=0.8):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*rgb, 1.0)
    return m


def bones_def():
    """Deforming bones: (name, parent, head, tail, connected). Character's left is +X."""
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


def grip_bones(path):
    """Non-deforming grip targets: (name, parent, head, tail). Tail points away from the body."""
    def on_lapel(top, z=1.36):
        p, n, _ = min((q for q in path if q[2] == top), key=lambda q: abs(q[0].z - z))
        head = p + n * LAPEL_THICK
        return head, head + n * 0.04
    belt_p, belt_n = surf(math.pi, 0.975, 0.027)
    collar_p, collar_n = surf(0, 1.475, 0.002 + LAPEL_THICK)
    g = [("BackCollarGrip", "Chest", collar_p, collar_p + collar_n * 0.04),
         ("BeltGrip", "Hips", belt_p, belt_p + belt_n * 0.04),
         ("LeftLapelGrip", "Chest", *on_lapel(True)),
         ("RightLapelGrip", "Chest", *on_lapel(False))]
    for side, s in (("Left", 1), ("Right", -1)):
        g.append((f"{side}SleeveGrip", f"{side}Forearm",
                  Vector((0.50 * s, 0, 1.42 - 0.072)), Vector((0.50 * s, 0, 1.42 - 0.11))))
    return g


def build(name, gi_rgb):
    for o in list(bpy.data.objects):
        if o.name.split("_")[0] == name:
            bpy.data.objects.remove(o, do_unlink=True)
    for coll, n in ((bpy.data.meshes, f"{name}_Mesh"), (bpy.data.armatures, f"{name}_Skeleton")):
        if n in coll:
            coll.remove(coll[n])

    gi = make_mat(f"Gi_{name}", gi_rgb, 0.85)
    mats = [gi, make_mat("Skin", (0.80, 0.55, 0.42), 0.6),
            make_mat("Hair", (0.05, 0.03, 0.02), 0.7), make_mat("Belt", (0.02, 0.02, 0.02), 0.7)]
    G, S, H, B = 0, 1, 2, 3
    path = lapel_path()

    # --- armature
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
    for bn, par, h, t in grip_bones(path):
        eb = adata.edit_bones.new(bn)
        eb.head, eb.tail = h, t
        eb.parent = adata.edit_bones[par]
        eb.use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')

    # --- mesh
    me = bpy.data.meshes.new(f"{name}_Mesh")
    body = bpy.data.objects.new(f"{name}_Body", me)
    bpy.context.scene.collection.objects.link(body)
    for m in mats:
        me.materials.append(m)
    groups = {bn: body.vertex_groups.new(name=bn).index for bn, *_ in bones_def()}
    bm = bmesh.new()
    dl = bm.verts.layers.deform.verify()
    custom = []  # faces built by hand; normals recalculated at the end

    def vert(co, w):
        v = bm.verts.new(co)
        for bone, val in w.items():
            if val > 1e-4:
                v[dl][groups[bone]] = val
        return v

    def face(vs, mi, smooth_shade=True, store=custom):
        f = bm.faces.new(vs)
        f.material_index, f.smooth = mi, smooth_shade
        store.append(f)
        return f

    def bridge(r1, r2, mi, closed=True, smooth_shade=True):
        n = len(r1)
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            face((r1[i], r1[j], r2[j], r2[i]), mi, smooth_shade)

    def tag(verts, bone, mi):
        for v in verts:
            v[dl][groups[bone]] = 1.0
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index, f.smooth = mi, True

    def cyl(p1, p2, r1, r2, bone, mi, sy=1.0, seg=20):
        p1, p2 = Vector(p1), Vector(p2)
        d = p2 - p1
        rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        M = Matrix.Translation((p1 + p2) / 2) @ rot @ Matrix.Diagonal((1, sy, 1, 1))
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2,
                                  depth=d.length, matrix=M)
        tag(r["verts"], bone, mi)

    def sph(c, r, bone, mi, sc=(1, 1, 1), plane=None, seg=(24, 14)):
        """UV sphere; plane=(point, normal) keeps only the part on the normal's side."""
        M = Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*sc, 1))
        vs = bmesh.ops.create_uvsphere(bm, u_segments=seg[0], v_segments=seg[1], radius=r, matrix=M)["verts"]
        if plane:
            geom = set(vs) | {e for v in vs for e in v.link_edges} | {f for v in vs for f in v.link_faces}
            res = bmesh.ops.bisect_plane(bm, geom=list(geom), plane_co=plane[0], plane_no=plane[1],
                                         clear_inner=True)
            vs = [v for v in vs if v.is_valid] + [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMVert)]
        tag(vs, bone, mi)

    def tube(rings, mi, hem=0.008, hem_depth=0.04, seg=24):
        """Hollow-ended tube. rings: [(center, radius, weights)]; open (hemmed) at the last ring."""
        axis = (rings[-1][0] - rings[0][0]).normalized()
        rot = axis.to_track_quat('Z', 'Y').to_matrix()
        ux, uy = rot.col[0], rot.col[1]

        def ring(c, r, w):
            return [vert(c + (ux * math.cos(a) + uy * math.sin(a)) * r, w)
                    for a in (2 * math.pi * i / seg for i in range(seg))]
        rs = [ring(c, r, w) for c, r, w in rings]
        c, r, w = rings[-1]
        rs.append(ring(c, r - hem, w))
        rs.append(ring(c - axis * hem_depth, r - hem, w))
        face(rs[0], mi)
        for a, b in zip(rs, rs[1:]):
            bridge(a, b, mi)
        face(rs[-1], mi)

    def sweep(samples, width, thick, mi, closed=False):
        """Rectangular band along [(base_point, outward_normal, weights)]."""
        rings = []
        n = len(samples)
        for i, (p, out, w) in enumerate(samples):
            a = samples[(i - 1) % n][0] if (closed or i > 0) else p
            b = samples[(i + 1) % n][0] if (closed or i < n - 1) else p
            t = (b - a).normalized()
            o = (out - t * out.dot(t)).normalized()
            bi = t.cross(o).normalized() * (width / 2)
            rings.append([vert(p + bi, w), vert(p - bi, w),
                          vert(p - bi + o * thick, w), vert(p + bi + o * thick, w)])
        for r1, r2 in zip(rings, rings[1:] + (rings[:1] if closed else [])):
            bridge(r1, r2, mi, smooth_shade=False)
        if not closed:
            face(rings[0], mi, False)
            face(rings[-1], mi, False)

    # --- jacket shell with flared skirt and thick hem
    seg = 32
    ths = [2 * math.pi * i / seg for i in range(seg)]
    outer = []
    for z, _, _ in PROFILE:
        outer.append([vert(p, torso_w(z, p.x)) for p in (surf(th, z)[0] for th in ths)])
    z0 = PROFILE[0][0]
    hem_in = [vert(Vector((p.x * .93, p.y * .93, z0)), torso_w(z0, p.x)) for p in (v.co for v in outer[0])]
    top_in = [vert(Vector((p.x * .9, p.y * .9, 0.86)), torso_w(0.86, p.x))
              for p in (surf(th, 0.86)[0] for th in ths)]
    for a, b in zip(outer, outer[1:]):
        bridge(a, b, G)
    face(outer[-1], G)
    bridge(outer[0], hem_in, G)
    bridge(hem_in, top_in, G)
    face(top_in, G)

    # --- collar + lapels (eri)
    sweep([(p, n, torso_w(p.z, p.x)) for p, n, _ in path], LAPEL_WIDTH, LAPEL_THICK, G)

    # --- skin showing in the V between the lapels, up to the neck
    tops = sorted((p for p, _, top in path if top and 1.22 < p.z < 1.48 and p.y < 0), key=lambda p: p.z)

    def lapel_x(z):
        return min(tops, key=lambda p: abs(p.z - z)).x
    patch, rows = [], []
    for k in range(11):
        z = 1.25 + 0.235 * k / 10
        hw = max(lapel_x(z) - 0.02, 0.002)
        rows.append([vert(surf(th_front(x, z), z, 0.003)[0], torso_w(z, x))
                     for x in (-hw + 2 * hw * c / 6 for c in range(7))])
    for r1, r2 in zip(rows, rows[1:]):
        for i in range(6):
            face((r1[i], r1[i + 1], r2[i + 1], r2[i]), S, store=patch)

    # --- belt (obi): band, knot, tails
    belt_ths = [2 * math.pi * i / 48 for i in range(48)]
    lapel_th = th_front(-0.098, 0.975)  # where the top lapel runs under the belt

    def belt_off(th):
        # 0.007 clears the skirt flaring out below the belt; bulges over the lapel
        return 0.007 + 0.010 * (1 - smooth(0.25, 0.45, abs(th - lapel_th)))
    sweep([(*surf(th, 0.975, belt_off(th)), {"Hips": 1}) for th in belt_ths], 0.045, 0.01, B, closed=True)
    knot, _ = surf(math.pi, 0.982, 0.03)
    sph(knot, 0.03, "Hips", B, (1.25, 0.6, 0.9))
    front = Vector((0, -1, 0))
    for s in (1, -1):
        tail = [knot + Vector((0.012 * s, 0.004, -0.01)), knot + Vector((0.045 * s, 0.0, -0.12)),
                knot + Vector((0.06 * s, 0.008, -0.24))]
        sweep([(p, front, {"Hips": 1}) for p in tail], 0.04, 0.008, B)

    # --- neck, head, hair
    # neck: tapers upwards, leans slightly forward, blends Chest -> Neck -> Head
    tube([(Vector((0, 0.010, 1.38)), .068, {"Chest": 1}),
          (Vector((0, 0.006, 1.45)), .062, {"Chest": .6, "Neck": .4}),
          (Vector((0, 0.000, 1.51)), .056, {"Neck": 1}),
          (Vector((0, -0.006, 1.58)), .054, {"Neck": .4, "Head": .6})], S, seg=20)
    head_c, head_r, head_sc = Vector((0, -0.005, 1.645)), 0.105, Vector((0.92, 1.0, 1.12))
    sph(head_c, head_r, "Head", S, head_sc, seg=(40, 24))
    for s in (1, -1):
        sph((0.094 * s, 0.0, 1.635), 0.03, "Head", S, (0.3, 0.6, 1.0))  # ears
    # hair: a cap 1.2 cm outside the head, cut by a tilted plane (forehead ~1.70, nape ~1.59)
    sph(head_c, head_r, "Head", H, (head_sc * head_r + Vector((.012, .012, .012))) / head_r,
        plane=(Vector((0, 0, 1.645)), Vector((0, 0.5, 1)).normalized()), seg=(40, 24))

    for side, s in (("Left", 1), ("Right", -1)):
        # wide sleeves, hollow cuff above the wrist; forearm visible inside
        sph((0.17 * s, 0, 1.405), 0.085, f"{side}Shoulder", G, (1, 1, 0.9))
        sleeve = [(0.15, .085), (0.25, .078), (0.35, .074), (0.46, .070), (0.56, .067), (0.655, .065)]
        tube([(Vector((x * s, 0, 1.42)), r, arm_w(x, side)) for x, r in sleeve], G)
        cyl((0.50 * s, 0, 1.42), (0.735 * s, 0, 1.42), 0.040, 0.034, f"{side}Forearm", S)
        sph((0.775 * s, 0, 1.418), 0.05, f"{side}Hand", S, (1.35, 1.0, 0.5))
        sph((0.745 * s, -0.045, 1.415), 0.018, f"{side}Hand", S, (1.6, 1, 1))  # thumb
        # wide trousers, hollow hem above the ankle
        pants = [(0.97, .100), (0.80, .093), (0.65, .087), (0.52, .080), (0.40, .076), (0.26, .073), (0.14, .071)]
        tube([(Vector((0.10 * s, 0, z)), r, leg_w(z, side)) for z, r in pants], G)
        cyl((0.10 * s, 0, 0.22), (0.10 * s, 0, 0.05), 0.046, 0.042, f"{side}Leg", S)
        sph((0.10 * s, -0.045, 0.04), 1.0, f"{side}Foot", S, (0.05, 0.12, 0.04))

    bmesh.ops.recalc_face_normals(bm, faces=[f for f in custom if f.is_valid])
    for f in patch:  # single-sided: make it face outwards
        f.normal_update()
        c = f.calc_center_median()
        if f.normal.dot(surf(th_front(c.x, c.z), c.z)[1]) < 0:
            f.normal_flip()
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
    uki.rotation_euler = (0, 0, math.pi)

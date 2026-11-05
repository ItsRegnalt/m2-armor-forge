# m2a_checks.py - Metin2 armor checks for Blender (bpy). MIT License.
# Load as a text block and exec, or import with sys.path. All functions return plain data and print a short table.
# Distances are in scene units (Blender metres unless the import used another scale).

import math
import struct
from collections import defaultdict

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HEAD_KEYS = ('head', 'neck')


# ----------------------------------------------------------------------------------------------------------- helpers
def _obj(o):
    return bpy.data.objects[o] if isinstance(o, str) else o


def _armature_of(o):
    o = _obj(o)
    if o is None:
        return None
    if o.type == 'ARMATURE':
        return o
    for m in o.modifiers:
        if m.type == 'ARMATURE' and m.object:
            return m.object
    return o.parent if o.parent and o.parent.type == 'ARMATURE' else None


def _world_verts(o, evaluated=True):
    """World-space vertex positions (with modifiers / pose when evaluated)."""
    o = _obj(o)
    if evaluated:
        dg = bpy.context.evaluated_depsgraph_get()
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        try:
            return [o.matrix_world @ v.co for v in me.vertices]
        finally:
            oe.to_mesh_clear()
    return [o.matrix_world @ v.co for v in o.data.vertices]


def _bvh(o, evaluated=True):
    o = _obj(o)
    bm = bmesh.new()
    if evaluated:
        dg = bpy.context.evaluated_depsgraph_get()
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        bm.from_mesh(me)
        oe.to_mesh_clear()
    else:
        bm.from_mesh(o.data)
    bm.transform(o.matrix_world)
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    return tree


def _signed_dist(tree, p):
    hit = tree.find_nearest(p)
    if hit[0] is None:
        return None
    loc, nor = hit[0], hit[1]
    d = (p - loc).length
    return d if (p - loc).dot(nor) >= 0 else -d


def _tris(o, evaluated=True):
    o = _obj(o)
    if evaluated:
        dg = bpy.context.evaluated_depsgraph_get()
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
    else:
        oe, me = None, o.data
    me.calc_loop_triangles()
    mw = o.matrix_world
    out = [[mw @ me.vertices[i].co for i in t.vertices] for t in me.loop_triangles]
    if oe:
        oe.to_mesh_clear()
    return out


def _tri_area(t):
    return ((t[1] - t[0]).cross(t[2] - t[0])).length * 0.5


def _groups_by_vertex(o):
    o = _obj(o)
    names = {g.index: g.name for g in o.vertex_groups}
    return [[(names[g.group], g.weight) for g in v.groups if g.group in names] for v in o.data.vertices]


def _materials(o):
    out = []
    for slot in _obj(o).material_slots:
        m = slot.material
        if not m:
            continue
        tex = []
        if m.use_nodes:
            tex = [n.image.filepath for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
        out.append((m.name, tex))
    return out


def _table(rows, head):
    w = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
    line = lambda r: ' | '.join(str(c).ljust(w[i]) for i, c in enumerate(r))
    print(line(head))
    print('-+-'.join('-' * x for x in w))
    for r in rows:
        print(line(r))


def _boundary_loops(o):
    """Open border loops of a mesh as lists of world positions (vertex indices too)."""
    o = _obj(o)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    edges = [e for e in bm.edges if e.is_boundary]
    adj = defaultdict(list)
    for e in edges:
        a, b = e.verts
        adj[a.index].append(b.index)
        adj[b.index].append(a.index)
    seen, loops = set(), []
    for start in adj:
        if start in seen:
            continue
        stack, comp = [start], []
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            comp.append(i)
            stack.extend(adj[i])
        loops.append(comp)
    mw = o.matrix_world
    co = {v.index: mw @ v.co for v in bm.verts}
    bm.free()
    return [(idx, [co[i] for i in idx]) for idx in loops]


def _head_bones(arm, head_bones=None):
    if head_bones:
        return [b for b in arm.data.bones if b.name in head_bones]
    return [b for b in arm.data.bones if any(k in b.name.lower() for k in HEAD_KEYS)]


def neck_border(body, armature=None):
    """The body's open border loop closest to the neck bone: (vertex indices, positions, centre)."""
    body = _obj(body)
    arm = _obj(armature) if armature else _armature_of(body)
    loops = _boundary_loops(body)
    if not loops:
        return None
    target = None
    if arm:
        hb = [b for b in arm.data.bones if 'neck' in b.name.lower()] or _head_bones(arm)
        if hb:
            target = arm.matrix_world @ hb[0].head_local
    if target is None:
        target = Vector((0, 0, max(p.z for _, pts in loops for p in pts)))
    best = min(loops, key=lambda L: (sum(L[1], Vector()) / len(L[1]) - target).length)
    c = sum(best[1], Vector()) / len(best[1])
    return best[0], best[1], c


# ------------------------------------------------------------------------------------------------------- inputs card
def inputs_report(armored, naked, armature_a=None, armature_n=None):
    rows, info = [], {}
    for slot, o, arm in (('original_armor', armored, armature_a), ('naked_body', naked, armature_n)):
        o = _obj(o) if o else None
        if o is None:
            rows.append((slot, '-', '-', '-', '-', 'MISSING'))
            info[slot] = None
            continue
        arm = _obj(arm) if arm else _armature_of(o)
        me = o.data
        me.calc_loop_triangles()
        mats = _materials(o)
        status = 'OK' if arm else 'PROBLEM: no armature'
        rows.append((slot, o.name, len(arm.data.bones) if arm else 0,
                     f'{len(me.vertices)} / {len(me.loop_triangles)}',
                     '; '.join(f"{m}:{','.join(t) or '-'}" for m, t in mats) or '-', status))
        info[slot] = dict(object=o.name, armature=arm.name if arm else None, verts=len(me.vertices),
                          tris=len(me.loop_triangles), materials=mats, status=status)
    _table(rows, ('slot', 'object', 'bones', 'verts / tris', 'materials:textures', 'status'))
    a, n = info.get('original_armor'), info.get('naked_body')
    if a and n and a['armature'] and n['armature']:
        r = rig_report(a['armature'], n['armature'], quiet=True)
        info['skeleton_match'] = r['status']
        print('skeleton match:', r['status'])
    return info


# ---------------------------------------------------------------------------------------------------------- rig
def _bone_data(arm):
    arm = _obj(arm)
    mw = arm.matrix_world
    out = {}
    for b in arm.data.bones:
        pb = arm.pose.bones.get(b.name)
        out[b.name] = dict(parent=b.parent.name if b.parent else None,
                           head=mw @ b.head_local, tail=mw @ b.tail_local,
                           mat=(mw @ b.matrix_local).copy(),
                           scale=tuple(pb.scale) if pb else (1, 1, 1))
    return out


def rig_report(arm_a, arm_b, tol=1e-4, quiet=False):
    A, B = _bone_data(arm_a), _bone_data(arm_b)
    missing = sorted(set(A) - set(B))
    extra = sorted(set(B) - set(A))
    diffs = []
    for n in sorted(set(A) & set(B)):
        a, b = A[n], B[n]
        reasons = []
        if a['parent'] != b['parent']:
            reasons.append(f"parent {a['parent']} != {b['parent']}")
        dh, dt = (a['head'] - b['head']).length, (a['tail'] - b['tail']).length
        if dh > tol or dt > tol:
            reasons.append(f'head {dh:.5f} tail {dt:.5f}')
        dm = max(abs(a['mat'][i][j] - b['mat'][i][j]) for i in range(3) for j in range(3))
        if dm > 1e-3:
            reasons.append(f'roll/orient {dm:.4f}')
        if max(abs(x - y) for x, y in zip(a['scale'], b['scale'])) > 1e-4:
            reasons.append(f"scale {a['scale']} != {b['scale']}")
        if reasons:
            diffs.append((n, '; '.join(reasons)))
    status = 'identical' if not (missing or extra or diffs) else 'DIFFERENT'
    if not quiet:
        print(f'rig: {status}  bones {len(A)} vs {len(B)}  missing {len(missing)}  extra {len(extra)}  changed {len(diffs)}')
        for n, r in diffs[:30]:
            print('  ', n, r)
    return dict(status=status, missing=missing, extra=extra, changed=diffs)


# ---------------------------------------------------------------------------------------------------------- locks
def lock_snapshot(armature, body, head_bones=None):
    """Record skeleton + head position from the ORIGINAL (call once, before any edit)."""
    arm = _obj(armature)
    nb = neck_border(body, arm)
    feet = min(v.z for v in _world_verts(body, evaluated=False))
    snap = dict(armature=arm.name, root=arm.data.bones[0].name if arm.data.bones else None,
                bones=_bone_data(arm),
                head_bones=[b.name for b in _head_bones(arm, head_bones)],
                neck_center=nb[2].copy() if nb else None,
                neck_height=(nb[2].z - feet) if nb else None,
                neck_radius=(sum((p - nb[2]).length for p in nb[1]) / len(nb[1])) if nb else None)
    print(f"lock snapshot: {len(snap['bones'])} bones, head bones {snap['head_bones']}, "
          f"neck height {snap['neck_height']}, neck radius {snap['neck_radius']}")
    return snap


def lock_check(snapshot, armature, armor=None, tol=1e-4, seam='skin'):
    """LOCKS OK when skeleton and head position match the snapshot. seam='skin' also checks the armor's neck border."""
    arm = _obj(armature)
    problems = []
    now = _bone_data(arm)
    old = snapshot['bones']
    if set(now) != set(old):
        problems.append(f'bone set changed: -{sorted(set(old) - set(now))} +{sorted(set(now) - set(old))}')
    if arm.data.bones and arm.data.bones[0].name != snapshot['root']:
        problems.append(f"root bone {arm.data.bones[0].name} != {snapshot['root']}")
    for n in set(now) & set(old):
        a, b = old[n], now[n]
        if a['parent'] != b['parent'] or (a['head'] - b['head']).length > tol or (a['tail'] - b['tail']).length > tol \
                or max(abs(x - y) for x, y in zip(a['scale'], b['scale'])) > 1e-4:
            problems.append(('HEAD ' if n in snapshot['head_bones'] else '') + f'bone moved: {n}')
    if armor is not None and seam == 'skin' and snapshot['neck_center'] is not None:
        nb = neck_border(armor, arm)
        if nb is None:
            problems.append('armor has no open neck border (skin join expected)')
        else:
            d = (nb[2] - snapshot['neck_center']).length
            r = sum((p - nb[2]).length for p in nb[1]) / len(nb[1])
            if d > tol * 5:
                problems.append(f'neck border centre moved {d:.5f}')
            if abs(r - snapshot['neck_radius']) > tol * 5:
                problems.append(f"neck border radius {r:.5f} != {snapshot['neck_radius']:.5f}")
    print('LOCKS OK' if not problems else 'LOCKS BROKEN')
    for p in problems[:30]:
        print('  ', p)
    return dict(ok=not problems, problems=problems)


# ---------------------------------------------------------------------------------------------------------- weights
def weight_report(obj, armature=None, max_inf=4, eps=1e-4):
    o = _obj(obj)
    arm = _obj(armature) if armature else _armature_of(o)
    bones = set(b.name for b in arm.data.bones) if arm else set()
    gv = _groups_by_vertex(o)
    unweighted, over, unnorm = [], [], []
    for i, gs in enumerate(gv):
        gs = [(n, w) for n, w in gs if w > eps and n in bones]
        if not gs:
            unweighted.append(i)
            continue
        if len(gs) > max_inf:
            over.append(i)
        s = sum(w for _, w in gs)
        if abs(s - 1) > 1e-3:
            unnorm.append(i)
    unknown = [g.name for g in o.vertex_groups if g.name not in bones]
    ok = not (unweighted or over or unnorm)
    print(f'weights {o.name}: {"OK" if ok else "PROBLEM"}  verts {len(gv)}  unweighted {len(unweighted)}  '
          f'>{max_inf} influences {len(over)}  unnormalised {len(unnorm)}  groups without bone {unknown}')
    return dict(ok=ok, unweighted=unweighted, over=over, unnormalised=unnorm, unknown_groups=unknown)


def limit_normalize(obj, max_inf=4, bones=None, eps=1e-4):
    """Keep the strongest max_inf bone groups per vertex and normalise them."""
    o = _obj(obj)
    names = {g.index: g.name for g in o.vertex_groups}
    for v in o.data.vertices:
        gs = [(g.group, g.weight) for g in v.groups if bones is None or names[g.group] in bones]
        gs.sort(key=lambda x: -x[1])
        keep = [(gi, w) for gi, w in gs[:max_inf] if w > eps]
        drop = [gi for gi, _ in gs if gi not in dict(keep)]
        for gi in drop:
            o.vertex_groups[gi].remove([v.index])
        s = sum(w for _, w in keep)
        for gi, w in keep:
            o.vertex_groups[gi].add([v.index], w / s if s > 0 else 0, 'REPLACE')


def transfer_weights(src, dst, max_inf=4):
    """Nearest-face-interpolated weight transfer by group name, then limit + normalise. Adds an Armature modifier."""
    src, dst = _obj(src), _obj(dst)
    arm = _armature_of(src)
    for g in src.vertex_groups:
        if g.name not in dst.vertex_groups:
            dst.vertex_groups.new(name=g.name)
    m = dst.modifiers.new('M2A_WeightTransfer', 'DATA_TRANSFER')
    m.object = src
    m.use_object_transform = True
    m.use_vert_data = True
    m.data_types_verts = {'VGROUP_WEIGHTS'}
    m.vert_mapping = 'POLYINTERP_NEAREST'
    m.layers_vgroup_select_src = 'ALL'
    m.layers_vgroup_select_dst = 'NAME'
    # keep it first so it is applied before any armature deformation
    while dst.modifiers.find(m.name) > 0:
        with bpy.context.temp_override(object=dst, active_object=dst):
            bpy.ops.object.modifier_move_up(modifier=m.name)
    with bpy.context.temp_override(object=dst, active_object=dst, selected_objects=[dst]):
        bpy.ops.object.modifier_apply(modifier=m.name)
    bones = set(b.name for b in arm.data.bones) if arm else None
    limit_normalize(dst, max_inf, bones)
    if arm and not any(md.type == 'ARMATURE' for md in dst.modifiers):
        am = dst.modifiers.new('Armature', 'ARMATURE')
        am.object = arm
    return weight_report(dst, arm, max_inf)


# ---------------------------------------------------------------------------------------------------------- neck seam
def neck_seam_report(body, armor, tol=0.0005, angle_tol=10.0):
    """Skin join: every armor neck-border vertex must lie on a body neck-border vertex (position, normal, weights)."""
    body, armor = _obj(body), _obj(armor)
    nb_b, nb_a = neck_border(body), neck_border(armor)
    if not nb_b or not nb_a:
        print('neck seam: no open border found', 'body' if not nb_b else 'armor')
        return dict(ok=False, reason='no border')
    gb, ga = _groups_by_vertex(body), _groups_by_vertex(armor)
    nb_norm = {i: (body.matrix_world.to_3x3() @ body.data.vertices[i].normal).normalized() for i in nb_b[0]}
    worst_d = worst_a = worst_w = 0.0
    for ia, pa in zip(nb_a[0], nb_a[1]):
        ib, pb = min(zip(nb_b[0], nb_b[1]), key=lambda t: (t[1] - pa).length)
        d = (pb - pa).length
        na = (armor.matrix_world.to_3x3() @ armor.data.vertices[ia].normal).normalized()
        ang = math.degrees(na.angle(nb_norm[ib], 0.0))
        wa, wb = dict(ga[ia]), dict(gb[ib])
        dw = max([abs(wa.get(k, 0) - wb.get(k, 0)) for k in set(wa) | set(wb)] or [0])
        worst_d, worst_a, worst_w = max(worst_d, d), max(worst_a, ang), max(worst_w, dw)
    ok = worst_d <= tol and worst_a <= angle_tol and worst_w <= 0.02 and len(nb_a[0]) == len(nb_b[0])
    print(f'neck seam: {"OK" if ok else "PROBLEM"}  border verts body {len(nb_b[0])} armor {len(nb_a[0])}  '
          f'max gap {worst_d:.5f}  max normal angle {worst_a:.1f}°  max weight diff {worst_w:.3f}')
    return dict(ok=ok, gap=worst_d, angle=worst_a, weight=worst_w, n_body=len(nb_b[0]), n_armor=len(nb_a[0]))


# ---------------------------------------------------------------------------------------------------------- proportion
DEFAULT_SLICE_KEYS = ('neck', 'clavicle', 'upperarm', 'forearm', 'hand', 'spine', 'pelvis', 'thigh', 'calf', 'foot')


def proportion_report(body, armor, armature=None, bones=None, min_w=0.5, ref_armor=None):
    """Per bone: body section width/depth (bone-local axes) and armor offset over the body (median, max).
    ref_armor: the ORIGINAL armor, to report its offsets side by side."""
    body, armor = _obj(body), _obj(armor)
    arm = _obj(armature) if armature else _armature_of(body)
    if bones is None:
        bones = [b.name for b in arm.data.bones if any(k in b.name.lower().replace(' ', '') for k in DEFAULT_SLICE_KEYS)]
    tree = _bvh(body, evaluated=False)

    def owned(o):
        gv = _groups_by_vertex(o)
        vs = _world_verts(o, evaluated=False)
        res = defaultdict(list)
        for v, gs in zip(vs, gv):
            if gs:
                n, w = max(gs, key=lambda x: x[1])
                if w >= min_w:
                    res[n].append(v)
        return res

    ob, oa = owned(body), owned(armor)
    orf = owned(_obj(ref_armor)) if ref_armor else {}
    rows, out = [], {}
    for n in bones:
        bone = arm.data.bones.get(n)
        if not bone or not ob.get(n):
            continue
        M = arm.matrix_world @ bone.matrix_local
        ax_x, ax_z = M.col[0].to_3d().normalized(), M.col[2].to_3d().normalized()
        bw = lambda pts, ax: (max(p.dot(ax) for p in pts) - min(p.dot(ax) for p in pts)) if pts else 0
        offs = sorted(_signed_dist(tree, p) or 0 for p in oa.get(n, []))
        roffs = sorted(_signed_dist(tree, p) or 0 for p in orf.get(n, [])) if orf else []
        med = offs[len(offs) // 2] if offs else None
        rmed = roffs[len(roffs) // 2] if roffs else None
        rec = dict(body_w=bw(ob[n], ax_x), body_d=bw(ob[n], ax_z), armor_w=bw(oa.get(n, []), ax_x),
                   armor_d=bw(oa.get(n, []), ax_z), off_med=med, off_max=offs[-1] if offs else None,
                   off_min=offs[0] if offs else None, ref_off_med=rmed)
        out[n] = rec
        f = lambda x: '-' if x is None else f'{x:.4f}'
        rows.append((n, f(rec['body_w']), f(rec['body_d']), f(rec['armor_w']), f(rec['armor_d']),
                     f(med), f(rec['off_max']), f(rec['off_min']), f(rmed)))
    _table(rows, ('bone', 'body w', 'body d', 'armor w', 'armor d', 'off med', 'off max', 'off min', 'orig off med'))
    return out


# ---------------------------------------------------------------------------------------------------------- poke / pose
def poke_through(body, armor, covered=None, eps=0.0, cover_dist=0.03):
    """Body vertices outside the armor. covered: vertex indices to test (default: body verts inside the armor
    and within cover_dist of it in the CURRENT pose's rest evaluation)."""
    tree = _bvh(armor)
    vs = _world_verts(body)
    if covered is None:
        covered = [i for i, p in enumerate(vs) if (lambda d: d is not None and -cover_dist <= d <= 0)(_signed_dist(tree, p))]
    bad = [i for i in covered if (_signed_dist(tree, vs[i]) or 0) > eps]
    return dict(covered=len(covered), poke=len(bad), ratio=len(bad) / max(1, len(covered)), indices=bad)


DEFAULT_POSES = {
    'bind': {},
    'arms_up': {'upperarm': (0, 0, 70)},
    'arms_down': {'upperarm': (0, 0, -30)},
    'arms_forward': {'upperarm': (0, 70, 0)},
    'elbow_bent': {'forearm': (0, 90, 0)},
    'torso_twist': {'spine': (25, 0, 0)},
    'leg_forward': {'l thigh': (0, 0, 60)},
    'leg_back': {'l thigh': (0, 0, -30)},
    'squat': {'thigh': (0, 0, 80), 'calf': (0, 0, -100)},
    'head_turn': {'head': (40, 0, 0)},
}


def pose_test(armature, body, armor, poses=None, eps=0.0, stretch_lim=2.5, poke_lim=0.005):
    """Poses: {name: {bone-name substring: (x, y, z) degrees local euler}}. Axes depend on the rig: check the bone
    list printed with each pose and adjust the dict if a pose bends the wrong way. Restores the pose afterwards."""
    arm, body, armor = _obj(armature), _obj(body), _obj(armor)
    poses = poses or DEFAULT_POSES
    saved = {pb.name: (pb.rotation_mode, pb.rotation_euler.copy(), pb.rotation_quaternion.copy()) for pb in arm.pose.bones}
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    tree0 = _bvh(armor)
    vs0 = _world_verts(body)
    covered = [i for i, p in enumerate(vs0) if (lambda d: d is not None and -0.03 <= d <= 0)(_signed_dist(tree0, p))]
    area0 = [_tri_area(t) for t in _tris(armor)]
    rows, out = [], {}
    try:
        for name, spec in poses.items():
            for pb in arm.pose.bones:
                pb.rotation_euler = (0, 0, 0)
            hit = []
            for key, rot in spec.items():
                for pb in arm.pose.bones:
                    if key in pb.name.lower():
                        pb.rotation_euler = tuple(math.radians(r) for r in rot)
                        hit.append(pb.name)
            bpy.context.view_layer.update()
            pk = poke_through(body, armor, covered=covered, eps=eps)
            area = [_tri_area(t) for t in _tris(armor)]
            st = max((a / a0 for a, a0 in zip(area, area0) if a0 > 1e-12), default=1.0)
            ok = pk['ratio'] <= poke_lim and st <= stretch_lim
            out[name] = dict(poke=pk['poke'], ratio=pk['ratio'], stretch=st, bones=hit, ok=ok)
            rows.append((name, pk['poke'], f"{pk['ratio'] * 100:.2f}%", f'{st:.2f}', 'OK' if ok else 'PROBLEM', len(hit)))
    finally:
        for pb in arm.pose.bones:
            m, e, q = saved[pb.name]
            pb.rotation_mode = m
            pb.rotation_euler = e
            pb.rotation_quaternion = q
        bpy.context.view_layer.update()
    _table(rows, ('pose', 'poke verts', 'poke %', 'max stretch', 'status', 'bones moved'))
    return out


# ---------------------------------------------------------------------------------------------------------- dds
def dds_info(path):
    with open(bpy.path.abspath(path), 'rb') as f:
        h = f.read(128)
    if h[:4] != b'DDS ':
        return dict(ok=False, reason='not a DDS file')
    height, width = struct.unpack_from('<II', h, 12)
    mips = struct.unpack_from('<I', h, 28)[0]
    pf_flags = struct.unpack_from('<I', h, 80)[0]
    fourcc = h[84:88].decode('ascii', 'replace') if pf_flags & 0x4 else None
    bits = struct.unpack_from('<I', h, 88)[0]
    alpha = bool(pf_flags & 0x1) or fourcc in ('DXT3', 'DXT5')
    info = dict(ok=True, width=width, height=height, mips=max(1, mips), fourcc=fourcc or f'RGB{bits}', alpha=alpha)
    print(f"dds: {width}x{height} mips {info['mips']} {info['fourcc']} alpha {alpha}")
    return info


# ---------------------------------------------------------------------------------------------------------- pose utils
def _save_pose(arm):
    return {pb.name: (pb.rotation_mode, pb.rotation_euler.copy(), pb.rotation_quaternion.copy()) for pb in arm.pose.bones}


def _restore_pose(arm, saved):
    for pb in arm.pose.bones:
        m, e, q = saved[pb.name]
        pb.rotation_mode, pb.rotation_euler, pb.rotation_quaternion = m, e, q
    bpy.context.view_layer.update()


def _apply_pose(arm, spec):
    hit = []
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        for key, rot in spec.items():
            if key in pb.name.lower():
                pb.rotation_euler = tuple(math.radians(r) for r in rot)
                hit.append(pb.name)
    bpy.context.view_layer.update()
    return hit


# ---------------------------------------------------------------------------------------------------------- region shift
def region_centroids(obj, min_w=0.5):
    """Centroid of the verts each bone owns (bind pose, weight >= min_w)."""
    obj = _obj(obj)
    acc = defaultdict(list)
    for v, gs in zip(_world_verts(obj, evaluated=False), _groups_by_vertex(obj)):
        if gs:
            n, w = max(gs, key=lambda x: x[1])
            if w >= min_w:
                acc[n].append(v)
    return {n: sum(p, Vector()) / len(p) for n, p in acc.items()}


def region_shift_report(ref, ours, armature=None, tol=0.01, min_w=0.5):
    """Head, chest, shoulders, hips must not drift. Compares per-bone centroids of `ours` with `ref` (the original
    armor, or the naked body for skin-tight areas) and reports the shift perpendicular to the bone
    (a longer sleeve along the bone is fine; a chest pushed forward or sideways is not)."""
    ours = _obj(ours)
    arm = _obj(armature) if armature else _armature_of(ours)
    ca, cb = region_centroids(ref, min_w), region_centroids(ours, min_w)
    rows, bad = [], []
    for n in sorted(set(ca) & set(cb)):
        b = arm.data.bones.get(n) if arm else None
        d = cb[n] - ca[n]
        if b:
            ax = ((arm.matrix_world @ b.tail_local) - (arm.matrix_world @ b.head_local)).normalized()
            d = d - ax * d.dot(ax)
        s = d.length
        if s > tol:
            bad.append(n)
        rows.append((n, f'{d.x:+.4f}', f'{d.y:+.4f}', f'{d.z:+.4f}', f'{s:.4f}', 'OK' if s <= tol else 'SHIFT'))
    _table(rows, ('bone', 'dx', 'dy', 'dz', 'shift', 'status'))
    print('region shift:', 'OK' if not bad else f'SHIFT in {bad}')
    return dict(ok=not bad, shifted=bad)


# ---------------------------------------------------------------------------------------------------------- part clipping
def split_parts(obj, by='LOOSE'):
    """Work copy of `obj` split into parts (by='LOOSE' or 'MATERIAL'); the original stays untouched."""
    o = _obj(obj)
    c = o.copy()
    c.data = o.data.copy()
    c.name = o.name + '_part'
    for col in o.users_collection:
        col.objects.link(c)
    before = set(bpy.data.objects)
    vl = bpy.context.view_layer
    prev_active, prev_sel = vl.objects.active, [x for x in vl.objects if x.select_get()]
    for x in prev_sel:
        x.select_set(False)
    c.select_set(True)
    vl.objects.active = c
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type=by)
        bpy.ops.object.mode_set(mode='OBJECT')
    finally:
        for x in vl.objects:
            x.select_set(x in prev_sel)
        vl.objects.active = prev_active
    return [c] + [x for x in bpy.data.objects if x not in before]


def part_clip_report(parts, margin=0.0005, allowed=(), evaluated=True, quiet=False):
    """Pairwise clipping between separate armor parts (belt, pauldrons, gloves, boots, knee pads...).
    Counts intersecting triangle pairs (BVH overlap) and vertices of one part closer than `margin` to the other's
    surface (near-clip: shows as z-fighting and clips as soon as the pose changes). A part fully under another (an
    inner layer) is fine: only crossing or touching surfaces fail.
    allowed: pairs of names that are meant to touch or tuck (e.g. a strap riveted into a plate); they are reported
    but do not fail."""
    parts = [_obj(p) for p in parts]
    trees = {p.name: _bvh(p, evaluated) for p in parts}
    verts = {p.name: _world_verts(p, evaluated) for p in parts}
    allowed = {frozenset(a) for a in allowed}

    def near(vs, tree):
        n = 0
        for v in vs:
            hit = tree.find_nearest(v, margin)
            if hit[0] is not None:
                n += 1
        return n

    rows, res = [], {}
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            inter = len(trees[a.name].overlap(trees[b.name]))
            ab, ba = near(verts[a.name], trees[b.name]), near(verts[b.name], trees[a.name])
            ok = (inter == 0 and ab == 0 and ba == 0) or frozenset((a.name, b.name)) in allowed
            res[(a.name, b.name)] = dict(intersections=inter, a_near_b=ab, b_near_a=ba, ok=ok)
            if not quiet or not ok:
                rows.append((a.name, b.name, inter, ab, ba, 'OK' if ok else 'CLIP'))
    if rows:
        _table(rows, ('part A', 'part B', 'tri hits', 'A verts touching B', 'B verts touching A', 'status'))
    bad = [k for k, v in res.items() if not v['ok']]
    print('part clipping:', 'OK' if not bad else f'CLIP in {len(bad)} pairs')
    return dict(ok=not bad, pairs=res, clipping=bad)


def pose_clip_test(armature, parts, body=None, poses=None, margin=0.0005, allowed=()):
    """part_clip_report (and poke-through against the body when given) in every pose of the pose set."""
    arm = _obj(armature)
    poses = poses or DEFAULT_POSES
    saved = _save_pose(arm)
    out = {}
    try:
        for name, spec in poses.items():
            _apply_pose(arm, spec)
            r = part_clip_report(parts, margin, allowed, quiet=True)
            if body is not None:
                pk = [poke_through(body, p) for p in parts]
                r['body_poke'] = sum(x['poke'] for x in pk)
            out[name] = r
            print(f'  pose {name}: {"OK" if r["ok"] else r["clipping"]}'
                  + (f"  body poke {r['body_poke']}" if body is not None else ''))
    finally:
        _restore_pose(arm, saved)
    return out


# ---------------------------------------------------------------------------------------------------------- macro shots
MACRO_VIEWS = {  # direction the camera looks FROM, relative to the region centre (world: -Y front, +Z up)
    'front': (0, -1, 0), 'back': (0, 1, 0), 'left': (-1, 0, 0), 'right': (1, 0, 0),
    'top': (0, 0, 1), 'bottom': (0, 0, -1), 'front_l': (-0.7, -0.7, 0.2), 'front_r': (0.7, -0.7, 0.2),
}
DEFAULT_MACRO_REGIONS = ('neck', 'clavicle', 'upperarm', 'forearm', 'hand', 'spine', 'pelvis', 'thigh', 'calf', 'foot')


def macro_shots(armature, objs, out_dir, poses=None, regions=None, views=None, res=768, size=0.25, engine=None):
    """Close-up renders of every region in every pose -> out_dir/<pose>/<bone>_<view>.png.
    Only `objs` render. size = ortho width (scene units) around the posed bone centre. Restores everything."""
    import os
    arm = _obj(armature)
    objs = [_obj(o) for o in objs]
    poses = poses or DEFAULT_POSES
    views = views or MACRO_VIEWS
    keys = regions or DEFAULT_MACRO_REGIONS
    bones = [b for b in arm.data.bones if any(k in b.name.lower().replace(' ', '') for k in keys)]
    scn = bpy.context.scene
    old = dict(cam=scn.camera, x=scn.render.resolution_x, y=scn.render.resolution_y, pct=scn.render.resolution_percentage,
               path=scn.render.filepath, engine=scn.render.engine,
               hide={o.name: o.hide_render for o in scn.objects})
    cam_data = bpy.data.cameras.new('M2A_MacroCam')
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new('M2A_MacroCam', cam_data)
    scn.collection.objects.link(cam)
    saved = _save_pose(arm)
    files = []
    try:
        if engine:
            try:
                scn.render.engine = engine
            except TypeError as e:
                print('engine not set:', e)
        for o in scn.objects:
            if o.type in ('MESH', 'CURVE') and o not in objs:
                o.hide_render = True
        scn.camera = cam
        scn.render.resolution_x = scn.render.resolution_y = res
        scn.render.resolution_percentage = 100
        cam_data.ortho_scale = size
        cam_data.clip_start, cam_data.clip_end = 0.001, size * 20
        for pname, spec in poses.items():
            _apply_pose(arm, spec)
            d = os.path.join(out_dir, pname)
            os.makedirs(d, exist_ok=True)
            for b in bones:
                pb = arm.pose.bones[b.name]
                c = arm.matrix_world @ ((pb.head + pb.tail) * 0.5)
                for vname, dirv in views.items():
                    dv = Vector(dirv).normalized()
                    cam.location = c + dv * (size * 5)
                    cam.rotation_euler = (-dv).to_track_quat('-Z', 'Y' if abs(dv.z) > 0.9 else 'Z').to_euler()
                    p = os.path.join(d, f"{b.name.replace(' ', '_')}_{vname}.png")
                    scn.render.filepath = p
                    bpy.ops.render.render(write_still=True)
                    files.append(p)
    finally:
        _restore_pose(arm, saved)
        for n, h in old['hide'].items():
            if n in scn.objects:
                scn.objects[n].hide_render = h
        scn.camera = old['cam']
        scn.render.resolution_x, scn.render.resolution_y = old['x'], old['y']
        scn.render.resolution_percentage = old['pct']
        scn.render.filepath = old['path']
        try:
            scn.render.engine = old['engine']
        except TypeError:
            pass
        bpy.data.objects.remove(cam)
        bpy.data.cameras.remove(cam_data)
    print(f'macro shots: {len(files)} images in {out_dir}')
    return files

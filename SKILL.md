---
name: m2-armor-forge
description: Designs new Metin2 armors (the below-the-neck body part) in Blender (MCP / bpy) from an original armored game model, the matching naked body, a Meshy sample and design references. Dresses the naked body with the new design while keeping the game's clothing structure, skeleton, bind pose, weights budget and body proportions; checks the neck seam, shoulder/chest/waist widths, poke-through and deformation in test poses; prepares the model and DDS textures for GR2 export. Built on reference-forge. Use for Metin2 armor, costume or body-part creation, retexturing or re-dressing a Metin2 character body.
---

# m2-armor-forge

A Metin2-specific version of **reference-forge**. Everything in reference-forge applies (working contract, scoring,
comparison toolkit, 360° part review, automatic compare-and-fix loop, progress collages, LookDev, records) unless this
file says otherwise. Read the installed `reference-forge` skill (`~/.claude/skills/reference-forge/SKILL.md`) for those
sections; its generic helper scripts live in its `scripts/` folder. If reference-forge is not installed, tell the user
and continue with this file and `scripts/m2a_checks.py` only.

## 0. Hard locks (never break, check every round)

1. **Original skeleton.** Bone names, hierarchy, bind pose (head, tail, roll), helper bone scales and the root bone /
   model name stay exactly as in the original armored model. Nothing is added, removed, renamed or moved.
2. **Head position.** The head part (face + hair) must sit exactly where it sits on the original armored model: the
   head / neck bones' world bind matrices, the neck border loop and the vertical distance from the feet to the neck
   border stay identical (tolerance 0.1 mm). The armor never pushes, lifts or rescales the head.
3. **No region drift.** Head, neck, chest, shoulders, waist and hips stay where the original armor puts them: the
   per-bone centre of our armor may not move more than 1 cm sideways / forwards / backwards from the original armor's
   (`region_shift_report(original_armor, ours)`). A chest pushed forward, a shoulder pushed up or a waist moved
   off-centre is a failure even when the skeleton is untouched.
4. **Body proportions** (§4).

`m2a_checks.lock_snapshot(armature, body)` records these values at the start (from the original); every round
`m2a_checks.lock_check(snapshot, armature, armor)` must return `LOCKS OK` and `region_shift_report` must say `OK`. Any difference is fixed before any other
work; the fix is always in the armor, never in the rig or the head.

## Language

Reply in the operating system's display language (detect with `(Get-UICulture).Name`, `defaults read -g
AppleLanguages` or `$LANG`; fall back to the user's language). An explicit request from the user overrides this.
Collage labels follow the same language. This file stays in English.

## Purpose

Produce a new armor for a Metin2 character that:

1. Looks like the requested design (Meshy sample + reference images / models).
2. Is built like the game's own armors: same part split, same layering logic, same neck join, comparable polygon
   and texture budget.
3. Sits on the **unchanged** game skeleton and bind pose, deforms with the game's animations and never changes the
   character's body proportions.

## 1. How Metin2 builds a character (what we must respect)

Facts gathered from Metin2 modding communities (Metin2Dev, Elitepvpers, Turkmmo). Verify each against the user's own
client and files; clients differ.

- **Two visual parts.** A player is drawn as a **head part** (above the neck: face + hair model) and a **body part**
  (everything below the neck: torso, arms, hands, legs, feet). Changing armor swaps only the body part. The head part
  is never edited by this skill.
- **Neck join.** The body part meets the head part at the neck in one of two ways:
  - *Seamless skin join*: the armor exposes skin at the neck; the neck border vertices, normals, UV skin tone and
    weights match the head part exactly, so the texture continues without a visible line.
  - *Covering join*: a collar / gorget / high neck piece rises over the join and hides it; it still must not leave a
    gap or let the head-part neck poke through in any animation.
  Read which one the original armor uses before designing; the user may pick the other one per design.
- **Files.** A model is a Granny 2 `.gr2` (32-bit, Granny 2.11.x runtime) plus `.dds` (or `.tga`) textures.
  Armors are registered through the race's `.msm` file (`ShapeData` group with a unique `ShapeIndex`,
  `ShapeDataCount` +1), `item_proto` (value3 = ShapeIndex) and `item_list.txt`. Registration is the user's job unless
  they ask; this skill delivers the model, textures and a short note of the lines to add.
- **Skeleton.** Player rigs use a Biped-style hierarchy (`Bip01 ...`) plus helper bones (some scaled, e.g. cloth /
  attachment helpers). The model is named after its root bone. Bone names, hierarchy, bind pose and helper scales must
  stay identical to the original; animations are shared files and will break otherwise.
- **Vertex layout.** Skinned meshes are written as `PWNT3432` (position, 4 bone weights + indices, normal, UV).
  So: **max 4 influences per vertex**, weights normalised, one UV channel. Rigid meshes (`PNT332`) have no weights.
- **Units / axes.** 3ds Max-origin data: centimetres, Z up. Through Noesis / FBX, wrong unit or up-axis settings are the
  most common cause of broken exports (`-fbxzup`, scale 100). Keep a copy of the original in its native scale and
  compare bounds after every round trip.
- **Textures.** Diffuse **alpha is the specular mask, not transparency.** Cut-outs (fur fringe, chain gaps, cloth
  tears) need the material's opacity map / alpha-test setup used by the original. Texture paths are written as
  `d:\ymir work\...`. Texture size follows the budget (§5b); keep the original's DDS compression type.
- **Tooling.** Either the Blender extension *M2 Granny Tools* (Blender 4.2+, Windows, imports/exports `.gr2`, `.msm`,
  `.mdatr`, keeps bind pose of scaled helpers), or 3ds Max (2018 is the most reported working version) with the Granny
  2.11.8 exporter, with Noesis for `.gr2` → FBX, or the user's own tool. Ask which one the user has; never download
  tools without approval.
- **OBJ mode.** Many users export the game models as OBJ + textures from their own tool. OBJ carries geometry, UVs and
  materials in bind pose but **no skeleton and no weights**. Then:
  - Ask once whether the tool can also export the skeleton (FBX / SMD / `.gr2`). If yes, use it for the rig checks.
  - If not, work in rig-free mode: the original armor OBJ is the position frame. Head position = its neck border;
    proportions and drift = `band_report(original_armor, ours)` (and against the naked body); head join =
    `strict_seam_report` + `neck_join_compare` with `poses={'bind': {}}`. Weights, pose tests and pose clipping are
    then done in the user's tool or after they supply a skeleton; say clearly which checks could not run.
  - Never move, scale or rotate the imported OBJs: compare bounds of the original before and after import.

## 2. Inputs (confirm every time)

The user hands over **only these three files**, plus the design references:

| # | File | Contents |
|---|---|---|
| 1 | Original armor `.fbx` | The game's armored body part with skeleton, weights and textures |
| 2 | Naked model `.fbx` | The naked body of the same race / gender, same skeleton |
| 3 | Head / neck part `.fbx` | Only the head + neck part (face, hair) that sits on top of the armor |
| + | References | Meshy sample armor, images, models when found (design only) |

**Everything else is this skill's job, not the user's**: importing, overlaying the three models in one space,
checking they share one skeleton, locking them as references, splitting the original armor into its pieces and
grouping them (collar, pauldrons, bracers, gloves, torso, belt / waist, thighs, knee / shin, boots), finding the neck
join type, taking the lock snapshot, preparing the Meshy sample and the reference boards. Never ask the user to
separate, align or export parts.

**Every session and every time new files arrive**, run

```python
inp = m2a_checks.prepare_inputs(armor_fbx, naked_fbx, head_fbx)
```

and post its input card before doing anything else:

| Slot | File | Meshes | Bones | Tris | Status |
|---|---|---|---|---|---|

Status is `OK`, `MISSING` or `PROBLEM: <reason>`. Then state in one or two lines:

- Skeleton armor vs naked and armor vs head: `identical` or the differences.
- Neck join of the original (skin join or covering join).
- The original armor's piece groups (region: piece count).
- The lock snapshot: neck border height and radius.
- Units: compare the character height with a plausible one and state the scale used. Never move, scale or rotate
  the imported references.

`prepare_inputs` puts the files in `REF_OrigArmor`, `REF_Naked`, `REF_Head` and the grouped pieces in
`REF_OrigArmor_Parts_<region>`; all of them are locked (not selectable, transforms locked). Our work goes in
`ARM_<piece>` objects in a `<Armor>_vN` collection, never into a `REF_` collection.

Any of the three files missing or broken (no skeleton, no mesh): stop and ask for exactly that file; the work cannot
start without all three. Missing references: say so and continue only with the user's agreement. If the user can only
give OBJ, use OBJ mode (§1) and say which checks cannot run.

## 3. Reference roles

| Reference | Drives | Never drives |
|---|---|---|
| Original armored model | Part split, layer order, neck join type, polygon / texture budget, UV density, weight style, which parts are rigid vs skinned, how plates overlap at joints | The new design's look |
| Naked body | Skeleton, bind pose, body surface, proportions, neck border, base weights | Design |
| Meshy sample | Overall design idea, silhouette motifs, colour scheme | Topology, scale, proportions, weights (Meshy meshes are triangle soup; never ship or skin them) |
| Design images / models | Shapes, ornaments, materials, colours, detail | Body proportions |

Compare against all references at once (reference-forge rule): every collage has one column per reference, then
Ours, then Difference.

## 4. Proportion guard (never make the character thinner, wider or fatter)

The naked body defines the character. The armor may only add the *thickness of its own layers* on top of it.

1. Slice the naked body and the armor at fixed heights taken from bones: neck base, clavicle / shoulder, chest,
   waist, hips, mid thigh, knee, mid calf, ankle; and along arms: upper arm, elbow, forearm, wrist.
   Run `m2a_checks.proportion_report(body, armor, armature)`.
2. For every slice record the body width and depth and the armor offset (median, max) over the body surface.
3. Limits (defaults; the original armor's measured offsets override them when they are larger, and the user can set
   others):
   - Cloth / leather layers: offset 0.3 to 1.5 cm.
   - Plate / metal: 0.8 to 3 cm.
   - Shoulder width (outer pauldron edge to edge) at most the original armor's width × 1.10, unless the design
     calls for big pauldrons and the user agrees (design decision: ask).
   - Waist and chest offsets never exceed the original armor's offsets × 1.25: this is what stops a "fat" look.
   - No slice may be narrower than the naked body (negative offset = poke-through).
4. Compare front and side silhouettes of naked body, original armor and ours with silhouette IoU (reference-forge
   `rf_silhouette.py`) and show them in the collage.
5. Never edit the naked body or the skeleton to make the armor fit. Fix the armor.

## 5. Build like the game's armors

Study the original armored model first (solo 360° review of each of its parts, see reference-forge §6). Record:

- Which body areas are replaced by armor and which keep skin (hands, feet, neck).
- Layer order (undershirt → padding → mail → plates → belts / straps → ornaments) and where layers overlap.
- Where geometry is split and where it is one skin.
- Polygon count per area and texture texel density (for information; the budget is set in §5b).

### 5b. Budget (game-ready, not 2006-limited)

The armor may have more polygons and larger textures than the original, but it must stay a game-ready asset.

1. **Calibrate from a modern Metin2 armor.** Recent Metin2 armors and costumes are much busier than the 2006 ones.
   Do not ask for extra files; if the user offers a recent armor / costume (OBJ + textures is enough), run
   `budget_report([ours...], calibrate=[recent_armor])`: its triangle count + 15%, its largest texture and its
   material count become the limits.
2. **Defaults when no calibration model is given** (estimates, not verified Metin2 data): body armor ≤ 12,000
   triangles, one 1024² texture (2048² only when the design needs it), ≤ 3 materials.
3. **Meshy is decimated away, not reduced.** Meshy meshes are 30k-300k+ triangle soup with baked lighting. Use them
   only as a shape guide (blueprints, slices with `rf_trace`, silhouettes); build clean low-poly geometry on the
   body base, then bake fine Meshy / high-poly detail into the diffuse texture if useful.
4. Spend triangles where they change the silhouette (pauldrons, collar, belt, skirt edges, boot cuffs) and on joint
   loops; flat surfaces stay light.
5. `budget_report` must say `OK` before delivery.

Production order:

1. **Base layer from the body.** Duplicate the naked body below the neck border, delete hidden skin, shrink-wrap /
   offset it outward by the layer thickness. This keeps body proportions and topology flow, and its weights come
   straight from the body.
2. **Neck border first.** Lock the neck border loop to the naked body's border (positions, normals, weights, UV skin
   colour) before anything else: run `m2a_checks.neck_seam_report()`. For a covering join, model the collar now and
   test it against the head part in the extreme head poses.
3. **Main shapes from the design** (chest plate, tassets, pauldrons, skirt, boots, gloves), each in its own object
   while modelling, joined at the end like the original.
4. **Joint-friendly topology.** Keep edge loops perpendicular to the bone at every joint (shoulder, elbow, wrist,
   hip, knee, ankle) with at least 3 loops across the bend, like the naked body. Rigid plates do not cross a bend:
   split them or let them overlap.
5. **Detail** (rivets, trims, straps, engraving) as geometry only where it changes the silhouette; the rest goes into
   the texture (normal maps are not used by the classic client: bake detail into the diffuse colour and specular
   alpha).

## 6. Weights and rig

1. Never change bone names, hierarchy, bind pose or helper scales. `m2a_checks.rig_report(original_arm, our_arm)` must
   say `identical`.
2. Transfer weights from the naked body (skin-tight layers) or from the original armor (loose parts like skirts, capes,
   tassets, pauldrons when it has similar ones): `m2a_checks.transfer_weights(src, dst)` uses Data Transfer with
   *Nearest Face Interpolated*, vertex groups by name, then limits to 4 influences and normalises.
3. Rigid plates: weight each plate 100% to its nearest bone; smooth only where it visibly breaks.
4. Pauldrons with several plates: lower plates follow the upper arm; the top plate keeps a partial weight on the
   clavicle / upper body so the shoulder top stays covered with the arm down.
5. Skirts / tassets: copy the original armor's weight style (often thigh bones blended with pelvis, or the original's
   cloth helper bones). Check leg-forward and run poses.
6. `m2a_checks.weight_report(obj, armature)`: no unweighted vertices, ≤ 4 influences, sums = 1, no group without a
   bone.

## 7. Pose test (mandatory after every weight change)

`m2a_checks.pose_test(armature, body, armor)` puts the rig in a fixed pose set and measures poke-through
(body vertices outside the armor where the armor should cover them) and stretched faces:

`bind`, `arms_up`, `arms_down`, `arms_forward`, `elbow_bent`, `torso_twist`, `leg_forward`, `leg_back`, `squat`,
`head_turn` (covering joins).

Use the game's own animations (wait, run, attack, skill poses) as well when the user's tools can import them.
Acceptance: poke-through ≤ 0.5% of covered body vertices in any pose and none at the neck; no face stretched beyond
2.5× its bind area. Show a pose collage: rows = poses, columns = Original armor, Ours.

## 7b. Part separation and clipping (check this specifically)

Armor pieces (upper body, belt, pauldrons, gloves, bracers, tassets / skirt, knee pads, boots, cape, ornaments) are
checked **as separate parts** even when they ship as one mesh:

1. Build or keep every piece as its own object while working (`ARM_<piece>`). For a joined or imported armor (also the
   original and the Meshy sample), split a work copy with `split_parts(obj, 'LOOSE')` or `'MATERIAL'` and name the
   pieces; the source object stays untouched.
2. Run `part_clip_report(parts)` in bind pose and `pose_clip_test(armature, parts, body)` in every pose of the pose
   set. Every pair must report 0 intersecting triangles and 0 sunk vertices. Pieces that are meant to tuck under each
   other (a strap riveted into a plate) go in `allowed`, and the reason is written in the report.
3. Fix by moving / reshaping the outer piece, adding a layer gap (≥ 0.5 mm cloth, ≥ 1 mm metal), changing layer order
   or giving overlapping pieces the same weights in the overlap zone. Never fix by deleting faces that show from
   any angle.
4. Re-run until clean in every pose, then join the pieces like the original armor (same object / material split).

## 7c. Macro loop (close-ups in every pose)

The automatic compare-and-fix loop of reference-forge §7, run on close-ups:

1. `macro_shots(armature, parts + [body], out_dir)` renders every region (neck, clavicle, upper arm, forearm, hand,
   spine / chest, pelvis / belt, thigh, calf, foot) from 8 views (front, back, left, right, top, bottom, two
   three-quarter) in every pose of the pose set.
2. Look at every image: clipping, poke-through, gaps, stretched or collapsed faces, broken plate overlaps, seam lines,
   texture stretching, missing back / inside faces.
3. Fix every defect without asking (only design decisions go to the user), re-run the measuring reports
   (locks, region shift, part clipping, poke-through, stretch), re-shoot only the changed regions plus their
   neighbours.
4. Repeat until a full pass finds nothing. Post a macro collage per round: rows = region + view, columns =
   poses (bind, two worst poses), first block Original armor, second block Ours. Keep labels short.
5. Stall rule (reference-forge §8): three rounds without improvement in a region → change approach (split the
   piece, re-topologise the joint, re-transfer weights from another source).

## 7d. Head-join verification (100% rule)

Runs after the armor design is finished, and again after every later change near the neck. The design may only be
*similar* to the references (normal scoring, §8), but the **fit of the head on the armor is not scored: it must be
perfect** (target 100%, nothing like the 90% rule). Compare the original armor + head and our armor + head side by
side with every method below, in every view and every pose:

| Method | Tool | Pass condition |
|---|---|---|
| Skeleton and head position | `lock_check` | `LOCKS OK` |
| Border geometry (skin join) | `strict_seam_report(head, ours)` | same border vertex count, gap ≤ 0.00001 units, normal angle ≤ 1°, weight difference ≤ 0.001 |
| Seam colour (skin join) | `seam_color_report(head, ours)` | ΔE ≤ 1 across the seam (re-run after every texture change) |
| Leak test | `neck_join_compare` | 0 magenta pixels: an emissive core inside the neck must never show through a gap, hole or flipped face |
| Head coverage | `neck_join_compare` | visible-head mask IoU vs original ≥ 0.99999 (skin join); covering join: no head-neck vertex visible outside the collar |
| Side-by-side images | `neck_join_compare` | `<pose>/<view>.png` = original \| ours \| difference, 26 views × all poses incl. `head_turn` |
| Close-ups | `macro_shots(..., regions=('neck', 'clavicle', 'head'))` | visual: no seam line, shading break, texture jump, z-fighting |
| Game check | user's client / Granny viewer, if available | same as above in wait, run, attack animations |

`head_join_gate(armature, head, orig_armor, ours, out_dir, snapshot, seam=...)` runs the measurable ones together
and returns `PASS` only when every check passes.

Loop: run → read every failing image and number → fix in the armor (never the head or the rig) → re-run everything
→ repeat. There is no "good enough" exit: the stall rule changes the approach (rebuild the neck ring from the head's
border, copy the original's neck topology and weights, re-bake the skin colour), it never accepts a failure. If the
original itself fails a check (e.g. it leaks in one view), ours must still pass; report the original's result too.
Post a join collage each round: rows = worst views / poses, columns = Original, Ours, Difference.

## 8. Scoring (adapted)

Same 90/100 working score as reference-forge, with Metin2 weights:

| Area | Weight | Main checks |
|---|---|---|
| Fit and proportion | 30 | Proportion report, silhouette IoU vs naked body and original, shoulder / waist limits |
| Design match | 25 | Meshy sample + references, motifs, layers, silhouette |
| Rig and deformation | 20 | Rig identical, weight report clean, pose test, part clipping in all poses, macro loop clean |
| Game structure | 15 | Neck seam, part split like original, budget, UV density |
| Texture and material | 10 | Palette, specular alpha, texel density, DDS settings |

Fit and proportion, locks (skeleton, head, region drift), part clipping and the head-join gate (§7d, 100%) are **gates**: any failure there blocks delivery whatever the total.

## 9. Textures

- One UV channel, no overlapping islands except mirrored ones the original also mirrors.
- Texel density equal to the original armor's (measure: texture pixels per cm on the chest).
- Paint / bake: diffuse colour with baked AO and light detail like the original's hand-painted style; specular mask in
  alpha (metal high, cloth / skin low). Bake procedural LookDev with reference-forge `rf_lookdev.bake_pbr`, then
  combine BaseColor + an AO pass into diffuse and Metallic / Roughness into the alpha mask.
- Skin areas near the neck use the head part's skin colour sampled from its texture (median in linear space).
- Export `.dds` within the budget size, with the original's compression type (check its header: DXT1 without alpha, DXT5 / DXT3 with
  alpha). `m2a_checks.dds_info(path)` reads the header.

## 10. Delivery

1. Run all reports: locks (skeleton + head position), region shift, inputs, rig, weights, neck seam, proportion,
   pose test, part clipping in all poses, last macro loop pass, head-join gate `PASS`. Post the summary table.
2. Final collage: rows = front, back, side, 3/4, two test poses; columns = Original armor, Meshy sample, references,
   Ours, Difference.
3. Export through the user's tool (M2 Granny Tools or FBX → 3ds Max → Granny exporter). Re-import the exported file
   and compare bounds, bone list and vertex count with the scene; scale or axis errors show up here.
4. Hand over: `.gr2`, `.dds`, a `.blend` with the clean source, the report and the `.msm` / `item_proto` /
   `item_list.txt` lines to add (as text, not applied).

## 11. Avoid

- Editing the head part, the naked body or the skeleton.
- Moving, lifting or rescaling the head, or changing the neck border height.
- Shipping or skinning the Meshy mesh.
- Scaling the armor to "fit": fix the shape instead.
- Using diffuse alpha as transparency.
- More than 4 influences per vertex, or bones not in the original rig.
- Rigid plates crossing a joint.
- Judging fit only in bind pose, or only from full-body views (macro close-ups are mandatory).
- Checking armor as one blob: pieces are checked against each other separately.
- Assuming community facts are true for this client without checking the user's files.

## Helper scripts

`scripts/m2a_checks.py` (load as a Blender text block and `exec`, like reference-forge's helpers):

| Function | What it does |
|---|---|
| `prepare_inputs(armor_fbx, naked_fbx, head_fbx)` | Imports the 3 FBX, checks one skeleton, locks them, splits + groups the original armor, takes the lock snapshot, prints the input card |
| `group_parts(obj, prefix, col_name)` / `lock_objects(objs)` | Piece grouping by dominant bone / reference lock |
| `inputs_report(armored, naked, armature_a=None, armature_n=None)` | Input card for already-loaded objects |
| `lock_snapshot(armature, body, head_bones=None)` | Records skeleton + head position locks from the original |
| `lock_check(snapshot, armature, armor=None, tol=1e-4)` | Verifies skeleton and head position are unchanged |
| `rig_report(arm_a, arm_b, tol=1e-4)` | Bone names, parents, bind-pose heads / tails / rolls compared |
| `weight_report(obj, armature, max_inf=4)` | Unweighted, over-influenced, unnormalised vertices, unknown groups |
| `transfer_weights(src, dst, max_inf=4)` | Nearest-face-interpolated weight transfer, limit and normalise |
| `neck_seam_report(body, armor, tol=0.0005)` | Matches the armor's open border near the neck with the body's (distance, normal angle, weight difference) |
| `proportion_report(body, armor, armature, bones=None)` | Slice widths / depths and armor offsets per bone height |
| `poke_through(body, armor, covered=None, eps=0.0)` | Body vertices outside the armor surface |
| `pose_test(armature, body, armor, poses=None)` | Runs the pose set, returns poke-through and stretch per pose |
| `region_shift_report(ref, ours, armature=None, tol=0.01)` | Per-bone centre drift (head, chest, shoulders, hips) against the original armor |
| `split_parts(obj, by='LOOSE')` | Work copy split into pieces (loose parts or materials) |
| `part_clip_report(parts, margin=0.0005, allowed=())` | Pairwise intersections and sunk vertices between pieces |
| `pose_clip_test(armature, parts, body=None, poses=None)` | Part clipping (+ body poke-through) in every pose |
| `macro_shots(armature, objs, out_dir, poses=None, regions=None, views=None)` | Close-up renders of every region, 8 views, every pose |
| `strict_seam_report(head, armor)` | Neck border vs the head part with the strict limits |
| `seam_color_report(head, armor, max_de=1.0)` | Texture colour difference across the seam (ΔE) |
| `neck_join_compare(armature, head, orig_armor, our_armor, out_dir, poses=None, views=None)` | Side-by-side ID renders, leak test, head mask IoU, 26 views × poses |
| `head_join_gate(armature, head, orig_armor, our_armor, out_dir, snapshot, seam='skin')` | All head-join checks; PASS only if all pass |
| `dds_info(path)` | Width, height, mip count, FourCC (DXT1 / DXT3 / DXT5) |
| `band_report(ref, ours, bands=24, tol=0.01)` | Rig-free (OBJ) proportion and drift check by height bands |
| `budget_report(objs, max_tris, max_tex, max_mats, calibrate=())` | Triangles, texture size, materials; limits from a recent armor |

All functions return plain dicts / lists and print a short table. Units are scene units; set the scene unit scale to
match the imported data before reading centimetres.

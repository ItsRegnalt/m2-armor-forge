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
  `d:\ymir work\...`. Keep the original's texture size and DDS compression unless the user says otherwise.
- **Tooling.** Either the Blender extension *M2 Granny Tools* (Blender 4.2+, Windows, imports/exports `.gr2`, `.msm`,
  `.mdatr`, keeps bind pose of scaled helpers), or 3ds Max (2018 is the most reported working version) with the Granny
  2.11.8 exporter, with Noesis for `.gr2` → FBX. Ask which one the user has; never download tools without approval.

## 2. Inputs (confirm every time)

The user provides, in this order:

1. **Original armored model** from the game (`.gr2`, FBX or OBJ + textures).
2. **Naked body model** of the same race / gender (same skeleton).
3. **Meshy sample armor** (generated mesh / render): design reference only.
4. **Design references**: images, and models when found.

**Every session and every time new files arrive, confirm receipt with an input card** before doing anything else.
Run `m2a_checks.inputs_report()` and post a short table:

| Slot | File | Loaded as | Bones | Verts / tris | Materials / textures | Status |
|---|---|---|---|---|---|---|

Status is `OK`, `MISSING` or `PROBLEM: <reason>`. Also state:

- The skeletons of 1 and 2 match (same bone names, hierarchy, bind pose within 0.1 mm) or list the differences.
- Which neck join the original uses (skin join or covering join).
- Which head part (if any) was supplied for seam checks.
- The lock snapshot was taken (`lock_snapshot`): head / neck bone positions and neck border height in cm.

Missing slot 1 or 2: stop and ask for it; the work cannot start without both. Missing 3 or 4: say so and continue
only with the user's agreement.

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
- Polygon count per area and texture texel density. The new armor stays within ±20% of the original's total
  triangle count unless the user sets a budget.

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

## 8. Scoring (adapted)

Same 90/100 working score as reference-forge, with Metin2 weights:

| Area | Weight | Main checks |
|---|---|---|
| Fit and proportion | 30 | Proportion report, silhouette IoU vs naked body and original, shoulder / waist limits |
| Design match | 25 | Meshy sample + references, motifs, layers, silhouette |
| Rig and deformation | 20 | Rig identical, weight report clean, pose test, part clipping in all poses, macro loop clean |
| Game structure | 15 | Neck seam, part split like original, budget, UV density |
| Texture and material | 10 | Palette, specular alpha, texel density, DDS settings |

Fit and proportion, locks (skeleton, head, region drift), part clipping and neck seam are **gates**: any failure there blocks delivery whatever the total.

## 9. Textures

- One UV channel, no overlapping islands except mirrored ones the original also mirrors.
- Texel density equal to the original armor's (measure: texture pixels per cm on the chest).
- Paint / bake: diffuse colour with baked AO and light detail like the original's hand-painted style; specular mask in
  alpha (metal high, cloth / skin low). Bake procedural LookDev with reference-forge `rf_lookdev.bake_pbr`, then
  combine BaseColor + an AO pass into diffuse and Metallic / Roughness into the alpha mask.
- Skin areas near the neck use the head part's skin colour sampled from its texture (median in linear space).
- Export `.dds` with the original's size and compression (check its header: DXT1 without alpha, DXT5 / DXT3 with
  alpha). `m2a_checks.dds_info(path)` reads the header.

## 10. Delivery

1. Run all reports: locks (skeleton + head position), region shift, inputs, rig, weights, neck seam, proportion,
   pose test, part clipping in all poses, last macro loop pass. Post the summary table.
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
| `inputs_report(armored, naked, armature_a=None, armature_n=None)` | Input card data: counts, materials, textures, skeleton match |
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
| `dds_info(path)` | Width, height, mip count, FourCC (DXT1 / DXT3 / DXT5) |

All functions return plain dicts / lists and print a short table. Units are scene units; set the scene unit scale to
match the imported data before reading centimetres.

# m2-armor-forge

**A Claude Code skill for designing new Metin2 armors in Blender.**

Give Claude an original armored character from the game, the matching naked body, a Meshy sample and a few design
references. m2-armor-forge dresses the naked body with the new design the way the game's own armors are built:
below-the-neck body part only, unchanged skeleton and head position, no change to body proportions, clean neck join,
no clipping between armor pieces in any pose, and textures ready for the client.

It is the Metin2 version of [reference-forge](https://github.com/ItsRegnalt/reference-forge) and uses its comparison
toolkit, scoring and compare-and-fix loop.

---

## What it does

- **Input card every time.** Confirms it received the original armored model and the naked body (bones, vertex /
  triangle counts, materials, textures, skeleton match) before any work; stops if one is missing.
- **Hard locks.** Original skeleton (names, hierarchy, bind pose, helper scales), head position and neck border, and
  no drift of head, chest, shoulders or hips. Checked every round.
- **Proportion guard.** Per-bone width / depth and armor offset over the body, compared with the original armor, so
  shoulders do not get too narrow or wide and the character never looks fat.
- **Built like the game.** Body part only (head part untouched), neck join as a seamless skin join or a covering
  collar, layers and budget taken from the original armor.
- **Rig and weights.** Weight transfer from the naked body or original armor, max 4 influences (Granny `PWNT3432`),
  normalised, no bones outside the original rig.
- **Part clipping.** Belt, pauldrons, gloves, boots, knee pads and other pieces are checked against each other
  separately, in bind pose and in every test pose.
- **Macro loop.** Close-up renders of every region from 8 views in every pose; defects are fixed and re-shot until a
  full pass is clean. Progress collages show the original armor, references and ours side by side.
- **Game-ready budget.** Polygon / texture limits calibrated from a recent Metin2 armor; Meshy meshes are rebuilt,
  never shipped.
- **Head join at 100%.** Original and new armor are compared with the head side by side from 26 views in every pose
  (leak test, head mask, seam geometry and colour); the loop runs until every check passes.
- **Textures for the client.** DDS format of the original; diffuse alpha as the specular mask.
- **Speaks your language.** Replies follow your operating system's display language.

## Requirements

- [Claude Code](https://claude.com/claude-code).
- Blender 4.2 or newer (tested on 5.2) with a Blender MCP server, e.g. [blender-mcp](https://github.com/ahujasid/blender-mcp).
- [reference-forge](https://github.com/ItsRegnalt/reference-forge) installed as a skill (comparison scripts, collages).
- A way to get the game models in and out: your own exporter (OBJ + textures works; a skeleton export enables the rig
  checks), the *M2 Granny Tools* Blender extension, or 3ds Max + Granny 2.11 exporter (+ Noesis for `.gr2` → FBX).
  The skill does not ship or download these.
- Python 3 with Pillow for collages.

## Installation

```bash
git clone https://github.com/ItsRegnalt/reference-forge.git ~/.claude/skills/reference-forge
git clone https://github.com/ItsRegnalt/m2-armor-forge.git ~/.claude/skills/m2-armor-forge
```

Restart Claude Code. Update later with `git pull` in each folder.

## Usage

```text
/m2-armor-forge Here are the original warrior armor (warrior_armor_01.gr2) and the naked warrior body.
Next I'll send a Meshy sample and references for a dark-knight armor.
```

What you will see:

1. An input card confirming both base models (or asking for the missing one).
2. A lock snapshot: skeleton, head / neck position.
3. Region-by-region work with collages, proportion tables, clipping and pose reports.
4. Macro loop rounds until clean, then export notes and the `.msm` / `item_proto` / `item_list.txt` lines to add.

## Helper script

`scripts/m2a_checks.py` (runs inside Blender): input card, lock snapshot / check, rig and weight reports, weight
transfer, neck seam, proportion and region drift reports, poke-through, pose test, part splitting and clipping (also
per pose), macro close-up renders, DDS header reader. See `SKILL.md` for the full table.

## Notes and limits

- Metin2 facts in the skill come from community sources (Metin2Dev, Elitepvpers, Turkmmo); clients differ, so the skill
  checks them against your own files.
- Use only game files and references you are allowed to use. Meshy samples are design references; their meshes are
  never shipped.
- Pose test axes depend on the rig; the skill prints which bones each pose moved and adjusts the pose set if needed.

## License

[MIT](LICENSE) © 2026 ItsRegnalt

---

## Türkçe özet

**m2-armor-forge**, Metin2 için yeni zırh tasarlatan bir Claude Code skill'idir. Oyunun orijinal zırhlı modelini ve
kıyafetsiz modeli her seferinde teyit eder, ardından Meshy örneği ve referanslarla kıyafetsiz gövdeyi giydirir.
Orijinal iskeleti, kafa konumunu ve boyun dikişini kilitler; göğüs / omuz / kalça kaymasına, omuz genişliği ve
şişmanlığa karşı ölçüm yapar; kemer, omuzluk, eldiven, bot, dizlik gibi parçaların birbirine clip etmesini her pozda
ayrı ayrı kontrol eder ve her bölgenin farklı pozlarda makro fotoğrafını çekip temiz çıkana kadar düzeltir.

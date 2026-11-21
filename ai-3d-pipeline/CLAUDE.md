# AI 3D Pipeline — Claude / Blender rules

Run Blender as: `blender -b file.blend --python script.py`
Default blender binary: `blender` (override with `BLENDER_BIN` or `config/defaults.yaml`).

Keep every step as a `.py` file so you can rerun after any change.
Work in project-relative paths under `examples/` and write outputs next to the asset.

## Free path (this repo default)

| Asset | Route | Cost |
|-------|-------|------|
| Props, buildings, vehicles, furniture | Python + bmesh in Blender | Free |
| Characters / creatures | Demo / import GLB (this AMD PC) · TRELLIS if NVIDIA | Free |
| Cleanup, retopo assist, UV, LOD, rig, clips, export | Blender + PyMeshLab + xatlas + meshoptimizer + glTF-Transform | Free |

**Studio app (preferred):** `.\scripts\start_studio.ps1` → http://127.0.0.1:8787/
This Lenovo has AMD iGPU only — TRELLIS/CUDA won’t run here. Use demo mesh or drop a GLB.
On an NVIDIA box (~16 GB+): `.\scripts\install_trellis.ps1` → `.\scripts\serve_trellis.ps1`.

## Props rules

- Units: metres. Origin at the base centre. Forward is -Y.
- Budget: 2,000 triangles for the whole prop (override per asset).
- Max 3 materials, flat colours, no image textures.
- Bevel hard edges 2 mm, 1 segment. Apply all modifiers before export.
- Renders: 768 px, orthographic, same view as the reference, side by side with it.
- Max 3 fix rounds per part, then stop and show me.
- One part per prompt / session for outlines and joints.

## Character rules

- Sheets: orthographic front / right / back, A-pose, empty hands, flat light.
- Put each view in the correct Tripo/local slot. Left slot empty if no left view.
- Clean before any bone: facing engine forward (-Y), feet on Z=0, apply transforms.
- Merge vertices by distance before weighting.
- Tag parts; never smooth weights across tagged parts.
- Max 4 bones per vertex, then normalize.
- Mixamo bone names for humanoids (Unity Humanoid maps them).
- Clips always start from the stored rest pose. Last frame of loops matches first.
- Export FBX: Apply Transform **off**, Add Leaf Bones **off**, scale 1.

## Words

Mesh, GLB/FBX, orthographic, UV/texture, normal map, decimate, armature, weights,
rest pose / A-pose, IK.

## Pipeline entry

```bash
cd ai-3d-pipeline
python3 -m pipeline.cli --help
python3 -m pipeline.cli prop crate          # free prop demo
python3 -m pipeline.cli character demo      # cleanup→rig→clips on a GLB
python3 -m pipeline.cli buildings           # procedural buildings
```

# Free AI 3D Modeling Pipeline

End-to-end **free** path from the “Opus + Blender + Tripo” workflow:

**measure / code props → (optional) generate characters → clean → split → joints → weight rules → pose test → clips → FBX/GLB**

Uses Blender headless Python for everything that should stay $0/model. Character *generation* is local MIT models (TripoSR / TRELLIS) or a drop-in GLB — **not Hunyuan3D** (licence excludes EU/UK/KR). Tripo API is optional paid.

## Quick start

```bash
cd ai-3d-pipeline
pip install -r requirements.txt
npm install
python3 -m pipeline.cli doctor

# Free prop (crate) — steps 03–05
python3 -m pipeline.cli prop crate

# Procedural buildings
python3 -m pipeline.cli buildings --count 10

# Free character path (placeholder mesh → rig → idle/walk → export)
python3 -m pipeline.cli character demo --demo
```

## Layout

| Path | Role |
|------|------|
| `CLAUDE.md` | Rules Claude/Cursor should follow (Blender cmd, budgets, weight rules) |
| `pipeline/cli.py` | Orchestrator |
| `blender/props/` | Steps 04–05 + buildings |
| `blender/characters/` | Steps 08–15 |
| `scripts/characters/` | Step 07 generators (local free / Tripo optional) |
| `scripts/tools/` | PyMeshLab, xatlas, glTF-Transform |
| `prompts/` | Copy-paste prompts from the article |
| `examples/` | Working assets (`crate`, `demo`) |
| `third_party/SOURCES.md` | The 14 GitHub projects + EU-safe generators |

## Cost map

| Stage | Tool | Cost |
|-------|------|------|
| Props / buildings | Blender bmesh / generator scripts | Free |
| Character mesh | TripoSR / TRELLIS / import GLB | Free on your GPU |
| Character mesh (optional) | Tripo API | ~$0.20–$0.60 |
| Cleanup, parts, joints, weights, clips, export | Blender scripts here | Free |
| LOD / pack | meshoptimizer via glTF-Transform | Free |
| UVs / remesh (optional) | xatlas, PyMeshLab, AutoRemesher, RetopoFlow | Free |
| Paint (optional desktop) | Material Maker, ArmorPaint | Free |

## Character pipeline (09–12 stretch fix)

Generator meshes are one fused shell. This repo:

1. Tags parts by position (`split_parts.py`)
2. Writes Mixamo `joints.json`
3. Binds auto-weights then **zeros arm influences on torso/coat**, locks hands/head, sends coat skirt to cloth bones
4. Pose-tests stretch ratios and dumps the 10 worst vertices

## Engine export (15)

- FBX: Apply Transform **off**, leaf bones **off**
- Unity: Humanoid biped, enable Loop Time
- Roblox: Custom rig, Zero Influence Bones on, ≤4 influences
- 10 cm `PROBE_10cm` cube included for scale checks

## View FBX / GLB in Cursor

Workspace recommends these extensions (`.vscode/extensions.json`):

- **3D Mesh Viewer** — `AssetToolLabs.mesh-viewer-vscode` (FBX + GLB, best all-rounder)
- **FBX Viewer** — `FiLL.fbx-viewer`
- **Simple Model Viewer** — `hwanhuh.simple-model-viewer`
- **3d Preview** — `mohitkumartoshniwal.3d-preview`

In Cursor: Extensions → search those IDs → Install. Then open any `.fbx` / `.glb` (or right-click → Open With…). Reload the window once if the custom editor doesn’t attach.

Fallback (no extension):

```bash
./scripts/view.sh examples/props/crate/exports/crate.fbx
# → http://127.0.0.1:8765/viewer/?src=...
```

## Claude / Cursor

Put `CLAUDE.md` in context. Drive Blender with the scripts above, or wire [blender-mcp](https://github.com/ahujasid/blender-mcp) + [blender-skills](https://github.com/EL4CTEO/blender-skills).

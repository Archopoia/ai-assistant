# Upstream free / open tools wired into this pipeline

## Claude × Blender
1. [blender-mcp](https://github.com/ahujasid/blender-mcp) — drive Blender from Claude (optional MCP)
2. [blender-skills](https://github.com/EL4CTEO/blender-skills) — modeling / UV / rig / LOD skills

## Modeling
3. [build123d](https://github.com/gumyr/build123d) — CAD props in Python
4. [building_tools](https://github.com/ranjian0/building_tools) — Blender buildings add-on
5. [tripo-3d-for-blender](https://github.com/Tripo-Developer/tripo-3d-for-blender) — optional paid add-on
6. [tripo-python-sdk](https://github.com/Tripo-Developer/tripo-python-sdk) — optional paid API

## Retopo & cleanup
7. [autoremesher](https://github.com/huxingyi/autoremesher) — auto quads (manual / add-on)
8. [retopoflow](https://github.com/CGCookie/retopoflow) — hand retopo in Blender
9. [PyMeshLab](https://github.com/cnr-isti-vclab/PyMeshLab) — scriptable cleanup

## UVs & textures
10. [xatlas](https://github.com/jpcy/xatlas) — auto UV unwrap / pack
11. [Material Maker](https://github.com/RodZill4/material-maker) — procedural PBR
12. [ArmorPaint](https://github.com/armory3d/armorpaint) — open PBR painting

## LODs & export
13. [meshoptimizer](https://github.com/zeux/meshoptimizer) — decimate / compress
14. [glTF-Transform](https://github.com/donmccurdy/glTF-Transform) — final GLB optimizer

## Free character generators (local GPU, $0/model)
- **[TRELLIS](https://github.com/microsoft/TRELLIS)** — **default**, MIT, ~16 GB VRAM. Windows: `.\scripts\install_trellis.ps1` → `.\scripts\serve_trellis.ps1` (see [TRELLIS#3](https://github.com/microsoft/TRELLIS/issues/3))
- [TRELLIS.2](https://github.com/microsoft/TRELLIS.2) — higher quality, more VRAM
- [TripoSR](https://github.com/VAST-AI-Research/TripoSR) — MIT, ~6 GB VRAM
- [Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) — Community Licence (fine outside EU/UK/KR)

Point `07_generate_local.py` at a local server via `TRELLIS_URL` / `TRIPOSR_URL` / `HUNYUAN_URL`, or drop a GLB with `--backend import`.

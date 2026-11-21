# Setup (once)

1. Install Blender (free) and put it on PATH, or set `BLENDER_BIN`.
2. From `ai-3d-pipeline/`:
   ```bash
   pip install -r requirements.txt
   npm install
   python3 -m pipeline.cli doctor
   ```
3. Keep every step as a `.py` file (already done in `blender/`).
4. Optional MCP: [blender-mcp](https://github.com/ahujasid/blender-mcp) + [blender-skills](https://github.com/EL4CTEO/blender-skills).

## Free path reminder

- Props / buildings / vehicles → Python in Blender (this repo).
- Characters → import GLB, or local TripoSR / TRELLIS / Hunyuan3D ($0 on your GPU).
- Rig / clips / export → Blender scripts here (free).

# Step 07 — generate (free)

Split sheet into `view_front.png`, `view_right.png`, `view_back.png`.

## Free (recommended here) — TRELLIS on Windows

```powershell
# Anaconda PowerShell Prompt, from ai-3d-pipeline\
.\scripts\install_trellis.ps1
.\scripts\serve_trellis.ps1   # http://127.0.0.1:8090

python scripts\characters\07_generate_local.py `
  --backend trellis `
  --front examples\characters\demo\views\view_front.png `
  --right examples\characters\demo\views\view_right.png `
  --back examples\characters\demo\views\view_back.png `
  -o examples\characters\demo\exports\raw.glb
# backends: import | triposr | trellis | hunyuan
```

Or drop any GLB as `raw.glb` / use `--demo` placeholder.

## Optional paid Tripo

```bash
export TRIPO_API_KEY=...
# use official tripo-python-sdk or scripts/characters/07_generate_tripo.py
```

Then:

```bash
python3 -m pipeline.cli character demo
```

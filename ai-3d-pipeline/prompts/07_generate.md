# Step 07 — generate (free)

Split sheet into `view_front.png`, `view_right.png`, `view_back.png`.

## Free chain (Studio / CLI default)

```powershell
python -m pipeline.cli generate <name> --force
# → scripts/characters/07_generate_chain.py
# Hunyuan :8080 → TRELLIS :8090 → HF TripoSR → demo mesh fallback
```

Optional local NVIDIA:

```powershell
.\scripts\serve_hunyuan.ps1   # :8080
.\scripts\serve_trellis.ps1   # :8090
```

Or drop any GLB as `raw.glb` / `python -m pipeline.cli character <name> --demo`.

## Optional paid Tripo

```bash
export TRIPO_API_KEY=...
# use official tripo-python-sdk or scripts/characters/07_generate_tripo.py
```

Then:

```bash
python3 -m pipeline.cli character demo
```

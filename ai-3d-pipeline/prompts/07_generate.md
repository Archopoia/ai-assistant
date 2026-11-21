# Step 07 — generate (free)

Split sheet into `view_front.png`, `view_right.png`, `view_back.png`.

## Free (recommended here)

```bash
# After starting TripoSR or TRELLIS locally:
python3 scripts/characters/07_generate_local.py \
  --backend triposr \
  --front examples/characters/demo/views/view_front.png \
  --right examples/characters/demo/views/view_right.png \
  --back examples/characters/demo/views/view_back.png \
  -o examples/characters/demo/exports/raw.glb
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

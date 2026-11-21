# Step 06 — character sheet for generators

You drop **one concept / reference picture** (not a finished sheet). The pipeline:

1. Captions the reference (Joy-Caption)
2. Generates orthographic front / right / back (A-pose, empty hands)
3. Scores each panel vs the reference (colour + silhouette)
4. Critiques misses and regenerates — **max 3 rounds** (`sheet_qc.json`)

Manual prompt if driving an image model yourself:

```
Character turnaround sheet: front, right side, back. Orthographic, same height,
A-pose, arms away from the body, legs apart. Empty hands: no weapon, no lantern,
no bag in hand. Light grey background, flat even light, no shadows.
Name the colour of every piece of clothing.
Match the uploaded reference character exactly.
```

Empty hands — props melt into fingers. Only true views (not mirrored left).

```bash
python -m pipeline.cli sheet hero --kind character --prompt "optional notes" --force
# put concept at examples/characters/hero/views/concept.png first
```

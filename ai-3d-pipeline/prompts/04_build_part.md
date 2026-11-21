# Step 04 — one part per session

```
Build part "<name>" from parts.json with bmesh in a Blender script.
For its outline: threshold side.png, trace the contour, simplify to about 30 points,
extrude to its width, bevel. Render next to the reference and list the differences
in cm. Fix and rerender, max 3 rounds.
```

Or run the automated box builder:

```bash
python3 -m pipeline.cli prop <name>
```

Use Sonnet for boxes/barrels; Opus for traced outlines and joints.

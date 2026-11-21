# Step 02 — measurable reference

Ask an image model:

```
Orthographic side view of [object], exactly side-on, no perspective.
Plain white background, flat colours, no shadows, no reflections.
Same scale as the front and top views. Nothing cut off at the edges.
```

Also request matching front and top views at the same scale.

If you only have one sheet with several views, ask Claude to cut it into
`front.png`, `side.png`, `top.png` under `examples/props/<name>/references/`.

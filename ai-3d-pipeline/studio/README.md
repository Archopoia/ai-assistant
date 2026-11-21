# 3D Pipeline Studio

Side-by-side walkthrough for non-developers:

- **Left:** each pipeline step + plain-English log  
- **Right:** the 3D model after that step  

## Open it

```bash
cd ai-3d-pipeline/studio
python3 -m http.server 8787 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8787/` (or use the Cursor app preview after publish).

Buttons:

1. Choose **Prop (crate)** or **Character**
2. **Play whole pipeline** — runs every step and updates the model
3. **Next step** — one step at a time
4. **Start over** — reset

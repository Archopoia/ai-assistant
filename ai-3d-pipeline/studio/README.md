# 3D Pipeline Studio

Local app for the **Create 3D Game Models for Free** tutorial funnel:

**Prompt or picture → pick route → game-ready export**

Three routes in, one pipeline out:

| Route | When | Steps |
|-------|------|--------|
| **Prop (code)** | Anything you could measure with a ruler | 02 sheet/refs → 03 OpenCV measure → 04–05 contour/box Blender build |
| **Character (generator)** | Anything you'd sculpt | 06–07 split sheet → Hunyuan/TRELLIS/HF TripoSR → 08–15 clean(+bake)/rig/clips |
| **Buildings** | Streets / blocks | Procedural generator |

## Start

```powershell
cd ai-3d-pipeline
.\scripts\start_studio.ps1
# http://127.0.0.1:8787/
```

1. Type a prompt and/or drop a concept / turnaround / orthographic sheet  
2. Route: **Auto** (or force Prop / Character / Buildings)  
3. **Start project** → run steps (or **Run remaining steps**)  
4. Model updates on the right  

**Single concept picture (the normal case):** step 06 captions the image (Joy-Caption), generates front/right/back, scores colour+silhouette vs the reference, critiques misses, and regenerates up to **3 rounds** (guide self-correction). Optional CharacterSheet LoRA Space tried first. Prompt-only still works via FLUX. True multi-panel sheets are detected and split only.

Generator chain (step 07): live `HUNYUAN_URL` → `TRELLIS_URL` → free HF TripoSR. AMD Lenovo = TripoSR unless you point at a remote NVIDIA box.

Prop path: measure → contour extrude in Blender.

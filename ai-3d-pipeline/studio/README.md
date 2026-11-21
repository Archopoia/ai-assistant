# 3D Pipeline Studio

Local app for the **Create 3D Game Models for Free** tutorial funnel:

**Prompt or picture → pick route → game-ready export**

Three routes in, one pipeline out:

| Route | When | Steps |
|-------|------|--------|
| **Prop (code)** | Anything you could measure with a ruler | 02 refs → 03 parts.json → 04–05 Blender build/export |
| **Character (generator)** | Anything you'd sculpt | 06–07 sheet → TripoSR/GLB → 08–15 clean/rig/clips/export |
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

Characters without a local NVIDIA GPU use free Hugging Face TripoSR for step 07.

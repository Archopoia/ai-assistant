# 3D Creator Studio

Local app that follows the Opus + Blender + Tripo tutorial — **you** make props and characters.

## Start

```powershell
cd ai-3d-pipeline
.\scripts\start_studio.ps1
# → http://127.0.0.1:8787/
```

## Props (tutorial steps 02–05)

1. Name the object, pick a template (crate / barrel / table / …), set metres
2. Optional: upload front/side/top reference pics
3. **Suggest parts.json** → edit sizes/colours → **Save**
4. **Build in Blender** → assembled GLB/FBX in the viewport

Hard-surface props are measured code, not image-to-3D (as the tutorial says).

## Characters (tutorial steps 06–15)

1. Upload A-pose **front** (plus right/back) — empty hands
2. **Generate mesh** → free [TripoSR](https://huggingface.co/spaces/stabilityai/TripoSR) on Hugging Face (no local NVIDIA required)
3. Or drop an existing `.glb`
4. **Clean → rig → clips → export** runs the Blender pipeline

## Buildings

Parametric houses/shops from seeds (tutorial city route).

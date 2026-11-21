# 3D Pipeline Studio

Local app on this PC: left = steps + log, right = live 3D model.

## Start (Windows)

```powershell
cd ai-3d-pipeline
.\scripts\start_studio.ps1
# → http://127.0.0.1:8787/
```

Uses Blender on this machine for real prop/character builds.
Image→mesh (TRELLIS) needs an NVIDIA GPU — this AMD laptop uses the free demo mesh / imported GLB instead.

Buttons: **Prop** / **Character** → **Play whole pipeline** or **Next step**.

# Free path ↔ guide (steps 01–15)

How this repo maps the tutorial **without paid Tripo**.

| Step | Guide | Free implementation | QC |
|------|-------|---------------------|-----|
| **01** | Prompt/picture → route | Studio + `prompt_parse.py` | — |
| **02** | Orthographic refs | Single concept → caption+FLUX+QC ≤3 **or** split real sheet (`generate_sheet.py`) | `sheet_qc.json` |
| **03** | `parts.json` numbers first; wait for OK | OpenCV `measure_parts.py`; Studio **Save parts** = OK | Contour on tallest |
| **04** | One part; contour; render vs ref; fix ≤3 | `build_part.py` + `compare_part.py` via `pipeline/prop_build.py` | `build_qc.json`, `*_side_vs_ref_rN.png` |
| **05** | Assemble, gaps, export | `assemble.py` + glTF-Transform | assemble report |
| **05b** | Buildings | `buildings.py` | — |
| **06** | Turnaround from concept | Same as 02 character path; empty hands / A-pose / true right | `sheet_qc.json` |
| **07** | Image→mesh | Hunyuan→TRELLIS→HF TripoSR; **demo mesh** if all fail | — |
| **08** | Clean + bake + **5 cm grid** | `clean.py` (`grid=True`) | clean_report |
| **09** | Tag parts | `split_parts.py` | flat colour renders |
| **10** | Joints + grid/axes | `joints.py` | joints_*.png |
| **11** | Mixamo weights / cloth bones | `rig_weights.py` | rig_report |
| **12** | Pose battery; fix ≤3 | `pose_test.py` + re-`rig_weights` loop in Studio | pose_test_report |
| **13–14** | Idle/walk + clip QC | `clips/*` + `check_clips.py` | clip_qc_report |
| **15** | FBX (no apply xform, no leaf bones) | `export_fbx.py` + GLB opt | export_report |

## Studio

`.\scripts\start_studio.ps1` → http://127.0.0.1:8787/

- Drop **one** concept picture (not a sheet).
- Prop: refs → parts (**Save**) → build (QC rounds) → done.
- Character: sheet QC → generate → clean…export as separate steps.

## CLI

```powershell
python -m pipeline.cli doctor
python -m pipeline.cli sheet hero --kind character --concept ref.png --force
python -m pipeline.cli generate hero --force
python -m pipeline.cli character hero
python -m pipeline.cli measure barrel --width 0.5 --depth 0.5 --height 0.9
python -m pipeline.cli prop barrel
```

## Not free / optional

- Tripo paid API (`07_generate_tripo.py`)
- Local Hunyuan/TRELLIS need **NVIDIA** (AMD Lenovo uses HF TripoSR or demo mesh)

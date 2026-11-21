#!/usr/bin/env python3
"""
Step 02 / 06 — turn a SINGLE reference picture (or prompt) into a full sheet.

Guide path:
  1. Caption the reference (Joy-Caption when available)
  2. Generate orthographic / turnaround panels (HF FLUX.1-schnell)
  3. Score each panel vs the reference (colour + silhouette)
  4. Critique → refine prompt → regenerate (max 3 rounds)

A lone drop-in image is NEVER treated as a finished character sheet.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

MAX_ROUNDS = 3
PASS_SCORE = 0.42  # histogram∩silhouette composite; tuned for free T2I drift


def _hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")


def _save_png(src: str | Path, out: Path) -> Path:
    out = out.with_suffix(".png")
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.open(src).convert("RGB").save(out, format="PNG")
    return out


def caption_reference(path: Path, hint: str = "") -> str:
    """Free vision caption of the concept image (Joy-Caption HF Space)."""
    try:
        from gradio_client import Client, handle_file

        client = Client("fancyfeast/joy-caption-alpha-two", token=_hf_token())
        result = client.predict(
            input_image=handle_file(str(path)),
            caption_type="Descriptive",
            caption_length="long",
            extra_options=[],
            name_input="",
            custom_prompt=(
                "Describe the character or creature for a 3D game turnaround sheet: "
                "species, body proportions, hair, every clothing piece and its colour, "
                "accessories (but note hands must be empty in the sheet), art style."
            ),
            api_name="/stream_chat",
        )
        text = result[-1] if isinstance(result, (list, tuple)) else str(result)
        if isinstance(text, list):
            text = text[-1] if text else ""
        text = str(text).strip()
        if text:
            if hint.strip():
                return f"{hint.strip()}. Visual reference details: {text}"
            return text
    except Exception as e:
        print(f"[caption] Joy-Caption failed: {e}")
    return hint.strip() or "game character matching the uploaded reference"


class QuotaError(RuntimeError):
    """HF ZeroGPU / auth quota exhausted."""


def _flux_t2i(prompt: str, out: Path, *, width: int, height: int) -> Path:
    from gradio_client import Client

    token = _hf_token()
    if not token:
        # Fail fast with a clear message — anonymous ZeroGPU depletes quickly
        print("[flux] No HF_TOKEN set; anonymous ZeroGPU often hits quota.")
    try:
        client = Client("black-forest-labs/FLUX.1-schnell", token=token)
        result = client.predict(
            prompt=prompt,
            seed=0,
            randomize_seed=True,
            width=int(width),
            height=int(height),
            num_inference_steps=4,
            api_name="/infer",
        )
    except Exception as e:
        msg = str(e)
        if "ZeroGPU" in msg or "quota" in msg.lower() or "exceeded" in msg.lower():
            raise QuotaError(
                "HF ZeroGPU quota exceeded. Set HF_TOKEN (https://huggingface.co/settings/tokens) "
                "then restart Studio, or continue with offline concept fallback."
            ) from e
        raise
    src = result[0] if isinstance(result, (list, tuple)) else result
    if not src or not Path(src).exists():
        raise RuntimeError(f"FLUX returned no image: {result!r}")
    return _save_png(src, out)


def _offline_views_from_concept(concept: Path, out_dir: Path, kind: str) -> dict[str, str]:
    """When cloud image-gen is unavailable: stamp the concept into view slots so the pipeline continues."""
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(concept).convert("RGB")
    names = (
        ["view_front.png", "view_right.png", "view_back.png"]
        if kind == "character"
        else ["front.png", "side.png", "top.png"]
    )
    labels = (
        ["FRONT (offline)", "RIGHT (offline)", "BACK (offline)"]
        if kind == "character"
        else ["FRONT (offline)", "SIDE (offline)", "TOP (offline)"]
    )
    saved = {}
    for name, label in zip(names, labels):
        panel = img.copy()
        # banner so it's obvious this isn't a real turnaround
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(panel)
        draw.rectangle((0, 0, panel.width, 36), fill=(20, 20, 20))
        draw.text((10, 8), f"{label} — set HF_TOKEN for real sheets", fill=(232, 184, 109))
        path = out_dir / name
        panel.save(path, format="PNG")
        saved[name] = str(path)
    return saved


def _try_charactersheet_lora(concept: Path, out_sheet: Path) -> Path | None:
    """Best-effort: dedicated image→sheet Space (may be gated / down)."""
    try:
        from gradio_client import Client, handle_file

        client = Client("ztoolx/charactersheet-lora-demo", token=_hf_token())
        result = client.predict(
            reference_image=handle_file(str(concept)),
            prompt=(
                "Convert the character in the image to a Character Sheet showing "
                "front, side and back full body views. A-pose, empty hands, "
                "orthographic, flat even light, light grey background."
            ),
            num_inference_steps=8,
            guidance_scale=1.0,
            lora_strength=1.0,
            seed=0,
            randomize_seed=True,
            width=1536,
            height=1024,
            api_name="/generate",
        )
        src = result[0] if isinstance(result, (list, tuple)) else result
        if src and Path(src).exists():
            return _save_png(src, out_sheet)
    except Exception as e:
        print(f"[charactersheet-lora] skipped: {e}")
    return None


def _silhouette(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))


def score_vs_reference(ref: Path, candidate: Path) -> dict:
    """Composite similarity: colour hist + silhouette overlap (0..1)."""
    a = cv2.imread(str(ref))
    b = cv2.imread(str(candidate))
    if a is None or b is None:
        return {"score": 0.0, "hist": 0.0, "sil": 0.0}
    b = cv2.resize(b, (a.shape[1], a.shape[0]))
    ha = cv2.calcHist([a], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3)
    hb = cv2.calcHist([b], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3)
    cv2.normalize(ha, ha)
    cv2.normalize(hb, hb)
    hist = float(cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL))
    hist = max(0.0, min(1.0, (hist + 1.0) * 0.5))  # [-1,1] → [0,1]

    sa = cv2.resize(_silhouette(ref), (128, 128))
    sb = cv2.resize(_silhouette(candidate), (128, 128))
    inter = np.logical_and(sa > 0, sb > 0).sum()
    union = np.logical_or(sa > 0, sb > 0).sum()
    sil = float(inter / union) if union else 0.0
    score = 0.55 * hist + 0.45 * sil
    return {"score": round(score, 4), "hist": round(hist, 4), "sil": round(sil, 4)}


def critique(scores: dict[str, dict], design: str) -> str:
    weak = [k for k, v in scores.items() if v["score"] < PASS_SCORE]
    notes = []
    if weak:
        notes.append(f"Panels too far from reference: {', '.join(weak)}.")
    for k, v in scores.items():
        if v["hist"] < 0.4:
            notes.append(f"{k}: colours diverge — lock palette from the reference.")
        if v["sil"] < 0.35:
            notes.append(f"{k}: silhouette mismatch — match proportions / costume volumes.")
    if not notes:
        notes.append("Views acceptably match reference.")
    notes.append(
        "Keep orthographic A-pose, empty hands, flat even light, light grey background, "
        "same character identity as the reference. "
        f"Design lock: {design[:400]}"
    )
    return " ".join(notes)


def character_prompts(design: str, feedback: str = "") -> dict[str, str]:
    base = (
        f"{design}. Same exact character as the reference. Orthographic game turnaround, "
        "A-pose, arms away from body, legs slightly apart, EMPTY HANDS "
        "(no weapon, lantern, bag, or prop), flat even light, light grey background, "
        "no shadows, no perspective, full body, clean silhouette, consistent colours."
    )
    if feedback:
        base += f" Corrections: {feedback}"
    return {
        "view_front.png": f"{base} FRONT VIEW only, facing camera, single figure centered.",
        "view_right.png": f"{base} RIGHT SIDE VIEW only, true right profile (not mirrored left), single figure.",
        "view_back.png": f"{base} BACK VIEW only, facing away, single figure centered.",
    }


def prop_prompts(design: str, feedback: str = "") -> dict[str, str]:
    base = (
        f"{design}. Same object as the reference. Orthographic product reference, "
        "flat colours, plain white background, no shadows, no reflections, no perspective."
    )
    if feedback:
        base += f" Corrections: {feedback}"
    return {
        "front.png": f"{base} FRONT VIEW only.",
        "side.png": f"{base} SIDE VIEW only, exactly side-on.",
        "top.png": f"{base} TOP VIEW only, looking straight down.",
    }


def looks_like_multiview_sheet(path: Path) -> bool:
    """Heuristic: wide image with 2+ content panels → existing sheet, just split."""
    img = cv2.imread(str(path))
    if img is None:
        return False
    h, w = img.shape[:2]
    if w < h * 1.35:
        return False
    from split_sheet import split_image

    try:
        crops = split_image(path, n_hint=3)
        return len(crops) >= 3
    except Exception:
        return False


def generate_views(
    *,
    kind: str,
    design: str,
    out_dir: Path,
    concept: Path | None = None,
    force: bool = False,
    mode: str = "auto",  # auto | panels | sheet
    max_rounds: int = MAX_ROUNDS,
    log=print,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"rounds": [], "backend": None, "saved": {}, "caption": None}

    # Persist concept as the source of truth
    concept_path: Path | None = None
    if concept and concept.exists():
        concept_path = out_dir / "concept.png"
        if concept.resolve() != concept_path.resolve():
            shutil.copy2(concept, concept_path)
        # If user actually dropped a finished multi-panel sheet, split & stop
        if looks_like_multiview_sheet(concept_path) and mode in ("auto", "sheet"):
            from split_sheet import save_character_views, save_prop_views

            log("Detected multi-panel sheet — splitting (no generation).")
            split = (
                save_character_views(concept_path, out_dir)
                if kind == "character"
                else save_prop_views(concept_path, out_dir)
            )
            report.update({"mode": "split_existing", "saved": split, "backend": "split"})
            (out_dir / "sheet_qc.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            return report

        log("Captioning reference image…")
        design = caption_reference(concept_path, design)
        report["caption"] = design
        log(f"Caption: {design[:240]}…")

    names = (
        ["view_front.png", "view_right.png", "view_back.png"]
        if kind == "character"
        else ["front.png", "side.png", "top.png"]
    )
    if all((out_dir / n).exists() for n in names[:2]) and not force:
        report.update({"skipped": True, "reason": "views already present"})
        return report

    # Optional one-shot dedicated sheet model when we have a concept
    if concept_path and kind == "character":
        log("Trying CharacterSheet LoRA (image→sheet)…")
        sheet = _try_charactersheet_lora(concept_path, out_dir / "sheet_gen.png")
        if sheet:
            from split_sheet import save_character_views

            split = save_character_views(sheet, out_dir)
            scores = {
                k: score_vs_reference(concept_path, Path(v))
                for k, v in split.items()
                if Path(v).exists() and k.startswith("view_")
            }
            avg = float(np.mean([s["score"] for s in scores.values()])) if scores else 0.0
            report["rounds"].append({"backend": "charactersheet_lora", "scores": scores, "avg": avg})
            report["saved"] = split
            report["backend"] = "charactersheet_lora"
            if avg >= PASS_SCORE:
                report["passed"] = True
                (out_dir / "sheet_qc.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                log(f"CharacterSheet LoRA passed (avg={avg:.3f})")
                return report
            log(f"CharacterSheet LoRA weak (avg={avg:.3f}) — entering FLUX correction loop")

    feedback = ""
    best: dict | None = None
    best_avg = -1.0
    w, h = (768, 1024) if kind == "character" else (768, 768)

    try:
        for round_i in range(1, max_rounds + 1):
            log(f"Round {round_i}/{max_rounds}: generate panels via FLUX…")
            prompts = character_prompts(design, feedback) if kind == "character" else prop_prompts(design, feedback)
            saved = {}
            for name, prompt in prompts.items():
                path = _flux_t2i(prompt, out_dir / name, width=w, height=h)
                saved[name] = str(path)

            scores = {}
            if concept_path:
                for name, path in saved.items():
                    scores[name] = score_vs_reference(concept_path, Path(path))
                avg = float(np.mean([s["score"] for s in scores.values()]))
            else:
                avg = 1.0
                scores = {n: {"score": 1.0, "hist": 1.0, "sil": 1.0} for n in saved}

            round_info = {
                "round": round_i,
                "scores": scores,
                "avg": round(avg, 4),
                "feedback": feedback,
                "backend": "flux_schnell",
            }
            report["rounds"].append(round_info)
            log(f"  scores={[ (k, v['score']) for k,v in scores.items() ]} avg={avg:.3f}")

            if avg > best_avg:
                best_avg = avg
                best = dict(saved)
                for name, path in saved.items():
                    shutil.copy2(path, out_dir / f"best_{name}")

            if avg >= PASS_SCORE or not concept_path:
                report["passed"] = True
                break

            feedback = critique(scores, design)
            log(f"  critique → {feedback[:220]}…")
    except QuotaError as e:
        log(str(e))
        if concept_path and concept_path.exists():
            log("Offline fallback: using your concept as temporary front/right/back slots.")
            saved = _offline_views_from_concept(concept_path, out_dir, kind)
            report["saved"] = saved
            report["backend"] = "offline_concept"
            report["passed"] = False
            report["mode"] = "offline_fallback"
            report["warning"] = str(e)
            (out_dir / "sheet_qc.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            return report
        raise

    if best:
        for name, path in best.items():
            src = out_dir / f"best_{name}"
            if src.exists():
                shutil.copy2(src, out_dir / name)
                report["saved"][name] = str(out_dir / name)
            else:
                report["saved"][name] = path
            bp = out_dir / f"best_{name}"
            if bp.exists():
                bp.unlink()

    report["backend"] = "flux_schnell_loop"
    report["best_avg"] = best_avg
    report["passed"] = bool(report.get("passed") or (best_avg >= PASS_SCORE) or not concept_path)
    report["mode"] = "panels_corrected"
    (out_dir / "sheet_qc.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"Sheet done. passed={report['passed']} best_avg={best_avg:.3f} → {out_dir}")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Reference → full turnaround/ortho sheet with QC loop")
    ap.add_argument("--kind", choices=("character", "prop"), required=True)
    ap.add_argument("--prompt", default="")
    ap.add_argument("--concept", type=Path, default=None, help="Single reference image (NOT a finished sheet)")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--rounds", type=int, default=MAX_ROUNDS)
    args = ap.parse_args()
    if not args.prompt.strip() and not (args.concept and args.concept.exists()):
        raise SystemExit("Need --concept (single reference) and/or --prompt")
    info = generate_views(
        kind=args.kind,
        design=args.prompt.strip() or "game asset",
        out_dir=args.out,
        concept=args.concept,
        force=args.force,
        max_rounds=args.rounds,
    )
    print(json.dumps({k: v for k, v in info.items() if k != "rounds"}, indent=2))
    print(f"rounds={len(info.get('rounds') or [])} passed={info.get('passed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

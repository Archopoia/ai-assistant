from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .config import ROOT, load_config


def run_blender_script(
    script: Path,
    *,
    blend_file: Path | None = None,
    args: dict[str, Any] | None = None,
    background: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a Blender Python script with JSON args via env PIPELINE_ARGS."""
    cfg = load_config()
    blender = cfg.get("blender_bin", "blender")
    cmd = [blender]
    if background:
        cmd.append("-b")
    if blend_file is not None:
        cmd.append(str(blend_file))
    cmd.extend(["--python", str(script), "--"])

    env = os.environ.copy()
    env["PIPELINE_ROOT"] = str(ROOT)
    if args:
        env["PIPELINE_ARGS"] = json.dumps(args)

    print("$", " ".join(cmd), flush=True)
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    combined = (result.stdout or "") + (result.stderr or "")
    # Blender often exits 0 even when the Python script raises
    if result.returncode != 0 or "Traceback (most recent call last)" in combined:
        raise RuntimeError(
            f"Blender failed for {script.name} (exit {result.returncode})\n{combined[-2500:]}"
        )
    return result


def run_blender_code(code: str, *, args: dict[str, Any] | None = None) -> None:
    """Write temp script and execute in Blender."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
        tmp.write(code)
        path = Path(tmp.name)
    try:
        run_blender_script(path, args=args)
    finally:
        path.unlink(missing_ok=True)


def parse_pipeline_args() -> dict[str, Any]:
    raw = os.environ.get("PIPELINE_ARGS", "{}")
    return json.loads(raw)

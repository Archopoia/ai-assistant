from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict[str, Any]:
    path = ROOT / "config" / "defaults.yaml"
    with path.open() as f:
        cfg = yaml.safe_load(f) or {}
    env_bin = os.environ.get("BLENDER_BIN")
    if env_bin:
        cfg["blender_bin"] = env_bin
    return cfg


def asset_dir(kind: str, name: str) -> Path:
    return ROOT / "examples" / kind / name


def ensure_asset_dirs(kind: str, name: str) -> Path:
    base = asset_dir(kind, name)
    for sub in ("references", "parts", "renders", "exports", "views", "clips"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base

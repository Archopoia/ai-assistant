#!/usr/bin/env python3
"""
Optional paid Tripo multiview client (step 07).
Free path: skip this and use import / TripoSR / TRELLIS instead.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

API = os.environ.get("TRIPO_API_BASE", "https://api.tripo3d.ai/v2/openapi")


def main() -> int:
    key = os.environ.get("TRIPO_API_KEY")
    if not key:
        print("Set TRIPO_API_KEY or use the free local/import route.", file=sys.stderr)
        return 2

    ap = argparse.ArgumentParser()
    ap.add_argument("--front", type=Path, required=True)
    ap.add_argument("--right", type=Path, default=None)
    ap.add_argument("--back", type=Path, default=None)
    ap.add_argument("--left", type=Path, default=None)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--texture", action="store_true", default=True)
    args = ap.parse_args()

    headers = {"Authorization": f"Bearer {key}"}
    # Upload helpers vary by Tripo API version — this follows the OpenAPI multiview task pattern.
    # See https://github.com/Tripo-Developer/tripo-python-sdk for the maintained client.
    print("Prefer the official tripo-python-sdk for production.")
    print("Stub: install `pip install tripo3d` and call MultiviewReconstruction.")
    print("Views:", args.front, args.right, args.back, args.left)
    print("Output would be:", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Fetch the credit-g dataset (OpenML data id 31) and cache it locally.

Keeps the notebook reproducible offline: the raw ARFF is stored under
artifacts/data and reused if present.
"""
from __future__ import annotations

import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "artifacts", "data")
URL = "https://api.openml.org/data/v1/download/31/credit-g.arff"
TARGET = os.path.join(DATA, "credit-g.arff")


def main() -> int:
    os.makedirs(DATA, exist_ok=True)
    if os.path.exists(TARGET) and os.path.getsize(TARGET) > 10_000:
        print("cached:", TARGET, os.path.getsize(TARGET), "bytes")
        return 0
    with urllib.request.urlopen(URL, timeout=120) as r, open(TARGET, "wb") as f:
        f.write(r.read())
    print("downloaded:", TARGET, os.path.getsize(TARGET), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

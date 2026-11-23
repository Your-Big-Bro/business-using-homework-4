"""Download the latest Prometheus release for Windows into ./prometheus.

The Windows sandbox has no working PowerShell HTTP client (TLS fails), so we
fetch with urllib from a normal Python process.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import zipfile

API = "https://api.github.com/repos/prometheus/prometheus/releases/latest"
HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(os.path.dirname(HERE), "prometheus")


def main() -> int:
    os.makedirs(DEST, exist_ok=True)
    req = urllib.request.Request(API, headers={"User-Agent": "dsh-homework"})
    meta = json.load(urllib.request.urlopen(req, timeout=60))
    tag = meta["tag_name"]
    asset = next(
        (a for a in meta["assets"] if a["name"].endswith("windows-amd64.zip")),
        None,
    )
    if asset is None:
        print("no windows-amd64 asset found", file=sys.stderr)
        return 1
    print(f"release {tag}: {asset['name']} ({asset['size'] / 1e6:.1f} MB)")
    target = os.path.join(DEST, asset["name"])
    if not os.path.exists(target):
        with urllib.request.urlopen(asset["browser_download_url"], timeout=300) as r, open(target, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
    print("downloaded:", target, os.path.getsize(target))

    with zipfile.ZipFile(target) as z:
        z.extractall(DEST)
    exe = os.path.join(DEST, "prometheus.exe")
    if not os.path.exists(exe):
        # zip contains prometheus-<version>.windows-amd64/prometheus.exe
        for root, _dirs, files in os.walk(DEST):
            if "prometheus.exe" in files:
                exe = os.path.join(root, "prometheus.exe")
                break
    print("prometheus.exe:", exe)
    with open(os.path.join(DEST, "VERSION.txt"), "w", encoding="utf-8") as f:
        f.write(f"{tag}\n{asset['name']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

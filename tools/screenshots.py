"""Captures Prometheus UI screenshots with headless Edge.

Used to produce artifacts/screenshots/*.png for the Word report / presentation.
Waits until at least one alert is firing, then screenshots /alerts, /graph, /targets.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOTS = os.path.join(ROOT, "artifacts", "screenshots")
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
PROM = "http://127.0.0.1:9090"


def api(path: str):
    with urllib.request.urlopen(PROM + path, timeout=10) as r:
        return json.load(r)


def wait_firing(timeout: float = 420.0) -> list[dict]:
    t0 = time.time()
    while time.time() - t0 < timeout:
        alerts = api("/api/v1/alerts")["data"]["alerts"]
        firing = [a for a in alerts if a["state"] == "firing"]
        print(f"  alerts: {len(alerts)} total, {len(firing)} firing", flush=True)
        if firing:
            return firing
        time.sleep(5)
    return []


def shot(edge: str, url: str, out: str, height: int = 1000, budget: int = 12000) -> bool:
    profile = os.path.join(ROOT, ".tmp-edge-profile")
    cmd = [
        edge,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--disable-extensions",
        f"--user-data-dir={profile}",
        f"--window-size=1600,{height}",
        f"--virtual-time-budget={budget}",
        f"--screenshot={out}",
        url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not os.path.exists(out):
        print(f"  ERR {os.path.basename(out)}: файл не создан")
        print("   stderr:", (res.stderr or "")[-400:])
        return False
    size = os.path.getsize(out)
    ok = size > 15_000
    print(f"  {'OK ' if ok else 'ERR'} {os.path.basename(out)} ({size / 1024:.0f} KB)")
    if not ok:
        print("   stderr:", (res.stderr or "")[-400:])
    return ok


def main() -> int:
    os.makedirs(SHOTS, exist_ok=True)
    edge = next((p for p in EDGE_CANDIDATES if os.path.exists(p)), None)
    if edge is None:
        print("Edge not found", file=sys.stderr)
        return 1

    print("waiting for firing alerts...")
    firing = wait_firing()
    print("firing:", [a["labels"]["alertname"] for a in firing])
    if not firing:
        print("no alert has fired within the timeout", file=sys.stderr)
        return 2

    # give the F1 curve a bit more time to finish its decline
    time.sleep(20)

    urls = {
        "prometheus_alerts.png": f"{PROM}/alerts",
        "prometheus_targets.png": f"{PROM}/targets",
        "prometheus_graph_f1.png": (
            f"{PROM}/graph?g0.expr=model_f1_score&g0.tab=0&g0.range_input=15m"
        ),
        "prometheus_graph_drift.png": (
            f"{PROM}/graph?g0.expr=model_drift_share&g0.tab=0&g0.range_input=15m"
        ),
    }
    ok = 0
    for name, url in urls.items():
        ok += shot(edge, url, os.path.join(SHOTS, name))

    # короткий текстовый слепок состояния — пригодится в отчёте
    state = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "alerts": api("/api/v1/alerts")["data"]["alerts"],
        "f1_series_size": len(api("/api/v1/query?query=model_f1_score")["data"]["result"]),
    }
    with open(os.path.join(SHOTS, "prometheus_state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"captured {ok}/{len(urls)} screenshots")
    return 0 if ok == len(urls) else 3


if __name__ == "__main__":
    raise SystemExit(main())

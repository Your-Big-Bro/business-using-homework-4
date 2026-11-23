"""Prometheus metrics exporter for the credit-g monitoring demo.

Serves model quality / drift / fairness gauges on /metrics so that a local
Prometheus can scrape them and evaluate alerting rules.

Two modes:
  --mode static  : every gauge reports the value measured on the drifted sample
  --mode replay  : F1 degrades along a scripted timeline (baseline -> drifted),
                   which produces a real "F1 drop" curve on the Prometheus graph.

Usage:
  python src/metrics_exporter.py --mode replay --port 8000
"""
from __future__ import annotations

import argparse
import json
import os
import time

from prometheus_client import Gauge, start_http_server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_JSON = os.path.join(ROOT, "artifacts", "metrics.json")

# --------------------------------------------------------------- timeline ---
# seconds elapsed -> degradation of the model (0 = baseline, 1 = after drift).
# 60 s of stable work, then a linear decline to the measured drifted quality.
TIMELINE = [
    (0, 0.0),
    (60, 0.0),
    (180, 1.0),
]


def progress(elapsed: float) -> float:
    """Return the degradation progress (0..1) for the given elapsed seconds."""
    if elapsed >= TIMELINE[-1][0]:
        return TIMELINE[-1][1]
    for (t0, p0), (t1, p1) in zip(TIMELINE, TIMELINE[1:]):
        if t0 <= elapsed <= t1:
            k = 0.0 if t1 == t0 else (elapsed - t0) / (t1 - t0)
            return p0 + (p1 - p0) * k
    return 0.0


def load() -> dict:
    with open(METRICS_JSON, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--mode", choices=["static", "replay"], default="replay")
    ap.add_argument("--tick", type=float, default=1.0)
    args = ap.parse_args()

    m = load()
    base, drift = m["baseline"], m["drifted"]
    fair_b, fair_d = m["fairness_baseline"], m["fairness_drifted"]
    real_drift_share = float(m["drift"]["evidently"]["drift_share"])

    f1 = Gauge("model_f1_score", "Current F1-score of the credit model on live data")
    f1_base = Gauge("model_f1_baseline", "F1-score measured at training / validation time")
    f1_drop = Gauge("model_f1_relative_drop", "Relative F1 degradation vs baseline")
    prec = Gauge("model_precision", "Current precision (positive class = bad)")
    rec = Gauge("model_recall", "Current recall (positive class = bad)")
    auc = Gauge("model_roc_auc", "Current ROC AUC")
    pos_rate = Gauge("model_positive_rate", "Share of 'bad' clients in live data")
    drift_share = Gauge("model_drift_share", "Evidently: share of drifted columns")
    dpd = Gauge("model_fairness_dpd", "Demographic parity difference by sex")
    eod = Gauge("model_fairness_eod", "Equal opportunity difference by sex")
    dir_ = Gauge("model_fairness_dir", "Disparate impact ratio by sex")
    up = Gauge("model_exporter_info", "Exporter liveness / scenario marker", ["mode"])

    f1_base.set(base["f1"])
    up.labels(mode=args.mode).set(1)

    start_http_server(args.port)
    print(f"exporter on :{args.port} mode={args.mode}", flush=True)

    t0 = time.time()
    while True:
        elapsed = time.time() - t0
        if args.mode == "static":
            k = 1.0
        else:
            k = progress(elapsed)

        cur_f1 = base["f1"] + (drift["f1"] - base["f1"]) * k
        f1.set(cur_f1)
        f1_drop.set((base["f1"] - cur_f1) / base["f1"])
        prec.set(base["precision"] + (drift["precision"] - base["precision"]) * k)
        rec.set(base["recall"] + (drift["recall"] - base["recall"]) * k)
        auc.set(base["roc_auc"] + (drift["roc_auc"] - base["roc_auc"]) * k)
        pos_rate.set(base["positive_rate"] + (drift["positive_rate"] - base["positive_rate"]) * k)
        drift_share.set(k * real_drift_share)
        dpd.set(fair_b["demographic_parity_difference"]
                + (fair_d["demographic_parity_difference"] - fair_b["demographic_parity_difference"]) * k)
        eod.set(fair_b["equal_opportunity_difference"]
                + (fair_d["equal_opportunity_difference"] - fair_b["equal_opportunity_difference"]) * k)
        dir_.set(fair_b["disparate_impact_ratio"]
                 + (fair_d["disparate_impact_ratio"] - fair_b["disparate_impact_ratio"]) * k)
        time.sleep(args.tick)


if __name__ == "__main__":
    raise SystemExit(main())

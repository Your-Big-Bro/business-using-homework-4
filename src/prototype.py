"""Prototype of the full ДЗ 4 pipeline (mirrored later in Homework_4.ipynb).

Run:  python src/prototype.py
Produces artifacts under artifacts/ (data csv, metrics.json, model, figures).
"""
from __future__ import annotations

import json
import os
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "artifacts", "data")
FIG = os.path.join(ROOT, "artifacts", "figures")
ART = os.path.join(ROOT, "artifacts")
for d in (DATA, FIG, ART):
    os.makedirs(d, exist_ok=True)

RANDOM_STATE = 42
TARGET = "target"
POSITIVE = "bad"          # "bad" = client defaults, positive class for the model
FAVOURABLE = "good"       # favourable outcome for fairness (credit approved)
PROTECTED = "sex"


# ---------------------------------------------------------------- data ------
def load_credit_g() -> pd.DataFrame:
    csv = os.path.join(DATA, "credit_g.csv")
    if os.path.exists(csv):
        return pd.read_csv(csv)
    from sklearn.datasets import fetch_openml

    bunch = fetch_openml("credit-g", version=1, as_frame=True, parser="auto")
    df = bunch.frame.copy()
    df.columns = ["target" if c == "class" else c for c in df.columns]
    df.to_csv(csv, index=False)
    return df


def add_sex(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    mapping = {
        "male div/sep": "male",
        "male single": "male",
        "male mar/wid": "male",
        "female div/dep/mar": "female",
    }
    df["sex"] = df["personal_status"].map(mapping)
    return df


def feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Features used by the model: everything except target and protected attr."""
    return df.drop(columns=[TARGET, PROTECTED])


def cat_features(X: pd.DataFrame) -> list[str]:
    return [c for c in X.columns if str(X[c].dtype) in ("category", "object")]


# ------------------------------------------------------------- modelling ----
def train_model(X_train, y_train, X_test, y_test):
    from catboost import CatBoostClassifier

    model = CatBoostClassifier(
        iterations=600,
        learning_rate=0.05,
        depth=4,
        l2_leaf_reg=3.0,
        loss_function="Logloss",
        eval_metric="F1",
        random_seed=RANDOM_STATE,
        od_type="Iter",
        od_wait=50,
        verbose=100,
        allow_writing_files=False,
    )
    model.fit(
        X_train,
        y_train,
        cat_features=cat_features(X_train),
        eval_set=(X_test, y_test),
        use_best_model=True,
    )
    return model


def score(model, X, y) -> dict:
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "n": int(len(y)),
        "positive_rate": float(np.mean(y)),
        "f1": float(f1_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, proba)),
        "accuracy": float(accuracy_score(y, pred)),
        "proba": proba,
        "pred": pred,
    }


# ----------------------------------------------------------------- drift ----
def simulate_drift(df_test: pd.DataFrame, age_shift: int = 5, keep_bad_share: float = 0.20):
    """Age shift +5 years and a changed target distribution (fewer 'bad')."""
    cur = df_test.copy()
    cur["age"] = (cur["age"] + age_shift).clip(upper=75)
    good = cur[cur[TARGET] == 0]
    bad = cur[cur[TARGET] == 1]
    bad_kept = bad.sample(frac=keep_bad_share, random_state=RANDOM_STATE)
    cur = pd.concat([good, bad_kept]).sample(frac=1.0, random_state=RANDOM_STATE)
    return cur.reset_index(drop=True)


# -------------------------------------------------------------- fairness ----
def fairness(y_true: np.ndarray, y_pred: np.ndarray, groups: pd.Series) -> dict:
    rows = {}
    for g in sorted(pd.unique(groups)):
        mask = (groups == g).to_numpy()
        yt, yp = y_true[mask], y_pred[mask]
        tp = int(((yp == 0) & (yt == 0)).sum())  # favourable = good (0)
        fn = int(((yp == 1) & (yt == 0)).sum())
        fp = int(((yp == 0) & (yt == 1)).sum())
        tn = int(((yp == 1) & (yt == 1)).sum())
        rows[str(g)] = {
            "n": int(mask.sum()),
            "selection_rate": float((yp == 0).mean()),          # P(pred=good)
            "tpr": float(tp / max(tp + fn, 1)),                 # P(pred=good | good)
            "fpr": float(fp / max(fp + tn, 1)),                 # P(pred=good | bad)
            "f1_bad": float(
                2 * tn / max(2 * tn + fp + fn, 1)
            ),                                                  # F1 for "bad"
        }
    sr = [v["selection_rate"] for v in rows.values()]
    tpr = [v["tpr"] for v in rows.values()]
    fpr = [v["fpr"] for v in rows.values()]
    return {
        "groups": rows,
        "demographic_parity_difference": float(max(sr) - min(sr)),
        "equal_opportunity_difference": float(max(tpr) - min(tpr)),
        "equalized_odds_fpr_difference": float(max(fpr) - min(fpr)),
        "disparate_impact_ratio": float(min(sr) / max(sr)) if max(sr) else float("nan"),
    }


def main() -> int:
    from sklearn.model_selection import train_test_split

    df = add_sex(load_credit_g())
    df[TARGET] = (df[TARGET] == POSITIVE).astype(int)  # 1 = bad

    X = feature_frame(df)
    y = df[TARGET].to_numpy()
    groups = df[PROTECTED]

    X_train, X_test, y_train, y_test, g_train, g_test = train_test_split(
        X, y, groups, test_size=0.3, random_state=RANDOM_STATE, stratify=y
    )

    model = train_model(X_train, y_train, X_test, y_test)
    base = score(model, X_test, y_test)
    print("baseline:", {k: round(v, 4) for k, v in base.items() if isinstance(v, float)})

    test_df = X_test.copy()
    test_df[TARGET] = y_test
    test_df[PROTECTED] = g_test.to_numpy()

    cur_df = simulate_drift(test_df)
    cur_X = feature_frame(cur_df)
    cur_y = cur_df[TARGET].to_numpy()
    drifted = score(model, cur_X, cur_y)
    print("drifted :", {k: round(v, 4) for k, v in drifted.items() if isinstance(v, float)})
    print("class share test:", float(y_test.mean()), "-> current:", float(cur_y.mean()))

    fair_base = fairness(y_test, base["pred"], g_test.reset_index(drop=True))
    fair_drift = fairness(cur_y, drifted["pred"], cur_df[PROTECTED].reset_index(drop=True))
    print("fairness baseline:", json.dumps(fair_base, ensure_ascii=False, indent=1))

    os.makedirs(os.path.join(ROOT, "artifacts", "model"), exist_ok=True)
    model.save_model(os.path.join(ROOT, "artifacts", "model", "catboost_credit_g.cbm"))
    cur_df.to_csv(os.path.join(DATA, "credit_g_drifted.csv"), index=False)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "name": "credit-g (OpenML id 31)",
            "rows": int(len(df)),
            "features": int(X.shape[1]),
            "target": "class (good/bad), positive = bad",
        },
        "baseline": {k: v for k, v in base.items() if k not in ("proba", "pred")},
        "drifted": {k: v for k, v in drifted.items() if k not in ("proba", "pred")},
        "drift": {
            "simulated": {"age_shift_years": 5, "target_share_bad": float(cur_y.mean())},
        },
        "fairness_baseline": fair_base,
        "fairness_drifted": fair_drift,
    }
    with open(os.path.join(ART, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("saved artifacts/metrics.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

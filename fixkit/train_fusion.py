"""
train_fusion.py  —  makes the slide claim TRUE: "Physics + ML fused via a learned meta-learner".

What it does
  1. Temporal holdout: train on years < --test-from, test on years >= --test-from.
  2. XGBoost with MONOTONE constraints (more rain / wetter soil / steeper slope can never
     LOWER risk) -> the What-If slider always behaves physically.
  3. Out-of-fold predictions with spatial-block grouped CV (no spatial leakage).
  4. L2 logistic-regression meta-learner on [ML prob, physics P(fail), I-D exceedance].
  5. Compares 5 systems on the SAME test set, with bootstrap 95% CIs:
        I-D rule alone | physics alone | XGBoost alone | old fixed 0.55/0.45 | learned fusion
  6. Writes fusion_report.json + a markdown table you can paste into the deck.

Usage
  python train_fusion.py --features features.csv --test-from 2019 --out artifacts/
  python train_fusion.py --smoke        # plumbing test on fake data (NOT results)
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from xgboost import XGBClassifier

ML_FEATURES = ["rain_6h", "rain_24h", "rain_48h", "rain_72h", "rain_7d", "max_1h_24h",
               "soil_0_28cm", "slope_deg", "elevation_m"]
MONOTONE = {"rain_6h": 1, "rain_24h": 1, "rain_48h": 1, "rain_72h": 1, "rain_7d": 1,
            "max_1h_24h": 1, "soil_0_28cm": 1, "slope_deg": 1, "elevation_m": 0}
EPS = 1e-4


def logit(p):
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def meta_X(ml_prob, p_phys, id_ratio):
    return np.column_stack([logit(ml_prob), logit(p_phys), np.log1p(np.asarray(id_ratio, float))])


def make_xgb(y):
    pos = max(1, int(y.sum())); neg = max(1, int(len(y) - y.sum()))
    return XGBClassifier(
        n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
        min_child_weight=3, reg_lambda=2.0, scale_pos_weight=neg / pos,
        monotone_constraints="(" + ",".join(str(MONOTONE[f]) for f in ML_FEATURES) + ")",
        eval_metric="logloss", random_state=42, n_jobs=4)


def spatial_block(df, size_deg=0.2):
    return (np.floor(df.lat / size_deg)).astype(int).astype(str) + "_" + (np.floor(df.lon / size_deg)).astype(int).astype(str)


def boot_ci(y, s, fn, n=1000, seed=0):
    rng = np.random.default_rng(seed); vals = []
    idx = np.arange(len(y))
    for _ in range(n):
        b = rng.choice(idx, len(idx), replace=True)
        if y[b].min() == y[b].max():
            continue
        vals.append(fn(y[b], s[b]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def binary_stats(y, yhat):
    tp = int(((yhat == 1) & (y == 1)).sum()); fp = int(((yhat == 1) & (y == 0)).sum())
    fn = int(((yhat == 0) & (y == 1)).sum()); tn = int(((yhat == 0) & (y == 0)).sum())
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "recall": round(tp / max(1, tp + fn), 3),
            "precision": round(tp / max(1, tp + fp), 3),
            "false_positive_rate": round(fp / max(1, fp + tn), 3)}


def threshold_for_recall(y, s, target=0.8):
    """Pick the HIGHEST threshold that still reaches the target recall on TRAIN (OOF) data."""
    pos = np.sort(s[y == 1])[::-1]
    k = int(np.ceil(target * len(pos))) - 1
    return float(pos[max(0, min(k, len(pos) - 1))])


def evaluate(name, y, score, thr=None) -> Dict:
    r = {"system": name, "n_test": int(len(y)), "n_pos": int(y.sum())}
    r["roc_auc"] = round(roc_auc_score(y, score), 3)
    r["roc_auc_95ci"] = [round(v, 3) for v in boot_ci(y, score, roc_auc_score)]
    r["pr_auc"] = round(average_precision_score(y, score), 3)
    r["pr_auc_95ci"] = [round(v, 3) for v in boot_ci(y, score, average_precision_score)]
    if score.min() >= 0 and score.max() <= 1:
        r["brier"] = round(brier_score_loss(y, score), 3)
    if thr is not None:
        r["threshold"] = round(thr, 4)
        r.update(binary_stats(y, (score >= thr).astype(int)))
    return r


def run(df: pd.DataFrame, test_from: int, out: str, target_recall: float = 0.8):
    os.makedirs(out, exist_ok=True)
    df = df.dropna(subset=ML_FEATURES + ["p_failure_phys", "id_ratio", "label"]).reset_index(drop=True)
    tr, te = df[df.year < test_from].reset_index(drop=True), df[df.year >= test_from].reset_index(drop=True)
    if tr.label.sum() < 15 or te.label.sum() < 5:
        raise SystemExit(f"Too few positives (train {tr.label.sum()}, test {te.label.sum()}). "
                         "Add events (use --region ner) or move --test-from.")
    Xtr, ytr = tr[ML_FEATURES].values, tr.label.values.astype(int)
    Xte, yte = te[ML_FEATURES].values, te.label.values.astype(int)

    # 1) OOF ML predictions on train with spatial-block groups
    groups = spatial_block(tr)
    n_splits = int(min(5, groups.nunique(), ytr.sum()))
    oof = np.zeros(len(tr))
    for f_tr, f_va in StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=42).split(Xtr, ytr, groups):
        m = make_xgb(ytr[f_tr]).fit(Xtr[f_tr], ytr[f_tr])
        oof[f_va] = m.predict_proba(Xtr[f_va])[:, 1]

    # 2) Meta-learner on OOF
    meta = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000)  # default = L2
    meta.fit(meta_X(oof, tr.p_failure_phys, tr.id_ratio), ytr)
    meta_oof = meta.predict_proba(meta_X(oof, tr.p_failure_phys, tr.id_ratio))[:, 1]

    # 3) Final ML on all train -> test
    ml = make_xgb(ytr).fit(Xtr, ytr)
    p_ml = ml.predict_proba(Xte)[:, 1]
    p_meta = meta.predict_proba(meta_X(p_ml, te.p_failure_phys, te.id_ratio))[:, 1]
    p_old = 0.55 * p_ml + 0.45 * te.p_failure_phys.values

    # thresholds chosen on TRAIN only (no peeking at test)
    thr = {
        "ml": threshold_for_recall(ytr, oof, target_recall),
        "phys": threshold_for_recall(ytr, tr.p_failure_phys.values, target_recall),
        "old": threshold_for_recall(ytr, 0.55 * oof + 0.45 * tr.p_failure_phys.values, target_recall),
        "meta": threshold_for_recall(ytr, meta_oof, target_recall),
    }
    rows = [
        evaluate("I-D threshold rule (published, ratio>=1)", yte, te.id_ratio.values, 1.0),
        evaluate("Physics FoS alone", yte, te.p_failure_phys.values, thr["phys"]),
        evaluate("XGBoost alone (monotone)", yte, p_ml, thr["ml"]),
        evaluate("Old fixed blend 0.55*ML + 0.45*physics", yte, p_old, thr["old"]),
        evaluate("Learned meta-learner (L2 logistic stacking)", yte, p_meta, thr["meta"]),
    ]

    coef = dict(zip(["ML_logit", "physics_logit", "log1p_ID_ratio"], np.round(meta.coef_[0], 3).tolist()))
    report = {
        "train_years": f"< {test_from}", "test_years": f">= {test_from}",
        "n_train": int(len(tr)), "n_train_pos": int(ytr.sum()),
        "n_test": int(len(te)), "n_test_pos": int(yte.sum()),
        "negatives": "case-crossover: same-place/other-date + same-date/other-place",
        "target_recall_on_train": target_recall,
        "meta_learner_coefficients": coef, "meta_learner_intercept": round(float(meta.intercept_[0]), 3),
        "results": rows,
        "feature_importance_ml": dict(zip(ML_FEATURES, np.round(ml.feature_importances_, 3).tolist())),
    }
    joblib.dump(ml, os.path.join(out, "xgb_monotone.joblib"))
    joblib.dump(meta, os.path.join(out, "meta_learner.joblib"))
    json.dump(report, open(os.path.join(out, "fusion_report.json"), "w"), indent=2)

    md = ["| System | ROC-AUC (95% CI) | PR-AUC | Recall | Precision | FPR |", "|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['system']} | {r['roc_auc']} ({r['roc_auc_95ci'][0]}-{r['roc_auc_95ci'][1]}) | "
                  f"{r['pr_auc']} | {r.get('recall','-')} | {r.get('precision','-')} | {r.get('false_positive_rate','-')} |")
    open(os.path.join(out, "fusion_table.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))
    print("\nMeta-learner weights (show these in the explainability panel):", coef)
    return report


def smoke_data(n_events=120, seed=1) -> pd.DataFrame:
    """FAKE data with a known rain signal, only to prove the code runs end-to-end."""
    rng = np.random.default_rng(seed); rows = []
    for i in range(n_events):
        year = 2010 + i % 12; lat = rng.uniform(27.1, 27.9); lon = rng.uniform(88.2, 88.8)
        slope = rng.uniform(20, 45)
        for lab, typ in [(1, ""), (0, "temporal"), (0, "temporal"), (0, "spatial")]:
            r24 = rng.gamma(4, 18) if lab else rng.gamma(2, 12)
            rows.append(dict(label=lab, neg_type=typ, year=year, lat=lat if typ != "spatial" else rng.uniform(27.1, 27.9),
                             lon=lon, rain_6h=r24 * 0.3, rain_24h=r24, rain_48h=r24 * 1.6, rain_72h=r24 * 2.0,
                             rain_7d=r24 * 3 + rng.uniform(0, 80), max_1h_24h=r24 / 6, soil_0_28cm=0.25 + min(r24, 150) / 900,
                             slope_deg=slope if typ != "spatial" else rng.uniform(15, 45), elevation_m=rng.uniform(400, 2500),
                             id_ratio=r24 / 43.26, p_failure_phys=float(np.clip(r24 / 250 + slope / 150 - 0.2, 0, 1))))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default="features.csv")
    ap.add_argument("--test-from", type=int, default=2019)
    ap.add_argument("--out", default="artifacts")
    ap.add_argument("--target-recall", type=float, default=0.8)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        print("=" * 70 + "\n SMOKE TEST ON FAKE DATA — checks plumbing only, NOT real results\n" + "=" * 70)
        run(smoke_data(), test_from=2019, out=a.out + "_smoke", target_recall=a.target_recall)
    else:
        run(pd.read_csv(a.features), a.test_from, a.out, a.target_recall)

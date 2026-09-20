"""
Model Integrity & Machine Learning Serialization Tests
SIH PS 26001 - Production Build
"""

import sys
import os
import json
import joblib
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import DATA_DIR, MODELS_DIR, MODEL_META_PATH, METRICS_PATH
from ml_pipeline.train_and_validate import FEATURE_COLUMNS


def test_model_files_exist():
    xgb_path = os.path.join(MODELS_DIR, "xgb_model.joblib")
    rf_path = os.path.join(MODELS_DIR, "rf_model.joblib")
    assert os.path.exists(xgb_path), f"XGBoost model artifact missing at {xgb_path}"
    assert os.path.exists(rf_path), f"Random Forest model artifact missing at {rf_path}"


def test_model_deserialization():
    xgb_path = os.path.join(MODELS_DIR, "xgb_model.joblib")
    rf_path = os.path.join(MODELS_DIR, "rf_model.joblib")
    
    xgb_model = joblib.load(xgb_path)
    rf_model = joblib.load(rf_path)
    
    assert hasattr(xgb_model, "predict_proba"), "XGBoost model must have predict_proba"
    assert hasattr(rf_model, "predict_proba"), "Random Forest model must have predict_proba"
    assert hasattr(xgb_model, "feature_importances_"), "XGBoost model must have feature_importances_"


def test_feature_order_and_prediction():
    xgb_path = os.path.join(MODELS_DIR, "xgb_model.joblib")
    xgb_model = joblib.load(xgb_path)
    
    with open(MODEL_META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["features"] == FEATURE_COLUMNS, "Feature column ordering mismatch"

    # Sample input test (10 features)
    dummy_input = np.array([[35.0, 110.0, 160.0, 240.0, 0.42, 0.38, 0.35, 38.0, 1650.0, 1.0]])
    probs = xgb_model.predict_proba(dummy_input)
    
    assert probs.shape == (1, 2), f"Expected shape (1, 2), got {probs.shape}"
    prob_class1 = probs[0, 1]
    assert 0.0 <= prob_class1 <= 1.0, f"Probability {prob_class1} out of bounds [0, 1]"


def test_metrics_json_integrity():
    assert os.path.exists(METRICS_PATH), f"metrics.json missing at {METRICS_PATH}"
    
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # Validate metrics structure & ranges
    assert "metrics" in metrics
    m = metrics["metrics"]
    assert 0.0 <= m["precision_pct"] <= 100.0
    assert 0.0 <= m["recall_pct"] <= 100.0
    assert 0.0 <= m["f1_score_pct"] <= 100.0
    assert 0.0 <= m["roc_auc"] <= 1.0

    # Validate confusion matrix
    assert "confusion_matrix" in metrics
    cm = metrics["confusion_matrix"]
    assert all(k in cm for k in ["tp", "fp", "fn", "tn"])
    assert (cm["tp"] + cm["fp"] + cm["fn"] + cm["tn"]) == metrics["total_test_samples"]

    # Validate ROC points
    assert "roc_curve_samples" in metrics
    for pt in metrics["roc_curve_samples"]:
        assert 0.0 <= pt["false_positive_rate"] <= 1.0
        assert 0.0 <= pt["true_positive_rate"] <= 1.0

    # Validate Feature Importances sum to approximately 1.0
    assert "feature_importance_ranking" in metrics
    total_imp = sum(f["importance"] for f in metrics["feature_importance_ranking"])
    assert 0.95 <= total_imp <= 1.05, f"Feature importances sum {total_imp} deviates from 1.0"


if __name__ == "__main__":
    print("Running Model Integrity Tests...")
    test_model_files_exist()
    print("[PASS] Model Files Exist (XGBoost & Random Forest)")
    test_model_deserialization()
    print("[PASS] Model Deserialization & predict_proba Verification")
    test_feature_order_and_prediction()
    print("[PASS] Feature Ordering & Prediction Range [0, 1]")
    test_metrics_json_integrity()
    print("[PASS] Metrics JSON Schema, Confusion Matrix & ROC Curve Range")
    print("\nALL MODEL INTEGRITY TESTS PASSED SUCCESSFULLY! :)")

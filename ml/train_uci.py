#!/usr/bin/env python3
"""Reproducible, group-disjoint UCI Diabetes readmission research benchmark.

Dataset is separate from CareFlow case data. Never use this model for patient care,
clinical decision support, or inference on MIMIC/Synthea records without validation.
Usage: python ml/train_uci.py --csv ml/data/diabetic_data.csv --out ml/output
"""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, f1_score, roc_auc_score, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FEATURES = ["race", "gender", "age", "admission_type_id", "time_in_hospital", "num_lab_procedures",
            "num_procedures", "num_medications", "number_outpatient", "number_emergency", "number_inpatient",
            "number_diagnoses", "A1Cresult", "max_glu_serum", "change", "diabetesMed"]
CATEGORICAL = ["race", "gender", "age", "admission_type_id", "A1Cresult", "max_glu_serum", "change", "diabetesMed"]
NUMERIC = [f for f in FEATURES if f not in CATEGORICAL]


def load(path: Path):
    data = pd.read_csv(path, na_values=['?'], low_memory=False)
    needed = FEATURES + ["readmitted", "patient_nbr"]
    missing = [c for c in needed if c not in data]
    if missing:
        raise ValueError(f"Dataset missing expected UCI columns: {missing}")
    # Label >30 and NO are negative for the specified 30-day readmission task.
    x = data[FEATURES].copy()
    y = data["readmitted"].eq("<30").astype(int)
    groups = data["patient_nbr"].astype(str)
    if len(y.unique()) < 2:
        raise ValueError("Both positive and negative readmission labels required")
    return x, y, groups


def preprocessing():
    categorical = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                            ("encoder", OneHotEncoder(handle_unknown="ignore"))])
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    return ColumnTransformer([("cat", categorical, CATEGORICAL), ("num", numeric, NUMERIC)])


def split_grouped(x, y, group, seed=42):
    outer = GroupShuffleSplit(test_size=.2, n_splits=1, random_state=seed)
    tr, te = next(outer.split(x, y, groups=group))
    inner = GroupShuffleSplit(test_size=.2, n_splits=1, random_state=seed+1)
    tr_rel, va_rel = next(inner.split(x.iloc[tr], y.iloc[tr], groups=group.iloc[tr]))
    train, val = tr[tr_rel], tr[va_rel]
    assert not (set(group.iloc[train]) & set(group.iloc[val]))
    assert not (set(group.iloc[train]) & set(group.iloc[te]))
    assert not (set(group.iloc[val]) & set(group.iloc[te]))
    return train, val, te


def scores(y, probabilities, threshold):
    labels = (probabilities >= threshold).astype(int)
    result = {"n": int(len(y)), "positive_rate": round(float(np.mean(y)), 6),
              "pr_auc": round(float(average_precision_score(y, probabilities)), 6),
              "roc_auc": round(float(roc_auc_score(y, probabilities)), 6) if len(np.unique(y)) == 2 else None,
              "brier": round(float(brier_score_loss(y, probabilities)), 6),
              "precision": round(float(precision_score(y, labels, zero_division=0)), 6),
              "recall": round(float(recall_score(y, labels, zero_division=0)), 6),
              "f1": round(float(f1_score(y, labels, zero_division=0)), 6),
              "confusion_matrix": confusion_matrix(y, labels, labels=[0, 1]).tolist()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path('ml/output'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    x, y, groups = load(args.csv)
    train, val, test = split_grouped(x, y, groups)
    models = {"logistic_regression": LogisticRegression(max_iter=750, class_weight="balanced", random_state=42),
              "random_forest": RandomForestClassifier(n_estimators=120, max_depth=12, min_samples_leaf=5,
                                                       n_jobs=-1, class_weight="balanced_subsample", random_state=42)}
    results = {}
    best = None
    best_score = -1
    for name, model in models.items():
        pipeline = Pipeline([("preprocess", preprocessing()), ("classifier", model)])
        pipeline.fit(x.iloc[train], y.iloc[train])
        validation_prob = pipeline.predict_proba(x.iloc[val])[:,1]
        # Tune threshold only on the validation set; do NOT optimize on held-out test.
        choices = np.arange(.1, .91, .05)
        threshold = float(max(choices, key=lambda t: f1_score(y.iloc[val], validation_prob >= t, zero_division=0)))
        test_prob = pipeline.predict_proba(x.iloc[test])[:,1]
        result = {"validation": scores(y.iloc[val], validation_prob, threshold),
                  "held_out_test": scores(y.iloc[test], test_prob, threshold), "threshold": round(threshold, 4)}
        results[name] = result
        validation_ap = result["validation"]["pr_auc"]
        if validation_ap > best_score:
            best, best_score = (name, pipeline), validation_ap
    artifact = {"dataset": "UCI Diabetes 130-US Hospitals (1999-2008)",
                "citation": "https://doi.org/10.24432/C5230J", "task": "readmission within 30 days",
                "dataset_scope": "historical research only; no clinical validation",
                "split": "disjoint patient_nbr, train/validation/test", "seed": 42,
                "samples": {"train": len(train), "validation": len(val), "test": len(test)},
                "selected_by": "highest validation PR-AUC", "selected_model": best[0], "models": results}
    (args.out/'metrics.json').write_text(json.dumps(artifact, indent=2), encoding='utf8')
    joblib.dump(best[1], args.out/'historical_readmission_research.joblib')
    print(json.dumps({"selected_model": best[0], "metrics": results[best[0]]["held_out_test"]}, indent=2))


if __name__=='__main__':
    main()

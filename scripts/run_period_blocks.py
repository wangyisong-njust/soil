#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import RESULTS_DIR, TABLES_DIR, ensure_project_dirs


DEFAULT_MODELS = [
    "RF",
    "ExtraTrees",
    "HistGBR",
    "ElasticNet",
    "PLSR",
    "XGBoost",
    "LightGBM",
    "CatBoost",
    "NGBoost",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run rolling period-block validation for 2000-2008, 2009-2017, 2018-2026.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Override cleaned CSV path.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for supported estimators.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated model names.")
    return parser.parse_args()


def period_name(year: int) -> str:
    if 2000 <= year <= 2008:
        return "P1_2000_2008"
    if 2009 <= year <= 2017:
        return "P2_2009_2017"
    if 2018 <= year <= 2026:
        return "P3_2018_2026"
    return "outside"


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = ROOT / (args.data or config["processed_csv"])
    raw = pd.read_csv(data_path)
    df, base_feature_cols = add_engineered_features(raw, config["base_feature_columns"])
    df["period_block"] = df["year"].map(period_name)
    model_feature_cols = base_feature_cols + (
        TARGET_SPATIAL_FEATURES if config.get("use_target_spatial_lag_features", False) else []
    )

    registry = build_model_registry(len(model_feature_cols), random_state=config["random_seed"], n_jobs=args.n_jobs)
    requested = [m.strip() for m in args.models.split(",") if m.strip()]
    registry = {name: registry[name] for name in requested if name in registry}
    if not registry:
        raise SystemExit("No requested models are available.")

    folds = [
        {
            "fold": "P1_to_P2",
            "train_start": 2000,
            "train_end": 2008,
            "test_start": 2009,
            "test_end": 2017,
        },
        {
            "fold": "P1P2_to_P3",
            "train_start": 2000,
            "train_end": 2017,
            "test_start": 2018,
            "test_end": 2026,
        },
    ]

    rows: list[dict[str, object]] = []
    predictions: list[pd.DataFrame] = []
    x_base = df[base_feature_cols].astype(float)

    for fold in folds:
        train_idx = df.index[(df["year"] >= fold["train_start"]) & (df["year"] <= fold["train_end"])].to_numpy()
        test_idx = df.index[(df["year"] >= fold["test_start"]) & (df["year"] <= fold["test_end"])].to_numpy()
        print(f"\n=== {fold['fold']} train={len(train_idx)} test={len(test_idx)} ===", flush=True)
        for target in config["target_columns"]:
            y = df[target].astype(float)
            if config.get("use_target_spatial_lag_features", False):
                k = int(config.get("target_spatial_lag_k", 12))
                x_train = add_target_spatial_lag_features(df, x_base, y, train_idx, train_idx, k=k, leave_one_out=True)
                x_test = add_target_spatial_lag_features(df, x_base, y, train_idx, test_idx, k=k, leave_one_out=False)
            else:
                x_train = x_base.loc[train_idx]
                x_test = x_base.loc[test_idx]

            pred_table = df.loc[test_idx, ["lon", "lat", "year", "period_block"]].copy()
            pred_table.insert(0, "row_id", test_idx)
            pred_table["fold"] = fold["fold"]
            pred_table["target"] = target
            pred_table["observed"] = y.loc[test_idx].to_numpy()

            for name, spec in registry.items():
                try:
                    model = fresh_model(spec)
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model.fit(x_train, y.loc[train_idx])
                        pred = np.asarray(model.predict(x_test), dtype=float).reshape(-1)
                    pred = np.maximum(pred, 0)
                    metric = regression_metrics(y.loc[test_idx], pred)
                    rows.append(
                        {
                            "fold": fold["fold"],
                            "target": target,
                            "model": name,
                            "family": spec.family,
                            "status": "ok",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "train_year_min": int(fold["train_start"]),
                            "train_year_max": int(fold["train_end"]),
                            "test_year_min": int(fold["test_start"]),
                            "test_year_max": int(fold["test_end"]),
                            **metric,
                        }
                    )
                    pred_table[f"pred_{name}"] = pred
                except Exception as exc:
                    rows.append(
                        {
                            "fold": fold["fold"],
                            "target": target,
                            "model": name,
                            "family": spec.family,
                            "status": f"failed: {exc}",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "train_year_min": int(fold["train_start"]),
                            "train_year_max": int(fold["train_end"]),
                            "test_year_min": int(fold["test_start"]),
                            "test_year_max": int(fold["test_end"]),
                            "r2": np.nan,
                            "r2_log1p": np.nan,
                            "rmse": np.nan,
                            "mae": np.nan,
                            "mape": np.nan,
                        }
                    )
            predictions.append(pred_table)

    metrics = pd.DataFrame(rows)
    metrics_path = TABLES_DIR / "period_block_metrics.csv"
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig")

    pred_path = RESULTS_DIR / "period_block_predictions.csv"
    pd.concat(predictions, ignore_index=True).to_csv(pred_path, index=False, encoding="utf-8-sig")

    summary = (
        metrics[metrics["status"] == "ok"]
        .sort_values(["fold", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["fold", "target"], as_index=False)
        .head(1)
    )
    summary_path = TABLES_DIR / "period_block_best_metrics.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    meta = {"folds": folds, "models": list(registry.keys())}
    (TABLES_DIR / "period_block_setup.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nWrote {metrics_path.relative_to(ROOT)}")
    print(f"Wrote {summary_path.relative_to(ROOT)}")
    print(f"Wrote {pred_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()


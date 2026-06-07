#!/usr/bin/env python
from __future__ import annotations

import argparse
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
from soilmodel.paths import TABLES_DIR, ensure_project_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute apparent training-fit metrics for model capacity diagnostics.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Override cleaned CSV path.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for supported estimators.")
    parser.add_argument("--models", default=None, help="Comma-separated model names. Default uses all available.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = ROOT / (args.data or config["processed_csv"])
    df_raw = pd.read_csv(data_path)
    df, base_feature_cols = add_engineered_features(df_raw, config["base_feature_columns"])
    model_feature_cols = base_feature_cols + (
        TARGET_SPATIAL_FEATURES if config.get("use_target_spatial_lag_features", False) else []
    )
    registry = build_model_registry(len(model_feature_cols), random_state=config["random_seed"], n_jobs=args.n_jobs)
    if args.models:
        requested = [m.strip() for m in args.models.split(",") if m.strip()]
        registry = {name: registry[name] for name in requested if name in registry}

    rows: list[dict[str, object]] = []
    all_idx = df.index.to_numpy()
    x_base = df[base_feature_cols].astype(float)

    for target in config["target_columns"]:
        y = df[target].astype(float)
        if config.get("use_target_spatial_lag_features", False):
            x_all = add_target_spatial_lag_features(
                df,
                x_base,
                y,
                all_idx,
                all_idx,
                k=int(config.get("target_spatial_lag_k", 12)),
                leave_one_out=True,
            )
        else:
            x_all = x_base.copy()

        print(f"\n=== Training fit {target} ===", flush=True)
        for name, spec in registry.items():
            try:
                model = fresh_model(spec)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model.fit(x_all, y)
                    pred = np.asarray(model.predict(x_all), dtype=float).reshape(-1)
                pred = np.maximum(pred, 0)
                metric = regression_metrics(y, pred)
                row = {
                    "target": target,
                    "model": name,
                    "family": spec.family,
                    "split": "apparent_training_fit",
                    "status": "ok",
                    "n_samples": int(len(df)),
                    "note": "训练拟合度，不作为外推验证指标。",
                    **metric,
                }
                rows.append(row)
                print(f"  {name:<15} R2={metric['r2']:.3f} logR2={metric['r2_log1p']:.3f}", flush=True)
            except Exception as exc:
                rows.append(
                    {
                        "target": target,
                        "model": name,
                        "family": spec.family,
                        "split": "apparent_training_fit",
                        "status": f"failed: {exc}",
                        "n_samples": int(len(df)),
                        "note": "训练拟合度，不作为外推验证指标。",
                        "r2": np.nan,
                        "r2_log1p": np.nan,
                        "rmse": np.nan,
                        "mae": np.nan,
                        "mape": np.nan,
                    }
                )

    output_path = TABLES_DIR / "training_fit_metrics.csv"
    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\nWrote {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()


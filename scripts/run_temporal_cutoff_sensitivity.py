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

from soilmodel.config import load_config, target_columns
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


EXTERNAL_PREFIXES = ("sg_", "np_", "osm_", "viirs_", "ghsl_", "wc_", "dem_", "terr_", "geo_")
DEFAULT_MODELS = ["ExtraTrees", "HistGBR", "ElasticNet", "XGBoost", "LightGBM", "CatBoost"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare temporal test-start cutoffs without overwriting main metrics.")
    parser.add_argument("--config", default="configs/soil_experiment.json")
    parser.add_argument("--data", default=None, help="CSV path. Default uses the richest available processed data.")
    parser.add_argument("--cutoffs", default="2019,2020,2021,2022,2023,2024")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--feature-set", choices=["base", "external"], default="external")
    parser.add_argument("--n-jobs", type=int, default=2)
    return parser.parse_args()


def normalize_prediction(pred) -> np.ndarray:
    arr = np.asarray(pred, dtype=float)
    if arr.ndim > 1:
        arr = arr.reshape(arr.shape[0], -1)[:, 0]
    return np.maximum(arr, 0.0)


def fit_predict(spec, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
    return normalize_prediction(pred)


def feature_columns(df: pd.DataFrame, config: dict[str, object], feature_set: str) -> list[str]:
    base = [str(col) for col in config["base_feature_columns"]]
    if feature_set == "base":
        return base
    external = [col for col in df.columns if col.startswith(EXTERNAL_PREFIXES)]
    return list(dict.fromkeys(base + external))


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = ROOT / args.data if args.data else preferred_processed_data_path()
    df_raw = pd.read_csv(data_path)
    df_raw["year"] = df_raw["year"].round().astype(int)
    df_raw = df_raw.reset_index(drop=True)

    targets = target_columns(config)
    cutoffs = [int(item.strip()) for item in args.cutoffs.split(",") if item.strip()]
    requested_models = [item.strip() for item in args.models.split(",") if item.strip()]
    use_lag = bool(config.get("use_target_spatial_lag_features", False))
    lag_k = int(config.get("target_spatial_lag_k", 12))

    df, engineered_cols = add_engineered_features(df_raw, feature_columns(df_raw, config, args.feature_set))
    model_feature_count = len(engineered_cols) + (len(TARGET_SPATIAL_FEATURES) if use_lag else 0)
    registry = build_model_registry(model_feature_count, random_state=int(config["random_seed"]), n_jobs=args.n_jobs)
    registry = {name: registry[name] for name in requested_models if name in registry}
    x_base = df[engineered_cols].astype(float)

    rows: list[dict[str, object]] = []
    for cutoff in cutoffs:
        train_idx = df.index[df["year"] < cutoff].to_numpy()
        test_idx = df.index[df["year"] >= cutoff].to_numpy()
        if len(train_idx) < 50 or len(test_idx) < 10:
            continue
        print(f"cutoff={cutoff}: train={len(train_idx)} test={len(test_idx)} features={model_feature_count}", flush=True)
        for target in targets:
            y = df[target].astype(float)
            if use_lag:
                x_train = add_target_spatial_lag_features(df, x_base, y, train_idx, train_idx, k=lag_k, leave_one_out=True)
                x_test = add_target_spatial_lag_features(df, x_base, y, train_idx, test_idx, k=lag_k, leave_one_out=False)
            else:
                x_train = x_base.loc[train_idx]
                x_test = x_base.loc[test_idx]
            y_train = y.loc[train_idx]
            y_test = y.loc[test_idx]
            for model_name, spec in registry.items():
                try:
                    pred = fit_predict(spec, x_train, y_train, x_test)
                    metric = regression_metrics(y_test, pred)
                    rows.append(
                        {
                            "cutoff_year": cutoff,
                            "feature_set": args.feature_set,
                            "target": target,
                            "model": model_name,
                            "status": "ok",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "test_year_min": int(df.loc[test_idx, "year"].min()),
                            "test_year_max": int(df.loc[test_idx, "year"].max()),
                            "n_features": int(model_feature_count),
                            **metric,
                        }
                    )
                except Exception as exc:
                    rows.append(
                        {
                            "cutoff_year": cutoff,
                            "feature_set": args.feature_set,
                            "target": target,
                            "model": model_name,
                            "status": f"failed: {exc}",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "test_year_min": int(df.loc[test_idx, "year"].min()),
                            "test_year_max": int(df.loc[test_idx, "year"].max()),
                            "n_features": int(model_feature_count),
                            "r2": np.nan,
                            "r2_log1p": np.nan,
                            "rmse": np.nan,
                            "mae": np.nan,
                            "mape": np.nan,
                        }
                    )

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "temporal_cutoff_sensitivity_metrics.csv", index=False, encoding="utf-8-sig")
    best = (
        metrics[metrics["status"].eq("ok")]
        .dropna(subset=["r2"])
        .sort_values(["cutoff_year", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["cutoff_year", "target"], as_index=False)
        .head(1)
        .sort_values(["cutoff_year", "target"])
    )
    best.to_csv(TABLES_DIR / "temporal_cutoff_sensitivity_best_by_target.csv", index=False, encoding="utf-8-sig")
    summary = (
        best.groupby("cutoff_year")
        .agg(
            n_test=("n_test", "first"),
            mean_r2=("r2", "mean"),
            median_r2=("r2", "median"),
            min_r2=("r2", "min"),
            positive_targets=("r2", lambda s: int((s > 0).sum())),
        )
        .reset_index()
    )
    summary.to_csv(TABLES_DIR / "temporal_cutoff_sensitivity_summary.csv", index=False, encoding="utf-8-sig")
    print("Wrote temporal cutoff sensitivity outputs")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import FIGURES_DIR, MODELS_DIR, RESULTS_DIR, ensure_project_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict future heavy-metal concentrations under a baseline scenario.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Override cleaned CSV path.")
    parser.add_argument(
        "--years",
        default="2027,2028,2029,2030,2031,2032,2033,2034,2035",
        help="Comma-separated future years.",
    )
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for supported estimators.")
    return parser.parse_args()


def choose_models(metrics: pd.DataFrame, targets: list[str], primary_protocol: str) -> dict[str, str]:
    chosen: dict[str, str] = {}
    ok = metrics[(metrics["status"] == "ok") & (metrics["split"] == "test") & (metrics["protocol"] == primary_protocol)]
    for target in targets:
        part = ok[(ok["target"] == target) & (ok["model"] != "WeightedEnsemble")]
        if len(part) == 0:
            continue
        best = part.sort_values(["r2", "rmse"], ascending=[False, True]).iloc[0]
        chosen[target] = str(best["model"])
    return chosen


def make_future_frame(df: pd.DataFrame, base_features: list[str], years: list[int]) -> pd.DataFrame:
    work = df.copy()
    work["lon_round"] = work["lon"].round(6)
    work["lat_round"] = work["lat"].round(6)
    latest = work.sort_values(["lon_round", "lat_round", "year"]).groupby(["lon_round", "lat_round"], as_index=False).tail(1)
    rows = []
    driver_features = [c for c in base_features if c not in ["lon", "lat", "year"]]
    for year in years:
        part = latest[["lon", "lat"] + driver_features].copy()
        part["year"] = year
        part["scenario"] = "baseline_constant_drivers"
        part["source_year"] = latest["year"].to_numpy()
        rows.append(part)
    future = pd.concat(rows, ignore_index=True)
    future.index = np.arange(1_000_000, 1_000_000 + len(future))
    return future


def save_future_map(part: pd.DataFrame, target: str, year: int, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.8, 4.8))
    sc = ax.scatter(part["lon"], part["lat"], c=part["predicted"], s=20, cmap="viridis", alpha=0.86)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("Predicted concentration")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"{target} baseline prediction ({year})")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = ROOT / (args.data or config["processed_csv"])
    metrics_path = ROOT / "tables" / "model_metrics.csv"
    if not metrics_path.exists():
        raise SystemExit("Missing tables/model_metrics.csv. Run scripts/run_experiment.py first.")

    df = pd.read_csv(data_path)
    targets = config["target_columns"]
    years = [int(y.strip()) for y in args.years.split(",") if y.strip()]
    metrics = pd.read_csv(metrics_path)
    chosen = choose_models(metrics, targets, config["primary_protocol"])

    future_raw = make_future_frame(df, config["base_feature_columns"], years)
    combined = pd.concat([df, future_raw.drop(columns=["scenario", "source_year"])], axis=0, sort=False)
    combined, base_feature_cols = add_engineered_features(combined, config["base_feature_columns"])
    model_feature_cols = base_feature_cols + (
        TARGET_SPATIAL_FEATURES if config.get("use_target_spatial_lag_features", False) else []
    )
    registry = build_model_registry(len(model_feature_cols), random_state=config["random_seed"], n_jobs=args.n_jobs)
    observed_idx = df.index.to_numpy()
    future_idx = future_raw.index.to_numpy()

    rows = []
    for target in targets:
        model_name = chosen.get(target)
        if model_name is None or model_name not in registry:
            print(f"Skip {target}: no validated model available")
            continue
        y = combined.loc[observed_idx, target].astype(float)
        x_base = combined[base_feature_cols].astype(float)
        if config.get("use_target_spatial_lag_features", False):
            k = int(config.get("target_spatial_lag_k", 12))
            x_train = add_target_spatial_lag_features(combined, x_base, y, observed_idx, observed_idx, k=k, leave_one_out=True)
            x_future = add_target_spatial_lag_features(combined, x_base, y, observed_idx, future_idx, k=k, leave_one_out=False)
        else:
            x_train = x_base.loc[observed_idx]
            x_future = x_base.loc[future_idx]

        model = fresh_model(registry[model_name])
        model.fit(x_train, y)
        predicted = np.asarray(model.predict(x_future), dtype=float).reshape(-1)
        out = future_raw[["lon", "lat", "year", "scenario", "source_year"]].copy()
        out["target"] = target
        out["model"] = model_name
        out["predicted"] = predicted
        rows.append(out)
        joblib.dump(
            {
                "target": target,
                "model_name": model_name,
                "feature_columns": model_feature_cols,
                "scenario": "baseline_constant_drivers",
                "model": model,
            },
            MODELS_DIR / f"{target}_future_baseline_{model_name}.joblib",
        )

    future_predictions = pd.concat(rows, ignore_index=True)
    output_path = RESULTS_DIR / f"future_predictions_baseline_{min(years)}_{max(years)}.csv"
    future_predictions.to_csv(output_path, index=False, encoding="utf-8-sig")

    for target in targets:
        target_dir = FIGURES_DIR / target
        target_dir.mkdir(parents=True, exist_ok=True)
        for year in years:
            part = future_predictions[(future_predictions["target"] == target) & (future_predictions["year"] == year)]
            if len(part):
                save_future_map(part, target, year, target_dir / f"{target}_future_{year}_baseline_map.png")

    print(f"Wrote {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import warnings
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import (
    TARGET_SPATIAL_FEATURES,
    add_engineered_features,
    add_target_spatial_lag_features,
    dataset_profile,
)
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import FIGURES_DIR, MODELS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs
from soilmodel.plots import (
    save_actual_vs_predicted,
    save_feature_importance,
    save_metric_comparison,
    save_residual_plot,
    save_shap_importance,
)
from soilmodel.validation import make_internal_validation_split, make_protocol_split


TREE_MODEL_ORDER = ["CatBoost", "XGBoost", "LightGBM", "ExtraTrees", "RF", "HistGBR"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-model soil heavy-metal prediction experiments.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Override cleaned CSV path.")
    parser.add_argument("--protocols", default="temporal,random", help="Comma-separated protocols: temporal,random.")
    parser.add_argument("--targets", default=None, help="Comma-separated target columns. Default uses config.")
    parser.add_argument("--models", default=None, help="Comma-separated model names. Default uses all available.")
    parser.add_argument("--skip-shap", action="store_true", help="Skip SHAP figures.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for supported estimators.")
    return parser.parse_args()


def normalize_prediction(pred) -> np.ndarray:
    arr = np.asarray(pred, dtype=float)
    if arr.ndim > 1:
        arr = arr.reshape(arr.shape[0], -1)[:, 0]
    return arr


def make_weights(validation_rows: list[dict[str, object]], top_k: int, include_raw_models: bool) -> dict[str, float]:
    usable = [
        row
        for row in validation_rows
        if np.isfinite(float(row["rmse"])) and float(row["rmse"]) > 0 and str(row["status"]) == "ok"
    ]
    if not include_raw_models:
        usable = [row for row in usable if not str(row["model"]).endswith("_raw")]
    usable = sorted(usable, key=lambda r: float(r["rmse"]))[:top_k]
    if not usable:
        return {}
    scores = {}
    for row in usable:
        r2 = max(float(row["r2"]), 0.0)
        scores[str(row["model"])] = (1.0 + r2) / (float(row["rmse"]) + 1e-8)
    total = sum(scores.values())
    return {name: value / total for name, value in scores.items()}


def fit_model(name, spec, x_train, y_train):
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
    return model


def choose_tree_model(metrics_part: pd.DataFrame, fitted_models: dict[str, object]) -> str | None:
    tree_candidates = [name for name in TREE_MODEL_ORDER if name in fitted_models]
    if not tree_candidates:
        return None
    ranked = metrics_part[metrics_part["model"].isin(tree_candidates)].sort_values(["r2", "rmse"], ascending=[False, True])
    if len(ranked):
        return str(ranked.iloc[0]["model"])
    return tree_candidates[0]


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = ROOT / (args.data or config["processed_csv"])
    if not data_path.exists():
        raise SystemExit(f"Cleaned CSV not found: {data_path}. Run scripts/convert_xlsx_to_csv.py first.")

    raw_df = pd.read_csv(data_path)
    targets = args.targets.split(",") if args.targets else config["target_columns"]
    df, base_feature_cols = add_engineered_features(raw_df, config["base_feature_columns"])
    use_spatial_lag = bool(config.get("use_target_spatial_lag_features", False))
    model_feature_cols = base_feature_cols + (TARGET_SPATIAL_FEATURES if use_spatial_lag else [])
    protocols = [p.strip() for p in args.protocols.split(",") if p.strip()]

    registry = build_model_registry(len(model_feature_cols), random_state=config["random_seed"], n_jobs=args.n_jobs)
    if args.models:
        requested = [m.strip() for m in args.models.split(",") if m.strip()]
        registry = {name: registry[name] for name in requested if name in registry}
    if not registry:
        raise SystemExit("No models available.")

    all_metrics: list[dict[str, object]] = []
    validation_metrics: list[dict[str, object]] = []
    ensemble_rows: list[dict[str, object]] = []
    importance_rows: list[pd.DataFrame] = []
    shap_rows: list[pd.DataFrame] = []

    profile = dataset_profile(raw_df, targets)
    profile.update({"feature_columns": model_feature_cols, "models": list(registry.keys()), "protocols": protocols})
    profile["data_cleaning_strategy"] = config.get("data_cleaning_strategy", "basic")
    (TABLES_DIR / "data_profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    for target in targets:
        y = df[target].astype(float)
        x_base = df[base_feature_cols].astype(float)
        target_dir = FIGURES_DIR / target
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n=== Target {target} ===", flush=True)

        for protocol in protocols:
            train_idx, test_idx = make_protocol_split(
                df,
                protocol=protocol,
                random_state=config["random_seed"],
                random_test_size=config["random_test_size"],
                temporal_test_start_year=config["temporal_test_start_year"],
            )
            core_idx, valid_idx = make_internal_validation_split(df, train_idx, protocol, config["random_seed"])
            if use_spatial_lag:
                k = int(config.get("target_spatial_lag_k", 12))
                x_core = add_target_spatial_lag_features(df, x_base, y, core_idx, core_idx, k=k, leave_one_out=True)
                x_valid = add_target_spatial_lag_features(df, x_base, y, core_idx, valid_idx, k=k, leave_one_out=False)
                x_train = add_target_spatial_lag_features(df, x_base, y, train_idx, train_idx, k=k, leave_one_out=True)
                x_test = add_target_spatial_lag_features(df, x_base, y, train_idx, test_idx, k=k, leave_one_out=False)
            else:
                x_core = x_base.loc[core_idx]
                x_valid = x_base.loc[valid_idx]
                x_train = x_base.loc[train_idx]
                x_test = x_base.loc[test_idx]
            y_core = y.loc[core_idx]
            y_valid = y.loc[valid_idx]
            y_train = y.loc[train_idx]
            y_test = y.loc[test_idx]

            fitted_full: dict[str, object] = {}
            test_predictions: dict[str, np.ndarray] = {}
            validation_rows: list[dict[str, object]] = []
            prediction_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
            prediction_table.insert(0, "row_id", test_idx)
            prediction_table["target"] = target
            prediction_table["observed"] = y_test.to_numpy()

            print(f"{protocol}: train={len(train_idx)}, test={len(test_idx)}, features={len(model_feature_cols)}", flush=True)

            for name, spec in registry.items():
                try:
                    valid_model = fit_model(name, spec, x_core, y_core)
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        valid_pred = normalize_prediction(valid_model.predict(x_valid))
                    valid_metric = regression_metrics(y_valid, valid_pred)
                    validation_row = {
                        "target": target,
                        "protocol": protocol,
                        "model": name,
                        "family": spec.family,
                        "split": "internal_validation",
                        "status": "ok",
                        "n_train": int(len(core_idx)),
                        "n_test": int(len(valid_idx)),
                        **valid_metric,
                    }
                    validation_rows.append(validation_row)
                    validation_metrics.append(validation_row)

                    full_model = fit_model(name, spec, x_train, y_train)
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        pred = normalize_prediction(full_model.predict(x_test))
                    metric = regression_metrics(y_test, pred)
                    fitted_full[name] = full_model
                    test_predictions[name] = pred
                    prediction_table[f"pred_{name}"] = pred

                    all_metrics.append(
                        {
                            "target": target,
                            "protocol": protocol,
                            "model": name,
                            "family": spec.family,
                            "split": "test",
                            "status": "ok",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "train_year_min": int(df.loc[train_idx, "year"].min()),
                            "train_year_max": int(df.loc[train_idx, "year"].max()),
                            "test_year_min": int(df.loc[test_idx, "year"].min()),
                            "test_year_max": int(df.loc[test_idx, "year"].max()),
                            **metric,
                        }
                    )
                    print(f"  {name:<10} R2={metric['r2']:.3f} RMSE={metric['rmse']:.4g}", flush=True)
                except Exception as exc:
                    row = {
                        "target": target,
                        "protocol": protocol,
                        "model": name,
                        "split": "test",
                        "status": f"failed: {exc}",
                        "n_train": int(len(train_idx)),
                        "n_test": int(len(test_idx)),
                        "r2": np.nan,
                        "rmse": np.nan,
                        "mae": np.nan,
                        "mape": np.nan,
                    }
                    all_metrics.append(row)
                    print(f"  {name:<10} failed: {exc}", flush=True)

            weights = make_weights(
                validation_rows,
                top_k=int(config["ensemble_top_k"]),
                include_raw_models=bool(config.get("ensemble_include_raw_models", False)),
            )
            if weights:
                ensemble_pred = np.zeros(len(x_test), dtype=float)
                for name, weight in weights.items():
                    ensemble_pred += weight * test_predictions[name]
                    ensemble_rows.append(
                        {
                            "target": target,
                            "protocol": protocol,
                            "model": name,
                            "weight": float(weight),
                        }
                    )
                prediction_table["pred_WeightedEnsemble"] = ensemble_pred
                metric = regression_metrics(y_test, ensemble_pred)
                all_metrics.append(
                    {
                        "target": target,
                        "protocol": protocol,
                        "model": "WeightedEnsemble",
                        "family": "ensemble",
                        "split": "test",
                        "status": "ok",
                        "n_train": int(len(train_idx)),
                        "n_test": int(len(test_idx)),
                        "train_year_min": int(df.loc[train_idx, "year"].min()),
                        "train_year_max": int(df.loc[train_idx, "year"].max()),
                        "test_year_min": int(df.loc[test_idx, "year"].min()),
                        "test_year_max": int(df.loc[test_idx, "year"].max()),
                        **metric,
                    }
                )
                print(f"  WeightedEnsemble R2={metric['r2']:.3f} RMSE={metric['rmse']:.4g}", flush=True)

            pred_path = RESULTS_DIR / f"predictions_{target}_{protocol}.csv"
            prediction_table.to_csv(pred_path, index=False, encoding="utf-8-sig")

            metrics_now = pd.DataFrame(all_metrics)
            save_metric_comparison(metrics_now, target, protocol, target_dir / f"{target}_{protocol}_model_r2.png")

            if protocol == config["primary_protocol"]:
                best_model_name = "WeightedEnsemble" if weights else None
                if best_model_name and f"pred_{best_model_name}" in prediction_table:
                    best_pred = prediction_table[f"pred_{best_model_name}"].to_numpy()
                else:
                    best_row = (
                        metrics_now[(metrics_now["target"] == target) & (metrics_now["protocol"] == protocol)]
                        .sort_values(["r2", "rmse"], ascending=[False, True])
                        .iloc[0]
                    )
                    best_model_name = str(best_row["model"])
                    best_pred = prediction_table[f"pred_{best_model_name}"].to_numpy()

                save_actual_vs_predicted(
                    y_test,
                    best_pred,
                    f"{target} observed vs predicted ({protocol}, {best_model_name})",
                    target_dir / f"{target}_{protocol}_observed_predicted.png",
                )
                save_residual_plot(
                    y_test,
                    best_pred,
                    f"{target} residuals ({protocol}, {best_model_name})",
                    target_dir / f"{target}_{protocol}_residuals.png",
                )

                tree_name = choose_tree_model(
                    metrics_now[(metrics_now["target"] == target) & (metrics_now["protocol"] == protocol)],
                    fitted_full,
                )
                if tree_name:
                    model = fitted_full[tree_name]
                    joblib.dump(
                        {
                            "target": target,
                            "protocol": protocol,
                            "model_name": tree_name,
                            "feature_columns": model_feature_cols,
                            "model": model,
                            "note": "Model trained on the protocol training split for validation-traceable interpretation.",
                        },
                        MODELS_DIR / f"{target}_{protocol}_{tree_name}.joblib",
                    )
                    imp = save_feature_importance(
                        model,
                        x_test,
                        y_test,
                        model_feature_cols,
                        f"{target} important predictors ({tree_name})",
                        target_dir / f"{target}_{protocol}_feature_importance.png",
                        random_state=config["random_seed"],
                    )
                    imp.insert(0, "target", target)
                    imp.insert(1, "protocol", protocol)
                    imp.insert(2, "model", tree_name)
                    importance_rows.append(imp)

                    if not args.skip_shap:
                        try:
                            sample = x_train.sample(
                                n=min(int(config["shap_max_samples"]), len(x_train)),
                                random_state=config["random_seed"],
                            )
                            shap_table = save_shap_importance(
                                model,
                                sample,
                                model_feature_cols,
                                f"{target} SHAP importance ({tree_name})",
                                target_dir / f"{target}_{protocol}_shap_importance.png",
                            )
                            shap_table.insert(0, "target", target)
                            shap_table.insert(1, "protocol", protocol)
                            shap_table.insert(2, "model", tree_name)
                            shap_rows.append(shap_table)
                        except Exception as exc:
                            print(f"  SHAP skipped for {target}/{tree_name}: {exc}", flush=True)

    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.to_csv(TABLES_DIR / "model_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(validation_metrics).to_csv(TABLES_DIR / "internal_validation_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(ensemble_rows).to_csv(TABLES_DIR / "ensemble_weights.csv", index=False, encoding="utf-8-sig")
    if importance_rows:
        pd.concat(importance_rows, ignore_index=True).to_csv(TABLES_DIR / "feature_importance.csv", index=False, encoding="utf-8-sig")
    if shap_rows:
        pd.concat(shap_rows, ignore_index=True).to_csv(TABLES_DIR / "shap_importance.csv", index=False, encoding="utf-8-sig")

    print("\nWrote:")
    print(f"- {TABLES_DIR / 'model_metrics.csv'}")
    print(f"- {RESULTS_DIR}")
    print(f"- {FIGURES_DIR}")
    print(f"- {MODELS_DIR}")


if __name__ == "__main__":
    main()

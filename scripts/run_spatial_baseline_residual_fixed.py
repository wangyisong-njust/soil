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
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs
from soilmodel.validation import make_protocol_split


DEFAULT_MODELS = ["RF_raw", "ExtraTrees_raw", "HistGBR_raw", "XGBoost_raw", "LightGBM_raw"]
RESIDUAL_SHRINKAGE = [0.25, 0.50, 1.00]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fixed spatial background plus residual models.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Override processed CSV path.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated model names.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for supported estimators.")
    return parser.parse_args()


def as_1d_prediction(pred) -> np.ndarray:
    arr = np.asarray(pred, dtype=float)
    if arr.ndim > 1:
        arr = arr.reshape(arr.shape[0], -1)[:, 0]
    return arr


def fit_predict(spec, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
    return as_1d_prediction(pred)


def protocol_indices(df: pd.DataFrame, config: dict[str, object]) -> tuple[np.ndarray, np.ndarray]:
    return make_protocol_split(
        df,
        protocol="temporal",
        random_state=int(config["random_seed"]),
        random_test_size=float(config["random_test_size"]),
        temporal_test_start_year=int(config["temporal_test_start_year"]),
    )


def target_spatial_features(
    df: pd.DataFrame,
    x_base: pd.DataFrame,
    y: pd.Series,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    k: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    x_train = add_target_spatial_lag_features(df, x_base, y, train_idx, train_idx, k=k, leave_one_out=True)
    x_test = add_target_spatial_lag_features(df, x_base, y, train_idx, test_idx, k=k, leave_one_out=False)
    fill_value = float(np.nanmedian(y.loc[train_idx].to_numpy(dtype=float)))
    for x_part in (x_train, x_test):
        for col in TARGET_SPATIAL_FEATURES:
            if col in x_part.columns:
                x_part[col] = pd.to_numeric(x_part[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
                x_part[col] = x_part[col].fillna(fill_value)
    return x_train, x_test


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_无记录。_"
    text = df.astype(str)
    lines = [
        "| " + " | ".join(text.columns) + " |",
        "| " + " | ".join(["---"] * len(text.columns)) + " |",
    ]
    for row in text.values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = ROOT / (args.data or config["processed_csv"])
    raw_df = pd.read_csv(data_path)
    df, base_feature_cols = add_engineered_features(raw_df, config["base_feature_columns"])
    x_base = df[base_feature_cols].astype(float)
    targets = [str(target) for target in config["target_columns"]]
    train_idx, test_idx = protocol_indices(df, config)
    k = int(config.get("target_spatial_lag_k", 12))
    feature_cols = base_feature_cols + TARGET_SPATIAL_FEATURES
    registry = build_model_registry(len(feature_cols), random_state=int(config["random_seed"]), n_jobs=args.n_jobs)
    model_names = [name.strip() for name in args.models.split(",") if name.strip()]
    registry = {name: registry[name] for name in model_names if name in registry}
    if not registry:
        raise SystemExit("No requested models are available.")

    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    for target in targets:
        y = df[target].astype(float)
        x_train, x_test = target_spatial_features(df, x_base, y, train_idx, test_idx, k)
        bg_train = x_train["target_spatial_idw"].to_numpy(dtype=float)
        bg_test = x_test["target_spatial_idw"].to_numpy(dtype=float)
        y_train = y.loc[train_idx]
        y_test = y.loc[test_idx]
        residual_train = y_train.to_numpy(dtype=float) - bg_train
        residual_train = pd.Series(residual_train, index=train_idx).replace([np.inf, -np.inf], np.nan)
        residual_train = residual_train.fillna(float(residual_train.median()))
        x_train = x_train.replace([np.inf, -np.inf], np.nan).fillna(x_train.median(numeric_only=True))
        x_test = x_test.replace([np.inf, -np.inf], np.nan).fillna(x_train.median(numeric_only=True))
        bg_pred = np.maximum(bg_test, 0.0)
        bg_metric = regression_metrics(y_test, bg_pred)
        rows.append(
            {
                "target": target,
                "protocol": "temporal_2022_2026",
                "method": "spatial_baseline_residual_fixed",
                "model": "IDW_background_alpha0",
                "status": "ok",
                "n_train": int(len(train_idx)),
                "n_test": int(len(test_idx)),
                "train_year_min": int(df.loc[train_idx, "year"].min()),
                "train_year_max": int(df.loc[train_idx, "year"].max()),
                "test_year_min": int(df.loc[test_idx, "year"].min()),
                "test_year_max": int(df.loc[test_idx, "year"].max()),
                **bg_metric,
            }
        )
        bg_pred_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
        bg_pred_table.insert(0, "row_id", test_idx)
        bg_pred_table["target"] = target
        bg_pred_table["protocol"] = "temporal_2022_2026"
        bg_pred_table["method"] = "spatial_baseline_residual_fixed"
        bg_pred_table["model"] = "IDW_background_alpha0"
        bg_pred_table["observed"] = y_test.to_numpy(dtype=float)
        bg_pred_table["predicted"] = bg_pred
        pred_rows.append(bg_pred_table)
        for model_name, spec in registry.items():
            try:
                residual_pred = fit_predict(spec, x_train, residual_train, x_test)
                status = "ok"
            except Exception as exc:
                residual_pred = np.full(len(test_idx), np.nan)
                metric = {"r2": np.nan, "r2_log1p": np.nan, "rmse": np.nan, "mae": np.nan, "mape": np.nan}
                status = f"failed: {exc}"
            for alpha in RESIDUAL_SHRINKAGE:
                pred = np.maximum(bg_test + alpha * residual_pred, 0.0)
                if status == "ok":
                    metric = regression_metrics(y_test, pred)
                rows.append(
                    {
                        "target": target,
                        "protocol": "temporal_2022_2026",
                        "method": "spatial_baseline_residual_fixed",
                        "model": f"{model_name}_alpha{alpha:.2f}",
                        "status": status,
                        "n_train": int(len(train_idx)),
                        "n_test": int(len(test_idx)),
                        "train_year_min": int(df.loc[train_idx, "year"].min()),
                        "train_year_max": int(df.loc[train_idx, "year"].max()),
                        "test_year_min": int(df.loc[test_idx, "year"].min()),
                        "test_year_max": int(df.loc[test_idx, "year"].max()),
                        **metric,
                    }
                )
                pred_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
                pred_table.insert(0, "row_id", test_idx)
                pred_table["target"] = target
                pred_table["protocol"] = "temporal_2022_2026"
                pred_table["method"] = "spatial_baseline_residual_fixed"
                pred_table["model"] = f"{model_name}_alpha{alpha:.2f}"
                pred_table["observed"] = y_test.to_numpy(dtype=float)
                pred_table["predicted"] = pred
                pred_rows.append(pred_table)

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "spatial_baseline_residual_fixed_metrics.csv", index=False, encoding="utf-8-sig")
    pd.concat(pred_rows, ignore_index=True).to_csv(
        RESULTS_DIR / "spatial_baseline_residual_fixed_predictions.csv", index=False, encoding="utf-8-sig"
    )
    best = (
        metrics[metrics["status"] == "ok"]
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    best.to_csv(TABLES_DIR / "spatial_baseline_residual_fixed_best_metrics.csv", index=False, encoding="utf-8-sig")
    show = best[["target", "method", "model", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: "" if pd.isna(value) else f"{float(value):.4f}")
    lines = [
        "# 空间背景值+残差模型修复版",
        "",
        "本脚本使用训练期留一空间邻域 IDW 构建训练背景场，测试期只引用训练期样本构建背景场，再对残差进行机器学习回归。背景场中的非有限值用训练期目标中位数兜底，残差模型使用 raw 回归器，并同时评估 0%、25%、50%、100% 残差校正强度，避免过度修正。",
        "",
        md_table(show),
        "",
        "结果表见 `tables/spatial_baseline_residual_fixed_metrics.csv` 和 `tables/spatial_baseline_residual_fixed_best_metrics.csv`；预测明细见 `results/spatial_baseline_residual_fixed_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "spatial_baseline_residual_fixed_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote fixed spatial baseline residual outputs")


if __name__ == "__main__":
    main()

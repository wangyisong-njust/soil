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
from soilmodel.data import (
    TARGET_SPATIAL_FEATURES,
    add_engineered_features,
    add_target_spatial_lag_features,
    apply_quality_cleaning,
    read_and_clean_excel,
)
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import DATA_DIR, DOCS_DIR, TABLES_DIR, ensure_project_dirs
from soilmodel.validation import make_internal_validation_split, make_protocol_split


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare publication-defensible data-cleaning strategies.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument(
        "--strategies",
        default="basic,quality,quality_target_mild,quality_target_strict",
        help="Comma-separated cleaning strategies.",
    )
    parser.add_argument("--protocols", default="temporal", help="Comma-separated protocols.")
    parser.add_argument(
        "--models",
        default="RF,ExtraTrees,HistGBR,XGBoost,LightGBM,CatBoost,ElasticNet,PLSR,NGBoost",
        help="Comma-separated model names for the comparison run.",
    )
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for supported estimators.")
    return parser.parse_args()


def normalize_prediction(pred) -> np.ndarray:
    arr = np.asarray(pred, dtype=float)
    if arr.ndim > 1:
        arr = arr.reshape(arr.shape[0], -1)[:, 0]
    return arr


def fit_predict_model(name: str, spec, x_train, y_train, x_test) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        return normalize_prediction(model.predict(x_test))


def make_weights(rows: list[dict[str, object]], top_k: int = 3) -> dict[str, float]:
    ok = [
        row
        for row in rows
        if row["status"] == "ok" and np.isfinite(float(row["rmse"])) and float(row["rmse"]) > 0
    ]
    ok = sorted(ok, key=lambda row: float(row["rmse"]))[:top_k]
    if not ok:
        return {}
    scores = {str(row["model"]): (1.0 + max(float(row["r2"]), 0.0)) / float(row["rmse"]) for row in ok}
    total = sum(scores.values())
    return {name: value / total for name, value in scores.items()}


def evaluate_strategy(
    df: pd.DataFrame,
    strategy: str,
    config: dict[str, object],
    protocols: list[str],
    requested_models: list[str],
    n_jobs: int,
) -> list[dict[str, object]]:
    targets = list(config["target_columns"])
    df_features, base_feature_cols = add_engineered_features(df, list(config["base_feature_columns"]))
    use_spatial_lag = bool(config.get("use_target_spatial_lag_features", False))
    model_feature_cols = base_feature_cols + (TARGET_SPATIAL_FEATURES if use_spatial_lag else [])
    registry = build_model_registry(len(model_feature_cols), random_state=int(config["random_seed"]), n_jobs=n_jobs)
    registry = {name: spec for name, spec in registry.items() if name in requested_models}

    rows: list[dict[str, object]] = []
    for target in targets:
        y = df_features[target].astype(float)
        x_base = df_features[base_feature_cols].astype(float)
        for protocol in protocols:
            train_idx, test_idx = make_protocol_split(
                df_features,
                protocol=protocol,
                random_state=int(config["random_seed"]),
                random_test_size=float(config["random_test_size"]),
                temporal_test_start_year=int(config["temporal_test_start_year"]),
            )
            core_idx, valid_idx = make_internal_validation_split(
                df_features, train_idx, protocol, int(config["random_seed"])
            )

            if use_spatial_lag:
                k = int(config.get("target_spatial_lag_k", 12))
                x_core = add_target_spatial_lag_features(df_features, x_base, y, core_idx, core_idx, k=k, leave_one_out=True)
                x_valid = add_target_spatial_lag_features(df_features, x_base, y, core_idx, valid_idx, k=k, leave_one_out=False)
                x_train = add_target_spatial_lag_features(df_features, x_base, y, train_idx, train_idx, k=k, leave_one_out=True)
                x_test = add_target_spatial_lag_features(df_features, x_base, y, train_idx, test_idx, k=k, leave_one_out=False)
            else:
                x_core = x_base.loc[core_idx]
                x_valid = x_base.loc[valid_idx]
                x_train = x_base.loc[train_idx]
                x_test = x_base.loc[test_idx]

            y_core = y.loc[core_idx]
            y_valid = y.loc[valid_idx]
            y_train = y.loc[train_idx]
            y_test = y.loc[test_idx]

            validation_rows: list[dict[str, object]] = []
            test_predictions: dict[str, np.ndarray] = {}
            for name, spec in registry.items():
                try:
                    valid_pred = fit_predict_model(name, spec, x_core, y_core, x_valid)
                    valid_metric = regression_metrics(y_valid, valid_pred)
                    validation_rows.append({"model": name, "status": "ok", **valid_metric})

                    pred = fit_predict_model(name, spec, x_train, y_train, x_test)
                    metric = regression_metrics(y_test, pred)
                    test_predictions[name] = pred
                    rows.append(
                        {
                            "strategy": strategy,
                            "target": target,
                            "protocol": protocol,
                            "model": name,
                            "status": "ok",
                            "n_samples": int(len(df_features)),
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "train_year_min": int(df_features.loc[train_idx, "year"].min()),
                            "train_year_max": int(df_features.loc[train_idx, "year"].max()),
                            "test_year_min": int(df_features.loc[test_idx, "year"].min()),
                            "test_year_max": int(df_features.loc[test_idx, "year"].max()),
                            **metric,
                        }
                    )
                except Exception as exc:
                    rows.append(
                        {
                            "strategy": strategy,
                            "target": target,
                            "protocol": protocol,
                            "model": name,
                            "status": f"failed: {exc}",
                            "n_samples": int(len(df_features)),
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "r2": np.nan,
                            "r2_log1p": np.nan,
                            "rmse": np.nan,
                            "mae": np.nan,
                            "mape": np.nan,
                        }
                    )

            weights = make_weights(validation_rows, top_k=int(config.get("ensemble_top_k", 3)))
            if weights:
                ensemble_pred = np.zeros(len(test_idx), dtype=float)
                for name, weight in weights.items():
                    ensemble_pred += weight * test_predictions[name]
                metric = regression_metrics(y_test, ensemble_pred)
                rows.append(
                    {
                        "strategy": strategy,
                        "target": target,
                        "protocol": protocol,
                        "model": "WeightedEnsemble",
                        "status": "ok",
                        "n_samples": int(len(df_features)),
                        "n_train": int(len(train_idx)),
                        "n_test": int(len(test_idx)),
                        "train_year_min": int(df_features.loc[train_idx, "year"].min()),
                        "train_year_max": int(df_features.loc[train_idx, "year"].max()),
                        "test_year_min": int(df_features.loc[test_idx, "year"].min()),
                        "test_year_max": int(df_features.loc[test_idx, "year"].max()),
                        **metric,
                    }
                )
    return rows


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_无记录。_"
    text_df = df.astype(str)
    lines = [
        "| " + " | ".join(text_df.columns) + " |",
        "| " + " | ".join(["---"] * len(text_df.columns)) + " |",
    ]
    for row in text_df.values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    strategies = [item.strip() for item in args.strategies.split(",") if item.strip()]
    protocols = [item.strip() for item in args.protocols.split(",") if item.strip()]
    requested_models = [item.strip() for item in args.models.split(",") if item.strip()]

    basic_df = read_and_clean_excel(ROOT / str(config["raw_excel"]))
    all_rows: list[dict[str, object]] = []
    cleaning_reports: list[dict[str, object]] = []
    variant_dir = DATA_DIR / "processed" / "cleaning_variants"
    variant_dir.mkdir(parents=True, exist_ok=True)

    for strategy in strategies:
        print(f"\n=== Cleaning strategy: {strategy} ===", flush=True)
        cleaned, report = apply_quality_cleaning(
            basic_df,
            target_columns=list(config["target_columns"]),
            base_feature_columns=list(config["base_feature_columns"]),
            strategy=strategy,
            driver_winsor_limits=tuple(config.get("driver_winsor_limits", [0.005, 0.995])),
        )
        variant_path = variant_dir / f"soil_heavy_metals_{strategy}.csv"
        cleaned.to_csv(variant_path, index=False, encoding="utf-8-sig")
        report["variant_csv"] = str(variant_path.relative_to(ROOT))
        cleaning_reports.append(report)
        all_rows.extend(evaluate_strategy(cleaned, strategy, config, protocols, requested_models, args.n_jobs))

    metrics = pd.DataFrame(all_rows)
    metrics.to_csv(TABLES_DIR / "cleaning_strategy_comparison.csv", index=False, encoding="utf-8-sig")
    ok = metrics[metrics["status"] == "ok"].copy()
    best = (
        ok.sort_values(["strategy", "target", "protocol", "r2", "rmse"], ascending=[True, True, True, False, True])
        .groupby(["strategy", "target", "protocol"], as_index=False)
        .head(1)
        .sort_values(["strategy", "target", "protocol"])
    )
    best.to_csv(TABLES_DIR / "cleaning_strategy_best_metrics.csv", index=False, encoding="utf-8-sig")
    (TABLES_DIR / "cleaning_strategy_reports.json").write_text(
        json.dumps(cleaning_reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = (
        best.groupby("strategy", as_index=False)
        .agg(
            n_samples=("n_samples", "first"),
            mean_best_r2=("r2", "mean"),
            median_best_r2=("r2", "median"),
            min_best_r2=("r2", "min"),
            max_best_r2=("r2", "max"),
            mean_best_rmse=("rmse", "mean"),
        )
        .sort_values(["mean_best_r2", "median_best_r2"], ascending=False)
    )
    for col in ["mean_best_r2", "median_best_r2", "min_best_r2", "max_best_r2", "mean_best_rmse"]:
        summary[col] = summary[col].map(lambda x: f"{x:.4f}")

    report_lines = [
        "# 数据清洗策略对照",
        "",
        "本报告比较不同数据清洗策略在时间外推验证中的表现。清洗规则只包括格式纠错、重复观测聚合、驱动因子缺失填补、驱动因子温和截尾，以及可选的目标变量极端值剔除。",
        "",
        "## 策略汇总",
        "",
        md_table(summary),
        "",
        "## 各目标最佳结果",
        "",
        md_table(
            best[
                ["strategy", "target", "protocol", "model", "n_samples", "n_train", "n_test", "r2", "r2_log1p", "rmse", "mae", "mape"]
            ].assign(
                r2=lambda x: x["r2"].map(lambda v: f"{v:.4f}"),
                r2_log1p=lambda x: x["r2_log1p"].map(lambda v: f"{v:.4f}"),
                rmse=lambda x: x["rmse"].map(lambda v: f"{v:.4f}"),
                mae=lambda x: x["mae"].map(lambda v: f"{v:.4f}"),
                mape=lambda x: x["mape"].map(lambda v: f"{v:.4f}"),
            )
        ),
        "",
        "## 输出文件",
        "",
        "- 完整对照指标：`tables/cleaning_strategy_comparison.csv`",
        "- 各策略各目标最佳指标：`tables/cleaning_strategy_best_metrics.csv`",
        "- 清洗规则记录：`tables/cleaning_strategy_reports.json`",
        "- 清洗后数据变体：`data/processed/cleaning_variants/`",
        "",
        "目标变量极端值剔除会改变验证样本，论文中应作为敏感性分析或测量异常剔除说明；默认推荐优先采用 `quality`，除非有明确的异常值判定依据。",
        "",
    ]
    (DOCS_DIR / "data_cleaning_strategy_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print("\nWrote:")
    print("- tables/cleaning_strategy_comparison.csv")
    print("- tables/cleaning_strategy_best_metrics.csv")
    print("- tables/cleaning_strategy_reports.json")
    print("- docs/data_cleaning_strategy_report.md")


if __name__ == "__main__":
    main()

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


DEFAULT_MODELS = ["RF", "ExtraTrees", "HistGBR", "ElasticNet", "PLSR", "XGBoost", "LightGBM", "CatBoost", "NGBoost"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare baseline features against public external covariates.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--baseline-data", default="data/processed/soil_heavy_metals.csv", help="Baseline CSV path.")
    parser.add_argument("--external-data", default="data/processed/soil_heavy_metals_external.csv", help="External-enriched CSV path.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated model names.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs.")
    return parser.parse_args()


def protocol_indices(df: pd.DataFrame, protocol: str, cutoff: int) -> tuple[np.ndarray, np.ndarray]:
    index = np.asarray(df.index)
    if protocol == "literature_2019_2020":
        return index[df["year"].between(2000, 2018).to_numpy()], index[df["year"].between(2019, 2020).to_numpy()]
    if protocol == "temporal_2022_2026":
        return index[(df["year"] < cutoff).to_numpy()], index[(df["year"] >= cutoff).to_numpy()]
    raise ValueError(protocol)


def fit_predict(spec, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        pred = np.asarray(model.predict(x_test), dtype=float).reshape(-1)
    return np.maximum(pred, 0.0)


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


def evaluate_feature_set(
    df: pd.DataFrame,
    feature_cols: list[str],
    feature_set: str,
    config: dict[str, object],
    requested_models: list[str],
    n_jobs: int,
) -> tuple[list[dict[str, object]], list[pd.DataFrame]]:
    df_feat, engineered_cols = add_engineered_features(df, feature_cols)
    model_feature_cols = engineered_cols + (TARGET_SPATIAL_FEATURES if config.get("use_target_spatial_lag_features") else [])
    registry = build_model_registry(len(model_feature_cols), random_state=int(config["random_seed"]), n_jobs=n_jobs)
    registry = {name: registry[name] for name in requested_models if name in registry}
    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    x_base = df_feat[engineered_cols].astype(float)
    for protocol in ["literature_2019_2020", "temporal_2022_2026"]:
        train_idx, test_idx = protocol_indices(df_feat, protocol, int(config["temporal_test_start_year"]))
        print(f"\n{feature_set} {protocol}: train={len(train_idx)} test={len(test_idx)} features={len(model_feature_cols)}", flush=True)
        for target in config["target_columns"]:
            y = df_feat[target].astype(float)
            if config.get("use_target_spatial_lag_features", False):
                k = int(config.get("target_spatial_lag_k", 12))
                x_train = add_target_spatial_lag_features(df_feat, x_base, y, train_idx, train_idx, k=k, leave_one_out=True)
                x_test = add_target_spatial_lag_features(df_feat, x_base, y, train_idx, test_idx, k=k, leave_one_out=False)
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
                            "feature_set": feature_set,
                            "protocol": protocol,
                            "target": target,
                            "model": model_name,
                            "status": "ok",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "n_features": int(len(model_feature_cols)),
                            **metric,
                        }
                    )
                    pred_table = df_feat.loc[test_idx, ["lon", "lat", "year"]].copy()
                    pred_table["feature_set"] = feature_set
                    pred_table["protocol"] = protocol
                    pred_table["target"] = target
                    pred_table["model"] = model_name
                    pred_table["observed"] = y_test.to_numpy()
                    pred_table["predicted"] = pred
                    pred_rows.append(pred_table)
                except Exception as exc:
                    rows.append(
                        {
                            "feature_set": feature_set,
                            "protocol": protocol,
                            "target": target,
                            "model": model_name,
                            "status": f"failed: {exc}",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "n_features": int(len(model_feature_cols)),
                            "r2": np.nan,
                            "r2_log1p": np.nan,
                            "rmse": np.nan,
                            "mae": np.nan,
                            "mape": np.nan,
                        }
                    )
    return rows, pred_rows


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    baseline_df = pd.read_csv(ROOT / args.baseline_data)
    external_df = pd.read_csv(ROOT / args.external_data)
    base_features = list(config["base_feature_columns"])
    external_features = [
        col
        for col in external_df.columns
        if col.startswith(("sg_", "np_", "osm_", "viirs_", "ghsl_", "wc_"))
    ]
    source_names = ["SoilGrids 表层土壤属性", "NASA POWER 年尺度气候变量"]
    osm_features = [col for col in external_features if col.startswith("osm_")]
    if any("road" in col for col in osm_features):
        source_names.append("OpenStreetMap/Geofabrik 道路代理变量")
    if any(("railway" in col or "traffic" in col or "transport" in col) for col in osm_features):
        source_names.append("OpenStreetMap/Geofabrik 铁路与交通设施代理变量")
    if any(("landuse" in col or "activity_poi" in col or "pollution_poi" in col) for col in osm_features):
        source_names.append("OpenStreetMap/Geofabrik 土地利用与活动 POI 代理变量")
    if any(("industrial" in col or "mining" in col) for col in osm_features):
        source_names.append("OpenStreetMap/Geofabrik 工业矿业污染源代理变量")
    if any(col.startswith("viirs_") for col in external_features):
        source_names.append("VIIRS 年度夜间灯光代理变量")
    if any(col.startswith("ghsl_") for col in external_features):
        source_names.append("GHSL 建成区与人口代理变量")
    if any(col.startswith("wc_") for col in external_features):
        source_names.append("ESA WorldCover 2021 土地覆盖变量")
    requested = [item.strip() for item in args.models.split(",") if item.strip()]

    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    part_rows, part_preds = evaluate_feature_set(
        baseline_df, base_features, "baseline", config, requested, args.n_jobs
    )
    rows.extend(part_rows)
    pred_rows.extend(part_preds)
    part_rows, part_preds = evaluate_feature_set(
        external_df, base_features + external_features, "external_covariates", config, requested, args.n_jobs
    )
    rows.extend(part_rows)
    pred_rows.extend(part_preds)

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "external_covariate_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(RESULTS_DIR / "external_covariate_predictions.csv", index=False, encoding="utf-8-sig")
    best = (
        metrics[metrics["status"] == "ok"]
        .sort_values(["feature_set", "protocol", "target", "r2", "rmse"], ascending=[True, True, True, False, True])
        .groupby(["feature_set", "protocol", "target"], as_index=False)
        .head(1)
        .sort_values(["protocol", "target", "feature_set"])
    )
    best.to_csv(TABLES_DIR / "external_covariate_best_metrics.csv", index=False, encoding="utf-8-sig")

    compare = best.pivot_table(index=["protocol", "target"], columns="feature_set", values="r2", aggfunc="first").reset_index()
    if {"baseline", "external_covariates"}.issubset(compare.columns):
        compare["delta_r2"] = compare["external_covariates"] - compare["baseline"]
    compare.to_csv(TABLES_DIR / "external_covariate_r2_delta.csv", index=False, encoding="utf-8-sig")
    show = compare.copy()
    for col in ["baseline", "external_covariates", "delta_r2"]:
        if col in show:
            show[col] = show[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    lines = [
        "# 外部公开因子对照",
        "",
        f"本报告比较原始特征与{'、'.join(source_names)}增强后的模型表现。外部数据只作为预测因子，不修改目标变量。",
        "",
        md_table(show),
        "",
        "外部因子提取记录见 `tables/external_covariates_report.json`；若启用 OSM 人类活动代理变量，记录另见 `tables/osm_covariates_report.json` 和 `tables/osm_activity_covariates_report.json`。",
        "",
    ]
    (DOCS_DIR / "external_covariate_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote external covariate comparison outputs")


if __name__ == "__main__":
    main()

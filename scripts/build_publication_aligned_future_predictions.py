#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import mean_squared_error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from soilmodel.config import load_config, target_columns
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path

from run_distribution_guided_spatial_quantile import predict_grid_quantile, predict_knn_quantile
from run_local_analog_memory_models import analog_features
from run_publication_validation_fusion import load_predictions as load_publication_fusion_validation_predictions
from run_spatiotemporal_innovations import add_spatial_clusters, fit_model as fit_innovation_model, temporal_weights
from run_temporal_sequence_models import fit_zones, rolling_temporal_features


OUT_DIR = FIGURES_DIR / "publication_aligned_future"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build future predictions aligned with publication-grade selected models.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Experiment config path.")
    parser.add_argument("--years", default="2027,2028,2029,2030,2031,2032,2033,2034,2035")
    parser.add_argument("--n-jobs", type=int, default=2)
    return parser.parse_args()


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


def model_feature_columns(df: pd.DataFrame, config: dict[str, object]) -> list[str]:
    base_features = [str(item) for item in config["base_feature_columns"]]
    external_features = [
        col for col in df.columns if col.startswith(("sg_", "np_", "osm_", "viirs_", "ghsl_", "wc_"))
    ]
    return list(dict.fromkeys(base_features + external_features))


def make_future_frame(df: pd.DataFrame, feature_cols: list[str], years: list[int]) -> pd.DataFrame:
    work = df.copy()
    work["lon_round"] = work["lon"].round(6)
    work["lat_round"] = work["lat"].round(6)
    latest = work.sort_values(["lon_round", "lat_round", "year"]).groupby(["lon_round", "lat_round"], as_index=False).tail(1)
    driver_features = [col for col in feature_cols if col not in {"lon", "lat", "year"} and col in latest.columns]
    rows: list[pd.DataFrame] = []
    for year in years:
        part = latest[["lon", "lat", *driver_features]].copy()
        part["year"] = int(year)
        part["scenario"] = "baseline_constant_drivers"
        part["source_year"] = latest["year"].to_numpy()
        rows.append(part)
    future = pd.concat(rows, ignore_index=True)
    future.index = np.arange(1_000_000, 1_000_000 + len(future))
    return future


def fit_registry_future(
    observed: pd.DataFrame,
    future_raw: pd.DataFrame,
    config: dict[str, object],
    feature_cols: list[str],
    target: str,
    model_name: str,
    n_jobs: int,
) -> tuple[np.ndarray, str]:
    combined = pd.concat([observed, future_raw.drop(columns=["scenario", "source_year"])], axis=0, sort=False)
    combined, engineered_cols = add_engineered_features(combined, feature_cols)
    model_cols = engineered_cols + (TARGET_SPATIAL_FEATURES if config.get("use_target_spatial_lag_features", False) else [])
    registry = build_model_registry(len(model_cols), random_state=int(config["random_seed"]), n_jobs=n_jobs)
    if model_name not in registry:
        raise ValueError(f"Unsupported registry model: {model_name}")
    observed_idx = observed.index.to_numpy()
    future_idx = future_raw.index.to_numpy()
    y = combined.loc[observed_idx, target].astype(float)
    x_base = combined[engineered_cols].astype(float)
    if config.get("use_target_spatial_lag_features", False):
        k = int(config.get("target_spatial_lag_k", 12))
        x_train = add_target_spatial_lag_features(combined, x_base, y, observed_idx, observed_idx, k=k, leave_one_out=True)
        x_future = add_target_spatial_lag_features(combined, x_base, y, observed_idx, future_idx, k=k, leave_one_out=False)
    else:
        x_train = x_base.loc[observed_idx]
        x_future = x_base.loc[future_idx]
    model = fresh_model(registry[model_name])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y)
        pred = np.asarray(model.predict(x_future), dtype=float).reshape(-1)
    return np.maximum(pred, 0.0), f"registry::{model_name}"


def fit_innovation_member_future(
    observed: pd.DataFrame,
    future_raw: pd.DataFrame,
    config: dict[str, object],
    target: str,
    method: str,
    model_name: str,
    n_jobs: int,
) -> tuple[np.ndarray, str]:
    feature_cols = [str(item) for item in config["base_feature_columns"]]
    combined = pd.concat([observed, future_raw.drop(columns=["scenario", "source_year"])], axis=0, sort=False)
    combined, engineered_cols = add_engineered_features(combined, feature_cols)
    observed_idx = observed.index.to_numpy()
    future_idx = future_raw.index.to_numpy()
    x_base = combined[engineered_cols].astype(float)
    y = combined.loc[observed_idx, target].astype(float)
    if config.get("use_target_spatial_lag_features", False):
        k = int(config.get("target_spatial_lag_k", 12))
        x_train = add_target_spatial_lag_features(combined, x_base, y, observed_idx, observed_idx, k=k, leave_one_out=True)
        x_future = add_target_spatial_lag_features(combined, x_base, y, observed_idx, future_idx, k=k, leave_one_out=False)
    else:
        x_train = x_base.loc[observed_idx]
        x_future = x_base.loc[future_idx]
    x_train_region, x_future_region, _ = add_spatial_clusters(
        x_train, x_future, combined, observed_idx, future_idx, 6, int(config["random_seed"])
    )
    registry = build_model_registry(x_train_region.shape[1], random_state=int(config["random_seed"]), n_jobs=n_jobs)
    if model_name not in registry:
        raise ValueError(f"Unsupported innovation model: {model_name}")
    spec = registry[model_name]
    y_train = y.loc[observed_idx]

    if method == "direct_global":
        model, _ = fit_innovation_model(spec, x_train, y_train)
        pred = np.asarray(model.predict(x_future), dtype=float).reshape(-1)
    elif method == "spatial_zone_features":
        model, _ = fit_innovation_model(spec, x_train_region, y_train)
        pred = np.asarray(model.predict(x_future_region), dtype=float).reshape(-1)
    elif method == "temporal_weighted":
        weights = temporal_weights(combined.loc[observed_idx, "year"])
        model, _ = fit_innovation_model(spec, x_train, y_train, sample_weight=weights)
        pred = np.asarray(model.predict(x_future), dtype=float).reshape(-1)
    elif method == "two_stage_high_pollution":
        threshold = float(y_train.quantile(0.85))
        high = y_train >= threshold
        if int(high.sum()) < 20 or int((~high).sum()) < 40:
            raise ValueError("not enough samples for two-stage split")
        clf = RandomForestClassifier(
            n_estimators=240,
            class_weight="balanced_subsample",
            random_state=int(config["random_seed"]),
            n_jobs=n_jobs,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            clf.fit(x_train, high.astype(int))
        reg_low, _ = fit_innovation_model(spec, x_train.loc[~high], y_train.loc[~high])
        reg_high, _ = fit_innovation_model(spec, x_train.loc[high], y_train.loc[high])
        p_high = clf.predict_proba(x_future)[:, 1]
        pred_low = np.asarray(reg_low.predict(x_future), dtype=float).reshape(-1)
        pred_high = np.asarray(reg_high.predict(x_future), dtype=float).reshape(-1)
        pred = (1.0 - p_high) * pred_low + p_high * pred_high
    else:
        raise ValueError(f"Unsupported innovation method for future: {method}")
    return np.maximum(pred, 0.0), f"innovation::{method}::{model_name}"


def fit_local_analog_future(
    observed: pd.DataFrame,
    future_raw: pd.DataFrame,
    config: dict[str, object],
    feature_cols: list[str],
    target: str,
    model_name: str,
    n_jobs: int,
) -> tuple[np.ndarray, str]:
    combined = pd.concat([observed, future_raw.drop(columns=["scenario", "source_year"])], axis=0, sort=False)
    combined, engineered_cols = add_engineered_features(combined, feature_cols)
    observed_idx = observed.index.to_numpy()
    future_idx = future_raw.index.to_numpy()
    y = combined.loc[observed_idx, target].astype(float)
    analog_train = analog_features(combined, y, observed_idx, observed_idx, k=12, leave_one_out=True)
    analog_future = analog_features(combined, y, observed_idx, future_idx, k=12, leave_one_out=False)
    x_train = pd.concat([combined.loc[observed_idx, engineered_cols].astype(float), analog_train], axis=1)
    x_future = pd.concat([combined.loc[future_idx, engineered_cols].astype(float), analog_future], axis=1)
    registry = build_model_registry(x_train.shape[1], random_state=int(config["random_seed"]), n_jobs=n_jobs)
    if model_name not in registry:
        raise ValueError(f"Unsupported local analog model: {model_name}")
    model = fresh_model(registry[model_name])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y)
        pred = np.asarray(model.predict(x_future), dtype=float).reshape(-1)
    return np.maximum(pred, 0.0), f"local_analog::{model_name}"


def fit_temporal_sequence_future(
    observed: pd.DataFrame,
    future_raw: pd.DataFrame,
    config: dict[str, object],
    target: str,
    model_name: str,
    n_jobs: int,
) -> tuple[np.ndarray, str]:
    observed_part = observed.copy()
    future_part = future_raw.drop(columns=["scenario", "source_year"]).copy()
    combined = pd.concat([observed_part, future_part], axis=0, sort=False).reset_index(drop=True)
    observed_idx = np.arange(len(observed_part))
    future_idx = np.arange(len(observed_part), len(combined))
    base_features = [str(item) for item in config["base_feature_columns"]]
    external_features = [col for col in combined.columns if col.startswith(("sg_", "np_", "osm_"))]
    combined_features, engineered_cols = add_engineered_features(combined, list(dict.fromkeys(base_features + external_features)))
    x_base = combined_features[engineered_cols].astype(float)
    y = combined_features[target].astype(float)
    zones = fit_zones(combined_features, observed_idx, 8, int(config["random_seed"]))
    ts_train, ts_future = rolling_temporal_features(
        combined_features,
        target,
        observed_idx,
        future_idx,
        zones,
        int(config["random_seed"]),
        260,
    )
    if config.get("use_target_spatial_lag_features", False):
        k = int(config.get("target_spatial_lag_k", 12))
        x_train_base = add_target_spatial_lag_features(
            combined_features, x_base, y, observed_idx, observed_idx, k=k, leave_one_out=True
        )
        x_future_base = add_target_spatial_lag_features(
            combined_features, x_base, y, observed_idx, future_idx, k=k, leave_one_out=False
        )
    else:
        x_train_base = x_base.loc[observed_idx]
        x_future_base = x_base.loc[future_idx]
    x_train = pd.concat([x_train_base, ts_train], axis=1)
    x_future = pd.concat([x_future_base, ts_future], axis=1)
    registry = build_model_registry(x_train.shape[1], random_state=int(config["random_seed"]), n_jobs=n_jobs)
    if model_name not in registry:
        raise ValueError(f"Unsupported temporal sequence model: {model_name}")
    model = fresh_model(registry[model_name])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y.loc[observed_idx])
        pred = np.asarray(model.predict(x_future), dtype=float).reshape(-1)
    return np.maximum(pred, 0.0), f"temporal_sequence::hybrid_spatiotemporal_sequence::{model_name}"


def distribution_guided_future(
    observed: pd.DataFrame,
    future_raw: pd.DataFrame,
    target: str,
    method: str,
    model: str,
) -> tuple[np.ndarray, str]:
    if method == "knn_spatial_quantile":
        stem, qtext = model.split("_Q")
        pred = predict_knn_quantile(observed, future_raw, target, int(stem.replace("KNN", "")), int(qtext) / 100.0)
    elif method == "grid_spatial_quantile":
        stem, qtext = model.split("_Q")
        pred = predict_grid_quantile(observed, future_raw, target, int(stem.replace("Grid", "")), int(qtext) / 100.0)
    else:
        raise ValueError(f"Unsupported distribution-guided method: {method}")
    return np.maximum(pred, 0.0), f"distribution_guided::{method}::{model}"


def fallback_future(target: str, selected_source: str, selected_model: str) -> tuple[np.ndarray, str, str]:
    fallback_path = RESULTS_DIR / "future_predictions_baseline_2027_2035.csv"
    if not fallback_path.exists() or fallback_path.stat().st_size == 0:
        raise FileNotFoundError("Missing fallback future predictions.")
    future = pd.read_csv(fallback_path)
    part = future[future["target"].astype(str) == str(target)].copy()
    if part.empty:
        raise ValueError(f"No fallback future rows for {target}.")
    return (
        part["predicted"].to_numpy(dtype=float),
        f"fallback::{part['model'].iloc[0]}",
        f"{selected_source}/{selected_model} needs multi-candidate future fusion; reused existing baseline future model.",
    )


def selected_candidate_validation_weights(target: str, selected: list[str]) -> np.ndarray:
    validation_predictions = load_publication_fusion_validation_predictions()
    part = validation_predictions[
        (validation_predictions["protocol"] == "literature_2019_2020")
        & (validation_predictions["target"].astype(str) == target)
        & (validation_predictions["candidate"].isin(selected))
    ].copy()
    if part.empty:
        raise ValueError(f"No validation predictions found for publication fusion target {target}.")
    rmses = []
    for candidate in selected:
        candidate_part = part[part["candidate"] == candidate]
        if candidate_part.empty:
            raise ValueError(f"Missing validation candidate: {candidate}")
        rmse = float(np.sqrt(mean_squared_error(candidate_part["observed"], candidate_part["predicted"])))
        rmses.append(rmse)
    weights = 1.0 / np.maximum(np.asarray(rmses, dtype=float), 1e-8)
    return weights / weights.sum()


def candidate_future_prediction(
    candidate: str,
    observed: pd.DataFrame,
    future_raw: pd.DataFrame,
    config: dict[str, object],
    target: str,
    feature_cols: list[str],
    n_jobs: int,
) -> np.ndarray:
    source, method, model = candidate.split("::", 2)
    if source == "local_analog":
        pred, _ = fit_local_analog_future(observed, future_raw, config, feature_cols, target, model, n_jobs)
    elif source == "temporal_sequence":
        if method != "hybrid_spatiotemporal_sequence":
            raise ValueError(f"Unsupported temporal candidate method: {method}")
        pred, _ = fit_temporal_sequence_future(observed, future_raw, config, target, model, n_jobs)
    elif source == "innovation":
        pred, _ = fit_innovation_member_future(observed, future_raw, config, target, method, model, n_jobs)
    else:
        raise ValueError(f"Unsupported fusion candidate source: {source}")
    return np.maximum(pred, 0.0)


def publication_validation_fusion_future(
    observed: pd.DataFrame,
    future_raw: pd.DataFrame,
    config: dict[str, object],
    feature_cols: list[str],
    target: str,
    model_name: str,
    n_jobs: int,
) -> tuple[np.ndarray, str, str]:
    best = pd.read_csv(TABLES_DIR / "publication_validation_fusion_best_metrics.csv")
    match = best[(best["target"].astype(str) == target) & (best["model"].astype(str) == model_name)]
    if match.empty:
        raise ValueError(f"No publication validation fusion metadata for {target}/{model_name}")
    selected = [item for item in str(match.iloc[0]["selected"]).split(";") if item]
    if not model_name.endswith("InvRMSEMean"):
        raise ValueError(f"Future implementation only supports InvRMSEMean fusion, got {model_name}")
    weights = selected_candidate_validation_weights(target, selected)
    matrix = np.column_stack(
        [
            candidate_future_prediction(candidate, observed, future_raw, config, target, feature_cols, n_jobs)
            for candidate in selected
        ]
    )
    pred = matrix @ weights
    implementation = f"publication_validation_fusion::{model_name}::{len(selected)}members"
    note = "Future fusion weights recomputed from 2019-2020 validation RMSE for the stored selected members."
    return np.maximum(pred, 0.0), implementation, note


def save_maps(predictions: pd.DataFrame, years: list[int]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for target, target_part in predictions.groupby("target"):
        for year in years:
            part = target_part[target_part["year"] == year]
            if part.empty:
                continue
            fig, ax = plt.subplots(figsize=(5.8, 4.8))
            sc = ax.scatter(part["lon"], part["lat"], c=part["predicted"], s=20, cmap="viridis", alpha=0.86)
            cb = fig.colorbar(sc, ax=ax)
            cb.set_label("Predicted concentration")
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.set_title(f"{target} publication-aligned future ({year})")
            fig.tight_layout()
            fig.savefig(OUT_DIR / f"{target}_future_{year}_publication_aligned_map.png", dpi=220)
            plt.close(fig)


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = preferred_processed_data_path()
    observed = pd.read_csv(data_path)
    observed["year"] = observed["year"].round().astype(int)
    feature_cols = model_feature_columns(observed, config)
    years = [int(item.strip()) for item in args.years.split(",") if item.strip()]
    future_raw = make_future_frame(observed, feature_cols, years)
    selected = pd.read_csv(TABLES_DIR / "publication_grade_recommended_metrics.csv").sort_values("target")
    rows: list[pd.DataFrame] = []
    summary_rows: list[dict[str, object]] = []

    # external_geo_terrain_covariates 目标使用含地形+地质的增强数据；坐标/年份与全局 future_raw 同序。
    geo_path = ROOT / "data" / "processed" / "soil_heavy_metals_geology.csv"
    geo_observed = geo_future_raw = geo_feature_cols = None
    if geo_path.exists():
        geo_observed = pd.read_csv(geo_path)
        geo_observed["year"] = geo_observed["year"].round().astype(int)
        geo_base = [str(item) for item in config["base_feature_columns"]]
        geo_ext = [c for c in geo_observed.columns
                   if c.startswith(("sg_", "np_", "osm_", "viirs_", "ghsl_", "wc_", "dem_", "terr_", "geo_"))]
        geo_feature_cols = list(dict.fromkeys(geo_base + geo_ext))
        geo_future_raw = make_future_frame(geo_observed, geo_feature_cols, years)

    for row in selected.itertuples(index=False):
        target = str(row.target)
        source = str(row.source)
        method = str(row.method)
        model = str(row.model)
        status = "exact_publication_model"
        note = ""
        try:
            if source in {"external_public_covariates", "spatiotemporal_innovation", "spatial_distribution_features"}:
                pred, implementation = fit_registry_future(observed, future_raw, config, feature_cols, target, model, args.n_jobs)
            elif source == "external_geo_terrain_covariates":
                if geo_observed is None:
                    raise ValueError("缺少 data/processed/soil_heavy_metals_geology.csv，无法复刻地形+地质未来模型。")
                pred, implementation = fit_registry_future(
                    geo_observed, geo_future_raw, config, geo_feature_cols, target, model, args.n_jobs
                )
            elif source == "local_analog_memory":
                pred, implementation = fit_local_analog_future(observed, future_raw, config, feature_cols, target, model, args.n_jobs)
            elif source == "distribution_guided_spatial_quantile":
                pred, implementation = distribution_guided_future(observed, future_raw, target, method, model)
            elif source == "publication_validation_fusion":
                pred, implementation, note = publication_validation_fusion_future(
                    observed, future_raw, config, feature_cols, target, model, args.n_jobs
                )
            else:
                pred, implementation, note = fallback_future(target, source, model)
                status = "documented_fallback"
        except Exception as exc:
            pred, implementation, note = fallback_future(target, source, model)
            status = "documented_fallback"
            note = f"Exact future implementation failed for {source}/{model}: {exc}; reused existing baseline future model."
        out = future_raw[["lon", "lat", "year", "scenario", "source_year"]].copy()
        out["target"] = target
        out["source"] = source
        out["method"] = method
        out["model"] = model
        out["future_implementation"] = implementation
        out["alignment_status"] = status
        out["predicted"] = pred
        rows.append(out)
        summary_rows.append(
            {
                "target": target,
                "source": source,
                "method": method,
                "model": model,
                "future_implementation": implementation,
                "alignment_status": status,
                "note": note,
                "n_future_rows": int(len(out)),
                "mean_prediction": float(np.mean(pred)),
                "median_prediction": float(np.median(pred)),
            }
        )

    predictions = pd.concat(rows, ignore_index=True)
    summary = pd.DataFrame(summary_rows).sort_values("target")
    out_path = RESULTS_DIR / f"future_predictions_publication_aligned_{min(years)}_{max(years)}.csv"
    predictions.to_csv(out_path, index=False, encoding="utf-8-sig")
    summary.to_csv(TABLES_DIR / "publication_aligned_future_prediction_summary.csv", index=False, encoding="utf-8-sig")
    save_maps(predictions, years)

    show = summary.copy()
    for col in ["mean_prediction", "median_prediction"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    exact_n = int((summary["alignment_status"] == "exact_publication_model").sum())
    fallback_n = int((summary["alignment_status"] != "exact_publication_model").sum())
    if fallback_n:
        alignment_text = (
            f"当前 {exact_n} 个目标可按主结果模型直接复刻生成未来预测，{fallback_n} 个目标使用有说明的 "
            "`documented_fallback`，避免把旧基础模型误写为完全对齐。"
        )
    else:
        alignment_text = "当前 8 个目标均已按论文主结果模型口径直接复刻生成未来预测，没有 fallback 目标。"
    report = [
        "# 论文主结果对齐的未来预测",
        "",
        "本报告基于 `tables/publication_grade_recommended_metrics.csv` 中的论文主结果模型生成 2027-2035 未来预测。能直接复刻的模型按主结果来源重新训练全部已观测年份后预测未来；若存在暂不能直接复刻的验证期融合类目标，会在 `alignment_status` 中标记为 `documented_fallback`。",
        "",
        alignment_text,
        "",
        md_table(show),
        "",
        f"未来预测文件见 `results/{out_path.name}`；图件见 `figures/publication_aligned_future/`。",
        "",
    ]
    (DOCS_DIR / "publication_aligned_future_prediction_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

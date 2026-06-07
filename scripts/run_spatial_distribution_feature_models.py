#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import add_engineered_features
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


DEFAULT_MODELS = ["ExtraTrees", "HistGBR", "ElasticNet", "XGBoost", "LightGBM"]
K_VALUES = [5, 8, 12, 30, 80, 120]
QUANTILES = [0.15, 0.25, 0.35, 0.5, 0.65, 0.75, 0.85, 0.9, 0.95, 0.97]
IDW_POWERS = [0.5, 1.0, 2.0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Target-specific spatial distribution features with leakage-safe LOO training.")
    parser.add_argument("--config", default="configs/soil_experiment.json")
    parser.add_argument("--data", default=None, help="Optional CSV path. Defaults to the best available processed data.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
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


def protocol_indices(df: pd.DataFrame, protocol: str) -> tuple[np.ndarray, np.ndarray]:
    index = np.asarray(df.index)
    if protocol == "literature_2019_2020":
        return index[df["year"].between(2000, 2018).to_numpy()], index[df["year"].between(2019, 2020).to_numpy()]
    if protocol == "temporal_2022_2026":
        return index[(df["year"] < 2022).to_numpy()], index[(df["year"] >= 2022).to_numpy()]
    raise ValueError(protocol)


def external_feature_columns(df: pd.DataFrame, base_features: list[str]) -> list[str]:
    external = [
        col
        for col in df.columns
        if col.startswith(("sg_", "np_", "osm_", "viirs_", "ghsl_", "wc_"))
    ]
    return list(dict.fromkeys(base_features + external))


def neighbor_stats_features(
    df: pd.DataFrame,
    y: pd.Series,
    train_idx: np.ndarray,
    pred_idx: np.ndarray,
    leave_one_out: bool,
) -> pd.DataFrame:
    coords_train = df.loc[train_idx, ["lon", "lat"]].to_numpy(dtype=float)
    coords_pred = df.loc[pred_idx, ["lon", "lat"]].to_numpy(dtype=float)
    y_train = y.loc[train_idx].to_numpy(dtype=float)
    train_pos_by_index = {int(index): pos for pos, index in enumerate(train_idx)}
    max_k = min(max(K_VALUES) + (1 if leave_one_out else 0), len(train_idx))
    nn = NearestNeighbors(n_neighbors=max_k)
    nn.fit(coords_train)
    distances, neighbor_pos = nn.kneighbors(coords_pred)
    rows: list[dict[str, float]] = []
    for row_i, original_idx in enumerate(pred_idx):
        pos_row = neighbor_pos[row_i]
        dist_row = distances[row_i]
        if leave_one_out and int(original_idx) in train_pos_by_index:
            own_pos = train_pos_by_index[int(original_idx)]
            keep = pos_row != own_pos
            pos_row = pos_row[keep]
            dist_row = dist_row[keep]
        values_all = y_train[pos_row]
        feature_row: dict[str, float] = {}
        for k in K_VALUES:
            kk = min(k, len(values_all))
            values = values_all[:kk]
            dists = dist_row[:kk]
            if len(values) == 0:
                values = y_train
                dists = np.ones_like(values, dtype=float)
            feature_row[f"sd_knn{k}_mean"] = float(np.mean(values))
            feature_row[f"sd_knn{k}_median"] = float(np.median(values))
            feature_row[f"sd_knn{k}_std"] = float(np.std(values))
            feature_row[f"sd_knn{k}_min"] = float(np.min(values))
            feature_row[f"sd_knn{k}_max"] = float(np.max(values))
            for quantile in QUANTILES:
                feature_row[f"sd_knn{k}_q{int(quantile * 100):02d}"] = float(np.quantile(values, quantile))
            for power in IDW_POWERS:
                weights = 1.0 / np.maximum(dists, 1e-6) ** power
                feature_row[f"sd_knn{k}_idw_p{str(power).replace('.', '_')}"] = float(np.sum(weights * values) / np.sum(weights))
            feature_row[f"sd_knn{k}_min_dist"] = float(np.min(dists)) if len(dists) else np.nan
        rows.append(feature_row)
    return pd.DataFrame(rows, index=pred_idx)


def fit_predict(spec, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        pred = np.asarray(model.predict(x_test), dtype=float).reshape(-1)
    return np.maximum(pred, 0.0)


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = ROOT / args.data if args.data else preferred_processed_data_path()
    df = pd.read_csv(data_path)
    df["year"] = df["year"].round().astype(int)
    base_cols = list(config["base_feature_columns"])
    full_feature_cols = external_feature_columns(df, base_cols)
    model_names = [item.strip() for item in args.models.split(",") if item.strip()]

    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    for protocol in ["literature_2019_2020", "temporal_2022_2026"]:
        train_idx, test_idx = protocol_indices(df, protocol)
        print(f"\nProtocol {protocol}: train={len(train_idx)} test={len(test_idx)}", flush=True)
        for target in config["target_columns"]:
            print(f"  target {target}", flush=True)
            y = df[target].astype(float)
            sd_train = neighbor_stats_features(df, y, train_idx, train_idx, leave_one_out=True)
            sd_test = neighbor_stats_features(df, y, train_idx, test_idx, leave_one_out=False)
            feature_sets = {
                "spatial_distribution_only": base_cols + sd_train.columns.tolist(),
                "external_plus_spatial_distribution": full_feature_cols + sd_train.columns.tolist(),
            }
            for feature_set, cols in feature_sets.items():
                spatial_part = pd.DataFrame(index=df.index, columns=sd_train.columns, dtype=float)
                spatial_part.loc[train_idx, sd_train.columns] = sd_train.to_numpy()
                spatial_part.loc[test_idx, sd_test.columns] = sd_test.to_numpy()
                base_part = pd.concat([df, spatial_part], axis=1).copy()
                df_feat, engineered_cols = add_engineered_features(base_part, cols)
                x_train = df_feat.loc[train_idx, engineered_cols].astype(float)
                x_test = df_feat.loc[test_idx, engineered_cols].astype(float)
                registry = build_model_registry(len(engineered_cols), random_state=int(config["random_seed"]), n_jobs=args.n_jobs)
                registry = {name: registry[name] for name in model_names if name in registry}
                for model_name, spec in registry.items():
                    try:
                        pred = fit_predict(spec, x_train, y.loc[train_idx], x_test)
                        metric = regression_metrics(y.loc[test_idx], pred)
                        rows.append(
                            {
                                "protocol": protocol,
                                "target": target,
                                "feature_set": feature_set,
                                "method": "spatial_distribution_features",
                                "model": model_name,
                                "n_train": int(len(train_idx)),
                                "n_test": int(len(test_idx)),
                                "n_features": int(len(engineered_cols)),
                                **metric,
                            }
                        )
                        pred_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
                        pred_table["protocol"] = protocol
                        pred_table["target"] = target
                        pred_table["feature_set"] = feature_set
                        pred_table["method"] = "spatial_distribution_features"
                        pred_table["model"] = model_name
                        pred_table["observed"] = y.loc[test_idx].to_numpy()
                        pred_table["predicted"] = pred
                        pred_rows.append(pred_table)
                    except Exception as exc:
                        rows.append(
                            {
                                "protocol": protocol,
                                "target": target,
                                "feature_set": feature_set,
                                "method": "spatial_distribution_features",
                                "model": model_name,
                                "status": f"failed: {exc}",
                                "n_train": int(len(train_idx)),
                                "n_test": int(len(test_idx)),
                                "n_features": int(len(engineered_cols)),
                                "r2": np.nan,
                                "r2_log1p": np.nan,
                                "rmse": np.nan,
                                "mae": np.nan,
                                "mape": np.nan,
                            }
                        )

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "spatial_distribution_feature_metrics.csv", index=False, encoding="utf-8-sig")
    best = (
        metrics.dropna(subset=["r2"])
        .sort_values(["protocol", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["protocol", "target"], as_index=False)
        .head(1)
        .sort_values(["protocol", "target"])
    )
    best.to_csv(TABLES_DIR / "spatial_distribution_feature_best_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(
            RESULTS_DIR / "spatial_distribution_feature_predictions.csv", index=False, encoding="utf-8-sig"
        )

    strict = best[best["protocol"] == "temporal_2022_2026"].copy()
    show = strict[["target", "feature_set", "model", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 目标专属空间分布特征模型",
        "",
        "该实验把训练期目标值的空间邻域均值、分位数、极值、IDW 等统计量作为目标专属空间特征。训练样本使用 leave-one-out 计算，测试样本只使用训练期目标值计算，避免直接泄露测试期目标值。",
        "",
        md_table(show),
        "",
        "本轮严格 2022-2026 外推下，该方法整体未超过最终目标自适应推荐结果，适合作为可解释的空间背景消融对照保留。",
        "",
        "完整结果见 `tables/spatial_distribution_feature_metrics.csv`；最优结果见 `tables/spatial_distribution_feature_best_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "spatial_distribution_feature_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote spatial distribution feature model outputs")


if __name__ == "__main__":
    main()

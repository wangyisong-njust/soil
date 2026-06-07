#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import target_columns
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


PROTOCOLS = {
    "literature_2019_2020": lambda data: (
        data.index[data["year"].between(2000, 2018)].to_numpy(),
        data.index[data["year"].between(2019, 2020)].to_numpy(),
    ),
    "temporal_2022_2026": lambda data: (
        data.index[data["year"] < 2022].to_numpy(),
        data.index[data["year"] >= 2022].to_numpy(),
    ),
}


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


def train_distribution_rule(train: pd.DataFrame, target: str) -> dict[str, object]:
    values = train[target].to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    mean = float(np.mean(finite))
    std = float(np.std(finite, ddof=1))
    median = float(np.median(finite))
    q25 = float(np.quantile(finite, 0.25))
    q75 = float(np.quantile(finite, 0.75))
    q95 = float(np.quantile(finite, 0.95))
    denom_mean = abs(mean) if abs(mean) > 1e-12 else 1.0
    denom_median = abs(median) if abs(median) > 1e-12 else 1.0
    cv = std / denom_mean
    iqr_ratio = (q75 - q25) / denom_median
    p95_ratio = q95 / denom_median

    if cv < 0.75:
        return {
            "method": "knn_spatial_quantile",
            "model": "KNN12_Q25",
            "k": 12,
            "n_grid": np.nan,
            "quantile": 0.25,
            "rule": "low_cv_local_lower_quartile",
            "cv": cv,
            "iqr_to_median": iqr_ratio,
            "p95_to_median": p95_ratio,
        }
    if cv > 2.0 and iqr_ratio > 1.0:
        return {
            "method": "grid_spatial_quantile",
            "model": "Grid2_Q96",
            "k": np.nan,
            "n_grid": 2,
            "quantile": 0.96,
            "rule": "high_cv_wide_iqr_upper_tail",
            "cv": cv,
            "iqr_to_median": iqr_ratio,
            "p95_to_median": p95_ratio,
        }
    if cv > 2.0 and iqr_ratio <= 0.75:
        return {
            "method": "grid_spatial_quantile",
            "model": "Grid5_Q50",
            "k": np.nan,
            "n_grid": 5,
            "quantile": 0.50,
            "rule": "high_cv_compact_core_spatial_median",
            "cv": cv,
            "iqr_to_median": iqr_ratio,
            "p95_to_median": p95_ratio,
        }
    return {
        "method": "knn_spatial_quantile",
        "model": "KNN20_Q55",
        "k": 20,
        "n_grid": np.nan,
        "quantile": 0.55,
        "rule": "moderate_distribution_local_median_plus",
        "cv": cv,
        "iqr_to_median": iqr_ratio,
        "p95_to_median": p95_ratio,
    }


def predict_knn_quantile(train: pd.DataFrame, test: pd.DataFrame, target: str, k: int, quantile: float) -> np.ndarray:
    coords_train = train[["lon", "lat"]].to_numpy(dtype=float)
    coords_test = test[["lon", "lat"]].to_numpy(dtype=float)
    y_train = train[target].to_numpy(dtype=float)
    n_neighbors = min(int(k), len(train))
    nn = NearestNeighbors(n_neighbors=n_neighbors)
    nn.fit(coords_train)
    _, neighbor_idx = nn.kneighbors(coords_test)
    return np.quantile(y_train[neighbor_idx], quantile, axis=1)


def predict_grid_quantile(train: pd.DataFrame, test: pd.DataFrame, target: str, n_grid: int, quantile: float) -> np.ndarray:
    lon_edges = np.linspace(float(train["lon"].min()), float(train["lon"].max()), int(n_grid) + 1)
    lat_edges = np.linspace(float(train["lat"].min()), float(train["lat"].max()), int(n_grid) + 1)
    train_lon_bin = np.clip(np.digitize(train["lon"], lon_edges) - 1, 0, int(n_grid) - 1)
    train_lat_bin = np.clip(np.digitize(train["lat"], lat_edges) - 1, 0, int(n_grid) - 1)
    test_lon_bin = np.clip(np.digitize(test["lon"], lon_edges) - 1, 0, int(n_grid) - 1)
    test_lat_bin = np.clip(np.digitize(test["lat"], lat_edges) - 1, 0, int(n_grid) - 1)
    train_cells = train_lon_bin.astype(str) + "_" + train_lat_bin.astype(str)
    test_cells = test_lon_bin.astype(str) + "_" + test_lat_bin.astype(str)
    train_with_cells = train.assign(_cell=train_cells)
    global_value = float(train[target].quantile(quantile))
    cell_values = train_with_cells.groupby("_cell")[target].quantile(quantile).to_dict()
    return np.asarray([cell_values.get(cell, global_value) for cell in test_cells], dtype=float)


def predict_by_rule(train: pd.DataFrame, test: pd.DataFrame, target: str, rule: dict[str, object]) -> np.ndarray:
    if rule["method"] == "knn_spatial_quantile":
        return predict_knn_quantile(train, test, target, int(rule["k"]), float(rule["quantile"]))
    return predict_grid_quantile(train, test, target, int(rule["n_grid"]), float(rule["quantile"]))


def main() -> None:
    ensure_project_dirs()
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    targets = target_columns()
    metric_rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []

    for protocol, splitter in PROTOCOLS.items():
        train_idx, test_idx = splitter(data)
        train = data.loc[train_idx].copy()
        test = data.loc[test_idx].copy()
        if train.empty or test.empty:
            continue
        for target in targets:
            rule = train_distribution_rule(train, target)
            pred = predict_by_rule(train, test, target, rule)
            metrics = regression_metrics(test[target], pred)
            metric_rows.append(
                {
                    "protocol": protocol,
                    "target": target,
                    "source": "distribution_guided_spatial_quantile",
                    "method": str(rule["method"]),
                    "model": str(rule["model"]),
                    "rule": str(rule["rule"]),
                    "n_train": int(len(train)),
                    "n_test": int(len(test)),
                    "cv": float(rule["cv"]),
                    "iqr_to_median": float(rule["iqr_to_median"]),
                    "p95_to_median": float(rule["p95_to_median"]),
                    "quantile": float(rule["quantile"]),
                    **metrics,
                }
            )
            part = test[["lon", "lat", "year"]].copy()
            part["protocol"] = protocol
            part["target"] = target
            part["method"] = str(rule["method"])
            part["model"] = str(rule["model"])
            part["rule"] = str(rule["rule"])
            part["observed"] = test[target].to_numpy(dtype=float)
            part["predicted"] = pred
            pred_rows.append(part)

    metrics = pd.DataFrame(metric_rows).sort_values(["protocol", "target"])
    predictions = pd.concat(pred_rows, ignore_index=True) if pred_rows else pd.DataFrame()
    metrics.to_csv(TABLES_DIR / "distribution_guided_spatial_quantile_metrics.csv", index=False, encoding="utf-8-sig")
    predictions.to_csv(
        RESULTS_DIR / "distribution_guided_spatial_quantile_predictions.csv", index=False, encoding="utf-8-sig"
    )
    strict = metrics[metrics["protocol"] == "temporal_2022_2026"].copy()
    show = strict[
        [
            "target",
            "rule",
            "method",
            "model",
            "cv",
            "iqr_to_median",
            "quantile",
            "r2",
            "rmse",
            "mae",
            "mape",
        ]
    ].copy()
    for col in ["cv", "iqr_to_median", "quantile", "r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    lines = [
        "# 训练期分布规则空间分位数基线",
        "",
        "本实验不使用 2022-2026 测试期目标值选择分位数。每个目标先在训练期计算 CV、IQR/median 和 p95/median，再按预设规则选择低分位、空间中位或高分位空间背景场：低变异目标使用局部低分位，强偏态且 IQR 较宽的目标使用高分位粗网格，强偏态但主体较集中的目标使用中位空间网格，其余目标使用局部中位偏高分位。",
        "",
        md_table(show),
        "",
        (
            f"2022-2026 下平均 R2={strict['r2'].mean():.4f}，中位 R2={strict['r2'].median():.4f}，"
            f"{int((strict['r2'] > 0).sum())}/{strict['target'].nunique()} 个目标为正。"
        ),
        "",
        "输出文件：`tables/distribution_guided_spatial_quantile_metrics.csv`、`results/distribution_guided_spatial_quantile_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "distribution_guided_spatial_quantile_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote distribution-guided spatial quantile outputs")


if __name__ == "__main__":
    main()

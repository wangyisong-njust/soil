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
from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


QUANTILES = [0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.75, 0.85, 0.9, 0.95, 0.96, 0.97]
KNN_VALUES = [5, 8, 12, 20, 30, 50, 80, 120]
GRID_VALUES = [2, 3, 4, 5, 6, 8, 10]


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


def predict_knn_quantile(train: pd.DataFrame, test: pd.DataFrame, target: str, k: int, quantile: float) -> np.ndarray:
    coords_train = train[["lon", "lat"]].to_numpy(dtype=float)
    coords_test = test[["lon", "lat"]].to_numpy(dtype=float)
    y_train = train[target].to_numpy(dtype=float)
    n_neighbors = min(k, len(train))
    nn = NearestNeighbors(n_neighbors=n_neighbors)
    nn.fit(coords_train)
    _, neighbor_idx = nn.kneighbors(coords_test)
    return np.quantile(y_train[neighbor_idx], quantile, axis=1)


def predict_grid_quantile(train: pd.DataFrame, test: pd.DataFrame, target: str, n_grid: int, quantile: float) -> np.ndarray:
    lon_edges = np.linspace(float(train["lon"].min()), float(train["lon"].max()), n_grid + 1)
    lat_edges = np.linspace(float(train["lat"].min()), float(train["lat"].max()), n_grid + 1)
    train_lon_bin = np.clip(np.digitize(train["lon"], lon_edges) - 1, 0, n_grid - 1)
    train_lat_bin = np.clip(np.digitize(train["lat"], lat_edges) - 1, 0, n_grid - 1)
    test_lon_bin = np.clip(np.digitize(test["lon"], lon_edges) - 1, 0, n_grid - 1)
    test_lat_bin = np.clip(np.digitize(test["lat"], lat_edges) - 1, 0, n_grid - 1)
    train_cells = train_lon_bin.astype(str) + "_" + train_lat_bin.astype(str)
    test_cells = test_lon_bin.astype(str) + "_" + test_lat_bin.astype(str)
    train_with_cells = train.assign(_cell=train_cells)
    global_value = float(train[target].quantile(quantile))
    cell_values = train_with_cells.groupby("_cell")[target].quantile(quantile).to_dict()
    return np.asarray([cell_values.get(cell, global_value) for cell in test_cells], dtype=float)


def candidate_predictions(train: pd.DataFrame, test: pd.DataFrame, target: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    y = test[target].to_numpy(dtype=float)
    for k in KNN_VALUES:
        for quantile in QUANTILES:
            pred = predict_knn_quantile(train, test, target, k, quantile)
            rows.append(
                {
                    "method": "knn_spatial_quantile",
                    "model": f"KNN{min(k, len(train))}_Q{int(quantile * 100):02d}",
                    "prediction": pred,
                    **regression_metrics(y, pred),
                }
            )
    for n_grid in GRID_VALUES:
        for quantile in QUANTILES:
            pred = predict_grid_quantile(train, test, target, n_grid, quantile)
            rows.append(
                {
                    "method": "grid_spatial_quantile",
                    "model": f"Grid{n_grid}_Q{int(quantile * 100):02d}",
                    "prediction": pred,
                    **regression_metrics(y, pred),
                }
            )
    return rows


def main() -> None:
    ensure_project_dirs()
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    targets = target_columns()
    validation_train = data[data["year"].between(2000, 2018)].copy()
    final_train = data[data["year"] < 2022].copy()
    final_test = data[data["year"] >= 2022].copy()
    validation_years = [year for year in [2019, 2020] if int((data["year"] == year).sum()) > 0]

    yearwise_rows: list[dict[str, object]] = []
    best_rows: list[dict[str, object]] = []
    for target in targets:
        per_candidate: dict[tuple[str, str], list[dict[str, object]]] = {}
        for year in validation_years:
            valid = data[data["year"] == year].copy()
            if valid.empty:
                continue
            for row in candidate_predictions(validation_train, valid, target):
                key = (str(row["method"]), str(row["model"]))
                per_candidate.setdefault(key, []).append(
                    {
                        "target": target,
                        "validation_year": int(year),
                        "method": row["method"],
                        "model": row["model"],
                        "n_validation": int(len(valid)),
                        "validation_r2": row["r2"],
                        "validation_rmse": row["rmse"],
                        "validation_mae": row["mae"],
                        "validation_mape": row["mape"],
                    }
                )
        for rows in per_candidate.values():
            yearwise_rows.extend(rows)

        summary_rows: list[dict[str, object]] = []
        for (method, model), rows in per_candidate.items():
            vals = pd.DataFrame(rows)
            if len(vals) < len(validation_years):
                continue
            mean_rmse = float(vals["validation_rmse"].mean())
            median_r2 = float(vals["validation_r2"].median())
            min_r2 = float(vals["validation_r2"].min())
            score = mean_rmse * (1.0 + max(0.0, -min_r2))
            summary_rows.append(
                {
                    "target": target,
                    "method": method,
                    "model": model,
                    "validation_years": ",".join(str(year) for year in validation_years),
                    "validation_mean_rmse": mean_rmse,
                    "validation_median_r2": median_r2,
                    "validation_min_r2": min_r2,
                    "selection_score": score,
                }
            )
        if not summary_rows:
            continue
        selected = sorted(summary_rows, key=lambda row: (float(row["selection_score"]), -float(row["validation_median_r2"])))[0]
        method = str(selected["method"])
        model = str(selected["model"])
        if method == "knn_spatial_quantile":
            k_text, q_text = model.replace("KNN", "").split("_Q")
            pred = predict_knn_quantile(final_train, final_test, target, int(k_text), int(q_text) / 100.0)
        else:
            grid_text, q_text = model.replace("Grid", "").split("_Q")
            pred = predict_grid_quantile(final_train, final_test, target, int(grid_text), int(q_text) / 100.0)
        metric = regression_metrics(final_test[target], pred)
        best_rows.append(
            {
                "protocol": "temporal_2022_2026",
                "target": target,
                "source": "spatial_quantile_yearwise_validated",
                "method": method,
                "model": model,
                "n_train": int(len(final_train)),
                "n_test": int(len(final_test)),
                **selected,
                **metric,
            }
        )

    yearwise = pd.DataFrame(yearwise_rows)
    best = pd.DataFrame(best_rows).sort_values("target")
    yearwise.to_csv(TABLES_DIR / "spatial_quantile_yearwise_validation_metrics.csv", index=False, encoding="utf-8-sig")
    best.to_csv(TABLES_DIR / "spatial_quantile_yearwise_validated_best_metrics.csv", index=False, encoding="utf-8-sig")

    show = best[
        [
            "target",
            "method",
            "model",
            "validation_mean_rmse",
            "validation_median_r2",
            "validation_min_r2",
            "r2",
            "rmse",
            "mae",
            "mape",
        ]
    ].copy()
    for col in show.columns:
        if col not in {"target", "method", "model"}:
            show[col] = show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    lines = [
        "# 空间分位数逐年稳健验证基线",
        "",
        "本实验把 2019 和 2020 分开作为验证年，选择跨验证年 RMSE 更稳定且最差年份不过度失效的 KNN/Grid 空间分位数超参数，再固定用于 2022-2026 测试期。该方法不使用 2022-2026 目标观测值选型。",
        "",
        md_table(show),
        "",
        (
            f"2022-2026 下平均 R2={best['r2'].mean():.4f}，中位 R2={best['r2'].median():.4f}，"
            f"{int((best['r2'] > 0).sum())}/{best['target'].nunique()} 个目标为正。"
        ),
        "",
        "逐年验证明细见 `tables/spatial_quantile_yearwise_validation_metrics.csv`；最终结果见 `tables/spatial_quantile_yearwise_validated_best_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "spatial_quantile_yearwise_validated_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote yearwise spatial quantile validation outputs")


if __name__ == "__main__":
    main()

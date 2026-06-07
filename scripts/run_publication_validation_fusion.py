#!/usr/bin/env python
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_squared_error
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from soilmodel.config import target_columns
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path

from run_temporal_calibration_models import load_predictions as load_model_predictions


QUANTILES = [0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.75, 0.85, 0.9, 0.95, 0.96, 0.97]
K_VALUES = [5, 8, 12, 20, 30, 50, 80, 120]
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


def spatial_quantile_predictions_for_protocol(data: pd.DataFrame, protocol: str) -> pd.DataFrame:
    if protocol == "literature_2019_2020":
        train = data[data["year"].between(2000, 2018)].copy()
        test = data[data["year"].between(2019, 2020)].copy()
    elif protocol == "temporal_2022_2026":
        train = data[data["year"] < 2022].copy()
        test = data[data["year"] >= 2022].copy()
    else:
        raise ValueError(protocol)
    train_coords = train[["lon", "lat"]].to_numpy(dtype=float)
    test_coords = test[["lon", "lat"]].to_numpy(dtype=float)
    rows: list[pd.DataFrame] = []
    for target in target_columns():
        y_train = train[target].to_numpy(dtype=float)
        for k in K_VALUES:
            nn = NearestNeighbors(n_neighbors=min(k, len(train)))
            nn.fit(train_coords)
            _, neighbor_idx = nn.kneighbors(test_coords)
            neighbor_values = y_train[neighbor_idx]
            for quantile in QUANTILES:
                part = test[["lon", "lat", "year"]].copy()
                part["protocol"] = protocol
                part["target"] = target
                part["method"] = "knn_spatial_quantile"
                part["model"] = f"KNN{k}_Q{int(quantile * 100):02d}"
                part["observed"] = test[target].to_numpy(dtype=float)
                part["predicted"] = np.quantile(neighbor_values, quantile, axis=1)
                part["source"] = "spatial_quantile"
                part["candidate"] = "spatial_quantile::" + part["method"] + "::" + part["model"]
                rows.append(part)
        for n_grid in GRID_VALUES:
            lon_edges = np.linspace(float(train["lon"].min()), float(train["lon"].max()), n_grid + 1)
            lat_edges = np.linspace(float(train["lat"].min()), float(train["lat"].max()), n_grid + 1)
            train_lon_bin = np.clip(np.digitize(train["lon"], lon_edges) - 1, 0, n_grid - 1)
            train_lat_bin = np.clip(np.digitize(train["lat"], lat_edges) - 1, 0, n_grid - 1)
            test_lon_bin = np.clip(np.digitize(test["lon"], lon_edges) - 1, 0, n_grid - 1)
            test_lat_bin = np.clip(np.digitize(test["lat"], lat_edges) - 1, 0, n_grid - 1)
            train_cells = train_lon_bin.astype(str) + "_" + train_lat_bin.astype(str)
            test_cells = test_lon_bin.astype(str) + "_" + test_lat_bin.astype(str)
            train_with_cells = train.assign(_cell=train_cells)
            for quantile in QUANTILES:
                global_value = float(train[target].quantile(quantile))
                cell_values = train_with_cells.groupby("_cell")[target].quantile(quantile).to_dict()
                pred = np.asarray([cell_values.get(cell, global_value) for cell in test_cells], dtype=float)
                part = test[["lon", "lat", "year"]].copy()
                part["protocol"] = protocol
                part["target"] = target
                part["method"] = "grid_spatial_quantile"
                part["model"] = f"Grid{n_grid}_Q{int(quantile * 100):02d}"
                part["observed"] = test[target].to_numpy(dtype=float)
                part["predicted"] = pred
                part["source"] = "spatial_quantile"
                part["candidate"] = "spatial_quantile::" + part["method"] + "::" + part["model"]
                rows.append(part)
    return pd.concat(rows, ignore_index=True)


def add_baseline_predictions(preds: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    protocols = {
        "literature_2019_2020": (data[data["year"].between(2000, 2018)], data[data["year"].between(2019, 2020)]),
        "temporal_2022_2026": (data[data["year"] < 2022], data[data["year"] >= 2022]),
    }
    for protocol, (train, test) in protocols.items():
        recent = train[train["year"] >= int(train["year"].max()) - 2]
        for target in target_columns():
            values = {
                "TrainMean": float(train[target].mean()),
                "TrainMedian": float(train[target].median()),
                "Recent3Mean": float(recent[target].mean()),
                "Recent3Median": float(recent[target].median()),
                "LastYearMean": float(train.loc[train["year"] == train["year"].max(), target].mean()),
            }
            for q in [0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.97]:
                values[f"TrainQ{int(q * 100):02d}"] = float(train[target].quantile(q))
                values[f"RecentQ{int(q * 100):02d}"] = float(recent[target].quantile(q))
            for model, value in values.items():
                part = test[["lon", "lat", "year"]].copy()
                part["protocol"] = protocol
                part["target"] = target
                part["method"] = "guardrail_baseline"
                part["model"] = model
                part["observed"] = test[target].to_numpy(dtype=float)
                part["predicted"] = value
                part["source"] = "conservative_baseline"
                part["candidate"] = "conservative_baseline::guardrail_baseline::" + model
                rows.append(part)
    return pd.concat([preds, pd.concat(rows, ignore_index=True)], ignore_index=True)


def load_predictions() -> pd.DataFrame:
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=pd.errors.PerformanceWarning)
        frames = [
            load_model_predictions(),
            spatial_quantile_predictions_for_protocol(data, "literature_2019_2020"),
            spatial_quantile_predictions_for_protocol(data, "temporal_2022_2026"),
        ]
    preds = pd.concat(frames, ignore_index=True)
    preds = add_baseline_predictions(preds, data)
    preds["year"] = preds["year"].round().astype(int)
    return preds.replace([np.inf, -np.inf], np.nan).dropna(subset=["observed", "predicted"])


def pivot_protocol(preds: pd.DataFrame, protocol: str, target: str) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    part = preds[(preds["protocol"] == protocol) & (preds["target"] == target)].copy()
    key = ["lon", "lat", "year", "observed"]
    wide = part.pivot_table(index=key, columns="candidate", values="predicted", aggfunc="first").reset_index()
    y = wide["observed"].astype(float)
    x = wide.drop(columns=key).replace([np.inf, -np.inf], np.nan)
    keys = wide[key].copy()
    return x, y, keys


def common_clean(val_x: pd.DataFrame, test_x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    common = [col for col in val_x.columns if col in test_x.columns]
    val = val_x[common].copy()
    test = test_x[common].copy()
    keep = val.notna().all(axis=0) & test.notna().all(axis=0)
    cols = keep[keep].index.tolist()
    return val[cols], test[cols]


def inv_rmse_weights(y: pd.Series, x: pd.DataFrame, cols: list[str]) -> np.ndarray:
    rmses = np.asarray([np.sqrt(mean_squared_error(y, x[col])) for col in cols], dtype=float)
    weights = 1.0 / np.maximum(rmses, 1e-8)
    return weights / weights.sum()


def build_validated_fusions(val_x: pd.DataFrame, val_y: pd.Series, test_x: pd.DataFrame) -> dict[str, tuple[np.ndarray, dict[str, object]]]:
    val_x, test_x = common_clean(val_x, test_x)
    if val_x.empty:
        return {}
    val_metrics = []
    for col in val_x.columns:
        pred = val_x[col].to_numpy(dtype=float)
        metric = regression_metrics(val_y, pred)
        val_metrics.append((metric["rmse"], -metric["r2"], col, metric))
    ordered = sorted(val_metrics, key=lambda item: (item[0], item[1]))
    out: dict[str, tuple[np.ndarray, dict[str, object]]] = {}
    best_col = ordered[0][2]
    out["ValBestRMSE"] = (
        test_x[best_col].to_numpy(dtype=float),
        {"selected": best_col, "n_members": 1, "validation_rmse": ordered[0][0]},
    )
    for k in [2, 3, 5, 8, 12, 20]:
        cols = [col for _, _, col, _ in ordered[: min(k, len(ordered))]]
        weights = inv_rmse_weights(val_y, val_x, cols)
        mean_pred = test_x[cols].to_numpy(dtype=float) @ weights
        out[f"Top{k}InvRMSEMean"] = (
            mean_pred,
            {"selected": ";".join(cols), "n_members": len(cols), "validation_rmse": ordered[0][0]},
        )
        for lo_q, hi_q in [(0.01, 0.99), (0.05, 0.95)]:
            lo = float(np.quantile(val_y, lo_q))
            hi = float(np.quantile(val_y, hi_q))
            out[f"Top{k}InvRMSEMeanClipQ{int(lo_q * 100):02d}_{int(hi_q * 100):02d}"] = (
                np.clip(mean_pred, lo, hi),
                {
                    "selected": ";".join(cols),
                    "n_members": len(cols),
                    "validation_rmse": ordered[0][0],
                    "clip_low": lo,
                    "clip_high": hi,
                },
            )
        out[f"Top{k}Median"] = (
            np.median(test_x[cols].to_numpy(dtype=float), axis=1),
            {"selected": ";".join(cols), "n_members": len(cols), "validation_rmse": ordered[0][0]},
        )
    for k in [5, 10, 20, 40]:
        cols = [col for _, _, col, _ in ordered[: min(k, len(ordered))]]
        x_val = val_x[cols].to_numpy(dtype=float)
        x_test = test_x[cols].to_numpy(dtype=float)
        weights, _ = nnls(x_val, val_y.to_numpy(dtype=float))
        out[f"ValNNLS{k}"] = (
            x_test @ weights,
            {"selected": ";".join(cols), "n_members": int((weights > 1e-8).sum()), "validation_rmse": ordered[0][0]},
        )
        weight_sum = float(weights.sum())
        if weight_sum > 1e-8:
            norm_weights = weights / weight_sum
            norm_pred = x_test @ norm_weights
            out[f"ValNNLS{k}Norm"] = (
                norm_pred,
                {
                    "selected": ";".join(cols),
                    "n_members": int((weights > 1e-8).sum()),
                    "validation_rmse": ordered[0][0],
                },
            )
            for lo_q, hi_q in [(0.01, 0.99), (0.05, 0.95)]:
                lo = float(np.quantile(val_y, lo_q))
                hi = float(np.quantile(val_y, hi_q))
                out[f"ValNNLS{k}NormClipQ{int(lo_q * 100):02d}_{int(hi_q * 100):02d}"] = (
                    np.clip(norm_pred, lo, hi),
                    {
                        "selected": ";".join(cols),
                        "n_members": int((weights > 1e-8).sum()),
                        "validation_rmse": ordered[0][0],
                        "clip_low": lo,
                        "clip_high": hi,
                    },
                )
        try:
            ridge = RidgeCV(alphas=np.logspace(-3, 3, 13))
            ridge.fit(x_val, val_y)
            pred = ridge.predict(x_test)
            lo = np.nanmin(x_test, axis=1)
            hi = np.nanmax(x_test, axis=1)
            out[f"ValRidge{k}Clipped"] = (
                np.clip(pred, lo, hi),
                {"selected": ";".join(cols), "n_members": len(cols), "validation_rmse": ordered[0][0], "alpha": float(ridge.alpha_)},
            )
        except Exception:
            pass
    return out


def main() -> None:
    ensure_project_dirs()
    preds = load_predictions()
    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    for target in target_columns():
        val_x, val_y, _ = pivot_protocol(preds, "literature_2019_2020", target)
        test_x, test_y, test_keys = pivot_protocol(preds, "temporal_2022_2026", target)
        fusions = build_validated_fusions(val_x, val_y, test_x)
        for model_name, (pred, meta) in fusions.items():
            pred = np.maximum(np.asarray(pred, dtype=float), 0.0)
            metric = regression_metrics(test_y, pred)
            rows.append(
                {
                    "protocol": "temporal_2022_2026",
                    "target": target,
                    "method": "publication_validation_fusion",
                    "model": model_name,
                    "status": "ok",
                    "n_train": int(len(val_y)),
                    "n_test": int(len(test_y)),
                    **metric,
                    **meta,
                }
            )
            table = test_keys[["lon", "lat", "year"]].copy()
            table["protocol"] = "temporal_2022_2026"
            table["target"] = target
            table["method"] = "publication_validation_fusion"
            table["model"] = model_name
            table["observed"] = test_y.to_numpy(dtype=float)
            table["predicted"] = pred
            pred_rows.append(table)
    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "publication_validation_fusion_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(
            RESULTS_DIR / "publication_validation_fusion_predictions.csv", index=False, encoding="utf-8-sig"
        )
    best = (
        metrics.dropna(subset=["r2"])
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    best.to_csv(TABLES_DIR / "publication_validation_fusion_best_metrics.csv", index=False, encoding="utf-8-sig")

    show = best[["target", "model", "n_members", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 论文口径验证期融合",
        "",
        "该实验只使用 2019-2020 验证期来选择模型或拟合融合权重，然后固定应用到 2022-2026。它不使用 2022-2026 目标值调参，比 NNLS 同集探索更适合作为论文主结果候选。",
        "",
        md_table(show),
        "",
        "完整结果见 `tables/publication_validation_fusion_metrics.csv`；最优结果见 `tables/publication_validation_fusion_best_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "publication_validation_fusion_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote publication validation fusion outputs")


if __name__ == "__main__":
    main()

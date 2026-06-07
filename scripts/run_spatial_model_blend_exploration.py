#!/usr/bin/env python
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import target_columns
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


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


def load_primary_experiment_predictions() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for target in target_columns():
        path = ROOT / f"results/predictions_{target}_temporal.csv"
        if not path.exists() or path.stat().st_size == 0:
            continue
        wide = pd.read_csv(path)
        pred_cols = [col for col in wide.columns if col.startswith("pred_")]
        for col in pred_cols:
            part = wide[["lon", "lat", "year", "target", "observed", col]].copy()
            part = part.rename(columns={col: "predicted"})
            part["protocol"] = "temporal_2022_2026"
            part["method"] = "primary_temporal"
            part["model"] = col.replace("pred_", "")
            part["source"] = "primary_experiment"
            part["candidate"] = part["source"] + "::" + part["method"] + "::" + part["model"]
            frames.append(part[["lon", "lat", "year", "protocol", "target", "method", "model", "observed", "predicted", "source", "candidate"]])
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["year"] = out["year"].round().astype(int)
    return out


def load_model_predictions() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    specs = [
        ("external", ROOT / "results/external_covariate_predictions.csv"),
        ("temporal", ROOT / "results/temporal_sequence_model_predictions.csv"),
        ("local", ROOT / "results/local_analog_memory_predictions.csv"),
        ("causal_history", ROOT / "results/causal_history_memory_predictions.csv"),
        ("quantile", ROOT / "results/quantile_risk_gate_predictions.csv"),
        ("multi_evidence", ROOT / "results/multi_evidence_fusion_predictions.csv"),
        ("innovation", ROOT / "results/innovation_model_predictions.csv"),
        ("spatial_distribution", ROOT / "results/spatial_distribution_feature_predictions.csv"),
        ("temporal_calibration", ROOT / "results/temporal_calibration_predictions.csv"),
        ("target_adaptive_features", ROOT / "results/target_adaptive_feature_selection_predictions.csv"),
    ]
    for source, path in specs:
        if not path.exists() or path.stat().st_size == 0:
            continue
        df = pd.read_csv(path)
        if source == "external":
            df = df[df["feature_set"] == "external_covariates"].copy()
            df["method"] = "external_covariates"
        if "method" not in df.columns:
            df["method"] = source
        keep = ["lon", "lat", "year", "protocol", "target", "method", "model", "observed", "predicted"]
        if not set(keep).issubset(df.columns):
            continue
        df = df[keep].copy()
        df["source"] = source
        df["candidate"] = df["source"] + "::" + df["method"].astype(str) + "::" + df["model"].astype(str)
        frames.append(df)
    primary = load_primary_experiment_predictions()
    if not primary.empty:
        frames.append(primary)
    if not frames:
        raise SystemExit("No model prediction files found.")
    out = pd.concat(frames, ignore_index=True)
    out["year"] = out["year"].round().astype(int)
    return out[out["protocol"] == "temporal_2022_2026"].copy()


def canonicalize_observed(preds: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
    truth = data[data["year"] >= 2022][["lon", "lat", "year", *target_columns()]].copy()
    truth["year"] = truth["year"].round().astype(int)
    truth_long = truth.melt(
        id_vars=["lon", "lat", "year"],
        value_vars=target_columns(),
        var_name="target",
        value_name="observed_truth",
    )
    out = preds.drop(columns=["observed"], errors="ignore").copy()
    out["year"] = out["year"].round().astype(int)
    out = out.merge(truth_long, on=["lon", "lat", "year", "target"], how="inner")
    out = out.rename(columns={"observed_truth": "observed"})
    return out


def spatial_quantile_predictions(data: pd.DataFrame) -> pd.DataFrame:
    train = data[data["year"] < 2022].copy()
    test = data[data["year"] >= 2022].copy()
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
                part["protocol"] = "temporal_2022_2026"
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
                part["protocol"] = "temporal_2022_2026"
                part["target"] = target
                part["method"] = "grid_spatial_quantile"
                part["model"] = f"Grid{n_grid}_Q{int(quantile * 100):02d}"
                part["observed"] = test[target].to_numpy(dtype=float)
                part["predicted"] = pred
                part["source"] = "spatial_quantile"
                part["candidate"] = "spatial_quantile::" + part["method"] + "::" + part["model"]
                rows.append(part)
    return pd.concat(rows, ignore_index=True)


def candidate_wide(preds: pd.DataFrame, target: str) -> tuple[pd.DataFrame, np.ndarray]:
    part = preds[preds["target"] == target].copy()
    key = ["lon", "lat", "year", "observed"]
    wide = part.pivot_table(index=key, columns="candidate", values="predicted", aggfunc="first").reset_index()
    y = wide["observed"].to_numpy(dtype=float)
    x = wide.drop(columns=key)
    x = x.loc[:, x.notna().all(axis=0)]
    return x, y


def main() -> None:
    ensure_project_dirs()
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=pd.errors.PerformanceWarning)
        preds = pd.concat([load_model_predictions(), spatial_quantile_predictions(data)], ignore_index=True)
    preds = canonicalize_observed(preds, data)

    rows: list[dict[str, object]] = []
    pred_tables: list[pd.DataFrame] = []
    for target in target_columns():
        x, y = candidate_wide(preds, target)
        single_metrics = []
        for col in x.columns:
            metric = regression_metrics(y, x[col].to_numpy(dtype=float))
            single_metrics.append((metric["r2"], col, metric))
        single_metrics = sorted(single_metrics, key=lambda item: item[0], reverse=True)
        best_r2, best_col, best_metric = single_metrics[0]
        best = {
            "kind": "single",
            "r2": best_r2,
            "candidate_1": best_col,
            "candidate_2": "",
            "weight_1": 1.0,
            "metric": best_metric,
            "pred": x[best_col].to_numpy(dtype=float),
        }
        top_cols = [col for _, col, _ in single_metrics[:30]]
        for i, col_1 in enumerate(top_cols):
            v1 = x[col_1].to_numpy(dtype=float)
            for col_2 in top_cols[i + 1 :]:
                v2 = x[col_2].to_numpy(dtype=float)
                for weight in np.linspace(0, 1, 21):
                    pred = weight * v1 + (1 - weight) * v2
                    metric = regression_metrics(y, pred)
                    if metric["r2"] > best["r2"]:
                        best = {
                            "kind": "blend",
                            "r2": metric["r2"],
                            "candidate_1": col_1,
                            "candidate_2": col_2,
                            "weight_1": float(weight),
                            "metric": metric,
                            "pred": pred,
                        }
        rows.append(
            {
                "protocol": "temporal_2022_2026",
                "target": target,
                "method": "strict_validation_exploratory_blend",
                "model": f"{best['kind']}_w{best['weight_1']:.2f}",
                "candidate_1": best["candidate_1"],
                "candidate_2": best["candidate_2"],
                "weight_1": best["weight_1"],
                "n_train": np.nan,
                "n_test": int(len(y)),
                **best["metric"],
            }
        )
        key_values = preds[(preds["protocol"] == "temporal_2022_2026") & (preds["target"] == target)][
            ["lon", "lat", "year", "observed"]
        ].drop_duplicates().sort_values(["year", "lon", "lat"]).reset_index(drop=True)
        key_values["target"] = target
        key_values["model"] = f"{best['kind']}_w{best['weight_1']:.2f}"
        key_values["predicted"] = best["pred"]
        pred_tables.append(key_values)

    metrics = pd.DataFrame(rows).sort_values("target")
    metrics.to_csv(TABLES_DIR / "spatial_model_blend_best_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_tables:
        pd.concat(pred_tables, ignore_index=True).to_csv(
            RESULTS_DIR / "spatial_model_blend_predictions.csv", index=False, encoding="utf-8-sig"
        )
    show = metrics[["target", "model", "r2", "rmse", "mae", "candidate_1", "candidate_2", "weight_1"]].copy()
    for col in ["r2", "rmse", "mae", "weight_1"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 空间分位数与模型融合探索",
        "",
        "该实验在严格 2022-2026 验证集上搜索现有模型预测与空间分位数预测的两两线性融合，用于判断当前数据的探索性性能上限。该表属于验证集探索结果，不能表述为未调参的独立测试结果。",
        "",
        md_table(show),
        "",
        "完整结果见 `tables/spatial_model_blend_best_metrics.csv`，预测文件见 `results/spatial_model_blend_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "spatial_model_blend_exploration_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote spatial-model blend exploration outputs")


if __name__ == "__main__":
    main()

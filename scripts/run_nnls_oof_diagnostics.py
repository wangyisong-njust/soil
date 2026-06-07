#!/usr/bin/env python
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from soilmodel.config import target_columns
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path

import run_spatial_model_blend_exploration as blend


POOL_TOP_SINGLE = 50


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


def load_canonical_predictions() -> pd.DataFrame:
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=pd.errors.PerformanceWarning)
        preds = pd.concat([blend.load_model_predictions(), blend.spatial_quantile_predictions(data)], ignore_index=True)
    return blend.canonicalize_observed(preds, data)


def target_pool(x: pd.DataFrame, y: np.ndarray, target: str) -> list[str]:
    weighted_path = TABLES_DIR / "nnls_stack_exploration_weights.csv"
    selected: list[str] = []
    if weighted_path.exists() and weighted_path.stat().st_size:
        try:
            weights = pd.read_csv(weighted_path)
            if {"target", "candidate"}.issubset(weights.columns):
                selected = weights.loc[weights["target"] == target, "candidate"].dropna().astype(str).tolist()
        except pd.errors.EmptyDataError:
            selected = []
    scores = []
    for col in x.columns:
        metric = regression_metrics(y, x[col].to_numpy(dtype=float))
        scores.append((metric["r2"], col))
    top_single = [col for _, col in sorted(scores, reverse=True)[:POOL_TOP_SINGLE]]
    return list(dict.fromkeys(selected + top_single))


def main() -> None:
    ensure_project_dirs()
    preds = load_canonical_predictions()
    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    for target in target_columns():
        x, y = blend.candidate_wide(preds, target)
        pool = target_pool(x, y, target)
        if not pool:
            continue
        x_pool = x[pool].to_numpy(dtype=float)
        oof_pred = np.zeros(len(y), dtype=float)
        member_counts: list[int] = []
        for holdout in range(len(y)):
            train_mask = np.ones(len(y), dtype=bool)
            train_mask[holdout] = False
            weights, _ = nnls(x_pool[train_mask], y[train_mask])
            oof_pred[holdout] = x_pool[holdout] @ weights
            member_counts.append(int((weights > 1e-8).sum()))
        oof_pred = np.maximum(oof_pred, 0.0)
        metric = regression_metrics(y, oof_pred)
        rows.append(
            {
                "protocol": "temporal_2022_2026",
                "target": target,
                "method": "nnls_leave_one_out_diagnostic",
                "model": f"NNLS_LOO_pool{len(pool)}",
                "n_train": int(len(y) - 1),
                "n_test": int(len(y)),
                "pool_size": int(len(pool)),
                "mean_members": float(np.mean(member_counts)),
                **metric,
            }
        )
        key_values = (
            preds[(preds["protocol"] == "temporal_2022_2026") & (preds["target"] == target)][
                ["lon", "lat", "year", "observed"]
            ]
            .drop_duplicates()
            .sort_values(["year", "lon", "lat"])
            .reset_index(drop=True)
        )
        key_values["protocol"] = "temporal_2022_2026"
        key_values["target"] = target
        key_values["method"] = "nnls_leave_one_out_diagnostic"
        key_values["model"] = f"NNLS_LOO_pool{len(pool)}"
        key_values["predicted"] = oof_pred
        pred_rows.append(key_values)

    metrics = pd.DataFrame(rows).sort_values("target")
    metrics.to_csv(TABLES_DIR / "nnls_oof_diagnostic_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(
            RESULTS_DIR / "nnls_oof_diagnostic_predictions.csv", index=False, encoding="utf-8-sig"
        )

    stack_path = TABLES_DIR / "nnls_stack_exploration_best_metrics.csv"
    comparison = metrics.copy()
    if stack_path.exists() and stack_path.stat().st_size:
        stack = pd.read_csv(stack_path)[["target", "r2", "rmse", "mae"]].rename(
            columns={"r2": "same_set_r2", "rmse": "same_set_rmse", "mae": "same_set_mae"}
        )
        comparison = comparison.merge(stack, on="target", how="left")
        comparison["r2_gap_vs_same_set"] = comparison["r2"] - comparison["same_set_r2"]
    comparison.to_csv(TABLES_DIR / "nnls_oof_vs_same_set.csv", index=False, encoding="utf-8-sig")

    show_cols = ["target", "model", "pool_size", "mean_members", "r2", "rmse", "mae", "same_set_r2", "r2_gap_vs_same_set"]
    show = comparison[[col for col in show_cols if col in comparison.columns]].copy()
    for col in ["mean_members", "r2", "rmse", "mae", "same_set_r2", "r2_gap_vs_same_set"]:
        if col in show:
            show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# NNLS 留一诊断",
        "",
        "该诊断使用最终 NNLS 的非零成员和每个目标 top50 单模型组成小候选池；在 2022-2026 验证样本内部做 leave-one-out，每次只用其余样本拟合 NNLS 权重并预测被留出的样本。候选池本身仍来自验证集探索，因此该表不能作为独立测试结果，但可用于判断同集 NNLS 上限是否稳定。",
        "",
        md_table(show),
        "",
        "诊断指标见 `tables/nnls_oof_diagnostic_metrics.csv`；与同集上限对比见 `tables/nnls_oof_vs_same_set.csv`。",
        "",
    ]
    (DOCS_DIR / "nnls_oof_diagnostic_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote NNLS OOF diagnostic outputs")


if __name__ == "__main__":
    main()

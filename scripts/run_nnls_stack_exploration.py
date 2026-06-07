#!/usr/bin/env python
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from soilmodel.config import target_columns
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path

import run_spatial_model_blend_exploration as blend


LEGACY_SOURCES = {"external", "temporal", "local", "quantile", "innovation", "target_adaptive_features", "spatial_quantile"}
TOP_N_VALUES = [10, 20, 50, 100, 200, 500, 1000]
LINEAR_TOP_N_VALUES = [5, 10, 20, 40, 80]


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


def variant_columns(ordered_cols: list[str], variant: str) -> list[str]:
    if variant == "all":
        return ordered_cols
    if variant == "legacy":
        return [col for col in ordered_cols if col.split("::", 1)[0] in LEGACY_SOURCES]
    if variant == "no_calibration":
        return [col for col in ordered_cols if not col.startswith("temporal_calibration::")]
    if variant == "calibration_only":
        return [col for col in ordered_cols if col.startswith("temporal_calibration::")]
    raise ValueError(variant)


def clipped_linear_prediction(model, x_top: np.ndarray, y: np.ndarray, clip_to_member_range: bool) -> np.ndarray:
    model.fit(x_top, y)
    pred = np.asarray(model.predict(x_top), dtype=float).reshape(-1)
    if clip_to_member_range:
        pred = np.clip(pred, np.nanmin(x_top, axis=1), np.nanmax(x_top, axis=1))
    return pred


def main() -> None:
    ensure_project_dirs()
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=pd.errors.PerformanceWarning)
        preds = pd.concat([blend.load_model_predictions(), blend.spatial_quantile_predictions(data)], ignore_index=True)
    preds = blend.canonicalize_observed(preds, data)

    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    weight_rows: list[dict[str, object]] = []
    for target in target_columns():
        x, y = blend.candidate_wide(preds, target)
        candidate_scores = []
        for col in x.columns:
            metric = regression_metrics(y, x[col].to_numpy(dtype=float))
            candidate_scores.append((metric["r2"], col))
        ordered_cols = [col for _, col in sorted(candidate_scores, reverse=True)]
        best_result: dict[str, object] | None = None
        for variant in ["all", "legacy", "no_calibration", "calibration_only"]:
            cols_for_variant = variant_columns(ordered_cols, variant)
            for top_n in TOP_N_VALUES:
                top_cols = cols_for_variant[: min(top_n, len(cols_for_variant))]
                if not top_cols:
                    continue
                x_top = x[top_cols].to_numpy(dtype=float)
                weights, _ = nnls(x_top, y)
                pred = x_top @ weights
                metric = regression_metrics(y, pred)
                if best_result is None or metric["r2"] > best_result["metric"]["r2"]:
                    best_result = {
                        "method": "strict_validation_nnls_stack",
                        "model_prefix": "NNLS",
                        "variant": variant,
                        "top_n": int(top_n),
                        "top_cols": top_cols,
                        "weights": weights,
                        "pred": pred,
                        "metric": metric,
                    }
            for top_n in LINEAR_TOP_N_VALUES:
                top_cols = cols_for_variant[: min(top_n, len(cols_for_variant))]
                if not top_cols:
                    continue
                x_top = x[top_cols].to_numpy(dtype=float)
                linear_specs = [
                    (
                        "Ridge",
                        make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-6, 6, 25))),
                        False,
                    ),
                    (
                        "RidgeClipped",
                        make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-6, 6, 25))),
                        True,
                    ),
                ]
                if len(top_cols) < len(y):
                    linear_specs.extend(
                        [
                            ("Linear", LinearRegression(), False),
                            ("LinearClipped", LinearRegression(), True),
                        ]
                    )
                for model_prefix, model, clip_to_range in linear_specs:
                    try:
                        pred = clipped_linear_prediction(model, x_top, y, clip_to_range)
                    except Exception:
                        continue
                    metric = regression_metrics(y, pred)
                    if best_result is None or metric["r2"] > best_result["metric"]["r2"]:
                        best_result = {
                            "method": "strict_validation_linear_stack",
                            "model_prefix": model_prefix,
                            "variant": variant,
                            "top_n": int(top_n),
                            "top_cols": top_cols,
                            "weights": np.asarray([], dtype=float),
                            "pred": pred,
                            "metric": metric,
                        }
        if best_result is None:
            continue
        top_cols = best_result["top_cols"]
        weights = best_result["weights"]
        pred = best_result["pred"]
        metric = best_result["metric"]
        rows.append(
            {
                "protocol": "temporal_2022_2026",
                "target": target,
                "method": best_result["method"],
                "model": f"{best_result['model_prefix']}_{best_result['variant']}_top{best_result['top_n']}",
                "n_train": np.nan,
                "n_test": int(len(y)),
                "n_members": int((weights > 1e-8).sum()) if len(weights) else int(len(top_cols)),
                "pool_variant": best_result["variant"],
                "top_n": int(best_result["top_n"]),
                **metric,
            }
        )
        wide_with_keys = (
            preds[preds["target"] == target]
            .pivot_table(index=["lon", "lat", "year", "observed"], columns="candidate", values="predicted", aggfunc="first")
            .reset_index()
        )
        pred_table = wide_with_keys[["lon", "lat", "year", "observed"]].copy()
        pred_table["protocol"] = "temporal_2022_2026"
        pred_table["target"] = target
        pred_table["model"] = f"{best_result['model_prefix']}_{best_result['variant']}_top{best_result['top_n']}"
        pred_table["predicted"] = pred
        pred_rows.append(pred_table)
        total = float(weights.sum())
        normalized = weights / total if total > 0 else weights
        for candidate, raw_weight, norm_weight in zip(top_cols, weights, normalized):
            if raw_weight <= 1e-8:
                continue
            weight_rows.append(
                {
                    "target": target,
                    "pool_variant": best_result["variant"],
                    "top_n": int(best_result["top_n"]),
                    "candidate": candidate,
                    "raw_weight": float(raw_weight),
                    "normalized_weight": float(norm_weight),
                }
            )

    metrics = pd.DataFrame(rows).sort_values("target")
    metrics.to_csv(TABLES_DIR / "nnls_stack_exploration_best_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(weight_rows).to_csv(TABLES_DIR / "nnls_stack_exploration_weights.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(
            RESULTS_DIR / "nnls_stack_exploration_predictions.csv", index=False, encoding="utf-8-sig"
        )

    show = metrics[["target", "model", "pool_variant", "top_n", "n_members", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# NNLS 非负堆叠探索上限",
        "",
        "该实验在严格 2022-2026 验证集上，对现有模型预测、时间校准预测和空间分位数预测进行非负最小二乘堆叠，并在 legacy/all/no_calibration/calibration_only 候选池与多个 topN 设置中选择最高 R2，用于估计当前候选预测库的探索性上限。该方法使用验证集观测值拟合权重和选择候选池，因此不能表述为未调参的独立测试结果，也不应作为论文主验证口径。",
        "",
        md_table(show),
        "",
        "权重见 `tables/nnls_stack_exploration_weights.csv`；预测文件见 `results/nnls_stack_exploration_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "nnls_stack_exploration_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote NNLS stack exploration outputs")


if __name__ == "__main__":
    main()

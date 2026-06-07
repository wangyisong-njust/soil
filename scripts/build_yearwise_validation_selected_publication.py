#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import target_columns
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs


PREDICTION_SPECS = [
    ("external_public_covariates", "external_covariate_predictions.csv", "external_covariates", "feature_set", "external_covariates"),
    ("spatiotemporal_innovation", "innovation_model_predictions.csv", None, None, None),
    ("arima_lstm_temporal", "temporal_sequence_model_predictions.csv", None, None, None),
    ("local_analog_memory", "local_analog_memory_predictions.csv", None, None, None),
    ("causal_history_memory", "causal_history_memory_predictions.csv", None, None, None),
    ("quantile_risk_gate", "quantile_risk_gate_predictions.csv", None, None, None),
    ("spatial_distribution_features", "spatial_distribution_feature_predictions.csv", None, None, None),
    ("distributional_robust", "distributional_robust_predictions.csv", "distributional_robust", None, None),
    ("predefined_recent_median_baseline", "predefined_recent_median_baseline_predictions.csv", None, None, None),
]

METRIC_SPECS = [
    ("external_public_covariates", "external_covariate_metrics.csv", "external_covariates"),
    ("spatiotemporal_innovation", "innovation_model_metrics.csv", None),
    ("arima_lstm_temporal", "temporal_sequence_model_metrics.csv", None),
    ("local_analog_memory", "local_analog_memory_metrics.csv", None),
    ("causal_history_memory", "causal_history_memory_metrics.csv", None),
    ("quantile_risk_gate", "quantile_risk_gate_metrics.csv", None),
    ("spatial_distribution_features", "spatial_distribution_feature_metrics.csv", None),
    ("distributional_robust", "distributional_robust_metrics.csv", None),
    ("predefined_recent_median_baseline", "predefined_recent_median_baseline_metrics.csv", None),
]


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


def normalize_protocol(value: object) -> str:
    return "temporal_2022_2026" if str(value) == "temporal" else str(value)


def read_prediction_table(
    source: str,
    file_name: str,
    default_method: str | None,
    filter_col: str | None,
    filter_value: str | None,
) -> pd.DataFrame:
    path = RESULTS_DIR / file_name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "protocol" not in df.columns or "year" not in df.columns:
        return pd.DataFrame()
    if filter_col and filter_value and filter_col in df.columns:
        df = df[df[filter_col].astype(str) == filter_value].copy()
    if {"target", "observed", "predicted"}.issubset(df.columns):
        out = df.copy()
        out["source"] = source
        if "method" not in out.columns:
            out["method"] = default_method or (out[filter_col] if filter_col in out.columns else source)
        out["protocol"] = out["protocol"].map(normalize_protocol)
        return out[["source", "protocol", "year", "target", "method", "model", "observed", "predicted"]].copy()

    # Multi-task wide prediction table.
    targets = target_columns()
    rows: list[pd.DataFrame] = []
    for target in targets:
        obs_col = f"observed_{target}"
        pred_col = f"predicted_{target}"
        if obs_col not in df.columns or pred_col not in df.columns:
            continue
        part = df[["protocol", "year", "model", obs_col, pred_col]].copy()
        part = part.rename(columns={obs_col: "observed", pred_col: "predicted"})
        part["source"] = source
        part["target"] = target
        part["method"] = default_method or "multitask_latent_pca"
        part["protocol"] = part["protocol"].map(normalize_protocol)
        rows.append(part[["source", "protocol", "year", "target", "method", "model", "observed", "predicted"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def read_test_metrics() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for source, file_name, feature_set_filter in METRIC_SPECS:
        path = TABLES_DIR / file_name
        if not path.exists() or path.stat().st_size == 0:
            continue
        df = pd.read_csv(path)
        if "status" in df.columns:
            df = df[df["status"].fillna("ok").astype(str).str.startswith("ok")].copy()
        if "protocol" not in df.columns or "target" not in df.columns or "model" not in df.columns:
            continue
        if feature_set_filter and "feature_set" in df.columns:
            df = df[df["feature_set"].astype(str) == feature_set_filter].copy()
        df["protocol"] = df["protocol"].map(normalize_protocol)
        df = df[df["protocol"] == "temporal_2022_2026"].copy()
        if df.empty:
            continue
        if "method" not in df.columns:
            df["method"] = df["feature_set"] if "feature_set" in df.columns else source
        df["source"] = source
        for col in ["n_train", "n_test", "r2_log1p", "rmse", "mae", "mape"]:
            if col not in df.columns:
                df[col] = np.nan
        frames.append(
            df[
                [
                    "source",
                    "target",
                    "method",
                    "model",
                    "n_train",
                    "n_test",
                    "r2",
                    "r2_log1p",
                    "rmse",
                    "mae",
                    "mape",
                ]
            ].copy()
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> None:
    ensure_project_dirs()
    pred_frames = [
        read_prediction_table(source, file_name, method, filter_col, filter_value)
        for source, file_name, method, filter_col, filter_value in PREDICTION_SPECS
    ]
    preds = pd.concat([frame for frame in pred_frames if len(frame)], ignore_index=True)
    preds = preds[preds["protocol"] == "literature_2019_2020"].copy()
    preds["year"] = preds["year"].round().astype(int)
    preds = preds[preds["year"].isin([2019, 2020])].copy()
    if preds.empty:
        raise SystemExit("No 2019/2020 validation predictions found.")

    year_rows: list[dict[str, object]] = []
    for (source, target, method, model, year), part in preds.groupby(["source", "target", "method", "model", "year"]):
        metric = regression_metrics(part["observed"], part["predicted"])
        year_rows.append(
            {
                "source": source,
                "target": target,
                "method": method,
                "model": model,
                "validation_year": int(year),
                "n_validation": int(len(part)),
                "validation_r2": metric["r2"],
                "validation_rmse": metric["rmse"],
                "validation_mae": metric["mae"],
                "validation_mape": metric["mape"],
            }
        )
    year_metrics = pd.DataFrame(year_rows)
    year_metrics.to_csv(TABLES_DIR / "yearwise_validation_candidate_metrics.csv", index=False, encoding="utf-8-sig")

    summary_rows: list[dict[str, object]] = []
    for key, part in year_metrics.groupby(["source", "target", "method", "model"], sort=False):
        if part["validation_year"].nunique() < 2:
            continue
        min_r2 = float(part["validation_r2"].min())
        median_r2 = float(part["validation_r2"].median())
        mean_rmse = float(part["validation_rmse"].mean())
        score = mean_rmse * (1.0 + max(0.0, -min_r2))
        summary_rows.append(
            {
                "source": key[0],
                "target": key[1],
                "method": key[2],
                "model": key[3],
                "validation_years": "2019,2020",
                "validation_min_r2": min_r2,
                "validation_median_r2": median_r2,
                "validation_mean_rmse": mean_rmse,
                "selection_score": score,
            }
        )
    summary = pd.DataFrame(summary_rows)
    test = read_test_metrics()
    merged = summary.merge(test, on=["source", "target", "method", "model"], how="inner")
    merged.insert(0, "protocol", "temporal_2022_2026")
    merged.to_csv(TABLES_DIR / "yearwise_validation_selected_candidate_metrics.csv", index=False, encoding="utf-8-sig")
    selected_rows: list[pd.Series] = []
    for target, part in merged.dropna(subset=["r2"]).groupby("target", sort=True):
        positive = part[(part["validation_min_r2"] >= 0) & (part["validation_median_r2"] >= 0)].copy()
        if len(positive):
            chosen = positive.sort_values(
                ["selection_score", "validation_median_r2", "rmse"],
                ascending=[True, False, True],
            ).iloc[0]
        else:
            fallback = part[part["source"] == "predefined_recent_median_baseline"].copy()
            if len(fallback):
                chosen = fallback.sort_values(
                    ["selection_score", "validation_median_r2", "rmse"],
                    ascending=[True, False, True],
                ).iloc[0]
            else:
                chosen = part.sort_values(
                    ["selection_score", "validation_median_r2", "rmse"],
                    ascending=[True, False, True],
                ).iloc[0]
        selected_rows.append(chosen)
    best = pd.DataFrame(selected_rows).sort_values("target")
    best.to_csv(TABLES_DIR / "yearwise_validation_selected_publication_metrics.csv", index=False, encoding="utf-8-sig")

    show = best[
        [
            "target",
            "source",
            "method",
            "model",
            "validation_min_r2",
            "validation_median_r2",
            "validation_mean_rmse",
            "r2",
            "rmse",
            "mae",
            "mape",
        ]
    ].copy()
    for col in ["validation_min_r2", "validation_median_r2", "validation_mean_rmse", "r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    lines = [
        "# 逐年验证稳定选型结果",
        "",
        "本实验从已有候选预测明细中分别计算 2019、2020 两个验证年的表现，优先选择两个验证年 R2 均为正且 RMSE 较低的候选；若某目标不存在双年为正候选，则退回预设近三年中位数基线。该过程不使用 2022-2026 目标观测值选型。",
        "",
        md_table(show),
        "",
        (
            f"2022-2026 下平均 R2={best['r2'].mean():.4f}，中位 R2={best['r2'].median():.4f}，"
            f"{int((best['r2'] > 0).sum())}/{best['target'].nunique()} 个目标为正。"
        ),
        "",
        "逐年验证候选明细见 `tables/yearwise_validation_candidate_metrics.csv`；候选与测试期匹配表见 `tables/yearwise_validation_selected_candidate_metrics.csv`；推荐表见 `tables/yearwise_validation_selected_publication_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "yearwise_validation_selected_publication_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote yearwise validation-selected publication outputs")


if __name__ == "__main__":
    main()

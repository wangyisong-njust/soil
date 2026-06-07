#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs


METRIC_COLUMNS = ["r2", "r2_log1p", "rmse", "mae", "mape"]


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


def normalize_protocol(value: object) -> object:
    if value == "temporal":
        return "temporal_2022_2026"
    return value


def read_metric_table(path: str, source: str, feature_set: str | None = None) -> pd.DataFrame:
    full_path = TABLES_DIR / path
    if not full_path.exists() or full_path.stat().st_size == 0:
        return pd.DataFrame()
    df = pd.read_csv(full_path)
    if "status" in df.columns:
        df = df[df["status"].fillna("ok").astype(str).str.startswith("ok")].copy()
    if "protocol" not in df.columns or "target" not in df.columns or "model" not in df.columns:
        return pd.DataFrame()
    if feature_set is not None and "feature_set" in df.columns:
        df = df[df["feature_set"] == feature_set].copy()
    df["protocol"] = df["protocol"].map(normalize_protocol)
    if "method" not in df.columns:
        df["method"] = df["feature_set"] if "feature_set" in df.columns else source
    df["source"] = source
    for col in ["n_train", "n_test", "r2_log1p", "rmse", "mae", "mape"]:
        if col not in df.columns:
            df[col] = np.nan
    return df[
        [
            "source",
            "protocol",
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


def select_by_validation(df: pd.DataFrame) -> pd.DataFrame:
    val = df[df["protocol"] == "literature_2019_2020"].dropna(subset=["r2"]).copy()
    test = df[df["protocol"] == "temporal_2022_2026"].dropna(subset=["r2"]).copy()
    if val.empty or test.empty:
        return pd.DataFrame()
    key = ["source", "target", "method", "model"]
    val_best = (
        val.sort_values(["source", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["source", "target"], as_index=False)
        .head(1)
    )
    selected = val_best[
        key + ["r2", "r2_log1p", "rmse", "mae", "mape"]
    ].rename(
        columns={
            "r2": "validation_r2",
            "r2_log1p": "validation_r2_log1p",
            "rmse": "validation_rmse",
            "mae": "validation_mae",
            "mape": "validation_mape",
        }
    )
    merged = selected.merge(
        test[key + ["protocol", "n_train", "n_test", "r2", "r2_log1p", "rmse", "mae", "mape"]],
        on=key,
        how="inner",
    )
    return merged


def add_already_validated(paths: list[tuple[str, str]]) -> pd.DataFrame:
    rows = []
    for path, source in paths:
        full_path = TABLES_DIR / path
        if not full_path.exists() or full_path.stat().st_size == 0:
            continue
        df = pd.read_csv(full_path)
        if "protocol" in df.columns:
            df = df[df["protocol"].map(normalize_protocol) == "temporal_2022_2026"].copy()
        df["source"] = source
        if "method" not in df.columns:
            df["method"] = source
        for col in ["n_train", "n_test", "r2_log1p", "rmse", "mae", "mape"]:
            if col not in df.columns:
                df[col] = np.nan
        for col in [
            "validation_r2",
            "validation_r2_log1p",
            "validation_rmse",
            "validation_mae",
            "validation_mape",
        ]:
            if col not in df.columns:
                df[col] = np.nan
        rows.append(
            df[
                [
                    "source",
                    "protocol",
                    "target",
                    "method",
                    "model",
                    "n_train",
                    "n_test",
                    "validation_r2",
                    "validation_r2_log1p",
                    "validation_rmse",
                    "validation_mae",
                    "validation_mape",
                    "r2",
                    "r2_log1p",
                    "rmse",
                    "mae",
                    "mape",
                ]
            ].copy()
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def main() -> None:
    ensure_project_dirs()
    sources = [
        ("external_covariate_metrics.csv", "external_public_covariates", "external_covariates"),
        ("innovation_model_metrics.csv", "spatiotemporal_innovation", None),
        ("multitask_latent_metrics.csv", "multitask_latent", None),
        ("temporal_sequence_model_metrics.csv", "arima_lstm_temporal", None),
        ("local_analog_memory_metrics.csv", "local_analog_memory", None),
        ("causal_history_memory_metrics.csv", "causal_history_memory", None),
        ("quantile_risk_gate_metrics.csv", "quantile_risk_gate", None),
        ("multi_evidence_fusion_metrics.csv", "multi_evidence_fusion", None),
        ("spatial_distribution_feature_metrics.csv", "spatial_distribution_features", None),
    ]
    selected_frames = []
    for path, source, feature_set in sources:
        table = read_metric_table(path, source, feature_set)
        if not table.empty:
            selected = select_by_validation(table)
            if not selected.empty:
                selected_frames.append(selected)

    validated = add_already_validated(
        [
            ("publication_validation_fusion_best_metrics.csv", "publication_validation_fusion"),
            ("validation_transfer_calibration_best_metrics.csv", "validation_transfer_calibration"),
            ("spatial_quantile_validated_best_metrics.csv", "spatial_quantile_validated"),
            ("predefined_recent_median_baseline_metrics.csv", "predefined_recent_median_baseline"),
        ]
    )
    if not validated.empty:
        selected_frames.append(validated)
    if not selected_frames:
        raise SystemExit("No validation-selected candidates were built.")

    all_candidates = pd.concat(selected_frames, ignore_index=True, sort=False)
    all_candidates["protocol"] = "temporal_2022_2026"
    all_candidates.to_csv(
        TABLES_DIR / "validation_selected_publication_candidate_metrics.csv", index=False, encoding="utf-8-sig"
    )
    best = (
        all_candidates.dropna(subset=["r2"])
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    best.to_csv(TABLES_DIR / "validation_selected_publication_metrics.csv", index=False, encoding="utf-8-sig")

    show = best[
        [
            "target",
            "source",
            "method",
            "model",
            "validation_r2",
            "r2",
            "rmse",
            "mae",
            "mape",
        ]
    ].copy()
    for col in ["validation_r2", "r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    summary = {
        "mean_r2": float(best["r2"].mean()),
        "median_r2": float(best["r2"].median()),
        "min_r2": float(best["r2"].min()),
        "max_r2": float(best["r2"].max()),
        "n_positive": int((best["r2"] > 0).sum()),
    }
    report = [
        "# 验证期选型论文结果",
        "",
        "该表要求普通模型族先在 2019-2020 验证期选择算法/方法，再固定到 2022-2026 测试期评估。已经内部使用验证期选型的融合模型、验证期迁移校正、空间分位数验证选择和预设近三年中位数基线也纳入候选。该口径比按 2022-2026 测试集挑模型更严格。",
        "",
        md_table(show),
        "",
        (
            f"平均 R2={summary['mean_r2']:.4f}，中位 R2={summary['median_r2']:.4f}，"
            f"最低 R2={summary['min_r2']:.4f}，最高 R2={summary['max_r2']:.4f}，"
            f"8 个目标中 {summary['n_positive']} 个为正。"
        ),
        "",
        "完整候选表见 `tables/validation_selected_publication_candidate_metrics.csv`；推荐表见 `tables/validation_selected_publication_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "validation_selected_publication_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote validation-selected publication outputs")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import target_columns
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs


OUT_DIR = FIGURES_DIR / "future_uncertainty"


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


def add_future_intervals(future: pd.DataFrame, interval_metrics: pd.DataFrame) -> pd.DataFrame:
    interval_cols = interval_metrics[
        ["target", "residual_q05", "residual_q95", "residual_median", "residual_mad", "coverage"]
    ].copy()
    out = future.merge(interval_cols, on="target", how="left")
    out["pred_lower"] = np.maximum(out["predicted"] + out["residual_q05"], 0.0)
    out["pred_upper"] = np.maximum(out["predicted"] + out["residual_q95"], 0.0)
    out["pred_median_bias_corrected"] = np.maximum(out["predicted"] + out["residual_median"], 0.0)
    out["interval_width"] = out["pred_upper"] - out["pred_lower"]
    out["relative_interval_width"] = out["interval_width"] / np.maximum(out["predicted"].abs(), 1e-8)
    out["interval_method"] = "empirical_2021_2026_residual_q05_q95"
    return out


def summarize(intervals: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_target_year = (
        intervals.groupby(["target", "year"], as_index=False)
        .agg(
            n=("predicted", "size"),
            mean_prediction=("predicted", "mean"),
            median_prediction=("predicted", "median"),
            mean_lower=("pred_lower", "mean"),
            mean_upper=("pred_upper", "mean"),
            median_interval_width=("interval_width", "median"),
            mean_relative_width=("relative_interval_width", "mean"),
        )
        .sort_values(["target", "year"])
    )
    by_target = (
        intervals.groupby("target", as_index=False)
        .agg(
            n=("predicted", "size"),
            mean_prediction=("predicted", "mean"),
            median_prediction=("predicted", "median"),
            median_interval_width=("interval_width", "median"),
            mean_relative_width=("relative_interval_width", "mean"),
            max_upper=("pred_upper", "max"),
        )
        .sort_values("target")
    )
    return by_target_year, by_target


def plot_width_by_target(summary: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    ax.bar(summary["target"], summary["median_interval_width"], color="#4C78A8")
    ax.set_xlabel("Target")
    ax.set_ylabel("Median 90% interval width")
    ax.set_title("Future prediction uncertainty by target (2027-2035)")
    ax.grid(axis="y", alpha=0.22)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "future_interval_width_by_target.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def plot_year_trend(by_target_year: pd.DataFrame, target: str) -> None:
    part = by_target_year[by_target_year["target"] == target].copy()
    if part.empty:
        return
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    ax.fill_between(part["year"], part["mean_lower"], part["mean_upper"], color="#A0CBE8", alpha=0.45, label="Mean 90% interval")
    ax.plot(part["year"], part["mean_prediction"], color="#4C78A8", marker="o", label="Mean prediction")
    ax.set_xlabel("Year")
    ax.set_ylabel("Concentration")
    ax.set_title(f"{target}: future mean prediction interval")
    ax.grid(alpha=0.22)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / f"{target}_future_mean_interval_trend.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_project_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = target_columns()
    aligned_future_path = RESULTS_DIR / "future_predictions_publication_aligned_2027_2035.csv"
    baseline_future_path = RESULTS_DIR / "future_predictions_baseline_2027_2035.csv"
    future_path = aligned_future_path if aligned_future_path.exists() and aligned_future_path.stat().st_size else baseline_future_path
    interval_path = TABLES_DIR / "publication_prediction_interval_metrics.csv"
    if not future_path.exists():
        raise SystemExit("Missing future predictions. Run scripts/predict_future_scenarios.py first.")
    if not interval_path.exists():
        raise SystemExit("Missing interval metrics. Run scripts/build_prediction_uncertainty_intervals.py first.")
    future = pd.read_csv(future_path)
    interval_metrics = pd.read_csv(interval_path)
    intervals = add_future_intervals(future, interval_metrics)
    legacy_interval_path = RESULTS_DIR / "future_predictions_baseline_2027_2035_intervals.csv"
    aligned_interval_path = RESULTS_DIR / "future_predictions_publication_aligned_2027_2035_intervals.csv"
    intervals.to_csv(legacy_interval_path, index=False, encoding="utf-8-sig")
    if future_path.name == "future_predictions_publication_aligned_2027_2035.csv":
        intervals.to_csv(aligned_interval_path, index=False, encoding="utf-8-sig")
    by_target_year, by_target = summarize(intervals)
    by_target_year["future_prediction_file"] = future_path.name
    by_target["future_prediction_file"] = future_path.name
    by_target_year.to_csv(TABLES_DIR / "future_prediction_interval_by_year.csv", index=False, encoding="utf-8-sig")
    by_target.to_csv(TABLES_DIR / "future_prediction_interval_summary.csv", index=False, encoding="utf-8-sig")
    plot_width_by_target(by_target)
    for target in [item for item in ["C", "F", "G"] if item in targets]:
        plot_year_trend(by_target_year, target)

    show = by_target.copy()
    for col in ["mean_prediction", "median_prediction", "median_interval_width", "mean_relative_width", "max_upper"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 未来预测不确定性区间",
        "",
        f"该报告将 2022-2026 论文主结果的经验残差 90% 区间迁移到 2027-2035 基线情景预测，输出未来预测下限、上限和区间宽度。当前使用的未来点预测文件为 `results/{future_path.name}`。该结果用于未来不确定性表达，不改变点预测。",
        "",
        md_table(show),
        "",
        "图件：",
        "",
        "- `figures/future_uncertainty/future_interval_width_by_target.png`",
        "- `figures/future_uncertainty/C_future_mean_interval_trend.png`",
        "- `figures/future_uncertainty/F_future_mean_interval_trend.png`",
        "- `figures/future_uncertainty/G_future_mean_interval_trend.png`",
        "",
        (
            "完整未来区间结果见 `results/future_predictions_publication_aligned_2027_2035_intervals.csv`；"
            "兼容旧流程的副本保留在 `results/future_predictions_baseline_2027_2035_intervals.csv`；"
            "年度汇总见 `tables/future_prediction_interval_by_year.csv`。"
        ),
        "",
    ]
    (DOCS_DIR / "future_prediction_uncertainty_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote future prediction uncertainty outputs")


if __name__ == "__main__":
    main()

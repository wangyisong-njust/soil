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


OUT_DIR = FIGURES_DIR / "prediction_uncertainty"
INTERVAL_LEVEL = 0.90


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


def robust_residual_scale(residual: np.ndarray) -> tuple[float, float, float, float]:
    residual = residual[np.isfinite(residual)]
    q_low = float(np.quantile(residual, (1.0 - INTERVAL_LEVEL) / 2.0))
    q_high = float(np.quantile(residual, 1.0 - (1.0 - INTERVAL_LEVEL) / 2.0))
    median = float(np.median(residual))
    mad = float(np.median(np.abs(residual - median)))
    return q_low, q_high, median, mad


def make_intervals(preds: pd.DataFrame, targets: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    interval_rows: list[pd.DataFrame] = []
    metric_rows: list[dict[str, object]] = []
    for target in targets:
        part = preds[preds["target"] == target].copy()
        residual = part["observed"].to_numpy(dtype=float) - part["predicted"].to_numpy(dtype=float)
        q_low, q_high, median, mad = robust_residual_scale(residual)
        out = part.copy()
        out["residual"] = residual
        out["interval_method"] = "empirical_residual_q05_q95"
        out["pred_lower"] = np.maximum(out["predicted"] + q_low, 0.0)
        out["pred_upper"] = np.maximum(out["predicted"] + q_high, 0.0)
        out["pred_median_bias_corrected"] = np.maximum(out["predicted"] + median, 0.0)
        out["interval_width"] = out["pred_upper"] - out["pred_lower"]
        out["covered"] = (out["observed"] >= out["pred_lower"]) & (out["observed"] <= out["pred_upper"])
        interval_rows.append(out)
        metric_rows.append(
            {
                "target": target,
                "n": int(len(out)),
                "coverage": float(out["covered"].mean()),
                "mean_interval_width": float(out["interval_width"].mean()),
                "median_interval_width": float(out["interval_width"].median()),
                "residual_q05": q_low,
                "residual_q95": q_high,
                "residual_median": median,
                "residual_mad": mad,
            }
        )
    return pd.concat(interval_rows, ignore_index=True), pd.DataFrame(metric_rows)


def plot_coverage(metrics: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(9.2, 4.8))
    x = np.arange(len(metrics))
    ax1.bar(x, metrics["coverage"], color="#4C78A8", label="Coverage")
    ax1.axhline(INTERVAL_LEVEL, color="#333333", linestyle="--", linewidth=0.9, label="Nominal 90%")
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics["target"])
    ax1.set_ylim(0, 1.05)
    ax1.set_ylabel("Coverage")
    ax1.set_xlabel("Target")
    ax1.grid(axis="y", alpha=0.22)
    ax2 = ax1.twinx()
    ax2.plot(x, metrics["median_interval_width"], color="#F28E2B", marker="o", label="Median width")
    ax2.set_ylabel("Median interval width")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, frameon=False, loc="upper right")
    ax1.set_title("Empirical residual interval coverage")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "coverage_and_width_by_target.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def plot_target_intervals(intervals: pd.DataFrame, target: str) -> None:
    part = intervals[intervals["target"] == target].copy()
    part = part.sort_values("observed").reset_index(drop=True)
    x = np.arange(len(part))
    fig, ax = plt.subplots(figsize=(9.4, 4.6))
    ax.fill_between(x, part["pred_lower"], part["pred_upper"], color="#A0CBE8", alpha=0.45, label="90% interval")
    ax.plot(x, part["predicted"], color="#4C78A8", linewidth=1.5, label="Prediction")
    ax.scatter(x, part["observed"], s=20, color="#E15759", label="Observed", zorder=3)
    ax.set_xlabel("Samples sorted by observed concentration")
    ax.set_ylabel("Concentration")
    ax.set_title(f"{target}: empirical residual prediction interval")
    ax.grid(alpha=0.22)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / f"{target}_prediction_interval.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_project_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = target_columns()
    preds = pd.read_csv(ROOT / "results/recommended_prediction_grid_values.csv")
    preds = preds[preds["tier"] == "publication_grade"].copy()
    intervals, metrics = make_intervals(preds, targets)
    intervals.to_csv(RESULTS_DIR / "publication_prediction_intervals.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(TABLES_DIR / "publication_prediction_interval_metrics.csv", index=False, encoding="utf-8-sig")
    plot_coverage(metrics)
    for target in [item for item in ["C", "F", "G"] if item in targets]:
        plot_target_intervals(intervals, target)

    show = metrics.copy()
    for col in [
        "coverage",
        "mean_interval_width",
        "median_interval_width",
        "residual_q05",
        "residual_q95",
        "residual_median",
        "residual_mad",
    ]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 预测不确定性区间",
        "",
        "该报告基于论文主结果在 2022-2026 测试期的经验残差，为每个目标构建 90% 经验残差预测区间。该区间用于结果不确定性表达和风险图扩展，不改变点预测 R2。",
        "",
        md_table(show),
        "",
        "图件：",
        "",
        "- `figures/prediction_uncertainty/coverage_and_width_by_target.png`",
        "- `figures/prediction_uncertainty/C_prediction_interval.png`",
        "- `figures/prediction_uncertainty/F_prediction_interval.png`",
        "- `figures/prediction_uncertainty/G_prediction_interval.png`",
        "",
        "完整区间结果见 `results/publication_prediction_intervals.csv`；覆盖率指标见 `tables/publication_prediction_interval_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "prediction_uncertainty_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote prediction uncertainty interval outputs")


if __name__ == "__main__":
    main()

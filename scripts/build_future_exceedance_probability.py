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
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


QUANTILES = [0.90, 0.95]
OUT_DIR = FIGURES_DIR / "future_exceedance_probability"


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


def empirical_exceedance_probability(predicted: np.ndarray, residuals: np.ndarray, threshold: float) -> np.ndarray:
    future_samples = predicted[:, None] + residuals[None, :]
    return np.mean(future_samples >= threshold, axis=1)


def build_thresholds(data: pd.DataFrame, targets: list[str]) -> pd.DataFrame:
    core = data[data["year"].between(2000, 2018)].copy()
    rows = []
    for target in targets:
        for quantile in QUANTILES:
            rows.append(
                {
                    "target": target,
                    "quantile": quantile,
                    "threshold_value": float(core[target].quantile(quantile)),
                    "n_core_train": int(len(core)),
                }
            )
    return pd.DataFrame(rows)


def build_probabilities(future: pd.DataFrame, residuals: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for threshold_row in thresholds.itertuples(index=False):
        target = threshold_row.target
        part = future[future["target"] == target].copy()
        target_residuals = residuals[residuals["target"] == target]["residual"].to_numpy(dtype=float)
        probability = empirical_exceedance_probability(
            part["predicted"].to_numpy(dtype=float),
            target_residuals,
            float(threshold_row.threshold_value),
        )
        part["quantile"] = float(threshold_row.quantile)
        part["threshold_value"] = float(threshold_row.threshold_value)
        part["exceedance_probability"] = probability
        part["probability_method"] = "empirical_residual_distribution"
        rows.append(part)
    return pd.concat(rows, ignore_index=True)


def summarize(probabilities: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_year = (
        probabilities.groupby(["target", "quantile", "year"], as_index=False)
        .agg(
            n=("exceedance_probability", "size"),
            mean_probability=("exceedance_probability", "mean"),
            median_probability=("exceedance_probability", "median"),
            p90_probability=("exceedance_probability", lambda values: float(np.quantile(values, 0.90))),
            high_prob_050_rate=("exceedance_probability", lambda values: float(np.mean(values >= 0.50))),
            high_prob_080_rate=("exceedance_probability", lambda values: float(np.mean(values >= 0.80))),
        )
        .sort_values(["quantile", "target", "year"])
    )
    by_target = (
        probabilities.groupby(["target", "quantile"], as_index=False)
        .agg(
            n=("exceedance_probability", "size"),
            mean_probability=("exceedance_probability", "mean"),
            median_probability=("exceedance_probability", "median"),
            p90_probability=("exceedance_probability", lambda values: float(np.quantile(values, 0.90))),
            high_prob_050_rate=("exceedance_probability", lambda values: float(np.mean(values >= 0.50))),
            high_prob_080_rate=("exceedance_probability", lambda values: float(np.mean(values >= 0.80))),
            threshold_value=("threshold_value", "first"),
        )
        .sort_values(["quantile", "target"])
    )
    return by_year, by_target


def plot_cfg_trends(by_year: pd.DataFrame, focus_targets: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    part = by_year[(by_year["target"].isin(focus_targets)) & (by_year["quantile"] == 0.90)].copy()
    if part.empty:
        return
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    for target, group in part.groupby("target"):
        ax.plot(group["year"], group["mean_probability"], marker="o", linewidth=1.7, label=target)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Mean exceedance probability")
    ax.set_title("Future q90 exceedance probability")
    ax.grid(alpha=0.22)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "cfg_q90_future_exceedance_probability_trend.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def plot_target_bar(summary: pd.DataFrame) -> None:
    part = summary[summary["quantile"] == 0.90].copy()
    x = np.arange(len(part))
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    ax.bar(x, part["mean_probability"], color="#4C78A8")
    ax.set_xticks(x)
    ax.set_xticklabels(part["target"])
    ax.set_ylim(0, 1)
    ax.set_xlabel("Target")
    ax.set_ylabel("Mean exceedance probability")
    ax.set_title("Mean future q90 exceedance probability by target")
    ax.grid(axis="y", alpha=0.22)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "target_q90_future_exceedance_probability.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_project_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = target_columns()
    focus_targets = [item for item in ["C", "F", "G"] if item in targets] or targets[: min(3, len(targets))]
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    aligned_future_path = RESULTS_DIR / "future_predictions_publication_aligned_2027_2035_intervals.csv"
    baseline_future_path = RESULTS_DIR / "future_predictions_baseline_2027_2035_intervals.csv"
    future_path = aligned_future_path if aligned_future_path.exists() and aligned_future_path.stat().st_size else baseline_future_path
    residual_path = RESULTS_DIR / "publication_prediction_intervals.csv"
    if not future_path.exists():
        raise SystemExit("Missing future interval predictions. Run scripts/build_future_prediction_uncertainty.py first.")
    if not residual_path.exists():
        raise SystemExit("Missing publication residual intervals. Run scripts/build_prediction_uncertainty_intervals.py first.")
    future = pd.read_csv(future_path)
    residuals = pd.read_csv(residual_path)
    thresholds = build_thresholds(data, targets)
    probabilities = build_probabilities(future, residuals, thresholds)
    by_year, summary = summarize(probabilities)
    probabilities.to_csv(RESULTS_DIR / "future_exceedance_probability_2027_2035.csv", index=False, encoding="utf-8-sig")
    thresholds.to_csv(TABLES_DIR / "future_exceedance_thresholds.csv", index=False, encoding="utf-8-sig")
    by_year.to_csv(TABLES_DIR / "future_exceedance_probability_by_year.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(TABLES_DIR / "future_exceedance_probability_summary.csv", index=False, encoding="utf-8-sig")
    plot_cfg_trends(by_year, focus_targets)
    plot_target_bar(summary)

    show = summary[summary["target"].isin(focus_targets)].copy()
    for col in [
        "quantile",
        "threshold_value",
        "mean_probability",
        "median_probability",
        "p90_probability",
        "high_prob_050_rate",
        "high_prob_080_rate",
    ]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 未来超阈值概率",
        "",
        f"该报告基于 2027-2035 未来点预测和 2022-2026 经验残差分布，估计未来浓度超过 2000-2018 训练核心期 q90/q95 阈值的概率。当前使用的未来区间文件为 `results/{future_path.name}`。该结果用于未来高污染风险图，不改变连续浓度点预测。",
        "",
        "## C/F/G 未来超阈值概率",
        "",
        md_table(show),
        "",
        "图件：",
        "",
        "- `figures/future_exceedance_probability/cfg_q90_future_exceedance_probability_trend.png`",
        "- `figures/future_exceedance_probability/target_q90_future_exceedance_probability.png`",
        "",
        "完整概率结果见 `results/future_exceedance_probability_2027_2035.csv`；年度汇总见 `tables/future_exceedance_probability_by_year.csv`。",
        "",
    ]
    (DOCS_DIR / "future_exceedance_probability_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote future exceedance probability outputs")


if __name__ == "__main__":
    main()

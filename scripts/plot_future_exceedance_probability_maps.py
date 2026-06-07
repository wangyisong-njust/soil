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
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, TABLES_DIR, ensure_project_dirs


QUANTILES = [0.90, 0.95]
MAP_YEAR = 2035
OUT_DIR = FIGURES_DIR / "future_exceedance_probability_maps"


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


def plot_probability_map(data: pd.DataFrame, target: str, quantile: float, year: int) -> Path:
    part = data[(data["target"] == target) & (data["quantile"] == quantile) & (data["year"] == year)].copy()
    if part.empty:
        raise ValueError(f"No probability rows for {target} q{quantile} {year}")
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    scatter = ax.scatter(
        part["lon"],
        part["lat"],
        c=part["exceedance_probability"],
        s=18,
        cmap="magma_r",
        vmin=0,
        vmax=1,
        alpha=0.88,
        linewidths=0,
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"{target} q{int(quantile * 100)} exceedance probability ({year})")
    ax.grid(alpha=0.18)
    cbar = fig.colorbar(scatter, ax=ax, fraction=0.042, pad=0.035)
    cbar.set_label("Probability")
    fig.tight_layout()
    path = OUT_DIR / f"{target}_q{int(quantile * 100)}_{year}_probability_map.png"
    fig.savefig(path, dpi=280, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_high_risk_trend(by_year: pd.DataFrame, targets: list[str], quantile: float) -> Path:
    part = by_year[(by_year["target"].isin(targets)) & (by_year["quantile"] == quantile)].copy()
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    for target, group in part.groupby("target"):
        ax.plot(group["year"], group["high_prob_050_rate"], marker="o", linewidth=1.7, label=f"{target} P>=0.5")
    ax.set_ylim(0, 1)
    ax.set_xlabel("Year")
    ax.set_ylabel("High-risk point ratio")
    ax.set_title(f"q{int(quantile * 100)} high-risk ratio (probability >= 0.5)")
    ax.grid(alpha=0.22)
    ax.legend(frameon=False)
    fig.tight_layout()
    path = OUT_DIR / f"cfg_q{int(quantile * 100)}_high_risk_ratio_trend.png"
    fig.savefig(path, dpi=280, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    ensure_project_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    probability_path = ROOT / "results/future_exceedance_probability_2027_2035.csv"
    by_year_path = TABLES_DIR / "future_exceedance_probability_by_year.csv"
    if not probability_path.exists():
        raise SystemExit("Missing future exceedance probabilities. Run scripts/build_future_exceedance_probability.py first.")
    if not by_year_path.exists():
        raise SystemExit("Missing yearly exceedance summary. Run scripts/build_future_exceedance_probability.py first.")
    probabilities = pd.read_csv(probability_path)
    by_year = pd.read_csv(by_year_path)
    configured_targets = target_columns()
    focus_targets = [item for item in ["C", "F", "G"] if item in configured_targets]
    if not focus_targets:
        focus_targets = sorted(probabilities["target"].dropna().astype(str).unique().tolist())[:3]

    map_paths = []
    for target in focus_targets:
        for quantile in QUANTILES:
            map_paths.append(plot_probability_map(probabilities, target, quantile, MAP_YEAR))
    trend_paths = [plot_high_risk_trend(by_year, focus_targets, quantile) for quantile in QUANTILES]

    summary = by_year[
        (by_year["target"].isin(focus_targets))
        & (by_year["quantile"].isin(QUANTILES))
        & (by_year["year"].isin([2027, 2030, 2035]))
    ][["target", "quantile", "year", "mean_probability", "high_prob_050_rate", "high_prob_080_rate"]].copy()
    for col in ["quantile", "mean_probability", "high_prob_050_rate", "high_prob_080_rate"]:
        summary[col] = summary[col].map(lambda value: f"{value:.4f}")
    summary.to_csv(TABLES_DIR / "future_exceedance_probability_map_summary.csv", index=False, encoding="utf-8-sig")

    report = [
        "# 未来超阈值概率图",
        "",
        f"本报告基于 `results/future_exceedance_probability_2027_2035.csv` 绘制重点目标在 {MAP_YEAR} 年的 q90/q95 超阈值概率空间图，并绘制 2027-2035 年高风险点位比例趋势。",
        "",
        "## 年度风险比例摘要",
        "",
        md_table(summary),
        "",
        "## 图件",
        "",
    ]
    for path in map_paths + trend_paths:
        report.append(f"- `{path.relative_to(ROOT)}`")
    report.extend(
        [
            "",
            "配套摘要表见 `tables/future_exceedance_probability_map_summary.csv`。",
            "",
        ]
    )
    (DOCS_DIR / "future_exceedance_probability_maps_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote future exceedance probability map outputs")


if __name__ == "__main__":
    main()

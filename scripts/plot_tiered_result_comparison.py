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


OUT_DIR = FIGURES_DIR / "tiered_results"


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


def load_layer(path: str, label: str, r2_col: str = "r2") -> pd.DataFrame:
    df = pd.read_csv(ROOT / path)
    if "protocol" in df.columns:
        df = df[df["protocol"] == "temporal_2022_2026"].copy()
    return df[["target", r2_col]].rename(columns={r2_col: label})


def annotate(ax, values: pd.Series, x_positions: np.ndarray) -> None:
    ymin, ymax = ax.get_ylim()
    span = ymax - ymin
    for x, value in zip(x_positions, values):
        if not np.isfinite(value):
            continue
        va = "bottom" if value >= 0 else "top"
        y = value + (0.018 * span if value >= 0 else -0.018 * span)
        ax.text(x, y, f"{value:.2f}", ha="center", va=va, fontsize=8)


def main() -> None:
    ensure_project_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    publication = load_layer("tables/publication_grade_recommended_metrics.csv", "publication_grade")
    exploration = load_layer("tables/final_adaptive_recommended_metrics.csv", "exploration_upper")
    linear = load_layer("tables/linear_stack_upper_bound_metrics.csv", "linear_same_set_upper")
    oof = load_layer("tables/nnls_oof_vs_same_set.csv", "nnls_loo_diagnostic")
    merged = (
        publication.merge(exploration, on="target", how="outer")
        .merge(linear, on="target", how="outer")
        .merge(oof, on="target", how="outer")
    )
    merged = merged.set_index("target").reindex(target_columns()).reset_index()
    merged.to_csv(TABLES_DIR / "tiered_result_comparison.csv", index=False, encoding="utf-8-sig")

    layers = [
        ("publication_grade", "Publication-grade", "#4C78A8"),
        ("exploration_upper", "Exploration upper", "#F28E2B"),
        ("linear_same_set_upper", "Linear same-set upper", "#59A14F"),
        ("nnls_loo_diagnostic", "NNLS LOO diagnostic", "#E15759"),
    ]
    x = np.arange(len(merged))
    width = 0.19
    fig, ax = plt.subplots(figsize=(12.5, 6))
    for i, (col, label, color) in enumerate(layers):
        pos = x + (i - 1.5) * width
        ax.bar(pos, merged[col], width=width, label=label, color=color)
        annotate(ax, merged[col], pos)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(merged["target"])
    ax.set_ylabel("R2")
    ax.set_xlabel("Heavy metal target")
    ax.set_title("Tiered R2 Comparison under 2022-2026 Validation")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=2)
    plt.tight_layout()
    fig_path = OUT_DIR / "tiered_r2_comparison.png"
    plt.savefig(fig_path, dpi=300, bbox_inches="tight")
    plt.close()

    summary = []
    for col, label, _ in layers:
        values = merged[col].dropna()
        summary.append(
            {
                "tier": label,
                "mean_r2": float(values.mean()),
                "median_r2": float(values.median()),
                "min_r2": float(values.min()),
                "max_r2": float(values.max()),
                "n_positive": int((values > 0).sum()),
            }
        )
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(TABLES_DIR / "tiered_result_summary.csv", index=False, encoding="utf-8-sig")
    show = summary_df.copy()
    for col in ["mean_r2", "median_r2", "min_r2", "max_r2"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 分层结果对比",
        "",
        "本报告把四种口径放在同一张图中：论文主结果、探索上限、线性同集上限和 NNLS 留一诊断。论文主结果不使用 2022-2026 目标值调参；探索上限与线性同集上限使用了验证集观测值进行候选选择、权重拟合或同集拟合，只能作为上限诊断；留一诊断用于显示同集上限的稳定性。",
        "",
        md_table(show),
        "",
        f"图件：`{fig_path.relative_to(ROOT)}`。",
        "",
        "逐目标对比表见 `tables/tiered_result_comparison.csv`；摘要表见 `tables/tiered_result_summary.csv`。",
        "",
    ]
    (DOCS_DIR / "tiered_result_comparison_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {fig_path.relative_to(ROOT)}")
    print("Wrote tiered result comparison outputs")


if __name__ == "__main__":
    main()

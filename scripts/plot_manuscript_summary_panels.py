#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, FIGURES_DIR, TABLES_DIR, ensure_project_dirs


FIG_DIR = FIGURES_DIR / "manuscript_summary"


SOURCE_COLORS = {
    "external_public_covariates": "#4E79A7",
    "publication_validation_fusion": "#59A14F",
    "distribution_guided_spatial_quantile": "#F28E2B",
    "local_analog_memory": "#B07AA1",
}


def read_required(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        raise SystemExit(f"Missing required input: {path.relative_to(ROOT)}")
    return pd.read_csv(path)


def to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def plot_performance(ax: plt.Axes, performance: pd.DataFrame) -> None:
    df = performance.sort_values("target").copy()
    df["r2"] = to_float(df["r2"])
    colors = [SOURCE_COLORS.get(str(source), "#9C755F") for source in df["source"]]
    ax.bar(df["target"], df["r2"], color=colors, edgecolor="#333333", linewidth=0.4)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_ylim(0, max(0.7, float(df["r2"].max()) + 0.08))
    ax.set_title("A. Publication validation R2", loc="left", fontsize=11, fontweight="bold")
    ax.set_ylabel("R2")
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    for idx, row in enumerate(df.itertuples(index=False)):
        value = float(row.r2)
        ax.text(idx, value + 0.018, f"{value:.2f}", ha="center", va="bottom", fontsize=8)
    handles = []
    labels = []
    for source, color in SOURCE_COLORS.items():
        if source in set(df["source"]):
            handles.append(plt.Rectangle((0, 0), 1, 1, color=color))
            labels.append(source.replace("_", " "))
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.0, -0.12), ncol=2, fontsize=7, frameon=False)


def plot_uncertainty(ax: plt.Axes, uncertainty: pd.DataFrame) -> None:
    df = uncertainty.sort_values("target").copy()
    df["mean_relative_width"] = to_float(df["mean_relative_width"])
    df["median_interval_width"] = to_float(df["median_interval_width"])
    ax.bar(df["target"], df["mean_relative_width"], color="#76B7B2", edgecolor="#333333", linewidth=0.4)
    ax.set_title("B. Future interval relative width", loc="left", fontsize=11, fontweight="bold")
    ax.set_ylabel("Mean relative width")
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    for idx, row in enumerate(df.itertuples(index=False)):
        value = float(row.mean_relative_width)
        ax.text(idx, value + max(df["mean_relative_width"].max() * 0.025, 0.05), f"{value:.1f}", ha="center", va="bottom", fontsize=8)


def plot_future_risk(ax: plt.Axes, risk: pd.DataFrame) -> None:
    df = risk.copy()
    df["quantile"] = to_float(df["quantile"])
    df["mean_probability"] = to_float(df["mean_probability"])
    pivot = df.pivot_table(index="target", columns="quantile", values="mean_probability", aggfunc="mean").sort_index()
    targets = list(pivot.index)
    x = np.arange(len(targets))
    width = 0.36
    q90 = pivot.get(0.90, pd.Series(index=pivot.index, dtype=float)).to_numpy(dtype=float)
    q95 = pivot.get(0.95, pd.Series(index=pivot.index, dtype=float)).to_numpy(dtype=float)
    ax.bar(x - width / 2, q90, width=width, color="#EDC948", edgecolor="#333333", linewidth=0.4, label="q90")
    ax.bar(x + width / 2, q95, width=width, color="#E15759", edgecolor="#333333", linewidth=0.4, label="q95")
    ax.set_xticks(x)
    ax.set_xticklabels(targets)
    ax.set_ylim(0, 1.05)
    ax.set_title("C. Mean future exceedance probability", loc="left", fontsize=11, fontweight="bold")
    ax.set_ylabel("Probability")
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.legend(frameon=False, fontsize=8)


def plot_feature_groups(ax: plt.Axes, feature_groups: pd.DataFrame) -> None:
    df = feature_groups.copy()
    df["normalized_shap"] = to_float(df["normalized_shap"])
    pivot = df.pivot_table(index="target", columns="feature_group", values="normalized_shap", aggfunc="sum").fillna(0)
    pivot = pivot.sort_index()
    preferred = ["Spatial lag", "Original driver variables", "Geographic position", "Temporal trend"]
    columns = [col for col in preferred if col in pivot.columns] + [col for col in pivot.columns if col not in preferred]
    pivot = pivot[columns]
    image = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap="YlGnBu", vmin=0, vmax=max(0.65, float(pivot.to_numpy().max())))
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=35, ha="right", fontsize=8)
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    ax.set_title("D. SHAP feature-group contribution", loc="left", fontsize=11, fontweight="bold")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            value = pivot.iloc[i, j]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=7, color="#111111")
    plt.colorbar(image, ax=ax, fraction=0.046, pad=0.03, label="Normalized SHAP")


def write_report(performance: pd.DataFrame, uncertainty: pd.DataFrame, risk: pd.DataFrame) -> None:
    perf = performance.copy()
    perf["r2"] = to_float(perf["r2"])
    risk = risk.copy()
    risk["mean_probability"] = to_float(risk["mean_probability"])
    f_q90 = risk[(risk["target"] == "F") & (to_float(risk["quantile"]) == 0.90)]
    f_q90_text = f"{float(f_q90['mean_probability'].iloc[0]):.4f}" if len(f_q90) else "NA"
    lines = [
        "# 论文总览组合图",
        "",
        "本图把论文主验证性能、2027-2035 未来预测区间宽度、未来超阈值概率和 SHAP 因子组贡献整合为一个 2x2 组合图。图件来自已有论文汇总表，不重新训练模型，也不修改数据。",
        "",
        "## 输出文件",
        "",
        "- PNG：`figures/manuscript_summary/manuscript_results_overview.png`",
        "- PDF：`figures/manuscript_summary/manuscript_results_overview.pdf`",
        "",
        "## 结果摘要",
        "",
        f"- 论文主模型平均 R2：{perf['r2'].mean():.4f}",
        f"- 论文主模型中位 R2：{perf['r2'].median():.4f}",
        f"- 论文主模型正 R2 目标数：{int((perf['r2'] > 0).sum())}/{perf['target'].nunique()}",
        f"- F 目标 q90 未来平均超阈值概率：{f_q90_text}",
        "",
        "## 图件说明",
        "",
        "- A 面板展示 8 个目标的论文主验证 R2，颜色表示模型来源。",
        "- B 面板展示未来预测 90% 区间的相对宽度，用于解释不同目标未来预测不确定性。",
        "- C 面板展示训练核心期 q90/q95 阈值下的未来平均超阈值概率。",
        "- D 面板展示 SHAP 因子组贡献，用于说明空间背景、原始驱动因子、地理位置和时间趋势的相对贡献。",
        "",
    ]
    (DOCS_DIR / "manuscript_summary_figure_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_project_dirs()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    performance = read_required(TABLES_DIR / "manuscript_table2_publication_model_performance.csv")
    uncertainty = read_required(TABLES_DIR / "manuscript_table3_future_prediction_uncertainty.csv")
    risk = read_required(TABLES_DIR / "manuscript_table4_future_exceedance_risk.csv")
    feature_groups = read_required(TABLES_DIR / "manuscript_table5_feature_group_importance.csv")

    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), constrained_layout=True)
    plot_performance(axes[0, 0], performance)
    plot_uncertainty(axes[0, 1], uncertainty)
    plot_future_risk(axes[1, 0], risk)
    plot_feature_groups(axes[1, 1], feature_groups)
    fig.suptitle("Soil Heavy Metal Spatiotemporal Prediction: Publication Summary", fontsize=14, fontweight="bold")
    png_path = FIG_DIR / "manuscript_results_overview.png"
    pdf_path = FIG_DIR / "manuscript_results_overview.pdf"
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    write_report(performance, uncertainty, risk)
    print("Wrote manuscript summary figure")


if __name__ == "__main__":
    main()

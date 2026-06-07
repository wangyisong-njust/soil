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


OUT_DIR = FIGURES_DIR / "feature_importance_summary"


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


def feature_group(feature: str) -> str:
    if feature.startswith("target_spatial_"):
        return "Spatial lag"
    if feature in {"lon", "lat", "lon_sq", "lat_sq", "lon_lat"}:
        return "Geographic position"
    if feature.startswith("year"):
        return "Temporal trend"
    if feature.startswith(("sg_", "np_")):
        return "Soil/climate public covariates"
    if feature.startswith(("osm_", "viirs_", "ghsl_", "wc_")):
        return "Human activity/remote sensing"
    return "Original driver variables"


def load_shap() -> pd.DataFrame:
    shap_path = TABLES_DIR / "shap_importance.csv"
    if not shap_path.exists() or shap_path.stat().st_size == 0:
        raise SystemExit("Missing tables/shap_importance.csv. Run scripts/run_experiment.py first.")
    shap = pd.read_csv(shap_path)
    shap = shap[shap["protocol"].isin(["temporal", "temporal_2022_2026"])].copy()
    shap["target"] = shap["target"].astype(str)
    shap["mean_abs_shap"] = pd.to_numeric(shap["mean_abs_shap"], errors="coerce")
    shap = shap.dropna(subset=["mean_abs_shap"])
    total = shap.groupby("target")["mean_abs_shap"].transform("sum")
    shap["normalized_shap"] = shap["mean_abs_shap"] / total.replace(0, np.nan)
    shap["feature_group"] = shap["feature"].map(feature_group)
    return shap


def write_tables(shap: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    top_features = (
        shap.sort_values(["target", "normalized_shap"], ascending=[True, False])
        .groupby("target", as_index=False)
        .head(8)
        .sort_values(["target", "normalized_shap"], ascending=[True, False])
    )
    top_features.to_csv(TABLES_DIR / "feature_importance_top_features.csv", index=False, encoding="utf-8-sig")
    group_summary = (
        shap.groupby(["target", "feature_group"], as_index=False)["normalized_shap"]
        .sum()
        .sort_values(["target", "normalized_shap"], ascending=[True, False])
    )
    group_summary.to_csv(TABLES_DIR / "feature_importance_group_summary.csv", index=False, encoding="utf-8-sig")
    return top_features, group_summary


def plot_top_feature_heatmap(shap: pd.DataFrame, targets: list[str]) -> None:
    ranked = (
        shap.groupby("feature", as_index=False)["normalized_shap"]
        .mean()
        .sort_values("normalized_shap", ascending=False)
        .head(20)
    )
    features = ranked["feature"].tolist()
    matrix = (
        shap[shap["feature"].isin(features)]
        .pivot_table(index="feature", columns="target", values="normalized_shap", aggfunc="sum")
        .reindex(features)
        .reindex(columns=targets)
        .fillna(0.0)
    )
    fig, ax = plt.subplots(figsize=(9.2, 7.2))
    im = ax.imshow(matrix.to_numpy(dtype=float), aspect="auto", cmap="YlGnBu")
    ax.set_xticks(np.arange(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns)
    ax.set_yticks(np.arange(len(matrix.index)))
    ax.set_yticklabels(matrix.index)
    ax.set_xlabel("Target")
    ax.set_title("Top SHAP Factors across 8 Heavy Metals")
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.025)
    cbar.set_label("Normalized mean |SHAP|")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "top_shap_feature_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_group_heatmap(group_summary: pd.DataFrame, targets: list[str]) -> None:
    groups = [
        "Spatial lag",
        "Geographic position",
        "Temporal trend",
        "Original driver variables",
        "Soil/climate public covariates",
        "Human activity/remote sensing",
    ]
    matrix = (
        group_summary.pivot_table(index="feature_group", columns="target", values="normalized_shap", aggfunc="sum")
        .reindex(groups)
        .reindex(columns=targets)
        .fillna(0.0)
    )
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    im = ax.imshow(matrix.to_numpy(dtype=float), aspect="auto", cmap="PuBuGn", vmin=0)
    ax.set_xticks(np.arange(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns)
    ax.set_yticks(np.arange(len(matrix.index)))
    ax.set_yticklabels(matrix.index)
    ax.set_xlabel("Target")
    ax.set_title("Grouped SHAP Contribution by Target")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix.iloc[i, j]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8, color="#222222")
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.025)
    cbar.set_label("Share of normalized mean |SHAP|")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "shap_group_contribution_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_top5_by_target(top_features: pd.DataFrame, targets: list[str]) -> None:
    n_cols = min(4, max(1, len(targets)))
    n_rows = int(np.ceil(len(targets) / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.7 * n_cols, 3.9 * n_rows))
    axes = axes.ravel()
    for ax, target in zip(axes, targets):
        part = top_features[top_features["target"] == target].head(5).sort_values("normalized_shap")
        ax.barh(part["feature"], part["normalized_shap"], color="#4C78A8")
        ax.set_title(f"Target {target}", fontsize=10)
        ax.set_xlabel("Normalized mean |SHAP|")
        ax.grid(axis="x", alpha=0.25)
    for ax in axes[len(targets):]:
        ax.axis("off")
    fig.suptitle("Top 5 SHAP Factors for Each Heavy Metal", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "top5_shap_factors_by_target.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_report(top_features: pd.DataFrame, group_summary: pd.DataFrame) -> None:
    show = top_features[["target", "model", "feature", "feature_group", "normalized_shap"]].copy()
    show["normalized_shap"] = show["normalized_shap"].map(lambda value: f"{value:.4f}")
    group_show = group_summary.copy()
    group_show["normalized_shap"] = group_show["normalized_shap"].map(lambda value: f"{value:.4f}")
    report = [
        "# 8 个重金属重要预测因子汇总",
        "",
        "本报告基于 `tables/shap_importance.csv` 中严格时间外推基础树模型的平均绝对 SHAP 值，生成跨 8 个重金属目标的可解释性汇总图。该解释结果对应基础可解释模型，不把后续验证期融合、近年中位数或线性同集上限强行解释为单一模型 SHAP。",
        "",
        "## 图件",
        "",
        "- Top SHAP 因子热图：`figures/feature_importance_summary/top_shap_feature_heatmap.png`",
        "- 因子组贡献热图：`figures/feature_importance_summary/shap_group_contribution_heatmap.png`",
        "- 8 目标 Top5 因子图：`figures/feature_importance_summary/top5_shap_factors_by_target.png`",
        "",
        "## Top 因子",
        "",
        md_table(show),
        "",
        "## 因子组贡献",
        "",
        md_table(group_show),
        "",
        "完整表格见 `tables/feature_importance_top_features.csv` 和 `tables/feature_importance_group_summary.csv`。",
        "",
    ]
    (DOCS_DIR / "feature_importance_summary_report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    ensure_project_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = target_columns()
    shap = load_shap()
    top_features, group_summary = write_tables(shap)
    plot_top_feature_heatmap(shap, targets)
    plot_group_heatmap(group_summary, targets)
    plot_top5_by_target(top_features, targets)
    write_report(top_features, group_summary)
    print("Wrote feature importance summary outputs")


if __name__ == "__main__":
    main()

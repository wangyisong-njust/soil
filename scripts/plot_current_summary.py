#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, ensure_project_dirs


SUMMARY_DIR = FIGURES_DIR / "summary"


def existing_file(rel_path: str) -> Path | None:
    path = ROOT / rel_path
    if path.exists() and path.stat().st_size:
        return path
    print(f"Skip missing summary input: {rel_path}")
    return None


def savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Wrote {path.relative_to(ROOT)}")


def annotate_bars(ax, fmt="{:.2f}", dy=0.015) -> None:
    ymin, ymax = ax.get_ylim()
    span = ymax - ymin
    for patch in ax.patches:
        value = patch.get_height()
        if not np.isfinite(value):
            continue
        y = value + dy * span if value >= 0 else value - dy * span
        va = "bottom" if value >= 0 else "top"
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            y,
            fmt.format(value),
            ha="center",
            va=va,
            fontsize=9,
        )


def plot_training_fit() -> None:
    path = existing_file("tables/training_fit_metrics.csv")
    if path is None:
        return
    fit = pd.read_csv(path)
    fit = fit[fit["status"] == "ok"].copy()
    best = (
        fit.sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(best["target"], best["r2"], color="#4C78A8")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Training fit R2")
    ax.set_xlabel("Heavy metal target")
    ax.set_title("Best Apparent Training Fit by Target")
    ax.grid(axis="y", alpha=0.25)
    annotate_bars(ax, fmt="{:.2f}", dy=0.01)
    savefig(SUMMARY_DIR / "training_fit_best_r2.png")


def plot_external_validation() -> None:
    path = existing_file("tables/external_covariate_best_metrics.csv")
    if path is None:
        return
    best = pd.read_csv(path)
    strict = best[(best["feature_set"] == "external_covariates") & (best["protocol"] == "temporal_2022_2026")].copy()
    strict = strict.sort_values("target")
    colors = ["#59A14F" if value >= 0 else "#E15759" for value in strict["r2"]]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(strict["target"], strict["r2"], color=colors)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_ylabel("Validation R2")
    ax.set_xlabel("Heavy metal target")
    ax.set_title("Strict Temporal Validation R2 with External Covariates")
    ax.grid(axis="y", alpha=0.25)
    annotate_bars(ax, fmt="{:.2f}", dy=0.02)
    savefig(SUMMARY_DIR / "strict_temporal_external_best_r2.png")


def plot_external_delta() -> None:
    path = existing_file("tables/external_covariate_r2_delta.csv")
    if path is None:
        return
    delta = pd.read_csv(path)
    strict = delta[delta["protocol"] == "temporal_2022_2026"].copy().sort_values("target")
    colors = ["#59A14F" if value >= 0 else "#E15759" for value in strict["delta_r2"]]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(strict["target"], strict["delta_r2"], color=colors)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_ylabel("Delta R2")
    ax.set_xlabel("Heavy metal target")
    ax.set_title("R2 Change after Adding Public External Covariates")
    ax.grid(axis="y", alpha=0.25)
    annotate_bars(ax, fmt="{:+.2f}", dy=0.025)
    savefig(SUMMARY_DIR / "external_covariate_r2_delta.png")


def plot_observed_predicted_grid() -> None:
    metrics_path = existing_file("tables/external_covariate_best_metrics.csv")
    preds_path = existing_file("results/external_covariate_predictions.csv")
    if metrics_path is None or preds_path is None:
        return
    metrics = pd.read_csv(metrics_path)
    preds = pd.read_csv(preds_path)
    strict = metrics[(metrics["feature_set"] == "external_covariates") & (metrics["protocol"] == "temporal_2022_2026")].copy()
    strict = strict.sort_values("target")
    fig, axes = plt.subplots(2, 4, figsize=(14, 7.2))
    axes = axes.ravel()
    for ax, row in zip(axes, strict.itertuples(index=False)):
        subset = preds[
            (preds["feature_set"] == "external_covariates")
            & (preds["protocol"] == "temporal_2022_2026")
            & (preds["target"] == row.target)
            & (preds["model"] == row.model)
        ].copy()
        ax.scatter(subset["observed"], subset["predicted"], s=28, alpha=0.75, color="#4C78A8", edgecolor="white", linewidth=0.4)
        values = np.r_[subset["observed"].to_numpy(), subset["predicted"].to_numpy()]
        finite = values[np.isfinite(values)]
        if len(finite):
            lo, hi = np.nanmin(finite), np.nanmax(finite)
            pad = (hi - lo) * 0.05 if hi > lo else 1.0
            ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="#333333", linewidth=0.9, linestyle="--")
            ax.set_xlim(lo - pad, hi + pad)
            ax.set_ylim(lo - pad, hi + pad)
        ax.set_title(f"{row.target} | {row.model} | R2={row.r2:.2f}", fontsize=10)
        ax.set_xlabel("Observed")
        ax.set_ylabel("Predicted")
        ax.grid(alpha=0.2)
    fig.suptitle("Observed vs Predicted under Strict Temporal Validation", fontsize=14, y=1.02)
    savefig(SUMMARY_DIR / "observed_predicted_external_temporal_grid.png")


def plot_literature_vs_strict() -> None:
    path = existing_file("tables/external_covariate_best_metrics.csv")
    if path is None:
        return
    best = pd.read_csv(path)
    ext = best[best["feature_set"] == "external_covariates"].copy()
    pivot = ext.pivot(index="target", columns="protocol", values="r2").sort_index()
    fig, ax = plt.subplots(figsize=(9.2, 5))
    x = np.arange(len(pivot))
    width = 0.36
    ax.bar(x - width / 2, pivot.get("literature_2019_2020"), width, label="2019-2020 validation", color="#F28E2B")
    ax.bar(x + width / 2, pivot.get("temporal_2022_2026"), width, label="2022-2026 strict validation", color="#4C78A8")
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index)
    ax.set_ylabel("R2")
    ax.set_xlabel("Heavy metal target")
    ax.set_title("External-Covariate Model R2 under Two Validation Protocols")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    savefig(SUMMARY_DIR / "external_validation_protocol_comparison.png")


def plot_publication_grade_r2() -> None:
    path = existing_file("tables/publication_grade_recommended_metrics.csv")
    if path is None:
        return
    metrics = pd.read_csv(path).sort_values("target")
    colors = ["#59A14F" if value >= 0 else "#E15759" for value in metrics["r2"]]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(metrics["target"], metrics["r2"], color=colors)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_ylabel("R2")
    ax.set_xlabel("Heavy metal target")
    ax.set_title("Publication-grade Recommended R2 by Target")
    ax.grid(axis="y", alpha=0.25)
    annotate_bars(ax, fmt="{:.2f}", dy=0.02)
    savefig(SUMMARY_DIR / "publication_grade_recommended_r2.png")


def plot_validation_sensitivity_comparison() -> None:
    frames = []
    for tier, path in [
        ("Publication-grade", "tables/publication_grade_recommended_metrics.csv"),
        ("Validation-selected", "tables/validation_selected_publication_metrics.csv"),
        ("Validation robust fusion", "tables/validation_robust_fusion_best_metrics.csv"),
    ]:
        full_path = ROOT / path
        if full_path.exists() and full_path.stat().st_size:
            part = pd.read_csv(full_path)[["target", "r2"]].copy()
            part["tier"] = tier
            frames.append(part)
    if not frames:
        return
    data = pd.concat(frames, ignore_index=True)
    pivot = data.pivot(index="target", columns="tier", values="r2").sort_index()
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    x = np.arange(len(pivot))
    width = 0.26
    colors = {
        "Publication-grade": "#4C78A8",
        "Validation-selected": "#59A14F",
        "Validation robust fusion": "#E15759",
    }
    for offset, tier in zip([-width, 0, width], ["Publication-grade", "Validation-selected", "Validation robust fusion"]):
        if tier in pivot:
            ax.bar(x + offset, pivot[tier], width, label=tier, color=colors[tier])
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index)
    ax.set_ylabel("R2")
    ax.set_xlabel("Heavy metal target")
    ax.set_title("R2 Sensitivity across Publication-grade Selection Rules")
    ax.legend(frameon=False, ncol=3, fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    savefig(SUMMARY_DIR / "publication_validation_sensitivity_r2.png")


def write_report() -> None:
    publication_path = existing_file("tables/publication_grade_recommended_metrics.csv")
    validation_path = existing_file("tables/validation_selected_publication_metrics.csv")
    robust_path = existing_file("tables/validation_robust_fusion_best_metrics.csv")
    lines = [
        "# 当前结果可视化摘要",
        "",
        "本报告汇总当前交付中最适合快速展示的图件：训练拟合度、严格时间外推 R2、外部公开因子增益、验证协议敏感性和观测-预测散点图。",
        "",
        "## 核心图件",
        "",
        "- 论文主结果 R2：`figures/summary/publication_grade_recommended_r2.png`",
        "- 选型规则敏感性：`figures/summary/publication_validation_sensitivity_r2.png`",
        "- 训练拟合 R2：`figures/summary/training_fit_best_r2.png`",
        "- 外部公开因子严格时间外推 R2：`figures/summary/strict_temporal_external_best_r2.png`",
        "- 外部公开因子增益：`figures/summary/external_covariate_r2_delta.png`",
        "- 2019-2020 与 2022-2026 验证协议对比：`figures/summary/external_validation_protocol_comparison.png`",
        "- 外部因子观测-预测散点图：`figures/summary/observed_predicted_external_temporal_grid.png`",
        "",
        "## 数值摘要",
        "",
    ]
    if publication_path is not None:
        publication = pd.read_csv(publication_path)
        lines.extend(
            [
                (
                    f"论文主结果平均 R2={publication['r2'].mean():.4f}，中位 R2={publication['r2'].median():.4f}，"
                    f"最低 R2={publication['r2'].min():.4f}，8 个目标中 {(publication['r2'] > 0).sum()} 个为正。"
                ),
                "",
            ]
        )
    if validation_path is not None and robust_path is not None:
        validation = pd.read_csv(validation_path)
        robust = pd.read_csv(robust_path)
        lines.extend(
            [
                (
                    f"验证期选型结果平均 R2={validation['r2'].mean():.4f}；"
                    f"验证期稳健融合平均 R2={robust['r2'].mean():.4f}。稳健融合没有提升，说明 2019-2020 到 2022-2026 的时空迁移不稳定，不能通过简单融合强行解决。"
                ),
                "",
            ]
        )
    (DOCS_DIR / "current_visual_summary_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote docs/current_visual_summary_report.md")


def main() -> None:
    ensure_project_dirs()
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    plot_training_fit()
    plot_external_validation()
    plot_external_delta()
    plot_literature_vs_strict()
    plot_observed_predicted_grid()
    plot_publication_grade_r2()
    plot_validation_sensitivity_comparison()
    write_report()


if __name__ == "__main__":
    main()

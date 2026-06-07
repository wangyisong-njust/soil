#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import target_columns
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, TABLES_DIR, ensure_project_dirs


OUT_DIR = FIGURES_DIR / "extreme_error_diagnostics"


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


def safe_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2 or np.nanstd(y_true) <= 1e-12:
        return np.nan
    return float(r2_score(y_true, y_pred))


def metric_row(target: str, label: str, data: pd.DataFrame) -> dict[str, object]:
    y = data["observed"].to_numpy(dtype=float)
    pred = data["predicted"].to_numpy(dtype=float)
    return {
        "target": target,
        "subset": label,
        "n": int(len(data)),
        "r2": safe_r2(y, pred),
        "rmse": float(np.sqrt(mean_squared_error(y, pred))),
        "mae": float(mean_absolute_error(y, pred)),
        "obs_max": float(np.max(y)),
        "obs_p95": float(np.quantile(y, 0.95)),
    }


def build_target_diagnostics(preds: pd.DataFrame, target: str) -> tuple[list[dict[str, object]], pd.DataFrame]:
    part = preds[preds["target"] == target].copy()
    part["abs_error"] = (part["predicted"] - part["observed"]).abs()
    part["sq_error"] = (part["predicted"] - part["observed"]) ** 2
    rows = [metric_row(target, "all", part)]
    for n_drop in [1, 2, 3]:
        trimmed = part.sort_values("observed", ascending=False).iloc[n_drop:].copy()
        rows.append(metric_row(target, f"drop_top_obs_{n_drop}", trimmed))
    for q in [0.95, 0.98]:
        cap = float(part["observed"].quantile(q))
        trimmed = part[part["observed"] <= cap].copy()
        rows.append(metric_row(target, f"obs_le_p{int(q * 100)}", trimmed))
    total_sq = float(part["sq_error"].sum())
    influential = part.sort_values("sq_error", ascending=False).head(8).copy()
    influential["sq_error_share"] = influential["sq_error"] / max(total_sq, 1e-12)
    return rows, influential


def plot_target(part: pd.DataFrame, target: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))
    ax = axes[0]
    ax.scatter(part["observed"], part["predicted"], s=32, alpha=0.78, color="#4C78A8", edgecolor="white", linewidth=0.35)
    values = np.r_[part["observed"].to_numpy(dtype=float), part["predicted"].to_numpy(dtype=float)]
    lo, hi = float(np.min(values)), float(np.max(values))
    pad = (hi - lo) * 0.04 if hi > lo else 1.0
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="#333333", linestyle="--", linewidth=0.9)
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlabel("Observed")
    ax.set_ylabel("Predicted")
    ax.set_title(f"{target}: observed vs predicted")
    ax.grid(alpha=0.22)

    ax = axes[1]
    ordered = part.sort_values("observed", ascending=False).head(12).copy()
    labels = [f"{int(year)}\\n{lon:.1f},{lat:.1f}" for lon, lat, year in ordered[["lon", "lat", "year"]].to_numpy()]
    x = np.arange(len(ordered))
    ax.bar(x - 0.18, ordered["observed"], width=0.36, label="Observed", color="#E15759")
    ax.bar(x + 0.18, ordered["predicted"], width=0.36, label="Predicted", color="#4C78A8")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Concentration")
    ax.set_title(f"{target}: top observed samples")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.22)
    fig.tight_layout()
    fig.savefig(OUT_DIR / f"{target}_extreme_error_diagnostic.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_project_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    preds = pd.read_csv(ROOT / "results/recommended_prediction_grid_values.csv")
    preds = preds[preds["tier"] == "publication_grade"].copy()
    rows: list[dict[str, object]] = []
    influential_frames: list[pd.DataFrame] = []
    targets = target_columns()
    focus_targets = [item for item in ["C", "F", "G"] if item in targets] or targets[: min(3, len(targets))]
    for target in targets:
        target_rows, influential = build_target_diagnostics(preds, target)
        rows.extend(target_rows)
        influential_frames.append(influential)
        if target in set(focus_targets):
            plot_target(preds[preds["target"] == target].copy(), target)

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "extreme_error_sensitivity_metrics.csv", index=False, encoding="utf-8-sig")
    influential = pd.concat(influential_frames, ignore_index=True)
    influential.to_csv(TABLES_DIR / "extreme_error_influential_samples.csv", index=False, encoding="utf-8-sig")

    show = metrics[metrics["target"].isin(["C", "F", "G"])].copy()
    for col in ["r2", "rmse", "mae", "obs_max", "obs_p95"]:
        show[col] = show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    top_show = influential[influential["target"].isin(["C", "F", "G"])][
        ["target", "lon", "lat", "year", "observed", "predicted", "abs_error", "sq_error_share"]
    ].head(18).copy()
    for col in ["lon", "lat", "observed", "predicted", "abs_error", "sq_error_share"]:
        top_show[col] = top_show[col].map(lambda value: f"{value:.4f}")

    report = [
        "# 极端样本误差诊断",
        "",
        "该报告用于解释严格时间外推下 C/F/G 的 R2 偏低原因。诊断不改变主结果，只计算去除最高观测值后的敏感性指标，并列出平方误差贡献最高的样本。",
        "",
        "## C/F/G 稳健敏感性",
        "",
        md_table(show[["target", "subset", "n", "r2", "rmse", "mae", "obs_max", "obs_p95"]]),
        "",
        "## 主要影响样本",
        "",
        md_table(top_show),
        "",
        "## 图件",
        "",
        "- `figures/extreme_error_diagnostics/C_extreme_error_diagnostic.png`",
        "- `figures/extreme_error_diagnostics/F_extreme_error_diagnostic.png`",
        "- `figures/extreme_error_diagnostics/G_extreme_error_diagnostic.png`",
        "",
        "完整表格见 `tables/extreme_error_sensitivity_metrics.csv` 和 `tables/extreme_error_influential_samples.csv`。",
        "",
    ]
    (DOCS_DIR / "extreme_error_diagnostics_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote extreme error diagnostic outputs")


if __name__ == "__main__":
    main()

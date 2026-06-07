#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import target_columns
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


OUT_DIR = FIGURES_DIR / "yearwise_error_diagnostics"


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


def metric_row(target: str, year: int, part: pd.DataFrame) -> dict[str, object]:
    observed = part["observed"].to_numpy(dtype=float)
    predicted = part["predicted"].to_numpy(dtype=float)
    residual = predicted - observed
    return {
        "target": target,
        "year": int(year),
        "n": int(len(part)),
        "r2": safe_r2(observed, predicted),
        "rmse": float(np.sqrt(mean_squared_error(observed, predicted))),
        "mae": float(mean_absolute_error(observed, predicted)),
        "bias": float(np.mean(residual)),
        "median_abs_error": float(np.median(np.abs(residual))),
        "observed_mean": float(np.mean(observed)),
        "observed_median": float(np.median(observed)),
        "observed_p90": float(np.quantile(observed, 0.9)),
        "predicted_mean": float(np.mean(predicted)),
    }


def build_yearwise_metrics(preds: pd.DataFrame, targets: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for target in targets:
        target_part = preds[preds["target"] == target].copy()
        for year, part in target_part.groupby(target_part["year"].round().astype(int), sort=True):
            rows.append(metric_row(target, int(year), part))
    return pd.DataFrame(rows)


def build_distribution_shift(data: pd.DataFrame, targets: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    train = data[data["year"] < 2022].copy()
    test = data[data["year"] >= 2022].copy()
    for target in targets:
        train_values = train[target].to_numpy(dtype=float)
        test_values = test[target].to_numpy(dtype=float)
        train_median = float(np.median(train_values))
        test_median = float(np.median(test_values))
        train_p90 = float(np.quantile(train_values, 0.9))
        test_p90 = float(np.quantile(test_values, 0.9))
        train_iqr = float(np.quantile(train_values, 0.75) - np.quantile(train_values, 0.25))
        median_shift_iqr = (test_median - train_median) / max(train_iqr, 1e-8)
        rows.append(
            {
                "target": target,
                "train_n": int(len(train_values)),
                "test_n": int(len(test_values)),
                "train_median": train_median,
                "test_median": test_median,
                "median_shift": test_median - train_median,
                "median_shift_iqr": median_shift_iqr,
                "train_p90": train_p90,
                "test_p90": test_p90,
                "p90_shift": test_p90 - train_p90,
                "test_over_train_p90_ratio": test_p90 / max(train_p90, 1e-8),
            }
        )
    return pd.DataFrame(rows)


def plot_heatmap(df: pd.DataFrame, value_col: str, title: str, filename: str, cmap: str, center_zero: bool = False) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pivot = df.pivot(index="target", columns="year", values=value_col).sort_index()
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    values = pivot.to_numpy(dtype=float)
    if center_zero:
        vmax = np.nanmax(np.abs(values))
        vmin = -vmax
    else:
        vmin = np.nanmin(values)
        vmax = np.nanmax(values)
    im = ax.imshow(values, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels([str(int(col)) for col in pivot.columns])
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("Year")
    ax.set_ylabel("Target")
    ax.set_title(title)
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            value = values[i, j]
            label = "NA" if not np.isfinite(value) else f"{value:.2f}"
            ax.text(j, i, label, ha="center", va="center", fontsize=8, color="#111111")
    fig.colorbar(im, ax=ax, fraction=0.035, pad=0.025)
    fig.tight_layout()
    fig.savefig(OUT_DIR / filename, dpi=260, bbox_inches="tight")
    plt.close(fig)


def plot_shift(shift: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    part = shift.sort_values("target")
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    x = np.arange(len(part))
    ax.bar(x - 0.18, part["median_shift_iqr"], width=0.36, label="Median shift / train IQR", color="#4C78A8")
    ax.bar(x + 0.18, part["test_over_train_p90_ratio"] - 1.0, width=0.36, label="P90 ratio - 1", color="#F28E2B")
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(part["target"])
    ax.set_xlabel("Target")
    ax.set_ylabel("Relative shift")
    ax.set_title("Train-test target distribution shift")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.22)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "train_test_distribution_shift.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_project_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = target_columns()
    preds = pd.read_csv(ROOT / "results/recommended_prediction_grid_values.csv")
    preds = preds[preds["tier"] == "publication_grade"].copy()
    preds["year"] = preds["year"].round().astype(int)
    yearwise = build_yearwise_metrics(preds, targets)
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    shift = build_distribution_shift(data, targets)
    yearwise.to_csv(TABLES_DIR / "publication_yearwise_error_metrics.csv", index=False, encoding="utf-8-sig")
    shift.to_csv(TABLES_DIR / "target_distribution_shift_metrics.csv", index=False, encoding="utf-8-sig")
    plot_heatmap(yearwise, "rmse", "Publication RMSE by target and year", "publication_yearwise_rmse_heatmap.png", "YlOrRd")
    plot_heatmap(yearwise, "bias", "Publication bias by target and year", "publication_yearwise_bias_heatmap.png", "coolwarm", center_zero=True)
    plot_heatmap(yearwise, "n", "Test sample count by target and year", "publication_yearwise_sample_count.png", "Blues")
    plot_shift(shift)

    summary = (
        yearwise.groupby("target", as_index=False)
        .agg(
            n_years=("year", "nunique"),
            total_n=("n", "sum"),
            mean_rmse=("rmse", "mean"),
            max_rmse=("rmse", "max"),
            mean_abs_bias=("bias", lambda values: float(np.mean(np.abs(values)))),
            worst_year=("rmse", lambda values: int(yearwise.loc[values.idxmax(), "year"])),
        )
        .merge(shift[["target", "median_shift_iqr", "test_over_train_p90_ratio"]], on="target", how="left")
    )
    summary.to_csv(TABLES_DIR / "publication_yearwise_error_summary.csv", index=False, encoding="utf-8-sig")
    show = summary.copy()
    for col in ["mean_rmse", "max_rmse", "mean_abs_bias", "median_shift_iqr", "test_over_train_p90_ratio"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    lines = [
        "# 逐年误差与分布漂移诊断",
        "",
        "本报告将论文主结果在 2022-2026 测试期按年份拆分，统计逐年 RMSE、MAE、偏差和样本量，并比较训练期与测试期目标分布差异。该诊断不改变点预测结果，用于解释严格时间外推下低 R2 的来源。",
        "",
        md_table(show),
        "",
        "图件：",
        "",
        "- `figures/yearwise_error_diagnostics/publication_yearwise_rmse_heatmap.png`",
        "- `figures/yearwise_error_diagnostics/publication_yearwise_bias_heatmap.png`",
        "- `figures/yearwise_error_diagnostics/publication_yearwise_sample_count.png`",
        "- `figures/yearwise_error_diagnostics/train_test_distribution_shift.png`",
        "",
        "完整逐年指标见 `tables/publication_yearwise_error_metrics.csv`；分布漂移指标见 `tables/target_distribution_shift_metrics.csv`；摘要表见 `tables/publication_yearwise_error_summary.csv`。",
        "",
    ]
    (DOCS_DIR / "yearwise_error_diagnostics_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote yearwise error diagnostics outputs")


if __name__ == "__main__":
    main()

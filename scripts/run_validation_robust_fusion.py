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
from soilmodel.config import target_columns
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs


VAL_PROTOCOL = "literature_2019_2020"
TEST_PROTOCOL = "temporal_2022_2026"
OUT_DIR = FIGURES_DIR / "validation_robust_fusion"


PREDICTION_SOURCES = [
    ("external", "results/external_covariate_predictions.csv", ["feature_set", "model"]),
    ("innovation", "results/innovation_model_predictions.csv", ["method", "model"]),
    ("temporal_sequence", "results/temporal_sequence_model_predictions.csv", ["method", "model"]),
    ("local_analog", "results/local_analog_memory_predictions.csv", ["method", "model"]),
    ("causal_history", "results/causal_history_memory_predictions.csv", ["method", "model"]),
    ("spatial_distribution", "results/spatial_distribution_feature_predictions.csv", ["method", "feature_set", "model"]),
    ("quantile_risk_gate", "results/quantile_risk_gate_predictions.csv", ["method", "model"]),
    ("multi_evidence", "results/multi_evidence_fusion_predictions.csv", ["method", "model"]),
    ("recent_median", "results/predefined_recent_median_baseline_predictions.csv", ["method", "model"]),
]


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


def normalize_protocol(value: object) -> object:
    if value == "temporal":
        return TEST_PROTOCOL
    return value


def candidate_name(source: str, row: pd.Series, cols: list[str]) -> str:
    parts = [source]
    for col in cols:
        if col in row and pd.notna(row[col]):
            parts.append(str(row[col]))
    return "::".join(parts)


def load_candidates() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for source, rel_path, cols in PREDICTION_SOURCES:
        path = ROOT / rel_path
        if not path.exists() or path.stat().st_size == 0:
            continue
        df = pd.read_csv(path)
        if "protocol" not in df.columns:
            continue
        df["protocol"] = df["protocol"].map(normalize_protocol)
        df = df[df["protocol"].isin([VAL_PROTOCOL, TEST_PROTOCOL])].copy()
        if df.empty:
            continue
        for col in cols:
            if col not in df.columns:
                df[col] = ""
        df["candidate"] = [candidate_name(source, row, cols) for _, row in df.iterrows()]
        keep = ["lon", "lat", "year", "protocol", "target", "observed", "predicted", "candidate"]
        frames.append(df[keep].copy())
    if not frames:
        raise SystemExit("No prediction sources found.")
    out = pd.concat(frames, ignore_index=True)
    out["predicted"] = pd.to_numeric(out["predicted"], errors="coerce")
    out["observed"] = pd.to_numeric(out["observed"], errors="coerce")
    return out.dropna(subset=["observed", "predicted"])


def build_matrix(df: pd.DataFrame, target: str, protocol: str) -> tuple[pd.DataFrame, pd.Series]:
    part = df[(df["target"] == target) & (df["protocol"] == protocol)].copy()
    if part.empty:
        return pd.DataFrame(), pd.Series(dtype=float)
    key = ["lon", "lat", "year"]
    obs = part.drop_duplicates(key).set_index(key)["observed"].sort_index()
    pivot = part.pivot_table(index=key, columns="candidate", values="predicted", aggfunc="mean").sort_index()
    pivot = pivot.loc[obs.index]
    pivot = pivot.dropna(axis=1, how="any")
    return pivot, obs


def eval_candidate_matrix(matrix: pd.DataFrame, observed: pd.Series) -> pd.DataFrame:
    rows = []
    y = observed.to_numpy(dtype=float)
    for candidate in matrix.columns:
        pred = np.maximum(matrix[candidate].to_numpy(dtype=float), 0.0)
        rows.append({"candidate": candidate, **regression_metrics(y, pred)})
    return pd.DataFrame(rows)


def inverse_rmse_weights(rmse: np.ndarray) -> np.ndarray:
    scores = 1.0 / np.maximum(rmse, 1e-9)
    return scores / scores.sum()


def blended_prediction(matrix: pd.DataFrame, candidates: list[str], weights: np.ndarray | None) -> np.ndarray:
    values = matrix[candidates].to_numpy(dtype=float)
    if weights is None:
        return np.nanmedian(values, axis=1)
    return values @ weights


def evaluate_fusions_for_target(all_preds: pd.DataFrame, target: str) -> tuple[list[dict[str, object]], pd.DataFrame]:
    val_x, val_y = build_matrix(all_preds, target, VAL_PROTOCOL)
    test_x, test_y = build_matrix(all_preds, target, TEST_PROTOCOL)
    if val_x.empty or test_x.empty:
        return [], pd.DataFrame()
    shared = [col for col in val_x.columns if col in test_x.columns]
    val_x = val_x[shared]
    test_x = test_x[shared]
    val_metrics = eval_candidate_matrix(val_x, val_y)
    val_metrics = val_metrics.sort_values(["rmse", "r2"], ascending=[True, False]).reset_index(drop=True)

    rows: list[dict[str, object]] = []
    pred_frames: list[pd.DataFrame] = []
    y_val = val_y.to_numpy(dtype=float)
    y_test = test_y.to_numpy(dtype=float)
    max_k = min(len(shared), 20)
    ks = sorted(set(k for k in [1, 2, 3, 5, 8, 12, 20] if k <= max_k))
    for k in ks:
        candidates = val_metrics.head(k)["candidate"].tolist()
        rmse = val_metrics.head(k)["rmse"].to_numpy(dtype=float)
        for method, weights in [
            (f"Top{k}InvRMSEMean", inverse_rmse_weights(rmse)),
            (f"Top{k}Median", None),
        ]:
            val_pred = np.maximum(blended_prediction(val_x, candidates, weights), 0.0)
            test_pred = np.maximum(blended_prediction(test_x, candidates, weights), 0.0)
            val_metric = regression_metrics(y_val, val_pred)
            test_metric = regression_metrics(y_test, test_pred)
            rows.append(
                {
                    "protocol": TEST_PROTOCOL,
                    "target": target,
                    "source": "validation_robust_fusion",
                    "method": "validation_topk_fusion",
                    "model": method,
                    "n_train": int(len(y_val)),
                    "n_test": int(len(y_test)),
                    "n_candidates": int(k),
                    "validation_r2": val_metric["r2"],
                    "validation_rmse": val_metric["rmse"],
                    **test_metric,
                    "candidate_list": " | ".join(candidates),
                }
            )
            pred_table = pd.DataFrame(index=test_x.index).reset_index()
            pred_table["protocol"] = TEST_PROTOCOL
            pred_table["target"] = target
            pred_table["source"] = "validation_robust_fusion"
            pred_table["method"] = "validation_topk_fusion"
            pred_table["model"] = method
            pred_table["observed"] = y_test
            pred_table["predicted"] = test_pred
            pred_frames.append(pred_table)

    candidate_cols = [
        "candidate",
        "r2",
        "r2_log1p",
        "rmse",
        "mae",
        "mape",
    ]
    candidate_out = val_metrics[candidate_cols].copy()
    candidate_out.insert(0, "target", target)
    candidate_out.to_csv(
        TABLES_DIR / f"validation_robust_fusion_{target}_validation_rank.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return rows, pd.concat(pred_frames, ignore_index=True)


def plot_results(best: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    colors = ["#4C78A8" if value >= 0 else "#D95F02" for value in best["r2"]]
    ax.bar(best["target"], best["r2"], color=colors, width=0.72)
    ax.axhline(0, color="#222222", linewidth=0.9)
    ax.set_title("Validation robust fusion test R2 by target")
    ax.set_xlabel("Target")
    ax.set_ylabel("R2 on 2022-2026")
    ax.grid(axis="y", alpha=0.25)
    for idx, row in best.iterrows():
        ax.text(idx, row["r2"], f"{row['r2']:.2f}", ha="center", va="bottom" if row["r2"] >= 0 else "top", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "validation_robust_fusion_r2.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_project_dirs()
    all_preds = load_candidates()
    targets = target_columns()
    rows: list[dict[str, object]] = []
    pred_frames: list[pd.DataFrame] = []
    for target in targets:
        target_rows, target_preds = evaluate_fusions_for_target(all_preds, target)
        rows.extend(target_rows)
        if not target_preds.empty:
            pred_frames.append(target_preds)
    if not rows:
        raise SystemExit("No validation robust fusion rows were generated.")
    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "validation_robust_fusion_metrics.csv", index=False, encoding="utf-8-sig")
    best = (
        metrics.sort_values(["target", "validation_rmse", "validation_r2"], ascending=[True, True, False])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    best.to_csv(TABLES_DIR / "validation_robust_fusion_best_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_frames:
        pd.concat(pred_frames, ignore_index=True).to_csv(
            RESULTS_DIR / "validation_robust_fusion_predictions.csv", index=False, encoding="utf-8-sig"
        )
    plot_results(best)

    show = best[
        [
            "target",
            "model",
            "n_candidates",
            "validation_r2",
            "validation_rmse",
            "r2",
            "rmse",
            "mae",
            "mape",
        ]
    ].copy()
    for col in ["validation_r2", "validation_rmse", "r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 验证期稳健融合模型",
        "",
        "本实验汇总已有候选模型在 2019-2020 验证期和 2022-2026 测试期的预测结果，只用 2019-2020 的 RMSE/R2 排名确定 TopK 候选和融合权重，再固定评估 2022-2026。该流程不使用 2022-2026 观测值调权重或选 TopK，可作为论文口径的稳健集成候选。",
        "",
        md_table(show),
        "",
        (
            f"平均 R2={best['r2'].mean():.4f}，中位 R2={best['r2'].median():.4f}，"
            f"最低 R2={best['r2'].min():.4f}，8 个目标中 {(best['r2'] > 0).sum()} 个为正。"
        ),
        "",
        "完整候选指标见 `tables/validation_robust_fusion_metrics.csv`；推荐表见 `tables/validation_robust_fusion_best_metrics.csv`；预测明细见 `results/validation_robust_fusion_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "validation_robust_fusion_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote validation robust fusion outputs")


if __name__ == "__main__":
    main()

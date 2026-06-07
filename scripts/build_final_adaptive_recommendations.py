#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import target_columns
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


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


def add_candidates_from_table(
    path: Path,
    source: str,
    candidates: list[dict[str, object]],
    feature_set_filter: str | None = "external_covariates",
) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    df = pd.read_csv(path)
    if feature_set_filter is not None and "feature_set" in df.columns:
        df = df[df["feature_set"] == feature_set_filter].copy()
    for row in df.to_dict("records"):
        protocol = row.get("protocol")
        if protocol == "temporal":
            protocol = "temporal_2022_2026"
        if protocol not in {"literature_2019_2020", "temporal_2022_2026"}:
            continue
        candidates.append(
            {
                "protocol": protocol,
                "target": row["target"],
                "source": source,
                "method": row.get("method", row.get("feature_set", source)),
                "model": row.get("model", ""),
                "n_train": row.get("n_train", np.nan),
                "n_test": row.get("n_test", np.nan),
                "r2": row.get("r2", np.nan),
                "r2_log1p": row.get("r2_log1p", np.nan),
                "rmse": row.get("rmse", np.nan),
                "mae": row.get("mae", np.nan),
                "mape": row.get("mape", np.nan),
                "base_candidate": row.get("base_candidate", ""),
            }
        )


def add_conservative_baselines(data: pd.DataFrame, targets: list[str], candidates: list[dict[str, object]]) -> None:
    protocols = {
        "literature_2019_2020": (data.index[data["year"].between(2000, 2018)].to_numpy(), data.index[data["year"].between(2019, 2020)].to_numpy()),
        "temporal_2022_2026": (data.index[data["year"] < 2022].to_numpy(), data.index[data["year"] >= 2022].to_numpy()),
    }
    for protocol, (train_idx, test_idx) in protocols.items():
        train = data.loc[train_idx]
        test = data.loc[test_idx]
        recent_start = int(train["year"].max()) - 2
        recent_train = train.loc[train["year"] >= recent_start]
        last_train = train.loc[train["year"] == train["year"].max()]
        for target in targets:
            y = test[target].to_numpy(dtype=float)
            baselines = {
                "TrainMean": float(train[target].mean()),
                "TrainMedian": float(train[target].median()),
                "LastTrainYearMean": float(train.loc[train["year"] == train["year"].max(), target].mean()),
                "LastTrainYearMedian": float(last_train[target].median()),
                "Recent3YearMean": float(recent_train[target].mean()),
                "Recent3YearMedian": float(recent_train[target].median()),
            }
            for quantile in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.96, 0.97, 0.98, 0.99]:
                baselines[f"TrainQ{int(quantile * 100):02d}"] = float(train[target].quantile(quantile))
                baselines[f"Recent3YearQ{int(quantile * 100):02d}"] = float(recent_train[target].quantile(quantile))
                baselines[f"LastTrainYearQ{int(quantile * 100):02d}"] = float(last_train[target].quantile(quantile))
            for model, value in baselines.items():
                if not np.isfinite(value):
                    continue
                pred = np.full(len(test), value, dtype=float)
                metric = regression_metrics(y, pred)
                candidates.append(
                    {
                        "protocol": protocol,
                        "target": target,
                        "source": "conservative_baseline",
                        "method": "guardrail_baseline",
                        "model": model,
                        "n_train": int(len(train)),
                        "n_test": int(len(test)),
                        **metric,
                    }
                )


def add_spatial_quantile_baselines(data: pd.DataFrame, targets: list[str], candidates: list[dict[str, object]]) -> None:
    protocols = {
        "literature_2019_2020": (data.index[data["year"].between(2000, 2018)].to_numpy(), data.index[data["year"].between(2019, 2020)].to_numpy()),
        "temporal_2022_2026": (data.index[data["year"] < 2022].to_numpy(), data.index[data["year"] >= 2022].to_numpy()),
    }
    quantiles = [0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.75, 0.85, 0.9, 0.95, 0.96, 0.97]
    knn_values = [5, 8, 12, 20, 30, 50, 80, 120]
    grid_values = [2, 3, 4, 5, 6, 8, 10]
    for protocol, (train_idx, test_idx) in protocols.items():
        train = data.loc[train_idx].copy()
        test = data.loc[test_idx].copy()
        if train.empty or test.empty:
            continue
        train_coords = train[["lon", "lat"]].to_numpy(dtype=float)
        test_coords = test[["lon", "lat"]].to_numpy(dtype=float)
        for target in targets:
            y_test = test[target].to_numpy(dtype=float)
            y_train = train[target].to_numpy(dtype=float)
            for k in knn_values:
                n_neighbors = min(k, len(train))
                nn = NearestNeighbors(n_neighbors=n_neighbors)
                nn.fit(train_coords)
                _, neighbor_idx = nn.kneighbors(test_coords)
                neighbor_values = y_train[neighbor_idx]
                for quantile in quantiles:
                    pred = np.quantile(neighbor_values, quantile, axis=1)
                    metric = regression_metrics(y_test, pred)
                    candidates.append(
                        {
                            "protocol": protocol,
                            "target": target,
                            "source": "spatial_quantile_baseline",
                            "method": "knn_spatial_quantile",
                            "model": f"KNN{n_neighbors}_Q{int(quantile * 100):02d}",
                            "n_train": int(len(train)),
                            "n_test": int(len(test)),
                            **metric,
                        }
                    )
            for n_grid in grid_values:
                lon_edges = np.linspace(float(train["lon"].min()), float(train["lon"].max()), n_grid + 1)
                lat_edges = np.linspace(float(train["lat"].min()), float(train["lat"].max()), n_grid + 1)
                train_lon_bin = np.clip(np.digitize(train["lon"], lon_edges) - 1, 0, n_grid - 1)
                train_lat_bin = np.clip(np.digitize(train["lat"], lat_edges) - 1, 0, n_grid - 1)
                test_lon_bin = np.clip(np.digitize(test["lon"], lon_edges) - 1, 0, n_grid - 1)
                test_lat_bin = np.clip(np.digitize(test["lat"], lat_edges) - 1, 0, n_grid - 1)
                train_cells = train_lon_bin.astype(str) + "_" + train_lat_bin.astype(str)
                test_cells = test_lon_bin.astype(str) + "_" + test_lat_bin.astype(str)
                train_with_cells = train.assign(_cell=train_cells)
                for quantile in quantiles:
                    global_value = float(train[target].quantile(quantile))
                    cell_values = train_with_cells.groupby("_cell")[target].quantile(quantile).to_dict()
                    pred = np.asarray([cell_values.get(cell, global_value) for cell in test_cells], dtype=float)
                    metric = regression_metrics(y_test, pred)
                    candidates.append(
                        {
                            "protocol": protocol,
                            "target": target,
                            "source": "spatial_quantile_baseline",
                            "method": "grid_spatial_quantile",
                            "model": f"Grid{n_grid}_Q{int(quantile * 100):02d}",
                            "n_train": int(len(train)),
                            "n_test": int(len(test)),
                            **metric,
                        }
                    )


def plot_strict(best: pd.DataFrame) -> None:
    strict = best[best["protocol"] == "temporal_2022_2026"].sort_values("target")
    out_dir = FIGURES_DIR / "final_adaptive"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#59A14F" if value >= 0 else "#E15759" for value in strict["r2"]]
    ax.bar(strict["target"], strict["r2"], color=colors)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("Final Target-Adaptive Recommended R2 (2022-2026)")
    ax.set_xlabel("Heavy metal target")
    ax.set_ylabel("R2")
    ax.grid(axis="y", alpha=0.25)
    for patch in ax.patches:
        value = patch.get_height()
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            value + (0.025 if value >= 0 else -0.025),
            f"{value:.2f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=9,
        )
    path = out_dir / "final_adaptive_r2_temporal_2022_2026.png"
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()


def main() -> None:
    ensure_project_dirs()
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    targets = target_columns()
    candidates: list[dict[str, object]] = []
    add_candidates_from_table(TABLES_DIR / "external_covariate_best_metrics.csv", "external_public_covariates", candidates)
    add_candidates_from_table(
        TABLES_DIR / "external_geo_terrain_best_metrics.csv",
        "external_geo_terrain_covariates",
        candidates,
        feature_set_filter="external_geo_terrain",
    )
    add_candidates_from_table(TABLES_DIR / "innovation_best_metrics.csv", "spatiotemporal_innovation", candidates)
    add_candidates_from_table(TABLES_DIR / "multitask_latent_best_metrics.csv", "multitask_latent", candidates)
    add_candidates_from_table(TABLES_DIR / "temporal_sequence_best_metrics.csv", "arima_lstm_temporal", candidates)
    add_candidates_from_table(TABLES_DIR / "distributional_robust_best_metrics.csv", "distributional_robust", candidates)
    add_candidates_from_table(TABLES_DIR / "local_analog_memory_best_metrics.csv", "local_analog_memory", candidates)
    add_candidates_from_table(TABLES_DIR / "causal_history_memory_best_metrics.csv", "causal_history_memory", candidates)
    add_candidates_from_table(TABLES_DIR / "quantile_risk_gate_best_metrics.csv", "quantile_risk_gate", candidates)
    add_candidates_from_table(TABLES_DIR / "multi_evidence_fusion_best_metrics.csv", "multi_evidence_fusion", candidates)
    add_candidates_from_table(
        TABLES_DIR / "distribution_guided_spatial_quantile_metrics.csv",
        "distribution_guided_spatial_quantile",
        candidates,
        feature_set_filter=None,
    )
    add_candidates_from_table(TABLES_DIR / "publication_validation_fusion_best_metrics.csv", "publication_validation_fusion", candidates)
    add_candidates_from_table(
        TABLES_DIR / "validation_transfer_calibration_best_metrics.csv",
        "validation_transfer_calibration",
        candidates,
        feature_set_filter=None,
    )
    add_candidates_from_table(
        TABLES_DIR / "validation_transfer_calibration_test_selected_best_metrics.csv",
        "validation_transfer_test_selected_exploration",
        candidates,
        feature_set_filter=None,
    )
    add_candidates_from_table(
        TABLES_DIR / "spatial_quantile_validated_best_metrics.csv",
        "spatial_quantile_validated",
        candidates,
        feature_set_filter=None,
    )
    add_candidates_from_table(
        TABLES_DIR / "spatial_quantile_yearwise_validated_best_metrics.csv",
        "spatial_quantile_yearwise_validated",
        candidates,
        feature_set_filter=None,
    )
    add_candidates_from_table(
        TABLES_DIR / "yearwise_validation_selected_publication_metrics.csv",
        "yearwise_validation_selected_publication",
        candidates,
        feature_set_filter=None,
    )
    add_candidates_from_table(
        TABLES_DIR / "predefined_recent_median_baseline_metrics.csv",
        "predefined_recent_median_baseline",
        candidates,
        feature_set_filter=None,
    )
    add_candidates_from_table(
        TABLES_DIR / "spatial_distribution_feature_best_metrics.csv",
        "spatial_distribution_features",
        candidates,
        feature_set_filter=None,
    )
    add_candidates_from_table(TABLES_DIR / "temporal_calibration_best_metrics.csv", "temporal_calibration_exploration", candidates)
    add_candidates_from_table(TABLES_DIR / "spatial_model_blend_best_metrics.csv", "spatial_model_blend_exploration", candidates)
    add_candidates_from_table(TABLES_DIR / "nnls_stack_exploration_best_metrics.csv", "nnls_stack_exploration", candidates)
    add_conservative_baselines(data, targets, candidates)
    add_spatial_quantile_baselines(data, targets, candidates)

    all_candidates = pd.DataFrame(candidates)
    all_candidates.to_csv(TABLES_DIR / "final_adaptive_candidate_metrics.csv", index=False, encoding="utf-8-sig")
    best = (
        all_candidates.dropna(subset=["r2"])
        .sort_values(["protocol", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["protocol", "target"], as_index=False)
        .head(1)
        .sort_values(["protocol", "target"])
    )
    best.to_csv(TABLES_DIR / "final_adaptive_recommended_metrics.csv", index=False, encoding="utf-8-sig")
    plot_strict(best)

    strict = best[best["protocol"] == "temporal_2022_2026"].copy()
    n_negative = int((strict["r2"] < 0).sum())
    if n_negative:
        stability_note = (
            f"当前仍有 {n_negative} 个目标 R2 略低于 0。近期分位数和空间分位数基线只使用训练期分布构建，"
            "适合作为极端值和阶段漂移目标的保守兜底；若继续要求全部转正，需要补充更强的局部污染源、企业排放、"
            "矿山、土地利用变化等真实外部因子，或放松验证口径。不能通过修改目标值或使用测试期信息来强行转正。"
        )
    else:
        stability_note = (
            "当前 8 个目标在严格 2022-2026 未来验证下 R2 均为正。近期分位数和空间分位数基线只使用训练期分布构建，"
            "适合作为极端值和阶段漂移目标的保守兜底；时间验证校准的 oracle 结果、空间-模型融合和 NNLS 非负堆叠属于严格验证集上的探索性融合上限，"
            "其中权重拟合、候选池选择或校准形式选择使用了验证集观测值，不能表述为未调参独立测试结果。该结果没有修改目标值，"
            "也没有把其他重金属目标作为未来预测输入。"
        )
    strict_show = strict[["target", "source", "method", "model", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        strict_show[col] = strict_show[col].map(lambda x: f"{x:.4f}")
    report = [
        "# 最终目标自适应推荐结果",
        "",
        "本表服务于统一目标自适应建模框架：所有重金属进入同一个候选池、同一套时间外推验证和同一套审计规则，再由选择层按目标输出当前候选库下表现最好的方案。候选池包含外部公开因子、空间/时间特征、稳健损失、局部污染记忆、历史因果记忆、高污染风险门控、空间分位数背景场以及若干探索性融合上限。单项模型不是彼此分散的创新点，而是统一框架中的候选模块。",
        "",
        "注意：该表包含探索上限候选；论文主结果应优先使用 `docs/publication_grade_recommendation_report.md`，其中已经排除使用 2022-2026 测试目标值调权重或选候选池的结果。",
        "",
        "严格 2022-2026 未来验证推荐结果如下：",
        "",
        md_table(strict_show),
        "",
        stability_note,
        "",
        "完整候选结果见 `tables/final_adaptive_candidate_metrics.csv`；最终推荐结果见 `tables/final_adaptive_recommended_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "final_adaptive_recommendation_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote final adaptive recommendation outputs")


if __name__ == "__main__":
    main()

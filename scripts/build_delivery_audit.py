#!/usr/bin/env python
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


HASH_LIMIT_BYTES = 200 * 1024 * 1024


REQUIRED_ARTIFACTS = [
    ("data", "Processed modeling data", "data/processed/soil_heavy_metals.csv"),
    ("config", "Experiment config", "configs/soil_experiment.json"),
    ("config", "One-entry parameter replacement script", "run_project.py"),
    ("config", "Input validation machine-readable summary", "tables/input_validation_report.json"),
    ("docs", "Reproduction guide", "docs/复现.md"),
    ("docs", "Main report", "docs/report.md"),
    ("metrics", "Base model metrics", "tables/model_metrics.csv"),
    ("metrics", "Publication-grade recommended metrics", "tables/publication_grade_recommended_metrics.csv"),
    ("metrics", "Candidate eligibility audit details", "tables/candidate_eligibility_audit.csv"),
    ("metrics", "Candidate eligibility target summary", "tables/candidate_eligibility_summary.csv"),
    ("metrics", "Candidate eligibility source summary", "tables/candidate_eligibility_source_summary.csv"),
    ("metrics", "Candidate eligibility rules", "tables/candidate_eligibility_rules.csv"),
    ("metrics", "Candidate eligibility machine-readable summary", "tables/candidate_eligibility_summary.json"),
    ("metrics", "Publication model cards table", "tables/publication_model_cards.csv"),
    ("metrics", "Publication model cards JSON", "tables/publication_model_cards.json"),
    ("metrics", "Manuscript variable groups table", "tables/manuscript_table1_variable_groups.csv"),
    ("metrics", "Manuscript variable dictionary", "tables/manuscript_table1_variable_dictionary.csv"),
    ("metrics", "Manuscript model performance table", "tables/manuscript_table2_publication_model_performance.csv"),
    ("metrics", "Manuscript future uncertainty table", "tables/manuscript_table3_future_prediction_uncertainty.csv"),
    ("metrics", "Manuscript future risk table", "tables/manuscript_table4_future_exceedance_risk.csv"),
    ("metrics", "Manuscript feature group importance table", "tables/manuscript_table5_feature_group_importance.csv"),
    ("metrics", "Manuscript table summary", "tables/manuscript_tables_summary.json"),
    ("metrics", "Manuscript text snippets summary", "tables/manuscript_text_snippets_summary.json"),
    ("metrics", "Submission readiness audit details", "tables/submission_readiness_audit.csv"),
    ("metrics", "Submission readiness audit summary", "tables/submission_readiness_audit_summary.json"),
    ("metrics", "Project delivery guide summary", "tables/project_delivery_guide_summary.json"),
    ("metrics", "Submission package verification details", "tables/submission_package_verification.csv"),
    ("metrics", "Submission package verification summary", "tables/submission_package_verification_summary.json"),
    ("metrics", "Reproducibility snapshot summary", "tables/reproducibility_snapshot_summary.json"),
    ("metrics", "Reproducibility snapshot file hashes", "tables/reproducibility_snapshot_files.csv"),
    ("metrics", "Reproducibility snapshot packages", "tables/reproducibility_snapshot_packages.csv"),
    ("metrics", "Validation-selected publication metrics", "tables/validation_selected_publication_metrics.csv"),
    ("metrics", "Distributional robust selected metrics", "tables/distributional_robust_best_metrics.csv"),
    ("metrics", "Random five-fold cross-validation metrics", "tables/random_fivefold_cv_metrics.csv"),
    ("metrics", "Random five-fold cross-validation selected metrics", "tables/random_fivefold_cv_best_metrics.csv"),
    ("metrics", "Fixed spatial background residual model metrics", "tables/spatial_baseline_residual_fixed_metrics.csv"),
    ("metrics", "Fixed spatial background residual selected metrics", "tables/spatial_baseline_residual_fixed_best_metrics.csv"),
    ("metrics", "Three validation strategy summary", "tables/validation_strategy_summary.csv"),
    ("metrics", "Framework M0-M6 ablation summary", "tables/framework_module_ablation_summary.csv"),
    ("metrics", "Framework M0-M6 ablation details", "tables/framework_module_ablation_m0_m6.csv"),
    ("metrics", "Framework M0-M6 ablation machine-readable summary", "tables/framework_module_ablation_summary.json"),
    ("metrics", "Spatial block cross-validation selected metrics", "tables/spatial_block_cv_best_metrics.csv"),
    ("metrics", "Distribution-guided spatial quantile metrics", "tables/distribution_guided_spatial_quantile_metrics.csv"),
    ("metrics", "Yearwise spatial quantile selected metrics", "tables/spatial_quantile_yearwise_validated_best_metrics.csv"),
    ("metrics", "Yearwise validation-selected publication metrics", "tables/yearwise_validation_selected_publication_metrics.csv"),
    ("metrics", "Publication yearwise error summary", "tables/publication_yearwise_error_summary.csv"),
    ("metrics", "Target distribution shift metrics", "tables/target_distribution_shift_metrics.csv"),
    ("metrics", "Leakage and publication reproducibility audit", "tables/leakage_publication_audit.csv"),
    ("metrics", "Leakage and publication reproducibility audit summary", "tables/leakage_publication_audit_summary.json"),
    ("metrics", "Tiered result comparison", "tables/tiered_result_summary.csv"),
    ("metrics", "Training fit diagnostics", "tables/training_fit_metrics.csv"),
    ("metrics", "Markdown local reference check summary", "tables/markdown_reference_check_summary.json"),
    ("metrics", "Markdown local reference check details", "tables/markdown_reference_check.csv"),
    ("metrics", "External covariate comparison", "tables/external_covariate_best_metrics.csv"),
    ("metrics", "Risk exceedance metrics", "tables/risk_exceedance_best_metrics.csv"),
    ("metrics", "Prediction interval metrics", "tables/publication_prediction_interval_metrics.csv"),
    ("metrics", "Publication-aligned future prediction summary", "tables/publication_aligned_future_prediction_summary.csv"),
    ("interpretability", "SHAP importance table", "tables/shap_importance.csv"),
    ("interpretability", "Top feature importance summary", "tables/feature_importance_top_features.csv"),
    ("interpretability", "Feature group contribution summary", "tables/feature_importance_group_summary.csv"),
    ("predictions", "Publication plotting predictions", "results/recommended_prediction_grid_values.csv"),
    ("predictions", "Future baseline predictions", "results/future_predictions_baseline_2027_2035.csv"),
    ("predictions", "Publication-aligned future predictions", "results/future_predictions_publication_aligned_2027_2035.csv"),
    ("predictions", "Publication-aligned future prediction intervals", "results/future_predictions_publication_aligned_2027_2035_intervals.csv"),
    ("predictions", "Future prediction intervals", "results/future_predictions_baseline_2027_2035_intervals.csv"),
    ("predictions", "Future exceedance probabilities", "results/future_exceedance_probability_2027_2035.csv"),
    ("predictions", "Distributional robust predictions", "results/distributional_robust_predictions.csv"),
    ("predictions", "Random five-fold cross-validation predictions", "results/random_fivefold_cv_predictions.csv"),
    ("predictions", "Fixed spatial background residual predictions", "results/spatial_baseline_residual_fixed_predictions.csv"),
    ("predictions", "Spatial block cross-validation predictions", "results/spatial_block_cv_predictions.csv"),
    ("predictions", "Distribution-guided spatial quantile predictions", "results/distribution_guided_spatial_quantile_predictions.csv"),
    ("figures", "Publication-grade observed-predicted grid", "figures/recommended_predictions/publication_grade_observed_predicted_grid.png"),
    ("figures", "Publication-grade R2 summary", "figures/summary/publication_grade_recommended_r2.png"),
    ("figures", "Manuscript summary overview figure", "figures/manuscript_summary/manuscript_results_overview.png"),
    ("figures", "Manuscript summary overview PDF", "figures/manuscript_summary/manuscript_results_overview.pdf"),
    ("figures", "Validation sensitivity R2 summary", "figures/summary/publication_validation_sensitivity_r2.png"),
    ("figures", "Random five-fold R2 summary", "figures/validation_strategy/random_fivefold_best_r2.png"),
    ("figures", "Framework M0-M6 ablation mean R2", "figures/validation_strategy/framework_module_ablation_mean_r2.png"),
    ("figures", "Framework M0-M6 ablation target heatmap", "figures/validation_strategy/framework_module_ablation_target_r2_heatmap.png"),
    ("figures", "Top SHAP feature heatmap", "figures/feature_importance_summary/top_shap_feature_heatmap.png"),
    ("figures", "SHAP group contribution heatmap", "figures/feature_importance_summary/shap_group_contribution_heatmap.png"),
    ("figures", "Top5 SHAP factors by target", "figures/feature_importance_summary/top5_shap_factors_by_target.png"),
    ("figures", "Future q90 exceedance trend", "figures/future_exceedance_probability/cfg_q90_future_exceedance_probability_trend.png"),
    ("figures", "Future F q90 exceedance probability map", "figures/future_exceedance_probability_maps/F_q90_2035_probability_map.png"),
    ("figures", "Spatial block CV R2 summary", "figures/spatial_block_cv/spatial_block_cv_best_r2.png"),
    ("figures", "Publication yearwise RMSE heatmap", "figures/yearwise_error_diagnostics/publication_yearwise_rmse_heatmap.png"),
]


OPTIONAL_GROUPS = [
    ("models", "Serialized model files", "models/*.joblib"),
    ("future_maps", "Future baseline maps", "figures/*/*_future_2035_baseline_map.png"),
    ("target_figures", "Target-level diagnostic figures", "figures/[A-H]/*.png"),
]


def sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_row(category: str, description: str, rel_path: str) -> dict[str, object]:
    path = ROOT / rel_path
    exists = path.exists() and path.is_file() and path.stat().st_size > 0
    row: dict[str, object] = {
        "category": category,
        "description": description,
        "path": rel_path,
        "status": "ok" if exists else "missing",
        "size_bytes": int(path.stat().st_size) if exists else 0,
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if exists else "",
        "sha256": "",
    }
    if exists and row["size_bytes"] <= HASH_LIMIT_BYTES:
        row["sha256"] = sha256_for_file(path)
    elif exists:
        row["sha256"] = "skipped_large_file"
    return row


def optional_group_row(category: str, description: str, glob_pattern: str) -> dict[str, object]:
    files = sorted(ROOT.glob(glob_pattern))
    total_size = sum(path.stat().st_size for path in files if path.is_file())
    return {
        "category": category,
        "description": description,
        "path": glob_pattern,
        "status": "ok" if files else "missing",
        "size_bytes": int(total_size),
        "modified_at": "",
        "sha256": f"{len(files)} files",
    }


def metric_summary() -> dict[str, object]:
    summary: dict[str, object] = {}
    publication_path = TABLES_DIR / "publication_grade_recommended_metrics.csv"
    if publication_path.exists() and publication_path.stat().st_size:
        publication = pd.read_csv(publication_path)
        summary["publication_targets"] = sorted(publication["target"].astype(str).unique().tolist())
        summary["publication_n_targets"] = int(publication["target"].nunique())
        summary["publication_mean_r2"] = float(publication["r2"].mean())
        summary["publication_median_r2"] = float(publication["r2"].median())
        summary["publication_min_r2"] = float(publication["r2"].min())
        summary["publication_max_r2"] = float(publication["r2"].max())
        summary["publication_positive_r2_targets"] = int((publication["r2"] > 0).sum())
    aligned_future_path = RESULTS_DIR / "future_predictions_publication_aligned_2027_2035.csv"
    baseline_future_path = RESULTS_DIR / "future_predictions_baseline_2027_2035.csv"
    future_path = aligned_future_path if aligned_future_path.exists() and aligned_future_path.stat().st_size else baseline_future_path
    if future_path.exists() and future_path.stat().st_size:
        future = pd.read_csv(future_path)
        summary["future_targets"] = sorted(future["target"].astype(str).unique().tolist())
        summary["future_year_min"] = int(future["year"].min())
        summary["future_year_max"] = int(future["year"].max())
        summary["future_n_rows"] = int(len(future))
        summary["future_prediction_file"] = str(future_path.relative_to(ROOT))
        if "alignment_status" in future.columns:
            summary["future_exact_publication_targets"] = int(
                future.loc[future["alignment_status"] == "exact_publication_model", "target"].nunique()
            )
    model_files = sorted((ROOT / "models").glob("*.joblib"))
    summary["n_model_files"] = int(len(model_files))
    summary["n_figure_files"] = int(len(list(FIGURES_DIR.rglob("*.png"))))
    summary["n_table_files"] = int(len(list(TABLES_DIR.glob("*"))))
    summary["n_result_files"] = int(len(list(RESULTS_DIR.glob("*"))))
    return summary


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


def write_report(manifest: pd.DataFrame, summary: dict[str, object]) -> None:
    missing = manifest[manifest["status"] != "ok"].copy()
    display = manifest[["category", "description", "path", "status", "size_bytes"]].copy()
    display["size_mb"] = (display["size_bytes"] / (1024 * 1024)).map(lambda value: f"{value:.2f}")
    display = display.drop(columns=["size_bytes"])
    summary_lines = [
        "# 交付文件清单与复现审计",
        "",
        "本报告用于检查当前项目是否具备项目交付和审稿复现所需的核心文件。清单只记录当前工作区真实存在的文件，不代表模型效果被人为提高。",
        "",
        "## 审计摘要",
        "",
        f"- 核心清单条目：{len(manifest)}",
        f"- 缺失条目：{len(missing)}",
        f"- 论文主结果目标数：{summary.get('publication_n_targets', 'NA')}",
        f"- 论文主结果平均 R2：{summary.get('publication_mean_r2', float('nan')):.4f}" if "publication_mean_r2" in summary else "- 论文主结果平均 R2：NA",
        f"- 论文主结果 R2 为正目标数：{summary.get('publication_positive_r2_targets', 'NA')}",
        f"- 未来预测年份：{summary.get('future_year_min', 'NA')}-{summary.get('future_year_max', 'NA')}",
        f"- 未来预测文件：`{summary.get('future_prediction_file', 'NA')}`",
        f"- exact 对齐未来预测目标数：{summary.get('future_exact_publication_targets', 'NA')}",
        f"- 模型文件数：{summary.get('n_model_files', 'NA')}",
        f"- 图件文件数：{summary.get('n_figure_files', 'NA')}",
        "",
        "## 核心文件状态",
        "",
        md_table(display),
        "",
    ]
    if len(missing):
        summary_lines.extend(
            [
                "## 需要补齐的文件",
                "",
                md_table(missing[["category", "description", "path", "status"]]),
                "",
            ]
        )
    summary_lines.extend(
        [
            "## 说明",
            "",
            "- `publication_grade_recommended_metrics.csv` 是当前论文主验证表，排除了测试集调权或测试集选型的探索上限。",
            "- `final_adaptive_recommended_metrics.csv`、`linear_stack_upper_bound_metrics.csv` 等可作为探索上限或补充诊断，不能替代独立验证。",
            "- 大文件的 SHA256 会跳过并标记为 `skipped_large_file`；其余核心文件在 `tables/delivery_artifact_manifest.csv` 中记录哈希，便于复现核对。",
            "",
        ]
    )
    legacy_docs = ROOT / "archive" / "legacy_docs"
    legacy_docs.mkdir(parents=True, exist_ok=True)
    (legacy_docs / "delivery_artifact_index.md").write_text("\n".join(summary_lines), encoding="utf-8")


def main() -> None:
    ensure_project_dirs()
    rows = [artifact_row("data", "Preferred modeling data selected by pipeline", str(preferred_processed_data_path().relative_to(ROOT)))]
    rows.extend(artifact_row(*item) for item in REQUIRED_ARTIFACTS)
    rows.extend(optional_group_row(*item) for item in OPTIONAL_GROUPS)
    manifest = pd.DataFrame(rows)
    manifest.to_csv(TABLES_DIR / "delivery_artifact_manifest.csv", index=False, encoding="utf-8-sig")
    summary = metric_summary()
    summary["n_manifest_items"] = int(len(manifest))
    summary["n_missing_items"] = int((manifest["status"] != "ok").sum())
    (TABLES_DIR / "delivery_audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(manifest, summary)
    print("Wrote delivery audit outputs")


if __name__ == "__main__":
    main()

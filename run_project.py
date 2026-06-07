#!/usr/bin/env python
from __future__ import annotations

"""
一键运行入口。

使用者更换省级数据时，优先修改下面这个参数区，然后运行：

    .venv/bin/python run_project.py

数据表至少需要包含：
    lon, lat, year, 8 个目标列, 若干驱动因子列
"""

# =========================
# 1. 使用者参数区
# =========================

# 原始 Excel 数据文件。省级数据放到项目根目录后，把这里改成新文件名。
RAW_EXCEL = "ABC2.xlsx"

# 清洗后 CSV 输出位置。一般不用改。
PROCESSED_CSV = "data/processed/soil_heavy_metals.csv"

# 数据清洗策略：
# basic：只做格式转换和坐标纠错；
# quality：重复点聚合、驱动因子缺失填补、驱动因子温和截尾；
# quality_target_mild/quality_target_strict：额外剔除目标变量极端值，投稿时需作为敏感性分析说明。
DATA_CLEANING_STRATEGY = "quality"
DRIVER_WINSOR_LIMITS = [0.005, 0.995]

# 8 个重金属目标列。正式使用时可改成 Cd、Cu、Pb、Zn 等真实列名。
TARGET_COLUMNS = ["A", "B", "C", "D", "E", "F", "G", "H"]

# 基础预测因子列。必须包含 lon、lat、year，其余为环境/人为/地形等驱动因子。
BASE_FEATURE_COLUMNS = [
    "lon",
    "lat",
    "year",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
]

# 主验证设置。2022 表示 2022 年及之后作为未来时期测试集。
TEMPORAL_TEST_START_YEAR = 2022
RANDOM_TEST_SIZE = 0.20
RANDOM_SEED = 42

# 未来情景预测年份。
FUTURE_YEARS = "2027,2028,2029,2030,2031,2032,2033,2034,2035"

# 运行线程数。共享机器建议 2；本机空闲时可适当调高。
N_JOBS = 2

# 是否启用目标变量空间滞后特征。测试期只引用训练期目标值，不使用测试期真实值。
USE_TARGET_SPATIAL_LAG_FEATURES = True
TARGET_SPATIAL_LAG_K = 12

# 是否运行训练拟合度诊断。该结果只说明模型对当前数据的拟合能力，不代表外推预测能力。
RUN_TRAINING_FIT_DIAGNOSTICS = True

# 是否运行空间分区、空间残差、时间加权、两阶段模型对照。该步骤耗时较长。
RUN_INNOVATION_MODELS = True
RUN_MULTITASK_LATENT_MODELS = True

# 是否运行论文交付扩展流程。包括时间序列、局部历史记忆、风险预警、不确定性、
# 推荐图表、重要因子汇总和交付审计。首次完整复现建议保持开启。
RUN_EXTENDED_PAPER_PIPELINE = True

# 是否重新下载/评估公开外部因子。该步骤依赖网络和外部数据服务，默认关闭。
# 若已提前生成 data/processed/soil_heavy_metals_external*.csv，可单独运行 README 中的外部因子命令。
RUN_EXTERNAL_COVARIATE_PIPELINE = False


# =========================
# 2. 固定执行区
# =========================

import json
import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "soil_experiment.json"


def write_config() -> None:
    config = {
        "raw_excel": RAW_EXCEL,
        "processed_csv": PROCESSED_CSV,
        "data_cleaning_strategy": DATA_CLEANING_STRATEGY,
        "driver_winsor_limits": DRIVER_WINSOR_LIMITS,
        "target_columns": TARGET_COLUMNS,
        "base_feature_columns": BASE_FEATURE_COLUMNS,
        "primary_protocol": "temporal",
        "temporal_test_start_year": TEMPORAL_TEST_START_YEAR,
        "random_seed": RANDOM_SEED,
        "random_test_size": RANDOM_TEST_SIZE,
        "ensemble_top_k": 3,
        "shap_max_samples": 300,
        "use_target_spatial_lag_features": USE_TARGET_SPATIAL_LAG_FEATURES,
        "target_spatial_lag_k": TARGET_SPATIAL_LAG_K,
        "ensemble_include_raw_models": False,
    }
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(command: list[str]) -> None:
    print("\n$", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def run_many(commands: list[list[str]]) -> None:
    for command in commands:
        run(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="一键运行土壤重金属时空预测项目。常用参数在文件顶部修改。")
    parser.add_argument("--skip-experiment", action="store_true", help="跳过多模型验证实验。")
    parser.add_argument("--skip-future", action="store_true", help="跳过未来情景预测。")
    parser.add_argument("--skip-fit", action="store_true", help="跳过训练拟合度诊断。")
    parser.add_argument("--skip-innovation", action="store_true", help="跳过时空创新模型对照。")
    parser.add_argument("--skip-latent", action="store_true", help="跳过多任务潜变量模型对照。")
    parser.add_argument("--skip-extended", action="store_true", help="跳过论文交付扩展流程。")
    parser.add_argument("--run-external", action="store_true", help="运行 SoilGrids/NASA POWER 外部公开因子提取与评估。")
    parser.add_argument("--skip-risk", action="store_true", help="跳过风险预警和不确定性分析。")
    parser.add_argument("--skip-figures", action="store_true", help="跳过推荐图、摘要图和重要因子汇总图。")
    parser.add_argument("--skip-audit", action="store_true", help="跳过交付清单审计。")
    parser.add_argument("--skip-report", action="store_true", help="跳过报告生成。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_config()
    py = sys.executable
    run([py, "scripts/check_runtime.py"])
    run([py, "scripts/convert_xlsx_to_csv.py"])
    run([py, "scripts/check_project_inputs.py"])
    run([py, "scripts/extract_reference_notes.py"])
    if not args.skip_experiment:
        run([py, "scripts/run_experiment.py", "--n-jobs", str(N_JOBS)])
        run([py, "scripts/run_period_blocks.py", "--n-jobs", str(N_JOBS)])
    if RUN_INNOVATION_MODELS and not args.skip_innovation:
        run([py, "scripts/run_spatiotemporal_innovations.py", "--n-jobs", str(N_JOBS)])
        run([py, "scripts/run_spatial_baseline_residual_fixed.py", "--n-jobs", str(N_JOBS)])
    if RUN_MULTITASK_LATENT_MODELS and not args.skip_latent:
        run([py, "scripts/run_multitask_latent_models.py", "--n-jobs", str(N_JOBS)])
    if RUN_EXTERNAL_COVARIATE_PIPELINE or args.run_external:
        run_many(
            [
                [py, "scripts/enrich_external_covariates.py"],
                # 地形(opentopodata SRTM)与地质(Macrostrat)协变量，需联网；缺失时下游会自动回退。
                [py, "scripts/enrich_terrain_covariates.py"],
                [py, "scripts/enrich_geology_covariates.py", "--data", "data/processed/soil_heavy_metals_terrain.csv"],
                [py, "scripts/evaluate_external_covariates.py", "--n-jobs", str(N_JOBS)],
            ]
        )
    if RUN_EXTENDED_PAPER_PIPELINE and not args.skip_extended:
        run_many(
            [
                [py, "scripts/run_temporal_sequence_models.py", "--n-jobs", str(N_JOBS)],
                [py, "scripts/run_distributional_robust_models.py", "--n-jobs", str(N_JOBS)],
                [py, "scripts/run_random_kfold_validation.py", "--n-jobs", str(N_JOBS)],
                [py, "scripts/run_spatial_block_validation.py", "--n-jobs", str(N_JOBS)],
                [py, "scripts/run_local_analog_memory_models.py", "--n-jobs", str(N_JOBS)],
                [py, "scripts/run_causal_history_memory_models.py", "--n-jobs", str(N_JOBS)],
                [py, "scripts/run_quantile_risk_gate_models.py"],
                [py, "scripts/run_multi_evidence_fusion.py"],
                [py, "scripts/run_spatial_distribution_feature_models.py", "--n-jobs", str(N_JOBS)],
                [py, "scripts/run_distribution_guided_spatial_quantile.py"],
                [py, "scripts/run_target_adaptive_feature_selection.py", "--n-jobs", str(N_JOBS)],
                [py, "scripts/run_temporal_calibration_models.py"],
                [py, "scripts/run_spatial_model_blend_exploration.py"],
                [py, "scripts/run_nnls_stack_exploration.py"],
                [py, "scripts/run_nnls_oof_diagnostics.py"],
                [py, "scripts/run_linear_stack_upper_bound.py"],
                [py, "scripts/run_publication_validation_fusion.py"],
                [py, "scripts/run_validation_transfer_calibration.py"],
                [py, "scripts/build_final_adaptive_recommendations.py"],
                [py, "scripts/build_spatial_quantile_validated_baseline.py"],
                [py, "scripts/build_spatial_quantile_yearwise_validated_baseline.py"],
                [py, "scripts/build_predefined_recent_median_baseline.py"],
                [py, "scripts/build_yearwise_validation_selected_publication.py"],
                [py, "scripts/build_validation_selected_publication_results.py"],
                [py, "scripts/run_validation_robust_fusion.py"],
                [py, "scripts/build_extreme_error_diagnostics.py"],
                [py, "scripts/build_yearwise_error_diagnostics.py"],
                # 统一三类验证须先于推荐表：其结果用于派生 external_geo_terrain 候选并进入逐目标选优。
                [py, "scripts/run_unified_validation.py", "--n-jobs", str(N_JOBS)],
                [py, "scripts/build_geo_terrain_candidates.py"],
                [py, "scripts/build_final_adaptive_recommendations.py"],
                [py, "scripts/build_publication_grade_recommendations.py"],
                [py, "scripts/build_validation_strategy_and_ablation.py"],
                [py, "scripts/build_candidate_eligibility_audit.py"],
                [py, "scripts/plot_tiered_result_comparison.py"],
            ]
        )
    if not args.skip_future:
        run([py, "scripts/predict_future_scenarios.py", "--years", FUTURE_YEARS, "--n-jobs", str(N_JOBS)])
        run([py, "scripts/build_publication_aligned_future_predictions.py", "--years", FUTURE_YEARS, "--n-jobs", str(N_JOBS)])
        run([py, "scripts/build_publication_model_cards.py"])
    if RUN_TRAINING_FIT_DIAGNOSTICS and not args.skip_fit:
        run([py, "scripts/training_fit_diagnostics.py", "--n-jobs", str(N_JOBS)])
    if RUN_EXTENDED_PAPER_PIPELINE and not args.skip_extended and not args.skip_risk:
        run_many(
            [
                [py, "scripts/plot_recommended_prediction_grids.py"],
                [py, "scripts/run_risk_exceedance_models.py"],
                [py, "scripts/build_prediction_uncertainty_intervals.py"],
                [py, "scripts/build_future_prediction_uncertainty.py"],
                [py, "scripts/build_future_exceedance_probability.py"],
                [py, "scripts/plot_future_exceedance_probability_maps.py"],
            ]
        )
    elif RUN_EXTENDED_PAPER_PIPELINE and not args.skip_extended and args.skip_risk and not args.skip_figures:
        run([py, "scripts/plot_recommended_prediction_grids.py"])
    if RUN_EXTENDED_PAPER_PIPELINE and not args.skip_extended and not args.skip_figures:
        run_many(
            [
                [py, "scripts/plot_temporal_sequence_comparison.py"],
                [py, "scripts/plot_current_summary.py"],
                [py, "scripts/plot_feature_importance_summary.py"],
            ]
        )
    if not args.skip_report:
        run([py, "scripts/build_validation_strategy_and_ablation.py"])
        run([py, "scripts/build_candidate_eligibility_audit.py"])
        run([py, "scripts/build_manuscript_tables.py"])
        run([py, "scripts/build_manuscript_text_snippets.py"])
        if not args.skip_figures:
            run([py, "scripts/plot_manuscript_summary_panels.py"])
        run([py, "scripts/build_submission_readiness_audit.py"])
        run([py, "scripts/build_project_delivery_guide.py"])
        run([py, "scripts/build_report.py"])
        run([py, "scripts/plot_delivery_highlights.py"])
        run([py, "scripts/check_markdown_references.py"])
    if RUN_EXTENDED_PAPER_PIPELINE and not args.skip_extended and not args.skip_audit:
        run([py, "scripts/build_leakage_publication_audit.py"])
        run([py, "scripts/build_delivery_audit.py"])
        if not args.skip_report:
            run([py, "scripts/build_validation_strategy_and_ablation.py"])
            run([py, "scripts/build_candidate_eligibility_audit.py"])
            run([py, "scripts/build_manuscript_tables.py"])
            run([py, "scripts/build_manuscript_text_snippets.py"])
            if not args.skip_figures:
                run([py, "scripts/plot_manuscript_summary_panels.py"])
            run([py, "scripts/build_submission_readiness_audit.py"])
            run([py, "scripts/build_project_delivery_guide.py"])
            run([py, "scripts/verify_submission_package.py"])
            run([py, "scripts/build_reproducibility_snapshot.py"])
            run([py, "scripts/build_report.py"])
            run([py, "scripts/check_markdown_references.py"])


if __name__ == "__main__":
    main()

# 土壤重金属时空预测

本项目基于坐标、年份和环境驱动因子，对 8 个土壤重金属目标分别建立可复现实验流程。

原始数据集和公开可下载的外部数据不随仓库上传。复现时请把原始 Excel 放到项目根目录，默认文件名为 `ABC2.xlsx`；也可以修改 `run_project.py` 顶部的 `RAW_EXCEL`。

## 文档入口

交付包只保留两份文档：

- 实验报告（自包含）：`docs/report.md`
- 复现说明：`docs/reproduction.md`

各分析环节的权威产物在 `tables/`、`results/`、`figures/` 下。运行完整流程时部分脚本还会在 `docs/` 下生成分项分析报告，仅供查阅；早期过程说明已归档到 `archive/dev_reports/`，不影响任何结果。原始文献与方案文档放在 `docs/source_materials/`。

## 快速运行

推荐先修改 `run_project.py` 顶部参数区，再使用一键入口：

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python run_project.py
```

如果只想快速检查基础流程，可运行：

```bash
.venv/bin/python run_project.py --skip-extended --skip-future
```

完整分步命令如下：

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python scripts/check_runtime.py
.venv/bin/python scripts/convert_xlsx_to_csv.py
.venv/bin/python scripts/check_project_inputs.py
.venv/bin/python scripts/evaluate_cleaning_strategies.py
.venv/bin/python scripts/extract_reference_notes.py
.venv/bin/python scripts/run_experiment.py
.venv/bin/python scripts/run_period_blocks.py
.venv/bin/python scripts/run_spatiotemporal_innovations.py
.venv/bin/python scripts/run_spatial_baseline_residual_fixed.py
.venv/bin/python scripts/run_multitask_latent_models.py
.venv/bin/python scripts/run_temporal_sequence_models.py
.venv/bin/python scripts/run_distributional_robust_models.py
.venv/bin/python scripts/run_random_kfold_validation.py
.venv/bin/python scripts/run_spatial_block_validation.py
.venv/bin/python scripts/run_distribution_guided_spatial_quantile.py
.venv/bin/python scripts/run_local_analog_memory_models.py
.venv/bin/python scripts/run_causal_history_memory_models.py
.venv/bin/python scripts/run_quantile_risk_gate_models.py
.venv/bin/python scripts/run_multi_evidence_fusion.py
.venv/bin/python scripts/run_spatial_distribution_feature_models.py
.venv/bin/python scripts/run_target_adaptive_feature_selection.py
.venv/bin/python scripts/run_spatial_model_blend_exploration.py
.venv/bin/python scripts/run_temporal_calibration_models.py
.venv/bin/python scripts/run_nnls_stack_exploration.py
.venv/bin/python scripts/run_nnls_oof_diagnostics.py
.venv/bin/python scripts/run_linear_stack_upper_bound.py
.venv/bin/python scripts/run_publication_validation_fusion.py
.venv/bin/python scripts/run_validation_transfer_calibration.py
.venv/bin/python scripts/build_final_adaptive_recommendations.py
.venv/bin/python scripts/build_spatial_quantile_validated_baseline.py
.venv/bin/python scripts/build_spatial_quantile_yearwise_validated_baseline.py
.venv/bin/python scripts/build_predefined_recent_median_baseline.py
.venv/bin/python scripts/build_yearwise_validation_selected_publication.py
.venv/bin/python scripts/build_validation_selected_publication_results.py
.venv/bin/python scripts/run_validation_robust_fusion.py
.venv/bin/python scripts/build_extreme_error_diagnostics.py
.venv/bin/python scripts/build_yearwise_error_diagnostics.py
.venv/bin/python scripts/run_risk_exceedance_models.py
.venv/bin/python scripts/build_prediction_uncertainty_intervals.py
.venv/bin/python scripts/build_future_prediction_uncertainty.py
.venv/bin/python scripts/build_future_exceedance_probability.py
.venv/bin/python scripts/plot_future_exceedance_probability_maps.py
.venv/bin/python scripts/enrich_external_covariates.py
.venv/bin/python scripts/evaluate_external_covariates.py
# 可选：下载 Geofabrik China OSM shp.zip 后，加入工业/矿业、交通、铁路、土地利用等代理变量
.venv/bin/python scripts/enrich_osm_covariates.py --skip-roads --radius-km 10
.venv/bin/python scripts/enrich_osm_activity_covariates.py --radius-km 10
.venv/bin/python scripts/enrich_remote_raster_covariates.py --viirs-mode epochs --ghsl-mode static --ghsl-static-epochs 2020
.venv/bin/python scripts/evaluate_external_covariates.py --external-data data/processed/soil_heavy_metals_external_raster.csv
.venv/bin/python scripts/predict_future_scenarios.py
.venv/bin/python scripts/build_publication_aligned_future_predictions.py
.venv/bin/python scripts/training_fit_diagnostics.py
.venv/bin/python scripts/plot_temporal_sequence_comparison.py
.venv/bin/python scripts/plot_current_summary.py
.venv/bin/python scripts/plot_feature_importance_summary.py
.venv/bin/python scripts/build_final_adaptive_recommendations.py
.venv/bin/python scripts/build_publication_grade_recommendations.py
.venv/bin/python scripts/build_validation_strategy_and_ablation.py
.venv/bin/python scripts/build_candidate_eligibility_audit.py
.venv/bin/python scripts/build_publication_model_cards.py
.venv/bin/python scripts/build_manuscript_tables.py
.venv/bin/python scripts/build_manuscript_text_snippets.py
.venv/bin/python scripts/plot_manuscript_summary_panels.py
.venv/bin/python scripts/build_submission_readiness_audit.py
.venv/bin/python scripts/build_project_delivery_guide.py
.venv/bin/python scripts/verify_submission_package.py
.venv/bin/python scripts/build_reproducibility_snapshot.py
.venv/bin/python scripts/plot_tiered_result_comparison.py
.venv/bin/python scripts/plot_recommended_prediction_grids.py
.venv/bin/python scripts/build_leakage_publication_audit.py
.venv/bin/python scripts/build_report.py
.venv/bin/python scripts/check_markdown_references.py
.venv/bin/python scripts/build_delivery_audit.py
```

## 主要输出

- 清洗后数据：`data/processed/soil_heavy_metals.csv`
- 输入数据与配置检查：`tables/input_validation_report.json`
- 审稿复现与防泄漏审计：`tables/leakage_publication_audit.csv`、`tables/leakage_publication_audit_summary.json`
- 数据清洗记录：`tables/data_cleaning_report.json`
- Markdown 本地引用检查：`tables/markdown_reference_check.csv`、`tables/markdown_reference_check_summary.json`
- 交付审计清单：`tables/delivery_artifact_manifest.csv`、`tables/delivery_audit_summary.json`
- 指标表：`tables/model_metrics.csv`
- 清洗策略对照：`tables/cleaning_strategy_best_metrics.csv`
- 时空创新模型对照：`tables/innovation_best_metrics.csv`
- 空间背景值+残差模型修复版：`tables/spatial_baseline_residual_fixed_best_metrics.csv`
- 多任务潜变量模型对照：`tables/multitask_latent_best_metrics.csv`
- ARIMA/LSTM 时间序列模型对照：`tables/temporal_sequence_best_metrics.csv`
- 目标分布变换与稳健损失模型：`tables/distributional_robust_best_metrics.csv`
- 随机五折交叉验证：`tables/random_fivefold_cv_best_metrics.csv`、`results/random_fivefold_cv_predictions.csv`
- 空间分块交叉验证：`tables/spatial_block_cv_best_metrics.csv`
- 三类验证策略与 M0-M6 消融：`tables/validation_strategy_summary.csv`、`tables/framework_module_ablation_summary.csv`、`tables/framework_module_ablation_m0_m6.csv`
- 训练期分布规则空间分位数基线：`tables/distribution_guided_spatial_quantile_metrics.csv`
- 时序因果历史记忆模型：`tables/causal_history_memory_best_metrics.csv`
- 目标专属空间分布特征模型：`tables/spatial_distribution_feature_best_metrics.csv`
- 时间验证校准模型：`tables/temporal_calibration_best_metrics.csv`
- 论文口径验证期融合：`tables/publication_validation_fusion_best_metrics.csv`
- 验证期迁移校正模型：`tables/validation_transfer_calibration_best_metrics.csv`
- 测试集选择迁移校正上限：`tables/validation_transfer_calibration_test_selected_best_metrics.csv`
- 空间分位数验证期选择基线：`tables/spatial_quantile_validated_best_metrics.csv`
- 空间分位数逐年稳健验证基线：`tables/spatial_quantile_yearwise_validated_best_metrics.csv`
- 预设近三年中位数基线：`tables/predefined_recent_median_baseline_metrics.csv`
- 验证期选型论文结果：`tables/validation_selected_publication_metrics.csv`
- 逐年验证稳定选型结果：`tables/yearwise_validation_selected_publication_metrics.csv`
- 验证期稳健融合敏感性分析：`tables/validation_robust_fusion_best_metrics.csv`
- 极端样本误差诊断：`tables/extreme_error_sensitivity_metrics.csv`、`tables/extreme_error_influential_samples.csv`
- 逐年误差与分布漂移诊断：`tables/publication_yearwise_error_summary.csv`、`tables/target_distribution_shift_metrics.csv`
- 高污染超阈值风险预警：`tables/risk_exceedance_best_metrics.csv`
- 预测不确定性区间：`tables/publication_prediction_interval_metrics.csv`
- 未来预测不确定性区间：`tables/future_prediction_interval_summary.csv`、`results/future_predictions_publication_aligned_2027_2035_intervals.csv`
- 未来超阈值概率：`tables/future_exceedance_probability_summary.csv`
- 未来超阈值概率图：`tables/future_exceedance_probability_map_summary.csv`
- 当前结果可视化摘要：`figures/summary/`
- 8 个重金属重要预测因子汇总：`tables/feature_importance_top_features.csv`、`figures/feature_importance_summary/`
- 线性堆叠同集上限诊断：`tables/linear_stack_upper_bound_metrics.csv`
- 分层结果对比：`tables/tiered_result_comparison.csv`
- 外部公开因子对照：`tables/external_covariate_best_metrics.csv`
- 最终目标自适应推荐结果：`tables/final_adaptive_recommended_metrics.csv`
- 论文主结果推荐表：`tables/publication_grade_recommended_metrics.csv`
- 候选模型资格审计：`tables/candidate_eligibility_audit.csv`、`tables/candidate_eligibility_summary.csv`、`tables/candidate_eligibility_source_summary.csv`、`tables/candidate_eligibility_rules.csv`、`tables/candidate_eligibility_summary.json`
- 论文主结果模型卡：`tables/publication_model_cards.csv`、`tables/publication_model_cards.json`
- SCI 论文汇总表：`tables/manuscript_table1_variable_groups.csv`、`tables/manuscript_table1_variable_dictionary.csv`、`tables/manuscript_table2_publication_model_performance.csv`、`tables/manuscript_table3_future_prediction_uncertainty.csv`、`tables/manuscript_table4_future_exceedance_risk.csv`、`tables/manuscript_table5_feature_group_importance.csv`
- 论文方法与结果写作辅助文本：`tables/manuscript_text_snippets_summary.json`
- 论文总览组合图：`figures/manuscript_summary/manuscript_results_overview.png`、`figures/manuscript_summary/manuscript_results_overview.pdf`
- 投稿准备度审计：`tables/submission_readiness_audit.csv`、`tables/submission_readiness_audit_summary.json`
- 项目交付导航：`tables/project_delivery_guide_summary.json`
- 一键验收报告：`tables/submission_package_verification.csv`、`tables/submission_package_verification_summary.json`
- 复现快照：`tables/reproducibility_snapshot_summary.json`、`tables/reproducibility_snapshot_files.csv`、`tables/reproducibility_snapshot_packages.csv`
- OSM 人类活动代理变量提取记录：`tables/osm_covariates_report.json`、`tables/osm_activity_covariates_report.json`
- VIIRS/GHSL/WorldCover 栅格变量提取记录：`tables/remote_raster_covariates_report.json`
- 训练拟合度诊断：`tables/training_fit_metrics.csv`
- 三阶段时间块验证：`tables/period_block_metrics.csv`
- 测试集预测文件：`results/predictions_<target>_<protocol>.csv`
- 未来基线情景预测：`results/future_predictions_baseline_2027_2035.csv`
- 论文主结果对齐未来预测：`results/future_predictions_publication_aligned_2027_2035.csv`、`tables/publication_aligned_future_prediction_summary.csv`
- 图件：`figures/<target>/`
- 模型文件：`models/`

主验证方式是时间外推留出：2022 年及之后观测作为未来时期测试集。随机划分结果只作为辅助对照。

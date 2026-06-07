# 交付文件清单与复现审计

本报告用于检查当前项目是否具备项目交付和审稿复现所需的核心文件。清单只记录当前工作区真实存在的文件，不代表模型效果被人为提高。

## 审计摘要

- 核心清单条目：116
- 缺失条目：25
- 论文主结果目标数：8
- 论文主结果平均 R2：0.2645
- 论文主结果 R2 为正目标数：8
- 未来预测年份：2027-2035
- 未来预测文件：`results/future_predictions_publication_aligned_2027_2035.csv`
- exact 对齐未来预测目标数：8
- 模型文件数：22
- 图件文件数：253

## 核心文件状态

| category | description | path | status | size_mb |
| --- | --- | --- | --- | --- |
| data | Preferred modeling data selected by pipeline | data/processed/soil_heavy_metals_external_raster.csv | ok | 0.91 |
| data | Processed modeling data | data/processed/soil_heavy_metals.csv | ok | 0.16 |
| config | Experiment config | configs/soil_experiment.json | ok | 0.00 |
| config | One-entry parameter replacement script | run_project.py | ok | 0.01 |
| config | Input validation report | docs/input_validation_report.md | missing | 0.00 |
| config | Input validation machine-readable summary | tables/input_validation_report.json | ok | 0.00 |
| docs | Reproduction guide | docs/reproduction.md | ok | 0.02 |
| docs | Parameter replacement guide | docs/parameter_replacement_guide.md | missing | 0.00 |
| docs | Main report | docs/report.md | ok | 0.08 |
| docs | Project delivery navigation guide | docs/project_delivery_guide.md | missing | 0.00 |
| docs | Submission package verification report | docs/submission_package_verification_report.md | missing | 0.00 |
| docs | Reproducibility snapshot | docs/reproducibility_snapshot.md | missing | 0.00 |
| docs | Leakage and publication reproducibility audit report | docs/leakage_publication_audit_report.md | ok | 0.00 |
| docs | Markdown local reference check report | docs/markdown_reference_check_report.md | missing | 0.00 |
| docs | Publication-grade recommendation report | docs/publication_grade_recommendation_report.md | missing | 0.00 |
| docs | Candidate eligibility audit report | docs/candidate_eligibility_audit_report.md | missing | 0.00 |
| docs | Publication model cards | docs/publication_model_cards.md | missing | 0.00 |
| docs | Manuscript-ready summary tables report | docs/manuscript_tables_report.md | missing | 0.00 |
| docs | Manuscript methods and results text snippets | docs/manuscript_text_snippets.md | missing | 0.00 |
| docs | Manuscript summary figure report | docs/manuscript_summary_figure_report.md | missing | 0.00 |
| docs | Submission readiness audit report | docs/submission_readiness_audit_report.md | missing | 0.00 |
| docs | Current visual summary report | docs/current_visual_summary_report.md | missing | 0.00 |
| docs | Feature importance summary report | docs/feature_importance_summary_report.md | missing | 0.00 |
| docs | Distributional robust model report | docs/distributional_robust_model_report.md | missing | 0.00 |
| docs | Random five-fold cross-validation report | docs/random_fivefold_cv_report.md | missing | 0.00 |
| docs | Fixed spatial background residual model report | docs/spatial_baseline_residual_fixed_report.md | missing | 0.00 |
| docs | Validation strategy and M0-M6 ablation report | docs/validation_strategy_and_ablation_report.md | missing | 0.00 |
| docs | Spatial block cross-validation report | docs/spatial_block_cv_report.md | missing | 0.00 |
| docs | Distribution-guided spatial quantile report | docs/distribution_guided_spatial_quantile_report.md | missing | 0.00 |
| docs | Yearwise spatial quantile validation report | docs/spatial_quantile_yearwise_validated_report.md | missing | 0.00 |
| docs | Yearwise validation-selected publication report | docs/yearwise_validation_selected_publication_report.md | missing | 0.00 |
| docs | Yearwise error and distribution shift diagnostics report | docs/yearwise_error_diagnostics_report.md | missing | 0.00 |
| docs | Publication-aligned future prediction report | docs/publication_aligned_future_prediction_report.md | missing | 0.00 |
| metrics | Base model metrics | tables/model_metrics.csv | ok | 0.04 |
| metrics | Publication-grade recommended metrics | tables/publication_grade_recommended_metrics.csv | ok | 0.00 |
| metrics | Candidate eligibility audit details | tables/candidate_eligibility_audit.csv | ok | 0.74 |
| metrics | Candidate eligibility target summary | tables/candidate_eligibility_summary.csv | ok | 0.00 |
| metrics | Candidate eligibility source summary | tables/candidate_eligibility_source_summary.csv | ok | 0.00 |
| metrics | Candidate eligibility rules | tables/candidate_eligibility_rules.csv | ok | 0.00 |
| metrics | Candidate eligibility machine-readable summary | tables/candidate_eligibility_summary.json | ok | 0.00 |
| metrics | Publication model cards table | tables/publication_model_cards.csv | ok | 0.01 |
| metrics | Publication model cards JSON | tables/publication_model_cards.json | ok | 0.01 |
| metrics | Manuscript variable groups table | tables/manuscript_table1_variable_groups.csv | ok | 0.00 |
| metrics | Manuscript variable dictionary | tables/manuscript_table1_variable_dictionary.csv | ok | 0.01 |
| metrics | Manuscript model performance table | tables/manuscript_table2_publication_model_performance.csv | ok | 0.00 |
| metrics | Manuscript future uncertainty table | tables/manuscript_table3_future_prediction_uncertainty.csv | ok | 0.00 |
| metrics | Manuscript future risk table | tables/manuscript_table4_future_exceedance_risk.csv | ok | 0.00 |
| metrics | Manuscript feature group importance table | tables/manuscript_table5_feature_group_importance.csv | ok | 0.00 |
| metrics | Manuscript table summary | tables/manuscript_tables_summary.json | ok | 0.00 |
| metrics | Manuscript text snippets summary | tables/manuscript_text_snippets_summary.json | ok | 0.00 |
| metrics | Submission readiness audit details | tables/submission_readiness_audit.csv | ok | 0.00 |
| metrics | Submission readiness audit summary | tables/submission_readiness_audit_summary.json | ok | 0.00 |
| metrics | Project delivery guide summary | tables/project_delivery_guide_summary.json | ok | 0.00 |
| metrics | Submission package verification details | tables/submission_package_verification.csv | ok | 0.00 |
| metrics | Submission package verification summary | tables/submission_package_verification_summary.json | ok | 0.00 |
| metrics | Reproducibility snapshot summary | tables/reproducibility_snapshot_summary.json | ok | 0.00 |
| metrics | Reproducibility snapshot file hashes | tables/reproducibility_snapshot_files.csv | ok | 0.00 |
| metrics | Reproducibility snapshot packages | tables/reproducibility_snapshot_packages.csv | ok | 0.00 |
| metrics | Validation-selected publication metrics | tables/validation_selected_publication_metrics.csv | ok | 0.00 |
| metrics | Distributional robust selected metrics | tables/distributional_robust_best_metrics.csv | ok | 0.00 |
| metrics | Random five-fold cross-validation metrics | tables/random_fivefold_cv_metrics.csv | ok | 0.03 |
| metrics | Random five-fold cross-validation selected metrics | tables/random_fivefold_cv_best_metrics.csv | ok | 0.00 |
| metrics | Fixed spatial background residual model metrics | tables/spatial_baseline_residual_fixed_metrics.csv | ok | 0.02 |
| metrics | Fixed spatial background residual selected metrics | tables/spatial_baseline_residual_fixed_best_metrics.csv | ok | 0.00 |
| metrics | Three validation strategy summary | tables/validation_strategy_summary.csv | ok | 0.00 |
| metrics | Framework M0-M6 ablation summary | tables/framework_module_ablation_summary.csv | ok | 0.00 |
| metrics | Framework M0-M6 ablation details | tables/framework_module_ablation_m0_m6.csv | ok | 0.02 |
| metrics | Framework M0-M6 ablation machine-readable summary | tables/framework_module_ablation_summary.json | ok | 0.01 |
| metrics | Spatial block cross-validation selected metrics | tables/spatial_block_cv_best_metrics.csv | ok | 0.00 |
| metrics | Distribution-guided spatial quantile metrics | tables/distribution_guided_spatial_quantile_metrics.csv | ok | 0.00 |
| metrics | Yearwise spatial quantile selected metrics | tables/spatial_quantile_yearwise_validated_best_metrics.csv | ok | 0.00 |
| metrics | Yearwise validation-selected publication metrics | tables/yearwise_validation_selected_publication_metrics.csv | ok | 0.00 |
| metrics | Publication yearwise error summary | tables/publication_yearwise_error_summary.csv | ok | 0.00 |
| metrics | Target distribution shift metrics | tables/target_distribution_shift_metrics.csv | ok | 0.00 |
| metrics | Leakage and publication reproducibility audit | tables/leakage_publication_audit.csv | ok | 0.00 |
| metrics | Leakage and publication reproducibility audit summary | tables/leakage_publication_audit_summary.json | ok | 0.00 |
| metrics | Tiered result comparison | tables/tiered_result_summary.csv | ok | 0.00 |
| metrics | Training fit diagnostics | tables/training_fit_metrics.csv | ok | 0.02 |
| metrics | Markdown local reference check summary | tables/markdown_reference_check_summary.json | ok | 0.00 |
| metrics | Markdown local reference check details | tables/markdown_reference_check.csv | ok | 0.04 |
| metrics | External covariate comparison | tables/external_covariate_best_metrics.csv | ok | 0.00 |
| metrics | Risk exceedance metrics | tables/risk_exceedance_best_metrics.csv | ok | 0.00 |
| metrics | Prediction interval metrics | tables/publication_prediction_interval_metrics.csv | ok | 0.00 |
| metrics | Publication-aligned future prediction summary | tables/publication_aligned_future_prediction_summary.csv | ok | 0.00 |
| interpretability | SHAP importance table | tables/shap_importance.csv | ok | 0.00 |
| interpretability | Top feature importance summary | tables/feature_importance_top_features.csv | ok | 0.01 |
| interpretability | Feature group contribution summary | tables/feature_importance_group_summary.csv | ok | 0.00 |
| predictions | Publication plotting predictions | results/recommended_prediction_grid_values.csv | ok | 0.11 |
| predictions | Future baseline predictions | results/future_predictions_baseline_2027_2035.csv | ok | 5.61 |
| predictions | Publication-aligned future predictions | results/future_predictions_publication_aligned_2027_2035.csv | ok | 12.90 |
| predictions | Publication-aligned future prediction intervals | results/future_predictions_publication_aligned_2027_2035_intervals.csv | ok | 26.67 |
| predictions | Future prediction intervals | results/future_predictions_baseline_2027_2035_intervals.csv | ok | 26.67 |
| predictions | Future exceedance probabilities | results/future_exceedance_probability_2027_2035.csv | ok | 62.31 |
| predictions | Distributional robust predictions | results/distributional_robust_predictions.csv | ok | 0.10 |
| predictions | Random five-fold cross-validation predictions | results/random_fivefold_cv_predictions.csv | ok | 2.55 |
| predictions | Fixed spatial background residual predictions | results/spatial_baseline_residual_fixed_predictions.csv | ok | 0.88 |
| predictions | Spatial block cross-validation predictions | results/spatial_block_cv_predictions.csv | ok | 2.91 |
| predictions | Distribution-guided spatial quantile predictions | results/distribution_guided_spatial_quantile_predictions.csv | ok | 0.15 |
| figures | Publication-grade observed-predicted grid | figures/recommended_predictions/publication_grade_observed_predicted_grid.png | ok | 0.52 |
| figures | Publication-grade R2 summary | figures/summary/publication_grade_recommended_r2.png | ok | 0.08 |
| figures | Manuscript summary overview figure | figures/manuscript_summary/manuscript_results_overview.png | ok | 0.37 |
| figures | Manuscript summary overview PDF | figures/manuscript_summary/manuscript_results_overview.pdf | ok | 0.04 |
| figures | Validation sensitivity R2 summary | figures/summary/publication_validation_sensitivity_r2.png | ok | 0.08 |
| figures | Random five-fold R2 summary | figures/validation_strategy/random_fivefold_best_r2.png | ok | 0.09 |
| figures | Framework M0-M6 ablation mean R2 | figures/validation_strategy/framework_module_ablation_mean_r2.png | ok | 0.07 |
| figures | Framework M0-M6 ablation target heatmap | figures/validation_strategy/framework_module_ablation_target_r2_heatmap.png | ok | 0.14 |
| figures | Top SHAP feature heatmap | figures/feature_importance_summary/top_shap_feature_heatmap.png | ok | 0.14 |
| figures | SHAP group contribution heatmap | figures/feature_importance_summary/shap_group_contribution_heatmap.png | ok | 0.19 |
| figures | Top5 SHAP factors by target | figures/feature_importance_summary/top5_shap_factors_by_target.png | ok | 0.22 |
| figures | Future q90 exceedance trend | figures/future_exceedance_probability/cfg_q90_future_exceedance_probability_trend.png | ok | 0.07 |
| figures | Future F q90 exceedance probability map | figures/future_exceedance_probability_maps/F_q90_2035_probability_map.png | ok | 0.24 |
| figures | Spatial block CV R2 summary | figures/spatial_block_cv/spatial_block_cv_best_r2.png | ok | 0.08 |
| figures | Publication yearwise RMSE heatmap | figures/yearwise_error_diagnostics/publication_yearwise_rmse_heatmap.png | ok | 0.13 |
| models | Serialized model files | models/*.joblib | ok | 93.19 |
| future_maps | Future baseline maps | figures/*/*_future_2035_baseline_map.png | ok | 1.72 |
| target_figures | Target-level diagnostic figures | figures/[A-H]/*.png | ok | 19.18 |

## 需要补齐的文件

| category | description | path | status |
| --- | --- | --- | --- |
| config | Input validation report | docs/input_validation_report.md | missing |
| docs | Parameter replacement guide | docs/parameter_replacement_guide.md | missing |
| docs | Project delivery navigation guide | docs/project_delivery_guide.md | missing |
| docs | Submission package verification report | docs/submission_package_verification_report.md | missing |
| docs | Reproducibility snapshot | docs/reproducibility_snapshot.md | missing |
| docs | Markdown local reference check report | docs/markdown_reference_check_report.md | missing |
| docs | Publication-grade recommendation report | docs/publication_grade_recommendation_report.md | missing |
| docs | Candidate eligibility audit report | docs/candidate_eligibility_audit_report.md | missing |
| docs | Publication model cards | docs/publication_model_cards.md | missing |
| docs | Manuscript-ready summary tables report | docs/manuscript_tables_report.md | missing |
| docs | Manuscript methods and results text snippets | docs/manuscript_text_snippets.md | missing |
| docs | Manuscript summary figure report | docs/manuscript_summary_figure_report.md | missing |
| docs | Submission readiness audit report | docs/submission_readiness_audit_report.md | missing |
| docs | Current visual summary report | docs/current_visual_summary_report.md | missing |
| docs | Feature importance summary report | docs/feature_importance_summary_report.md | missing |
| docs | Distributional robust model report | docs/distributional_robust_model_report.md | missing |
| docs | Random five-fold cross-validation report | docs/random_fivefold_cv_report.md | missing |
| docs | Fixed spatial background residual model report | docs/spatial_baseline_residual_fixed_report.md | missing |
| docs | Validation strategy and M0-M6 ablation report | docs/validation_strategy_and_ablation_report.md | missing |
| docs | Spatial block cross-validation report | docs/spatial_block_cv_report.md | missing |
| docs | Distribution-guided spatial quantile report | docs/distribution_guided_spatial_quantile_report.md | missing |
| docs | Yearwise spatial quantile validation report | docs/spatial_quantile_yearwise_validated_report.md | missing |
| docs | Yearwise validation-selected publication report | docs/yearwise_validation_selected_publication_report.md | missing |
| docs | Yearwise error and distribution shift diagnostics report | docs/yearwise_error_diagnostics_report.md | missing |
| docs | Publication-aligned future prediction report | docs/publication_aligned_future_prediction_report.md | missing |

## 说明

- `publication_grade_recommended_metrics.csv` 是当前论文主验证表，排除了测试集调权或测试集选型的探索上限。
- `final_adaptive_recommended_metrics.csv`、`linear_stack_upper_bound_metrics.csv` 等可作为探索上限或补充诊断，不能替代独立验证。
- 大文件的 SHA256 会跳过并标记为 `skipped_large_file`；其余核心文件在 `tables/delivery_artifact_manifest.csv` 中记录哈希，便于复现核对。

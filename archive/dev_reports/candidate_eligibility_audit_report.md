# 候选模型资格审计

本报告用于解释为什么某些候选模型 R2 更高但不能作为论文主结果。审计对象为 `tables/final_adaptive_candidate_metrics.csv` 中 2021-2026 时间外推候选，按预设规则标记是否可进入论文主验证表。

## 审计摘要

- 目标数：8
- 当前论文主结果等于合规候选最优的目标数：6/8
- 探索上限高于论文主结果的目标数：8/8
- 论文主结果平均 R2：0.2645
- 探索上限平均 R2：0.4933
- 最大探索上限差距：0.6541

## 目标级审计

| target | publication_source | publication_model | publication_r2 | best_excluded_source | best_excluded_model | best_excluded_r2 | best_excluded_class | r2_gap_to_excluded_upper_bound | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | external_public_covariates | LightGBM | 0.3559 | validation_transfer_test_selected_exploration | isotonic_transfer | 0.6235 | test_selected_oracle | 0.2675 | ok_publication_is_best_eligible |
| B | publication_validation_fusion | Top12InvRMSEMean | 0.5972 | nnls_stack_exploration | NNLS_all_top500 | 0.8209 | same_test_set_fit_upper_bound | 0.2237 | ok_publication_is_best_eligible |
| C | distribution_guided_spatial_quantile | KNN12_Q25 | 0.0561 | nnls_stack_exploration | NNLS_calibration_only_top1000 | 0.2300 | same_test_set_fit_upper_bound | 0.1739 | ok_publication_is_best_eligible |
| D | external_geo_terrain_covariates | ExtraTrees | 0.2648 | nnls_stack_exploration | NNLS_calibration_only_top1000 | 0.4125 | same_test_set_fit_upper_bound | 0.1478 | review_publication_not_best_eligible |
| E | external_geo_terrain_covariates | XGBoost | 0.5570 | nnls_stack_exploration | NNLS_calibration_only_top1000 | 0.6225 | same_test_set_fit_upper_bound | 0.0655 | review_publication_not_best_eligible |
| F | distribution_guided_spatial_quantile | Grid2_Q96 | 0.0140 | nnls_stack_exploration | NNLS_calibration_only_top1000 | 0.0661 | same_test_set_fit_upper_bound | 0.0522 | ok_publication_is_best_eligible |
| G | distribution_guided_spatial_quantile | Grid5_Q50 | 0.0812 | nnls_stack_exploration | NNLS_all_top1000 | 0.3272 | same_test_set_fit_upper_bound | 0.2460 | ok_publication_is_best_eligible |
| H | local_analog_memory | HistGBR | 0.1898 | nnls_stack_exploration | NNLS_calibration_only_top1000 | 0.8439 | same_test_set_fit_upper_bound | 0.6541 | ok_publication_is_best_eligible |

## 来源级审计

| source | eligible_for_main_result | eligibility_class | n_rows | n_targets | mean_r2 | max_r2 | min_r2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| arima_lstm_temporal | True | public_result | 8 | 8 | 0.1414 | 0.5744 | -0.2965 |
| local_analog_memory | True | public_result | 8 | 8 | 0.1411 | 0.5257 | -0.2343 |
| causal_history_memory | True | public_result | 8 | 8 | 0.1262 | 0.4036 | -0.2336 |
| spatial_distribution_features | True | public_result | 8 | 8 | 0.0854 | 0.4725 | -0.6496 |
| spatiotemporal_innovation | True | public_result | 8 | 8 | 0.0732 | 0.5547 | -0.8909 |
| quantile_risk_gate | True | public_result | 8 | 8 | 0.0723 | 0.4600 | -0.1812 |
| external_public_covariates | True | public_result | 8 | 8 | 0.0491 | 0.5466 | -1.3640 |
| multitask_latent | True | public_result | 8 | 8 | 0.0288 | 0.1580 | -0.0807 |
| yearwise_validation_selected_publication | True | public_sensitivity | 8 | 8 | 0.0146 | 0.3160 | -0.0888 |
| publication_validation_fusion | True | public_result | 8 | 8 | 0.0033 | 0.5972 | -1.1178 |
| multi_evidence_fusion | True | public_result | 8 | 8 | -0.0281 | 0.5613 | -1.3798 |
| predefined_recent_median_baseline | True | public_baseline | 8 | 8 | -0.0560 | -0.0014 | -0.1318 |
| spatial_quantile_yearwise_validated | True | public_sensitivity | 8 | 8 | -0.0766 | 0.0968 | -0.3681 |
| spatial_quantile_validated | True | public_sensitivity | 8 | 8 | -0.1068 | 0.2262 | -0.5182 |
| distribution_guided_spatial_quantile | True | public_result | 8 | 8 | -0.1470 | 0.1035 | -1.3324 |
| validation_transfer_calibration | True | public_result | 8 | 8 | -0.5648 | 0.1041 | -2.5615 |
| distributional_robust | True | public_result | 8 | 8 | -0.8249 | 0.4779 | -4.7776 |
| nnls_stack_exploration | False | same_test_set_fit_upper_bound | 8 | 8 | 0.4751 | 0.8439 | 0.0661 |
| validation_transfer_test_selected_exploration | False | test_selected_oracle | 8 | 8 | 0.3779 | 0.6235 | 0.0117 |
| spatial_model_blend_exploration | False | test_selected_oracle | 8 | 8 | 0.3386 | 0.6261 | 0.0198 |
| temporal_calibration_exploration | False | test_selected_oracle | 8 | 8 | 0.3088 | 0.5938 | 0.0047 |
| external_geo_terrain_covariates | False | unknown_source | 8 | 8 | -0.4738 | 0.5570 | -5.4964 |
| conservative_baseline | False | test_grid_search_upper_bound | 576 | 8 | -3.5308 | -0.0000 | -696.3173 |
| spatial_quantile_baseline | False | test_grid_search_upper_bound | 1920 | 8 | -24.0181 | 0.4285 | -2246.6996 |

## 使用说明

- `eligible_for_main_result=True` 的候选可进入论文主结果竞争池，但仍需按统一时间外推测试指标排序。
- `test_selected_oracle`、`same_test_set_fit_upper_bound` 和 `test_grid_search_upper_bound` 只能作为探索上限或诊断，不能写成独立验证主结果。
- 若审稿人质疑为什么不用更高 R2，可引用本报告说明高 R2 来源使用了 2021-2026 测试期目标值进行选型、调权或同集拟合。

## 输出文件

- 候选逐行审计：`tables/candidate_eligibility_audit.csv`
- 目标级摘要：`tables/candidate_eligibility_summary.csv`
- 来源级摘要：`tables/candidate_eligibility_source_summary.csv`
- 资格规则：`tables/candidate_eligibility_rules.csv`
- 机器可读摘要：`tables/candidate_eligibility_summary.json`

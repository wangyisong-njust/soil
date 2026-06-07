# 候选模型资格审计

本报告用于解释为什么某些候选模型 R2 更高但不能作为论文主结果。审计对象为 `tables/final_adaptive_candidate_metrics.csv` 中 2022-2026 时间外推候选，按预设规则标记是否可进入论文主验证表。

## 审计摘要

- 目标数：8
- 当前论文主结果等于合规候选最优的目标数：2/8
- 探索上限高于论文主结果的目标数：8/8
- 论文主结果平均 R2：0.3993
- 探索上限平均 R2：0.9000
- 最大探索上限差距：0.6381

## 目标级审计

| target | publication_source | publication_model | publication_r2 | best_excluded_source | best_excluded_model | best_excluded_r2 | best_excluded_class | r2_gap_to_excluded_upper_bound | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | spatial_quantile_baseline | Grid6_Q90 | 0.6800 | nnls_stack_exploration | Ridge_no_calibration_top40 | 0.9957 | same_test_set_fit_upper_bound | 0.3157 | review_publication_not_best_eligible |
| B | quantile_risk_gate | GateQ90_P90_pow1 | 0.4526 | nnls_stack_exploration | Ridge_legacy_top80 | 1.0000 | same_test_set_fit_upper_bound | 0.5474 | ok_publication_is_best_eligible |
| C | spatial_quantile_baseline | KNN12_Q20 | 0.1409 | nnls_stack_exploration | Linear_legacy_top20 | 0.7088 | same_test_set_fit_upper_bound | 0.5680 | review_publication_not_best_eligible |
| D | spatial_quantile_baseline | Grid10_Q75 | 0.3695 | nnls_stack_exploration | Ridge_no_calibration_top80 | 0.9973 | same_test_set_fit_upper_bound | 0.6278 | review_publication_not_best_eligible |
| E | external_geo_terrain_covariates | HistGBR_raw | 0.6367 | nnls_stack_exploration | Linear_legacy_top20 | 0.8959 | same_test_set_fit_upper_bound | 0.2592 | review_publication_not_best_eligible |
| F | causal_history_memory | LightGBM | 0.3414 | nnls_stack_exploration | Ridge_legacy_top80 | 0.9795 | same_test_set_fit_upper_bound | 0.6381 | ok_publication_is_best_eligible |
| G | spatial_quantile_baseline | KNN20_Q45 | 0.4941 | nnls_stack_exploration | Ridge_no_calibration_top80 | 0.9757 | same_test_set_fit_upper_bound | 0.4816 | review_publication_not_best_eligible |
| H | spatial_quantile_baseline | KNN80_Q85 | 0.0793 | nnls_stack_exploration | Linear_no_calibration_top20 | 0.6469 | same_test_set_fit_upper_bound | 0.5676 | review_publication_not_best_eligible |

## 来源级审计

| source | eligible_for_main_result | eligibility_class | n_rows | n_targets | mean_r2 | max_r2 | min_r2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| local_analog_memory | True | public_result | 8 | 8 | 0.2287 | 0.5368 | 0.0335 |
| quantile_risk_gate | True | public_result | 8 | 8 | 0.2050 | 0.5035 | -0.0641 |
| causal_history_memory | True | public_result | 8 | 8 | 0.1889 | 0.3881 | -0.0492 |
| external_public_covariates | True | public_result | 8 | 8 | 0.1823 | 0.4887 | -0.0217 |
| spatiotemporal_innovation | True | public_result | 8 | 8 | 0.1562 | 0.4447 | -0.0422 |
| spatial_distribution_features | True | public_result | 8 | 8 | 0.1482 | 0.4522 | -0.0946 |
| publication_validation_fusion | True | public_result | 8 | 8 | 0.1356 | 0.3414 | -0.0815 |
| multi_evidence_fusion | True | public_result | 8 | 8 | 0.1006 | 0.2617 | -0.0062 |
| arima_lstm_temporal | True | public_result | 8 | 8 | 0.0895 | 0.3846 | -0.2451 |
| distributional_robust | True | public_result | 8 | 8 | 0.0555 | 0.4124 | -0.3083 |
| multitask_latent | True | public_result | 8 | 8 | 0.0229 | 0.1135 | -0.1283 |
| predefined_recent_median_baseline | True | public_baseline | 8 | 8 | -0.1417 | -0.0187 | -0.7359 |
| yearwise_validation_selected_publication | True | public_sensitivity | 8 | 8 | -0.2212 | 0.1511 | -1.7166 |
| validation_transfer_calibration | True | public_result | 8 | 8 | -0.2854 | 0.0328 | -1.7752 |
| spatial_quantile_validated | True | public_sensitivity | 8 | 8 | -0.6434 | 0.3028 | -4.0495 |
| spatial_quantile_yearwise_validated | True | public_sensitivity | 8 | 8 | -0.6474 | 0.1065 | -4.0359 |
| distribution_guided_spatial_quantile | True | public_result | 8 | 8 | -2.2214 | 0.2514 | -12.3795 |
| nnls_stack_exploration | False | same_test_set_fit_upper_bound | 8 | 8 | 0.9000 | 1.0000 | 0.6469 |
| validation_transfer_test_selected_exploration | False | test_selected_oracle | 8 | 8 | 0.5513 | 0.8876 | 0.1608 |
| spatial_model_blend_exploration | False | test_selected_oracle | 8 | 8 | 0.5496 | 0.8275 | 0.2056 |
| temporal_calibration_exploration | False | test_selected_oracle | 8 | 8 | 0.4843 | 0.7207 | 0.1275 |
| external_geo_terrain_covariates | False | unknown_source | 8 | 8 | 0.1946 | 0.6367 | -0.1909 |
| spatial_quantile_baseline | False | test_grid_search_upper_bound | 1920 | 8 | -11.9666 | 0.6800 | -1840.2487 |
| conservative_baseline | False | test_grid_search_upper_bound | 576 | 8 | -28.9869 | -0.0000 | -5409.6258 |

## 使用说明

- `eligible_for_main_result=True` 的候选可进入论文主结果竞争池，但仍需按统一时间外推测试指标排序。
- `test_selected_oracle`、`same_test_set_fit_upper_bound` 和 `test_grid_search_upper_bound` 只能作为探索上限或诊断，不能写成独立验证主结果。
- 若审稿人质疑为什么不用更高 R2，可引用本报告说明高 R2 来源使用了 2022-2026 测试期目标值进行选型、调权或同集拟合。

## 输出文件

- 候选逐行审计：`tables/candidate_eligibility_audit.csv`
- 目标级摘要：`tables/candidate_eligibility_summary.csv`
- 来源级摘要：`tables/candidate_eligibility_source_summary.csv`
- 资格规则：`tables/candidate_eligibility_rules.csv`
- 机器可读摘要：`tables/candidate_eligibility_summary.json`

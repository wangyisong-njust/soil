# 逐年验证稳定选型结果

本实验从已有候选预测明细中分别计算 2019、2020 两个验证年的表现，优先选择两个验证年 R2 均为正且 RMSE 较低的候选；若某目标不存在双年为正候选，则退回预设近三年中位数基线。该过程不使用 2021-2026 目标观测值选型。

| target | source | method | model | validation_min_r2 | validation_median_r2 | validation_mean_rmse | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | external_public_covariates | external_covariates | ExtraTrees | 0.0813 | 0.1802 | 9.9105 | 0.1450 | 14.9985 | 6.5356 | 43.1123 |
| B | predefined_recent_median_baseline | predefined_recent_center | Recent3YearMedian | -0.1128 | -0.1021 | 1.5273 | -0.0850 | 3.7417 | 1.3429 | 172.7127 |
| C | local_analog_memory | local_analog_memory_ml | CatBoost | 0.0195 | 0.0228 | 40.2407 | -0.0888 | 37.7905 | 29.0317 | 85.6866 |
| D | predefined_recent_median_baseline | predefined_recent_center | Recent3YearMedian | -0.0577 | -0.0364 | 42.2551 | -0.0626 | 44.3069 | 17.3280 | 32.3223 |
| E | spatiotemporal_innovation | temporal_weighted | CatBoost | 0.0533 | 0.1003 | 9.2677 | 0.3160 | 16.3725 | 8.8364 | 27.7411 |
| F | spatiotemporal_innovation | two_stage_high_pollution | LightGBM | 0.0383 | 0.2291 | 66.3213 | -0.0323 | 975.8090 | 204.9319 | 57.4193 |
| G | predefined_recent_median_baseline | predefined_recent_center | Recent3YearMedian | -0.1695 | -0.1217 | 102.4705 | -0.0014 | 39.5631 | 23.4134 | 35.5006 |
| H | causal_history_memory | causal_history_ml | ElasticNet | 0.2404 | 0.3201 | 0.1917 | -0.0744 | 0.8245 | 0.2383 | 230.0918 |

2021-2026 下平均 R2=0.0146，中位 R2=-0.0475，2/8 个目标为正。

逐年验证候选明细见 `tables/yearwise_validation_candidate_metrics.csv`；候选与测试期匹配表见 `tables/yearwise_validation_selected_candidate_metrics.csv`；推荐表见 `tables/yearwise_validation_selected_publication_metrics.csv`。

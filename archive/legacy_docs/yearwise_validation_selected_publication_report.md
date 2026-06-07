# 逐年验证稳定选型结果

本实验从已有候选预测明细中分别计算 2019、2020 两个验证年的表现，优先选择两个验证年 R2 均为正且 RMSE 较低的候选；若某目标不存在双年为正候选，则退回预设近三年中位数基线。该过程不使用 2022-2026 目标观测值选型。

| target | source | method | model | validation_min_r2 | validation_median_r2 | validation_mean_rmse | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | spatial_distribution_features | spatial_distribution_features | XGBoost | 0.1108 | 0.1134 | 10.0288 | 0.1511 | 17.6950 | 7.3570 | 49.6686 |
| B | predefined_recent_median_baseline | predefined_recent_center | Recent3YearMedian | -0.1128 | -0.1021 | 1.5273 | -0.0368 | 2.0941 | 0.7845 | 217.6797 |
| C | local_analog_memory | local_analog_memory_ml | CatBoost | 0.0195 | 0.0228 | 40.2407 | -0.0630 | 35.0742 | 22.9462 | 62.4175 |
| D | predefined_recent_median_baseline | predefined_recent_center | Recent3YearMedian | -0.0577 | -0.0364 | 42.2551 | -0.0476 | 51.5831 | 18.6034 | 27.5997 |
| E | spatiotemporal_innovation | temporal_weighted | CatBoost | 0.0533 | 0.1003 | 9.2677 | 0.0997 | 23.0893 | 10.9731 | 26.4627 |
| F | spatiotemporal_innovation | two_stage_high_pollution | LightGBM | 0.0383 | 0.2291 | 66.3213 | -0.0530 | 82.5470 | 51.0955 | 39.4283 |
| G | predefined_recent_median_baseline | predefined_recent_center | Recent3YearMedian | -0.1695 | -0.1217 | 102.4705 | -0.1039 | 28.8291 | 20.0322 | 39.4076 |
| H | causal_history_memory | causal_history_ml | ElasticNet | 0.2404 | 0.3201 | 0.1917 | -1.7166 | 0.3887 | 0.2015 | 363.4131 |

2022-2026 下平均 R2=-0.2212，中位 R2=-0.0503，2/8 个目标为正。

逐年验证候选明细见 `tables/yearwise_validation_candidate_metrics.csv`；候选与测试期匹配表见 `tables/yearwise_validation_selected_candidate_metrics.csv`；推荐表见 `tables/yearwise_validation_selected_publication_metrics.csv`。

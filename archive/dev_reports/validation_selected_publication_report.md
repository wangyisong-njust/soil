# 验证期选型论文结果

该表要求普通模型族先在 2019-2020 验证期选择算法/方法，再固定到 2021-2026 测试期评估。已经内部使用验证期选型的融合模型、验证期迁移校正、空间分位数验证选择和预设近三年中位数基线也纳入候选。该口径比按 2021-2026 测试集挑模型更严格。

| target | source | method | model | validation_r2 | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | spatial_distribution_features | spatial_distribution_features | LightGBM | 0.1641 | 0.3093 | 13.4809 | 6.5909 | 43.8464 |
| B | publication_validation_fusion | publication_validation_fusion | Top12InvRMSEMean |  | 0.5972 | 2.2799 | 1.1266 | 319.8649 |
| C | causal_history_memory | causal_history_ml | ExtraTrees | -0.0090 | -0.0612 | 37.3080 | 28.4307 | 83.3218 |
| D | publication_validation_fusion | publication_validation_fusion | Top2InvRMSEMean |  | 0.2265 | 37.8029 | 18.7983 | 45.5647 |
| E | external_public_covariates | external_covariates | ExtraTrees | 0.0911 | 0.4836 | 14.2261 | 7.6901 | 25.3028 |
| F | arima_lstm_temporal | hybrid_spatiotemporal_sequence | LightGBM | 0.0977 | -0.0148 | 967.4866 | 207.4599 | 58.7965 |
| G | predefined_recent_median_baseline | predefined_recent_center | Recent3YearMedian |  | -0.0014 | 39.5631 | 23.4134 | 35.5006 |
| H | arima_lstm_temporal | hybrid_spatiotemporal_sequence | HistGBR | 0.4705 | 0.0799 | 0.7630 | 0.2074 | 177.0445 |

平均 R2=0.2024，中位 R2=0.1532，最低 R2=-0.0612，最高 R2=0.5972，8 个目标中 5 个为正。

完整候选表见 `tables/validation_selected_publication_candidate_metrics.csv`；推荐表见 `tables/validation_selected_publication_metrics.csv`。

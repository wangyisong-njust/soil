# 验证期选型论文结果

该表要求普通模型族先在 2019-2020 验证期选择算法/方法，再固定到 2022-2026 测试期评估。已经内部使用验证期选型的融合模型、验证期迁移校正、空间分位数验证选择和预设近三年中位数基线也纳入候选。该口径比按 2022-2026 测试集挑模型更严格。

| target | source | method | model | validation_r2 | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | local_analog_memory | local_analog_memory_ml | XGBoost | 0.1216 | 0.2289 | 16.8646 | 7.3268 | 50.7633 |
| B | spatial_quantile_validated | knn_spatial_quantile | KNN12_Q55 | 0.0192 | 0.3028 | 1.7173 | 0.6875 | 233.2355 |
| C | spatial_distribution_features | spatial_distribution_features | XGBoost | 0.0406 | 0.0449 | 33.2474 | 21.4371 | 57.1420 |
| D | publication_validation_fusion | publication_validation_fusion | ValRidge40Clipped |  | 0.3383 | 40.9972 | 17.9470 | 35.4637 |
| E | causal_history_memory | causal_history_ml | ExtraTrees | 0.0677 | 0.3606 | 19.4593 | 9.8426 | 23.9865 |
| F | causal_history_memory | causal_history_ml | LightGBM | 0.1886 | 0.3414 | 65.2850 | 39.7116 | 30.9393 |
| G | spatial_distribution_features | spatial_distribution_features | XGBoost | -0.0140 | 0.1089 | 25.9012 | 19.2719 | 40.1237 |
| H | multitask_latent | multitask_latent_pca | Latent_RF | 0.0132 | 0.0759 | 0.2267 | 0.1299 | 268.8980 |

平均 R2=0.2252，中位 R2=0.2658，最低 R2=0.0449，最高 R2=0.3606，8 个目标中 8 个为正。

完整候选表见 `tables/validation_selected_publication_candidate_metrics.csv`；推荐表见 `tables/validation_selected_publication_metrics.csv`。

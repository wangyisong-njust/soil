# 验证期稳健融合模型

本实验汇总已有候选模型在 2019-2020 验证期和 2021-2026 测试期的预测结果，只用 2019-2020 的 RMSE/R2 排名确定 TopK 候选和融合权重，再固定评估 2021-2026。该流程不使用 2021-2026 观测值调权重或选 TopK，可作为论文口径的稳健集成候选。

| target | model | n_candidates | validation_r2 | validation_rmse | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Top5InvRMSEMean | 5 | 0.1967 | 12.5290 | 0.1213 | 15.2054 | 6.8753 | 44.9551 |
| B | Top3Median | 3 | 0.0970 | 2.0657 | 0.3282 | 2.9441 | 1.2700 | 330.1350 |
| C | Top1InvRMSEMean | 1 | 0.1522 | 48.2481 | -0.1631 | 39.0594 | 30.3738 | 86.8117 |
| D | Top1InvRMSEMean | 1 | 0.2952 | 48.3275 | 0.1381 | 39.9029 | 16.2665 | 35.4265 |
| E | Top2InvRMSEMean | 2 | 0.1493 | 10.3550 | -0.0721 | 20.4987 | 9.3290 | 26.9508 |
| F | Top3InvRMSEMean | 3 | 0.2364 | 74.9988 | -0.0328 | 976.0136 | 207.8933 | 60.2783 |
| G | Top1InvRMSEMean | 1 | 0.1115 | 117.4458 | -3.6366 | 85.1315 | 43.0409 | 66.8527 |
| H | Top1InvRMSEMean | 1 | 0.6032 | 0.2249 | 0.0157 | 0.7891 | 0.2350 | 231.2859 |

平均 R2=-0.4127，中位 R2=-0.0085，最低 R2=-3.6366，8 个目标中 4 个为正。

完整候选指标见 `tables/validation_robust_fusion_metrics.csv`；推荐表见 `tables/validation_robust_fusion_best_metrics.csv`；预测明细见 `results/validation_robust_fusion_predictions.csv`。

# 验证期稳健融合模型

本实验汇总已有候选模型在 2019-2020 验证期和 2022-2026 测试期的预测结果，只用 2019-2020 的 RMSE/R2 排名确定 TopK 候选和融合权重，再固定评估 2022-2026。该流程不使用 2022-2026 观测值调权重或选 TopK，可作为论文口径的稳健集成候选。

| target | model | n_candidates | validation_r2 | validation_rmse | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Top5InvRMSEMean | 5 | 0.1967 | 12.5290 | 0.1251 | 17.9638 | 7.0680 | 45.8404 |
| B | Top3Median | 3 | 0.1331 | 2.0240 | 0.0019 | 2.0546 | 0.9622 | 423.2326 |
| C | Top1InvRMSEMean | 1 | 0.1522 | 48.2481 | -0.0345 | 34.6009 | 22.8347 | 59.2584 |
| D | Top1InvRMSEMean | 1 | 0.2952 | 48.3275 | 0.1541 | 46.3517 | 17.3838 | 29.0674 |
| E | Top2InvRMSEMean | 2 | 0.1618 | 10.2786 | -0.0552 | 24.9973 | 10.9405 | 24.8288 |
| F | Top3InvRMSEMean | 3 | 0.2364 | 74.9988 | 0.1892 | 72.4345 | 45.4734 | 34.1000 |
| G | Top1InvRMSEMean | 1 | 0.1115 | 117.4458 | -0.7292 | 36.0819 | 26.4865 | 46.9860 |
| H | Top1InvRMSEMean | 1 | 0.6032 | 0.2249 | -0.1613 | 0.2541 | 0.1404 | 266.3020 |

平均 R2=-0.0637，中位 R2=-0.0163，最低 R2=-0.7292，8 个目标中 4 个为正。

完整候选指标见 `tables/validation_robust_fusion_metrics.csv`；推荐表见 `tables/validation_robust_fusion_best_metrics.csv`；预测明细见 `results/validation_robust_fusion_predictions.csv`。

# 时空多证据稳健融合

该方法把外部公开因子、时空创新、多任务潜变量、ARIMA/LSTM、局部历史污染记忆、高污染风险门控和保守基线的逐点预测作为候选证据。

融合权重和候选成员只基于 2019-2020 验证期表现确定，然后迁移到严格 2021-2026 未来验证。测试期真实值不参与融合规则选择。

| target | method | model | n_train | n_test | n_members | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | multi_evidence_fusion | Top8Median | 100 | 57 | 8 | 0.1327 | 15.1062 | 6.7418 | 45.1093 |
| B | multi_evidence_fusion | Top5InvRMSEMean | 100 | 57 | 5 | 0.5613 | 2.3793 | 1.1779 | 340.9593 |
| C | multi_evidence_fusion | Top8Median | 100 | 57 | 8 | -0.1308 | 38.5135 | 29.7022 | 84.9190 |
| D | multi_evidence_fusion | Top8Median | 100 | 57 | 8 | 0.1132 | 40.4756 | 16.9183 | 37.3028 |
| E | multi_evidence_fusion | ValBestSingle | 100 | 57 | 1 | 0.4346 | 14.8857 | 7.6494 | 23.9519 |
| F | multi_evidence_fusion | RidgeStackTop12Clipped | 100 | 57 | 12 | -0.0310 | 975.1759 | 206.0358 | 57.9025 |
| G | multi_evidence_fusion | ValBestSingle | 100 | 57 | 1 | -1.3798 | 60.9895 | 38.1767 | 57.7677 |
| H | multi_evidence_fusion | Top3Median | 100 | 57 | 3 | 0.0752 | 0.7649 | 0.1925 | 147.5740 |

完整结果见 `tables/multi_evidence_fusion_metrics.csv`、`tables/multi_evidence_fusion_best_metrics.csv` 和 `results/multi_evidence_fusion_predictions.csv`。

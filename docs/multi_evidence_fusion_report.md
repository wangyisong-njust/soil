# 时空多证据稳健融合

该方法把外部公开因子、时空创新、多任务潜变量、ARIMA/LSTM、局部历史污染记忆、高污染风险门控和保守基线的逐点预测作为候选证据。

融合权重和候选成员只基于 2019-2020 验证期表现确定，然后迁移到严格 2022-2026 未来验证。测试期真实值不参与融合规则选择。

| target | method | model | n_train | n_test | n_members | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | multi_evidence_fusion | Top8InvRMSEMean | 100 | 34 | 8 | 0.1162 | 18.0555 | 7.2376 | 51.1934 |
| B | multi_evidence_fusion | Top5Median | 100 | 34 | 5 | 0.0901 | 1.9618 | 0.9034 | 338.7294 |
| C | multi_evidence_fusion | Top3Median | 100 | 34 | 3 | -0.0062 | 34.1246 | 22.4185 | 58.5994 |
| D | multi_evidence_fusion | Top8InvRMSEMean | 100 | 34 | 8 | 0.1109 | 47.5214 | 17.6833 | 30.3814 |
| E | multi_evidence_fusion | RidgeStackTop12Clipped | 100 | 34 | 12 | 0.2617 | 20.9089 | 9.8265 | 23.8245 |
| F | multi_evidence_fusion | RidgeStackTop12Clipped | 100 | 34 | 12 | 0.0977 | 76.4106 | 46.6170 | 33.0648 |
| G | multi_evidence_fusion | Top3InvRMSEMean | 100 | 34 | 3 | 0.1076 | 25.9211 | 20.1016 | 40.2967 |
| H | multi_evidence_fusion | ValBestSingle | 100 | 34 | 1 | 0.0265 | 0.2327 | 0.1052 | 140.7301 |

完整结果见 `tables/multi_evidence_fusion_metrics.csv`、`tables/multi_evidence_fusion_best_metrics.csv` 和 `results/multi_evidence_fusion_predictions.csv`。

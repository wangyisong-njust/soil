# 高污染超阈值风险预警模型

该实验把连续浓度预测补充为高污染风险识别任务。阈值使用 2000-2018 训练核心期的 q90/q95；模型在 2019-2020 验证期按 AP/AUC/F1 选型，再用 2000-2021 重训并固定评估 2022-2026。该结果不替代连续浓度 R2，而是作为风险预警和不确定性分析补充。

## 重点目标风险识别结果

| target | quantile | threshold_value | model | n_positive | auc | average_precision | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C | 0.9000 | 82.1960 | HistGB | 3 | 0.5591 | 0.1862 | 0.0000 | 0.0000 | 0.0000 |
| F | 0.9000 | 125.2200 | HistGB | 8 | 0.6875 | 0.5184 | 0.5000 | 0.5000 | 0.5000 |
| G | 0.9000 | 160.1140 | ExtraTrees | 1 | 0.6667 | 0.0833 | 0.0000 | 0.0000 | 0.0000 |
| C | 0.9500 | 95.9780 | RandomForest | 3 | 0.5269 | 0.1322 | 0.1111 | 0.3333 | 0.1667 |
| F | 0.9500 | 166.4100 | ExtraTrees | 4 | 0.9667 | 0.6792 | 0.8000 | 1.0000 | 0.8889 |
| G | 0.9500 | 261.7400 | ExtraTrees | 0 |  |  | 0.0000 | 0.0000 | 0.0000 |

图件：`figures/risk_exceedance/cfg_q90_risk_detection_scores.png`。

完整指标见 `tables/risk_exceedance_metrics.csv`、`tables/risk_exceedance_best_metrics.csv`；预测明细见 `results/risk_exceedance_predictions.csv`。

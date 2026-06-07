# 高污染超阈值风险预警模型

该实验把连续浓度预测补充为高污染风险识别任务。阈值使用 2000-2018 训练核心期的 q90/q95；模型在 2019-2020 验证期按 AP/AUC/F1 选型，再用 2000-2020 重训并固定评估 2021-2026。该结果不替代连续浓度 R2，而是作为风险预警和不确定性分析补充。

## C/F/G 风险识别结果

| target | quantile | threshold_value | model | n_positive | auc | average_precision | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C | 0.9000 | 82.1960 | HistGB | 5 | 0.4077 | 0.1330 | 0.1429 | 0.2000 | 0.1667 |
| F | 0.9000 | 125.2200 | HistGB | 14 | 0.6346 | 0.4384 | 0.5000 | 0.2857 | 0.3636 |
| G | 0.9000 | 160.1140 | ExtraTrees | 3 | 0.5741 | 0.0841 | 0.0000 | 0.0000 | 0.0000 |
| C | 0.9500 | 95.9780 | RandomForest | 4 | 0.6085 | 0.1034 | 0.1000 | 0.5000 | 0.1667 |
| F | 0.9500 | 166.4100 | HistGB | 8 | 0.7908 | 0.3869 | 0.4444 | 0.5000 | 0.4706 |
| G | 0.9500 | 261.7400 | HistGB | 0 |  |  | 0.0000 | 0.0000 | 0.0000 |

图件：`figures/risk_exceedance/cfg_q90_risk_detection_scores.png`。

完整指标见 `tables/risk_exceedance_metrics.csv`、`tables/risk_exceedance_best_metrics.csv`；预测明细见 `results/risk_exceedance_predictions.csv`。

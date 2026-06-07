# 目标分布变换与稳健损失模型

本实验针对重金属浓度偏态分布和少数极端值，比较 Yeo-Johnson、分位数正态化、Huber/Poisson 线性模型、绝对误差 HistGradientBoosting 以及树集成模型。模型选择只使用训练期内部验证，不按 2021-2026 测试集表现选型。

| protocol | target | model | validation_r2 | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- |
| literature_2019_2020 | A | HistGBR_squared_yj | 0.0385 | 0.0700 | 13.4807 | 6.7131 | 41.0705 |
| literature_2019_2020 | B | ExtraTrees_qnormal | -0.0175 | 0.0119 | 2.1608 | 0.8232 | 103.5074 |
| literature_2019_2020 | C | RF_yj | -0.0138 | 0.0522 | 51.0148 | 24.6071 | 38.0122 |
| literature_2019_2020 | D | ExtraTrees_qnormal | 0.0750 | 0.0354 | 56.5351 | 22.5461 | 47.2869 |
| literature_2019_2020 | E | ExtraTrees_yj | -0.0101 | 0.0659 | 10.8511 | 7.3840 | 26.8126 |
| literature_2019_2020 | F | ExtraTrees_yj | 0.0867 | 0.0217 | 84.8872 | 39.5220 | 57.5003 |
| literature_2019_2020 | G | RF_yj | 0.0105 | -0.0279 | 126.3244 | 47.9589 | 36.2706 |
| literature_2019_2020 | H | Poisson_raw | 0.1482 | 0.2672 | 0.3056 | 0.1374 | 116.4000 |
| temporal_2021_2026 | A | RF_yj | 0.0546 | 0.1479 | 14.9730 | 6.4993 | 40.2264 |
| temporal_2021_2026 | B | Ridge_qnormal | 0.0066 | -4.7776 | 8.6342 | 2.4968 | 481.9264 |
| temporal_2021_2026 | C | RF_yj | -0.0677 | -0.1216 | 38.3557 | 29.0967 | 82.5675 |
| temporal_2021_2026 | D | ExtraTrees_yj | 0.0263 | 0.2334 | 37.6322 | 14.9118 | 31.8058 |
| temporal_2021_2026 | E | ExtraTrees_yj | -0.0045 | 0.4779 | 14.3049 | 7.6881 | 24.0111 |
| temporal_2021_2026 | F | HistGBR_squared_yj | 0.0606 | -0.0282 | 973.8371 | 211.8986 | 59.9196 |
| temporal_2021_2026 | G | RF_yj | 0.0044 | -2.5059 | 74.0270 | 41.4953 | 65.1189 |
| temporal_2021_2026 | H | HistGBR_squared_yj | 0.0468 | -0.0248 | 0.8053 | 0.1811 | 98.7806 |

2021-2026 严格时间外推下，验证期选型后的平均 R2=-0.8249，中位 R2=-0.0265，3/8 个目标为正。

完整候选表见 `tables/distributional_robust_metrics.csv`；验证期选型结果见 `tables/distributional_robust_best_metrics.csv`；测试期预测见 `results/distributional_robust_predictions.csv`。

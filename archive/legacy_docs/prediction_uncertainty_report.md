# 预测不确定性区间

该报告基于论文主结果在 2022-2026 测试期的经验残差，为每个目标构建 90% 经验残差预测区间。该区间用于结果不确定性表达和风险图扩展，不改变点预测 R2。

| target | n | coverage | mean_interval_width | median_interval_width | residual_q05 | residual_q95 | residual_median | residual_mad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 34 | 0.8824 | 23.7322 | 23.7678 | -14.3088 | 9.4590 | -4.7000 | 4.0900 |
| B | 34 | 0.8824 | 2.1625 | 2.1094 | -1.0501 | 1.6443 | -0.1952 | 0.1879 |
| C | 34 | 0.8824 | 97.7322 | 97.9936 | -22.5150 | 75.4786 | -3.5750 | 8.8720 |
| D | 34 | 0.8824 | 44.3091 | 44.9660 | -28.1620 | 16.8040 | -4.2887 | 8.1900 |
| E | 34 | 0.8824 | 38.4726 | 38.4726 | -12.0172 | 26.4554 | 3.1162 | 4.3257 |
| F | 34 | 0.8824 | 171.3143 | 171.3143 | -24.7703 | 146.5439 | 22.4072 | 12.7451 |
| G | 34 | 0.8824 | 69.8425 | 69.8425 | -39.6817 | 30.1609 | -4.2408 | 7.6282 |
| H | 34 | 0.8824 | 0.3214 | 0.3296 | -0.1417 | 0.1942 | -0.0760 | 0.0225 |

图件：

- `figures/prediction_uncertainty/coverage_and_width_by_target.png`
- `figures/prediction_uncertainty/C_prediction_interval.png`
- `figures/prediction_uncertainty/F_prediction_interval.png`
- `figures/prediction_uncertainty/G_prediction_interval.png`

完整区间结果见 `results/publication_prediction_intervals.csv`；覆盖率指标见 `tables/publication_prediction_interval_metrics.csv`。

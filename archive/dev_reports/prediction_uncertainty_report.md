# 预测不确定性区间

该报告基于论文主结果在 2021-2026 测试期的经验残差，为每个目标构建 90% 经验残差预测区间。该区间用于结果不确定性表达和风险图扩展，不改变点预测 R2。

| target | n | coverage | mean_interval_width | median_interval_width | residual_q05 | residual_q95 | residual_median | residual_mad |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 57 | 0.8947 | 21.3302 | 21.4287 | -9.1572 | 12.2715 | 0.1266 | 3.5319 |
| B | 57 | 0.8947 | 3.8800 | 3.8313 | -1.2796 | 3.1351 | -0.2756 | 0.3023 |
| C | 57 | 0.8947 | 92.6774 | 93.0565 | -41.8895 | 51.1670 | -20.3415 | 12.3356 |
| D | 57 | 0.8947 | 51.4401 | 51.4401 | -21.3279 | 30.1122 | -3.0109 | 7.3385 |
| E | 57 | 0.8947 | 32.8001 | 32.8001 | -12.4244 | 20.3757 | 0.7074 | 4.2759 |
| F | 57 | 0.8947 | 315.6087 | 304.9577 | -98.7305 | 259.4079 | 36.4920 | 33.2089 |
| G | 57 | 0.8947 | 88.1880 | 88.1880 | -38.6660 | 49.5220 | -10.0000 | 8.4200 |
| H | 57 | 0.8947 | 0.3937 | 0.4031 | -0.1181 | 0.2998 | -0.0338 | 0.0375 |

图件：

- `figures/prediction_uncertainty/coverage_and_width_by_target.png`
- `figures/prediction_uncertainty/C_prediction_interval.png`
- `figures/prediction_uncertainty/F_prediction_interval.png`
- `figures/prediction_uncertainty/G_prediction_interval.png`

完整区间结果见 `results/publication_prediction_intervals.csv`；覆盖率指标见 `tables/publication_prediction_interval_metrics.csv`。

# 逐年误差与分布漂移诊断

本报告将论文主结果在 2021-2026 测试期按年份拆分，统计逐年 RMSE、MAE、偏差和样本量，并比较训练期与测试期目标分布差异。该诊断不改变点预测结果，用于解释严格时间外推下低 R2 的来源。

| target | n_years | total_n | mean_rmse | max_rmse | mean_abs_bias | worst_year | median_shift_iqr | test_over_train_p90_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 6 | 57 | 10.0800 | 24.6175 | 4.1107 | 2022 | 0.1999 | 1.1751 |
| B | 6 | 57 | 1.4885 | 2.7573 | 0.5919 | 2022 | -0.0215 | 1.5270 |
| C | 6 | 57 | 31.6566 | 43.7284 | 16.7176 | 2023 | -0.5655 | 0.8246 |
| D | 6 | 57 | 20.1499 | 61.0907 | 6.7838 | 2022 | 0.1036 | 1.0480 |
| E | 6 | 57 | 13.1169 | 40.1069 | 6.6039 | 2024 | 0.0133 | 1.0494 |
| F | 6 | 57 | 330.5270 | 1517.5973 | 119.9698 | 2021 | 1.3482 | 1.7015 |
| G | 6 | 57 | 29.9633 | 51.5820 | 14.4246 | 2021 | -0.1697 | 0.6767 |
| H | 6 | 57 | 0.2922 | 1.0879 | 0.0846 | 2021 | -0.1667 | 1.5392 |

图件：

- `figures/yearwise_error_diagnostics/publication_yearwise_rmse_heatmap.png`
- `figures/yearwise_error_diagnostics/publication_yearwise_bias_heatmap.png`
- `figures/yearwise_error_diagnostics/publication_yearwise_sample_count.png`
- `figures/yearwise_error_diagnostics/train_test_distribution_shift.png`

完整逐年指标见 `tables/publication_yearwise_error_metrics.csv`；分布漂移指标见 `tables/target_distribution_shift_metrics.csv`；摘要表见 `tables/publication_yearwise_error_summary.csv`。

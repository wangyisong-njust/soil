# 逐年误差与分布漂移诊断

本报告将论文主结果在 2022-2026 测试期按年份拆分，统计逐年 RMSE、MAE、偏差和样本量，并比较训练期与测试期目标分布差异。该诊断不改变点预测结果，用于解释严格时间外推下低 R2 的来源。

| target | n_years | total_n | mean_rmse | max_rmse | mean_abs_bias | worst_year | median_shift_iqr | test_over_train_p90_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 5 | 34 | 9.8294 | 12.5542 | 6.3285 | 2022 | 0.1652 | 1.0751 |
| B | 5 | 34 | 1.0489 | 2.0096 | 0.5341 | 2022 | -0.1419 | 1.0184 |
| C | 5 | 34 | 31.8976 | 63.8600 | 16.8314 | 2025 | -0.6195 | 0.8331 |
| D | 5 | 34 | 20.9415 | 56.9770 | 9.1314 | 2022 | 0.0617 | 0.9892 |
| E | 5 | 34 | 12.8064 | 33.9264 | 6.5513 | 2024 | 0.1120 | 1.2093 |
| F | 5 | 34 | 51.0135 | 75.2980 | 31.2504 | 2023 | 1.2024 | 1.2469 |
| G | 5 | 34 | 20.2474 | 36.6300 | 13.1985 | 2025 | -0.2689 | 0.5896 |
| H | 5 | 34 | 0.1229 | 0.3148 | 0.0544 | 2022 | -0.5957 | 1.5654 |

图件：

- `figures/yearwise_error_diagnostics/publication_yearwise_rmse_heatmap.png`
- `figures/yearwise_error_diagnostics/publication_yearwise_bias_heatmap.png`
- `figures/yearwise_error_diagnostics/publication_yearwise_sample_count.png`
- `figures/yearwise_error_diagnostics/train_test_distribution_shift.png`

完整逐年指标见 `tables/publication_yearwise_error_metrics.csv`；分布漂移指标见 `tables/target_distribution_shift_metrics.csv`；摘要表见 `tables/publication_yearwise_error_summary.csv`。

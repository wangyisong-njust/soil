# 未来预测不确定性区间

该报告将 2021-2026 论文主结果的经验残差 90% 区间迁移到 2027-2035 基线情景预测，输出未来预测下限、上限和区间宽度。当前使用的未来点预测文件为 `results/future_predictions_publication_aligned_2027_2035.csv`。该结果用于未来不确定性表达，不改变点预测。

| target | n | mean_prediction | median_prediction | median_interval_width | mean_relative_width | max_upper | future_prediction_file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 8478 | 14.0453 | 12.3352 | 21.4287 | 1.8563 | 170.9484 | future_predictions_publication_aligned_2027_2035.csv |
| B | 8478 | 0.7406 | 0.5248 | 3.6599 | 7.2231 | 25.3552 | future_predictions_publication_aligned_2027_2035.csv |
| C | 8478 | 38.7347 | 37.6625 | 88.8295 | 2.4808 | 126.6170 | future_predictions_publication_aligned_2027_2035.csv |
| D | 8478 | 35.3778 | 30.6364 | 51.4401 | 1.6872 | 393.4244 | future_predictions_publication_aligned_2027_2035.csv |
| E | 8478 | 32.6361 | 31.5411 | 32.8001 | 1.0412 | 194.6475 | future_predictions_publication_aligned_2027_2035.csv |
| F | 8478 | 220.3596 | 272.2000 | 358.1384 | 1.8643 | 531.6079 | future_predictions_publication_aligned_2027_2035.csv |
| G | 8478 | 78.5653 | 75.3800 | 88.1880 | 1.1461 | 177.0220 | future_predictions_publication_aligned_2027_2035.csv |
| H | 8478 | 0.1462 | 0.1096 | 0.4094 | 3.8101 | 2.6683 | future_predictions_publication_aligned_2027_2035.csv |

图件：

- `figures/future_uncertainty/future_interval_width_by_target.png`
- `figures/future_uncertainty/C_future_mean_interval_trend.png`
- `figures/future_uncertainty/F_future_mean_interval_trend.png`
- `figures/future_uncertainty/G_future_mean_interval_trend.png`

完整未来区间结果见 `results/future_predictions_publication_aligned_2027_2035_intervals.csv`；兼容旧流程的副本保留在 `results/future_predictions_baseline_2027_2035_intervals.csv`；年度汇总见 `tables/future_prediction_interval_by_year.csv`。

# 未来超阈值概率

该报告基于 2027-2035 未来点预测和 2022-2026 经验残差分布，估计未来浓度超过 2000-2018 训练核心期 q90/q95 阈值的概率。当前使用的未来区间文件为 `results/future_predictions_publication_aligned_2027_2035_intervals.csv`。该结果用于未来高污染风险图，不改变连续浓度点预测。

## C/F/G 未来超阈值概率

| target | quantile | n | mean_probability | median_probability | p90_probability | high_prob_050_rate | high_prob_080_rate | threshold_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C | 0.9000 | 8478 | 0.0951 | 0.0882 | 0.0882 | 0.0042 | 0.0011 | 82.1960 |
| F | 0.9000 | 8478 | 0.7232 | 1.0000 | 1.0000 | 0.7261 | 0.6369 | 125.2200 |
| G | 0.9000 | 8478 | 0.0140 | 0.0000 | 0.0000 | 0.0138 | 0.0096 | 160.1140 |
| C | 0.9500 | 8478 | 0.0879 | 0.0882 | 0.0882 | 0.0011 | 0.0011 | 95.9780 |
| F | 0.9500 | 8478 | 0.6098 | 0.8529 | 1.0000 | 0.6062 | 0.5032 | 166.4100 |
| G | 0.9500 | 8478 | 0.0002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 261.7400 |

图件：

- `figures/future_exceedance_probability/cfg_q90_future_exceedance_probability_trend.png`
- `figures/future_exceedance_probability/target_q90_future_exceedance_probability.png`

完整概率结果见 `results/future_exceedance_probability_2027_2035.csv`；年度汇总见 `tables/future_exceedance_probability_by_year.csv`。

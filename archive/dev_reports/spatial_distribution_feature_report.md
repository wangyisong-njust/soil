# 目标专属空间分布特征模型

该实验把训练期目标值的空间邻域均值、分位数、极值、IDW 等统计量作为目标专属空间特征。训练样本使用 leave-one-out 计算，测试样本只使用训练期目标值计算，避免直接泄露测试期目标值。

| target | feature_set | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | external_plus_spatial_distribution | LightGBM | 0.3093 | 13.4809 | 6.5909 | 43.8464 |
| B | external_plus_spatial_distribution | ExtraTrees | 0.3775 | 2.8341 | 1.3282 | 348.6012 |
| C | external_plus_spatial_distribution | ExtraTrees | -0.0907 | 37.8237 | 28.4585 | 81.5807 |
| D | external_plus_spatial_distribution | ExtraTrees | 0.1945 | 38.5768 | 15.3072 | 33.4496 |
| E | external_plus_spatial_distribution | LightGBM | 0.4725 | 14.3790 | 7.6355 | 23.1198 |
| F | external_plus_spatial_distribution | LightGBM | -0.0295 | 974.4542 | 212.5004 | 68.0311 |
| G | spatial_distribution_only | ExtraTrees | -0.6496 | 50.7781 | 34.5874 | 54.8722 |
| H | spatial_distribution_only | LightGBM | 0.0995 | 0.7548 | 0.1876 | 131.6575 |

本轮严格 2021-2026 外推下，该方法整体未超过最终目标自适应推荐结果，适合作为可解释的空间背景消融对照保留。

完整结果见 `tables/spatial_distribution_feature_metrics.csv`；最优结果见 `tables/spatial_distribution_feature_best_metrics.csv`。

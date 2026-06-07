# 目标专属空间分布特征模型

该实验把训练期目标值的空间邻域均值、分位数、极值、IDW 等统计量作为目标专属空间特征。训练样本使用 leave-one-out 计算，测试样本只使用训练期目标值计算，避免直接泄露测试期目标值。

| target | feature_set | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | external_plus_spatial_distribution | HistGBR | 0.1896 | 17.2889 | 7.1689 | 47.7447 |
| B | external_plus_spatial_distribution | XGBoost | 0.1071 | 1.9434 | 0.9109 | 373.8480 |
| C | external_plus_spatial_distribution | XGBoost | 0.0449 | 33.2474 | 21.4371 | 57.1420 |
| D | external_plus_spatial_distribution | ElasticNet | 0.1923 | 45.2939 | 17.1825 | 29.5009 |
| E | external_plus_spatial_distribution | ExtraTrees | 0.4522 | 18.0114 | 8.7738 | 21.8621 |
| F | spatial_distribution_only | LightGBM | 0.1853 | 72.6094 | 44.7357 | 35.8100 |
| G | external_plus_spatial_distribution | XGBoost | 0.1089 | 25.9012 | 19.2719 | 40.1237 |
| H | external_plus_spatial_distribution | HistGBR | -0.0946 | 0.2467 | 0.1285 | 218.6427 |

本轮严格 2022-2026 外推下，该方法整体未超过最终目标自适应推荐结果，适合作为可解释的空间背景消融对照保留。

完整结果见 `tables/spatial_distribution_feature_metrics.csv`；最优结果见 `tables/spatial_distribution_feature_best_metrics.csv`。

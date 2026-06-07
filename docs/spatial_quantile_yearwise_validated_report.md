# 空间分位数逐年稳健验证基线

本实验把 2019 和 2020 分开作为验证年，选择跨验证年 RMSE 更稳定且最差年份不过度失效的 KNN/Grid 空间分位数超参数，再固定用于 2022-2026 测试期。该方法不使用 2022-2026 目标观测值选型。

| target | method | model | validation_mean_rmse | validation_median_r2 | validation_min_r2 | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | grid_spatial_quantile | Grid10_Q55 | 9.6670 | 0.1705 | 0.1561 | 0.1065 | 18.1539 | 7.0451 | 45.2414 |
| B | grid_spatial_quantile | Grid3_Q50 | 1.5367 | -0.1376 | -0.1576 | -0.0575 | 2.1150 | 0.6503 | 79.6597 |
| C | grid_spatial_quantile | Grid2_Q60 | 39.8398 | 0.0413 | 0.0400 | -0.2251 | 37.6538 | 31.3631 | 98.0967 |
| D | grid_spatial_quantile | Grid2_Q60 | 42.5622 | -0.0738 | -0.0904 | -0.0707 | 52.1486 | 18.6615 | 26.6036 |
| E | grid_spatial_quantile | Grid3_Q60 | 9.6139 | 0.0219 | 0.0120 | -0.0395 | 24.8105 | 11.0630 | 25.0702 |
| F | knn_spatial_quantile | KNN8_Q35 | 71.5920 | 0.0582 | 0.0356 | -0.7346 | 105.9465 | 81.2082 | 70.9578 |
| G | grid_spatial_quantile | Grid2_Q60 | 100.7545 | -0.1008 | -0.1825 | -0.1228 | 29.0753 | 20.6839 | 39.6971 |
| H | knn_spatial_quantile | KNN5_Q55 | 0.1779 | 0.2343 | -0.0742 | -4.0359 | 0.5292 | 0.2129 | 352.1314 |

2022-2026 下平均 R2=-0.6474，中位 R2=-0.0968，1/8 个目标为正。

逐年验证明细见 `tables/spatial_quantile_yearwise_validation_metrics.csv`；最终结果见 `tables/spatial_quantile_yearwise_validated_best_metrics.csv`。

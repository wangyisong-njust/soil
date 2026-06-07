# 空间分位数逐年稳健验证基线

本实验把 2019 和 2020 分开作为验证年，选择跨验证年 RMSE 更稳定且最差年份不过度失效的 KNN/Grid 空间分位数超参数，再固定用于 2021-2026 测试期。该方法不使用 2021-2026 目标观测值选型。

| target | method | model | validation_mean_rmse | validation_median_r2 | validation_min_r2 | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | grid_spatial_quantile | Grid10_Q55 | 9.6670 | 0.1705 | 0.1561 | 0.0968 | 15.4158 | 6.8525 | 41.7599 |
| B | grid_spatial_quantile | Grid3_Q50 | 1.5367 | -0.1376 | -0.1576 | -0.0642 | 3.7055 | 1.2458 | 77.9416 |
| C | grid_spatial_quantile | Grid2_Q60 | 39.8398 | 0.0413 | 0.0400 | -0.1481 | 38.8056 | 31.1366 | 94.1528 |
| D | grid_spatial_quantile | Grid2_Q60 | 42.5622 | -0.0738 | -0.0904 | -0.0501 | 44.0464 | 17.3292 | 31.8528 |
| E | grid_spatial_quantile | Grid3_Q60 | 9.6139 | 0.0219 | 0.0120 | -0.0005 | 19.8015 | 8.8085 | 24.6886 |
| F | knn_spatial_quantile | KNN8_Q35 | 71.5920 | 0.0582 | 0.0356 | -0.0510 | 984.5931 | 224.8663 | 70.4553 |
| G | grid_spatial_quantile | Grid2_Q60 | 100.7545 | -0.1008 | -0.1825 | -0.0277 | 40.0789 | 24.7439 | 37.1274 |
| H | knn_spatial_quantile | KNN5_Q55 | 0.1779 | 0.2343 | -0.0742 | -0.3681 | 0.9304 | 0.2990 | 266.3205 |

2021-2026 下平均 R2=-0.0766，中位 R2=-0.0506，1/8 个目标为正。

逐年验证明细见 `tables/spatial_quantile_yearwise_validation_metrics.csv`；最终结果见 `tables/spatial_quantile_yearwise_validated_best_metrics.csv`。

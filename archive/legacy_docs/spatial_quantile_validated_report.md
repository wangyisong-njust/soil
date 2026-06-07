# 空间分位数验证期选择基线

该报告把空间分位数 KNN/Grid 兜底模型拆成两个口径：验证期选择版和测试集选择上限。论文主结果只能使用验证期选择版；测试集选择上限只用于诊断空间分布候选库的可拟合空间。

## 验证期选择版

| target | method | model | validation_r2 | validation_rmse | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | grid_spatial_quantile | Grid10_Q55 | 0.1920 | 12.5654 | 0.1065 | 18.1539 | 7.0451 | 45.2414 |
| B | knn_spatial_quantile | KNN12_Q55 | 0.0192 | 2.1527 | 0.3028 | 1.7173 | 0.6875 | 233.2355 |
| C | knn_spatial_quantile | KNN8_Q75 | 0.1095 | 49.4491 | -0.4831 | 41.4296 | 34.6704 | 108.1862 |
| D | knn_spatial_quantile | KNN12_Q75 | 0.2814 | 48.7972 | 0.2363 | 44.0436 | 20.6842 | 45.3873 |
| E | knn_spatial_quantile | KNN5_Q60 | 0.1057 | 10.6171 | -0.1091 | 25.6274 | 11.7763 | 26.4842 |
| F | grid_spatial_quantile | Grid2_Q75 | 0.0777 | 82.4259 | -0.3472 | 93.3675 | 58.6425 | 42.4248 |
| G | grid_spatial_quantile | Grid2_Q75 | 0.0333 | 122.5095 | -0.8043 | 36.8570 | 30.6688 | 58.7316 |
| H | knn_spatial_quantile | KNN5_Q50 | 0.5423 | 0.2416 | -4.0495 | 0.5299 | 0.2132 | 343.9762 |

## 测试集选择上限

| target | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | grid_spatial_quantile | Grid6_Q90 | 0.6800 | 10.8646 | 7.4576 | 80.3602 |
| B | grid_spatial_quantile | Grid10_Q60 | 0.4368 | 1.5434 | 0.6130 | 238.8579 |
| C | knn_spatial_quantile | KNN12_Q20 | 0.1409 | 31.5328 | 18.4638 | 42.5612 |
| D | grid_spatial_quantile | Grid10_Q75 | 0.3695 | 40.0182 | 17.2896 | 36.6441 |
| E | grid_spatial_quantile | Grid10_Q75 | 0.5758 | 15.8497 | 9.4173 | 27.6474 |
| F | knn_spatial_quantile | KNN80_Q85 | 0.2640 | 69.0142 | 52.2560 | 47.6173 |
| G | knn_spatial_quantile | KNN20_Q45 | 0.4941 | 19.5170 | 14.3481 | 31.0369 |
| H | knn_spatial_quantile | KNN80_Q85 | 0.0793 | 0.2263 | 0.1185 | 238.2160 |

输出文件：`tables/spatial_quantile_validated_best_metrics.csv`、`tables/spatial_quantile_test_selected_best_metrics.csv`。

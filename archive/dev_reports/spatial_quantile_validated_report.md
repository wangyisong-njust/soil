# 空间分位数验证期选择基线

该报告把空间分位数 KNN/Grid 兜底模型拆成两个口径：验证期选择版和测试集选择上限。论文主结果只能使用验证期选择版；测试集选择上限只用于诊断空间分布候选库的可拟合空间。

## 验证期选择版

| target | method | model | validation_r2 | validation_rmse | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | grid_spatial_quantile | Grid10_Q55 | 0.1920 | 12.5654 | 0.0968 | 15.4158 | 6.8525 | 41.7599 |
| B | knn_spatial_quantile | KNN12_Q55 | 0.0192 | 2.1527 | 0.0621 | 3.4788 | 1.2960 | 241.8423 |
| C | knn_spatial_quantile | KNN8_Q75 | 0.1095 | 49.4491 | -0.5182 | 44.6246 | 36.8445 | 113.9188 |
| D | knn_spatial_quantile | KNN12_Q75 | 0.2814 | 48.7972 | 0.2262 | 37.8091 | 20.2988 | 53.1376 |
| E | knn_spatial_quantile | KNN5_Q60 | 0.1057 | 10.6171 | -0.0521 | 20.3059 | 9.7018 | 26.7963 |
| F | grid_spatial_quantile | Grid2_Q75 | 0.0777 | 82.4259 | -0.0358 | 977.4514 | 207.1567 | 57.4169 |
| G | grid_spatial_quantile | Grid2_Q75 | 0.0333 | 122.5095 | -0.2800 | 44.7286 | 34.1529 | 54.9658 |
| H | knn_spatial_quantile | KNN5_Q50 | 0.5423 | 0.2416 | -0.3535 | 0.9254 | 0.2947 | 257.6890 |

## 测试集选择上限

| target | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | grid_spatial_quantile | Grid5_Q85 | 0.1998 | 14.5106 | 8.4162 | 67.5864 |
| B | knn_spatial_quantile | KNN5_Q50 | 0.3404 | 2.9172 | 1.2408 | 283.0235 |
| C | knn_spatial_quantile | KNN12_Q30 | 0.0596 | 35.1208 | 21.6593 | 51.5820 |
| D | knn_spatial_quantile | KNN12_Q75 | 0.2262 | 37.8091 | 20.2988 | 53.1376 |
| E | grid_spatial_quantile | Grid8_Q75 | 0.4285 | 14.9656 | 9.3691 | 32.2775 |
| F | grid_spatial_quantile | Grid2_Q96 | 0.0140 | 953.6686 | 269.2298 | 191.6443 |
| G | grid_spatial_quantile | Grid5_Q50 | 0.0812 | 37.8970 | 22.4388 | 33.5596 |
| H | knn_spatial_quantile | KNN50_Q85 | 0.0476 | 0.7763 | 0.2067 | 197.9618 |

输出文件：`tables/spatial_quantile_validated_best_metrics.csv`、`tables/spatial_quantile_test_selected_best_metrics.csv`。

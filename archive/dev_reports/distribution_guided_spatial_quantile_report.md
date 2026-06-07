# 训练期分布规则空间分位数基线

本实验不使用 2021-2026 测试期目标值选择分位数。每个目标先在训练期计算 CV、IQR/median 和 p95/median，再按预设规则选择低分位、空间中位或高分位空间背景场：低变异目标使用局部低分位，强偏态且 IQR 较宽的目标使用高分位粗网格，强偏态但主体较集中的目标使用中位空间网格，其余目标使用局部中位偏高分位。

| target | rule | method | model | cv | iqr_to_median | quantile | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | moderate_distribution_local_median_plus | knn_spatial_quantile | KNN20_Q55 | 1.4371 | 0.6500 | 0.5500 | 0.1035 | 15.3586 | 6.8916 | 44.1635 |
| B | high_cv_wide_iqr_upper_tail | grid_spatial_quantile | Grid2_Q96 | 4.1310 | 2.1136 | 0.9600 | -1.3324 | 5.4859 | 4.4784 | 2371.0862 |
| C | low_cv_local_lower_quartile | knn_spatial_quantile | KNN12_Q25 | 0.6222 | 0.6404 | 0.2500 | 0.0561 | 35.1860 | 20.9462 | 47.9229 |
| D | moderate_distribution_local_median_plus | knn_spatial_quantile | KNN20_Q55 | 1.2910 | 0.5273 | 0.5500 | -0.0485 | 44.0127 | 16.7653 | 31.2963 |
| E | moderate_distribution_local_median_plus | knn_spatial_quantile | KNN20_Q55 | 0.8863 | 0.2443 | 0.5500 | -0.0358 | 20.1480 | 8.7555 | 23.9003 |
| F | high_cv_wide_iqr_upper_tail | grid_spatial_quantile | Grid2_Q96 | 2.2801 | 1.2710 | 0.9600 | 0.0140 | 953.6686 | 269.2298 | 191.6443 |
| G | high_cv_compact_core_spatial_median | grid_spatial_quantile | Grid5_Q50 | 2.8937 | 0.4438 | 0.5000 | 0.0812 | 37.8970 | 22.4388 | 33.5596 |
| H | high_cv_compact_core_spatial_median | grid_spatial_quantile | Grid5_Q50 | 2.2366 | 0.6667 | 0.5000 | -0.0138 | 0.8009 | 0.1788 | 97.7119 |

2021-2026 下平均 R2=-0.1470，中位 R2=0.0001，4/8 个目标为正。

输出文件：`tables/distribution_guided_spatial_quantile_metrics.csv`、`results/distribution_guided_spatial_quantile_predictions.csv`。

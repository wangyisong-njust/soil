# 训练期分布规则空间分位数基线

本实验不使用 2022-2026 测试期目标值选择分位数。每个目标先在训练期计算 CV、IQR/median 和 p95/median，再按预设规则选择低分位、空间中位或高分位空间背景场：低变异目标使用局部低分位，强偏态且 IQR 较宽的目标使用高分位粗网格，强偏态但主体较集中的目标使用中位空间网格，其余目标使用局部中位偏高分位。

| target | rule | method | model | cv | iqr_to_median | quantile | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | moderate_distribution_local_median_plus | knn_spatial_quantile | KNN20_Q55 | 1.4170 | 0.6466 | 0.5500 | 0.0783 | 18.4386 | 7.3796 | 48.6065 |
| B | high_cv_wide_iqr_upper_tail | grid_spatial_quantile | Grid2_Q96 | 4.0369 | 2.1136 | 0.9600 | -12.3795 | 7.5226 | 5.5287 | 3309.3558 |
| C | low_cv_local_lower_quartile | knn_spatial_quantile | KNN12_Q25 | 0.6270 | 0.6440 | 0.2500 | 0.1311 | 31.7119 | 19.4907 | 47.4475 |
| D | moderate_distribution_local_median_plus | knn_spatial_quantile | KNN20_Q55 | 1.2795 | 0.5238 | 0.5500 | -0.0696 | 52.1226 | 18.6172 | 27.4804 |
| E | moderate_distribution_local_median_plus | knn_spatial_quantile | KNN20_Q55 | 0.8780 | 0.2463 | 0.5500 | -0.0801 | 25.2905 | 11.0736 | 24.2424 |
| F | high_cv_wide_iqr_upper_tail | grid_spatial_quantile | Grid2_Q96 | 3.6752 | 1.4149 | 0.9600 | -5.7021 | 208.2545 | 143.1539 | 171.9581 |
| G | high_cv_compact_core_spatial_median | grid_spatial_quantile | Grid5_Q50 | 2.8797 | 0.4430 | 0.5000 | 0.2514 | 23.7413 | 17.0166 | 34.4428 |
| H | high_cv_compact_core_spatial_median | grid_spatial_quantile | Grid5_Q50 | 2.4794 | 0.6528 | 0.5000 | -0.0006 | 0.2359 | 0.1038 | 137.6334 |

2022-2026 下平均 R2=-2.2214，中位 R2=-0.0351，3/8 个目标为正。

输出文件：`tables/distribution_guided_spatial_quantile_metrics.csv`、`results/distribution_guided_spatial_quantile_predictions.csv`。

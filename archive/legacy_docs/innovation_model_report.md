# 时空创新模型对照

本报告比较空间分区、空间背景值残差、时间加权和两阶段高污染模型。所有模型只使用训练期目标值构建空间背景或阈值，不使用验证期真实目标值。

## 协议汇总

| protocol | mean_best_r2 | median_best_r2 | max_best_r2 | min_best_r2 |
| --- | --- | --- | --- | --- |
| temporal_2022_2026 | 0.1562 | 0.0815 | 0.4447 | -0.0422 |
| literature_2019_2020 | 0.1507 | 0.1090 | 0.4402 | 0.0243 |

## 各目标最佳模型

| protocol | target | method | model | n_train | n_test | r2 | r2_log1p | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| literature_2019_2020 | A | temporal_weighted | ElasticNet | 815.0 | 100.0 | 0.1109 | 0.1204 | 13.1807 | 6.4337 | 42.0066 |
| literature_2019_2020 | B | two_stage_high_pollution | CatBoost | 815.0 | 100.0 | 0.0612 | -0.1411 | 2.1062 | 1.0963 | 279.8004 |
| literature_2019_2020 | C | direct_global | HistGBR | 815.0 | 100.0 | 0.1522 | 0.0814 | 48.2481 | 24.6248 | 38.7681 |
| literature_2019_2020 | D | spatial_zone_features | HistGBR | 815.0 | 100.0 | 0.2068 | -0.1881 | 51.2692 | 24.5735 | 64.0806 |
| literature_2019_2020 | E | direct_global | RF | 815.0 | 100.0 | 0.1072 | 0.0888 | 10.6085 | 7.4138 | 27.3992 |
| literature_2019_2020 | F | direct_global | XGBoost | 815.0 | 100.0 | 0.1028 | 0.2666 | 81.2924 | 37.5522 | 58.8888 |
| literature_2019_2020 | G | temporal_weighted | CatBoost | 815.0 | 100.0 | 0.0243 | 0.0254 | 123.0781 | 49.0977 | 37.7444 |
| literature_2019_2020 | H | spatial_zone_features | RF | 815.0 | 100.0 | 0.4402 | 0.4279 | 0.2671 | 0.1177 | 91.9660 |
| temporal_2022_2026 | A | temporal_weighted | LightGBM | 938.0 | 34.0 | 0.4447 | 0.2081 | 14.3112 | 7.2072 | 53.8504 |
| temporal_2022_2026 | B | two_stage_high_pollution | CatBoost | 938.0 | 34.0 | -0.0422 | -0.1707 | 2.0995 | 1.0348 | 401.9657 |
| temporal_2022_2026 | C | spatial_zone_features | LightGBM | 938.0 | 34.0 | 0.0298 | -0.0804 | 33.5093 | 22.1738 | 57.7552 |
| temporal_2022_2026 | D | spatial_zone_features | NGBoost | 938.0 | 34.0 | 0.2892 | 0.5014 | 42.4907 | 15.2041 | 25.7431 |
| temporal_2022_2026 | E | spatial_zone_features | PLSR | 938.0 | 34.0 | 0.3527 | 0.2936 | 19.5785 | 9.8610 | 25.0173 |
| temporal_2022_2026 | F | spatial_zone_features | LightGBM | 938.0 | 34.0 | 0.0500 | -0.6819 | 78.4072 | 50.6845 | 39.3205 |
| temporal_2022_2026 | G | direct_global | PLSR | 938.0 | 34.0 | 0.1131 | -0.1889 | 25.8408 | 20.3836 | 41.1135 |
| temporal_2022_2026 | H | direct_global | CatBoost | 938.0 | 34.0 | 0.0119 | 0.0216 | 0.2344 | 0.1191 | 213.0705 |

## 方法说明

- `direct_global`：全局模型基线。
- `spatial_zone_features`：基于训练期经纬度 KMeans 分区，将分区哑变量加入模型。
- `spatial_baseline_residual`：先用训练期 IDW 背景场估计空间基线，再用机器学习预测残差。
- `spatial_baseline_residual_zone`：在空间残差模型中加入分区特征。
- `temporal_weighted`：对靠近验证期的训练样本赋予更高权重。
- `two_stage_high_pollution`：先识别高污染概率，再融合正常区间和高污染区间回归结果。

## 输出文件

- 完整指标：`tables/innovation_model_metrics.csv`
- 各目标最佳指标：`tables/innovation_best_metrics.csv`
- 预测明细：`results/innovation_model_predictions.csv`
- 对照图：`figures/innovation_models/`

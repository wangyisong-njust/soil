# 时空创新模型对照

本报告比较空间分区、空间背景值残差、时间加权和两阶段高污染模型。所有模型只使用训练期目标值构建空间背景或阈值，不使用验证期真实目标值。

## 协议汇总

| protocol | mean_best_r2 | median_best_r2 | max_best_r2 | min_best_r2 |
| --- | --- | --- | --- | --- |
| literature_2019_2020 | 0.1507 | 0.1090 | 0.4402 | 0.0243 |
| temporal_2021_2026 | 0.0732 | 0.1741 | 0.5547 | -0.8909 |

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
| temporal_2021_2026 | A | temporal_weighted | LightGBM | 915.0 | 57.0 | 0.2883 | 0.1298 | 13.6844 | 7.6603 | 51.3379 |
| temporal_2021_2026 | B | spatial_zone_features | ElasticNet | 915.0 | 57.0 | 0.5547 | 0.3201 | 2.3969 | 1.2317 | 343.7841 |
| temporal_2021_2026 | C | direct_global | NGBoost | 915.0 | 57.0 | -0.0616 | -0.4478 | 37.3150 | 28.6660 | 80.8498 |
| temporal_2021_2026 | D | spatial_zone_features | ElasticNet | 915.0 | 57.0 | 0.1906 | 0.2415 | 38.6697 | 16.1601 | 35.9928 |
| temporal_2021_2026 | E | direct_global | PLSR | 915.0 | 57.0 | 0.3617 | 0.2120 | 15.8161 | 8.4350 | 26.3411 |
| temporal_2021_2026 | F | spatial_zone_features | HistGBR | 915.0 | 57.0 | -0.0149 | -0.3366 | 967.5378 | 210.5544 | 61.9134 |
| temporal_2021_2026 | G | two_stage_high_pollution | CatBoost | 915.0 | 57.0 | -0.8909 | -0.8607 | 54.3661 | 40.4744 | 64.5571 |
| temporal_2021_2026 | H | temporal_weighted | NGBoost | 915.0 | 57.0 | 0.1577 | 0.2189 | 0.7300 | 0.2092 | 169.3328 |

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

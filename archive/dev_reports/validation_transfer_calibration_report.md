# 验证期迁移校正模型

该实验使用 2019-2020 验证期学习候选预测的偏差校正、尺度校正、锚点收缩和时空局部残差校正，然后固定迁移到 2021-2026 测试期。论文口径表只按 2019-2020 校正后验证表现选择模型，不使用 2021-2026 目标观测值选模型。

## 验证期选择结果

| target | model | base_candidate | validation_r2_calibrated | validation_rmse_calibrated | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | isotonic_transfer | spatial_quantile::knn_spatial_quantile::KNN12_Q85 | 0.3831 | 10.9790 | 0.0030 | 16.1967 | 7.5560 | 53.2565 |
| B | isotonic_transfer | temporal_sequence::hybrid_spatiotemporal_sequence::HistGBR | 0.2647 | 1.8639 | 0.1041 | 3.4000 | 1.3791 | 241.5517 |
| C | isotonic_transfer | innovation::direct_global::LightGBM | 0.6714 | 30.0369 | -2.5615 | 68.3481 | 39.2887 | 110.9259 |
| D | isotonic_transfer | spatial_quantile::knn_spatial_quantile::KNN8_Q20 | 0.8434 | 22.7772 | 0.0362 | 42.1969 | 18.0529 | 40.8885 |
| E | isotonic_transfer | spatial_quantile::knn_spatial_quantile::KNN80_Q50 | 0.3090 | 9.3328 | -0.0232 | 20.0251 | 9.5464 | 26.0019 |
| F | isotonic_transfer | quantile_gate::quantile_regression::QuantileP90 | 0.5191 | 59.5205 | -0.0337 | 976.4487 | 211.8818 | 65.0764 |
| G | isotonic_transfer | external::external_covariates::HistGBR | 0.2057 | 111.0444 | -2.0266 | 68.7811 | 41.5269 | 61.2710 |
| H | isotonic_transfer | quantile_gate::quantile_regression::QuantileP90 | 0.9481 | 0.0813 | -0.0171 | 0.8022 | 0.1942 | 139.7169 |

## 测试集选择上限

下表按 2021-2026 测试表现选择，只能作为探索上限或诊断，不可作为论文主验证结果。

| target | model | base_candidate | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | isotonic_transfer | spatial_quantile::knn_spatial_quantile::KNN120_Q15 | 0.6235 | 9.9534 | 6.8109 | 55.0702 |
| B | ridge_1d_transfer | temporal_sequence::hybrid_spatiotemporal_sequence::ElasticNet | 0.5954 | 2.2850 | 1.2423 | 478.0581 |
| C | spacetime_residual_knn35 | temporal_sequence::pure_temporal_baseline::LSTMAnnualMean | 0.0878 | 34.5900 | 22.2803 | 54.6776 |
| D | isotonic_transfer | causal_history::causal_history_ml::XGBoost | 0.3600 | 34.3851 | 16.7166 | 43.2240 |
| E | robust_iqr_scale_shift | spatial_distribution::spatial_distribution_features::LightGBM | 0.5776 | 12.8660 | 7.6590 | 25.2252 |
| F | robust_iqr_scale_shift | temporal_sequence::hybrid_spatiotemporal_sequence::LightGBM | 0.0117 | 954.7764 | 228.2275 | 103.7663 |
| G | validated_anchor_shrink | spatial_quantile::knn_spatial_quantile::KNN20_Q60 | 0.1953 | 35.4653 | 23.5729 | 38.6940 |
| H | isotonic_transfer | spatial_quantile::knn_spatial_quantile::KNN12_Q35 | 0.5722 | 0.5203 | 0.1758 | 219.3944 |

完整指标见 `tables/validation_transfer_calibration_metrics.csv`；验证期选择结果见 `tables/validation_transfer_calibration_best_metrics.csv`；测试集选择上限见 `tables/validation_transfer_calibration_test_selected_best_metrics.csv`；验证期选择预测明细见 `results/validation_transfer_calibration_predictions.csv`。

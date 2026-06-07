# 验证期迁移校正模型

该实验使用 2019-2020 验证期学习候选预测的偏差校正、尺度校正、锚点收缩和时空局部残差校正，然后固定迁移到 2022-2026 测试期。论文口径表只按 2019-2020 校正后验证表现选择模型，不使用 2022-2026 目标观测值选模型。

## 验证期选择结果

| target | model | base_candidate | validation_r2_calibrated | validation_rmse_calibrated | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | isotonic_transfer | spatial_quantile::knn_spatial_quantile::KNN12_Q85 | 0.3831 | 10.9790 | 0.0328 | 18.8882 | 7.8905 | 62.5142 |
| B | isotonic_transfer | temporal_sequence::hybrid_spatiotemporal_sequence::HistGBR | 0.2647 | 1.8639 | -0.1044 | 2.1613 | 0.9589 | 295.6209 |
| C | isotonic_transfer | external::external_covariates::RF | 0.6814 | 29.5784 | -0.2499 | 38.0339 | 30.1242 | 94.2642 |
| D | isotonic_transfer | spatial_quantile::knn_spatial_quantile::KNN8_Q20 | 0.8434 | 22.7772 | 0.0206 | 49.8749 | 19.1464 | 34.0473 |
| E | isotonic_transfer | spatial_quantile::knn_spatial_quantile::KNN80_Q50 | 0.3090 | 9.3328 | -0.0022 | 24.3609 | 11.0209 | 23.3698 |
| F | isotonic_transfer | quantile_gate::quantile_regression::QuantileP90 | 0.5191 | 59.5205 | -0.1744 | 87.1757 | 56.9313 | 43.0700 |
| G | isotonic_transfer | causal_history::causal_history_ml::HistGBR | 0.1994 | 111.4902 | -1.7752 | 45.7104 | 29.9694 | 54.0086 |
| H | isotonic_transfer | quantile_gate::quantile_regression::QuantileP90 | 0.9481 | 0.0813 | -0.0306 | 0.2394 | 0.1126 | 173.5478 |

## 测试集选择上限

下表按 2022-2026 测试表现选择，只能作为探索上限或诊断，不可作为论文主验证结果。

| target | model | base_candidate | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | median_residual_shift | spatial_quantile::grid_spatial_quantile::Grid6_Q95 | 0.8550 | 7.3131 | 5.0962 | 49.6602 |
| B | mean_std_scale_shift | spatial_quantile::grid_spatial_quantile::Grid10_Q45 | 0.8876 | 0.6895 | 0.4682 | 264.8839 |
| C | spacetime_residual_knn10 | innovation::spatial_zone_features::XGBoost | 0.1608 | 31.1640 | 21.9617 | 60.5865 |
| D | mean_std_scale_shift | causal_history::causal_history_ml::HistGBR | 0.5930 | 32.1503 | 22.6534 | 57.5294 |
| E | robust_iqr_scale_shift | spatial_quantile::grid_spatial_quantile::Grid5_Q55 | 0.6192 | 15.0161 | 9.8393 | 27.7577 |
| F | spacetime_residual_knn35 | causal_history::causal_history_ml::LightGBM | 0.4992 | 56.9269 | 36.9067 | 30.9366 |
| G | median_residual_shift | spatial_quantile::knn_spatial_quantile::KNN20_Q50 | 0.5249 | 18.9135 | 13.3114 | 30.5002 |
| H | robust_iqr_scale_shift | spatial_quantile::grid_spatial_quantile::Grid4_Q15 | 0.2705 | 0.2014 | 0.1143 | 190.6411 |

完整指标见 `tables/validation_transfer_calibration_metrics.csv`；验证期选择结果见 `tables/validation_transfer_calibration_best_metrics.csv`；测试集选择上限见 `tables/validation_transfer_calibration_test_selected_best_metrics.csv`；验证期选择预测明细见 `results/validation_transfer_calibration_predictions.csv`。

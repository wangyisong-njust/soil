# 空间分位数与模型融合探索

该实验在严格 2021-2026 验证集上搜索现有模型预测与空间分位数预测的两两线性融合，用于判断当前数据的探索性性能上限。该表属于验证集探索结果，不能表述为未调参的独立测试结果。

| target | model | r2 | rmse | mae | candidate_1 | candidate_2 | weight_1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | blend_w0.65 | 0.3373 | 13.2047 | 7.1293 | temporal_calibration::temporal_validation_calibration::spatial_distribution:LightGBM:RatioScaled | innovation::temporal_weighted::LightGBM | 0.6500 |
| B | blend_w0.55 | 0.6261 | 2.1966 | 1.0566 | temporal_calibration::temporal_validation_calibration::temporal_sequence:ElasticNet:BiasCorrected | temporal_calibration::temporal_validation_calibration::local_analog:ElasticNet:MeanStdMapped | 0.5500 |
| C | blend_w0.55 | 0.0956 | 34.4415 | 22.4374 | spatial_quantile::knn_spatial_quantile::KNN12_Q25 | temporal_calibration::temporal_validation_calibration::temporal_sequence:ZoneLastAnnualMean:BiasCorrected | 0.5500 |
| D | blend_w0.70 | 0.3782 | 33.8940 | 15.6296 | temporal_calibration::temporal_validation_calibration::external:ElasticNet:QuantileMapped | temporal_calibration::temporal_validation_calibration::local_analog:AnalogRecentMax:QuantileMapped | 0.7000 |
| E | blend_w0.55 | 0.5675 | 13.0187 | 6.9429 | temporal_calibration::temporal_validation_calibration::local_analog:NGBoost:BiasCorrected | temporal_calibration::temporal_validation_calibration::spatial_distribution:LightGBM:RatioScaled | 0.5500 |
| F | blend_w0.50 | 0.0198 | 950.8507 | 225.5146 | spatial_quantile::grid_spatial_quantile::Grid2_Q97 | temporal_calibration::temporal_validation_calibration::temporal_sequence:LightGBM:QuantileMapped | 0.5000 |
| G | blend_w0.60 | 0.1220 | 37.0448 | 23.4221 | spatial_quantile::grid_spatial_quantile::Grid5_Q45 | temporal_calibration::temporal_validation_calibration::local_analog:AnalogP90:LogAffine | 0.6000 |
| H | single_w1.00 | 0.5623 | 0.5262 | 0.1503 | temporal_calibration::temporal_validation_calibration::local_analog:HistGBR:QuantileMapped |  | 1.0000 |

完整结果见 `tables/spatial_model_blend_best_metrics.csv`，预测文件见 `results/spatial_model_blend_predictions.csv`。

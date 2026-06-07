# 空间分位数与模型融合探索

该实验在严格 2022-2026 验证集上搜索现有模型预测与空间分位数预测的两两线性融合，用于判断当前数据的探索性性能上限。该表属于验证集探索结果，不能表述为未调参的独立测试结果。

| target | model | r2 | rmse | mae | candidate_1 | candidate_2 | weight_1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | blend_w0.65 | 0.8275 | 7.9756 | 5.9761 | temporal_calibration::temporal_validation_calibration::external:HistGBR:QuantileMapped | spatial_quantile::grid_spatial_quantile::Grid6_Q96 | 0.6500 |
| B | blend_w0.75 | 0.7162 | 1.0956 | 0.6467 | temporal_calibration::temporal_validation_calibration::local_analog:LightGBM:QuantileMapped | spatial_quantile::grid_spatial_quantile::Grid10_Q75 | 0.7500 |
| C | blend_w0.50 | 0.2056 | 30.3223 | 19.0989 | spatial_quantile::knn_spatial_quantile::KNN12_Q15 | temporal_calibration::temporal_validation_calibration::local_analog:ElasticNet:QuantileMapped | 0.5000 |
| D | blend_w0.70 | 0.6728 | 28.8296 | 16.1472 | temporal_calibration::temporal_validation_calibration::causal_history:HistGBR:MeanStdMappedClipped | multi_evidence::multi_evidence_fusion::Top5Median | 0.7000 |
| E | blend_w0.60 | 0.6201 | 14.9980 | 8.7426 | spatial_quantile::grid_spatial_quantile::Grid10_Q75 | temporal_calibration::temporal_validation_calibration::spatial_distribution:HistGBR:MeanStdMapped | 0.6000 |
| F | blend_w0.65 | 0.4797 | 58.0223 | 36.8472 | temporal_calibration::temporal_validation_calibration::local_analog:AnalogSameOrNearestMax:MeanStdMapped | spatial_quantile::knn_spatial_quantile::KNN80_Q85 | 0.6500 |
| G | blend_w0.70 | 0.5242 | 18.9277 | 14.3526 | spatial_quantile::knn_spatial_quantile::KNN20_Q50 | temporal_calibration::temporal_validation_calibration::external:NGBoost:RatioScaled | 0.7000 |
| H | blend_w0.75 | 0.3509 | 0.1900 | 0.1117 | temporal_calibration::temporal_validation_calibration::multitask_latent:Latent_Ridge:QuantileMapped | temporal_calibration::temporal_validation_calibration::quantile_gate:QuantileP50:QuantileMapped | 0.7500 |

完整结果见 `tables/spatial_model_blend_best_metrics.csv`，预测文件见 `results/spatial_model_blend_predictions.csv`。

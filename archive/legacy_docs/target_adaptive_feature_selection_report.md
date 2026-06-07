# 目标自适应特征筛选模型

该实验只使用 2000-2018 训练、2019-2020 内部验证来选择每个重金属的特征组、top-k 特征数和模型；选择完成后固定方案，用 2000-2021 重新训练并评估 2022-2026。该设计用于减少高维外部变量对不同目标的噪声影响。

| target | feature_set | top_k | model | selection_val_r2 | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | raster_activity | 16 | ExtraTrees | 0.1810 | 0.0929 | 18.2915 | 7.2615 | 49.1112 |
| B | osm_activity | 64 | XGBoost | 0.1235 | 0.3551 | 1.6515 | 0.8018 | 334.9242 |
| C | raster_landcover | 48 | HistGBR | 0.1556 | -0.0524 | 34.8994 | 22.6363 | 56.8199 |
| D | raster_landcover | 24 | ExtraTrees | 0.3065 | 0.2152 | 44.6467 | 15.8793 | 27.0123 |
| E | soil_climate | 36 | ExtraTrees | 0.1157 | 0.4196 | 18.5390 | 9.5467 | 25.3510 |
| F | osm_activity | all | XGBoost | 0.1079 | -0.1304 | 85.5261 | 53.3179 | 39.6177 |
| G | all_external | 64 | ExtraTrees | 0.0490 | -0.4663 | 33.2256 | 24.8334 | 46.0744 |
| H | osm_pollution | 24 | HistGBR | 0.5538 | -0.1569 | 0.2536 | 0.1405 | 267.4194 |

完整内部验证结果见 `tables/target_adaptive_feature_selection_validation_metrics.csv`；严格未来验证结果见 `tables/target_adaptive_feature_selection_best_metrics.csv`。

# 目标自适应特征筛选模型

该实验只使用 2000-2018 训练、2019-2020 内部验证来选择每个重金属的特征组、top-k 特征数和模型；选择完成后固定方案，用 2000-2020 重新训练并评估 2021-2026。该设计用于减少高维外部变量对不同目标的噪声影响。

| target | feature_set | top_k | model | selection_val_r2 | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | raster_activity | 16 | ExtraTrees | 0.1810 | -0.0900 | 16.9353 | 8.2126 | 53.4127 |
| B | osm_activity | 64 | XGBoost | 0.1235 | 0.2842 | 3.0391 | 1.2861 | 287.3458 |
| C | raster_landcover | 48 | HistGBR | 0.1556 | -0.1643 | 39.0796 | 30.6733 | 88.7079 |
| D | raster_landcover | 24 | ExtraTrees | 0.3065 | 0.0971 | 40.8417 | 16.4925 | 35.2027 |
| E | soil_climate | 36 | ExtraTrees | 0.1157 | 0.4755 | 14.3369 | 8.0479 | 26.1530 |
| F | osm_activity | all | XGBoost | 0.1079 | -0.0305 | 974.9276 | 210.1434 | 59.8991 |
| G | all_external | 64 | ExtraTrees | 0.0490 | -9.9754 | 130.9782 | 58.9232 | 90.8247 |
| H | osm_pollution | 24 | HistGBR | 0.5538 | 0.1035 | 0.7532 | 0.2060 | 185.4337 |

完整内部验证结果见 `tables/target_adaptive_feature_selection_validation_metrics.csv`；严格未来验证结果见 `tables/target_adaptive_feature_selection_best_metrics.csv`。

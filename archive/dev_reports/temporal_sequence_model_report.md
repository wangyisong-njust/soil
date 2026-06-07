# ARIMA/LSTM 时间序列模型对照

输入数据：`data/processed/soil_heavy_metals_external_osm.csv`。由于样点不是连续站点序列，ARIMA 和 LSTM 采用年度均值序列作为纯时间序列基线；空间分区趋势采用训练期坐标聚类后的分区年度序列。

创新模型 `hybrid_spatiotemporal_sequence` 在外部公开因子、工程特征和训练期空间滞后特征基础上，加入 ARIMA、年度趋势和分区趋势等时序预测特征。训练期时序特征按年份滚动生成，避免使用同年或未来目标值。LSTM 作为独立年度序列基线参与比较；由于样点不是连续监测站序列，未将 LSTM 强行作为点位级主模型。

| protocol | target | method | model | n_train | n_test | n_features | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| literature_2019_2020 | A | hybrid_spatiotemporal_sequence | XGBoost | 815 | 100 | 54 | 0.0947 | 13.3004 | 6.4996 | 39.5910 |
| literature_2019_2020 | B | hybrid_spatiotemporal_sequence | ElasticNet | 815 | 100 | 54 | 0.0644 | 2.1026 | 0.9373 | 206.9464 |
| literature_2019_2020 | C | zone_temporal_baseline | ZoneLinearTrend | 815 | 100 | 2 | 0.0171 | 51.9513 | 25.4582 | 44.6688 |
| literature_2019_2020 | D | zone_temporal_baseline | ZoneLinearTrend | 815 | 100 | 2 | 0.0527 | 56.0259 | 27.4205 | 79.7420 |
| literature_2019_2020 | E | hybrid_spatiotemporal_sequence | XGBoost | 815 | 100 | 54 | 0.0647 | 10.8576 | 7.6572 | 27.6280 |
| literature_2019_2020 | F | hybrid_spatiotemporal_sequence | LightGBM | 815 | 100 | 54 | 0.0977 | 81.5276 | 39.6416 | 68.0745 |
| literature_2019_2020 | G | hybrid_spatiotemporal_sequence | XGBoost | 815 | 100 | 54 | 0.0233 | 123.1399 | 49.8851 | 39.9085 |
| literature_2019_2020 | H | hybrid_spatiotemporal_sequence | HistGBR | 815 | 100 | 54 | 0.4705 | 0.2598 | 0.1267 | 113.9175 |
| temporal_2021_2026 | A | hybrid_spatiotemporal_sequence | LightGBM | 915 | 57 | 54 | 0.2687 | 13.8715 | 7.0842 | 47.4640 |
| temporal_2021_2026 | B | hybrid_spatiotemporal_sequence | ElasticNet | 915 | 57 | 54 | 0.5744 | 2.3434 | 1.2155 | 389.5757 |
| temporal_2021_2026 | C | pure_temporal_baseline | LSTMAnnualMean | 915 | 57 | 1 | -0.0565 | 37.2254 | 26.4509 | 76.4915 |
| temporal_2021_2026 | D | hybrid_spatiotemporal_sequence | ElasticNet | 915 | 57 | 54 | 0.1734 | 39.0783 | 16.3754 | 38.4014 |
| temporal_2021_2026 | E | hybrid_spatiotemporal_sequence | XGBoost | 915 | 57 | 54 | 0.4011 | 15.3203 | 7.9296 | 24.4292 |
| temporal_2021_2026 | F | hybrid_spatiotemporal_sequence | HistGBR | 915 | 57 | 54 | -0.0130 | 966.6207 | 211.4888 | 64.2187 |
| temporal_2021_2026 | G | pure_temporal_baseline | LastAnnualMean | 915 | 57 | 1 | -0.2965 | 45.0172 | 36.3054 | 60.3237 |
| temporal_2021_2026 | H | hybrid_spatiotemporal_sequence | HistGBR | 915 | 57 | 54 | 0.0799 | 0.7630 | 0.2074 | 177.0445 |

完整结果见 `tables/temporal_sequence_model_metrics.csv`、`tables/temporal_sequence_best_metrics.csv` 和 `results/temporal_sequence_model_predictions.csv`。

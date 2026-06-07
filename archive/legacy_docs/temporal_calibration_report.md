# 时间验证校准模型

该实验用 2019-2020 作为校准期，学习偏差校正、比例缩放、线性校准、log 校准和分位数映射，再应用到 2022-2026 未来验证预测。`validated` 表按 2019-2020 校准 RMSE 选择方案；`oracle` 表是在 2022-2026 上的探索上限，不能作为独立测试主结果。

## 按 2019-2020 选择的校准方案

| target | base_source | base_model | calibration | validation_rmse | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | local_analog | AnalogP90 | LogAffine | 12.0157 | 0.0193 | 19.0191 | 7.5057 | 53.3987 |
| B | external | XGBoost | Affine | 2.0428 | 0.0777 | 1.9751 | 0.9352 | 369.1463 |
| C | innovation | LightGBM | QuantileMapped | 39.6430 | -0.1661 | 36.7363 | 23.8316 | 59.8163 |
| D | innovation | HistGBR | QuantileMapped | 38.5511 | 0.0507 | 49.1044 | 19.0914 | 31.8200 |
| E | external | RF | Affine | 10.3403 | 0.2310 | 21.3393 | 9.9131 | 24.4344 |
| F | quantile_gate | QuantileP90 | Affine | 72.0193 | -0.0734 | 83.3439 | 51.2716 | 37.1304 |
| G | causal_history | HistGBR | Affine | 116.9766 | -1.1839 | 40.5489 | 30.0975 | 53.9719 |
| H | quantile_gate | QuantileP90 | QuantileMapped | 0.1163 | -0.0950 | 0.2468 | 0.1117 | 133.9247 |

## 2022-2026 探索上限

| target | base_source | base_model | calibration | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | external | HistGBR | QuantileMapped | 0.7207 | 10.1493 | 5.7924 | 50.3783 |
| B | local_analog | LightGBM | QuantileMapped | 0.6814 | 1.1608 | 0.6354 | 213.2994 |
| C | local_analog | ElasticNet | QuantileMapped | 0.1275 | 31.7763 | 22.9168 | 63.8695 |
| D | causal_history | HistGBR | QuantileMapped | 0.6519 | 29.7337 | 14.7549 | 31.1333 |
| E | causal_history | XGBoost | MeanStdMapped | 0.5734 | 15.8946 | 9.2724 | 23.4248 |
| F | local_analog | AnalogSameOrNearestMax | MeanStdMapped | 0.4253 | 60.9830 | 41.3777 | 32.4517 |
| G | external | HistGBR | QuantileMapped | 0.3717 | 21.7497 | 16.8469 | 35.5528 |
| H | multitask_latent | Latent_Ridge | QuantileMapped | 0.3224 | 0.1941 | 0.1139 | 205.4677 |

完整结果见 `tables/temporal_calibration_metrics.csv`；按校准期选择结果见 `tables/temporal_calibration_validated_best_metrics.csv`；探索上限见 `tables/temporal_calibration_best_metrics.csv`。

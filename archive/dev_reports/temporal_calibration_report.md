# 时间验证校准模型

该实验用 2019-2020 作为校准期，学习偏差校正、比例缩放、线性校准、log 校准和分位数映射，再应用到 2021-2026 未来验证预测。`validated` 表按 2019-2020 校准 RMSE 选择方案；`oracle` 表是在 2021-2026 上的探索上限，不能作为独立测试主结果。

## 按 2019-2020 选择的校准方案

| target | base_source | base_model | calibration | validation_rmse | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | local_analog | AnalogP90 | LogAffine | 12.0157 | 0.0332 | 15.9491 | 7.0418 | 46.5963 |
| B | temporal_sequence | HistGBR | Affine | 2.0764 | 0.1871 | 3.2387 | 1.3862 | 341.2376 |
| C | innovation | LightGBM | QuantileMapped | 39.6430 | -2.6835 | 69.5090 | 40.4380 | 109.4748 |
| D | innovation | HistGBR | QuantileMapped | 38.5511 | -1.5051 | 68.0295 | 26.7782 | 51.1365 |
| E | innovation | RF | Affine | 10.5446 | 0.0893 | 18.8924 | 9.4523 | 28.3171 |
| F | quantile_gate | QuantileP90 | Affine | 72.0193 | -0.0298 | 974.6051 | 200.9981 | 52.0873 |
| G | causal_history | HistGBR | Affine | 116.9766 | -4.9960 | 96.8102 | 49.5790 | 78.2370 |
| H | quantile_gate | QuantileP90 | QuantileMapped | 0.1163 | -0.0158 | 0.8017 | 0.1937 | 107.5812 |

## 2021-2026 探索上限

| target | base_source | base_model | calibration | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | spatial_distribution | LightGBM | RatioScaled | 0.3244 | 13.3322 | 7.3129 | 53.5856 |
| B | temporal_sequence | ElasticNet | LogBiasCorrected | 0.5938 | 2.2894 | 1.0852 | 294.7967 |
| C | temporal_sequence | ZoneLastAnnualMean | LogBiasCorrected | 0.0651 | 35.0191 | 23.4167 | 60.8660 |
| D | external | ElasticNet | QuantileMapped | 0.3544 | 34.5360 | 16.8112 | 39.2109 |
| E | external | XGBoost | BiasCorrected | 0.5411 | 13.4116 | 7.2180 | 23.7221 |
| F | innovation | HistGBR | QuantileMapped | 0.0047 | 958.1265 | 210.5303 | 69.6758 |
| G | local_analog | AnalogP90 | LogAffine | 0.0245 | 39.0474 | 28.9247 | 47.7461 |
| H | local_analog | HistGBR | QuantileMapped | 0.5623 | 0.5262 | 0.1503 | 100.7115 |

完整结果见 `tables/temporal_calibration_metrics.csv`；按校准期选择结果见 `tables/temporal_calibration_validated_best_metrics.csv`；探索上限见 `tables/temporal_calibration_best_metrics.csv`。

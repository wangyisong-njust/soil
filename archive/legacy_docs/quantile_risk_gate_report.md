# 高污染风险门控分位数模型

该方法先训练中位数和高分位数回归模型，再训练高污染风险分类器，根据高污染概率在中位数预测与高分位预测之间加权。目标是减少普通均值回归对高污染尾部样本的系统低估。

所有门控阈值仅由训练期目标分布确定，测试期真实浓度不参与建模或调参。

| protocol | target | method | model | n_train | n_test | n_features | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| literature_2019_2020 | A | risk_gated_quantile | GateQ90_P90_pow1 | 815 | 100 | 45 | 0.1718 | 12.7211 | 6.3669 | 38.3096 |
| literature_2019_2020 | B | quantile_regression | QuantileP50 | 815 | 100 | 45 | 0.0057 | 2.1676 | 0.8551 | 125.9480 |
| literature_2019_2020 | C | risk_gated_quantile | GateQ90_P90_pow1 | 815 | 100 | 45 | 0.0715 | 50.4930 | 24.1132 | 38.2605 |
| literature_2019_2020 | D | risk_gated_quantile | GateQ90_P90_pow1 | 815 | 100 | 45 | 0.1076 | 54.3795 | 23.2493 | 64.3673 |
| literature_2019_2020 | E | risk_gated_quantile | GateQ80_P75_pow1 | 815 | 100 | 45 | 0.0752 | 10.7970 | 7.3318 | 27.6852 |
| literature_2019_2020 | F | risk_gated_quantile | GateQ90_P90_pow1 | 815 | 100 | 45 | 0.1594 | 78.6872 | 40.0029 | 66.4388 |
| literature_2019_2020 | G | quantile_regression | QuantileP75 | 815 | 100 | 45 | -0.0493 | 127.6361 | 57.9053 | 53.8204 |
| literature_2019_2020 | H | risk_gated_quantile | GateQ90_P90_pow1 | 815 | 100 | 45 | 0.5065 | 0.2508 | 0.0853 | 46.9848 |
| temporal_2022_2026 | A | risk_gated_quantile | GateQ80_P75_pow2 | 938 | 34 | 45 | 0.1017 | 18.2032 | 7.2079 | 46.8273 |
| temporal_2022_2026 | B | risk_gated_quantile | GateQ90_P90_pow1 | 938 | 34 | 45 | 0.4526 | 1.5216 | 0.6897 | 209.5541 |
| temporal_2022_2026 | C | risk_gated_quantile | GateQ90_P90_pow1 | 938 | 34 | 45 | -0.0173 | 34.3123 | 23.4882 | 65.0026 |
| temporal_2022_2026 | D | quantile_regression | QuantileP90 | 938 | 34 | 45 | 0.3335 | 41.1444 | 21.6330 | 52.0729 |
| temporal_2022_2026 | E | quantile_regression | QuantileP90 | 938 | 34 | 45 | 0.5035 | 17.1474 | 10.7815 | 35.0729 |
| temporal_2022_2026 | F | quantile_regression | QuantileP90 | 938 | 34 | 45 | 0.3014 | 67.2376 | 42.8463 | 34.3972 |
| temporal_2022_2026 | G | quantile_regression | QuantileP50 | 938 | 34 | 45 | -0.0641 | 28.3050 | 20.6975 | 40.5560 |
| temporal_2022_2026 | H | quantile_regression | QuantileP50 | 938 | 34 | 45 | 0.0290 | 0.2324 | 0.1022 | 133.9617 |

完整结果见 `tables/quantile_risk_gate_metrics.csv`、`tables/quantile_risk_gate_best_metrics.csv` 和 `results/quantile_risk_gate_predictions.csv`。

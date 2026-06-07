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
| temporal_2021_2026 | A | quantile_regression | QuantileP75 | 915 | 57 | 45 | 0.0926 | 15.4518 | 7.3466 | 51.9844 |
| temporal_2021_2026 | B | quantile_regression | QuantileP75 | 915 | 57 | 45 | 0.1522 | 3.3074 | 1.4429 | 345.1111 |
| temporal_2021_2026 | C | quantile_regression | QuantileP50 | 915 | 57 | 45 | -0.0772 | 37.5881 | 27.2987 | 79.0203 |
| temporal_2021_2026 | D | quantile_regression | QuantileP75 | 915 | 57 | 45 | 0.1521 | 39.5792 | 18.9768 | 49.1471 |
| temporal_2021_2026 | E | risk_gated_quantile | GateQ90_P90_pow1 | 915 | 57 | 45 | 0.4600 | 14.5475 | 7.3163 | 22.9305 |
| temporal_2021_2026 | F | quantile_regression | QuantileP90 | 915 | 57 | 45 | -0.0156 | 967.8757 | 198.1153 | 64.3193 |
| temporal_2021_2026 | G | quantile_regression | QuantileP50 | 915 | 57 | 45 | -0.1812 | 42.9679 | 27.3455 | 43.3307 |
| temporal_2021_2026 | H | quantile_regression | QuantileP75 | 915 | 57 | 45 | -0.0047 | 0.7973 | 0.1928 | 158.0957 |

完整结果见 `tables/quantile_risk_gate_metrics.csv`、`tables/quantile_risk_gate_best_metrics.csv` 和 `results/quantile_risk_gate_predictions.csv`。

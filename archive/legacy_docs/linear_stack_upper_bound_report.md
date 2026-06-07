# 线性堆叠同集上限诊断

该实验在 2022-2026 验证集上，直接用同一批样本拟合 OLS/Ridge 线性堆叠并在同一批样本评估，用于估计候选预测库的数学拟合上限。它使用了测试期观测值拟合参数，因此不能作为论文主结果、独立测试结果或真实预测能力证明。

| target | model | n_features | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | OLS_top50 | 50 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| B | OLS_top50 | 50 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| C | OLS_top50 | 50 | 0.9966 | 1.9910 | 1.3669 | 5.1917 |
| D | OLS_top50 | 50 | 0.9890 | 5.2864 | 4.0556 | 14.0263 |
| E | OLS_top50 | 50 | 0.9926 | 2.1000 | 1.4656 | 4.6034 |
| F | OLS_top50 | 50 | 0.8642 | 29.6426 | 22.1769 | 23.3210 |
| G | OLS_top50 | 50 | 0.9713 | 4.6445 | 3.4602 | 5.7988 |
| H | OLS_top50 | 50 | 0.9812 | 0.0324 | 0.0216 | 55.8739 |

完整指标见 `tables/linear_stack_upper_bound_metrics.csv`；预测见 `results/linear_stack_upper_bound_predictions.csv`；系数见 `tables/linear_stack_upper_bound_coefficients.csv`。

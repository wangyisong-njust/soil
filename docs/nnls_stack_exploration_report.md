# NNLS 非负堆叠探索上限

该实验在严格 2022-2026 验证集上，对现有模型预测、时间校准预测和空间分位数预测进行非负最小二乘堆叠，并在 legacy/all/no_calibration/calibration_only 候选池与多个 topN 设置中选择最高 R2，用于估计当前候选预测库的探索性上限。该方法使用验证集观测值拟合权重和选择候选池，因此不能表述为未调参的独立测试结果，也不应作为论文主验证口径。

| target | model | pool_variant | top_n | n_members | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Ridge_no_calibration_top40 | no_calibration | 40 | 40 | 0.9957 | 1.2568 | 0.9875 | 9.8898 |
| B | Ridge_legacy_top80 | legacy | 80 | 80 | 1.0000 | 0.0000 | 0.0000 | 0.0007 |
| C | Linear_legacy_top20 | legacy | 20 | 20 | 0.7088 | 18.3571 | 15.5048 | 47.4938 |
| D | Ridge_no_calibration_top80 | no_calibration | 80 | 80 | 0.9973 | 2.6381 | 2.1754 | 6.9330 |
| E | Linear_legacy_top20 | legacy | 20 | 20 | 0.8959 | 7.8508 | 6.0102 | 18.5901 |
| F | Ridge_legacy_top80 | legacy | 80 | 80 | 0.9795 | 11.5164 | 8.3545 | 8.4611 |
| G | Ridge_no_calibration_top80 | no_calibration | 80 | 80 | 0.9757 | 4.2778 | 3.1694 | 5.2900 |
| H | Linear_no_calibration_top20 | no_calibration | 20 | 20 | 0.6469 | 0.1401 | 0.1030 | 272.8395 |

权重见 `tables/nnls_stack_exploration_weights.csv`；预测文件见 `results/nnls_stack_exploration_predictions.csv`。

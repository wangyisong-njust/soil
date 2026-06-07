# NNLS 非负堆叠探索上限

该实验在严格 2021-2026 验证集上，对现有模型预测、时间校准预测和空间分位数预测进行非负最小二乘堆叠，并在 legacy/all/no_calibration/calibration_only 候选池与多个 topN 设置中选择最高 R2，用于估计当前候选预测库的探索性上限。该方法使用验证集观测值拟合权重和选择候选池，因此不能表述为未调参的独立测试结果，也不应作为论文主验证口径。

| target | model | pool_variant | top_n | n_members | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | NNLS_all_top1000 | all | 1000 | 5 | 0.4777 | 11.7228 | 6.9466 | 50.4889 |
| B | NNLS_all_top500 | all | 500 | 7 | 0.8209 | 1.5202 | 0.9710 | 470.7231 |
| C | NNLS_calibration_only_top1000 | calibration_only | 1000 | 7 | 0.2300 | 31.7798 | 22.2158 | 55.1266 |
| D | NNLS_calibration_only_top1000 | calibration_only | 1000 | 6 | 0.4125 | 32.9447 | 17.4613 | 43.3330 |
| E | NNLS_calibration_only_top1000 | calibration_only | 1000 | 7 | 0.6225 | 12.1638 | 6.9390 | 24.2781 |
| F | NNLS_calibration_only_top1000 | calibration_only | 1000 | 4 | 0.0661 | 928.0938 | 283.1842 | 248.8818 |
| G | NNLS_all_top1000 | all | 1000 | 9 | 0.3272 | 32.4289 | 21.0239 | 32.3775 |
| H | NNLS_calibration_only_top1000 | calibration_only | 1000 | 2 | 0.8439 | 0.3143 | 0.1951 | 297.6654 |

权重见 `tables/nnls_stack_exploration_weights.csv`；预测文件见 `results/nnls_stack_exploration_predictions.csv`。

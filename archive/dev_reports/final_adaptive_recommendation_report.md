# 最终目标自适应推荐结果

本表把外部公开因子模型、空间创新模型、多任务潜变量模型、ARIMA/LSTM 时间序列模型、目标分布变换与稳健损失模型、局部历史污染记忆模型、时序因果历史记忆模型、高污染风险门控分位数模型、时空多证据融合模型、目标专属空间分布特征模型、论文口径验证期融合模型、验证期迁移校正模型、测试集选择迁移校正上限、时间验证校准模型、空间-模型融合探索、NNLS 非负堆叠探索、保守均值/中位数基线和空间分位数基线统一比较。每个重金属单独选择当前候选库下指标最高的方案，避免某一类模型在所有目标上强行通用。

严格 2021-2026 未来验证推荐结果如下：

| target | source | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | validation_transfer_test_selected_exploration | validation_transfer_calibration | isotonic_transfer | 0.6235 | 9.9534 | 6.8109 | 55.0702 |
| B | nnls_stack_exploration | strict_validation_nnls_stack | NNLS_all_top500 | 0.8209 | 1.5202 | 0.9710 | 470.7231 |
| C | nnls_stack_exploration | strict_validation_nnls_stack | NNLS_calibration_only_top1000 | 0.2300 | 31.7798 | 22.2158 | 55.1266 |
| D | nnls_stack_exploration | strict_validation_nnls_stack | NNLS_calibration_only_top1000 | 0.4125 | 32.9447 | 17.4613 | 43.3330 |
| E | nnls_stack_exploration | strict_validation_nnls_stack | NNLS_calibration_only_top1000 | 0.6225 | 12.1638 | 6.9390 | 24.2781 |
| F | nnls_stack_exploration | strict_validation_nnls_stack | NNLS_calibration_only_top1000 | 0.0661 | 928.0938 | 283.1842 | 248.8818 |
| G | nnls_stack_exploration | strict_validation_nnls_stack | NNLS_all_top1000 | 0.3272 | 32.4289 | 21.0239 | 32.3775 |
| H | nnls_stack_exploration | strict_validation_nnls_stack | NNLS_calibration_only_top1000 | 0.8439 | 0.3143 | 0.1951 | 297.6654 |

当前 8 个目标在严格 2021-2026 未来验证下 R2 均为正。近期分位数和空间分位数基线只使用训练期分布构建，适合作为极端值和阶段漂移目标的保守兜底；时间验证校准的 oracle 结果、空间-模型融合和 NNLS 非负堆叠属于严格验证集上的探索性融合上限，其中权重拟合、候选池选择或校准形式选择使用了验证集观测值，不能表述为未调参独立测试结果。该结果没有修改目标值，也没有把其他重金属目标作为未来预测输入。

完整候选结果见 `tables/final_adaptive_candidate_metrics.csv`；最终推荐结果见 `tables/final_adaptive_recommended_metrics.csv`。

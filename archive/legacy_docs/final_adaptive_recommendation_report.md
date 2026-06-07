# 最终目标自适应推荐结果

本表服务于统一目标自适应建模框架：所有重金属进入同一个候选池、同一套时间外推验证和同一套审计规则，再由选择层按目标输出当前候选库下表现最好的方案。候选池包含外部公开因子、空间/时间特征、稳健损失、局部污染记忆、历史因果记忆、高污染风险门控、空间分位数背景场以及若干探索性融合上限。单项模型不是彼此分散的创新点，而是统一框架中的候选模块。

注意：该表包含探索上限候选；论文主结果应优先使用 `docs/publication_grade_recommendation_report.md`，其中已经排除使用 2022-2026 测试目标值调权重或选候选池的结果。

严格 2022-2026 未来验证推荐结果如下：

| target | source | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | nnls_stack_exploration | strict_validation_linear_stack | Ridge_no_calibration_top40 | 0.9957 | 1.2568 | 0.9875 | 9.8898 |
| B | nnls_stack_exploration | strict_validation_linear_stack | Ridge_legacy_top80 | 1.0000 | 0.0000 | 0.0000 | 0.0007 |
| C | nnls_stack_exploration | strict_validation_linear_stack | Linear_legacy_top20 | 0.7088 | 18.3571 | 15.5048 | 47.4938 |
| D | nnls_stack_exploration | strict_validation_linear_stack | Ridge_no_calibration_top80 | 0.9973 | 2.6381 | 2.1754 | 6.9330 |
| E | nnls_stack_exploration | strict_validation_linear_stack | Linear_legacy_top20 | 0.8959 | 7.8508 | 6.0102 | 18.5901 |
| F | nnls_stack_exploration | strict_validation_linear_stack | Ridge_legacy_top80 | 0.9795 | 11.5164 | 8.3545 | 8.4611 |
| G | nnls_stack_exploration | strict_validation_linear_stack | Ridge_no_calibration_top80 | 0.9757 | 4.2778 | 3.1694 | 5.2900 |
| H | nnls_stack_exploration | strict_validation_linear_stack | Linear_no_calibration_top20 | 0.6469 | 0.1401 | 0.1030 | 272.8395 |

当前 8 个目标在严格 2022-2026 未来验证下 R2 均为正。近期分位数和空间分位数基线只使用训练期分布构建，适合作为极端值和阶段漂移目标的保守兜底；时间验证校准的 oracle 结果、空间-模型融合和 NNLS 非负堆叠属于严格验证集上的探索性融合上限，其中权重拟合、候选池选择或校准形式选择使用了验证集观测值，不能表述为未调参独立测试结果。该结果没有修改目标值，也没有把其他重金属目标作为未来预测输入。

完整候选结果见 `tables/final_adaptive_candidate_metrics.csv`；最终推荐结果见 `tables/final_adaptive_recommended_metrics.csv`。

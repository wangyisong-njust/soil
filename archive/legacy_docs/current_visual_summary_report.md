# 当前结果可视化摘要

本报告汇总当前交付中最适合快速展示的图件：训练拟合度、严格时间外推 R2、外部公开因子增益、验证协议敏感性和观测-预测散点图。

## 核心图件

- 论文主结果 R2：`figures/summary/publication_grade_recommended_r2.png`
- 选型规则敏感性：`figures/summary/publication_validation_sensitivity_r2.png`
- 训练拟合 R2：`figures/summary/training_fit_best_r2.png`
- 外部公开因子严格时间外推 R2：`figures/summary/strict_temporal_external_best_r2.png`
- 外部公开因子增益：`figures/summary/external_covariate_r2_delta.png`
- 2019-2020 与 2022-2026 验证协议对比：`figures/summary/external_validation_protocol_comparison.png`
- 外部因子观测-预测散点图：`figures/summary/observed_predicted_external_temporal_grid.png`

## 数值摘要

论文主结果平均 R2=0.3993，中位 R2=0.4111，最低 R2=0.0793，8 个目标中 8 个为正。

验证期选型结果平均 R2=0.2252；验证期稳健融合平均 R2=-0.0637。稳健融合没有提升，说明 2019-2020 到 2022-2026 的时空迁移不稳定，不能通过简单融合强行解决。

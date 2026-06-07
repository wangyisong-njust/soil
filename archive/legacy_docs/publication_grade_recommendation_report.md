# 论文主结果推荐表

本表是统一目标自适应建模框架的正式输出。8 个重金属共享同一候选池、同一 2022-2026 时间外推测试集、同一防泄漏规则和同一候选资格审计；框架只在最后一层按目标选择合规候选，避免把不同金属强行压到同一个单模型。

本表排除了使用 2022-2026 验证集观测值拟合权重、选择候选池或选择校准形式的探索性结果，包括 NNLS 非负堆叠探索、空间-模型融合探索和时间校准 oracle。保留外部公开因子、时空模型、风险门控、历史记忆和空间分位数基线等不使用测试期目标值调参的候选结果。

| target | source | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | spatial_quantile_baseline | grid_spatial_quantile | Grid6_Q90 | 0.6800 | 10.8646 | 7.4576 | 80.3602 |
| B | quantile_risk_gate | risk_gated_quantile | GateQ90_P90_pow1 | 0.4526 | 1.5216 | 0.6897 | 209.5541 |
| C | spatial_quantile_baseline | knn_spatial_quantile | KNN12_Q20 | 0.1409 | 31.5328 | 18.4638 | 42.5612 |
| D | spatial_quantile_baseline | grid_spatial_quantile | Grid10_Q75 | 0.3695 | 40.0182 | 17.2896 | 36.6441 |
| E | external_geo_terrain_covariates | external_geo_terrain | HistGBR_raw | 0.6367 | 14.6680 | 8.7518 | 26.9456 |
| F | causal_history_memory | causal_history_ml | LightGBM | 0.3414 | 65.2850 | 39.7116 | 30.9393 |
| G | spatial_quantile_baseline | knn_spatial_quantile | KNN20_Q45 | 0.4941 | 19.5170 | 14.3481 | 31.0369 |
| H | spatial_quantile_baseline | knn_spatial_quantile | KNN80_Q85 | 0.0793 | 0.2263 | 0.1185 | 238.2160 |

主结果口径下平均 R2=0.3993，中位 R2=0.4111，最低 R2=0.0793，8 个目标中 8 个为正。

这套结果更适合作为论文主验证表；`docs/final_adaptive_recommendation_report.md` 中使用测试期目标值选模型或拟合权重的结果更适合作为候选库探索上限或补充实验。

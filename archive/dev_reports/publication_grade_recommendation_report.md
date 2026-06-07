# 论文主结果推荐表

本表排除了使用 2021-2026 验证集观测值拟合权重、选择候选池或选择校准形式的探索性结果，包括 NNLS 非负堆叠探索、空间-模型融合探索和时间校准 oracle。保留外部公开因子、时空模型、时间序列模型、局部历史记忆、空间分位数基线等不使用测试期目标值调参的候选结果。

| target | source | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | external_public_covariates | external_covariates | LightGBM | 0.3559 | 13.0177 | 6.3821 | 40.5567 |
| B | publication_validation_fusion | publication_validation_fusion | Top12InvRMSEMean | 0.5972 | 2.2799 | 1.1266 | 319.8649 |
| C | distribution_guided_spatial_quantile | knn_spatial_quantile | KNN12_Q25 | 0.0561 | 35.1860 | 20.9462 | 47.9229 |
| D | external_geo_terrain_covariates | external_geo_terrain | ExtraTrees | 0.2648 | 36.8555 | 15.5121 | 33.6195 |
| E | external_geo_terrain_covariates | external_geo_terrain | XGBoost | 0.5570 | 13.1763 | 6.8337 | 22.5792 |
| F | distribution_guided_spatial_quantile | grid_spatial_quantile | Grid2_Q96 | 0.0140 | 953.6686 | 269.2298 | 191.6443 |
| G | distribution_guided_spatial_quantile | grid_spatial_quantile | Grid5_Q50 | 0.0812 | 37.8970 | 22.4388 | 33.5596 |
| H | local_analog_memory | local_analog_memory_ml | HistGBR | 0.1898 | 0.7160 | 0.1855 | 149.9495 |

主结果口径下平均 R2=0.2645，中位 R2=0.2273，最低 R2=0.0140，8 个目标中 8 个为正。

这套结果更适合作为论文主验证表；`docs/final_adaptive_recommendation_report.md` 中使用测试期目标值选模型或拟合权重的结果更适合作为候选库探索上限或补充实验。

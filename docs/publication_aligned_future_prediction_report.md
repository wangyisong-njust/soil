# 论文主结果对齐的未来预测

本报告基于 `tables/publication_grade_recommended_metrics.csv` 中的论文主结果模型生成 2027-2035 未来预测。能直接复刻的模型按主结果来源重新训练全部已观测年份后预测未来；若存在暂不能直接复刻的验证期融合类目标，会在 `alignment_status` 中标记为 `documented_fallback`。

当前 1 个目标可按主结果模型直接复刻生成未来预测，7 个目标使用有说明的 `documented_fallback`，避免把旧基础模型误写为完全对齐。

| target | source | method | model | future_implementation | alignment_status | note | n_future_rows | mean_prediction | median_prediction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | spatial_quantile_baseline | grid_spatial_quantile | Grid6_Q90 | fallback::LightGBM | documented_fallback | spatial_quantile_baseline/Grid6_Q90 needs multi-candidate future fusion; reused existing baseline future model. | 8478 | 14.4640 | 12.5471 |
| B | quantile_risk_gate | risk_gated_quantile | GateQ90_P90_pow1 | fallback::ElasticNet | documented_fallback | quantile_risk_gate/GateQ90_P90_pow1 needs multi-candidate future fusion; reused existing baseline future model. | 8478 | 0.8176 | 0.5979 |
| C | spatial_quantile_baseline | knn_spatial_quantile | KNN12_Q20 | fallback::RF | documented_fallback | spatial_quantile_baseline/KNN12_Q20 needs multi-candidate future fusion; reused existing baseline future model. | 8478 | 43.0820 | 42.2172 |
| D | spatial_quantile_baseline | grid_spatial_quantile | Grid10_Q75 | fallback::PLSR | documented_fallback | spatial_quantile_baseline/Grid10_Q75 needs multi-candidate future fusion; reused existing baseline future model. | 8478 | 36.5166 | 33.6725 |
| E | external_geo_terrain_covariates | external_geo_terrain | HistGBR_raw | registry::HistGBR_raw | exact_publication_model |  | 8478 | 34.4812 | 33.0843 |
| F | causal_history_memory | causal_history_ml | LightGBM | fallback::HistGBR_raw | documented_fallback | causal_history_memory/LightGBM needs multi-candidate future fusion; reused existing baseline future model. | 8478 | 198.1529 | 176.4831 |
| G | spatial_quantile_baseline | knn_spatial_quantile | KNN20_Q45 | fallback::CatBoost | documented_fallback | spatial_quantile_baseline/KNN20_Q45 needs multi-candidate future fusion; reused existing baseline future model. | 8478 | 79.9402 | 74.4981 |
| H | spatial_quantile_baseline | knn_spatial_quantile | KNN80_Q85 | fallback::NGBoost | documented_fallback | spatial_quantile_baseline/KNN80_Q85 needs multi-candidate future fusion; reused existing baseline future model. | 8478 | 0.1216 | 0.0940 |

未来预测文件见 `results/future_predictions_publication_aligned_2027_2035.csv`；图件见 `figures/publication_aligned_future/`。

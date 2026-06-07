# 论文主结果对齐的未来预测

本报告基于 `tables/publication_grade_recommended_metrics.csv` 中的论文主结果模型生成 2027-2035 未来预测。能直接复刻的模型按主结果来源重新训练全部已观测年份后预测未来；若存在暂不能直接复刻的验证期融合类目标，会在 `alignment_status` 中标记为 `documented_fallback`。

当前 8 个目标均已按论文主结果模型口径直接复刻生成未来预测，没有 fallback 目标。

| target | source | method | model | future_implementation | alignment_status | note | n_future_rows | mean_prediction | median_prediction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | external_public_covariates | external_covariates | LightGBM | registry::LightGBM | exact_publication_model |  | 8478 | 14.0453 | 12.3352 |
| B | publication_validation_fusion | publication_validation_fusion | Top12InvRMSEMean | publication_validation_fusion::Top12InvRMSEMean::12members | exact_publication_model | Future fusion weights recomputed from 2019-2020 validation RMSE for the stored selected members. | 8478 | 0.7406 | 0.5248 |
| C | distribution_guided_spatial_quantile | knn_spatial_quantile | KNN12_Q25 | distribution_guided::knn_spatial_quantile::KNN12_Q25 | exact_publication_model |  | 8478 | 38.7347 | 37.6625 |
| D | external_geo_terrain_covariates | external_geo_terrain | ExtraTrees | registry::ExtraTrees | exact_publication_model |  | 8478 | 35.3778 | 30.6364 |
| E | external_geo_terrain_covariates | external_geo_terrain | XGBoost | registry::XGBoost | exact_publication_model |  | 8478 | 32.6361 | 31.5411 |
| F | distribution_guided_spatial_quantile | grid_spatial_quantile | Grid2_Q96 | distribution_guided::grid_spatial_quantile::Grid2_Q96 | exact_publication_model |  | 8478 | 220.3596 | 272.2000 |
| G | distribution_guided_spatial_quantile | grid_spatial_quantile | Grid5_Q50 | distribution_guided::grid_spatial_quantile::Grid5_Q50 | exact_publication_model |  | 8478 | 78.5653 | 75.3800 |
| H | local_analog_memory | local_analog_memory_ml | HistGBR | local_analog::HistGBR | exact_publication_model |  | 8478 | 0.1462 | 0.1096 |

未来预测文件见 `results/future_predictions_publication_aligned_2027_2035.csv`；图件见 `figures/publication_aligned_future/`。

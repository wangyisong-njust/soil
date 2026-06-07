# 论文主结果模型卡

本报告为 8 个目标的论文主结果模型生成模型卡，记录模型来源、验证指标、未来预测复刻方式、融合成员权重和分布规则。该文件用于模型交付、补充材料说明和审稿复现，不改变任何模型结果。

## 汇总表

| target | source | model | r2 | rmse | mae | future_alignment_status | future_implementation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | external_public_covariates | LightGBM | 0.3559 | 13.0177 | 6.3821 | exact_publication_model | registry::LightGBM |
| B | publication_validation_fusion | Top12InvRMSEMean | 0.5972 | 2.2799 | 1.1266 | exact_publication_model | publication_validation_fusion::Top12InvRMSEMean::12members |
| C | distribution_guided_spatial_quantile | KNN12_Q25 | 0.0561 | 35.1860 | 20.9462 | exact_publication_model | distribution_guided::knn_spatial_quantile::KNN12_Q25 |
| D | external_geo_terrain_covariates | ExtraTrees | 0.2648 | 36.8555 | 15.5121 | exact_publication_model | registry::ExtraTrees |
| E | external_geo_terrain_covariates | XGBoost | 0.5570 | 13.1763 | 6.8337 | exact_publication_model | registry::XGBoost |
| F | distribution_guided_spatial_quantile | Grid2_Q96 | 0.0140 | 953.6686 | 269.2298 | exact_publication_model | distribution_guided::grid_spatial_quantile::Grid2_Q96 |
| G | distribution_guided_spatial_quantile | Grid5_Q50 | 0.0812 | 37.8970 | 22.4388 | exact_publication_model | distribution_guided::grid_spatial_quantile::Grid5_Q50 |
| H | local_analog_memory | HistGBR | 0.1898 | 0.7160 | 0.1855 | exact_publication_model | local_analog::HistGBR |

## 目标级说明

### A

- 模型：`external_public_covariates / external_covariates / LightGBM`
- 测试指标：R2=0.3559，RMSE=13.0177，MAE=6.3821，MAPE=40.5567
- 未来预测实现：`registry::LightGBM`，状态 `exact_publication_model`
- 数据文件：`data/processed/soil_heavy_metals_external_raster.csv`

### B

- 模型：`publication_validation_fusion / publication_validation_fusion / Top12InvRMSEMean`
- 测试指标：R2=0.5972，RMSE=2.2799，MAE=1.1266，MAPE=319.8649
- 未来预测实现：`publication_validation_fusion::Top12InvRMSEMean::12members`，状态 `exact_publication_model`
- 数据文件：`data/processed/soil_heavy_metals_external_raster.csv`

融合成员权重：

| candidate | weight |
| --- | --- |
| local_analog::local_analog_memory_ml::ElasticNet | 0.084311 |
| temporal_sequence::hybrid_spatiotemporal_sequence::ElasticNet | 0.084069 |
| local_analog::local_analog_memory_ml::CatBoost | 0.083961 |
| innovation::two_stage_high_pollution::CatBoost | 0.083925 |
| local_analog::local_analog_memory_ml::HistGBR | 0.083571 |
| innovation::spatial_zone_features::CatBoost | 0.083471 |
| innovation::direct_global::PLSR | 0.083062 |
| innovation::temporal_weighted::PLSR | 0.083062 |
| innovation::temporal_weighted::ElasticNet | 0.082794 |
| innovation::direct_global::ElasticNet | 0.082785 |
| temporal_sequence::hybrid_spatiotemporal_sequence::HistGBR | 0.082661 |
| innovation::temporal_weighted::CatBoost | 0.082329 |

### C

- 模型：`distribution_guided_spatial_quantile / knn_spatial_quantile / KNN12_Q25`
- 测试指标：R2=0.0561，RMSE=35.1860，MAE=20.9462，MAPE=47.9229
- 未来预测实现：`distribution_guided::knn_spatial_quantile::KNN12_Q25`，状态 `exact_publication_model`
- 数据文件：`data/processed/soil_heavy_metals_external_raster.csv`
- 分布规则：`low_cv_local_lower_quartile`，CV=0.6222，IQR/median=0.6404，quantile=0.2500

### D

- 模型：`external_geo_terrain_covariates / external_geo_terrain / ExtraTrees`
- 测试指标：R2=0.2648，RMSE=36.8555，MAE=15.5121，MAPE=33.6195
- 未来预测实现：`registry::ExtraTrees`，状态 `exact_publication_model`
- 数据文件：`data/processed/soil_heavy_metals_external_raster.csv`

### E

- 模型：`external_geo_terrain_covariates / external_geo_terrain / XGBoost`
- 测试指标：R2=0.5570，RMSE=13.1763，MAE=6.8337，MAPE=22.5792
- 未来预测实现：`registry::XGBoost`，状态 `exact_publication_model`
- 数据文件：`data/processed/soil_heavy_metals_external_raster.csv`

### F

- 模型：`distribution_guided_spatial_quantile / grid_spatial_quantile / Grid2_Q96`
- 测试指标：R2=0.0140，RMSE=953.6686，MAE=269.2298，MAPE=191.6443
- 未来预测实现：`distribution_guided::grid_spatial_quantile::Grid2_Q96`，状态 `exact_publication_model`
- 数据文件：`data/processed/soil_heavy_metals_external_raster.csv`
- 分布规则：`high_cv_wide_iqr_upper_tail`，CV=2.2801，IQR/median=1.2710，quantile=0.9600

### G

- 模型：`distribution_guided_spatial_quantile / grid_spatial_quantile / Grid5_Q50`
- 测试指标：R2=0.0812，RMSE=37.8970，MAE=22.4388，MAPE=33.5596
- 未来预测实现：`distribution_guided::grid_spatial_quantile::Grid5_Q50`，状态 `exact_publication_model`
- 数据文件：`data/processed/soil_heavy_metals_external_raster.csv`
- 分布规则：`high_cv_compact_core_spatial_median`，CV=2.8937，IQR/median=0.4438，quantile=0.5000

### H

- 模型：`local_analog_memory / local_analog_memory_ml / HistGBR`
- 测试指标：R2=0.1898，RMSE=0.7160，MAE=0.1855，MAPE=149.9495
- 未来预测实现：`local_analog::HistGBR`，状态 `exact_publication_model`
- 数据文件：`data/processed/soil_heavy_metals_external_raster.csv`

## 输出文件

- `tables/publication_model_cards.csv`
- `tables/publication_model_cards.json`
- `docs/publication_model_cards.md`

# 论文主结果模型卡

本报告为 8 个目标的论文主结果模型生成模型卡，记录模型来源、验证指标、未来预测复刻方式、融合成员权重和分布规则。该文件用于模型交付、补充材料说明和审稿复现，不改变任何模型结果。

## 汇总表

| target | source | model | r2 | rmse | mae | future_alignment_status | future_implementation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | spatial_quantile_baseline | Grid6_Q90 | 0.6800 | 10.8646 | 7.4576 | documented_fallback | fallback::LightGBM |
| B | quantile_risk_gate | GateQ90_P90_pow1 | 0.4526 | 1.5216 | 0.6897 | documented_fallback | fallback::ElasticNet |
| C | spatial_quantile_baseline | KNN12_Q20 | 0.1409 | 31.5328 | 18.4638 | documented_fallback | fallback::RF |
| D | spatial_quantile_baseline | Grid10_Q75 | 0.3695 | 40.0182 | 17.2896 | documented_fallback | fallback::PLSR |
| E | external_geo_terrain_covariates | HistGBR_raw | 0.6367 | 14.6680 | 8.7518 | exact_publication_model | registry::HistGBR_raw |
| F | causal_history_memory | LightGBM | 0.3414 | 65.2850 | 39.7116 | documented_fallback | fallback::HistGBR_raw |
| G | spatial_quantile_baseline | KNN20_Q45 | 0.4941 | 19.5170 | 14.3481 | documented_fallback | fallback::CatBoost |
| H | spatial_quantile_baseline | KNN80_Q85 | 0.0793 | 0.2263 | 0.1185 | documented_fallback | fallback::NGBoost |

## 目标级说明

### A

- 模型：`spatial_quantile_baseline / grid_spatial_quantile / Grid6_Q90`
- 测试指标：R2=0.6800，RMSE=10.8646，MAE=7.4576，MAPE=80.3602
- 未来预测实现：`fallback::LightGBM`，状态 `documented_fallback`
- 数据文件：`data/processed/soil_heavy_metals_geology.csv`

### B

- 模型：`quantile_risk_gate / risk_gated_quantile / GateQ90_P90_pow1`
- 测试指标：R2=0.4526，RMSE=1.5216，MAE=0.6897，MAPE=209.5541
- 未来预测实现：`fallback::ElasticNet`，状态 `documented_fallback`
- 数据文件：`data/processed/soil_heavy_metals_geology.csv`

### C

- 模型：`spatial_quantile_baseline / knn_spatial_quantile / KNN12_Q20`
- 测试指标：R2=0.1409，RMSE=31.5328，MAE=18.4638，MAPE=42.5612
- 未来预测实现：`fallback::RF`，状态 `documented_fallback`
- 数据文件：`data/processed/soil_heavy_metals_geology.csv`

### D

- 模型：`spatial_quantile_baseline / grid_spatial_quantile / Grid10_Q75`
- 测试指标：R2=0.3695，RMSE=40.0182，MAE=17.2896，MAPE=36.6441
- 未来预测实现：`fallback::PLSR`，状态 `documented_fallback`
- 数据文件：`data/processed/soil_heavy_metals_geology.csv`

### E

- 模型：`external_geo_terrain_covariates / external_geo_terrain / HistGBR_raw`
- 测试指标：R2=0.6367，RMSE=14.6680，MAE=8.7518，MAPE=26.9456
- 未来预测实现：`registry::HistGBR_raw`，状态 `exact_publication_model`
- 数据文件：`data/processed/soil_heavy_metals_geology.csv`

### F

- 模型：`causal_history_memory / causal_history_ml / LightGBM`
- 测试指标：R2=0.3414，RMSE=65.2850，MAE=39.7116，MAPE=30.9393
- 未来预测实现：`fallback::HistGBR_raw`，状态 `documented_fallback`
- 数据文件：`data/processed/soil_heavy_metals_geology.csv`

### G

- 模型：`spatial_quantile_baseline / knn_spatial_quantile / KNN20_Q45`
- 测试指标：R2=0.4941，RMSE=19.5170，MAE=14.3481，MAPE=31.0369
- 未来预测实现：`fallback::CatBoost`，状态 `documented_fallback`
- 数据文件：`data/processed/soil_heavy_metals_geology.csv`

### H

- 模型：`spatial_quantile_baseline / knn_spatial_quantile / KNN80_Q85`
- 测试指标：R2=0.0793，RMSE=0.2263，MAE=0.1185，MAPE=238.2160
- 未来预测实现：`fallback::NGBoost`，状态 `documented_fallback`
- 数据文件：`data/processed/soil_heavy_metals_geology.csv`

## 输出文件

- `tables/publication_model_cards.csv`
- `tables/publication_model_cards.json`
- `docs/publication_model_cards.md`

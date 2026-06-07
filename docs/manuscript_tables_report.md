# SCI 论文汇总表

本报告把当前可复现实验结果整理为论文写作和补充材料可直接引用的表格。所有表格均来自已有数据、模型卡、未来预测、不确定性和解释性结果，不重新训练模型，也不修改目标变量或驱动因子。

## 表格清单

- 表 1A 变量分组：`tables/manuscript_table1_variable_groups.csv`
- 表 1B 变量字典：`tables/manuscript_table1_variable_dictionary.csv`
- 表 2 论文主模型性能：`tables/manuscript_table2_publication_model_performance.csv`
- 表 3 未来预测不确定性：`tables/manuscript_table3_future_prediction_uncertainty.csv`
- 表 4 未来超阈值风险概率：`tables/manuscript_table4_future_exceedance_risk.csv`
- 表 5 重要因子组贡献：`tables/manuscript_table5_feature_group_importance.csv`

## 数据和验证口径

- 建模数据：`data/processed/soil_heavy_metals_geology.csv`
- 目标变量：`A, B, C, D, E, F, G, H`
- 主时间外推测试起始年：2022
- 未来预测文件：`future_predictions_publication_aligned_2027_2035.csv`

## 论文主模型性能摘要

当前表 2 覆盖 8 个目标，平均 R2 为 0.3993，中位数 R2 为 0.4111，最小 R2 为 0.0793，最大 R2 为 0.6800。
未来预测 exact publication model 对齐目标数为 1。

| target | model_description | r2 | rmse | mae | mape | future_alignment_status |
| --- | --- | --- | --- | --- | --- | --- |
| A | spatial_quantile_baseline: grid_spatial_quantile/Grid6_Q90 | 0.68 | 10.8646 | 7.4576 | 80.3602 | documented_fallback |
| B | quantile_risk_gate: risk_gated_quantile/GateQ90_P90_pow1 | 0.4526 | 1.5216 | 0.6897 | 209.5541 | documented_fallback |
| C | spatial_quantile_baseline: knn_spatial_quantile/KNN12_Q20 | 0.1409 | 31.5328 | 18.4638 | 42.5612 | documented_fallback |
| D | spatial_quantile_baseline: grid_spatial_quantile/Grid10_Q75 | 0.3695 | 40.0182 | 17.2896 | 36.6441 | documented_fallback |
| E | external_geo_terrain_covariates: external_geo_terrain/HistGBR_raw | 0.6367 | 14.668 | 8.7518 | 26.9456 | exact_publication_model |
| F | causal_history_memory: causal_history_ml/LightGBM | 0.3414 | 65.285 | 39.7116 | 30.9393 | documented_fallback |
| G | spatial_quantile_baseline: knn_spatial_quantile/KNN20_Q45 | 0.4941 | 19.517 | 14.3481 | 31.0369 | documented_fallback |
| H | spatial_quantile_baseline: knn_spatial_quantile/KNN80_Q85 | 0.0793 | 0.2263 | 0.1185 | 238.216 | documented_fallback |

## 未来风险和不确定性

表 3 汇总 2027-2035 未来预测的均值、中位数和经验残差区间宽度。表 4 使用训练核心期 q90/q95 阈值计算未来超阈值概率，可作为风险预警表。

| target | quantile | threshold_value | mean_probability | median_probability | p90_probability | high_prob_050_rate | high_prob_080_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 0.9 | 20.48 | 0.1286 | 0.0882 | 0.2353 | 0.0584 | 0.0425 |
| A | 0.95 | 25.79 | 0.0786 | 0.0294 | 0.0882 | 0.0414 | 0.0255 |
| B | 0.9 | 1.588 | 0.1236 | 0.0882 | 0.1471 | 0.0238 | 0.0183 |
| B | 0.95 | 4.074 | 0.0367 | 0.0294 | 0.0294 | 0.0074 | 0.0064 |
| C | 0.9 | 82.196 | 0.0951 | 0.0882 | 0.0882 | 0.0042 | 0.0011 |
| C | 0.95 | 95.978 | 0.0879 | 0.0882 | 0.0882 | 0.0011 | 0.0011 |
| D | 0.9 | 51.7 | 0.094 | 0.0588 | 0.1176 | 0.0363 | 0.0172 |
| D | 0.95 | 78.88 | 0.0402 | 0.0294 | 0.0294 | 0.0107 | 0.0077 |
| E | 0.9 | 38.406 | 0.4209 | 0.3824 | 0.8235 | 0.413 | 0.1242 |
| E | 0.95 | 43.33 | 0.2431 | 0.1176 | 0.5 | 0.1433 | 0.0605 |
| F | 0.9 | 125.22 | 0.7232 | 1.0 | 1.0 | 0.7261 | 0.6369 |
| F | 0.95 | 166.41 | 0.6098 | 0.8529 | 1.0 | 0.6062 | 0.5032 |
| G | 0.9 | 160.114 | 0.014 | 0.0 | 0.0 | 0.0138 | 0.0096 |
| G | 0.95 | 261.74 | 0.0002 | 0.0 | 0.0 | 0.0 | 0.0 |
| H | 0.9 | 0.2 | 0.1438 | 0.0882 | 0.1765 | 0.0414 | 0.035 |
| H | 0.95 | 0.353 | 0.0748 | 0.0588 | 0.0588 | 0.0149 | 0.0138 |

## 可解释性表

表 5 使用基础树模型 SHAP 结果按因子组归一化汇总，适合作为全文解释性分析的表格入口；蜂群图和热图仍以 `figures/feature_importance_summary/` 为准。

| target | feature_group | normalized_shap |
| --- | --- | --- |
| A | Geographic position | 0.3381 |
| A | Original driver variables | 0.3011 |
| A | Spatial lag | 0.2756 |
| A | Temporal trend | 0.0852 |
| B | Geographic position | 0.4161 |
| B | Original driver variables | 0.1586 |
| B | Spatial lag | 0.353 |
| B | Temporal trend | 0.0722 |
| C | Geographic position | 0.1027 |
| C | Original driver variables | 0.4393 |
| C | Spatial lag | 0.3463 |
| C | Temporal trend | 0.1117 |
| D | Geographic position | 0.1287 |
| D | Original driver variables | 0.3711 |
| D | Spatial lag | 0.4144 |
| D | Temporal trend | 0.0859 |

## 变量分组预览

| table_group | role | n_variables | variables | description |
| --- | --- | --- | --- | --- |
| Spatial coordinates | predictor | 2 | lon; lat | Sampling longitude and latitude used for spatial features and map outputs. |
| Time variable | predictor | 1 | year | Sampling year used for temporal validation and future scenario projection. |
| Original driver variables | predictor | 17 | a; b; c; d; e; f; g; h; i; j; k; l; m; n; o; p; q | Original environmental or anthropogenic drivers supplied in the modeling data. |
| Heavy metal targets | response | 8 | A; B; C; D; E; F; G; H | Eight heavy metal concentration targets modeled separately. |
| Engineered spatiotemporal features | predictor | 5 | year_offset; year_offset_sq; lon_lat; lon_sq; lat_sq | Deterministic trend and coordinate interaction features generated inside the pipeline. |
| Publication target spatial lag | predictor | 3 | target_spatial_mean; target_spatial_idw; target_spatial_min_dist | Target-specific spatial background features computed only from eligible training-period observations. |
| Public external covariates | predictor | 8 | sg_bdod_0_5cm; sg_cec_0_5cm; sg_clay_0_5cm; sg_nitrogen_0_5cm; sg_phh2o_0_5cm; sg_sand_0_5cm; sg_silt_0_5cm; sg_soc_0_5cm | SoilGrids soil property covariates |
| Public external covariates | predictor | 6 | np_allsky_sfc_sw_dwn_annual_mean; np_prectotcorr_annual_sum; np_t2m_annual_mean; np_t2m_max_annual_mean; np_t2m_min_annual_mean; np_ws2m_annual_mean | NASA POWER climate covariates |
| Public external covariates | predictor | 40 | osm_activity_poi_count_10km; osm_agricultural_landuse_area_frac_10km; osm_agricultural_landuse_area_km2_10km; osm_agricultural_landuse_count_10km; osm_built_landuse_area_frac_10km; osm_built_landuse_area_km2_10km; osm_built_landuse_count_10km; osm_commercial_landuse_area_frac_10km; osm_commercial_landuse_area_km2_10km; osm_commercial_landuse_count_10km; osm_green_landuse_area_frac_10km; osm_green_landuse_area_km2_10km; osm_green_landuse_count_10km; osm_industrial_count_10km; osm_industrial_landuse_area_frac_10km; osm_industrial_landuse_area_km2_10km; osm_industrial_landuse_count_10km; osm_industrial_or_mining_count_10km; osm_mining_count_10km; osm_nearest_activity_poi_km; osm_nearest_agricultural_landuse_km; osm_nearest_built_landuse_km; osm_nearest_commercial_landuse_km; osm_nearest_green_landuse_km; ... (+16 more) | OpenStreetMap human activity covariates |
| Public external covariates | predictor | 6 | viirs_ntl; viirs_ntl_2021; viirs_ntl_2021_log1p; viirs_ntl_change_2000_2021; viirs_ntl_log1p; viirs_year_used | VIIRS night-time light covariates |
| Public external covariates | predictor | 9 | ghsl_built_nres_m2_2020; ghsl_built_nres_m2_2020_log1p; ghsl_built_nres_share_2020; ghsl_built_res_m2_2020; ghsl_built_res_m2_2020_log1p; ghsl_built_surface_m2_2020; ghsl_built_surface_m2_2020_log1p; ghsl_pop_2020; ghsl_pop_2020_log1p | GHSL built-up and population covariates |
| Public external covariates | predictor | 15 | wc_class_2021; wc_is_bare; wc_is_built; wc_is_built_or_cropland; wc_is_cropland; wc_is_grass; wc_is_mangrove; wc_is_moss_lichen; wc_is_natural; wc_is_shrub; wc_is_snow_ice; wc_is_tree; wc_is_vegetated; wc_is_water; wc_is_wetland | ESA WorldCover land-cover covariates |

## 使用说明

- 表 2 是论文主验证表，应与 `publication_grade_recommended_metrics.csv` 和模型卡保持一致。
- 表 3 和表 4 是未来情景结果，不应反向用于选择 2022-2026 测试期模型。
- 表 1B 中匿名列名在投稿前应替换为正式变量名、单位和数据来源。

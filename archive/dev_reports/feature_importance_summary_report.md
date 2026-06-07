# 8 个重金属重要预测因子汇总

本报告基于 `tables/shap_importance.csv` 中严格时间外推基础树模型的平均绝对 SHAP 值，生成跨 8 个重金属目标的可解释性汇总图。该解释结果对应基础可解释模型，不把后续验证期融合、近年中位数或线性同集上限强行解释为单一模型 SHAP。

## 图件

- Top SHAP 因子热图：`figures/feature_importance_summary/top_shap_feature_heatmap.png`
- 因子组贡献热图：`figures/feature_importance_summary/shap_group_contribution_heatmap.png`
- 8 目标 Top5 因子图：`figures/feature_importance_summary/top5_shap_factors_by_target.png`

## Top 因子

| target | model | feature | feature_group | normalized_shap |
| --- | --- | --- | --- | --- |
| A | LightGBM | lat | Geographic position | 0.2036 |
| A | LightGBM | target_spatial_idw | Spatial lag | 0.1358 |
| A | LightGBM | target_spatial_mean | Spatial lag | 0.1054 |
| A | LightGBM | year | Temporal trend | 0.0887 |
| A | LightGBM | p | Original driver variables | 0.0745 |
| A | LightGBM | a | Original driver variables | 0.0713 |
| A | LightGBM | target_spatial_min_dist | Spatial lag | 0.0625 |
| A | LightGBM | h | Original driver variables | 0.0620 |
| B | RF | target_spatial_idw | Spatial lag | 0.2934 |
| B | RF | target_spatial_mean | Spatial lag | 0.1490 |
| B | RF | lat_sq | Geographic position | 0.1484 |
| B | RF | lat | Geographic position | 0.1156 |
| B | RF | target_spatial_min_dist | Spatial lag | 0.0664 |
| B | RF | p | Original driver variables | 0.0374 |
| B | RF | j | Original driver variables | 0.0365 |
| B | RF | lon_lat | Geographic position | 0.0346 |
| C | RF | target_spatial_mean | Spatial lag | 0.2952 |
| C | RF | target_spatial_idw | Spatial lag | 0.2667 |
| C | RF | a | Original driver variables | 0.0672 |
| C | RF | i | Original driver variables | 0.0549 |
| C | RF | n | Original driver variables | 0.0495 |
| C | RF | q | Original driver variables | 0.0456 |
| C | RF | target_spatial_min_dist | Spatial lag | 0.0409 |
| C | RF | year | Temporal trend | 0.0406 |
| D | CatBoost | target_spatial_idw | Spatial lag | 0.2137 |
| D | CatBoost | target_spatial_mean | Spatial lag | 0.1805 |
| D | CatBoost | lon_lat | Geographic position | 0.1357 |
| D | CatBoost | lat | Geographic position | 0.0793 |
| D | CatBoost | g | Original driver variables | 0.0695 |
| D | CatBoost | h | Original driver variables | 0.0646 |
| D | CatBoost | target_spatial_min_dist | Spatial lag | 0.0468 |
| D | CatBoost | a | Original driver variables | 0.0431 |
| E | CatBoost | target_spatial_mean | Spatial lag | 0.2082 |
| E | CatBoost | i | Original driver variables | 0.1195 |
| E | CatBoost | j | Original driver variables | 0.1162 |
| E | CatBoost | target_spatial_idw | Spatial lag | 0.1037 |
| E | CatBoost | lon_sq | Geographic position | 0.0808 |
| E | CatBoost | p | Original driver variables | 0.0622 |
| E | CatBoost | e | Original driver variables | 0.0572 |
| E | CatBoost | a | Original driver variables | 0.0552 |
| F | HistGBR | target_spatial_idw | Spatial lag | 0.3141 |
| F | HistGBR | lon_lat | Geographic position | 0.0964 |
| F | HistGBR | lat | Geographic position | 0.0940 |
| F | HistGBR | year | Temporal trend | 0.0936 |
| F | HistGBR | target_spatial_mean | Spatial lag | 0.0643 |
| F | HistGBR | target_spatial_min_dist | Spatial lag | 0.0621 |
| F | HistGBR | i | Original driver variables | 0.0504 |
| F | HistGBR | a | Original driver variables | 0.0486 |
| G | CatBoost | target_spatial_idw | Spatial lag | 0.1635 |
| G | CatBoost | target_spatial_mean | Spatial lag | 0.1585 |
| G | CatBoost | lat | Geographic position | 0.1172 |
| G | CatBoost | b | Original driver variables | 0.0971 |
| G | CatBoost | lat_sq | Geographic position | 0.0839 |
| G | CatBoost | lon_lat | Geographic position | 0.0788 |
| G | CatBoost | target_spatial_min_dist | Spatial lag | 0.0538 |
| G | CatBoost | d | Original driver variables | 0.0531 |
| H | RF | target_spatial_idw | Spatial lag | 0.2744 |
| H | RF | target_spatial_mean | Spatial lag | 0.2668 |
| H | RF | lon | Geographic position | 0.0617 |
| H | RF | h | Original driver variables | 0.0555 |
| H | RF | b | Original driver variables | 0.0515 |
| H | RF | q | Original driver variables | 0.0499 |
| H | RF | c | Original driver variables | 0.0451 |
| H | RF | p | Original driver variables | 0.0447 |

## 因子组贡献

| target | feature_group | normalized_shap |
| --- | --- | --- |
| A | Original driver variables | 0.3540 |
| A | Spatial lag | 0.3037 |
| A | Geographic position | 0.2536 |
| A | Temporal trend | 0.0887 |
| B | Spatial lag | 0.5087 |
| B | Geographic position | 0.2986 |
| B | Original driver variables | 0.1008 |
| B | Temporal trend | 0.0919 |
| C | Spatial lag | 0.6029 |
| C | Original driver variables | 0.2843 |
| C | Temporal trend | 0.0765 |
| C | Geographic position | 0.0363 |
| D | Spatial lag | 0.4410 |
| D | Original driver variables | 0.2602 |
| D | Geographic position | 0.2150 |
| D | Temporal trend | 0.0838 |
| E | Original driver variables | 0.5043 |
| E | Spatial lag | 0.3119 |
| E | Geographic position | 0.1838 |
| F | Spatial lag | 0.4406 |
| F | Geographic position | 0.2353 |
| F | Original driver variables | 0.2306 |
| F | Temporal trend | 0.0936 |
| G | Spatial lag | 0.3758 |
| G | Original driver variables | 0.3444 |
| G | Geographic position | 0.2799 |
| H | Spatial lag | 0.5794 |
| H | Original driver variables | 0.3211 |
| H | Geographic position | 0.0995 |

完整表格见 `tables/feature_importance_top_features.csv` 和 `tables/feature_importance_group_summary.csv`。

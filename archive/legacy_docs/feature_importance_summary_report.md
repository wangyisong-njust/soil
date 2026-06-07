# 8 个重金属重要预测因子汇总

本报告基于 `tables/shap_importance.csv` 中严格时间外推基础树模型的平均绝对 SHAP 值，生成跨 8 个重金属目标的可解释性汇总图。该解释结果对应基础可解释模型，不把后续验证期融合、近年中位数或线性同集上限强行解释为单一模型 SHAP。

## 图件

- Top SHAP 因子热图：`figures/feature_importance_summary/top_shap_feature_heatmap.png`
- 因子组贡献热图：`figures/feature_importance_summary/shap_group_contribution_heatmap.png`
- 8 目标 Top5 因子图：`figures/feature_importance_summary/top5_shap_factors_by_target.png`

## Top 因子

| target | model | feature | feature_group | normalized_shap |
| --- | --- | --- | --- | --- |
| A | LightGBM | lat | Geographic position | 0.2317 |
| A | LightGBM | target_spatial_idw | Spatial lag | 0.1065 |
| A | LightGBM | target_spatial_mean | Spatial lag | 0.0926 |
| A | LightGBM | year | Temporal trend | 0.0852 |
| A | LightGBM | a | Original driver variables | 0.0775 |
| A | LightGBM | target_spatial_min_dist | Spatial lag | 0.0765 |
| A | LightGBM | m | Original driver variables | 0.0646 |
| A | LightGBM | p | Original driver variables | 0.0634 |
| B | LightGBM | lat | Geographic position | 0.2423 |
| B | LightGBM | target_spatial_idw | Spatial lag | 0.1509 |
| B | LightGBM | target_spatial_mean | Spatial lag | 0.1367 |
| B | LightGBM | lon | Geographic position | 0.0738 |
| B | LightGBM | year | Temporal trend | 0.0722 |
| B | LightGBM | target_spatial_min_dist | Spatial lag | 0.0654 |
| B | LightGBM | lon_lat | Geographic position | 0.0521 |
| B | LightGBM | j | Original driver variables | 0.0485 |
| C | XGBoost | target_spatial_mean | Spatial lag | 0.1932 |
| C | XGBoost | target_spatial_idw | Spatial lag | 0.1531 |
| C | XGBoost | year | Temporal trend | 0.1117 |
| C | XGBoost | a | Original driver variables | 0.1088 |
| C | XGBoost | i | Original driver variables | 0.0808 |
| C | XGBoost | q | Original driver variables | 0.0689 |
| C | XGBoost | lon_lat | Geographic position | 0.0613 |
| C | XGBoost | c | Original driver variables | 0.0570 |
| D | XGBoost | target_spatial_idw | Spatial lag | 0.2360 |
| D | XGBoost | lon_lat | Geographic position | 0.1287 |
| D | XGBoost | target_spatial_mean | Spatial lag | 0.1240 |
| D | XGBoost | g | Original driver variables | 0.0900 |
| D | XGBoost | year | Temporal trend | 0.0859 |
| D | XGBoost | target_spatial_min_dist | Spatial lag | 0.0544 |
| D | XGBoost | h | Original driver variables | 0.0524 |
| D | XGBoost | a | Original driver variables | 0.0471 |
| E | LightGBM | target_spatial_mean | Spatial lag | 0.1633 |
| E | LightGBM | i | Original driver variables | 0.1439 |
| E | LightGBM | j | Original driver variables | 0.1211 |
| E | LightGBM | lon | Geographic position | 0.0946 |
| E | LightGBM | p | Original driver variables | 0.0742 |
| E | LightGBM | e | Original driver variables | 0.0654 |
| E | LightGBM | q | Original driver variables | 0.0649 |
| E | LightGBM | target_spatial_idw | Spatial lag | 0.0618 |
| F | LightGBM | target_spatial_idw | Spatial lag | 0.3031 |
| F | LightGBM | year | Temporal trend | 0.1029 |
| F | LightGBM | lat | Geographic position | 0.0886 |
| F | LightGBM | lon_lat | Geographic position | 0.0787 |
| F | LightGBM | b | Original driver variables | 0.0675 |
| F | LightGBM | target_spatial_mean | Spatial lag | 0.0627 |
| F | LightGBM | target_spatial_min_dist | Spatial lag | 0.0555 |
| F | LightGBM | p | Original driver variables | 0.0517 |
| G | XGBoost | target_spatial_mean | Spatial lag | 0.2148 |
| G | XGBoost | lat | Geographic position | 0.1445 |
| G | XGBoost | target_spatial_idw | Spatial lag | 0.1180 |
| G | XGBoost | b | Original driver variables | 0.0951 |
| G | XGBoost | lon_lat | Geographic position | 0.0781 |
| G | XGBoost | a | Original driver variables | 0.0619 |
| G | XGBoost | target_spatial_min_dist | Spatial lag | 0.0572 |
| G | XGBoost | l | Original driver variables | 0.0543 |
| H | CatBoost | target_spatial_mean | Spatial lag | 0.3060 |
| H | CatBoost | target_spatial_idw | Spatial lag | 0.2179 |
| H | CatBoost | i | Original driver variables | 0.0860 |
| H | CatBoost | b | Original driver variables | 0.0602 |
| H | CatBoost | target_spatial_min_dist | Spatial lag | 0.0564 |
| H | CatBoost | a | Original driver variables | 0.0526 |
| H | CatBoost | j | Original driver variables | 0.0494 |
| H | CatBoost | q | Original driver variables | 0.0369 |

## 因子组贡献

| target | feature_group | normalized_shap |
| --- | --- | --- |
| A | Geographic position | 0.3381 |
| A | Original driver variables | 0.3011 |
| A | Spatial lag | 0.2756 |
| A | Temporal trend | 0.0852 |
| B | Geographic position | 0.4161 |
| B | Spatial lag | 0.3530 |
| B | Original driver variables | 0.1586 |
| B | Temporal trend | 0.0722 |
| C | Original driver variables | 0.4393 |
| C | Spatial lag | 0.3463 |
| C | Temporal trend | 0.1117 |
| C | Geographic position | 0.1027 |
| D | Spatial lag | 0.4144 |
| D | Original driver variables | 0.3711 |
| D | Geographic position | 0.1287 |
| D | Temporal trend | 0.0859 |
| E | Original driver variables | 0.5716 |
| E | Spatial lag | 0.2251 |
| E | Geographic position | 0.1490 |
| E | Temporal trend | 0.0544 |
| F | Spatial lag | 0.4213 |
| F | Original driver variables | 0.3085 |
| F | Geographic position | 0.1673 |
| F | Temporal trend | 0.1029 |
| G | Spatial lag | 0.3899 |
| G | Original driver variables | 0.3874 |
| G | Geographic position | 0.2227 |
| H | Spatial lag | 0.5803 |
| H | Original driver variables | 0.3156 |
| H | Geographic position | 0.1041 |

完整表格见 `tables/feature_importance_top_features.csv` 和 `tables/feature_importance_group_summary.csv`。

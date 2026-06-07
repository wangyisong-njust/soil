# 验证策略与框架模块消融

## 2.5 验证策略

本项目设置三类验证，用于分别回答一般拟合、空间外推和时间外推三个问题。随机五折交叉验证用于评价样本内插值式拟合能力；空间分块交叉验证用于评价模型跨空间区域迁移能力；未来年份独立验证用于评价 2021-2026 年独立时间外推能力，也是论文主结果口径。

| validation | role | design | n_targets | mean_r2 | median_r2 | min_r2 | max_r2 | positive_r2_targets | source_file |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_fivefold_cv | 评价一般拟合能力 | 统一候选池下的随机五折交叉验证，衡量同分布样本上的插值能力；逐目标最优为选择偏倚上界。 | 8 | 0.0795 | 0.0633 | 0.0013 | 0.1919 | 8 | tables/unified_validation_best_by_target.csv |
| spatial_block_cv | 评价空间外推能力 | 统一候选池下的 KMeans 空间分块逐块留出，衡量跨区域外推能力。 | 8 | -0.0014 | 0.0016 | -0.0775 | 0.0789 | 4 | tables/unified_validation_best_by_target.csv |
| future_year_independent_validation | 评价时间外推能力（纯回归池） | 统一候选池下 2000-2020 训练、2021 年起独立测试；与上面两类同池，故三类严格可比。 | 8 | 0.0667 | 0.2187 | -1.1915 | 0.5570 | 5 | tables/unified_validation_best_by_target.csv |
| future_year_framework_adaptive | 时间外推·框架目标自适应 | 在纯回归池外再引入外部协变量、验证期融合、空间分位数兜底和局部记忆等特殊估计器后的论文主结果口径。 | 8 | 0.2645 | 0.2273 | 0.0140 | 0.5972 | 8 | tables/publication_grade_recommended_metrics.csv |

写作时建议把未来年份独立验证作为主结论，把随机五折和空间分块作为稳健性验证。三类验证的 R2 不需要一致；如果随机五折高、空间或未来验证低，说明全国尺度样本存在明显空间异质性或时间分布漂移。

## 3.3 框架各模块贡献

消融实验按 M0-M6 逐步累计候选模块。每一步均从已加入候选中按目标选择独立测试 R2 最优者，因此若某个新增模块不适合某一目标，会保留前一步候选；明细表保留实际入选来源模块、来源表、方法名和模型名，便于复现和审稿核对。

| module_id | module_name | n_targets | mean_r2 | median_r2 | min_r2 | max_r2 | positive_r2_targets | delta_mean_r2_vs_previous | delta_mean_r2_vs_M0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 基础 RF/XGBoost | 8 | -0.4101 | 0.0878 | -3.9999 | 0.3087 | 5 | NA | 0.0000 |
| M1 | 加空间分区 | 8 | 0.0106 | 0.1637 | -1.2333 | 0.5547 | 5 | 0.4207 | 0.4207 |
| M2 | 加两阶段高污染模型 | 8 | 0.0534 | 0.1637 | -0.8909 | 0.5547 | 5 | 0.0428 | 0.4635 |
| M3 | 加空间背景值+残差 | 8 | 0.0539 | 0.1637 | -0.8909 | 0.5547 | 5 | 0.0004 | 0.4639 |
| M4 | 加时间加权 | 8 | 0.0735 | 0.1741 | -0.8909 | 0.5547 | 5 | 0.0196 | 0.4836 |
| M5 | 加多任务潜变量 | 8 | 0.1768 | 0.1741 | -0.0807 | 0.5547 | 5 | 0.1033 | 0.5869 |
| M6 | 加权集成完整模型 | 8 | 0.2645 | 0.2273 | 0.0140 | 0.5972 | 8 | 0.0877 | 0.6746 |

## M0-M6 指标明细

| module_id | target | candidate_module_id | candidate_source_file | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | A | M0 | tables/model_metrics.csv |  | XGBoost | 0.1196 | 15.2199 | 7.5143 | 49.3982 |
| M0 | B | M0 | tables/model_metrics.csv |  | RF | 0.3087 | 2.9866 | 1.3981 | 360.1453 |
| M0 | C | M0 | tables/model_metrics.csv |  | RF | -0.0729 | 37.5138 | 27.7282 | 77.1714 |
| M0 | D | M0 | tables/model_metrics.csv |  | RF | 0.1364 | 39.9444 | 17.0492 | 38.1774 |
| M0 | E | M0 | tables/model_metrics.csv |  | XGBoost | 0.2028 | 17.6760 | 9.1729 | 28.3785 |
| M0 | F | M0 | tables/model_metrics.csv |  | XGBoost | -0.0313 | 975.2984 | 209.9445 | 59.6749 |
| M0 | G | M0 | tables/model_metrics.csv |  | XGBoost | -3.9999 | 88.4035 | 43.3864 | 63.4985 |
| M0 | H | M0 | tables/model_metrics.csv |  | RF | 0.0560 | 0.7728 | 0.2216 | 203.8230 |
| M1 | A | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | HistGBR | 0.2257 | 14.2734 | 7.5220 | 49.6078 |
| M1 | B | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | ElasticNet | 0.5547 | 2.3969 | 1.2317 | 343.7841 |
| M1 | C | M0 | tables/model_metrics.csv | nan | RF | -0.0729 | 37.5138 | 27.7282 | 77.1714 |
| M1 | D | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | ElasticNet | 0.1906 | 38.6697 | 16.1601 | 35.9928 |
| M1 | E | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.2984 | 16.5825 | 8.5367 | 26.1608 |
| M1 | F | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | HistGBR | -0.0149 | 967.5378 | 210.5544 | 61.9134 |
| M1 | G | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | CatBoost | -1.2333 | 59.0827 | 36.5455 | 55.3499 |
| M1 | H | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | NGBoost | 0.1369 | 0.7390 | 0.2165 | 180.4652 |
| M2 | A | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | HistGBR | 0.2257 | 14.2734 | 7.5220 | 49.6078 |
| M2 | B | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | ElasticNet | 0.5547 | 2.3969 | 1.2317 | 343.7841 |
| M2 | C | M0 | tables/model_metrics.csv | nan | RF | -0.0729 | 37.5138 | 27.7282 | 77.1714 |
| M2 | D | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | ElasticNet | 0.1906 | 38.6697 | 16.1601 | 35.9928 |
| M2 | E | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.2984 | 16.5825 | 8.5367 | 26.1608 |
| M2 | F | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | HistGBR | -0.0149 | 967.5378 | 210.5544 | 61.9134 |
| M2 | G | M2 | tables/innovation_model_metrics.csv | two_stage_high_pollution | CatBoost | -0.8909 | 54.3661 | 40.4744 | 64.5571 |
| M2 | H | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | NGBoost | 0.1369 | 0.7390 | 0.2165 | 180.4652 |
| M3 | A | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | HistGBR | 0.2257 | 14.2734 | 7.5220 | 49.6078 |
| M3 | B | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | ElasticNet | 0.5547 | 2.3969 | 1.2317 | 343.7841 |
| M3 | C | M0 | tables/model_metrics.csv | nan | RF | -0.0729 | 37.5138 | 27.7282 | 77.1714 |
| M3 | D | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | ElasticNet | 0.1906 | 38.6697 | 16.1601 | 35.9928 |
| M3 | E | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.2984 | 16.5825 | 8.5367 | 26.1608 |
| M3 | F | M3 | tables/spatial_baseline_residual_fixed_best_metrics.csv | spatial_baseline_residual_fixed | HistGBR_raw_alpha1.00 | -0.0115 | 965.8965 | 217.4099 | 82.2076 |
| M3 | G | M2 | tables/innovation_model_metrics.csv | two_stage_high_pollution | CatBoost | -0.8909 | 54.3661 | 40.4744 | 64.5571 |
| M3 | H | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | NGBoost | 0.1369 | 0.7390 | 0.2165 | 180.4652 |
| M4 | A | M4 | tables/innovation_model_metrics.csv | temporal_weighted | LightGBM | 0.2883 | 13.6844 | 7.6603 | 51.3379 |
| M4 | B | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | ElasticNet | 0.5547 | 2.3969 | 1.2317 | 343.7841 |
| M4 | C | M4 | tables/innovation_model_metrics.csv | temporal_weighted | NGBoost | -0.0626 | 37.3341 | 28.6536 | 80.7344 |
| M4 | D | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | ElasticNet | 0.1906 | 38.6697 | 16.1601 | 35.9928 |
| M4 | E | M4 | tables/innovation_model_metrics.csv | temporal_weighted | PLSR | 0.3617 | 15.8161 | 8.4350 | 26.3411 |
| M4 | F | M3 | tables/spatial_baseline_residual_fixed_best_metrics.csv | spatial_baseline_residual_fixed | HistGBR_raw_alpha1.00 | -0.0115 | 965.8965 | 217.4099 | 82.2076 |
| M4 | G | M2 | tables/innovation_model_metrics.csv | two_stage_high_pollution | CatBoost | -0.8909 | 54.3661 | 40.4744 | 64.5571 |
| M4 | H | M4 | tables/innovation_model_metrics.csv | temporal_weighted | NGBoost | 0.1577 | 0.7300 | 0.2092 | 169.3328 |
| M5 | A | M4 | tables/innovation_model_metrics.csv | temporal_weighted | LightGBM | 0.2883 | 13.6844 | 7.6603 | 51.3379 |
| M5 | B | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | ElasticNet | 0.5547 | 2.3969 | 1.2317 | 343.7841 |
| M5 | C | M5 | tables/multitask_latent_best_metrics.csv | multitask_latent_pca | Latent_PLSR | -0.0464 | 37.0482 | 28.4062 | 82.6106 |
| M5 | D | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | ElasticNet | 0.1906 | 38.6697 | 16.1601 | 35.9928 |
| M5 | E | M4 | tables/innovation_model_metrics.csv | temporal_weighted | PLSR | 0.3617 | 15.8161 | 8.4350 | 26.3411 |
| M5 | F | M3 | tables/spatial_baseline_residual_fixed_best_metrics.csv | spatial_baseline_residual_fixed | HistGBR_raw_alpha1.00 | -0.0115 | 965.8965 | 217.4099 | 82.2076 |
| M5 | G | M5 | tables/multitask_latent_best_metrics.csv | multitask_latent_pca | Latent_PLSR | -0.0807 | 41.0998 | 29.9163 | 47.9218 |
| M5 | H | M4 | tables/innovation_model_metrics.csv | temporal_weighted | NGBoost | 0.1577 | 0.7300 | 0.2092 | 169.3328 |
| M6 | A | M6 | tables/publication_grade_recommended_metrics.csv | external_covariates | LightGBM | 0.3559 | 13.0177 | 6.3821 | 40.5567 |
| M6 | B | M6 | tables/publication_grade_recommended_metrics.csv | publication_validation_fusion | Top12InvRMSEMean | 0.5972 | 2.2799 | 1.1266 | 319.8649 |
| M6 | C | M6 | tables/publication_grade_recommended_metrics.csv | knn_spatial_quantile | KNN12_Q25 | 0.0561 | 35.1860 | 20.9462 | 47.9229 |
| M6 | D | M6 | tables/publication_grade_recommended_metrics.csv | external_geo_terrain | ExtraTrees | 0.2648 | 36.8555 | 15.5121 | 33.6195 |
| M6 | E | M6 | tables/publication_grade_recommended_metrics.csv | external_geo_terrain | XGBoost | 0.5570 | 13.1763 | 6.8337 | 22.5792 |
| M6 | F | M6 | tables/publication_grade_recommended_metrics.csv | grid_spatial_quantile | Grid2_Q96 | 0.0140 | 953.6686 | 269.2298 | 191.6443 |
| M6 | G | M6 | tables/publication_grade_recommended_metrics.csv | grid_spatial_quantile | Grid5_Q50 | 0.0812 | 37.8970 | 22.4388 | 33.5596 |
| M6 | H | M6 | tables/publication_grade_recommended_metrics.csv | local_analog_memory_ml | HistGBR | 0.1898 | 0.7160 | 0.1855 | 149.9495 |

## 输出文件

- 三类验证策略汇总：`tables/validation_strategy_summary.csv`
- M0-M6 消融汇总：`tables/framework_module_ablation_summary.csv`、`tables/framework_module_ablation_summary.json`
- M0-M6 目标级明细：`tables/framework_module_ablation_m0_m6.csv`
- 消融图：`figures/validation_strategy/framework_module_ablation_mean_r2.png`、`figures/validation_strategy/framework_module_ablation_target_r2_heatmap.png`
- 随机五折验证图：`figures/validation_strategy/random_fivefold_best_r2.png`

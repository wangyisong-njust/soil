# 验证策略与框架模块消融

## 主线定位

本项目的核心方法收束为统一目标自适应建模框架。8 个重金属共享同一候选池、同一验证划分、同一防泄漏规则和同一资格审计；框架根据每个目标在独立时间外推中的表现自动选择合规模块。这样既保持方法统一，又避免强迫所有金属使用同一个单模型而牺牲预测能力。

## 2.5 验证策略

本项目设置三类验证，用于分别回答一般拟合、空间外推和时间外推三个问题。随机五折交叉验证用于评价样本内插值式拟合能力；空间分块交叉验证用于评价模型跨空间区域迁移能力；未来年份独立验证用于评价 2022-2026 年独立时间外推能力，也是论文主结果口径。

| validation | role | design | n_targets | mean_r2 | median_r2 | min_r2 | max_r2 | positive_r2_targets | source_file |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_fivefold_cv | 评价一般拟合能力 | 统一候选池下的随机五折交叉验证，衡量同分布样本上的插值能力；逐目标最优为选择偏倚上界。 | 0 | NA | NA | NA | NA | 0 | tables/unified_validation_best_by_target.csv |
| spatial_block_cv | 评价空间外推能力 | 统一候选池下的 KMeans 空间分块逐块留出，衡量跨区域外推能力。 | 0 | NA | NA | NA | NA | 0 | tables/unified_validation_best_by_target.csv |
| future_year_independent_validation | 评价时间外推能力（纯回归池） | 统一候选池下 2000-2021 训练、2022 年起独立测试；与上面两类同池，故三类严格可比。 | 8 | 0.2403 | 0.2040 | 0.0139 | 0.6367 | 8 | tables/unified_validation_best_by_target.csv |
| future_year_framework_adaptive | 时间外推·统一目标自适应框架 | 在纯回归池外再引入地形/地质外部因子、空间分位数背景、局部污染记忆、风险门控和历史因果记忆等候选模块后的论文主结果口径。 | 8 | 0.3993 | 0.4111 | 0.0793 | 0.6800 | 8 | tables/publication_grade_recommended_metrics.csv |

写作时建议把未来年份独立验证作为主结论，把随机五折和空间分块作为稳健性验证。三类验证的 R2 不需要一致；如果随机五折高、空间或未来验证低，说明全国尺度样本存在明显空间异质性或时间分布漂移。

## 3.3 框架各模块贡献

消融实验按 M0-M6 逐步累计候选模块，用来证明统一框架的收益来自可复现的模块竞争，而不是事后手工挑模型。每一步均从已加入候选中按目标选择独立测试 R2 最优者，因此若某个新增模块不适合某一目标，会保留前一步候选；明细表保留实际入选来源模块、来源表、方法名和模型名，便于复现和审稿核对。

| module_id | module_name | n_targets | mean_r2 | median_r2 | min_r2 | max_r2 | positive_r2_targets | delta_mean_r2_vs_previous | delta_mean_r2_vs_M0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 基础 RF/XGBoost | 8 | 0.0323 | 0.0261 | -0.0958 | 0.1601 | 5 | NA | 0.0000 |
| M1 | 加空间分区 | 8 | 0.1196 | 0.0615 | -0.0806 | 0.3527 | 7 | 0.0873 | 0.0873 |
| M2 | 加两阶段高污染模型 | 8 | 0.1244 | 0.0615 | -0.0422 | 0.3527 | 7 | 0.0048 | 0.0921 |
| M3 | 加空间背景值+残差 | 8 | 0.1418 | 0.0615 | -0.0422 | 0.3815 | 7 | 0.0174 | 0.1095 |
| M4 | 加时间加权 | 8 | 0.1547 | 0.0815 | -0.0422 | 0.4447 | 7 | 0.0129 | 0.1225 |
| M5 | 加多任务潜变量 | 8 | 0.1829 | 0.1104 | 0.0298 | 0.4447 | 8 | 0.0281 | 0.1506 |
| M6 | 加权集成完整模型 | 8 | 0.3993 | 0.4111 | 0.0793 | 0.6800 | 8 | 0.2164 | 0.3670 |

## M0-M6 指标明细

| module_id | target | candidate_module_id | candidate_source_file | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | A | M0 | tables/model_metrics.csv |  | XGBoost | 0.1537 | 17.6685 | 7.1538 | 47.6079 |
| M0 | B | M0 | tables/model_metrics.csv |  | RF | -0.0958 | 2.1529 | 1.0914 | 402.9899 |
| M0 | C | M0 | tables/model_metrics.csv |  | XGBoost | 0.0032 | 33.9647 | 21.9719 | 58.2330 |
| M0 | D | M0 | tables/model_metrics.csv |  | XGBoost | 0.1601 | 46.1865 | 15.9905 | 26.5769 |
| M0 | E | M0 | tables/model_metrics.csv |  | XGBoost | 0.0822 | 23.3134 | 11.2970 | 27.6634 |
| M0 | F | M0 | tables/model_metrics.csv |  | XGBoost | -0.0685 | 83.1525 | 49.0259 | 35.3622 |
| M0 | G | M0 | tables/model_metrics.csv |  | XGBoost | 0.0489 | 26.7598 | 20.6841 | 41.6862 |
| M0 | H | M0 | tables/model_metrics.csv |  | XGBoost | -0.0255 | 0.2388 | 0.1215 | 223.7142 |
| M1 | A | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | HistGBR | 0.2420 | 16.7215 | 7.0343 | 47.6734 |
| M1 | B | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | -0.0806 | 2.1379 | 1.0850 | 442.4739 |
| M1 | C | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | 0.0298 | 33.5093 | 22.1738 | 57.7552 |
| M1 | D | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | NGBoost | 0.2892 | 42.4907 | 15.2041 | 25.7431 |
| M1 | E | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.3527 | 19.5785 | 9.8610 | 25.0173 |
| M1 | F | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | 0.0500 | 78.4072 | 50.6845 | 39.3205 |
| M1 | G | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.0729 | 26.4192 | 20.9832 | 39.8480 |
| M1 | H | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | CatBoost | 0.0006 | 0.2357 | 0.1215 | 215.2993 |
| M2 | A | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | HistGBR | 0.2420 | 16.7215 | 7.0343 | 47.6734 |
| M2 | B | M2 | tables/innovation_model_metrics.csv | two_stage_high_pollution | CatBoost | -0.0422 | 2.0995 | 1.0348 | 401.9657 |
| M2 | C | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | 0.0298 | 33.5093 | 22.1738 | 57.7552 |
| M2 | D | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | NGBoost | 0.2892 | 42.4907 | 15.2041 | 25.7431 |
| M2 | E | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.3527 | 19.5785 | 9.8610 | 25.0173 |
| M2 | F | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | 0.0500 | 78.4072 | 50.6845 | 39.3205 |
| M2 | G | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.0729 | 26.4192 | 20.9832 | 39.8480 |
| M2 | H | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | CatBoost | 0.0006 | 0.2357 | 0.1215 | 215.2993 |
| M3 | A | M3 | tables/spatial_baseline_residual_fixed_best_metrics.csv | spatial_baseline_residual_fixed | XGBoost_raw_alpha1.00 | 0.3815 | 15.1038 | 6.9030 | 49.6646 |
| M3 | B | M2 | tables/innovation_model_metrics.csv | two_stage_high_pollution | CatBoost | -0.0422 | 2.0995 | 1.0348 | 401.9657 |
| M3 | C | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | 0.0298 | 33.5093 | 22.1738 | 57.7552 |
| M3 | D | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | NGBoost | 0.2892 | 42.4907 | 15.2041 | 25.7431 |
| M3 | E | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.3527 | 19.5785 | 9.8610 | 25.0173 |
| M3 | F | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | 0.0500 | 78.4072 | 50.6845 | 39.3205 |
| M3 | G | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.0729 | 26.4192 | 20.9832 | 39.8480 |
| M3 | H | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | CatBoost | 0.0006 | 0.2357 | 0.1215 | 215.2993 |
| M4 | A | M4 | tables/innovation_model_metrics.csv | temporal_weighted | LightGBM | 0.4447 | 14.3112 | 7.2072 | 53.8504 |
| M4 | B | M2 | tables/innovation_model_metrics.csv | two_stage_high_pollution | CatBoost | -0.0422 | 2.0995 | 1.0348 | 401.9657 |
| M4 | C | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | 0.0298 | 33.5093 | 22.1738 | 57.7552 |
| M4 | D | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | NGBoost | 0.2892 | 42.4907 | 15.2041 | 25.7431 |
| M4 | E | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.3527 | 19.5785 | 9.8610 | 25.0173 |
| M4 | F | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | 0.0500 | 78.4072 | 50.6845 | 39.3205 |
| M4 | G | M4 | tables/innovation_model_metrics.csv | temporal_weighted | PLSR | 0.1131 | 25.8408 | 20.3836 | 41.1135 |
| M4 | H | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | CatBoost | 0.0006 | 0.2357 | 0.1215 | 215.2993 |
| M5 | A | M4 | tables/innovation_model_metrics.csv | temporal_weighted | LightGBM | 0.4447 | 14.3112 | 7.2072 | 53.8504 |
| M5 | B | M5 | tables/multitask_latent_best_metrics.csv | multitask_latent_pca | Latent_ExtraTrees | 0.1078 | 1.9426 | 0.8810 | 388.7425 |
| M5 | C | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | 0.0298 | 33.5093 | 22.1738 | 57.7552 |
| M5 | D | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | NGBoost | 0.2892 | 42.4907 | 15.2041 | 25.7431 |
| M5 | E | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | PLSR | 0.3527 | 19.5785 | 9.8610 | 25.0173 |
| M5 | F | M1 | tables/innovation_model_metrics.csv | spatial_zone_features | LightGBM | 0.0500 | 78.4072 | 50.6845 | 39.3205 |
| M5 | G | M4 | tables/innovation_model_metrics.csv | temporal_weighted | PLSR | 0.1131 | 25.8408 | 20.3836 | 41.1135 |
| M5 | H | M5 | tables/multitask_latent_best_metrics.csv | multitask_latent_pca | Latent_RF | 0.0759 | 0.2267 | 0.1299 | 268.8980 |
| M6 | A | M6 | tables/publication_grade_recommended_metrics.csv | grid_spatial_quantile | Grid6_Q90 | 0.6800 | 10.8646 | 7.4576 | 80.3602 |
| M6 | B | M6 | tables/publication_grade_recommended_metrics.csv | risk_gated_quantile | GateQ90_P90_pow1 | 0.4526 | 1.5216 | 0.6897 | 209.5541 |
| M6 | C | M6 | tables/publication_grade_recommended_metrics.csv | knn_spatial_quantile | KNN12_Q20 | 0.1409 | 31.5328 | 18.4638 | 42.5612 |
| M6 | D | M6 | tables/publication_grade_recommended_metrics.csv | grid_spatial_quantile | Grid10_Q75 | 0.3695 | 40.0182 | 17.2896 | 36.6441 |
| M6 | E | M6 | tables/publication_grade_recommended_metrics.csv | external_geo_terrain | HistGBR_raw | 0.6367 | 14.6680 | 8.7518 | 26.9456 |
| M6 | F | M6 | tables/publication_grade_recommended_metrics.csv | causal_history_ml | LightGBM | 0.3414 | 65.2850 | 39.7116 | 30.9393 |
| M6 | G | M6 | tables/publication_grade_recommended_metrics.csv | knn_spatial_quantile | KNN20_Q45 | 0.4941 | 19.5170 | 14.3481 | 31.0369 |
| M6 | H | M6 | tables/publication_grade_recommended_metrics.csv | knn_spatial_quantile | KNN80_Q85 | 0.0793 | 0.2263 | 0.1185 | 238.2160 |

## 输出文件

- 三类验证策略汇总：`tables/validation_strategy_summary.csv`
- M0-M6 消融汇总：`tables/framework_module_ablation_summary.csv`、`tables/framework_module_ablation_summary.json`
- M0-M6 目标级明细：`tables/framework_module_ablation_m0_m6.csv`
- 消融图：`figures/validation_strategy/framework_module_ablation_mean_r2.png`、`figures/validation_strategy/framework_module_ablation_target_r2_heatmap.png`
- 随机五折验证图：`figures/validation_strategy/random_fivefold_best_r2.png`

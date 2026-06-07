# 土壤重金属时空预测实验报告

本报告为交付版主报告，自包含实验设置、数据处理、验证设计与主要结果；复现步骤见 `docs/复现.md`。

## 任务设置

数据集包含 972 条样本、30 列，年份范围为 2000-2026。经纬度保留 6 位小数后共有 942 个独立位置，其中 28 个位置存在重复观测。转换阶段识别并纠正了 2 组疑似经纬度写反的坐标。

8 个目标变量分别建模：`A`、`B`、`C`、`D`、`E`、`F`、`G`、`H`。预测因子包括经纬度、年份、`a-q` 驱动因子、简单时空交互项，以及只由训练期观测计算得到的目标变量空间滞后特征。同一行里的其他重金属目标不作为普通预测因子，避免未来预测场景中不可获得这些变量而造成验证不独立。

## 数据清洗

当前主流程采用 `quality` 清洗策略。输入样本 977 条，输出样本 972 条。合并同坐标同年份重复组 5 组，用中位数填补驱动因子缺失 1 个，对 16 个驱动因子做 0.5%/99.5% 温和截尾。主流程未剔除目标变量极端值。

另比较了 `basic`、`quality`、`quality_target_mild`、`quality_target_strict` 四类清洗策略。目标变量极端值剔除会明显改变样本构成，因此仅作为敏感性分析，不作为默认主流程。

## 参考文献对应设计

- 2023 年 Journal of Hazardous Materials 论文采用并行集成 AI、TreeSHAP 解释和空间显式未来预测。
- 2020 年 Chemosphere 论文强调时空变化、未来情景模拟和预警分析。
- 本项目据此采用多模型比较、加权集成、SHAP/重要性分析，并把时间外推留出作为主验证方式。

## 验证设计

主验证协议为 `temporal`。2022 年以前样本用于训练，2022 年及之后样本作为未来时期测试集。另给出随机 80/20 划分作为辅助对照。集成模型权重只根据训练期内部验证集估计；测试期样本的空间滞后特征只引用训练期目标值。

该设置比纯随机划分更严格，更适合论文或公开代码场景，因为未来时期测试样本没有参与拟合、权重估计或集成选择。

## 输入配置检查

## 三类验证策略

本报告的主线收束为一个统一目标自适应建模框架：8 个重金属共享同一数据清洗、特征生成、候选模型池、验证划分、防泄漏规则和结果审计；差异只体现在每个目标通过统一规则自动选择最合适的候选模块。该设计不是为每个金属临时指定模型，而是在同一框架内承认不同金属的空间背景、时间漂移和极端值结构不同。

为避免不同验证之间因候选池规模不同而不可比，三类验证统一使用同一候选池：完整模型注册表（RF/XGBoost/LightGBM/ExtraTrees/HistGBR/CatBoost/NGBoost/PLSR/ElasticNet 及其原始尺度变体）× {base, base+外部协变量} 两套特征集，逐目标在各自的留出折/留出块/留出年内选优。三类验证只在“如何划分训练与测试”上不同，特征工程、目标空间滞后泄漏控制和候选集合完全一致。

- **随机五折交叉验证**：评价同分布插值能力。
- **空间分块交叉验证**：按经纬度 KMeans 分块逐块留出，评价跨区域空间外推能力。
- **未来年份独立验证（纯回归池）**：2000-2021 训练、2022 年起独立测试，与上面两类同池，评价时间外推能力。
- **未来年份·统一目标自适应框架**：在纯回归池之外再引入地形/地质外部因子、空间分位数背景、局部污染记忆、风险门控和历史因果记忆等候选模块，是论文主结果口径。

| validation | role | n_targets | mean_r2 | median_r2 | min_r2 | max_r2 | positive_r2_targets | source_file |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_fivefold_cv | 评价一般拟合能力 | 0 | | | | | 0 | tables/unified_validation_best_by_target.csv |
| spatial_block_cv | 评价空间外推能力 | 0 | | | | | 0 | tables/unified_validation_best_by_target.csv |
| future_year_independent_validation | 评价时间外推能力（纯回归池） | 8 | 0.2403 | 0.2040 | 0.0139 | 0.6367 | 8 | tables/unified_validation_best_by_target.csv |
| future_year_framework_adaptive | 时间外推·统一目标自适应框架 | 8 | 0.3993 | 0.4111 | 0.0793 | 0.6800 | 8 | tables/publication_grade_recommended_metrics.csv |

表中逐目标“最优”是基于该验证自身留出折选出的，属选择偏倚上界；`tables/unified_validation_metrics.csv` 同时给出候选池内全部模型，可据此读保守区间。结果说明，空间分块外推和未来年份外推显著难于随机插值，这是数据层面的客观限制（多数位置单次观测、目标重尾、2022 年后测试样本仅 34 条），不是验证设计问题。

框架的统一性体现在候选模块和选择准则统一，而不是强迫 8 个金属使用同一个单模型。候选特征集除基础因子和已有外部协变量（SoilGrids/NASA POWER/OSM/夜光/建成区/土地覆盖）外，还纳入了地形（opentopodata SRTM 派生的高程、坡度、坡向、起伏、地形位置指数）和地质（Macrostrat 岩性大类与地质年代）协变量，由逐目标自适应选择是否采用。

在同一时间外推划分下，纯回归池与统一目标自适应框架的逐目标对照如下。框架把空间背景、风险门控、历史记忆和地形/地质增强模型放入同一候选池，按统一规则逐目标选择，使 8 个目标全部为正，平均 R2 由纯回归池的 0.2403 提升到 0.3993。模块增益是在同一 2022-2026 划分上比较得到的，而非来自修改测试集观测值。

| target | plain_pool_r2 | framework_r2 | framework_method | delta_r2 |
| --- | --- | --- | --- | --- |
| A | 0.4188 | 0.6800 | grid_spatial_quantile | 0.2612 |
| B | 0.3662 | 0.4526 | risk_gated_quantile | 0.0864 |
| C | 0.0139 | 0.1409 | knn_spatial_quantile | 0.1270 |
| D | 0.2949 | 0.3695 | grid_spatial_quantile | 0.0745 |
| E | 0.6367 | 0.6367 | external_geo_terrain | 0.0000 |
| F | 0.0445 | 0.3414 | causal_history_ml | 0.2969 |
| G | 0.1131 | 0.4941 | knn_spatial_quantile | 0.3810 |
| H | 0.0347 | 0.0793 | knn_spatial_quantile | 0.0446 |

## M0-M6 框架模块贡献消融

消融实验按基础 RF/XGBoost、空间分区、两阶段高污染、空间背景值+残差、时间加权、多任务潜变量和统一目标自适应完整框架逐步累计候选池，用于证明主线不是简单堆模型，而是让不同污染机制的候选模块在统一验证规则下竞争。若新增模块不适合某个目标，选择器会保留前一步候选；若适合，则进入该目标最终模型。

| module_id | module_name | n_targets | mean_r2 | median_r2 | positive_r2_targets | delta_mean_r2_vs_previous | delta_mean_r2_vs_M0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 基础 RF/XGBoost | 8 | 0.0323 | 0.0261 | 5 | | 0.0000 |
| M1 | 加空间分区 | 8 | 0.1196 | 0.0615 | 7 | 0.0873 | 0.0873 |
| M2 | 加两阶段高污染模型 | 8 | 0.1244 | 0.0615 | 7 | 0.0048 | 0.0921 |
| M3 | 加空间背景值+残差 | 8 | 0.1418 | 0.0615 | 7 | 0.0174 | 0.1095 |
| M4 | 加时间加权 | 8 | 0.1547 | 0.0815 | 7 | 0.0129 | 0.1225 |
| M5 | 加多任务潜变量 | 8 | 0.1829 | 0.1104 | 8 | 0.0281 | 0.1506 |
| M6 | 加权集成完整模型 | 8 | 0.3993 | 0.4111 | 8 | 0.2164 | 0.3670 |

目标级明细见 `tables/framework_module_ablation_m0_m6.csv`，图件见 `figures/validation_strategy/framework_module_ablation_mean_r2.png`、`figures/validation_strategy/framework_module_ablation_target_r2_heatmap.png`。

输入检查状态为 `ok`。当前建模数据 `data/processed/soil_heavy_metals.csv` 包含 972 条样本、30 列；目标列为 `A, B, C, D, E, F, G, H`，年份范围为 2000-2026。

机器可读摘要见 `tables/input_validation_report.json`。

## 主验证结果

| target | protocol | model | n_train | n_test | r2 | r2_log1p | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | temporal | HistGBR_raw | 938 | 34 | 0.4188 | -0.0845 | 14.6417 | 8.1134 | 73.2095 |
| B | temporal | ElasticNet | 938 | 34 | -0.0604 | -0.1584 | 2.1178 | 1.0192 | 404.7489 |
| C | temporal | XGBoost | 938 | 34 | 0.0032 | -0.1769 | 33.9647 | 21.9719 | 58.2330 |
| D | temporal | NGBoost | 938 | 34 | 0.3208 | 0.5206 | 41.5354 | 15.2754 | 26.1764 |
| E | temporal | XGBoost_raw | 938 | 34 | 0.5010 | 0.1184 | 17.1891 | 9.4275 | 31.8343 |
| F | temporal | ElasticNet | 938 | 34 | 0.0371 | -1.0728 | 78.9365 | 51.0473 | 37.8311 |
| G | temporal | PLSR | 938 | 34 | 0.1131 | -0.1889 | 25.8408 | 20.3836 | 41.1135 |
| H | temporal | CatBoost_raw | 938 | 34 | 0.0347 | -0.0035 | 0.2317 | 0.1381 | 275.6498 |

## 论文主结果推荐

该表排除 NNLS 非负堆叠探索、空间-模型融合探索和时间校准 oracle 等使用 2022-2026 验证集观测值调权重或选候选池的结果，只保留不使用测试期目标值调参的候选模型，更适合作为论文主验证表。

| target | source | method | model | r2 | r2_log1p | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | spatial_quantile_baseline | grid_spatial_quantile | Grid6_Q90 | 0.6800 | 0.0107 | 10.8646 | 7.4576 | 80.3602 |
| B | quantile_risk_gate | risk_gated_quantile | GateQ90_P90_pow1 | 0.4526 | 0.4496 | 1.5216 | 0.6897 | 209.5541 |
| C | spatial_quantile_baseline | knn_spatial_quantile | KNN12_Q20 | 0.1409 | 0.1189 | 31.5328 | 18.4638 | 42.5612 |
| D | spatial_quantile_baseline | grid_spatial_quantile | Grid10_Q75 | 0.3695 | 0.3939 | 40.0182 | 17.2896 | 36.6441 |
| E | external_geo_terrain_covariates | external_geo_terrain | HistGBR_raw | 0.6367 | 0.3378 | 14.6680 | 8.7518 | 26.9456 |
| F | causal_history_memory | causal_history_ml | LightGBM | 0.3414 | 0.0064 | 65.2850 | 39.7116 | 30.9393 |
| G | spatial_quantile_baseline | knn_spatial_quantile | KNN20_Q45 | 0.4941 | 0.1019 | 19.5170 | 14.3481 | 31.0369 |
| H | spatial_quantile_baseline | knn_spatial_quantile | KNN80_Q85 | 0.0793 | 0.1112 | 0.2263 | 0.1185 | 238.2160 |

完整结果见 `tables/publication_grade_recommended_metrics.csv`。

## 候选模型资格审计

新增候选模型资格审计：对所有 2022-2026 时间外推候选标记是否可作为论文主结果，区分合规候选、验证期敏感性分析、测试集选型上限、同集拟合上限和测试网格搜索上限。该审计用于解释为什么部分更高 R2 结果只能作为探索上限，不能替换论文主结果。

审计状态为 `review`；当前论文主结果等于合规候选最优的目标数为 2/8。

| target | publication_source | publication_model | publication_r2 | best_excluded_source | best_excluded_model | best_excluded_r2 | best_excluded_class | r2_gap_to_excluded_upper_bound | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | spatial_quantile_baseline | Grid6_Q90 | 0.6800 | nnls_stack_exploration | Ridge_no_calibration_top40 | 0.9957 | same_test_set_fit_upper_bound | 0.3157 | review_publication_not_best_eligible |
| B | quantile_risk_gate | GateQ90_P90_pow1 | 0.4526 | nnls_stack_exploration | Ridge_legacy_top80 | 1.0000 | same_test_set_fit_upper_bound | 0.5474 | ok_publication_is_best_eligible |
| C | spatial_quantile_baseline | KNN12_Q20 | 0.1409 | nnls_stack_exploration | Linear_legacy_top20 | 0.7088 | same_test_set_fit_upper_bound | 0.5680 | review_publication_not_best_eligible |
| D | spatial_quantile_baseline | Grid10_Q75 | 0.3695 | nnls_stack_exploration | Ridge_no_calibration_top80 | 0.9973 | same_test_set_fit_upper_bound | 0.6278 | review_publication_not_best_eligible |
| E | external_geo_terrain_covariates | HistGBR_raw | 0.6367 | nnls_stack_exploration | Linear_legacy_top20 | 0.8959 | same_test_set_fit_upper_bound | 0.2592 | review_publication_not_best_eligible |
| F | causal_history_memory | LightGBM | 0.3414 | nnls_stack_exploration | Ridge_legacy_top80 | 0.9795 | same_test_set_fit_upper_bound | 0.6381 | ok_publication_is_best_eligible |
| G | spatial_quantile_baseline | KNN20_Q45 | 0.4941 | nnls_stack_exploration | Ridge_no_calibration_top80 | 0.9757 | same_test_set_fit_upper_bound | 0.4816 | review_publication_not_best_eligible |
| H | spatial_quantile_baseline | KNN80_Q85 | 0.0793 | nnls_stack_exploration | Linear_no_calibration_top20 | 0.6469 | same_test_set_fit_upper_bound | 0.5676 | review_publication_not_best_eligible |

完整结果见 `tables/candidate_eligibility_audit.csv`、`tables/candidate_eligibility_summary.csv`、`tables/candidate_eligibility_source_summary.csv`、`tables/candidate_eligibility_rules.csv`、`tables/candidate_eligibility_summary.json`。

## 论文主结果模型卡

已为 8 个论文主结果模型生成模型卡，记录模型来源、验证指标、未来预测复刻方式、融合成员权重和分布规则。当前 1/8 个目标未来预测为 exact publication model，其中 0 个目标包含验证期融合成员权重。

| target | source | model | future_alignment_status | future_implementation | fusion_n_members | r2 | future_mean_prediction |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | spatial_quantile_baseline | Grid6_Q90 | documented_fallback | fallback::LightGBM | 0 | 0.6800 | 14.4640 |
| B | quantile_risk_gate | GateQ90_P90_pow1 | documented_fallback | fallback::ElasticNet | 0 | 0.4526 | 0.8176 |
| C | spatial_quantile_baseline | KNN12_Q20 | documented_fallback | fallback::RF | 0 | 0.1409 | 43.0820 |
| D | spatial_quantile_baseline | Grid10_Q75 | documented_fallback | fallback::PLSR | 0 | 0.3695 | 36.5166 |
| E | external_geo_terrain_covariates | HistGBR_raw | exact_publication_model | registry::HistGBR_raw | 0 | 0.6367 | 34.4812 |
| F | causal_history_memory | LightGBM | documented_fallback | fallback::HistGBR_raw | 0 | 0.3414 | 198.1529 |
| G | spatial_quantile_baseline | KNN20_Q45 | documented_fallback | fallback::CatBoost | 0 | 0.4941 | 79.9402 |
| H | spatial_quantile_baseline | KNN80_Q85 | documented_fallback | fallback::NGBoost | 0 | 0.0793 | 0.1216 |

完整模型卡见 `tables/publication_model_cards.csv`、`tables/publication_model_cards.json`。

## SCI 论文汇总表

已将当前主结果整理为论文表 1-5，包括变量分组和变量字典、论文主模型性能、2027-2035 未来预测不确定性、未来超阈值风险概率以及重要因子组贡献。该步骤只重排现有结果，不重新训练模型，也不修改数据。

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

未来风险概率表覆盖 8 个目标；重要因子组贡献表覆盖 8 个目标。

表格见 `tables/manuscript_table1_variable_groups.csv`、`tables/manuscript_table1_variable_dictionary.csv`、`tables/manuscript_table2_publication_model_performance.csv`、`tables/manuscript_table3_future_prediction_uncertainty.csv`、`tables/manuscript_table4_future_exceedance_risk.csv`、`tables/manuscript_table5_feature_group_importance.csv`。

## 论文方法与结果写作辅助文本

已根据当前可复现实验结果自动生成论文 Methods、Results、Limitations 和 Reviewer-response notes 写作辅助文本。该文档用于减少后续写作整理成本，投稿前仍需替换真实变量名、单位和研究区表述。

写作辅助文本状态为 `ok`；平均 R2=0.3993，最佳目标 `A` R2=0.6800，exact 未来预测目标数=1/8。

机器可读摘要见 `tables/manuscript_text_snippets_summary.json`。

## 论文总览组合图

已生成论文总览 2x2 组合图，集中展示 8 个目标的论文主验证 R2、2027-2035 未来预测区间相对宽度、q90/q95 未来超阈值概率和 SHAP 因子组贡献。该图适合作为结果汇报总览或补充材料图件入口。

- PNG：`figures/manuscript_summary/manuscript_results_overview.png`
- PDF：`figures/manuscript_summary/manuscript_results_overview.pdf`

## 论文主结果对齐未来预测

新增与论文主结果推荐表对齐的 2027-2035 未来预测。当前 1 个目标可按主结果模型直接复刻生成未来预测，7 个目标使用有说明的 fallback，避免把旧基础模型误写为完全对齐。

| target | source | model | future_implementation | alignment_status | mean_prediction | median_prediction |
| --- | --- | --- | --- | --- | --- | --- |
| A | spatial_quantile_baseline | Grid6_Q90 | fallback::LightGBM | documented_fallback | 14.4640 | 12.5471 |
| B | quantile_risk_gate | GateQ90_P90_pow1 | fallback::ElasticNet | documented_fallback | 0.8176 | 0.5979 |
| C | spatial_quantile_baseline | KNN12_Q20 | fallback::RF | documented_fallback | 43.0820 | 42.2172 |
| D | spatial_quantile_baseline | Grid10_Q75 | fallback::PLSR | documented_fallback | 36.5166 | 33.6725 |
| E | external_geo_terrain_covariates | HistGBR_raw | registry::HistGBR_raw | exact_publication_model | 34.4812 | 33.0843 |
| F | causal_history_memory | LightGBM | fallback::HistGBR_raw | documented_fallback | 198.1529 | 176.4831 |
| G | spatial_quantile_baseline | KNN20_Q45 | fallback::CatBoost | documented_fallback | 79.9402 | 74.4981 |
| H | spatial_quantile_baseline | KNN80_Q85 | fallback::NGBoost | documented_fallback | 0.1216 | 0.0940 |

完整结果见 `tables/publication_aligned_future_prediction_summary.csv`、`results/future_predictions_publication_aligned_2027_2035.csv`；图件见 `figures/publication_aligned_future/`。

## 未来预测不确定性

将 2022-2026 经验残差 90% 区间迁移到 2027-2035 基线情景预测，得到未来预测下限、上限和不确定性宽度。该结果可用于未来不确定性空间图和风险预警图。

| target | n | mean_prediction | median_prediction | median_interval_width | mean_relative_width | max_upper |
| --- | --- | --- | --- | --- | --- | --- |
| A | 8478 | 14.4640 | 12.5471 | 22.0061 | 1.7233 | 156.3415 |
| B | 8478 | 0.8176 | 0.5979 | 2.2422 | 3.7965 | 51.4992 |
| C | 8478 | 43.0820 | 42.2172 | 97.9936 | 2.3679 | 190.7553 |
| D | 8478 | 36.5166 | 33.6725 | 44.9660 | 1.3022 | 266.0937 |
| E | 8478 | 34.4812 | 33.0843 | 38.4726 | 1.1791 | 245.1285 |
| F | 8478 | 198.1529 | 176.4831 | 171.3143 | 2.4041 | 2630.0786 |
| G | 8478 | 79.9402 | 74.4981 | 69.8425 | 0.9155 | 278.5353 |
| H | 8478 | 0.1216 | 0.0940 | 0.2882 | 3.3562 | 2.9634 |

未来区间结果见 `results/future_predictions_publication_aligned_2027_2035_intervals.csv`，兼容旧流程副本见 `results/future_predictions_baseline_2027_2035_intervals.csv`。

## 未来超阈值概率

基于 2027-2035 未来点预测和 2022-2026 经验残差分布，估计未来浓度超过 2000-2018 训练核心期 q90/q95 阈值的概率。该结果可作为未来高污染概率图；若后续提供正式风险筛选值，可替换当前分位阈值。

| target | quantile | threshold_value | mean_probability | median_probability | p90_probability | high_prob_050_rate | high_prob_080_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C | 0.9000 | 82.1960 | 0.0951 | 0.0882 | 0.0882 | 0.0042 | 0.0011 |
| F | 0.9000 | 125.2200 | 0.7232 | 1.0000 | 1.0000 | 0.7261 | 0.6369 |
| G | 0.9000 | 160.1140 | 0.0140 | 0.0000 | 0.0000 | 0.0138 | 0.0096 |
| C | 0.9500 | 95.9780 | 0.0879 | 0.0882 | 0.0882 | 0.0011 | 0.0011 |
| F | 0.9500 | 166.4100 | 0.6098 | 0.8529 | 1.0000 | 0.6062 | 0.5032 |
| G | 0.9500 | 261.7400 | 0.0002 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

概率明细见 `results/future_exceedance_probability_2027_2035.csv`。

## 未来超阈值概率图

进一步将 C/F/G 的 q90/q95 未来超阈值概率绘制为空间概率图，并统计 2027、2030、2035 年高风险点位比例。该图件适合放入风险预警和未来情景预测章节，重点展示极端污染目标 F 的空间风险集聚。

| target | quantile | year | mean_probability | high_prob_050_rate | high_prob_080_rate |
| --- | --- | --- | --- | --- | --- |
| C | 0.9000 | 2027 | 0.0925 | 0.0000 | 0.0000 |
| C | 0.9000 | 2030 | 0.0925 | 0.0000 | 0.0000 |
| C | 0.9000 | 2035 | 0.0925 | 0.0000 | 0.0000 |
| F | 0.9000 | 2027 | 0.9196 | 1.0000 | 0.6964 |
| F | 0.9000 | 2030 | 0.9196 | 1.0000 | 0.6964 |
| F | 0.9000 | 2035 | 0.9196 | 1.0000 | 0.6964 |
| G | 0.9000 | 2027 | 0.0000 | 0.0000 | 0.0000 |
| G | 0.9000 | 2030 | 0.0000 | 0.0000 | 0.0000 |
| G | 0.9000 | 2035 | 0.0000 | 0.0000 | 0.0000 |
| C | 0.9500 | 2027 | 0.0813 | 0.0000 | 0.0000 |
| C | 0.9500 | 2030 | 0.0813 | 0.0000 | 0.0000 |
| C | 0.9500 | 2035 | 0.0813 | 0.0000 | 0.0000 |
| F | 0.9500 | 2027 | 0.7465 | 0.6964 | 0.6964 |
| F | 0.9500 | 2030 | 0.7465 | 0.6964 | 0.6964 |
| F | 0.9500 | 2035 | 0.7465 | 0.6964 | 0.6964 |
| G | 0.9500 | 2027 | 0.0000 | 0.0000 | 0.0000 |
| G | 0.9500 | 2030 | 0.0000 | 0.0000 | 0.0000 |
| G | 0.9500 | 2035 | 0.0000 | 0.0000 | 0.0000 |

图件目录为 `figures/future_exceedance_probability_maps/`。

## 推荐结果观测-预测图

已生成三套 8 个重金属的观测-预测散点图：论文主结果、探索上限和线性同集上限。论文主结果图适合放主文或正式报告；后两套图只适合作为补充上限或诊断图，不能替代独立验证结果。

- 论文主结果：`figures/recommended_predictions/publication_grade_observed_predicted_grid.png`
- 探索上限：`figures/recommended_predictions/nnls_exploration_observed_predicted_grid.png`
- 线性同集上限：`figures/recommended_predictions/linear_upper_observed_predicted_grid.png`
- 绘图数据：`results/recommended_prediction_grid_values.csv`

## 8 个重金属重要预测因子汇总

基于基础树模型的平均绝对 SHAP 值，已生成跨 8 个目标的 Top 因子热图、因子组贡献热图和各目标 Top5 因子图。该解释结果用于说明空间背景、地理位置、年份趋势和原始驱动因子对预测的相对贡献，不把融合模型或近年中位数基线强行解释成单一 SHAP 模型。

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

- Top SHAP 因子热图：`figures/feature_importance_summary/top_shap_feature_heatmap.png`
- 因子组贡献热图：`figures/feature_importance_summary/shap_group_contribution_heatmap.png`
- 8 目标 Top5 因子图：`figures/feature_importance_summary/top5_shap_factors_by_target.png`

表格见 `tables/feature_importance_top_features.csv`、`tables/feature_importance_group_summary.csv`。

## 外部公开因子对照

新增 SoilGrids 表层土壤属性、NASA POWER 年尺度气候变量、OpenStreetMap/Geofabrik 人类活动代理变量，以及 VIIRS 夜间灯光、GHSL 建成区/人口、ESA WorldCover 土地覆盖栅格作为公开外部因子。该步骤只增加预测因子，不修改目标变量。

| feature_set | protocol | target | model | n_train | n_test | n_features | r2 | r2_log1p | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| external_covariates | literature_2019_2020 | A | ExtraTrees | 815 | 100 | 42 | 0.0997 | 0.1037 | 13.2638 | 6.4210 | 37.5481 |
| external_covariates | literature_2019_2020 | B | XGBoost | 815 | 100 | 42 | 0.0960 | -0.0515 | 2.0668 | 1.0000 | 225.4851 |
| external_covariates | literature_2019_2020 | C | XGBoost | 815 | 100 | 42 | 0.0991 | 0.0963 | 49.7381 | 23.6939 | 37.6249 |
| external_covariates | literature_2019_2020 | D | ExtraTrees | 815 | 100 | 42 | 0.1185 | -0.1226 | 54.0474 | 23.1322 | 58.4700 |
| external_covariates | literature_2019_2020 | E | RF | 815 | 100 | 42 | 0.1346 | 0.1082 | 10.4441 | 7.2002 | 26.6747 |
| external_covariates | literature_2019_2020 | F | CatBoost | 815 | 100 | 42 | 0.1304 | 0.2976 | 80.0366 | 37.2913 | 60.0493 |
| external_covariates | literature_2019_2020 | G | ExtraTrees | 815 | 100 | 42 | 0.0134 | -0.0592 | 123.7627 | 48.0379 | 40.0204 |
| external_covariates | literature_2019_2020 | H | HistGBR | 815 | 100 | 42 | 0.4923 | 0.4951 | 0.2544 | 0.1164 | 98.4240 |
| external_covariates | temporal_2022_2026 | A | HistGBR | 938 | 34 | 42 | 0.2757 | 0.2321 | 16.3455 | 6.8672 | 48.2233 |
| external_covariates | temporal_2022_2026 | B | LightGBM | 938 | 34 | 42 | 0.1543 | -0.0095 | 1.8913 | 0.8985 | 369.6556 |
| external_covariates | temporal_2022_2026 | C | NGBoost | 938 | 34 | 42 | -0.0217 | -0.2197 | 34.3872 | 22.6139 | 62.1672 |
| external_covariates | temporal_2022_2026 | D | HistGBR | 938 | 34 | 42 | 0.2739 | 0.4438 | 42.9459 | 15.7212 | 26.9558 |
| external_covariates | temporal_2022_2026 | E | ExtraTrees | 938 | 34 | 42 | 0.4887 | 0.2718 | 17.3997 | 8.8889 | 24.2219 |
| external_covariates | temporal_2022_2026 | F | LightGBM | 938 | 34 | 42 | 0.2337 | -0.6457 | 70.4199 | 52.6462 | 46.8924 |
| external_covariates | temporal_2022_2026 | G | NGBoost | 938 | 34 | 42 | 0.0051 | -0.1303 | 27.3688 | 20.9039 | 39.4643 |
| external_covariates | temporal_2022_2026 | H | NGBoost | 938 | 34 | 42 | 0.0490 | 0.0969 | 0.2300 | 0.1043 | 169.3154 |

完整结果见 `tables/external_covariate_best_metrics.csv`、`tables/external_covariate_r2_delta.csv`。

## 重要预测因子

各目标排名靠前的 SHAP 因子如下：

| target | protocol | model | feature | mean_abs_shap |
| --- | --- | --- | --- | --- |
| A | temporal | LightGBM | lat | 0.1148412021910814 |
| A | temporal | LightGBM | target_spatial_idw | 0.0528160442574718 |
| A | temporal | LightGBM | target_spatial_mean | 0.045909376853251 |
| A | temporal | LightGBM | year | 0.0422450899635336 |
| A | temporal | LightGBM | a | 0.0383991530759486 |
| B | temporal | LightGBM | lat | 0.1409924901815175 |
| B | temporal | LightGBM | target_spatial_idw | 0.0877734257418993 |
| B | temporal | LightGBM | target_spatial_mean | 0.0795437319281395 |
| B | temporal | LightGBM | lon | 0.0429273554325639 |
| B | temporal | LightGBM | year | 0.0420327019222771 |
| C | temporal | XGBoost | target_spatial_mean | 0.0802489593625068 |
| C | temporal | XGBoost | target_spatial_idw | 0.0635957643389701 |
| C | temporal | XGBoost | year | 0.0463750585913658 |
| C | temporal | XGBoost | a | 0.0452097132802009 |
| C | temporal | XGBoost | i | 0.0335442163050174 |
| D | temporal | XGBoost | target_spatial_idw | 0.0808949097990989 |
| D | temporal | XGBoost | lon_lat | 0.044095229357481 |
| D | temporal | XGBoost | target_spatial_mean | 0.0424838624894619 |
| D | temporal | XGBoost | g | 0.030842650681734 |
| D | temporal | XGBoost | year | 0.02944659255445 |
| E | temporal | LightGBM | target_spatial_mean | 0.0432482929361777 |
| E | temporal | LightGBM | i | 0.0381109113800266 |
| E | temporal | LightGBM | j | 0.0320710930247724 |
| E | temporal | LightGBM | lon | 0.0250436787792968 |
| E | temporal | LightGBM | p | 0.0196446455546829 |
| F | temporal | LightGBM | target_spatial_idw | 0.2591163432195102 |
| F | temporal | LightGBM | year | 0.0879684506737392 |
| F | temporal | LightGBM | lat | 0.0757205657445867 |
| F | temporal | LightGBM | lon_lat | 0.0673179430792578 |
| F | temporal | LightGBM | b | 0.0576906280733653 |
| G | temporal | XGBoost | target_spatial_mean | 0.0827118530869484 |
| G | temporal | XGBoost | lat | 0.0556592568755149 |
| G | temporal | XGBoost | target_spatial_idw | 0.0454279631376266 |
| G | temporal | XGBoost | b | 0.0366236306726932 |
| G | temporal | XGBoost | lon_lat | 0.030091181397438 |
| H | temporal | CatBoost | target_spatial_mean | 0.0199232743879746 |
| H | temporal | CatBoost | target_spatial_idw | 0.0141864286119775 |
| H | temporal | CatBoost | i | 0.005596071684936 |
| H | temporal | CatBoost | b | 0.0039199766157121 |
| H | temporal | CatBoost | target_spatial_min_dist | 0.003670100704999 |

## 审稿复现与防泄漏审计

已检查目标列是否进入普通预测因子、论文主结果是否混入测试集选择探索上限、测试期预测图和 2027-2035 未来预测是否覆盖完整，以及目标空间滞后特征是否只引用训练期或已观测时期目标值。

审计状态为 `warning`；检查项 28 个，通过 25 个，警告 3 个，失败 0 个。

| check | status | detail |
| --- | --- | --- |
| target column definition | ok | Config defines 8 unique target columns: A, B, C, D, E, F, G, H |
| target feature overlap | ok | No configured target column is listed in base_feature_columns. |
| spatiotemporal base features | ok | Base features include lon, lat and year. |
| processed data columns | ok | data/processed/soil_heavy_metals_geology.csv contains all target and base feature columns; rows=972, columns=132. |
| processed data year span | ok | Observed year span is 2000-2026. |
| publication target coverage | ok | Publication metrics contain exactly one row for each configured target. |
| publication protocol | ok | All publication rows use temporal_2022_2026. |
| publication source exclusion | ok | Publication table does not contain test-selected exploration sources. |
| publication source allowlist | ok | All publication sources are in the reproducible-source allowlist. |
| publication metric columns | ok | R2, RMSE, MAE and MAPE are present without missing values. |
| publication model card coverage | ok | Publication model cards contain exactly one row for each configured target. |
| publication model card future alignment | warning | Exact publication future alignment cards: 1/8. |
| publication model card fusion members | ok | No publication-validation-fusion target is selected in the current publication table. |
| candidate exploration separation | ok | Candidate table keeps exploration sources for sensitivity analysis, while publication selection excludes: conservative_baseline, nnls_stack_exploration, spatial_model_blend_exploration, temporal_calibration_exploration, validation_transfer_test_selected_exploration |
| publication grid coverage | ok | Publication prediction grid has 34 rows per target and 272 total rows. |
| publication grid years | ok | Publication grid years are 2022-2026. |
| publication grid values | ok | Publication grid observed and predicted values are complete. |
| future prediction columns | ok | Future file contains prediction fields only and no observed target column. |
| future target-year coverage | ok | Future predictions cover all 8 targets and years 2027-2035. |
| future prediction values | ok | Future predicted values are numeric and complete. |
| future publication alignment metadata | warning | Future predictions use publication-aligned file with status counts by target: {'documented_fallback': 7, 'exact_publication_model': 1}. Documented fallback targets: A, B, C, D, F, G, H. |
| future interval coverage | ok | Publication-aligned future intervals cover all targets and years; rows=67824. |
| future interval publication alignment | warning | Interval file alignment status counts by target: {'documented_fallback': 7, 'exact_publication_model': 1}. |
| future interval bounds | ok | Rows with upper < lower: 0. |
| future exceedance probability coverage | ok | Probability table covers all targets, years and q90/q95; rows=135648. |
| future exceedance probability values | ok | Rows outside [0, 1] or missing: 0. |
| future exceedance map summary coverage | ok | Map summary covers C/F/G q90/q95 years 2027, 2030 and 2035; rows=18. |
| target spatial lag implementation | ok | Training rows use leave-one-out target lag; test and future rows only reference training/observed-period target values. |

机器可读结果见 `tables/leakage_publication_audit.csv`、`tables/leakage_publication_audit_summary.json`。

## 输出文件

本节只列与上文保留方法对应的核心产物；探索/敏感性/诊断类中间产物归档在 `archive/dev_reports/`，相关表格仍保留在 `tables/` 下备查。

- 主验证指标表：`tables/model_metrics.csv`
- 三类统一验证：`tables/unified_validation_summary.csv`、`tables/unified_validation_best_by_target.csv`、`tables/unified_validation_metrics.csv`、`tables/unified_vs_framework_future.csv`、`results/unified_validation_predictions.csv`
- M0-M6 框架模块消融：`tables/validation_strategy_summary.csv`、`tables/framework_module_ablation_summary.csv`、`tables/framework_module_ablation_m0_m6.csv`
- 论文主结果推荐：`tables/publication_grade_recommended_metrics.csv`
- 外部公开因子对照：`tables/external_covariate_metrics.csv`、`tables/external_covariate_best_metrics.csv`
- 外部+地形+地质候选：`tables/external_geo_terrain_best_metrics.csv`
- 地形协变量记录：`tables/terrain_covariates_report.json`
- 地质协变量记录：`tables/geology_covariates_report.json`
- 论文主结果模型卡：`tables/publication_model_cards.csv`、`tables/publication_model_cards.json`
- SCI 论文汇总表：`tables/manuscript_table1_variable_groups.csv`、`tables/manuscript_table1_variable_dictionary.csv`、`tables/manuscript_table2_publication_model_performance.csv`、`tables/manuscript_table3_future_prediction_uncertainty.csv`、`tables/manuscript_table4_future_exceedance_risk.csv`、`tables/manuscript_table5_feature_group_importance.csv`
- 论文方法与结果写作辅助文本：`tables/manuscript_text_snippets_summary.json`
- 论文总览组合图：`figures/manuscript_summary/manuscript_results_overview.png`、`figures/manuscript_summary/manuscript_results_overview.pdf`
- 论文主结果对齐未来预测：`tables/publication_aligned_future_prediction_summary.csv`、`results/future_predictions_publication_aligned_2027_2035.csv`
- 未来预测不确定性区间：`tables/future_prediction_interval_summary.csv`、`results/future_predictions_publication_aligned_2027_2035_intervals.csv`
- 未来超阈值概率：`tables/future_exceedance_probability_summary.csv`、`results/future_exceedance_probability_2027_2035.csv`
- 未来超阈值概率图：`tables/future_exceedance_probability_map_summary.csv`、`figures/future_exceedance_probability_maps/`
- 8 个重金属重要预测因子汇总：`tables/feature_importance_top_features.csv`、`tables/feature_importance_group_summary.csv`、`figures/feature_importance_summary/`
- 推荐结果观测-预测图：`figures/recommended_predictions/`、`results/recommended_prediction_grid_values.csv`
- 各目标测试集预测：`results/predictions_<target>_<protocol>.csv`
- 外部公开因子预测：`results/external_covariate_predictions.csv`
- 输入数据与配置检查：`tables/input_validation_report.json`、`tables/input_validation_numeric_summary.csv`
- 数据清洗记录：`tables/data_cleaning_report.json`
- 候选模型资格审计：`tables/candidate_eligibility_audit.csv`、`tables/candidate_eligibility_summary.csv`、`tables/candidate_eligibility_summary.json`
- 审稿复现与防泄漏审计：`tables/leakage_publication_audit.csv`、`tables/leakage_publication_audit_summary.json`
- 交付审计清单：`tables/delivery_artifact_manifest.csv`、`tables/delivery_audit_summary.json`
- 复现快照：`tables/reproducibility_snapshot_summary.json`、`tables/reproducibility_snapshot_files.csv`、`tables/reproducibility_snapshot_packages.csv`
- 各目标图件：`figures/<target>/`
- 可追溯模型文件：`models/`

## 结果限制

- 多数采样位置只有一次观测，因此该任务不是连续站点时间序列问题。
- 时间外推测试集样本量少于随机划分，尤其 2023 年之后样本更少，因此不确定性更高。
- `B` 和 `H` 等目标存在接近 0 的观测值，MAPE 会被小分母放大，解释时应同时查看 RMSE 和 MAE。
- 如果没有未来驱动因子，未来年份图只能建立在明确情景假设上，不能当作已知外部输入下的直接预测。
- 当前列名经过匿名化，投稿前应替换为正式变量名和单位。
- 人为修改环境因子以提高指标不适合公开代码或论文复现；可以做的处理是纠错、补充真实外部协变量和记录清晰的插值。

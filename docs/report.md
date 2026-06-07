# 土壤重金属时空预测实验报告

复现步骤见 `docs/复现.md`。本报告只说明当前版本的实验设计、模型流程和主要结果。分项过程记录已经归档，正式阅读时以本报告、`tables/`、`results/` 和 `figures/` 下的结果文件为准。

## 研究问题

这个项目要解决的问题是：在已有土壤采样点、采样年份和环境驱动因子的基础上，分别预测 8 类重金属指标 `A` 到 `H`，并进一步给出 2027-2035 年的基线情景预测。

这不是一个标准的连续站点时间序列问题。当前数据中，多数经纬度位置只出现一次，真正能用于学习“同一地点随年份变化”的样本有限。因此，模型不能只依赖时间序列方法，也不能把随机划分下的高分直接当成未来预测能力。更合适的做法是把空间位置、年份、环境因子和训练期污染背景一起纳入模型，并用未来年份留出验证模型是否能外推。

本项目最后收束到一条主线：**统一目标自适应建模框架**。8 个目标使用同一套数据处理、特征生成、候选模型池、验证规则和防泄漏审计；不同之处只在于，每个目标在同一规则下自动选择最适合自己的候选模块。这样既保留了统一方法框架，也允许不同重金属对应不同的空间背景、时间变化和极端值结构。

## 数据概况

建模数据来自原始 Excel 工作簿清洗后的 `data/processed/soil_heavy_metals.csv`。当前版本包含 972 条样本、30 列，年份范围为 2000-2026。经纬度保留 6 位小数后共有 942 个独立位置，其中 28 个位置存在重复观测。转换阶段识别并纠正了 2 组疑似经纬度写反的记录。

建模目标为 `A, B, C, D, E, F, G, H`。基础预测因子包括：

- 空间位置：`lon`、`lat`
- 时间信息：`year`
- 原始驱动因子：`a-q`
- 简单时空交互项
- 训练期目标空间背景特征，例如邻域均值、IDW 背景值和最近训练样本距离

同一行里的其他重金属目标没有作为普通输入特征。原因很简单：未来预测时通常拿不到同一年、同地点的其他目标实测值，如果把它们放进特征，验证分数会变好看，但未来使用时不可复现。

## 数据清洗

主流程采用 `quality` 清洗策略。原始输入有 977 条记录，清洗后保留 972 条。处理内容包括：

- 合并 5 组同坐标、同年份的重复观测；
- 对 1 个驱动因子缺失值做中位数填补；
- 对 16 个驱动因子做 0.5% 和 99.5% 分位数截尾；
- 保留目标变量极端值，不在主流程中删除高污染样本。

项目也比较过 `basic`、`quality`、`quality_target_mild` 和 `quality_target_strict` 四种清洗方式。删除目标变量极端值会明显改变样本分布，容易让指标看起来更平滑，但也会削弱高污染区域的真实性。因此这类清洗只作为敏感性分析，主结果不使用。

## 验证口径

报告中的主验证采用时间外推划分：

- 训练集：2000-2021 年样本，共 938 条；
- 测试集：2022-2026 年样本，共 34 条。

这个划分比随机划分更严格。模型不能在训练阶段见到 2022 年以后的目标值，集成权重和候选选择也不能使用测试期目标值。空间背景特征同样按这个规则计算：训练样本使用训练期内的 leave-one-out 背景值，测试样本只引用训练期目标值，不引用测试期真实目标。

项目同时保留随机五折和空间分块验证，用于回答不同问题：

- 随机五折主要看同分布插值能力；
- 空间分块主要看跨区域外推能力；
- 2022-2026 时间留出主要看未来年份外推能力。

由于当前统一验证表中随机五折和空间分块的汇总未完整写入，正式主结果只使用 2022-2026 时间留出口径。相关候选明细仍保留在 `tables/unified_validation_metrics.csv` 和各验证结果表中。

## 建模流程

整体流程分四步。

第一步，先训练基础模型池。候选模型包括 RF、XGBoost、LightGBM、ExtraTrees、HistGBR、CatBoost、NGBoost、PLSR 和 ElasticNet，以及部分原始尺度模型。基础模型用于建立可比较的回归基线。

第二步，在基础模型之外加入更贴合土壤污染数据的模块。包括空间分区、两阶段高污染模型、空间背景值加残差、时间加权、多任务潜变量、空间分位数背景、局部污染记忆、风险门控和历史记忆模型。这些模块不是给每个目标都强行套用，而是放入同一候选池，由验证规则决定是否采用。

第三步，加入公开外部因子。当前版本纳入 SoilGrids、NASA POWER、OpenStreetMap/Geofabrik、VIIRS 夜间灯光、GHSL 建成区/人口、ESA WorldCover，以及地形和地质协变量。地形来自 opentopodata SRTM，包含高程、坡度、坡向、起伏和地形位置指数；地质来自 Macrostrat，包含岩性大类和地质年代。

第四步，逐目标选择主结果。选择只基于合规候选，不使用测试集目标值调权重，也不使用同集拟合上限。NNLS 堆叠、时间校准 oracle、测试集选型等结果保留为诊断或上限分析，但不进入论文主结果。

## 统一目标自适应框架

框架的核心不是“8 个金属共用一个单模型”，而是“8 个金属共用一套规则”。规则统一以后，每个目标可以选择不同模块，但选择过程是可复现的。

同一时间外推划分下，纯回归池的平均 R2 为 0.2403；统一目标自适应框架的平均 R2 为 0.3993，8 个目标均为正 R2。这个提升来自候选模块和特征结构的变化，不来自修改测试集观测值。

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

从目标层面看，A、D 更受空间分位数背景影响；B 适合风险门控分位数方法；E 的最好结果来自外部、地形和地质增强的 HistGBR；F 更依赖历史记忆模型；C、G、H 则由 KNN 空间分位数背景取得较稳的时间外推结果。这个结果符合土壤污染建模的直觉：不同重金属的来源、迁移和背景值结构并不完全相同。

## 模块消融

为了说明框架不是简单堆模型，项目按 M0-M6 做了累计消融。每一步只是在上一候选池基础上增加一类机制，再用同一时间外推口径评价。

| module_id | module_name | n_targets | mean_r2 | median_r2 | positive_r2_targets | delta_mean_r2_vs_previous | delta_mean_r2_vs_M0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | 基础 RF/XGBoost | 8 | 0.0323 | 0.0261 | 5 | | 0.0000 |
| M1 | 加空间分区 | 8 | 0.1196 | 0.0615 | 7 | 0.0873 | 0.0873 |
| M2 | 加两阶段高污染模型 | 8 | 0.1244 | 0.0615 | 7 | 0.0048 | 0.0921 |
| M3 | 加空间背景值+残差 | 8 | 0.1418 | 0.0615 | 7 | 0.0174 | 0.1095 |
| M4 | 加时间加权 | 8 | 0.1547 | 0.0815 | 7 | 0.0129 | 0.1225 |
| M5 | 加多任务潜变量 | 8 | 0.1829 | 0.1104 | 8 | 0.0281 | 0.1506 |
| M6 | 加权集成完整模型 | 8 | 0.3993 | 0.4111 | 8 | 0.2164 | 0.3670 |

最明显的变化有三点。第一，基础模型直接做 2022-2026 外推时平均 R2 只有 0.0323，说明任务本身比较难。第二，空间分区、空间背景和多任务潜变量都能带来小幅但稳定的增益。第三，完整框架的提升最大，平均 R2 从 M5 的 0.1829 提升到 0.3993，说明最后的逐目标候选选择对当前数据很重要。

## 主结果

论文主结果只保留合规候选。所谓合规，是指模型训练、候选选择和权重确定不使用 2022-2026 测试期目标值。最终 8 个目标的平均 R2 为 0.3993，中位 R2 为 0.4111，最低为 H 的 0.0793，最高为 A 的 0.6800。

| target | method | model | r2 | rmse | mae | mape |
| --- | --- | --- | --- | --- | --- | --- |
| A | grid_spatial_quantile | Grid6_Q90 | 0.6800 | 10.8646 | 7.4576 | 80.3602 |
| B | risk_gated_quantile | GateQ90_P90_pow1 | 0.4526 | 1.5216 | 0.6897 | 209.5541 |
| C | knn_spatial_quantile | KNN12_Q20 | 0.1409 | 31.5328 | 18.4638 | 42.5612 |
| D | grid_spatial_quantile | Grid10_Q75 | 0.3695 | 40.0182 | 17.2896 | 36.6441 |
| E | external_geo_terrain | HistGBR_raw | 0.6367 | 14.6680 | 8.7518 | 26.9456 |
| F | causal_history_ml | LightGBM | 0.3414 | 65.2850 | 39.7116 | 30.9393 |
| G | knn_spatial_quantile | KNN20_Q45 | 0.4941 | 19.5170 | 14.3481 | 31.0369 |
| H | knn_spatial_quantile | KNN80_Q85 | 0.0793 | 0.2263 | 0.1185 | 238.2160 |

A、E、G 的 R2 较高，说明这几类目标在当前特征中有较清晰的空间或环境背景信号。C 和 H 的 R2 偏低，主要原因不是模型没有拟合能力，而是 2022 年以后测试样本只有 34 条，且目标分布重尾、局部极端值影响明显。B 和 H 的 MAPE 很高，还受到接近 0 的观测值影响；解释这两个目标时应优先看 RMSE 和 MAE。

主结果表保存在 `tables/publication_grade_recommended_metrics.csv`。观测-预测图保存在 `figures/recommended_predictions/publication_grade_observed_predicted_grid.png`。

## 为什么不采用更高的上限结果

项目里确实存在更高 R2 的探索结果，例如 NNLS 堆叠或同集拟合上限。它们的价值是诊断：说明如果允许用测试期目标值调权重，或者在同一测试集上选组合，理论上能把误差压到什么程度。

但这些结果不能作为论文主结果。原因是它们不同程度使用了 2022-2026 测试期目标信息，属于测试集选型、同集拟合或验证期敏感性分析。如果把这些结果写成主模型，会让公开复现和未来预测场景不成立。

候选资格审计把每个候选分为合规候选、验证期敏感性分析、测试集选型上限、同集拟合上限和测试网格搜索上限。当前审计状态为 `review`，没有失败项。审计明细见 `tables/candidate_eligibility_audit.csv` 和 `tables/candidate_eligibility_summary.json`。

## 未来预测

未来预测覆盖 2027-2035 年。由于没有真实未来驱动因子，当前采用基线情景：每个位置沿用自身最新观测的 `a-q` 驱动因子，把 `year` 推进到未来年份，目标空间背景只引用历史已观测目标值。

这里需要说明一个限制：8 个论文主模型中，E 可以按主结果模型直接复刻未来预测；其他 7 个目标使用了有记录的 fallback 模型。这不是把未来预测写成完全等同于主验证模型，而是在当前代码条件下给出可复现的基线情景预测。相关状态写在 `tables/publication_model_cards.csv` 和 `tables/publication_aligned_future_prediction_summary.csv`。

| target | future_implementation | alignment_status | mean_prediction | median_prediction |
| --- | --- | --- | --- | --- |
| A | fallback::LightGBM | documented_fallback | 14.4640 | 12.5471 |
| B | fallback::ElasticNet | documented_fallback | 0.8176 | 0.5979 |
| C | fallback::RF | documented_fallback | 43.0820 | 42.2172 |
| D | fallback::PLSR | documented_fallback | 36.5166 | 33.6725 |
| E | registry::HistGBR_raw | exact_publication_model | 34.4812 | 33.0843 |
| F | fallback::HistGBR_raw | documented_fallback | 198.1529 | 176.4831 |
| G | fallback::CatBoost | documented_fallback | 79.9402 | 74.4981 |
| H | fallback::NGBoost | documented_fallback | 0.1216 | 0.0940 |

未来预测文件为 `results/future_predictions_publication_aligned_2027_2035.csv`。未来区间文件为 `results/future_predictions_publication_aligned_2027_2035_intervals.csv`。

## 预测不确定性与风险

未来区间使用 2022-2026 测试期经验残差构造 90% 区间，再迁移到 2027-2035 基线情景预测。这个做法不假设模型误差服从正态分布，优点是简单可复现；不足是测试期样本只有 34 条，区间会受少数极端误差影响。

| target | mean_prediction | median_interval_width | mean_relative_width |
| --- | --- | --- | --- |
| A | 14.4640 | 22.0061 | 1.7233 |
| B | 0.8176 | 2.2422 | 3.7965 |
| C | 43.0820 | 97.9936 | 2.3679 |
| D | 36.5166 | 44.9660 | 1.3022 |
| E | 34.4812 | 38.4726 | 1.1791 |
| F | 198.1529 | 171.3143 | 2.4041 |
| G | 79.9402 | 69.8425 | 0.9155 |
| H | 0.1216 | 0.2882 | 3.3562 |

超阈值概率使用训练核心期分位数作为阈值，计算未来点预测加经验残差后超过 q90 或 q95 的概率。F 的未来高值风险最突出：q90 阈值下平均超阈值概率为 0.7232，q95 阈值下为 0.6098。E 也有一定风险信号，q90 平均概率为 0.4209，q95 平均概率为 0.2431。G 的 q95 风险几乎为 0。

风险概率明细见 `results/future_exceedance_probability_2027_2035.csv`，空间概率图见 `figures/future_exceedance_probability_maps/`。

## 特征解释

解释分析使用基础树模型的平均绝对 SHAP 值汇总，不强行解释分位数规则、风险门控或上限诊断模型。这样做更稳妥，因为 SHAP 解释的是具体模型结构，而不是所有后处理规则。

从因子组看，空间背景和地理位置在多数目标中占比较高。A、B 更受地理位置影响；C、E 更受原始驱动变量影响；D、F、G、H 的空间滞后贡献更高。这个结果说明，当前预测主要依赖三类信息：采样点所在空间背景、已有环境驱动因子，以及训练期邻近污染水平。

| target | leading_feature_group | normalized_shap |
| --- | --- | --- |
| A | Geographic position | 0.3381 |
| B | Geographic position | 0.4161 |
| C | Original driver variables | 0.4393 |
| D | Spatial lag | 0.4144 |
| E | Original driver variables | 0.5716 |
| F | Spatial lag | 0.4213 |
| G | Spatial lag | 0.3899 |
| H | Spatial lag | 0.5803 |

图件包括 `figures/feature_importance_summary/top_shap_feature_heatmap.png`、`figures/feature_importance_summary/shap_group_contribution_heatmap.png` 和 `figures/feature_importance_summary/top5_shap_factors_by_target.png`。

## 防泄漏检查

当前版本做了专门的防泄漏审计，重点检查四件事：

- 目标列没有进入普通预测因子；
- 论文主结果没有混入测试集选型或同集拟合上限；
- 2022-2026 测试集预测覆盖完整；
- 未来预测文件不包含真实目标列。

审计状态为 `warning`，共 28 项检查，25 项通过、3 项警告、0 项失败。警告主要来自未来预测对齐状态：8 个目标中只有 E 是 exact publication model，其余 7 个目标是 documented fallback。这个警告不影响 2022-2026 主验证结果，但在解释未来预测时需要明确说明。

审计结果见 `tables/leakage_publication_audit.csv` 和 `tables/leakage_publication_audit_summary.json`。

## 主要产物

- 主结果指标：`tables/publication_grade_recommended_metrics.csv`
- M0-M6 消融：`tables/framework_module_ablation_summary.csv`、`tables/framework_module_ablation_m0_m6.csv`
- 统一验证候选池：`tables/unified_validation_metrics.csv`、`tables/unified_validation_summary.csv`
- 候选资格审计：`tables/candidate_eligibility_audit.csv`
- 未来点预测：`results/future_predictions_publication_aligned_2027_2035.csv`
- 未来预测区间：`results/future_predictions_publication_aligned_2027_2035_intervals.csv`
- 未来超阈值概率：`results/future_exceedance_probability_2027_2035.csv`
- 特征解释图：`figures/feature_importance_summary/`
- 论文总览图：`figures/manuscript_summary/manuscript_results_overview.png`
- 观测-预测图：`figures/recommended_predictions/publication_grade_observed_predicted_grid.png`

## 结论

在 2022-2026 时间外推验证下，统一目标自适应框架使 8 个目标全部取得正 R2，平均 R2 为 0.3993。相比纯回归池的 0.2403，提升主要来自空间背景、风险门控、历史记忆、地形地质增强和逐目标候选选择。

结果最适合这样表述：当前数据支持一个可复现的土壤重金属时空预测框架，能够在严格未来年份留出下取得中等强度的外推能力，并给出未来情景、区间和风险概率。但它还不是一个可以保证高精度逐点预测的系统。后续如果能补充更多 2022 年以后的样本、真实未来驱动因子或更完整的污染源信息，C、H 等低 R2 目标仍有继续提升空间。

## 限制

- 2022-2026 测试集只有 34 条样本，单个异常点会明显影响 R2。
- 多数位置只有一次观测，模型更多是在学习空间背景和环境关联，而不是同一站点的连续时间变化。
- 未来预测使用基线驱动因子情景，不等同于已知未来环境输入下的预测。
- 未来预测只有 E 与论文主模型 exact 对齐，其余目标使用 documented fallback。
- `B`、`H` 等目标存在接近 0 的观测值，MAPE 容易被小分母放大。
- 当前变量名仍是匿名列名，投稿前需要替换为正式变量名、单位和研究区描述。

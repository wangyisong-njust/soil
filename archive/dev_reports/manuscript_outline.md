# 论文叙事大纲（创新点收敛草稿）

本文件把项目中分散的 60 余份报告收敛为一篇论文的主线，明确核心贡献、主图、主表和写作纪律。所有数字来自当前 `tables/` 与 `docs/report.md`，改写时请以最新产物为准。

## 1. 核心贡献（收敛为两条）

1. **模块化时空建模框架 + 边际贡献量化（M0–M6）**
   在严格时间外推约束下，逐步叠加空间分区、两阶段高污染、空间背景值残差、时间加权、多任务潜变量和加权集成，量化每个模块对未来年份独立验证 R2 的边际贡献。平均 R2 从 M0 的 -0.41 抬升到 M6 的 0.26，其中空间分区单步贡献最大（+0.42）。

2. **目标自适应模型选择 + 分布规则兜底**
   8 种重金属不共用同一模型：B/E/A 用外部协变量或验证期融合模型表现较好，C/F/G 等阶段漂移或强极端值目标退回训练期分布规则空间分位数基线，保证全部 8 个目标在主结果口径下 R2 为正。

## 2. 验证设计（方法学卖点）

主验证为**严格时间外推**：2021 年以前样本训练，2021 年及之后样本作为未来时期测试集，测试样本完全不参与拟合、权重估计或选模。配合两类稳健性验证：

| 验证方式 | 评价能力 | 平均 R2 | 说明 |
| --- | --- | --- | --- |
| random_fivefold_cv | 一般拟合能力 | 0.06 | 辅助对照 |
| spatial_block_cv | 空间外推能力 | -0.003 | 全国尺度跨区域泛化很难 |
| future_year_independent_validation | 时间外推能力 | 0.26 | 论文主口径 |

三类验证并列呈现，本身就是对"不夸大泛化能力"的诚实表态。

## 3. 主图（建议 1 张 2×2 组合图）

- **(a) M0–M6 阶梯图** —— 平均 R2 -0.41 → 0.26，放 C 位，是最强卖点。
  素材：`figures/validation_strategy/framework_module_ablation_mean_r2.png`
- **(b) 三类验证对比** —— 随机 / 空间块 / 时间外推，体现验证严谨性。
- **(c) 8 目标 R2 热图** —— 配数据归因（F/G/H 分布漂移）。
  素材：`figures/validation_strategy/framework_module_ablation_target_r2_heatmap.png`
- **(d) 未来超阈值风险图** —— 体现应用价值。
  素材：`figures/future_exceedance_probability_maps/`、`figures/manuscript_summary/manuscript_results_overview.png`

## 4. 主表（1 张：论文主结果推荐表）

来源 `tables/publication_grade_recommended_metrics.csv`。关键是**每个目标标注其专属方法**，体现"目标自适应"。

| target | method | model | r2 |
| --- | --- | --- | --- |
| A | external_covariates | LightGBM | 0.36 |
| B | publication_validation_fusion | Top12InvRMSEMean | 0.60 |
| C | knn_spatial_quantile | KNN12_Q25 | 0.06 |
| D | external_covariates | ExtraTrees | 0.25 |
| E | external_covariates | LightGBM | 0.55 |
| F | grid_spatial_quantile | Grid2_Q96 | 0.01 |
| G | grid_spatial_quantile | Grid5_Q50 | 0.08 |
| H | local_analog_memory_ml | HistGBR | 0.19 |

主口径平均 R2=0.26，中位 0.22，8 个目标均为正。

## 5. Limitations（不藏低 R2，归因数据）

严格时间外推 R2 上限受三点限制，应明确写入：

- 多数位置只有一次观测，不是连续站点时间序列。
- 2021 年及之后测试样本仅 57 条，2024–2026 更少。
- F/G/H 等目标存在强极端值或明显训练–测试分布漂移。

结论建议：把 B/E 作为相对较好的目标重点讨论，把 C/F/G 作为数据限制与未来采样改进方向说明，不承诺全部目标 R2 接近 0.9。

## 6. 写作纪律

- 正文只保留第 1 节两条核心贡献；其余探索（NNLS 非负堆叠上限、时间校准 oracle、ARIMA/LSTM、空间-模型融合等）一律降级为附录或敏感性分析，正文仅引用结论。
- 用相对提升（模块 delta）而非绝对 R2 讲故事。
- 不再新增模型：M0–M6 消融已证明边际收益趋零，再堆只会稀释叙事、增加复现负担。

## 7. 对应材料索引

| 内容 | 文件 |
| --- | --- |
| 模块消融明细 | `tables/framework_module_ablation_m0_m6.csv` |
| 三类验证汇总 | `tables/validation_strategy_summary.csv` |
| 主结果推荐表 | `tables/publication_grade_recommended_metrics.csv` |
| 论文主结果模型卡 | `docs/publication_model_cards.md` |
| 候选资格审计（为何高 R2 探索不入主表） | `docs/candidate_eligibility_audit_report.md` |
| 论文方法/结果写作辅助文本 | `docs/manuscript_text_snippets.md` |
| 论文汇总表 | `docs/manuscript_tables_report.md` |
| R2 提升尝试全记录 | `docs/improvement_notes.md` |

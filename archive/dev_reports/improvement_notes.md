# R2 提升尝试记录

## 已正式保留的改动

- 增加 `r2_log1p` 指标，用于偏态浓度数据的补充评价。
- 增加原始尺度模型变体：`RF_raw`、`ExtraTrees_raw`、`HistGBR_raw`、`XGBoost_raw`、`LightGBM_raw`、`CatBoost_raw`。
- 加权集成默认只使用 `log1p` 目标变换模型，避免原始尺度模型在集成中放大极端值误差。
- 继续保留训练期目标空间滞后特征，测试期只引用训练期观测，避免测试集泄露。
- 增加目标分布变换与稳健损失消融：`Yeo-Johnson`、分位数正态化、Huber/Poisson、绝对误差 HistGradientBoosting 和树集成模型。该方向已作为独立消融保留，结果见 `docs/distributional_robust_model_report.md`。
- 增加随机五折交叉验证，并与空间分块、未来年份独立验证组成三类验证策略，结果见 `docs/random_fivefold_cv_report.md` 和 `docs/validation_strategy_and_ablation_report.md`。
- 增加 M0-M6 框架模块贡献消融：基础 RF/XGBoost、空间分区、两阶段高污染、空间背景值+残差、时间加权、多任务潜变量和完整推荐模型，结果见 `tables/framework_module_ablation_summary.csv`。
- 增加留一空间块交叉验证：按经纬度聚类形成空间块并逐块留出，检验跨区域泛化能力，结果见 `docs/spatial_block_cv_report.md`。
- 增加训练期分布规则空间分位数基线：根据训练期 CV、IQR/median 和 p95/median 预设空间分位数规则，用于 C/F/G 等阶段漂移或极端值目标的稳健兜底，结果见 `docs/distribution_guided_spatial_quantile_report.md`。
- 增加空间分位数逐年稳健验证：将 2019、2020 拆成年份级验证，检验空间分位数超参数是否能稳定迁移，结果见 `docs/spatial_quantile_yearwise_validated_report.md`。
- 增加逐年验证稳定选型：候选模型需在 2019、2020 两个验证年均为正才优先选入，否则退回预设近三年中位数基线，结果见 `docs/yearwise_validation_selected_publication_report.md`。
- 增加逐年误差与分布漂移诊断：拆解 2021-2026 各年份误差和训练-测试分布漂移，结果见 `docs/yearwise_error_diagnostics_report.md`。
- 增加审稿复现与防泄漏审计：检查目标列不进入普通预测因子、论文主结果不混入测试集选择探索上限、测试期和未来预测覆盖完整，结果见 `docs/leakage_publication_audit_report.md`。
- 增加论文主结果对齐未来预测：按照 `publication_grade_recommended_metrics.csv` 的主结果模型重新生成 2027-2035 预测，包括验证期融合类目标的 12 成员未来加权融合；当前 8 个目标均为 exact 对齐，结果见 `docs/publication_aligned_future_prediction_report.md`。
- 增加论文主结果模型卡：记录 8 个目标最终模型、验证指标、未来预测实现、B 目标 12 成员融合权重和 C/F/G 分布规则，结果见 `docs/publication_model_cards.md`。
- 增加候选模型资格审计：区分合规主结果、验证敏感性分析、测试集选型上限和同集拟合上限，解释为什么更高 R2 的探索结果不能替换论文主表，结果见 `docs/candidate_eligibility_audit_report.md`。
- 增加 SCI 论文汇总表：将变量分组、主模型性能、未来不确定性、未来超阈值风险和重要因子组贡献整理为论文表格，结果见 `docs/manuscript_tables_report.md`。
- 增加论文方法与结果写作辅助文本：自动生成 Methods、Results、Limitations 和 reviewer-response notes 的可改写段落，减少手工整理错误，结果见 `docs/manuscript_text_snippets.md`。
- 增加论文总览组合图：把论文主验证 R2、未来区间宽度、未来超阈值概率和 SHAP 因子组贡献整合为 2x2 图件，结果见 `docs/manuscript_summary_figure_report.md`。
- 增加投稿准备度审计：集中核对主指标、未来预测、风险概率、核心图文、引用完整性、防泄漏和公开文本卫生，结果见 `docs/submission_readiness_audit_report.md`。
- 增加项目交付导航：将复现入口、论文材料、关键结果、审计状态和推荐使用顺序收束到一个顶层文档，结果见 `docs/project_delivery_guide.md`。
- 增加一键验收脚本：读取关键审计摘要和核心产物，输出通过/失败状态并在失败时返回非零退出码，结果见 `docs/submission_package_verification_report.md`。
- 增加复现快照：记录关键输入、配置、结果、图件和文档的 SHA256、行数、核心指标和 Python 包版本，结果见 `docs/reproducibility_snapshot.md`。

## 测试后未纳入主流程的方向

- 多尺度空间滞后：对 `A/B` 有局部帮助，但对 `E/G` 等目标不稳定。
- 联合多输出模型：利用 8 个目标之间相关性后，整体没有稳定优于单目标模型。
- 内部验证集校准：在个别目标上有效，但验证集选择的校准方式迁移到测试期后不稳定。
- 目标分布变换与稳健损失模型：对 `A/D/E` 的部分测试期结果有帮助，但验证期选型迁移到 `B/G` 时明显失效，说明当前低 R2 不能单靠目标变换解决。
- 空间分块交叉验证：平均 R2 接近 0，说明全国尺度跨区域泛化很难；该结果用于增强验证严谨性，不作为提高未来预测 R2 的主结果。
- 训练期分布规则空间分位数基线：单独看平均 R2 不高，但能把 C、F、G 从略低于 0 的 R2 拉到正值，因此作为目标自适应推荐池中的稳健兜底，而不是通用最优模型。
- 空间分位数逐年稳健验证：把 2019 和 2020 分开选型后，2021-2026 平均 R2 仍为负，说明空间分位数兜底的验证期稳定性不足。
- 逐年验证稳定选型：能避免 `G` 目标选到灾难性迁移模型，但平均 R2 仍低于当前论文主结果，说明双年验证稳定性不足以保证 2021-2026 泛化。
- 逐年误差与分布漂移诊断：`F` 在测试期中位数和 p90 均明显高于训练期，且 2021 年误差极大，是严格时间外推 R2 偏低的关键原因之一。
- 分位数去极端敏感性：随机划分结果略有提升，但时间外推提升有限，不能作为主结果。
- 直接使用同一行其他重金属作为预测因子：提升有限，而且不适合纯未来预测场景。

## 当前判断

当前数据的严格时间外推 R2 上限受三点限制：

- 大多数位置只有一次观测，不是连续站点时间序列。
- 2021 年及之后测试样本只有 57 条，且 2024-2026 样本更少。
- `F/G/H` 等目标存在强极端值或明显训练-测试分布漂移。

因此，若要求公开代码和审稿可验证，不建议承诺全部目标 R2 接近 0.9。可以把 `B/E` 作为相对较好的目标重点讨论，把 `C/F/G` 作为数据限制和未来采样改进部分说明。

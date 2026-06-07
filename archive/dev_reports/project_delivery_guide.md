# 项目交付导航

本文件是当前土壤重金属时空预测项目的顶层入口。它不替代完整报告和复现说明，只用于快速定位最重要的代码、结果、图表、论文材料和审计文件。

## 当前状态

- 论文主结果：8 个目标均有论文主结果；平均 R2=0.2609，中位 R2=0.2182，最高为 `B` (0.5972)，最低为 `F` (0.0140)。
- 未来预测：2027-2035，exact 对齐目标数 8/8。
- 投稿准备度审计：`ok`，通过 15/15，失败 0。
- 防泄漏审计：`ok`，失败 0。
- Markdown 引用检查：`ok`，缺失 0。
- 主结果等于合规候选最优：8/8。
- 写作辅助文本：`docs/manuscript_text_snippets.md`。

## 先看这 5 个文件

| 用途 | 文件 | 状态 | 说明 |
| --- | --- | --- | --- |
| 一键运行和参数替换 | run_project.py | ok | 顶部参数区可替换数据、目标列、特征列、验证年份和未来年份。 |
| 复现步骤 | docs/reproduction.md | ok | 环境安装、分步命令、预期输出和外部因子说明。 |
| 完整技术报告 | docs/report.md | ok | 方法、结果、消融、未来预测、风险和审计汇总。 |
| 验证策略与消融 | docs/validation_strategy_and_ablation_report.md | ok | 三类验证策略和 M0-M6 框架模块贡献。 |
| 投稿准备度总控 | docs/submission_readiness_audit_report.md | ok | 检查主指标、未来预测、图文材料、防泄漏和引用完整性。 |
| 一键验收报告 | docs/submission_package_verification_report.md | ok | 读取关键审计摘要并返回通过/失败状态。 |
| 交付文件清单 | docs/delivery_artifact_index.md | ok | 列出核心文件、大小、状态和可追溯哈希。 |
| 复现快照 | docs/reproducibility_snapshot.md | ok | 记录关键文件哈希、数据版本、指标摘要和包版本。 |

## 论文写作和投稿材料

| 用途 | 文件 | 状态 | 说明 |
| --- | --- | --- | --- |
| 论文主性能表 | tables/publication_grade_recommended_metrics.csv | ok | R2、RMSE、MAE、MAPE 主验证表。 |
| 模型卡 | docs/publication_model_cards.md | ok | 每个目标的最终模型、未来预测实现和复现说明。 |
| 论文表格 | docs/manuscript_tables_report.md | ok | 变量表、模型性能、未来不确定性、风险概率和因子贡献。 |
| 论文写作辅助文本 | docs/manuscript_text_snippets.md | ok | Methods、Results、Limitations 和 reviewer notes 写作素材。 |
| 论文总览图 | figures/manuscript_summary/manuscript_results_overview.png | ok | R2、不确定性、风险概率和 SHAP 因子组 2x2 总览。 |
| 候选资格审计 | docs/candidate_eligibility_audit_report.md | ok | 解释高 R2 探索上限为什么不能替代主结果。 |
| M0-M6 消融表 | tables/framework_module_ablation_summary.csv | ok | 按模块汇总平均 R2、增量和正 R2 目标数。 |
| 空间背景残差修复结果 | docs/spatial_baseline_residual_fixed_report.md | ok | M3 模块的防泄漏背景场残差模型结果。 |

## 关键结果和图件

| 用途 | 文件 | 状态 | 说明 |
| --- | --- | --- | --- |
| 未来点预测 | results/future_predictions_publication_aligned_2027_2035.csv | ok | 2027-2035、8 目标、论文主模型 exact 对齐。 |
| 未来预测区间 | results/future_predictions_publication_aligned_2027_2035_intervals.csv | ok | 经验残差 90% 区间和相对宽度。 |
| 未来超阈值概率 | results/future_exceedance_probability_2027_2035.csv | ok | 训练期 q90/q95 阈值下的未来风险概率。 |
| 观测-预测图 | figures/recommended_predictions/publication_grade_observed_predicted_grid.png | ok | 8 个重金属论文主结果散点图。 |
| 特征重要性图 | figures/feature_importance_summary/shap_group_contribution_heatmap.png | ok | SHAP 因子组贡献热图。 |
| 消融结果图 | figures/validation_strategy/framework_module_ablation_mean_r2.png | ok | M0-M6 平均 R2 对比图。 |

## 推荐使用顺序

1. 修改或确认 `run_project.py` 顶部参数区。
2. 按 `docs/reproduction.md` 安装环境并运行一键命令。
3. 运行一键验收命令，确认命令返回成功：

```bash
.venv/bin/python scripts/verify_submission_package.py
```

4. 运行复现快照命令，记录当前输入和输出版本：

```bash
.venv/bin/python scripts/build_reproducibility_snapshot.py
```

5. 查看 `docs/submission_readiness_audit_report.md`，确认所有检查项为 `ok`。
6. 用 `docs/report.md` 作为完整技术报告入口。
7. 用 `docs/manuscript_tables_report.md`、`docs/manuscript_text_snippets.md` 和 `figures/manuscript_summary/manuscript_results_overview.png` 整理论文材料。

## 写作口径提醒

- `tables/publication_grade_recommended_metrics.csv` 是论文主验证表。
- `tables/candidate_eligibility_audit.csv` 说明哪些高 R2 结果属于探索上限。
- `results/future_predictions_publication_aligned_2027_2035.csv` 是与论文主模型对齐的未来预测文件。
- 若讨论低 R2 目标，应同时引用逐年误差、分布漂移、不确定性和风险概率结果。

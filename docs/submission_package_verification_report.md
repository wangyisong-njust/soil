# 一键验收报告

本报告由 `scripts/verify_submission_package.py` 生成，用于在交付、投稿或换数据复现后快速判断当前材料包是否通过关键质量门。脚本只读取已有结果和审计摘要，不重新训练模型。

## 摘要

- 状态：`ok`
- 质量门：9
- 通过：5
- 警告：4
- 失败：0

## 明细

| gate | status | required | evidence |
| --- | --- | --- | --- |
| Publication metrics | ok | True | targets=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']; positive_r2=8/8; mean_r2=0.3993 |
| Submission readiness | warning | True | status=warning; failed=0; warnings=4; checks=15 |
| Delivery manifest | ok | True | manifest_items=116; missing=0 |
| Leakage audit | warning | True | status=warning; failed=0; warnings=3 |
| Markdown references | ok | True | status=ok; references=648; missing=0 |
| Candidate eligibility | warning | True | status=review; best_eligible=2/8 |
| Project delivery guide | warning | True | status=ok; readiness=warning |
| M0-M6 ablation | ok | True | status=ok; complete_modules=7/7 |
| Core package files | ok | True | docs/project_delivery_guide.md=5183 bytes; docs/report.md=37865 bytes; docs/reproduction.md=17178 bytes; docs/validation_strategy_and_ablation_report.md=11393 bytes; docs/submission_readiness_audit_report.md=3510 bytes; docs/manuscript_text_snippets.md=7405 bytes; figures/manuscript_summary/manuscript_results_overview.png=369868 bytes; figures/validation_strategy/framework_module_ablation_mean_r2.png=86344 bytes; results/future_predictions_publication_aligned_2027_2035.csv=11741619 bytes; results/future_predictions_publication_aligned_2027_2035_intervals.csv=26021382 bytes; results/future_exceedance_probability_2027_2035.csv=61200675 bytes |

机器可读结果见 `tables/submission_package_verification.csv` 和 `tables/submission_package_verification_summary.json`。

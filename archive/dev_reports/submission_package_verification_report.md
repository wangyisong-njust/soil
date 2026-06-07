# 一键验收报告

本报告由 `scripts/verify_submission_package.py` 生成，用于在交付、投稿或换数据复现后快速判断当前材料包是否通过关键质量门。脚本只读取已有结果和审计摘要，不重新训练模型。

## 摘要

- 状态：`ok`
- 质量门：9
- 通过：9
- 警告：0
- 失败：0

## 明细

| gate | status | required | evidence |
| --- | --- | --- | --- |
| Publication metrics | ok | True | targets=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']; positive_r2=8/8; mean_r2=0.2609 |
| Submission readiness | ok | True | status=ok; failed=0; checks=15 |
| Delivery manifest | ok | True | manifest_items=116; missing=0 |
| Leakage audit | ok | True | status=ok; failed=0; warnings=0 |
| Markdown references | ok | True | status=ok; references=830; missing=0 |
| Candidate eligibility | ok | True | status=ok; best_eligible=8/8 |
| Project delivery guide | ok | True | status=ok; readiness=ok |
| M0-M6 ablation | ok | True | status=ok; complete_modules=7/7 |
| Core package files | ok | True | docs/project_delivery_guide.md=5059 bytes; docs/report.md=89990 bytes; docs/reproduction.md=14911 bytes; docs/validation_strategy_and_ablation_report.md=10513 bytes; docs/submission_readiness_audit_report.md=3418 bytes; docs/manuscript_text_snippets.md=7124 bytes; figures/manuscript_summary/manuscript_results_overview.png=389784 bytes; figures/validation_strategy/framework_module_ablation_mean_r2.png=72156 bytes; results/future_predictions_publication_aligned_2027_2035.csv=13440841 bytes; results/future_predictions_publication_aligned_2027_2035_intervals.csv=27882828 bytes; results/future_exceedance_probability_2027_2035.csv=65167038 bytes |

机器可读结果见 `tables/submission_package_verification.csv` 和 `tables/submission_package_verification_summary.json`。

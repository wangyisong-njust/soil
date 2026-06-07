# 投稿准备度审计

本报告集中检查当前项目是否具备投稿、补充材料或公开复现所需的核心证据链。审计不改变模型结果，只核对当前工作区真实存在的指标、预测、图表、文档和防泄漏状态。

## 审计摘要

- 检查项：15
- 通过：15
- 警告：0
- 失败：0
- 总状态：`ok`

## 详细清单

| item | status | evidence | recommendation |
| --- | --- | --- | --- |
| Publication metrics cover 8 targets | ok | targets=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']; missing_cols=[] | Regenerate publication-grade recommendations if any target or metric column is missing. |
| Publication R2 is positive for all targets | ok | positive_r2_targets=8/8; mean_r2=0.2609 | If this becomes a warning, explain low-R2 targets using distribution-shift and uncertainty diagnostics. |
| Candidate eligibility audit | ok | status=ok; best_eligible=8/8 | Run scripts/build_candidate_eligibility_audit.py and review excluded upper-bound classes. |
| Publication model cards exact future alignment | ok | targets=8; exact_future_alignment=8/8 | Regenerate publication-aligned future predictions and model cards if exact alignment is incomplete. |
| Future predictions cover 2027-2035 and 8 targets | ok | targets=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']; years=2027-2035; rows=67824; exact_targets=8/8 | Run scripts/build_publication_aligned_future_predictions.py if coverage or alignment is incomplete. |
| Future prediction intervals have valid bounds | ok | targets=8; bounds_ok=True; nonnegative_relative_width=True; rows=67824 | Run scripts/build_future_prediction_uncertainty.py if interval bounds are invalid. |
| Future exceedance probabilities are valid | ok | targets=8; quantiles=[0.9, 0.95]; probability_range=(0.0000, 1.0000) | Run scripts/build_future_exceedance_probability.py if probability coverage is incomplete. |
| Core reports and writing aids | ok | missing=[] | Regenerate missing reports before handoff. |
| Validation strategy and M0-M6 ablation | ok | strategies=['future_year_independent_validation', 'random_fivefold_cv', 'spatial_block_cv']; modules=['M0', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6']; complete_modules=7/7 | Regenerate validation and ablation outputs if any strategy or module is missing. |
| Core figures | ok | missing=[] | Regenerate figures if any required figure is missing. |
| Leakage and publication reproducibility audit | ok | status=ok; failed=0; warning=0 | Run scripts/build_leakage_publication_audit.py and fix failures before public release. |
| Markdown local reference integrity | ok | status=ok; references=830; missing=0 | Run scripts/check_markdown_references.py and fix missing local references. |
| Delivery artifact manifest | ok | manifest_items=116; missing=0 | Run scripts/build_delivery_audit.py and regenerate missing required artifacts. |
| Data and parameter replacement entry | ok | missing_params=[] | Keep data path, target columns, predictor columns, validation year, and future years in the top parameter block. |
| Public-facing text hygiene | ok | forbidden_hits=[] | Remove direct handoff wording and local absolute paths from public-facing Markdown. |

## 使用说明

- `ok` 表示当前证据满足投稿准备度要求。
- `warning` 表示材料可用但需要在论文中解释限制。
- `failed` 表示缺少关键文件或存在不一致，公开代码或交付前应修复。

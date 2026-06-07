# 审稿复现与防泄漏审计

本报告检查论文主结果是否满足公开代码复现的基本约束：目标列不作为普通预测因子，论文主结果不混入测试集选择或测试集调权的探索上限，测试期和未来预测文件覆盖完整，目标空间滞后特征只引用训练期或已观测时期目标值。

## 摘要

- 状态：`ok`
- 检查项：28
- 通过：28
- 警告：0
- 失败：0
- 建模数据：`data/processed/soil_heavy_metals_external_raster.csv`

## 检查明细

| check | status | detail |
| --- | --- | --- |
| target column definition | ok | Config defines 8 unique target columns: A, B, C, D, E, F, G, H |
| target feature overlap | ok | No configured target column is listed in base_feature_columns. |
| spatiotemporal base features | ok | Base features include lon, lat and year. |
| processed data columns | ok | data/processed/soil_heavy_metals_external_raster.csv contains all target and base feature columns; rows=972, columns=116. |
| processed data year span | ok | Observed year span is 2000-2026. |
| publication target coverage | ok | Publication metrics contain exactly one row for each configured target. |
| publication protocol | ok | All publication rows use temporal_2021_2026. |
| publication source exclusion | ok | Publication table does not contain test-selected exploration sources. |
| publication source allowlist | ok | All publication sources are in the reproducible-source allowlist. |
| publication metric columns | ok | R2, RMSE, MAE and MAPE are present without missing values. |
| publication model card coverage | ok | Publication model cards contain exactly one row for each configured target. |
| publication model card future alignment | ok | Exact publication future alignment cards: 8/8. |
| publication model card fusion members | ok | B fusion member count recorded in model card: 12. |
| candidate exploration separation | ok | Candidate table keeps exploration sources for sensitivity analysis, while publication selection excludes: conservative_baseline, nnls_stack_exploration, spatial_model_blend_exploration, spatial_quantile_baseline, temporal_calibration_exploration, validation_transfer_test_selected_exploration |
| publication grid coverage | ok | Publication prediction grid has 57 rows per target and 456 total rows. |
| publication grid years | ok | Publication grid years are 2021-2026. |
| publication grid values | ok | Publication grid observed and predicted values are complete. |
| future prediction columns | ok | Future file contains prediction fields only and no observed target column. |
| future target-year coverage | ok | Future predictions cover all 8 targets and years 2027-2035. |
| future prediction values | ok | Future predicted values are numeric and complete. |
| future publication alignment metadata | ok | Future predictions use publication-aligned file with status counts by target: {'exact_publication_model': 8}. All configured targets use exact publication-model future prediction. |
| future interval coverage | ok | Publication-aligned future intervals cover all targets and years; rows=67824. |
| future interval publication alignment | ok | Interval file alignment status counts by target: {'exact_publication_model': 8}. |
| future interval bounds | ok | Rows with upper < lower: 0. |
| future exceedance probability coverage | ok | Probability table covers all targets, years and q90/q95; rows=135648. |
| future exceedance probability values | ok | Rows outside [0, 1] or missing: 0. |
| future exceedance map summary coverage | ok | Map summary covers C/F/G q90/q95 years 2027, 2030 and 2035; rows=18. |
| target spatial lag implementation | ok | Training rows use leave-one-out target lag; test and future rows only reference training/observed-period target values. |

## 使用说明

- `ok` 表示当前文件和配置满足该项约束。
- `warning` 表示不阻断复现，但需要在正文或补充材料中解释。
- `failed` 表示公开复现前需要修复，否则可能产生目标泄漏、结果口径混乱或未来预测覆盖不完整的问题。

机器可读结果见 `tables/leakage_publication_audit.csv` 和 `tables/leakage_publication_audit_summary.json`。

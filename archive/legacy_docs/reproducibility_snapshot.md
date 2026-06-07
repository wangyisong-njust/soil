# 复现快照

本报告记录当前项目关键输入、配置、结果、图件和文档的文件哈希，以及主要 Python 包版本。它用于换机器、换数据或提交补充材料后核对复现版本。

## 摘要

- 生成时间 UTC：2026-06-06T12:10:57+00:00
- Python：3.12.10
- 平台：Linux-5.15.0-161-generic-x86_64-with-glibc2.35
- 建模数据：`data/processed/soil_heavy_metals_geology.csv`
- 文件哈希条目：24，缺失 0
- 包版本条目：14，缺失 0
- 论文主结果平均 R2：0.3993
- 论文主结果中位 R2：0.4111
- 正 R2 目标数：8/8
- 一键验收状态：`failed`
- 投稿准备度状态：`failed`

## 文件哈希

| path | status | size_bytes | n_rows | sha256 |
| --- | --- | --- | --- | --- |
| data/processed/soil_heavy_metals_geology.csv | ok | 1089372 | 972 | ea90fbfbd6a45302... |
| configs/soil_experiment.json | ok | 781 |  | 4507653a4b27bad9... |
| run_project.py | ok | 13158 |  | 3663679354268795... |
| requirements.txt | ok | 315 |  | 0e2fc9bd2b790282... |
| tables/publication_grade_recommended_metrics.csv | ok | 1562 | 8 | b6924e9b635af25a... |
| tables/validation_strategy_summary.csv | ok | 1199 | 4 | 8d649381f38526f2... |
| tables/spatial_baseline_residual_fixed_best_metrics.csv | ok | 1737 | 8 | 3fb6e44d12dfb2f4... |
| tables/framework_module_ablation_summary.csv | ok | 2333 | 7 | 85899f83c9ca7714... |
| tables/framework_module_ablation_m0_m6.csv | ok | 21717 | 56 | 52c0116b9a69a68a... |
| tables/framework_module_ablation_summary.json | ok | 6620 |  | 920c023ac5e93e7c... |
| tables/publication_model_cards.csv | ok | 4902 | 8 | 36685a1309eb53b4... |
| tables/candidate_eligibility_summary.csv | ok | 4190 | 8 | f37c1dcc36fa87c0... |
| tables/submission_readiness_audit_summary.json | ok | 90 |  | 156b3751808d37a1... |
| tables/submission_package_verification_summary.json | ok | 115 |  | 60d2da5b049092ac... |
| results/future_predictions_publication_aligned_2027_2035.csv | ok | 11741619 | 67824 | dd6d89dd9221e388... |
| results/future_predictions_publication_aligned_2027_2035_intervals.csv | ok | 27719306 | 67824 | 44290c43066929cb... |
| results/future_exceedance_probability_2027_2035.csv | ok | 64395574 | 135648 | fe21be863737c67f... |
| figures/manuscript_summary/manuscript_results_overview.png | ok | 398946 |  | b31352495b3825b3... |
| figures/validation_strategy/framework_module_ablation_mean_r2.png | ok | 86298 |  | c72bc658749c85bc... |
| docs/project_delivery_guide.md | ok | 5072 |  | 88328750c569d826... |
| docs/report.md | ok | 37878 |  | 83fc8efb4a60c19a... |
| docs/reproduction.md | ok | 17178 |  | f392be6ff343dcb5... |
| docs/spatial_baseline_residual_fixed_report.md | ok | 1511 |  | f10ba21a96e707da... |
| docs/validation_strategy_and_ablation_report.md | ok | 10876 |  | 4d28b1d41e499d6b... |

## Python 包版本

| package | version | status |
| --- | --- | --- |
| pandas | 3.0.3 | ok |
| numpy | 2.4.6 | ok |
| scipy | 1.17.1 | ok |
| scikit-learn | 1.8.0 | ok |
| matplotlib | 3.10.9 | ok |
| xgboost | 3.2.0 | ok |
| lightgbm | 4.6.0 | ok |
| catboost | 1.2.10 | ok |
| ngboost | 0.5.10 | ok |
| shap | 0.52.0 | ok |
| statsmodels | 0.14.6 | ok |
| torch | 2.12.0+cpu | ok |
| rasterio | 1.5.0 | ok |
| requests | 2.34.2 | ok |

机器可读结果见 `tables/reproducibility_snapshot_summary.json`、`tables/reproducibility_snapshot_files.csv` 和 `tables/reproducibility_snapshot_packages.csv`。

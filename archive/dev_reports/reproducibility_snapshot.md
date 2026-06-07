# 复现快照

本报告记录当前项目关键输入、配置、结果、图件和文档的文件哈希，以及主要 Python 包版本。它用于换机器、换数据或提交补充材料后核对复现版本。

## 摘要

- 生成时间 UTC：2026-06-05T06:05:39+00:00
- Python：3.12.10
- 平台：Linux-5.15.0-161-generic-x86_64-with-glibc2.35
- 建模数据：`data/processed/soil_heavy_metals_external_raster.csv`
- 文件哈希条目：24，缺失 0
- 包版本条目：14，缺失 0
- 论文主结果平均 R2：0.2609
- 论文主结果中位 R2：0.2182
- 正 R2 目标数：8/8
- 一键验收状态：`ok`
- 投稿准备度状态：`ok`

## 文件哈希

| path | status | size_bytes | n_rows | sha256 |
| --- | --- | --- | --- | --- |
| data/processed/soil_heavy_metals_external_raster.csv | ok | 952782 | 972 | 1d13a94fcc85d73b... |
| configs/soil_experiment.json | ok | 781 |  | c0a988cdff3c022f... |
| run_project.py | ok | 12514 |  | 1046bc4e273528bc... |
| requirements.txt | ok | 315 |  | 0e2fc9bd2b790282... |
| tables/publication_grade_recommended_metrics.csv | ok | 1606 | 8 | e0b2ac8e156e98d5... |
| tables/validation_strategy_summary.csv | ok | 893 | 3 | fdb5044f4c3390c4... |
| tables/spatial_baseline_residual_fixed_best_metrics.csv | ok | 1736 | 8 | 0a3fb3ca8651ef1a... |
| tables/framework_module_ablation_summary.csv | ok | 2335 | 7 | 1e5ded4a2de2c257... |
| tables/framework_module_ablation_m0_m6.csv | ok | 21752 | 56 | b6ab84922c19d93d... |
| tables/framework_module_ablation_summary.json | ok | 6056 |  | d31691e8099416c2... |
| tables/publication_model_cards.csv | ok | 6079 | 8 | fabd3c27a26444a5... |
| tables/candidate_eligibility_summary.csv | ok | 4158 | 8 | b6d543c6b7406485... |
| tables/submission_readiness_audit_summary.json | ok | 87 |  | 723c1e133733ad82... |
| tables/submission_package_verification_summary.json | ok | 111 |  | 05428644a04cee7e... |
| results/future_predictions_publication_aligned_2027_2035.csv | ok | 13440841 | 67824 | 7d346f9edbc1b7a1... |
| results/future_predictions_publication_aligned_2027_2035_intervals.csv | ok | 27882828 | 67824 | 322a12f6e2e795fe... |
| results/future_exceedance_probability_2027_2035.csv | ok | 65167038 | 135648 | 63afc6acc8581349... |
| figures/manuscript_summary/manuscript_results_overview.png | ok | 389784 |  | 7b1fc0c86b991e2f... |
| figures/validation_strategy/framework_module_ablation_mean_r2.png | ok | 72156 |  | da813422184636a6... |
| docs/project_delivery_guide.md | ok | 5059 |  | d784c77c779d76f7... |
| docs/report.md | ok | 89990 |  | 99676e4548b7c702... |
| docs/reproduction.md | ok | 14911 |  | e46dbb3a0fc4bfec... |
| docs/spatial_baseline_residual_fixed_report.md | ok | 1519 |  | 90b08bfe06f9ea4d... |
| docs/validation_strategy_and_ablation_report.md | ok | 10513 |  | bd215547b1ab7a6b... |

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

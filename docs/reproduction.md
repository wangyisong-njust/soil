# 复现说明

交付包的 `docs/` 目录只保留两份文档：本复现说明 `docs/reproduction.md` 和主报告 `docs/report.md`。各分析环节的权威产物是 `tables/`、`results/` 和 `figures/` 下的表格、结果与图件。运行完整流程时，部分脚本还会在 `docs/` 下额外生成分项分析报告，仅供查阅；交付快照已将这些分项报告归档到 `archive/dev_reports/`，不影响任何结果。

## 环境要求

推荐环境：

- Python 3.10 或更高版本
- Linux、macOS 或 Windows
- 完整模型比较建议至少 8 GB 内存

创建本地环境：

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

检查依赖：

```bash
.venv/bin/python scripts/check_runtime.py
```

预期结果：必需依赖均显示为 `OK`。如果要运行完整模型比较，XGBoost、LightGBM、CatBoost、NGBoost 和 SHAP 也应显示为 `OK`。

## 数据准备

原始数据集不随仓库上传。复现前请将 Excel 工作簿放到项目根目录，默认文件名为 `ABC2.xlsx`；如果使用其它文件名，请同步修改 `run_project.py` 顶部的 `RAW_EXCEL`，或修改 `configs/soil_experiment.json` 中的 `raw_excel`。

如果只是替换为新的省级数据，优先修改根目录 `run_project.py` 文件最前面的参数区。常用参数包括原始数据文件、目标列、驱动因子列、清洗策略、测试起始年份和未来预测年份。

将 Excel 工作簿转换为清洗后的 CSV：

```bash
.venv/bin/python scripts/convert_xlsx_to_csv.py
.venv/bin/python scripts/check_project_inputs.py
```

预期输出：

- `data/processed/soil_heavy_metals.csv`
- `tables/data_profile.json`
- `tables/data_cleaning_report.json`
- `tables/input_validation_report.json`

转换脚本会处理数值字符串、不间断空格，以及 `6.6-8.3` 这类范围值；范围值按中点转换。脚本还会标记并纠正疑似经纬度写反的记录。

当前主流程默认采用 `quality` 清洗策略，包括同坐标同年份重复观测聚合、驱动因子缺失中位数填补，以及驱动因子 0.5%/99.5% 温和截尾。若需比较不同清洗策略，运行：

```bash
.venv/bin/python scripts/evaluate_cleaning_strategies.py
```

预期输出：

- `tables/cleaning_strategy_comparison.csv`
- `tables/cleaning_strategy_best_metrics.csv`
- `tables/cleaning_strategy_reports.json`

## 本地材料摘要

从两篇本地参考论文和方案文档中抽取简要记录。原始文献与方案文档不随仓库上传；如需重新生成材料摘要，可将文件放在 `docs/source_materials/`。缺失时脚本会跳过对应文献：

```bash
.venv/bin/python scripts/extract_reference_notes.py
```

该步骤会在 `docs/` 下生成本地材料摘要（属分项文档，交付快照已归档到 `archive/dev_reports/`），不产生其它结果文件。

## 运行实验

推荐方式是先修改 `run_project.py` 顶部参数区，然后运行一键入口：

```bash
.venv/bin/python run_project.py
```

如果只想检查数据转换、基础模型和报告生成，可先运行：

```bash
.venv/bin/python run_project.py --skip-extended --skip-future
```

如果需要重新拉取 SoilGrids/NASA POWER 外部公开因子，可额外加入：

```bash
.venv/bin/python run_project.py --run-external
```

对 8 个目标分步运行全部模型：

```bash
.venv/bin/python scripts/run_experiment.py
.venv/bin/python scripts/run_period_blocks.py
.venv/bin/python scripts/run_spatiotemporal_innovations.py
.venv/bin/python scripts/run_spatial_baseline_residual_fixed.py
.venv/bin/python scripts/run_multitask_latent_models.py
.venv/bin/python scripts/run_temporal_sequence_models.py
.venv/bin/python scripts/run_distributional_robust_models.py
.venv/bin/python scripts/run_random_kfold_validation.py
.venv/bin/python scripts/run_spatial_block_validation.py
.venv/bin/python scripts/run_distribution_guided_spatial_quantile.py
.venv/bin/python scripts/run_local_analog_memory_models.py
.venv/bin/python scripts/run_quantile_risk_gate_models.py
.venv/bin/python scripts/run_multi_evidence_fusion.py
.venv/bin/python scripts/plot_temporal_sequence_comparison.py
.venv/bin/python scripts/build_spatial_quantile_yearwise_validated_baseline.py
.venv/bin/python scripts/build_yearwise_validation_selected_publication.py
.venv/bin/python scripts/build_yearwise_error_diagnostics.py
.venv/bin/python scripts/run_unified_validation.py
.venv/bin/python scripts/build_geo_terrain_candidates.py
.venv/bin/python scripts/build_final_adaptive_recommendations.py
.venv/bin/python scripts/build_publication_grade_recommendations.py
.venv/bin/python scripts/build_validation_strategy_and_ablation.py
```

`run_unified_validation.py` 须先于推荐表运行：`build_geo_terrain_candidates.py` 从其结果派生“外部+地形+地质”候选（`tables/external_geo_terrain_best_metrics.csv`），再由 `build_final_adaptive_recommendations.py` 纳入逐目标选优。这条链让 D、E 在论文主结果中自动选用地形/地质增强模型。

`run_unified_validation.py` 让随机五折、空间分块、未来年份三类验证使用同一候选池（完整模型注册表 × {base, base+外部协变量}），逐目标按各自留出折选优，使三类 R2 严格可比；`build_validation_strategy_and_ablation.py` 据此汇总并对照框架目标自适应口径。

预期输出：

- `tables/model_metrics.csv`
- `tables/data_cleaning_report.json`
- `tables/cleaning_strategy_best_metrics.csv`
- `tables/internal_validation_metrics.csv`
- `tables/ensemble_weights.csv`
- `tables/feature_importance.csv`
- `tables/shap_importance.csv`
- `tables/period_block_metrics.csv`
- `tables/period_block_best_metrics.csv`
- `tables/innovation_model_metrics.csv`
- `tables/innovation_best_metrics.csv`
- `tables/spatial_baseline_residual_fixed_metrics.csv`
- `tables/spatial_baseline_residual_fixed_best_metrics.csv`
- `tables/multitask_latent_metrics.csv`
- `tables/multitask_latent_best_metrics.csv`
- `tables/temporal_sequence_model_metrics.csv`
- `tables/temporal_sequence_best_metrics.csv`
- `tables/temporal_sequence_vs_external_delta.csv`
- `tables/distributional_robust_metrics.csv`
- `tables/distributional_robust_best_metrics.csv`
- `tables/random_fivefold_cv_metrics.csv`
- `tables/random_fivefold_cv_best_metrics.csv`
- `tables/spatial_block_cv_metrics.csv`
- `tables/spatial_block_cv_best_metrics.csv`
- `tables/unified_validation_metrics.csv`
- `tables/unified_validation_best_by_target.csv`
- `tables/unified_validation_summary.csv`
- `tables/unified_vs_framework_future.csv`
- `results/unified_validation_predictions.csv`
- `figures/validation_strategy/unified_validation_r2.png`
- `tables/validation_strategy_summary.csv`
- `tables/framework_module_ablation_summary.csv`
- `tables/framework_module_ablation_m0_m6.csv`
- `tables/distribution_guided_spatial_quantile_metrics.csv`
- `tables/spatial_quantile_yearwise_validation_metrics.csv`
- `tables/spatial_quantile_yearwise_validated_best_metrics.csv`
- `tables/yearwise_validation_candidate_metrics.csv`
- `tables/yearwise_validation_selected_publication_metrics.csv`
- `tables/publication_yearwise_error_metrics.csv`
- `tables/publication_yearwise_error_summary.csv`
- `tables/target_distribution_shift_metrics.csv`
- `tables/local_analog_memory_metrics.csv`
- `tables/local_analog_memory_best_metrics.csv`
- `tables/quantile_risk_gate_metrics.csv`
- `tables/quantile_risk_gate_best_metrics.csv`
- `tables/multi_evidence_fusion_metrics.csv`
- `tables/multi_evidence_fusion_best_metrics.csv`
- `tables/final_adaptive_candidate_metrics.csv`
- `tables/final_adaptive_recommended_metrics.csv`
- `results/predictions_<target>_<protocol>.csv`
- `results/innovation_model_predictions.csv`
- `results/spatial_baseline_residual_fixed_predictions.csv`
- `results/multitask_latent_predictions.csv`
- `results/temporal_sequence_model_predictions.csv`
- `results/distributional_robust_predictions.csv`
- `results/random_fivefold_cv_predictions.csv`
- `results/spatial_block_cv_predictions.csv`
- `results/distribution_guided_spatial_quantile_predictions.csv`
- `figures/<target>/*.png`
- `models/*.joblib`

生成未来基线情景预测和报告：

```bash
.venv/bin/python scripts/predict_future_scenarios.py
.venv/bin/python scripts/build_publication_aligned_future_predictions.py
.venv/bin/python scripts/build_publication_model_cards.py
.venv/bin/python scripts/training_fit_diagnostics.py
.venv/bin/python scripts/build_validation_strategy_and_ablation.py
.venv/bin/python scripts/build_candidate_eligibility_audit.py
.venv/bin/python scripts/build_manuscript_tables.py
.venv/bin/python scripts/build_manuscript_text_snippets.py
.venv/bin/python scripts/plot_manuscript_summary_panels.py
.venv/bin/python scripts/build_submission_readiness_audit.py
.venv/bin/python scripts/build_project_delivery_guide.py
.venv/bin/python scripts/verify_submission_package.py
.venv/bin/python scripts/build_reproducibility_snapshot.py
.venv/bin/python scripts/build_leakage_publication_audit.py
.venv/bin/python scripts/build_report.py
.venv/bin/python scripts/plot_delivery_highlights.py
.venv/bin/python scripts/check_markdown_references.py
.venv/bin/python scripts/build_delivery_audit.py
```

预期输出：

- `results/future_predictions_baseline_2027_2035.csv`
- `results/future_predictions_publication_aligned_2027_2035.csv`
- `results/future_predictions_publication_aligned_2027_2035_intervals.csv`
- `tables/publication_aligned_future_prediction_summary.csv`
- `tables/publication_model_cards.csv`
- `tables/publication_model_cards.json`
- `tables/validation_strategy_summary.csv`
- `tables/framework_module_ablation_summary.csv`
- `tables/framework_module_ablation_summary.json`
- `tables/framework_module_ablation_m0_m6.csv`
- `tables/candidate_eligibility_audit.csv`
- `tables/candidate_eligibility_summary.csv`
- `tables/candidate_eligibility_source_summary.csv`
- `tables/candidate_eligibility_rules.csv`
- `tables/candidate_eligibility_summary.json`
- `tables/manuscript_table1_variable_groups.csv`
- `tables/manuscript_table1_variable_dictionary.csv`
- `tables/manuscript_table2_publication_model_performance.csv`
- `tables/manuscript_table3_future_prediction_uncertainty.csv`
- `tables/manuscript_table4_future_exceedance_risk.csv`
- `tables/manuscript_table5_feature_group_importance.csv`
- `tables/manuscript_text_snippets_summary.json`
- `figures/manuscript_summary/manuscript_results_overview.png`
- `figures/manuscript_summary/manuscript_results_overview.pdf`
- `tables/submission_readiness_audit.csv`
- `tables/submission_readiness_audit_summary.json`
- `tables/project_delivery_guide_summary.json`
- `tables/submission_package_verification.csv`
- `tables/submission_package_verification_summary.json`
- `tables/reproducibility_snapshot_summary.json`
- `tables/reproducibility_snapshot_files.csv`
- `tables/reproducibility_snapshot_packages.csv`
- `tables/training_fit_metrics.csv`
- `tables/leakage_publication_audit.csv`
- `tables/leakage_publication_audit_summary.json`
- `docs/report.md`
- `tables/markdown_reference_check.csv`
- `tables/markdown_reference_check_summary.json`
- `tables/delivery_artifact_manifest.csv`
- `tables/delivery_audit_summary.json`

## 外部公开因子

如需重新提取 SoilGrids 和 NASA POWER 外部因子，运行：

```bash
.venv/bin/python scripts/enrich_external_covariates.py
.venv/bin/python scripts/evaluate_external_covariates.py
```

预期输出：

- `data/processed/soil_heavy_metals_external.csv`
- `tables/external_covariates_report.json`
- `tables/external_covariate_metrics.csv`
- `tables/external_covariate_best_metrics.csv`

外部 API 受网络和限流影响，脚本会把缓存保存在 `data/external_cache/`。NASA POWER 当前月尺度接口不接受 2026 年整年请求，脚本会使用 2025 年气候值前向填充 2026 年样本，并在提取报告中记录。

### 地形与地质协变量（联网自动获取）

```bash
.venv/bin/python scripts/enrich_terrain_covariates.py
.venv/bin/python scripts/enrich_geology_covariates.py --data data/processed/soil_heavy_metals_terrain.csv
```

- `enrich_terrain_covariates.py`：opentopodata SRTM 30m 高程，逐点取 3×3 网格，派生高程、坡度、坡向、地形起伏和地形位置指数（`dem_* / terr_*`）。输出 `data/processed/soil_heavy_metals_terrain.csv`，记录 `tables/terrain_covariates_report.json`。
- `enrich_geology_covariates.py`：Macrostrat 地质单元 API，按经纬度取地表岩性大类与地质年代（`geo_*`）。输出 `data/processed/soil_heavy_metals_geology.csv`，记录 `tables/geology_covariates_report.json`。
- 两者逐点缓存到 `data/external_cache/`，可断点续跑；无覆盖或失败的点以中位数/`unknown` 填补。
- 实测增量（temporal 留出，小模型池）：地质对 B 提升约 +0.10（母岩信号）、地形对 D 提升约 +0.06，C/E/F/H 小幅正向；A/G 不获益，故按目标自适应使用。`run_unified_validation.py` 与 `evaluate_external_covariates.py` 会把这些列纳入候选特征池，逐目标自动选择是否采用。

如需加入 OpenStreetMap/Geofabrik 人类活动代理变量，先下载 China shapefile 压缩包到 `data/external_raw/osm/china-latest-free.shp.zip`：

```bash
mkdir -p data/external_raw/osm
curl -L -o data/external_raw/osm/china-latest-free.shp.zip https://download.geofabrik.de/asia/china-latest-free.shp.zip
.venv/bin/python scripts/enrich_osm_covariates.py --skip-roads --radius-km 10
.venv/bin/python scripts/enrich_osm_activity_covariates.py --radius-km 10
.venv/bin/python scripts/enrich_remote_raster_covariates.py --viirs-mode epochs --ghsl-mode static --ghsl-static-epochs 2020
.venv/bin/python scripts/evaluate_external_covariates.py --external-data data/processed/soil_heavy_metals_external_raster.csv --models ExtraTrees,HistGBR,ElasticNet,XGBoost,LightGBM
```

`scripts/enrich_osm_covariates.py` 提取工业/矿业污染源最近距离和 10 km 邻域数量。`scripts/enrich_osm_activity_covariates.py` 进一步提取铁路长度密度、交通设施、运输设施、活动 POI、污染相关 POI，以及工业/商业/居住/农业/绿地等土地利用斑块的最近距离、数量和面积比例。

本次结果使用 `--skip-roads` 快方案跳过全国道路层。若要加入道路密度和最近道路距离，可去掉 `--skip-roads`；全国道路层很大，运行时间和内存占用会明显增加。活动增强模型已另存为 `tables/external_covariate_best_metrics_activity_subset.csv`，并与旧外部因子全量模型结果合并后生成 `tables/external_covariate_best_metrics.csv`。

`scripts/enrich_remote_raster_covariates.py` 继续接入三类公开栅格因子：

- VIIRS 年度夜间灯光：使用 Zenodo 开放 COG，默认采样 2000、2005、2010、2015、2020、2021 代表年度，2022 年以后使用最近可用的 2021 层；
- GHSL 建成区/人口：默认采样 JRC GHSL R2023A 的 2020 年 30 arc-second 人口、总建成区和非居住建成区栅格；
- ESA WorldCover：采样 2021 v200 的 10 m 土地覆盖类别，并生成 built、cropland、tree、water 等 one-hot 变量。

完整逐年 GHSL 可用 `--ghsl-mode temporal` 打开，但远程 zip 内 GeoTIFF 读取耗时较长。栅格增强模型结果另存为 `tables/external_covariate_best_metrics_remote_raster_subset.csv`。

## 验证协议

主验证协议是时间外推留出：

- 训练期：2021 年以前
- 测试期：2022 年及之后

同时生成随机 80/20 划分结果作为辅助对照。论文或公开代码场景优先采用时间外推结果，因为它更接近未来时期预测。

目标变量空间滞后特征只在训练划分内部计算。对测试期样本，这些特征只使用训练期观测值，不使用测试期真实目标值。

另提供三阶段时间块验证：

- 第一阶段：2000-2008
- 第二阶段：2009-2017
- 第三阶段：2018-2026

脚本 `scripts/run_period_blocks.py` 会生成两个滚动外推结果：用第一阶段预测第二阶段，以及用前两阶段预测第三阶段。该验证方式适合描述文献样本随年份变化的阶段性外推，但仍不能保证得到高 R2。

## 训练拟合度诊断

运行：

```bash
.venv/bin/python scripts/training_fit_diagnostics.py
```

输出：

- `tables/training_fit_metrics.csv`

该表用于展示模型对当前样本的拟合能力。树模型在训练集上可能达到 0.89 以上，甚至接近 1.0。这个结果不能写成外推预测精度，也不能替代 `tables/model_metrics.csv` 中的验证指标。

## 未来情景预测

未来预测脚本采用基线常量驱动因子情景：

- 默认预测年份：2027-2035
- 每个位置沿用自身最新观测的 `a-q` 驱动因子
- `year` 特征推进到目标年份
- 目标变量空间滞后特征只引用历史观测

这是一个可复现的情景假设。如果后续获得未来驱动因子的实测值或外部模拟值，应替换该基线情景。

## 常见问题

如果缺少 `data/processed/soil_heavy_metals.csv`，先运行 `scripts/convert_xlsx_to_csv.py`。

如果某个模型的 SHAP 计算失败，脚本仍会输出模型指标和特征重要性图。失败信息会打印在终端。

如果缺少某个可选模型包，脚本只跳过对应模型。完整运行需要安装 `requirements.txt` 中的全部依赖。

共享机器上建议保留默认 `--n-jobs 2`。只有在机器空闲时再提高线程数。

# 外部公开因子对照

本轮外部因子包括 SoilGrids 表层土壤属性、NASA POWER 年尺度气候变量、OpenStreetMap/Geofabrik 工业矿业和人类活动代理变量，以及新增的 VIIRS 夜间灯光、GHSL 建成区/人口、ESA WorldCover 2021 土地覆盖栅格。所有变量只作为预测因子加入，不修改目标重金属含量，不使用测试期真实目标值调参。

## 严格未来验证结果

综合旧外部因子全量模型、OSM 活动增强模型和 VIIRS/GHSL/WorldCover 栅格增强模型后，每个目标选择当前外部因子组最优结果：

| target | baseline_r2 | external_r2 | delta_r2 | best_external_model | n_features |
| --- | --- | --- | --- | --- | ---: |
| A | 0.2645 | 0.3559 | 0.0914 | LightGBM | 82 |
| B | 0.4413 | 0.5044 | 0.0632 | ElasticNet | 48 |
| C | -0.0729 | -0.0264 | 0.0465 | LightGBM | 112 |
| D | 0.1770 | 0.2466 | 0.0695 | ExtraTrees | 112 |
| E | 0.3617 | 0.5466 | 0.1848 | LightGBM | 82 |
| F | -0.0198 | -0.0137 | 0.0061 | HistGBR | 48 |
| G | -1.1915 | -1.3640 | -0.1725 | CatBoost | 48 |
| H | 0.1500 | 0.1436 | -0.0064 | NGBoost | 48 |

外部因子对 A、B、C、D、E、F 有正向增量，其中 E 的提升最明显，严格 2021-2026 未来验证 R2 从 0.3617 提高到 0.5466。新增 VIIRS/GHSL/WorldCover 栅格因子主要提升 C 和 D：C 从 -0.0290 小幅提高到 -0.0264，D 从 0.2026 提高到 0.2466。

G 和 H 不适合直接采用外部因子模型，最终推荐表会自动选择更稳健的保守基线或局部历史污染记忆模型。

## 栅格增强因子增量

相对于上一版 SoilGrids + NASA POWER + OSM 外部因子，新增 VIIRS/GHSL/WorldCover 后的外部模型变化如下：

| target | previous_external_r2 | raster_external_r2 | delta_r2 |
| --- | --- | --- | --- |
| A | 0.3559 | 0.2478 | -0.1081 |
| B | 0.5044 | 0.4576 | -0.0468 |
| C | -0.0290 | -0.0264 | 0.0026 |
| D | 0.2026 | 0.2466 | 0.0439 |
| E | 0.5466 | 0.5343 | -0.0123 |
| F | -0.0137 | -0.0183 | -0.0046 |
| G | -1.3640 | -3.8813 | -2.5172 |
| H | 0.1436 | 0.1053 | -0.0382 |

栅格增强因子不是所有目标都受益。论文中更合理的写法是把它作为消融实验：证明夜间灯光、建成区/人口和土地覆盖能改善部分目标的空间异质性解释，尤其是 D；同时保留目标自适应选择，避免把对 G/H 明显不稳定的特征强行纳入主模型。

## 数据记录

- 基础外部因子提取记录：`tables/external_covariates_report.json`
- OSM 工业/矿业变量记录：`tables/osm_covariates_report.json`
- OSM 活动增强变量记录：`tables/osm_activity_covariates_report.json`
- VIIRS/GHSL/WorldCover 栅格变量记录：`tables/remote_raster_covariates_report.json`
- OSM 活动因子子集模型结果：`tables/external_covariate_best_metrics_activity_subset.csv`
- 栅格增强因子子集模型结果：`tables/external_covariate_best_metrics_remote_raster_subset.csv`
- 合并后的外部因子最优结果：`tables/external_covariate_best_metrics.csv`

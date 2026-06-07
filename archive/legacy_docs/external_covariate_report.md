# 外部公开因子对照

本报告比较原始特征与SoilGrids 表层土壤属性、NASA POWER 年尺度气候变量增强后的模型表现。外部数据只作为预测因子，不修改目标变量。

| protocol | target | baseline | external_covariates | delta_r2 |
| --- | --- | --- | --- | --- |
| literature_2019_2020 | A | 0.1031 | 0.0997 | -0.0035 |
| literature_2019_2020 | B | 0.0416 | 0.0960 | 0.0544 |
| literature_2019_2020 | C | 0.1522 | 0.0991 | -0.0532 |
| literature_2019_2020 | D | 0.2025 | 0.1185 | -0.0840 |
| literature_2019_2020 | E | 0.1072 | 0.1346 | 0.0275 |
| literature_2019_2020 | F | 0.1028 | 0.1304 | 0.0275 |
| literature_2019_2020 | G | -0.0118 | 0.0134 | 0.0252 |
| literature_2019_2020 | H | 0.4235 | 0.4923 | 0.0688 |
| temporal_2022_2026 | A | 0.2684 | 0.2757 | 0.0072 |
| temporal_2022_2026 | B | -0.0604 | 0.1543 | 0.2147 |
| temporal_2022_2026 | C | 0.0032 | -0.0217 | -0.0250 |
| temporal_2022_2026 | D | 0.2528 | 0.2739 | 0.0210 |
| temporal_2022_2026 | E | 0.3449 | 0.4887 | 0.1438 |
| temporal_2022_2026 | F | 0.0371 | 0.2337 | 0.1966 |
| temporal_2022_2026 | G | 0.1131 | 0.0051 | -0.1080 |
| temporal_2022_2026 | H | 0.0119 | 0.0490 | 0.0371 |

外部因子提取记录见 `tables/external_covariates_report.json`；若启用 OSM 人类活动代理变量，记录另见 `tables/osm_covariates_report.json` 和 `tables/osm_activity_covariates_report.json`。

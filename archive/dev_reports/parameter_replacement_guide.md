# 数据与参数替换说明

## 推荐入口

优先修改根目录的 `run_project.py`。文件最前面已经集中放置常用参数：

- `RAW_EXCEL`：原始 Excel 文件名
- `DATA_CLEANING_STRATEGY`：数据清洗策略
- `DRIVER_WINSOR_LIMITS`：驱动因子温和截尾分位数
- `TARGET_COLUMNS`：8 个重金属目标列
- `BASE_FEATURE_COLUMNS`：经纬度、年份和环境驱动因子列
- `TEMPORAL_TEST_START_YEAR`：时间外推测试起始年份
- `FUTURE_YEARS`：未来预测年份
- `N_JOBS`：运行线程数
- `RUN_INNOVATION_MODELS`：是否运行空间分区、空间残差、时间加权和两阶段模型对照
- `RUN_MULTITASK_LATENT_MODELS`：是否运行多任务潜变量模型对照
- `RUN_EXTENDED_PAPER_PIPELINE`：是否运行时间序列、局部记忆、风险预警、不确定性、图件和交付审计等扩展流程
- `RUN_EXTERNAL_COVARIATE_PIPELINE`：是否重新下载并评估 SoilGrids/NASA POWER 外部公开因子，默认关闭

修改后运行：

```bash
.venv/bin/python run_project.py
```

常用快速检查命令：

```bash
.venv/bin/python run_project.py --skip-extended --skip-future
```

常用外部因子命令：

```bash
.venv/bin/python run_project.py --run-external
```

当前默认未来预测年份为 2027-2035。若只预测到 2030，可把 `FUTURE_YEARS` 改成：

```python
FUTURE_YEARS = "2027,2028,2029,2030"
```

## 省级数据替换要求

省级数据表至少需要包含下面几类字段：

- `lon`：经度
- `lat`：纬度
- `year`：采样年份
- 8 个重金属目标列，例如 `Cd`、`Cu`、`Pb`、`Zn` 等
- 若干环境驱动因子列，例如土壤理化性质、气候、地形、土地利用、人为活动强度等

如果列名不同，只需要在 `run_project.py` 的 `TARGET_COLUMNS` 和 `BASE_FEATURE_COLUMNS` 中同步修改。

## 指标口径

`tables/model_metrics.csv` 是验证指标，适合公开复现和论文方法部分使用。

`tables/data_cleaning_report.json` 记录主流程清洗细节，包含重复观测聚合、缺失填补和驱动因子截尾规则。

`tables/cleaning_strategy_best_metrics.csv` 是不同清洗策略的对照结果，用于说明为什么选择当前默认策略。

`tables/period_block_best_metrics.csv` 是三阶段时间块验证结果，对应 2000-2008、2009-2017、2018-2026 的滚动外推设计。

`tables/innovation_best_metrics.csv` 是空间分区、空间残差、时间加权和两阶段模型的最佳对照结果。

`tables/multitask_latent_best_metrics.csv` 是多任务潜变量模型结果，用于检验 8 个重金属协同污染潜因子是否能改善预测。

`tables/external_covariate_best_metrics.csv` 是 SoilGrids、NASA POWER，以及可选 OSM 人类活动代理变量增强后的对照结果。

`tables/training_fit_metrics.csv` 是训练拟合度，通常会明显高于验证指标。它只能说明模型对当前数据的拟合能力，不能作为未来预测性能使用。

## 关于环境因子调整

可以做的处理：

- 修正明显录入错误，例如经纬度写反、非法数值、单位不一致。
- 增加真实来源的外部协变量，例如 DEM、降水、温度、土地利用、路网距离、工业源距离。
- 对驱动因子做标准化、分箱、交互项和空间邻域特征。
- 对缺失值做 KNN、随机森林或空间插值，并在文档中说明规则。

不建议做的处理：

- 为了提高 R2 人为修改环境因子数值。
- 使用测试期真实目标值反推环境因子。
- 删除表现差的测试样本但不说明规则。
- 把训练拟合度写成外推验证精度。

如果模型、数据和代码需要公开，以上不建议做的处理会很容易被复现检查发现。

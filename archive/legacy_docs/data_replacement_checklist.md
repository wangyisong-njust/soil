# 省级数据替换检查清单

本文件说明如何把新的省级土壤重金属数据放入当前流程。字段模板和要求来自当前 `configs/soil_experiment.json`，因此与 `run_project.py` 顶部参数区保持一致。

## 模板文件

- CSV 模板：`data/templates/soil_heavy_metal_input_template.csv`
- 字段要求表：`tables/data_replacement_schema.csv`

## 最低字段要求

- 必须包含 `lon`、`lat`、`year`。
- 当前目标列为：`A, B, C, D, E, F, G, H`。
- 当前基础预测因子列为：`lon, lat, year, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q`。
- 所有目标列和驱动因子列应尽量为数值型；范围值、单位和缺失值应在导入前统一。

## 替换步骤

1. 将新的 Excel 数据放到项目根目录或 `data/raw/`。
2. 修改 `run_project.py` 顶部的 `RAW_EXCEL`、`TARGET_COLUMNS` 和 `BASE_FEATURE_COLUMNS`。
3. 运行输入检查：

```bash
.venv/bin/python scripts/convert_xlsx_to_csv.py
.venv/bin/python scripts/check_project_inputs.py
```

4. 检查 `docs/input_validation_report.md` 和 `tables/input_validation_report.json`。
5. 通过输入检查后，再运行完整流程或快速流程。

## 常见问题

- 如果新数据没有 8 个目标列，需要同步修改 `TARGET_COLUMNS`，并确认后续论文表格是否仍按 8 个目标设计。
- 如果列名使用真实重金属名称，例如 `Cd`、`Cu`、`Pb`，直接写入 `TARGET_COLUMNS` 即可。
- 如果省级数据年份范围小于当前数据，`TEMPORAL_TEST_START_YEAR` 应同步调整。
- 如果未来预测年份不需要 2027-2035，可修改 `FUTURE_YEARS`。
- 不应为了提高 R2 修改目标值或使用测试期目标值反推环境因子。

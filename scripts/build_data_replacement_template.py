#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.paths import DATA_DIR, DOCS_DIR, TABLES_DIR, ensure_project_dirs


TEMPLATE_DIR = DATA_DIR / "templates"


def example_values(column: str, role: str, index: int) -> object:
    if column == "lon":
        return 116.40
    if column == "lat":
        return 39.90
    if column == "year":
        return 2020
    if role == "target":
        return round(1.0 + index * 0.5, 3)
    return round(10.0 + index, 3)


def main() -> None:
    ensure_project_dirs()
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config(ROOT / "configs" / "soil_experiment.json")
    target_columns = [str(col) for col in config["target_columns"]]
    base_features = [str(col) for col in config["base_feature_columns"]]
    all_columns = base_features + [col for col in target_columns if col not in base_features]

    rows: list[dict[str, object]] = []
    for idx, column in enumerate(all_columns):
        if column in {"lon", "lat"}:
            role = "spatial_coordinate"
            required = True
            dtype = "numeric"
            description = "Sampling coordinate in decimal degrees."
        elif column == "year":
            role = "time"
            required = True
            dtype = "integer"
            description = "Sampling year used for temporal validation and future prediction."
        elif column in target_columns:
            role = "target"
            required = True
            dtype = "numeric"
            description = "Heavy metal concentration target. Replace anonymous names with formal metal names before manuscript use."
        else:
            role = "driver"
            required = True
            dtype = "numeric"
            description = "Environmental, soil, climate, terrain, land-use, or anthropogenic predictor."
        rows.append(
            {
                "column": column,
                "role": role,
                "required": required,
                "dtype": dtype,
                "example_value": example_values(column, role, idx),
                "description": description,
                "run_project_parameter": "TARGET_COLUMNS" if role == "target" else "BASE_FEATURE_COLUMNS",
            }
        )

    schema = pd.DataFrame(rows)
    schema.to_csv(TABLES_DIR / "data_replacement_schema.csv", index=False, encoding="utf-8-sig")
    template_row = {row["column"]: row["example_value"] for row in rows}
    template = pd.DataFrame([template_row])
    template.to_csv(TEMPLATE_DIR / "soil_heavy_metal_input_template.csv", index=False, encoding="utf-8-sig")

    checklist = [
        "# 省级数据替换检查清单",
        "",
        "本文件说明如何把新的省级土壤重金属数据放入当前流程。字段模板和要求来自当前 `configs/soil_experiment.json`，因此与 `run_project.py` 顶部参数区保持一致。",
        "",
        "## 模板文件",
        "",
        "- CSV 模板：`data/templates/soil_heavy_metal_input_template.csv`",
        "- 字段要求表：`tables/data_replacement_schema.csv`",
        "",
        "## 最低字段要求",
        "",
        "- 必须包含 `lon`、`lat`、`year`。",
        f"- 当前目标列为：`{', '.join(target_columns)}`。",
        f"- 当前基础预测因子列为：`{', '.join(base_features)}`。",
        "- 所有目标列和驱动因子列应尽量为数值型；范围值、单位和缺失值应在导入前统一。",
        "",
        "## 替换步骤",
        "",
        "1. 将新的 Excel 数据放到项目根目录或 `data/raw/`。",
        "2. 修改 `run_project.py` 顶部的 `RAW_EXCEL`、`TARGET_COLUMNS` 和 `BASE_FEATURE_COLUMNS`。",
        "3. 运行输入检查：",
        "",
        "```bash",
        ".venv/bin/python scripts/convert_xlsx_to_csv.py",
        ".venv/bin/python scripts/check_project_inputs.py",
        "```",
        "",
        "4. 检查 `docs/input_validation_report.md` 和 `tables/input_validation_report.json`。",
        "5. 通过输入检查后，再运行完整流程或快速流程。",
        "",
        "## 常见问题",
        "",
        "- 如果新数据没有 8 个目标列，需要同步修改 `TARGET_COLUMNS`，并确认后续论文表格是否仍按 8 个目标设计。",
        "- 如果列名使用真实重金属名称，例如 `Cd`、`Cu`、`Pb`，直接写入 `TARGET_COLUMNS` 即可。",
        "- 如果省级数据年份范围小于当前数据，`TEMPORAL_TEST_START_YEAR` 应同步调整。",
        "- 如果未来预测年份不需要 2027-2035，可修改 `FUTURE_YEARS`。",
        "- 不应为了提高 R2 修改目标值或使用测试期目标值反推环境因子。",
        "",
    ]
    checklist_text = "\n".join(checklist)
    (DOCS_DIR / "data_replacement_checklist.md").write_text(checklist_text, encoding="utf-8")
    (DOCS_DIR / "parameter_replacement_guide.md").write_text(checklist_text, encoding="utf-8")
    summary = {
        "status": "ok",
        "template": "data/templates/soil_heavy_metal_input_template.csv",
        "schema": "tables/data_replacement_schema.csv",
        "checklist": "docs/data_replacement_checklist.md",
        "parameter_guide": "docs/parameter_replacement_guide.md",
        "n_columns": len(all_columns),
        "n_targets": len(target_columns),
        "n_base_features": len(base_features),
    }
    (TABLES_DIR / "data_replacement_template_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Wrote data replacement template")


if __name__ == "__main__":
    main()

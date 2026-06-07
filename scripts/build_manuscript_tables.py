#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


EXTERNAL_PREFIX_GROUPS = {
    "sg_": ("Public external covariates", "SoilGrids soil property covariates"),
    "np_": ("Public external covariates", "NASA POWER climate covariates"),
    "osm_": ("Public external covariates", "OpenStreetMap human activity covariates"),
    "viirs_": ("Public external covariates", "VIIRS night-time light covariates"),
    "ghsl_": ("Public external covariates", "GHSL built-up and population covariates"),
    "wc_": ("Public external covariates", "ESA WorldCover land-cover covariates"),
}

ENGINEERED_FEATURES = [
    ("year_offset", "Temporal trend feature centered on the training period"),
    ("year_offset_sq", "Quadratic temporal trend feature"),
    ("lon_lat", "Longitude-latitude interaction feature"),
    ("lon_sq", "Longitude squared feature"),
    ("lat_sq", "Latitude squared feature"),
]

SPATIAL_LAG_FEATURES = [
    ("target_spatial_mean", "Training-period neighboring target mean feature"),
    ("target_spatial_idw", "Training-period inverse-distance weighted target feature"),
    ("target_spatial_min_dist", "Distance to nearest training-period target observation"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build manuscript-ready summary tables from current outputs.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    return parser.parse_args()


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame()


def short_list(values: list[str], limit: int = 24) -> str:
    values = [str(value) for value in values]
    if len(values) <= limit:
        return "; ".join(values)
    shown = "; ".join(values[:limit])
    return f"{shown}; ... (+{len(values) - limit} more)"


def fmt_float(value: object, digits: int = 4) -> str:
    if pd.isna(value):
        return ""
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def md_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_No records._"
    text_df = df.astype(str)
    lines = [
        "| " + " | ".join(text_df.columns) + " |",
        "| " + " | ".join(["---"] * len(text_df.columns)) + " |",
    ]
    for row in text_df.values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def numeric_stats_by_column() -> dict[str, dict[str, object]]:
    summary = read_csv_if_exists(TABLES_DIR / "input_validation_numeric_summary.csv")
    if summary.empty or "column" not in summary:
        return {}
    return {str(row["column"]): row.to_dict() for _, row in summary.iterrows()}


def make_variable_groups(data: pd.DataFrame, config: dict[str, object]) -> pd.DataFrame:
    targets = [str(value) for value in config["target_columns"]]
    base_features = [str(value) for value in config["base_feature_columns"]]
    raw_drivers = [value for value in base_features if value not in {"lon", "lat", "year"}]

    rows: list[dict[str, object]] = [
        {
            "table_group": "Spatial coordinates",
            "role": "predictor",
            "n_variables": 2,
            "variables": "lon; lat",
            "description": "Sampling longitude and latitude used for spatial features and map outputs.",
        },
        {
            "table_group": "Time variable",
            "role": "predictor",
            "n_variables": 1,
            "variables": "year",
            "description": "Sampling year used for temporal validation and future scenario projection.",
        },
        {
            "table_group": "Original driver variables",
            "role": "predictor",
            "n_variables": len(raw_drivers),
            "variables": short_list(raw_drivers),
            "description": "Original environmental or anthropogenic drivers supplied in the modeling data.",
        },
        {
            "table_group": "Heavy metal targets",
            "role": "response",
            "n_variables": len(targets),
            "variables": short_list(targets),
            "description": "Eight heavy metal concentration targets modeled separately.",
        },
        {
            "table_group": "Engineered spatiotemporal features",
            "role": "predictor",
            "n_variables": len(ENGINEERED_FEATURES),
            "variables": short_list([name for name, _ in ENGINEERED_FEATURES]),
            "description": "Deterministic trend and coordinate interaction features generated inside the pipeline.",
        },
        {
            "table_group": "Publication target spatial lag",
            "role": "predictor",
            "n_variables": len(SPATIAL_LAG_FEATURES),
            "variables": short_list([name for name, _ in SPATIAL_LAG_FEATURES]),
            "description": "Target-specific spatial background features computed only from eligible training-period observations.",
        },
    ]

    for prefix, (group, description) in EXTERNAL_PREFIX_GROUPS.items():
        columns = sorted([col for col in data.columns if str(col).startswith(prefix)])
        rows.append(
            {
                "table_group": group,
                "role": "predictor",
                "n_variables": len(columns),
                "variables": short_list(columns) if columns else "",
                "description": description,
            }
        )
    return pd.DataFrame(rows)


def make_variable_dictionary(data: pd.DataFrame, config: dict[str, object]) -> pd.DataFrame:
    stats = numeric_stats_by_column()
    targets = [str(value) for value in config["target_columns"]]
    base_features = [str(value) for value in config["base_feature_columns"]]
    raw_drivers = [value for value in base_features if value not in {"lon", "lat", "year"}]

    descriptions: dict[str, str] = {
        "lon": "Sampling longitude.",
        "lat": "Sampling latitude.",
        "year": "Sampling year.",
    }
    for target in targets:
        descriptions[target] = "Heavy metal concentration response variable."
    for feature in raw_drivers:
        descriptions[feature] = "Original driver variable supplied in the modeling data."
    for name, description in ENGINEERED_FEATURES + SPATIAL_LAG_FEATURES:
        descriptions[name] = description

    rows: list[dict[str, object]] = []

    def add_row(variable: str, role: str, group: str, in_raw_data: bool) -> None:
        stat = stats.get(variable, {})
        rows.append(
            {
                "variable": variable,
                "role": role,
                "variable_group": group,
                "in_modeling_data": bool(in_raw_data),
                "missing": stat.get("missing", ""),
                "non_numeric": stat.get("non_numeric", ""),
                "min": stat.get("min", ""),
                "median": stat.get("median", ""),
                "max": stat.get("max", ""),
                "description": descriptions.get(variable, ""),
            }
        )

    for variable in ["lon", "lat", "year"]:
        add_row(variable, "predictor", "Spatial/time base variable", variable in data.columns)
    for variable in raw_drivers:
        add_row(variable, "predictor", "Original driver variable", variable in data.columns)
    for variable in targets:
        add_row(variable, "response", "Heavy metal target", variable in data.columns)
    for variable, _ in ENGINEERED_FEATURES:
        add_row(variable, "predictor", "Engineered spatiotemporal feature", variable in data.columns)
    for variable, _ in SPATIAL_LAG_FEATURES:
        add_row(variable, "predictor", "Publication target spatial lag", variable in data.columns)

    for prefix, (_, description) in EXTERNAL_PREFIX_GROUPS.items():
        columns = sorted([col for col in data.columns if str(col).startswith(prefix)])
        for variable in columns:
            descriptions[str(variable)] = description
            add_row(str(variable), "predictor", "Public external covariate", True)
    return pd.DataFrame(rows)


def make_model_performance_table(model_cards: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "target",
        "model_description",
        "source",
        "method",
        "model",
        "test_protocol",
        "n_train",
        "n_test",
        "r2",
        "rmse",
        "mae",
        "mape",
        "future_alignment_status",
        "future_implementation",
        "fusion_n_members",
        "distribution_rule",
    ]
    if model_cards.empty:
        return pd.DataFrame(columns=columns)
    out = model_cards[[col for col in columns if col in model_cards.columns]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        if col in out:
            out[col] = out[col].map(lambda value: fmt_float(value, 4))
    return out.sort_values("target")


def make_future_uncertainty_table(future_interval: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "target",
        "n",
        "mean_prediction",
        "median_prediction",
        "median_interval_width",
        "mean_relative_width",
        "max_upper",
        "future_prediction_file",
    ]
    if future_interval.empty:
        return pd.DataFrame(columns=columns)
    out = future_interval[[col for col in columns if col in future_interval.columns]].copy()
    for col in ["mean_prediction", "median_prediction", "median_interval_width", "mean_relative_width", "max_upper"]:
        if col in out:
            out[col] = out[col].map(lambda value: fmt_float(value, 4))
    return out.sort_values("target")


def make_future_risk_table(future_exceedance: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "target",
        "quantile",
        "threshold_value",
        "mean_probability",
        "median_probability",
        "p90_probability",
        "high_prob_050_rate",
        "high_prob_080_rate",
    ]
    if future_exceedance.empty:
        return pd.DataFrame(columns=columns)
    out = future_exceedance[[col for col in columns if col in future_exceedance.columns]].copy()
    for col in [
        "quantile",
        "threshold_value",
        "mean_probability",
        "median_probability",
        "p90_probability",
        "high_prob_050_rate",
        "high_prob_080_rate",
    ]:
        if col in out:
            out[col] = out[col].map(lambda value: fmt_float(value, 4))
    return out.sort_values(["target", "quantile"])


def make_feature_group_table(feature_groups: pd.DataFrame) -> pd.DataFrame:
    columns = ["target", "feature_group", "normalized_shap"]
    if feature_groups.empty:
        return pd.DataFrame(columns=columns)
    out = feature_groups[[col for col in columns if col in feature_groups.columns]].copy()
    if "normalized_shap" in out:
        out["normalized_shap"] = out["normalized_shap"].map(lambda value: fmt_float(value, 4))
    return out.sort_values(["target", "feature_group"])


def write_report(outputs: dict[str, Path], config: dict[str, object], data_path: Path) -> None:
    model_perf = pd.read_csv(outputs["performance"])
    future_uncertainty = pd.read_csv(outputs["uncertainty"])
    future_risk = pd.read_csv(outputs["risk"])
    feature_groups = pd.read_csv(outputs["feature_groups"])
    variable_groups = pd.read_csv(outputs["variable_groups"])

    r2_values = pd.to_numeric(model_perf.get("r2", pd.Series(dtype=float)), errors="coerce")
    exact_n = int((model_perf.get("future_alignment_status", pd.Series(dtype=str)) == "exact_publication_model").sum())
    future_file = ""
    if "future_prediction_file" in future_uncertainty and len(future_uncertainty):
        future_file = str(future_uncertainty["future_prediction_file"].iloc[0])

    lines = [
        "# SCI 论文汇总表",
        "",
        "本报告把当前可复现实验结果整理为论文写作和补充材料可直接引用的表格。所有表格均来自已有数据、模型卡、未来预测、不确定性和解释性结果，不重新训练模型，也不修改目标变量或驱动因子。",
        "",
        "## 表格清单",
        "",
        f"- 表 1A 变量分组：`{outputs['variable_groups'].relative_to(ROOT)}`",
        f"- 表 1B 变量字典：`{outputs['variable_dictionary'].relative_to(ROOT)}`",
        f"- 表 2 论文主模型性能：`{outputs['performance'].relative_to(ROOT)}`",
        f"- 表 3 未来预测不确定性：`{outputs['uncertainty'].relative_to(ROOT)}`",
        f"- 表 4 未来超阈值风险概率：`{outputs['risk'].relative_to(ROOT)}`",
        f"- 表 5 重要因子组贡献：`{outputs['feature_groups'].relative_to(ROOT)}`",
        "",
        "## 数据和验证口径",
        "",
        f"- 建模数据：`{data_path.relative_to(ROOT)}`",
        f"- 目标变量：`{', '.join(str(value) for value in config['target_columns'])}`",
        f"- 主时间外推测试起始年：{config['temporal_test_start_year']}",
        f"- 未来预测文件：`{future_file}`" if future_file else "- 未来预测文件：未生成",
        "",
        "## 论文主模型性能摘要",
        "",
        (
            f"当前表 2 覆盖 {model_perf['target'].nunique() if 'target' in model_perf else 0} 个目标，"
            f"平均 R2 为 {r2_values.mean():.4f}，中位数 R2 为 {r2_values.median():.4f}，"
            f"最小 R2 为 {r2_values.min():.4f}，最大 R2 为 {r2_values.max():.4f}。"
            if len(r2_values.dropna())
            else "当前表 2 未包含可计算的 R2。"
        ),
        f"未来预测 exact publication model 对齐目标数为 {exact_n}。",
        "",
        md_table(model_perf[["target", "model_description", "r2", "rmse", "mae", "mape", "future_alignment_status"]], max_rows=12)
        if len(model_perf)
        else "_No records._",
        "",
        "## 未来风险和不确定性",
        "",
        "表 3 汇总 2027-2035 未来预测的均值、中位数和经验残差区间宽度。表 4 使用训练核心期 q90/q95 阈值计算未来超阈值概率，可作为风险预警表。",
        "",
        md_table(future_risk, max_rows=16) if len(future_risk) else "_No records._",
        "",
        "## 可解释性表",
        "",
        "表 5 使用基础树模型 SHAP 结果按因子组归一化汇总，适合作为全文解释性分析的表格入口；蜂群图和热图仍以 `figures/feature_importance_summary/` 为准。",
        "",
        md_table(feature_groups, max_rows=16) if len(feature_groups) else "_No records._",
        "",
        "## 变量分组预览",
        "",
        md_table(variable_groups),
        "",
        "## 使用说明",
        "",
        "- 表 2 是论文主验证表，应与 `publication_grade_recommended_metrics.csv` 和模型卡保持一致。",
        "- 表 3 和表 4 是未来情景结果，不应反向用于选择 2022-2026 测试期模型。",
        "- 表 1B 中匿名列名在投稿前应替换为正式变量名、单位和数据来源。",
        "",
    ]
    (DOCS_DIR / "manuscript_tables_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = preferred_processed_data_path()
    data = pd.read_csv(data_path)

    model_cards = read_csv_if_exists(TABLES_DIR / "publication_model_cards.csv")
    future_interval = read_csv_if_exists(TABLES_DIR / "future_prediction_interval_summary.csv")
    future_exceedance = read_csv_if_exists(TABLES_DIR / "future_exceedance_probability_summary.csv")
    feature_groups = read_csv_if_exists(TABLES_DIR / "feature_importance_group_summary.csv")

    outputs = {
        "variable_groups": TABLES_DIR / "manuscript_table1_variable_groups.csv",
        "variable_dictionary": TABLES_DIR / "manuscript_table1_variable_dictionary.csv",
        "performance": TABLES_DIR / "manuscript_table2_publication_model_performance.csv",
        "uncertainty": TABLES_DIR / "manuscript_table3_future_prediction_uncertainty.csv",
        "risk": TABLES_DIR / "manuscript_table4_future_exceedance_risk.csv",
        "feature_groups": TABLES_DIR / "manuscript_table5_feature_group_importance.csv",
    }

    make_variable_groups(data, config).to_csv(outputs["variable_groups"], index=False, encoding="utf-8-sig")
    make_variable_dictionary(data, config).to_csv(outputs["variable_dictionary"], index=False, encoding="utf-8-sig")
    make_model_performance_table(model_cards).to_csv(outputs["performance"], index=False, encoding="utf-8-sig")
    make_future_uncertainty_table(future_interval).to_csv(outputs["uncertainty"], index=False, encoding="utf-8-sig")
    make_future_risk_table(future_exceedance).to_csv(outputs["risk"], index=False, encoding="utf-8-sig")
    make_feature_group_table(feature_groups).to_csv(outputs["feature_groups"], index=False, encoding="utf-8-sig")
    write_report(outputs, config, data_path)

    summary = {
        "status": "ok",
        "data_file": str(data_path.relative_to(ROOT)),
        "n_targets": len(config["target_columns"]),
        "outputs": {name: str(path.relative_to(ROOT)) for name, path in outputs.items()},
        "report": "docs/manuscript_tables_report.md",
    }
    (TABLES_DIR / "manuscript_tables_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Wrote manuscript tables")


if __name__ == "__main__":
    main()

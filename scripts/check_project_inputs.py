#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate processed data and experiment configuration before modeling.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Optional processed CSV path. Defaults to config['processed_csv'].")
    parser.add_argument("--allow-missing-drivers", action="store_true", help="Do not fail when driver variables contain missing values.")
    return parser.parse_args()


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_无记录。_"
    text_df = df.astype(str)
    lines = [
        "| " + " | ".join(text_df.columns) + " |",
        "| " + " | ".join(["---"] * len(text_df.columns)) + " |",
    ]
    for row in text_df.values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def numeric_summary(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = []
    for col in columns:
        series = pd.to_numeric(df[col], errors="coerce")
        finite = series[np.isfinite(series)]
        rows.append(
            {
                "column": col,
                "missing": int(series.isna().sum()),
                "non_numeric": int(series.notna().sum() - finite.size),
                "min": "" if finite.empty else f"{float(finite.min()):.6g}",
                "median": "" if finite.empty else f"{float(finite.median()):.6g}",
                "max": "" if finite.empty else f"{float(finite.max()):.6g}",
            }
        )
    return pd.DataFrame(rows)


def validate(config: dict[str, object], data_path: Path, allow_missing_drivers: bool) -> tuple[dict[str, object], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not data_path.exists() or data_path.stat().st_size == 0:
        raise SystemExit(f"Missing processed data: {data_path}")
    df = pd.read_csv(data_path)
    target_cols = [str(item) for item in config["target_columns"]]
    feature_cols = [str(item) for item in config["base_feature_columns"]]
    required_cols = list(dict.fromkeys(["lon", "lat", "year", *target_cols, *feature_cols]))
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append("Missing required columns: " + ", ".join(missing_cols))

    if len(target_cols) != 8:
        warnings.append(f"Expected 8 target columns for this project, found {len(target_cols)}.")
    if len(set(target_cols)) != len(target_cols):
        errors.append("Duplicate target column names in config['target_columns'].")
    if len(set(feature_cols)) != len(feature_cols):
        warnings.append("Duplicate feature column names in config['base_feature_columns'].")
    overlap = sorted(set(target_cols).intersection(feature_cols))
    if overlap:
        errors.append("Target columns must not also be listed as predictors: " + ", ".join(overlap))

    summary: dict[str, object] = {
        "data_path": str(data_path.relative_to(ROOT) if data_path.is_relative_to(ROOT) else data_path),
        "n_rows": int(len(df)),
        "n_columns": int(df.shape[1]),
        "target_columns": target_cols,
        "base_feature_columns": feature_cols,
        "missing_required_columns": missing_cols,
        "warnings": warnings,
        "errors": errors,
        "status": "ok",
    }

    if not missing_cols:
        numeric_cols = required_cols
        numeric = numeric_summary(df, numeric_cols)
        numeric.to_csv(TABLES_DIR / "input_validation_numeric_summary.csv", index=False, encoding="utf-8-sig")
        coord = df[["lon", "lat"]].apply(pd.to_numeric, errors="coerce")
        year = pd.to_numeric(df["year"], errors="coerce")
        summary.update(
            {
                "year_min": int(year.min()) if year.notna().any() else None,
                "year_max": int(year.max()) if year.notna().any() else None,
                "lon_min": float(coord["lon"].min()) if coord["lon"].notna().any() else None,
                "lon_max": float(coord["lon"].max()) if coord["lon"].notna().any() else None,
                "lat_min": float(coord["lat"].min()) if coord["lat"].notna().any() else None,
                "lat_max": float(coord["lat"].max()) if coord["lat"].notna().any() else None,
                "n_unique_years": int(year.nunique(dropna=True)),
                "n_unique_points_rounded6": int(df[["lon", "lat"]].round(6).drop_duplicates().shape[0]),
            }
        )
        bad_numeric = numeric[numeric["non_numeric"] > 0]["column"].tolist()
        if bad_numeric:
            errors.append("Non-numeric values remain in numeric columns: " + ", ".join(bad_numeric))
        missing_target = numeric[numeric["column"].isin(target_cols) & (numeric["missing"] > 0)]["column"].tolist()
        if missing_target:
            errors.append("Target columns contain missing values: " + ", ".join(missing_target))
        missing_drivers = numeric[numeric["column"].isin(feature_cols) & (numeric["missing"] > 0)]["column"].tolist()
        if missing_drivers and not allow_missing_drivers:
            warnings.append("Driver columns contain missing values; main modeling scripts usually impute them: " + ", ".join(missing_drivers))
        if coord["lon"].lt(-180).any() or coord["lon"].gt(180).any() or coord["lat"].lt(-90).any() or coord["lat"].gt(90).any():
            errors.append("Longitude/latitude values exceed valid ranges.")
        if year.nunique(dropna=True) < 2:
            warnings.append("Only one unique year detected; temporal validation and future extrapolation will be weak.")

    summary["warnings"] = warnings
    summary["errors"] = errors
    summary["status"] = "ok" if not errors else "failed"
    return summary, errors


def write_report(summary: dict[str, object]) -> None:
    numeric_path = TABLES_DIR / "input_validation_numeric_summary.csv"
    numeric = pd.read_csv(numeric_path) if numeric_path.exists() and numeric_path.stat().st_size else pd.DataFrame()
    lines = [
        "# 输入数据与配置检查",
        "",
        "本报告在建模前检查配置文件和处理后数据是否一致，包括目标列、预测因子列、经纬度、年份、数值类型和缺失情况。",
        "",
        "## 摘要",
        "",
        f"- 状态：`{summary['status']}`",
        f"- 数据文件：`{summary['data_path']}`",
        f"- 样本数：{summary['n_rows']}",
        f"- 列数：{summary['n_columns']}",
        f"- 目标列：`{', '.join(summary['target_columns'])}`",
        f"- 年份范围：{summary.get('year_min', 'NA')}-{summary.get('year_max', 'NA')}",
        f"- 独立点位数：{summary.get('n_unique_points_rounded6', 'NA')}",
        "",
    ]
    if summary["errors"]:
        lines.extend(["## 错误", "", *[f"- {item}" for item in summary["errors"]], ""])
    if summary["warnings"]:
        lines.extend(["## 提醒", "", *[f"- {item}" for item in summary["warnings"]], ""])
    lines.extend(
        [
            "## 数值列摘要",
            "",
            md_table(numeric),
            "",
            "机器可读摘要见 `tables/input_validation_report.json`；数值列摘要见 `tables/input_validation_numeric_summary.csv`。",
            "",
        ]
    )
    (DOCS_DIR / "input_validation_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = ROOT / (args.data or str(config["processed_csv"]))
    summary, errors = validate(config, data_path, args.allow_missing_drivers)
    (TABLES_DIR / "input_validation_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(summary)
    print(f"Wrote input validation outputs: {summary['status']}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

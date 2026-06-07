#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import apply_quality_cleaning, dataset_profile, read_and_clean_excel
from soilmodel.paths import ensure_project_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert the soil Excel workbook into a cleaned CSV file.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--input", default=None, help="Override Excel input path.")
    parser.add_argument("--output", default=None, help="Override CSV output path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    input_path = ROOT / (args.input or config["raw_excel"])
    output_path = ROOT / (args.output or config["processed_csv"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    basic_df = read_and_clean_excel(input_path)
    strategy = config.get("data_cleaning_strategy", "quality")
    if strategy not in {"basic", "none", ""}:
        basic_output_path = output_path.with_name(output_path.stem + "_basic.csv")
        basic_df.to_csv(basic_output_path, index=False, encoding="utf-8-sig")
    df, cleaning_report = apply_quality_cleaning(
        basic_df,
        target_columns=config["target_columns"],
        base_feature_columns=config["base_feature_columns"],
        strategy=strategy,
        driver_winsor_limits=tuple(config.get("driver_winsor_limits", [0.005, 0.995])),
    )
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    profile = dataset_profile(df, config["target_columns"])
    profile["data_cleaning_strategy"] = strategy
    profile_path = ROOT / "tables" / "data_profile.json"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    cleaning_report_path = ROOT / "tables" / "data_cleaning_report.json"
    cleaning_report_path.write_text(json.dumps(cleaning_report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote cleaned CSV: {output_path.relative_to(ROOT)}")
    print(f"Wrote data profile: {profile_path.relative_to(ROOT)}")
    print(f"Wrote cleaning report: {cleaning_report_path.relative_to(ROOT)}")
    print(f"Rows: {profile['n_rows']}, years: {profile['year_min']}-{profile['year_max']}")


if __name__ == "__main__":
    main()

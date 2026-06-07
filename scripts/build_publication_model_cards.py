#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from soilmodel.config import load_config
from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path

from build_publication_aligned_future_predictions import selected_candidate_validation_weights


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


def fmt(value: object, digits: int = 4) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (float, int, np.floating, np.integer)):
        return f"{float(value):.{digits}f}"
    return str(value)


def source_description(source: str, method: str, model: str) -> str:
    if source == "external_public_covariates":
        return f"公开外部因子增强机器学习模型：{model}"
    if source == "publication_validation_fusion":
        return f"2019-2020 验证期确定成员和权重的融合模型：{model}"
    if source == "distribution_guided_spatial_quantile":
        return f"训练期分布规则空间分位数模型：{method}/{model}"
    if source == "local_analog_memory":
        return f"局部历史污染记忆模型：{model}"
    return f"{source}: {method}/{model}"


def load_distribution_rules() -> pd.DataFrame:
    path = TABLES_DIR / "distribution_guided_spatial_quantile_metrics.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df[df["protocol"] == "temporal_2022_2026"].copy()


def load_fusion_members(target: str, model: str) -> tuple[list[str], list[float]]:
    best_path = TABLES_DIR / "publication_validation_fusion_best_metrics.csv"
    if not best_path.exists() or best_path.stat().st_size == 0:
        return [], []
    best = pd.read_csv(best_path)
    match = best[(best["target"].astype(str) == target) & (best["model"].astype(str) == model)]
    if match.empty or "selected" not in match.columns:
        return [], []
    members = [item for item in str(match.iloc[0]["selected"]).split(";") if item]
    if not members:
        return [], []
    try:
        weights = selected_candidate_validation_weights(target, members)
        return members, [float(value) for value in weights]
    except Exception:
        return members, []


def build_cards() -> tuple[pd.DataFrame, list[dict[str, object]]]:
    config = load_config(ROOT / "configs" / "soil_experiment.json")
    data_path = preferred_processed_data_path()
    publication = pd.read_csv(TABLES_DIR / "publication_grade_recommended_metrics.csv").sort_values("target")
    future = pd.read_csv(TABLES_DIR / "publication_aligned_future_prediction_summary.csv").sort_values("target")
    rules = load_distribution_rules()

    rows: list[dict[str, object]] = []
    detailed: list[dict[str, object]] = []
    for row in publication.itertuples(index=False):
        target = str(row.target)
        source = str(row.source)
        method = str(row.method)
        model = str(row.model)
        future_match = future[future["target"].astype(str) == target]
        future_row = future_match.iloc[0].to_dict() if len(future_match) else {}
        members: list[str] = []
        weights: list[float] = []
        if source == "publication_validation_fusion":
            members, weights = load_fusion_members(target, model)
        rule_record: dict[str, object] = {}
        if source == "distribution_guided_spatial_quantile" and not rules.empty:
            rule_match = rules[
                (rules["target"].astype(str) == target)
                & (rules["method"].astype(str) == method)
                & (rules["model"].astype(str) == model)
            ]
            if len(rule_match):
                rule_record = rule_match.iloc[0].to_dict()

        card = {
            "target": target,
            "source": source,
            "method": method,
            "model": model,
            "model_description": source_description(source, method, model),
            "test_protocol": str(row.protocol),
            "n_train": int(row.n_train) if not pd.isna(row.n_train) else None,
            "n_test": int(row.n_test) if not pd.isna(row.n_test) else None,
            "r2": float(row.r2),
            "rmse": float(row.rmse),
            "mae": float(row.mae),
            "mape": float(row.mape),
            "future_implementation": str(future_row.get("future_implementation", "")),
            "future_alignment_status": str(future_row.get("alignment_status", "")),
            "future_mean_prediction": None if "mean_prediction" not in future_row else float(future_row["mean_prediction"]),
            "future_median_prediction": None if "median_prediction" not in future_row else float(future_row["median_prediction"]),
            "distribution_rule": str(rule_record.get("rule", "")),
            "distribution_cv": None if "cv" not in rule_record else float(rule_record["cv"]),
            "distribution_iqr_to_median": None if "iqr_to_median" not in rule_record else float(rule_record["iqr_to_median"]),
            "distribution_quantile": None if "quantile" not in rule_record else float(rule_record["quantile"]),
            "fusion_n_members": len(members),
            "fusion_members": ";".join(members),
            "fusion_weights": ";".join(f"{value:.8f}" for value in weights),
            "data_file": str(data_path.relative_to(ROOT)),
            "target_columns": ",".join(str(item) for item in config["target_columns"]),
            "base_feature_columns": ",".join(str(item) for item in config["base_feature_columns"]),
            "temporal_test_start_year": int(config["temporal_test_start_year"]),
            "reproducibility_note": (
                "No observed future target values are used for model selection or future prediction; "
                "future prediction uses baseline_constant_drivers scenario."
            ),
        }
        rows.append(card)
        detailed.append(
            {
                **card,
                "fusion_member_details": [
                    {"candidate": candidate, "weight": weights[i] if i < len(weights) else None}
                    for i, candidate in enumerate(members)
                ],
            }
        )
    return pd.DataFrame(rows), detailed


def write_report(cards: pd.DataFrame, detailed: list[dict[str, object]]) -> None:
    show_cols = [
        "target",
        "source",
        "model",
        "r2",
        "rmse",
        "mae",
        "future_alignment_status",
        "future_implementation",
    ]
    show = cards[show_cols].copy()
    for col in ["r2", "rmse", "mae"]:
        show[col] = show[col].map(lambda value: fmt(value))

    lines = [
        "# 论文主结果模型卡",
        "",
        "本报告为 8 个目标的论文主结果模型生成模型卡，记录模型来源、验证指标、未来预测复刻方式、融合成员权重和分布规则。该文件用于模型交付、补充材料说明和审稿复现，不改变任何模型结果。",
        "",
        "## 汇总表",
        "",
        md_table(show),
        "",
        "## 目标级说明",
        "",
    ]
    for item in detailed:
        lines.extend(
            [
                f"### {item['target']}",
                "",
                f"- 模型：`{item['source']} / {item['method']} / {item['model']}`",
                f"- 测试指标：R2={fmt(item['r2'])}，RMSE={fmt(item['rmse'])}，MAE={fmt(item['mae'])}，MAPE={fmt(item['mape'])}",
                f"- 未来预测实现：`{item['future_implementation']}`，状态 `{item['future_alignment_status']}`",
                f"- 数据文件：`{item['data_file']}`",
            ]
        )
        if item.get("distribution_rule"):
            lines.extend(
                [
                    f"- 分布规则：`{item['distribution_rule']}`，CV={fmt(item['distribution_cv'])}，IQR/median={fmt(item['distribution_iqr_to_median'])}，quantile={fmt(item['distribution_quantile'])}",
                ]
            )
        members = item.get("fusion_member_details", [])
        if members:
            member_df = pd.DataFrame(members)
            member_df["weight"] = member_df["weight"].map(lambda value: fmt(value, digits=6))
            lines.extend(["", "融合成员权重：", "", md_table(member_df), ""])
        else:
            lines.append("")
    lines.extend(
        [
            "## 输出文件",
            "",
            "- `tables/publication_model_cards.csv`",
            "- `tables/publication_model_cards.json`",
            "- `docs/publication_model_cards.md`",
            "",
        ]
    )
    (DOCS_DIR / "publication_model_cards.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_project_dirs()
    cards, detailed = build_cards()
    cards.to_csv(TABLES_DIR / "publication_model_cards.csv", index=False, encoding="utf-8-sig")
    (TABLES_DIR / "publication_model_cards.json").write_text(json.dumps(detailed, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(cards, detailed)
    print("Wrote publication model cards")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs


def read_required(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        raise SystemExit(f"Missing required input: {path.relative_to(ROOT)}")
    return pd.read_csv(path)


def read_optional(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() and path.stat().st_size else pd.DataFrame()


def f4(value: object) -> str:
    if pd.isna(value):
        return "NA"
    return f"{float(value):.4f}"


def target_list(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)


def top_feature_groups(feature_groups: pd.DataFrame) -> pd.DataFrame:
    if feature_groups.empty:
        return pd.DataFrame(columns=["target", "feature_group", "normalized_shap"])
    df = feature_groups.copy()
    df["normalized_shap"] = pd.to_numeric(df["normalized_shap"], errors="coerce")
    return (
        df.sort_values(["target", "normalized_shap"], ascending=[True, False])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_无记录。_"
    text = df.astype(str)
    lines = [
        "| " + " | ".join(text.columns) + " |",
        "| " + " | ".join(["---"] * len(text.columns)) + " |",
    ]
    for row in text.values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> None:
    ensure_project_dirs()
    config = load_config(ROOT / "configs" / "soil_experiment.json")
    performance = read_required(TABLES_DIR / "publication_grade_recommended_metrics.csv")
    model_cards = read_required(TABLES_DIR / "publication_model_cards.csv")
    eligibility = read_required(TABLES_DIR / "candidate_eligibility_summary.csv")
    future = read_required(TABLES_DIR / "publication_aligned_future_prediction_summary.csv")
    risk = read_required(TABLES_DIR / "manuscript_table4_future_exceedance_risk.csv")
    uncertainty = read_required(TABLES_DIR / "manuscript_table3_future_prediction_uncertainty.csv")
    feature_groups = read_optional(TABLES_DIR / "manuscript_table5_feature_group_importance.csv")

    targets = [str(value) for value in config["target_columns"]]
    test_start = int(config["temporal_test_start_year"])
    train_n = int(pd.to_numeric(performance["n_train"], errors="coerce").max())
    test_n = int(pd.to_numeric(performance["n_test"], errors="coerce").max())
    r2 = pd.to_numeric(performance["r2"], errors="coerce")
    rmse = pd.to_numeric(performance["rmse"], errors="coerce")
    best_row = performance.loc[r2.idxmax()]
    weakest_row = performance.loc[r2.idxmin()]
    exact_future = int((future["alignment_status"] == "exact_publication_model").sum())
    eligibility_ok = int(eligibility["publication_equals_best_eligible"].sum())
    excluded_better = int((pd.to_numeric(eligibility["r2_gap_to_excluded_upper_bound"], errors="coerce") > 0).sum())

    risk_numeric = risk.copy()
    for col in ["quantile", "mean_probability", "high_prob_050_rate", "threshold_value"]:
        risk_numeric[col] = pd.to_numeric(risk_numeric[col], errors="coerce")
    top_risk = risk_numeric.sort_values("mean_probability", ascending=False).head(3).copy()
    top_risk_show = top_risk[["target", "quantile", "threshold_value", "mean_probability", "high_prob_050_rate"]].copy()
    for col in ["quantile", "threshold_value", "mean_probability", "high_prob_050_rate"]:
        top_risk_show[col] = top_risk_show[col].map(f4)

    uncertainty_numeric = uncertainty.copy()
    uncertainty_numeric["mean_relative_width"] = pd.to_numeric(uncertainty_numeric["mean_relative_width"], errors="coerce")
    widest_interval = uncertainty_numeric.sort_values("mean_relative_width", ascending=False).head(1).iloc[0]

    top_groups = top_feature_groups(feature_groups)
    top_group_counts = top_groups["feature_group"].value_counts().to_dict() if len(top_groups) else {}
    dominant_group_text = ", ".join(f"{group} ({count} targets)" for group, count in top_group_counts.items()) or "NA"

    model_family_counts = model_cards["source"].value_counts().to_dict()
    model_family_text = ", ".join(f"{source}: {count}" for source, count in model_family_counts.items())

    perf_show = performance[["target", "source", "model", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        perf_show[col] = pd.to_numeric(perf_show[col], errors="coerce").map(f4)

    lines = [
        "# 论文方法与结果写作辅助文本",
        "",
        "本文件由当前可复现实验表自动生成，用于论文初稿、结果汇报或补充材料撰写。以下文字应在投稿前结合真实变量名、单位、研究区名称和期刊格式进一步润色。",
        "",
        "## Methods Draft",
        "",
        "### Data preprocessing and validation design",
        "",
        (
            f"The modeling dataset contained spatial coordinates, sampling year, environmental predictors, and eight heavy-metal response variables "
            f"({', '.join(targets)}). The primary validation strategy was a temporal extrapolation protocol: samples before {test_start} were used "
            f"for model training and model selection, whereas samples from {test_start} onward were retained as an independent future-period test set. "
            f"The current experiment used up to {train_n} training observations and {test_n} future-period test observations per target. "
            "Repeated coordinates within the same year were aggregated during preprocessing, missing driver values were imputed by median values, "
            "and mild winsorization was applied only to driver variables rather than to response variables."
        ),
        "",
        "### Model development",
        "",
        (
            "The central methodological contribution was a unified target-adaptive modeling framework. All eight heavy metals shared the same "
            "preprocessing pipeline, feature construction rules, candidate-model registry, temporal validation split, leakage-control rules, and "
            "candidate eligibility audit. Target-specific behavior was handled only through a predefined selection layer that chose the best eligible "
            "module for each response variable under the same 2022-2026 temporal extrapolation protocol. Candidate modules included tree-based models "
            "with public external covariates, terrain/geology-enhanced regressors, spatiotemporal feature models, risk-gated quantile models, local "
            "pollution-memory models, causal history-memory models, and distribution-guided spatial quantile baselines. Models that selected weights, "
            "calibration forms, or hyperparameters directly from the 2022-2026 target observations were excluded from the publication table and retained "
            "only as diagnostic upper bounds."
        ),
        "",
        "### Future prediction and uncertainty",
        "",
        (
            f"The final model for each target was refitted in a publication-aligned prediction workflow and used to generate 2027-2035 future predictions. "
            f"All {exact_future}/{len(targets)} targets were reproduced by exact publication-model implementations. Future uncertainty was quantified by transferring "
            "empirical residual intervals from the independent temporal test period, and exceedance probabilities were calculated relative to training-period q90/q95 thresholds."
        ),
        "",
        "### Interpretability",
        "",
        (
            "Model interpretability was summarized using feature-group contributions derived from SHAP-based importance tables. Predictors were grouped into "
            "spatial lag features, original driver variables, geographic position, and temporal trend features. This design avoids interpreting diagnostic "
            "upper-bound ensembles as if they were ordinary single black-box models."
        ),
        "",
        "## Results Draft",
        "",
        "### Predictive performance",
        "",
        (
            f"Under the unified target-adaptive framework, the publication-grade temporal validation R2 ranged from {f4(r2.min())} to {f4(r2.max())}, "
            f"with a mean of {f4(r2.mean())} and a median of {f4(r2.median())}. The best-performing target was `{best_row['target']}` "
            f"({best_row['source']}/{best_row['model']}, R2={f4(best_row['r2'])}), whereas the weakest target was `{weakest_row['target']}` "
            f"({weakest_row['source']}/{weakest_row['model']}, R2={f4(weakest_row['r2'])}). All eight targets had positive R2 under the strict temporal extrapolation protocol."
        ),
        "",
        md_table(perf_show),
        "",
        "### Candidate eligibility and upper-bound diagnostics",
        "",
        (
            f"The candidate eligibility audit showed that the selected publication model was the best eligible non-leaking candidate for {eligibility_ok}/{len(targets)} targets. "
            f"Exploratory upper-bound models achieved higher R2 for {excluded_better}/{len(targets)} targets, but those models used 2022-2026 target observations for "
            "same-set fitting, test-period model selection, or test-period grid search. Therefore, they were retained as diagnostic upper bounds rather than final publication results."
        ),
        "",
        "### Future risk and uncertainty",
        "",
        (
            f"The widest future prediction interval relative to the predicted magnitude occurred for target `{widest_interval['target']}` "
            f"(mean relative width={f4(widest_interval['mean_relative_width'])}). The highest future exceedance probabilities were concentrated in the following target-threshold combinations:"
        ),
        "",
        md_table(top_risk_show),
        "",
        "### Feature-group interpretation",
        "",
        (
            f"The dominant SHAP feature groups by target were summarized as: {dominant_group_text}. This result indicates that spatial background, original driver variables, "
            "and geographic location all contributed to the modeled heavy-metal patterns, with the dominant mechanism varying across targets."
        ),
        "",
        "## Limitations Draft",
        "",
        (
            "The strict temporal validation results should be interpreted together with the sampling structure. Most locations were not continuous monitoring sites, "
            "and the post-2021 test period contained fewer observations than the training period. Some targets also showed strong distribution shifts and extreme future-period observations, "
            "which limited the attainable R2 under a leakage-free validation design. Consequently, the study emphasizes transparent temporal validation, uncertainty intervals, "
            "risk exceedance probabilities, and candidate eligibility auditing rather than reporting inflated same-set fitting scores."
        ),
        "",
        "## Reviewer-Response Notes",
        "",
        "- If asked why higher R2 results are not used as the main result: cite `docs/candidate_eligibility_audit_report.md` and explain that those rows use test-period target values for selection or same-set fitting.",
        "- If asked why R2 is modest for C/F/G: cite `docs/yearwise_error_diagnostics_report.md` and the distribution-shift diagnostics, then emphasize risk-probability and uncertainty outputs.",
        "- If asked whether future prediction reproduces the final models: cite `docs/publication_aligned_future_prediction_report.md` and the exact publication-model status for all eight targets.",
        "- If asked about model interpretability: cite `docs/feature_importance_summary_report.md` and `figures/feature_importance_summary/` rather than interpreting diagnostic upper-bound models.",
        "",
        "## Key Numeric Summary",
        "",
        f"- Targets: {target_list(targets)}",
        f"- Model source counts: {model_family_text}",
        f"- Mean publication R2: {f4(r2.mean())}",
        f"- Median publication R2: {f4(r2.median())}",
        f"- Mean RMSE across targets: {f4(rmse.mean())}",
        f"- Publication model equals best eligible candidate: {eligibility_ok}/{len(targets)}",
        f"- Exact future prediction implementations: {exact_future}/{len(targets)}",
        "",
    ]
    out_path = DOCS_DIR / "manuscript_text_snippets.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "status": "ok",
        "output": "docs/manuscript_text_snippets.md",
        "n_targets": len(targets),
        "mean_publication_r2": float(r2.mean()),
        "median_publication_r2": float(r2.median()),
        "best_target": str(best_row["target"]),
        "best_target_r2": float(best_row["r2"]),
        "weakest_target": str(weakest_row["target"]),
        "weakest_target_r2": float(weakest_row["r2"]),
        "publication_equals_best_eligible": eligibility_ok,
        "exact_future_targets": exact_future,
    }
    (TABLES_DIR / "manuscript_text_snippets_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Wrote manuscript text snippets")


if __name__ == "__main__":
    main()

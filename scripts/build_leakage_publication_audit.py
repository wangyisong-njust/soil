#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config, target_columns
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


EXCLUDED_PUBLICATION_SOURCES = {
    "nnls_stack_exploration",
    "spatial_model_blend_exploration",
    "temporal_calibration_exploration",
    "validation_transfer_test_selected_exploration",
    "conservative_baseline",
}

ALLOWED_PUBLICATION_SOURCES = {
    "arima_lstm_temporal",
    "causal_history_memory",
    "distribution_guided_spatial_quantile",
    "distributional_robust",
    "external_public_covariates",
    "external_geo_terrain_covariates",
    "local_analog_memory",
    "multi_evidence_fusion",
    "multitask_latent",
    "predefined_recent_median_baseline",
    "publication_validation_fusion",
    "quantile_risk_gate",
    "spatial_distribution_features",
    "spatial_quantile_baseline",
    "spatial_quantile_validated",
    "spatial_quantile_yearwise_validated",
    "spatiotemporal_innovation",
    "validation_transfer_calibration",
    "yearwise_validation_selected_publication",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def file_exists(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


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


def add_check(rows: list[dict[str, str]], check: str, status: str, detail: str) -> None:
    rows.append({"check": check, "status": status, "detail": detail})


def load_csv(path: Path, rows: list[dict[str, str]], label: str) -> pd.DataFrame:
    if not file_exists(path):
        add_check(rows, f"{label} exists", "failed", f"Missing or empty file: {rel(path)}")
        return pd.DataFrame()
    return pd.read_csv(path)


def check_static_spatial_lag(rows: list[dict[str, str]]) -> None:
    run_experiment = ROOT / "scripts" / "run_experiment.py"
    future = ROOT / "scripts" / "predict_future_scenarios.py"
    if not file_exists(run_experiment) or not file_exists(future):
        add_check(rows, "target spatial lag implementation", "failed", "Missing core modeling scripts.")
        return
    train_text = run_experiment.read_text(encoding="utf-8")
    future_text = future.read_text(encoding="utf-8")
    train_ok = (
        "add_target_spatial_lag_features" in train_text
        and "core_idx, core_idx" in train_text
        and "leave_one_out=True" in train_text
        and "train_idx, test_idx" in train_text
        and "leave_one_out=False" in train_text
    )
    future_ok = (
        "add_target_spatial_lag_features" in future_text
        and "observed_idx, observed_idx" in future_text
        and "observed_idx, future_idx" in future_text
    )
    if train_ok and future_ok:
        add_check(
            rows,
            "target spatial lag implementation",
            "ok",
            "Training rows use leave-one-out target lag; test and future rows only reference training/observed-period target values.",
        )
    else:
        add_check(
            rows,
            "target spatial lag implementation",
            "warning",
            "Static scan could not fully verify target spatial lag isolation. Review scripts/run_experiment.py and scripts/predict_future_scenarios.py.",
        )


def main() -> None:
    ensure_project_dirs()
    config = load_config(ROOT / "configs" / "soil_experiment.json")
    targets = target_columns(config)
    base_features = [str(item) for item in config.get("base_feature_columns", [])]
    rows: list[dict[str, str]] = []

    data_path = preferred_processed_data_path()
    data = load_csv(data_path, rows, "preferred processed data")
    publication_path = TABLES_DIR / "publication_grade_recommended_metrics.csv"
    publication = load_csv(publication_path, rows, "publication metrics")
    model_cards_path = TABLES_DIR / "publication_model_cards.csv"
    model_cards = load_csv(model_cards_path, rows, "publication model cards")
    candidates_path = TABLES_DIR / "final_adaptive_candidate_metrics.csv"
    candidates = load_csv(candidates_path, rows, "candidate metrics")
    grid_path = RESULTS_DIR / "recommended_prediction_grid_values.csv"
    grid = load_csv(grid_path, rows, "recommended prediction grid")
    aligned_future_path = RESULTS_DIR / "future_predictions_publication_aligned_2027_2035.csv"
    baseline_future_path = RESULTS_DIR / "future_predictions_baseline_2027_2035.csv"
    future_path = aligned_future_path if file_exists(aligned_future_path) else baseline_future_path
    future = load_csv(future_path, rows, "future predictions")
    future_interval_path = RESULTS_DIR / "future_predictions_publication_aligned_2027_2035_intervals.csv"
    future_intervals = load_csv(future_interval_path, rows, "publication-aligned future intervals")
    future_probability_path = RESULTS_DIR / "future_exceedance_probability_2027_2035.csv"
    future_probabilities = load_csv(future_probability_path, rows, "future exceedance probabilities")
    future_probability_map_path = TABLES_DIR / "future_exceedance_probability_map_summary.csv"
    future_probability_map = load_csv(future_probability_map_path, rows, "future exceedance probability map summary")

    if len(targets) == 8 and len(set(targets)) == 8:
        add_check(rows, "target column definition", "ok", "Config defines 8 unique target columns: " + ", ".join(targets))
    else:
        add_check(
            rows,
            "target column definition",
            "failed",
            f"Expected 8 unique targets, found {len(targets)} entries and {len(set(targets))} unique names.",
        )

    overlap = sorted(set(targets).intersection(base_features))
    if overlap:
        add_check(rows, "target feature overlap", "failed", "Target columns are listed as predictors: " + ", ".join(overlap))
    else:
        add_check(rows, "target feature overlap", "ok", "No configured target column is listed in base_feature_columns.")

    required_base = {"lon", "lat", "year"}
    missing_base = sorted(required_base.difference(base_features))
    if missing_base:
        add_check(rows, "spatiotemporal base features", "failed", "Missing base features: " + ", ".join(missing_base))
    else:
        add_check(rows, "spatiotemporal base features", "ok", "Base features include lon, lat and year.")

    if not data.empty:
        missing_data_cols = [col for col in [*targets, *base_features] if col not in data.columns]
        if missing_data_cols:
            add_check(rows, "processed data columns", "failed", "Missing columns in " + rel(data_path) + ": " + ", ".join(missing_data_cols))
        else:
            add_check(
                rows,
                "processed data columns",
                "ok",
                f"{rel(data_path)} contains all target and base feature columns; rows={len(data)}, columns={data.shape[1]}.",
            )
        if "year" in data:
            years = pd.to_numeric(data["year"], errors="coerce").dropna()
            if len(years):
                add_check(rows, "processed data year span", "ok", f"Observed year span is {int(years.min())}-{int(years.max())}.")

    if not publication.empty:
        pub_targets = publication["target"].astype(str).tolist() if "target" in publication else []
        missing_targets = sorted(set(targets).difference(pub_targets))
        extra_targets = sorted(set(pub_targets).difference(targets))
        duplicate_targets = sorted(publication["target"].astype(str)[publication["target"].astype(str).duplicated()].unique().tolist()) if "target" in publication else []
        if missing_targets or extra_targets or duplicate_targets:
            detail = (
                f"missing={missing_targets or 'none'}; extra={extra_targets or 'none'}; "
                f"duplicates={duplicate_targets or 'none'}"
            )
            add_check(rows, "publication target coverage", "failed", detail)
        else:
            add_check(rows, "publication target coverage", "ok", "Publication metrics contain exactly one row for each configured target.")

        if "protocol" in publication:
            protocols = sorted(publication["protocol"].astype(str).unique().tolist())
            if protocols == ["temporal_2022_2026"]:
                add_check(rows, "publication protocol", "ok", "All publication rows use temporal_2022_2026.")
            else:
                add_check(rows, "publication protocol", "failed", "Unexpected protocols: " + ", ".join(protocols))

        if "source" in publication:
            pub_sources = set(publication["source"].astype(str))
            excluded = sorted(pub_sources.intersection(EXCLUDED_PUBLICATION_SOURCES))
            unknown = sorted(pub_sources.difference(ALLOWED_PUBLICATION_SOURCES))
            if excluded:
                add_check(rows, "publication source exclusion", "failed", "Publication table contains excluded exploration sources: " + ", ".join(excluded))
            else:
                add_check(rows, "publication source exclusion", "ok", "Publication table does not contain test-selected exploration sources.")
            if unknown:
                add_check(rows, "publication source allowlist", "warning", "Sources not in allowlist: " + ", ".join(unknown))
            else:
                add_check(rows, "publication source allowlist", "ok", "All publication sources are in the reproducible-source allowlist.")

        metric_cols = ["r2", "rmse", "mae", "mape"]
        missing_metric_cols = [col for col in metric_cols if col not in publication.columns]
        if missing_metric_cols:
            add_check(rows, "publication metric columns", "failed", "Missing metric columns: " + ", ".join(missing_metric_cols))
        elif publication[metric_cols].isna().any().any():
            add_check(rows, "publication metric columns", "failed", "Publication metric table contains NaN values.")
        else:
            add_check(rows, "publication metric columns", "ok", "R2, RMSE, MAE and MAPE are present without missing values.")

    if not model_cards.empty:
        card_targets = set(model_cards["target"].astype(str)) if "target" in model_cards else set()
        if card_targets == set(targets) and len(model_cards) == len(set(targets)):
            add_check(rows, "publication model card coverage", "ok", "Publication model cards contain exactly one row for each configured target.")
        else:
            add_check(rows, "publication model card coverage", "failed", f"targets={sorted(card_targets)}; rows={len(model_cards)}")
        if "future_alignment_status" in model_cards:
            exact_cards = int((model_cards["future_alignment_status"].astype(str) == "exact_publication_model").sum())
            status = "ok" if exact_cards == len(set(targets)) else "warning"
            add_check(rows, "publication model card future alignment", status, f"Exact publication future alignment cards: {exact_cards}/{len(set(targets))}.")
        if {"target", "fusion_n_members"}.issubset(model_cards.columns):
            fusion_cards = model_cards[model_cards.get("source", pd.Series(dtype=str)).astype(str) == "publication_validation_fusion"].copy()
            if fusion_cards.empty:
                add_check(rows, "publication model card fusion members", "ok", "No publication-validation-fusion target is selected in the current publication table.")
            else:
                member_counts = pd.to_numeric(fusion_cards["fusion_n_members"], errors="coerce").fillna(0)
                status = "ok" if int((member_counts > 0).sum()) == len(fusion_cards) else "warning"
                add_check(rows, "publication model card fusion members", status, f"Fusion member counts recorded: {member_counts.astype(int).tolist()}.")

    if not candidates.empty and "source" in candidates:
        candidate_sources = set(candidates["source"].astype(str))
        excluded_in_candidates = sorted(candidate_sources.intersection(EXCLUDED_PUBLICATION_SOURCES))
        if excluded_in_candidates:
            add_check(
                rows,
                "candidate exploration separation",
                "ok",
                "Candidate table keeps exploration sources for sensitivity analysis, while publication selection excludes: " + ", ".join(excluded_in_candidates),
            )
        else:
            add_check(rows, "candidate exploration separation", "warning", "No excluded exploration sources were found in the candidate table.")

    if not grid.empty:
        required_grid_cols = {"target", "year", "observed", "predicted", "tier"}
        missing_grid_cols = sorted(required_grid_cols.difference(grid.columns))
        if missing_grid_cols:
            add_check(rows, "recommended grid columns", "failed", "Missing columns: " + ", ".join(missing_grid_cols))
        else:
            pub_grid = grid[grid["tier"].astype(str) == "publication_grade"].copy()
            counts = pub_grid.groupby("target").size().to_dict()
            expected_n = int(publication["n_test"].iloc[0]) if not publication.empty and "n_test" in publication else 0
            count_ok = bool(expected_n) and set(map(str, counts.keys())) == set(targets) and all(int(value) == expected_n for value in counts.values())
            if count_ok:
                add_check(rows, "publication grid coverage", "ok", f"Publication prediction grid has {expected_n} rows per target and {len(pub_grid)} total rows.")
            else:
                add_check(rows, "publication grid coverage", "failed", f"Unexpected publication grid counts by target: {counts}.")
            years = pd.to_numeric(pub_grid["year"], errors="coerce").dropna()
            if len(years) and int(years.min()) >= 2022 and int(years.max()) <= 2026:
                add_check(rows, "publication grid years", "ok", f"Publication grid years are {int(years.min())}-{int(years.max())}.")
            else:
                add_check(rows, "publication grid years", "failed", "Publication grid years are outside 2022-2026 or missing.")
            if pub_grid[["observed", "predicted"]].isna().any().any():
                add_check(rows, "publication grid values", "failed", "Publication grid contains missing observed or predicted values.")
            else:
                add_check(rows, "publication grid values", "ok", "Publication grid observed and predicted values are complete.")

    if not future.empty:
        required_future_cols = {"lon", "lat", "year", "scenario", "target", "model", "predicted"}
        missing_future_cols = sorted(required_future_cols.difference(future.columns))
        forbidden_future_cols = sorted({"observed", "actual", "true", "y_true"}.intersection(future.columns))
        if missing_future_cols:
            add_check(rows, "future prediction columns", "failed", "Missing columns: " + ", ".join(missing_future_cols))
        elif forbidden_future_cols:
            add_check(rows, "future prediction columns", "failed", "Future prediction file contains observed target columns: " + ", ".join(forbidden_future_cols))
        else:
            add_check(rows, "future prediction columns", "ok", "Future file contains prediction fields only and no observed target column.")
        future_targets = set(future["target"].astype(str)) if "target" in future else set()
        future_years = sorted(pd.to_numeric(future["year"], errors="coerce").dropna().astype(int).unique().tolist()) if "year" in future else []
        if future_targets == set(targets) and future_years == list(range(2027, 2036)):
            add_check(rows, "future target-year coverage", "ok", "Future predictions cover all 8 targets and years 2027-2035.")
        else:
            add_check(rows, "future target-year coverage", "failed", f"targets={sorted(future_targets)}; years={future_years}")
        if "predicted" in future and pd.to_numeric(future["predicted"], errors="coerce").isna().any():
            add_check(rows, "future prediction values", "failed", "Future predicted column contains nonnumeric or missing values.")
        elif "predicted" in future:
            add_check(rows, "future prediction values", "ok", "Future predicted values are numeric and complete.")
        if "alignment_status" in future:
            status_counts = future.groupby("alignment_status")["target"].nunique().to_dict()
            fallback_targets = sorted(future.loc[future["alignment_status"] != "exact_publication_model", "target"].astype(str).unique().tolist())
            detail = f"Future predictions use publication-aligned file with status counts by target: {status_counts}."
            if fallback_targets:
                detail += " Documented fallback targets: " + ", ".join(fallback_targets) + "."
            expected_exact = len(set(targets))
            exact_targets = int(status_counts.get("exact_publication_model", 0))
            status = "ok" if exact_targets == expected_exact and not fallback_targets else "warning"
            if status == "ok":
                detail += " All configured targets use exact publication-model future prediction."
            add_check(rows, "future publication alignment metadata", status, detail)

    if not future.empty and not future_intervals.empty:
        required_interval_cols = {
            "target",
            "year",
            "predicted",
            "pred_lower",
            "pred_upper",
            "interval_width",
            "interval_method",
        }
        missing_interval_cols = sorted(required_interval_cols.difference(future_intervals.columns))
        if missing_interval_cols:
            add_check(rows, "future interval columns", "failed", "Missing interval columns: " + ", ".join(missing_interval_cols))
        elif len(future_intervals) != len(future):
            add_check(rows, "future interval coverage", "failed", f"Interval rows={len(future_intervals)} but future rows={len(future)}.")
        else:
            interval_targets = set(future_intervals["target"].astype(str))
            interval_years = sorted(pd.to_numeric(future_intervals["year"], errors="coerce").dropna().astype(int).unique().tolist())
            if interval_targets == set(targets) and interval_years == list(range(2027, 2036)):
                add_check(
                    rows,
                    "future interval coverage",
                    "ok",
                    f"Publication-aligned future intervals cover all targets and years; rows={len(future_intervals)}.",
                )
            else:
                add_check(rows, "future interval coverage", "failed", f"targets={sorted(interval_targets)}; years={interval_years}")
        if "alignment_status" in future_intervals:
            interval_status_counts = future_intervals.groupby("alignment_status")["target"].nunique().to_dict()
            exact_interval_targets = int(interval_status_counts.get("exact_publication_model", 0))
            status = "ok" if exact_interval_targets == len(set(targets)) else "warning"
            add_check(
                rows,
                "future interval publication alignment",
                status,
                f"Interval file alignment status counts by target: {interval_status_counts}.",
            )
        if {"pred_lower", "pred_upper"}.issubset(future_intervals.columns):
            bad_bounds = int((pd.to_numeric(future_intervals["pred_upper"], errors="coerce") < pd.to_numeric(future_intervals["pred_lower"], errors="coerce")).sum())
            status = "ok" if bad_bounds == 0 else "failed"
            add_check(rows, "future interval bounds", status, f"Rows with upper < lower: {bad_bounds}.")

    if not future_intervals.empty and not future_probabilities.empty:
        required_probability_cols = {
            "target",
            "year",
            "quantile",
            "threshold_value",
            "exceedance_probability",
            "probability_method",
        }
        missing_probability_cols = sorted(required_probability_cols.difference(future_probabilities.columns))
        if missing_probability_cols:
            add_check(rows, "future exceedance probability columns", "failed", "Missing probability columns: " + ", ".join(missing_probability_cols))
        else:
            quantiles = sorted(round(float(value), 2) for value in future_probabilities["quantile"].dropna().unique().tolist())
            expected_quantiles = [0.9, 0.95]
            expected_rows = len(future_intervals) * len(expected_quantiles)
            probability_targets = set(future_probabilities["target"].astype(str))
            probability_years = sorted(pd.to_numeric(future_probabilities["year"], errors="coerce").dropna().astype(int).unique().tolist())
            if (
                len(future_probabilities) == expected_rows
                and quantiles == expected_quantiles
                and probability_targets == set(targets)
                and probability_years == list(range(2027, 2036))
            ):
                add_check(
                    rows,
                    "future exceedance probability coverage",
                    "ok",
                    f"Probability table covers all targets, years and q90/q95; rows={len(future_probabilities)}.",
                )
            else:
                add_check(
                    rows,
                    "future exceedance probability coverage",
                    "failed",
                    f"rows={len(future_probabilities)} expected={expected_rows}; targets={sorted(probability_targets)}; years={probability_years}; quantiles={quantiles}",
                )
            probs = pd.to_numeric(future_probabilities["exceedance_probability"], errors="coerce")
            bad_probs = int((probs.isna() | (probs < 0) | (probs > 1)).sum())
            status = "ok" if bad_probs == 0 else "failed"
            add_check(rows, "future exceedance probability values", status, f"Rows outside [0, 1] or missing: {bad_probs}.")

    if not future_probability_map.empty:
        required_map_cols = {"target", "quantile", "year", "mean_probability", "high_prob_050_rate", "high_prob_080_rate"}
        missing_map_cols = sorted(required_map_cols.difference(future_probability_map.columns))
        if missing_map_cols:
            add_check(rows, "future exceedance map summary columns", "failed", "Missing map summary columns: " + ", ".join(missing_map_cols))
        else:
            focus_targets = [target for target in ["C", "F", "G"] if target in targets]
            expected_pairs = {
                (target, quantile, year)
                for target in focus_targets
                for quantile in [0.9, 0.95]
                for year in [2027, 2030, 2035]
            }
            actual_pairs = {
                (str(row.target), round(float(row.quantile), 2), int(row.year))
                for row in future_probability_map.itertuples(index=False)
            }
            missing_pairs = sorted(expected_pairs.difference(actual_pairs))
            status = "ok" if not missing_pairs else "failed"
            detail = (
                f"Map summary covers C/F/G q90/q95 years 2027, 2030 and 2035; rows={len(future_probability_map)}."
                if status == "ok"
                else f"Missing map summary pairs: {missing_pairs[:10]}"
            )
            add_check(rows, "future exceedance map summary coverage", status, detail)

    check_static_spatial_lag(rows)

    audit = pd.DataFrame(rows)
    audit.to_csv(TABLES_DIR / "leakage_publication_audit.csv", index=False, encoding="utf-8-sig")
    summary = {
        "status": "failed" if (audit["status"] == "failed").any() else ("warning" if (audit["status"] == "warning").any() else "ok"),
        "n_checks": int(len(audit)),
        "n_ok": int((audit["status"] == "ok").sum()),
        "n_warning": int((audit["status"] == "warning").sum()),
        "n_failed": int((audit["status"] == "failed").sum()),
        "data_path": rel(data_path),
        "publication_metrics": rel(publication_path),
        "future_predictions": rel(future_path),
    }
    (TABLES_DIR / "leakage_publication_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report_lines = [
        "# 审稿复现与防泄漏审计",
        "",
        "本报告检查论文主结果是否满足公开代码复现的基本约束：目标列不作为普通预测因子，论文主结果不混入测试集选择或测试集调权的探索上限，测试期和未来预测文件覆盖完整，目标空间滞后特征只引用训练期或已观测时期目标值。",
        "",
        "## 摘要",
        "",
        f"- 状态：`{summary['status']}`",
        f"- 检查项：{summary['n_checks']}",
        f"- 通过：{summary['n_ok']}",
        f"- 警告：{summary['n_warning']}",
        f"- 失败：{summary['n_failed']}",
        f"- 建模数据：`{summary['data_path']}`",
        "",
        "## 检查明细",
        "",
        md_table(audit),
        "",
        "## 使用说明",
        "",
        "- `ok` 表示当前文件和配置满足该项约束。",
        "- `warning` 表示不阻断复现，但需要在正文或补充材料中解释。",
        "- `failed` 表示公开复现前需要修复，否则可能产生目标泄漏、结果口径混乱或未来预测覆盖不完整的问题。",
        "",
        "机器可读结果见 `tables/leakage_publication_audit.csv` 和 `tables/leakage_publication_audit_summary.json`。",
        "",
    ]
    (DOCS_DIR / "leakage_publication_audit_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote leakage/publication audit outputs: {summary['status']}")
    if summary["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

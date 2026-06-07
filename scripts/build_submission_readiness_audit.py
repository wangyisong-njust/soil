#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs


TARGETS = list("ABCDEFGH")
FUTURE_YEARS = list(range(2027, 2036))


def exists_file(rel_path: str) -> bool:
    path = ROOT / rel_path
    return path.exists() and path.is_file() and path.stat().st_size > 0


def read_csv(rel_path: str) -> pd.DataFrame:
    path = ROOT / rel_path
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def read_json(rel_path: str) -> dict[str, object]:
    path = ROOT / rel_path
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def add_check(rows: list[dict[str, object]], item: str, status: str, evidence: str, recommendation: str = "") -> None:
    rows.append(
        {
            "item": item,
            "status": status,
            "evidence": evidence,
            "recommendation": recommendation,
        }
    )


def status_from_bool(ok: bool, warning: bool = False) -> str:
    if ok:
        return "ok"
    return "warning" if warning else "failed"


def status_from_soft_condition(ok: bool, soft_ok: bool = False) -> str:
    if ok:
        return "ok"
    return "warning" if soft_ok else "failed"


def main() -> None:
    ensure_project_dirs()
    rows: list[dict[str, object]] = []

    publication = read_csv("tables/publication_grade_recommended_metrics.csv")
    if publication.empty:
        add_check(rows, "Publication metrics table", "failed", "Missing tables/publication_grade_recommended_metrics.csv")
    else:
        targets = sorted(publication["target"].astype(str).unique().tolist())
        required_cols = {"target", "source", "method", "model", "r2", "rmse", "mae", "mape"}
        missing_cols = sorted(required_cols.difference(publication.columns))
        all_targets = targets == TARGETS
        add_check(
            rows,
            "Publication metrics cover 8 targets",
            status_from_bool(all_targets and not missing_cols),
            f"targets={targets}; missing_cols={missing_cols}",
            "Regenerate publication-grade recommendations if any target or metric column is missing.",
        )
        positive = int((pd.to_numeric(publication["r2"], errors="coerce") > 0).sum())
        add_check(
            rows,
            "Publication R2 is positive for all targets",
            status_from_bool(positive == 8, warning=True),
            f"positive_r2_targets={positive}/8; mean_r2={publication['r2'].mean():.4f}",
            "If this becomes a warning, explain low-R2 targets using distribution-shift and uncertainty diagnostics.",
        )

    eligibility = read_json("tables/candidate_eligibility_summary.json")
    eligibility_status = str(eligibility.get("status", "missing"))
    best_eligible = eligibility.get("n_publication_equals_best_eligible")
    add_check(
        rows,
        "Candidate eligibility audit",
        status_from_soft_condition(
            eligibility_status == "ok" and best_eligible == 8,
            eligibility_status == "review" and best_eligible not in (None, "NA"),
        ),
        f"status={eligibility_status}; best_eligible={eligibility.get('n_publication_equals_best_eligible', 'NA')}/8",
        "Treat review status as a documented limitation when excluded upper-bound classes use validation labels.",
    )

    model_cards = read_csv("tables/publication_model_cards.csv")
    if model_cards.empty:
        add_check(rows, "Publication model cards", "failed", "Missing tables/publication_model_cards.csv")
    else:
        exact_cards = int((model_cards["future_alignment_status"] == "exact_publication_model").sum())
        target_count = int(model_cards["target"].nunique())
        add_check(
            rows,
            "Publication model cards exact future alignment",
            status_from_soft_condition(target_count == 8 and exact_cards == 8, target_count == 8 and exact_cards > 0),
            f"targets={target_count}; exact_future_alignment={exact_cards}/8",
            "Use documented fallback future models when an exact publication model is unavailable for future grids.",
        )

    future = read_csv("results/future_predictions_publication_aligned_2027_2035.csv")
    if future.empty:
        add_check(rows, "Publication-aligned future predictions", "failed", "Missing future prediction file")
    else:
        targets = sorted(future["target"].astype(str).unique().tolist())
        years = sorted(pd.to_numeric(future["year"], errors="coerce").dropna().astype(int).unique().tolist())
        exact = int(future.loc[future["alignment_status"] == "exact_publication_model", "target"].nunique())
        coverage_ok = targets == TARGETS and years == FUTURE_YEARS
        add_check(
            rows,
            "Future predictions cover 2027-2035 and 8 targets",
            status_from_soft_condition(coverage_ok and exact == 8, coverage_ok and exact > 0),
            f"targets={targets}; years={years[0] if years else 'NA'}-{years[-1] if years else 'NA'}; rows={len(future)}; exact_targets={exact}/8",
            "Coverage must be complete; partial exact alignment is reported as a documented fallback warning.",
        )

    intervals = read_csv("results/future_predictions_publication_aligned_2027_2035_intervals.csv")
    if intervals.empty:
        add_check(rows, "Future prediction intervals", "failed", "Missing future interval file")
    else:
        bounds_ok = bool((pd.to_numeric(intervals["pred_lower"], errors="coerce") <= pd.to_numeric(intervals["pred_upper"], errors="coerce")).all())
        targets = int(intervals["target"].nunique())
        rel_width_ok = bool((pd.to_numeric(intervals["relative_interval_width"], errors="coerce") >= 0).all())
        add_check(
            rows,
            "Future prediction intervals have valid bounds",
            status_from_bool(bounds_ok and rel_width_ok and targets == 8),
            f"targets={targets}; bounds_ok={bounds_ok}; nonnegative_relative_width={rel_width_ok}; rows={len(intervals)}",
            "Run scripts/build_future_prediction_uncertainty.py if interval bounds are invalid.",
        )

    exceedance = read_csv("results/future_exceedance_probability_2027_2035.csv")
    if exceedance.empty:
        add_check(rows, "Future exceedance probabilities", "failed", "Missing future exceedance probability file")
    else:
        probabilities = pd.to_numeric(exceedance["exceedance_probability"], errors="coerce")
        prob_ok = bool(probabilities.between(0, 1).all())
        quantiles = sorted(pd.to_numeric(exceedance["quantile"], errors="coerce").dropna().round(2).unique().tolist())
        add_check(
            rows,
            "Future exceedance probabilities are valid",
            status_from_bool(prob_ok and quantiles == [0.9, 0.95] and exceedance["target"].nunique() == 8),
            f"targets={exceedance['target'].nunique()}; quantiles={quantiles}; probability_range=({probabilities.min():.4f}, {probabilities.max():.4f})",
            "Run scripts/build_future_exceedance_probability.py if probability coverage is incomplete.",
        )

    required_docs = [
        "docs/report.md",
        "docs/复现.md",
    ]
    missing_docs = [path for path in required_docs if not exists_file(path)]
    add_check(
        rows,
        "Core reports and writing aids",
        status_from_bool(not missing_docs),
        f"missing={missing_docs}",
        "Regenerate missing reports before handoff.",
    )

    validation_strategy = read_csv("tables/validation_strategy_summary.csv")
    ablation = read_csv("tables/framework_module_ablation_summary.csv")
    if validation_strategy.empty or ablation.empty:
        add_check(
            rows,
            "Validation strategy and M0-M6 ablation",
            "failed",
            "Missing validation strategy or ablation summary tables",
            "Run scripts/run_random_kfold_validation.py and scripts/build_validation_strategy_and_ablation.py.",
        )
    else:
        strategies = sorted(validation_strategy["validation"].astype(str).unique().tolist())
        required_strategies = ["future_year_independent_validation", "random_fivefold_cv", "spatial_block_cv"]
        modules = sorted(ablation["module_id"].astype(str).unique().tolist())
        complete = int((ablation["status"].astype(str) == "ok").sum()) if "status" in ablation else 0
        add_check(
            rows,
            "Validation strategy and M0-M6 ablation",
            status_from_bool(
                set(required_strategies).issubset(strategies)
                and modules == [f"M{i}" for i in range(7)]
                and complete == 7
            ),
            f"strategies={strategies}; modules={modules}; complete_modules={complete}/7",
            "Regenerate validation and ablation outputs if any strategy or module is missing.",
        )

    required_figures = [
        "figures/recommended_predictions/publication_grade_observed_predicted_grid.png",
        "figures/manuscript_summary/manuscript_results_overview.png",
        "figures/feature_importance_summary/shap_group_contribution_heatmap.png",
        "figures/future_exceedance_probability_maps/F_q90_2035_probability_map.png",
        "figures/validation_strategy/random_fivefold_best_r2.png",
        "figures/validation_strategy/framework_module_ablation_mean_r2.png",
    ]
    missing_figures = [path for path in required_figures if not exists_file(path)]
    add_check(
        rows,
        "Core figures",
        status_from_bool(not missing_figures),
        f"missing={missing_figures}",
        "Regenerate figures if any required figure is missing.",
    )

    leakage = read_json("tables/leakage_publication_audit_summary.json")
    leakage_failed = int(leakage.get("n_failed", 0) or 0)
    leakage_warning = int(leakage.get("n_warning", 0) or 0)
    add_check(
        rows,
        "Leakage and publication reproducibility audit",
        status_from_soft_condition(
            leakage.get("status") == "ok" and leakage_failed == 0,
            leakage_failed == 0 and leakage_warning > 0,
        ),
        f"status={leakage.get('status', 'missing')}; failed={leakage.get('n_failed', 'NA')}; warning={leakage.get('n_warning', 'NA')}",
        "Fix hard failures; warnings document future-grid fallback or non-critical alignment differences.",
    )

    markdown = read_json("tables/markdown_reference_check_summary.json")
    add_check(
        rows,
        "Markdown local reference integrity",
        status_from_bool(markdown.get("status") == "ok" and markdown.get("n_missing") == 0),
        f"status={markdown.get('status', 'missing')}; references={markdown.get('n_references', 'NA')}; missing={markdown.get('n_missing', 'NA')}",
        "Run scripts/check_markdown_references.py and fix missing local references.",
    )

    delivery = read_json("tables/delivery_audit_summary.json")
    add_check(
        rows,
        "Delivery artifact manifest",
        status_from_bool(delivery.get("n_missing_items") == 0),
        f"manifest_items={delivery.get('n_manifest_items', 'NA')}; missing={delivery.get('n_missing_items', 'NA')}",
        "Run scripts/build_delivery_audit.py and regenerate missing required artifacts.",
    )

    run_project = (ROOT / "run_project.py").read_text(encoding="utf-8")
    required_params = ["RAW_EXCEL", "TARGET_COLUMNS", "BASE_FEATURE_COLUMNS", "TEMPORAL_TEST_START_YEAR", "FUTURE_YEARS"]
    missing_params = [name for name in required_params if name not in run_project]
    add_check(
        rows,
        "Data and parameter replacement entry",
        status_from_bool(not missing_params),
        f"missing_params={missing_params}",
        "Keep data path, target columns, predictor columns, validation year, and future years in the top parameter block.",
    )

    scanned_paths = list((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]
    forbidden_hits: list[str] = []
    handoff_term = "客" + "户"
    local_home_term = "/" + "home" + "/" + "kaixin"
    for path in scanned_paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if handoff_term in text or local_home_term in text:
            forbidden_hits.append(str(path.relative_to(ROOT)))
    add_check(
        rows,
        "Public-facing text hygiene",
        status_from_bool(not forbidden_hits),
        f"forbidden_hits={forbidden_hits}",
        "Remove direct handoff wording and local absolute paths from public-facing Markdown.",
    )

    audit = pd.DataFrame(rows)
    audit.to_csv(TABLES_DIR / "submission_readiness_audit.csv", index=False, encoding="utf-8-sig")
    n_failed = int((audit["status"] == "failed").sum())
    n_warning = int((audit["status"] == "warning").sum())
    n_ok = int((audit["status"] == "ok").sum())
    summary = {
        "status": "ok" if n_failed == 0 and n_warning == 0 else ("warning" if n_failed == 0 else "failed"),
        "n_checks": int(len(audit)),
        "n_ok": n_ok,
        "n_warning": n_warning,
        "n_failed": n_failed,
    }
    (TABLES_DIR / "submission_readiness_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    show = audit.copy()
    report = [
        "# 投稿准备度审计",
        "",
        "本报告集中检查当前项目是否具备投稿、补充材料或公开复现所需的核心证据链。审计不改变模型结果，只核对当前工作区真实存在的指标、预测、图表、文档和防泄漏状态。",
        "",
        "## 审计摘要",
        "",
        f"- 检查项：{summary['n_checks']}",
        f"- 通过：{summary['n_ok']}",
        f"- 警告：{summary['n_warning']}",
        f"- 失败：{summary['n_failed']}",
        f"- 总状态：`{summary['status']}`",
        "",
        "## 详细清单",
        "",
        "| item | status | evidence | recommendation |",
        "| --- | --- | --- | --- |",
    ]
    for row in show.to_dict("records"):
        report.append(
            f"| {row['item']} | {row['status']} | {str(row['evidence']).replace('|', '/')} | {str(row['recommendation']).replace('|', '/')} |"
        )
    report.extend(
        [
            "",
            "## 使用说明",
            "",
            "- `ok` 表示当前证据满足投稿准备度要求。",
            "- `warning` 表示材料可用但需要在论文中解释限制。",
            "- `failed` 表示缺少关键文件或存在不一致，公开代码或交付前应修复。",
            "",
        ]
    )
    legacy_docs = ROOT / "archive" / "legacy_docs"
    legacy_docs.mkdir(parents=True, exist_ok=True)
    (legacy_docs / "submission_readiness_audit_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote submission readiness audit outputs")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs


ELIGIBILITY_RULES = {
    "external_public_covariates": (
        True,
        "public_result",
        "Uses measured or public covariates and does not tune on 2022-2026 target values.",
    ),
    "spatiotemporal_innovation": (
        True,
        "public_result",
        "Predefined spatiotemporal feature/model family evaluated without 2022-2026 target-value selection.",
    ),
    "multitask_latent": (
        True,
        "public_result",
        "Latent pollution-factor model evaluated without 2022-2026 target-value selection.",
    ),
    "arima_lstm_temporal": (
        True,
        "public_result",
        "Temporal sequence baseline evaluated without 2022-2026 target-value selection.",
    ),
    "distributional_robust": (
        True,
        "public_result",
        "Distributional transformation and robust-loss model evaluated as a predefined candidate family.",
    ),
    "local_analog_memory": (
        True,
        "public_result",
        "Local historical analog model evaluated without 2022-2026 target-value selection.",
    ),
    "causal_history_memory": (
        True,
        "public_result",
        "Historical memory model evaluated without 2022-2026 target-value selection.",
    ),
    "quantile_risk_gate": (
        True,
        "public_result",
        "Risk-gated quantile model evaluated without 2022-2026 target-value selection.",
    ),
    "spatial_distribution_features": (
        True,
        "public_result",
        "Target-specific spatial distribution features evaluated without 2022-2026 target-value selection.",
    ),
    "multi_evidence_fusion": (
        True,
        "public_result",
        "Validation-defined multi-evidence fusion retained as a candidate when weights are not fitted on 2022-2026.",
    ),
    "distribution_guided_spatial_quantile": (
        True,
        "public_result",
        "Distribution rule is fixed from training-period distribution diagnostics.",
    ),
    "publication_validation_fusion": (
        True,
        "public_result",
        "Fusion members and weights are fixed from 2019-2020 validation before 2022-2026 testing.",
    ),
    "validation_transfer_calibration": (
        True,
        "public_result",
        "Calibration is selected from 2019-2020 validation and then fixed for 2022-2026 testing.",
    ),
    "spatial_quantile_validated": (
        True,
        "public_sensitivity",
        "Spatial quantile parameters are selected from 2019-2020 validation; suitable as sensitivity analysis.",
    ),
    "spatial_quantile_yearwise_validated": (
        True,
        "public_sensitivity",
        "Spatial quantile parameters are selected by yearwise 2019 and 2020 validation stability.",
    ),
    "yearwise_validation_selected_publication": (
        True,
        "public_sensitivity",
        "Model selection uses predefined 2019 and 2020 validation-year rules.",
    ),
    "predefined_recent_median_baseline": (
        True,
        "public_baseline",
        "Predefined recent median baseline; useful as a guardrail, not an optimized main model.",
    ),
    "conservative_baseline": (
        False,
        "test_grid_search_upper_bound",
        "Contains many distribution constants and quantiles compared directly on 2022-2026; keep as diagnostic only.",
    ),
    "spatial_quantile_baseline": (
        False,
        "test_grid_search_upper_bound",
        "KNN/grid and quantile hyperparameters are searched directly against 2022-2026 target values.",
    ),
    "temporal_calibration_exploration": (
        False,
        "test_selected_oracle",
        "Best row is selected by 2022-2026 target performance; use only as exploration upper bound.",
    ),
    "spatial_model_blend_exploration": (
        False,
        "test_selected_oracle",
        "Blend weights are selected against 2022-2026 target performance.",
    ),
    "nnls_stack_exploration": (
        False,
        "same_test_set_fit_upper_bound",
        "Stacking weights are fitted and evaluated on the same 2022-2026 target set.",
    ),
    "validation_transfer_test_selected_exploration": (
        False,
        "test_selected_oracle",
        "Transfer-calibration form is selected by 2022-2026 target performance.",
    ),
}


def md_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
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


def fmt(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out:
            out[col] = pd.to_numeric(out[col], errors="coerce").map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    return out


def eligibility_for_source(source: str) -> tuple[bool, str, str]:
    if source in ELIGIBILITY_RULES:
        return ELIGIBILITY_RULES[source]
    return False, "unknown_source", "Source is not classified; keep out of publication main results until reviewed."


def candidate_key(df: pd.DataFrame) -> pd.Series:
    return (
        df["target"].astype(str)
        + "||"
        + df["source"].astype(str)
        + "||"
        + df["method"].astype(str)
        + "||"
        + df["model"].astype(str)
    )


def main() -> None:
    ensure_project_dirs()
    candidates_path = TABLES_DIR / "final_adaptive_candidate_metrics.csv"
    publication_path = TABLES_DIR / "publication_grade_recommended_metrics.csv"
    if not candidates_path.exists() or candidates_path.stat().st_size == 0:
        raise SystemExit("Missing tables/final_adaptive_candidate_metrics.csv")
    if not publication_path.exists() or publication_path.stat().st_size == 0:
        raise SystemExit("Missing tables/publication_grade_recommended_metrics.csv")

    candidates = pd.read_csv(candidates_path)
    publication = pd.read_csv(publication_path)
    candidates = candidates[(candidates["protocol"] == "temporal_2022_2026") & candidates["r2"].notna()].copy()

    rules = candidates["source"].astype(str).map(eligibility_for_source)
    candidates["eligible_for_main_result"] = [rule[0] for rule in rules]
    candidates["eligibility_class"] = [rule[1] for rule in rules]
    candidates["eligibility_reason"] = [rule[2] for rule in rules]
    candidates["candidate_key"] = candidate_key(candidates)
    publication_keys = set(candidate_key(publication.assign(protocol="temporal_2022_2026")))
    candidates["selected_publication_main"] = candidates["candidate_key"].isin(publication_keys)

    best_eligible = (
        candidates[candidates["eligible_for_main_result"]]
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    best_excluded = (
        candidates[~candidates["eligible_for_main_result"]]
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    publication_compact = publication[["target", "source", "method", "model", "r2", "rmse", "mae", "mape"]].copy()
    publication_compact = publication_compact.rename(
        columns={
            "source": "publication_source",
            "method": "publication_method",
            "model": "publication_model",
            "r2": "publication_r2",
            "rmse": "publication_rmse",
            "mae": "publication_mae",
            "mape": "publication_mape",
        }
    )
    eligible_compact = best_eligible[["target", "source", "method", "model", "r2", "rmse"]].rename(
        columns={
            "source": "best_eligible_source",
            "method": "best_eligible_method",
            "model": "best_eligible_model",
            "r2": "best_eligible_r2",
            "rmse": "best_eligible_rmse",
        }
    )
    excluded_compact = best_excluded[["target", "source", "method", "model", "r2", "rmse", "eligibility_class"]].rename(
        columns={
            "source": "best_excluded_source",
            "method": "best_excluded_method",
            "model": "best_excluded_model",
            "r2": "best_excluded_r2",
            "rmse": "best_excluded_rmse",
            "eligibility_class": "best_excluded_class",
        }
    )
    counts = (
        candidates.groupby("target", as_index=False)
        .agg(
            n_candidates=("target", "size"),
            n_eligible=("eligible_for_main_result", "sum"),
            n_selected=("selected_publication_main", "sum"),
        )
    )
    counts["n_excluded"] = counts["n_candidates"] - counts["n_eligible"]
    summary = (
        publication_compact.merge(eligible_compact, on="target", how="left")
        .merge(excluded_compact, on="target", how="left")
        .merge(counts, on="target", how="left")
        .sort_values("target")
    )
    summary["publication_equals_best_eligible"] = (
        summary["publication_source"].astype(str).eq(summary["best_eligible_source"].astype(str))
        & summary["publication_method"].astype(str).eq(summary["best_eligible_method"].astype(str))
        & summary["publication_model"].astype(str).eq(summary["best_eligible_model"].astype(str))
    )
    summary["r2_gap_to_excluded_upper_bound"] = summary["best_excluded_r2"] - summary["publication_r2"]
    summary["r2_gap_to_best_eligible"] = summary["best_eligible_r2"] - summary["publication_r2"]
    summary["status"] = summary["publication_equals_best_eligible"].map(
        {True: "ok_publication_is_best_eligible", False: "review_publication_not_best_eligible"}
    )

    source_summary = (
        candidates.groupby(["source", "eligible_for_main_result", "eligibility_class"], as_index=False)
        .agg(
            n_rows=("target", "size"),
            n_targets=("target", "nunique"),
            mean_r2=("r2", "mean"),
            max_r2=("r2", "max"),
            min_r2=("r2", "min"),
            n_positive=("r2", lambda value: int((value > 0).sum())),
        )
        .sort_values(["eligible_for_main_result", "mean_r2"], ascending=[False, False])
    )
    rules_df = pd.DataFrame(
        [
            {
                "source": source,
                "eligible_for_main_result": eligible,
                "eligibility_class": cls,
                "eligibility_reason": reason,
            }
            for source, (eligible, cls, reason) in sorted(ELIGIBILITY_RULES.items())
        ]
    )

    audit_cols = [
        "protocol",
        "target",
        "source",
        "method",
        "model",
        "r2",
        "rmse",
        "mae",
        "mape",
        "eligible_for_main_result",
        "eligibility_class",
        "eligibility_reason",
        "selected_publication_main",
    ]
    candidates[audit_cols].sort_values(["target", "eligible_for_main_result", "r2"], ascending=[True, False, False]).to_csv(
        TABLES_DIR / "candidate_eligibility_audit.csv", index=False, encoding="utf-8-sig"
    )
    summary.to_csv(TABLES_DIR / "candidate_eligibility_summary.csv", index=False, encoding="utf-8-sig")
    source_summary.to_csv(TABLES_DIR / "candidate_eligibility_source_summary.csv", index=False, encoding="utf-8-sig")
    rules_df.to_csv(TABLES_DIR / "candidate_eligibility_rules.csv", index=False, encoding="utf-8-sig")

    n_ok = int(summary["publication_equals_best_eligible"].sum())
    n_targets = int(summary["target"].nunique())
    n_excluded_better = int((summary["r2_gap_to_excluded_upper_bound"] > 0).sum())
    machine_summary = {
        "status": "ok" if n_ok == n_targets else "review",
        "n_targets": n_targets,
        "n_publication_equals_best_eligible": n_ok,
        "n_excluded_upper_bound_better_than_publication": n_excluded_better,
        "mean_publication_r2": float(summary["publication_r2"].mean()),
        "mean_best_excluded_r2": float(summary["best_excluded_r2"].mean()),
        "max_gap_to_excluded_upper_bound": float(summary["r2_gap_to_excluded_upper_bound"].max()),
    }
    (TABLES_DIR / "candidate_eligibility_summary.json").write_text(
        json.dumps(machine_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    show_summary = summary[
        [
            "target",
            "publication_source",
            "publication_model",
            "publication_r2",
            "best_excluded_source",
            "best_excluded_model",
            "best_excluded_r2",
            "best_excluded_class",
            "r2_gap_to_excluded_upper_bound",
            "status",
        ]
    ].copy()
    show_summary = fmt(show_summary, ["publication_r2", "best_excluded_r2", "r2_gap_to_excluded_upper_bound"])
    show_sources = source_summary[
        ["source", "eligible_for_main_result", "eligibility_class", "n_rows", "n_targets", "mean_r2", "max_r2", "min_r2"]
    ].copy()
    show_sources = fmt(show_sources, ["mean_r2", "max_r2", "min_r2"])
    report = [
        "# 候选模型资格审计",
        "",
        "本报告用于解释为什么某些候选模型 R2 更高但不能作为论文主结果。审计对象为 `tables/final_adaptive_candidate_metrics.csv` 中 2022-2026 时间外推候选，按预设规则标记是否可进入论文主验证表。",
        "",
        "## 审计摘要",
        "",
        f"- 目标数：{n_targets}",
        f"- 当前论文主结果等于合规候选最优的目标数：{n_ok}/{n_targets}",
        f"- 探索上限高于论文主结果的目标数：{n_excluded_better}/{n_targets}",
        f"- 论文主结果平均 R2：{machine_summary['mean_publication_r2']:.4f}",
        f"- 探索上限平均 R2：{machine_summary['mean_best_excluded_r2']:.4f}",
        f"- 最大探索上限差距：{machine_summary['max_gap_to_excluded_upper_bound']:.4f}",
        "",
        "## 目标级审计",
        "",
        md_table(show_summary),
        "",
        "## 来源级审计",
        "",
        md_table(show_sources, max_rows=30),
        "",
        "## 使用说明",
        "",
        "- `eligible_for_main_result=True` 的候选可进入论文主结果竞争池，但仍需按统一时间外推测试指标排序。",
        "- `test_selected_oracle`、`same_test_set_fit_upper_bound` 和 `test_grid_search_upper_bound` 只能作为探索上限或诊断，不能写成独立验证主结果。",
        "- 若审稿人质疑为什么不用更高 R2，可引用本报告说明高 R2 来源使用了 2022-2026 测试期目标值进行选型、调权或同集拟合。",
        "",
        "## 输出文件",
        "",
        "- 候选逐行审计：`tables/candidate_eligibility_audit.csv`",
        "- 目标级摘要：`tables/candidate_eligibility_summary.csv`",
        "- 来源级摘要：`tables/candidate_eligibility_source_summary.csv`",
        "- 资格规则：`tables/candidate_eligibility_rules.csv`",
        "- 机器可读摘要：`tables/candidate_eligibility_summary.json`",
        "",
    ]
    (DOCS_DIR / "candidate_eligibility_audit_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote candidate eligibility audit outputs")


if __name__ == "__main__":
    main()

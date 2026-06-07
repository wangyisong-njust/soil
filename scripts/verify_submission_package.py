#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs


REQUIRED_TARGETS = list("ABCDEFGH")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the current submission package from generated audit summaries.")
    parser.add_argument("--allow-warnings", action="store_true", help="Return success when warnings exist but no failures exist.")
    return parser.parse_args()


def read_json(rel_path: str) -> dict[str, object]:
    path = ROOT / rel_path
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(rel_path: str) -> pd.DataFrame:
    path = ROOT / rel_path
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def file_status(rel_path: str) -> tuple[bool, str]:
    path = ROOT / rel_path
    if not path.exists():
        return False, "missing"
    if path.is_file() and path.stat().st_size == 0:
        return False, "empty"
    return True, f"{path.stat().st_size} bytes"


def add(rows: list[dict[str, object]], gate: str, status: str, evidence: str, required: bool = True) -> None:
    rows.append({"gate": gate, "status": status, "required": required, "evidence": evidence})


def ok_status(condition: bool, warning: bool = False) -> str:
    if condition:
        return "ok"
    return "warning" if warning else "failed"


def summary_status(data: dict[str, object], ok_condition: bool, warning_condition: bool = False) -> str:
    if ok_condition:
        return "ok"
    return "warning" if warning_condition else "failed"


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No records._"
    text = df.astype(str)
    lines = [
        "| " + " | ".join(text.columns) + " |",
        "| " + " | ".join(["---"] * len(text.columns)) + " |",
    ]
    for row in text.values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    rows: list[dict[str, object]] = []

    publication = read_csv("tables/publication_grade_recommended_metrics.csv")
    if publication.empty:
        add(rows, "Publication metrics", "failed", "Missing or empty tables/publication_grade_recommended_metrics.csv")
    else:
        targets = sorted(publication["target"].astype(str).unique().tolist())
        r2 = pd.to_numeric(publication["r2"], errors="coerce")
        add(
            rows,
            "Publication metrics",
            ok_status(targets == REQUIRED_TARGETS and int((r2 > 0).sum()) == 8),
            f"targets={targets}; positive_r2={int((r2 > 0).sum())}/8; mean_r2={r2.mean():.4f}",
        )

    summary_checks = [
        (
            "Submission readiness",
            "tables/submission_readiness_audit_summary.json",
            lambda data: data.get("status") == "ok" and data.get("n_failed") == 0,
            lambda data: data.get("status") == "warning" and data.get("n_failed") == 0,
            lambda data: f"status={data.get('status', 'missing')}; failed={data.get('n_failed', 'NA')}; warnings={data.get('n_warning', 'NA')}; checks={data.get('n_checks', 'NA')}",
        ),
        (
            "Delivery manifest",
            "tables/delivery_audit_summary.json",
            lambda data: data.get("n_missing_items") == 0,
            lambda data: False,
            lambda data: f"manifest_items={data.get('n_manifest_items', 'NA')}; missing={data.get('n_missing_items', 'NA')}",
        ),
        (
            "Leakage audit",
            "tables/leakage_publication_audit_summary.json",
            lambda data: data.get("status") == "ok" and data.get("n_failed") == 0,
            lambda data: data.get("status") == "warning" and data.get("n_failed") == 0,
            lambda data: f"status={data.get('status', 'missing')}; failed={data.get('n_failed', 'NA')}; warnings={data.get('n_warning', 'NA')}",
        ),
        (
            "Markdown references",
            "tables/markdown_reference_check_summary.json",
            lambda data: data.get("status") == "ok" and data.get("n_missing") == 0,
            lambda data: False,
            lambda data: f"status={data.get('status', 'missing')}; references={data.get('n_references', 'NA')}; missing={data.get('n_missing', 'NA')}",
        ),
        (
            "Candidate eligibility",
            "tables/candidate_eligibility_summary.json",
            lambda data: data.get("status") == "ok" and data.get("n_publication_equals_best_eligible") == 8,
            lambda data: data.get("status") == "review" and data.get("n_publication_equals_best_eligible") is not None,
            lambda data: f"status={data.get('status', 'missing')}; best_eligible={data.get('n_publication_equals_best_eligible', 'NA')}/8",
        ),
        (
            "Project delivery guide",
            "tables/project_delivery_guide_summary.json",
            lambda data: data.get("status") == "ok" and data.get("submission_readiness_status") == "ok",
            lambda data: data.get("status") == "ok" and data.get("submission_readiness_status") == "warning",
            lambda data: f"status={data.get('status', 'missing')}; readiness={data.get('submission_readiness_status', 'NA')}",
        ),
        (
            "M0-M6 ablation",
            "tables/framework_module_ablation_summary.json",
            lambda data: data.get("status") == "ok" and data.get("n_complete_modules") == 7,
            lambda data: False,
            lambda data: f"status={data.get('status', 'missing')}; complete_modules={data.get('n_complete_modules', 'NA')}/{data.get('n_modules', 'NA')}",
        ),
    ]
    for gate, rel_path, predicate, warning_predicate, evidence_fn in summary_checks:
        data = read_json(rel_path)
        add(
            rows,
            gate,
            summary_status(data, bool(data) and predicate(data), bool(data) and warning_predicate(data)),
            evidence_fn(data) if data else f"missing {rel_path}",
        )

    required_files = [
        "docs/project_delivery_guide.md",
        "docs/report.md",
        "docs/reproduction.md",
        "docs/validation_strategy_and_ablation_report.md",
        "docs/submission_readiness_audit_report.md",
        "docs/manuscript_text_snippets.md",
        "figures/manuscript_summary/manuscript_results_overview.png",
        "figures/validation_strategy/framework_module_ablation_mean_r2.png",
        "results/future_predictions_publication_aligned_2027_2035.csv",
        "results/future_predictions_publication_aligned_2027_2035_intervals.csv",
        "results/future_exceedance_probability_2027_2035.csv",
    ]
    missing_files: list[str] = []
    file_evidence: list[str] = []
    for rel_path in required_files:
        exists, detail = file_status(rel_path)
        if not exists:
            missing_files.append(rel_path)
        file_evidence.append(f"{rel_path}={detail}")
    add(
        rows,
        "Core package files",
        ok_status(not missing_files),
        "; ".join(file_evidence),
    )

    audit = pd.DataFrame(rows)
    n_failed = int((audit["status"] == "failed").sum())
    n_warning = int((audit["status"] == "warning").sum())
    n_ok = int((audit["status"] == "ok").sum())
    status = "ok" if n_failed == 0 and (args.allow_warnings or n_warning == 0) else "failed"
    summary = {
        "status": status,
        "n_gates": int(len(audit)),
        "n_ok": n_ok,
        "n_warning": n_warning,
        "n_failed": n_failed,
        "allow_warnings": bool(args.allow_warnings),
    }
    audit.to_csv(TABLES_DIR / "submission_package_verification.csv", index=False, encoding="utf-8-sig")
    (TABLES_DIR / "submission_package_verification_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# 一键验收报告",
        "",
        "本报告由 `scripts/verify_submission_package.py` 生成，用于在交付、投稿或换数据复现后快速判断当前材料包是否通过关键质量门。脚本只读取已有结果和审计摘要，不重新训练模型。",
        "",
        "## 摘要",
        "",
        f"- 状态：`{summary['status']}`",
        f"- 质量门：{summary['n_gates']}",
        f"- 通过：{summary['n_ok']}",
        f"- 警告：{summary['n_warning']}",
        f"- 失败：{summary['n_failed']}",
        "",
        "## 明细",
        "",
        md_table(audit),
        "",
        "机器可读结果见 `tables/submission_package_verification.csv` 和 `tables/submission_package_verification_summary.json`。",
        "",
    ]
    (DOCS_DIR / "submission_package_verification_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Submission package verification: {status} ({n_ok} ok, {n_warning} warning, {n_failed} failed)")
    if status != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python
from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


HASH_FILES = [
    "configs/soil_experiment.json",
    "run_project.py",
    "requirements.txt",
    "tables/publication_grade_recommended_metrics.csv",
    "tables/validation_strategy_summary.csv",
    "tables/spatial_baseline_residual_fixed_best_metrics.csv",
    "tables/framework_module_ablation_summary.csv",
    "tables/framework_module_ablation_m0_m6.csv",
    "tables/framework_module_ablation_summary.json",
    "tables/publication_model_cards.csv",
    "tables/candidate_eligibility_summary.csv",
    "tables/submission_readiness_audit_summary.json",
    "tables/submission_package_verification_summary.json",
    "results/future_predictions_publication_aligned_2027_2035.csv",
    "results/future_predictions_publication_aligned_2027_2035_intervals.csv",
    "results/future_exceedance_probability_2027_2035.csv",
    "figures/manuscript_summary/manuscript_results_overview.png",
    "figures/validation_strategy/framework_module_ablation_mean_r2.png",
    "docs/project_delivery_guide.md",
    "docs/report.md",
    "docs/reproduction.md",
    "docs/spatial_baseline_residual_fixed_report.md",
    "docs/validation_strategy_and_ablation_report.md",
]

PACKAGE_NAMES = [
    "pandas",
    "numpy",
    "scipy",
    "scikit-learn",
    "matplotlib",
    "xgboost",
    "lightgbm",
    "catboost",
    "ngboost",
    "shap",
    "statsmodels",
    "torch",
    "rasterio",
    "requests",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_row(rel_path: str) -> dict[str, object]:
    path = ROOT / rel_path
    exists = path.exists() and path.is_file() and path.stat().st_size > 0
    row: dict[str, object] = {
        "path": rel_path,
        "status": "ok" if exists else "missing",
        "size_bytes": int(path.stat().st_size) if exists else 0,
        "sha256": sha256(path) if exists else "",
    }
    if exists and path.suffix.lower() == ".csv":
        try:
            row["n_rows"] = int(sum(1 for _ in path.open("rb")) - 1)
        except OSError:
            row["n_rows"] = ""
    else:
        row["n_rows"] = ""
    return row


def package_row(name: str) -> dict[str, str]:
    try:
        version = metadata.version(name)
        status = "ok"
    except metadata.PackageNotFoundError:
        version = ""
        status = "missing"
    return {"package": name, "version": version, "status": status}


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
    data_path = preferred_processed_data_path()
    hash_paths = [str(data_path.relative_to(ROOT)), *HASH_FILES]
    seen: set[str] = set()
    file_rows = []
    for rel_path in hash_paths:
        if rel_path in seen:
            continue
        seen.add(rel_path)
        file_rows.append(file_row(rel_path))
    files = pd.DataFrame(file_rows)
    packages = pd.DataFrame([package_row(name) for name in PACKAGE_NAMES])

    publication = pd.read_csv(ROOT / "tables" / "publication_grade_recommended_metrics.csv")
    r2 = pd.to_numeric(publication["r2"], errors="coerce")
    verification = {}
    verification_path = ROOT / "tables" / "submission_package_verification_summary.json"
    if verification_path.exists() and verification_path.stat().st_size:
        verification = json.loads(verification_path.read_text(encoding="utf-8"))
    readiness = {}
    readiness_path = ROOT / "tables" / "submission_readiness_audit_summary.json"
    if readiness_path.exists() and readiness_path.stat().st_size:
        readiness = json.loads(readiness_path.read_text(encoding="utf-8"))

    summary = {
        "status": "ok" if (files["status"] == "ok").all() else "missing_files",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "data_file": str(data_path.relative_to(ROOT)),
        "n_hash_files": int(len(files)),
        "n_missing_hash_files": int((files["status"] != "ok").sum()),
        "n_packages": int(len(packages)),
        "n_missing_packages": int((packages["status"] != "ok").sum()),
        "publication_mean_r2": float(r2.mean()),
        "publication_median_r2": float(r2.median()),
        "publication_positive_r2_targets": int((r2 > 0).sum()),
        "submission_verification_status": verification.get("status", "unknown"),
        "submission_readiness_status": readiness.get("status", "unknown"),
    }
    files.to_csv(TABLES_DIR / "reproducibility_snapshot_files.csv", index=False, encoding="utf-8-sig")
    packages.to_csv(TABLES_DIR / "reproducibility_snapshot_packages.csv", index=False, encoding="utf-8-sig")
    (TABLES_DIR / "reproducibility_snapshot_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    display_files = files[["path", "status", "size_bytes", "n_rows", "sha256"]].copy()
    display_files["sha256"] = display_files["sha256"].map(lambda value: str(value)[:16] + "..." if value else "")
    lines = [
        "# 复现快照",
        "",
        "本报告记录当前项目关键输入、配置、结果、图件和文档的文件哈希，以及主要 Python 包版本。它用于换机器、换数据或提交补充材料后核对复现版本。",
        "",
        "## 摘要",
        "",
        f"- 生成时间 UTC：{summary['generated_at_utc']}",
        f"- Python：{summary['python']}",
        f"- 平台：{summary['platform']}",
        f"- 建模数据：`{summary['data_file']}`",
        f"- 文件哈希条目：{summary['n_hash_files']}，缺失 {summary['n_missing_hash_files']}",
        f"- 包版本条目：{summary['n_packages']}，缺失 {summary['n_missing_packages']}",
        f"- 论文主结果平均 R2：{summary['publication_mean_r2']:.4f}",
        f"- 论文主结果中位 R2：{summary['publication_median_r2']:.4f}",
        f"- 正 R2 目标数：{summary['publication_positive_r2_targets']}/8",
        f"- 一键验收状态：`{summary['submission_verification_status']}`",
        f"- 投稿准备度状态：`{summary['submission_readiness_status']}`",
        "",
        "## 文件哈希",
        "",
        md_table(display_files),
        "",
        "## Python 包版本",
        "",
        md_table(packages),
        "",
        "机器可读结果见 `tables/reproducibility_snapshot_summary.json`、`tables/reproducibility_snapshot_files.csv` 和 `tables/reproducibility_snapshot_packages.csv`。",
        "",
    ]
    (DOCS_DIR / "reproducibility_snapshot.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote reproducibility snapshot")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs


DOC_PATHS = [ROOT / "README.md", *sorted(DOCS_DIR.glob("*.md"))]
CHECK_PREFIXES = (
    "configs/",
    "data/",
    "docs/",
    "figures/",
    "models/",
    "results/",
    "scripts/",
    "src/",
    "tables/",
    "run_project.py",
    "README.md",
    "requirements.txt",
)
PLACEHOLDER_TOKENS = ("<", ">", "*", "...")
URL_PREFIXES = ("http://", "https://", "file://", "mailto:")
GENERATED_OUTPUTS = {
    "docs/markdown_reference_check_report.md",
    "tables/markdown_reference_check.csv",
    "tables/markdown_reference_check_summary.json",
}


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


def clean_candidate(text: str) -> str:
    text = text.strip().strip(".,;:，。；：)")
    if text.startswith("./"):
        text = text[2:]
    return text


def should_check(path: str) -> bool:
    if not path or path.startswith(URL_PREFIXES):
        return False
    if any(token in path for token in PLACEHOLDER_TOKENS):
        return False
    if path.startswith("#"):
        return False
    return path.startswith(CHECK_PREFIXES)


def extract_references(markdown: str) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if ".venv/bin/python " not in stripped:
            continue
        parts = stripped.split()
        for part in parts[1:]:
            candidate = clean_candidate(part)
            if should_check(candidate):
                refs.append((candidate, "python_command"))
    for match in re.finditer(r"`([^`\n]+)`", markdown):
        content = match.group(1).strip()
        if content.startswith(".venv/bin/python "):
            parts = content.split()
            for part in parts[1:]:
                candidate = clean_candidate(part)
                if should_check(candidate):
                    refs.append((candidate, "python_command"))
        else:
            for token in re.split(r"\s+", content):
                candidate = clean_candidate(token)
                if should_check(candidate):
                    refs.append((candidate, "inline_code"))
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", markdown):
        target = clean_candidate(match.group(1).split("#", 1)[0])
        if should_check(target):
            refs.append((target, "markdown_link"))
    return refs


def check_reference(doc_path: Path, rel_ref: str, source_type: str) -> dict[str, object]:
    path = ROOT / rel_ref
    exists = path.exists() or rel_ref in GENERATED_OUTPUTS
    return {
        "document": str(doc_path.relative_to(ROOT)),
        "reference": rel_ref,
        "source_type": source_type,
        "status": "ok" if exists else "missing",
        "is_dir": bool(path.is_dir()) if exists else False,
        "size_bytes": int(path.stat().st_size) if exists and path.is_file() else 0,
    }


def main() -> None:
    ensure_project_dirs()
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for doc_path in DOC_PATHS:
        if not doc_path.exists() or doc_path.stat().st_size == 0:
            continue
        refs = extract_references(doc_path.read_text(encoding="utf-8", errors="ignore"))
        for rel_ref, source_type in refs:
            key = (str(doc_path.relative_to(ROOT)), rel_ref, source_type)
            if key in seen:
                continue
            seen.add(key)
            rows.append(check_reference(doc_path, rel_ref, source_type))
    report_df = pd.DataFrame(rows).sort_values(["status", "document", "reference"]) if rows else pd.DataFrame()
    report_df.to_csv(TABLES_DIR / "markdown_reference_check.csv", index=False, encoding="utf-8-sig")
    summary = {
        "n_documents": int(sum(1 for path in DOC_PATHS if path.exists())),
        "n_references": int(len(report_df)),
        "n_missing": int((report_df["status"] == "missing").sum()) if len(report_df) else 0,
        "status": "ok" if not len(report_df) or not (report_df["status"] == "missing").any() else "failed",
    }
    (TABLES_DIR / "markdown_reference_check_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    missing = report_df[report_df["status"] == "missing"].copy() if len(report_df) else pd.DataFrame()
    show = report_df[["document", "reference", "source_type", "status"]].copy() if len(report_df) else pd.DataFrame()
    lines = [
        "# Markdown 本地引用检查",
        "",
        "本报告检查 `README.md` 和 `docs/*.md` 中明确写出的本地文件、目录和脚本引用是否存在。URL、通配符和带尖括号的占位符不会纳入检查。",
        "",
        "## 摘要",
        "",
        f"- 状态：`{summary['status']}`",
        f"- 文档数：{summary['n_documents']}",
        f"- 本地引用数：{summary['n_references']}",
        f"- 缺失引用数：{summary['n_missing']}",
        "",
    ]
    if len(missing):
        lines.extend(["## 缺失引用", "", md_table(missing[["document", "reference", "source_type", "status"]]), ""])
    lines.extend(
        [
            "## 检查明细",
            "",
            md_table(show),
            "",
            "机器可读结果见 `tables/markdown_reference_check.csv` 和 `tables/markdown_reference_check_summary.json`。",
            "",
        ]
    )
    (DOCS_DIR / "markdown_reference_check_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote markdown reference check outputs: {summary['status']}")
    if summary["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

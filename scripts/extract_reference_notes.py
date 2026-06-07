#!/usr/bin/env python
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pypdf import PdfReader

from soilmodel.paths import DOCS_DIR, ensure_project_dirs


# 原始文献与方案文档存放在 docs/source_materials/，仅供方法对照，可按需从交付包移除。
MATERIALS_DIR = ROOT / "docs" / "source_materials"
PDF_FILES = ["预测main.pdf", "预测1-s2.0-S0045653520311012-main.pdf"]


def find_docx_file(explicit_path: str | None = None) -> Path:
    if explicit_path:
        path = ROOT / explicit_path
        if not path.exists():
            raise SystemExit(f"Missing DOCX file: {explicit_path}")
        return path
    candidates = sorted(path for path in MATERIALS_DIR.glob("*.docx") if not path.name.startswith("~$"))
    if not candidates:
        raise SystemExit(
            "Missing planning DOCX file. Put one .docx file in docs/source_materials/ or pass --docx."
        )
    return candidates[0]


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_docx_text(path: Path) -> list[str]:
    import html

    with ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    paragraphs: list[str] = []
    for para in re.findall(r"<w:p[\s\S]*?</w:p>", xml):
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", para, flags=re.S)
        if texts:
            paragraphs.append(html.unescape("".join(texts)))
    return paragraphs


def find_snippets(text: str, patterns: list[str], window: int = 420) -> dict[str, str]:
    lower = text.lower()
    snippets: dict[str, str] = {}
    for pattern in patterns:
        idx = lower.find(pattern.lower())
        if idx >= 0:
            snippets[pattern] = compact(text[max(0, idx - window) : idx + window])
    return snippets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract concise notes from local reference papers and planning document.")
    parser.add_argument("--docx", default=None, help="Optional planning DOCX path, relative to project root.")
    parser.add_argument("--output", default="docs/source_materials_summary.md", help="Output Markdown path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    lines: list[str] = [
        "# 本地材料摘要",
        "",
        "本文件记录用于设计复现实验的本地材料要点。",
        "",
    ]

    patterns = [
        "parallel ensemble artificial intelligence",
        "TreeExplainer",
        "10-fold cross-validation",
        "weighted ensemble",
        "scenario simulation",
        "optimistic scenario",
        "default scenario",
        "spatiotemporal",
    ]

    for name in PDF_FILES:
        path = MATERIALS_DIR / name
        if not path.exists():
            print(f"跳过缺失文献：{path.relative_to(ROOT)}（原文献仅供方法对照，可不随交付包提供）")
            continue
        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        first_page = compact(reader.pages[0].extract_text() or "")
        title = first_page[:220]
        lines.extend([f"## {name}", "", f"- 页数：{len(reader.pages)}", f"- 首页文本摘录：{title}", ""])
        snippets = find_snippets(text, patterns)
        for key, snippet in snippets.items():
            lines.extend([f"### 关键词：{key}", "", snippet, ""])

    docx_path = find_docx_file(args.docx)
    paragraphs = extract_docx_text(docx_path)
    wanted = [
        p
        for p in paragraphs
        if any(k in p for k in ["研究目标", "模型选择", "模型验证", "可解释性", "未来情景", "论文撰写注意事项"])
    ][:30]
    lines.extend(["## 方案文档要点", ""])
    lines.extend([f"- {compact(p)}" for p in wanted])

    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

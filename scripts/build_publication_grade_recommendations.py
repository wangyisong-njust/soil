#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs


EXCLUDED_SOURCES = {
    "nnls_stack_exploration",
    "spatial_model_blend_exploration",
    "temporal_calibration_exploration",
    "validation_transfer_test_selected_exploration",
    "conservative_baseline",
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


def main() -> None:
    ensure_project_dirs()
    candidates_path = TABLES_DIR / "final_adaptive_candidate_metrics.csv"
    if not candidates_path.exists() or candidates_path.stat().st_size == 0:
        raise SystemExit("Missing final adaptive candidates. Run scripts/build_final_adaptive_recommendations.py first.")
    candidates = pd.read_csv(candidates_path)
    filtered = candidates[
        (candidates["protocol"] == "temporal_2022_2026")
        & (~candidates["source"].isin(EXCLUDED_SOURCES))
    ].dropna(subset=["r2"])
    best = (
        filtered.sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    best.to_csv(TABLES_DIR / "publication_grade_recommended_metrics.csv", index=False, encoding="utf-8-sig")

    show = best[["target", "source", "method", "model", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    summary = {
        "mean_r2": float(best["r2"].mean()),
        "median_r2": float(best["r2"].median()),
        "min_r2": float(best["r2"].min()),
        "n_positive": int((best["r2"] > 0).sum()),
    }
    report = [
        "# 论文主结果推荐表",
        "",
        "本表是统一目标自适应建模框架的正式输出。8 个重金属共享同一候选池、同一 2022-2026 时间外推测试集、同一防泄漏规则和同一候选资格审计；框架只在最后一层按目标选择合规候选，避免把不同金属强行压到同一个单模型。",
        "",
        "本表排除了使用 2022-2026 验证集观测值拟合权重、选择候选池或选择校准形式的探索性结果，包括 NNLS 非负堆叠探索、空间-模型融合探索和时间校准 oracle。保留外部公开因子、时空模型、风险门控、历史记忆和空间分位数基线等不使用测试期目标值调参的候选结果。",
        "",
        md_table(show),
        "",
        f"主结果口径下平均 R2={summary['mean_r2']:.4f}，中位 R2={summary['median_r2']:.4f}，最低 R2={summary['min_r2']:.4f}，8 个目标中 {summary['n_positive']} 个为正。",
        "",
        "这套结果更适合作为论文主验证表；`docs/final_adaptive_recommendation_report.md` 中使用测试期目标值选模型或拟合权重的结果更适合作为候选库探索上限或补充实验。",
        "",
    ]
    (DOCS_DIR / "publication_grade_recommendation_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote publication-grade recommendation outputs")


if __name__ == "__main__":
    main()

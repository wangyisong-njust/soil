#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs


def read_json(rel_path: str) -> dict[str, object]:
    path = ROOT / rel_path
    if path.exists() and path.stat().st_size:
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def read_csv(rel_path: str) -> pd.DataFrame:
    path = ROOT / rel_path
    if path.exists() and path.stat().st_size:
        return pd.read_csv(path)
    return pd.DataFrame()


def exists(rel_path: str) -> str:
    path = ROOT / rel_path
    return "ok" if path.exists() and path.stat().st_size else "missing"


def f4(value: object) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.4f}"


def md_table(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "_无记录。_"
    df = pd.DataFrame(rows).astype(str)
    lines = [
        "| " + " | ".join(df.columns) + " |",
        "| " + " | ".join(["---"] * len(df.columns)) + " |",
    ]
    for row in df.values.tolist():
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> None:
    ensure_project_dirs()
    delivery = read_json("tables/delivery_audit_summary.json")
    readiness = read_json("tables/submission_readiness_audit_summary.json")
    leakage = read_json("tables/leakage_publication_audit_summary.json")
    markdown = read_json("tables/markdown_reference_check_summary.json")
    text_summary = read_json("tables/manuscript_text_snippets_summary.json")
    eligibility = read_json("tables/candidate_eligibility_summary.json")
    performance = read_csv("tables/publication_grade_recommended_metrics.csv")

    if not performance.empty:
        r2 = pd.to_numeric(performance["r2"], errors="coerce")
        best = performance.loc[r2.idxmax()]
        weakest = performance.loc[r2.idxmin()]
        metrics_summary = (
            f"8 个目标均有论文主结果；平均 R2={f4(r2.mean())}，中位 R2={f4(r2.median())}，"
            f"最高为 `{best['target']}` ({f4(best['r2'])})，最低为 `{weakest['target']}` ({f4(weakest['r2'])})。"
        )
    else:
        metrics_summary = "当前未读取到论文主结果表。"

    primary_entries = [
        {
            "用途": "一键运行和参数替换",
            "文件": "run_project.py",
            "状态": exists("run_project.py"),
            "说明": "顶部参数区可替换数据、目标列、特征列、验证年份和未来年份。",
        },
        {
            "用途": "复现步骤",
            "文件": "docs/复现.md",
            "状态": exists("docs/复现.md"),
            "说明": "环境安装、分步命令、预期输出和外部因子说明。",
        },
        {
            "用途": "完整技术报告",
            "文件": "docs/report.md",
            "状态": exists("docs/report.md"),
            "说明": "方法、结果、消融、未来预测、风险和审计汇总。",
        },
    ]

    paper_entries = [
        {
            "用途": "论文主性能表",
            "文件": "tables/publication_grade_recommended_metrics.csv",
            "状态": exists("tables/publication_grade_recommended_metrics.csv"),
            "说明": "R2、RMSE、MAE、MAPE 主验证表。",
        },
        {
            "用途": "模型卡",
            "文件": "tables/publication_model_cards.csv",
            "状态": exists("tables/publication_model_cards.csv"),
            "说明": "每个目标的最终模型、未来预测实现和复现说明。",
        },
        {
            "用途": "论文表格",
            "文件": "tables/manuscript_table2_publication_model_performance.csv",
            "状态": exists("tables/manuscript_table2_publication_model_performance.csv"),
            "说明": "变量表、模型性能、未来不确定性、风险概率和因子贡献。",
        },
        {
            "用途": "论文写作辅助文本",
            "文件": "tables/manuscript_text_snippets_summary.json",
            "状态": exists("tables/manuscript_text_snippets_summary.json"),
            "说明": "Methods、Results、Limitations 和 reviewer notes 写作素材。",
        },
        {
            "用途": "论文总览图",
            "文件": "figures/manuscript_summary/manuscript_results_overview.png",
            "状态": exists("figures/manuscript_summary/manuscript_results_overview.png"),
            "说明": "R2、不确定性、风险概率和 SHAP 因子组 2x2 总览。",
        },
        {
            "用途": "候选资格审计",
            "文件": "tables/candidate_eligibility_audit.csv",
            "状态": exists("tables/candidate_eligibility_audit.csv"),
            "说明": "解释高 R2 探索上限为什么不能替代主结果。",
        },
        {
            "用途": "M0-M6 消融表",
            "文件": "tables/framework_module_ablation_summary.csv",
            "状态": exists("tables/framework_module_ablation_summary.csv"),
            "说明": "按模块汇总平均 R2、增量和正 R2 目标数。",
        },
        {
            "用途": "空间背景残差修复结果",
            "文件": "tables/spatial_baseline_residual_fixed_best_metrics.csv",
            "状态": exists("tables/spatial_baseline_residual_fixed_best_metrics.csv"),
            "说明": "M3 模块的防泄漏背景场残差模型结果。",
        },
    ]

    result_entries = [
        {
            "用途": "未来点预测",
            "文件": "results/future_predictions_publication_aligned_2027_2035.csv",
            "状态": exists("results/future_predictions_publication_aligned_2027_2035.csv"),
            "说明": "2027-2035、8 目标；exact 对齐与 documented fallback 状态见模型卡。",
        },
        {
            "用途": "未来预测区间",
            "文件": "results/future_predictions_publication_aligned_2027_2035_intervals.csv",
            "状态": exists("results/future_predictions_publication_aligned_2027_2035_intervals.csv"),
            "说明": "经验残差 90% 区间和相对宽度。",
        },
        {
            "用途": "未来超阈值概率",
            "文件": "results/future_exceedance_probability_2027_2035.csv",
            "状态": exists("results/future_exceedance_probability_2027_2035.csv"),
            "说明": "训练期 q90/q95 阈值下的未来风险概率。",
        },
        {
            "用途": "观测-预测图",
            "文件": "figures/recommended_predictions/publication_grade_observed_predicted_grid.png",
            "状态": exists("figures/recommended_predictions/publication_grade_observed_predicted_grid.png"),
            "说明": "8 个重金属论文主结果散点图。",
        },
        {
            "用途": "特征重要性图",
            "文件": "figures/feature_importance_summary/shap_group_contribution_heatmap.png",
            "状态": exists("figures/feature_importance_summary/shap_group_contribution_heatmap.png"),
            "说明": "SHAP 因子组贡献热图。",
        },
        {
            "用途": "消融结果图",
            "文件": "figures/validation_strategy/framework_module_ablation_mean_r2.png",
            "状态": exists("figures/validation_strategy/framework_module_ablation_mean_r2.png"),
            "说明": "M0-M6 平均 R2 对比图。",
        },
    ]

    lines = [
        "# 项目交付导航",
        "",
        "本文件是当前土壤重金属时空预测项目的顶层入口。它不替代完整报告和复现说明，只用于快速定位最重要的代码、结果、图表、论文材料和审计文件。",
        "",
        "## 当前状态",
        "",
        f"- 论文主结果：{metrics_summary}",
        f"- 未来预测：{delivery.get('future_year_min', 'NA')}-{delivery.get('future_year_max', 'NA')}，exact 对齐目标数 {delivery.get('future_exact_publication_targets', 'NA')}/8。",
        f"- 投稿准备度审计：`{readiness.get('status', 'unknown')}`，通过 {readiness.get('n_ok', 'NA')}/{readiness.get('n_checks', 'NA')}，失败 {readiness.get('n_failed', 'NA')}。",
        f"- 防泄漏审计：`{leakage.get('status', 'unknown')}`，失败 {leakage.get('n_failed', 'NA')}。",
        f"- Markdown 引用检查：`{markdown.get('status', 'unknown')}`，缺失 {markdown.get('n_missing', 'NA')}。",
        f"- 主结果等于合规候选最优：{eligibility.get('n_publication_equals_best_eligible', 'NA')}/8。",
        f"- 写作辅助摘要：`tables/manuscript_text_snippets_summary.json`。",
        "",
        "## 先看这 5 个文件",
        "",
        md_table(primary_entries),
        "",
        "## 论文写作和投稿材料",
        "",
        md_table(paper_entries),
        "",
        "## 关键结果和图件",
        "",
        md_table(result_entries),
        "",
        "## 推荐使用顺序",
        "",
        "1. 修改或确认 `run_project.py` 顶部参数区。",
        "2. 按 `docs/复现.md` 安装环境并运行一键命令。",
        "3. 运行一键验收命令，确认命令返回成功：",
        "",
        "```bash",
        ".venv/bin/python scripts/verify_submission_package.py --allow-warnings",
        "```",
        "",
        "4. 运行复现快照命令，记录当前输入和输出版本：",
        "",
        "```bash",
        ".venv/bin/python scripts/build_reproducibility_snapshot.py",
        "```",
        "",
        "5. 查看 `tables/submission_readiness_audit.csv`，确认没有 `failed`；`warning` 项需要在论文限制或方法说明中披露。",
        "6. 用 `docs/report.md` 作为完整技术报告入口。",
        "7. 用 `tables/manuscript_table*.csv`、`tables/manuscript_text_snippets_summary.json` 和 `figures/manuscript_summary/manuscript_results_overview.png` 整理论文材料。",
        "",
        "## 写作口径提醒",
        "",
        "- `tables/publication_grade_recommended_metrics.csv` 是论文主验证表。",
        "- `tables/candidate_eligibility_audit.csv` 说明哪些高 R2 结果属于探索上限。",
        "- `results/future_predictions_publication_aligned_2027_2035.csv` 是与论文主模型对齐的未来预测文件。",
        "- 若讨论低 R2 目标，应同时引用逐年误差、分布漂移、不确定性和风险概率结果。",
        "",
    ]

    legacy_docs = ROOT / "archive" / "legacy_docs"
    legacy_docs.mkdir(parents=True, exist_ok=True)
    out = legacy_docs / "project_delivery_guide.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "status": "ok",
        "output": "archive/legacy_docs/project_delivery_guide.md",
        "primary_entries": len(primary_entries),
        "paper_entries": len(paper_entries),
        "result_entries": len(result_entries),
        "submission_readiness_status": readiness.get("status", "unknown"),
    }
    (TABLES_DIR / "project_delivery_guide_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Wrote project delivery guide")


if __name__ == "__main__":
    main()

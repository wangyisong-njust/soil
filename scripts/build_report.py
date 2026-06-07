#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import re

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


KEEP_DOCS = {"docs/report.md", "docs/reproduction.md"}

# 交付版主报告只保留最终有效创新方法、主结果与必要可信度骨架；
# 下列章节属探索/敏感性/诊断/被概括的中间过程，整段删除（底层表格、图件、归档仍保留可追溯）。
DROP_SECTIONS = {
    # 元章节（对已归档文档集合的审计）
    "## Markdown 本地引用检查",
    "## 交付文件清单与复现审计",
    # 探索 / 未提升 / 被 M0-M6 概括的方法
    "## 随机划分对照",
    "## 时空创新模型对照",
    "## ARIMA/LSTM 时间序列对照",
    "## 目标分布变换与稳健损失模型",
    "## 空间分块交叉验证",
    "## 训练期分布规则空间分位数基线",
    "## 最终目标自适应推荐",
    "## 验证期选型论文结果",
    "## 逐年验证稳定选型结果",
    "## 验证期稳健融合敏感性分析",
    "## 验证期迁移校正模型",
    "## 空间分位数验证期选择基线",
    "## 空间分位数逐年稳健验证基线",
    "## 预设近三年中位数基线",
    "## 线性堆叠同集上限诊断",
    "## 分层结果对比",
    "## 完整模型比较",
    "## 集成权重",
    # 诊断 / 敏感性 / 被主结果替代的中间过程
    "## 极端样本误差诊断",
    "## 逐年误差与分布漂移诊断",
    "## 预测不确定性区间",
    "## 高污染风险预警",
    "## 清洗策略对照",
    "## 三阶段时间块验证",
    "## 训练拟合度诊断",
    "## 当前结果可视化摘要",
    "## 投稿准备度审计",
}

# 匹配 "<前缀>见 ` 引用 `、` 引用 `…" 或 "<前缀>：` 引用 `…" 形式的引用子句
_REF_CLAUSE = re.compile(r"([一-龥A-Za-z0-9（）]{1,40}?[见：])\s*(`[^`]*`(?:[、，和\s]*`[^`]*`)*)")


def _is_archived_doc(ref: str) -> bool:
    inner = ref.strip("`").strip()
    return inner.startswith("docs/") and inner.endswith(".md") and inner not in KEEP_DOCS


def _rewrite_ref_clause(match: "re.Match[str]") -> str:
    prefix = match.group(1)
    refs = re.findall(r"`[^`]*`", match.group(2))
    survivors = [ref for ref in refs if not _is_archived_doc(ref)]
    if not survivors:
        return ""  # 整个引用子句只指向已归档文档，删除
    sep = " " if prefix.endswith("见") else ""
    return prefix + sep + "、".join(survivors)


def strip_archived_doc_links(text: str) -> str:
    """让交付版主报告自包含：去掉指向 docs/ 下已归档明细报告的引用，保留 tables/figures/results 引用。

    明细报告在交付前已收束到 archive/dev_reports/，正文只保留主报告与复现说明两份文档，
    其余分析的可追溯入口改为指向实际产出的表格、图件和结果文件。
    """
    text = _REF_CLAUSE.sub(_rewrite_ref_clause, text)
    # 清理删除子句后残留的标点
    text = re.sub(r"[、，；]\s*(?=[；。，、])", "", text)   # 相邻分隔符合并
    text = re.sub(r"^[\s，、；和]+", "", text)             # 行首悬挂连接词
    text = re.sub(r"[，、和；]+\s*$", "", text)            # 行尾悬挂连接词（保留句号）
    text = re.sub(r"。\s*。", "。", text)
    text = re.sub(r" {2,}", " ", text)
    stripped = text.strip()
    if stripped in {"", "。", "；", "，", "、", "-", "- "}:
        return ""
    # 删除子句后只剩孤立短前缀（如 "R2 。"）的整行
    if re.fullmatch(r"[A-Za-z0-9]{1,8}\s*[。；]?", stripped):
        return ""
    return text.rstrip()

from soilmodel.config import load_config
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, TABLES_DIR, ensure_project_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Markdown report from current experiment outputs.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--output", default="docs/report.md", help="Output report path.")
    return parser.parse_args()


def md_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if max_rows:
        df = df.head(max_rows)
    if df.empty:
        return "_无记录。_"
    text_df = df.astype(str)
    headers = list(text_df.columns)
    rows = text_df.values.tolist()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def fmt_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["r2", "r2_log1p", "rmse", "mae", "mape"]:
        if col in out:
            out[col] = out[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    return out


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    metrics_path = TABLES_DIR / "model_metrics.csv"
    if not metrics_path.exists():
        raise SystemExit("Missing tables/model_metrics.csv. Run scripts/run_experiment.py first.")

    metrics = pd.read_csv(metrics_path)
    profile = json.loads((TABLES_DIR / "data_profile.json").read_text(encoding="utf-8"))
    cleaning_report_path = TABLES_DIR / "data_cleaning_report.json"
    cleaning_report = (
        json.loads(cleaning_report_path.read_text(encoding="utf-8")) if cleaning_report_path.exists() else {}
    )
    input_validation_path = TABLES_DIR / "input_validation_report.json"
    input_validation = (
        json.loads(input_validation_path.read_text(encoding="utf-8"))
        if input_validation_path.exists() and input_validation_path.stat().st_size
        else {}
    )
    weights_path = TABLES_DIR / "ensemble_weights.csv"
    weights = pd.read_csv(weights_path) if weights_path.exists() and weights_path.stat().st_size else pd.DataFrame()
    shap_path = TABLES_DIR / "shap_importance.csv"
    shap_df = pd.read_csv(shap_path) if shap_path.exists() and shap_path.stat().st_size else pd.DataFrame()
    importance_path = TABLES_DIR / "feature_importance.csv"
    imp_df = pd.read_csv(importance_path) if importance_path.exists() and importance_path.stat().st_size else pd.DataFrame()
    feature_group_summary_path = TABLES_DIR / "feature_importance_group_summary.csv"
    feature_group_summary_df = (
        pd.read_csv(feature_group_summary_path)
        if feature_group_summary_path.exists() and feature_group_summary_path.stat().st_size
        else pd.DataFrame()
    )
    fit_path = TABLES_DIR / "training_fit_metrics.csv"
    fit_df = pd.read_csv(fit_path) if fit_path.exists() and fit_path.stat().st_size else pd.DataFrame()
    period_path = TABLES_DIR / "period_block_best_metrics.csv"
    period_df = pd.read_csv(period_path) if period_path.exists() and period_path.stat().st_size else pd.DataFrame()
    innovation_path = TABLES_DIR / "innovation_best_metrics.csv"
    innovation_df = pd.read_csv(innovation_path) if innovation_path.exists() and innovation_path.stat().st_size else pd.DataFrame()
    latent_path = TABLES_DIR / "multitask_latent_best_metrics.csv"
    latent_df = pd.read_csv(latent_path) if latent_path.exists() and latent_path.stat().st_size else pd.DataFrame()
    temporal_sequence_path = TABLES_DIR / "temporal_sequence_best_metrics.csv"
    temporal_sequence_df = (
        pd.read_csv(temporal_sequence_path)
        if temporal_sequence_path.exists() and temporal_sequence_path.stat().st_size
        else pd.DataFrame()
    )
    distributional_robust_path = TABLES_DIR / "distributional_robust_best_metrics.csv"
    distributional_robust_df = (
        pd.read_csv(distributional_robust_path)
        if distributional_robust_path.exists() and distributional_robust_path.stat().st_size
        else pd.DataFrame()
    )
    spatial_block_cv_path = TABLES_DIR / "spatial_block_cv_best_metrics.csv"
    spatial_block_cv_df = (
        pd.read_csv(spatial_block_cv_path)
        if spatial_block_cv_path.exists() and spatial_block_cv_path.stat().st_size
        else pd.DataFrame()
    )
    random_fivefold_path = TABLES_DIR / "random_fivefold_cv_best_metrics.csv"
    random_fivefold_df = (
        pd.read_csv(random_fivefold_path)
        if random_fivefold_path.exists() and random_fivefold_path.stat().st_size
        else pd.DataFrame()
    )
    validation_strategy_path = TABLES_DIR / "validation_strategy_summary.csv"
    validation_strategy_df = (
        pd.read_csv(validation_strategy_path)
        if validation_strategy_path.exists() and validation_strategy_path.stat().st_size
        else pd.DataFrame()
    )
    unified_vs_framework_path = TABLES_DIR / "unified_vs_framework_future.csv"
    unified_vs_framework_df = (
        pd.read_csv(unified_vs_framework_path)
        if unified_vs_framework_path.exists() and unified_vs_framework_path.stat().st_size
        else pd.DataFrame()
    )
    ablation_summary_path = TABLES_DIR / "framework_module_ablation_summary.csv"
    ablation_summary_df = (
        pd.read_csv(ablation_summary_path)
        if ablation_summary_path.exists() and ablation_summary_path.stat().st_size
        else pd.DataFrame()
    )
    distribution_guided_path = TABLES_DIR / "distribution_guided_spatial_quantile_metrics.csv"
    distribution_guided_df = (
        pd.read_csv(distribution_guided_path)
        if distribution_guided_path.exists() and distribution_guided_path.stat().st_size
        else pd.DataFrame()
    )
    final_adaptive_path = TABLES_DIR / "final_adaptive_recommended_metrics.csv"
    final_adaptive_df = (
        pd.read_csv(final_adaptive_path)
        if final_adaptive_path.exists() and final_adaptive_path.stat().st_size
        else pd.DataFrame()
    )
    publication_grade_path = TABLES_DIR / "publication_grade_recommended_metrics.csv"
    publication_grade_df = (
        pd.read_csv(publication_grade_path)
        if publication_grade_path.exists() and publication_grade_path.stat().st_size
        else pd.DataFrame()
    )
    candidate_eligibility_path = TABLES_DIR / "candidate_eligibility_summary.csv"
    candidate_eligibility_df = (
        pd.read_csv(candidate_eligibility_path)
        if candidate_eligibility_path.exists() and candidate_eligibility_path.stat().st_size
        else pd.DataFrame()
    )
    candidate_eligibility_summary_path = TABLES_DIR / "candidate_eligibility_summary.json"
    candidate_eligibility_summary = (
        json.loads(candidate_eligibility_summary_path.read_text(encoding="utf-8"))
        if candidate_eligibility_summary_path.exists() and candidate_eligibility_summary_path.stat().st_size
        else {}
    )
    publication_model_cards_path = TABLES_DIR / "publication_model_cards.csv"
    publication_model_cards_df = (
        pd.read_csv(publication_model_cards_path)
        if publication_model_cards_path.exists() and publication_model_cards_path.stat().st_size
        else pd.DataFrame()
    )
    manuscript_performance_path = TABLES_DIR / "manuscript_table2_publication_model_performance.csv"
    manuscript_performance_df = (
        pd.read_csv(manuscript_performance_path)
        if manuscript_performance_path.exists() and manuscript_performance_path.stat().st_size
        else pd.DataFrame()
    )
    manuscript_risk_path = TABLES_DIR / "manuscript_table4_future_exceedance_risk.csv"
    manuscript_risk_df = (
        pd.read_csv(manuscript_risk_path)
        if manuscript_risk_path.exists() and manuscript_risk_path.stat().st_size
        else pd.DataFrame()
    )
    manuscript_feature_group_path = TABLES_DIR / "manuscript_table5_feature_group_importance.csv"
    manuscript_feature_group_df = (
        pd.read_csv(manuscript_feature_group_path)
        if manuscript_feature_group_path.exists() and manuscript_feature_group_path.stat().st_size
        else pd.DataFrame()
    )
    manuscript_text_summary_path = TABLES_DIR / "manuscript_text_snippets_summary.json"
    manuscript_text_summary = (
        json.loads(manuscript_text_summary_path.read_text(encoding="utf-8"))
        if manuscript_text_summary_path.exists() and manuscript_text_summary_path.stat().st_size
        else {}
    )
    manuscript_summary_figure_path = FIGURES_DIR / "manuscript_summary" / "manuscript_results_overview.png"
    submission_readiness_path = TABLES_DIR / "submission_readiness_audit.csv"
    submission_readiness_df = (
        pd.read_csv(submission_readiness_path)
        if submission_readiness_path.exists() and submission_readiness_path.stat().st_size
        else pd.DataFrame()
    )
    submission_readiness_summary_path = TABLES_DIR / "submission_readiness_audit_summary.json"
    submission_readiness_summary = (
        json.loads(submission_readiness_summary_path.read_text(encoding="utf-8"))
        if submission_readiness_summary_path.exists() and submission_readiness_summary_path.stat().st_size
        else {}
    )
    linear_stack_upper_path = TABLES_DIR / "linear_stack_upper_bound_metrics.csv"
    linear_stack_upper_df = (
        pd.read_csv(linear_stack_upper_path)
        if linear_stack_upper_path.exists() and linear_stack_upper_path.stat().st_size
        else pd.DataFrame()
    )
    tiered_summary_path = TABLES_DIR / "tiered_result_summary.csv"
    tiered_summary_df = (
        pd.read_csv(tiered_summary_path)
        if tiered_summary_path.exists() and tiered_summary_path.stat().st_size
        else pd.DataFrame()
    )
    validation_transfer_path = TABLES_DIR / "validation_transfer_calibration_best_metrics.csv"
    validation_transfer_df = (
        pd.read_csv(validation_transfer_path)
        if validation_transfer_path.exists() and validation_transfer_path.stat().st_size
        else pd.DataFrame()
    )
    validation_transfer_upper_path = TABLES_DIR / "validation_transfer_calibration_test_selected_best_metrics.csv"
    validation_transfer_upper_df = (
        pd.read_csv(validation_transfer_upper_path)
        if validation_transfer_upper_path.exists() and validation_transfer_upper_path.stat().st_size
        else pd.DataFrame()
    )
    spatial_quantile_validated_path = TABLES_DIR / "spatial_quantile_validated_best_metrics.csv"
    spatial_quantile_validated_df = (
        pd.read_csv(spatial_quantile_validated_path)
        if spatial_quantile_validated_path.exists() and spatial_quantile_validated_path.stat().st_size
        else pd.DataFrame()
    )
    spatial_quantile_yearwise_path = TABLES_DIR / "spatial_quantile_yearwise_validated_best_metrics.csv"
    spatial_quantile_yearwise_df = (
        pd.read_csv(spatial_quantile_yearwise_path)
        if spatial_quantile_yearwise_path.exists() and spatial_quantile_yearwise_path.stat().st_size
        else pd.DataFrame()
    )
    predefined_recent_path = TABLES_DIR / "predefined_recent_median_baseline_metrics.csv"
    predefined_recent_df = (
        pd.read_csv(predefined_recent_path)
        if predefined_recent_path.exists() and predefined_recent_path.stat().st_size
        else pd.DataFrame()
    )
    validation_selected_publication_path = TABLES_DIR / "validation_selected_publication_metrics.csv"
    validation_selected_publication_df = (
        pd.read_csv(validation_selected_publication_path)
        if validation_selected_publication_path.exists() and validation_selected_publication_path.stat().st_size
        else pd.DataFrame()
    )
    yearwise_validation_selected_path = TABLES_DIR / "yearwise_validation_selected_publication_metrics.csv"
    yearwise_validation_selected_df = (
        pd.read_csv(yearwise_validation_selected_path)
        if yearwise_validation_selected_path.exists() and yearwise_validation_selected_path.stat().st_size
        else pd.DataFrame()
    )
    validation_robust_fusion_path = TABLES_DIR / "validation_robust_fusion_best_metrics.csv"
    validation_robust_fusion_df = (
        pd.read_csv(validation_robust_fusion_path)
        if validation_robust_fusion_path.exists() and validation_robust_fusion_path.stat().st_size
        else pd.DataFrame()
    )
    extreme_error_path = TABLES_DIR / "extreme_error_sensitivity_metrics.csv"
    extreme_error_df = (
        pd.read_csv(extreme_error_path)
        if extreme_error_path.exists() and extreme_error_path.stat().st_size
        else pd.DataFrame()
    )
    influential_error_path = TABLES_DIR / "extreme_error_influential_samples.csv"
    influential_error_df = (
        pd.read_csv(influential_error_path)
        if influential_error_path.exists() and influential_error_path.stat().st_size
        else pd.DataFrame()
    )
    yearwise_error_summary_path = TABLES_DIR / "publication_yearwise_error_summary.csv"
    yearwise_error_summary_df = (
        pd.read_csv(yearwise_error_summary_path)
        if yearwise_error_summary_path.exists() and yearwise_error_summary_path.stat().st_size
        else pd.DataFrame()
    )
    risk_exceedance_path = TABLES_DIR / "risk_exceedance_best_metrics.csv"
    risk_exceedance_df = (
        pd.read_csv(risk_exceedance_path)
        if risk_exceedance_path.exists() and risk_exceedance_path.stat().st_size
        else pd.DataFrame()
    )
    prediction_interval_path = TABLES_DIR / "publication_prediction_interval_metrics.csv"
    prediction_interval_df = (
        pd.read_csv(prediction_interval_path)
        if prediction_interval_path.exists() and prediction_interval_path.stat().st_size
        else pd.DataFrame()
    )
    future_interval_path = TABLES_DIR / "future_prediction_interval_summary.csv"
    future_interval_df = (
        pd.read_csv(future_interval_path)
        if future_interval_path.exists() and future_interval_path.stat().st_size
        else pd.DataFrame()
    )
    future_exceedance_path = TABLES_DIR / "future_exceedance_probability_summary.csv"
    future_exceedance_df = (
        pd.read_csv(future_exceedance_path)
        if future_exceedance_path.exists() and future_exceedance_path.stat().st_size
        else pd.DataFrame()
    )
    future_exceedance_map_path = TABLES_DIR / "future_exceedance_probability_map_summary.csv"
    future_exceedance_map_df = (
        pd.read_csv(future_exceedance_map_path)
        if future_exceedance_map_path.exists() and future_exceedance_map_path.stat().st_size
        else pd.DataFrame()
    )
    publication_aligned_future_path = TABLES_DIR / "publication_aligned_future_prediction_summary.csv"
    publication_aligned_future_df = (
        pd.read_csv(publication_aligned_future_path)
        if publication_aligned_future_path.exists() and publication_aligned_future_path.stat().st_size
        else pd.DataFrame()
    )
    external_path = TABLES_DIR / "external_covariate_best_metrics.csv"
    external_df = pd.read_csv(external_path) if external_path.exists() and external_path.stat().st_size else pd.DataFrame()
    cleaning_best_path = TABLES_DIR / "cleaning_strategy_best_metrics.csv"
    cleaning_best_df = (
        pd.read_csv(cleaning_best_path) if cleaning_best_path.exists() and cleaning_best_path.stat().st_size else pd.DataFrame()
    )
    delivery_summary_path = TABLES_DIR / "delivery_audit_summary.json"
    delivery_summary = (
        json.loads(delivery_summary_path.read_text(encoding="utf-8"))
        if delivery_summary_path.exists() and delivery_summary_path.stat().st_size
        else {}
    )
    delivery_manifest_path = TABLES_DIR / "delivery_artifact_manifest.csv"
    delivery_manifest_df = (
        pd.read_csv(delivery_manifest_path)
        if delivery_manifest_path.exists() and delivery_manifest_path.stat().st_size
        else pd.DataFrame()
    )
    leakage_audit_summary_path = TABLES_DIR / "leakage_publication_audit_summary.json"
    leakage_audit_summary = (
        json.loads(leakage_audit_summary_path.read_text(encoding="utf-8"))
        if leakage_audit_summary_path.exists() and leakage_audit_summary_path.stat().st_size
        else {}
    )
    leakage_audit_path = TABLES_DIR / "leakage_publication_audit.csv"
    leakage_audit_df = (
        pd.read_csv(leakage_audit_path)
        if leakage_audit_path.exists() and leakage_audit_path.stat().st_size
        else pd.DataFrame()
    )
    markdown_check_summary_path = TABLES_DIR / "markdown_reference_check_summary.json"
    markdown_check_summary = (
        json.loads(markdown_check_summary_path.read_text(encoding="utf-8"))
        if markdown_check_summary_path.exists() and markdown_check_summary_path.stat().st_size
        else {}
    )

    primary = config["primary_protocol"]
    ok = metrics[(metrics["status"] == "ok") & (metrics["split"] == "test")].copy()
    best_primary = (
        ok[ok["protocol"] == primary]
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    best_random = (
        ok[ok["protocol"] == "random"]
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )

    lines: list[str] = [
        "# 土壤重金属时空预测实验报告",
        "",
        "本报告为交付版主报告，自包含实验设置、数据处理、验证设计与主要结果；复现步骤见 `docs/reproduction.md`。",
        "",
        "## 任务设置",
        "",
        (
            f"数据集包含 {profile['n_rows']} 条样本、{profile['n_columns']} 列，年份范围为 "
            f"{profile['year_min']}-{profile['year_max']}。经纬度保留 6 位小数后共有 "
            f"{profile['n_unique_points_rounded6']} 个独立位置，其中 {profile['n_repeated_points_rounded6']} "
            f"个位置存在重复观测。转换阶段识别并纠正了 {profile.get('n_coordinate_swapped', 0)} "
            f"组疑似经纬度写反的坐标。"
        ),
        "",
        "8 个目标变量分别建模：`A`、`B`、`C`、`D`、`E`、`F`、`G`、`H`。预测因子包括经纬度、年份、`a-q` 驱动因子、简单时空交互项，以及只由训练期观测计算得到的目标变量空间滞后特征。同一行里的其他重金属目标不作为普通预测因子，避免未来预测场景中不可获得这些变量而造成验证不独立。",
        "",
        "## 数据清洗",
        "",
        (
            f"当前主流程采用 `{cleaning_report.get('strategy', profile.get('data_cleaning_strategy', 'basic'))}` 清洗策略。"
            f"输入样本 {cleaning_report.get('n_input', profile['n_rows'])} 条，输出样本 {profile['n_rows']} 条。"
            f"合并同坐标同年份重复组 {cleaning_report.get('n_duplicate_groups_aggregated', 0)} 组，"
            f"用中位数填补驱动因子缺失 {sum(cleaning_report.get('feature_missing_imputed_by_median', {}).values()) if cleaning_report else 0} 个，"
            f"对 {len(cleaning_report.get('driver_winsorized', {})) if cleaning_report else 0} 个驱动因子做 0.5%/99.5% 温和截尾。"
            f"主流程未剔除目标变量极端值。"
        ),
        "",
        "另比较了 `basic`、`quality`、`quality_target_mild`、`quality_target_strict` 四类清洗策略。目标变量极端值剔除会明显改变样本构成，因此仅作为敏感性分析，不作为默认主流程。",
        "",
        "## 参考文献对应设计",
        "",
        "- 2023 年 Journal of Hazardous Materials 论文采用并行集成 AI、TreeSHAP 解释和空间显式未来预测。",
        "- 2020 年 Chemosphere 论文强调时空变化、未来情景模拟和预警分析。",
        "- 本项目据此采用多模型比较、加权集成、SHAP/重要性分析，并把时间外推留出作为主验证方式。",
        "",
        "## 验证设计",
        "",
        f"主验证协议为 `{primary}`。{config['temporal_test_start_year']} 年以前样本用于训练，"
        f"{config['temporal_test_start_year']} 年及之后样本作为未来时期测试集。另给出随机 80/20 "
        "划分作为辅助对照。集成模型权重只根据训练期内部验证集估计；测试期样本的空间滞后特征只引用训练期目标值。",
        "",
        "该设置比纯随机划分更严格，更适合论文或公开代码场景，因为未来时期测试样本没有参与拟合、权重估计或集成选择。",
        "",
        "## 输入配置检查",
        "",
    ]
    if len(validation_strategy_df):
        validation_show = validation_strategy_df[
            [
                "validation",
                "role",
                "n_targets",
                "mean_r2",
                "median_r2",
                "min_r2",
                "max_r2",
                "positive_r2_targets",
                "source_file",
            ]
        ].copy()
        for col in ["mean_r2", "median_r2", "min_r2", "max_r2"]:
            validation_show[col] = validation_show[col].map(lambda value: "" if pd.isna(value) else f"{float(value):.4f}")
        validation_lines = [
            "## 三类验证策略",
            "",
            "本报告的主线收束为一个统一目标自适应建模框架：8 个重金属共享同一数据清洗、特征生成、候选模型池、验证划分、防泄漏规则和结果审计；差异只体现在每个目标通过统一规则自动选择最合适的候选模块。该设计不是为每个金属临时指定模型，而是在同一框架内承认不同金属的空间背景、时间漂移和极端值结构不同。",
            "",
            "为避免不同验证之间因候选池规模不同而不可比，三类验证统一使用同一候选池：完整模型注册表（RF/XGBoost/LightGBM/ExtraTrees/HistGBR/CatBoost/NGBoost/PLSR/ElasticNet 及其原始尺度变体）× {base, base+外部协变量} 两套特征集，逐目标在各自的留出折/留出块/留出年内选优。三类验证只在“如何划分训练与测试”上不同，特征工程、目标空间滞后泄漏控制和候选集合完全一致。",
            "",
            "- **随机五折交叉验证**：评价同分布插值能力。",
            "- **空间分块交叉验证**：按经纬度 KMeans 分块逐块留出，评价跨区域空间外推能力。",
            "- **未来年份独立验证（纯回归池）**：2000-2021 训练、2022 年起独立测试，与上面两类同池，评价时间外推能力。",
            "- **未来年份·统一目标自适应框架**：在纯回归池之外再引入地形/地质外部因子、空间分位数背景、局部污染记忆、风险门控和历史因果记忆等候选模块，是论文主结果口径。",
            "",
            md_table(validation_show),
            "",
            "表中逐目标“最优”是基于该验证自身留出折选出的，属选择偏倚上界；`tables/unified_validation_metrics.csv` 同时给出候选池内全部模型，可据此读保守区间。结果说明，空间分块外推和未来年份外推显著难于随机插值，这是数据层面的客观限制（多数位置单次观测、目标重尾、2022 年后测试样本仅 34 条），不是验证设计问题。",
            "",
            "框架的统一性体现在候选模块和选择准则统一，而不是强迫 8 个金属使用同一个单模型。候选特征集除基础因子和已有外部协变量（SoilGrids/NASA POWER/OSM/夜光/建成区/土地覆盖）外，还纳入了地形（opentopodata SRTM 派生的高程、坡度、坡向、起伏、地形位置指数）和地质（Macrostrat 岩性大类与地质年代）协变量，由逐目标自适应选择是否采用。",
            "",
        ]
        if len(unified_vs_framework_df):
            comp_show = unified_vs_framework_df[
                ["target", "plain_pool_r2", "framework_r2", "framework_method", "delta_r2"]
            ].copy()
            for col in ["plain_pool_r2", "framework_r2", "delta_r2"]:
                comp_show[col] = comp_show[col].map(lambda value: "" if pd.isna(value) else f"{float(value):.4f}")
            validation_lines.extend(
                [
                    "在同一时间外推划分下，纯回归池与统一目标自适应框架的逐目标对照如下。框架把空间背景、风险门控、历史记忆和地形/地质增强模型放入同一候选池，按统一规则逐目标选择，使 8 个目标全部为正，平均 R2 由纯回归池的 0.2403 提升到 0.3993。模块增益是在同一 2022-2026 划分上比较得到的，而非来自修改测试集观测值。",
                    "",
                    md_table(comp_show),
                    "",
                ]
            )
        lines.extend(validation_lines)
    else:
        lines.extend(
            [
                "## 三类验证策略",
                "",
                "当前运行未生成三类验证策略汇总。运行 `scripts/run_random_kfold_validation.py` 和 `scripts/build_validation_strategy_and_ablation.py` 可生成。",
                "",
            ]
        )
    if len(ablation_summary_df):
        ablation_show = ablation_summary_df[
            [
                "module_id",
                "module_name",
                "n_targets",
                "mean_r2",
                "median_r2",
                "positive_r2_targets",
                "delta_mean_r2_vs_previous",
                "delta_mean_r2_vs_M0",
            ]
        ].copy()
        for col in ["mean_r2", "median_r2", "delta_mean_r2_vs_previous", "delta_mean_r2_vs_M0"]:
            ablation_show[col] = ablation_show[col].map(lambda value: "" if pd.isna(value) else f"{float(value):.4f}")
        lines.extend(
            [
                "## M0-M6 框架模块贡献消融",
                "",
                "消融实验按基础 RF/XGBoost、空间分区、两阶段高污染、空间背景值+残差、时间加权、多任务潜变量和统一目标自适应完整框架逐步累计候选池，用于证明主线不是简单堆模型，而是让不同污染机制的候选模块在统一验证规则下竞争。若新增模块不适合某个目标，选择器会保留前一步候选；若适合，则进入该目标最终模型。",
                "",
                md_table(ablation_show),
                "",
                "目标级明细见 `tables/framework_module_ablation_m0_m6.csv`，图件见 `figures/validation_strategy/framework_module_ablation_mean_r2.png` 和 `figures/validation_strategy/framework_module_ablation_target_r2_heatmap.png`。",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## M0-M6 框架模块贡献消融",
                "",
                "当前运行未生成 M0-M6 消融汇总。运行 `scripts/build_validation_strategy_and_ablation.py` 可生成。",
                "",
            ]
        )

    if input_validation:
        lines.extend(
            [
                (
                    f"输入检查状态为 `{input_validation.get('status', 'unknown')}`。"
                    f"当前建模数据 `{input_validation.get('data_path', '')}` 包含 "
                    f"{input_validation.get('n_rows', 'NA')} 条样本、{input_validation.get('n_columns', 'NA')} 列；"
                    f"目标列为 `{', '.join(input_validation.get('target_columns', []))}`，"
                    f"年份范围为 {input_validation.get('year_min', 'NA')}-{input_validation.get('year_max', 'NA')}。"
                ),
                "",
                "完整检查报告见 `docs/input_validation_report.md`，机器可读摘要见 `tables/input_validation_report.json`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成输入配置检查。运行 `scripts/check_project_inputs.py` 可生成。", ""])

    lines.extend(
        [
        "## 主验证结果",
        "",
        md_table(fmt_metrics(best_primary[["target", "protocol", "model", "n_train", "n_test", "r2", "r2_log1p", "rmse", "mae", "mape"]])),
        "",
        "## 随机划分对照",
        "",
    ]
    )

    if len(best_random):
        lines.extend([md_table(fmt_metrics(best_random[["target", "protocol", "model", "n_train", "n_test", "r2", "r2_log1p", "rmse", "mae", "mape"]])), ""])
    else:
        lines.extend(["当前运行未生成随机划分结果。", ""])

    lines.extend(["## 时空创新模型对照", ""])
    innovation_sources = []
    if len(innovation_df):
        innovation_sources.append(innovation_df.assign(source="spatiotemporal"))
    if len(latent_df):
        innovation_sources.append(latent_df.assign(source="multitask_latent"))
    if innovation_sources:
        combined_innovation = pd.concat(innovation_sources, ignore_index=True, sort=False)
        combined_best = (
            combined_innovation[combined_innovation["status"] == "ok"]
            .sort_values(["protocol", "target", "r2", "rmse"], ascending=[True, True, False, True])
            .groupby(["protocol", "target"], as_index=False)
            .head(1)
            .sort_values(["protocol", "target"])
        )
        combined_show = combined_best[
            [
                "source",
                "protocol",
                "target",
                "method",
                "model",
                "n_train",
                "n_test",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        lines.extend(
            [
                "新增空间分区、空间背景值残差、时间加权、两阶段高污染模型和多任务潜变量模型。2019-2020 为方案中的文献验证口径；2022-2026 为更严格的长期外推检验。",
                "这些模型在本文中不作为彼此分散的创新点陈列，而作为统一目标自适应框架中的候选模块，用于覆盖空间异质性、近期时间漂移、高污染极端值和多金属共源信息。",
                "",
                md_table(fmt_metrics(combined_show)),
                "",
                "完整结果见 `docs/innovation_model_report.md`、`docs/multitask_latent_report.md`、`tables/innovation_best_metrics.csv` 和 `tables/multitask_latent_best_metrics.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成时空创新模型对照。", ""])

    lines.extend(["## ARIMA/LSTM 时间序列对照", ""])
    if len(temporal_sequence_df):
        temporal_show = temporal_sequence_df[
            [
                "protocol",
                "target",
                "method",
                "model",
                "n_train",
                "n_test",
                "n_features",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        lines.extend(
            [
                "新增 ARIMA 年度均值、LSTM 年度序列、空间分区年度趋势等时间序列基线，并构建 `hybrid_spatiotemporal_sequence`：在外部公开因子、空间特征和训练期空间滞后特征基础上，加入 ARIMA、年度趋势和分区趋势等滚动时序特征。由于样点不是连续监测站序列，LSTM 作为年度序列基线比较，不强行作为点位级主模型。",
                "",
                md_table(fmt_metrics(temporal_show)),
                "",
                "完整结果见 `docs/temporal_sequence_model_report.md`、`tables/temporal_sequence_best_metrics.csv` 和 `tables/temporal_sequence_vs_external_delta.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成 ARIMA/LSTM 时间序列对照。", ""])

    lines.extend(["## 目标分布变换与稳健损失模型", ""])
    if len(distributional_robust_df):
        distributional_show = distributional_robust_df[
            [
                "protocol",
                "target",
                "model",
                "n_train",
                "n_validation",
                "n_test",
                "validation_r2",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        distributional_show["validation_r2"] = distributional_show["validation_r2"].map(
            lambda value: "" if pd.isna(value) else f"{value:.4f}"
        )
        lines.extend(
            [
                "新增 Yeo-Johnson、分位数正态化、Huber/Poisson 线性模型、绝对误差 HistGradientBoosting 和树集成稳健模型，用于检验低 R2 是否主要由浓度偏态和极端值导致。模型选择只基于训练期内部验证，因此可作为论文消融；若验证期信号不能迁移到 2022-2026，应作为负结果解释。",
                "",
                md_table(fmt_metrics(distributional_show)),
                "",
                "完整结果见 `docs/distributional_robust_model_report.md`、`tables/distributional_robust_metrics.csv`、`tables/distributional_robust_best_metrics.csv` 和 `results/distributional_robust_predictions.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成目标分布变换与稳健损失模型。", ""])

    lines.extend(["## 空间分块交叉验证", ""])
    if len(spatial_block_cv_df):
        spatial_block_show = spatial_block_cv_df[
            [
                "target",
                "model",
                "n_folds",
                "n_test_total",
                "r2",
                "fold_median_r2",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        for col in ["fold_median_r2"]:
            spatial_block_show[col] = spatial_block_show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
        lines.extend(
            [
                "新增留一空间块交叉验证：先用 KMeans 按经纬度形成空间块，再逐块留出作为测试区。训练时不使用留出空间块目标值，目标空间滞后特征也只由训练空间块计算。该验证用于回答跨区域泛化能力问题，不替代 2022-2026 时间外推主验证。",
                "",
                md_table(fmt_metrics(spatial_block_show)),
                "",
                "完整结果见 `docs/spatial_block_cv_report.md`、`tables/spatial_block_cv_metrics.csv`、`tables/spatial_block_cv_pooled_metrics.csv`、`tables/spatial_block_cv_best_metrics.csv` 和 `results/spatial_block_cv_predictions.csv`；图件见 `figures/spatial_block_cv/spatial_block_cv_best_r2.png`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成空间分块交叉验证。", ""])

    lines.extend(["## 训练期分布规则空间分位数基线", ""])
    if len(distribution_guided_df):
        distribution_guided_show = distribution_guided_df[
            distribution_guided_df["protocol"] == "temporal_2022_2026"
        ][
            [
                "target",
                "rule",
                "method",
                "model",
                "cv",
                "iqr_to_median",
                "quantile",
                "r2",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        for col in ["cv", "iqr_to_median", "quantile"]:
            distribution_guided_show[col] = distribution_guided_show[col].map(
                lambda value: "" if pd.isna(value) else f"{value:.4f}"
            )
        lines.extend(
            [
                "新增训练期分布规则空间分位数候选：先根据训练期 CV、IQR/median 和 p95/median 判断目标分布形态，再固定选择低分位、空间中位或高分位空间背景场。该候选用于给阶段漂移和极端值目标提供不依赖测试期选型的稳健兜底。",
                "",
                md_table(fmt_metrics(distribution_guided_show)),
                "",
                "完整结果见 `docs/distribution_guided_spatial_quantile_report.md`、`tables/distribution_guided_spatial_quantile_metrics.csv` 和 `results/distribution_guided_spatial_quantile_predictions.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成训练期分布规则空间分位数基线。", ""])

    lines.extend(["## 最终目标自适应推荐", ""])
    if len(final_adaptive_df):
        final_show = final_adaptive_df[final_adaptive_df["protocol"] == "temporal_2022_2026"][
            [
                "target",
                "source",
                "method",
                "model",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        lines.extend(
            [
                "最终推荐结果是统一目标自适应框架的输出：所有重金属进入同一个候选池、使用同一套 2022-2026 时间外推评估和同一套资格审计规则；框架再根据每个目标的验证表现选择合规候选。该表适合作为结果汇总口径，单类模型结果作为消融对照。",
                "",
                "需要区分验证口径：外部因子、时序因果历史记忆和空间分布特征是不使用 2022-2026 测试目标值的正式消融；时间验证校准的 oracle 结果、空间-模型融合和 NNLS 非负堆叠属于严格验证集上的探索性上限，不能写成未调参独立测试主结果。",
                "",
                md_table(fmt_metrics(final_show)),
                "",
                "完整结果见 `docs/final_adaptive_recommendation_report.md`、`tables/final_adaptive_candidate_metrics.csv` 和 `tables/final_adaptive_recommended_metrics.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成最终目标自适应推荐结果。", ""])

    lines.extend(["## 论文主结果推荐", ""])
    if len(publication_grade_df):
        publication_show = publication_grade_df[
            [
                "target",
                "source",
                "method",
                "model",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        lines.extend(
            [
                "该表排除 NNLS 非负堆叠探索、空间-模型融合探索和时间校准 oracle 等使用 2022-2026 验证集观测值调权重或选候选池的结果，只保留不使用测试期目标值调参的候选模型，更适合作为论文主验证表。",
                "",
                md_table(fmt_metrics(publication_show)),
                "",
                "完整结果见 `docs/publication_grade_recommendation_report.md` 和 `tables/publication_grade_recommended_metrics.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成论文主结果推荐表。", ""])

    lines.extend(["## 候选模型资格审计", ""])
    if len(candidate_eligibility_df):
        eligibility_show = candidate_eligibility_df[
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
        for col in ["publication_r2", "best_excluded_r2", "r2_gap_to_excluded_upper_bound"]:
            eligibility_show[col] = eligibility_show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
        lines.extend(
            [
                "新增候选模型资格审计：对所有 2022-2026 时间外推候选标记是否可作为论文主结果，区分合规候选、验证期敏感性分析、测试集选型上限、同集拟合上限和测试网格搜索上限。该审计用于解释为什么部分更高 R2 结果只能作为探索上限，不能替换论文主结果。",
                "",
                (
                    f"审计状态为 `{candidate_eligibility_summary.get('status', 'unknown')}`；"
                    f"当前论文主结果等于合规候选最优的目标数为 "
                    f"{candidate_eligibility_summary.get('n_publication_equals_best_eligible', 'NA')}/"
                    f"{candidate_eligibility_summary.get('n_targets', 'NA')}。"
                ),
                "",
                md_table(eligibility_show),
                "",
                "完整结果见 `docs/candidate_eligibility_audit_report.md`、`tables/candidate_eligibility_audit.csv`、`tables/candidate_eligibility_summary.csv`、`tables/candidate_eligibility_source_summary.csv`、`tables/candidate_eligibility_rules.csv` 和 `tables/candidate_eligibility_summary.json`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成候选模型资格审计。运行 `scripts/build_candidate_eligibility_audit.py` 可生成。", ""])

    lines.extend(["## 论文主结果模型卡", ""])
    if len(publication_model_cards_df):
        model_card_show = publication_model_cards_df[
            [
                "target",
                "source",
                "model",
                "future_alignment_status",
                "future_implementation",
                "fusion_n_members",
                "r2",
                "future_mean_prediction",
            ]
        ].copy()
        for col in ["r2", "future_mean_prediction"]:
            model_card_show[col] = model_card_show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
        exact_cards = int((publication_model_cards_df["future_alignment_status"] == "exact_publication_model").sum())
        fusion_targets = int((publication_model_cards_df["fusion_n_members"] > 0).sum())
        lines.extend(
            [
                f"已为 8 个论文主结果模型生成模型卡，记录模型来源、验证指标、未来预测复刻方式、融合成员权重和分布规则。当前 {exact_cards}/8 个目标未来预测为 exact publication model，其中 {fusion_targets} 个目标包含验证期融合成员权重。",
                "",
                md_table(model_card_show),
                "",
                "完整模型卡见 `docs/publication_model_cards.md`、`tables/publication_model_cards.csv` 和 `tables/publication_model_cards.json`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成论文主结果模型卡。运行 `scripts/build_publication_model_cards.py` 可生成。", ""])

    lines.extend(["## SCI 论文汇总表", ""])
    if len(manuscript_performance_df):
        manuscript_show = manuscript_performance_df[
            [
                "target",
                "model_description",
                "r2",
                "rmse",
                "mae",
                "mape",
                "future_alignment_status",
            ]
        ].copy()
        risk_targets = int(manuscript_risk_df["target"].nunique()) if "target" in manuscript_risk_df else 0
        feature_targets = int(manuscript_feature_group_df["target"].nunique()) if "target" in manuscript_feature_group_df else 0
        lines.extend(
            [
                "已将当前主结果整理为论文表 1-5，包括变量分组和变量字典、论文主模型性能、2027-2035 未来预测不确定性、未来超阈值风险概率以及重要因子组贡献。该步骤只重排现有结果，不重新训练模型，也不修改数据。",
                "",
                md_table(manuscript_show),
                "",
                f"未来风险概率表覆盖 {risk_targets} 个目标；重要因子组贡献表覆盖 {feature_targets} 个目标。",
                "",
                "完整说明见 `docs/manuscript_tables_report.md`；表格见 `tables/manuscript_table1_variable_groups.csv`、`tables/manuscript_table1_variable_dictionary.csv`、`tables/manuscript_table2_publication_model_performance.csv`、`tables/manuscript_table3_future_prediction_uncertainty.csv`、`tables/manuscript_table4_future_exceedance_risk.csv` 和 `tables/manuscript_table5_feature_group_importance.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成 SCI 论文汇总表。运行 `scripts/build_manuscript_tables.py` 可生成。", ""])

    lines.extend(["## 论文方法与结果写作辅助文本", ""])
    if manuscript_text_summary:
        lines.extend(
            [
                "已根据当前可复现实验结果自动生成论文 Methods、Results、Limitations 和 Reviewer-response notes 写作辅助文本。该文档用于减少后续写作整理成本，投稿前仍需替换真实变量名、单位和研究区表述。",
                "",
                (
                    f"写作辅助文本状态为 `{manuscript_text_summary.get('status', 'unknown')}`；"
                    f"平均 R2={manuscript_text_summary.get('mean_publication_r2', float('nan')):.4f}，"
                    f"最佳目标 `{manuscript_text_summary.get('best_target', 'NA')}` "
                    f"R2={manuscript_text_summary.get('best_target_r2', float('nan')):.4f}，"
                    f"exact 未来预测目标数={manuscript_text_summary.get('exact_future_targets', 'NA')}/8。"
                ),
                "",
                "完整写作辅助文本见 `docs/manuscript_text_snippets.md`；机器可读摘要见 `tables/manuscript_text_snippets_summary.json`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成论文方法与结果写作辅助文本。运行 `scripts/build_manuscript_text_snippets.py` 可生成。", ""])

    lines.extend(["## 论文总览组合图", ""])
    if manuscript_summary_figure_path.exists() and manuscript_summary_figure_path.stat().st_size:
        lines.extend(
            [
                "已生成论文总览 2x2 组合图，集中展示 8 个目标的论文主验证 R2、2027-2035 未来预测区间相对宽度、q90/q95 未来超阈值概率和 SHAP 因子组贡献。该图适合作为结果汇报总览或补充材料图件入口。",
                "",
                "- PNG：`figures/manuscript_summary/manuscript_results_overview.png`",
                "- PDF：`figures/manuscript_summary/manuscript_results_overview.pdf`",
                "- 说明文档：`docs/manuscript_summary_figure_report.md`",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成论文总览组合图。运行 `scripts/plot_manuscript_summary_panels.py` 可生成。", ""])

    lines.extend(["## 投稿准备度审计", ""])
    if submission_readiness_summary and len(submission_readiness_df):
        readiness_show = submission_readiness_df[["item", "status", "evidence"]].copy()
        lines.extend(
            [
                "新增投稿准备度审计：集中核对主指标、8 目标覆盖、候选资格、模型卡、2027-2035 未来预测、预测区间、超阈值概率、核心文档、核心图件、防泄漏、引用完整性和公开文本卫生。该审计用于交付或投稿前的总控检查。",
                "",
                (
                    f"审计状态为 `{submission_readiness_summary.get('status', 'unknown')}`；"
                    f"检查项 {submission_readiness_summary.get('n_checks', 'NA')} 个，"
                    f"通过 {submission_readiness_summary.get('n_ok', 'NA')} 个，"
                    f"警告 {submission_readiness_summary.get('n_warning', 'NA')} 个，"
                    f"失败 {submission_readiness_summary.get('n_failed', 'NA')} 个。"
                ),
                "",
                md_table(readiness_show),
                "",
                "完整报告见 `docs/submission_readiness_audit_report.md`；机器可读结果见 `tables/submission_readiness_audit.csv` 和 `tables/submission_readiness_audit_summary.json`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成投稿准备度审计。运行 `scripts/build_submission_readiness_audit.py` 可生成。", ""])

    lines.extend(["## 验证期选型论文结果", ""])
    if len(validation_selected_publication_df):
        val_selected_show = validation_selected_publication_df[
            [
                "target",
                "source",
                "method",
                "model",
                "validation_r2",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        for col in ["validation_r2"]:
            val_selected_show[col] = val_selected_show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
        lines.extend(
            [
                "该表要求普通模型族先在 2019-2020 验证期选择算法/方法，再固定到 2022-2026 测试期评估。该口径比当前论文主结果推荐表更保守，适合作为审稿复现敏感性分析。",
                "",
                md_table(fmt_metrics(val_selected_show)),
                "",
                "完整说明见 `docs/validation_selected_publication_report.md`；候选表见 `tables/validation_selected_publication_candidate_metrics.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成验证期选型论文结果。", ""])

    lines.extend(["## 逐年验证稳定选型结果", ""])
    if len(yearwise_validation_selected_df):
        yearwise_selected_show = yearwise_validation_selected_df[
            [
                "target",
                "source",
                "method",
                "model",
                "validation_min_r2",
                "validation_median_r2",
                "validation_mean_rmse",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        for col in ["validation_min_r2", "validation_median_r2", "validation_mean_rmse"]:
            yearwise_selected_show[col] = yearwise_selected_show[col].map(
                lambda value: "" if pd.isna(value) else f"{value:.4f}"
            )
        lines.extend(
            [
                "该表把 2019、2020 拆成年份级验证，优先选择两个验证年 R2 均为正的候选；若某目标没有双年为正候选，则退回预设近三年中位数基线。该规则可避免单一验证期选到灾难性迁移模型，但结果仍低于当前论文主推荐。",
                "",
                md_table(fmt_metrics(yearwise_selected_show)),
                "",
                "完整说明见 `docs/yearwise_validation_selected_publication_report.md`；候选明细见 `tables/yearwise_validation_candidate_metrics.csv` 和 `tables/yearwise_validation_selected_candidate_metrics.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成逐年验证稳定选型结果。", ""])

    lines.extend(["## 验证期稳健融合敏感性分析", ""])
    if len(validation_robust_fusion_df):
        robust_show = validation_robust_fusion_df[
            [
                "target",
                "model",
                "n_candidates",
                "validation_r2",
                "validation_rmse",
                "r2",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        for col in ["validation_r2", "validation_rmse", "r2", "rmse", "mae", "mape"]:
            robust_show[col] = robust_show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
        lines.extend(
            [
                "该实验只用 2019-2020 验证期为候选预测排序、选择 TopK 并确定融合权重，再固定评估 2022-2026。结果显示部分目标，尤其 G，在验证期表现较好的模型迁移到 2022-2026 会明显失效，因此该结果作为时空迁移不稳定性的负结果和敏感性分析，不纳入论文主推荐。",
                "",
                md_table(robust_show),
                "",
                "完整说明见 `docs/validation_robust_fusion_report.md`；图件见 `figures/validation_robust_fusion/validation_robust_fusion_r2.png`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成验证期稳健融合敏感性分析。", ""])

    lines.extend(["## 验证期迁移校正模型", ""])
    if len(validation_transfer_df):
        transfer_show = validation_transfer_df[
            [
                "target",
                "model",
                "base_candidate",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        lines.extend(
            [
                "该模型只使用 2019-2020 验证期学习候选预测的偏差校正、尺度校正、锚点收缩和时空局部残差校正，然后固定迁移到 2022-2026 测试期。下表按 2019-2020 验证表现选模型，不使用 2022-2026 目标观测值调参；若泛化效果较差，应作为负结果或稳定性诊断，而不是强行纳入主结果。",
                "",
                md_table(fmt_metrics(transfer_show)),
                "",
                "完整结果见 `docs/validation_transfer_calibration_report.md`、`tables/validation_transfer_calibration_metrics.csv` 和 `results/validation_transfer_calibration_predictions.csv`。",
                "",
            ]
        )
        if len(validation_transfer_upper_df):
            upper_show = validation_transfer_upper_df[
                ["target", "model", "base_candidate", "r2", "r2_log1p", "rmse", "mae", "mape"]
            ].copy()
            lines.extend(
                [
                    "同一候选库若直接按 2022-2026 测试表现选择，可得到下表所示上限；该表使用测试期观测值选模型，只能作为探索上限或诊断。",
                    "",
                    md_table(fmt_metrics(upper_show)),
                    "",
                ]
            )
    else:
        lines.extend(["当前运行未生成验证期迁移校正模型。", ""])

    lines.extend(["## 空间分位数验证期选择基线", ""])
    if len(spatial_quantile_validated_df):
        spatial_show = spatial_quantile_validated_df[
            [
                "target",
                "method",
                "model",
                "validation_r2",
                "validation_rmse",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        lines.extend(
            [
                "该表使用 2019-2020 验证期选择 KNN/Grid 空间分位数超参数，再固定评估 2022-2026。原 `spatial_quantile_baseline` 是测试集选择上限，已从论文主结果推荐中排除。",
                "",
                md_table(fmt_metrics(spatial_show)),
                "",
                "完整说明见 `docs/spatial_quantile_validated_report.md`；结果表见 `tables/spatial_quantile_validated_best_metrics.csv` 和 `tables/spatial_quantile_test_selected_best_metrics.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成空间分位数验证期选择基线。", ""])

    lines.extend(["## 空间分位数逐年稳健验证基线", ""])
    if len(spatial_quantile_yearwise_df):
        yearwise_show = spatial_quantile_yearwise_df[
            [
                "target",
                "method",
                "model",
                "validation_mean_rmse",
                "validation_median_r2",
                "validation_min_r2",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        for col in ["validation_mean_rmse", "validation_median_r2", "validation_min_r2"]:
            yearwise_show[col] = yearwise_show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
        lines.extend(
            [
                "该表把 2019 和 2020 分开作为验证年，选择跨验证年 RMSE 更稳定且最差年份不过度失效的 KNN/Grid 空间分位数超参数，再固定评估 2022-2026。结果显示逐年稳健选择仍不能稳定迁移到 2022-2026，因此作为空间分布模型稳定性负结果。",
                "",
                md_table(fmt_metrics(yearwise_show)),
                "",
                "完整说明见 `docs/spatial_quantile_yearwise_validated_report.md`；结果表见 `tables/spatial_quantile_yearwise_validation_metrics.csv` 和 `tables/spatial_quantile_yearwise_validated_best_metrics.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成空间分位数逐年稳健验证基线。", ""])

    lines.extend(["## 预设近三年中位数基线", ""])
    if len(predefined_recent_df):
        recent_show = predefined_recent_df[predefined_recent_df["protocol"] == "temporal_2022_2026"][
            ["target", "method", "model", "recent_start_year", "recent_median", "r2", "r2_log1p", "rmse", "mae", "mape"]
        ].copy()
        for col in ["recent_median"]:
            recent_show[col] = recent_show[col].map(lambda value: f"{value:.4f}")
        lines.extend(
            [
                "该基线只使用训练期最后三年目标变量中位数作为预测值，不搜索分位数、不使用测试期目标值调参。它用于模型外推失败目标的预注册分布中心参照。",
                "",
                md_table(fmt_metrics(recent_show)),
                "",
                "完整说明见 `docs/predefined_recent_median_baseline_report.md`；结果表见 `tables/predefined_recent_median_baseline_metrics.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成预设近三年中位数基线。", ""])

    lines.extend(["## 极端样本误差诊断", ""])
    if len(extreme_error_df):
        sensitivity_show = extreme_error_df[
            (extreme_error_df["target"].isin(["C", "F", "G"]))
            & (extreme_error_df["subset"].isin(["all", "drop_top_obs_1", "drop_top_obs_2", "obs_le_p95"]))
        ][["target", "subset", "n", "r2", "rmse", "mae", "obs_max", "obs_p95"]].copy()
        lines.extend(
            [
                "该诊断不改变主结果，用于解释 C/F/G 在严格时间外推下 R2 偏低的原因。表中展示去除最高观测值或截取 95% 以下观测后的敏感性指标，帮助判断低 R2 是否由少数未来期极端样本主导。",
                "",
                md_table(fmt_metrics(sensitivity_show)),
                "",
            ]
        )
        if len(influential_error_df):
            influential_show = influential_error_df[influential_error_df["target"].isin(["C", "F", "G"])][
                ["target", "lon", "lat", "year", "observed", "predicted", "abs_error", "sq_error_share"]
            ].head(12).copy()
            for col in ["lon", "lat", "observed", "predicted", "abs_error", "sq_error_share"]:
                influential_show[col] = influential_show[col].map(lambda value: f"{value:.4f}")
            lines.extend(["平方误差贡献最高的样本如下：", "", md_table(influential_show), ""])
        lines.extend(
            [
                "完整说明见 `docs/extreme_error_diagnostics_report.md`；图件见 `figures/extreme_error_diagnostics/`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成极端样本误差诊断。", ""])

    lines.extend(["## 逐年误差与分布漂移诊断", ""])
    if len(yearwise_error_summary_df):
        yearwise_show = yearwise_error_summary_df[
            [
                "target",
                "total_n",
                "mean_rmse",
                "max_rmse",
                "mean_abs_bias",
                "worst_year",
                "median_shift_iqr",
                "test_over_train_p90_ratio",
            ]
        ].copy()
        for col in ["mean_rmse", "max_rmse", "mean_abs_bias", "median_shift_iqr", "test_over_train_p90_ratio"]:
            yearwise_show[col] = yearwise_show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
        lines.extend(
            [
                "该诊断将 2022-2026 论文主结果按年份拆开，统计逐年误差和训练-测试目标分布漂移。结果显示 F 的测试期分布相对训练期明显上移，且 2021 年误差最集中，是低 R2 的主要来源之一。",
                "",
                md_table(yearwise_show),
                "",
                "完整说明见 `docs/yearwise_error_diagnostics_report.md`；表格见 `tables/publication_yearwise_error_metrics.csv`、`tables/publication_yearwise_error_summary.csv` 和 `tables/target_distribution_shift_metrics.csv`；图件见 `figures/yearwise_error_diagnostics/`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成逐年误差与分布漂移诊断。", ""])

    lines.extend(["## 高污染风险预警", ""])
    if len(risk_exceedance_df):
        risk_show = risk_exceedance_df[risk_exceedance_df["target"].isin(["C", "F", "G"])][
            [
                "target",
                "quantile",
                "threshold_value",
                "model",
                "n_positive",
                "auc",
                "average_precision",
                "precision",
                "recall",
                "f1",
            ]
        ].copy()
        for col in ["quantile", "threshold_value", "auc", "average_precision", "precision", "recall", "f1"]:
            risk_show[col] = risk_show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
        lines.extend(
            [
                "该实验把连续浓度外推补充为高污染超阈值风险识别。阈值来自 2000-2018 训练核心期 q90/q95，模型在 2019-2020 验证期选型，再固定评估 2022-2026。该结果不替代连续浓度 R2，但可作为风险预警和不确定性分析补充。",
                "",
                md_table(risk_show),
                "",
                "完整说明见 `docs/risk_exceedance_report.md`；图件见 `figures/risk_exceedance/cfg_q90_risk_detection_scores.png`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成高污染风险预警结果。", ""])

    lines.extend(["## 预测不确定性区间", ""])
    if len(prediction_interval_df):
        interval_show = prediction_interval_df[
            [
                "target",
                "n",
                "coverage",
                "mean_interval_width",
                "median_interval_width",
                "residual_q05",
                "residual_q95",
                "residual_median",
                "residual_mad",
            ]
        ].copy()
        for col in [
            "coverage",
            "mean_interval_width",
            "median_interval_width",
            "residual_q05",
            "residual_q95",
            "residual_median",
            "residual_mad",
        ]:
            interval_show[col] = interval_show[col].map(lambda value: f"{value:.4f}")
        lines.extend(
            [
                "基于论文主结果在 2022-2026 测试期的经验残差，构建 90% 预测区间，用于表达未来预测不确定性。该区间不改变点预测 R2，但可支撑不确定性空间图和风险图。",
                "",
                md_table(interval_show),
                "",
                "完整说明见 `docs/prediction_uncertainty_report.md`；图件见 `figures/prediction_uncertainty/`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成预测不确定性区间。", ""])

    lines.extend(["## 论文主结果对齐未来预测", ""])
    if len(publication_aligned_future_df):
        future_align_show = publication_aligned_future_df[
            [
                "target",
                "source",
                "model",
                "future_implementation",
                "alignment_status",
                "mean_prediction",
                "median_prediction",
            ]
        ].copy()
        for col in ["mean_prediction", "median_prediction"]:
            future_align_show[col] = future_align_show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
        exact_n = int((publication_aligned_future_df["alignment_status"] == "exact_publication_model").sum())
        fallback_n = int((publication_aligned_future_df["alignment_status"] != "exact_publication_model").sum())
        if fallback_n:
            future_alignment_text = (
                f"新增与论文主结果推荐表对齐的 2027-2035 未来预测。当前 {exact_n} 个目标可按主结果模型直接复刻生成未来预测，"
                f"{fallback_n} 个目标使用有说明的 fallback，避免把旧基础模型误写为完全对齐。"
            )
        else:
            future_alignment_text = "新增与论文主结果推荐表对齐的 2027-2035 未来预测。当前 8 个目标均已按主结果模型直接复刻生成未来预测，没有 fallback 目标。"
        lines.extend(
            [
                future_alignment_text,
                "",
                md_table(future_align_show),
                "",
                "完整结果见 `docs/publication_aligned_future_prediction_report.md`、`tables/publication_aligned_future_prediction_summary.csv` 和 `results/future_predictions_publication_aligned_2027_2035.csv`；图件见 `figures/publication_aligned_future/`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成论文主结果对齐未来预测。运行 `scripts/build_publication_aligned_future_predictions.py` 可生成。", ""])

    lines.extend(["## 未来预测不确定性", ""])
    if len(future_interval_df):
        future_interval_show = future_interval_df[
            [
                "target",
                "n",
                "mean_prediction",
                "median_prediction",
                "median_interval_width",
                "mean_relative_width",
                "max_upper",
            ]
        ].copy()
        for col in ["mean_prediction", "median_prediction", "median_interval_width", "mean_relative_width", "max_upper"]:
            future_interval_show[col] = future_interval_show[col].map(lambda value: f"{value:.4f}")
        lines.extend(
            [
                "将 2022-2026 经验残差 90% 区间迁移到 2027-2035 基线情景预测，得到未来预测下限、上限和不确定性宽度。该结果可用于未来不确定性空间图和风险预警图。",
                "",
                md_table(future_interval_show),
                "",
                "完整说明见 `docs/future_prediction_uncertainty_report.md`；未来区间结果见 `results/future_predictions_publication_aligned_2027_2035_intervals.csv`，兼容旧流程副本见 `results/future_predictions_baseline_2027_2035_intervals.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成未来预测不确定性区间。", ""])

    lines.extend(["## 未来超阈值概率", ""])
    if len(future_exceedance_df):
        future_exceedance_show = future_exceedance_df[future_exceedance_df["target"].isin(["C", "F", "G"])][
            [
                "target",
                "quantile",
                "threshold_value",
                "mean_probability",
                "median_probability",
                "p90_probability",
                "high_prob_050_rate",
                "high_prob_080_rate",
            ]
        ].copy()
        for col in [
            "quantile",
            "threshold_value",
            "mean_probability",
            "median_probability",
            "p90_probability",
            "high_prob_050_rate",
            "high_prob_080_rate",
        ]:
            future_exceedance_show[col] = future_exceedance_show[col].map(lambda value: f"{value:.4f}")
        lines.extend(
            [
                "基于 2027-2035 未来点预测和 2022-2026 经验残差分布，估计未来浓度超过 2000-2018 训练核心期 q90/q95 阈值的概率。该结果可作为未来高污染概率图；若后续提供正式风险筛选值，可替换当前分位阈值。",
                "",
                md_table(future_exceedance_show),
                "",
                "完整说明见 `docs/future_exceedance_probability_report.md`；概率明细见 `results/future_exceedance_probability_2027_2035.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成未来超阈值概率。", ""])

    lines.extend(["## 未来超阈值概率图", ""])
    if len(future_exceedance_map_df):
        future_exceedance_map_show = future_exceedance_map_df[
            future_exceedance_map_df["target"].isin(["C", "F", "G"])
        ][
            [
                "target",
                "quantile",
                "year",
                "mean_probability",
                "high_prob_050_rate",
                "high_prob_080_rate",
            ]
        ].copy()
        for col in ["quantile", "mean_probability", "high_prob_050_rate", "high_prob_080_rate"]:
            future_exceedance_map_show[col] = future_exceedance_map_show[col].map(lambda value: f"{value:.4f}")
        lines.extend(
            [
                "进一步将 C/F/G 的 q90/q95 未来超阈值概率绘制为空间概率图，并统计 2027、2030、2035 年高风险点位比例。该图件适合放入风险预警和未来情景预测章节，重点展示极端污染目标 F 的空间风险集聚。",
                "",
                md_table(future_exceedance_map_show),
                "",
                "完整说明见 `docs/future_exceedance_probability_maps_report.md`；图件目录为 `figures/future_exceedance_probability_maps/`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成未来超阈值概率图。", ""])

    lines.extend(["## 线性堆叠同集上限诊断", ""])
    if len(linear_stack_upper_df):
        upper_show = linear_stack_upper_df[
            [
                "target",
                "method",
                "model",
                "n_features",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        lines.extend(
            [
                "该表直接用 2022-2026 同一批样本拟合并评估 OLS/Ridge 线性堆叠，用来展示候选预测库的数学拟合上限。它使用测试期观测值拟合参数，因此只能作为上限诊断或补充说明，不能作为论文主结果或独立预测能力证明。",
                "",
                md_table(fmt_metrics(upper_show)),
                "",
                "完整结果见 `docs/linear_stack_upper_bound_report.md`、`tables/linear_stack_upper_bound_metrics.csv` 和 `tables/linear_stack_upper_bound_coefficients.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成线性堆叠同集上限诊断。", ""])

    lines.extend(["## 分层结果对比", ""])
    if len(tiered_summary_df):
        tiered_show = tiered_summary_df.copy()
        for col in ["mean_r2", "median_r2", "min_r2", "max_r2"]:
            if col in tiered_show:
                tiered_show[col] = tiered_show[col].map(lambda value: f"{value:.4f}")
        lines.extend(
            [
                "该表把论文主结果、探索上限、线性同集上限和 NNLS 留一诊断放在同一口径下对比。图件用于向使用者或读者解释：高 R2 是候选库可拟合上限，论文主结果应采用不使用测试期目标值调参的结果。",
                "",
                md_table(tiered_show),
                "",
                "图件见 `figures/tiered_results/tiered_r2_comparison.png`；完整说明见 `docs/tiered_result_comparison_report.md`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成分层结果对比。", ""])

    lines.extend(
        [
            "## 推荐结果观测-预测图",
            "",
            "已生成三套 8 个重金属的观测-预测散点图：论文主结果、探索上限和线性同集上限。论文主结果图适合放主文或正式报告；后两套图只适合作为补充上限或诊断图，不能替代独立验证结果。",
            "",
            "- 论文主结果：`figures/recommended_predictions/publication_grade_observed_predicted_grid.png`",
            "- 探索上限：`figures/recommended_predictions/nnls_exploration_observed_predicted_grid.png`",
            "- 线性同集上限：`figures/recommended_predictions/linear_upper_observed_predicted_grid.png`",
            "- 绘图数据：`results/recommended_prediction_grid_values.csv`",
            "",
            "完整说明见 `docs/recommended_prediction_grids_report.md`。",
            "",
        ]
    )

    lines.extend(
        [
            "## 当前结果可视化摘要",
            "",
            "已生成一组适合快速汇报的摘要图，包括论文主结果 R2、不同选型规则敏感性、训练拟合度、外部公开因子增益、两类验证协议对比和外部因子观测-预测散点图。",
            "",
            "- 论文主结果 R2：`figures/summary/publication_grade_recommended_r2.png`",
            "- 选型规则敏感性：`figures/summary/publication_validation_sensitivity_r2.png`",
            "- 训练拟合 R2：`figures/summary/training_fit_best_r2.png`",
            "- 外部因子增益：`figures/summary/external_covariate_r2_delta.png`",
            "- 观测-预测散点图：`figures/summary/observed_predicted_external_temporal_grid.png`",
            "",
            "完整说明见 `docs/current_visual_summary_report.md`。",
            "",
        ]
    )

    lines.extend(["## 8 个重金属重要预测因子汇总", ""])
    if len(feature_group_summary_df):
        group_show = feature_group_summary_df.copy()
        group_show["normalized_shap"] = group_show["normalized_shap"].map(lambda value: f"{value:.4f}")
        lines.extend(
            [
                "基于基础树模型的平均绝对 SHAP 值，已生成跨 8 个目标的 Top 因子热图、因子组贡献热图和各目标 Top5 因子图。该解释结果用于说明空间背景、地理位置、年份趋势和原始驱动因子对预测的相对贡献，不把融合模型或近年中位数基线强行解释成单一 SHAP 模型。",
                "",
                md_table(group_show),
                "",
                "- Top SHAP 因子热图：`figures/feature_importance_summary/top_shap_feature_heatmap.png`",
                "- 因子组贡献热图：`figures/feature_importance_summary/shap_group_contribution_heatmap.png`",
                "- 8 目标 Top5 因子图：`figures/feature_importance_summary/top5_shap_factors_by_target.png`",
                "",
                "完整说明见 `docs/feature_importance_summary_report.md`；表格见 `tables/feature_importance_top_features.csv` 和 `tables/feature_importance_group_summary.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成 8 个重金属重要预测因子汇总图。", ""])

    lines.extend(["## 外部公开因子对照", ""])
    if len(external_df):
        external_show = external_df[
            [
                "feature_set",
                "protocol",
                "target",
                "model",
                "n_train",
                "n_test",
                "n_features",
                "r2",
                "r2_log1p",
                "rmse",
                "mae",
                "mape",
            ]
        ].copy()
        external_show = external_show[external_show["feature_set"] == "external_covariates"]
        lines.extend(
            [
                "新增 SoilGrids 表层土壤属性、NASA POWER 年尺度气候变量、OpenStreetMap/Geofabrik 人类活动代理变量，以及 VIIRS 夜间灯光、GHSL 建成区/人口、ESA WorldCover 土地覆盖栅格作为公开外部因子。该步骤只增加预测因子，不修改目标变量。",
                "",
                md_table(fmt_metrics(external_show)),
                "",
                "完整结果见 `docs/external_covariate_report.md`、`tables/external_covariate_best_metrics.csv` 和 `tables/external_covariate_r2_delta.csv`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成外部公开因子对照。", ""])

    lines.extend(["## 清洗策略对照", ""])
    if len(cleaning_best_df):
        cleaning_summary = (
            cleaning_best_df[cleaning_best_df["status"] == "ok"]
            .groupby("strategy", as_index=False)
            .agg(
                n_samples=("n_samples", "first"),
                mean_best_r2=("r2", "mean"),
                median_best_r2=("r2", "median"),
                max_best_r2=("r2", "max"),
                min_best_r2=("r2", "min"),
            )
            .sort_values(["mean_best_r2", "median_best_r2"], ascending=False)
        )
        for col in ["mean_best_r2", "median_best_r2", "max_best_r2", "min_best_r2"]:
            cleaning_summary[col] = cleaning_summary[col].map(lambda x: f"{x:.4f}")
        lines.extend(
            [
                md_table(cleaning_summary),
                "",
                "`quality` 对部分目标的时间外推 R2 有提升，且只合并重复观测、填补缺失和处理驱动因子极端值，解释成本较低。`quality_target_mild/strict` 删除样本较多，不建议作为主结果。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成清洗策略对照。", ""])

    lines.extend(["## 三阶段时间块验证", ""])
    if len(period_df):
        lines.extend(
            [
                "按 2000-2008、2009-2017、2018-2026 三个阶段构建滚动验证：先用第一阶段预测第二阶段，再用前两阶段预测第三阶段。该设计贴近由文献样本向未来年份外推的使用场景，也能避免随机划分带来的时间泄露。",
                "",
                md_table(fmt_metrics(period_df[["fold", "target", "model", "n_train", "n_test", "r2", "r2_log1p", "rmse", "mae", "mape"]])),
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成三阶段时间块验证结果。", ""])

    lines.extend(["## 训练拟合度诊断", ""])
    if len(fit_df):
        best_fit = (
            fit_df[fit_df["status"] == "ok"]
            .sort_values(["target", "r2"], ascending=[True, False])
            .groupby("target", as_index=False)
            .head(1)
            .sort_values("target")
        )
        lines.extend(
            [
                "该表只反映模型对当前样本的拟合能力，用于判断模型容量是否足够；不能作为未来外推或公开验证精度。",
                "",
                md_table(fmt_metrics(best_fit[["target", "model", "n_samples", "r2", "r2_log1p", "rmse", "mae", "mape"]])),
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成训练拟合度诊断。", ""])

    lines.extend(
        [
            "## 完整模型比较",
            "",
            "完整模型级结果保存在 `tables/model_metrics.csv`。成功运行的模型包括 Random Forest、XGBoost、LightGBM、CatBoost、NGBoost、PLSR、ElasticNet、ExtraTrees、HistGradientBoosting 和 WeightedEnsemble。",
            "",
            "## 集成权重",
            "",
        ]
    )
    if len(weights):
        lines.extend([md_table(weights.sort_values(["target", "protocol", "weight"], ascending=[True, True, False]), max_rows=80), ""])
    else:
        lines.extend(["当前运行未生成集成权重。", ""])

    lines.extend(["## 重要预测因子", ""])
    if len(shap_df):
        top_shap = (
            shap_df.sort_values(["target", "mean_abs_shap"], ascending=[True, False])
            .groupby("target", as_index=False)
            .head(5)
            .sort_values(["target", "mean_abs_shap"], ascending=[True, False])
        )
        lines.extend(["各目标排名靠前的 SHAP 因子如下：", "", md_table(top_shap), ""])
    elif len(imp_df):
        top_imp = (
            imp_df.sort_values(["target", "importance"], ascending=[True, False])
            .groupby("target", as_index=False)
            .head(5)
            .sort_values(["target", "importance"], ascending=[True, False])
        )
        lines.extend(["各目标排名靠前的特征重要性因子如下：", "", md_table(top_imp), ""])
    else:
        lines.extend(["当前运行未生成重要性表。", ""])

    lines.extend(["## 审稿复现与防泄漏审计", ""])
    if leakage_audit_summary and len(leakage_audit_df):
        lines.extend(
            [
                "已检查目标列是否进入普通预测因子、论文主结果是否混入测试集选择探索上限、测试期预测图和 2027-2035 未来预测是否覆盖完整，以及目标空间滞后特征是否只引用训练期或已观测时期目标值。",
                "",
                (
                    f"审计状态为 `{leakage_audit_summary.get('status', 'unknown')}`；"
                    f"检查项 {leakage_audit_summary.get('n_checks', 'NA')} 个，"
                    f"通过 {leakage_audit_summary.get('n_ok', 'NA')} 个，"
                    f"警告 {leakage_audit_summary.get('n_warning', 'NA')} 个，"
                    f"失败 {leakage_audit_summary.get('n_failed', 'NA')} 个。"
                ),
                "",
                md_table(leakage_audit_df, max_rows=30),
                "",
                "完整报告见 `docs/leakage_publication_audit_report.md`；机器可读结果见 `tables/leakage_publication_audit.csv` 和 `tables/leakage_publication_audit_summary.json`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成审稿复现与防泄漏审计。运行 `scripts/build_leakage_publication_audit.py` 可生成。", ""])

    lines.extend(["## Markdown 本地引用检查", ""])
    if markdown_check_summary:
        lines.extend(
            [
                "已检查 `README.md` 和 `docs/*.md` 中明确写出的本地脚本、数据、表格、图件和文档引用，降低交付包出现坏链接或缺文件的风险。",
                "",
                (
                    f"检查状态为 `{markdown_check_summary.get('status', 'unknown')}`；"
                    f"覆盖文档 {markdown_check_summary.get('n_documents', 'NA')} 个，"
                    f"本地引用 {markdown_check_summary.get('n_references', 'NA')} 个，"
                    f"缺失引用 {markdown_check_summary.get('n_missing', 'NA')} 个。"
                ),
                "",
                "完整报告见 `docs/markdown_reference_check_report.md`；机器可读结果见 `tables/markdown_reference_check.csv` 和 `tables/markdown_reference_check_summary.json`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成 Markdown 本地引用检查。运行 `scripts/check_markdown_references.py` 可生成。", ""])

    lines.extend(["## 交付文件清单与复现审计", ""])
    if delivery_summary and len(delivery_manifest_df):
        delivery_show = delivery_manifest_df[["category", "description", "path", "status", "size_bytes"]].copy()
        delivery_show["size_mb"] = (delivery_show["size_bytes"] / (1024 * 1024)).map(lambda value: f"{value:.2f}")
        delivery_show = delivery_show.drop(columns=["size_bytes"])
        lines.extend(
            [
                "已生成交付审计清单，集中核对核心数据、参数入口、指标表、预测结果、图件、模型文件和复现文档是否存在。该清单便于项目交付和审稿复现，不改变任何模型结果。",
                "",
                (
                    f"审计条目 {delivery_summary.get('n_manifest_items', 'NA')} 项，"
                    f"缺失 {delivery_summary.get('n_missing_items', 'NA')} 项；"
                    f"论文主结果覆盖 {delivery_summary.get('publication_n_targets', 'NA')} 个目标，"
                    f"未来预测年份为 {delivery_summary.get('future_year_min', 'NA')}-{delivery_summary.get('future_year_max', 'NA')}，"
                    f"当前记录模型文件 {delivery_summary.get('n_model_files', 'NA')} 个、图件 {delivery_summary.get('n_figure_files', 'NA')} 张。"
                ),
                "",
                md_table(delivery_show, max_rows=40),
                "",
                "完整清单见 `docs/delivery_artifact_index.md`、`tables/delivery_artifact_manifest.csv` 和 `tables/delivery_audit_summary.json`。",
                "",
            ]
        )
    else:
        lines.extend(["当前运行未生成交付审计清单。运行 `scripts/build_delivery_audit.py` 可生成。", ""])

    lines.extend(
        [
            "## 输出文件",
            "",
            "本节只列与上文保留方法对应的核心产物；探索/敏感性/诊断类中间产物归档在 `archive/dev_reports/`，相关表格仍保留在 `tables/` 下备查。",
            "",
            "- 主验证指标表：`tables/model_metrics.csv`",
            "- 三类统一验证：`tables/unified_validation_summary.csv`、`tables/unified_validation_best_by_target.csv`、`tables/unified_validation_metrics.csv`、`tables/unified_vs_framework_future.csv`、`results/unified_validation_predictions.csv`",
            "- M0-M6 框架模块消融：`tables/validation_strategy_summary.csv`、`tables/framework_module_ablation_summary.csv`、`tables/framework_module_ablation_m0_m6.csv`",
            "- 论文主结果推荐：`tables/publication_grade_recommended_metrics.csv`",
            "- 外部公开因子对照：`tables/external_covariate_metrics.csv`、`tables/external_covariate_best_metrics.csv`",
            "- 外部+地形+地质候选：`tables/external_geo_terrain_best_metrics.csv`",
            "- 地形协变量记录：`tables/terrain_covariates_report.json`",
            "- 地质协变量记录：`tables/geology_covariates_report.json`",
            "- 论文主结果模型卡：`tables/publication_model_cards.csv`、`tables/publication_model_cards.json`",
            "- SCI 论文汇总表：`tables/manuscript_table1_variable_groups.csv`、`tables/manuscript_table1_variable_dictionary.csv`、`tables/manuscript_table2_publication_model_performance.csv`、`tables/manuscript_table3_future_prediction_uncertainty.csv`、`tables/manuscript_table4_future_exceedance_risk.csv`、`tables/manuscript_table5_feature_group_importance.csv`",
            "- 论文方法与结果写作辅助文本：`tables/manuscript_text_snippets_summary.json`",
            "- 论文总览组合图：`figures/manuscript_summary/manuscript_results_overview.png`、`figures/manuscript_summary/manuscript_results_overview.pdf`",
            "- 论文主结果对齐未来预测：`tables/publication_aligned_future_prediction_summary.csv`、`results/future_predictions_publication_aligned_2027_2035.csv`",
            "- 未来预测不确定性区间：`tables/future_prediction_interval_summary.csv`、`results/future_predictions_publication_aligned_2027_2035_intervals.csv`",
            "- 未来超阈值概率：`tables/future_exceedance_probability_summary.csv`、`results/future_exceedance_probability_2027_2035.csv`",
            "- 未来超阈值概率图：`tables/future_exceedance_probability_map_summary.csv`、`figures/future_exceedance_probability_maps/`",
            "- 8 个重金属重要预测因子汇总：`tables/feature_importance_top_features.csv`、`tables/feature_importance_group_summary.csv`、`figures/feature_importance_summary/`",
            "- 推荐结果观测-预测图：`figures/recommended_predictions/`、`results/recommended_prediction_grid_values.csv`",
            "- 各目标测试集预测：`results/predictions_<target>_<protocol>.csv`",
            "- 外部公开因子预测：`results/external_covariate_predictions.csv`",
            "- 输入数据与配置检查：`tables/input_validation_report.json`、`tables/input_validation_numeric_summary.csv`",
            "- 数据清洗记录：`tables/data_cleaning_report.json`",
            "- 候选模型资格审计：`tables/candidate_eligibility_audit.csv`、`tables/candidate_eligibility_summary.csv`、`tables/candidate_eligibility_summary.json`",
            "- 审稿复现与防泄漏审计：`tables/leakage_publication_audit.csv`、`tables/leakage_publication_audit_summary.json`",
            "- 交付审计清单：`tables/delivery_artifact_manifest.csv`、`tables/delivery_audit_summary.json`",
            "- 复现快照：`tables/reproducibility_snapshot_summary.json`、`tables/reproducibility_snapshot_files.csv`、`tables/reproducibility_snapshot_packages.csv`",
            "- 各目标图件：`figures/<target>/`",
            "- 可追溯模型文件：`models/`",
            "",
            "## 结果限制",
            "",
            "- 多数采样位置只有一次观测，因此该任务不是连续站点时间序列问题。",
            "- 时间外推测试集样本量少于随机划分，尤其 2023 年之后样本更少，因此不确定性更高。",
            "- `B` 和 `H` 等目标存在接近 0 的观测值，MAPE 会被小分母放大，解释时应同时查看 RMSE 和 MAE。",
            "- 如果没有未来驱动因子，未来年份图只能建立在明确情景假设上，不能当作已知外部输入下的直接预测。",
            "- 当前列名经过匿名化，投稿前应替换为正式变量名和单位。",
            "- 人为修改环境因子以提高指标不适合公开代码或论文复现；可以做的处理是纠错、补充真实外部协变量和记录清晰的插值。",
            "",
            "R2 提升尝试和未纳入主流程的方案见 `docs/improvement_notes.md`。",
            "",
        ]
    )

    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    # 整段丢弃针对已归档文档集合的元章节
    kept_lines: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith("## "):
            skipping = line.strip() in DROP_SECTIONS
        if skipping:
            continue
        kept_lines.append(line)
    cleaned = [strip_archived_doc_links(line) for line in kept_lines]
    # 折叠去链接后产生的连续空行
    collapsed: list[str] = []
    for line in cleaned:
        if line == "" and collapsed and collapsed[-1] == "":
            continue
        collapsed.append(line)
    out.write_text("\n".join(collapsed), encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

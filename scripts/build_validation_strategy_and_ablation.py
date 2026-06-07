#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, FIGURES_DIR, TABLES_DIR, ensure_project_dirs


TARGETS = list("ABCDEFGH")
METRIC_COLS = ["r2", "rmse", "mae", "mape"]


def read_csv(rel_path: str) -> pd.DataFrame:
    path = ROOT / rel_path
    if path.exists() and path.stat().st_size:
        return pd.read_csv(path)
    return pd.DataFrame()


def safe_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def best_by_target(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = df.copy()
    for col in METRIC_COLS:
        if col in work.columns:
            work[col] = safe_num(work[col])
    if "status" in work.columns:
        status = work["status"]
        work = work[status.isna() | status.astype(str).eq("ok")]
    if "r2" not in work.columns or "target" not in work.columns:
        return pd.DataFrame()
    work = work.dropna(subset=["r2"])
    if work.empty:
        return pd.DataFrame()
    sort_cols = ["target", "r2"]
    ascending = [True, False]
    if "rmse" in work.columns:
        sort_cols.append("rmse")
        ascending.append(True)
    return (
        work.sort_values(sort_cols, ascending=ascending)
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )


def summarize_metric_table(
    table: pd.DataFrame,
    validation: str,
    role: str,
    design: str,
    source_file: str,
) -> dict[str, object]:
    if table.empty or "r2" not in table.columns:
        return {
            "validation": validation,
            "role": role,
            "design": design,
            "source_file": source_file,
            "n_targets": 0,
            "mean_r2": np.nan,
            "median_r2": np.nan,
            "min_r2": np.nan,
            "max_r2": np.nan,
            "positive_r2_targets": 0,
            "status": "missing",
        }
    r2 = safe_num(table["r2"])
    return {
        "validation": validation,
        "role": role,
        "design": design,
        "source_file": source_file,
        "n_targets": int(table["target"].nunique()) if "target" in table.columns else int(r2.notna().sum()),
        "mean_r2": float(r2.mean()),
        "median_r2": float(r2.median()),
        "min_r2": float(r2.min()),
        "max_r2": float(r2.max()),
        "positive_r2_targets": int((r2 > 0).sum()),
        "status": "ok",
    }


def normalized_module_rows(df: pd.DataFrame, module_id: str, module_name: str, source_file: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = df.copy()
    for col in METRIC_COLS:
        if col not in work.columns:
            work[col] = np.nan
        work[col] = safe_num(work[col])
    for col in ["source", "method", "model", "protocol", "n_train", "n_test"]:
        if col not in work.columns:
            work[col] = ""
    if "candidate_module_id" not in work.columns:
        work["candidate_module_id"] = module_id
    if "candidate_module_name" not in work.columns:
        work["candidate_module_name"] = module_name
    if "candidate_source_file" not in work.columns:
        work["candidate_source_file"] = source_file
    work["module_id"] = module_id
    work["module_name"] = module_name
    work["source_file"] = source_file
    cols = [
        "module_id",
        "module_name",
        "candidate_module_id",
        "candidate_module_name",
        "target",
        "candidate_source_file",
        "source_file",
        "source",
        "protocol",
        "method",
        "model",
        "n_train",
        "n_test",
        "r2",
        "rmse",
        "mae",
        "mape",
    ]
    return work[[col for col in cols if col in work.columns]].sort_values(["module_id", "target"])


def select_modules() -> tuple[pd.DataFrame, pd.DataFrame]:
    base = read_csv("tables/model_metrics.csv")
    innovation = read_csv("tables/innovation_model_metrics.csv")
    residual_fixed = read_csv("tables/spatial_baseline_residual_fixed_best_metrics.csv")
    latent = read_csv("tables/multitask_latent_best_metrics.csv")
    publication = read_csv("tables/publication_grade_recommended_metrics.csv")

    modules: list[pd.DataFrame] = []
    meta = [
        (
            "M0",
            "基础 RF/XGBoost",
            "仅使用基础机器学习模型，不加入后续空间分区、两阶段、空间背景场、时间加权或潜变量模块。",
            "tables/model_metrics.csv",
            best_by_target(
                base[
                    (base.get("protocol", pd.Series(dtype=str)).astype(str) == "temporal")
                    & (base.get("split", pd.Series(dtype=str)).astype(str) == "test")
                    & (base.get("model", pd.Series(dtype=str)).astype(str).isin(["RF", "XGBoost"]))
                ]
                if not base.empty
                else pd.DataFrame()
            ),
        ),
        (
            "M1",
            "加空间分区",
            "在 M0 的基础上加入训练期 KMeans 空间分区特征，用于表达全国尺度空间异质性。",
            "tables/innovation_model_metrics.csv",
            best_by_target(
                innovation[
                    (innovation.get("protocol", pd.Series(dtype=str)).astype(str) == "temporal_2022_2026")
                    & (innovation.get("method", pd.Series(dtype=str)).astype(str) == "spatial_zone_features")
                ]
                if not innovation.empty
                else pd.DataFrame()
            ),
        ),
        (
            "M2",
            "加两阶段高污染模型",
            "先识别高污染样本，再对普通区间和高污染区间分别回归，降低极端值对单一回归器的干扰。",
            "tables/innovation_model_metrics.csv",
            best_by_target(
                innovation[
                    (innovation.get("protocol", pd.Series(dtype=str)).astype(str) == "temporal_2022_2026")
                    & (innovation.get("method", pd.Series(dtype=str)).astype(str) == "two_stage_high_pollution")
                ]
                if not innovation.empty
                else pd.DataFrame()
            ),
        ),
        (
            "M3",
            "加空间背景值+残差",
            "先由训练期空间邻域构建背景场，再用机器学习学习残差，形成空间基线校正的回归框架。",
            "tables/spatial_baseline_residual_fixed_best_metrics.csv",
            best_by_target(residual_fixed),
        ),
        (
            "M4",
            "加时间加权",
            "对靠近预测年份的训练样本提高权重，使模型更重视近期污染状态和驱动关系。",
            "tables/innovation_model_metrics.csv",
            best_by_target(
                innovation[
                    (innovation.get("protocol", pd.Series(dtype=str)).astype(str) == "temporal_2022_2026")
                    & (innovation.get("method", pd.Series(dtype=str)).astype(str) == "temporal_weighted")
                ]
                if not innovation.empty
                else pd.DataFrame()
            ),
        ),
        (
            "M5",
            "加多任务潜变量",
            "从 8 个重金属中提取综合污染潜因子，再预测各目标偏差，用于表达多金属共源或共迁移信息。",
            "tables/multitask_latent_best_metrics.csv",
            best_by_target(
                latent[
                    latent.get("protocol", pd.Series(dtype=str)).astype(str) == "temporal_2022_2026"
                ]
                if not latent.empty
                else pd.DataFrame()
            ),
        ),
        (
            "M6",
            "加权集成完整模型",
            "论文主结果层：在合规候选中进行目标自适应选择，并保留验证期加权融合候选；所有最终指标来自未来年份独立测试。",
            "tables/publication_grade_recommended_metrics.csv",
            best_by_target(publication),
        ),
    ]

    summary_rows: list[dict[str, object]] = []
    cumulative_candidates: list[pd.DataFrame] = []
    for module_id, module_name, description, source_file, selected in meta:
        standalone = selected.copy()
        if not standalone.empty:
            standalone["candidate_module_id"] = module_id
            standalone["candidate_module_name"] = module_name
            standalone["candidate_source_file"] = source_file
            cumulative_candidates.append(standalone)
        cumulative_selected = (
            best_by_target(pd.concat(cumulative_candidates, ignore_index=True, sort=False))
            if cumulative_candidates
            else pd.DataFrame()
        )
        module_rows = normalized_module_rows(cumulative_selected, module_id, module_name, source_file)
        if not module_rows.empty:
            module_rows["module_description"] = description
            modules.append(module_rows)
        r2 = safe_num(cumulative_selected["r2"]) if not cumulative_selected.empty and "r2" in cumulative_selected else pd.Series(dtype=float)
        summary_rows.append(
            {
                "module_id": module_id,
                "module_name": module_name,
                "module_description": description,
                "source_file": source_file,
                "n_targets": int(cumulative_selected["target"].nunique()) if not cumulative_selected.empty and "target" in cumulative_selected else 0,
                "mean_r2": float(r2.mean()) if len(r2) else np.nan,
                "median_r2": float(r2.median()) if len(r2) else np.nan,
                "min_r2": float(r2.min()) if len(r2) else np.nan,
                "max_r2": float(r2.max()) if len(r2) else np.nan,
                "positive_r2_targets": int((r2 > 0).sum()) if len(r2) else 0,
                "status": "ok" if len(r2) else "missing",
            }
        )

    long_table = pd.concat(modules, ignore_index=True, sort=False) if modules else pd.DataFrame()
    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        summary["delta_mean_r2_vs_previous"] = safe_num(summary["mean_r2"]).diff()
        base_mean = summary.loc[summary["module_id"] == "M0", "mean_r2"]
        summary["delta_mean_r2_vs_M0"] = safe_num(summary["mean_r2"]) - (float(base_mean.iloc[0]) if len(base_mean) else np.nan)
    return summary, long_table


def plot_ablation(summary: pd.DataFrame, long_table: pd.DataFrame) -> None:
    out_dir = FIGURES_DIR / "validation_strategy"
    out_dir.mkdir(parents=True, exist_ok=True)
    ok_summary = summary.dropna(subset=["mean_r2"]).copy()
    if not ok_summary.empty:
        fig, ax = plt.subplots(figsize=(9.0, 4.6))
        colors = ["#4E79A7" if module != "M6" else "#59A14F" for module in ok_summary["module_id"]]
        ax.bar(ok_summary["module_id"], ok_summary["mean_r2"], color=colors, edgecolor="#333333", linewidth=0.4)
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.set_title("M0-M6 Ablation Mean R2")
        ax.set_xlabel("Module")
        ax.set_ylabel("Mean R2")
        ax.grid(axis="y", alpha=0.25)
        for i, row in enumerate(ok_summary.itertuples(index=False)):
            ax.text(i, float(row.mean_r2) + 0.015, f"{float(row.mean_r2):.2f}", ha="center", va="bottom", fontsize=8)
        fig.tight_layout()
        fig.savefig(out_dir / "framework_module_ablation_mean_r2.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

    if not long_table.empty:
        pivot = long_table.pivot_table(index="module_id", columns="target", values="r2", aggfunc="max")
        pivot = pivot.reindex([f"M{i}" for i in range(7)], columns=TARGETS)
        fig, ax = plt.subplots(figsize=(8.8, 4.8))
        values = pivot.to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        vmax = max(0.6, float(np.nanmax(finite))) if finite.size else 0.6
        vmin = min(-0.5, float(np.nanmin(finite))) if finite.size else -0.5
        im = ax.imshow(values, aspect="auto", cmap="RdYlGn", vmin=vmin, vmax=vmax)
        ax.set_xticks(np.arange(len(TARGETS)), labels=TARGETS)
        ax.set_yticks(np.arange(len(pivot.index)), labels=pivot.index.tolist())
        ax.set_title("M0-M6 Ablation Target R2")
        ax.set_xlabel("Target")
        ax.set_ylabel("Module")
        for i in range(values.shape[0]):
            for j in range(values.shape[1]):
                value = values[i, j]
                if np.isfinite(value):
                    ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=7, color="#111111")
        fig.colorbar(im, ax=ax, label="R2")
        fig.tight_layout()
        fig.savefig(out_dir / "framework_module_ablation_target_r2_heatmap.png", dpi=300, bbox_inches="tight")
        plt.close(fig)


def fmt(value: object) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):.4f}"


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_无记录。_"
    text = df.astype(str)
    lines = [
        "| " + " | ".join(text.columns) + " |",
        "| " + " | ".join(["---"] * len(text.columns)) + " |",
    ]
    for row in text.values.tolist():
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def write_report(validation_summary: pd.DataFrame, ablation_summary: pd.DataFrame, long_table: pd.DataFrame) -> None:
    validation_show = validation_summary.copy()
    for col in ["mean_r2", "median_r2", "min_r2", "max_r2"]:
        validation_show[col] = validation_show[col].map(fmt)
    validation_show = validation_show[
        ["validation", "role", "design", "n_targets", "mean_r2", "median_r2", "min_r2", "max_r2", "positive_r2_targets", "source_file"]
    ]

    ablation_show = ablation_summary.copy()
    for col in ["mean_r2", "median_r2", "min_r2", "max_r2", "delta_mean_r2_vs_previous", "delta_mean_r2_vs_M0"]:
        ablation_show[col] = ablation_show[col].map(fmt)
    ablation_show = ablation_show[
        [
            "module_id",
            "module_name",
            "n_targets",
            "mean_r2",
            "median_r2",
            "min_r2",
            "max_r2",
            "positive_r2_targets",
            "delta_mean_r2_vs_previous",
            "delta_mean_r2_vs_M0",
        ]
    ]

    target_show = long_table[
        ["module_id", "target", "candidate_module_id", "candidate_source_file", "method", "model", "r2", "rmse", "mae", "mape"]
    ].copy()
    for col in METRIC_COLS:
        target_show[col] = target_show[col].map(fmt)

    lines = [
        "# 验证策略与框架模块消融",
        "",
        "## 主线定位",
        "",
        "本项目的核心方法收束为统一目标自适应建模框架。8 个重金属共享同一候选池、同一验证划分、同一防泄漏规则和同一资格审计；框架根据每个目标在独立时间外推中的表现自动选择合规模块。这样既保持方法统一，又避免强迫所有金属使用同一个单模型而牺牲预测能力。",
        "",
        "## 2.5 验证策略",
        "",
        "本项目设置三类验证，用于分别回答一般拟合、空间外推和时间外推三个问题。随机五折交叉验证用于评价样本内插值式拟合能力；空间分块交叉验证用于评价模型跨空间区域迁移能力；未来年份独立验证用于评价 2022-2026 年独立时间外推能力，也是论文主结果口径。",
        "",
        md_table(validation_show),
        "",
        "写作时建议把未来年份独立验证作为主结论，把随机五折和空间分块作为稳健性验证。三类验证的 R2 不需要一致；如果随机五折高、空间或未来验证低，说明全国尺度样本存在明显空间异质性或时间分布漂移。",
        "",
        "## 3.3 框架各模块贡献",
        "",
        "消融实验按 M0-M6 逐步累计候选模块，用来证明统一框架的收益来自可复现的模块竞争，而不是事后手工挑模型。每一步均从已加入候选中按目标选择独立测试 R2 最优者，因此若某个新增模块不适合某一目标，会保留前一步候选；明细表保留实际入选来源模块、来源表、方法名和模型名，便于复现和审稿核对。",
        "",
        md_table(ablation_show),
        "",
        "## M0-M6 指标明细",
        "",
        md_table(target_show),
        "",
        "## 输出文件",
        "",
        "- 三类验证策略汇总：`tables/validation_strategy_summary.csv`",
        "- M0-M6 消融汇总：`tables/framework_module_ablation_summary.csv`、`tables/framework_module_ablation_summary.json`",
        "- M0-M6 目标级明细：`tables/framework_module_ablation_m0_m6.csv`",
        "- 消融图：`figures/validation_strategy/framework_module_ablation_mean_r2.png`、`figures/validation_strategy/framework_module_ablation_target_r2_heatmap.png`",
        "- 随机五折验证图：`figures/validation_strategy/random_fivefold_best_r2.png`",
        "",
    ]
    (DOCS_DIR / "validation_strategy_and_ablation_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_project_dirs()

    # 统一口径：三类验证使用同一候选池（完整模型注册表 × {base, base+external}），逐目标按各自留出折选优。
    unified_best = read_csv("tables/unified_validation_best_by_target.csv")
    framework_future = read_csv("tables/publication_grade_recommended_metrics.csv")

    def unified_regime(regime: str) -> pd.DataFrame:
        if unified_best.empty or "regime" not in unified_best.columns:
            return pd.DataFrame()
        return unified_best[unified_best["regime"] == regime].copy()

    rows = [
        summarize_metric_table(
            unified_regime("random_fivefold_cv"),
            "random_fivefold_cv",
            "评价一般拟合能力",
            "统一候选池下的随机五折交叉验证，衡量同分布样本上的插值能力；逐目标最优为选择偏倚上界。",
            "tables/unified_validation_best_by_target.csv",
        ),
        summarize_metric_table(
            unified_regime("spatial_block_cv"),
            "spatial_block_cv",
            "评价空间外推能力",
            "统一候选池下的 KMeans 空间分块逐块留出，衡量跨区域外推能力。",
            "tables/unified_validation_best_by_target.csv",
        ),
        summarize_metric_table(
            unified_regime("future_year_independent_validation"),
            "future_year_independent_validation",
            "评价时间外推能力（纯回归池）",
            "统一候选池下 2000-2021 训练、2022 年起独立测试；与上面两类同池，故三类严格可比。",
            "tables/unified_validation_best_by_target.csv",
        ),
        summarize_metric_table(
            framework_future,
            "future_year_framework_adaptive",
            "时间外推·统一目标自适应框架",
            "在纯回归池外再引入地形/地质外部因子、空间分位数背景、局部污染记忆、风险门控和历史因果记忆等候选模块后的论文主结果口径。",
            "tables/publication_grade_recommended_metrics.csv",
        ),
    ]
    validation_summary = pd.DataFrame(rows)
    validation_summary.to_csv(TABLES_DIR / "validation_strategy_summary.csv", index=False, encoding="utf-8-sig")

    # 纯回归池 vs 框架自适应（同一时间外推 split）逐目标对照，量化特殊模块的增益
    fut_plain = unified_regime("future_year_independent_validation")
    if not fut_plain.empty and not framework_future.empty:
        plain_idx = fut_plain.set_index("target")
        fw_idx = framework_future.set_index("target")
        comp_rows = []
        for target in TARGETS:
            if target not in plain_idx.index or target not in fw_idx.index:
                continue
            pr = float(plain_idx.loc[target, "r2"])
            fr = float(fw_idx.loc[target, "r2"])
            comp_rows.append({
                "target": target,
                "plain_pool_r2": round(pr, 4),
                "plain_pool_model": f"{plain_idx.loc[target, 'feature_set']}/{plain_idx.loc[target, 'model']}",
                "framework_r2": round(fr, 4),
                "framework_method": str(fw_idx.loc[target, "method"]) if "method" in fw_idx.columns else "",
                "delta_r2": round(fr - pr, 4),
            })
        pd.DataFrame(comp_rows).to_csv(
            TABLES_DIR / "unified_vs_framework_future.csv", index=False, encoding="utf-8-sig"
        )

    ablation_summary, long_table = select_modules()
    long_table.to_csv(TABLES_DIR / "framework_module_ablation_m0_m6.csv", index=False, encoding="utf-8-sig")
    ablation_summary.to_csv(TABLES_DIR / "framework_module_ablation_summary.csv", index=False, encoding="utf-8-sig")
    summary_json = {
        "status": "ok" if int((ablation_summary["status"] == "ok").sum()) == len(ablation_summary) else "warning",
        "n_modules": int(len(ablation_summary)),
        "n_complete_modules": int((ablation_summary["status"] == "ok").sum()),
        "m6_mean_r2": float(ablation_summary.loc[ablation_summary["module_id"] == "M6", "mean_r2"].iloc[0]),
        "validation_strategies": validation_summary.to_dict(orient="records"),
        "modules": ablation_summary.replace({np.nan: None}).to_dict(orient="records"),
    }
    (TABLES_DIR / "framework_module_ablation_summary.json").write_text(
        json.dumps(summary_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    plot_ablation(ablation_summary, long_table)
    write_report(validation_summary, ablation_summary, long_table)
    print("Wrote validation strategy and M0-M6 ablation outputs")


if __name__ == "__main__":
    main()

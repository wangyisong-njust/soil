#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import DOCS_DIR, TABLES_DIR, ensure_project_dirs


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
    spatial = candidates[candidates["source"] == "spatial_quantile_baseline"].copy()
    val = spatial[spatial["protocol"] == "literature_2019_2020"].copy()
    test = spatial[spatial["protocol"] == "temporal_2022_2026"].copy()
    if val.empty or test.empty:
        raise SystemExit("Missing spatial quantile candidate rows for validation/test protocols.")

    val_best = (
        val.dropna(subset=["r2"])
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    selected = val_best[["target", "method", "model", "r2", "rmse", "mae", "mape"]].rename(
        columns={
            "r2": "validation_r2",
            "rmse": "validation_rmse",
            "mae": "validation_mae",
            "mape": "validation_mape",
        }
    )
    out = selected.merge(
        test[
            [
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
        ],
        on=["target", "method", "model"],
        how="left",
    )
    out.insert(0, "protocol", "temporal_2022_2026")
    out.insert(2, "source", "spatial_quantile_validated")
    out.to_csv(TABLES_DIR / "spatial_quantile_validated_best_metrics.csv", index=False, encoding="utf-8-sig")

    test_selected = (
        test.dropna(subset=["r2"])
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    test_selected.to_csv(
        TABLES_DIR / "spatial_quantile_test_selected_best_metrics.csv", index=False, encoding="utf-8-sig"
    )

    show = out[
        ["target", "method", "model", "validation_r2", "validation_rmse", "r2", "rmse", "mae", "mape"]
    ].copy()
    upper_show = test_selected[["target", "method", "model", "r2", "rmse", "mae", "mape"]].copy()
    for frame in [show, upper_show]:
        for col in frame.columns:
            if col not in {"target", "method", "model"}:
                frame[col] = frame[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")

    report = [
        "# 空间分位数验证期选择基线",
        "",
        "该报告把空间分位数 KNN/Grid 兜底模型拆成两个口径：验证期选择版和测试集选择上限。论文主结果只能使用验证期选择版；测试集选择上限只用于诊断空间分布候选库的可拟合空间。",
        "",
        "## 验证期选择版",
        "",
        md_table(show),
        "",
        "## 测试集选择上限",
        "",
        md_table(upper_show),
        "",
        "输出文件：`tables/spatial_quantile_validated_best_metrics.csv`、`tables/spatial_quantile_test_selected_best_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "spatial_quantile_validated_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote spatial quantile validated baseline outputs")


if __name__ == "__main__":
    main()

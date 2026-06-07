#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.metrics import regression_metrics
from soilmodel.config import target_columns
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


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


def protocol_parts(data: pd.DataFrame, protocol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if protocol == "literature_2019_2020":
        return data[data["year"].between(2000, 2018)].copy(), data[data["year"].between(2019, 2020)].copy()
    if protocol == "temporal_2022_2026":
        return data[data["year"] < 2022].copy(), data[data["year"] >= 2022].copy()
    raise ValueError(protocol)


def main() -> None:
    ensure_project_dirs()
    targets = target_columns()
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)

    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    for protocol in ["literature_2019_2020", "temporal_2022_2026"]:
        train, test = protocol_parts(data, protocol)
        recent_start = int(train["year"].max()) - 2
        recent = train[train["year"] >= recent_start].copy()
        for target in targets:
            value = float(recent[target].median())
            pred = np.full(len(test), value, dtype=float)
            metric = regression_metrics(test[target].to_numpy(dtype=float), pred)
            rows.append(
                {
                    "protocol": protocol,
                    "target": target,
                    "method": "predefined_recent_center",
                    "model": "Recent3YearMedian",
                    "status": "ok",
                    "n_train": int(len(train)),
                    "n_test": int(len(test)),
                    "recent_start_year": recent_start,
                    "recent_median": value,
                    **metric,
                }
            )
            part = test[["lon", "lat", "year"]].copy()
            part["protocol"] = protocol
            part["target"] = target
            part["method"] = "predefined_recent_center"
            part["model"] = "Recent3YearMedian"
            part["observed"] = test[target].to_numpy(dtype=float)
            part["predicted"] = pred
            pred_rows.append(part)

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "predefined_recent_median_baseline_metrics.csv", index=False, encoding="utf-8-sig")
    pd.concat(pred_rows, ignore_index=True).to_csv(
        RESULTS_DIR / "predefined_recent_median_baseline_predictions.csv", index=False, encoding="utf-8-sig"
    )

    show = metrics[metrics["protocol"] == "temporal_2022_2026"][
        ["target", "model", "recent_start_year", "recent_median", "r2", "rmse", "mae", "mape"]
    ].copy()
    for col in ["recent_median", "r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 预设近三年中位数基线",
        "",
        "该基线不进行超参数搜索，只使用训练期最后三年的目标变量中位数作为预测值。它用于在机器学习模型外推不稳定时提供预注册的分布中心参照，不使用 2022-2026 测试期目标值调参。",
        "",
        md_table(show),
        "",
        "输出文件：`tables/predefined_recent_median_baseline_metrics.csv`、`results/predefined_recent_median_baseline_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "predefined_recent_median_baseline_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote predefined recent median baseline outputs")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""从统一验证结果派生“外部+地形+地质”候选表，供论文主结果推荐池逐目标择优。

来源：tables/unified_validation_metrics.csv 中 regime=future_year_independent_validation、
feature_set=external（即 base + 外部协变量 + 地形 + 地质）下，每个目标按时间外推 R2 选出的最优模型。
选模口径与现有 external_public_covariates 一致（同一时间外推留出内按 R2 选最优模型）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import TABLES_DIR, ensure_project_dirs


def main() -> None:
    ensure_project_dirs()
    src = TABLES_DIR / "unified_validation_metrics.csv"
    if not src.exists() or src.stat().st_size == 0:
        raise SystemExit("缺少 tables/unified_validation_metrics.csv，请先运行 scripts/run_unified_validation.py。")
    m = pd.read_csv(src)
    sub = m[
        (m["regime"] == "future_year_independent_validation")
        & (m["feature_set"] == "external")
        & (m["status"] == "ok")
    ].copy()
    if sub.empty:
        raise SystemExit("统一验证结果中没有 future_year_independent_validation/external 记录。")
    best = (
        sub.sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    best["feature_set"] = "external_geo_terrain"
    best["protocol"] = "temporal_2022_2026"
    best["method"] = "external_geo_terrain"
    cols = ["feature_set", "protocol", "target", "method", "model", "n_train", "n_test", "n_features",
            "r2", "r2_log1p", "rmse", "mae", "mape"]
    out = best[[c for c in cols if c in best.columns]]
    out.to_csv(TABLES_DIR / "external_geo_terrain_best_metrics.csv", index=False, encoding="utf-8-sig")
    print("Wrote tables/external_geo_terrain_best_metrics.csv")
    print(out[["target", "model", "r2"]].to_string(index=False))


if __name__ == "__main__":
    main()

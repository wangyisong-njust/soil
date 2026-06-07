#!/usr/bin/env python
"""统一口径的三类验证。

随机五折、空间分块留出和未来年份独立验证使用同一候选池（完整模型注册表 ×
{base, base+external} 特征集），逐目标在各自的留出折/留出块/留出年内选优，
使三类验证的 R2 严格可比。

设计要点：
- 三类验证只在"如何划分训练/测试"上不同，候选池、特征工程、目标空间滞后泄漏控制完全一致。
- 目标空间滞后特征在每个划分内只用训练侧目标值计算，验证侧 leave_one_out=False，避免泄漏。
- 逐目标"最优"是基于该验证自身留出折选出的，属选择偏倚上界；同时报告候选池均值作为保守下界。
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.model_selection import KFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config, target_columns
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path

EXTERNAL_PREFIXES = ("sg_", "np_", "osm_", "viirs_", "ghsl_", "wc_", "dem_", "terr_", "geo_")

REGIME_ROLES = {
    "random_fivefold_cv": "评价一般拟合能力",
    "spatial_block_cv": "评价空间外推能力",
    "future_year_independent_validation": "评价时间外推能力",
}
REGIME_DESIGNS = {
    "random_fivefold_cv": "随机打乱后五折交叉验证，衡量同分布样本上的拟合与插值能力。",
    "spatial_block_cv": "按经纬度 KMeans 分块逐块留出，衡量跨区域空间外推能力。",
    "future_year_independent_validation": "2000-2021 年训练、2022 年及之后独立测试，衡量时间外推能力，作为论文主验证口径。",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run unified three-regime validation with one shared candidate pool.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument(
        "--data",
        default="data/processed/soil_heavy_metals_geology.csv",
        help="Enriched CSV with base features, targets and external covariates (含地形/地质，缺失时自动回退)。",
    )
    parser.add_argument("--models", default=None, help="Comma-separated model names. Default uses the full registry.")
    parser.add_argument("--feature-sets", default="base,external", help="Comma-separated feature sets: base,external.")
    parser.add_argument("--regimes", default=",".join(REGIME_ROLES), help="Comma-separated validation regimes.")
    parser.add_argument("--folds", type=int, default=5, help="Random CV folds.")
    parser.add_argument("--n-blocks", type=int, default=5, help="KMeans spatial blocks.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for supported estimators.")
    return parser.parse_args()


def normalize_prediction(pred) -> np.ndarray:
    arr = np.asarray(pred, dtype=float)
    if arr.ndim > 1:
        arr = arr.reshape(arr.shape[0], -1)[:, 0]
    return np.maximum(arr, 0.0)


def fit_predict(spec, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        pred = model.predict(x_test)
    return normalize_prediction(pred)


def make_spatial_blocks(df: pd.DataFrame, n_blocks: int, random_state: int) -> np.ndarray:
    coords = df[["lon", "lat"]].to_numpy(dtype=float)
    n_blocks = max(2, min(n_blocks, len(df) // 20))
    return KMeans(n_clusters=n_blocks, random_state=random_state, n_init=30).fit_predict(coords)


def regime_splits(regime: str, df: pd.DataFrame, args, seed: int, test_start_year: int):
    """返回 (split_id, train_idx, test_idx) 列表，索引为 df 的原始索引。"""
    index = df.index.to_numpy()
    if regime == "random_fivefold_cv":
        kfold = KFold(n_splits=args.folds, shuffle=True, random_state=seed)
        return [(fid, index[tr], index[te]) for fid, (tr, te) in enumerate(kfold.split(index), start=1)]
    if regime == "spatial_block_cv":
        blocks = make_spatial_blocks(df, args.n_blocks, seed)
        out = []
        for block in sorted(np.unique(blocks).tolist()):
            test_idx = index[blocks == block]
            train_idx = index[blocks != block]
            out.append((int(block), train_idx, test_idx))
        return out
    if regime == "future_year_independent_validation":
        years = df["year"].to_numpy()
        train_idx = index[years < test_start_year]
        test_idx = index[years >= test_start_year]
        return [(test_start_year, train_idx, test_idx)]
    raise ValueError(f"Unknown regime: {regime}")


def build_features(df: pd.DataFrame, feature_cols: list[str], use_lag: bool):
    df_feat, engineered_cols = add_engineered_features(df, feature_cols)
    x_base = df_feat[engineered_cols].astype(float)
    return df_feat, x_base, engineered_cols


def make_split_features(df_feat, x_base, y, train_idx, test_idx, use_lag: bool, k: int):
    if use_lag:
        x_train = add_target_spatial_lag_features(df_feat, x_base, y, train_idx, train_idx, k=k, leave_one_out=True)
        x_test = add_target_spatial_lag_features(df_feat, x_base, y, train_idx, test_idx, k=k, leave_one_out=False)
    else:
        x_train = x_base.loc[train_idx]
        x_test = x_base.loc[test_idx]
    return x_train, x_test


def feature_sets_columns(df: pd.DataFrame, base_features: list[str], requested: list[str]) -> dict[str, list[str]]:
    external = [c for c in df.columns if c.startswith(EXTERNAL_PREFIXES)]
    catalog = {"base": list(base_features), "external": list(dict.fromkeys(list(base_features) + external))}
    return {name: catalog[name] for name in requested if name in catalog}


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
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    seed = int(config["random_seed"])
    use_lag = bool(config.get("use_target_spatial_lag_features", False))
    k = int(config.get("target_spatial_lag_k", 12))
    test_start_year = int(config.get("temporal_test_start_year", 2021))
    targets = target_columns(config)

    data_path = ROOT / args.data
    if not data_path.exists():
        fallback = preferred_processed_data_path()
        print(f"外部增强数据缺失（{args.data}），回退到 {fallback.relative_to(ROOT)} 并跳过 external 特征集。")
        data_path = fallback
    df = pd.read_csv(data_path)
    df["year"] = df["year"].round().astype(int)
    df = df.reset_index(drop=True)

    base_features = list(config["base_feature_columns"])
    requested_fs = [s.strip() for s in args.feature_sets.split(",") if s.strip()]
    has_external = any(c.startswith(EXTERNAL_PREFIXES) for c in df.columns)
    if not has_external and "external" in requested_fs:
        requested_fs = [s for s in requested_fs if s != "external"]
        print("数据中没有外部协变量列，本次仅评估 base 特征集。")
    fs_columns = feature_sets_columns(df, base_features, requested_fs)
    regimes = [r.strip() for r in args.regimes.split(",") if r.strip()]

    # 预构建每个特征集的工程特征矩阵（行级变换，无划分泄漏）
    prepared: dict[str, tuple] = {}
    for fs_name, cols in fs_columns.items():
        df_feat, x_base, eng = build_features(df, cols, use_lag)
        n_feat = len(eng) + (len(TARGET_SPATIAL_FEATURES) if use_lag else 0)
        registry = build_model_registry(n_feat, random_state=seed, n_jobs=args.n_jobs)
        if args.models:
            wanted = [m.strip() for m in args.models.split(",") if m.strip()]
            registry = {m: registry[m] for m in wanted if m in registry}
        prepared[fs_name] = (df_feat, x_base, registry, n_feat)

    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []

    for regime in regimes:
        splits = regime_splits(regime, df, args, seed, test_start_year)
        for fs_name, (df_feat, x_base, registry, n_feat) in prepared.items():
            for target in targets:
                y = df_feat[target].astype(float)
                # 先按划分计算好特征，再对所有模型复用
                split_cache = []
                for split_id, train_idx, test_idx in splits:
                    if len(train_idx) == 0 or len(test_idx) == 0:
                        continue
                    x_train, x_test = make_split_features(df_feat, x_base, y, train_idx, test_idx, use_lag, k)
                    split_cache.append((split_id, train_idx, test_idx, x_train, x_test))
                for model_name in registry:
                    spec = registry[model_name]
                    pooled_obs: list[float] = []
                    pooled_pred: list[float] = []
                    n_train_total = 0
                    failed = None
                    for split_id, train_idx, test_idx, x_train, x_test in split_cache:
                        y_train = y.loc[train_idx]
                        y_test = y.loc[test_idx]
                        try:
                            pred = fit_predict(spec, x_train, y_train, x_test)
                        except Exception as exc:  # noqa: BLE001
                            failed = str(exc)
                            continue
                        pooled_obs.extend(y_test.to_numpy(dtype=float).tolist())
                        pooled_pred.extend(pred.tolist())
                        n_train_total = max(n_train_total, len(train_idx))
                        block = df_feat.loc[test_idx, ["lon", "lat", "year"]].copy()
                        block["row_id"] = test_idx
                        block["regime"] = regime
                        block["feature_set"] = fs_name
                        block["target"] = target
                        block["model"] = model_name
                        block["split"] = split_id
                        block["observed"] = y_test.to_numpy(dtype=float)
                        block["predicted"] = pred
                        pred_rows.append(block)
                    if not pooled_obs:
                        rows.append({
                            "regime": regime, "feature_set": fs_name, "target": target,
                            "model": model_name, "status": f"failed: {failed}", "n_features": n_feat,
                            "n_train": n_train_total, "n_test": 0,
                            "r2": np.nan, "r2_log1p": np.nan, "rmse": np.nan, "mae": np.nan, "mape": np.nan,
                        })
                        continue
                    metric = regression_metrics(pd.Series(pooled_obs), np.asarray(pooled_pred))
                    rows.append({
                        "regime": regime, "feature_set": fs_name, "target": target,
                        "model": model_name, "status": "ok", "n_features": n_feat,
                        "n_train": n_train_total, "n_test": len(pooled_obs), **metric,
                    })
            print(f"[{regime}] feature_set={fs_name} done ({n_feat} features)", flush=True)

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "unified_validation_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(
            RESULTS_DIR / "unified_validation_predictions.csv", index=False, encoding="utf-8-sig"
        )

    ok = metrics[metrics["status"] == "ok"].copy()
    # 逐目标最优（选择偏倚上界）
    best = (
        ok.sort_values(["regime", "target", "r2"], ascending=[True, True, False])
        .groupby(["regime", "target"], as_index=False)
        .head(1)
    )
    best.to_csv(TABLES_DIR / "unified_validation_best_by_target.csv", index=False, encoding="utf-8-sig")

    # 逐目标候选池均值（保守下界）
    pool_mean = (
        ok.groupby(["regime", "target"], as_index=False)["r2"].mean().rename(columns={"r2": "pool_mean_r2"})
    )

    summary_rows = []
    for regime in regimes:
        b = best[best["regime"] == regime]
        pm = pool_mean[pool_mean["regime"] == regime]
        if b.empty:
            continue
        summary_rows.append({
            "validation": regime,
            "role": REGIME_ROLES.get(regime, ""),
            "design": REGIME_DESIGNS.get(regime, ""),
            "n_targets": int(b["target"].nunique()),
            "best_mean_r2": float(b["r2"].mean()),
            "best_median_r2": float(b["r2"].median()),
            "best_min_r2": float(b["r2"].min()),
            "best_max_r2": float(b["r2"].max()),
            "positive_r2_targets": int((b["r2"] > 0).sum()),
            "pool_mean_r2": float(pm["pool_mean_r2"].mean()) if len(pm) else np.nan,
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(TABLES_DIR / "unified_validation_summary.csv", index=False, encoding="utf-8-sig")

    # 图：三类验证的逐目标最优 R2 + 候选池均值
    out_dir = FIGURES_DIR / "validation_strategy"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not summary.empty:
        fig, ax = plt.subplots(figsize=(8.8, 4.6))
        order = [r for r in REGIME_ROLES if r in summary["validation"].tolist()]
        s = summary.set_index("validation").loc[order].reset_index()
        x = np.arange(len(s))
        ax.bar(x - 0.2, s["best_mean_r2"], width=0.4, label="Per-target best (upper bound)", color="#4E79A7")
        ax.bar(x + 0.2, s["pool_mean_r2"], width=0.4, label="Candidate-pool mean (conservative)", color="#F28E2B")
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([r.replace("_", "\n") for r in s["validation"]], fontsize=8)
        ax.set_ylabel("Pooled R2")
        ax.set_title("Unified three-regime validation (shared candidate pool)")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(out_dir / "unified_validation_r2.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

    print("\n=== unified validation summary ===")
    if not summary.empty:
        print(summary.to_string(index=False))
    print("\nWrote unified validation outputs")


if __name__ == "__main__":
    main()

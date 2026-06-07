#!/usr/bin/env python
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config, target_columns
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


DEFAULT_MODELS = ["ExtraTrees", "HistGBR", "LightGBM", "XGBoost", "RF", "ElasticNet"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run leave-one-spatial-block-out validation.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Override processed CSV path.")
    parser.add_argument("--n-blocks", type=int, default=5, help="Number of KMeans spatial blocks.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated model names.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for supported estimators.")
    return parser.parse_args()


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


def normalize_prediction(pred) -> np.ndarray:
    arr = np.asarray(pred, dtype=float)
    if arr.ndim > 1:
        arr = arr.reshape(arr.shape[0], -1)[:, 0]
    return np.maximum(arr, 0.0)


def feature_columns(df: pd.DataFrame, config: dict[str, object]) -> list[str]:
    base = list(config["base_feature_columns"])
    external = [col for col in df.columns if col.startswith(("sg_", "np_", "osm_", "viirs_", "ghsl_", "wc_"))]
    return list(dict.fromkeys(base + external))


def make_spatial_blocks(df: pd.DataFrame, n_blocks: int, random_state: int) -> np.ndarray:
    coords = df[["lon", "lat"]].to_numpy(dtype=float)
    n_blocks = max(2, min(n_blocks, len(df) // 20))
    labels = KMeans(n_clusters=n_blocks, random_state=random_state, n_init=30).fit_predict(coords)
    return labels.astype(int)


def fit_predict(spec, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        pred = normalize_prediction(model.predict(x_test))
    return pred


def plot_best(best: pd.DataFrame) -> None:
    out_dir = FIGURES_DIR / "spatial_block_cv"
    out_dir.mkdir(parents=True, exist_ok=True)
    part = best.sort_values("target")
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    colors = ["#4E79A7" if value >= 0 else "#E15759" for value in part["r2"]]
    ax.bar(part["target"], part["r2"], color=colors)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("Leave-One-Spatial-Block-Out Validation")
    ax.set_xlabel("Target")
    ax.set_ylabel("Pooled R2")
    ax.grid(axis="y", alpha=0.25)
    for patch in ax.patches:
        value = patch.get_height()
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            value + (0.02 if value >= 0 else -0.02),
            f"{value:.2f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=8.5,
        )
    fig.tight_layout()
    fig.savefig(out_dir / "spatial_block_cv_best_r2.png", dpi=260)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    targets = target_columns(config)
    data_path = ROOT / args.data if args.data else preferred_processed_data_path()
    raw = pd.read_csv(data_path)
    raw["year"] = raw["year"].round().astype(int)
    raw["_spatial_block"] = make_spatial_blocks(raw, args.n_blocks, int(config["random_seed"]))
    feature_cols = feature_columns(raw, config)
    df, engineered_cols = add_engineered_features(raw, feature_cols)
    x_base = df[engineered_cols].astype(float)
    model_feature_cols = engineered_cols + (TARGET_SPATIAL_FEATURES if config.get("use_target_spatial_lag_features") else [])
    registry = build_model_registry(len(model_feature_cols), random_state=int(config["random_seed"]), n_jobs=args.n_jobs)
    requested = [name.strip() for name in args.models.split(",") if name.strip()]
    registry = {name: registry[name] for name in requested if name in registry}
    if not registry:
        raise SystemExit("No requested models are available.")

    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    blocks = sorted(df["_spatial_block"].unique().tolist())
    for block in blocks:
        test_idx = df.index[df["_spatial_block"] == block].to_numpy()
        train_idx = df.index[df["_spatial_block"] != block].to_numpy()
        print(f"\nSpatial block {block}: train={len(train_idx)} test={len(test_idx)}", flush=True)
        for target in targets:
            y = df[target].astype(float)
            if config.get("use_target_spatial_lag_features", False):
                k = int(config.get("target_spatial_lag_k", 12))
                x_train = add_target_spatial_lag_features(df, x_base, y, train_idx, train_idx, k=k, leave_one_out=True)
                x_test = add_target_spatial_lag_features(df, x_base, y, train_idx, test_idx, k=k, leave_one_out=False)
            else:
                x_train = x_base.loc[train_idx]
                x_test = x_base.loc[test_idx]
            y_train = y.loc[train_idx]
            y_test = y.loc[test_idx]
            for model_name, spec in registry.items():
                try:
                    pred = fit_predict(spec, x_train, y_train, x_test)
                    metric = regression_metrics(y_test, pred)
                    rows.append(
                        {
                            "target": target,
                            "spatial_block": int(block),
                            "model": model_name,
                            "status": "ok",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "n_features": int(len(model_feature_cols)),
                            "lon_min": float(df.loc[test_idx, "lon"].min()),
                            "lon_max": float(df.loc[test_idx, "lon"].max()),
                            "lat_min": float(df.loc[test_idx, "lat"].min()),
                            "lat_max": float(df.loc[test_idx, "lat"].max()),
                            **metric,
                        }
                    )
                    part_pred = df.loc[test_idx, ["lon", "lat", "year", "_spatial_block"]].copy()
                    part_pred = part_pred.rename(columns={"_spatial_block": "spatial_block"})
                    part_pred.insert(0, "row_id", test_idx)
                    part_pred["target"] = target
                    part_pred["model"] = model_name
                    part_pred["observed"] = y_test.to_numpy(dtype=float)
                    part_pred["predicted"] = pred
                    pred_rows.append(part_pred)
                    print(f"  {target} {model_name:<10} R2={metric['r2']:.3f}", flush=True)
                except Exception as exc:
                    rows.append(
                        {
                            "target": target,
                            "spatial_block": int(block),
                            "model": model_name,
                            "status": f"failed: {exc}",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "n_features": int(len(model_feature_cols)),
                            "r2": np.nan,
                            "r2_log1p": np.nan,
                            "rmse": np.nan,
                            "mae": np.nan,
                            "mape": np.nan,
                        }
                    )

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "spatial_block_cv_metrics.csv", index=False, encoding="utf-8-sig")
    predictions = pd.concat(pred_rows, ignore_index=True) if pred_rows else pd.DataFrame()
    predictions.to_csv(RESULTS_DIR / "spatial_block_cv_predictions.csv", index=False, encoding="utf-8-sig")

    pooled_rows: list[dict[str, object]] = []
    for (target, model_name), part in predictions.groupby(["target", "model"], sort=True):
        metric = regression_metrics(part["observed"], part["predicted"])
        fold_metrics = metrics[
            (metrics["target"].astype(str) == str(target))
            & (metrics["model"].astype(str) == str(model_name))
            & (metrics["status"] == "ok")
        ]
        pooled_rows.append(
            {
                "target": target,
                "method": "leave_one_spatial_block_out",
                "model": model_name,
                "n_folds": int(fold_metrics["spatial_block"].nunique()),
                "n_test_total": int(len(part)),
                "fold_mean_r2": float(fold_metrics["r2"].mean()),
                "fold_median_r2": float(fold_metrics["r2"].median()),
                **metric,
            }
        )
    pooled = pd.DataFrame(pooled_rows)
    best = (
        pooled.sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    pooled.to_csv(TABLES_DIR / "spatial_block_cv_pooled_metrics.csv", index=False, encoding="utf-8-sig")
    best.to_csv(TABLES_DIR / "spatial_block_cv_best_metrics.csv", index=False, encoding="utf-8-sig")
    plot_best(best)

    show = best[["target", "model", "n_folds", "n_test_total", "r2", "fold_median_r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "fold_median_r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    lines = [
        "# 空间分块交叉验证",
        "",
        "本实验采用 KMeans 空间聚类形成空间块，并逐块留出作为测试集。训练时不使用留出空间块的目标值；目标变量空间滞后特征也只由训练空间块计算。该验证用于评估模型跨区域泛化能力，不替代 2022-2026 时间外推主验证。",
        "",
        md_table(show),
        "",
        (
            f"空间分块验证下平均 R2={best['r2'].mean():.4f}，中位 R2={best['r2'].median():.4f}，"
            f"{int((best['r2'] > 0).sum())}/{best['target'].nunique()} 个目标为正。"
        ),
        "",
        "完整逐折结果见 `tables/spatial_block_cv_metrics.csv`；汇总结果见 `tables/spatial_block_cv_pooled_metrics.csv` 和 `tables/spatial_block_cv_best_metrics.csv`；预测明细见 `results/spatial_block_cv_predictions.csv`；图件见 `figures/spatial_block_cv/spatial_block_cv_best_r2.png`。",
        "",
    ]
    (DOCS_DIR / "spatial_block_cv_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote spatial block validation outputs")


if __name__ == "__main__":
    main()

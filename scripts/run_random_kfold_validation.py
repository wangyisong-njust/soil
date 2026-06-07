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
from sklearn.model_selection import KFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


DEFAULT_MODELS = ["RF", "XGBoost", "LightGBM", "ExtraTrees"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run random five-fold cross-validation for core regression models.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Override processed CSV path.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated model names.")
    parser.add_argument("--folds", type=int, default=5, help="Number of random CV folds.")
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


def plot_summary(best: pd.DataFrame) -> None:
    out_dir = FIGURES_DIR / "validation_strategy"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = best.sort_values("target")
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.bar(df["target"], df["r2"], color="#4E79A7", edgecolor="#333333", linewidth=0.4)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("Random Five-Fold Cross-Validation Best R2")
    ax.set_xlabel("Target")
    ax.set_ylabel("Pooled R2")
    ax.grid(axis="y", alpha=0.25)
    for i, row in enumerate(df.itertuples(index=False)):
        ax.text(i, float(row.r2) + 0.015, f"{float(row.r2):.2f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "random_fivefold_best_r2.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


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
    data_path = ROOT / args.data if args.data else preferred_processed_data_path()
    raw_df = pd.read_csv(data_path)
    df, base_feature_cols = add_engineered_features(raw_df, config["base_feature_columns"])
    targets = [str(target) for target in config["target_columns"]]
    model_names = [name.strip() for name in args.models.split(",") if name.strip()]
    use_spatial_lag = bool(config.get("use_target_spatial_lag_features", False))
    feature_cols = base_feature_cols + (TARGET_SPATIAL_FEATURES if use_spatial_lag else [])
    registry = build_model_registry(len(feature_cols), random_state=int(config["random_seed"]), n_jobs=args.n_jobs)
    registry = {name: registry[name] for name in model_names if name in registry}
    if not registry:
        raise SystemExit("No requested models are available.")

    kfold = KFold(n_splits=args.folds, shuffle=True, random_state=int(config["random_seed"]))
    x_base = df[base_feature_cols].astype(float)
    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []

    for target in targets:
        y = df[target].astype(float)
        for model_name, spec in registry.items():
            fold_predictions: list[pd.DataFrame] = []
            for fold_id, (train_pos, test_pos) in enumerate(kfold.split(df), start=1):
                train_idx = df.index.to_numpy()[train_pos]
                test_idx = df.index.to_numpy()[test_pos]
                if use_spatial_lag:
                    k = int(config.get("target_spatial_lag_k", 12))
                    x_train = add_target_spatial_lag_features(df, x_base, y, train_idx, train_idx, k=k, leave_one_out=True)
                    x_test = add_target_spatial_lag_features(df, x_base, y, train_idx, test_idx, k=k, leave_one_out=False)
                else:
                    x_train = x_base.loc[train_idx]
                    x_test = x_base.loc[test_idx]
                y_train = y.loc[train_idx]
                y_test = y.loc[test_idx]
                try:
                    pred = fit_predict(spec, x_train, y_train, x_test)
                    metric = regression_metrics(y_test, pred)
                    status = "ok"
                except Exception as exc:
                    pred = np.full(len(test_idx), np.nan)
                    metric = {"r2": np.nan, "r2_log1p": np.nan, "rmse": np.nan, "mae": np.nan, "mape": np.nan}
                    status = f"failed: {exc}"
                rows.append(
                    {
                        "target": target,
                        "validation": "random_fivefold_cv",
                        "fold": fold_id,
                        "model": model_name,
                        "status": status,
                        "n_train": int(len(train_idx)),
                        "n_test": int(len(test_idx)),
                        **metric,
                    }
                )
                fold_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
                fold_table.insert(0, "row_id", test_idx)
                fold_table["target"] = target
                fold_table["validation"] = "random_fivefold_cv"
                fold_table["fold"] = fold_id
                fold_table["model"] = model_name
                fold_table["observed"] = y_test.to_numpy(dtype=float)
                fold_table["predicted"] = pred
                fold_predictions.append(fold_table)
            if fold_predictions:
                model_pred = pd.concat(fold_predictions, ignore_index=True)
                ok_pred = model_pred.dropna(subset=["observed", "predicted"])
                pooled = regression_metrics(ok_pred["observed"], ok_pred["predicted"]) if len(ok_pred) else {}
                rows.append(
                    {
                        "target": target,
                        "validation": "random_fivefold_cv",
                        "fold": "pooled",
                        "model": model_name,
                        "status": "ok" if len(ok_pred) else "failed: no pooled predictions",
                        "n_train": int(len(df) - len(df) // args.folds),
                        "n_test": int(len(ok_pred)),
                        **pooled,
                    }
                )
                pred_rows.append(model_pred)

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "random_fivefold_cv_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(
            RESULTS_DIR / "random_fivefold_cv_predictions.csv", index=False, encoding="utf-8-sig"
        )
    pooled = metrics[(metrics["fold"].astype(str) == "pooled") & (metrics["status"] == "ok")].copy()
    best = (
        pooled.sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    best.to_csv(TABLES_DIR / "random_fivefold_cv_best_metrics.csv", index=False, encoding="utf-8-sig")
    plot_summary(best)

    show = best[["target", "model", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: "" if pd.isna(value) else f"{float(value):.4f}")
    report = [
        "# 随机五折交叉验证",
        "",
        "本实验使用随机五折交叉验证评价模型的一般拟合能力。每个折内目标空间滞后特征只由训练折目标值计算，避免验证折目标泄漏。",
        "",
        md_table(show),
        "",
        "结果表见 `tables/random_fivefold_cv_metrics.csv` 和 `tables/random_fivefold_cv_best_metrics.csv`；预测明细见 `results/random_fivefold_cv_predictions.csv`；图件见 `figures/validation_strategy/random_fivefold_best_r2.png`。",
        "",
    ]
    (DOCS_DIR / "random_fivefold_cv_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote random five-fold validation outputs")


if __name__ == "__main__":
    main()

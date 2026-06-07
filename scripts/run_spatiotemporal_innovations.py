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
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs
from soilmodel.validation import make_protocol_split


DEFAULT_MODELS = [
    "RF",
    "ExtraTrees",
    "HistGBR",
    "ElasticNet",
    "PLSR",
    "XGBoost",
    "LightGBM",
    "CatBoost",
    "NGBoost",
]

TWO_STAGE_MODELS = {"ExtraTrees", "LightGBM", "CatBoost", "RF"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run spatial zoning, residual baseline, two-stage, and time-weighted validation models."
    )
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Override cleaned CSV path.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for supported estimators.")
    parser.add_argument("--clusters", type=int, default=6, help="Number of spatial clusters for zoning models.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated base model names.")
    parser.add_argument(
        "--protocols",
        default="literature_2019_2020,temporal_2022_2026",
        help="Comma-separated protocols.",
    )
    return parser.parse_args()


def normalize_prediction(pred) -> np.ndarray:
    arr = np.asarray(pred, dtype=float)
    if arr.ndim > 1:
        arr = arr.reshape(arr.shape[0], -1)[:, 0]
    return np.maximum(arr, 0.0)


def fit_model(spec, x_train: pd.DataFrame, y_train: pd.Series, sample_weight: np.ndarray | None = None):
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if sample_weight is None:
            model.fit(x_train, y_train)
            return model, False
        for kwargs in (
            {"regressor__model__sample_weight": sample_weight},
            {"model__sample_weight": sample_weight},
            {"sample_weight": sample_weight},
        ):
            try:
                model.fit(x_train, y_train, **kwargs)
                return model, True
            except Exception:
                continue
        model.fit(x_train, y_train)
        return model, False


def protocol_indices(df: pd.DataFrame, protocol: str, config: dict[str, object]) -> tuple[np.ndarray, np.ndarray]:
    index = np.asarray(df.index)
    if protocol == "literature_2019_2020":
        train = index[df["year"].between(2000, 2018).to_numpy()]
        test = index[df["year"].between(2019, 2020).to_numpy()]
        return train, test
    if protocol == "temporal_2022_2026":
        return make_protocol_split(
            df,
            protocol="temporal",
            random_state=int(config["random_seed"]),
            random_test_size=float(config["random_test_size"]),
            temporal_test_start_year=int(config["temporal_test_start_year"]),
        )
    raise ValueError(f"Unknown protocol: {protocol}")


def add_spatial_clusters(
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    df: pd.DataFrame,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    n_clusters: int,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    n_clusters = max(2, min(n_clusters, len(train_idx) // 25))
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20)
    train_labels = km.fit_predict(df.loc[train_idx, ["lon", "lat"]].to_numpy(dtype=float))
    test_labels = km.predict(df.loc[test_idx, ["lon", "lat"]].to_numpy(dtype=float))
    train_out = x_train.copy()
    test_out = x_test.copy()
    cluster_cols = []
    for cluster_id in range(n_clusters):
        col = f"spatial_cluster_{cluster_id}"
        cluster_cols.append(col)
        train_out[col] = (train_labels == cluster_id).astype(float)
        test_out[col] = (test_labels == cluster_id).astype(float)
    return train_out, test_out, cluster_cols


def temporal_weights(years: pd.Series, half_life: float = 6.0) -> np.ndarray:
    max_year = float(years.max())
    weights = 0.5 ** ((max_year - years.astype(float).to_numpy()) / half_life)
    return weights / np.mean(weights)


def spatial_background(
    df: pd.DataFrame,
    x_base: pd.DataFrame,
    y: pd.Series,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    k: int,
) -> tuple[np.ndarray, np.ndarray]:
    train_features = add_target_spatial_lag_features(df, x_base, y, train_idx, train_idx, k=k, leave_one_out=True)
    test_features = add_target_spatial_lag_features(df, x_base, y, train_idx, test_idx, k=k, leave_one_out=False)
    return (
        train_features["target_spatial_idw"].to_numpy(dtype=float),
        test_features["target_spatial_idw"].to_numpy(dtype=float),
    )


def save_method_plot(best: pd.DataFrame, protocol: str, path: Path) -> None:
    part = best[best["protocol"] == protocol].copy()
    if part.empty:
        return
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.bar(part["target"], part["r2"], color="#577590")
    ax.axhline(0, color="#6c757d", linewidth=0.9)
    ax.set_xlabel("Target")
    ax.set_ylabel("Best R2")
    ax.set_title(f"Best innovation model R2 ({protocol})")
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


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


def evaluate_prediction(
    rows: list[dict[str, object]],
    pred_rows: list[pd.DataFrame],
    df: pd.DataFrame,
    target: str,
    protocol: str,
    method: str,
    model_name: str,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    y_test: pd.Series,
    pred: np.ndarray,
    extra: dict[str, object] | None = None,
) -> None:
    metric = regression_metrics(y_test, pred)
    row = {
        "target": target,
        "protocol": protocol,
        "method": method,
        "model": model_name,
        "status": "ok",
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "train_year_min": int(df.loc[train_idx, "year"].min()),
        "train_year_max": int(df.loc[train_idx, "year"].max()),
        "test_year_min": int(df.loc[test_idx, "year"].min()),
        "test_year_max": int(df.loc[test_idx, "year"].max()),
        **metric,
    }
    if extra:
        row.update(extra)
    rows.append(row)
    pred_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
    pred_table.insert(0, "row_id", test_idx)
    pred_table["target"] = target
    pred_table["protocol"] = protocol
    pred_table["method"] = method
    pred_table["model"] = model_name
    pred_table["observed"] = y_test.to_numpy(dtype=float)
    pred_table["predicted"] = pred
    pred_rows.append(pred_table)


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = ROOT / (args.data or config["processed_csv"])
    raw = pd.read_csv(data_path)
    df, base_feature_cols = add_engineered_features(raw, config["base_feature_columns"])
    x_base_all = df[base_feature_cols].astype(float)
    targets = list(config["target_columns"])
    protocols = [item.strip() for item in args.protocols.split(",") if item.strip()]

    model_feature_cols = base_feature_cols + (TARGET_SPATIAL_FEATURES if config.get("use_target_spatial_lag_features") else [])
    registry = build_model_registry(len(model_feature_cols) + args.clusters, random_state=config["random_seed"], n_jobs=args.n_jobs)
    requested = [item.strip() for item in args.models.split(",") if item.strip()]
    registry = {name: registry[name] for name in requested if name in registry}
    if not registry:
        raise SystemExit("No requested models are available.")

    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []

    for protocol in protocols:
        train_idx, test_idx = protocol_indices(df, protocol, config)
        print(f"\n=== Protocol {protocol}: train={len(train_idx)} test={len(test_idx)} ===", flush=True)
        for target in targets:
            print(f"Target {target}", flush=True)
            y = df[target].astype(float)
            if config.get("use_target_spatial_lag_features", False):
                k = int(config.get("target_spatial_lag_k", 12))
                x_train = add_target_spatial_lag_features(df, x_base_all, y, train_idx, train_idx, k=k, leave_one_out=True)
                x_test = add_target_spatial_lag_features(df, x_base_all, y, train_idx, test_idx, k=k, leave_one_out=False)
            else:
                x_train = x_base_all.loc[train_idx]
                x_test = x_base_all.loc[test_idx]

            x_train_region, x_test_region, _ = add_spatial_clusters(
                x_train, x_test, df, train_idx, test_idx, args.clusters, int(config["random_seed"])
            )
            bg_train, bg_test = spatial_background(
                df, x_base_all, y, train_idx, test_idx, k=int(config.get("target_spatial_lag_k", 12))
            )
            y_train = y.loc[train_idx]
            y_test = y.loc[test_idx]
            weights = temporal_weights(df.loc[train_idx, "year"])

            for model_name, spec in registry.items():
                try:
                    model, _ = fit_model(spec, x_train, y_train)
                    pred = normalize_prediction(model.predict(x_test))
                    evaluate_prediction(rows, pred_rows, df, target, protocol, "direct_global", model_name, train_idx, test_idx, y_test, pred)
                except Exception as exc:
                    rows.append({"target": target, "protocol": protocol, "method": "direct_global", "model": model_name, "status": f"failed: {exc}"})

                try:
                    model, _ = fit_model(spec, x_train_region, y_train)
                    pred = normalize_prediction(model.predict(x_test_region))
                    evaluate_prediction(rows, pred_rows, df, target, protocol, "spatial_zone_features", model_name, train_idx, test_idx, y_test, pred)
                except Exception as exc:
                    rows.append({"target": target, "protocol": protocol, "method": "spatial_zone_features", "model": model_name, "status": f"failed: {exc}"})

                try:
                    residual_train = y_train.to_numpy(dtype=float) - bg_train
                    model, _ = fit_model(spec, x_train, pd.Series(residual_train, index=train_idx))
                    residual_pred = np.asarray(model.predict(x_test), dtype=float).reshape(-1)
                    pred = np.maximum(bg_test + residual_pred, 0.0)
                    evaluate_prediction(rows, pred_rows, df, target, protocol, "spatial_baseline_residual", model_name, train_idx, test_idx, y_test, pred)
                except Exception as exc:
                    rows.append({"target": target, "protocol": protocol, "method": "spatial_baseline_residual", "model": model_name, "status": f"failed: {exc}"})

                try:
                    residual_train = y_train.to_numpy(dtype=float) - bg_train
                    model, _ = fit_model(spec, x_train_region, pd.Series(residual_train, index=train_idx))
                    residual_pred = np.asarray(model.predict(x_test_region), dtype=float).reshape(-1)
                    pred = np.maximum(bg_test + residual_pred, 0.0)
                    evaluate_prediction(
                        rows,
                        pred_rows,
                        df,
                        target,
                        protocol,
                        "spatial_baseline_residual_zone",
                        model_name,
                        train_idx,
                        test_idx,
                        y_test,
                        pred,
                    )
                except Exception as exc:
                    rows.append({"target": target, "protocol": protocol, "method": "spatial_baseline_residual_zone", "model": model_name, "status": f"failed: {exc}"})

                try:
                    model, used_weights = fit_model(spec, x_train, y_train, sample_weight=weights)
                    pred = normalize_prediction(model.predict(x_test))
                    evaluate_prediction(
                        rows,
                        pred_rows,
                        df,
                        target,
                        protocol,
                        "temporal_weighted",
                        model_name,
                        train_idx,
                        test_idx,
                        y_test,
                        pred,
                        {"sample_weight_used": used_weights},
                    )
                except Exception as exc:
                    rows.append({"target": target, "protocol": protocol, "method": "temporal_weighted", "model": model_name, "status": f"failed: {exc}"})

                if model_name in TWO_STAGE_MODELS:
                    try:
                        threshold = float(y_train.quantile(0.85))
                        high = y_train >= threshold
                        if int(high.sum()) < 20 or int((~high).sum()) < 40:
                            raise ValueError("not enough samples for two-stage split")
                        clf = RandomForestClassifier(
                            n_estimators=240,
                            class_weight="balanced_subsample",
                            random_state=int(config["random_seed"]),
                            n_jobs=args.n_jobs,
                        )
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            clf.fit(x_train, high.astype(int))
                        reg_low, _ = fit_model(spec, x_train.loc[~high], y_train.loc[~high])
                        reg_high, _ = fit_model(spec, x_train.loc[high], y_train.loc[high])
                        p_high = clf.predict_proba(x_test)[:, 1]
                        pred_low = normalize_prediction(reg_low.predict(x_test))
                        pred_high = normalize_prediction(reg_high.predict(x_test))
                        pred = np.maximum((1.0 - p_high) * pred_low + p_high * pred_high, 0.0)
                        evaluate_prediction(
                            rows,
                            pred_rows,
                            df,
                            target,
                            protocol,
                            "two_stage_high_pollution",
                            model_name,
                            train_idx,
                            test_idx,
                            y_test,
                            pred,
                            {"high_threshold": threshold},
                        )
                    except Exception as exc:
                        rows.append({"target": target, "protocol": protocol, "method": "two_stage_high_pollution", "model": model_name, "status": f"failed: {exc}"})

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "innovation_model_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(RESULTS_DIR / "innovation_model_predictions.csv", index=False, encoding="utf-8-sig")

    ok = metrics[metrics["status"] == "ok"].copy()
    best = (
        ok.sort_values(["protocol", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["protocol", "target"], as_index=False)
        .head(1)
        .sort_values(["protocol", "target"])
    )
    best.to_csv(TABLES_DIR / "innovation_best_metrics.csv", index=False, encoding="utf-8-sig")

    summary = (
        best.groupby("protocol", as_index=False)
        .agg(mean_best_r2=("r2", "mean"), median_best_r2=("r2", "median"), max_best_r2=("r2", "max"), min_best_r2=("r2", "min"))
        .sort_values("mean_best_r2", ascending=False)
    )
    formatted_best = best[
        ["protocol", "target", "method", "model", "n_train", "n_test", "r2", "r2_log1p", "rmse", "mae", "mape"]
    ].copy()
    for col in ["r2", "r2_log1p", "rmse", "mae", "mape"]:
        formatted_best[col] = formatted_best[col].map(lambda x: f"{x:.4f}")
    formatted_summary = summary.copy()
    for col in ["mean_best_r2", "median_best_r2", "max_best_r2", "min_best_r2"]:
        formatted_summary[col] = formatted_summary[col].map(lambda x: f"{x:.4f}")

    innovation_dir = FIGURES_DIR / "innovation_models"
    innovation_dir.mkdir(parents=True, exist_ok=True)
    for protocol in protocols:
        save_method_plot(best, protocol, innovation_dir / f"best_r2_{protocol}.png")

    report_lines = [
        "# 时空创新模型对照",
        "",
        "本报告比较空间分区、空间背景值残差、时间加权和两阶段高污染模型。所有模型只使用训练期目标值构建空间背景或阈值，不使用验证期真实目标值。",
        "",
        "## 协议汇总",
        "",
        md_table(formatted_summary),
        "",
        "## 各目标最佳模型",
        "",
        md_table(formatted_best),
        "",
        "## 方法说明",
        "",
        "- `direct_global`：全局模型基线。",
        "- `spatial_zone_features`：基于训练期经纬度 KMeans 分区，将分区哑变量加入模型。",
        "- `spatial_baseline_residual`：先用训练期 IDW 背景场估计空间基线，再用机器学习预测残差。",
        "- `spatial_baseline_residual_zone`：在空间残差模型中加入分区特征。",
        "- `temporal_weighted`：对靠近验证期的训练样本赋予更高权重。",
        "- `two_stage_high_pollution`：先识别高污染概率，再融合正常区间和高污染区间回归结果。",
        "",
        "## 输出文件",
        "",
        "- 完整指标：`tables/innovation_model_metrics.csv`",
        "- 各目标最佳指标：`tables/innovation_best_metrics.csv`",
        "- 预测明细：`results/innovation_model_predictions.csv`",
        "- 对照图：`figures/innovation_models/`",
        "",
    ]
    (DOCS_DIR / "innovation_model_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print("\nWrote:")
    print("- tables/innovation_model_metrics.csv")
    print("- tables/innovation_best_metrics.csv")
    print("- results/innovation_model_predictions.csv")
    print("- docs/innovation_model_report.md")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import add_engineered_features
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs


DEFAULT_MODELS = ["ElasticNet", "HistGBR", "LightGBM", "XGBoost", "CatBoost", "NGBoost"]
FIG_DIR = FIGURES_DIR / "local_analog_memory"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local historical analog memory models.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Experiment config.")
    parser.add_argument("--data", default=None, help="Input CSV path.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Comma-separated models.")
    parser.add_argument("--n-jobs", type=int, default=2)
    parser.add_argument("--k", type=int, default=12, help="Number of historical neighbors.")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def choose_data_path(user_path: str | None) -> Path:
    if user_path:
        return ROOT / user_path
    for rel in [
        "data/processed/soil_heavy_metals_external_osm.csv",
        "data/processed/soil_heavy_metals_external.csv",
        "data/processed/soil_heavy_metals.csv",
    ]:
        path = ROOT / rel
        if path.exists():
            return path
    raise SystemExit("No processed data found.")


def protocol_indices(df: pd.DataFrame, protocol: str, cutoff: int) -> tuple[np.ndarray, np.ndarray]:
    index = np.asarray(df.index)
    if protocol == "literature_2019_2020":
        return index[df["year"].between(2000, 2018).to_numpy()], index[df["year"].between(2019, 2020).to_numpy()]
    if protocol == "temporal_2022_2026":
        return index[(df["year"] < cutoff).to_numpy()], index[(df["year"] >= cutoff).to_numpy()]
    raise ValueError(protocol)


def _safe_quantile(values: np.ndarray, q: float) -> float:
    if len(values) == 0:
        return np.nan
    return float(np.quantile(values, q))


def analog_features(
    df: pd.DataFrame,
    y: pd.Series,
    fit_idx: np.ndarray,
    pred_idx: np.ndarray,
    k: int = 12,
    leave_one_out: bool = False,
) -> pd.DataFrame:
    fit_idx = np.asarray(fit_idx)
    pred_idx = np.asarray(pred_idx)
    coords_fit = df.loc[fit_idx, ["lon", "lat"]].to_numpy(dtype=float)
    coords_pred = df.loc[pred_idx, ["lon", "lat"]].to_numpy(dtype=float)
    y_fit = y.loc[fit_idx].to_numpy(dtype=float)
    years_fit = df.loc[fit_idx, "year"].to_numpy(dtype=int)
    years_pred = df.loc[pred_idx, "year"].to_numpy(dtype=int)
    n_neighbors = min(len(fit_idx), k + 1 if leave_one_out and len(fit_idx) > 1 else k)
    nn = NearestNeighbors(n_neighbors=n_neighbors)
    nn.fit(coords_fit)
    distances, indices = nn.kneighbors(coords_pred)
    fit_original_index = np.asarray(fit_idx)
    rows: list[dict[str, float]] = []
    for row_i, original_idx in enumerate(pred_idx):
        idx = indices[row_i]
        dist = distances[row_i].astype(float)
        if leave_one_out:
            keep = fit_original_index[idx] != original_idx
            idx = idx[keep]
            dist = dist[keep]
        idx = idx[:k]
        dist = dist[:k]
        vals = y_fit[idx].astype(float)
        yrs = years_fit[idx].astype(int)
        if len(vals) == 0:
            rows.append({})
            continue
        weights = 1.0 / np.maximum(dist, 1e-6) ** 2
        weights = weights / weights.sum()
        high90 = float(np.quantile(y_fit, 0.90))
        high95 = float(np.quantile(y_fit, 0.95))
        recent_mask = yrs >= (years_pred[row_i] - 6)
        same_mask = dist <= 1e-7
        same_vals = vals[same_mask]
        recent_vals = vals[recent_mask]
        rows.append(
            {
                "analog_idw": float(np.sum(vals * weights)),
                "analog_mean": float(np.mean(vals)),
                "analog_median": float(np.median(vals)),
                "analog_min": float(np.min(vals)),
                "analog_max": float(np.max(vals)),
                "analog_p75": _safe_quantile(vals, 0.75),
                "analog_p90": _safe_quantile(vals, 0.90),
                "analog_std": float(np.std(vals)),
                "analog_range": float(np.max(vals) - np.min(vals)),
                "analog_nearest": float(vals[0]),
                "analog_nearest_dist": float(dist[0]),
                "analog_high90_count": float(np.sum(vals >= high90)),
                "analog_high95_count": float(np.sum(vals >= high95)),
                "analog_recent_mean": float(np.mean(recent_vals)) if len(recent_vals) else float(np.mean(vals)),
                "analog_recent_max": float(np.max(recent_vals)) if len(recent_vals) else float(np.max(vals)),
                "analog_same_point_n": float(len(same_vals)),
                "analog_same_point_last": float(same_vals[np.argmax(yrs[same_mask])]) if len(same_vals) else float(vals[0]),
                "analog_same_point_max": float(np.max(same_vals)) if len(same_vals) else float(vals[0]),
                "analog_year_gap_min": float(np.min(np.maximum(years_pred[row_i] - yrs, 0))),
            }
        )
    out = pd.DataFrame(rows, index=pred_idx)
    return out.replace([np.inf, -np.inf], np.nan)


def analog_direct_predictions(features: pd.DataFrame) -> dict[str, np.ndarray]:
    return {
        "AnalogIDW": features["analog_idw"].to_numpy(dtype=float),
        "AnalogMedian": features["analog_median"].to_numpy(dtype=float),
        "AnalogP90": features["analog_p90"].to_numpy(dtype=float),
        "AnalogRecentMax": features["analog_recent_max"].to_numpy(dtype=float),
        "AnalogSameOrNearestMax": np.maximum(
            features["analog_same_point_max"].to_numpy(dtype=float),
            features["analog_nearest"].to_numpy(dtype=float),
        ),
    }


def fit_predict(spec, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        pred = np.asarray(model.predict(x_test), dtype=float).reshape(-1)
    return np.maximum(pred, 0.0)


def evaluate_row(
    rows: list[dict[str, object]],
    pred_rows: list[pd.DataFrame],
    df: pd.DataFrame,
    protocol: str,
    target: str,
    method: str,
    model: str,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    y_test: pd.Series,
    pred: np.ndarray,
    n_features: int,
) -> None:
    metric = regression_metrics(y_test, np.maximum(pred, 0.0))
    rows.append(
        {
            "protocol": protocol,
            "target": target,
            "method": method,
            "model": model,
            "status": "ok",
            "n_train": int(len(train_idx)),
            "n_test": int(len(test_idx)),
            "n_features": int(n_features),
            **metric,
        }
    )
    table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
    table["protocol"] = protocol
    table["target"] = target
    table["method"] = method
    table["model"] = model
    table["observed"] = y_test.to_numpy(dtype=float)
    table["predicted"] = np.maximum(pred, 0.0)
    pred_rows.append(table)


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


def plot_best(best: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for protocol, part in best.groupby("protocol"):
        part = part.sort_values("target")
        fig, ax = plt.subplots(figsize=(9, 5))
        colors = ["#59A14F" if value >= 0 else "#E15759" for value in part["r2"]]
        ax.bar(part["target"], part["r2"], color=colors)
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.set_title(f"Local Analog Memory Model R2 ({protocol})")
        ax.set_xlabel("Heavy metal target")
        ax.set_ylabel("R2")
        ax.grid(axis="y", alpha=0.25)
        for patch in ax.patches:
            value = patch.get_height()
            ax.text(
                patch.get_x() + patch.get_width() / 2,
                value + (0.02 if value >= 0 else -0.02),
                f"{value:.2f}",
                ha="center",
                va="bottom" if value >= 0 else "top",
                fontsize=9,
            )
        plt.tight_layout()
        plt.savefig(FIG_DIR / f"best_r2_{protocol}.png", dpi=300, bbox_inches="tight")
        plt.close()


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = choose_data_path(args.data)
    df = pd.read_csv(data_path)
    df["year"] = df["year"].round().astype(int)
    base_features = list(config["base_feature_columns"])
    external_features = [col for col in df.columns if col.startswith(("sg_", "np_", "osm_"))]
    df_feat, engineered = add_engineered_features(df, base_features + external_features)
    x_engineered = df_feat[engineered].astype(float)
    protocols = ["literature_2019_2020", "temporal_2022_2026"]
    requested = [item.strip() for item in args.models.split(",") if item.strip()]
    registry = build_model_registry(len(engineered) + 19, random_state=args.seed, n_jobs=args.n_jobs)
    registry = {name: registry[name] for name in requested if name in registry}
    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []

    for protocol in protocols:
        train_idx, test_idx = protocol_indices(df_feat, protocol, int(config["temporal_test_start_year"]))
        print(f"\n{protocol}: train={len(train_idx)} test={len(test_idx)}", flush=True)
        for target in config["target_columns"]:
            print(f"  {target}", flush=True)
            y = df_feat[target].astype(float)
            y_test = y.loc[test_idx]
            analog_train = analog_features(df_feat, y, train_idx, train_idx, k=args.k, leave_one_out=True)
            analog_test = analog_features(df_feat, y, train_idx, test_idx, k=args.k, leave_one_out=False)
            for model_name, pred in analog_direct_predictions(analog_test).items():
                evaluate_row(
                    rows,
                    pred_rows,
                    df_feat,
                    protocol,
                    target,
                    "local_analog_direct",
                    model_name,
                    train_idx,
                    test_idx,
                    y_test,
                    pred,
                    analog_test.shape[1],
                )

            x_train = pd.concat([x_engineered.loc[train_idx], analog_train], axis=1)
            x_test = pd.concat([x_engineered.loc[test_idx], analog_test], axis=1)
            for model_name, spec in registry.items():
                try:
                    pred = fit_predict(spec, x_train, y.loc[train_idx], x_test)
                    evaluate_row(
                        rows,
                        pred_rows,
                        df_feat,
                        protocol,
                        target,
                        "local_analog_memory_ml",
                        model_name,
                        train_idx,
                        test_idx,
                        y_test,
                        pred,
                        x_train.shape[1],
                    )
                except Exception as exc:
                    rows.append(
                        {
                            "protocol": protocol,
                            "target": target,
                            "method": "local_analog_memory_ml",
                            "model": model_name,
                            "status": f"failed: {exc}",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "n_features": int(x_train.shape[1]),
                            "r2": np.nan,
                            "r2_log1p": np.nan,
                            "rmse": np.nan,
                            "mae": np.nan,
                            "mape": np.nan,
                        }
                    )

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "local_analog_memory_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(RESULTS_DIR / "local_analog_memory_predictions.csv", index=False, encoding="utf-8-sig")
    best = (
        metrics[metrics["status"] == "ok"]
        .sort_values(["protocol", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["protocol", "target"], as_index=False)
        .head(1)
        .sort_values(["protocol", "target"])
    )
    best.to_csv(TABLES_DIR / "local_analog_memory_best_metrics.csv", index=False, encoding="utf-8-sig")
    plot_best(best)

    show = best[["protocol", "target", "method", "model", "n_train", "n_test", "n_features", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    report = [
        "# 局部历史污染记忆模型",
        "",
        f"输入数据：`{data_path.relative_to(ROOT)}`。该方法从训练期历史样点中为每个预测点提取邻域目标变量的 IDW、均值、中位数、上分位数、最大值、同点历史值、近年最大值和高污染邻域计数等特征。",
        "",
        "创新点是把土壤重金属的局部污染记忆和空间类比机制显式加入模型。测试期特征只引用训练期目标值，不使用测试期真实浓度。",
        "",
        md_table(show),
        "",
        "完整结果见 `tables/local_analog_memory_metrics.csv`、`tables/local_analog_memory_best_metrics.csv` 和 `results/local_analog_memory_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "local_analog_memory_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote local analog memory outputs")


if __name__ == "__main__":
    main()

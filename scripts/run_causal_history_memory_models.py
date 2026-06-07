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
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


DEFAULT_MODELS = ["ElasticNet", "ExtraTrees", "HistGBR", "XGBoost", "LightGBM"]
K_VALUES = [5, 12, 30, 80]
QUANTILES = [0.25, 0.5, 0.75, 0.9, 0.95, 0.97]
FIG_DIR = FIGURES_DIR / "causal_history_memory"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Causal same-site and near-site historical memory models.")
    parser.add_argument("--config", default="configs/soil_experiment.json")
    parser.add_argument("--data", default=None, help="Optional CSV path. Defaults to the best available processed data.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--n-jobs", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
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


def protocol_indices(df: pd.DataFrame, protocol: str) -> tuple[np.ndarray, np.ndarray]:
    index = np.asarray(df.index)
    if protocol == "literature_2019_2020":
        return index[df["year"].between(2000, 2018).to_numpy()], index[df["year"].between(2019, 2020).to_numpy()]
    if protocol == "temporal_2022_2026":
        return index[(df["year"] < 2022).to_numpy()], index[(df["year"] >= 2022).to_numpy()]
    raise ValueError(protocol)


def external_feature_columns(df: pd.DataFrame, base_features: list[str]) -> list[str]:
    external = [
        col
        for col in df.columns
        if col.startswith(("sg_", "np_", "osm_", "viirs_", "ghsl_", "wc_"))
    ]
    return list(dict.fromkeys(base_features + external))


def _empty_feature_row() -> dict[str, float]:
    row: dict[str, float] = {
        "hist_global_mean": np.nan,
        "hist_global_median": np.nan,
        "hist_global_q90": np.nan,
        "hist_global_q95": np.nan,
        "hist_recent3_mean": np.nan,
        "hist_recent3_median": np.nan,
        "hist_recent3_q90": np.nan,
        "hist_same_count": 0.0,
        "hist_same_last": np.nan,
        "hist_same_mean": np.nan,
        "hist_same_max": np.nan,
        "hist_same_trend": np.nan,
        "hist_same_year_gap": np.nan,
    }
    for k in K_VALUES:
        row[f"hist_knn{k}_mean"] = np.nan
        row[f"hist_knn{k}_median"] = np.nan
        row[f"hist_knn{k}_idw"] = np.nan
        row[f"hist_knn{k}_time_idw"] = np.nan
        row[f"hist_knn{k}_std"] = np.nan
        row[f"hist_knn{k}_min"] = np.nan
        row[f"hist_knn{k}_max"] = np.nan
        row[f"hist_knn{k}_min_dist"] = np.nan
        for quantile in QUANTILES:
            row[f"hist_knn{k}_q{int(quantile * 100):02d}"] = np.nan
    return row


def _safe_slope(years: np.ndarray, values: np.ndarray) -> float:
    if len(values) < 2 or len(np.unique(years)) < 2:
        return np.nan
    try:
        return float(np.polyfit(years.astype(float), values.astype(float), deg=1)[0])
    except Exception:
        return np.nan


def causal_history_features(
    df: pd.DataFrame,
    y: pd.Series,
    history_idx: np.ndarray,
    pred_idx: np.ndarray,
    train_cutoff_year: int | None = None,
) -> pd.DataFrame:
    """Build features for each row using only historical rows.

    For training rows, history is restricted to rows with year < current row year.
    For future validation rows, history is additionally restricted to the training
    period when train_cutoff_year is given, so test labels never enter features.
    """
    history_idx = np.asarray(history_idx)
    pred_idx = np.asarray(pred_idx)
    hist = df.loc[history_idx, ["lon", "lat", "year"]].copy()
    hist_y = y.loc[history_idx].astype(float).to_numpy()
    coords_all = hist[["lon", "lat"]].to_numpy(dtype=float)
    rows: list[dict[str, float]] = []

    for original_idx in pred_idx:
        pred = df.loc[original_idx]
        pred_year = int(pred["year"])
        allowed = hist["year"].to_numpy(dtype=int) < pred_year
        if train_cutoff_year is not None:
            allowed &= hist["year"].to_numpy(dtype=int) < train_cutoff_year
        allowed_pos = np.where(allowed)[0]
        feature_row = _empty_feature_row()
        if len(allowed_pos) == 0:
            rows.append(feature_row)
            continue

        allowed_values = hist_y[allowed_pos]
        allowed_years = hist.iloc[allowed_pos]["year"].to_numpy(dtype=int)
        feature_row["hist_global_mean"] = float(np.mean(allowed_values))
        feature_row["hist_global_median"] = float(np.median(allowed_values))
        feature_row["hist_global_q90"] = float(np.quantile(allowed_values, 0.90))
        feature_row["hist_global_q95"] = float(np.quantile(allowed_values, 0.95))
        recent_mask = allowed_years >= (pred_year - 3)
        recent_values = allowed_values[recent_mask] if recent_mask.any() else allowed_values
        feature_row["hist_recent3_mean"] = float(np.mean(recent_values))
        feature_row["hist_recent3_median"] = float(np.median(recent_values))
        feature_row["hist_recent3_q90"] = float(np.quantile(recent_values, 0.90))

        same = (
            np.isclose(hist.iloc[allowed_pos]["lon"].to_numpy(dtype=float), float(pred["lon"]), atol=1e-6)
            & np.isclose(hist.iloc[allowed_pos]["lat"].to_numpy(dtype=float), float(pred["lat"]), atol=1e-6)
        )
        if same.any():
            same_pos = allowed_pos[same]
            same_values = hist_y[same_pos]
            same_years = hist.iloc[same_pos]["year"].to_numpy(dtype=int)
            last_pos = int(np.argmax(same_years))
            feature_row["hist_same_count"] = float(len(same_values))
            feature_row["hist_same_last"] = float(same_values[last_pos])
            feature_row["hist_same_mean"] = float(np.mean(same_values))
            feature_row["hist_same_max"] = float(np.max(same_values))
            feature_row["hist_same_trend"] = _safe_slope(same_years, same_values)
            feature_row["hist_same_year_gap"] = float(pred_year - same_years[last_pos])

        coords_allowed = coords_all[allowed_pos]
        max_k = min(max(K_VALUES), len(allowed_pos))
        nn = NearestNeighbors(n_neighbors=max_k)
        nn.fit(coords_allowed)
        distances, indices = nn.kneighbors(np.asarray([[float(pred["lon"]), float(pred["lat"])]]))
        distances = distances.ravel()
        neighbor_pos = allowed_pos[indices.ravel()]
        neighbor_values_all = hist_y[neighbor_pos]
        neighbor_years_all = hist.iloc[neighbor_pos]["year"].to_numpy(dtype=int)
        for k in K_VALUES:
            kk = min(k, len(neighbor_values_all))
            values = neighbor_values_all[:kk]
            years = neighbor_years_all[:kk]
            dist = distances[:kk]
            year_gap = np.maximum(pred_year - years, 1)
            spatial_weights = 1.0 / np.maximum(dist, 1e-6) ** 2
            time_weights = spatial_weights / year_gap
            feature_row[f"hist_knn{k}_mean"] = float(np.mean(values))
            feature_row[f"hist_knn{k}_median"] = float(np.median(values))
            feature_row[f"hist_knn{k}_idw"] = float(np.sum(spatial_weights * values) / np.sum(spatial_weights))
            feature_row[f"hist_knn{k}_time_idw"] = float(np.sum(time_weights * values) / np.sum(time_weights))
            feature_row[f"hist_knn{k}_std"] = float(np.std(values))
            feature_row[f"hist_knn{k}_min"] = float(np.min(values))
            feature_row[f"hist_knn{k}_max"] = float(np.max(values))
            feature_row[f"hist_knn{k}_min_dist"] = float(np.min(dist))
            for quantile in QUANTILES:
                feature_row[f"hist_knn{k}_q{int(quantile * 100):02d}"] = float(np.quantile(values, quantile))
        rows.append(feature_row)
    return pd.DataFrame(rows, index=pred_idx).replace([np.inf, -np.inf], np.nan)


def direct_predictions(features: pd.DataFrame) -> dict[str, np.ndarray]:
    same_last = features["hist_same_last"].to_numpy(dtype=float)
    same_max = features["hist_same_max"].to_numpy(dtype=float)
    knn12_median = features["hist_knn12_median"].to_numpy(dtype=float)
    knn12_idw = features["hist_knn12_idw"].to_numpy(dtype=float)
    knn30_q90 = features["hist_knn30_q90"].to_numpy(dtype=float)
    knn80_q95 = features["hist_knn80_q95"].to_numpy(dtype=float)
    global_q95 = features["hist_global_q95"].to_numpy(dtype=float)
    recent_q90 = features["hist_recent3_q90"].to_numpy(dtype=float)
    return {
        "CausalKNN12IDW": knn12_idw,
        "CausalKNN12Median": knn12_median,
        "CausalKNN30Q90": knn30_q90,
        "CausalKNN80Q95": knn80_q95,
        "CausalRecentQ90": recent_q90,
        "CausalSameLastElseKNN12IDW": np.where(np.isfinite(same_last), same_last, knn12_idw),
        "CausalSameMaxElseKNN30Q90": np.where(np.isfinite(same_max), np.maximum(same_max, knn30_q90), knn30_q90),
        "CausalHighGuard": np.maximum.reduce([np.nan_to_num(knn30_q90), np.nan_to_num(knn80_q95), np.nan_to_num(global_q95)]),
    }


def fit_predict(spec, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        pred = np.asarray(model.predict(x_test), dtype=float).reshape(-1)
    return np.maximum(pred, 0.0)


def add_eval_row(
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
    pred = np.maximum(np.asarray(pred, dtype=float), 0.0)
    metric = regression_metrics(y_test, pred)
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
    table["predicted"] = pred
    pred_rows.append(table)


def plot_best(best: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for protocol, part in best.groupby("protocol"):
        part = part.sort_values("target")
        fig, ax = plt.subplots(figsize=(9, 5))
        colors = ["#59A14F" if value >= 0 else "#E15759" for value in part["r2"]]
        ax.bar(part["target"], part["r2"], color=colors)
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.set_title(f"Causal Historical Memory R2 ({protocol})")
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
    data_path = ROOT / args.data if args.data else preferred_processed_data_path()
    df = pd.read_csv(data_path)
    df["year"] = df["year"].round().astype(int)
    base_cols = list(config["base_feature_columns"])
    feature_cols = external_feature_columns(df, base_cols)
    model_names = [item.strip() for item in args.models.split(",") if item.strip()]
    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []

    for protocol in ["literature_2019_2020", "temporal_2022_2026"]:
        train_idx, test_idx = protocol_indices(df, protocol)
        train_cutoff = int(df.loc[test_idx, "year"].min()) if len(test_idx) else None
        print(f"\n{protocol}: train={len(train_idx)} test={len(test_idx)}", flush=True)
        for target in config["target_columns"]:
            print(f"  target {target}", flush=True)
            y = df[target].astype(float)
            hist_train = causal_history_features(df, y, train_idx, train_idx, train_cutoff_year=None)
            hist_test = causal_history_features(df, y, train_idx, test_idx, train_cutoff_year=train_cutoff)

            for model_name, pred in direct_predictions(hist_test).items():
                add_eval_row(
                    rows,
                    pred_rows,
                    df,
                    protocol,
                    target,
                    "causal_history_direct",
                    model_name,
                    train_idx,
                    test_idx,
                    y.loc[test_idx],
                    pred,
                    n_features=hist_test.shape[1],
                )

            model_df = pd.concat([df, pd.concat([hist_train, hist_test], axis=0).sort_index()], axis=1)
            df_feat, engineered_cols = add_engineered_features(model_df, feature_cols + hist_train.columns.tolist())
            x_train = df_feat.loc[train_idx, engineered_cols].astype(float)
            x_test = df_feat.loc[test_idx, engineered_cols].astype(float)
            registry = build_model_registry(len(engineered_cols), random_state=args.seed, n_jobs=args.n_jobs)
            registry = {name: registry[name] for name in model_names if name in registry}
            for model_name, spec in registry.items():
                try:
                    pred = fit_predict(spec, x_train, y.loc[train_idx], x_test)
                    add_eval_row(
                        rows,
                        pred_rows,
                        df,
                        protocol,
                        target,
                        "causal_history_ml",
                        model_name,
                        train_idx,
                        test_idx,
                        y.loc[test_idx],
                        pred,
                        n_features=len(engineered_cols),
                    )
                except Exception as exc:
                    rows.append(
                        {
                            "protocol": protocol,
                            "target": target,
                            "method": "causal_history_ml",
                            "model": model_name,
                            "status": f"failed: {exc}",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "n_features": int(len(engineered_cols)),
                            "r2": np.nan,
                            "r2_log1p": np.nan,
                            "rmse": np.nan,
                            "mae": np.nan,
                            "mape": np.nan,
                        }
                    )

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "causal_history_memory_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(
            RESULTS_DIR / "causal_history_memory_predictions.csv", index=False, encoding="utf-8-sig"
        )
    best = (
        metrics.dropna(subset=["r2"])
        .sort_values(["protocol", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["protocol", "target"], as_index=False)
        .head(1)
        .sort_values(["protocol", "target"])
    )
    best.to_csv(TABLES_DIR / "causal_history_memory_best_metrics.csv", index=False, encoding="utf-8-sig")
    plot_best(best)

    strict = best[best["protocol"] == "temporal_2022_2026"].copy()
    show = strict[["target", "method", "model", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 时序因果历史记忆模型",
        "",
        "该实验为每个重金属单独构建同点历史、近邻历史、近期历史分位数和时空距离加权特征。训练样本只使用更早年份作为历史，2022-2026 测试样本只使用训练期历史记录，避免测试期目标值进入特征。",
        "",
        md_table(show),
        "",
        "完整结果见 `tables/causal_history_memory_metrics.csv`；最优结果见 `tables/causal_history_memory_best_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "causal_history_memory_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote causal history memory outputs")


if __name__ == "__main__":
    main()

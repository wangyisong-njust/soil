#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import add_engineered_features
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-task latent-factor models for 8 heavy metals.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Override cleaned CSV path.")
    parser.add_argument("--clusters", type=int, default=6, help="Number of spatial clusters.")
    parser.add_argument("--n-components", type=int, default=4, help="PCA latent components.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs.")
    return parser.parse_args()


def protocol_indices(df: pd.DataFrame, protocol: str, cutoff: int) -> tuple[np.ndarray, np.ndarray]:
    index = np.asarray(df.index)
    if protocol == "literature_2019_2020":
        return index[df["year"].between(2000, 2018).to_numpy()], index[df["year"].between(2019, 2020).to_numpy()]
    if protocol == "temporal_2022_2026":
        return index[(df["year"] < cutoff).to_numpy()], index[(df["year"] >= cutoff).to_numpy()]
    raise ValueError(protocol)


def add_cluster_features(
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    df: pd.DataFrame,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    n_clusters: int,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    n_clusters = max(2, min(n_clusters, len(train_idx) // 25))
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20)
    train_labels = km.fit_predict(df.loc[train_idx, ["lon", "lat"]].to_numpy(dtype=float))
    test_labels = km.predict(df.loc[test_idx, ["lon", "lat"]].to_numpy(dtype=float))
    train_out = x_train.copy()
    test_out = x_test.copy()
    for cluster_id in range(n_clusters):
        col = f"spatial_cluster_{cluster_id}"
        train_out[col] = (train_labels == cluster_id).astype(float)
        test_out[col] = (test_labels == cluster_id).astype(float)
    return train_out, test_out


def build_models(random_state: int, n_jobs: int, n_components: int) -> dict[str, object]:
    return {
        "Latent_Ridge": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=2.0)),
            ]
        ),
        "Latent_PLSR": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", PLSRegression(n_components=max(1, min(n_components, 8)))),
            ]
        ),
        "Latent_RF": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=320,
                        min_samples_leaf=2,
                        max_features=0.8,
                        random_state=random_state,
                        n_jobs=n_jobs,
                    ),
                ),
            ]
        ),
        "Latent_ExtraTrees": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    ExtraTreesRegressor(
                        n_estimators=360,
                        min_samples_leaf=2,
                        max_features=0.85,
                        random_state=random_state,
                        n_jobs=n_jobs,
                    ),
                ),
            ]
        ),
    }


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
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    raw = pd.read_csv(ROOT / (args.data or config["processed_csv"]))
    df, feature_cols = add_engineered_features(raw, config["base_feature_columns"])
    x_all = df[feature_cols].astype(float)
    targets = list(config["target_columns"])
    y_all = np.log1p(df[targets].astype(float).clip(lower=0))
    protocols = ["literature_2019_2020", "temporal_2022_2026"]
    models = build_models(int(config["random_seed"]), args.n_jobs, args.n_components)

    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    for protocol in protocols:
        train_idx, test_idx = protocol_indices(df, protocol, int(config["temporal_test_start_year"]))
        x_train, x_test = add_cluster_features(
            x_all.loc[train_idx],
            x_all.loc[test_idx],
            df,
            train_idx,
            test_idx,
            args.clusters,
            int(config["random_seed"]),
        )
        y_train_log = y_all.loc[train_idx].to_numpy(dtype=float)
        y_test = df.loc[test_idx, targets].astype(float)
        n_components = max(1, min(args.n_components, len(targets), len(train_idx) - 1))
        pca = PCA(n_components=n_components, random_state=int(config["random_seed"]))
        train_scores = pca.fit_transform(y_train_log)

        for model_name, model in models.items():
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model.fit(x_train, train_scores)
                    pred_scores = np.asarray(model.predict(x_test), dtype=float)
                if pred_scores.ndim == 1:
                    pred_scores = pred_scores.reshape(-1, 1)
                pred_log = pca.inverse_transform(pred_scores[:, :n_components])
                pred = np.maximum(np.expm1(pred_log), 0.0)
                for target_pos, target in enumerate(targets):
                    metric = regression_metrics(y_test[target], pred[:, target_pos])
                    rows.append(
                        {
                            "protocol": protocol,
                            "target": target,
                            "method": "multitask_latent_pca",
                            "model": model_name,
                            "status": "ok",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "n_components": int(n_components),
                            "pca_explained_variance": float(pca.explained_variance_ratio_.sum()),
                            **metric,
                        }
                    )
                pred_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
                pred_table["protocol"] = protocol
                pred_table["model"] = model_name
                for target_pos, target in enumerate(targets):
                    pred_table[f"observed_{target}"] = y_test[target].to_numpy(dtype=float)
                    pred_table[f"predicted_{target}"] = pred[:, target_pos]
                pred_rows.append(pred_table)
            except Exception as exc:
                for target in targets:
                    rows.append(
                        {
                            "protocol": protocol,
                            "target": target,
                            "method": "multitask_latent_pca",
                            "model": model_name,
                            "status": f"failed: {exc}",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "r2": np.nan,
                            "r2_log1p": np.nan,
                            "rmse": np.nan,
                            "mae": np.nan,
                            "mape": np.nan,
                        }
                    )

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "multitask_latent_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(RESULTS_DIR / "multitask_latent_predictions.csv", index=False, encoding="utf-8-sig")
    best = (
        metrics[metrics["status"] == "ok"]
        .sort_values(["protocol", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["protocol", "target"], as_index=False)
        .head(1)
        .sort_values(["protocol", "target"])
    )
    best.to_csv(TABLES_DIR / "multitask_latent_best_metrics.csv", index=False, encoding="utf-8-sig")

    show = best[["protocol", "target", "model", "n_train", "n_test", "n_components", "pca_explained_variance", "r2", "r2_log1p", "rmse", "mae", "mape"]].copy()
    for col in ["pca_explained_variance", "r2", "r2_log1p", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda x: f"{x:.4f}")
    lines = [
        "# 多任务潜变量模型对照",
        "",
        "该模型先在训练期 8 个重金属 log 浓度上提取 PCA 综合污染潜因子，再由环境因子和空间分区特征预测潜因子，最后重构各重金属浓度。验证期其他重金属不作为输入。",
        "",
        md_table(show),
        "",
        "输出文件：",
        "",
        "- `tables/multitask_latent_metrics.csv`",
        "- `tables/multitask_latent_best_metrics.csv`",
        "- `results/multitask_latent_predictions.csv`",
        "",
    ]
    (DOCS_DIR / "multitask_latent_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote multitask latent outputs")


if __name__ == "__main__":
    main()

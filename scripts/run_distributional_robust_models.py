#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import HuberRegressor, PoissonRegressor, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PowerTransformer, QuantileTransformer, RobustScaler, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config, target_columns
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run distribution-aware and robust-loss regressors.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--data", default=None, help="Override processed CSV path.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for tree ensembles.")
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


def protocol_indices(df: pd.DataFrame, protocol: str, cutoff: int) -> tuple[np.ndarray, np.ndarray]:
    index = np.asarray(df.index)
    if protocol == "literature_2019_2020":
        return index[df["year"].between(2000, 2018).to_numpy()], index[df["year"].between(2019, 2020).to_numpy()]
    if protocol == "temporal_2022_2026":
        return index[(df["year"] < cutoff).to_numpy()], index[(df["year"] >= cutoff).to_numpy()]
    raise ValueError(protocol)


def validation_indices(df: pd.DataFrame, train_idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    train = df.loc[train_idx]
    years = sorted(train["year"].unique())
    if len(years) >= 5:
        valid_years = set(years[-max(1, int(np.ceil(len(years) * 0.2))) :])
        valid_mask = train["year"].isin(valid_years)
        if valid_mask.sum() >= 10 and (~valid_mask).sum() >= 50:
            return train.index[~valid_mask].to_numpy(), train.index[valid_mask].to_numpy()
    rng = np.random.default_rng(42)
    shuffled = np.asarray(train_idx).copy()
    rng.shuffle(shuffled)
    n_valid = max(10, int(round(len(shuffled) * 0.2)))
    return shuffled[n_valid:], shuffled[:n_valid]


def make_regressors(random_state: int, n_jobs: int) -> dict[str, object]:
    qt = QuantileTransformer(n_quantiles=100, output_distribution="normal", random_state=random_state, subsample=None)
    return {
        "HistGBR_absolute_yj": TransformedTargetRegressor(
            regressor=Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        HistGradientBoostingRegressor(
                            loss="absolute_error",
                            max_iter=220,
                            learning_rate=0.04,
                            max_leaf_nodes=24,
                            l2_regularization=0.08,
                            random_state=random_state,
                        ),
                    ),
                ]
            ),
            transformer=PowerTransformer(method="yeo-johnson", standardize=True),
        ),
        "HistGBR_squared_yj": TransformedTargetRegressor(
            regressor=Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        HistGradientBoostingRegressor(
                            loss="squared_error",
                            max_iter=240,
                            learning_rate=0.035,
                            max_leaf_nodes=31,
                            l2_regularization=0.1,
                            random_state=random_state,
                        ),
                    ),
                ]
            ),
            transformer=PowerTransformer(method="yeo-johnson", standardize=True),
        ),
        "ExtraTrees_yj": TransformedTargetRegressor(
            regressor=Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        ExtraTreesRegressor(
                            n_estimators=260,
                            max_features=0.8,
                            min_samples_leaf=2,
                            random_state=random_state,
                            n_jobs=n_jobs,
                        ),
                    ),
                ]
            ),
            transformer=PowerTransformer(method="yeo-johnson", standardize=True),
        ),
        "ExtraTrees_qnormal": TransformedTargetRegressor(
            regressor=Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        ExtraTreesRegressor(
                            n_estimators=260,
                            max_features=0.8,
                            min_samples_leaf=3,
                            random_state=random_state + 17,
                            n_jobs=n_jobs,
                        ),
                    ),
                ]
            ),
            transformer=qt,
        ),
        "RF_yj": TransformedTargetRegressor(
            regressor=Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        RandomForestRegressor(
                            n_estimators=240,
                            max_features=0.75,
                            min_samples_leaf=3,
                            random_state=random_state,
                            n_jobs=n_jobs,
                        ),
                    ),
                ]
            ),
            transformer=PowerTransformer(method="yeo-johnson", standardize=True),
        ),
        "Huber_yj": TransformedTargetRegressor(
            regressor=Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", RobustScaler()),
                    ("model", HuberRegressor(epsilon=1.35, alpha=0.001, max_iter=3000)),
                ]
            ),
            transformer=PowerTransformer(method="yeo-johnson", standardize=True),
        ),
        "Ridge_qnormal": TransformedTargetRegressor(
            regressor=Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    ("model", Ridge(alpha=5.0)),
                ]
            ),
            transformer=QuantileTransformer(
                n_quantiles=100,
                output_distribution="normal",
                random_state=random_state + 29,
                subsample=None,
            ),
        ),
        "Poisson_raw": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", PoissonRegressor(alpha=0.02, max_iter=3000)),
            ]
        ),
    }


def fit_predict(model, x_train: pd.DataFrame, y_train: pd.Series, x_pred: pd.DataFrame) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = clone(model)
        fitted.fit(x_train, y_train)
        pred = np.asarray(fitted.predict(x_pred), dtype=float).reshape(-1)
    return np.maximum(pred, 0.0)


def feature_columns(df: pd.DataFrame, config: dict[str, object], targets: list[str]) -> list[str]:
    base = list(config["base_feature_columns"])
    public_external = [col for col in df.columns if col.startswith(("sg_", "np_", "osm_", "viirs_", "ghsl_", "wc_"))]
    return list(dict.fromkeys(base + public_external))


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    targets = target_columns(config)
    data_path = ROOT / args.data if args.data else preferred_processed_data_path()
    raw = pd.read_csv(data_path)
    raw["year"] = raw["year"].round().astype(int)
    feature_cols = feature_columns(raw, config, targets)
    df, engineered_cols = add_engineered_features(raw, feature_cols)
    model_feature_cols = engineered_cols + (TARGET_SPATIAL_FEATURES if config.get("use_target_spatial_lag_features") else [])
    x_base = df[engineered_cols].astype(float)
    models = make_regressors(int(config["random_seed"]), args.n_jobs)
    rows: list[dict[str, object]] = []
    best_rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []

    for protocol in ["literature_2019_2020", "temporal_2022_2026"]:
        train_idx, test_idx = protocol_indices(df, protocol, int(config["temporal_test_start_year"]))
        core_idx, valid_idx = validation_indices(df, train_idx)
        print(
            f"\n{protocol}: train={len(train_idx)} valid={len(valid_idx)} test={len(test_idx)} features={len(model_feature_cols)}",
            flush=True,
        )
        for target in targets:
            y = df[target].astype(float)
            if config.get("use_target_spatial_lag_features", False):
                k = int(config.get("target_spatial_lag_k", 12))
                x_core = add_target_spatial_lag_features(df, x_base, y, core_idx, core_idx, k=k, leave_one_out=True)
                x_valid = add_target_spatial_lag_features(df, x_base, y, core_idx, valid_idx, k=k, leave_one_out=False)
                x_train = add_target_spatial_lag_features(df, x_base, y, train_idx, train_idx, k=k, leave_one_out=True)
                x_test = add_target_spatial_lag_features(df, x_base, y, train_idx, test_idx, k=k, leave_one_out=False)
            else:
                x_core = x_base.loc[core_idx]
                x_valid = x_base.loc[valid_idx]
                x_train = x_base.loc[train_idx]
                x_test = x_base.loc[test_idx]
            y_core = y.loc[core_idx]
            y_valid = y.loc[valid_idx]
            y_train = y.loc[train_idx]
            y_test = y.loc[test_idx]
            target_records: list[dict[str, object]] = []
            target_predictions: dict[str, np.ndarray] = {}
            for model_name, model in models.items():
                try:
                    if model_name == "Poisson_raw" and (y_core < 0).any():
                        raise ValueError("PoissonRegressor requires non-negative target values.")
                    valid_pred = fit_predict(model, x_core, y_core, x_valid)
                    valid_metric = regression_metrics(y_valid, valid_pred)
                    test_pred = fit_predict(model, x_train, y_train, x_test)
                    test_metric = regression_metrics(y_test, test_pred)
                    record = {
                        "protocol": protocol,
                        "target": target,
                        "feature_set": "external_covariates" if any(col.startswith(("sg_", "np_", "osm_", "viirs_", "ghsl_", "wc_")) for col in feature_cols) else "baseline",
                        "method": "distributional_robust",
                        "model": model_name,
                        "status": "ok",
                        "n_train": int(len(train_idx)),
                        "n_validation": int(len(valid_idx)),
                        "n_test": int(len(test_idx)),
                        "n_features": int(len(model_feature_cols)),
                        "validation_r2": valid_metric["r2"],
                        "validation_rmse": valid_metric["rmse"],
                        "validation_mae": valid_metric["mae"],
                        **test_metric,
                    }
                    rows.append(record)
                    target_records.append(record)
                    target_predictions[model_name] = test_pred
                    print(
                        f"  {target} {model_name:<20} val_R2={valid_metric['r2']:.3f} test_R2={test_metric['r2']:.3f}",
                        flush=True,
                    )
                except Exception as exc:
                    rows.append(
                        {
                            "protocol": protocol,
                            "target": target,
                            "feature_set": "external_covariates",
                            "method": "distributional_robust",
                            "model": model_name,
                            "status": f"failed: {exc}",
                            "n_train": int(len(train_idx)),
                            "n_validation": int(len(valid_idx)),
                            "n_test": int(len(test_idx)),
                            "n_features": int(len(model_feature_cols)),
                            "validation_r2": np.nan,
                            "validation_rmse": np.nan,
                            "validation_mae": np.nan,
                            "r2": np.nan,
                            "r2_log1p": np.nan,
                            "rmse": np.nan,
                            "mae": np.nan,
                            "mape": np.nan,
                        }
                    )
            ok_records = [record for record in target_records if np.isfinite(float(record["validation_r2"]))]
            if ok_records:
                selected = sorted(ok_records, key=lambda item: (-float(item["validation_r2"]), float(item["validation_rmse"])))[0]
                best_rows.append(selected)
                pred_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
                pred_table["protocol"] = protocol
                pred_table["target"] = target
                pred_table["model"] = selected["model"]
                pred_table["observed"] = y_test.to_numpy(dtype=float)
                pred_table["predicted"] = target_predictions[str(selected["model"])]
                pred_rows.append(pred_table)

    metrics = pd.DataFrame(rows)
    best = pd.DataFrame(best_rows).sort_values(["protocol", "target"])
    metrics.to_csv(TABLES_DIR / "distributional_robust_metrics.csv", index=False, encoding="utf-8-sig")
    best.to_csv(TABLES_DIR / "distributional_robust_best_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(
            RESULTS_DIR / "distributional_robust_predictions.csv", index=False, encoding="utf-8-sig"
        )

    show = best[["protocol", "target", "model", "validation_r2", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["validation_r2", "r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    strict = best[best["protocol"] == "temporal_2022_2026"]
    lines = [
        "# 目标分布变换与稳健损失模型",
        "",
        "本实验针对重金属浓度偏态分布和少数极端值，比较 Yeo-Johnson、分位数正态化、Huber/Poisson 线性模型、绝对误差 HistGradientBoosting 以及树集成模型。模型选择只使用训练期内部验证，不按 2022-2026 测试集表现选型。",
        "",
        md_table(show),
        "",
    ]
    if len(strict):
        lines.extend(
            [
                (
                    f"2022-2026 严格时间外推下，验证期选型后的平均 R2={strict['r2'].mean():.4f}，"
                    f"中位 R2={strict['r2'].median():.4f}，{int((strict['r2'] > 0).sum())}/{strict['target'].nunique()} 个目标为正。"
                ),
                "",
            ]
        )
    lines.extend(
        [
            "完整候选表见 `tables/distributional_robust_metrics.csv`；验证期选型结果见 `tables/distributional_robust_best_metrics.csv`；测试期预测见 `results/distributional_robust_predictions.csv`。",
            "",
        ]
    )
    (DOCS_DIR / "distributional_robust_model_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote distributional robust model outputs")


if __name__ == "__main__":
    main()

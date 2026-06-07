#!/usr/bin/env python
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import HuberRegressor, RidgeCV
from sklearn.metrics import mean_squared_error
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from soilmodel.config import target_columns
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path

from run_publication_validation_fusion import load_predictions


ALPHAS = np.linspace(0.0, 1.0, 11)


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


def pivot_protocol(preds: pd.DataFrame, protocol: str, target: str) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    part = preds[(preds["protocol"] == protocol) & (preds["target"] == target)].copy()
    key = ["lon", "lat", "year", "observed"]
    wide = part.pivot_table(index=key, columns="candidate", values="predicted", aggfunc="first").reset_index()
    y = wide["observed"].astype(float)
    x = wide.drop(columns=key).replace([np.inf, -np.inf], np.nan)
    keys = wide[key].copy()
    return x, y, keys


def robust_iqr(values: np.ndarray) -> float:
    q25, q75 = np.nanquantile(values, [0.25, 0.75])
    return float(max(q75 - q25, 1e-8))


def best_alpha_shrink(val_pred: np.ndarray, val_y: np.ndarray, anchor: float) -> tuple[float, float]:
    best_alpha = 1.0
    best_rmse = np.inf
    for alpha in ALPHAS:
        candidate = alpha * val_pred + (1.0 - alpha) * anchor
        rmse = float(np.sqrt(mean_squared_error(val_y, candidate)))
        if rmse < best_rmse:
            best_alpha = float(alpha)
            best_rmse = rmse
    return best_alpha, best_rmse


def local_residual_transfer(
    fit_keys: pd.DataFrame,
    pred_keys: pd.DataFrame,
    fit_residual: np.ndarray,
    k: int,
    leave_one_out: bool = False,
) -> np.ndarray:
    fit_coord = fit_keys[["lon", "lat"]].to_numpy(dtype=float)
    pred_coord = pred_keys[["lon", "lat"]].to_numpy(dtype=float)
    year_scale = 8.0
    fit_features = np.c_[fit_coord, fit_keys["year"].to_numpy(dtype=float) / year_scale]
    pred_features = np.c_[pred_coord, pred_keys["year"].to_numpy(dtype=float) / year_scale]
    n_neighbors = min(k + int(leave_one_out), len(fit_features))
    nn = NearestNeighbors(n_neighbors=n_neighbors)
    nn.fit(fit_features)
    distances, idx = nn.kneighbors(pred_features)
    if leave_one_out and len(fit_features) == len(pred_features):
        distances = distances[:, 1:]
        idx = idx[:, 1:]
    weights = 1.0 / np.maximum(distances, 1e-8)
    weights = weights / weights.sum(axis=1, keepdims=True)
    return np.sum(fit_residual[idx] * weights, axis=1)


def candidate_variants(
    val_pred: np.ndarray,
    test_pred: np.ndarray,
    val_y: np.ndarray,
    val_keys: pd.DataFrame,
    test_keys: pd.DataFrame,
    val_anchor: float,
    test_anchor: float,
) -> list[tuple[str, np.ndarray, np.ndarray, dict[str, object]]]:
    variants: list[tuple[str, np.ndarray, np.ndarray, dict[str, object]]] = []
    residual = val_y - val_pred
    median_residual = float(np.median(residual))
    mean_residual = float(np.mean(residual))
    variants.append(("median_residual_shift", val_pred + median_residual, test_pred + median_residual, {}))
    variants.append(("mean_residual_shift", val_pred + mean_residual, test_pred + mean_residual, {}))

    pred_iqr = robust_iqr(val_pred)
    y_iqr = robust_iqr(val_y)
    pred_median = float(np.median(val_pred))
    y_median = float(np.median(val_y))
    robust_val = y_median + (val_pred - pred_median) * (y_iqr / pred_iqr)
    robust_test = y_median + (test_pred - pred_median) * (y_iqr / pred_iqr)
    variants.append(("robust_iqr_scale_shift", robust_val, robust_test, {"scale": float(y_iqr / pred_iqr)}))

    pred_std = float(max(np.std(val_pred), 1e-8))
    y_std = float(np.std(val_y))
    mean_scaled_val = float(np.mean(val_y)) + (val_pred - float(np.mean(val_pred))) * (y_std / pred_std)
    mean_scaled_test = float(np.mean(val_y)) + (test_pred - float(np.mean(val_pred))) * (y_std / pred_std)
    variants.append(("mean_std_scale_shift", mean_scaled_val, mean_scaled_test, {"scale": float(y_std / pred_std)}))

    alpha, alpha_rmse = best_alpha_shrink(val_pred, val_y, val_anchor)
    shrink_val = alpha * val_pred + (1.0 - alpha) * val_anchor
    shrink_test = alpha * test_pred + (1.0 - alpha) * test_anchor
    variants.append(("validated_anchor_shrink", shrink_val, shrink_test, {"alpha": alpha, "validation_rmse": alpha_rmse}))

    if np.unique(val_pred).size >= 4:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ridge = RidgeCV(alphas=np.logspace(-4, 4, 17))
            ridge.fit(val_pred.reshape(-1, 1), val_y)
            variants.append(
                (
                    "ridge_1d_transfer",
                    ridge.predict(val_pred.reshape(-1, 1)),
                    ridge.predict(test_pred.reshape(-1, 1)),
                    {"alpha": float(ridge.alpha_)},
                )
            )
        try:
            huber = HuberRegressor(alpha=1e-4, epsilon=1.35)
            huber.fit(val_pred.reshape(-1, 1), val_y)
            variants.append(
                (
                    "huber_1d_transfer",
                    huber.predict(val_pred.reshape(-1, 1)),
                    huber.predict(test_pred.reshape(-1, 1)),
                    {},
                )
            )
        except Exception:
            pass
        try:
            isotonic = IsotonicRegression(out_of_bounds="clip")
            isotonic.fit(val_pred, val_y)
            variants.append(("isotonic_transfer", isotonic.predict(val_pred), isotonic.predict(test_pred), {}))
        except Exception:
            pass

    for k in [5, 10, 20, 35]:
        val_residual_transfer = local_residual_transfer(val_keys, val_keys, residual, k, leave_one_out=True)
        test_residual_transfer = local_residual_transfer(val_keys, test_keys, residual, k)
        variants.append(
            (
                f"spacetime_residual_knn{k}",
                val_pred + val_residual_transfer,
                test_pred + test_residual_transfer,
                {"residual_k": k},
            )
        )

    return variants


def main() -> None:
    ensure_project_dirs()
    preds = load_predictions()
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)

    rows: list[dict[str, object]] = []
    validation_selected_pred_by_target: dict[str, pd.DataFrame] = {}
    validation_selected_score_by_target: dict[str, tuple[float, float]] = {}
    test_selected_pred_by_target: dict[str, pd.DataFrame] = {}
    test_selected_score_by_target: dict[str, tuple[float, float]] = {}
    for target in target_columns():
        val_x, val_y, val_keys = pivot_protocol(preds, "literature_2019_2020", target)
        test_x, test_y, test_keys = pivot_protocol(preds, "temporal_2022_2026", target)
        common = [col for col in val_x.columns if col in test_x.columns]
        val_x = val_x[common].copy()
        test_x = test_x[common].copy()
        keep = val_x.notna().all(axis=0) & test_x.notna().all(axis=0)
        common = keep[keep].index.tolist()
        val_x = val_x[common]
        test_x = test_x[common]

        val_train = data[data["year"].between(2000, 2018)]
        test_train = data[data["year"] < 2022]
        val_anchor = float(val_train.loc[val_train["year"] >= 2016, target].median())
        test_anchor = float(test_train.loc[test_train["year"] >= 2018, target].median())
        lower = 0.0
        upper = float(max(test_train[target].quantile(0.995) * 1.8, test_train[target].max() * 1.05))

        for candidate in common:
            val_pred = val_x[candidate].to_numpy(dtype=float)
            test_pred = test_x[candidate].to_numpy(dtype=float)
            if np.nanstd(val_pred) < 1e-10:
                continue
            val_raw_metric = regression_metrics(val_y, val_pred)
            for variant_name, val_calibrated, test_calibrated, meta in candidate_variants(
                val_pred,
                test_pred,
                val_y.to_numpy(dtype=float),
                val_keys,
                test_keys,
                val_anchor,
                test_anchor,
            ):
                val_calibrated = np.clip(np.asarray(val_calibrated, dtype=float).reshape(-1), lower, upper)
                test_calibrated = np.clip(np.asarray(test_calibrated, dtype=float).reshape(-1), lower, upper)
                if not np.isfinite(val_calibrated).all() or not np.isfinite(test_calibrated).all():
                    continue
                validation_metric = regression_metrics(val_y, val_calibrated)
                test_metric = regression_metrics(test_y, test_calibrated)
                rows.append(
                    {
                        "protocol": "temporal_2022_2026",
                        "target": target,
                        "method": "validation_transfer_calibration",
                        "model": variant_name,
                        "status": "ok",
                        "n_train": int(len(val_y)),
                        "n_test": int(len(test_y)),
                        "base_candidate": candidate,
                        "validation_r2_raw": val_raw_metric["r2"],
                        "validation_rmse_raw": val_raw_metric["rmse"],
                        "validation_r2_calibrated": validation_metric["r2"],
                        "validation_r2_log1p_calibrated": validation_metric["r2_log1p"],
                        "validation_rmse_calibrated": validation_metric["rmse"],
                        "validation_mae_calibrated": validation_metric["mae"],
                        "validation_mape_calibrated": validation_metric["mape"],
                        **test_metric,
                        **meta,
                    }
                )
                validation_score = (float(validation_metric["r2"]), -float(validation_metric["rmse"]))
                if (
                    target not in validation_selected_score_by_target
                    or validation_score > validation_selected_score_by_target[target]
                ):
                    validation_selected_score_by_target[target] = validation_score
                    table = test_keys[["lon", "lat", "year"]].copy()
                    table["protocol"] = "temporal_2022_2026"
                    table["target"] = target
                    table["method"] = "validation_transfer_calibration"
                    table["model"] = variant_name
                    table["base_candidate"] = candidate
                    table["observed"] = test_y.to_numpy(dtype=float)
                    table["predicted"] = test_calibrated
                    validation_selected_pred_by_target[target] = table

                test_score = (float(test_metric["r2"]), -float(test_metric["rmse"]))
                if target not in test_selected_score_by_target or test_score > test_selected_score_by_target[target]:
                    test_selected_score_by_target[target] = test_score
                    table = test_keys[["lon", "lat", "year"]].copy()
                    table["protocol"] = "temporal_2022_2026"
                    table["target"] = target
                    table["method"] = "validation_transfer_calibration"
                    table["model"] = variant_name
                    table["base_candidate"] = candidate
                    table["observed"] = test_y.to_numpy(dtype=float)
                    table["predicted"] = test_calibrated
                    test_selected_pred_by_target[target] = table

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "validation_transfer_calibration_metrics.csv", index=False, encoding="utf-8-sig")
    if validation_selected_pred_by_target:
        pd.concat(validation_selected_pred_by_target.values(), ignore_index=True).to_csv(
            RESULTS_DIR / "validation_transfer_calibration_predictions.csv", index=False, encoding="utf-8-sig"
        )
    if test_selected_pred_by_target:
        pd.concat(test_selected_pred_by_target.values(), ignore_index=True).to_csv(
            RESULTS_DIR / "validation_transfer_calibration_test_selected_predictions.csv",
            index=False,
            encoding="utf-8-sig",
        )

    validation_best = (
        metrics.dropna(subset=["r2"])
        .sort_values(
            ["target", "validation_r2_calibrated", "validation_rmse_calibrated", "r2", "rmse"],
            ascending=[True, False, True, False, True],
        )
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    validation_best.to_csv(
        TABLES_DIR / "validation_transfer_calibration_best_metrics.csv", index=False, encoding="utf-8-sig"
    )

    test_selected_best = (
        metrics.dropna(subset=["r2"])
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    test_selected_best.to_csv(
        TABLES_DIR / "validation_transfer_calibration_test_selected_best_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )

    show = validation_best[
        [
            "target",
            "model",
            "base_candidate",
            "validation_r2_calibrated",
            "validation_rmse_calibrated",
            "r2",
            "rmse",
            "mae",
            "mape",
        ]
    ].copy()
    for col in ["validation_r2_calibrated", "validation_rmse_calibrated", "r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda value: f"{value:.4f}")
    test_show = test_selected_best[["target", "model", "base_candidate", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        test_show[col] = test_show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 验证期迁移校正模型",
        "",
        "该实验使用 2019-2020 验证期学习候选预测的偏差校正、尺度校正、锚点收缩和时空局部残差校正，然后固定迁移到 2022-2026 测试期。论文口径表只按 2019-2020 校正后验证表现选择模型，不使用 2022-2026 目标观测值选模型。",
        "",
        "## 验证期选择结果",
        "",
        md_table(show),
        "",
        "## 测试集选择上限",
        "",
        "下表按 2022-2026 测试表现选择，只能作为探索上限或诊断，不可作为论文主验证结果。",
        "",
        md_table(test_show),
        "",
        "完整指标见 `tables/validation_transfer_calibration_metrics.csv`；验证期选择结果见 `tables/validation_transfer_calibration_best_metrics.csv`；测试集选择上限见 `tables/validation_transfer_calibration_test_selected_best_metrics.csv`；验证期选择预测明细见 `results/validation_transfer_calibration_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "validation_transfer_calibration_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote validation transfer calibration outputs")


if __name__ == "__main__":
    main()

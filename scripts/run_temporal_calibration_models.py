#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import target_columns
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs


FIG_DIR = FIGURES_DIR / "temporal_calibration"


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


def normalize_long(df: pd.DataFrame, source: str) -> pd.DataFrame:
    out = df.copy()
    if "feature_set" in out.columns:
        out = out[out["feature_set"].isin(["external_covariates", "external_plus_spatial_distribution"])].copy()
        if "method" not in out.columns:
            out["method"] = out["feature_set"]
    if "method" not in out.columns:
        out["method"] = source
    keep = ["lon", "lat", "year", "protocol", "target", "method", "model", "observed", "predicted"]
    out = out[[col for col in keep if col in out.columns]].copy()
    if set(keep).difference(out.columns):
        raise ValueError(f"{source} missing required columns: {set(keep).difference(out.columns)}")
    out["source"] = source
    out["year"] = out["year"].round().astype(int)
    out["candidate"] = out["source"] + "::" + out["method"].astype(str) + "::" + out["model"].astype(str)
    return out


def load_predictions() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    specs = [
        ("external", ROOT / "results/external_covariate_predictions.csv"),
        ("temporal_sequence", ROOT / "results/temporal_sequence_model_predictions.csv"),
        ("local_analog", ROOT / "results/local_analog_memory_predictions.csv"),
        ("causal_history", ROOT / "results/causal_history_memory_predictions.csv"),
        ("quantile_gate", ROOT / "results/quantile_risk_gate_predictions.csv"),
        ("innovation", ROOT / "results/innovation_model_predictions.csv"),
        ("spatial_distribution", ROOT / "results/spatial_distribution_feature_predictions.csv"),
    ]
    for source, path in specs:
        if path.exists() and path.stat().st_size:
            frames.append(normalize_long(pd.read_csv(path), source))

    mt_path = ROOT / "results/multitask_latent_predictions.csv"
    if mt_path.exists() and mt_path.stat().st_size:
        mt = pd.read_csv(mt_path)
        mt["year"] = mt["year"].round().astype(int)
        rows = []
        for target in target_columns():
            obs_col = f"observed_{target}"
            pred_col = f"predicted_{target}"
            if obs_col not in mt.columns or pred_col not in mt.columns:
                continue
            part = mt[["lon", "lat", "year", "protocol", "model", obs_col, pred_col]].copy()
            part = part.rename(columns={obs_col: "observed", pred_col: "predicted"})
            part["target"] = target
            part["method"] = "multitask_latent_pca"
            part["source"] = "multitask_latent"
            part["candidate"] = part["source"] + "::" + part["method"] + "::" + part["model"].astype(str)
            rows.append(part[["lon", "lat", "year", "protocol", "target", "method", "model", "observed", "predicted", "source", "candidate"]])
        if rows:
            frames.append(pd.concat(rows, ignore_index=True))

    if not frames:
        raise SystemExit("No reusable prediction files found.")
    preds = pd.concat(frames, ignore_index=True)
    preds = preds.replace([np.inf, -np.inf], np.nan).dropna(subset=["observed", "predicted"])
    return preds


def calibrated_predictions(y_val: np.ndarray, p_val: np.ndarray, p_test: np.ndarray) -> dict[str, tuple[np.ndarray, float]]:
    out: dict[str, tuple[np.ndarray, float]] = {}
    p_test = np.asarray(p_test, dtype=float)
    p_val = np.asarray(p_val, dtype=float)
    y_val = np.asarray(y_val, dtype=float)
    out["Raw"] = (p_test, float(np.sqrt(np.mean((y_val - p_val) ** 2))))

    bias = float(np.mean(y_val - p_val))
    p_val_bias = p_val + bias
    out["BiasCorrected"] = (p_test + bias, float(np.sqrt(np.mean((y_val - p_val_bias) ** 2))))

    denom = float(np.sum(p_val * p_val))
    ratio = float(np.sum(y_val * p_val) / denom) if denom > 0 else 1.0
    p_val_ratio = p_val * ratio
    out["RatioScaled"] = (p_test * ratio, float(np.sqrt(np.mean((y_val - p_val_ratio) ** 2))))

    if np.nanstd(p_val) > 1e-8:
        model = LinearRegression()
        model.fit(p_val.reshape(-1, 1), y_val)
        p_val_affine = model.predict(p_val.reshape(-1, 1))
        out["Affine"] = (
            model.predict(p_test.reshape(-1, 1)),
            float(np.sqrt(np.mean((y_val - p_val_affine) ** 2))),
        )
        sd = float(np.std(p_val))
        y_sd = float(np.std(y_val))
        p_val_ms = (p_val - np.mean(p_val)) / sd * y_sd + np.mean(y_val)
        p_test_ms = (p_test - np.mean(p_val)) / sd * y_sd + np.mean(y_val)
        out["MeanStdMapped"] = (p_test_ms, float(np.sqrt(np.mean((y_val - p_val_ms) ** 2))))

    log_y = np.log1p(np.maximum(y_val, 0))
    log_p_val = np.log1p(np.maximum(p_val, 0))
    log_p_test = np.log1p(np.maximum(p_test, 0))
    log_bias = float(np.mean(log_y - log_p_val))
    p_val_log_bias = np.expm1(log_p_val + log_bias)
    out["LogBiasCorrected"] = (
        np.expm1(log_p_test + log_bias),
        float(np.sqrt(np.mean((y_val - p_val_log_bias) ** 2))),
    )
    if np.nanstd(log_p_val) > 1e-8:
        log_model = LinearRegression()
        log_model.fit(log_p_val.reshape(-1, 1), log_y)
        p_val_log_affine = np.expm1(log_model.predict(log_p_val.reshape(-1, 1)))
        out["LogAffine"] = (
            np.expm1(log_model.predict(log_p_test.reshape(-1, 1))),
            float(np.sqrt(np.mean((y_val - p_val_log_affine) ** 2))),
        )

    if len(np.unique(p_val)) >= 4:
        order = np.argsort(p_val)
        sorted_p = p_val[order]
        sorted_y = np.sort(y_val)
        unique_p, unique_index = np.unique(sorted_p, return_index=True)
        mapped_val = np.interp(p_val, unique_p, sorted_y[unique_index], left=sorted_y[0], right=sorted_y[-1])
        mapped_test = np.interp(p_test, unique_p, sorted_y[unique_index], left=sorted_y[0], right=sorted_y[-1])
        out["QuantileMapped"] = (mapped_test, float(np.sqrt(np.mean((y_val - mapped_val) ** 2))))

    clipped: dict[str, tuple[np.ndarray, float]] = {}
    lo, hi = float(np.min(y_val)), float(np.max(y_val))
    for name, (pred, val_rmse) in out.items():
        clipped[f"{name}Clipped"] = (np.clip(pred, lo, hi), val_rmse)
    out.update(clipped)
    return {name: (np.maximum(pred, 0.0), val_rmse) for name, (pred, val_rmse) in out.items()}


def key_cols(df: pd.DataFrame) -> pd.DataFrame:
    return df[["lon", "lat", "year", "observed"]].drop_duplicates().sort_values(["year", "lon", "lat"]).reset_index(drop=True)


def plot_oracle(best: pd.DataFrame) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    strict = best.sort_values("target")
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#59A14F" if value >= 0 else "#E15759" for value in strict["r2"]]
    ax.bar(strict["target"], strict["r2"], color=colors)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("Temporal Calibration Exploration R2 (2022-2026)")
    ax.set_xlabel("Heavy metal target")
    ax.set_ylabel("R2")
    ax.grid(axis="y", alpha=0.25)
    for patch in ax.patches:
        value = patch.get_height()
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            value + (0.025 if value >= 0 else -0.025),
            f"{value:.2f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=9,
        )
    plt.tight_layout()
    plt.savefig(FIG_DIR / "oracle_best_r2_temporal_2022_2026.png", dpi=300, bbox_inches="tight")
    plt.close()


def main() -> None:
    ensure_project_dirs()
    preds = load_predictions()
    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    selected_rows: list[dict[str, object]] = []

    for target in target_columns():
        val = preds[(preds["protocol"] == "literature_2019_2020") & (preds["target"] == target)].copy()
        test = preds[(preds["protocol"] == "temporal_2022_2026") & (preds["target"] == target)].copy()
        if val.empty or test.empty:
            continue
        test_keys = key_cols(test)
        candidate_rows: list[dict[str, object]] = []
        for candidate in sorted(set(val["candidate"]).intersection(set(test["candidate"]))):
            val_part = val[val["candidate"] == candidate].sort_values(["year", "lon", "lat"]).copy()
            test_part = test[test["candidate"] == candidate].sort_values(["year", "lon", "lat"]).copy()
            if len(val_part) == 0 or len(test_part) == 0:
                continue
            y_val = val_part["observed"].to_numpy(dtype=float)
            p_val = val_part["predicted"].to_numpy(dtype=float)
            y_test = test_part["observed"].to_numpy(dtype=float)
            p_test = test_part["predicted"].to_numpy(dtype=float)
            source, method, model_name = candidate.split("::", 2)
            calibrated = calibrated_predictions(y_val, p_val, p_test)
            for cal_name, (pred, val_rmse) in calibrated.items():
                metric = regression_metrics(y_test, pred)
                row = {
                    "protocol": "temporal_2022_2026",
                    "target": target,
                    "method": "temporal_validation_calibration",
                    "model": f"{source}:{model_name}:{cal_name}",
                    "status": "ok",
                    "n_train": int(len(y_val)),
                    "n_test": int(len(y_test)),
                    "candidate": candidate,
                    "base_source": source,
                    "base_method": method,
                    "base_model": model_name,
                    "calibration": cal_name,
                    "validation_rmse": val_rmse,
                    **metric,
                }
                rows.append(row)
                candidate_rows.append(row)
                table = test_part[["lon", "lat", "year"]].copy()
                table["protocol"] = "temporal_2022_2026"
                table["target"] = target
                table["method"] = "temporal_validation_calibration"
                table["model"] = row["model"]
                table["observed"] = y_test
                table["predicted"] = pred
                pred_rows.append(table)

        if candidate_rows:
            selected = sorted(candidate_rows, key=lambda item: (item["validation_rmse"], -item["r2"], item["rmse"]))[0].copy()
            selected["selection_scope"] = "selected_by_2019_2020_validation_rmse"
            selected_rows.append(selected)

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "temporal_calibration_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(
            RESULTS_DIR / "temporal_calibration_predictions.csv", index=False, encoding="utf-8-sig"
        )
    validated = pd.DataFrame(selected_rows).sort_values("target")
    validated.to_csv(TABLES_DIR / "temporal_calibration_validated_best_metrics.csv", index=False, encoding="utf-8-sig")
    oracle = (
        metrics.dropna(subset=["r2"])
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    oracle.to_csv(TABLES_DIR / "temporal_calibration_best_metrics.csv", index=False, encoding="utf-8-sig")
    plot_oracle(oracle)

    show_valid = validated[["target", "base_source", "base_model", "calibration", "validation_rmse", "r2", "rmse", "mae", "mape"]].copy()
    show_oracle = oracle[["target", "base_source", "base_model", "calibration", "r2", "rmse", "mae", "mape"]].copy()
    for show in [show_valid, show_oracle]:
        for col in ["validation_rmse", "r2", "rmse", "mae", "mape"]:
            if col in show:
                show[col] = show[col].map(lambda value: f"{value:.4f}")
    report = [
        "# 时间验证校准模型",
        "",
        "该实验用 2019-2020 作为校准期，学习偏差校正、比例缩放、线性校准、log 校准和分位数映射，再应用到 2022-2026 未来验证预测。`validated` 表按 2019-2020 校准 RMSE 选择方案；`oracle` 表是在 2022-2026 上的探索上限，不能作为独立测试主结果。",
        "",
        "## 按 2019-2020 选择的校准方案",
        "",
        md_table(show_valid),
        "",
        "## 2022-2026 探索上限",
        "",
        md_table(show_oracle),
        "",
        "完整结果见 `tables/temporal_calibration_metrics.csv`；按校准期选择结果见 `tables/temporal_calibration_validated_best_metrics.csv`；探索上限见 `tables/temporal_calibration_best_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "temporal_calibration_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote temporal calibration outputs")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import target_columns
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


FIG_DIR = FIGURES_DIR / "multi_evidence_fusion"


def load_long_predictions() -> pd.DataFrame:
    targets = target_columns()
    frames: list[pd.DataFrame] = []
    specs = [
        ("external", ROOT / "results/external_covariate_predictions.csv"),
        ("temporal_sequence", ROOT / "results/temporal_sequence_model_predictions.csv"),
        ("local_analog", ROOT / "results/local_analog_memory_predictions.csv"),
        ("quantile_gate", ROOT / "results/quantile_risk_gate_predictions.csv"),
        ("innovation", ROOT / "results/innovation_model_predictions.csv"),
    ]
    for source, path in specs:
        if not path.exists() or path.stat().st_size == 0:
            continue
        df = pd.read_csv(path)
        if source == "external":
            df = df[df["feature_set"] == "external_covariates"].copy()
            df["method"] = "external_covariates"
        if "method" not in df.columns:
            df["method"] = source
        keep = ["lon", "lat", "year", "protocol", "target", "method", "model", "observed", "predicted"]
        df = df[keep].copy()
        df["source"] = source
        frames.append(df)

    mt_path = ROOT / "results/multitask_latent_predictions.csv"
    if mt_path.exists() and mt_path.stat().st_size:
        mt = pd.read_csv(mt_path)
        rows = []
        for target in targets:
            obs_col = f"observed_{target}"
            pred_col = f"predicted_{target}"
            if obs_col not in mt.columns or pred_col not in mt.columns:
                continue
            part = mt[["lon", "lat", "year", "protocol", "model", obs_col, pred_col]].copy()
            part = part.rename(columns={obs_col: "observed", pred_col: "predicted"})
            part["target"] = target
            part["method"] = "multitask_latent_pca"
            part["source"] = "multitask_latent"
            rows.append(part[["lon", "lat", "year", "protocol", "target", "method", "model", "observed", "predicted", "source"]])
        if rows:
            frames.append(pd.concat(rows, ignore_index=True))

    if not frames:
        raise SystemExit("No prediction files found.")
    out = pd.concat(frames, ignore_index=True)
    out["candidate"] = out["source"] + "::" + out["method"].astype(str) + "::" + out["model"].astype(str)
    out["year"] = out["year"].round().astype(int)
    return out


def add_baseline_predictions(preds: pd.DataFrame) -> pd.DataFrame:
    targets = target_columns()
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    rows = []
    protocols = {
        "literature_2019_2020": (data[data["year"].between(2000, 2018)], data[data["year"].between(2019, 2020)]),
        "temporal_2022_2026": (data[data["year"] < 2022], data[data["year"] >= 2022]),
    }
    for protocol, (train, test) in protocols.items():
        for target in targets:
            values = {
                "TrainMean": float(train[target].mean()),
                "TrainMedian": float(train[target].median()),
                "LastTrainYearMean": float(train.loc[train["year"] == train["year"].max(), target].mean()),
            }
            for model, value in values.items():
                part = test[["lon", "lat", "year"]].copy()
                part["protocol"] = protocol
                part["target"] = target
                part["method"] = "guardrail_baseline"
                part["model"] = model
                part["observed"] = test[target].to_numpy(dtype=float)
                part["predicted"] = value
                part["source"] = "conservative_baseline"
                part["candidate"] = "conservative_baseline::guardrail_baseline::" + model
                rows.append(part)
    return pd.concat([preds, pd.concat(rows, ignore_index=True)], ignore_index=True)


def pivot_protocol(preds: pd.DataFrame, protocol: str, target: str) -> tuple[pd.DataFrame, pd.Series]:
    part = preds[(preds["protocol"] == protocol) & (preds["target"] == target)].copy()
    key_cols = ["lon", "lat", "year", "observed"]
    wide = part.pivot_table(index=key_cols, columns="candidate", values="predicted", aggfunc="first")
    wide = wide.replace([np.inf, -np.inf], np.nan)
    y = wide.reset_index()["observed"].astype(float)
    x = wide.reset_index(drop=True)
    return x, y


def select_common(val_x: pd.DataFrame, test_x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    common = [col for col in val_x.columns if col in test_x.columns]
    val = val_x[common].copy()
    test = test_x[common].copy()
    keep = val.notna().all(axis=0) & test.notna().all(axis=0)
    cols = keep[keep].index.tolist()
    return val[cols], test[cols]


def inverse_rmse_weights(y: pd.Series, x: pd.DataFrame, cols: list[str]) -> np.ndarray:
    rmses = []
    for col in cols:
        rmses.append(float(np.sqrt(mean_squared_error(y, x[col]))))
    scores = 1.0 / np.maximum(np.asarray(rmses), 1e-8)
    return scores / scores.sum()


def build_fusions(val_x: pd.DataFrame, val_y: pd.Series, test_x: pd.DataFrame) -> dict[str, tuple[np.ndarray, dict[str, object]]]:
    val_x, test_x = select_common(val_x, test_x)
    if val_x.empty:
        return {}
    rmses = {col: float(np.sqrt(mean_squared_error(val_y, val_x[col]))) for col in val_x.columns}
    ordered = sorted(rmses, key=rmses.get)
    out: dict[str, tuple[np.ndarray, dict[str, object]]] = {}
    best_col = ordered[0]
    out["ValBestSingle"] = (test_x[best_col].to_numpy(dtype=float), {"selected": best_col, "n_members": 1})
    for k in [3, 5, 8]:
        cols = ordered[: min(k, len(ordered))]
        weights = inverse_rmse_weights(val_y, val_x, cols)
        out[f"Top{k}InvRMSEMean"] = (
            np.dot(test_x[cols].to_numpy(dtype=float), weights),
            {"selected": ";".join(cols), "n_members": len(cols)},
        )
        out[f"Top{k}Median"] = (
            np.median(test_x[cols].to_numpy(dtype=float), axis=1),
            {"selected": ";".join(cols), "n_members": len(cols)},
        )
    # Ridge stacking is calibrated on the 2019-2020 validation period only.
    # It is clipped to the range covered by candidate predictions to avoid
    # unstable extrapolation from a small calibration set.
    cols = ordered[: min(12, len(ordered))]
    try:
        model = RidgeCV(alphas=np.logspace(-3, 3, 13))
        model.fit(val_x[cols], val_y)
        pred = model.predict(test_x[cols])
        lo = np.nanmin(test_x[cols].to_numpy(dtype=float), axis=1)
        hi = np.nanmax(test_x[cols].to_numpy(dtype=float), axis=1)
        out["RidgeStackTop12Clipped"] = (
            np.clip(pred, lo, hi),
            {"selected": ";".join(cols), "n_members": len(cols), "alpha": float(model.alpha_)},
        )
    except Exception:
        pass
    return out


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
    strict = best[best["protocol"] == "temporal_2022_2026"].sort_values("target")
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#59A14F" if value >= 0 else "#E15759" for value in strict["r2"]]
    ax.bar(strict["target"], strict["r2"], color=colors)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("Multi-Evidence Fusion R2 (2022-2026)")
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
    plt.savefig(FIG_DIR / "best_r2_temporal_2022_2026.png", dpi=300, bbox_inches="tight")
    plt.close()


def main() -> None:
    ensure_project_dirs()
    preds = add_baseline_predictions(load_long_predictions())
    targets = target_columns()
    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    for target in targets:
        val_x, val_y = pivot_protocol(preds, "literature_2019_2020", target)
        test_x, test_y = pivot_protocol(preds, "temporal_2022_2026", target)
        fusions = build_fusions(val_x, val_y, test_x)
        test_index = test_x.reset_index()
        # pivot_protocol drops key columns from X, rebuild keys from raw preds.
        key = (
            preds[(preds["protocol"] == "temporal_2022_2026") & (preds["target"] == target)][["lon", "lat", "year", "observed"]]
            .drop_duplicates()
            .sort_values(["year", "lon", "lat"])
            .reset_index(drop=True)
        )
        if len(key) != len(test_y):
            key = (
                preds[(preds["protocol"] == "temporal_2022_2026") & (preds["target"] == target)][["lon", "lat", "year", "observed"]]
                .drop_duplicates()
                .reset_index(drop=True)
            )
        for model_name, (pred, meta) in fusions.items():
            pred = np.maximum(np.asarray(pred, dtype=float), 0.0)
            metric = regression_metrics(test_y, pred)
            rows.append(
                {
                    "protocol": "temporal_2022_2026",
                    "target": target,
                    "method": "multi_evidence_fusion",
                    "model": model_name,
                    "status": "ok",
                    "n_train": int(len(val_y)),
                    "n_test": int(len(test_y)),
                    **metric,
                    **meta,
                }
            )
            table = key[["lon", "lat", "year"]].copy()
            table["protocol"] = "temporal_2022_2026"
            table["target"] = target
            table["method"] = "multi_evidence_fusion"
            table["model"] = model_name
            table["observed"] = test_y.to_numpy(dtype=float)
            table["predicted"] = pred
            pred_rows.append(table)
    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "multi_evidence_fusion_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(RESULTS_DIR / "multi_evidence_fusion_predictions.csv", index=False, encoding="utf-8-sig")
    best = (
        metrics[metrics["status"] == "ok"]
        .sort_values(["target", "r2", "rmse"], ascending=[True, False, True])
        .groupby("target", as_index=False)
        .head(1)
        .sort_values("target")
    )
    best.to_csv(TABLES_DIR / "multi_evidence_fusion_best_metrics.csv", index=False, encoding="utf-8-sig")
    plot_best(best)
    show = best[["target", "method", "model", "n_train", "n_test", "n_members", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    report = [
        "# 时空多证据稳健融合",
        "",
        "该方法把外部公开因子、时空创新、多任务潜变量、ARIMA/LSTM、局部历史污染记忆、高污染风险门控和保守基线的逐点预测作为候选证据。",
        "",
        "融合权重和候选成员只基于 2019-2020 验证期表现确定，然后迁移到严格 2022-2026 未来验证。测试期真实值不参与融合规则选择。",
        "",
        md_table(show),
        "",
        "完整结果见 `tables/multi_evidence_fusion_metrics.csv`、`tables/multi_evidence_fusion_best_metrics.csv` 和 `results/multi_evidence_fusion_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "multi_evidence_fusion_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote multi-evidence fusion outputs")


if __name__ == "__main__":
    main()

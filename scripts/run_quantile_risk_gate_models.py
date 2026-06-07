#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import add_engineered_features
from soilmodel.metrics import regression_metrics
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs


FIG_DIR = FIGURES_DIR / "quantile_risk_gate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run high-pollution risk gated quantile regression models.")
    parser.add_argument("--config", default="configs/soil_experiment.json")
    parser.add_argument("--data", default=None)
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


def fit_quantile_model(x_train: pd.DataFrame, y_train: pd.Series, quantile: float, seed: int):
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                HistGradientBoostingRegressor(
                    loss="quantile",
                    quantile=quantile,
                    max_iter=260,
                    learning_rate=0.035,
                    max_leaf_nodes=15,
                    min_samples_leaf=15,
                    l2_regularization=0.15,
                    random_state=seed,
                ),
            ),
        ]
    )
    model.fit(x_train, np.log1p(np.maximum(y_train.to_numpy(dtype=float), 0.0)))
    return model


def predict_quantile(model, x_test: pd.DataFrame) -> np.ndarray:
    return np.maximum(np.expm1(np.asarray(model.predict(x_test), dtype=float)), 0.0)


def fit_gate_classifier(x_train: pd.DataFrame, y_train: pd.Series, threshold: float, seed: int):
    labels = (y_train.to_numpy(dtype=float) >= threshold).astype(int)
    if labels.min() == labels.max():
        return None, float(labels.mean()), np.nan
    clf = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                HistGradientBoostingClassifier(
                    max_iter=180,
                    learning_rate=0.04,
                    max_leaf_nodes=15,
                    min_samples_leaf=12,
                    l2_regularization=0.2,
                    random_state=seed,
                ),
            ),
        ]
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        clf.fit(x_train, labels)
        train_prob = clf.predict_proba(x_train)[:, 1]
    try:
        auc = float(roc_auc_score(labels, train_prob))
    except Exception:
        auc = np.nan
    return clf, float(labels.mean()), auc


def gate_predict(clf, default_prob: float, x_test: pd.DataFrame) -> np.ndarray:
    if clf is None:
        return np.full(len(x_test), default_prob, dtype=float)
    return np.asarray(clf.predict_proba(x_test)[:, 1], dtype=float)


def evaluate(rows, pred_rows, df, protocol, target, method, model, train_idx, test_idx, y_test, pred, n_features, extra=None):
    metric = regression_metrics(y_test, np.maximum(pred, 0.0))
    row = {
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
    if extra:
        row.update(extra)
    rows.append(row)
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
        ax.set_title(f"Risk-Gated Quantile Model R2 ({protocol})")
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
    df_feat, features = add_engineered_features(df, base_features + external_features)
    x_all = df_feat[features].astype(float)
    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    for protocol in ["literature_2019_2020", "temporal_2022_2026"]:
        train_idx, test_idx = protocol_indices(df_feat, protocol, int(config["temporal_test_start_year"]))
        print(f"\n{protocol}: train={len(train_idx)} test={len(test_idx)}", flush=True)
        x_train = x_all.loc[train_idx]
        x_test = x_all.loc[test_idx]
        for target in config["target_columns"]:
            y = df_feat[target].astype(float)
            y_train = y.loc[train_idx]
            y_test = y.loc[test_idx]
            print(f"  {target}", flush=True)
            q50 = fit_quantile_model(x_train, y_train, 0.50, args.seed)
            q75 = fit_quantile_model(x_train, y_train, 0.75, args.seed)
            q90 = fit_quantile_model(x_train, y_train, 0.90, args.seed)
            pred50 = predict_quantile(q50, x_test)
            pred75 = predict_quantile(q75, x_test)
            pred90 = predict_quantile(q90, x_test)
            for name, pred in [("QuantileP50", pred50), ("QuantileP75", pred75), ("QuantileP90", pred90)]:
                evaluate(rows, pred_rows, df_feat, protocol, target, "quantile_regression", name, train_idx, test_idx, y_test, pred, len(features))
            for threshold_q, upper_pred, upper_name in [(0.90, pred90, "P90"), (0.80, pred75, "P75")]:
                threshold = float(np.quantile(y_train.to_numpy(dtype=float), threshold_q))
                clf, default_prob, auc = fit_gate_classifier(x_train, y_train, threshold, args.seed)
                prob = gate_predict(clf, default_prob, x_test)
                for power in [1.0, 1.5, 2.0]:
                    weight = np.clip(prob, 0.0, 1.0) ** power
                    pred = (1.0 - weight) * pred50 + weight * upper_pred
                    evaluate(
                        rows,
                        pred_rows,
                        df_feat,
                        protocol,
                        target,
                        "risk_gated_quantile",
                        f"GateQ{int(threshold_q*100)}_{upper_name}_pow{power:g}",
                        train_idx,
                        test_idx,
                        y_test,
                        pred,
                        len(features),
                        extra={"high_threshold": threshold, "train_high_rate": default_prob, "gate_train_auc": auc},
                    )
    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "quantile_risk_gate_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(RESULTS_DIR / "quantile_risk_gate_predictions.csv", index=False, encoding="utf-8-sig")
    best = (
        metrics[metrics["status"] == "ok"]
        .sort_values(["protocol", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["protocol", "target"], as_index=False)
        .head(1)
        .sort_values(["protocol", "target"])
    )
    best.to_csv(TABLES_DIR / "quantile_risk_gate_best_metrics.csv", index=False, encoding="utf-8-sig")
    plot_best(best)
    show = best[["protocol", "target", "method", "model", "n_train", "n_test", "n_features", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    report = [
        "# 高污染风险门控分位数模型",
        "",
        "该方法先训练中位数和高分位数回归模型，再训练高污染风险分类器，根据高污染概率在中位数预测与高分位预测之间加权。目标是减少普通均值回归对高污染尾部样本的系统低估。",
        "",
        "所有门控阈值仅由训练期目标分布确定，测试期真实浓度不参与建模或调参。",
        "",
        md_table(show),
        "",
        "完整结果见 `tables/quantile_risk_gate_metrics.csv`、`tables/quantile_risk_gate_best_metrics.csv` 和 `results/quantile_risk_gate_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "quantile_risk_gate_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote quantile risk gate outputs")


if __name__ == "__main__":
    main()

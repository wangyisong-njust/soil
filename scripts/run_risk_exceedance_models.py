#!/usr/bin/env python
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import target_columns
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


QUANTILES = [0.90, 0.95]
OUT_DIR = FIGURES_DIR / "risk_exceedance"


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


def feature_columns(data: pd.DataFrame, targets: list[str]) -> list[str]:
    numeric = data.select_dtypes(include=[np.number]).columns.tolist()
    excluded = set(targets)
    return [col for col in numeric if col not in excluded]


def build_models(random_state: int = 42) -> dict[str, object]:
    return {
        "LogisticL2": make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight="balanced", random_state=random_state),
        ),
        "RandomForest": make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestClassifier(
                n_estimators=500,
                min_samples_leaf=3,
                class_weight="balanced_subsample",
                random_state=random_state,
                n_jobs=2,
            ),
        ),
        "ExtraTrees": make_pipeline(
            SimpleImputer(strategy="median"),
            ExtraTreesClassifier(
                n_estimators=600,
                min_samples_leaf=2,
                class_weight="balanced",
                random_state=random_state,
                n_jobs=2,
            ),
        ),
        "HistGB": make_pipeline(
            SimpleImputer(strategy="median"),
            HistGradientBoostingClassifier(
                max_iter=260,
                learning_rate=0.04,
                l2_regularization=0.1,
                min_samples_leaf=8,
                random_state=random_state,
            ),
        ),
    }


def predict_proba(model: object, x: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(x)[:, 1], dtype=float)
    proba = model[-1].predict_proba(model[:-1].transform(x))[:, 1]
    return np.asarray(proba, dtype=float)


def safe_auc(y_true: np.ndarray, score: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return np.nan
    return float(roc_auc_score(y_true, score))


def safe_ap(y_true: np.ndarray, score: np.ndarray) -> float:
    if int(np.sum(y_true)) == 0:
        return np.nan
    return float(average_precision_score(y_true, score))


def best_threshold_by_f1(y_true: np.ndarray, score: np.ndarray) -> tuple[float, float]:
    if int(np.sum(y_true)) == 0:
        return 0.5, 0.0
    candidates = np.unique(np.quantile(score, np.linspace(0.05, 0.95, 19)))
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold in candidates:
        pred = (score >= threshold).astype(int)
        f1 = float(f1_score(y_true, pred, zero_division=0))
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = float(threshold)
    return best_threshold, best_f1


def classification_metrics(y_true: np.ndarray, score: np.ndarray, threshold: float) -> dict[str, float]:
    pred = (score >= threshold).astype(int)
    return {
        "auc": safe_auc(y_true, score),
        "average_precision": safe_ap(y_true, score),
        "threshold": float(threshold),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "positive_rate": float(np.mean(y_true)),
        "predicted_positive_rate": float(np.mean(pred)),
    }


def plot_cfg(best: pd.DataFrame, focus_targets: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    part = best[(best["target"].isin(focus_targets)) & (best["quantile"] == 0.90)].copy()
    if part.empty:
        return
    x = np.arange(len(part))
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.bar(x - 0.18, part["auc"], width=0.36, label="AUC", color="#4C78A8")
    ax.bar(x + 0.18, part["average_precision"], width=0.36, label="AP", color="#F28E2B")
    ax.set_xticks(x)
    ax.set_xticklabels(part["target"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score")
    ax.set_title("High-pollution risk detection (q90)")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.22)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "cfg_q90_risk_detection_scores.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_project_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = target_columns()
    focus_targets = [item for item in ["C", "F", "G"] if item in targets] or targets[: min(3, len(targets))]
    data = pd.read_csv(preferred_processed_data_path())
    data["year"] = data["year"].round().astype(int)
    features = feature_columns(data, targets)
    core_train = data[data["year"].between(2000, 2018)].copy()
    val = data[data["year"].between(2019, 2020)].copy()
    full_train = data[data["year"] < 2022].copy()
    test = data[data["year"] >= 2022].copy()
    models = build_models()

    rows: list[dict[str, object]] = []
    selected_rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []

    for target in targets:
        for quantile in QUANTILES:
            threshold_value = float(core_train[target].quantile(quantile))
            y_core = (core_train[target].to_numpy(dtype=float) >= threshold_value).astype(int)
            y_val = (val[target].to_numpy(dtype=float) >= threshold_value).astype(int)
            y_full = (full_train[target].to_numpy(dtype=float) >= threshold_value).astype(int)
            y_test = (test[target].to_numpy(dtype=float) >= threshold_value).astype(int)
            val_records = []
            for model_name, model in models.items():
                if len(np.unique(y_core)) < 2:
                    continue
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model.fit(core_train[features], y_core)
                    val_score = predict_proba(model, val[features])
                val_threshold, _ = best_threshold_by_f1(y_val, val_score)
                val_metric = classification_metrics(y_val, val_score, val_threshold)
                record = {
                    "target": target,
                    "quantile": quantile,
                    "threshold_value": threshold_value,
                    "model": model_name,
                    "split": "validation_2019_2020",
                    "n_train": int(len(core_train)),
                    "n_eval": int(len(val)),
                    "n_positive": int(np.sum(y_val)),
                    **val_metric,
                }
                rows.append(record)
                val_records.append(record)

            if not val_records:
                continue
            selection = sorted(
                val_records,
                key=lambda item: (
                    -np.nan_to_num(item["average_precision"], nan=-1.0),
                    -np.nan_to_num(item["auc"], nan=-1.0),
                    -item["f1"],
                ),
            )[0]
            model = build_models()[selection["model"]]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(full_train[features], y_full)
                test_score = predict_proba(model, test[features])
            test_metric = classification_metrics(y_test, test_score, float(selection["threshold"]))
            selected = {
                "target": target,
                "quantile": quantile,
                "threshold_value": threshold_value,
                "model": selection["model"],
                "split": "test_2022_2026",
                "n_train": int(len(full_train)),
                "n_eval": int(len(test)),
                "n_positive": int(np.sum(y_test)),
                "validation_auc": selection["auc"],
                "validation_average_precision": selection["average_precision"],
                "validation_f1": selection["f1"],
                **test_metric,
            }
            selected_rows.append(selected)
            rows.append(selected)
            pred = test[["lon", "lat", "year"]].copy()
            pred["target"] = target
            pred["quantile"] = quantile
            pred["threshold_value"] = threshold_value
            pred["model"] = selection["model"]
            pred["observed"] = test[target].to_numpy(dtype=float)
            pred["is_exceedance"] = y_test
            pred["risk_probability"] = test_score
            pred["risk_prediction"] = (test_score >= float(selection["threshold"])).astype(int)
            pred_rows.append(pred)

    metrics = pd.DataFrame(rows)
    best = pd.DataFrame(selected_rows).sort_values(["quantile", "target"])
    metrics.to_csv(TABLES_DIR / "risk_exceedance_metrics.csv", index=False, encoding="utf-8-sig")
    best.to_csv(TABLES_DIR / "risk_exceedance_best_metrics.csv", index=False, encoding="utf-8-sig")
    pd.concat(pred_rows, ignore_index=True).to_csv(
        RESULTS_DIR / "risk_exceedance_predictions.csv", index=False, encoding="utf-8-sig"
    )
    plot_cfg(best, focus_targets)

    show = best[best["target"].isin(["C", "F", "G"])][
        [
            "target",
            "quantile",
            "threshold_value",
            "model",
            "n_positive",
            "auc",
            "average_precision",
            "precision",
            "recall",
            "f1",
        ]
    ].copy()
    for col in ["quantile", "threshold_value", "auc", "average_precision", "precision", "recall", "f1"]:
        show[col] = show[col].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    report = [
        "# 高污染超阈值风险预警模型",
        "",
        "该实验把连续浓度预测补充为高污染风险识别任务。阈值使用 2000-2018 训练核心期的 q90/q95；模型在 2019-2020 验证期按 AP/AUC/F1 选型，再用 2000-2021 重训并固定评估 2022-2026。该结果不替代连续浓度 R2，而是作为风险预警和不确定性分析补充。",
        "",
        "## 重点目标风险识别结果",
        "",
        md_table(show),
        "",
        "图件：`figures/risk_exceedance/cfg_q90_risk_detection_scores.png`。",
        "",
        "完整指标见 `tables/risk_exceedance_metrics.csv`、`tables/risk_exceedance_best_metrics.csv`；预测明细见 `results/risk_exceedance_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "risk_exceedance_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote risk exceedance model outputs")


if __name__ == "__main__":
    main()

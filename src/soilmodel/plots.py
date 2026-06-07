from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.inspection import permutation_importance

from .models import final_estimator_from_wrapped, transformed_features_from_wrapped


STYLE = {
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 140,
    "savefig.dpi": 220,
}


def setup_plot_style() -> None:
    sns.set_theme(style="whitegrid", rc=STYLE)


def save_actual_vs_predicted(y_true, y_pred, title: str, path: Path) -> None:
    setup_plot_style()
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    ax.scatter(y_true, y_pred, s=28, alpha=0.72, color="#2a6f97", edgecolor="white", linewidth=0.4)
    low = float(min(y_true.min(), y_pred.min()))
    high = float(max(y_true.max(), y_pred.max()))
    ax.plot([low, high], [low, high], color="#c44536", linewidth=1.4, label="1:1")
    ax.set_xlabel("Observed concentration")
    ax.set_ylabel("Predicted concentration")
    ax.set_title(title)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_residual_plot(y_true, y_pred, title: str, path: Path) -> None:
    setup_plot_style()
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    residual = y_true - y_pred
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    ax.scatter(y_pred, residual, s=28, alpha=0.72, color="#4d908e", edgecolor="white", linewidth=0.4)
    ax.axhline(0, color="#c44536", linewidth=1.2)
    ax.set_xlabel("Predicted concentration")
    ax.set_ylabel("Residual")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_metric_comparison(metrics: pd.DataFrame, target: str, protocol: str, path: Path) -> None:
    setup_plot_style()
    part = metrics[(metrics["target"] == target) & (metrics["protocol"] == protocol)].copy()
    part = part.sort_values("r2", ascending=False)
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    sns.barplot(data=part, x="r2", y="model", ax=ax, color="#577590")
    ax.axvline(0, color="#6c757d", linewidth=0.8)
    ax.set_xlabel("R2")
    ax.set_ylabel("")
    ax.set_title(f"{target} model comparison ({protocol})")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_bar(items: pd.DataFrame, value_col: str, title: str, path: Path) -> None:
    setup_plot_style()
    items = items.sort_values(value_col, ascending=True)
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    ax.barh(items["feature"], items[value_col], color="#577590")
    ax.set_xlabel(value_col)
    ax.set_ylabel("")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_feature_importance(
    model,
    x_eval: pd.DataFrame,
    y_eval: pd.Series,
    feature_names: list[str],
    title: str,
    path: Path,
    random_state: int,
    top_n: int = 12,
) -> pd.DataFrame:
    estimator = final_estimator_from_wrapped(model)
    if hasattr(estimator, "feature_importances_"):
        values = np.asarray(estimator.feature_importances_, dtype=float)
    else:
        result = permutation_importance(
            model,
            x_eval,
            y_eval,
            scoring="r2",
            n_repeats=8,
            random_state=random_state,
            n_jobs=-1,
        )
        values = np.asarray(result.importances_mean, dtype=float)

    table = pd.DataFrame({"feature": feature_names, "importance": values})
    table = table.sort_values("importance", ascending=False).head(top_n)
    _plot_bar(table, "importance", title, path)
    return table


def save_shap_importance(
    model,
    x_sample: pd.DataFrame,
    feature_names: list[str],
    title: str,
    path: Path,
    top_n: int = 12,
) -> pd.DataFrame:
    import shap

    estimator = final_estimator_from_wrapped(model)
    x_trans = transformed_features_from_wrapped(model, x_sample)
    explainer = shap.TreeExplainer(estimator)
    values = explainer.shap_values(x_trans)
    if isinstance(values, list):
        values = values[0]
    values = np.asarray(values)
    if values.ndim == 3:
        values = values[:, :, 0]
    mean_abs = np.abs(values).mean(axis=0)
    table = pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_abs})
    table = table.sort_values("mean_abs_shap", ascending=False).head(top_n)
    _plot_bar(table, "mean_abs_shap", title, path)
    return table


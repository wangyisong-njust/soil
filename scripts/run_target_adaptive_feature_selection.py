#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_selection import f_regression
from sklearn.impute import SimpleImputer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import DOCS_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs, preferred_processed_data_path


DEFAULT_MODELS = ["ExtraTrees", "HistGBR", "ElasticNet", "XGBoost", "LightGBM"]
DEFAULT_K = ["all", "16", "24", "36", "48", "64"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Target-adaptive feature group and top-k selection.")
    parser.add_argument("--config", default="configs/soil_experiment.json")
    parser.add_argument("--data", default=None, help="Optional CSV path. Defaults to the best available processed data.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    parser.add_argument("--top-k", default=",".join(DEFAULT_K))
    parser.add_argument("--n-jobs", type=int, default=2)
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
    if protocol == "selector_validation_2019_2020":
        return index[df["year"].between(2000, 2018).to_numpy()], index[df["year"].between(2019, 2020).to_numpy()]
    if protocol == "temporal_2022_2026":
        return index[(df["year"] < 2022).to_numpy()], index[(df["year"] >= 2022).to_numpy()]
    raise ValueError(protocol)


def feature_groups(df: pd.DataFrame, base_features: list[str]) -> dict[str, list[str]]:
    sg_np = [col for col in df.columns if col.startswith(("sg_", "np_"))]
    osm = [col for col in df.columns if col.startswith("osm_")]
    osm_pollution = [
        col
        for col in osm
        if any(token in col for token in ["industrial", "mining", "pollution", "built_landuse", "railway", "traffic"])
    ]
    raster = [col for col in df.columns if col.startswith(("viirs_", "ghsl_", "wc_"))]
    viirs_ghsl = [col for col in df.columns if col.startswith(("viirs_", "ghsl_"))]
    groups = {
        "baseline": base_features,
        "soil_climate": base_features + sg_np,
        "osm_pollution": base_features + sg_np + osm_pollution,
        "osm_activity": base_features + sg_np + osm,
        "raster_activity": base_features + viirs_ghsl,
        "raster_landcover": base_features + raster,
        "human_activity": base_features + osm + raster,
        "all_external": base_features + sg_np + osm + raster,
    }
    return {name: list(dict.fromkeys(cols)) for name, cols in groups.items()}


def target_design(
    df_feat: pd.DataFrame,
    engineered_cols: list[str],
    y: pd.Series,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    use_target_spatial_lag: bool,
    k_neighbors: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    x_base = df_feat[engineered_cols].astype(float)
    if not use_target_spatial_lag:
        return x_base.loc[train_idx], x_base.loc[test_idx]
    x_train = add_target_spatial_lag_features(
        df_feat, x_base, y, train_idx, train_idx, k=k_neighbors, leave_one_out=True
    )
    x_test = add_target_spatial_lag_features(
        df_feat, x_base, y, train_idx, test_idx, k=k_neighbors, leave_one_out=False
    )
    return x_train, x_test


def select_columns(x_train: pd.DataFrame, y_train: pd.Series, top_k: str) -> list[str]:
    cols = x_train.columns.tolist()
    if top_k == "all":
        return cols
    k = min(int(top_k), len(cols))
    if k >= len(cols):
        return cols
    imputer = SimpleImputer(strategy="median")
    x_imp = imputer.fit_transform(x_train)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        scores, _ = f_regression(x_imp, y_train.to_numpy(dtype=float))
    scores = np.nan_to_num(scores, nan=-np.inf, posinf=-np.inf, neginf=-np.inf)
    order = np.argsort(scores)[::-1][:k]
    selected = [cols[i] for i in order]
    forced = [col for col in ["year", "year_offset", "lon", "lat", "target_spatial_idw"] if col in cols]
    return list(dict.fromkeys(forced + selected))


def fit_predict(spec, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        pred = np.asarray(model.predict(x_test), dtype=float).reshape(-1)
    return np.maximum(pred, 0.0)


def evaluate_candidate(
    df: pd.DataFrame,
    base_cols: list[str],
    target: str,
    feature_set: str,
    selected_k: str,
    model_name: str,
    spec,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    config: dict[str, object],
) -> tuple[dict[str, object], pd.DataFrame, list[str]]:
    df_feat, engineered_cols = add_engineered_features(df, base_cols)
    y = df_feat[target].astype(float)
    x_train, x_test = target_design(
        df_feat,
        engineered_cols,
        y,
        train_idx,
        test_idx,
        bool(config.get("use_target_spatial_lag_features", False)),
        int(config.get("target_spatial_lag_k", 12)),
    )
    cols = select_columns(x_train, y.loc[train_idx], selected_k)
    pred = fit_predict(spec, x_train[cols], y.loc[train_idx], x_test[cols])
    metrics = regression_metrics(y.loc[test_idx], pred)
    row = {
        "target": target,
        "feature_set": feature_set,
        "top_k": selected_k,
        "model": model_name,
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "n_input_features": int(len(engineered_cols) + (len(TARGET_SPATIAL_FEATURES) if config.get("use_target_spatial_lag_features") else 0)),
        "n_selected_features": int(len(cols)),
        **metrics,
    }
    pred_table = df_feat.loc[test_idx, ["lon", "lat", "year"]].copy()
    pred_table["target"] = target
    pred_table["feature_set"] = feature_set
    pred_table["top_k"] = selected_k
    pred_table["model"] = model_name
    pred_table["observed"] = y.loc[test_idx].to_numpy()
    pred_table["predicted"] = pred
    return row, pred_table, cols


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    data_path = ROOT / args.data if args.data else preferred_processed_data_path()
    df = pd.read_csv(data_path)
    df["year"] = df["year"].round().astype(int)
    groups = feature_groups(df, list(config["base_feature_columns"]))
    requested_models = [item.strip() for item in args.models.split(",") if item.strip()]
    top_k_values = [item.strip() for item in args.top_k.split(",") if item.strip()]
    registry = build_model_registry(128, random_state=int(config["random_seed"]), n_jobs=args.n_jobs)
    registry = {name: registry[name] for name in requested_models if name in registry}

    selector_train_idx, selector_val_idx = protocol_indices(df, "selector_validation_2019_2020")
    strict_train_idx, strict_test_idx = protocol_indices(df, "temporal_2022_2026")
    validation_rows: list[dict[str, object]] = []
    strict_rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []
    selection_records: list[dict[str, object]] = []

    for target in config["target_columns"]:
        print(f"\nSelecting for target {target}", flush=True)
        for feature_set, cols in groups.items():
            for top_k in top_k_values:
                for model_name, spec in registry.items():
                    try:
                        row, _, selected_cols = evaluate_candidate(
                            df,
                            cols,
                            target,
                            feature_set,
                            top_k,
                            model_name,
                            spec,
                            selector_train_idx,
                            selector_val_idx,
                            config,
                        )
                        row["protocol"] = "selector_validation_2019_2020"
                        validation_rows.append(row)
                        selection_records.append(
                            {
                                "target": target,
                                "feature_set": feature_set,
                                "top_k": top_k,
                                "model": model_name,
                                "selected_features": ",".join(selected_cols),
                            }
                        )
                    except Exception as exc:
                        validation_rows.append(
                            {
                                "protocol": "selector_validation_2019_2020",
                                "target": target,
                                "feature_set": feature_set,
                                "top_k": top_k,
                                "model": model_name,
                                "status": f"failed: {exc}",
                                "r2": np.nan,
                                "r2_log1p": np.nan,
                                "rmse": np.nan,
                                "mae": np.nan,
                                "mape": np.nan,
                            }
                        )
        val_df = pd.DataFrame(validation_rows)
        target_val = val_df[(val_df["target"] == target) & val_df["r2"].notna()].copy()
        best_val = target_val.sort_values(["r2", "rmse"], ascending=[False, True]).iloc[0]
        print(
            f"  selected {best_val.feature_set}/{best_val.top_k}/{best_val.model} "
            f"val_r2={best_val.r2:.4f}",
            flush=True,
        )
        spec = registry[str(best_val["model"])]
        strict_row, strict_pred, selected_cols = evaluate_candidate(
            df,
            groups[str(best_val["feature_set"])],
            target,
            str(best_val["feature_set"]),
            str(best_val["top_k"]),
            str(best_val["model"]),
            spec,
            strict_train_idx,
            strict_test_idx,
            config,
        )
        strict_row["protocol"] = "temporal_2022_2026"
        strict_row["selection_val_r2"] = float(best_val["r2"])
        strict_row["method"] = "target_adaptive_feature_selection"
        strict_rows.append(strict_row)
        strict_pred["protocol"] = "temporal_2022_2026"
        pred_rows.append(strict_pred)
        selection_records.append(
            {
                "target": target,
                "feature_set": str(best_val["feature_set"]),
                "top_k": str(best_val["top_k"]),
                "model": str(best_val["model"]),
                "selected_for_strict": 1,
                "selected_features": ",".join(selected_cols),
            }
        )

    validation = pd.DataFrame(validation_rows)
    strict = pd.DataFrame(strict_rows).sort_values("target")
    validation.to_csv(TABLES_DIR / "target_adaptive_feature_selection_validation_metrics.csv", index=False, encoding="utf-8-sig")
    strict.to_csv(TABLES_DIR / "target_adaptive_feature_selection_best_metrics.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(selection_records).to_csv(TABLES_DIR / "target_adaptive_feature_selection_selected_features.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(
            RESULTS_DIR / "target_adaptive_feature_selection_predictions.csv", index=False, encoding="utf-8-sig"
        )

    show = strict[["target", "feature_set", "top_k", "model", "selection_val_r2", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["selection_val_r2", "r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda x: f"{x:.4f}")
    report = [
        "# 目标自适应特征筛选模型",
        "",
        "该实验只使用 2000-2018 训练、2019-2020 内部验证来选择每个重金属的特征组、top-k 特征数和模型；选择完成后固定方案，用 2000-2021 重新训练并评估 2022-2026。该设计用于减少高维外部变量对不同目标的噪声影响。",
        "",
        md_table(show),
        "",
        "完整内部验证结果见 `tables/target_adaptive_feature_selection_validation_metrics.csv`；严格未来验证结果见 `tables/target_adaptive_feature_selection_best_metrics.csv`。",
        "",
    ]
    (DOCS_DIR / "target_adaptive_feature_selection_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Wrote target-adaptive feature selection outputs")


if __name__ == "__main__":
    main()

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors


RANGE_PATTERN = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*-\s*([+-]?\d+(?:\.\d+)?)\s*$")


def parse_numeric_cell(value: object) -> float:
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.number)):
        return float(value)
    text = str(value).replace("\u00a0", " ").strip()
    text = re.sub(r"(?<=\d)\.\s+(?=\d)", ".", text)
    text = re.sub(r"\s+", "", text)
    match = RANGE_PATTERN.match(text)
    if match:
        low, high = map(float, match.groups())
        return (low + high) / 2.0
    return float(text)


def clean_soil_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    for col in cleaned.columns:
        cleaned[col] = cleaned[col].map(parse_numeric_cell)
    swap_mask = ((cleaned["lat"].abs() > 90) & (cleaned["lon"].abs() <= 90)) | (
        (cleaned["lat"] > 55) & (cleaned["lon"] < 70)
    )
    cleaned["coord_swapped_flag"] = swap_mask.astype(int)
    if swap_mask.any():
        lon = cleaned.loc[swap_mask, "lon"].copy()
        cleaned.loc[swap_mask, "lon"] = cleaned.loc[swap_mask, "lat"].to_numpy()
        cleaned.loc[swap_mask, "lat"] = lon.to_numpy()
    cleaned["year"] = cleaned["year"].round().astype(int)
    return cleaned


def read_and_clean_excel(path: str | Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    return clean_soil_dataframe(df)


def apply_quality_cleaning(
    df: pd.DataFrame,
    target_columns: list[str],
    base_feature_columns: list[str],
    strategy: str = "quality",
    duplicate_decimals: int = 6,
    driver_winsor_limits: tuple[float, float] = (0.005, 0.995),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply documented, publication-defensible cleaning rules.

    The target-removal variants are intentionally separated from the default
    quality strategy because they change the evaluation sample.
    """
    if strategy in {"basic", "none", ""}:
        return df.copy(), {"strategy": strategy or "basic", "n_input": int(len(df)), "n_output": int(len(df))}

    target_multiplier_by_strategy = {
        "quality": None,
        "quality_target_mild": 3.0,
        "quality_target_strict": 2.5,
    }
    if strategy not in target_multiplier_by_strategy:
        raise ValueError(f"Unknown cleaning strategy: {strategy}")

    cleaned = df.copy()
    report: dict[str, Any] = {
        "strategy": strategy,
        "n_input": int(len(cleaned)),
        "duplicate_decimals": duplicate_decimals,
        "driver_winsor_limits": list(driver_winsor_limits),
    }

    required = ["lon", "lat", "year", *target_columns]
    required_missing = cleaned[required].isna().any(axis=1)
    report["n_required_missing_rows_removed"] = int(required_missing.sum())
    cleaned = cleaned.loc[~required_missing].copy()

    coord_mask = cleaned["lon"].between(70, 140) & cleaned["lat"].between(15, 55)
    report["n_coordinate_outside_broad_china_bounds_removed"] = int((~coord_mask).sum())
    cleaned = cleaned.loc[coord_mask].copy()

    cleaned["lon_round_for_group"] = cleaned["lon"].round(duplicate_decimals)
    cleaned["lat_round_for_group"] = cleaned["lat"].round(duplicate_decimals)
    duplicate_rows = int(cleaned.duplicated(["lon_round_for_group", "lat_round_for_group", "year"], keep=False).sum())
    duplicate_groups = int(
        cleaned.groupby(["lon_round_for_group", "lat_round_for_group", "year"]).size().gt(1).sum()
    )
    numeric_cols = cleaned.select_dtypes(include=[np.number]).columns.tolist()
    aggregated = (
        cleaned.groupby(["lon_round_for_group", "lat_round_for_group", "year"], as_index=False)[numeric_cols]
        .median(numeric_only=True)
        .reset_index(drop=True)
    )
    group_sizes = (
        cleaned.groupby(["lon_round_for_group", "lat_round_for_group", "year"], as_index=False)
        .size()
        .rename(columns={"size": "duplicate_group_size"})
    )
    cleaned = aggregated.merge(group_sizes, on=["lon_round_for_group", "lat_round_for_group", "year"], how="left")
    cleaned["lon"] = cleaned["lon_round_for_group"]
    cleaned["lat"] = cleaned["lat_round_for_group"]
    cleaned = cleaned.drop(columns=["lon_round_for_group", "lat_round_for_group"], errors="ignore")
    report["n_duplicate_rows_involved"] = duplicate_rows
    report["n_duplicate_groups_aggregated"] = duplicate_groups
    report["n_after_duplicate_aggregation"] = int(len(cleaned))

    imputed: dict[str, int] = {}
    feature_cols = [c for c in base_feature_columns if c in cleaned.columns and c not in ["lon", "lat", "year"]]
    for col in feature_cols:
        n_missing = int(cleaned[col].isna().sum())
        if n_missing:
            cleaned[col] = cleaned[col].fillna(float(cleaned[col].median()))
            imputed[col] = n_missing
    report["feature_missing_imputed_by_median"] = imputed

    winsorized: dict[str, dict[str, float | int]] = {}
    low_q, high_q = driver_winsor_limits
    skip_winsor = {"lon", "lat", "year", "coord_swapped_flag", "duplicate_group_size"}
    for col in feature_cols:
        if col in skip_winsor:
            continue
        low = float(cleaned[col].quantile(low_q))
        high = float(cleaned[col].quantile(high_q))
        low_count = int((cleaned[col] < low).sum())
        high_count = int((cleaned[col] > high).sum())
        if low_count or high_count:
            cleaned[col] = cleaned[col].clip(low, high)
            winsorized[col] = {
                "low": low,
                "high": high,
                "n_low_capped": low_count,
                "n_high_capped": high_count,
            }
    report["driver_winsorized"] = winsorized

    multiplier = target_multiplier_by_strategy[strategy]
    target_outliers: dict[str, dict[str, float | int]] = {}
    if multiplier is not None:
        keep = pd.Series(True, index=cleaned.index)
        for col in target_columns:
            values = np.log1p(cleaned[col].astype(float))
            q1 = float(values.quantile(0.25))
            q3 = float(values.quantile(0.75))
            iqr = q3 - q1
            low = q1 - multiplier * iqr
            high = q3 + multiplier * iqr
            col_keep = values.between(low, high)
            target_outliers[col] = {
                "log_low": low,
                "log_high": high,
                "n_removed_if_applied_alone": int((~col_keep).sum()),
            }
            keep &= col_keep
        report["n_target_outlier_rows_removed"] = int((~keep).sum())
        report["target_log_iqr_multiplier"] = multiplier
        report["target_outlier_rules"] = target_outliers
        cleaned = cleaned.loc[keep].copy()
    else:
        report["n_target_outlier_rows_removed"] = 0

    cleaned = cleaned.sort_values(["year", "lon", "lat"]).reset_index(drop=True)
    report["n_output"] = int(len(cleaned))
    report["n_removed_total"] = int(report["n_input"] - report["n_output"])
    return cleaned, report


def add_engineered_features(df: pd.DataFrame, base_features: list[str]) -> tuple[pd.DataFrame, list[str]]:
    out = df.copy()
    min_year = int(out["year"].min())
    out["year_offset"] = out["year"] - min_year
    out["year_offset_sq"] = out["year_offset"] ** 2
    out["lon_lat"] = out["lon"] * out["lat"]
    out["lon_sq"] = out["lon"] ** 2
    out["lat_sq"] = out["lat"] ** 2

    engineered = ["year_offset", "year_offset_sq", "lon_lat", "lon_sq", "lat_sq"]
    feature_cols = list(dict.fromkeys(base_features + engineered))
    return out, feature_cols


def dataset_profile(df: pd.DataFrame, target_columns: list[str]) -> dict[str, object]:
    point_counts = (
        df.assign(lon_round=df["lon"].round(6), lat_round=df["lat"].round(6))
        .groupby(["lon_round", "lat_round"])
        .size()
    )
    return {
        "n_rows": int(len(df)),
        "n_columns": int(df.shape[1]),
        "year_min": int(df["year"].min()),
        "year_max": int(df["year"].max()),
        "n_years": int(df["year"].nunique()),
        "n_unique_points_rounded6": int(len(point_counts)),
        "n_repeated_points_rounded6": int((point_counts > 1).sum()),
        "max_repeat_per_point_rounded6": int(point_counts.max()),
        "n_coordinate_swapped": int(df.get("coord_swapped_flag", pd.Series(dtype=float)).sum()),
        "targets": target_columns,
        "year_counts": {int(k): int(v) for k, v in df["year"].value_counts().sort_index().items()},
        "missing_by_column": {str(k): int(v) for k, v in df.isna().sum().items()},
    }


TARGET_SPATIAL_FEATURES = ["target_spatial_mean", "target_spatial_idw", "target_spatial_min_dist"]


def add_target_spatial_lag_features(
    df: pd.DataFrame,
    x_base: pd.DataFrame,
    y: pd.Series,
    fit_idx,
    pred_idx,
    k: int = 12,
    leave_one_out: bool = False,
) -> pd.DataFrame:
    fit_idx = np.asarray(fit_idx)
    pred_idx = np.asarray(pred_idx)
    x_out = x_base.loc[pred_idx].copy()
    if len(fit_idx) == 0:
        for col in TARGET_SPATIAL_FEATURES:
            x_out[col] = np.nan
        return x_out

    coords_fit = df.loc[fit_idx, ["lon", "lat"]].to_numpy(dtype=float)
    y_fit = y.loc[fit_idx].to_numpy(dtype=float)
    n_neighbors = min(len(fit_idx), k + 1 if leave_one_out and len(fit_idx) > 1 else k)
    nn = NearestNeighbors(n_neighbors=n_neighbors)
    nn.fit(coords_fit)
    distances, indices = nn.kneighbors(df.loc[pred_idx, ["lon", "lat"]].to_numpy(dtype=float))
    fit_original_index = np.asarray(fit_idx)

    means: list[float] = []
    idw_values: list[float] = []
    min_distances: list[float] = []
    for row_pos, (dist_row, ind_row) in enumerate(zip(distances, indices)):
        if leave_one_out:
            current_idx = pred_idx[row_pos]
            keep = fit_original_index[ind_row] != current_idx
            dist_row = dist_row[keep]
            ind_row = ind_row[keep]
        dist_row = dist_row[:k]
        ind_row = ind_row[:k]
        if len(ind_row) == 0:
            means.append(float(np.nanmean(y_fit)))
            idw_values.append(float(np.nanmean(y_fit)))
            min_distances.append(float("nan"))
            continue
        values = y_fit[ind_row]
        weights = 1.0 / (dist_row + 1e-6)
        means.append(float(np.mean(values)))
        idw_values.append(float(np.sum(weights * values) / np.sum(weights)))
        min_distances.append(float(np.min(dist_row)))

    x_out["target_spatial_mean"] = means
    x_out["target_spatial_idw"] = idw_values
    x_out["target_spatial_min_dist"] = min_distances
    return x_out

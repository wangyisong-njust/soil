from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


def make_protocol_split(
    df: pd.DataFrame,
    protocol: str,
    random_state: int,
    random_test_size: float,
    temporal_test_start_year: int,
) -> tuple[np.ndarray, np.ndarray]:
    index = np.asarray(df.index)
    if protocol == "temporal":
        train_mask = df["year"] < temporal_test_start_year
        test_mask = df["year"] >= temporal_test_start_year
        if train_mask.sum() < 50 or test_mask.sum() < 10:
            sorted_years = sorted(df["year"].unique())
            cutoff = sorted_years[max(1, int(len(sorted_years) * 0.8))]
            train_mask = df["year"] < cutoff
            test_mask = df["year"] >= cutoff
        return index[train_mask.to_numpy()], index[test_mask.to_numpy()]

    if protocol == "random":
        train_idx, test_idx = train_test_split(
            index,
            test_size=random_test_size,
            random_state=random_state,
            shuffle=True,
        )
        return np.asarray(train_idx), np.asarray(test_idx)

    raise ValueError(f"Unknown protocol: {protocol}")


def make_internal_validation_split(
    df: pd.DataFrame,
    train_idx: np.ndarray,
    protocol: str,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray]:
    train_df = df.loc[train_idx]
    if protocol == "temporal" and train_df["year"].nunique() >= 5:
        years = sorted(train_df["year"].unique())
        n_valid_years = max(1, math.ceil(len(years) * 0.2))
        valid_years = set(years[-n_valid_years:])
        valid_mask = train_df["year"].isin(valid_years)
        if valid_mask.sum() >= 10 and (~valid_mask).sum() >= 50:
            return train_df.index[~valid_mask].to_numpy(), train_df.index[valid_mask].to_numpy()

    core_idx, valid_idx = train_test_split(
        train_idx,
        test_size=0.2,
        random_state=random_state,
        shuffle=True,
    )
    return np.asarray(core_idx), np.asarray(valid_idx)


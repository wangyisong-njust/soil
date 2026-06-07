#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.data import TARGET_SPATIAL_FEATURES, add_engineered_features, add_target_spatial_lag_features
from soilmodel.metrics import regression_metrics
from soilmodel.models import build_model_registry, fresh_model
from soilmodel.paths import DOCS_DIR, FIGURES_DIR, RESULTS_DIR, TABLES_DIR, ensure_project_dirs


TS_FIG_DIR = FIGURES_DIR / "temporal_sequence_models"
DEFAULT_MODELS = ["ElasticNet", "HistGBR", "LightGBM", "XGBoost"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare ARIMA/LSTM-style temporal baselines and hybrid temporal feature models.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Experiment config.")
    parser.add_argument("--data", default=None, help="Input CSV. Defaults to OSM/external/processed data in that order.")
    parser.add_argument("--n-zones", type=int, default=8, help="Spatial zones for zone-wise temporal trends.")
    parser.add_argument("--n-jobs", type=int, default=2, help="Parallel jobs for sklearn models.")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Hybrid model names.")
    parser.add_argument("--lstm-epochs", type=int, default=260, help="Epochs for annual LSTM baseline.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
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


def annual_means(history: pd.DataFrame, target: str) -> pd.Series:
    if history.empty:
        return pd.Series(dtype=float)
    series = history.groupby("year")[target].mean().sort_index().astype(float)
    years = np.arange(int(series.index.min()), int(series.index.max()) + 1)
    return series.reindex(years).interpolate(limit_direction="both").ffill().bfill()


def fallback_value(history: pd.DataFrame, target: str) -> float:
    if history.empty:
        return 0.0
    return float(np.nanmedian(history[target].to_numpy(dtype=float)))


def forecast_annual(history: pd.DataFrame, target: str, pred_years: list[int], method: str, seed: int = 42, lstm_epochs: int = 260) -> dict[int, float]:
    pred_years = sorted({int(year) for year in pred_years})
    if not pred_years:
        return {}
    base = fallback_value(history, target)
    series = annual_means(history, target)
    if len(series) < 2:
        return {year: max(base, 0.0) for year in pred_years}

    if method == "last_mean":
        value = float(series.iloc[-1])
        return {year: max(value, 0.0) for year in pred_years}

    if method == "linear":
        x = series.index.to_numpy(dtype=float)
        y = series.to_numpy(dtype=float)
        if len(np.unique(x)) < 2:
            return {year: max(float(np.nanmean(y)), 0.0) for year in pred_years}
        slope, intercept = np.polyfit(x, y, 1)
        return {year: max(float(slope * year + intercept), 0.0) for year in pred_years}

    if method == "arima":
        try:
            from statsmodels.tsa.arima.model import ARIMA

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = ARIMA(series.to_numpy(dtype=float), order=(1, 1, 0), trend="n")
                fit = model.fit()
                steps = max(pred_years) - int(series.index.max())
                if steps <= 0:
                    linear = forecast_annual(history, target, pred_years, "linear", seed=seed)
                    return linear
                fcst = np.asarray(fit.forecast(steps=steps), dtype=float)
            out = {}
            for year in pred_years:
                offset = year - int(series.index.max()) - 1
                out[year] = max(float(fcst[offset]), 0.0) if 0 <= offset < len(fcst) else max(base, 0.0)
            return out
        except Exception:
            return forecast_annual(history, target, pred_years, "linear", seed=seed)

    if method == "lstm":
        try:
            return forecast_lstm(series, pred_years, seed=seed, epochs=lstm_epochs)
        except Exception:
            return forecast_annual(history, target, pred_years, "linear", seed=seed)

    raise ValueError(method)


def forecast_lstm(series: pd.Series, pred_years: list[int], seed: int = 42, epochs: int = 260) -> dict[int, float]:
    import torch
    from torch import nn

    torch.manual_seed(seed)
    torch.set_num_threads(1)
    values_raw = series.to_numpy(dtype=np.float32)
    values = np.log1p(np.maximum(values_raw, 0.0)).astype(np.float32)
    mean = float(values.mean())
    std = float(values.std() if values.std() > 1e-6 else 1.0)
    scaled = (values - mean) / std
    lookback = min(4, max(2, len(scaled) // 3))
    if len(scaled) <= lookback + 1:
        last = float(np.expm1(values[-1]))
        return {year: max(last, 0.0) for year in pred_years}

    xs, ys = [], []
    for i in range(lookback, len(scaled)):
        xs.append(scaled[i - lookback : i])
        ys.append(scaled[i])
    x = torch.tensor(np.asarray(xs)[:, :, None], dtype=torch.float32)
    y = torch.tensor(np.asarray(ys)[:, None], dtype=torch.float32)

    class AnnualLSTM(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.lstm = nn.LSTM(input_size=1, hidden_size=12, num_layers=1, batch_first=True)
            self.fc = nn.Linear(12, 1)

        def forward(self, batch):
            out, _ = self.lstm(batch)
            return self.fc(out[:, -1, :])

    model = AnnualLSTM()
    optim = torch.optim.Adam(model.parameters(), lr=0.03, weight_decay=1e-4)
    loss_fn = nn.MSELoss()
    model.train()
    for _ in range(epochs):
        optim.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        optim.step()

    max_train_year = int(series.index.max())
    max_year = max(pred_years)
    hist = list(scaled.astype(float))
    out_scaled: dict[int, float] = {}
    model.eval()
    with torch.no_grad():
        for year in range(max_train_year + 1, max_year + 1):
            batch = torch.tensor(np.asarray(hist[-lookback:], dtype=np.float32)[None, :, None], dtype=torch.float32)
            pred = float(model(batch).numpy().reshape(-1)[0])
            hist.append(pred)
            out_scaled[year] = pred
    out = {}
    for year in pred_years:
        if year <= max_train_year:
            idx = list(series.index).index(year) if year in series.index else -1
            value = float(values_raw[idx]) if idx >= 0 else float(values_raw[-1])
        else:
            value = float(np.expm1(out_scaled.get(year, hist[-1]) * std + mean))
        out[year] = max(value, 0.0)
    return out


def fit_zones(df: pd.DataFrame, train_idx: np.ndarray, n_zones: int, seed: int) -> np.ndarray:
    coords = df[["lon", "lat"]].to_numpy(dtype=float)
    k = max(2, min(n_zones, len(train_idx) // 30))
    model = KMeans(n_clusters=k, random_state=seed, n_init=20)
    model.fit(coords[train_idx])
    return model.predict(coords)


def zone_forecast_map(
    df: pd.DataFrame,
    target: str,
    train_idx: np.ndarray,
    zones: np.ndarray,
    pred_years: list[int],
    method: str = "linear",
    seed: int = 42,
) -> dict[tuple[int, int], float]:
    train_df = df.loc[train_idx].copy()
    train_df["zone"] = zones[train_idx]
    global_fcst = forecast_annual(train_df, target, pred_years, method, seed=seed)
    out: dict[tuple[int, int], float] = {}
    for zone, zone_df in train_df.groupby("zone"):
        if zone_df["year"].nunique() >= 3 and len(zone_df) >= 15:
            fcst = forecast_annual(zone_df, target, pred_years, method, seed=seed)
        else:
            fcst = global_fcst
        for year in pred_years:
            out[(int(zone), int(year))] = fcst[int(year)]
    return out


def rolling_temporal_features(
    df: pd.DataFrame,
    target: str,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    zones: np.ndarray,
    seed: int,
    lstm_epochs: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_years = sorted(df.loc[train_idx, "year"].astype(int).unique())
    test_years = sorted(df.loc[test_idx, "year"].astype(int).unique())
    feature_frames = []
    all_feature_idx = list(train_idx) + list(test_idx)
    template = pd.DataFrame(index=all_feature_idx)

    global_train = df.loc[train_idx]
    train_years = sorted(global_train["year"].astype(int).unique())
    zone_values = sorted(np.unique(zones[train_idx]).astype(int).tolist())

    global_train_features: dict[int, dict[str, float]] = {}
    for year in train_years:
        history_idx = train_idx[df.loc[train_idx, "year"].to_numpy(dtype=int) < year]
        history = df.loc[history_idx]
        global_train_features[year] = {
            "ts_global_last_mean": forecast_annual(history, target, [year], "last_mean", seed=seed)[year],
            "ts_global_linear": forecast_annual(history, target, [year], "linear", seed=seed)[year],
            "ts_global_arima": forecast_annual(history, target, [year], "arima", seed=seed)[year],
        }

    zone_train_features: dict[tuple[int, int], dict[str, float]] = {}
    for zone in zone_values:
        zone_train_idx = train_idx[zones[train_idx] == zone]
        for year in train_years:
            zone_history_idx = zone_train_idx[df.loc[zone_train_idx, "year"].to_numpy(dtype=int) < year]
            zone_history = df.loc[zone_history_idx]
            zone_train_features[(zone, year)] = {
                "ts_zone_linear": forecast_annual(zone_history, target, [year], "linear", seed=seed)[year],
                "ts_zone_last_mean": forecast_annual(zone_history, target, [year], "last_mean", seed=seed)[year],
                "ts_zone_history_n": float(len(zone_history)),
            }

    test_fcsts = {
        method: forecast_annual(global_train, target, test_years, method, seed=seed, lstm_epochs=lstm_epochs)
        for method in ["last_mean", "linear", "arima"]
    }
    zone_test_fcst = zone_forecast_map(df, target, train_idx, zones, test_years, method="linear", seed=seed)
    zone_test_last = zone_forecast_map(df, target, train_idx, zones, test_years, method="last_mean", seed=seed)

    for idx in train_idx:
        year = int(df.loc[idx, "year"])
        zone = int(zones[idx])
        row = {**global_train_features[year], **zone_train_features[(zone, year)]}
        feature_frames.append(pd.DataFrame(row, index=[idx]))

    for idx in test_idx:
        year = int(df.loc[idx, "year"])
        zone = int(zones[idx])
        row = {
            "ts_global_last_mean": test_fcsts["last_mean"][year],
            "ts_global_linear": test_fcsts["linear"][year],
            "ts_global_arima": test_fcsts["arima"][year],
            "ts_zone_linear": zone_test_fcst.get((zone, year), test_fcsts["linear"][year]),
            "ts_zone_last_mean": zone_test_last.get((zone, year), test_fcsts["last_mean"][year]),
            "ts_zone_history_n": float(((zones[train_idx] == zone)).sum()),
        }
        feature_frames.append(pd.DataFrame(row, index=[idx]))

    if feature_frames:
        template = pd.concat(feature_frames).sort_index()
    return template.loc[train_idx].copy(), template.loc[test_idx].copy()


def fit_predict(spec, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> np.ndarray:
    model = fresh_model(spec)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(x_train, y_train)
        pred = np.asarray(model.predict(x_test), dtype=float).reshape(-1)
    return np.maximum(pred, 0.0)


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
    TS_FIG_DIR.mkdir(parents=True, exist_ok=True)
    for protocol, part in best.groupby("protocol"):
        part = part.sort_values("target")
        fig, ax = plt.subplots(figsize=(9, 5))
        colors = ["#59A14F" if value >= 0 else "#E15759" for value in part["r2"]]
        ax.bar(part["target"], part["r2"], color=colors)
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.set_title(f"Best Temporal Sequence Model R2 ({protocol})")
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
        path = TS_FIG_DIR / f"best_r2_{protocol}.png"
        plt.savefig(path, dpi=300, bbox_inches="tight")
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
    requested = [item.strip() for item in args.models.split(",") if item.strip()]
    protocols = ["literature_2019_2020", "temporal_2022_2026"]

    rows: list[dict[str, object]] = []
    pred_rows: list[pd.DataFrame] = []

    for protocol in protocols:
        train_idx, test_idx = protocol_indices(df, protocol, int(config["temporal_test_start_year"]))
        zones = fit_zones(df, train_idx, args.n_zones, args.seed)
        x_df, engineered = add_engineered_features(df, base_features + external_features)
        x_base_all = x_df[engineered].astype(float)
        print(f"\n{protocol}: train={len(train_idx)} test={len(test_idx)} base_features={len(engineered)}", flush=True)

        for target in config["target_columns"]:
            y = df[target].astype(float)
            y_test = y.loc[test_idx]
            test_years = sorted(df.loc[test_idx, "year"].astype(int).unique())
            train_df = df.loc[train_idx]

            baseline_specs = {
                "LastAnnualMean": forecast_annual(train_df, target, test_years, "last_mean", seed=args.seed),
                "LinearAnnualTrend": forecast_annual(train_df, target, test_years, "linear", seed=args.seed),
                "ARIMAAnnualMean": forecast_annual(train_df, target, test_years, "arima", seed=args.seed),
                "LSTMAnnualMean": forecast_annual(train_df, target, test_years, "lstm", seed=args.seed, lstm_epochs=args.lstm_epochs),
            }
            zone_linear = zone_forecast_map(df, target, train_idx, zones, test_years, method="linear", seed=args.seed)
            zone_last = zone_forecast_map(df, target, train_idx, zones, test_years, method="last_mean", seed=args.seed)
            for model_name, mapping in baseline_specs.items():
                pred = df.loc[test_idx, "year"].astype(int).map(mapping).to_numpy(dtype=float)
                metric = regression_metrics(y_test, np.maximum(pred, 0.0))
                rows.append(
                    {
                        "protocol": protocol,
                        "target": target,
                        "method": "pure_temporal_baseline",
                        "model": model_name,
                        "status": "ok",
                        "n_train": int(len(train_idx)),
                        "n_test": int(len(test_idx)),
                        "n_features": 1,
                        **metric,
                    }
                )
                pred_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
                pred_table["protocol"] = protocol
                pred_table["target"] = target
                pred_table["method"] = "pure_temporal_baseline"
                pred_table["model"] = model_name
                pred_table["observed"] = y_test.to_numpy()
                pred_table["predicted"] = np.maximum(pred, 0.0)
                pred_rows.append(pred_table)

            for model_name, mapping in [("ZoneLinearTrend", zone_linear), ("ZoneLastAnnualMean", zone_last)]:
                pred = np.asarray(
                    [mapping.get((int(zones[idx]), int(df.loc[idx, "year"])), fallback_value(train_df, target)) for idx in test_idx],
                    dtype=float,
                )
                metric = regression_metrics(y_test, np.maximum(pred, 0.0))
                rows.append(
                    {
                        "protocol": protocol,
                        "target": target,
                        "method": "zone_temporal_baseline",
                        "model": model_name,
                        "status": "ok",
                        "n_train": int(len(train_idx)),
                        "n_test": int(len(test_idx)),
                        "n_features": 2,
                        **metric,
                    }
                )
                pred_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
                pred_table["protocol"] = protocol
                pred_table["target"] = target
                pred_table["method"] = "zone_temporal_baseline"
                pred_table["model"] = model_name
                pred_table["observed"] = y_test.to_numpy()
                pred_table["predicted"] = np.maximum(pred, 0.0)
                pred_rows.append(pred_table)

            print(f"  {target}: temporal features", flush=True)
            ts_train, ts_test = rolling_temporal_features(df, target, train_idx, test_idx, zones, args.seed, args.lstm_epochs)
            if config.get("use_target_spatial_lag_features", False):
                k = int(config.get("target_spatial_lag_k", 12))
                x_train_base = add_target_spatial_lag_features(df, x_base_all, y, train_idx, train_idx, k=k, leave_one_out=True)
                x_test_base = add_target_spatial_lag_features(df, x_base_all, y, train_idx, test_idx, k=k, leave_one_out=False)
            else:
                x_train_base = x_base_all.loc[train_idx]
                x_test_base = x_base_all.loc[test_idx]
            x_train = pd.concat([x_train_base, ts_train], axis=1)
            x_test = pd.concat([x_test_base, ts_test], axis=1)
            registry = build_model_registry(len(x_train.columns), random_state=args.seed, n_jobs=args.n_jobs)
            registry = {name: registry[name] for name in requested if name in registry}
            for model_name, spec in registry.items():
                try:
                    pred = fit_predict(spec, x_train, y.loc[train_idx], x_test)
                    metric = regression_metrics(y_test, pred)
                    rows.append(
                        {
                            "protocol": protocol,
                            "target": target,
                            "method": "hybrid_spatiotemporal_sequence",
                            "model": model_name,
                            "status": "ok",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "n_features": int(x_train.shape[1]),
                            **metric,
                        }
                    )
                    pred_table = df.loc[test_idx, ["lon", "lat", "year"]].copy()
                    pred_table["protocol"] = protocol
                    pred_table["target"] = target
                    pred_table["method"] = "hybrid_spatiotemporal_sequence"
                    pred_table["model"] = model_name
                    pred_table["observed"] = y_test.to_numpy()
                    pred_table["predicted"] = pred
                    pred_rows.append(pred_table)
                except Exception as exc:
                    rows.append(
                        {
                            "protocol": protocol,
                            "target": target,
                            "method": "hybrid_spatiotemporal_sequence",
                            "model": model_name,
                            "status": f"failed: {exc}",
                            "n_train": int(len(train_idx)),
                            "n_test": int(len(test_idx)),
                            "n_features": int(x_train.shape[1]),
                            "r2": np.nan,
                            "r2_log1p": np.nan,
                            "rmse": np.nan,
                            "mae": np.nan,
                            "mape": np.nan,
                        }
                    )

    metrics = pd.DataFrame(rows)
    metrics.to_csv(TABLES_DIR / "temporal_sequence_model_metrics.csv", index=False, encoding="utf-8-sig")
    if pred_rows:
        pd.concat(pred_rows, ignore_index=True).to_csv(RESULTS_DIR / "temporal_sequence_model_predictions.csv", index=False, encoding="utf-8-sig")
    best = (
        metrics[metrics["status"] == "ok"]
        .sort_values(["protocol", "target", "r2", "rmse"], ascending=[True, True, False, True])
        .groupby(["protocol", "target"], as_index=False)
        .head(1)
        .sort_values(["protocol", "target"])
    )
    best.to_csv(TABLES_DIR / "temporal_sequence_best_metrics.csv", index=False, encoding="utf-8-sig")
    plot_best(best)

    show = best[["protocol", "target", "method", "model", "n_train", "n_test", "n_features", "r2", "rmse", "mae", "mape"]].copy()
    for col in ["r2", "rmse", "mae", "mape"]:
        show[col] = show[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    report = [
        "# ARIMA/LSTM 时间序列模型对照",
        "",
        f"输入数据：`{data_path.relative_to(ROOT)}`。由于样点不是连续站点序列，ARIMA 和 LSTM 采用年度均值序列作为纯时间序列基线；空间分区趋势采用训练期坐标聚类后的分区年度序列。",
        "",
        "创新模型 `hybrid_spatiotemporal_sequence` 在外部公开因子、工程特征和训练期空间滞后特征基础上，加入 ARIMA、年度趋势和分区趋势等时序预测特征。训练期时序特征按年份滚动生成，避免使用同年或未来目标值。LSTM 作为独立年度序列基线参与比较；由于样点不是连续监测站序列，未将 LSTM 强行作为点位级主模型。",
        "",
        md_table(show),
        "",
        "完整结果见 `tables/temporal_sequence_model_metrics.csv`、`tables/temporal_sequence_best_metrics.csv` 和 `results/temporal_sequence_model_predictions.csv`。",
        "",
    ]
    (DOCS_DIR / "temporal_sequence_model_report.md").write_text("\n".join(report), encoding="utf-8")
    metadata = {
        "data": str(data_path.relative_to(ROOT)),
        "protocols": protocols,
        "n_zones": args.n_zones,
        "lstm_epochs": args.lstm_epochs,
        "note": "Point-level continuous time series are sparse; ARIMA/LSTM are annual-series baselines.",
    }
    (TABLES_DIR / "temporal_sequence_setup.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote temporal sequence model outputs")


if __name__ == "__main__":
    main()

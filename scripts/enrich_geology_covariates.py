#!/usr/bin/env python
"""为样本点补充地质/岩性协变量。

数据源：Macrostrat 地质单元 API（https://macrostrat.org/api，公开、按经纬度查询）。
对每个唯一坐标取地表地质单元的岩性大类与地质年代，派生为数值/哑变量特征。
逐点结果缓存到 data/external_cache/，可断点续跑；无覆盖或失败的点记为 unknown 并填补。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import ensure_project_dirs, preferred_processed_data_path

DEFAULT_API = "https://macrostrat.org/api/v2/geologic_units/map"

# 岩性大类哑变量（覆盖常见类型）
LITH_CLASSES = ["sedimentary", "igneous_volcanic", "igneous_plutonic", "metamorphic", "unconsolidated"]
GEO_NUMERIC = ["geo_age_top", "geo_age_bottom", "geo_age_mid", "geo_age_span"]
GEO_COLUMNS = GEO_NUMERIC + [f"geo_is_{c}" for c in LITH_CLASSES] + ["geo_has_data"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich samples with Macrostrat geology/lithology covariates.")
    parser.add_argument("--data", default=None, help="Input CSV (default: preferred processed data).")
    parser.add_argument(
        "--output",
        default="data/processed/soil_heavy_metals_geology.csv",
        help="Output enriched CSV path.",
    )
    parser.add_argument("--api-base", default=DEFAULT_API, help="Macrostrat geologic_units/map endpoint.")
    parser.add_argument("--sleep", type=float, default=0.4, help="Seconds between API requests.")
    return parser.parse_args()


def classify_lithology(lith_text: str) -> str:
    t = (lith_text or "").lower()
    if any(k in t for k in ["sediment", "sandstone", "shale", "limestone", "mudstone", "conglomerate", "carbonate", "dolomite"]):
        return "sedimentary"
    if any(k in t for k in ["volcanic", "basalt", "andesite", "rhyolite", "tuff", "lava"]):
        return "igneous_volcanic"
    if any(k in t for k in ["granit", "plutonic", "gabbro", "diorite", "intrusive", "pluton"]):
        return "igneous_plutonic"
    if any(k in t for k in ["metamorph", "gneiss", "schist", "slate", "marble", "quartzite", "amphibolite"]):
        return "metamorphic"
    if any(k in t for k in ["alluvi", "unconsolidated", "sand and gravel", "loess", "soil", "regolith", "colluvi"]):
        return "unconsolidated"
    return "unknown"


def parse_record(data: list[dict]) -> dict[str, float]:
    feats = {col: 0.0 for col in GEO_COLUMNS}
    feats["geo_has_data"] = 0.0
    for col in GEO_NUMERIC:
        feats[col] = np.nan
    if not data:
        return feats
    rec = data[0]
    feats["geo_has_data"] = 1.0
    b_age = rec.get("b_age")
    t_age = rec.get("t_age")
    try:
        b = float(b_age) if b_age is not None else np.nan
        t = float(t_age) if t_age is not None else np.nan
    except (TypeError, ValueError):
        b, t = np.nan, np.nan
    feats["geo_age_bottom"] = b
    feats["geo_age_top"] = t
    if np.isfinite(b) and np.isfinite(t):
        feats["geo_age_mid"] = (b + t) / 2.0
        feats["geo_age_span"] = abs(b - t)
    lith_text = rec.get("lith") or rec.get("name") or ""
    cls = classify_lithology(lith_text)
    if cls in LITH_CLASSES:
        feats[f"geo_is_{cls}"] = 1.0
    return feats


def fetch_point(lon: float, lat: float, api_base: str, cache_dir: Path) -> dict[str, float]:
    key = f"geology_{lon:.6f}_{lat:.6f}"
    cpath = cache_dir / f"{key}.json"
    if cpath.exists():
        return json.loads(cpath.read_text(encoding="utf-8"))
    url = f"{api_base}?{urlencode({'lat': lat, 'lng': lon, 'format': 'json'})}"
    try:
        req = Request(url, headers={"User-Agent": "soil-geology-enrich/1.0"})
        with urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode())
        data = payload.get("success", {}).get("data", [])
        feats = parse_record(data)
    except Exception as exc:  # noqa: BLE001
        print(f"  ({lon},{lat}) 失败：{type(exc).__name__}: {exc}", flush=True)
        feats = parse_record([])
    cpath.write_text(json.dumps(feats), encoding="utf-8")
    return feats


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    cache_dir = ROOT / "data" / "external_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    data_path = ROOT / args.data if args.data else preferred_processed_data_path()
    df = pd.read_csv(data_path)
    uniq = df[["lon", "lat"]].drop_duplicates().reset_index(drop=True)
    print(f"输入 {len(df)} 行，唯一坐标 {len(uniq)} 个。地质数据源：{args.api_base}", flush=True)

    records = []
    n_req = 0
    for _, row in uniq.iterrows():
        lon, lat = float(row["lon"]), float(row["lat"])
        key = f"geology_{lon:.6f}_{lat:.6f}"
        was_cached = (cache_dir / f"{key}.json").exists()
        feats = fetch_point(lon, lat, args.api_base, cache_dir)
        records.append({"lon": lon, "lat": lat, **feats})
        if not was_cached:
            n_req += 1
            time.sleep(args.sleep)

    geo_df = pd.DataFrame(records)
    n_no_data = int((geo_df["geo_has_data"] == 0).sum())
    for col in GEO_NUMERIC:
        geo_df[col] = geo_df[col].fillna(geo_df[col].median())

    merged = df.merge(geo_df, on=["lon", "lat"], how="left")
    out_path = ROOT / args.output
    merged.to_csv(out_path, index=False, encoding="utf-8-sig")
    report = {
        "source": args.api_base,
        "n_rows": int(len(merged)),
        "n_unique_locations": int(len(uniq)),
        "n_api_requests": n_req,
        "n_locations_without_geology": n_no_data,
        "geology_columns": GEO_COLUMNS,
    }
    (ROOT / "tables" / "geology_covariates_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"写出 {out_path.relative_to(ROOT)}（新增 {len(GEO_COLUMNS)} 列，无地质覆盖 {n_no_data} 个坐标）", flush=True)


if __name__ == "__main__":
    main()

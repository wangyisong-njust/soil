#!/usr/bin/env python
"""为样本点补充地形协变量（高程及其派生量）。

数据源：opentopodata 公共 API 的 SRTM 30m 高程（https://www.opentopodata.org/）。
对每个唯一坐标取 3x3 高程网格，计算高程、坡度、坡向、地形起伏和地形位置指数。
逐点结果缓存到 data/external_cache/，可断点续跑；离线或 API 失败的点以中位数填补并记录。

注意：opentopodata 公共实例有限速（约 1 请求/秒、100 坐标/请求、1000 请求/天）。
本脚本按 100 坐标/请求分批，并在请求间留出间隔。若要大批量或离线运行，可自建 opentopodata 实例后用 --api-base 覆盖。
"""
from __future__ import annotations

import argparse
import json
import math
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

DEFAULT_API = "https://api.opentopodata.org/v1/srtm30m"
TERRAIN_COLUMNS = [
    "dem_elev",
    "terr_slope_deg",
    "terr_aspect_sin",
    "terr_aspect_cos",
    "terr_roughness",
    "terr_tpi",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich samples with SRTM terrain covariates.")
    parser.add_argument("--data", default=None, help="Input CSV (default: preferred processed data).")
    parser.add_argument(
        "--output",
        default="data/processed/soil_heavy_metals_terrain.csv",
        help="Output enriched CSV path.",
    )
    parser.add_argument("--api-base", default=DEFAULT_API, help="opentopodata dataset endpoint.")
    parser.add_argument("--delta-deg", type=float, default=0.0025, help="Stencil half-step in degrees (~278 m).")
    parser.add_argument("--batch", type=int, default=100, help="Locations per API request (<=100 for public API).")
    parser.add_argument("--sleep", type=float, default=1.1, help="Seconds between API requests (respect rate limit).")
    return parser.parse_args()


def stencil_offsets(lon: float, lat: float, d: float) -> list[tuple[float, float]]:
    """3x3 网格，行优先；经度步长按纬度做余弦校正。"""
    dlon = d / max(math.cos(math.radians(lat)), 1e-6)
    pts = []
    for dy in (d, 0.0, -d):  # 北、中、南
        for dx in (-dlon, 0.0, dlon):  # 西、中、东
            pts.append((round(lon + dx, 6), round(lat + dy, 6)))
    return pts


def fetch_elevations(coords: list[tuple[float, float]], api_base: str, batch: int, sleep: float) -> dict[tuple[float, float], float]:
    out: dict[tuple[float, float], float] = {}
    for i in range(0, len(coords), batch):
        chunk = coords[i : i + batch]
        locs = "|".join(f"{lat},{lon}" for lon, lat in chunk)
        url = f"{api_base}?{urlencode({'locations': locs})}"
        try:
            req = Request(url, headers={"User-Agent": "soil-terrain-enrich/1.0"})
            with urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
            for (lon, lat), res in zip(chunk, data.get("results", [])):
                elev = res.get("elevation")
                out[(lon, lat)] = float(elev) if elev is not None else math.nan
        except Exception as exc:  # noqa: BLE001
            print(f"  batch {i//batch} 失败：{type(exc).__name__}: {exc}", flush=True)
            for key in chunk:
                out[key] = math.nan
        time.sleep(sleep)
    return out


def terrain_from_stencil(elev: np.ndarray, d_m: float) -> dict[str, float]:
    """elev: 长度9，行优先(北->南, 西->东)。返回地形派生量。"""
    grid = elev.reshape(3, 3)
    center = grid[1, 1]
    if not np.isfinite(center):
        return {col: math.nan for col in TERRAIN_COLUMNS}
    # 有限差分梯度（y 向北为正）
    west, east = grid[1, 0], grid[1, 2]
    north, south = grid[0, 1], grid[2, 1]
    dzdx = (east - west) / (2 * d_m) if np.isfinite(east) and np.isfinite(west) else 0.0
    dzdy = (north - south) / (2 * d_m) if np.isfinite(north) and np.isfinite(south) else 0.0
    slope_rad = math.atan(math.hypot(dzdx, dzdy))
    aspect_rad = math.atan2(dzdy, -dzdx) if (dzdx or dzdy) else 0.0
    neighbors = np.array([grid[0, 1], grid[2, 1], grid[1, 0], grid[1, 2],
                          grid[0, 0], grid[0, 2], grid[2, 0], grid[2, 2]], dtype=float)
    finite_nb = neighbors[np.isfinite(neighbors)]
    return {
        "dem_elev": float(center),
        "terr_slope_deg": float(math.degrees(slope_rad)),
        "terr_aspect_sin": float(math.sin(aspect_rad)),
        "terr_aspect_cos": float(math.cos(aspect_rad)),
        "terr_roughness": float(np.std(np.append(finite_nb, center))) if finite_nb.size else 0.0,
        "terr_tpi": float(center - finite_nb.mean()) if finite_nb.size else 0.0,
    }


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    cache_dir = ROOT / "data" / "external_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    data_path = ROOT / args.data if args.data else preferred_processed_data_path()
    df = pd.read_csv(data_path)
    uniq = df[["lon", "lat"]].drop_duplicates().reset_index(drop=True)
    print(f"输入 {len(df)} 行，唯一坐标 {len(uniq)} 个。地形数据源：{args.api_base}", flush=True)

    d_m = args.delta_deg * 111_320.0  # 度->米（纬度方向近似）
    records: list[dict[str, float]] = []
    pending: list[tuple[float, float]] = []
    pending_meta: list[tuple[int, float, float]] = []

    # 先读缓存，未命中的进入待请求
    cached: dict[int, dict[str, float]] = {}
    for idx, row in uniq.iterrows():
        lon, lat = float(row["lon"]), float(row["lat"])
        key = f"terrain_{lon:.6f}_{lat:.6f}_{args.delta_deg}"
        cpath = cache_dir / f"{key}.json"
        if cpath.exists():
            cached[idx] = json.loads(cpath.read_text(encoding="utf-8"))
        else:
            pending_meta.append((idx, lon, lat))
            pending.extend(stencil_offsets(lon, lat, args.delta_deg))

    if pending:
        print(f"需请求 {len(pending_meta)} 个坐标（{len(pending)} 个网格点）...", flush=True)
        elev_map = fetch_elevations(pending, args.api_base, args.batch, args.sleep)
        for j, (idx, lon, lat) in enumerate(pending_meta):
            sten = stencil_offsets(lon, lat, args.delta_deg)
            elev = np.array([elev_map.get(p, math.nan) for p in sten], dtype=float)
            feats = terrain_from_stencil(elev, d_m)
            cached[idx] = feats
            key = f"terrain_{lon:.6f}_{lat:.6f}_{args.delta_deg}"
            (cache_dir / f"{key}.json").write_text(json.dumps(feats), encoding="utf-8")

    for idx, row in uniq.iterrows():
        feats = cached.get(idx, {col: math.nan for col in TERRAIN_COLUMNS})
        records.append({"lon": float(row["lon"]), "lat": float(row["lat"]), **feats})

    terr_df = pd.DataFrame(records)
    # 中位数填补失败点
    n_missing = int(terr_df["dem_elev"].isna().sum())
    for col in TERRAIN_COLUMNS:
        med = terr_df[col].median()
        terr_df[col] = terr_df[col].fillna(med)

    merged = df.merge(terr_df, on=["lon", "lat"], how="left")
    out_path = ROOT / args.output
    merged.to_csv(out_path, index=False, encoding="utf-8-sig")
    report = {
        "source": args.api_base,
        "n_rows": int(len(merged)),
        "n_unique_locations": int(len(uniq)),
        "n_missing_locations_filled": n_missing,
        "terrain_columns": TERRAIN_COLUMNS,
        "delta_deg": args.delta_deg,
    }
    (ROOT / "tables" / "terrain_covariates_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"写出 {out_path.relative_to(ROOT)}（新增 {len(TERRAIN_COLUMNS)} 列，失败填补 {n_missing} 个坐标）", flush=True)


if __name__ == "__main__":
    main()

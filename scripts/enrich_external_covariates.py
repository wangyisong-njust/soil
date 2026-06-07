#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.config import load_config
from soilmodel.paths import DATA_DIR, TABLES_DIR, ensure_project_dirs


SOILGRIDS_PROPERTIES = ["phh2o", "soc", "clay", "sand", "silt", "cec", "bdod", "nitrogen"]
POWER_PARAMETERS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "WS2M", "ALLSKY_SFC_SW_DWN"]
USER_AGENT = "soil-heavy-metal-model/1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich point samples with public external covariates.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--input", default=None, help="Input cleaned CSV path.")
    parser.add_argument("--output", default="data/processed/soil_heavy_metals_external.csv", help="Output enriched CSV path.")
    parser.add_argument("--max-workers", type=int, default=4, help="Concurrent API workers.")
    parser.add_argument("--skip-soilgrids", action="store_true", help="Skip SoilGrids extraction.")
    parser.add_argument("--skip-power", action="store_true", help="Skip NASA POWER extraction.")
    parser.add_argument("--limit-points", type=int, default=None, help="Debug limit for unique points.")
    return parser.parse_args()


def fetch_json(url: str, retries: int = 3, pause: float = 1.0) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except Exception as exc:
            last_error = exc
            time.sleep(pause * (attempt + 1))
    raise RuntimeError(str(last_error))


def point_key(lon: float, lat: float) -> str:
    return f"{lon:.6f}_{lat:.6f}"


def fetch_soilgrids_point(lon: float, lat: float, cache_dir: Path) -> dict[str, float | str]:
    key = point_key(lon, lat)
    cache_path = cache_dir / f"{key}.json"
    if cache_path.exists():
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        params: list[tuple[str, str | float]] = [("lon", lon), ("lat", lat), ("depth", "0-5cm"), ("value", "mean")]
        params.extend(("property", prop) for prop in SOILGRIDS_PROPERTIES)
        url = "https://rest.isric.org/soilgrids/v2.0/properties/query?" + urlencode(params)
        data = fetch_json(url)
        cache_path.write_text(json.dumps(data), encoding="utf-8")
    out: dict[str, float | str] = {"lon": lon, "lat": lat, "soilgrids_status": "ok"}
    try:
        for layer in data["properties"]["layers"]:
            name = layer["name"]
            unit = layer.get("unit_measure", {})
            factor = float(unit.get("d_factor") or 1.0)
            values = layer["depths"][0]["values"]
            raw_value = values.get("mean")
            out[f"sg_{name}_0_5cm"] = np.nan if raw_value is None else float(raw_value) / factor
    except Exception as exc:
        out["soilgrids_status"] = f"parse_failed: {exc}"
    return out


def fetch_power_point(lon: float, lat: float, year_min: int, year_max: int, cache_dir: Path) -> pd.DataFrame:
    key = point_key(lon, lat)
    cache_path = cache_dir / f"{key}_{year_min}_{year_max}.json"
    if cache_path.exists():
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        params = {
            "parameters": ",".join(POWER_PARAMETERS),
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "start": year_min,
            "end": year_max,
            "format": "JSON",
        }
        url = "https://power.larc.nasa.gov/api/temporal/monthly/point?" + urlencode(params)
        data = fetch_json(url)
        cache_path.write_text(json.dumps(data), encoding="utf-8")

    params_data = data["properties"]["parameter"]
    years = list(range(year_min, year_max + 1))
    rows = []
    for year in years:
        row: dict[str, float | int | str] = {"lon": lon, "lat": lat, "year": year, "power_status": "ok"}
        month_keys = [f"{year}{month:02d}" for month in range(1, 13)]
        for param in POWER_PARAMETERS:
            values = [params_data.get(param, {}).get(month_key) for month_key in month_keys]
            clean_values = [float(v) for v in values if v is not None and float(v) > -900]
            if not clean_values:
                row[f"np_{param.lower()}_annual"] = np.nan
            elif param == "PRECTOTCORR":
                row["np_prectotcorr_annual_sum"] = float(np.sum(clean_values))
            else:
                row[f"np_{param.lower()}_annual_mean"] = float(np.mean(clean_values))
        rows.append(row)
    return pd.DataFrame(rows)


def run_parallel(points: pd.DataFrame, worker, max_workers: int) -> list:
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(worker, float(row.lon), float(row.lat)) for row in points.itertuples(index=False)]
        for i, future in enumerate(as_completed(futures), start=1):
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"error": f"{type(exc).__name__}: {exc}"})
            if i % 50 == 0 or i == len(futures):
                print(f"  completed {i}/{len(futures)}", flush=True)
    return results


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    config = load_config(ROOT / args.config)
    input_path = ROOT / (args.input or config["processed_csv"])
    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    df["lon_ext_key"] = df["lon"].round(6)
    df["lat_ext_key"] = df["lat"].round(6)
    unique_points = df[["lon_ext_key", "lat_ext_key"]].drop_duplicates().rename(
        columns={"lon_ext_key": "lon", "lat_ext_key": "lat"}
    )
    if args.limit_points:
        unique_points = unique_points.head(args.limit_points)
    print(f"Unique points for external extraction: {len(unique_points)}", flush=True)

    cache_root = DATA_DIR / "external_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    merge = df.copy()
    reports: dict[str, object] = {
        "input_csv": str(input_path.relative_to(ROOT)),
        "output_csv": str(output_path.relative_to(ROOT)),
        "n_rows": int(len(df)),
        "n_unique_points": int(len(unique_points)),
        "sources": [],
    }

    if not args.skip_soilgrids:
        print("Fetching SoilGrids point covariates...", flush=True)
        soil_cache = cache_root / "soilgrids"
        soil_cache.mkdir(parents=True, exist_ok=True)
        soil_results = run_parallel(
            unique_points,
            lambda lon, lat: fetch_soilgrids_point(lon, lat, soil_cache),
            max_workers=args.max_workers,
        )
        soil_df = pd.DataFrame([r for r in soil_results if "error" not in r])
        soil_df = soil_df.rename(columns={"lon": "lon_ext_key", "lat": "lat_ext_key"})
        merge = merge.merge(soil_df, on=["lon_ext_key", "lat_ext_key"], how="left")
        reports["sources"].append(
            {
                "name": "SoilGrids",
                "url": "https://rest.isric.org/soilgrids/v2.0/properties/query",
                "n_success": int((soil_df.get("soilgrids_status") == "ok").sum()) if len(soil_df) else 0,
                "columns": [c for c in soil_df.columns if c.startswith("sg_")],
            }
        )

    if not args.skip_power:
        print("Fetching NASA POWER monthly climate covariates...", flush=True)
        power_cache = cache_root / "nasa_power"
        power_cache.mkdir(parents=True, exist_ok=True)
        year_min = int(math.floor(df["year"].min()))
        requested_year_max = int(math.ceil(df["year"].max()))
        # NASA POWER monthly API currently rejects 2026. Use the latest accepted
        # full year and forward-fill later sample years from that year.
        year_max = min(requested_year_max, 2025)
        power_results = run_parallel(
            unique_points,
            lambda lon, lat: fetch_power_point(lon, lat, year_min, year_max, power_cache),
            max_workers=args.max_workers,
        )
        power_errors = [r for r in power_results if isinstance(r, dict) and "error" in r]
        power_tables = [r for r in power_results if isinstance(r, pd.DataFrame)]
        if power_tables:
            power_df = pd.concat(power_tables, ignore_index=True)
            if requested_year_max > year_max:
                last_year = power_df[power_df["year"] == year_max].copy()
                fills = []
                for fill_year in range(year_max + 1, requested_year_max + 1):
                    part = last_year.copy()
                    part["year"] = fill_year
                    part["power_status"] = f"forward_filled_from_{year_max}"
                    fills.append(part)
                if fills:
                    power_df = pd.concat([power_df, *fills], ignore_index=True)
            power_df = power_df.rename(columns={"lon": "lon_ext_key", "lat": "lat_ext_key"})
            merge = merge.merge(power_df, on=["lon_ext_key", "lat_ext_key", "year"], how="left")
            reports["sources"].append(
                {
                    "name": "NASA POWER",
                    "url": "https://power.larc.nasa.gov/api/temporal/monthly/point",
                    "n_point_year_rows": int(len(power_df)),
                    "requested_year_max": requested_year_max,
                    "api_year_max_used": year_max,
                    "n_errors": int(len(power_errors)),
                    "sample_errors": power_errors[:5],
                    "columns": [c for c in power_df.columns if c.startswith("np_")],
                }
            )
        else:
            reports["sources"].append(
                {
                    "name": "NASA POWER",
                    "url": "https://power.larc.nasa.gov/api/temporal/monthly/point",
                    "n_point_year_rows": 0,
                    "requested_year_max": requested_year_max,
                    "api_year_max_used": year_max,
                    "n_errors": int(len(power_errors)),
                    "sample_errors": power_errors[:10],
                    "columns": [],
                }
            )

    merge = merge.drop(columns=["lon_ext_key", "lat_ext_key"], errors="ignore")
    merge.to_csv(output_path, index=False, encoding="utf-8-sig")
    report_path = TABLES_DIR / "external_covariates_report.json"
    report_path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path.relative_to(ROOT)}")
    print(f"Wrote {report_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

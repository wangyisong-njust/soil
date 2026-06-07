#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.errors import RasterioIOError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import TABLES_DIR, ensure_project_dirs


ZENODO_VIIRS_RECORD = "https://zenodo.org/records/8277198"
GHSL_ROOT = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL"
WORLDCOVER_ROOT = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map"

GHSL_EPOCHS = [2000, 2005, 2010, 2015, 2020, 2025]
VIIRS_EPOCHS = [2000, 2005, 2010, 2015, 2020, 2021]
WORLDCOVER_CLASSES = {
    10: "tree",
    20: "shrub",
    30: "grass",
    40: "cropland",
    50: "built",
    60: "bare",
    70: "snow_ice",
    80: "water",
    90: "wetland",
    95: "mangrove",
    100: "moss_lichen",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample public VIIRS/GHSL/WorldCover raster covariates at soil points.")
    parser.add_argument(
        "--input",
        default="data/processed/soil_heavy_metals_external_activity.csv",
        help="Input CSV with soil and existing external covariates.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/soil_heavy_metals_external_raster.csv",
        help="Output CSV enriched with remote raster covariates.",
    )
    parser.add_argument("--skip-viirs", action="store_true")
    parser.add_argument("--skip-ghsl", action="store_true")
    parser.add_argument("--skip-worldcover", action="store_true")
    parser.add_argument(
        "--viirs-mode",
        choices=["epochs", "annual"],
        default="epochs",
        help="Use selected VIIRS representative annual layers or every available annual layer.",
    )
    parser.add_argument(
        "--ghsl-mode",
        choices=["static", "temporal"],
        default="static",
        help="Use static GHSL representative epochs or nearest 5-year epoch for each row.",
    )
    parser.add_argument(
        "--ghsl-static-epochs",
        default="2020",
        help="Comma-separated GHSL epochs sampled for every row when --ghsl-mode static.",
    )
    return parser.parse_args()


def viirs_url(year: int) -> str:
    version = "20230318" if year <= 2011 else "20230823"
    filename = (
        f"nightlights.average_viirs.v21_m_500m_s_{year}0101_{year}1231_"
        f"go_epsg4326_v{version}.tif"
    )
    return f"{ZENODO_VIIRS_RECORD}/files/{filename}?download=1"


def viirs_difference_url() -> str:
    filename = "nightlights.difference_viirs.v21_m_500m_s_2000_2021_go_epsg4326_v20230318.tif"
    return f"{ZENODO_VIIRS_RECORD}/files/{filename}?download=1"


def ghsl_zip_tif_url(product: str, epoch: int) -> str:
    if product == "pop":
        dataset = "GHS_POP_GLOBE_R2023A"
        stem = f"GHS_POP_E{epoch}_GLOBE_R2023A_4326_30ss"
    elif product == "built":
        dataset = "GHS_BUILT_S_GLOBE_R2023A"
        stem = f"GHS_BUILT_S_E{epoch}_GLOBE_R2023A_4326_30ss"
    elif product == "built_nres":
        dataset = "GHS_BUILT_S_GLOBE_R2023A"
        stem = f"GHS_BUILT_S_NRES_E{epoch}_GLOBE_R2023A_4326_30ss"
    else:
        raise ValueError(product)
    zip_url = f"{GHSL_ROOT}/{dataset}/{stem}/V1-0/{stem}_V1_0.zip"
    tif_name = f"{stem}_V1_0.tif"
    return f"/vsizip/vsicurl/{zip_url}/{tif_name}"


def worldcover_tile_code(lon: float, lat: float) -> str:
    lon_base = math.floor(lon / 3.0) * 3
    lat_base = math.floor(lat / 3.0) * 3
    lat_prefix = "N" if lat_base >= 0 else "S"
    lon_prefix = "E" if lon_base >= 0 else "W"
    return f"{lat_prefix}{abs(lat_base):02.0f}{lon_prefix}{abs(lon_base):03.0f}"


def worldcover_url(tile_code: str) -> str:
    return f"{WORLDCOVER_ROOT}/ESA_WorldCover_10m_2021_v200_{tile_code}_Map.tif"


def sample_open_raster(url: str, coords: list[tuple[float, float]]) -> np.ndarray:
    if not coords:
        return np.empty(0, dtype=float)
    last_exc: Exception | None = None
    for attempt in range(5):
        try:
            with rasterio.Env(
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.zip",
                GDAL_HTTP_MULTIRANGE="YES",
            ):
                with rasterio.open(url) as src:
                    values = np.asarray([item[0] for item in src.sample(coords)], dtype=float)
                    if src.nodata is not None:
                        values[values == src.nodata] = np.nan
                    return values
        except RasterioIOError as exc:
            last_exc = exc
            wait = 20 * (attempt + 1)
            print(f"  raster read failed ({exc}); retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise RasterioIOError(str(last_exc))


def nearest_viirs_year(year: int) -> int:
    return int(min(max(year, 2000), 2021))


def nearest_viirs_epoch(year: int) -> int:
    year = nearest_viirs_year(year)
    return int(min(VIIRS_EPOCHS, key=lambda epoch: abs(epoch - year)))


def nearest_ghsl_epoch(year: int) -> int:
    return int(min(GHSL_EPOCHS, key=lambda epoch: abs(epoch - year)))


def add_viirs(df: pd.DataFrame, coords: list[tuple[float, float]], report: dict[str, object], mode: str) -> None:
    mapper = nearest_viirs_year if mode == "annual" else nearest_viirs_epoch
    years = df["year"].astype(int).map(mapper).to_numpy()
    df["viirs_year_used"] = years
    values = np.full(len(df), np.nan, dtype=float)
    for year in sorted(set(years)):
        idx = np.where(years == year)[0]
        print(f"Sampling VIIRS night lights year={year} n={len(idx)}", flush=True)
        vals = sample_open_raster(viirs_url(int(year)), [coords[i] for i in idx])
        values[idx] = vals
    df["viirs_ntl"] = values
    df["viirs_ntl_log1p"] = np.log1p(np.maximum(values, 0))
    print("Sampling VIIRS 2021 static and 2000-2021 change layers", flush=True)
    df["viirs_ntl_2021"] = sample_open_raster(viirs_url(2021), coords)
    df["viirs_ntl_2021_log1p"] = np.log1p(np.maximum(df["viirs_ntl_2021"].to_numpy(dtype=float), 0))
    df["viirs_ntl_change_2000_2021"] = sample_open_raster(viirs_difference_url(), coords)
    report["viirs"] = {
        "source": "Zenodo 10.5281/zenodo.8277198, based on Annual VNL V2 VIIRS",
        "years_used": sorted(int(year) for year in set(years)),
        "mode": mode,
        "note": "Rows after 2021 use the nearest available 2021 annual layer. Epoch mode uses representative annual layers to avoid remote-source rate limits.",
    }


def add_ghsl_temporal(df: pd.DataFrame, coords: list[tuple[float, float]], report: dict[str, object]) -> None:
    epochs = df["year"].astype(int).map(nearest_ghsl_epoch).to_numpy()
    df["ghsl_epoch_used"] = epochs
    product_cols = {
        "pop": "ghsl_pop",
        "built": "ghsl_built_surface_m2",
        "built_nres": "ghsl_built_nres_m2",
    }
    for product, col in product_cols.items():
        values = np.full(len(df), np.nan, dtype=float)
        for epoch in sorted(set(epochs)):
            idx = np.where(epochs == epoch)[0]
            print(f"Sampling GHSL {product} epoch={epoch} n={len(idx)}", flush=True)
            vals = sample_open_raster(ghsl_zip_tif_url(product, int(epoch)), [coords[i] for i in idx])
            values[idx] = vals
        df[col] = values
        df[f"{col}_log1p"] = np.log1p(np.maximum(values, 0))
    built = df["ghsl_built_surface_m2"].to_numpy(dtype=float)
    nres = df["ghsl_built_nres_m2"].to_numpy(dtype=float)
    df["ghsl_built_res_m2"] = np.maximum(built - nres, 0)
    df["ghsl_built_res_m2_log1p"] = np.log1p(df["ghsl_built_res_m2"].to_numpy(dtype=float))
    df["ghsl_built_nres_share"] = np.divide(nres, built, out=np.zeros_like(nres), where=built > 0)
    report["ghsl"] = {
        "source": "JRC GHSL R2023A 4326 30 arc-second grids",
        "epochs_used": sorted(int(epoch) for epoch in set(epochs)),
        "mode": "temporal",
        "note": "Epoch is nearest 5-year GHSL layer for each row year.",
    }


def add_ghsl_static(
    df: pd.DataFrame,
    coords: list[tuple[float, float]],
    report: dict[str, object],
    epochs: list[int],
) -> None:
    product_cols = {
        "pop": "ghsl_pop",
        "built": "ghsl_built_surface_m2",
        "built_nres": "ghsl_built_nres_m2",
    }
    for epoch in epochs:
        for product, base_col in product_cols.items():
            col = f"{base_col}_{epoch}"
            print(f"Sampling GHSL {product} static epoch={epoch} n={len(coords)}", flush=True)
            values = sample_open_raster(ghsl_zip_tif_url(product, int(epoch)), coords)
            df[col] = values
            df[f"{col}_log1p"] = np.log1p(np.maximum(values, 0))
        built = df[f"ghsl_built_surface_m2_{epoch}"].to_numpy(dtype=float)
        nres = df[f"ghsl_built_nres_m2_{epoch}"].to_numpy(dtype=float)
        df[f"ghsl_built_res_m2_{epoch}"] = np.maximum(built - nres, 0)
        df[f"ghsl_built_res_m2_{epoch}_log1p"] = np.log1p(df[f"ghsl_built_res_m2_{epoch}"].to_numpy(dtype=float))
        df[f"ghsl_built_nres_share_{epoch}"] = np.divide(nres, built, out=np.zeros_like(nres), where=built > 0)
    report["ghsl"] = {
        "source": "JRC GHSL R2023A 4326 30 arc-second grids",
        "epochs_used": [int(epoch) for epoch in epochs],
        "mode": "static",
        "note": "Static mode samples selected representative GHSL epochs for all rows to reduce remote IO.",
    }


def add_worldcover(df: pd.DataFrame, coords: list[tuple[float, float]], report: dict[str, object]) -> None:
    tile_codes = [worldcover_tile_code(lon, lat) for lon, lat in coords]
    class_values = np.full(len(df), np.nan, dtype=float)
    failures: dict[str, str] = {}
    for tile_code in sorted(set(tile_codes)):
        idx = [i for i, code in enumerate(tile_codes) if code == tile_code]
        print(f"Sampling ESA WorldCover tile={tile_code} n={len(idx)}", flush=True)
        try:
            vals = sample_open_raster(worldcover_url(tile_code), [coords[i] for i in idx])
            class_values[idx] = vals
        except RasterioIOError as exc:
            failures[tile_code] = str(exc)
    df["wc_class_2021"] = class_values
    for code, name in WORLDCOVER_CLASSES.items():
        df[f"wc_is_{name}"] = (class_values == code).astype(int)
    natural_codes = {10, 20, 30, 60, 70, 80, 90, 95, 100}
    vegetated_codes = {10, 20, 30, 40, 90, 95, 100}
    df["wc_is_natural"] = np.isin(class_values, list(natural_codes)).astype(int)
    df["wc_is_vegetated"] = np.isin(class_values, list(vegetated_codes)).astype(int)
    df["wc_is_built_or_cropland"] = np.isin(class_values, [40, 50]).astype(int)
    report["worldcover"] = {
        "source": "ESA WorldCover 10 m 2021 v200 COGs on AWS Open Data",
        "n_tiles": len(set(tile_codes)),
        "tile_failures": failures,
        "class_codes": WORLDCOVER_CLASSES,
    }


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    input_path = ROOT / args.input
    output_path = ROOT / args.output
    df = pd.read_csv(input_path)
    coords = [(float(lon), float(lat)) for lon, lat in df[["lon", "lat"]].to_numpy()]
    report: dict[str, object] = {
        "input_csv": str(input_path.relative_to(ROOT)),
        "output_csv": str(output_path.relative_to(ROOT)),
        "n_rows": int(len(df)),
    }
    if not args.skip_viirs:
        add_viirs(df, coords, report, args.viirs_mode)
    if not args.skip_ghsl:
        if args.ghsl_mode == "temporal":
            add_ghsl_temporal(df, coords, report)
        else:
            epochs = [int(item.strip()) for item in args.ghsl_static_epochs.split(",") if item.strip()]
            add_ghsl_static(df, coords, report, epochs)
    if not args.skip_worldcover:
        add_worldcover(df, coords, report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    report_path = TABLES_DIR / "remote_raster_covariates_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path.relative_to(ROOT)}")
    print(f"Wrote {report_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

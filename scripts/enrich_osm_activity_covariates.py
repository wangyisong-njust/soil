#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import shapefile
from sklearn.neighbors import BallTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import TABLES_DIR, ensure_project_dirs


EARTH_RADIUS_KM = 6371.0088
OSM_ZIP_URL = "https://download.geofabrik.de/asia/china-latest-free.shp.zip"

RAILWAY_LAYER = "gis_osm_railways_free_1"
TRAFFIC_LAYER = "gis_osm_traffic_free_1"
TRANSPORT_LAYER = "gis_osm_transport_free_1"
POI_LAYER = "gis_osm_pois_free_1"
LANDUSE_LAYER = "gis_osm_landuse_a_free_1"

ACTIVITY_POI_CLASSES = {
    "bank",
    "market_place",
    "mall",
    "supermarket",
    "department_store",
    "car_dealership",
    "doityourself",
    "furniture_shop",
    "fuel",
    "recycling",
    "waste_basket",
    "wastewater_plant",
    "water_works",
    "camera_surveillance",
    "comms_tower",
    "tower",
}
POLLUTION_POI_CLASSES = {
    "fuel",
    "recycling",
    "waste_basket",
    "wastewater_plant",
    "water_works",
    "car_dealership",
    "doityourself",
}

LANDUSE_GROUPS = {
    "built_landuse": {
        "residential",
        "industrial",
        "commercial",
        "retail",
        "farmyard",
        "military",
    },
    "industrial_landuse": {"industrial", "quarry"},
    "commercial_landuse": {"commercial", "retail"},
    "residential_landuse": {"residential"},
    "agricultural_landuse": {"farmland", "farmyard", "orchard", "vineyard"},
    "green_landuse": {"forest", "grass", "park", "scrub", "meadow", "nature_reserve", "heath"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add OSM traffic, railway, POI, and land-use covariates.")
    parser.add_argument(
        "--input",
        default="data/processed/soil_heavy_metals_external_osm.csv",
        help="Input CSV with existing soil/external covariates.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/soil_heavy_metals_external_activity.csv",
        help="Output CSV enriched with additional OSM activity covariates.",
    )
    parser.add_argument(
        "--osm-zip",
        default="data/external_raw/osm/china-latest-free.shp.zip",
        help="Geofabrik china-latest-free.shp.zip path.",
    )
    parser.add_argument("--extract-dir", default="data/external_raw/osm/china_shp")
    parser.add_argument("--radius-km", type=float, default=10.0)
    parser.add_argument("--rail-segment-step", type=int, default=1)
    parser.add_argument("--rail-chunk-size", type=int, default=200_000)
    return parser.parse_args()


def ensure_layers(zip_path: Path, extract_dir: Path, layers: list[str]) -> dict[str, Path]:
    suffixes = [".shp", ".shx", ".dbf", ".prj", ".cpg"]
    extract_dir.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for layer in layers:
            shp_candidates = [name for name in names if name.endswith(f"{layer}.shp")]
            if not shp_candidates:
                continue
            shp_name = shp_candidates[0]
            base = shp_name[: -len(".shp")]
            target_base = extract_dir / Path(base).name
            for suffix in suffixes:
                member = base + suffix
                final = target_base.with_suffix(suffix)
                if member in names and not final.exists():
                    zf.extract(member, extract_dir)
                    extracted = extract_dir / member
                    final.parent.mkdir(parents=True, exist_ok=True)
                    if extracted != final:
                        extracted.replace(final)
            found[layer] = target_base.with_suffix(".shp")
    return found


def field_index(reader: shapefile.Reader, field: str) -> int | None:
    names = [item[0] for item in reader.fields[1:]]
    return names.index(field) if field in names else None


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    lon1_r, lat1_r, lon2_r, lat2_r = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2_r - lon1_r
    dlat = lat2_r - lat1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def nearest_and_count(point_rad: np.ndarray, feature_rad: np.ndarray, radius_km: float) -> tuple[np.ndarray, np.ndarray]:
    if len(feature_rad) == 0:
        return np.full(len(point_rad), np.nan), np.zeros(len(point_rad), dtype=int)
    tree = BallTree(feature_rad, metric="haversine")
    dist, _ = tree.query(point_rad, k=1)
    counts = tree.query_radius(point_rad, r=radius_km / EARTH_RADIUS_KM, count_only=True)
    return dist[:, 0] * EARTH_RADIUS_KM, np.asarray(counts, dtype=int)


def nearest_count_and_weighted_sum(
    point_rad: np.ndarray,
    feature_rad: np.ndarray,
    weights: np.ndarray,
    radius_km: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if len(feature_rad) == 0:
        return np.full(len(point_rad), np.nan), np.zeros(len(point_rad), dtype=int), np.zeros(len(point_rad), dtype=float)
    tree = BallTree(feature_rad, metric="haversine")
    dist, _ = tree.query(point_rad, k=1)
    idxs = tree.query_radius(point_rad, r=radius_km / EARTH_RADIUS_KM)
    counts = np.zeros(len(point_rad), dtype=int)
    sums = np.zeros(len(point_rad), dtype=float)
    for i, idx in enumerate(idxs):
        counts[i] = len(idx)
        if len(idx):
            sums[i] = float(weights[idx].sum())
    return dist[:, 0] * EARTH_RADIUS_KM, counts, sums


def point_records(path: Path, selected_classes: set[str] | None = None) -> pd.DataFrame:
    reader = shapefile.Reader(str(path))
    fclass_idx = field_index(reader, "fclass")
    rows = []
    for shape_record in reader.iterShapeRecords():
        fclass = str(shape_record.record[fclass_idx]).lower() if fclass_idx is not None else ""
        if selected_classes is not None and fclass not in selected_classes:
            continue
        points = shape_record.shape.points
        if not points:
            continue
        arr = np.asarray(points, dtype=float)
        lon = float(np.nanmean(arr[:, 0]))
        lat = float(np.nanmean(arr[:, 1]))
        if np.isfinite(lon) and np.isfinite(lat):
            rows.append({"lat": lat, "lon": lon, "fclass": fclass})
    return pd.DataFrame(rows)


def polygon_area_km2(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    arr = np.asarray(points, dtype=float)
    lon = arr[:, 0]
    lat = arr[:, 1]
    lat0 = float(np.nanmean(lat))
    x = lon * math.cos(math.radians(lat0)) * 111.32
    y = lat * 110.57
    return abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)


def landuse_records(path: Path) -> pd.DataFrame:
    reader = shapefile.Reader(str(path))
    fclass_idx = field_index(reader, "fclass")
    selected = set().union(*LANDUSE_GROUPS.values())
    rows = []
    for shape_record in reader.iterShapeRecords():
        fclass = str(shape_record.record[fclass_idx]).lower() if fclass_idx is not None else ""
        if fclass not in selected:
            continue
        points = shape_record.shape.points
        if not points:
            continue
        arr = np.asarray(points, dtype=float)
        lon = float(np.nanmean(arr[:, 0]))
        lat = float(np.nanmean(arr[:, 1]))
        if not np.isfinite(lon) or not np.isfinite(lat):
            continue
        parts = list(shape_record.shape.parts) + [len(points)]
        area = 0.0
        for start, end in zip(parts[:-1], parts[1:]):
            area += polygon_area_km2(points[start:end])
        rows.append({"lat": lat, "lon": lon, "fclass": fclass, "area_km2": area})
    return pd.DataFrame(rows)


def line_density_features(
    path: Path,
    point_rad: np.ndarray,
    radius_km: float,
    segment_step: int,
    chunk_size: int,
) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    reader = shapefile.Reader(str(path))
    radius = radius_km / EARTH_RADIUS_KM
    area = math.pi * radius_km**2
    nearest = np.full(len(point_rad), np.inf, dtype=float)
    length_density = np.zeros(len(point_rad), dtype=float)
    mids: list[tuple[float, float]] = []
    lengths: list[float] = []
    n_segments = 0
    n_shapes = 0

    def flush() -> None:
        nonlocal mids, lengths
        if not mids:
            return
        mid_rad = np.radians(np.asarray(mids, dtype=float))
        length_arr = np.asarray(lengths, dtype=float)
        tree = BallTree(mid_rad, metric="haversine")
        dist, _ = tree.query(point_rad, k=1)
        np.minimum(nearest, dist[:, 0] * EARTH_RADIUS_KM, out=nearest)
        idxs = tree.query_radius(point_rad, r=radius)
        for point_i, idx in enumerate(idxs):
            if len(idx):
                length_density[point_i] += float(length_arr[idx].sum() / area)
        mids = []
        lengths = []

    for shape_record in reader.iterShapeRecords():
        n_shapes += 1
        points = shape_record.shape.points
        if len(points) < 2:
            continue
        parts = list(shape_record.shape.parts) + [len(points)]
        for start, end in zip(parts[:-1], parts[1:]):
            part_points = points[start:end]
            for i in range(0, len(part_points) - 1, max(1, segment_step)):
                lon1, lat1 = part_points[i]
                lon2, lat2 = part_points[i + 1]
                length = haversine_km(lon1, lat1, lon2, lat2)
                if not np.isfinite(length) or length <= 0:
                    continue
                mids.append(((lat1 + lat2) / 2, (lon1 + lon2) / 2))
                lengths.append(length)
                n_segments += 1
                if len(mids) >= chunk_size:
                    flush()
    flush()
    nearest[~np.isfinite(nearest)] = np.nan
    radius_label = int(radius_km)
    return (
        {
            "osm_nearest_railway_km": nearest,
            f"osm_railway_length_km_per_km2_{radius_label}km": length_density,
        },
        {"n_railway_shapes_processed": int(n_shapes), "n_railway_segments_sampled": int(n_segments)},
    )


def add_point_feature_block(
    df: pd.DataFrame,
    point_rad: np.ndarray,
    records: pd.DataFrame,
    prefix: str,
    radius_km: float,
) -> dict[str, int]:
    radius_label = int(radius_km)
    feature_rad = np.radians(records[["lat", "lon"]].to_numpy(dtype=float)) if len(records) else np.empty((0, 2))
    dist, count = nearest_and_count(point_rad, feature_rad, radius_km)
    df[f"osm_nearest_{prefix}_km"] = dist
    df[f"osm_{prefix}_count_{radius_label}km"] = count
    return {f"n_{prefix}_points": int(len(records))}


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    input_path = ROOT / args.input
    output_path = ROOT / args.output
    zip_path = ROOT / args.osm_zip
    extract_dir = ROOT / args.extract_dir
    if not zip_path.exists():
        raise SystemExit(f"Missing OSM zip: {zip_path}. Download from {OSM_ZIP_URL}")

    df = pd.read_csv(input_path)
    point_rad = np.radians(df[["lat", "lon"]].to_numpy(dtype=float))
    layers = ensure_layers(
        zip_path,
        extract_dir,
        [RAILWAY_LAYER, TRAFFIC_LAYER, TRANSPORT_LAYER, POI_LAYER, LANDUSE_LAYER],
    )
    report: dict[str, object] = {
        "source": "OpenStreetMap / Geofabrik",
        "url": OSM_ZIP_URL,
        "input_csv": str(input_path.relative_to(ROOT)),
        "output_csv": str(output_path.relative_to(ROOT)),
        "layers": {key: str(value.relative_to(ROOT)) for key, value in layers.items()},
        "radius_km": args.radius_km,
    }

    if RAILWAY_LAYER in layers:
        print("Building railway distance and density features...", flush=True)
        cols, rail_report = line_density_features(
            layers[RAILWAY_LAYER],
            point_rad,
            args.radius_km,
            args.rail_segment_step,
            args.rail_chunk_size,
        )
        for col, values in cols.items():
            df[col] = values
        report.update(rail_report)

    for layer, prefix in [(TRAFFIC_LAYER, "traffic_facility"), (TRANSPORT_LAYER, "transport_facility")]:
        if layer in layers:
            print(f"Reading {prefix} points...", flush=True)
            records = point_records(layers[layer])
            report.update(add_point_feature_block(df, point_rad, records, prefix, args.radius_km))
            if len(records):
                report[f"{prefix}_top_classes"] = records["fclass"].value_counts().head(20).to_dict()

    if POI_LAYER in layers:
        print("Reading activity and pollution-related POIs...", flush=True)
        activity_pois = point_records(layers[POI_LAYER], ACTIVITY_POI_CLASSES)
        pollution_pois = activity_pois[activity_pois["fclass"].isin(POLLUTION_POI_CLASSES)].copy()
        report.update(add_point_feature_block(df, point_rad, activity_pois, "activity_poi", args.radius_km))
        report.update(add_point_feature_block(df, point_rad, pollution_pois, "pollution_poi", args.radius_km))
        if len(activity_pois):
            report["activity_poi_top_classes"] = activity_pois["fclass"].value_counts().head(30).to_dict()

    if LANDUSE_LAYER in layers:
        print("Reading selected land-use polygons...", flush=True)
        landuse = landuse_records(layers[LANDUSE_LAYER])
        report["n_selected_landuse_polygons"] = int(len(landuse))
        report["landuse_top_classes"] = landuse["fclass"].value_counts().head(30).to_dict() if len(landuse) else {}
        radius_label = int(args.radius_km)
        area = math.pi * args.radius_km**2
        for group, classes in LANDUSE_GROUPS.items():
            subset = landuse[landuse["fclass"].isin(classes)].copy()
            feature_rad = np.radians(subset[["lat", "lon"]].to_numpy(dtype=float)) if len(subset) else np.empty((0, 2))
            weights = subset["area_km2"].to_numpy(dtype=float) if len(subset) else np.empty(0)
            dist, count, area_sum = nearest_count_and_weighted_sum(point_rad, feature_rad, weights, args.radius_km)
            df[f"osm_nearest_{group}_km"] = dist
            df[f"osm_{group}_count_{radius_label}km"] = count
            df[f"osm_{group}_area_km2_{radius_label}km"] = area_sum
            df[f"osm_{group}_area_frac_{radius_label}km"] = area_sum / area
            report[f"n_{group}_polygons"] = int(len(subset))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    report_path = TABLES_DIR / "osm_activity_covariates_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path.relative_to(ROOT)}")
    print(f"Wrote {report_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

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

from soilmodel.config import load_config
from soilmodel.paths import DATA_DIR, TABLES_DIR, ensure_project_dirs


EARTH_RADIUS_KM = 6371.0088
OSM_ZIP_URL = "https://download.geofabrik.de/asia/china-latest-free.shp.zip"

ROAD_LAYER = "gis_osm_roads_free_1"
POI_LAYER = "gis_osm_pois_free_1"
LANDUSE_LAYER = "gis_osm_landuse_a_free_1"

MAJOR_ROADS = {"motorway", "trunk", "primary", "secondary", "motorway_link", "trunk_link", "primary_link"}
INDUSTRIAL_CLASSES = {
    "industrial",
    "factory",
    "works",
    "power",
    "power_station",
    "power_substation",
    "wastewater_plant",
    "water_works",
    "landfill",
    "storage_tank",
}
MINING_CLASSES = {"mine", "quarry", "mining", "mineshaft"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract OSM human-activity covariates from Geofabrik shapefiles.")
    parser.add_argument("--config", default="configs/soil_experiment.json", help="Path to experiment JSON config.")
    parser.add_argument("--input", default="data/processed/soil_heavy_metals_external.csv", help="Input CSV path.")
    parser.add_argument("--output", default="data/processed/soil_heavy_metals_external_osm.csv", help="Output CSV path.")
    parser.add_argument(
        "--osm-zip",
        default="data/external_raw/osm/china-latest-free.shp.zip",
        help="Geofabrik china-latest-free.shp.zip path.",
    )
    parser.add_argument("--extract-dir", default="data/external_raw/osm/china_shp", help="Directory for selected shapefiles.")
    parser.add_argument("--radius-km", type=float, default=10.0, help="Buffer radius for density features.")
    parser.add_argument("--segment-step", type=int, default=1, help="Use every Nth road segment for speed.")
    parser.add_argument("--road-chunk-size", type=int, default=200_000, help="Road segment batch size.")
    parser.add_argument("--skip-roads", action="store_true", help="Skip large road layer and only build POI/landuse covariates.")
    return parser.parse_args()


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    lon1_r, lat1_r, lon2_r, lat2_r = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2_r - lon1_r
    dlat = lat2_r - lat1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def ensure_layers(zip_path: Path, extract_dir: Path) -> dict[str, Path]:
    needed = [ROAD_LAYER, POI_LAYER, LANDUSE_LAYER]
    suffixes = [".shp", ".shx", ".dbf", ".prj", ".cpg"]
    extract_dir.mkdir(parents=True, exist_ok=True)
    found: dict[str, Path] = {}
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for layer in needed:
            shp_candidates = [name for name in names if name.endswith(f"{layer}.shp")]
            if not shp_candidates:
                continue
            shp_name = shp_candidates[0]
            base = shp_name[: -len(".shp")]
            target_base = extract_dir / Path(base).name
            for suffix in suffixes:
                member = base + suffix
                if member in names and not (target_base.with_suffix(suffix)).exists():
                    zf.extract(member, extract_dir)
                    extracted = extract_dir / member
                    final = target_base.with_suffix(suffix)
                    final.parent.mkdir(parents=True, exist_ok=True)
                    if extracted != final:
                        extracted.replace(final)
            found[layer] = target_base.with_suffix(".shp")
    return found


def field_index(reader: shapefile.Reader, field: str) -> int | None:
    names = [item[0] for item in reader.fields[1:]]
    return names.index(field) if field in names else None


def sample_road_segments(path: Path, segment_step: int = 1) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    reader = shapefile.Reader(str(path))
    fclass_idx = field_index(reader, "fclass")
    midpoints: list[tuple[float, float]] = []
    lengths: list[float] = []
    is_major: list[int] = []
    for shape_record in reader.iterShapeRecords():
        points = shape_record.shape.points
        if len(points) < 2:
            continue
        fclass = str(shape_record.record[fclass_idx]).lower() if fclass_idx is not None else ""
        major = int(fclass in MAJOR_ROADS)
        parts = list(shape_record.shape.parts) + [len(points)]
        for start, end in zip(parts[:-1], parts[1:]):
            part_points = points[start:end]
            for i in range(0, len(part_points) - 1, max(1, segment_step)):
                lon1, lat1 = part_points[i]
                lon2, lat2 = part_points[i + 1]
                length = haversine_km(lon1, lat1, lon2, lat2)
                if not np.isfinite(length) or length <= 0:
                    continue
                midpoints.append(((lat1 + lat2) / 2, (lon1 + lon2) / 2))
                lengths.append(length)
                is_major.append(major)
    coords_rad = np.radians(np.asarray(midpoints, dtype=float))
    return coords_rad, np.asarray(lengths, dtype=float), np.asarray(is_major, dtype=bool)


def representative_points(path: Path, selected_classes: set[str], source_name: str) -> pd.DataFrame:
    reader = shapefile.Reader(str(path))
    fclass_idx = field_index(reader, "fclass")
    rows = []
    for shape_record in reader.iterShapeRecords():
        record = shape_record.record
        fclass = str(record[fclass_idx]).lower() if fclass_idx is not None else ""
        if selected_classes and fclass not in selected_classes:
            continue
        points = shape_record.shape.points
        if not points:
            continue
        arr = np.asarray(points, dtype=float)
        lon = float(np.nanmean(arr[:, 0]))
        lat = float(np.nanmean(arr[:, 1]))
        if np.isfinite(lon) and np.isfinite(lat):
            rows.append({"lat": lat, "lon": lon, "fclass": fclass, "source": source_name})
    return pd.DataFrame(rows)


def nearest_and_count(
    point_rad: np.ndarray,
    feature_rad: np.ndarray,
    radius_km: float,
) -> tuple[np.ndarray, np.ndarray]:
    if len(feature_rad) == 0:
        return np.full(len(point_rad), np.nan), np.zeros(len(point_rad), dtype=int)
    tree = BallTree(feature_rad, metric="haversine")
    dist, _ = tree.query(point_rad, k=1)
    counts = tree.query_radius(point_rad, r=radius_km / EARTH_RADIUS_KM, count_only=True)
    return dist[:, 0] * EARTH_RADIUS_KM, np.asarray(counts, dtype=int)


def road_features(point_rad: np.ndarray, road_rad: np.ndarray, lengths: np.ndarray, is_major: np.ndarray, radius_km: float) -> dict[str, np.ndarray]:
    tree = BallTree(road_rad, metric="haversine")
    nearest_dist, _ = tree.query(point_rad, k=1)
    nearest_major = np.full(len(point_rad), np.nan)
    if is_major.any():
        major_tree = BallTree(road_rad[is_major], metric="haversine")
        major_dist, _ = major_tree.query(point_rad, k=1)
        nearest_major = major_dist[:, 0] * EARTH_RADIUS_KM

    radius = radius_km / EARTH_RADIUS_KM
    area = math.pi * radius_km**2
    road_length_density = np.zeros(len(point_rad), dtype=float)
    major_length_density = np.zeros(len(point_rad), dtype=float)
    indices = tree.query_radius(point_rad, r=radius)
    for i, idx in enumerate(indices):
        if len(idx):
            road_length_density[i] = float(lengths[idx].sum() / area)
            major_length_density[i] = float(lengths[idx][is_major[idx]].sum() / area)
    return {
        "osm_nearest_road_km": nearest_dist[:, 0] * EARTH_RADIUS_KM,
        "osm_nearest_major_road_km": nearest_major,
        f"osm_road_length_km_per_km2_{int(radius_km)}km": road_length_density,
        f"osm_major_road_length_km_per_km2_{int(radius_km)}km": major_length_density,
    }


def road_features_streaming(
    path: Path,
    point_rad: np.ndarray,
    radius_km: float,
    segment_step: int = 1,
    chunk_size: int = 200_000,
) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    reader = shapefile.Reader(str(path))
    fclass_idx = field_index(reader, "fclass")
    radius = radius_km / EARTH_RADIUS_KM
    area = math.pi * radius_km**2
    nearest_road = np.full(len(point_rad), np.inf, dtype=float)
    nearest_major = np.full(len(point_rad), np.inf, dtype=float)
    road_length_density = np.zeros(len(point_rad), dtype=float)
    major_length_density = np.zeros(len(point_rad), dtype=float)
    mids: list[tuple[float, float]] = []
    lengths: list[float] = []
    majors: list[bool] = []
    n_segments = 0
    n_major_segments = 0
    n_shapes = 0

    def flush() -> None:
        nonlocal mids, lengths, majors
        if not mids:
            return
        mid_rad = np.radians(np.asarray(mids, dtype=float))
        length_arr = np.asarray(lengths, dtype=float)
        major_arr = np.asarray(majors, dtype=bool)
        tree = BallTree(mid_rad, metric="haversine")
        dist, _ = tree.query(point_rad, k=1)
        np.minimum(nearest_road, dist[:, 0] * EARTH_RADIUS_KM, out=nearest_road)
        idxs = tree.query_radius(point_rad, r=radius)
        for point_i, idx in enumerate(idxs):
            if len(idx):
                road_length_density[point_i] += float(length_arr[idx].sum() / area)
                if major_arr[idx].any():
                    major_length_density[point_i] += float(length_arr[idx][major_arr[idx]].sum() / area)
        if major_arr.any():
            major_tree = BallTree(mid_rad[major_arr], metric="haversine")
            major_dist, _ = major_tree.query(point_rad, k=1)
            np.minimum(nearest_major, major_dist[:, 0] * EARTH_RADIUS_KM, out=nearest_major)
        mids = []
        lengths = []
        majors = []

    for shape_record in reader.iterShapeRecords():
        n_shapes += 1
        points = shape_record.shape.points
        if len(points) < 2:
            continue
        fclass = str(shape_record.record[fclass_idx]).lower() if fclass_idx is not None else ""
        major = fclass in MAJOR_ROADS
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
                majors.append(major)
                n_segments += 1
                n_major_segments += int(major)
                if len(mids) >= chunk_size:
                    flush()
        if n_shapes % 200_000 == 0:
            print(f"  processed road shapes={n_shapes:,}, segments={n_segments:,}", flush=True)
    flush()
    nearest_road[~np.isfinite(nearest_road)] = np.nan
    nearest_major[~np.isfinite(nearest_major)] = np.nan
    return (
        {
            "osm_nearest_road_km": nearest_road,
            "osm_nearest_major_road_km": nearest_major,
            f"osm_road_length_km_per_km2_{int(radius_km)}km": road_length_density,
            f"osm_major_road_length_km_per_km2_{int(radius_km)}km": major_length_density,
        },
        {
            "n_road_shapes_processed": int(n_shapes),
            "n_road_segments_sampled": int(n_segments),
            "n_major_road_segments_sampled": int(n_major_segments),
        },
    )


def main() -> None:
    args = parse_args()
    ensure_project_dirs()
    _ = load_config(ROOT / args.config)
    input_path = ROOT / args.input
    output_path = ROOT / args.output
    zip_path = ROOT / args.osm_zip
    extract_dir = ROOT / args.extract_dir
    if not zip_path.exists():
        raise SystemExit(f"Missing OSM zip: {zip_path}. Download from {OSM_ZIP_URL}")

    df = pd.read_csv(input_path)
    point_rad = np.radians(df[["lat", "lon"]].to_numpy(dtype=float))
    layers = ensure_layers(zip_path, extract_dir)
    report: dict[str, object] = {
        "source": "OpenStreetMap / Geofabrik",
        "url": OSM_ZIP_URL,
        "input_csv": str(input_path.relative_to(ROOT)),
        "output_csv": str(output_path.relative_to(ROOT)),
        "layers": {key: str(value.relative_to(ROOT)) for key, value in layers.items()},
        "radius_km": args.radius_km,
        "segment_step": args.segment_step,
    }

    if ROAD_LAYER not in layers and not args.skip_roads:
        raise SystemExit("Road layer not found in OSM zip.")
    if args.skip_roads:
        report["road_layer_skipped"] = True
    else:
        print("Sampling road segments...", flush=True)
        road_cols, road_report = road_features_streaming(
            layers[ROAD_LAYER],
            point_rad,
            args.radius_km,
            segment_step=args.segment_step,
            chunk_size=args.road_chunk_size,
        )
        report.update(road_report)
        for col, values in road_cols.items():
            df[col] = values

    poi_frames = []
    if POI_LAYER in layers:
        print("Reading industrial/mining POIs...", flush=True)
        poi_frames.append(representative_points(layers[POI_LAYER], INDUSTRIAL_CLASSES | MINING_CLASSES, "pois"))
    if LANDUSE_LAYER in layers:
        print("Reading industrial/mining landuse polygons...", flush=True)
        poi_frames.append(representative_points(layers[LANDUSE_LAYER], INDUSTRIAL_CLASSES | MINING_CLASSES, "landuse"))

    if poi_frames:
        source_df = pd.concat([frame for frame in poi_frames if len(frame)], ignore_index=True)
    else:
        source_df = pd.DataFrame(columns=["lat", "lon", "fclass", "source"])
    report["n_pollution_source_points"] = int(len(source_df))
    if len(source_df):
        all_source_rad = np.radians(source_df[["lat", "lon"]].to_numpy(dtype=float))
        industrial_df = source_df[source_df["fclass"].isin(INDUSTRIAL_CLASSES)]
        mining_df = source_df[source_df["fclass"].isin(MINING_CLASSES)]
        dist, count = nearest_and_count(point_rad, all_source_rad, args.radius_km)
        df["osm_nearest_industrial_or_mining_km"] = dist
        df[f"osm_industrial_or_mining_count_{int(args.radius_km)}km"] = count
        for name, subset in [("industrial", industrial_df), ("mining", mining_df)]:
            subset_rad = np.radians(subset[["lat", "lon"]].to_numpy(dtype=float)) if len(subset) else np.empty((0, 2))
            dist, count = nearest_and_count(point_rad, subset_rad, args.radius_km)
            df[f"osm_nearest_{name}_km"] = dist
            df[f"osm_{name}_count_{int(args.radius_km)}km"] = count
            report[f"n_{name}_source_points"] = int(len(subset))
    else:
        for col in [
            "osm_nearest_industrial_or_mining_km",
            f"osm_industrial_or_mining_count_{int(args.radius_km)}km",
            "osm_nearest_industrial_km",
            f"osm_industrial_count_{int(args.radius_km)}km",
            "osm_nearest_mining_km",
            f"osm_mining_count_{int(args.radius_km)}km",
        ]:
            df[col] = np.nan

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    report_path = TABLES_DIR / "osm_covariates_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path.relative_to(ROOT)}")
    print(f"Wrote {report_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

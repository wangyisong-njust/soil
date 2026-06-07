from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"
RESULTS_DIR = PROJECT_ROOT / "results"
TABLES_DIR = PROJECT_ROOT / "tables"
FIGURES_DIR = PROJECT_ROOT / "figures"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"

PROCESSED_DATA_CANDIDATES = [
    PROCESSED_DATA_DIR / "soil_heavy_metals_geology.csv",
    PROCESSED_DATA_DIR / "soil_heavy_metals_terrain.csv",
    PROCESSED_DATA_DIR / "soil_heavy_metals_external_raster.csv",
    PROCESSED_DATA_DIR / "soil_heavy_metals_external_activity.csv",
    PROCESSED_DATA_DIR / "soil_heavy_metals_external_osm.csv",
    PROCESSED_DATA_DIR / "soil_heavy_metals_external.csv",
    PROCESSED_DATA_DIR / "soil_heavy_metals.csv",
]


def ensure_project_dirs() -> None:
    for path in [
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        DOCS_DIR,
        RESULTS_DIR,
        TABLES_DIR,
        FIGURES_DIR,
        MODELS_DIR,
        LOGS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def preferred_processed_data_path() -> Path:
    for path in PROCESSED_DATA_CANDIDATES:
        if path.exists() and path.stat().st_size:
            return path
    raise FileNotFoundError("Missing processed data. Run scripts/convert_xlsx_to_csv.py first.")

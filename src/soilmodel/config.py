from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import CONFIG_DIR


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else CONFIG_DIR / "soil_experiment.json"
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def target_columns(config: dict[str, Any] | None = None, path: str | Path | None = None) -> list[str]:
    cfg = config if config is not None else load_config(path)
    return [str(item) for item in cfg["target_columns"]]

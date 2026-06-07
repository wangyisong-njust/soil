#!/usr/bin/env python
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


REQUIRED = [
    "pandas",
    "numpy",
    "sklearn",
    "matplotlib",
    "seaborn",
    "openpyxl",
    "pypdf",
    "joblib",
]

OPTIONAL_MODELS = ["xgboost", "lightgbm", "catboost", "ngboost", "shap"]


def main() -> None:
    print(f"Python: {sys.version.split()[0]}")
    failed: list[str] = []
    for name in REQUIRED + OPTIONAL_MODELS:
        try:
            mod = importlib.import_module(name)
            version = getattr(mod, "__version__", "unknown")
            print(f"OK {name} {version}")
        except Exception as exc:
            print(f"MISS {name}: {exc}")
            if name in REQUIRED:
                failed.append(name)
    if failed:
        raise SystemExit(f"Missing required packages: {', '.join(failed)}")


if __name__ == "__main__":
    main()


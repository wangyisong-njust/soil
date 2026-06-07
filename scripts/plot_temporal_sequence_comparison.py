#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soilmodel.paths import FIGURES_DIR, TABLES_DIR, ensure_project_dirs


def write_skip_report(reason: str) -> None:
    path = TABLES_DIR / "temporal_sequence_vs_external_delta.csv"
    pd.DataFrame(
        [{"status": "skipped", "reason": reason}]
    ).to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Skipped temporal sequence comparison: {reason}")


def main() -> None:
    ensure_project_dirs()
    external_path = TABLES_DIR / "external_covariate_best_metrics.csv"
    temporal_path = TABLES_DIR / "temporal_sequence_best_metrics.csv"
    if not external_path.exists() or external_path.stat().st_size == 0:
        write_skip_report("missing external_covariate_best_metrics.csv")
        return
    if not temporal_path.exists() or temporal_path.stat().st_size == 0:
        write_skip_report("missing temporal_sequence_best_metrics.csv")
        return
    external = pd.read_csv(external_path)
    temporal = pd.read_csv(temporal_path)
    ext = external[
        (external["feature_set"] == "external_covariates")
        & (external["protocol"] == "temporal_2022_2026")
    ][["target", "model", "r2", "rmse", "mae", "mape"]].rename(
        columns={
            "model": "external_model",
            "r2": "external_r2",
            "rmse": "external_rmse",
            "mae": "external_mae",
            "mape": "external_mape",
        }
    )
    ts = temporal[temporal["protocol"] == "temporal_2022_2026"][
        ["target", "method", "model", "r2", "rmse", "mae", "mape"]
    ].rename(
        columns={
            "method": "temporal_method",
            "model": "temporal_model",
            "r2": "temporal_r2",
            "rmse": "temporal_rmse",
            "mae": "temporal_mae",
            "mape": "temporal_mape",
        }
    )
    compare = ext.merge(ts, on="target", how="inner").sort_values("target")
    compare["delta_r2_temporal_minus_external"] = compare["temporal_r2"] - compare["external_r2"]
    compare.to_csv(TABLES_DIR / "temporal_sequence_vs_external_delta.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#59A14F" if value >= 0 else "#E15759" for value in compare["delta_r2_temporal_minus_external"]]
    ax.bar(compare["target"], compare["delta_r2_temporal_minus_external"], color=colors)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("Temporal-Sequence Innovation R2 Change vs External-Covariate Model")
    ax.set_xlabel("Heavy metal target")
    ax.set_ylabel("Delta R2")
    ax.grid(axis="y", alpha=0.25)
    for patch in ax.patches:
        value = patch.get_height()
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            value + (0.025 if value >= 0 else -0.025),
            f"{value:+.2f}",
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=9,
        )
    out = FIGURES_DIR / "temporal_sequence_models" / "delta_vs_external_temporal_2022_2026.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Wrote {TABLES_DIR / 'temporal_sequence_vs_external_delta.csv'}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

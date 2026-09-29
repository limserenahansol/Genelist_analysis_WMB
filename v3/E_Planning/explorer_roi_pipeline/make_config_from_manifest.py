"""Validate a flat ROI manifest and create the JSON consumed by pipeline scripts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REQUIRED = [
    "roi_name", "animal_id", "condition", "anatomy", "section_id", "xenium",
    "explorer_cells_csv", "explorer_coordinates_csv",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(HERE / "four_mouse_24roi_manifest_template.csv"))
    parser.add_argument("--output", default=str(HERE / "rois_four_mouse_generated.json"))
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, dtype=str).fillna("")
    missing = [column for column in REQUIRED if column not in manifest.columns]
    if missing:
        raise ValueError(f"Missing manifest columns: {missing}")
    if manifest["roi_name"].duplicated().any():
        duplicates = manifest.loc[manifest["roi_name"].duplicated(), "roi_name"].tolist()
        raise ValueError(f"Duplicate roi_name values: {duplicates}")
    if not set(manifest["condition"]).issubset({"Active", "Passive"}):
        raise ValueError("condition must be Active or Passive")
    if not set(manifest["anatomy"]).issubset({"ORBm", "BMAp"}):
        raise ValueError("anatomy must be ORBm or BMAp")
    condition_per_mouse = manifest.groupby("animal_id")["condition"].nunique()
    if (condition_per_mouse != 1).any():
        raise ValueError("Each animal_id must have exactly one condition")

    if not args.allow_incomplete:
        animals_by_condition = manifest.drop_duplicates("animal_id").groupby("condition")["animal_id"].nunique()
        if animals_by_condition.to_dict() != {"Active": 2, "Passive": 2}:
            raise ValueError(f"Expected 2 Active and 2 Passive mice: {animals_by_condition.to_dict()}")
        section_counts = manifest.groupby(["animal_id", "anatomy"])["section_id"].nunique()
        if not (section_counts == 3).all():
            raise ValueError(f"Expected three sections per mouse and anatomy: {section_counts.to_dict()}")
        if len(manifest) != 24:
            raise ValueError(f"Expected 24 ROI rows, found {len(manifest)}")

    rois = []
    for record in manifest.to_dict(orient="records"):
        record["module_set"] = record.get("module_set") or (
            "ORBm_layers" if record["anatomy"] == "ORBm" else "BMAp_classes"
        )
        if record.get("tdtom_min_counts"):
            record["tdtom_min_counts"] = int(record["tdtom_min_counts"])
        else:
            record.pop("tdtom_min_counts", None)
        rois.append({key: value for key, value in record.items() if value != ""})

    output = {
        "panel_note": "Four-mouse reporter-aware design; three sections per anatomy are nested within mouse.",
        "rois": rois,
    }
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {args.output}: {len(rois)} ROI rows")


if __name__ == "__main__":
    main()

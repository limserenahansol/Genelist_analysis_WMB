"""Build Cell-ID lists for new Explorer polygons that have no cells_stats.csv.

Centroid-in-polygon. Does not modify the Xenium folders.
Explorer's own cell count uses cells fully inside the polygon, so the two counts can differ.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from matplotlib.path import Path as MplPath

OUT = Path(__file__).resolve().parent / "outputs" / "derived_explorer_cells"
OUT.mkdir(parents=True, exist_ok=True)

JOBS = [
    {
        "roi_name": "orbm_r2_right",
        "anatomy": "ORBm",
        "slide": "0063814",
        "region": "Region_2",
        "module_set": "ORBm_layers",
        "xenium": r"D:\output-XETG00277__0063814__Region_2__20260923__002559",
        "polygon_csv": r"D:\output-XETG00277__0063814__Region_2__20260923__002559\orbm_right_coordinates.csv",
        "selection": "orbm_right",
        "explorer_cell_count": 951,
    },
    {
        "roi_name": "bla_r1_left",
        "anatomy": "BLA",
        "slide": "0063817",
        "region": "Region_1",
        "module_set": "BMAp_classes",
        "xenium": r"D:\output-XETG00277__0063817__Region_1__20260923__002558",
        "polygon_csv": r"D:\output-XETG00277__0063817__Region_1__20260923__002558\BLA_left_right.csv",
        "selection": "BLA_left",
        "explorer_cell_count": None,
    },
    {
        "roi_name": "bla_r1_right",
        "anatomy": "BLA",
        "slide": "0063817",
        "region": "Region_1",
        "module_set": "BMAp_classes",
        "xenium": r"D:\output-XETG00277__0063817__Region_1__20260923__002558",
        "polygon_csv": r"D:\output-XETG00277__0063817__Region_1__20260923__002558\BLA_left_right.csv",
        "selection": "BLA_right",
        "explorer_cell_count": None,
    },
    {
        "roi_name": "bla_r2_left",
        "anatomy": "BLA",
        "slide": "0063817",
        "region": "Region_2",
        "module_set": "BMAp_classes",
        "xenium": r"D:\output-XETG00277__0063817__Region_2__20260923__002559",
        "polygon_csv": r"D:\output-XETG00277__0063817__Region_2__20260923__002559\coordinates.csv",
        "selection": "BLA_left",
        "explorer_cell_count": 707,
    },
    {
        "roi_name": "bla_r2_right",
        "anatomy": "BLA",
        "slide": "0063817",
        "region": "Region_2",
        "module_set": "BMAp_classes",
        "xenium": r"D:\output-XETG00277__0063817__Region_2__20260923__002559",
        "polygon_csv": r"D:\output-XETG00277__0063817__Region_2__20260923__002559\coordinates.csv",
        "selection": "BLA_right",
        "explorer_cell_count": 1601,
    },
    {
        "roi_name": "cea_r2_left",
        "anatomy": "CEA",
        "slide": "0063817",
        "region": "Region_2",
        "module_set": "BMAp_classes",
        "xenium": r"D:\output-XETG00277__0063817__Region_2__20260923__002559",
        "polygon_csv": r"D:\output-XETG00277__0063817__Region_2__20260923__002559\coordinates.csv",
        "selection": "CEA_left",
        "explorer_cell_count": 1013,
    },
    {
        "roi_name": "cea_r2_right",
        "anatomy": "CEA",
        "slide": "0063817",
        "region": "Region_2",
        "module_set": "BMAp_classes",
        "xenium": r"D:\output-XETG00277__0063817__Region_2__20260923__002559",
        "polygon_csv": r"D:\output-XETG00277__0063817__Region_2__20260923__002559\coordinates.csv",
        "selection": "CEA_right",
        "explorer_cell_count": 852,
    },
]


def centroids(xenium: Path) -> pd.DataFrame:
    cells = pd.read_parquet(xenium / "cells.parquet")
    cells["cell_id"] = cells["cell_id"].astype(str)
    cl = pd.read_csv(xenium / "analysis" / "clustering" / "gene_expression_graphclust" / "clusters.csv")
    cl["Barcode"] = cl["Barcode"].astype(str)
    cl["Cluster"] = "Cluster " + cl["Cluster"].astype(str)
    cells = cells.merge(cl, left_on="cell_id", right_on="Barcode", how="left")
    return cells


def selection_xy(path: Path, selection: str):
    df = pd.read_csv(path, comment="#")
    if "Selection" in df.columns:
        df = df[df["Selection"].astype(str) == selection]
    return df["X"].to_numpy(float), df["Y"].to_numpy(float)


def main():
    cache = {}
    rois = []
    rows = []
    # Direct Explorer cell-ID exports.
    direct = [
        {
            "roi_name": "orbm_r3_left",
            "anatomy": "ORBm",
            "slide": "0063814",
            "region": "Region_3",
            "module_set": "ORBm_layers",
            "xenium": r"D:\output-XETG00277__0063814__Region_3__20260923__002559",
            "explorer_cells_csv": "orbm_left_cells_stats.csv",
            "explorer_coordinates_csv": "orbm_left_coordinates.csv",
            "assignment": "explorer_cells_stats",
        },
        {
            "roi_name": "bmap_r1_right",
            "anatomy": "BMAp",
            "slide": "0063817",
            "region": "Region_1",
            "module_set": "BMAp_classes",
            "xenium": r"D:\output-XETG00277__0063817__Region_1__20260923__002558",
            "explorer_cells_csv": "bmap_right_cells_stats.csv",
            "explorer_coordinates_csv": "",
            "assignment": "explorer_cells_stats",
        },
    ]
    for cfg in direct:
        n = len(pd.read_csv(Path(cfg["xenium"]) / cfg["explorer_cells_csv"], comment="#"))
        rows.append({**cfg, "n_cells": n, "explorer_complete_count": n, "status": "ready"})
        rois.append({k: cfg[k] for k in ["roi_name", "anatomy", "slide", "region", "module_set", "xenium", "explorer_cells_csv", "explorer_coordinates_csv"]})
        rois[-1]["animal_id"] = f"pilot_slide_{cfg['slide']}"

    for job in JOBS:
        xenium = Path(job["xenium"])
        if xenium not in cache:
            cache[xenium] = centroids(xenium)
        cells = cache[xenium]
        x, y = selection_xy(Path(job["polygon_csv"]), job["selection"])
        cell_box = (cells["x_centroid"].min(), cells["x_centroid"].max(), cells["y_centroid"].min(), cells["y_centroid"].max())
        overlaps = (x.max() >= cell_box[0]) and (x.min() <= cell_box[1]) and (y.max() >= cell_box[2]) and (y.min() <= cell_box[3])
        if not overlaps or len(x) < 3:
            rows.append({**job, "n_cells": 0, "status": "polygon_outside_section"})
            continue
        path = MplPath(list(zip(x, y)))
        inside = path.contains_points(cells[["x_centroid", "y_centroid"]].to_numpy())
        hit = cells.loc[inside].copy()
        status = "ready" if len(hit) >= 30 else "too_few_cells"
        cells_path = OUT / f"{job['roi_name']}_cells_stats.csv"
        coord_path = OUT / f"{job['roi_name']}_coordinates.csv"
        out_cells = pd.DataFrame({
            "Cell ID": hit["cell_id"],
            "Cluster": hit["Cluster"].fillna("NA"),
            "Transcripts": hit["transcript_counts"],
            "Area (um^2)": hit["cell_area"],
        })
        cells_path.write_text(
            f"#Selection name: {job['selection']}\n#Assignment: centroid in polygon\n" + out_cells.to_csv(index=False),
            encoding="utf-8",
        )
        pd.DataFrame({"Selection": job["selection"], "X": x, "Y": y}).to_csv(coord_path, index=False)
        rows.append({
            "roi_name": job["roi_name"],
            "anatomy": job["anatomy"],
            "n_cells": int(len(hit)),
            "explorer_complete_count": job["explorer_cell_count"],
            "status": status,
            "assignment": "centroid_in_polygon",
        })
        if status == "ready":
            rois.append({
                "roi_name": job["roi_name"],
                "anatomy": job["anatomy"],
                "animal_id": f"pilot_slide_{job['slide']}",
                "slide": job["slide"],
                "region": job["region"],
                "xenium": job["xenium"],
                "explorer_cells_csv": str(cells_path),
                "explorer_coordinates_csv": str(coord_path),
                "module_set": {
                    "BLA": "BLA_types",
                    "CEA": "CEA_types",
                }.get(job["anatomy"], job["module_set"]),
            })
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "assignment_check.csv", index=False)
    cfg = {
        "panel_note": (
            "New Explorer exports on the 247-gene pilot. BLA and CEA use Allen-informed "
            "region-specific marker modules; _like labels remain provisional when the defining "
            "Allen gene is absent from this panel."
        ),
        "rois": rois,
    }
    dest = Path(__file__).resolve().parent / "rois_new_exports.json"
    dest.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(tab.to_string(index=False))
    print("config", dest, "n_rois", len(rois))


if __name__ == "__main__":
    main()

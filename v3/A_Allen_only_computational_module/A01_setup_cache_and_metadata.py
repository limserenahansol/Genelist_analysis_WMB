#!/usr/bin/env python
"""
A01_setup_cache_and_metadata.py

Module A: Allen-only computational module.
Purpose:
- Initialize Allen ABC cache (manifest pinned via project_config.yaml if set).
- Save WMB metadata + WMB-taxonomy parquet snapshots for downstream modules.
- Append a record to run_log.jsonl for traceability.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.config import load_config, open_abc_cache, write_run_log  # noqa: E402

REQUESTS = [
    ("WMB-10X", "cell_metadata"),
    ("WMB-10X", "cell_metadata_with_cluster_annotation"),
    ("WMB-10X", "gene"),
    ("WMB-10X", "region_of_interest_metadata"),
    ("WMB-taxonomy", "cluster"),
    ("WMB-taxonomy", "cluster_annotation_term"),
    ("WMB-taxonomy", "cluster_to_cluster_annotation_membership_pivoted"),
]


def safe_metadata(cache, directory: str, file_name: str):
    try:
        return cache.get_metadata_dataframe(directory=directory, file_name=file_name)
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Failed {directory}/{file_name}: {e}")
        return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default=None)
    p.add_argument("--out_dir", required=True)
    args = p.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config(args.config)
    cache = open_abc_cache(cfg)

    audit: list[dict] = []
    for directory, file_name in REQUESTS:
        df = safe_metadata(cache, directory, file_name)
        if df is None:
            audit.append({"directory": directory, "file_name": file_name, "status": "failed"})
            continue
        path = out / f"{directory}__{file_name}.parquet"
        df.to_parquet(path, index=True)
        audit.append(
            {
                "directory": directory,
                "file_name": file_name,
                "status": "loaded",
                "n_rows": int(df.shape[0]),
                "n_cols": int(df.shape[1]),
                "columns_first_80": ";".join(map(str, df.columns[:80])),
                "saved_to": str(path),
            }
        )
        print(f"[OK] {directory}/{file_name}: {df.shape}")

    pd.DataFrame(audit).to_csv(out / "Allen_Metadata_Audit.csv", index=False)
    write_run_log(
        out,
        "A01_setup_cache_and_metadata",
        {
            "cache_dir": str(cfg.cache_dir),
            "manifest_version": cfg.manifest_version,
            "n_requests": len(REQUESTS),
        },
    )
    print("[DONE] Wrote Allen_Metadata_Audit.csv")


if __name__ == "__main__":
    main()

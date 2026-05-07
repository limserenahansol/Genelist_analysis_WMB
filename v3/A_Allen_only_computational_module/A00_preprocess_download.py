#!/usr/bin/env python
"""
A00_preprocess_download.py

Module A: Allen-only computational module - PREPROCESSING.

Why this script exists
----------------------
Before any region/GPCR analysis can run we must (1) prove `abc_atlas_access`
talks to the Allen public S3 bucket, (2) ensure the cache directory has enough
free space, (3) download the small metadata Allen requires to map cells to
clusters/regions/genes, and (4) optionally kick off paper raw-data downloads
described in `inputs/paper_source_manifest_template.csv`.

Outputs
-------
- preprocess_summary.csv  : versions, manifest, cache size, free disk
- allen_metadata_files.csv: which Allen metadata files are now in cache
- paper_download_status.csv (optional)
- run_log.jsonl           : appends a record describing this run

This is intentionally separate from A01 so users can debug environment
issues (network, cache, manifest pin) without running the full audit.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import urllib.request
from pathlib import Path

import pandas as pd

# Allow running as a script: add repo root to sys.path so `common` resolves.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.config import load_config, open_abc_cache, write_run_log  # noqa: E402

ALLEN_METADATA_REQUESTS = [
    ("WMB-10X", "cell_metadata_with_cluster_annotation"),
    ("WMB-10X", "gene"),
    ("WMB-10X", "region_of_interest_metadata"),
    ("WMB-taxonomy", "cluster"),
    ("WMB-taxonomy", "cluster_annotation_term"),
    ("WMB-taxonomy", "cluster_to_cluster_annotation_membership_pivoted"),
]


def _bytes_to_gib(n: int) -> float:
    return round(n / (1024**3), 2)


def _measure_cache(cache_dir: Path) -> tuple[int, int]:
    """Return (n_files, total_bytes) under cache_dir."""
    n, total = 0, 0
    if not cache_dir.is_dir():
        return 0, 0
    for p in cache_dir.rglob("*"):
        if p.is_file():
            n += 1
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return n, total


def _disk_free(path: Path) -> int:
    try:
        return shutil.disk_usage(str(path if path.is_dir() else path.parent)).free
    except OSError:
        return 0


def _download_allen_metadata(cache, out_rows: list[dict]) -> None:
    for directory, file_name in ALLEN_METADATA_REQUESTS:
        try:
            df = cache.get_metadata_dataframe(directory=directory, file_name=file_name)
            out_rows.append(
                {
                    "directory": directory,
                    "file_name": file_name,
                    "status": "ok",
                    "n_rows": int(df.shape[0]),
                    "n_cols": int(df.shape[1]),
                }
            )
            print(f"[OK] Allen metadata {directory}/{file_name}: {df.shape}")
        except Exception as e:  # noqa: BLE001
            out_rows.append(
                {
                    "directory": directory,
                    "file_name": file_name,
                    "status": f"failed: {e!s}",
                    "n_rows": 0,
                    "n_cols": 0,
                }
            )
            print(f"[WARN] Allen metadata {directory}/{file_name}: {e}")


def _download_paper_manifest(manifest_csv: Path, download_dir: Path) -> pd.DataFrame:
    rows: list[dict] = []
    if not manifest_csv.exists():
        print(f"[INFO] Paper manifest not found at {manifest_csv}; skipping paper downloads.")
        return pd.DataFrame()
    download_dir.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(manifest_csv)
    for _, r in manifest.iterrows():
        url = str(r.get("data_url", "") or "").strip()
        paper_id = str(r.get("paper_id", "paper") or "paper").strip() or "paper"
        status = "skipped_landing_page"
        local_path = ""
        if url.startswith("http") and not url.lower().endswith((".html", ".htm")):
            fname = url.split("/")[-1] or f"{paper_id}_downloaded_file"
            dest = download_dir / fname
            if dest.exists() and dest.stat().st_size > 0:
                status = "already_present"
                local_path = str(dest)
            else:
                try:
                    print(f"[INFO] Downloading {paper_id} -> {dest}")
                    urllib.request.urlretrieve(url, dest)  # noqa: S310
                    status = "downloaded"
                    local_path = str(dest)
                except Exception as e:  # noqa: BLE001
                    status = f"failed: {e!s}"
        elif not url:
            status = "no_url"
        else:
            status = "manual_download_required_or_landing_page"
        rec = r.to_dict()
        rec["download_status"] = status
        rec["local_path"] = local_path
        rows.append(rec)
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None, help="Path to project_config.yaml")
    ap.add_argument(
        "--out_dir",
        required=True,
        help="Output directory (e.g. F:/Allen_ABC_Project/output/preprocess)",
    )
    ap.add_argument(
        "--paper_manifest",
        default=None,
        help="Optional path to paper_source_manifest_template.csv to attempt downloads",
    )
    ap.add_argument(
        "--paper_download_dir",
        default=None,
        help="Where to save paper raw files; required if --paper_manifest is provided",
    )
    ap.add_argument(
        "--skip_allen_metadata",
        action="store_true",
        help="Do not call AbcProjectCache (use only when verifying env)",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = load_config(args.config)

    summary_rows: list[dict] = []
    allen_rows: list[dict] = []

    summary_rows.append({"item": "python", "value": sys.version.split()[0]})
    summary_rows.append({"item": "cache_dir", "value": str(cfg.cache_dir)})
    summary_rows.append({"item": "manifest_version_pinned", "value": cfg.manifest_version or "<latest>"})
    summary_rows.append(
        {
            "item": "disk_free_at_cache_GiB",
            "value": _bytes_to_gib(_disk_free(cfg.cache_dir)),
        }
    )

    if args.skip_allen_metadata:
        print("[INFO] --skip_allen_metadata set; not contacting Allen S3.")
    else:
        try:
            cache = open_abc_cache(cfg)
            summary_rows.append(
                {"item": "current_manifest", "value": str(getattr(cache, "current_manifest", "?"))}
            )
            _download_allen_metadata(cache, allen_rows)
        except Exception as e:  # noqa: BLE001
            summary_rows.append({"item": "abc_cache_error", "value": repr(e)})
            print(f"[ERROR] Could not open AbcProjectCache: {e}")

    n_files, total_bytes = _measure_cache(cfg.cache_dir)
    summary_rows.append({"item": "cache_total_files", "value": n_files})
    summary_rows.append({"item": "cache_total_GiB", "value": _bytes_to_gib(total_bytes)})

    paper_df = pd.DataFrame()
    if args.paper_manifest:
        paper_dir = Path(args.paper_download_dir or out_dir / "paper_raw")
        paper_df = _download_paper_manifest(Path(args.paper_manifest), paper_dir)
        if not paper_df.empty:
            paper_df.to_csv(out_dir / "paper_download_status.csv", index=False)
            print(f"[OK] paper_download_status.csv: {len(paper_df)} rows")

    pd.DataFrame(summary_rows).to_csv(out_dir / "preprocess_summary.csv", index=False)
    if allen_rows:
        pd.DataFrame(allen_rows).to_csv(out_dir / "allen_metadata_files.csv", index=False)
    write_run_log(
        out_dir,
        "A00_preprocess_download",
        {
            "cache_dir": str(cfg.cache_dir),
            "manifest_version": cfg.manifest_version,
            "paper_manifest": args.paper_manifest,
            "skip_allen_metadata": args.skip_allen_metadata,
            "n_files_in_cache": n_files,
            "cache_total_GiB": _bytes_to_gib(total_bytes),
        },
    )
    print(f"[DONE] preprocess outputs under {out_dir}")


if __name__ == "__main__":
    main()

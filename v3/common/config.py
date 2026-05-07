"""Shared config + run-log helpers used across modules A/B/C/D."""
from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError as e:  # pragma: no cover - tested via runtime usage
    raise SystemExit(
        "PyYAML required for v3 pipeline. Install with: pip install pyyaml"
    ) from e


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "project_config.yaml"


@dataclass
class Thresholds:
    min_cells: int
    min_pct_expr_candidate: float
    min_mean_log2_expr_candidate: float
    strong_pct_expr: float
    strong_mean_log2_expr: float


@dataclass
class ProjectConfig:
    raw: dict[str, Any]
    cache_dir: Path
    project_dir: Path
    input_dir: Path
    output_dir: Path
    manifest_version: str | None
    thresholds: Thresholds
    expression_data_type: str
    chunk_size: int
    regions: list[dict[str, str]]


def load_config(path: str | Path | None = None) -> ProjectConfig:
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    paths = raw.get("paths", {})
    th = raw.get("thresholds", {})
    al = raw.get("allen", {})
    return ProjectConfig(
        raw=raw,
        cache_dir=Path(os.environ.get("ABC_ATLAS_CACHE", paths.get("cache_dir", "."))),
        project_dir=Path(paths.get("project_dir", ".")),
        input_dir=Path(paths.get("input_dir", "inputs")),
        output_dir=Path(paths.get("output_dir", "outputs")),
        manifest_version=al.get("manifest_version"),
        thresholds=Thresholds(
            min_cells=int(th.get("min_cells", 30)),
            min_pct_expr_candidate=float(th.get("min_pct_expr_candidate", 10)),
            min_mean_log2_expr_candidate=float(th.get("min_mean_log2_expr_candidate", 0.25)),
            strong_pct_expr=float(th.get("strong_pct_expr", 20)),
            strong_mean_log2_expr=float(th.get("strong_mean_log2_expr", 0.5)),
        ),
        expression_data_type=str(al.get("expression_data_type", "log2")),
        chunk_size=int(al.get("chunk_size", 8192)),
        regions=raw.get("regions", []),
    )


def _git_hash(repo_dir: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def write_run_log(out_dir: Path, module: str, params: dict[str, Any]) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "run_log.jsonl"
    repo_root = Path(__file__).resolve().parents[2]
    record = {
        "module": module,
        "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "git_commit": _git_hash(repo_root),
        "params": params,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return log_path


def open_abc_cache(config: ProjectConfig):
    """Open AbcProjectCache, optionally pinning manifest version."""
    from abc_atlas_access.abc_atlas_cache.abc_project_cache import AbcProjectCache

    config.cache_dir.mkdir(parents=True, exist_ok=True)
    cache = AbcProjectCache.from_cache_dir(config.cache_dir)
    if config.manifest_version:
        try:
            cache.load_manifest(config.manifest_version)
            print(f"[INFO] Pinned manifest: {config.manifest_version}")
        except Exception as e:  # noqa: BLE001
            print(
                f"[WARN] Could not pin manifest {config.manifest_version}: {e}; "
                f"using current manifest {getattr(cache, 'current_manifest', '?')}"
            )
    return cache

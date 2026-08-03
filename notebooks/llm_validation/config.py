from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def find_project_root() -> Path:
    for path in [Path.cwd().resolve(), *Path.cwd().resolve().parents]:
        if (path / "config.txt").exists():
            return path
    raise RuntimeError("config.txt not found; run this command inside the repository")


PROJECT_ROOT = find_project_root()
load_dotenv(PROJECT_ROOT / ".env")

MODEL = os.environ.get("LLM_VALIDATION_MODEL", "google/gemma-4-31B-it")
MODEL_REVISION = os.environ.get(
    "LLM_VALIDATION_MODEL_REVISION",
    "518276fb130dc81caf9a4f772e65e63ef2526493",
)
MODEL_VARIANT = "bf16-thinking"
BASE_URL = os.environ.get("LLM_VALIDATION_BASE_URL", "http://127.0.0.1:8000/v1")
TEMPERATURE = 0.2
MAX_COMPLETION_TOKENS = 4096
DEFAULT_CONCURRENCY = int(os.environ.get("LLM_VALIDATION_CONCURRENCY", "32"))
REQUEST_TIMEOUT_SECONDS = 900.0
MAX_ATTEMPTS = 3
RANDOM_SEED = 42
SMOKE_NOTES = 128
RUN_ID = os.environ.get("LLM_VALIDATION_RUN_ID", "gemma-4-31b-it-scckn-v1")
STAGE15_RUN_ID = "gemma-4-31b-it-scckn-stage1-5-opinion-v1"
STAGE15_CONCURRENCY = 64
STAGE2_EXPANDED_RUN_ID = "gemma-4-31b-it-scckn-stage2-expanded-v1"
STAGE2_EXPANDED_CONCURRENCY = 64
STAGE2_EXPANDED_SHARD_SIZE = 2000
STAGE2_RESCUE_THRESHOLD = 50
STAGE1_RUNS = 1
STAGE2_RUNS = 1
EXPORT_EVERY = 100
STAGE1_SHARD_SIZE = 2000


@dataclass(frozen=True)
class RunPaths:
    root: Path
    database: Path
    database_backup: Path
    input_manifest: Path
    input_csv: Path
    run_manifest: Path
    stage1_results: Path
    stage1_unresolved: Path
    stage2_results: Path
    stage2_unresolved: Path
    calls_export: Path
    raw_calls_export: Path
    summary: Path
    benchmark: Path


def _paths_for_root(root: Path) -> RunPaths:
    return RunPaths(
        root=root,
        database=root / "calls.sqlite3",
        database_backup=root / "calls.backup.sqlite3",
        input_manifest=root / "input_manifest.parquet",
        input_csv=root / "input_manifest.csv",
        run_manifest=root / "run_manifest.json",
        stage1_results=root / "stage1_results.parquet",
        stage1_unresolved=root / "stage1_unresolved.parquet",
        stage2_results=root / "stage2_results.parquet",
        stage2_unresolved=root / "stage2_unresolved.parquet",
        calls_export=root / "calls.parquet",
        raw_calls_export=root / "raw_calls.jsonl.gz",
        summary=root / "summary.json",
        benchmark=root / "benchmark.json",
    )


def get_run_paths(*, smoke: bool) -> RunPaths:
    if smoke:
        root = PROJECT_ROOT / ".artifacts" / "smoke" / "llm_validation" / RUN_ID
    else:
        root = PROJECT_ROOT / "data" / "llm_validation" / "runs" / RUN_ID
    return _paths_for_root(root)


def get_stage1_shard_paths(batch_number: int) -> RunPaths:
    if batch_number < 2:
        raise ValueError("Stage 1 shard batch_number must be at least 2")
    canonical = get_run_paths(smoke=False)
    root = canonical.root / "shards" / f"stage1-batch-{batch_number:04d}"
    return _paths_for_root(root)


def get_stage15_paths() -> RunPaths:
    root = PROJECT_ROOT / "data" / "llm_validation" / "runs" / STAGE15_RUN_ID
    paths = _paths_for_root(root)
    return RunPaths(
        root=paths.root,
        database=paths.database,
        database_backup=paths.database_backup,
        input_manifest=paths.input_manifest,
        input_csv=paths.input_csv,
        run_manifest=paths.run_manifest,
        stage1_results=root / "stage1_5_results.parquet",
        stage1_unresolved=root / "stage1_5_unresolved.parquet",
        stage2_results=root / "stage2_not_applicable.parquet",
        stage2_unresolved=root / "stage2_unresolved_not_applicable.parquet",
        calls_export=paths.calls_export,
        raw_calls_export=paths.raw_calls_export,
        summary=paths.summary,
        benchmark=paths.benchmark,
    )


def get_stage2_expanded_paths() -> RunPaths:
    root = PROJECT_ROOT / "data" / "llm_validation" / "runs" / STAGE2_EXPANDED_RUN_ID
    return _paths_for_root(root)


def get_stage2_expanded_shard_paths(batch_number: int) -> RunPaths:
    if batch_number < 1:
        raise ValueError("Expanded Stage 2 shard batch_number must be at least 1")
    canonical = get_stage2_expanded_paths()
    root = canonical.root / "shards" / f"stage2-batch-{batch_number:04d}"
    return _paths_for_root(root)
